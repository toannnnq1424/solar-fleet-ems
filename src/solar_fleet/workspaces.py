"""Local operational records, scoped to sites. Drafts never actuate equipment."""

from __future__ import annotations

import csv
import io
import json
import math
import sqlite3
import uuid
from datetime import datetime
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException, Response
from pydantic import Field, SecretStr, field_validator, model_validator

from .domain import Model, Role, SafetyError, Sample, utcnow
from .providers import PROVIDERS
from .rules import RuleForm, evaluate
from .security import create_user


class SiteForm(Model):
    name: str = Field(min_length=1, max_length=160)
    customer: str = Field(default="", max_length=160)
    address: str = Field(default="", max_length=300)
    timezone: str = "Asia/Ho_Chi_Minh"
    capacity_kwp: float | None = Field(default=None, ge=0, le=10_000_000, allow_inf_nan=False)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)

    @field_validator("timezone")
    @classmethod
    def timezone_valid(cls, value):
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError):
            raise ValueError("invalid timezone") from None
        return value

    @model_validator(mode="after")
    def coordinate_pair(self):
        if (self.latitude is None) != (self.longitude is None):
            raise ValueError("both coordinates required")
        return self


class IntegrationForm(Model):
    name: str = Field(min_length=1, max_length=120)
    vendor: str
    region: str
    identity_field: Literal["email", "username"] = "email"
    credentials: dict[str, SecretStr]
    org_id: int | None = Field(default=None, gt=0)
    equipment_brand: str | None = Field(default=None, min_length=1, max_length=80)


class Enabled(Model):
    enabled: bool


class RecordForm(Model):
    site_id: str
    title: str = Field(min_length=1, max_length=200)
    description: str = Field(default="", max_length=4000)
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    assigned_to: str = Field(default="", max_length=100)
    due_date: str | None = None
    incident_id: str | None = None
    device_id: str | None = None

    @field_validator("due_date")
    @classmethod
    def valid_date(cls, value):
        if value is not None:
            datetime.strptime(value, "%Y-%m-%d")
        return value


class RecordUpdate(Model):
    revision: int = Field(ge=1)
    status: Literal["open", "acknowledged", "in_progress", "resolved", "closed"]
    assigned_to: str = Field(default="", max_length=100)
    note: str = Field(min_length=1, max_length=2000)


class Slot(Model):
    day: int = Field(ge=0, le=6)
    start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$")
    mode: Literal["self_use", "charge", "discharge", "hold"]
    target_soc: int | None = Field(default=None, ge=0, le=100)
    power_kw: float | None = Field(default=None, ge=0, le=1000000, allow_inf_nan=False)

    @model_validator(mode="after")
    def order(self):
        if self.start >= self.end:
            raise ValueError("split overnight slots at midnight")
        return self


class ScheduleForm(Model):
    name: str = Field(min_length=1, max_length=120)
    site_id: str
    slots: list[Slot] = Field(min_length=1, max_length=168)

    @model_validator(mode="after")
    def no_overlap(self):
        ordered = sorted(self.slots, key=lambda s: (s.day, s.start))
        for left, right in zip(ordered, ordered[1:]):
            if left.day == right.day and right.start < left.end:
                raise ValueError("overlapping slots")
        return self


class CompatibilityForm(Model):
    device_ids: list[str] = Field(min_length=1, max_length=100)
    intent: str = Field(min_length=1, max_length=100)


class UserForm(Model):
    username: str = Field(min_length=1, max_length=100, pattern=r"^[\w.@-]+$")
    password: SecretStr
    role: Role
    site_ids: list[str] = Field(min_length=1, max_length=1000)


class CommissionCheck(Model):
    site_id: str
    check: Literal["topology", "meter_ct", "power_direction", "battery", "control_readback", "alarms"]
    result: Literal["pending", "pass", "warning", "fail"]
    evidence: str = Field(min_length=1, max_length=3000)


