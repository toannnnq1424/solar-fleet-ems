"""Experimental SEMS+ read transport, composed by the existing GoodWe plugin.

Protocol references and MIT attribution: THIRD_PARTY_NOTICES.md. No browser
session reuse, regional fallback, physical writes or automatic profile promotion.
"""

import asyncio
import base64
import hashlib
import math
import time
from datetime import datetime
from urllib.parse import quote, urlsplit

from ..domain import VendorError
from ..integration import DeviceEnergyReport, DeviceReport, ReportedEnergy, StationReport
from .cloud import ReadCloud, compact, records

REGIONS = ("hk", "eu", "au", "us", "cn")
PREFIX = "/web/sems"
LOGIN = PREFIX + "/sems-user/api/v1/auth/cross-login"
STATIONS = PREFIX + "/sems-plant/api/stations/simple-query"
DEVICES = PREFIX + "/sems-plant/api/stations/device/all-status"
EQUIPMENT = PREFIX + "/sems-plant/api/equipments/"
FLOW = PREFIX + "/sems-plant/api/stations/flow"
STATISTICS = PREFIX + "/sems-plant/api/stations/statistics"
ENERGY_ITEMS = {"proSystemTotalStats": "generation_kwh", "proConsumStats": "consumption_kwh",
                "proPurchaseStats": "import_kwh", "proGridStats": "export_kwh"}


def reported_number(value, *, nonnegative=False):
    if isinstance(value, bool) or not isinstance(value, (int, float, str)):
        return None
    try:
        number = float(value)
    except (ValueError, OverflowError):
        return None
    return number if math.isfinite(number) and (not nonnegative or number >= 0) else None


def energy_rows(data, start, end):
    """Keep the API's dated/unit-bearing series; do not sum overlapping devices."""
    if not isinstance(data, dict):
        raise VendorError("vendor_invalid_statistics")
    dated, seen = {}, set()
    for item in records(data.get("dataList")):
        key = item.get("item")
        if key not in ENERGY_ITEMS:
            continue
        if key in seen or item.get("unit") != "kWh":
            raise VendorError("vendor_invalid_statistics")
        seen.add(key)
        dates = set()
        for row in records(item.get("statisticsList")):
            day = row.get("date")
            try:
                valid = isinstance(day, str) and datetime.strptime(day, "%Y-%m-%d").date().isoformat() == day
            except ValueError:
                valid = False
            if not valid or not start <= day <= end or day in dates:
                raise VendorError("vendor_invalid_statistics")
            dates.add(day)
            dated.setdefault(day, {})[ENERGY_ITEMS[key]] = reported_number(row.get("val"), nonnegative=True)
    return [ReportedEnergy(start_date=day, end_date=day, **values) for day, values in sorted(dated.items())]


def period_energy(data, start, end, dimension):
    """Read one explicitly dated bucket, never a sum of partial daily series.

    hk observations: dimension=month returns YYYY-MM, year returns YYYY.
    Flat summaries may be omitted depending on requested items, and can differ
    from the unit-bearing series. Use the requested series consistently.
    """
    if not isinstance(data, dict):
        raise VendorError("vendor_invalid_statistics")
    bucket = end[:{"day": 10, "month": 7, "year": 4}[dimension]]
    values, seen = {}, set()
    for item in records(data.get("dataList")):
        key = item.get("item")
        if key not in ENERGY_ITEMS:
            continue
        if key in seen or item.get("unit") != "kWh":
            raise VendorError("vendor_invalid_statistics")
        seen.add(key)
        rows = records(item.get("statisticsList"))
        if len(rows) > 1 or (rows and rows[0].get("date") != bucket):
            raise VendorError("vendor_invalid_statistics")
        values[ENERGY_ITEMS[key]] = reported_number(rows[0].get("val"), nonnegative=True) if rows else None
    return ReportedEnergy(start_date=start, end_date=end, **values)


def device_report(serial, telemetry, counters, *, counters_available):
    """Exact field + unit + unique occurrence. Display evidence, not commissioning."""
    def number(points, code, units, nonnegative=False):
        matches = [p for p in points if p['key'].rsplit(':', 1)[-1] == code]
        if len(matches) != 1 or matches[0].get('unit') not in units:
            return None
        return reported_number(matches[0].get('value'), nonnegative=nonnegative)
    rated = number(counters, 'ratedPower', ('kW',), True)
    report = DeviceReport(
        serial=serial, ac_kw=number(telemetry, 'pAc', ('kW',)),
        pv_dc_kw=number(telemetry, 'pDc', ('kW',), True),
        rated_kw=rated if rated is not None and rated > 0 else None,
        temperature_c=number(telemetry, 'Temperature', ('℃', '°C')),
        counters_available=counters_available, evidence_ids=['GOODWE_SEMSPLUS_STATION_001'],
    )
    for period, suffix in (('today', 'Today'), ('week', 'Week'), ('month', 'Month'), ('year', 'Year'), ('total', 'Total')):
        values = {key: number(counters, native + suffix, ('kWh',), True) for key, native in (
            ('generation_kwh', 'proPvStats'), ('charge_kwh', 'proCharStats'), ('discharge_kwh', 'proDischarStats'))}
        if any(value is not None for value in values.values()):
            report.periods[period] = DeviceEnergyReport(**values)
    return report


