"""Eybond cloud reads: platform-specific auth, bounded discovery and native telemetry.

Protocol researched against ha-dessmonitor@3b530bf34d91eef43ec2474d971019fa48c5ae16.
See THIRD_PARTY_NOTICES.md. No inferred local protocol, write mappings or device clock.
"""

from __future__ import annotations

import asyncio
import hashlib
import math
import time
from contextvars import ContextVar
from urllib.parse import quote_plus

import httpx

from ..domain import VendorError
from .cloud import ReadCloud, records

PLATFORMS = {
    "dessmonitor": ("https://api.dessmonitor.com", "authSource", "1"),
    "shinemonitor": ("https://ios.shinemonitor.com", "auth", "0"),
}
READ_ACTIONS = frozenset(
    {"queryPlants", "webQueryCollectorsEs", "queryCollectorDevices", "queryDeviceLastData"}
)
PAGE_SIZE = 50
MAX_COLLECTORS = 1000


class SignedQueryTransport(httpx.AsyncBaseTransport):
    """Keep credentials out of httpx's request URL logs, hooks and response history.

    The signed query exists only on the inner wire request. Never follow redirects or
    forward it to a different host. HTTP exceptions are converted to static messages.
    """

    def __init__(self, host, inner=None):
        self.host = host
        self.inner = inner or httpx.AsyncHTTPTransport(retries=0, trust_env=False)
        self.query = ContextVar("signed_query", default=None)

    async def handle_async_request(self, request):
        if str(request.url) != self.host + "/public/" or request.method != "GET":
            raise VendorError("dessmonitor_transport_target_invalid")
        query = self.query.get()
        if not isinstance(query, bytes):
            raise VendorError("dessmonitor_signature_required")
        wire = httpx.Request(
            "GET", request.url.copy_with(query=query), headers=request.headers, extensions=request.extensions
        )
        try:
            response = await self.inner.handle_async_request(wire)
        except httpx.HTTPError:
            raise VendorError("vendor_network_outcome_unknown") from None
        # Cookies and redirect locations can contain tokens; neither is a contract input.
        for name in ("set-cookie", "location"):
            if name in response.headers:
                del response.headers[name]
        response.request = request
        return response

    async def aclose(self):
        await self.inner.aclose()


def _identity(value, kind):
    if type(value) not in (str, int) or not str(value).strip() or len(str(value)) > 160:
        raise VendorError("dessmonitor_invalid_" + kind)
    return str(value)


def _integer(value, kind):
    if type(value) is not int or value < 0:
        raise VendorError("dessmonitor_invalid_" + kind)
    return value


