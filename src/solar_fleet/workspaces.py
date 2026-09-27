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
from pydantic import ConfigDict, Field, SecretStr, ValidationError, field_validator, model_validator

from .domain import Model, Role, SafetyError, Sample, utcnow
from .operational_views import OperationalViews, period_bounds
from .providers import PROVIDERS
from .rules import RuleForm, evaluate
from .security import create_user

WEEKDAYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")


class NotificationConfigForm(Model):
    smtp_host: str = Field(default="", max_length=253)
    smtp_port: int = Field(default=587, ge=1, le=65535)
    smtp_user: str = Field(default="", max_length=254)
    smtp_password: SecretStr | None = None
    smtp_tls: bool = True
    from_address: str = Field(default="", max_length=254)
    recipients_alarm: list[str] = Field(default_factory=list, max_length=100)
    recipients_report: list[str] = Field(default_factory=list, max_length=100)
    enabled: bool = False
    email_enabled: bool = False
    zalo_webhook: SecretStr | None = None
    telegram_bot_token: SecretStr | None = None
    telegram_chat_id: str = Field(default="", max_length=100)


class DeclaredSiteSpecs(Model):
    """User-declared inventory only; never a dispatch or billing configuration."""

    plant_type: Literal["ROOFTOP_CI", "RESIDENTIAL", "GROUND_MOUNT", "AGRIVOLTAICS"] | None = None
    battery_capacity_kwh: float | None = Field(default=None, ge=0, le=10_000_000, allow_inf_nan=False)
    grid_limit_kw: float | None = Field(default=None, ge=0, le=10_000_000, allow_inf_nan=False)
    tariff_type: Literal["TOU_INDUSTRIAL", "TOU_COMMERCIAL", "FLAT_RATE"] | None = None
    inverter_vendor: str | None = Field(default=None, min_length=1, max_length=80)


class SiteForm(Model):
    model_config = ConfigDict(extra="ignore")
    name: str = Field(min_length=1, max_length=160)
    customer: str = Field(default="", max_length=160)
    address: str = Field(default="", max_length=300)
    timezone: str = "Asia/Ho_Chi_Minh"
    capacity_kwp: float | None = Field(default=None, ge=0, le=10_000_000, allow_inf_nan=False)
    latitude: float | None = Field(default=None, ge=-90, le=90, allow_inf_nan=False)
    longitude: float | None = Field(default=None, ge=-180, le=180, allow_inf_nan=False)
    declared_specs: DeclaredSiteSpecs | None = None

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
    vendor: str | None = None
    category: str = "other"
    root_cause: str | None = None
    tags: list[str] = Field(default_factory=list)

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


class BatchAssessForm(Model):
    site_ids: list[str] = Field(min_length=1, max_length=100)
    intents: list[str] = Field(
        default_factory=lambda: [
            "set_zero_export",
            "set_reserve_soc",
            "set_grid_charge",
            "set_tou_schedule",
            "set_active_power_limit",
        ]
    )


class BatchDeployForm(Model):
    campaign_name: str = Field(min_length=1, max_length=160)
    site_ids: list[str] = Field(min_length=1, max_length=100)
    actions: list[dict] = Field(default_factory=list)
    dry_run: bool = True
    scheduled_at: str | None = None
    notes: str = Field(default="", max_length=2000)


