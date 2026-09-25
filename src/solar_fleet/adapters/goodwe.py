"""Classic SEMS read contract; distinct from SEMS+ and official WE OpenAPI.
Reviewed against yaleman/pygoodwe@a8f636d23c9921681d9e0fb8c7e0f3e5943f37c6 (see source audit for exact pin).
Configured plant IDs are required until account-wide discovery is verified.
"""

import asyncio
import json
import time
from urllib.parse import urlsplit

from ..domain import VendorError
from .cloud import ReadCloud, compact, records

HOSTS = {
    "global": "https://www.semsportal.com",
    "eu": "https://eu.semsportal.com",
    "au": "https://au.semsportal.com",
}
READS = {"/api/v2/PowerStation/GetMonitorDetailByPowerstationId"}

GOODWE_NATIVE_POINTS = {
    # PV
    "ppv": {"metric": "pv_power", "unit": "W", "direction": "positive"},
    "vpv1": {"metric": "pv1_voltage", "unit": "V"},
    "vpv2": {"metric": "pv2_voltage", "unit": "V"},
    "vpv3": {"metric": "pv3_voltage", "unit": "V"},
    "ipv1": {"metric": "pv1_current", "unit": "A"},
    "ipv2": {"metric": "pv2_current", "unit": "A"},
    "ipv3": {"metric": "pv3_current", "unit": "A"},
    # Power
    "active_power": {"metric": "active_power", "unit": "W", "direction": "bidirectional"},
    "load_power": {"metric": "load_power", "unit": "W", "direction": "positive"},
    "grid_power": {"metric": "grid_power", "unit": "W", "direction": "bidirectional"},
    "backup_power": {"metric": "backup_power", "unit": "W", "direction": "positive"},
    # Battery
    "battery_soc": {"metric": "battery_soc", "unit": "%"},
    "battery_power": {"metric": "battery_power", "unit": "W", "direction": "bidirectional"},
    "battery_voltage": {"metric": "battery_voltage", "unit": "V"},
    "battery_current": {"metric": "battery_current", "unit": "A"},
    "battery_temperature": {"metric": "battery_temp", "unit": "°C"},
    # Energy
    "eday": {"metric": "energy_today", "unit": "kWh"},
    "etotal": {"metric": "energy_total", "unit": "kWh"},
    "export_energy_today": {"metric": "export_energy_today", "unit": "kWh"},
    "import_energy_today": {"metric": "import_energy_today", "unit": "kWh"},
    "total_export_energy": {"metric": "total_export_energy", "unit": "kWh"},
    "total_import_energy": {"metric": "total_import_energy", "unit": "kWh"},
    # Grid AC
    "grid_voltage": {"metric": "grid_voltage_r", "unit": "V"},
    "grid_frequency": {"metric": "grid_frequency", "unit": "Hz"},
    "vac_r": {"metric": "grid_voltage_r", "unit": "V"},
    "vac_s": {"metric": "grid_voltage_s", "unit": "V"},
    "vac_t": {"metric": "grid_voltage_t", "unit": "V"},
    "iac_r": {"metric": "grid_current_r", "unit": "A"},
    "iac_s": {"metric": "grid_current_s", "unit": "A"},
    "iac_t": {"metric": "grid_current_t", "unit": "A"},
    # Inverter
    "temperature": {"metric": "inverter_temp", "unit": "°C"},
    "power_factor": {"metric": "power_factor", "unit": ""},
}