def csv_text(rows, columns):
    stream = io.StringIO(newline="")
    writer = csv.writer(stream)
    writer.writerow(columns)
    for row in rows:
        values = []
        for key in columns:
            value = row.get(key)
            if isinstance(value, (list, dict)):
                value = json.dumps(value, ensure_ascii=False)
            if isinstance(value, str) and value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                value = "'" + value
            values.append("" if value is None else value)
        writer.writerow(values)
    return "\ufeff" + stream.getvalue()


def install_workspaces(app, controller, user, admin):
    store = controller.store

    def site_access(id, who):
        if not who.can_access(id):
            raise HTTPException(403, "site_access_denied")
        row = store.get("site", id)
        if row is None:
            raise HTTPException(404, "site_not_found")
        return {**row, **(store.get("site_profile", id) or {})}

    def operator(who=Depends(user)):
        if who.role == Role.VIEWER:
            raise HTTPException(403, "operator_required")
        return who

    def assignee(value, site_id):
        if not value:
            return
        row = store.db.execute("SELECT sites,active FROM users WHERE id=?", (value,)).fetchone()
        if row is None or not row["active"] or not ({site_id, "*"} & set(json.loads(row["sites"]))):
            raise SafetyError("assignee_not_authorized_for_site")

    @app.get("/api/providers")
    async def providers(who=Depends(user)):
        registered = controller.registry.registration_catalog()
        ids = {p["id"] for p in registered}
        return registered + [p for p in PROVIDERS if p["id"] not in ids and not p["implemented"]]

    @app.post("/api/integrations", status_code=201)
    async def add_integration(body: IntegrationForm, who=Depends(admin)):
        credentials = controller.registry.credentials(
            body.vendor,
            {k: v.get_secret_value() for k, v in body.credentials.items()},
            {
                "region": body.region,
                "identity_field": body.identity_field,
                "org_id": body.org_id,
                "equipment_brand": body.equipment_brand,
            },
        )
        id = uuid.uuid4().hex
        with store.transaction():
            controller.vault.put(id, credentials)
            store.put(
                "integration",
                id,
                {
                    "id": id,
                    "name": body.name,
                    "vendor": body.vendor,
                    "region": body.region,
                    "enabled": True,
                    "equipment_brand": body.equipment_brand,
                },
            )
            store.audit(
                "security",
                {
                    "event": "integration_added",
                    "operator": who.id,
                    "integration_id": id,
                    "vendor": body.vendor,
                },
            )
        return {"id": id, "state": "SAVED", "write_enabled": False}

    @app.post("/api/integrations/{id}/enabled")
    async def integration_enabled(id: str, body: Enabled, who=Depends(admin)):
        if controller.poll_lock.locked():
            raise SafetyError("poll_already_running")
        row = store.get("integration", id)
        if row is None:
            raise HTTPException(404)
        row["enabled"] = body.enabled
        store.put("integration", id, row)
        old = controller.adapters.pop(id, None)
        if old:
            await old.close()
        store.audit(
            "security",
            {
                "event": "integration_enabled_changed",
                "operator": who.id,
                "integration_id": id,
                "enabled": body.enabled,
            },
        )
        return {"ok": True}

    @app.post("/api/sites", status_code=201)
    async def add_site(body: SiteForm, who=Depends(admin)):
        id = uuid.uuid4().hex
        row = {
            "id": id,
            **body.model_dump(),
            "vendor": None,
            "source": "MANUAL",
            "created_at": utcnow().isoformat(),
        }
        with store.transaction():
            store.put("site", id, row)
            store.audit("operations", {"event": "site_created", "operator": who.id}, id)
        return row

    @app.post("/api/sites/{id}/profile")
    async def site_profile(id: str, body: SiteForm, who=Depends(admin)):
        site_access(id, who)
        with store.transaction():
            store.put("site_profile", id, body.model_dump())
            store.audit("operations", {"event": "site_profile_updated", "operator": who.id}, id)
        return {"ok": True}

    @app.get("/api/operations")
    async def operations(who=Depends(user)):
        result = {
            kind: [r for r in store.list(kind) if who.can_access(r["site_id"])]
            for kind in ("incident", "work_order", "schedule", "commissioning", "rule", "rule_run")
        }
        result["assignees"] = [
            {"id": r["id"]}
            for r in store.db.execute("SELECT id,sites FROM users WHERE active=1")
            if "*" in who.site_ids or {"*", *who.site_ids} & set(json.loads(r["sites"]))
        ]
        return result

    @app.post("/api/records/{kind}", status_code=201)
    async def create_record(kind: str, body: RecordForm, who=Depends(operator)):
        if kind not in {"incident", "work_order"}:
            raise HTTPException(404)
        site_access(body.site_id, who)
        assignee(body.assigned_to, body.site_id)
        if body.device_id and controller.device(body.device_id).site_id != body.site_id:
            raise SafetyError("device_site_mismatch")
        if body.incident_id:
            linked = store.get("incident", body.incident_id)
            if kind != "work_order" or not linked or linked["site_id"] != body.site_id:
                raise SafetyError("incident_site_mismatch")
        if kind == "incident":
            return controller.incidents.create_manual(body, who)
        id, now = uuid.uuid4().hex, utcnow().isoformat()
        row = {
            "id": id,
            **body.model_dump(),
            "status": "open",
            "revision": 1,
            "created_at": now,
            "updated_at": now,
            "source": "MANUAL",
            "timeline": [{"at": now, "actor": who.id, "status": "open", "note": body.description}],
        }
        with store.transaction():
            store.put(kind, id, row)
            store.audit(
                "operations", {"event": kind + "_created", "id": id, "operator": who.id}, body.site_id
            )
        return row

    @app.post("/api/records/{kind}/{id}")
    async def update_record(kind: str, id: str, body: RecordUpdate, who=Depends(operator)):
        if kind not in {"incident", "work_order"}:
            raise HTTPException(404)
        if kind == "incident":
            return controller.incidents.change(id, body, who)
        with store.transaction():
            row = store.get(kind, id)
            if row is None:
                raise HTTPException(404)
            site_access(row["site_id"], who)
            assignee(body.assigned_to, row["site_id"])
            if body.revision != row["revision"]:
                raise SafetyError("record_changed_reload")
            transitions = {
                "open": {"open", "acknowledged", "in_progress"},
                "acknowledged": {"acknowledged", "in_progress", "resolved"},
                "in_progress": {"in_progress", "resolved"},
                "resolved": {"resolved", "closed", "open"},
                "closed": {"closed", "open"},
            }
            if body.status not in transitions[row["status"]]:
                raise SafetyError("invalid_status_transition")
            from .maintenance import guard_work_order_completion

            guard_work_order_completion(store, row, body.status)
            now = utcnow().isoformat()
            row.update(
                status=body.status, assigned_to=body.assigned_to, revision=row["revision"] + 1, updated_at=now
            )
            row["timeline"].append({"at": now, "actor": who.id, "status": body.status, "note": body.note})
            store.put(kind, id, row)
            store.audit(
                "operations",
                {
                    "event": kind + "_updated",
                    "id": id,
                    "operator": who.id,
                    "status": body.status,
                    "revision": row["revision"],
                },
                row["site_id"],
            )
        return row

    @app.post("/api/schedules", status_code=201)
    async def save_schedule(body: ScheduleForm, who=Depends(operator)):
        site = site_access(body.site_id, who)
        timezone = site.get("timezone")
        try:
            ZoneInfo(timezone or "")
        except (ZoneInfoNotFoundError, ValueError):
            raise SafetyError("site_timezone_required") from None
        id = uuid.uuid4().hex
        row = {
            "id": id,
            **body.model_dump(),
            "timezone": timezone,
            "state": "DRAFT",
            "execution_location": "UNCOMMISSIONED",
            "created_at": utcnow().isoformat(),
            "created_by": who.id,
        }
        with store.transaction():
            store.put("schedule", id, row)
            store.audit(
                "operations", {"event": "schedule_draft_created", "id": id, "operator": who.id}, body.site_id
            )
        return row

    @app.post("/api/compatibility")
    async def compatibility(body: CompatibilityForm, who=Depends(user)):
        result = []
        for id in dict.fromkeys(body.device_ids):
            device = controller.device(id)
            if not who.can_access(device.site_id):
                raise HTTPException(403, "site_access_denied")
            cap = controller.capability(device, body.intent)
            result.append(
                {
                    "device_id": id,
                    "vendor": device.identity.vendor,
                    "state": cap.state,
                    "semantic_match": cap.semantic_match,
                    "reasons": [cap.reason],
                    "dispatch_enabled": False,
                    "evidence_ids": cap.evidence_ids,
                }
            )
        return {"intent": body.intent, "targets": result, "mode": "ASSESSMENT_ONLY"}

    @app.post("/api/rules", status_code=201)
    async def save_rule(body: RuleForm, who=Depends(operator)):
        site_access(body.site_id, who)
        for item in [*body.conditions, *body.actions]:
            device = controller.device(item.device_id)
            if device.site_id != body.site_id:
                raise SafetyError("device_site_mismatch")
        for action in body.actions:
            controller.capability(controller.device(action.device_id), action.intent)
        id = uuid.uuid4().hex
        row = {
            "id": id,
            **body.model_dump(),
            "state": "DRAFT",
            "created_at": utcnow().isoformat(),
            "created_by": who.id,
        }
        with store.transaction():
            store.put("rule", id, row)
            store.audit(
                "operations", {"event": "rule_draft_created", "id": id, "operator": who.id}, body.site_id
            )
        return row

    @app.post("/api/rules/{id}/evaluate")
    async def evaluate_rule(id: str, who=Depends(operator)):
        row = store.get("rule", id)
        if row is None:
            raise HTTPException(404)
        site_access(row["site_id"], who)
        rule = RuleForm.model_validate({key: row[key] for key in RuleForm.model_fields})
        device_ids = {item.device_id for item in [*rule.conditions, *rule.actions]}
        devices = [controller.device(id) for id in device_ids]
        if any(d.site_id != rule.site_id for d in devices):
            raise SafetyError("device_site_mismatch")
        samples = [Sample.model_validate(s) for d in devices for s in controller.latest(d)["samples"]]
        result = evaluate(rule, samples)
        result["capabilities"] = [
            {
                "device_id": a.device_id,
                "intent": a.intent,
                "state": controller.capability(controller.device(a.device_id), a.intent).state,
            }
            for a in rule.actions
        ]
        result["evaluated_at"] = result["evaluated_at"].isoformat()
        for item in result["conditions"]:
            if item.get("source_timestamp"):
                item["source_timestamp"] = item["source_timestamp"].isoformat()
        run_id = uuid.uuid4().hex
        result.update(id=run_id, rule_id=id, site_id=rule.site_id, created_by=who.id)
        with store.transaction():
            store.put("rule_run", run_id, result)
            store.audit(
                "operations",
                {
                    "event": "rule_dry_run",
                    "id": run_id,
                    "operator": who.id,
                    "condition_state": result["condition_state"],
                },
                rule.site_id,
            )
        return result

    @app.post("/api/commissioning")
    async def commissioning(body: CommissionCheck, who=Depends(operator)):
        if who.role not in {Role.INSTALLER, Role.ENGINEER}:
            raise HTTPException(403, "technical_role_required")
        site_access(body.site_id, who)
        id = uuid.uuid4().hex
        row = {
            "id": id,
            **body.model_dump(),
            "created_by": who.id,
            "created_at": utcnow().isoformat(),
            "method": "MANUAL_ATTESTATION",
            "unlocks_control": False,
        }
        with store.transaction():
            store.put("commissioning", id, row)
            store.audit(
                "operations", {"event": "commissioning_recorded", "id": id, "operator": who.id}, body.site_id
            )
        return row

    @app.get("/api/users")
    async def users(who=Depends(admin)):
        return [
            {
                "id": row["id"],
                "role": row["role"],
                "site_ids": json.loads(row["sites"]),
                "active": bool(row["active"]),
                "permissions": json.loads(row["permissions"]),
            }
            for row in store.db.execute("SELECT * FROM users ORDER BY id")
        ]

    @app.post("/api/users", status_code=201)
    async def add_user(body: UserForm, who=Depends(admin)):
        for id in body.site_ids:
            if id != "*":
                site_access(id, who)
        try:
            with store.transaction():
                create_user(store, body.username, body.password.get_secret_value(), body.role, body.site_ids)
                store.audit("security", {"event": "user_created", "operator": who.id, "user": body.username})
        except (ValueError, sqlite3.IntegrityError):
            raise SafetyError("user_invalid_or_exists") from None
        return {"id": body.username}

    @app.post("/api/users/{id}/enabled")
    async def user_enabled(id: str, body: Enabled, who=Depends(admin)):
        if id == who.id:
            raise SafetyError("cannot_disable_current_user")
        with store.transaction():
            result = store.db.execute("UPDATE users SET active=? WHERE id=?", (int(body.enabled), id))
            if not result.rowcount:
                raise HTTPException(404)
            if not body.enabled:
                store.db.execute("DELETE FROM sessions WHERE user_id=?", (id,))
            store.audit(
                "security",
                {"event": "user_enabled_changed", "operator": who.id, "user": id, "enabled": body.enabled},
            )
        return {"ok": True}

    @app.get("/api/reports/telemetry")
    async def report(
        device_id: str,
        start: datetime | None = None,
        end: datetime | None = None,
        metric: str | None = None,
        download: bool = False,
        who=Depends(user),
    ):
        device = controller.device(device_id)
        if not who.can_access(device.site_id):
            raise HTTPException(403, "site_access_denied")
        if any(t is not None and t.tzinfo is None for t in (start, end)) or (start and end and start >= end):
            raise SafetyError("invalid_time_range")
        rows = []
        # Query one beyond the documented cap so truncation is explicit.
        raw = store.report_samples(device_id, start, end, metric, limit=10001)
        for row in raw[:10000]:
            timestamp = row["source_timestamp"] or row["received_at"]
            at = datetime.fromisoformat(timestamp)
            if (start and at < start) or (end and at >= end) or (metric and row["metric"] != metric):
                continue
            rows.append(row)
        columns = [
            "device_id",
            "metric",
            "value",
            "unit",
            "source",
            "source_timestamp",
            "received_at",
            "quality",
            "binding_id",
            "evidence_ids",
        ]
        if download:
            return Response(
                csv_text(rows, columns),
                media_type="text/csv; charset=utf-8",
                headers={
                    "Content-Disposition": 'attachment; filename="solar-fleet-telemetry.csv"',
                    "X-Data-Truncated": str(len(raw) > 10000).lower(),
                },
            )
        numeric = [r["value"] for r in rows if r.get("value") is not None and math.isfinite(r["value"])]
        comparable = metric is not None and len({r["unit"] for r in rows}) == 1
        return {
            "rows": rows,
            "truncated": len(raw) > 10000,
            "retention_days": 7,
            "sample_count": len(rows),
            "time_basis": "source_timestamp_else_received_at",
            "min": min(numeric) if comparable and numeric else None,
            "max": max(numeric) if comparable and numeric else None,
            "energy_total": None,
        }

    @app.get("/api/reports/records/{kind}")
    async def records_export(kind: str, who=Depends(user)):
        if kind not in {"incident", "work_order", "schedule"}:
            raise HTTPException(404)
        rows = [r for r in store.list(kind) if who.can_access(r["site_id"])]
        columns = [
            "id",
            "site_id",
            "title",
            "name",
            "status",
            "state",
            "assigned_to",
            "created_at",
            "description",
            "slots",
        ]
        return Response(
            csv_text(rows, columns),
            media_type="text/csv; charset=utf-8",
            headers={"Content-Disposition": f'attachment; filename="solar-fleet-{kind}.csv"'},
        )

    @app.get("/api/activity")
    async def activity(who=Depends(user)):
        return [r for r in store.audit_rows("operations") if r["site_id"] and who.can_access(r["site_id"])]
