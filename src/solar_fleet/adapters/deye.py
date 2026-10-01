from __future__ import annotations

import asyncio
import hashlib
import json
import time
from datetime import UTC, datetime
from typing import Any
from urllib.parse import quote

import httpx
from jsonschema import Draft7Validator

from ..budgets import Budgets
from ..catalog import data
from ..domain import Ack, Configuration, Device, OrderResult, VendorCall, VendorError
from ..transport_guard import check_transport_guard
from .tou_builder import (
    TouSlotProgramme,
    encode_deye_tou,
)

CONTRACTS = {row["path"]: row for row in data("deye-contract.json")}

# ---------------------------------------------------------------------------
# TTL constants (from batpred/deye_const.py)
# ComponentBase ticks run() every 60s, so DEYE_TTL_LIVE of 1 = "every tick".
# Clocks seeded from storage.age() at startup so cadence survives restart.
# ---------------------------------------------------------------------------
DEYE_TTL_STATIC = 8 * 60 * 60    # station/device discovery — 8 hours
DEYE_TTL_CONFIG = 15 * 60         # config/battery — 15 minutes
DEYE_TTL_LIVE = 60                 # telemetry/energy counters — 1 minute

# DEYE executes one control order at a time per device. A second command sent
# while one is still running is rejected with code "2104004" — means "retry
# shortly", not "rejected", so it is logged as back-pressure rather than failure.
# (Source: batpred/deye_const.py DEYE_BUSY_CODES)
DEYE_BUSY_CODES: frozenset[str] = frozenset({"2104004"})
DEYE_BUSY_MARKERS: tuple[str, ...] = (
    "command concurrent running",
    "concurrent running",
    "order is running",
)

# DEYE does NOT answer an expired/invalid bearer token with HTTP 401 — it
# returns HTTP 200 carrying a body-level failure.  Status-code-only handling
# therefore never triggers a refresh, so the transport also checks the body.
# (Source: batpred/deye_const.py DEYE_AUTH_ERROR_MARKERS)
DEYE_AUTH_ERROR_MARKERS: tuple[str, ...] = (
    "auth invalid token",
    "invalid token",
    "token expired",
    "authentication failed",
    "unauthorized",
)

HOSTS = {
    "eu": "https://eu1-developer.deyecloud.com",
    "am": "https://us1-developer.deyecloud.com",
    "india": "https://india-developer.deyecloud.com",
}
# Deliberately explicit: mutations elsewhere in the catalog are NOT accidentally exposed as reads.
READS = {
    "/v1.0/account/info",
    "/v1.0/station/list",
    "/v1.0/station/device",
    "/v1.0/station/listWithDevice",
    "/v1.0/station/latest",
    "/v1.0/station/history",
    "/v1.0/station/history/power",
    "/v1.0/station/alertList",
    "/v1.0/device/list",
    "/v1.0/device/latest",
    "/v1.0/device/history",
    "/v1.0/device/historyRaw",
    "/v1.0/device/measurePoints",
    "/v1.0/device/alertList",
    "/v1.0/config/battery",
    "/v1.0/config/system",
    "/v1.0/config/tou",
    "/v1.0/strategy/dynamicControl/read",
    "/v1.0/strategy/dynamicControl/readResult",
}


def source_time(value: Any) -> datetime | None:
    # DEYE_API_001 collectionTime is Unix seconds. Ambiguous strings/milliseconds are not guessed.
    if not isinstance(value, (int, float)) or isinstance(value, bool):
        return None
    try:
        if not 0 < value < 10_000_000_000:
            return None
        return datetime.fromtimestamp(value, UTC)
    except (OverflowError, ValueError, OSError):
        return None


