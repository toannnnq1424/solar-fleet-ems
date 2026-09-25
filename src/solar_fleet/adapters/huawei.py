"""Huawei Northbound read contracts. HUAWEI_AUTH_001 and HUAWEI_CLIENT_AUDIT_001.

Cloud engineering values are distinct from raw SUN2000 Modbus registers.
Contract tests do not establish hardware/model acceptance or control support.
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from ..domain import VendorError
from .cloud import ReadCloud, compact, records

HOSTS = {
    "global": "https://intl.fusionsolar.huawei.com",
    "eu": "https://eu5.fusionsolar.huawei.com",
    "cn": "https://cn.fusionsolar.huawei.com",
}

# Deliberately explicit: mutations elsewhere are NOT accidentally exposed as reads.
READS = {
    "/thirdData/login",
    "/thirdData/getStationList",
    "/thirdData/getDevList",
    "/thirdData/getDevRealKpi",
    "/thirdData/getKpiStationDay",
    "/thirdData/getKpiStationMonth",
    "/thirdData/getKpiStationYear",
    "/thirdData/getAlarmList",
    "/thirdData/getDevFiveMinutes",
    "/thirdData/getStationRealKpi",
    "/thirdData/getDevDetail",
}

# Huawei SUN2000 native KPI points — native field catalogue; canonical mappings require reviewed evidence
HUAWEI_NATIVE_POINTS = {
    # Power
    "active_power": {"metric": "active_power", "unit": "kW"},
    "reactive_power": {"metric": "reactive_power", "unit": "kvar"},
    "mppt_power": {"metric": "pv_power", "unit": "kW"},
    # Energy
    "day_cap": {"metric": "energy_today", "unit": "kWh"},
    "total_cap": {"metric": "energy_total", "unit": "kWh"},
    "day_feed_in_energy": {"metric": "export_energy_today", "unit": "kWh"},
    "total_feed_in_energy": {"metric": "total_export_energy", "unit": "kWh"},
    "day_grid_energy": {"metric": "import_energy_today", "unit": "kWh"},
    "total_grid_energy": {"metric": "total_import_energy", "unit": "kWh"},
    # Inverter
    "power_factor": {"metric": "power_factor", "unit": ""},
    "efficiency": {"metric": "efficiency", "unit": "%"},
    "temperature": {"metric": "inverter_temp", "unit": "°C"},
    "inverter_state": {"metric": "inverter_state", "unit": ""},
    # Battery
    "battery_soc": {"metric": "battery_soc", "unit": "%"},
    "battery_charge_discharge_power": {"metric": "battery_power", "unit": "kW"},
    "battery_voltage": {"metric": "battery_voltage", "unit": "V"},
    "battery_current": {"metric": "battery_current", "unit": "A"},
    "battery_temperature": {"metric": "battery_temp", "unit": "°C"},
    "ch_discharge_model": {"metric": "battery_mode", "unit": ""},
    # Grid AC phase measurements
    "a_u": {"metric": "grid_voltage_r", "unit": "V"},
    "b_u": {"metric": "grid_voltage_s", "unit": "V"},
    "c_u": {"metric": "grid_voltage_t", "unit": "V"},
    "a_i": {"metric": "grid_current_r", "unit": "A"},
    "b_i": {"metric": "grid_current_s", "unit": "A"},
    "c_i": {"metric": "grid_current_t", "unit": "A"},
    "grid_frequency": {"metric": "grid_frequency", "unit": "Hz"},
    # PV strings (MPPT)
    "pv1_u": {"metric": "pv1_voltage", "unit": "V"},
    "pv1_i": {"metric": "pv1_current", "unit": "A"},
    "pv2_u": {"metric": "pv2_voltage", "unit": "V"},
    "pv2_i": {"metric": "pv2_current", "unit": "A"},
    "pv3_u": {"metric": "pv3_voltage", "unit": "V"},
    "pv3_i": {"metric": "pv3_current", "unit": "A"},
    "pv4_u": {"metric": "pv4_voltage", "unit": "V"},
    "pv4_i": {"metric": "pv4_current", "unit": "A"},
    # Load
    "meter_power": {"metric": "meter_power", "unit": "kW"},
}


class Huawei(ReadCloud):
    """Huawei FusionSolar Northbound API adapter with tested discovery/latest contracts."""

    evidence_ids = ["HUAWEI_AUTH_001", "HUAWEI_NB_001"]
    version = "0.2.0"

    def __init__(self, integration, credentials, **kwargs):
        region = integration.get("region", "global")
        if region not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[region]
        if any(not credentials.get(k) for k in ("user_name", "system_code")):
            raise VendorError("credentials_incomplete")
        super().__init__(integration, credentials, **kwargs)
        self.xsrf_token, self.expires_at = None, 0.0
        self.auth_lock = asyncio.Lock()
        self.device_types = {}

    def validate_response(self, payload):
        code = str(payload.get("failCode", "0"))
        if code == "407":
            self.cooldown_until = time.monotonic() + 600
            raise VendorError("vendor_rate_limited")
        if code in {"305", "306", "307", "401"}:
            self.invalidate_auth()
            raise VendorError("vendor_auth_or_permission_denied")
        super().validate_response(payload)

    async def authenticate(self) -> str:
        async with self.auth_lock:
            if self.xsrf_token and time.monotonic() < self.expires_at:
                return self.xsrf_token
            c = self.credentials
            body = {
                "userName": c["user_name"],
                "systemCode": c["system_code"],
            }
            await self.http(
                "/thirdData/login",
                compact(body),
                headers={"Content-Type": "application/json"},
            )
            token = self.response_headers.get("XSRF-TOKEN")
            if not token:
                raise VendorError("vendor_invalid_token")
            self.xsrf_token = token
            # Huawei tokens typically expire in 30 minutes
            self.expires_at = time.monotonic() + 1800 - 60
            return token

    async def read(self, path: str, body: dict[str, Any]) -> dict[str, Any]:
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        token = await self.authenticate()
        headers = {
            "Content-Type": "application/json",
            "XSRF-TOKEN": token,
        }
        return await self.http(path, compact(body), headers=headers)

    async def stations(self) -> list[dict[str, Any]]:
        payload = await self.read("/thirdData/getStationList", {})
        rows = records(payload.get("data"))
        return [{"id": r.get("stationCode"), "name": r.get("stationName"), "native": r} for r in rows]

    async def station_real_kpi(self, station_codes: str) -> dict[str, Any]:
        """Get real-time KPI for a station."""
        payload = await self.read("/thirdData/getStationRealKpi", {"stationCodes": station_codes})
        return payload.get("data", [])

    async def devices(self, station_id: str) -> list[dict[str, Any]]:
        payload = await self.read("/thirdData/getDevList", {"stationCodes": station_id})
        result = []
        for row in records(payload.get("data")):
            id, kind = row.get("id"), row.get("devTypeId")
            if type(id) not in (int, str) or type(kind) is not int:
                raise VendorError("vendor_device_identity_invalid")
            serial = str(id)
            self.device_types[serial] = kind
            result.append(
                {
                    "deviceSn": serial,
                    "deviceType": str(kind),
                    "model": row.get("model"),
                    "connectStatus": None,
                    "collectionTime": None,
                    "native": row,
                }
            )
        return result

    async def device_detail(self, dev_id: str, dev_type_id: int = 1) -> dict[str, Any]:
        """Get device detail information."""
        payload = await self.read("/thirdData/getDevDetail", {"devIds": dev_id, "devTypeId": dev_type_id})
        data = payload.get("data", [])
        return data[0] if data and isinstance(data, list) else {}

    async def latest(self, serials: list[str]) -> list[dict[str, Any]]:
        result = []
        for dev_id in serials:
            if dev_id not in self.device_types:
                raise VendorError("device_type_discovery_required")
            row = await self.read(
                "/thirdData/getDevRealKpi", {"devIds": dev_id, "devTypeId": self.device_types[dev_id]}
            )
            items = records(row.get("data"))
            item = next((r for r in items if str(r.get("devId")) == dev_id), None)
            if item is None:
                raise VendorError("latest_response_device_mismatch")
            raw_time = item.get("collectTime")
            stamp = raw_time / 1000 if type(raw_time) in (int, float) else None
            points = item.get("dataItemMap")
            if not isinstance(points, dict):
                raise VendorError("vendor_invalid_measurements")
            result.append(
                {
                    "deviceSn": dev_id,
                    "deviceState": 1 if stamp else 0,
                    "collectionTime": stamp,
                    "dataList": self.decode_native_points(points),
                    "native": item,
                }
            )
        return result

    @staticmethod
    def validate_collect_time(value: int) -> None:
        # Operational solar history only: reject seconds, booleans and implausible epoch values.
        if type(value) is not int or not 946684800000 <= value < 4102444800000:
            raise VendorError("collect_time_must_be_epoch_milliseconds_2000_2099")

    async def history(self, dev_id: str, dev_type_id: int, collect_time: int) -> dict[str, Any]:
        """Native five-minute history; collect_time must be epoch milliseconds."""
        self.validate_collect_time(collect_time)
        if type(dev_type_id) is not int or dev_type_id <= 0:
            raise VendorError("invalid_device_type")
        return await self.read(
            "/thirdData/getDevFiveMinutes",
            {
                "devIds": dev_id,
                "devTypeId": dev_type_id,
                "collectTime": collect_time,
            },
        )

    async def history_station_day(self, station_codes: str, collect_time: int) -> dict[str, Any]:
        """Query station day-level KPI with epoch milliseconds."""
        self.validate_collect_time(collect_time)
        return await self.read(
            "/thirdData/getKpiStationDay",
            {
                "stationCodes": station_codes,
                "collectTime": collect_time,
            },
        )

    async def history_station_month(self, station_codes: str, collect_time: int) -> dict[str, Any]:
        """Query station month-level KPI with epoch milliseconds."""
        self.validate_collect_time(collect_time)
        return await self.read(
            "/thirdData/getKpiStationMonth",
            {
                "stationCodes": station_codes,
                "collectTime": collect_time,
            },
        )

    async def history_station_year(self, station_codes: str, collect_time: int) -> dict[str, Any]:
        """Query station year-level KPI with epoch milliseconds."""
        self.validate_collect_time(collect_time)
        return await self.read(
            "/thirdData/getKpiStationYear",
            {
                "stationCodes": station_codes,
                "collectTime": collect_time,
            },
        )

    async def alerts(
        self, station_codes: str, begin_time: int, end_time: int, page: int = 1, size: int = 100
    ) -> list[dict[str, Any]]:
        """Query alarm list for stations.

        Args:
            station_codes: Comma-separated station codes.
            begin_time: Begin time as Unix timestamp (ms).
            end_time: End time as Unix timestamp (ms).
        """
        payload = await self.read(
            "/thirdData/getAlarmList",
            {
                "stationCodes": station_codes,
                "beginTime": begin_time,
                "endTime": end_time,
                "pageNo": page,
                "pageSize": size,
            },
        )
        return records(payload.get("data", {}).get("list", []))

    @staticmethod
    def decode_native_points(native_data: dict[str, Any]) -> list[dict[str, Any]]:
        # Northbound JSON exposes engineering values, not raw Modbus registers.
        return [
            {"key": key, "value": value, "unit": HUAWEI_NATIVE_POINTS.get(key, {}).get("unit")}
            for key, value in native_data.items()
            if type(value) in (str, int, float)
        ]