class AdvancedRuleForm(Model):
    site_id: str
    name: str = Field(min_length=1, max_length=160)
    description: str = Field(default="", max_length=1000)
    trigger_type: str = Field(default="SCHEDULE", max_length=50)
    trigger_detail: str = Field(default="22:00 hàng ngày", max_length=160)
    condition_expr: str = Field(default="", max_length=250)
    action_detail: str = Field(default="Bật grid charge 5 kW tới 05:00", max_length=250)
    max_export_kw: float = Field(default=0.0, ge=0.0)
    protected_loads: list[str] = Field(
        default_factory=lambda: ["Tải văn phòng", "Hệ thống an ninh", "Server/IT"]
    )
    is_active: bool = True
    dry_run: bool = False


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
    views = OperationalViews(controller)

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
            site = store.get("site", id) or {"id": id}
            site.update(body.model_dump(exclude_unset=True))
            store.put("site", id, site)
            store.put(
                "site_profile",
                id,
                {**(store.get("site_profile", id) or {}), **body.model_dump(exclude_unset=True)},
            )
            store.audit("operations", {"event": "site_profile_updated", "operator": who.id}, id)
        return site

    @app.get("/api/sites/{id}/overview-summary")
    async def site_overview_summary(id: str, who=Depends(user)):
        site_access(id, who)
        result = views.overview(id)
        weather = await site_weather(id, who)
        current = weather.get("current") or {}
        forecast_from_weather = [
            {
                "hour": e.get("hour", ""),
                "temperature_c": e.get("temperature_c"),
                "irradiance_wm2": e.get("ghi_wm2"),
            }
            for e in weather.get("hourly_forecast", [])
        ]
        forecast_24h = (
            forecast_from_weather[:24]
            if len(forecast_from_weather) >= 24
            else result["weather"].get("forecast_24h", [])
        )
        hourly_forecast = weather.get("hourly_forecast") or result["weather"].get("hourly_forecast", [])
        result["weather"] = {
            **result["weather"],
            **current,
            "condition": current.get("description", "UNKNOWN"),
            "hourly_forecast": hourly_forecast,
            "forecast_24h": forecast_24h,
            "meta": weather.get("meta"),
            "status": weather.get("status"),
        }
        return result

    @app.post("/api/sites/{id}/quick-preset")
    async def apply_site_quick_preset(id: str, body: dict, who=Depends(operator)):
        site_access(id, who)
        raise SafetyError("select_device_and_preview_intent_required")

    @app.get("/api/sites/{id}/telemetry-timeseries")
    async def site_telemetry_timeseries(
        id: str, metric: str = "pv_power", period: str = "today", who=Depends(user)
    ):
        site_access(id, who)
        return views.series(id, metric, period)

    @app.get("/api/vendor-registers/{brand}")
    async def get_vendor_registers_endpoint(brand: str, model: str | None = None, who=Depends(user)):
        from .vendor_registers import get_vendor_registers as fetch_registers
        return fetch_registers(brand, model=model)

    @app.get("/api/sites/{id}/diagnostics-checklist")
    async def get_site_diagnostics(id: str, who=Depends(user)):
        site = site_access(id, who)
        rows = [
            r
            for r in store.list("commissioning")
            if r.get("site_id") == id and r.get("method") == "MANUAL_ATTESTATION"
        ]
        steps = []
        for key in ("topology", "meter_ct", "power_direction", "battery", "control_readback", "alarms"):
            latest = max(
                (r for r in rows if r.get("check") == key), key=lambda r: r["created_at"], default={}
            )
            steps.append(
                {
                    "id": key,
                    "title": key,
                    "status": latest.get("result", "pending"),
                    "evidence": latest.get("evidence"),
                    "measured": None,
                    "recorded_at": latest.get("created_at"),
                }
            )
        status = (
            "ATTESTED"
            if all(s["status"] == "pass" for s in steps)
            else "INCOMPLETE"
            if rows
            else "NOT_TESTED"
        )
        return {
            "site_id": id,
            "site_name": site.get("name"),
            "standard": None,
            "overall_status": status,
            "steps": steps,
            "records": rows,
            "certificate": None,
            "unlocks_control": False,
        }

    @app.post("/api/sites/{id}/diagnostics-checklist")
    async def update_site_diagnostics(id: str, body: CommissionCheck, who=Depends(operator)):
        site_access(id, who)
        if body.site_id != id:
            raise HTTPException(422, "site_identity_mismatch")
        return await commissioning(body, who)

    @app.get("/api/sites/{id}/network-status")
    async def get_site_network_status(id: str, who=Depends(user)):
        site_access(id, who)
        agents = [
            {k: a.get(k) for k in ("id", "name", "site_id", "enabled", "last_heartbeat", "last_seen")}
            for a in store.list("agent")
            if a.get("site_id") == id
        ]
        profiles = [
            r for r in store.list("network_profile") if r.get("site_id") == id and not r.get("archived")
        ]
        return {
            "site_id": id,
            "agents": agents,
            "profiles": profiles,
            "local_agent": {
                "enrolled": bool(agents),
                "connected": None,
                "last_heartbeat": max(
                    (a.get("last_heartbeat") for a in agents if a.get("last_heartbeat")), default=None
                ),
                "latency_ms": None,
            },
            "rs485_bus": {"baudrate": None, "parity": None, "termination_resistor_ohm": None},
            "solarman_logger": {"protocol": None, "serial": None},
            "status": "OBSERVATIONS_REQUIRED",
        }

    @app.get("/api/fleet/plants-benchmarking")
    async def fleet_plants_benchmarking(who=Depends(user)):
        rows = []
        for raw in store.list("site"):
            if not who.can_access(raw["id"]):
                continue
            site = views.site(raw["id"])
            total = views.energy(site["id"], *period_bounds(site, "today"))["pv"]["wh"]
            capacity = site.get("capacity_kwp")
            yield_kwh = views.kw(total)
            rows.append(
                {
                    **site,
                    "today_yield_kwh": yield_kwh,
                    "specific_yield_kwh_per_kwp": yield_kwh / capacity
                    if yield_kwh is not None and capacity
                    else None,
                    "performance_ratio_pct": None,
                    "status": "IRRADIANCE_REFERENCE_REQUIRED",
                }
            )
        valid = [r["specific_yield_kwh_per_kwp"] for r in rows if r["specific_yield_kwh_per_kwp"] is not None]
        return {
            "total_plants": len(rows),
            "fleet_avg_pr_pct": None,
            "fleet_avg_specific_yield": sum(valid) / len(valid) if valid else None,
            "plants": rows,
            "top_performers": [],
            "underperformers": [],
        }

    @app.get("/api/fleet/regions-summary")
    async def fleet_regions_summary(who=Depends(user)):
        regions = {
            key: {
                "name": key,
                "plants_count": 0,
                "total_kwp": 0,
                "today_kwh": None,
                "online_pct": None,
                "sites": [],
            }
            for key in ("north", "central", "south", "unknown")
        }
        for raw in store.list("site"):
            if not who.can_access(raw["id"]):
                continue
            site = views.site(raw["id"])
            lat = site.get("latitude")
            key = (
                "unknown" if lat is None else "north" if lat >= 19 else "central" if lat >= 13.5 else "south"
            )
            region = regions[key]
            region["sites"].append(site)
            region["plants_count"] += 1
            region["total_kwp"] += site.get("capacity_kwp") or 0
        return {
            "total_sites": sum(r["plants_count"] for r in regions.values()),
            "regions": regions,
            "method": "LATITUDE_BANDS_NOT_ADMINISTRATIVE_REGIONS",
        }

    @app.get("/api/fleet/map-data")
    async def fleet_map_data(who=Depends(user)):
        return views.map_data([s for s in store.list("site") if who.can_access(s["id"])])

    @app.get("/api/fleet/topology-summary")
    async def fleet_topology_summary(who=Depends(user)):
        sites = [views.site(s["id"]) for s in store.list("site") if who.can_access(s["id"])]
        devices = [d for d in controller.devices() if who.can_access(d.site_id)]
        return {
            "total_sites": len(sites),
            "total_inverters": sum(d.type == "INVERTER" for d in devices),
            "total_bess_systems": sum(d.type == "BATTERY" for d in devices),
            "total_smart_meters": sum(d.type == "METER" for d in devices),
            "sites": [
                {
                    **s,
                    "grid_type": "UNKNOWN",
                    "inverters_count": sum(d.type == "INVERTER" and d.site_id == s["id"] for d in devices),
                    "status": "CONFIGURATION_ONLY",
                }
                for s in sites
            ],
        }

    @app.get("/api/sites/{site_id}/topology-detail")
    async def site_topology_detail(site_id: str, who=Depends(user)):
        site_access(site_id, who)
        return views.topology(site_id)

    @app.get("/api/fleet/devices-overview")
    async def fleet_devices_overview(site_id: str | None = None, who=Depends(user)):
        if site_id:
            site_access(site_id, who)
        rows = [views.equipment(d) for d in controller.devices()
                if who.can_access(d.site_id) and (not site_id or d.site_id == site_id)]
        return {
            "devices": rows,
            "summary": {
                "total_devices": len(rows),
                "online_count": sum(d["online"] for d in rows),
                "offline_count": sum(d["status"] == "OFFLINE" for d in rows),
                "unknown_count": sum(d["status"] == "UNKNOWN" for d in rows),
                "warning_count": 0,
                "commissioned_count": sum(d["commissioned"] for d in rows),
                "by_type": {
                    key: sum(d["type"] == kind for d in rows)
                    for key, kind in [
                        ("inverters", "INVERTER"),
                        ("batteries", "BATTERY"),
                        ("meters", "METER"),
                        ("loggers", "LOGGER"),
                        ("weather", "WEATHER"),
                    ]
                },
            },
        }

    @app.post("/api/devices/{id}/modbus-inspect")
    async def device_modbus_inspect(id: str, payload: dict, who=Depends(user)):
        device = controller.device(id)
        site_access(device.site_id, who)
        raise SafetyError("local_register_reader_not_connected")

    @app.get("/api/devices/{id}/native-config-groups")
    async def device_native_config_groups(id: str, who=Depends(user)):
        device = controller.device(id)
        site_access(device.site_id, who)
        description = controller.registry.describe(device.identity.vendor)
        return {
            "device_id": id,
            "groups": [
                {
                    **g,
                    "key": g["id"],
                    "title": g["label"],
                    "fields": g.get("native_fields", []),
                    "locked": True,
                    "lock_reason": g.get("reason"),
                }
                for g in description["groups"]
            ],
        }

    @app.get("/api/control/device-state/{device_id}")
    async def get_control_device_state(device_id: str, who=Depends(user)):
        device = controller.device(device_id)
        site_access(device.site_id, who)
        return views.control_state(device, who)

    @app.post("/api/control/execute")
    async def execute_control_command(payload: dict, who=Depends(operator)):
        # All UI entry points share the exact capability/identity/freshness engine.
        device = controller.device(payload.get("device_id", ""))
        site_access(device.site_id, who)
        if payload.get("plan_id"):
            return await controller.engine.confirm(
                who, payload["plan_id"], payload.get("digest", ""), payload.get("idempotency_key", "")
            )
        return await controller.engine.preview(
            who, device.id, payload.get("intent", ""), payload.get("parameters", {})
        )

    @app.get("/api/control/journal/{device_id}")
    async def get_control_device_journal(device_id: str, who=Depends(user)):
        device = controller.device(device_id)
        site_access(device.site_id, who)
        rows = [
            r
            for r in store.audit_rows("control")
            if r["site_id"] == device.site_id and r["body"].get("device_id") == device.id
        ]
        return {
            "device_id": device_id,
            "journal": [
                {
                    "time": r["body"].get("timestamp"),
                    "actor": r["body"].get("operator"),
                    "action": r["body"].get("event"),
                    "status": r["body"].get("status", "RECORDED"),
                    "details": r["body"],
                }
                for r in rows
            ],
        }

    @app.post("/api/control/batch-dispatch")
    async def batch_dispatch_control(payload: dict, who=Depends(operator)):
        ids = payload.get("device_ids", [])
        if not ids or len(ids) > 100:
            raise SafetyError("invalid_device_selection")
        for id in ids:
            site_access(controller.device(id).site_id, who)
        raise SafetyError("use_rollout_preview_and_confirm")

    @app.get("/api/control/safety-quarantine")
    async def get_safety_quarantine(who=Depends(user)):
        rows = [c for c in store.commands() if who.can_access(c["site_id"]) and c["status"] == "TIMEOUT"]
        return {
            "quarantined_count": len(rows),
            "devices": rows,
            "safety_policy": {"mode": "UNKNOWN_OUTCOME_BLOCKS_RETRY", "closed_loop_readback": True},
        }

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

    @app.get("/api/tariffs/evn-current")
    async def get_evn_tariffs(who=Depends(user)):
        rows = [r for r in store.list("tariff") if who.can_access(r["site_id"]) and not r.get("archived")]
        return {
            "source": "CONFIGURED_SITE_TARIFFS",
            "rates": {},
            "windows": {},
            "tariffs": rows,
            "status": "SITE_AND_EFFECTIVE_DATE_REQUIRED",
        }

    @app.get("/api/schedules/weekly-plan/{site_id}")
    async def get_weekly_plan(site_id: str, who=Depends(user)):
        site = site_access(site_id, who)
        row = store.get("weekly_schedule", site_id) or {}
        return {
            **row,
            "site_id": site_id,
            "site_name": site["name"],
            "ems_mode": "DRAFT",
            "safety_backup_mode": "UNKNOWN",
            "current_work_mode": "UNKNOWN",
            "schedule_matrix": row.get("schedule_matrix", {day: [] for day in WEEKDAYS}),
            "zero_export": {},
            "load_priority": [],
            "reserve_soc_by_tariff": {},
            "generator_trigger": {},
            "backup_strategy": {},
            "impact_projection_7d": {},
            "hardware_accepted": False,
            "can_deploy_physical": False,
        }

    @app.post("/api/schedules/weekly-plan/{site_id}")
    async def save_weekly_plan(site_id: str, payload: dict, who=Depends(operator)):
        site = site_access(site_id, who)
        matrix = payload.get("schedule_matrix", {})
        if not isinstance(matrix, dict) or set(matrix) != set(WEEKDAYS):
            raise SafetyError("seven_weekdays_required")
        slots = []
        for day, key in enumerate(WEEKDAYS):
            if not isinstance(matrix[key], list) or any(not isinstance(s, dict) for s in matrix[key]):
                raise HTTPException(422, "invalid_weekday_slots")
            for s in matrix[key]:
                slots.append(
                    {
                        "day": day,
                        "start": s.get("start"),
                        "end": s.get("end"),
                        "mode": str(s.get("action", "")).lower(),
                        "target_soc": s.get("target_soc"),
                        "power_kw": s.get("max_power_kw"),
                    }
                )
        try:
            form = ScheduleForm.model_validate(
                {"site_id": site_id, "name": payload.get("name") or site["name"], "slots": slots}
            )
        except ValidationError:
            raise HTTPException(422, "invalid_schedule_slots") from None
        with store.transaction():
            row = await save_schedule(form, who)
            view = {
                "site_id": site_id,
                "schedule_id": row["id"],
                "schedule_matrix": matrix,
                "updated_at": row["created_at"],
                "state": "DRAFT",
            }
            store.put("weekly_schedule", site_id, view)
        return {"ok": True, **view}

    @app.post("/api/schedules/deploy-to-hardware")
    async def deploy_schedule_to_hardware(payload: dict, who=Depends(operator)):
        site_access(payload.get("site_id", ""), who)
        raise SafetyError("schedule_compilation_and_rollout_confirmation_required")

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

    @app.post("/api/ems/batch-assess")
    async def ems_batch_assess(body: BatchAssessForm, who=Depends(user)):
        rows, vendors = [], {}
        intents = [i.upper() for i in body.intents]
        for id in dict.fromkeys(body.site_ids):
            site = site_access(id, who)
            devices = views.devices(id)
            targets = []
            for d in devices:
                for intent in intents:
                    try:
                        cap = controller.capability(d, intent)
                        targets.append(
                            {
                                "device_id": d.id,
                                "intent": intent,
                                "state": cap.state,
                                "semantic_match": cap.semantic_match,
                                "reason": cap.reason,
                            }
                        )
                    except SafetyError:
                        targets.append(
                            {
                                "device_id": d.id,
                                "intent": intent,
                                "state": "UNKNOWN",
                                "reason": "intent_unknown",
                            }
                        )
                vendors[d.identity.vendor] = {
                    "vendor": d.identity.vendor,
                    "support_level": "Per-device assessment required",
                }
            exact = bool(targets) and all(
                t["state"] == "VERIFIED" and t.get("semantic_match") == "exact" for t in targets
            )
            rows.append(
                {
                    "site_id": id,
                    "name": site["name"],
                    "vendor": ", ".join(sorted({d.identity.vendor for d in devices})),
                    "capacity_kwp": site.get("capacity_kwp"),
                    "status": "Exact" if exact else "Requires review",
                    "detail": "CAPABILITY_ASSESSMENT_ONLY",
                    "targets": targets,
                }
            )
        exact = sum(r["status"] == "Exact" for r in rows)
        return {
            "selected_count": len(rows),
            "total_sites": sum(who.can_access(s["id"]) for s in store.list("site")),
            "vendor_count": len(vendors),
            "total_capacity_kwp": sum(r["capacity_kwp"] or 0 for r in rows),
            "estimated_duration": None,
            "sites": rows,
            "vendor_breakdown": list(vendors.values()),
            "compatibility_summary": {
                "exact": exact,
                "partial": 0,
                "review": len(rows) - exact,
                "unsupported": 0,
                "label": "ASSESSMENT_ONLY",
            },
        }

    @app.post("/api/ems/batch-deploy")
    async def ems_batch_deploy(body: BatchDeployForm, who=Depends(operator)):
        for id in body.site_ids:
            site_access(id, who)
        raise SafetyError("use_rollout_preview_and_confirm")

    @app.get("/api/ems/batch-campaigns")
    async def ems_batch_campaigns(who=Depends(user)):
        return [
            r
            for r in store.list("rollout")
            if all(who.can_access(s) for s in r.get("site_ids", [])) and r.get("owner_id") == who.id
        ]

    @app.get("/api/ems/rules-advanced")
    async def ems_get_rules_advanced(who=Depends(user)):
        return [r for r in store.list("advanced_rule") if who.can_access(r.get("site_id", "*"))]

    @app.post("/api/ems/rules-advanced", status_code=201)
    async def ems_save_rule_advanced(body: AdvancedRuleForm, who=Depends(operator)):
        site_access(body.site_id, who)
        rule_id = uuid.uuid4().hex
        site_row = store.get("site", body.site_id) or {}
        row = {
            "id": rule_id,
            **body.model_dump(),
            "site_name": site_row.get("name", body.site_id),
            "status": "DRAFT",
            "is_active": False,
            "created_by": who.id,
            "created_at": utcnow().isoformat(),
            "last_run": "Chưa chạy",
        }
        with store.transaction():
            store.put("advanced_rule", rule_id, row)
            store.audit(
                "operations",
                {
                    "event": "advanced_rule_created",
                    "id": rule_id,
                    "name": body.name,
                    "operator": who.id,
                },
                body.site_id,
            )
        return row

    @app.post("/api/ems/rules-advanced/{id}/toggle")
    async def ems_toggle_rule_advanced(id: str, who=Depends(operator)):
        row = store.get("advanced_rule", id)
        if not row:
            raise HTTPException(404, "rule_not_found")
        site_access(row["site_id"], who)
        raise SafetyError("structured_rule_conditions_and_actions_required")

    @app.post("/api/ems/rules/{id}/simulate")
    async def ems_simulate_rule(id: str, who=Depends(user)):
        row = store.get("rule", id) or store.get("advanced_rule", id)
        if not row:
            raise HTTPException(404, "rule_not_found")
        site_access(row["site_id"], who)
        if store.get("rule", id):
            samples = [
                Sample.model_validate(s)
                for d in views.devices(row["site_id"])
                for s in controller.latest(d)["samples"]
            ]
            fields = {k: row[k] for k in RuleForm.model_fields if k in row}
            return {
                "rule_id": id,
                "simulation_mode": "DRY_RUN",
                "points": [],
                "result": evaluate(RuleForm.model_validate(fields), samples),
            }
        raise SafetyError("structured_rule_conditions_and_actions_required")

    @app.get("/api/ems/execution-logs")
    async def ems_execution_logs(who=Depends(user)):
        raw_rows = store.audit_rows("operations")
        filtered = []
        for idx, r in enumerate(raw_rows):
            site_id = r.get("site_id") or ""
            if site_id and not who.can_access(site_id):
                continue
            b = r.get("body", {})
            event = b.get("event", "")
            if site_id and event == "advanced_rule_executed":
                filtered.append(
                    {
                        "id": f"log_{r.get('seq', idx)}",
                        "time": b.get("timestamp"),
                        "rule_name": b.get("name", event),
                        "site_name": site_id,
                        "result": b.get("status", "UNKNOWN"),
                        "result_label": b.get("status", "UNKNOWN"),
                        "message": f"Sự kiện {event} thực hiện bởi {b.get('operator', 'system')}.",
                    }
                )
        return filtered

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

    # ==================================================================
    # G10: Weather & Solar Irradiance API (Open-Meteo, free, no key)
    # ==================================================================
    @app.get("/api/weather/{site_id}")
    async def site_weather(site_id: str, who=Depends(user)):
        """Fetch current weather and 48h GHI/DNI/DHI forecast for a site."""
        site_access(site_id, who)
        site = views.site(site_id)
        if not site:
            raise HTTPException(404, "site_not_found")
        lat = site.get("latitude")
        lon = site.get("longitude")
        if lat is None or lon is None:
            return {
                "status": "no_coordinates",
                "message": "Nhà máy chưa có tọa độ GPS. Cập nhật latitude/longitude trong cấu hình nhà máy.",
                "current": None,
                "hourly_forecast": [],
            }
        try:
            from .weather import fetch_weather

            result = await fetch_weather(float(lat), float(lon))
            if result is None:
                return {
                    "status": "offline",
                    "message": "Không kết nối được Open-Meteo API.",
                    "current": None,
                    "hourly_forecast": [],
                }
            return {"status": "ok", **result}
        except (ValueError, TypeError):
            return {
                "status": "error",
                "message": "invalid_weather_data",
                "current": None,
                "hourly_forecast": [],
            }

    # ==================================================================
    # G12: Multi-vendor Alarm Decoder API
    # ==================================================================
    @app.get("/api/alarms/decode/{vendor}/{code}")
    async def decode_alarm_endpoint(vendor: str, code: int, model: str | None = None, who=Depends(user)):
        """Decode a vendor-specific fault code into structured alarm with SOP."""
        from .vendor_registers import decode_vendor_alarm

        result = decode_vendor_alarm(vendor, code, model=model)
        return result

    @app.get("/api/alarms/decoder-summary")
    async def alarm_decoder_summary(who=Depends(user)):
        """Return registered alarm code counts per vendor."""
        from .vendor_registers import (
            DEYE_ALARM_CODES,
            GOODWE_ALARM_CODES,
            GROWATT_ALARM_CODES,
            HUAWEI_ALARM_CODES,
            SOLIS_ALARM_CODES,
            SUNGROW_ALARM_CODES,
        )

        return {
            "vendors": {
                "GoodWe": {"code_count": len(GOODWE_ALARM_CODES), "type": "bitmask"},
                "Deye": {"code_count": len(DEYE_ALARM_CODES), "type": "bitmask"},
                "Sungrow": {"code_count": len(SUNGROW_ALARM_CODES), "type": "code"},
                "Huawei": {"code_count": len(HUAWEI_ALARM_CODES), "type": "code"},
                "Solis": {"code_count": len(SOLIS_ALARM_CODES), "type": "code"},
                "Growatt": {"code_count": len(GROWATT_ALARM_CODES), "type": "code"},
            },
            "total_codes": sum(
                len(t)
                for t in [
                    GOODWE_ALARM_CODES,
                    DEYE_ALARM_CODES,
                    SUNGROW_ALARM_CODES,
                    HUAWEI_ALARM_CODES,
                    SOLIS_ALARM_CODES,
                    GROWATT_ALARM_CODES,
                ]
            ),
        }

    @app.get("/api/alarms/vendor-codes/{vendor}")
    async def vendor_alarm_codes(vendor: str, who=Depends(user)):
        """List all known alarm codes for a specific vendor."""
        from .vendor_registers import (
            DEYE_ALARM_CODES,
            GOODWE_ALARM_CODES,
            GROWATT_ALARM_CODES,
            HUAWEI_ALARM_CODES,
            SOLIS_ALARM_CODES,
            SUNGROW_ALARM_CODES,
        )

        tables = {
            "goodwe": GOODWE_ALARM_CODES,
            "deye": DEYE_ALARM_CODES,
            "sungrow": SUNGROW_ALARM_CODES,
            "huawei": HUAWEI_ALARM_CODES,
            "solis": SOLIS_ALARM_CODES,
            "growatt": GROWATT_ALARM_CODES,
        }
        v = vendor.lower().strip()
        table = tables.get(v)
        if not table:
            raise HTTPException(404, f"vendor_not_supported: {vendor}")
        codes = []
        for code, (title, severity, advice) in sorted(table.items()):
            codes.append(
                {
                    "code": code,
                    "code_hex": hex(code) if isinstance(code, int) and code > 15 else str(code),
                    "title": title,
                    "severity": severity,
                    "remediation_vi": advice,
                }
            )
        return {"vendor": vendor, "codes": codes}

    # ==================================================================
    # G15: Email Notification Delivery Skeleton (SMTP)
    # ==================================================================
    @app.get("/api/notifications/config")
    async def notification_config(who=Depends(admin)):
        """Get current notification configuration."""
        if "*" not in who.site_ids:
            raise HTTPException(403, "global_admin_required")
        config = store.get("config", "notification") or {}
        return {
            "smtp_host": config.get("smtp_host", ""),
            "smtp_port": config.get("smtp_port", 587),
            "smtp_user": config.get("smtp_user", ""),
            "smtp_tls": config.get("smtp_tls", True),
            "from_address": config.get("from_address", ""),
            "recipients_alarm": config.get("recipients_alarm", []),
            "recipients_report": config.get("recipients_report", []),
            "enabled": config.get("enabled", False),
            "channels": {
                "email": config.get("email_enabled", False),
                "zalo_webhook_configured": bool(config.get("zalo_webhook_configured") or config.get("zalo_webhook")),
                "telegram_bot_token_configured": bool(config.get("telegram_bot_token_configured") or config.get("telegram_bot_token")),
                "telegram_chat_id": config.get("telegram_chat_id", ""),
            },
        }

    @app.post("/api/notifications/config")
    async def update_notification_config(body: NotificationConfigForm, who=Depends(admin)):
        """Update notification configuration (SMTP, recipients, channels)."""
        if "*" not in who.site_ids:
            raise HTTPException(403, "global_admin_required")
        secret_keys = {"smtp_password", "zalo_webhook", "telegram_bot_token"}
        changes = body.model_dump(exclude_unset=True, exclude=secret_keys)
        with store.transaction():
            config = store.get("config", "notification") or {}
            credentials = {}
            if store.db.execute("SELECT 1 FROM secrets WHERE id=?", ("notification",)).fetchone():
                credentials = controller.vault.get("notification")
            for key in secret_keys:
                if key in config:
                    credentials[key] = config.pop(key)
                if key in body.model_fields_set:
                    value = getattr(body, key)
                    credentials[key] = value.get_secret_value() if value else ""
                config[key + "_configured"] = bool(credentials.get(key))
            controller.vault.put("notification", credentials)
            config.update(changes)
            store.put("config", "notification", config)
            store.audit("settings", {"event": "notification_config_updated", "operator": who.id,
                                     "keys_changed": sorted(body.model_fields_set)})
        return {"status": "saved"}

    @app.post("/api/notifications/test")
    async def test_notification(who=Depends(admin)):
        """Send a test notification to verify SMTP configuration."""
        if "*" not in who.site_ids:
            raise HTTPException(403, "global_admin_required")
        config = store.get("config", "notification") or {}
        if not config.get("smtp_host") or not config.get("from_address"):
            return {"status": "error", "message": "Chưa cấu hình SMTP host và địa chỉ gửi."}
        # Skeleton: actual email sending requires smtplib integration
        # which would use real credentials — locked behind safety gate
        return {
            "status": "locked",
            "message": "LOCKED_PENDING_HARDWARE_ACCEPTANCE — Gửi email thật cần cấu hình SMTP đã xác thực.",
            "would_send_to": config.get("recipients_alarm", [])[:3],
        }

    # ==================================================================
    # L8: Sync failure → auto incident escalation
    # ==================================================================
    @app.get("/api/sync/health")
    async def sync_health(who=Depends(user)):
        ids = {d.integration_id for d in controller.devices() if who.can_access(d.site_id)}
        rows = [
            {"integration_id": id, **(store.get("integration_state", id) or {"status": "UNKNOWN"})}
            for id in ids
        ]
        return {
            "total_connections": len(rows),
            "connections": rows,
            "issues": [r for r in rows if r.get("status") != "OK"],
            "auto_incidents_created": [],
            "mode": "READ_ONLY",
        }

    # ==================================================================
    # D1: Consolidated Firmware API (shared by Device + Maintenance tabs)
    # ==================================================================
    @app.get("/api/fleet/firmware-matrix")
    async def firmware_matrix(site_id: str | None = None, who=Depends(user)):
        """Unified firmware matrix — single source of truth for Device and Maintenance workspaces."""
        if site_id:
            site_access(site_id, who)
        sites = {s["id"]: s for s in store.list("site")
                 if who.can_access(s["id"]) and (not site_id or s["id"] == site_id)}
        all_devices = [d for d in store.list("device") if d.get("site_id") in sites]

        matrix = []
        for d in all_devices:
            fw = d.get("identity", {}).get("firmware")
            identity = d.get("identity", {})
            matrix.append(
                {
                    "device_id": d.get("id", ""),
                    "site_id": d.get("site_id", ""),
                    "site_name": sites.get(d.get("site_id", ""), {}).get("name", ""),
                    "device_name": d.get("name", ""),
                    "vendor": identity.get("vendor") or d.get("vendor", ""),
                    "model": identity.get("model") or d.get("model", ""),
                    "serial": identity.get("serial") or d.get("serial", ""),
                    "device_type": d.get("type", ""),
                    "current_firmware": fw,
                    "latest_firmware": "—",  # Would come from vendor API
                    "update_available": None,
                    "last_check": d.get("firmware_checked_at"),
                    "ota_supported": False,  # LOCKED_PENDING_HARDWARE_ACCEPTANCE
                }
            )

        vendors_summary = {}
        for m in matrix:
            v = m["vendor"]
            if v not in vendors_summary:
                vendors_summary[v] = {"total": 0, "versions": set()}
            vendors_summary[v]["total"] += 1
            vendors_summary[v]["versions"].add(m["current_firmware"])
        for v in vendors_summary:
            vendors_summary[v]["versions"] = sorted(
                version for version in vendors_summary[v]["versions"] if version is not None
            )

        return {
            "devices": matrix,
            "vendors_summary": vendors_summary,
            "total_devices": len(matrix),
            "ota_note": "OTA cập nhật firmware qua API của hãng cần hardware acceptance và readback xác nhận.",
        }