class GoodWe(ReadCloud):
    evidence_ids = ["GOODWE_API_001"]
    version = "0.3.0"

    def __init__(self, integration, credentials, **kwargs):
        region = integration.get("region", "global")
        if region not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[region]
        if not credentials.get("account") or not credentials.get("password"):
            raise VendorError("credentials_incomplete")
        super().__init__(integration, credentials, **kwargs)
        self.access_token, self.expires_at = None, 0
        self.auth_lock = asyncio.Lock()
        self.device_plants = {}

    def validate_response(self, payload):
        if str(payload.get("code")) != "0":
            self.invalidate_auth()
            raise VendorError("goodwe_request_rejected")

    async def authenticate(self):
        async with self.auth_lock:
            if self.access_token and time.monotonic() < self.expires_at:
                return self.access_token
            response = await self.http(
                "/api/v2/Common/CrossLogin",
                compact({"account": self.credentials["account"], "pwd": self.credentials["password"]}),
                headers={
                    "Content-Type": "application/json",
                    "Token": '{"version":"v2.0.4","client":"ios","language":"en"}',
                },
            )
            data = response.get("data")
            if not isinstance(data, dict) or not data.get("token") or not data.get("uid"):
                raise VendorError("vendor_invalid_token")
            # A response must never redirect credentials to an arbitrary API host.
            route = response.get("api")
            if route:
                parsed = urlsplit(route)
                allowed = {urlsplit(v).hostname for v in HOSTS.values()} | {"semsportal.com"}
                if (
                    parsed.scheme != "https"
                    or parsed.hostname not in allowed
                    or parsed.port not in (None, 443)
                    or parsed.username
                    or parsed.password
                    or parsed.path.rstrip("/") != "/api"
                    or parsed.query
                    or parsed.fragment
                ):
                    raise VendorError("unrecognized_goodwe_api_route")
                self.host = "https://" + parsed.netloc
            self.access_token = json.dumps(data, separators=(",", ":"))
            # Conservative refresh; the upstream token metadata remains intact.
            self.expires_at = time.monotonic() + 1800
            return self.access_token

    async def read(self, path, body):
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        token = await self.authenticate()
        return await self.http(
            path, compact(body), headers={"Content-Type": "application/json", "Token": token}
        )

    async def stations(self):
        await self.authenticate()
        ids = [v.strip() for v in self.credentials.get("plant_ids", "").split(",") if v.strip()]
        if not ids:
            raise VendorError("goodwe_explicit_plant_ids_required")
        if len(ids) > 100 or len(ids) != len(set(ids)):
            raise VendorError("invalid_plant_scope")
        # Each configured ID is checked through the authorized station API below.
        return [{"id": id, "name": id} for id in ids]

    async def devices(self, station_id):
        response = await self.read(
            "/api/v2/PowerStation/GetMonitorDetailByPowerstationId", {"powerStationId": station_id}
        )
        result = []
        for row in records(response.get("data", {}).get("inverter")):
            sn = row.get("sn")
            if not isinstance(sn, str) or not sn:
                raise VendorError("vendor_device_identity_invalid")
            self.device_plants[sn] = station_id
            result.append(
                {
                    "deviceSn": sn,
                    "deviceType": "INVERTER",
                    "model": row.get("model_type"),
                    "connectStatus": None,
                    "collectionTime": None,
                    "native": row,
                }
            )
        return result

    async def latest(self, serials):
        result, cache = [], {}
        for sn in serials:
            plant = self.device_plants.get(sn)
            if plant is None:
                raise VendorError("device_discovery_required")
            if plant not in cache:
                response = await self.read(
                    "/api/v2/PowerStation/GetMonitorDetailByPowerstationId", {"powerStationId": plant}
                )
                cache[plant] = records(response.get("data", {}).get("inverter"))
            row = next((r for r in cache[plant] if r.get("sn") == sn), None)
            if row is None or not isinstance(row.get("invert_full"), dict):
                raise VendorError("latest_response_device_mismatch")
            result.append(
                {
                    "deviceSn": sn,
                    "deviceState": 1,
                    "collectionTime": None,
                    "dataList": self.decode_native_points(row["invert_full"]),
                    "native": row,
                    "timestamp_state": "DEVICE_TIMEZONE_REQUIRED",
                }
            )
        return result

    @staticmethod
    def decode_native_points(data):
        return [
            {"key": k, "value": v, "unit": GOODWE_NATIVE_POINTS.get(k, {}).get("unit")}
            for k, v in data.items()
            if type(v) in (str, int, float)
        ]