class Deye:
    evidence_ids = ["DEYE_API_001"]
    per_poll = 50

    version = "0.1.0"

    def __init__(
        self,
        integration: dict,
        credentials: dict,
        *,
        client: httpx.AsyncClient | None = None,
        budgets: Budgets | None = None,
    ):
        if integration.get("region") not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.integration = integration
        self.credentials = credentials
        self.host = HOSTS[integration["region"]]
        account_identity = [
            self.host,
            credentials.get("identity_field"),
            credentials.get("identity_value"),
            credentials.get("company_id"),
        ]
        self.account_budget_key = hashlib.sha256(json.dumps(account_identity).encode()).hexdigest()
        self.client = client or httpx.AsyncClient(
            timeout=httpx.Timeout(20), follow_redirects=False, trust_env=False
        )
        self.budgets = budgets or Budgets()
        self.access_token = None
        self.expires_at = 0.0
        self.auth_lock = asyncio.Lock()
        self.cooldown_until = 0.0

        # TTL-based 3-tier cache
        # Each tier tracks the last successful fetch time so callers can skip
        # repeated API requests within the TTL window.
        self._cache_times: dict[str, float] = {
            "static": 0.0,    # station/device list
            "config": 0.0,    # battery/system/tou config
            "live": 0.0,      # telemetry (latest)
        }
        self._cache: dict[str, Any] = {}
        self._busy_until: float = 0.0  # back-off after BUSY_CODE

    async def close(self):
        await self.client.aclose()

    async def _http(self, method: str, path: str, body: dict | None, *, token=None, params=None, before_send=None) -> dict:
        check_transport_guard()
        if time.monotonic() < self.cooldown_until:
            raise VendorError("vendor_backoff_active")
        devices = body.get("deviceList", []) if body else []
        if body and "deviceSn" in body:
            devices = [body["deviceSn"]]
        await self.budgets.acquire(self.account_budget_key, devices)
        check_transport_guard()
        headers = {"Authorization": f"Bearer {token}"} if token else {}
        # Revalidate after authentication and the budget lock, not before them.
        # Once client.request starts, a physical outcome can no longer be ruled out.
        if before_send is not None:
            before_send()
        try:
            # Use a fully allowlisted host and no redirects/proxies; credentials never leave the selected region.
            response = await self.client.request(
                method, self.host + path, json=body, params=params, headers=headers
            )
        except (httpx.TimeoutException, httpx.NetworkError, httpx.ProtocolError):
            raise VendorError("vendor_network_outcome_unknown") from None
        # Only guarded reads carry this task-local context. Sends retain ACKs
        # before the command engine's post-send authority check.
        check_transport_guard()
        if response.status_code == 429:
            try:
                delay = min(3600, max(60, int(response.headers.get("Retry-After", "60"))))
            except ValueError:
                delay = 60
            self.cooldown_until = time.monotonic() + delay
            raise VendorError("vendor_rate_limited")
        if response.status_code in (401, 403):
            self.access_token = None
            self.expires_at = 0
            raise VendorError("vendor_auth_or_permission_denied")
        if response.status_code != 200:
            raise VendorError("vendor_http_error")
        # Never persist/log raw error bodies: vendors may echo passwords, tokens or private account details.
        if len(response.content) > 10_000_000:
            raise VendorError("vendor_response_too_large")
        try:
            payload = response.json()
        except ValueError:
            raise VendorError("vendor_invalid_json") from None
        if not isinstance(payload, dict):
            raise VendorError("vendor_request_rejected")

        # DEYE returns HTTP 200 even for auth failures — must inspect body.
        # (Source: batpred/deye_const.py DEYE_AUTH_ERROR_MARKERS)
        msg_lower = str(payload.get("msg", "")).lower()
        code_str = str(payload.get("code", ""))
        if any(marker in msg_lower for marker in DEYE_AUTH_ERROR_MARKERS):
            self.access_token = None
            self.expires_at = 0.0
            raise VendorError("vendor_auth_or_permission_denied")

        # BUSY code: "command concurrent running" — back-pressure, not failure.
        # (Source: batpred/deye_const.py DEYE_BUSY_CODES, DEYE_BUSY_MARKERS)
        if code_str in DEYE_BUSY_CODES or any(m in msg_lower for m in DEYE_BUSY_MARKERS):
            self._busy_until = time.monotonic() + 30  # 30s back-pressure
            raise VendorError("deye_command_busy_retry")

        if payload.get("success") is not True:
            raise VendorError("vendor_request_rejected")
        if code_str not in ("", "1000000"):
            raise VendorError("vendor_request_rejected")
        return payload

    async def authenticate(self) -> str:
        async with self.auth_lock:
            check_transport_guard()
            if self.access_token and time.monotonic() < self.expires_at:
                return self.access_token
            c = self.credentials
            required = ("app_id", "app_secret", "password_sha256", "identity_field", "identity_value")
            if any(not c.get(k) for k in required) or c["identity_field"] not in (
                "email",
                "username",
                "mobile",
            ):
                raise VendorError("credentials_incomplete")
            body = {
                "appSecret": c["app_secret"],
                "password": c["password_sha256"],
                c["identity_field"]: c["identity_value"],
            }
            if c.get("company_id") is not None:
                body["companyId"] = c["company_id"]
            if c.get("country_code"):
                body["countryCode"] = c["country_code"]
            payload = await self._http("POST", "/v1.0/account/token", body, params={"appId": c["app_id"]})
            token = payload.get("accessToken")
            lifetime = payload.get("expiresIn")
            if (
                not isinstance(token, str)
                or not token.strip()
                or not isinstance(lifetime, (int, float))
                or lifetime <= 0
            ):
                raise VendorError("vendor_invalid_token_response")
            self.access_token = token.removeprefix("Bearer ").strip()
            self.expires_at = time.monotonic() + max(0, lifetime - 60)
            return self.access_token

    @staticmethod
    def validate(path: str, body: dict):
        if path not in CONTRACTS or not Draft7Validator(CONTRACTS[path]["request_schema"]).is_valid(body):
            raise VendorError("request_outside_official_contract")

    async def read(self, path: str, body: dict) -> dict:
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        self.validate(path, body)
        return await self._http("POST", path, body, token=await self.authenticate())

    async def pages(
        self, path: str, field: str, *, body: dict | None = None, total_field="total", size=100
    ) -> list[dict]:
        result = []
        signatures = set()
        for page in range(1, 501):
            payload = await self.read(path, {**(body or {}), "page": page, "size": size})
            rows = payload.get(field)
            total = payload.get(total_field)
            if not isinstance(rows, list) or any(not isinstance(row, dict) for row in rows):
                raise VendorError("vendor_invalid_page")
            signature = hashlib.sha256(json.dumps(rows, sort_keys=True).encode()).hexdigest()
            if rows and signature in signatures:
                raise VendorError("vendor_repeated_page")
            signatures.add(signature)
            result.extend(rows)
            if isinstance(total, int) and len(result) >= total:
                return result
            if not rows:
                if isinstance(total, int) and len(result) < total:
                    raise VendorError("vendor_incomplete_pagination")
                return result
            if not isinstance(total, int) and len(rows) < size:
                return result
        raise VendorError("vendor_pagination_limit")

    async def stations(self) -> list[dict]:
        return await self.pages("/v1.0/station/list", "stationList")

    async def devices(self, station_id: int) -> list[dict]:
        return await self.pages("/v1.0/station/device", "deviceListItems", body={"stationIds": [station_id]})

    async def account_devices(self) -> list[dict]:
        return await self.pages("/v1.0/device/list", "deviceList")

    async def latest(self, serials: list[str]) -> list[dict]:
        result = []
        for offset in range(0, len(serials), 10):
            payload = await self.read("/v1.0/device/latest", {"deviceList": serials[offset : offset + 10]})
            rows = payload.get("deviceDataList")
            if not isinstance(rows, list) or any(not isinstance(r, dict) for r in rows):
                raise VendorError("vendor_invalid_latest_data")
            result.extend(rows)
        return result

    async def dynamic_control_read(self, serial: str) -> dict:
        """Trigger an on-demand hardware configuration read via Deye Cloud."""
        read_path = "/v1.0/strategy/dynamicControl/read"
        result_path = "/v1.0/strategy/dynamicControl/readResult"
        if read_path not in CONTRACTS or result_path not in CONTRACTS:
            raise VendorError("dynamic_control_read_not_in_contract")
        payload = await self.read(read_path, {"deviceSn": serial})
        order_id = payload.get("orderId")
        if not order_id:
            raise VendorError("dynamic_read_missing_order_id")
        for _ in range(15):  # poll up to 30 seconds
            await asyncio.sleep(2.0)
            res = await self.read(result_path, {"orderId": order_id})
            status = str(res.get("status", ""))
            if status == "666" or res.get("success"):
                return res
            if status in ("400", "500"):
                raise VendorError("dynamic_read_failed")
        raise VendorError("dynamic_read_timeout")

    async def configuration(self, device: Device, *, dynamic_read: bool = False) -> Configuration:
        values = {}
        latest_ts = None
        for name in ("system", "battery", "tou"):
            payload = await self.read("/v1.0/config/" + name, {"deviceSn": device.vendor_id})
            for ts_key in ("collectionTime", "updateTime", "deviceTime", "timestamp", "time", "lastUpdateTime"):
                if ts_key in payload:
                    parsed = source_time(payload[ts_key])
                    if parsed is not None:
                        if latest_ts is None or parsed > latest_ts:
                            latest_ts = parsed
            values.update(
                {k: v for k, v in payload.items() if k not in ("code", "msg", "requestId", "success")}
            )

        if dynamic_read and latest_ts is None and "/v1.0/strategy/dynamicControl/read" in CONTRACTS:
            try:
                dyn = await self.dynamic_control_read(device.vendor_id)
                if isinstance(dyn, dict):
                    for ts_key in ("collectionTime", "updateTime", "timestamp"):
                        if ts_key in dyn:
                            parsed = source_time(dyn[ts_key])
                            if parsed is not None:
                                latest_ts = parsed
                    if "touList" in dyn:
                        values["touList"] = dyn["touList"]
                    for k, v in dyn.items():
                        if k not in ("code", "msg", "requestId", "success", "orderId", "status"):
                            values[k] = v
            except Exception:
                pass

        if latest_ts is not None:
            return Configuration(values=values, device_timestamp=latest_ts, freshness_verified=True)
        return Configuration(values=values, freshness_verified=False)

    async def history(self, serial: str, start: int, end: int, points: list[str]) -> dict:
        if end <= start or end - start > 86400 or not points or len(points) > 100:
            raise VendorError("history_window_or_points_invalid")
        return await self.read(
            "/v1.0/device/historyRaw",
            {"deviceSn": serial, "startTimestamp": start, "endTimestamp": end, "measurePoints": points},
        )

    async def alerts(self, serial: str, start: int, end: int) -> list[dict]:
        if end <= start or end - start > 7 * 86400:
            raise VendorError("alert_window_invalid")
        return await self.pages(
            "/v1.0/device/alertList",
            "alertList",
            body={"deviceSn": serial, "startTimestamp": start, "endTimestamp": end},
            size=100,
        )

    async def send(self, call: VendorCall, *, before_send=None) -> Ack:
        if call.path not in CONTRACTS or CONTRACTS[call.path]["mode"] != "CONTROL":
            raise VendorError("control_endpoint_not_allowed")
        if call.path == "/v1.0/order/customControl":
            raise VendorError("raw_control_locked")
        # BUSY back-pressure gate
        if time.monotonic() < self._busy_until:
            raise VendorError("deye_command_busy_retry")
        self.validate(call.path, call.body)
        # Exactly one request; retrying after a timeout could dispatch a second physical action.
        payload = await self._http(
            "POST", call.path, call.body, token=await self.authenticate(), before_send=before_send
        )
        order_id = payload.get("orderId")
        if not isinstance(order_id, (str, int)) or isinstance(order_id, bool) or not str(order_id):
            raise VendorError("vendor_missing_order_outcome_unknown")
        return Ack(order_id=str(order_id), online=payload.get("connectionStatus") == 1)

    async def order(self, order_id: str) -> OrderResult:
        if not order_id or len(order_id) > 200:
            raise VendorError("invalid_order_id")
        payload = await self._http(
            "GET", "/v1.0/order/" + quote(order_id, safe=""), None, token=await self.authenticate()
        )
        status = str(payload.get("status"))
        # Official registry documents 666=success, 400=terminated, 500=failed; unknown codes keep waiting.
        state = (
            "SUCCEEDED"
            if status == "666"
            else "CANCELLED"
            if status == "400"
            else "FAILED"
            if status == "500"
            else "PENDING"
        )
        return OrderResult(state=state, vendor_status=status)

    # ------------------------------------------------------------------
    # TTL cache helpers
    # ------------------------------------------------------------------
    def _cache_fresh(self, tier: str) -> bool:
        """Return True if the cache for the given tier is still within TTL."""
        ttls = {"static": DEYE_TTL_STATIC, "config": DEYE_TTL_CONFIG, "live": DEYE_TTL_LIVE}
        return time.monotonic() - self._cache_times.get(tier, 0.0) < ttls.get(tier, 0)

    def _cache_set(self, tier: str, key: str, value: Any) -> None:
        self._cache[key] = value
        self._cache_times[tier] = time.monotonic()

    def _cache_get(self, key: str) -> Any:
        return self._cache.get(key)

    async def stations_cached(self) -> list[dict]:
        """Return station list, using static-tier cache (8h TTL)."""
        if self._cache_fresh("static") and self._cache_get("stations") is not None:
            return self._cache_get("stations")
        result = await self.stations()
        self._cache_set("static", "stations", result)
        return result

    async def configuration_cached(self, device: Device) -> Configuration:
        """Return device configuration, using config-tier cache (15min TTL)."""
        cache_key = f"config_{device.vendor_id}"
        if self._cache_fresh("config") and self._cache_get(cache_key) is not None:
            return self._cache_get(cache_key)
        result = await self.configuration(device)
        self._cache_set("config", cache_key, result)
        return result

    async def latest_cached(self, serials: list[str]) -> list[dict]:
        """Return latest telemetry, using live-tier cache (1min TTL)."""
        cache_key = "latest_" + "_".join(sorted(serials))
        if self._cache_fresh("live") and self._cache_get(cache_key) is not None:
            return self._cache_get(cache_key)
        result = await self.latest(serials)
        self._cache_set("live", cache_key, result)
        return result

    # ------------------------------------------------------------------
    # TOU write — requires /v1.0/strategy/dynamicControl to be in CONTRACTS
    # and the account to have the strategy write scope.
    # Source: batpred/deye.py strategy_dynamic_control + tou_schedule.py
    # ------------------------------------------------------------------
    async def set_tou_schedule(
        self,
        device_sn: str,
        slots: list[TouSlotProgramme],
        *,
        before_send=None,
    ) -> Ack:
        """Write a 6-slot TOU programme to the device via Deye Cloud API.

        Validates that slots are chronological and start at 00:00 before
        dispatching (see tou_builder.py _validate_programme).

        Args:
            device_sn: device serial number
            slots: list of TouSlotProgramme (must have <= 6 slots for Deye)
            before_send: optional callback called immediately before network send

        Raises:
            VendorError("tou_write_not_in_contract") if the control endpoint is
            not in CONTRACTS (e.g. account scope not granted).
        """
        TOU_WRITE_PATH = "/v1.0/strategy/dynamicControl"
        if TOU_WRITE_PATH not in CONTRACTS:
            raise VendorError("tou_write_not_in_contract")
        if CONTRACTS[TOU_WRITE_PATH].get("mode") != "CONTROL":
            raise VendorError("control_endpoint_not_allowed")
        encoded = encode_deye_tou(slots[:6])  # Deye firmware has 6 slots
        body = {"deviceSn": device_sn, "touList": encoded}
        call = VendorCall(path=TOU_WRITE_PATH, body=body)
        return await self.send(call, before_send=before_send)
