"""Server-managed Deye application credentials, with explicit account authentication.

Uses the existing official Deye adapter. No browser-session scraping, user grants,
device control, invented refresh endpoint or account-wide support claim.
"""

from __future__ import annotations

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

Region = Literal["eu", "am", "india"]
MANAGED = "MANAGED_DEYE_APPLICATION"


class ApplicationForm(Model):
    revision: str | None = None
    app_id: SecretStr = Field(min_length=1, max_length=4096)
    app_secret: SecretStr = Field(min_length=1, max_length=4096)


class RevisionForm(Model):
    revision: str = Field(min_length=1, max_length=64)


class ConnectionForm(Model):
    region: Region
    application_revision: str = Field(min_length=1, max_length=64)
    email: str = Field(min_length=3, max_length=254)
    password: SecretStr = Field(min_length=1, max_length=4096)
    integration_id: str | None = Field(default=None, min_length=1, max_length=64)

    @field_validator("email")
    @classmethod
    def email_valid(cls, value):
        value = value.strip()
        if value.count("@") != 1 or any(c.isspace() for c in value) or not all(value.split("@")):
            raise ValueError("invalid_email")
        return value


def require_managed_application(store, config):
    if config.get("credential_source") != MANAGED:
        return
    app = store.get("deye_application", config.get("region"))
    if not app or not app.get("enabled") or app["revision"] != config.get("application_revision"):
        raise SafetyError("deye_application_reconnect_required")


