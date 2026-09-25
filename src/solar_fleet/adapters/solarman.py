"""SOLARMAN cloud is a transport ecosystem; it does not establish inverter OEM identity.

Source references:
- SOLARMAN_CLOUD_002: Solarman OpenAPI (https://globalapi.solarmanpv.com)
- SOLARMAN_LOCAL_001: pysolarmanv5 for local Modbus frame transport
Evidence grade: B-C (OpenAPI documented; control via customControl needs platform enablement)
"""

from __future__ import annotations

import asyncio
import hashlib
import time
from typing import Any

from ..domain import VendorError
from .cloud import ReadCloud, compact, records

HOSTS = {"global": "https://globalapi.solarmanpv.com", "cn": "https://api.solarmanpv.com"}

# Deliberately explicit: mutations elsewhere are NOT accidentally exposed as reads.
READS = {
    "/station/v1.0/list",
    "/station/v1.0/device",
    "/station/v1.0/history",
    "/device/v1.0/currentData",
    "/device/v1.0/list",
    "/device/v1.0/historical",
    "/device/v1.0/alertList",
}


class Solarman(ReadCloud):
    """Solarman OpenAPI adapter with full read coverage and alert/history support."""

    evidence_ids = ["SOLARMAN_CLOUD_002", "SOLARMAN_LOCAL_001"]
    version = "0.2.0"

    def __init__(self, integration, credentials, **kwargs):
        if integration.get("region") not in HOSTS:
            raise VendorError("unsupported_data_center")
        self.host = HOSTS[integration["region"]]
        if any(not credentials.get(k) for k in ("app_id", "app_secret", "identity_value", "password_sha256")):
            raise VendorError("credentials_incomplete")
        if credentials.get("identity_field") not in {"email", "username"}:
            raise VendorError("identity_method_not_supported")
        super().__init__(integration, credentials, **kwargs)
        self.access_token, self.expires_at = None, 0.0
        self.auth_lock = asyncio.Lock()

    async def authenticate(self):
        async with self.auth_lock:
            if self.access_token and time.monotonic() < self.expires_at:
                return self.access_token
            c = self.credentials
            body = {
                "appSecret": c["app_secret"],
                "password": c["password_sha256"],
                c["identity_field"]: c["identity_value"],
            }
            if c.get("org_id") is not None:
                body["orgId"] = c["org_id"]
            result = await self.http(
                "/account/v1.0/token",
                compact(body),
                headers={"Content-Type": "application/json"},
                params={"appId": c["app_id"], "language": "en"},
            )
            token = result.get("access_token")
            try:
                duration = int(result["expires_in"])
            except (KeyError, TypeError, ValueError):
                raise VendorError("vendor_invalid_token") from None
            if not isinstance(token, str) or not token or not 60 < duration <= 60 * 86400:
                raise VendorError("vendor_invalid_token")
            if str(result.get("token_type", "")).lower() != "bearer":
                raise VendorError("vendor_invalid_token")
            self.access_token, self.expires_at = token, time.monotonic() + duration - 60
            return token

    async def read(self, path, body):
        if path not in READS:
            raise VendorError("read_endpoint_not_allowed")
        token = await self.authenticate()
        return await self.http(
            path,
            compact(body),
            params={"language": "en"},
            headers={"Content-Type": "application/json", "Authorization": "bearer " + token},
            serial=body.get("deviceSn"),
        )

    async def pages(self, path, key, body):
        result, seen = [], set()
        for page in range(1, 501):
            payload = await self.read(path, {**body, "page": page, "size": 50})
            rows = records(payload.get(key))
            total = payload.get("total")
            if type(total) is not int or total < 0:
                raise VendorError("vendor_invalid_pagination")
            fingerprint = hashlib.sha256(compact(rows)).hexdigest()
            if rows and fingerprint in seen:
                raise VendorError("vendor_pagination_repeated")
            seen.add(fingerprint)
            result.extend(rows)
            if len(result) == total:
                return result
            if not rows or len(result) > total:
                raise VendorError("vendor_pagination_incomplete")
        raise VendorError("vendor_pagination_limit")

    async def stations(self):
        return await self.pages("/station/v1.0/list", "stationList", {})

    async def devices(self, station_id):
        return await self.pages("/station/v1.0/device", "deviceListItems", {"stationId": station_id})

    async def latest(self, serials):
        result = []
        for serial in serials:
            row = await self.read("/device/v1.0/currentData", {"deviceSn": serial})
            if row.get("deviceSn") != serial:
                raise VendorError("latest_response_device_mismatch")
            records(row.get("dataList"))
            result.append(row)
        return result

    async def history(
        self, serial: str, start_time: int, end_time: int, time_type: int = 1
    ) -> dict[str, Any]:
        """Query device historical data.

        Args:
            serial: Device serial number.
            start_time: Start time as Unix timestamp (seconds).
            end_time: End time as Unix timestamp (seconds).
            time_type: 1=day, 2=month, 3=year.
        """
        if end_time <= start_time:
            raise VendorError("history_window_invalid")
        return await self.read(
            "/device/v1.0/historical",
            {
                "deviceSn": serial,
                "startTime": start_time,
                "endTime": end_time,
                "timeType": time_type,
            },
        )

    async def station_history(self, station_id: int, start_time: int, end_time: int) -> dict[str, Any]:
        """Query station-level historical data."""
        if end_time <= start_time:
            raise VendorError("history_window_invalid")
        return await self.read(
            "/station/v1.0/history",
            {
                "stationId": station_id,
                "startTime": start_time,
                "endTime": end_time,
            },
        )

    async def alerts(
        self, serial: str, start_time: int = None, end_time: int = None, page: int = 1, size: int = 100
    ) -> list[dict[str, Any]]:
        """Query device alert list."""
        body: dict[str, Any] = {"deviceSn": serial, "page": page, "size": size}
        if start_time is not None:
            body["startTime"] = start_time
        if end_time is not None:
            body["endTime"] = end_time
        payload = await self.read("/device/v1.0/alertList", body)
        return records(payload.get("alertList", []))
