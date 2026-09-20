"""SOLARMAN cloud is a transport ecosystem; it does not establish inverter OEM identity."""

from __future__ import annotations

import asyncio
import hashlib
import time

from ..domain import VendorError
from .cloud import ReadCloud, compact, records

HOSTS = {"global": "https://globalapi.solarmanpv.com", "cn": "https://api.solarmanpv.com"}
READS = {"/station/v1.0/list", "/station/v1.0/device", "/device/v1.0/currentData"}


class Solarman(ReadCloud):
    evidence_ids = ["SOLARMAN_CLOUD_002"]

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