def install_deye_connection(app, controller, user, admin):
    store, vault = controller.store, controller.vault
    attempts = deque()

    def secret_id(region):
        return "deye-application:" + region

    def state(region):
        row = store.get("deye_application", region)
        return {
            "region": region,
            "enabled": bool(row and row["enabled"]),
            "revision": row["revision"] if row else None,
            "updated_at": row["updated_at"] if row else None,
        }

    def matching(region):
        return [
            r
            for r in store.list("integration")
            if r.get("credential_source") == MANAGED and r.get("region") == region
        ]

    async def evict(ids):
        for id in ids:
            old = controller.adapters.pop(id, None)
            controller.adapter_credentials.pop(id, None)
            if old:
                await old.close()

    def suspend(region):
        ids = []
        for row in matching(region):
            row["enabled"] = False
            store.put("integration", row["id"], row)
            ids.append(row["id"])
        return ids

    @app.get("/api/connections/deye/options")
    async def options(who=Depends(user)):
        # Only status, not API identifiers, secrets, account identities or tokens.
        return {
            "applications": [state(r) for r in ("eu", "am", "india")],
            "authentication": "EMAIL_PASSWORD_WITH_SERVER_APPLICATION",
            "link_permission": "ORGANIZATION_ADMINISTRATOR",
        }

    @app.post("/api/admin/deye-applications/{region}")
    async def save_application(region: Region, body: ApplicationForm, request: Request, who=Depends(admin)):
        values = {
            "app_id": body.app_id.get_secret_value().strip(),
            "app_secret": body.app_secret.get_secret_value().strip(),
        }
        if not all(values.values()):
            raise HTTPException(422, "deye_application_values_required")
        with store.transaction():
            require_session_principal(store, request.cookies.get("solar_session"), who)
            previous = store.get("deye_application", region)
            if body.revision != (previous["revision"] if previous else None):
                raise HTTPException(409, "deye_application_revision_conflict")
            vault.put(secret_id(region), values)
            store.put(
                "deye_application",
                region,
                {
                    "region": region,
                    "enabled": True,
                    "revision": uuid.uuid4().hex,
                    "updated_at": utcnow().isoformat(),
                },
            )
            ids = suspend(region)
            store.audit(
                "security",
                {
                    "event": "deye_application_saved",
                    "operator": who.id,
                    "region": region,
                    "suspended_accounts": len(ids),
                },
            )
        await evict(ids)
        return {**state(region), "suspended_accounts": len(ids), "vendor_verified": False}

    @app.post("/api/admin/deye-applications/{region}/disable")
    async def disable_application(region: Region, body: RevisionForm, request: Request, who=Depends(admin)):
        with store.transaction():
            require_session_principal(store, request.cookies.get("solar_session"), who)
            previous = store.get("deye_application", region)
            if not previous or previous["revision"] != body.revision:
                raise HTTPException(409, "deye_application_revision_conflict")
            store.put(
                "deye_application",
                region,
                {
                    **previous,
                    "enabled": False,
                    "revision": uuid.uuid4().hex,
                    "updated_at": utcnow().isoformat(),
                },
            )
            ids = suspend(region)
            store.audit(
                "security",
                {
                    "event": "deye_application_disabled",
                    "operator": who.id,
                    "region": region,
                    "suspended_accounts": len(ids),
                },
            )
        await evict(ids)
        return {**state(region), "suspended_accounts": len(ids)}

    @app.post("/api/connections/deye", status_code=201)
    async def connect(body: ConnectionForm, request: Request, who=Depends(admin)):
        if controller.poll_lock.locked():
            raise HTTPException(409, "poll_already_running")
        async with controller.poll_lock:
            with store.transaction():
                require_session_principal(store, request.cookies.get("solar_session"), who)
                application = store.get("deye_application", body.region)
                if not application or not application.get("enabled"):
                    raise HTTPException(409, "deye_application_not_configured")
                if application["revision"] != body.application_revision:
                    raise HTTPException(409, "deye_application_revision_conflict")
                previous = store.get("integration", body.integration_id) if body.integration_id else None
                if body.integration_id and (
                    not previous
                    or previous.get("credential_source") != MANAGED
                    or previous.get("region") != body.region
                ):
                    raise HTTPException(409, "deye_connection_not_managed")
                if previous and vault.get(previous["id"]).get("identity_value") != body.email:
                    raise HTTPException(409, "deye_reconnect_identity_mismatch")
                for row in matching(body.region):
                    if (
                        row["id"] != body.integration_id
                        and vault.get(row["id"]).get("identity_value") == body.email
                    ):
                        raise HTTPException(409, "deye_account_already_linked")
                now = time.monotonic()
                while attempts and attempts[0] <= now - 60:
                    attempts.popleft()
                if len(attempts) >= 6:
                    raise HTTPException(429, "deye_login_rate_limited")
                attempts.append(now)
                id = body.integration_id or uuid.uuid4().hex
                revisions = store.object_revisions({"deye_application": [body.region], "integration": [id]})
                credentials = controller.registry.credentials(
                    "Deye",
                    {
                        **vault.get(secret_id(body.region)),
                        "identity_value": body.email,
                        "password": body.password.get_secret_value(),
                    },
                    {"region": body.region, "identity_field": "email"},
                )
                config = {
                    "id": id,
                    "name": previous["name"] if previous else "Deye Cloud",
                    "vendor": "Deye",
                    "region": body.region,
                    "enabled": True,
                    "credential_source": MANAGED,
                    "application_revision": application["revision"],
                }

            def revalidate():
                require_session_principal(store, request.cookies.get("solar_session"), who)
                if store.object_revisions(revisions) != revisions:
                    raise HTTPException(409, "deye_connection_context_changed")

            adapter = controller.registry.create(config, credentials, controller.budgets)
            try:
                try:
                    async with asyncio.timeout(30):
                        await guarded_read(revalidate, adapter.authenticate)
                except HTTPException:
                    raise
                except SafetyError:
                    revalidate()
                    raise HTTPException(400, "deye_authentication_failed") from None
                except (TimeoutError, OSError):
                    revalidate()
                    raise HTTPException(503, "deye_authentication_unavailable") from None
                with store.transaction():
                    revalidate()
                    store.put(
                        "integration",
                        id,
                        {**(previous or {}), **config, "authenticated_at": utcnow().isoformat()},
                    )
                    vault.put(id, credentials)
                    # Old diagnostics do not certify a new credential session.
                    store.put(
                        "connection_check",
                        id,
                        {"id": id, "state": "NOT_CHECKED", "checked_at": None, "checks": []},
                    )
                    store.audit(
                        "security",
                        {
                            "event": "deye_account_authenticated",
                            "operator": who.id,
                            "integration_id": id,
                            "region": body.region,
                        },
                    )
            finally:
                await adapter.close()
            await evict([id])
            return {"id": id, "state": "AUTHENTICATED", "inventory_synced": False, "write_enabled": False}
