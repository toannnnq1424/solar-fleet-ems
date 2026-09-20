"""Site-scoped management workflows. Configured intent is separate from device state."""

from __future__ import annotations

import hashlib
import html
import secrets
import uuid
from datetime import date, datetime
from typing import Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Response
from pydantic import Field, ValidationError, field_validator, model_validator

from .domain import Device, DeviceIdentity, Model, Role, SafetyError, Sample, utcnow
from .rules import RuleForm
from .telemetry import discrepancy, refresh_quality, select_source
from .workspaces import ScheduleForm, csv_text


class Scoped(Model):
    site_id: str
    name: str = Field(min_length=1, max_length=160)


class Customer(Scoped):
    group: str = Field(default="", max_length=100)
    contact: str = Field(default="", max_length=120)
    phone: str = Field(default="", max_length=50)
    email: str = Field(default="", max_length=254)
    notes: str = Field(default="", max_length=3000)


class Edge(Model):
    source: str
    target: str
    connection: Literal["AC", "DC", "RS485", "LAN", "WIRELESS", "CAN", "OTHER"]


class Topology(Scoped):
    edges: list[Edge] = Field(default_factory=list, max_length=300)
    notes: str = Field(default="", max_length=2000)

    @model_validator(mode="after")
    def unique(self):
        keys = [(e.source, e.target, e.connection) for e in self.edges]
        if any(a == b for a, b, _ in keys) or len(set(keys)) != len(keys):
            raise ValueError("duplicate edge or self loop")
        return self


class SourcePolicy(Scoped):
    priority: list[Literal["LOCAL", "SITE_AGENT", "VENDOR_CLOUD"]] = Field(min_length=1, max_length=3)
    max_age_seconds: int = Field(default=300, ge=5, le=300)
    max_skew_seconds: int = Field(default=5, ge=0, le=60)
    disagreement_percent: float = Field(default=5, ge=0, le=100, allow_inf_nan=False)
    notes: str = Field(default="", max_length=2000)

    @field_validator("priority")
    @classmethod
    def distinct(cls, value):
        if len(set(value)) != len(value):
            raise ValueError("duplicate priority")
        return value


class TariffSlot(Model):
    day: int = Field(ge=0, le=6)
    start: str = Field(pattern=r"^(?:[01]\d|2[0-3]):[0-5]\d$")
    end: str = Field(pattern=r"^(?:(?:[01]\d|2[0-3]):[0-5]\d|24:00)$")
    price: float = Field(ge=0, le=1_000_000, allow_inf_nan=False)


class Tariff(Scoped):
    currency: Literal["VND", "USD", "EUR"] = "VND"
    effective_from: date
    import_per_kwh: float = Field(ge=0, le=1_000_000, allow_inf_nan=False)
    export_per_kwh: float = Field(default=0, ge=0, le=1_000_000, allow_inf_nan=False)
    carbon_kg_per_kwh: float | None = Field(default=None, ge=0, le=10, allow_inf_nan=False)
    reference: str = Field(min_length=1, max_length=500)
    slots: list[TariffSlot] = Field(default_factory=list, max_length=168)

    @model_validator(mode="after")
    def no_overlap(self):
        ordered = sorted(self.slots, key=lambda s: (s.day, s.start))
        if any(s.start >= s.end for s in ordered):
            raise ValueError("split overnight tariff at midnight")
        if any(a.day == b.day and a.end > b.start for a, b in zip(ordered, ordered[1:])):
            raise ValueError("overlapping tariff")
        return self


class MaintenancePlan(Scoped):
    device_id: str | None = None
    interval_days: int = Field(ge=1, le=3650)
    next_due: date
    instructions: str = Field(min_length=1, max_length=4000)
    severity: Literal["critical", "high", "medium", "low"] = "medium"
    enabled: bool = True


