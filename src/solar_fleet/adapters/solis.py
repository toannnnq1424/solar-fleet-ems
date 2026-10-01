"""SolisCloud user HMAC API and OAuth2 API.

Source references:
- SOLIS_DEV_DATA_002: SolisCloud API V2.0 data endpoints
- SOLIS_DEV_AUTH_002: SolisCloud HMAC-SHA1 authentication
- SOLIS_CONTROL_001: SolisCloud Device Control API V2.0
Evidence grade: C (API docs behind activation; community implementations available)

Critical: Solis exposes TWO distinct API surfaces with DIFFERENT route namespaces:
  1. HMAC host (soliscloud.com:13333): /v1/api/*, /v2/api/*
  2. OAuth2 host (api-oauth2.soliscloud.com): /api/access_data/*, /api/control_device/*

Using HMAC routes on the OAuth host returns HTTP 200 with an XML
<ForbiddenException> body that looks like a failed auth attempt, causing infinite
token refresh loops.  Route translation via SOLIS_OAUTH_ENDPOINT_MAP is mandatory.
(Source: batpred/solis.py — verified live 2026-07-21)

Public protocol docs do not yet specify timestamp units or stable list pagination.
Retain raw values; report incomplete discovery instead of inventing a cursor.
"""

from __future__ import annotations

import asyncio
import base64
import hashlib
import hmac
import time
from datetime import datetime
from email.utils import format_datetime
from typing import Any

from ..domain import VendorError, utcnow
from .cloud import ReadCloud, compact, records

# ---------------------------------------------------------------------------
# HMAC host (default) — uses HMAC-SHA1 Authorization header
# ---------------------------------------------------------------------------
HOSTS = {"global": "https://www.soliscloud.com:13333"}

# ---------------------------------------------------------------------------
# OAuth2 host — uses Bearer token; route namespace differs from HMAC host
# VERIFIED: HMAC paths return XML ForbiddenException on this host
# (Source: batpred/solis.py SOLIS_OAUTH_BASE_URL + SOLIS_OAUTH_ENDPOINTS)
# ---------------------------------------------------------------------------
OAUTH_HOST = "https://api-oauth2.soliscloud.com"

# Translate HMAC-side route paths to the OAuth2-side namespace
# The HMAC paths return XML <ForbiddenException> on the OAuth host;
# these translated paths are the correct equivalents verified live.
SOLIS_OAUTH_ENDPOINT_MAP: dict[str, str] = {
    "/v1/api/userStationList": "/api/access_data/userStationList",
    "/v1/api/inverterList": "/api/access_data/inverterList",
    "/v1/api/inverterDetail": "/api/access_data/inverterDetail",
    "/v1/api/inverterDay": "/api/access_data/inverterDay",
    "/v1/api/inverterMonth": "/api/access_data/inverterMonth",
    "/v1/api/inverterYear": "/api/access_data/inverterYear",
    "/v1/api/alarmList": "/api/access_data/alarmList",
    "/v1/api/stationDetail": "/api/access_data/stationDetail",
    "/v1/api/inverterAll": "/api/access_data/inverterAll",
    "/v1/api/inverterDetailList": "/api/access_data/inverterDetailList",
    "/v2/api/atRead": "/api/control_device/atRead",
    "/v2/api/atReadBatch": "/api/control_device/atReadBatch",
    "/v2/api/control": "/api/control_device/control",
}

# OAuth2-specific endpoints (only on OAuth host)
SOLIS_OAUTH_TOKEN_PATH = "/oauth2/token"
SOLIS_OAUTH_REFRESH_PATH = "/oauth2/refresh"

# TTL constants (consistent with batpred/solis.py patterns)
SOLIS_TTL_STATIC = 8 * 60 * 60    # station/device list: 8h
SOLIS_TTL_LIVE = 5 * 60           # telemetry: 5 minutes

# Deliberately explicit: mutations elsewhere are NOT accidentally exposed as reads.
READS = {
    "/v1/api/userStationList",
    "/v1/api/inverterList",
    "/v1/api/inverterDetail",
    "/v1/api/inverterDay",
    "/v1/api/inverterMonth",
    "/v1/api/inverterYear",
    "/v1/api/alarmList",
    "/v1/api/stationDetail",
    "/v1/api/inverterAll",
    "/v1/api/inverterDetailList",
}

