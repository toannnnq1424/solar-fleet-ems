"""Growatt OpenAPI v1 read subset. SPH/MIX and MIN/TLX have distinct form endpoints.
Contract source: indykoning/PyPi_GrowattServer@6469d881462eaa4a3b3c6e3cfa6f17082e86eaf5.
This is not the Shine web-session API. Unsupported families remain explicit errors.
"""

from urllib.parse import urlencode

from ..domain import VendorError
from .cloud import ReadCloud, records

HOSTS = {"global": "https://openapi.growatt.com", "server": "https://server.growatt.com"}
LATEST = {5: ("/v1/device/mix/mix_last_data", "mix_sn"), 7: ("/v1/device/tlx/tlx_last_data", "tlx_sn")}
READS = {"/v1/plant/list", "/v1/plant/details", "/v1/device/list", *(v[0] for v in LATEST.values())}

GROWATT_NATIVE_POINTS = {
    # Inverter AC output
    "pac": {"metric": "active_power", "unit": "W", "scale": 1.0},
    "ppv": {"metric": "pv_power", "unit": "W", "scale": 1.0},
    # PV string voltages/currents
    "vpv1": {"metric": "pv1_voltage", "unit": "V", "scale": 1.0},
    "vpv2": {"metric": "pv2_voltage", "unit": "V", "scale": 1.0},
    "vpv3": {"metric": "pv3_voltage", "unit": "V", "scale": 1.0},
    "ipv1": {"metric": "pv1_current", "unit": "A", "scale": 1.0},
    "ipv2": {"metric": "pv2_current", "unit": "A", "scale": 1.0},
    "ipv3": {"metric": "pv3_current", "unit": "A", "scale": 1.0},
    # Energy accumulators
    "eac_today": {"metric": "energy_today", "unit": "kWh", "scale": 1.0},
    "eac_total": {"metric": "energy_total", "unit": "kWh", "scale": 1.0},
    # Battery
    "soc": {"metric": "battery_soc", "unit": "%", "scale": 1.0},
    "pcharge": {"metric": "battery_charge_power", "unit": "W", "scale": 1.0},
    "pdischarge": {"metric": "battery_discharge_power", "unit": "W", "scale": 1.0},
    "batteryVoltage": {"metric": "battery_voltage", "unit": "V", "scale": 1.0},
    "batteryCurrent": {"metric": "battery_current", "unit": "A", "scale": 1.0},
    "batteryTemperature": {"metric": "battery_temp", "unit": "°C", "scale": 1.0},
    # Load and grid
    "pLocalLoad": {"metric": "load_power", "unit": "W", "scale": 1.0},
    "gridPower": {"metric": "grid_power", "unit": "W", "scale": 1.0},
    "pToGrid": {"metric": "grid_export_power", "unit": "W", "scale": 1.0},
    "pFromGrid": {"metric": "grid_import_power", "unit": "W", "scale": 1.0},
    # Grid AC measurements
    "vac1": {"metric": "grid_voltage_r", "unit": "V", "scale": 1.0},
    "vac2": {"metric": "grid_voltage_s", "unit": "V", "scale": 1.0},
    "vac3": {"metric": "grid_voltage_t", "unit": "V", "scale": 1.0},
    "iac1": {"metric": "grid_current_r", "unit": "A", "scale": 1.0},
    "iac2": {"metric": "grid_current_s", "unit": "A", "scale": 1.0},
    "iac3": {"metric": "grid_current_t", "unit": "A", "scale": 1.0},
    "frequency": {"metric": "grid_frequency", "unit": "Hz", "scale": 1.0},
    # Energy import/export
    "totalExportEnergy": {"metric": "total_export_energy", "unit": "kWh", "scale": 1.0},
    "totalImportEnergy": {"metric": "total_import_energy", "unit": "kWh", "scale": 1.0},
    "todayExportEnergy": {"metric": "export_energy_today", "unit": "kWh", "scale": 1.0},
    "todayImportEnergy": {"metric": "import_energy_today", "unit": "kWh", "scale": 1.0},
    # Inverter status
    "temperature": {"metric": "inverter_temp", "unit": "°C", "scale": 1.0},
    "status": {"metric": "inverter_status", "unit": "", "scale": 1.0},
}


class Growatt(ReadCloud):
    evidence_ids = ["GROWATT_OSS_001"]
    version = "0.3.0"

    def __init__(self, integration, credentials, **kwargs):
        region = integration.get("region", "global")
        if region not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[region]
        if not credentials.get("token"):
            raise VendorError("credentials_incomplete")
        super().__init__(integration, credentials, **kwargs)
        self.device_types = {}

    def validate_response(self, payload):
        if type(payload.get("error_code")) is not int or payload["error_code"] != 0:
            raise VendorError("growatt_request_rejected")

    async def authenticate(self):
        return self.credentials["token"]

    async def read(self, path, body):
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        headers = {"token": self.credentials["token"]}
        if path in {v[0] for v in LATEST.values()}:
            headers["Content-Type"] = "application/x-www-form-urlencoded"
            result = await self.http(path, urlencode(body).encode(), headers=headers)
        else:
            result = await self.http(path, headers=headers, params=body, method="GET")
        return result["data"]

    async def listing(self, path, body, key):
        rows = []
        seen = set()
        for page in range(1, 501):
            data = await self.read(path, {**body, "page": page, "perpage": 100})
            part = records(data.get(key))
            count = data.get("count")
            if type(count) is not int or count < len(rows) + len(part):
                raise VendorError("vendor_invalid_pagination")
            for row in part:
                id = str(row.get("plant_id") if key == "plants" else row.get("device_sn"))
                if id in seen or id == "None":
                    raise VendorError("vendor_repeated_or_missing_identity")
                seen.add(id)
                rows.append(row)
            if len(rows) == count:
                return rows
            if not part:
                break
        raise VendorError("vendor_discovery_incomplete")

    async def stations(self):
        return [
            {"id": r.get("plant_id"), "name": r.get("name"), "native": r}
            for r in await self.listing("/v1/plant/list", {}, "plants")
        ]

    async def devices(self, station_id):
        result = []
        for r in await self.listing("/v1/device/list", {"plant_id": station_id}, "devices"):
            sn = r["device_sn"]
            self.device_types[sn] = r.get("type")
            result.append(
                {
                    "deviceSn": sn,
                    "deviceType": str(r.get("type")),
                    "model": r.get("model"),
                    "connectStatus": 0 if r.get("lost") else 1,
                    "collectionTime": None,
                    "native": r,
                }
            )
        return result

    async def latest(self, serials):
        result = []
        for sn in serials:
            route = LATEST.get(self.device_types.get(sn))
            if not route:
                raise VendorError("growatt_device_family_contract_required")
            data = await self.read(route[0], {route[1]: sn})
            if not isinstance(data, dict):
                raise VendorError("vendor_invalid_measurements")
            # The textual device clock is not UTC. Preserve it without inventing freshness.
            result.append(
                {
                    "deviceSn": sn,
                    "deviceState": 1,
                    "collectionTime": None,
                    "dataList": self.decode_native_points(data),
                    "native": data,
                    "timestamp_state": "DEVICE_TIMEZONE_REQUIRED",
                }
            )
        return result

    @staticmethod
    def decode_native_points(data):
        return [
            {"key": k, "value": v, "unit": GROWATT_NATIVE_POINTS.get(k, {}).get("unit")}
            for k, v in data.items()
            if type(v) in (str, int, float)
        ]