def identifier(value):
    if not isinstance(value, str) or not value.strip() or len(value) > 200:
        raise VendorError("vendor_identity_invalid")
    return value


class GoodWePlus(ReadCloud):
    version = "0.4.0"
    evidence_ids = ["GOODWE_SEMSPLUS_COMMUNITY_001"]
    per_poll = 5

    def __init__(self, integration, credentials, **kwargs):
        region = integration.get("region")
        if region not in REGIONS:
            raise VendorError("unsupported_data_center")
        if credentials.get("vendor_terms_accepted") is not True:
            raise VendorError("goodwe_terms_confirmation_required")
        if not credentials.get("account") or not credentials.get("password"):
            raise VendorError("credentials_incomplete")
        self.region = region
        self.login_host = f"https://{region}-semsplus.goodwe.com"
        self.gateway = f"https://{region}-gateway.semsportal.com"
        self.host = self.login_host
        super().__init__(integration, credentials, **kwargs)
        self.access_token = None
        self.expires_at = 0
        self.auth_lock = asyncio.Lock()
        self.io_lock = asyncio.Lock()
        self.plant_ids = set()
        self.device_routes = {}
        self.inventory_ready = False

    def validate_response(self, payload):
        code = str(payload.get("code"))
        if code == "GY0429":
            self.cooldown_until = time.monotonic() + 300
            raise VendorError("vendor_rate_limited")
        if code not in ("0", "00000"):
            # Unknown business errors are not evidence of token expiry. Do not
            # repeatedly log in or switch regions on an ambiguous error.
            raise VendorError("goodwe_plus_request_rejected")

    def headers(self, session=None):
        session = session or {}
        uid, token = session.get("uid", ""), session.get("token", "")
        stamp = str(int(time.time() * 1000))
        digest = hashlib.sha256(f"{stamp}@{uid}@{token}".encode()).hexdigest()
        signature = base64.b64encode(f"{digest}@{stamp}".encode()).decode()
        return {
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Origin": self.login_host,
            "Referer": self.login_host + "/",
            "token": compact({
                "uid": uid, "token": token, "timestamp": session.get("timestamp", 0),
                "client": "semsPlusWeb", "version": "", "language": "en",
                **({"api": self.gateway + PREFIX, "region": self.region} if session else {}),
            }).decode(),
            "x-signature": signature,
        }

    async def authenticate(self):
        async with self.auth_lock:
            if self.access_token and time.monotonic() < self.expires_at:
                return self.access_token
            password = hashlib.md5(self.credentials["password"].encode(), usedforsecurity=False).hexdigest()
            async with self.io_lock:
                self.host = self.login_host
                response = await self.http(LOGIN, compact({
                    "account": self.credentials["account"],
                    "pwd": base64.b64encode(password.encode()).decode(),
                    "agreement": 1,  # Only after explicit user confirmation in the connection form.
                    "isChinese": self.region == "cn", "isLocal": False,
                }), headers=self.headers())
            data = response.get("data")
            if not isinstance(data, dict) or any(
                not isinstance(data.get(k), str) or not data[k] for k in ("uid", "token")
            ):
                raise VendorError("vendor_invalid_token")
            route = response.get("api") or data.get("api")
            if route is not None:
                try:
                    parsed = urlsplit(route)
                    valid = (
                        parsed.scheme == "https"
                        and parsed.hostname == urlsplit(self.gateway).hostname
                        and parsed.port in (None, 443)
                        and not parsed.username and not parsed.password
                        and parsed.path.rstrip("/") in ("/sems", PREFIX)
                        and not parsed.query and not parsed.fragment
                    )
                except (TypeError, ValueError):
                    valid = False
                if not valid:
                    raise VendorError("unrecognized_goodwe_api_route")
            self.access_token = {k: data[k] for k in ("uid", "token", "timestamp") if k in data}
            self.expires_at = time.monotonic() + 1800  # local conservative refresh, not vendor TTL
            return self.access_token

    async def read(self, path, *, body=None, params=None):
        # No arbitrary endpoint/URL escape hatch, even for a future caller.
        if path in (FLOW, STATISTICS):
            scope = (body or params or {}).get("stationId")
            if scope not in self.plant_ids:
                raise VendorError("station_discovery_required")
        if path not in (STATIONS, DEVICES, FLOW, STATISTICS) and not any(
            path == EQUIPMENT + quote(sn, safe="") + "/" + suffix
            for sn in self.device_routes for suffix in ("telemetry", "telecounting", "relatedDevices")
        ):
            raise VendorError("read_endpoint_not_allowed")
        token = await self.authenticate()
        async with self.io_lock:
            self.host = self.gateway
            response = await self.http(
                path, compact(body) if body is not None else None,
                params=params, method="POST" if body is not None else "GET", headers=self.headers(token),
            )
        # The authorized hk trial observed code=00000 with data OMITTED on
        # logger/battery-bank telemetry. Scope that exception to the discovered
        # kind and endpoint; missing station/inverter data remains malformed.
        empty_telemetry = any(
            kind in ("DATA_LOGGER", "BATTERY_BANK")
            and path == EQUIPMENT + quote(sn, safe="") + "/telemetry"
            for sn, (_, kind) in self.device_routes.items()
        )
        if "data" not in response and not empty_telemetry:
            raise VendorError("vendor_invalid_list")
        return response.get("data")

    async def station_report(self, station_id):
        """Station aggregates, separate from exact-profile device telemetry.

        Protocol research: TimSoethout/goodwe-sems-home-assistant@72c06c72,
        MIT; local hk read observation 2026-10-08. No inferred pAc -> PV,
        implicit timezone, topology summation, profit/billing or hardware writes.
        """
        flow = await self.read(FLOW, params={"stationId": station_id})
        if not isinstance(flow, dict) or flow.get("id", station_id) != station_id:
            raise VendorError("vendor_invalid_station_flow")
        power = {}
        for native, key, scale in (("pSystem", "pv_w", 1000), ("pConsum", "load_w", 1000),
                                   ("pBat", "battery_w", -1000), ("pGrid", "grid_w", -1000),
                                   ("soc", "battery_soc", 1)):
            val = reported_number(flow.get(native), nonnegative=key in ("pv_w", "load_w", "battery_soc"))
            if val is not None and (key != "battery_soc" or val <= 100) and math.isfinite(val * scale):
                power[key] = val * scale
        stamp = flow.get("refreshTime")
        try:
            clock = datetime.fromisoformat(stamp) if isinstance(stamp, str) else None
        except ValueError:
            clock = None
        report = StationReport(station_id=station_id, source_clock=stamp if clock else None,
                               power=power, evidence_ids=["GOODWE_SEMSPLUS_STATION_001"])
        if clock is None:
            return report
        end = clock.date().isoformat()
        for period, dimension, start in (("today", "day", end), ("month", "month", end[:8] + "01"),
                                         ("year", "year", end[:5] + "01-01")):
            try:
                data = await self.read(STATISTICS, body={
                    "stationId": station_id, "isReport": False, "items": list(ENERGY_ITEMS),
                    "dimension": dimension, "startTime": start + " 00:00:00", "endTime": end + " 23:59:59",
                })
                report.periods[period] = period_energy(data, start, end, dimension)
            except VendorError as exc:
                if str(exc) not in ("vendor_invalid_statistics", "goodwe_plus_request_rejected"):
                    raise  # quota/auth/network failures must stop further requests
                report.unavailable_periods.append(period)
        try:
            start = end[:8] + "01"
            daily = await self.read(STATISTICS, body={
                "stationId": station_id, "isReport": False, "items": list(ENERGY_ITEMS),
                "dimension": "day", "startTime": start + " 00:00:00", "endTime": end + " 23:59:59",
            })
            report.daily_energy = energy_rows(daily, start, end)
        except VendorError as exc:
            if str(exc) not in ("vendor_invalid_statistics", "goodwe_plus_request_rejected"):
                raise
        return report

    async def stations(self):
        self.inventory_ready = False
        self.plant_ids = set()
        self.device_routes = {}
        result, seen = [], set()
        for page in range(1, 21):
            data = await self.read(STATIONS, body={"pageIndex": page, "pageSize": 50})
            if not isinstance(data, dict):
                raise VendorError("vendor_invalid_list")
            rows = records(data.get("dataList"))
            if len(rows) > 50:
                raise VendorError("vendor_invalid_pagination")
            for row in rows:
                id = identifier(row.get("id"))
                if id in seen:
                    raise VendorError("vendor_duplicate_station")
                seen.add(id)
                result.append({"id": id, "name": row.get("stationName") or row.get("name") or id})
            if len(rows) < 50:
                self.plant_ids = seen
                return result
        raise VendorError("vendor_inventory_limit_exceeded")

    async def devices(self, station_id):
        if station_id not in self.plant_ids:
            raise VendorError("station_discovery_required")
        # Build a complete temporary inventory; never retain a half-discovered tree.
        routes = {k: v for k, v in self.device_routes.items() if v[0] != station_id}
        data = await self.read(DEVICES, params={"stationId": station_id})
        if not isinstance(data, dict):
            raise VendorError("vendor_invalid_list")
        result, seen = [], set()
        for group in records(data.get("deviceDetailList")):
            kind = identifier(group.get("deviceType"))
            for status in records(group.get("statusDetailList")):
                detail = status.get("detailMap")
                if not isinstance(detail, dict):
                    raise VendorError("vendor_invalid_list")
                for serial, row in detail.items():
                    identifier(serial)
                    if not isinstance(row, dict) or row.get("sn", serial) != serial:
                        raise VendorError("vendor_device_identity_invalid")
                    if serial in seen or serial in routes:
                        raise VendorError("ambiguous_device_site_binding")
                    seen.add(serial)
                    if len(seen) > 200:
                        raise VendorError("vendor_inventory_limit_exceeded")
                    routes[serial] = (station_id, kind)
                    result.append({
                        "deviceSn": serial, "deviceType": kind, "model": row.get("model"),
                        "connectStatus": None, "collectionTime": None, "native": row,
                    })
        previous_routes = self.device_routes
        self.device_routes = routes
        try:
            # Related batteries may not be present in the station inventory.
            # Read only the explicit relationship returned for discovered inverters.
            for inverter in list(result):
                if inverter["deviceType"] != "INVERTER":
                    continue
                parent = inverter["deviceSn"]
                related = await self.read(
                    EQUIPMENT + quote(parent, safe="") + "/relatedDevices",
                    params={"sn": parent, "deviceType": "INVERTER", "pwId": station_id},
                )
                for child in records(related):
                    serial, kind = identifier(child.get("sn")), identifier(child.get("type"))
                    if serial in routes:
                        if routes[serial] != (station_id, kind):
                            raise VendorError("ambiguous_device_site_binding")
                        continue
                    if len(result) >= 200:
                        raise VendorError("vendor_inventory_limit_exceeded")
                    routes[serial] = (station_id, kind)
                    result.append({"deviceSn": serial, "deviceType": kind, "model": None,
                                   "connectStatus": None, "collectionTime": None,
                                   "parentDeviceSn": parent, "native": child})
        except BaseException:
            self.device_routes = previous_routes
            raise
        return result

    @staticmethod
    def points(groups, channel):
        result, seen = [], set()
        for group in records(groups):
            group_id = identifier(group.get("code"))
            for factor in records(group.get("factors")):
                code = identifier(factor.get("code"))
                key = channel + ":" + group_id + ":" + code
                if key in seen:
                    raise VendorError("vendor_duplicate_point")
                seen.add(key)
                value, unit = factor.get("data"), factor.get("unit")
                if value is not None and type(value) not in (str, int, float):
                    raise VendorError("vendor_invalid_measurements")
                point = {"key": key, "value": value, "unit": unit if isinstance(unit, str) else None}
                # Display metadata only; aliases never define canonical semantics.
                for name, label in (("title", factor.get("alias")), ("group", group.get("alias"))):
                    if isinstance(label, str) and label.strip():
                        point[name] = label[:200]
                point["group_id"] = group_id
                result.append(point)
        return result

    async def latest(self, serials):
        result = []
        for serial in serials:
            if serial not in self.device_routes:
                raise VendorError("device_discovery_required")
            plant, kind = self.device_routes[serial]
            params = {"deviceType": kind, "pwId": plant}
            data = await self.read(EQUIPMENT + quote(serial, safe="") + "/telemetry", params=params)
            points = [] if data is None else self.points(data, "telemetry")
            reported, counting = None, None
            if kind == 'INVERTER':
                try:
                    counting = await self.read(EQUIPMENT + quote(serial, safe="") + '/telecounting', params=params)
                    counter_points = self.points(counting, 'telecounting')
                except VendorError as exc:
                    if str(exc) not in ('goodwe_plus_request_rejected', 'vendor_invalid_list'):
                        raise
                    counter_points = []
                reported = device_report(serial, points, counter_points, counters_available=counting is not None)
            # Preserve units/factors; no kW -> W or signed-power inference without
            # an accepted profile. Response arrival is NOT the observation time.
            result.append({
                "deviceSn": serial, "deviceState": None, "collectionTime": None,
                "dataList": points,
                "reported": reported.model_dump(mode='json') if reported else None,
                "native_telecounting": counting,
                "reading_state": "NO_VENDOR_TELEMETRY" if data is None else "NATIVE_RESPONSE",
                "timestamp_state": "SOURCE_TIME_UNVERIFIED", "native": data,
            })
        return result
