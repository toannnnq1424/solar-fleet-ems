"""Shared read transport. Only explicit endpoints in each adapter can reach the network."""

from __future__ import annotations

import hashlib
import json
import time

import httpx

from ..budgets import Budgets
from ..domain import VendorError


class ReadCloud:
    version = "0.2.0"
    per_poll = 10

    def __init__(self, integration, credentials, *, client=None, budgets=None):
        self.integration, self.credentials = integration, credentials
        self.client = client or httpx.AsyncClient(timeout=20, follow_redirects=False, trust_env=False)
        self.budgets = budgets or Budgets()
        # Credentials never enter logs; duplicate accounts share a conservative budget.
        identity = {k: v for k, v in credentials.items() if k in {"key_id", "identity_value", "org_id"}}
        self.account_key = hashlib.sha256(
            json.dumps([self.host, identity], sort_keys=True).encode()
        ).hexdigest()
        self.cooldown_until = 0.0

    async def close(self):
        await self.client.aclose()

    async def http(self, path, body, *, headers=None, params=None, serial=None):
        if time.monotonic() < self.cooldown_until:
            raise VendorError("vendor_backoff_active")
        await self.budgets.acquire(self.account_key, [serial] if serial else [])
        try:
            response = await self.client.post(self.host + path, content=body, headers=headers, params=params)
        except httpx.HTTPError:
            raise VendorError("vendor_network_outcome_unknown") from None
        if response.status_code == 429:
            try:
                delay = min(3600, max(60, int(response.headers.get("Retry-After", "60"))))
            except ValueError:
                delay = 60
            self.cooldown_until = time.monotonic() + delay
            raise VendorError("vendor_rate_limited")
        if response.status_code in (401, 403):
            if hasattr(self, "access_token"):
                self.access_token = None
            raise VendorError("vendor_auth_or_permission_denied")
        if response.status_code != 200:
            raise VendorError("vendor_http_error")
        if len(response.content) > 10_000_000:
            raise VendorError("vendor_response_too_large")
        try:
            payload = response.json()
        except ValueError:
            raise VendorError("vendor_invalid_json") from None
        if not isinstance(payload, dict) or payload.get("success") is not True:
            raise VendorError("vendor_request_rejected")
        return payload

    async def configuration(self, device):
        raise VendorError("configuration_contract_not_commissioned")

    async def history(self, *args):
        raise VendorError("vendor_history_contract_not_implemented")

    async def alerts(self, *args):
        raise VendorError("vendor_alarm_contract_not_implemented")

    async def send(self, *args):
        raise VendorError("read_only_adapter")

    async def order(self, *args):
        raise VendorError("read_only_adapter")


def records(value):
    if not isinstance(value, list) or any(not isinstance(row, dict) for row in value):
        raise VendorError("vendor_invalid_list")
    return value


def compact(body):
    return json.dumps(body, ensure_ascii=False, separators=(",", ":"), allow_nan=False).encode("utf-8")