class NetworkProfile(Scoped):
    device_id: str
    connection: Literal["Ethernet", "Wi-Fi", "4G", "RS485", "Modbus TCP", "CAN"]
    address: str = Field(default="", max_length=200)
    port: int | None = Field(default=None, ge=1, le=65535)
    slave_id: int | None = Field(default=None, ge=1, le=247)
    baud: Literal[1200, 2400, 4800, 9600, 19200, 38400, 57600, 115200] = 9600
    parity: Literal["none", "even", "odd"] = "none"
    dhcp: bool = True
    notes: str = Field(default="", max_length=2000)


class FirmwareRequest(Scoped):
    device_id: str
    target_version: str = Field(min_length=1, max_length=80)
    sha256: str = Field(pattern=r"^[a-fA-F0-9]{64}$")
    release_reference: str = Field(min_length=1, max_length=500)
    maintenance_window: datetime
    notes: str = Field(default="", max_length=2000)

    @field_validator("maintenance_window")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("timezone required")
        return value


class NotificationPolicy(Scoped):
    minimum_severity: Literal["critical", "high", "medium", "low"] = "high"
    escalation_minutes: int = Field(default=30, ge=1, le=10080)
    channel: Literal["in_app", "email", "sms", "zalo", "webhook"] = "in_app"
    destination: str = Field(default="", max_length=300)
    enabled: bool = True


class Document(Scoped):
    category: Literal["manual", "installation", "handover", "evidence", "other"] = "other"
    reference: str = Field(min_length=1, max_length=1000)
    sha256: str = Field(default="", pattern=r"^(?:[a-fA-F0-9]{64})?$")
    notes: str = Field(default="", max_length=4000)


MODELS = {
    "customer": Customer,
    "topology": Topology,
    "source_policy": SourcePolicy,
    "tariff": Tariff,
    "maintenance_plan": MaintenancePlan,
    "network_profile": NetworkProfile,
    "firmware_request": FirmwareRequest,
    "notification_policy": NotificationPolicy,
    "document": Document,
}
TECHNICAL = {"topology", "source_policy", "network_profile", "firmware_request"}


class SaveEntity(Model):
    id: str | None = None
    revision: int | None = Field(default=None, ge=1)
    data: dict


class Revision(Model):
    revision: int = Field(ge=1)


class Asset(Scoped):
    vendor: str = Field(min_length=1, max_length=80)
    serial: str = Field(min_length=1, max_length=100)
    model: str = Field(default="", max_length=120)
    type: Literal[
        "INVERTER",
        "BATTERY",
        "LOGGER",
        "METER",
        "CT",
        "UPS",
        "ATS",
        "GENERATOR",
        "EV_CHARGER",
        "LOAD",
        "OTHER",
    ]


class AgentEnrollment(Scoped):
    device_ids: list[str] = Field(min_length=1, max_length=100)


class Handover(Model):
    site_id: str
    inspector_name: str = Field(min_length=1, max_length=120)
    customer_name: str = Field(min_length=1, max_length=120)
    acknowledgement: bool
    notes: str = Field(default="", max_length=4000)