# Solis native field mapping — native field catalogue; canonical mappings require reviewed evidence
SOLIS_NATIVE_POINTS = {
    "pac": {"metric": "active_power", "unit": "W", "unit_field": "pacStr"},
    "etoday": {"metric": "energy_today", "unit": "kWh", "unit_field": "etodayStr"},
    "etotal": {"metric": "energy_total", "unit": "kWh", "unit_field": "etotalStr"},
    "fac": {"metric": "grid_frequency", "unit": "Hz"},
    "batteryCapacitySoc": {"metric": "battery_soc", "unit": "%"},
    "batteryPower": {"metric": "battery_power", "unit": "W"},
    "batteryVoltage": {"metric": "battery_voltage", "unit": "V"},
    "batteryCurrent": {"metric": "battery_current", "unit": "A"},
    "batteryTemperature": {"metric": "battery_temp", "unit": "°C"},
    "familyLoadPower": {"metric": "load_power", "unit": "W"},
    "pSum": {"metric": "grid_power", "unit": "W"},
    "gridPurchasedTodayEnergy": {"metric": "import_energy_today", "unit": "kWh"},
    "gridSellTodayEnergy": {"metric": "export_energy_today", "unit": "kWh"},
    # Grid AC
    "uAc1": {"metric": "grid_voltage_r", "unit": "V"},
    "uAc2": {"metric": "grid_voltage_s", "unit": "V"},
    "uAc3": {"metric": "grid_voltage_t", "unit": "V"},
    "iAc1": {"metric": "grid_current_r", "unit": "A"},
    "iAc2": {"metric": "grid_current_s", "unit": "A"},
    "iAc3": {"metric": "grid_current_t", "unit": "A"},
    # PV strings
    "pow1": {"metric": "pv1_power", "unit": "W"},
    "pow2": {"metric": "pv2_power", "unit": "W"},
    "uPv1": {"metric": "pv1_voltage", "unit": "V"},
    "uPv2": {"metric": "pv2_voltage", "unit": "V"},
    "iPv1": {"metric": "pv1_current", "unit": "A"},
    "iPv2": {"metric": "pv2_current", "unit": "A"},
    # Inverter
    "inverterTemperature": {"metric": "inverter_temp", "unit": "°C"},
}


def signed_headers(path: str, body: bytes, key_id: str, secret: str, date: str) -> dict:
    content_type = "application/json;charset=UTF-8"
    digest = base64.b64encode(hashlib.md5(body).digest()).decode()
    message = "\n".join(["POST", digest, content_type, date, path]).encode()
    signature = base64.b64encode(hmac.new(secret.encode(), message, hashlib.sha1).digest()).decode()
    return {
        "Content-Type": content_type,
        "Content-MD5": digest,
        "Date": date,
        "Authorization": f"API {key_id}:{signature}",
    }


