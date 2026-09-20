"""SolisCloud user HMAC API, official developer portal retrieved 2026-09-13.

Public protocol docs do not yet specify timestamp units or stable list pagination.
Retain raw values; report incomplete discovery instead of inventing a cursor.
"""

from __future__ import annotations

import base64
import hashlib
import hmac
from email.utils import format_datetime

from ..domain import VendorError, utcnow
from .cloud import ReadCloud, compact, records

HOSTS = {"global": "https://www.soliscloud.com:13333"}
READS = {"/v1/api/userStationList", "/v1/api/inverterList", "/v1/api/inverterDetail"}


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
    evidence_ids = ["SOLIS_DEV_DATA_002", "SOLIS_DEV_AUTH_002"]

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
            # Field meanings are kept native; no guessed W/kW or charge/discharge signs.
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