def install_management(app, controller, user, admin):
    store = controller.store

    def access(site_id, who):
        if not who.can_access(site_id):
            raise HTTPException(403, "site_access_denied")
        row = store.get("site", site_id)
        if row is None:
            raise HTTPException(404, "site_not_found")
        return {**row, **(store.get("site_profile", site_id) or {})}

    def operator(who=Depends(user)):
        if who.role == Role.VIEWER:
            raise HTTPException(403, "operator_required")
        return who

    def technical(who):
        if who.role not in {Role.INSTALLER, Role.ENGINEER}:
            raise HTTPException(403, "technical_role_required")

    def scoped_device(device_id, site_id):
        if controller.device(device_id).site_id != site_id:
            raise SafetyError("device_site_mismatch")

    def audit(event, row, who):
        store.audit(
            "operations",
            {"event": event, "id": row["id"], "operator": who.id, "revision": row.get("revision")},
            row["site_id"],
        )

    @app.get("/api/workbench")
    async def workbench(who=Depends(user)):
        app.state.operations_runtime.rollouts()
        kinds = [*MODELS, "agent", "handover", "rollout", "notification", "rule_monitor"]
        result = {
            k: [
                r
                for r in store.list(k)
                if all(who.can_access(id) for id in r.get("site_ids", [r["site_id"]]))
            ]
            for k in kinds
        }
        for agent in result["agent"]:
            agent.pop("token_hash", None)
        return result

    @app.post("/api/workbench/{kind}")
    async def save(kind: str, body: SaveEntity, who=Depends(operator)):
        if kind not in MODELS:
            raise HTTPException(404)
        if kind in TECHNICAL:
            technical(who)
        try:
            data = MODELS[kind].model_validate(body.data)
        except ValidationError:
            raise SafetyError("management_fields_invalid") from None
        site = access(data.site_id, who)
        if kind == "tariff":
            try:
                ZoneInfo(site.get("timezone") or "")
            except (ValueError, KeyError):
                raise SafetyError("site_timezone_required") from None
        if getattr(data, "device_id", None):
            scoped_device(data.device_id, data.site_id)
        if kind == "topology":
            for edge in data.edges:
                scoped_device(edge.source, data.site_id)
                scoped_device(edge.target, data.site_id)
        with store.transaction():
            old = store.get(kind, body.id) if body.id else None
            if body.id and not old:
                raise HTTPException(404)
            if old:
                access(old["site_id"], who)
                if old["site_id"] != data.site_id or old["revision"] != body.revision:
                    raise SafetyError("record_changed_reload")
            if kind in {"topology", "source_policy", "notification_policy"} and any(
                r["site_id"] == data.site_id and not r.get("archived") and r["id"] != body.id
                for r in store.list(kind)
            ):
                raise SafetyError("site_configuration_already_exists")
            now = utcnow().isoformat()
            row = {
                **data.model_dump(mode="json"),
                "id": body.id or uuid.uuid4().hex,
                "revision": (old or {}).get("revision", 0) + 1,
                "archived": False,
                "created_at": (old or {}).get("created_at", now),
                "updated_at": now,
                "updated_by": who.id,
            }
            if kind in {"network_profile", "firmware_request"}:
                row.update(state="AWAITING_DEVICE_CONTRACT", applied_to_device=False)
            if kind == "notification_policy":
                row["delivery_state"] = "READY" if data.channel == "in_app" else "PROVIDER_REQUIRED"
            store.put(kind, row["id"], row)
            audit(kind + "_saved", row, who)
        return row

    @app.post("/api/workbench/{kind}/{id}/archive")
    async def archive(kind: str, id: str, body: Revision, who=Depends(operator)):
        if kind not in MODELS:
            raise HTTPException(404)
        if kind in TECHNICAL:
            technical(who)
        with store.transaction():
            row = store.get(kind, id)
            if not row:
                raise HTTPException(404)
            access(row["site_id"], who)
            if row["revision"] != body.revision:
                raise SafetyError("record_changed_reload")
            row.update(archived=True, revision=row["revision"] + 1, updated_at=utcnow().isoformat())
            store.put(kind, id, row)
            audit(kind + "_archived", row, who)
        return row

    @app.post("/api/assets", status_code=201)
    async def register_asset(body: Asset, who=Depends(operator)):
        technical(who)
        access(body.site_id, who)
        # A manual asset cannot replace a discovered device or create a second physical command queue.
        if any(
            d["identity"]["vendor"].casefold() == body.vendor.casefold() and d["vendor_id"] == body.serial
            for d in store.list("device")
        ):
            raise SafetyError("device_already_registered")
        device = Device(
            id=uuid.uuid4().hex,
            site_id=body.site_id,
            name=body.name,
            vendor_id=body.serial,
            integration_id="MANUAL",
            type=body.type,
            identity=DeviceIdentity(vendor=body.vendor, model=body.model or None),
            metadata={"identity_state": "UNVERIFIED", "registration": "MANUAL"},
        )
        with store.transaction():
            store.put("device", device.id, device.model_dump(mode="json"))
            audit("asset_registered", device.model_dump(), who)
        return device

    @app.post("/api/agents", status_code=201)
    async def enroll(body: AgentEnrollment, who=Depends(admin)):
        access(body.site_id, who)
        for id in body.device_ids:
            scoped_device(id, body.site_id)
        secret = secrets.token_urlsafe(40)
        row = {
            **body.model_dump(),
            "id": uuid.uuid4().hex,
            "enabled": True,
            "last_seen": None,
            "last_sequence": 0,
            "token_hash": hashlib.sha256(secret.encode()).hexdigest(),
            "created_at": utcnow().isoformat(),
        }
        with store.transaction():
            store.put("agent", row["id"], row)
            audit("agent_enrolled", row, who)
        return {**{k: v for k, v in row.items() if k != "token_hash"}, "token": secret}

    @app.post("/api/agents/{id}/revoke")
    async def revoke(id: str, who=Depends(admin)):
        row = store.get("agent", id)
        if not row:
            raise HTTPException(404)
        access(row["site_id"], who)
        row.update(enabled=False, token_hash="")
        with store.transaction():
            store.put("agent", id, row)
            audit("agent_revoked", row, who)
        return {"ok": True}

    @app.post("/api/schedules/{id}/edit")
    async def edit_schedule(id: str, body: SaveEntity, who=Depends(operator)):
        try:
            data = ScheduleForm.model_validate(body.data)
        except ValidationError:
            raise SafetyError("schedule_invalid") from None
        access(data.site_id, who)
        with store.transaction():
            old = store.get("schedule", id)
            if not old:
                raise HTTPException(404)
            access(old["site_id"], who)
            if old["site_id"] != data.site_id or old.get("revision", 1) != body.revision:
                raise SafetyError("record_changed_reload")
            store.put("schedule_version", id + ":" + str(old.get("revision", 1)), old)
            row = {
                **old,
                **data.model_dump(),
                "revision": old.get("revision", 1) + 1,
                "state": "DRAFT",
                "updated_at": utcnow().isoformat(),
            }
            store.put("schedule", id, row)
            audit("schedule_edited", row, who)
        return row

    @app.get("/api/schedules/{id}/versions")
    async def schedule_versions(id: str, who=Depends(user)):
        row = store.get("schedule", id)
        if not row:
            raise HTTPException(404)
        access(row["site_id"], who)
        return [r for r in store.list("schedule_version") if r["id"] == id] + [row]

    @app.post("/api/rules/{id}/edit")
    async def edit_rule(id: str, body: SaveEntity, who=Depends(operator)):
        try:
            data = RuleForm.model_validate(body.data)
        except ValidationError:
            raise SafetyError("rule_invalid") from None
        access(data.site_id, who)
        for item in [*data.conditions, *data.actions]:
            scoped_device(item.device_id, data.site_id)
        for action in data.actions:
            controller.capability(controller.device(action.device_id), action.intent)
        with store.transaction():
            old = store.get("rule", id)
            if not old:
                raise HTTPException(404)
            access(old["site_id"], who)
            if old["site_id"] != data.site_id or old.get("revision", 1) != body.revision:
                raise SafetyError("record_changed_reload")
            monitor = store.get("rule_monitor", id)
            if monitor:
                monitor.update(enabled=False, since=None)
                store.put("rule_monitor", id, monitor)
            row = {**old, **data.model_dump(), "revision": old.get("revision", 1) + 1, "state": "DRAFT"}
            store.put("rule", id, row)
            audit("rule_edited", row, who)
        return row

    @app.get("/api/sites/{id}/diagnostics")
    async def diagnostics(id: str, who=Depends(user)):
        access(id, who)
        rows = []
        for raw in store.list("device"):
            if raw["site_id"] != id:
                continue
            device = controller.device(raw["id"])
            readings = controller.latest(device)["samples"]
            fresh = [s for s in readings if not s.get("stale", True)]
            commands = [
                c for c in store.commands() if c["device_id"] == device.id and c["status"] == "TIMEOUT"
            ]
            rows.append(
                {
                    "device_id": device.id,
                    "name": device.name or device.vendor_id,
                    "online": device.online,
                    "last_seen": device.last_seen,
                    "sample_count": len(readings),
                    "fresh_samples": len(fresh),
                    "verified_samples": sum(s["quality"] == "GOOD" for s in fresh),
                    "unresolved_commands": len(commands),
                    "next_step": "RECONCILE_COMMAND"
                    if commands
                    else "CHECK_CONNECTION"
                    if not fresh
                    else "VERIFY_MAPPING"
                    if not any(s["quality"] == "GOOD" for s in fresh)
                    else "MONITOR",
                }
            )
        return {"site_id": id, "checked_at": utcnow(), "method": "STORED_DATA_REVIEW", "devices": rows}

    @app.get("/api/sites/{id}/energy")
    async def energy(id: str, who=Depends(user)):
        access(id, who)
        # Explicit meter bindings prevent inverter/meter double counting. One topology annotation per metric.
        topology = next(
            (r for r in store.list("topology") if r["site_id"] == id and not r.get("archived")), None
        )
        policy = next(
            (r for r in store.list("source_policy") if r["site_id"] == id and not r.get("archived")), {}
        )
        metrics = {}
        for metric in (
            "pv_w",
            "load_w",
            "grid_import_w",
            "grid_export_w",
            "battery_charge_w",
            "battery_discharge_w",
            "soc_pct",
        ):
            candidates = []
            for d in store.list("device"):
                if d["site_id"] == id:
                    candidates += [
                        Sample.model_validate(s)
                        for s in controller.latest(controller.device(d["id"]))["samples"]
                        if s["metric"] == metric and s.get("unit") == ("%" if metric == "soc_pct" else "W")
                    ]
            targets = {s.device_id for s in candidates}
            age = policy.get("max_age_seconds", 300)
            selected = (
                select_source(candidates, age, priority_order=policy.get("priority"))
                if len(targets) == 1
                else None
            )
            disagreement = False
            if selected:
                for candidate in candidates:
                    candidate = refresh_quality(candidate, age)
                    if candidate.binding_id == selected.binding_id or candidate.unit != selected.unit:
                        continue
                    tolerance = abs(selected.value) * policy.get("disagreement_percent", 5) / 100
                    disagreement |= (
                        discrepancy(selected, candidate, tolerance, policy.get("max_skew_seconds", 5)) is True
                    )
                if disagreement:
                    selected = None
            metrics[metric] = {
                "value": selected.value if selected else None,
                "unit": selected.unit if selected else None,
                "device_id": selected.device_id if selected else None,
                "reason": "SOURCE_DISAGREEMENT"
                if disagreement
                else "MEASURED"
                if selected
                else "METER_MAPPING_REQUIRED"
                if len(targets) > 1
                else "VERIFIED_DATA_REQUIRED",
            }
        return {"metrics": metrics, "topology": topology, "generated_at": utcnow(), "summed": False}

    def checklist(site_id):
        latest = {}
        for r in sorted(store.list("commissioning"), key=lambda r: r["created_at"]):
            if r["site_id"] == site_id:
                latest[r["check"]] = r
        return [
            {"check": check, **latest.get(check, {"result": "pending", "evidence": ""})}
            for check in ("topology", "meter_ct", "power_direction", "battery", "control_readback", "alarms")
        ]

    @app.get("/api/sites/{id}/handover")
    async def handover_status(id: str, who=Depends(user)):
        access(id, who)
        checks = checklist(id)
        incidents = [
            r["id"]
            for r in store.list("incident")
            if r["site_id"] == id
            and r["severity"] == "critical"
            and r["status"] not in {"closed", "resolved"}
        ]
        return {
            "checks": checks,
            "blocking_incidents": incidents,
            "ready": all(c["result"] == "pass" for c in checks) and not incidents,
        }

    @app.post("/api/handovers", status_code=201)
    async def record_handover(body: Handover, who=Depends(operator)):
        technical(who)
        access(body.site_id, who)
        status = await handover_status(body.site_id, who)
        if not status["ready"] or not body.acknowledgement:
            raise SafetyError("handover_checks_incomplete")
        row = {
            **body.model_dump(),
            **status,
            "id": uuid.uuid4().hex,
            "signed_by_user": who.id,
            "created_at": utcnow().isoformat(),
            "signature_type": "TYPED_ATTESTATION_NOT_DIGITAL_SIGNATURE",
            "unlocks_control": False,
        }
        with store.transaction():
            store.put("handover", row["id"], row)
            audit("handover_recorded", row, who)
        return row

    @app.get("/api/sites/{id}/report")
    async def site_report(id: str, format: Literal["json", "csv", "html"] = "json", who=Depends(user)):
        site = access(id, who)
        checks = checklist(id)
        jobs = [r for r in store.list("work_order") if r["site_id"] == id]
        incidents = [r for r in store.list("incident") if r["site_id"] == id]
        body = {
            "site": site,
            "generated_at": utcnow().isoformat(),
            "checks": checks,
            "incidents": incidents,
            "work_orders": jobs,
            "handovers": [r for r in store.list("handover") if r["site_id"] == id],
            "method": "MANAGEMENT_RECORDS",
        }
        if format == "json":
            return body
        if format == "csv":
            return Response(
                csv_text(
                    incidents + jobs,
                    ["id", "title", "status", "severity", "created_at", "assigned_to", "description"],
                ),
                media_type="text/csv; charset=utf-8",
                headers={"Content-Disposition": 'attachment; filename="site-report.csv"'},
            )

        def esc(value):
            return html.escape(str(value))

        sections = ""
        for title, rows in (
            ("Nghiệm thu / Commissioning", checks),
            ("Sự cố / Incidents", incidents),
            ("Bảo trì / Maintenance", jobs),
        ):
            sections += (
                "<h2>"
                + title
                + "</h2><table><tbody>"
                + "".join(
                    "<tr><th>"
                    + esc(r.get("title", r.get("check")))
                    + "</th><td>"
                    + esc(r.get("status", r.get("result")))
                    + "</td><td>"
                    + esc(r.get("description", r.get("evidence", "")))
                    + "</td></tr>"
                    for r in rows
                )
                + "</tbody></table>"
            )
        markup = (
            '<!doctype html><html lang="vi"><meta charset="utf-8"><title>Solar Fleet Report</title><link rel="stylesheet" href="/static/app.css"><main class="report-document"><h1>'
            + esc(site["name"])
            + "</h1><p>Báo cáo vận hành / Operations report · "
            + esc(body["generated_at"])
            + "</p><p>In / Print → Save as PDF</p>"
            + sections
            + "<p>Hồ sơ quản lý; chữ ký tên nhập không phải chữ ký số. / Management records; typed names are not digital signatures.</p></main></html>"
        )
        return Response(markup, media_type="text/html")

    @app.post("/api/notifications/{id}/read")
    async def read_notification(id: str, who=Depends(user)):
        row = store.get("notification", id)
        if not row:
            raise HTTPException(404)
        access(row["site_id"], who)
        with store.transaction():
            row = store.get("notification", id)
            row["read_by"] = sorted(set(row.get("read_by", []) + [who.id]))
            store.put("notification", id, row)
        return {"ok": True}
