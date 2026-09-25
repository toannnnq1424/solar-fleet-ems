"""Account management diagnostics and revocable, site-scoped read API keys."""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import secrets
import time
import uuid
from collections import defaultdict, deque
from datetime import datetime, timedelta

from fastapi import Depends, HTTPException, Request
from pydantic import Field

from .domain import Model, Role, SafetyError, utcnow
from .security import principal


class ReadKeyForm(Model):
    name: str = Field(min_length=1, max_length=120)
    site_ids: list[str] = Field(min_length=1, max_length=1000)
    expires_days: int = Field(default=90, ge=1, le=365)


def install_accounts(app, controller, admin):
    store = controller.store
    key_calls = defaultdict(deque)

    def public_key(row):
        return {k: v for k, v in row.items() if k != "token_hash"}

    @app.get("/api/accounts/overview")
    async def overview(who=Depends(admin)):
        rows = []
        vault_ok = True
        for config in store.list("integration"):
            try:
                credential = controller.vault.get(config["id"])
                plugin = controller.registry.find(config["vendor"])
                identity_field = (
                    plugin.registration.get("account_identity_field", "identity_value")
                    if plugin
                    else "identity_value"
                )
                identity = credential.get(identity_field) or ""
                # Account identity is organization-admin-only. Never return API identifiers or secrets.
                account = identity if isinstance(identity, str) else ""
            except SafetyError:
                vault_ok = False
                account = ""
            bindings = [b for b in store.list("binding") if b.get("integration_id") == config["id"]]
            rows.append(
                {
                    **config,
                    "account": account or config["name"],
                    "plant_count": len({b["site_id"] for b in bindings}),
                    "authentication": controller.registry.describe(config["vendor"])["authentication"],
                    "expires_at": None,
                    "status": store.get("integration_state", config["id"]),
                    "diagnostic": store.get("connection_check", config["id"]),
                }
            )
        keys = [public_key(k) for k in store.list("read_api_key")]
        return {
            "accounts": rows,
            "keys": keys,
            "active_keys": sum(
                k["active"] and datetime.fromisoformat(k["expires_at"]) > utcnow() for k in keys
            ),
            "agents": len([a for a in store.list("agent") if a.get("enabled")]),
            "certificates": {"count": 0, "implemented": False},
            "vault": {
                "state": "AVAILABLE" if vault_ok else "UNAVAILABLE",
                "checked_at": utcnow().isoformat(),
                "encrypted_accounts": len(rows),
                "encryption": "Fernet",
                "browser_secret_access": False,
            },
        }

    @app.post("/api/integrations/{id}/check")
    async def check(id: str, who=Depends(admin)):
        config = store.get("integration", id)
        if config is None:
            raise HTTPException(404, "integration_not_found")
        if not config.get("enabled"):
            raise SafetyError("integration_not_available")
        last = store.get("connection_check", id)
        if last and (utcnow() - datetime.fromisoformat(last["checked_at"])).total_seconds() < 60:
            raise HTTPException(429, "connection_check_cooldown")
        if controller.poll_lock.locked():
            raise SafetyError("poll_already_running")
        names = ["api", "authentication", "plants", "devices", "sample", "control"]
        result = {
            "id": id,
            "checked_at": utcnow().isoformat(),
            "state": "CHECKING",
            "checks": [{"key": n, "state": "NOT_CHECKED"} for n in names],
        }

        def mark(name, state, **extra):
            item = next(c for c in result["checks"] if c["key"] == name)
            item.update(state=state, **extra)

        started = time.monotonic()
        async with controller.poll_lock:
            store.put("connection_check", id, result)
            try:
                async with asyncio.timeout(90):
                    adapter = controller.integration_adapter(id)
                    stations = await adapter.stations()
                    mark("api", "PASS")
                    mark("authentication", "PASS")
                    mark("plants", "PASS", count=len(stations))
                    if stations:
                        # One plant and at most one device sample; never actuate or scan a network.
                        found = await adapter.devices(stations[0]["id"])
                        mark("devices", "PASS", count=len(found), scope="FIRST_PLANT")
                        if found:
                            serial = found[0].get("deviceSn")
                            if not isinstance(serial, str) or not serial:
                                raise SafetyError("device_identity_invalid")
                            readings = await adapter.latest([serial])
                            if any(r.get("deviceSn") != serial for r in readings):
                                raise SafetyError("latest_response_device_mismatch")
                            count = sum(len(r.get("dataList") or []) for r in readings)
                            mark("sample", "PASS" if count else "NO_DATA", count=count)
                        else:
                            mark("sample", "NO_DATA")
                    else:
                        mark("devices", "NO_DATA")
                        mark("sample", "NO_DATA")
                    result["state"] = "PASS"
            except asyncio.CancelledError:
                result["state"] = "INTERRUPTED"
                raise
            except (SafetyError, TimeoutError):
                result["state"] = "FAILED"
                result["reason"] = "connection_check_failed"
                target = next((c for c in result["checks"] if c["state"] == "NOT_CHECKED"), None)
                if target:
                    target["state"] = "FAILED"
            except Exception:
                result["state"] = "FAILED"
                result["reason"] = "invalid_vendor_response"
            finally:
                # Reading an account never proves hardware write permission or acceptance.
                mark("control", "NOT_COMMISSIONED")
                result["duration_ms"] = round((time.monotonic() - started) * 1000)
                store.put("connection_check", id, result)
                store.audit(
                    "security",
                    {
                        "event": "connection_checked",
                        "operator": who.id,
                        "integration_id": id,
                        "state": result["state"],
                    },
                )
        return result

    @app.post("/api/access-keys", status_code=201)
    async def create_key(body: ReadKeyForm, who=Depends(admin)):
        selected = sorted(set(body.site_ids))
        if any(s == "*" or store.get("site", s) is None for s in selected):
            raise HTTPException(422, "explicit_existing_sites_required")
        if len(store.list("read_api_key")) >= 1000:
            raise HTTPException(409, "api_key_capacity_reached")
        token = "sf_read_" + secrets.token_urlsafe(40)
        id = uuid.uuid4().hex
        row = {
            "id": id,
            "name": body.name,
            "created_by": who.id,
            "site_ids": selected,
            "active": True,
            "created_at": utcnow().isoformat(),
            "expires_at": (utcnow() + timedelta(days=body.expires_days)).isoformat(),
            "scope": "fleet:read",
            "token_hash": hashlib.sha256(token.encode()).hexdigest(),
        }
        with store.transaction():
            store.put("read_api_key", id, row)
            store.audit("security", {"event": "read_api_key_created", "operator": who.id, "key_id": id})
        return {"key": public_key(row), "token": token}

    @app.post("/api/access-keys/{id}/revoke")
    async def revoke(id: str, who=Depends(admin)):
        row = store.get("read_api_key", id)
        if row is None:
            raise HTTPException(404, "api_key_not_found")
        with store.transaction():
            row.update(active=False, revoked_at=utcnow().isoformat())
            store.put("read_api_key", id, row)
            store.audit("security", {"event": "read_api_key_revoked", "operator": who.id, "key_id": id})
        return {"ok": True}

    @app.get("/api/public/v1/fleet")
    async def public_fleet(request: Request):
        header = request.headers.get("authorization", "")
        if not header.startswith("Bearer "):
            raise HTTPException(401, "api_key_required")
        token = header.removeprefix("Bearer ")
        if not token.startswith("sf_read_") or len(token) > 200:
            raise HTTPException(401, "api_key_required")
        digest = hashlib.sha256(token.encode()).hexdigest()
        row = next(
            (k for k in store.list("read_api_key") if hmac.compare_digest(k["token_hash"], digest)), None
        )
        if not row or not row["active"] or datetime.fromisoformat(row["expires_at"]) <= utcnow():
            raise HTTPException(401, "api_key_invalid")
        try:
            owner = principal(store, row["created_by"])
        except SafetyError:
            raise HTTPException(401, "api_key_invalid") from None
        if not owner or owner.role != Role.ADMIN or "*" not in owner.site_ids:
            raise HTTPException(401, "api_key_invalid")
        now = time.monotonic()
        queue = key_calls[row["id"]]
        while queue and queue[0] <= now - 60:
            queue.popleft()
        if len(queue) >= 120:
            raise HTTPException(429, "api_key_rate_limited")
        queue.append(now)
        keys = {"id", "name", "timezone"}
        sites = [
            {k: v for k, v in s.items() if k in keys}
            for s in store.list("site")
            if s["id"] in row["site_ids"]
        ]
        device_keys = {"id", "site_id", "type", "online", "last_seen"}
        devices = [
            {k: v for k, v in d.items() if k in device_keys}
            for d in store.list("device")
            if d["site_id"] in row["site_ids"]
        ]
        return {
            "sites": sites,
            "devices": devices,
            "generated_at": utcnow().isoformat(),
            "scope": "fleet:read",
        }

    return {"overview": overview, "check": check}