class Dessmonitor(ReadCloud):
    version = "0.3.0"
    per_poll = 10
    evidence_ids = ["EYBOND_DESSMONITOR_AUDIT_001", "EYBOND_GUIDE_001"]

    def __init__(self, integration, credentials, *, transport=None, budgets=None):
        platform = integration.get("region")
        if platform not in PLATFORMS:
            raise VendorError("unsupported_data_center")
        self.host, self.auth_action, self.auth_source = PLATFORMS[platform]
        if any(
            not isinstance(credentials.get(k), str) or not credentials[k]
            for k in ("user_name", "password", "company_key")
        ):
            raise VendorError("credentials_incomplete")
        self.signed_transport = SignedQueryTransport(self.host, transport)
        client = httpx.AsyncClient(
            transport=self.signed_transport,
            timeout=20,
            follow_redirects=False,
            trust_env=False,
        )
        super().__init__(integration, credentials, client=client, budgets=budgets)
        self.access_token = self.secret = None
        self.expires_at = 0.0
        self.auth_lock = asyncio.Lock()
        self.plants = set()
        self.routes = {}
        self.serial_plants = {}
        self.inventory_ready = False

    def invalidate_auth(self):
        self.access_token = self.secret = None
        self.expires_at = 0.0

    def validate_response(self, payload):
        # Missing err is not success. Never echo vendor descriptions or signed URLs.
        if type(payload.get("err")) is not int or payload["err"] != 0:
            self.invalidate_auth()
            raise VendorError("dessmonitor_request_rejected")

    async def _request(self, action, parameters, *, login=False, serial=None):
        if (login and action != self.auth_action) or (not login and action not in READ_ACTIONS):
            raise VendorError("read_endpoint_not_allowed")
        action_string = (
            "&action="
            + action
            + "".join("&" + key + "=" + quote_plus(str(value)) for key, value in parameters.items())
        )
        salt = str(time.time_ns() // 1_000_000)
        prefix = (
            hashlib.sha1(self.credentials["password"].encode()).hexdigest()
            if login
            else self.secret + self.access_token
        )
        signature = hashlib.sha1((salt + prefix + action_string).encode()).hexdigest()
        query = "sign=" + signature + "&salt=" + salt
        if not login:
            query += "&token=" + quote_plus(self.access_token)
        query += action_string
        context_token = self.signed_transport.query.set(query.encode("ascii"))
        try:
            return await self.http("/public/", method="GET", serial=serial)
        finally:
            self.signed_transport.query.reset(context_token)

    async def authenticate(self):
        async with self.auth_lock:
            if self.access_token and time.monotonic() < self.expires_at:
                return self.access_token
            self.invalidate_auth()
            response = await self._request(
                self.auth_action,
                {
                    "usr": self.credentials["user_name"],
                    "company-key": self.credentials["company_key"],
                    "source": self.auth_source,
                    "_app_client_": "web",
                    "_app_id_": "solar-fleet-ems",
                    "_app_version_": self.version,
                },
                login=True,
            )
            data = response.get("dat")
            if not isinstance(data, dict):
                raise VendorError("vendor_invalid_token")
            token, secret, lifetime = data.get("token"), data.get("secret"), data.get("expire")
            if (
                not isinstance(token, str)
                or not token
                or len(token) > 4096
                or not isinstance(secret, str)
                or not secret
                or len(secret) > 4096
                or type(lifetime) is not int
                or lifetime <= 0
            ):
                raise VendorError("vendor_invalid_token")
            self.access_token, self.secret = token, secret
            lifetime = min(lifetime, 7 * 86400)
            self.expires_at = time.monotonic() + lifetime - min(300, lifetime / 10)
            return token

    async def read(self, action, parameters, *, serial=None):
        if action not in READ_ACTIONS:
            raise VendorError("read_endpoint_not_allowed")
        await self.authenticate()
        # Failed grants/auth are surfaced; no retry storm or account/platform fallback.
        return await self._request(action, parameters, serial=serial)

    async def stations(self):
        self.inventory_ready = False
        response = await self.read("queryPlants", {"pagesize": PAGE_SIZE})
        data = response.get("dat")
        if not isinstance(data, dict):
            raise VendorError("vendor_invalid_list")
        rows = records(data.get("plant"))
        total = data.get("total")
        if (
            (total is not None and _integer(total, "plant_total") != len(rows))
            or len(rows) > PAGE_SIZE
            or (total is None and len(rows) == PAGE_SIZE)
        ):
            # queryPlants pagination is not established by the inspected contract.
            raise VendorError("pagination_contract_incomplete")
        ids = [_identity(row.get("pid"), "plant_id") for row in rows]
        if len(set(ids)) != len(ids):
            raise VendorError("duplicate_station_identity")
        self.plants = set(ids)
        # Clear stale collector routes before rediscovery; latest requires fresh binding.
        self.routes.clear()
        self.serial_plants.clear()
        return [
            {"id": row["pid"], "name": str(row.get("name") or row.get("pname") or row["pid"])} for row in rows
        ]

    async def _collectors(self, pid):
        result, seen, expected = [], set(), None
        for page in range(MAX_COLLECTORS // PAGE_SIZE):
            response = await self.read(
                "webQueryCollectorsEs", {"pid": pid, "page": page, "pagesize": PAGE_SIZE}
            )
            data = response.get("dat")
            if not isinstance(data, dict):
                raise VendorError("vendor_invalid_list")
            rows = records(data.get("collector"))
            total = data.get("total")
            if total is not None:
                total = _integer(total, "collector_total")
                if total > MAX_COLLECTORS or (expected is not None and expected != total):
                    raise VendorError("pagination_contract_incomplete")
                expected = total
            if len(rows) > PAGE_SIZE:
                raise VendorError("pagination_contract_incomplete")
            for row in rows:
                pn = _identity(row.get("pn"), "collector_id")
                if pn in seen or (row.get("pid") is not None and str(row["pid"]) != str(pid)):
                    raise VendorError("collector_scope_or_pagination_mismatch")
                seen.add(pn)
                result.append(row)
            if expected is not None and len(result) == expected:
                return result
            if expected is not None and (len(result) > expected or not rows):
                raise VendorError("pagination_contract_incomplete")
            if expected is None and len(rows) < PAGE_SIZE:
                return result
        raise VendorError("pagination_contract_incomplete")

    async def devices(self, station_id):
        pid = _identity(station_id, "plant_id")
        if pid not in self.plants:
            raise VendorError("station_discovery_required")
        staged, result = {}, []
        for collector in await self._collectors(station_id):
            pn = _identity(collector["pn"], "collector_id")
            response = await self.read("queryCollectorDevices", {"pn": pn})
            data = response.get("dat")
            if not isinstance(data, dict):
                raise VendorError("vendor_invalid_list")
            rows = records(data.get("dev"))
            if len(rows) > 1000 or len(result) + len(rows) > 10000:
                raise VendorError("device_inventory_limit_exceeded")
            for row in rows:
                sn = _identity(row.get("sn"), "device_serial")
                code = _integer(row.get("devcode"), "device_code")
                address = _integer(row.get("devaddr"), "device_address")
                route = {"pn": pn, "devcode": code, "devaddr": address, "sn": sn}
                if (
                    sn in staged
                    or (sn in self.serial_plants and self.serial_plants[sn] != pid)
                    or (sn in self.routes and self.routes[sn] != route)
                ):
                    raise VendorError("ambiguous_device_collector_binding")
                if row.get("pn") is not None and str(row["pn"]) != pn:
                    raise VendorError("device_collector_response_mismatch")
                staged[sn] = route
                result.append(
                    {
                        "deviceSn": sn,
                        "deviceType": "UNKNOWN",
                        "model": row.get("model"),
                        "productId": code,
                        "connectStatus": None,
                        "collectionTime": None,
                        "native": {"collector": collector, "device": row, "route": route},
                    }
                )
        for sn in [sn for sn, plant in self.serial_plants.items() if plant == pid]:
            self.routes.pop(sn, None)
            self.serial_plants.pop(sn, None)
        self.routes.update(staged)
        self.serial_plants.update({sn: pid for sn in staged})
        return result

    async def latest(self, serials):
        if len(serials) > self.per_poll or len(set(serials)) != len(serials):
            raise VendorError("invalid_device_batch")
        if any(sn not in self.routes for sn in serials):
            raise VendorError("device_discovery_required")
        result = []
        for sn in serials:
            route = dict(self.routes[sn])
            response = await self.read("queryDeviceLastData", {**route, "i18n": "en"}, serial=sn)
            points = records(response.get("dat"))
            if len(points) > 1000:
                raise VendorError("measurement_count_limit_exceeded")
            seen, normalized = set(), []
            for point in points:
                title = point.get("title")
                if not isinstance(title, str) or not title.strip() or len(title) > 500 or title in seen:
                    raise VendorError("dessmonitor_invalid_point_identity")
                seen.add(title)
                # Keys survive sorting, punctuation and Unicode without merging different titles.
                key = "point_" + hashlib.sha256(title.encode()).hexdigest()[:24]
                value = point.get("val")
                if isinstance(value, bool) or (isinstance(value, float) and not math.isfinite(value)):
                    value = None
                if value is not None and type(value) not in (str, int, float):
                    raise VendorError("vendor_invalid_measurements")
                unit = point.get("unit") if isinstance(point.get("unit"), str) else None
                normalized.append({"key": key, "title": title, "value": value, "unit": unit})
            result.append(
                {
                    "deviceSn": sn,
                    "deviceState": None,
                    "collectionTime": None,
                    "dataList": normalized,
                    "native": {"route": route, "points": points},
                    "timestamp_state": "SOURCE_TIMESTAMP_NOT_PROVIDED",
                }
            )
        return result
