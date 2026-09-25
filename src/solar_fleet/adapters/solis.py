"""SolisCloud user HMAC API, official developer portal retrieved 2026-09-13.

Source references:
- SOLIS_DEV_DATA_002: SolisCloud API V2.0 data endpoints
- SOLIS_DEV_AUTH_002: SolisCloud HMAC-SHA1 authentication
- SOLIS_CONTROL_001: SolisCloud Device Control API V2.0
Evidence grade: C (API docs behind activation; community implementations available)

Public protocol docs do not yet specify timestamp units or stable list pagination.
Retain raw values; report incomplete discovery instead of inventing a cursor.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from datetime import datetime
from email.utils import format_datetime
from typing import Any

from ..domain import VendorError, utcnow
from .cloud import ReadCloud, compact, records

HOSTS = {"global": "https://www.soliscloud.com:13333"}

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
    """SolisCloud HMAC-SHA1 API adapter with tested discovery/latest contracts and native point normalization."""

    evidence_ids = ["SOLIS_DEV_DATA_002", "SOLIS_DEV_AUTH_002", "SOLIS_CONTROL_001"]
    version = "0.2.0"

    def __init__(self, integration, credentials, **kwargs):
        if integration.get("region") not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[integration["region"]]
        if any(not credentials.get(k) for k in ("key_id", "key_secret")):
            raise VendorError("credentials_incomplete")
        super().__init__(integration, credentials, **kwargs)

    async def read(self, path, body):
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
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