class Solis(ReadCloud):
    """SolisCloud adapter supporting both HMAC-SHA1 and OAuth2 authentication.

    Auth method is selected by the ``auth_method`` credential field:
    - ``"hmac"`` (default): HMAC-SHA1 with key_id + key_secret on soliscloud.com:13333
    - ``"oauth2"``: Bearer token on api-oauth2.soliscloud.com with route translation

    The OAuth2 route namespace differs from the HMAC namespace — HMAC routes
    return XML ForbiddenException on the OAuth host.  Route translation is
    handled transparently via SOLIS_OAUTH_ENDPOINT_MAP.
    (Source: batpred/solis.py, verified live 2026-07-21)
    """

    evidence_ids = ["SOLIS_DEV_DATA_002", "SOLIS_DEV_AUTH_002", "SOLIS_CONTROL_001"]
    version = "0.3.0"

    def __init__(self, integration, credentials, **kwargs):
        if integration.get("region") not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[integration["region"]]
        self._auth_method = credentials.get("auth_method", "hmac")
        if self._auth_method == "hmac":
            if any(not credentials.get(k) for k in ("key_id", "key_secret")):
                raise VendorError("credentials_incomplete")
        elif self._auth_method == "oauth2":
            if any(not credentials.get(k) for k in ("oauth_client_id", "oauth_client_secret")):
                raise VendorError("credentials_incomplete")
            # Override host for OAuth2 — different URL, different route namespace
            self.host = OAUTH_HOST
        else:
            raise VendorError("solis_unsupported_auth_method")
        super().__init__(integration, credentials, **kwargs)
        # OAuth2 token state
        self._oauth_token: str | None = None
        self._oauth_expires_at: float = 0.0
        self._oauth_refresh_token: str | None = None
        self._auth_lock = asyncio.Lock()
        # TTL cache
        self._cache: dict[str, Any] = {}
        self._cache_times: dict[str, float] = {}

    async def read(self, path, body):
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        if self._auth_method == "oauth2":
            return await self._read_oauth2(path, body)
        return await self._read_hmac(path, body)

    async def _read_hmac(self, path: str, body: dict) -> dict:
        """Read via HMAC-SHA1 auth on the HMAC host."""
        content = compact(body)
        headers = signed_headers(
            path,
            content,
            self.credentials["key_id"],
            self.credentials["key_secret"],
            format_datetime(utcnow(), usegmt=True),
        )
        payload = await self.http(path, content, headers=headers, serial=body.get("sn"))
        if str(payload.get("code")) != "0" or "data" not in payload:
            raise VendorError("vendor_request_rejected")
        return payload["data"]

    async def _get_oauth2_token(self) -> str:
        """Fetch or refresh the OAuth2 Bearer token.

        OAuth2 token endpoint is on the OAuth host, NOT the HMAC host.
        Returns a valid bearer token string.
        """
        async with self._auth_lock:
            if self._oauth_token and time.monotonic() < self._oauth_expires_at:
                return self._oauth_token
            c = self.credentials
            if self._oauth_refresh_token and time.monotonic() < self._oauth_expires_at + 300:
                # Try refresh before re-login
                try:
                    payload = await self.http(
                        SOLIS_OAUTH_REFRESH_PATH,
                        compact({"refresh_token": self._oauth_refresh_token,
                                 "grant_type": "refresh_token"}),
                        headers={"Content-Type": "application/json"},
                        method="POST",
                    )
                    token = payload.get("access_token")
                    if isinstance(token, str) and token:
                        self._oauth_token = token
                        self._oauth_expires_at = time.monotonic() + payload.get("expires_in", 3600) - 60
                        return self._oauth_token
                except VendorError:
                    pass  # Fall through to re-login
            # Full login
            payload = await self.http(
                SOLIS_OAUTH_TOKEN_PATH,
                compact({
                    "client_id": c["oauth_client_id"],
                    "client_secret": c["oauth_client_secret"],
                    "grant_type": "client_credentials",
                }),
                headers={"Content-Type": "application/json"},
                method="POST",
            )
            token = payload.get("access_token")
            if not isinstance(token, str) or not token:
                raise VendorError("solis_oauth2_token_invalid")
            self._oauth_token = token
            self._oauth_expires_at = time.monotonic() + payload.get("expires_in", 3600) - 60
            self._oauth_refresh_token = payload.get("refresh_token")
            return self._oauth_token

    async def _read_oauth2(self, path: str, body: dict) -> dict:
        """Read via OAuth2 Bearer auth on the OAuth host with route translation.

        CRITICAL: Use translated path, not the HMAC path.
        HMAC routes return XML ForbiddenException on the OAuth host.
        """
        oauth_path = SOLIS_OAUTH_ENDPOINT_MAP.get(path)
        if not oauth_path:
            raise VendorError("solis_oauth2_route_not_mapped")
        token = await self._get_oauth2_token()
        content = compact(body)
        payload = await self.http(
            oauth_path,
            content,
            headers={
                "Content-Type": "application/json",
                "Authorization": f"Bearer {token}",
            },
            serial=body.get("sn"),
        )
        if str(payload.get("code")) != "0" or "data" not in payload:
            # Check if this is an auth error (body-level, not HTTP-level)
            msg = str(payload.get("msg", "")).lower()
            if any(m in msg for m in ("invalid token", "token expired", "unauthorized", "forbidden")):
                self._oauth_token = None  # Force re-auth next call
                raise VendorError("vendor_auth_or_permission_denied")
            raise VendorError("vendor_request_rejected")
        return payload["data"]

    def validate_response(self, payload):
        """Override: Solis OAuth2 may return non-200 for auth failures."""
        # For HMAC path: standard check in _read_hmac
        # For OAuth2 path: handled in _read_oauth2
        # Base class validate_response checks payload["success"] which Solis doesn't use
        pass  # Solis uses {"code": "0"} not {"success": true}

    async def listing(self, path, body):
        data = await self.read(path, body)
        page = data.get("page") if isinstance(data, dict) else None
        if not isinstance(page, dict):
            raise VendorError("vendor_invalid_pagination")
        rows = records(page.get("records"))
        total = page.get("total")
        if type(total) is not int or total < len(rows):
            raise VendorError("vendor_invalid_pagination")
        if total != len(rows):
            # Official minId/pagination is marked Coming soon. Never claim all plants were discovered.
            raise VendorError("solis_pagination_contract_incomplete")
        return rows

    async def stations(self):
        return [
            {"id": r.get("id"), "name": r.get("stationName"), "native": r}
            for r in await self.listing("/v1/api/userStationList", {})
        ]

    async def station_detail(self, station_id):
        """Get station detail."""
        data = await self.read("/v1/api/stationDetail", {"id": station_id})
        return data

    async def devices(self, station_id):
        result = []
        for row in await self.listing("/v1/api/inverterList", {"stationId": station_id}):
            if str(row.get("stationId")) != str(station_id):
                raise VendorError("vendor_device_site_mismatch")
            result.append(
                {
                    "deviceSn": row.get("sn"),
                    "deviceType": "INVERTER",
                    "connectStatus": 1 if row.get("state") in (1, 3) else 0,
                    "model": row.get("productModel"),
                    "loggerSn": row.get("collectorSn"),
                    "native": row,
                }
            )
        return result

    async def latest(self, serials):
        result = []
        for serial in serials:
            row = await self.read("/v1/api/inverterDetail", {"sn": serial})
            if not isinstance(row, dict) or row.get("sn") != serial:
                raise VendorError("latest_response_device_mismatch")
            unit_fields = {"pac": "pacStr", "etoday": "etodayStr", "etotal": "etotalStr"}
            numeric = {
                "pac",
                "etoday",
                "etotal",
                "eToday",
                "eTotal",
                "fac",
                "batteryCapacitySoc",
                "batteryPower",
                "familyLoadPower",
                "pSum",
                "gridPurchasedTodayEnergy",
                "gridSellTodayEnergy",
                "iAc1",
                "iAc2",
                "iAc3",
                "uAc1",
                "uAc2",
                "uAc3",
            }
            points = [
                {"key": k, "value": row[k], "unit": row.get(unit_fields.get(k, ""))}
                for k in sorted(numeric)
                if k in row
            ]
            result.append(
                {
                    "deviceSn": serial,
                    "deviceState": 1 if row.get("state") in (1, 3) else 0,
                    "collectionTime": None,
                    "dataList": points,
                    "native": row,
                    "timestamp_state": "UNIT_NOT_DOCUMENTED",
                }
            )
        return result

    @staticmethod
    def history_date(value: str, fmt: str) -> str:
        try:
            parsed = datetime.strptime(value, fmt)
            if parsed.strftime(fmt) != value:
                raise ValueError
        except (ValueError, TypeError):
            raise VendorError("invalid_history_date") from None
        return value

    @staticmethod
    def history_currency(money: str) -> str:
        if (
            not isinstance(money, str)
            or len(money) != 3
            or not money.isascii()
            or not money.isalpha()
            or money != money.upper()
        ):
            raise VendorError("invalid_history_currency")
        return money

    async def history_day(self, serial: str, time_str: str, *, money: str, time_zone: int):
        """Native plant timeZone is required; do not infer it from the browser timezone."""
        if type(time_zone) is not int:
            raise VendorError("invalid_native_timezone")
        return await self.read(
            "/v1/api/inverterDay",
            {
                "sn": serial,
                "time": self.history_date(time_str, "%Y-%m-%d"),
                "money": self.history_currency(money),
                "timeZone": time_zone,
            },
        )

    async def history_month(self, serial: str, time_str: str, *, money: str):
        return await self.read(
            "/v1/api/inverterMonth",
            {
                "sn": serial,
                "month": self.history_date(time_str, "%Y-%m"),
                "money": self.history_currency(money),
            },
        )

    async def history_year(self, serial: str, time_str: str, *, money: str):
        return await self.read(
            "/v1/api/inverterYear",
            {
                "sn": serial,
                "year": self.history_date(time_str, "%Y"),
                "money": self.history_currency(money),
            },
        )

    async def alerts(self, station_id=None, serial=None, *, begin_date=None, end_date=None):
        # Solis marks minId/pagination Coming soon; listing fails if completeness cannot be proven.
        body = {}
        if station_id is not None:
            body["stationId"] = station_id
        if serial is not None:
            body["alarmDeviceSn"] = serial
        for key, value in (("alarmBeginTime", begin_date), ("alarmEndTime", end_date)):
            if value is not None:
                body[key] = self.history_date(value, "%Y-%m-%d")
        if begin_date and end_date and begin_date > end_date:
            raise VendorError("invalid_history_range")
        return await self.listing("/v1/api/alarmList", body)

    @staticmethod
    def decode_native_points(native_data: dict[str, Any]) -> list[dict[str, Any]]:
        """Preserve raw keys and values. Never apply local-register scales to cloud data."""
        return [
            {"key": key, "value": native_data[key], "unit": native_data.get(cfg.get("unit_field", ""))}
            for key, cfg in SOLIS_NATIVE_POINTS.items()
            if key in native_data
        ]
