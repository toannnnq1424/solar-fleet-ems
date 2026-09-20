"""Access changes revoke sessions; command reconciliation only reads terminal vendor orders."""

from __future__ import annotations

import json

from fastapi import Depends, HTTPException
from pydantic import Field, SecretStr

from .control import fresh
from .domain import CommandStatus, Model, Role, SafetyError
from .security import authorize_control, password_hash


class AccessChange(Model):
    role: Role
    site_ids: list[str] = Field(min_length=1, max_length=1000)
    permissions: list[str] = Field(default_factory=list, max_length=20)


class ResetPassword(Model):
    password: SecretStr


def install_administration(app, controller, user, admin):
    store = controller.store

    @app.post("/api/users/{id}/access")
    async def change_access(id: str, body: AccessChange, who=Depends(admin)):
        if id == who.id:
            raise SafetyError("cannot_change_current_administrator")
        if set(body.permissions) - {"grid_settings", "raw_commands", "firmware_upgrade", "battery_settings"}:
            raise SafetyError("unknown_permission")
        if any(s != "*" and not store.get("site", s) for s in body.site_ids):
            raise SafetyError("site_not_found")
        with store.transaction():
            result = store.db.execute(
                "UPDATE users SET role=?,sites=?,permissions=? WHERE id=?",
                (
                    body.role,
                    json.dumps(sorted(set(body.site_ids))),
                    json.dumps(sorted(set(body.permissions))),
                    id,
                ),
            )
            if not result.rowcount:
                raise HTTPException(404)
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (id,))
            store.audit(
                "security",
                {
                    "event": "user_access_changed",
                    "operator": who.id,
                    "user": id,
                    "role": body.role,
                    "site_ids": body.site_ids,
                    "permissions": body.permissions,
                },
            )
        return {"ok": True, "sessions_revoked": True}

    @app.post("/api/users/{id}/password")
    async def reset_password(id: str, body: ResetPassword, who=Depends(admin)):
        if id == who.id:
            raise SafetyError("cannot_reset_current_administrator_here")
        try:
            hashed = password_hash(body.password.get_secret_value())
        except ValueError:
            raise SafetyError("password_invalid") from None
        with store.transaction():
            result = store.db.execute("UPDATE users SET password_hash=? WHERE id=?", (hashed, id))
            if not result.rowcount:
                raise HTTPException(404)
            store.db.execute("DELETE FROM sessions WHERE user_id=?", (id,))
            store.audit("security", {"event": "password_reset", "operator": who.id, "user": id})
        return {"ok": True, "sessions_revoked": True}

    @app.get("/api/commands/{id}/timeline")
    async def timeline(id: str, who=Depends(user)):
        command = store.command(id)
        if not command or not who.can_access(command["site_id"]):
            raise HTTPException(404)
        plan = store.plan(command["plan_id"])
        # Scope is checked against both current device and original plan.
        if not who.can_access(controller.device(command["device_id"]).site_id):
            raise HTTPException(403, "site_access_denied")
        events = [
            r["body"]
            for r in reversed(store.audit_rows("control"))
            if r["body"].get("command_id") == id or r["body"].get("plan_id") == id
        ]
        return {"command": command, "plan": plan, "events": events}

    @app.post("/api/commands/{id}/reconcile")
    async def reconcile(id: str, who=Depends(user)):
        command = store.command(id)
        if not command or not who.can_access(command["site_id"]):
            raise HTTPException(404)
        if command["status"] != "TIMEOUT":
            raise SafetyError("reconciliation_requires_unknown_outcome")
        plan = store.plan(command["plan_id"])
        device = controller.device(command["device_id"])
        capability = controller.capability(device, plan.intent)
        authorize_control(who, device.site_id, capability)
        if device.identity != plan.capability.identity or capability != plan.capability:
            raise SafetyError("capability_profile_changed")
        async with controller.engine.locks[device.id]:
            current = store.command(id)
            if current["status"] != "TIMEOUT":
                raise SafetyError("command_changed_reload")
            orders = json.loads(current["order_ids"])
            if not orders:
                raise SafetyError("missing_vendor_order_manual_investigation_required")
            adapter = controller.adapter(device)
            outcomes = [await adapter.order(order) for order in orders]
            if any(o.state == "PENDING" for o in outcomes):
                raise SafetyError("vendor_order_still_pending")
            config = await adapter.configuration(device)
            fresh(config, after=plan.created_at)
            if not all(key in config.values for key in plan.expected):
                raise SafetyError("readback_fields_incomplete")
            matched = all(config.values[key] == value for key, value in plan.expected.items())
            succeeded = all(o.state == "SUCCEEDED" for o in outcomes)
            status = CommandStatus.VERIFIED if succeeded and matched else CommandStatus.FAILED
            with store.transaction():
                controller.engine.transition(
                    plan,
                    status,
                    orders=orders,
                    error=None
                    if status == CommandStatus.VERIFIED
                    else "terminal_order_reconciled_with_observed_state",
                    readback=config.values,
                )
                store.audit(
                    "control",
                    {
                        "event": "command_reconciled",
                        "command_id": id,
                        "operator": who.id,
                        "vendor_terminal": True,
                        "matched": matched,
                    },
                    command["site_id"],
                )
            return store.command(id)
