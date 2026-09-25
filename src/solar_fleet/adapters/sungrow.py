"""iSolarCloud OpenAPI read subset, Sungrow API guide (February 2026).
Only the documented Hong Kong gateway is enabled. App account permissions,
plant IDs and native point IDs are explicit; no guessed Modbus/cloud scaling.
"""

import asyncio
import time

from ..domain import VendorError
from .cloud import ReadCloud, compact, records

HOSTS = {"global": "https://gateway.isolarcloud.com.hk"}
READS = {"/openapi/getDeviceList", "/openapi/getDeviceRealTimeData", "/openapi/getPowerStationDetail"}
SUNGROW_NATIVE_POINTS = {}  # Points differ by device_type; an exact profile supplies units.


class Sungrow(ReadCloud):
    evidence_ids = ["SUNGROW_DEV_001"]
    version = "0.3.0"

    def __init__(self, integration, credentials, **kwargs):
        region = integration.get("region", "global")
        if region not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[region]
        if any(not credentials.get(k) for k in ("app_key", "app_secret", "user_account", "user_password")):
            raise VendorError("credentials_incomplete")
        super().__init__(integration, credentials, **kwargs)
        self.access_token, self.expires_at = None, 0
        self.auth_lock, self.device_types = asyncio.Lock(), {}

    def headers(self):
        return {
            "Content-Type": "application/json",
            "sys_code": "901",
            "lang": "en_US",
            "x-access-key": self.credentials["app_secret"],
        }

    def validate_response(self, payload):
        if str(payload.get("result_code")) != "1":
            self.invalidate_auth()
            raise VendorError("sungrow_request_rejected")

    async def authenticate(self):
        async with self.auth_lock:
            if self.access_token and time.monotonic() < self.expires_at:
                return self.access_token
            response = await self.http(
                "/openapi/login",
                compact(
                    {
                        "appkey": self.credentials["app_key"],
                        "user_account": self.credentials["user_account"],
                        "user_password": self.credentials["user_password"],
                    }
                ),
                headers=self.headers(),
            )
            data = response.get("result_data", {})
            if (
                str(data.get("login_state")) != "1"
                or not isinstance(data.get("token"), str)
                or not data["token"]
            ):
                raise VendorError("vendor_invalid_token")
            self.access_token = data["token"]
            self.expires_at = time.monotonic() + 86400 - 300
            return self.access_token

    async def read(self, path, body):
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        token = await self.authenticate()
        response = await self.http(
            path,
            compact({**body, "appkey": self.credentials["app_key"], "token": token}),
            headers=self.headers(),
        )
        return response["result_data"]

    async def stations(self):
        await self.authenticate()
        ids = [v.strip() for v in self.credentials.get("plant_ids", "").split(",") if v.strip()]
        if not ids or len(ids) > 100 or len(ids) != len(set(ids)):
            raise VendorError("sungrow_explicit_plant_ids_required")
        return [{"id": id, "name": id} for id in ids]

    async def devices(self, station_id):
        result, seen = [], set()
        for page in range(1, 501):
            data = await self.read(
                "/openapi/getDeviceList", {"ps_id": station_id, "curPage": page, "size": 100}
            )
            rows = records(data.get("pageList"))
            for row in rows:
                key, kind = row.get("ps_key"), row.get("device_type")
                if not isinstance(key, str) or not key or key in seen or type(kind) not in (int, str):
                    raise VendorError("vendor_device_identity_invalid")
                seen.add(key)
                self.device_types[key] = kind
                result.append(
                    {
                        "deviceSn": key,
                        "deviceType": str(kind),
                        "model": row.get("device_model_code"),
                        "connectStatus": 1 if str(row.get("dev_status")) == "1" else 0,
                        "collectionTime": None,
                        "native": row,
                    }
                )
            total = data.get("rowCount")
            if type(total) is not int or total < len(result):
                raise VendorError("vendor_invalid_pagination")
            if len(result) == total:
                return result
            if not rows:
                break
        raise VendorError("vendor_discovery_incomplete")

    async def latest(self, serials):
        ids = [v.strip() for v in self.credentials.get("point_ids", "").split(",") if v.strip()]
        if not ids or len(ids) > 200 or any(not v.isdigit() for v in ids):
            raise VendorError("sungrow_native_point_selection_required")
        result = []
        for key in serials:
            if key not in self.device_types:
                raise VendorError("device_type_discovery_required")
            data = await self.read(
                "/openapi/getDeviceRealTimeData",
                {
                    "ps_key_list": [key],
                    "point_id_list": [int(v) for v in ids],
                    "device_type": self.device_types[key],
                },
            )
            if data.get("fail_ps_key_list"):
                raise VendorError("sungrow_device_data_unavailable")
            points = [r.get("device_point", {}) for r in records(data.get("device_point_list"))]
            point = next((r for r in points if r.get("ps_key") == key), None)
            if point is None:
                raise VendorError("latest_response_device_mismatch")
            result.append(
                {
                    "deviceSn": key,
                    "deviceState": 1 if str(point.get("dev_status")) == "1" else 0,
                    "collectionTime": None,
                    "dataList": self.decode_native_points(point),
                    "native": point,
                    "timestamp_state": "DEVICE_TIMEZONE_REQUIRED",
                }
            )
        return result

    @staticmethod
    def decode_native_points(data):
        return [
            {"key": k, "value": v, "unit": None}
            for k, v in data.items()
            if k.startswith("p") and k[1:].isdigit() and type(v) in (int, float, str)
        ]
