"""Explicit SEMS+ read-only account linking; the shared registry owns transport."""

import asyncio
import time
import uuid
from collections import deque
from typing import Literal

from fastapi import Depends, HTTPException, Request
from pydantic import Field, SecretStr, field_validator

from .domain import Model, SafetyError, utcnow
from .security import require_session_principal
from .transport_guard import guarded_read


class GoodWeConnectionForm(Model):
    region: Literal["hk", "eu", "au", "us", "cn"]
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=4096)
    vendor_terms_accepted: Literal[True]
    integration_id: str | None = Field(default=None, min_length=1, max_length=64)
    revision: int | None = Field(default=None, ge=1)

    @field_validator("email")
    @classmethod
    def valid_email(cls, value):
        value = value.strip()
        if value.count("@") != 1 or any(c.isspace() for c in value) or not all(value.split("@")):
            raise ValueError("invalid_email")
        return value


def install_goodwe_connection(app, controller, admin):
    store, vault = controller.store, controller.vault
    attempts = deque()
    cooldowns = {}

    @app.post("/api/connections/goodwe", status_code=201)
    async def connect(body: GoodWeConnectionForm, request: Request, who=Depends(admin)):
        email = body.email
        if controller.poll_lock.locked():
            raise HTTPException(409, "poll_already_running")
        async with controller.poll_lock:
            with store.transaction():
                require_session_principal(store, request.cookies.get("solar_session"), who)
                id = body.integration_id or uuid.uuid4().hex
                previous = store.get("integration", id)
                if body.integration_id and (
                    not previous or previous.get("vendor") != "GoodWe"
                    or previous.get("platform") != "sems_plus"
                    or previous.get("region") != body.region
                    or vault.get(id).get("account") != email
                    or previous.get("connection_revision") != body.revision
                ):
                    raise HTTPException(409, "goodwe_reconnect_context_changed")
                for row in store.list("integration"):
                    if (row["id"] != id and row.get("vendor") == "GoodWe"
                            and row.get("region") == body.region and row.get("platform") == "sems_plus"
                            and vault.get(row["id"]).get("account") == email):
                        raise HTTPException(409, "goodwe_account_already_linked")
                now = time.monotonic()
                cooldowns_key = (body.region, email)
                if cooldowns.get(cooldowns_key, 0) > now:
                    raise HTTPException(429, "goodwe_login_rate_limited")
                for key in list(cooldowns):
                    if cooldowns[key] <= now:
                        del cooldowns[key]
                while attempts and attempts[0] <= now - 60:
                    attempts.popleft()
                if len(attempts) >= 3:
                    raise HTTPException(429, "goodwe_login_rate_limited")
                attempts.append(now)
                revisions = store.object_revisions({"integration": [id]})
                config = {
                    **(previous or {}), "id": id, "name": previous["name"] if previous else "GoodWe SEMS+",
                    "vendor": "GoodWe", "platform": "sems_plus", "region": body.region,
                    "enabled": True, "connection_revision": (previous or {}).get("connection_revision", 0) + 1,
                }
                credentials = {"account": email, "password": body.password.get_secret_value(),
                               "vendor_terms_accepted": True}

            def revalidate():
                require_session_principal(store, request.cookies.get("solar_session"), who)
                if store.object_revisions(revisions) != revisions:
                    raise HTTPException(409, "goodwe_connection_context_changed")

            adapter = controller.registry.create(config, credentials, controller.budgets)
            try:
                try:
                    async with asyncio.timeout(40):
                        await guarded_read(revalidate, adapter.authenticate)
                except HTTPException:
                    raise
                except SafetyError as exc:
                    revalidate()
                    reason = str(exc)
                    if reason in ("vendor_rate_limited", "vendor_backoff_active", "local_rate_budget_exhausted"):
                        cooldowns[cooldowns_key] = max(time.monotonic() + 300, adapter.cooldown_until)
                        raise HTTPException(429, "goodwe_login_rate_limited") from None
                    if reason in ("vendor_network_outcome_unknown", "vendor_http_error"):
                        raise HTTPException(503, "goodwe_authentication_unavailable") from None
                    raise HTTPException(400, "goodwe_authentication_failed") from None
                except (TimeoutError, OSError):
                    revalidate()
                    raise HTTPException(503, "goodwe_authentication_unavailable") from None
                with store.transaction():
                    revalidate()
                    vault.put(id, credentials)
                    store.put("integration", id, {**config, "authenticated_at": utcnow().isoformat()})
                    store.put("connection_check", id, {"id": id, "state": "NOT_CHECKED", "checked_at": None, "checks": []})
                    store.audit("security", {"event": "goodwe_semsplus_authenticated", "operator": who.id,
                                             "integration_id": id, "region": body.region})
            finally:
                await adapter.close()
            old = controller.adapters.pop(id, None)
            controller.adapter_credentials.pop(id, None)
            if old:
                await old.close()
            return {"id": id, "state": "AUTHENTICATED", "inventory_synced": False, "write_enabled": False}
