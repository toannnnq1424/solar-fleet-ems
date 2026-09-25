"""Vendor-neutral weekly schedule compilation and immutable rollout preparation.

Compilation assesses a native schedule installation; it does not schedule arbitrary
cloud commands at future timestamps. Adapters must state their exact time semantics.
"""

from __future__ import annotations

import hashlib
import uuid
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException, Query
from pydantic import Field, field_validator

from .domain import Model, Role, SafetyError, utcnow
from .storage import encoded


@dataclass(frozen=True)
class ProgramSlot:
    day: int
    start_minute: int
    end_minute: int
    mode: str
    target_soc_pct: int | None
    power_w: float | None


@dataclass(frozen=True)
class WeeklyProgram:
    timezone: str
    slots: tuple[ProgramSlot, ...]
    gap_policy: str
    dst_policy: str


class ScheduleTranslation(Model):
    intent: str
    parameters: dict = Field(default_factory=dict)
    semantics: Literal["exact", "equivalent", "partial", "unsupported"]
    reason_vi: str = Field(min_length=1, max_length=2000)
    reason_en: str = Field(min_length=1, max_length=2000)
    device_clock: Literal["plant_timezone", "utc", "unknown"]
    evidence_ids: list[str] = Field(default_factory=list)


class ScheduleCompilation(Model):
    device_ids: list[str] = Field(min_length=1, max_length=100)
    start_date: str
    days: int = Field(default=7, ge=1, le=14)
    gap_policy: Literal["reject", "preserve_device_schedule"] = "reject"
    dst_policy: Literal["reject", "earlier", "later"] = "reject"

    @field_validator("start_date")
    @classmethod
    def valid_day(cls, value):
        return date.fromisoformat(value).isoformat()

    @field_validator("device_ids")
    @classmethod
    def unique_targets(cls, values):
        if len(set(values)) != len(values):
            raise ValueError("duplicate_schedule_device")
        return values


class CompileConfirmation(Model):
    digest: str = Field(pattern=r"^[a-f0-9]{64}$")


def minutes(value):
    hour, minute = map(int, value.split(":"))
    return hour * 60 + minute


def schedule_digest(row):
    return hashlib.sha256(
        encoded(
            {key: row.get(key) for key in ("id", "site_id", "revision", "timezone", "slots", "state")}
        ).encode()
    ).hexdigest()


def program_for(row, request):
    return WeeklyProgram(
        row["timezone"],
        tuple(
            ProgramSlot(
                slot["day"],
                minutes(slot["start"]),
                minutes(slot["end"]),
                slot["mode"],
                slot.get("target_soc"),
                None if slot.get("power_kw") is None else slot["power_kw"] * 1000,
            )
            for slot in sorted(row["slots"], key=lambda s: (s["day"], s["start"]))
        ),
        request.gap_policy,
        request.dst_policy,
    )


def utc_boundary(wall, zone, policy):
    candidates = sorted(
        {
            wall.replace(tzinfo=zone, fold=fold).astimezone(UTC)
            for fold in (0, 1)
            if wall.replace(tzinfo=zone, fold=fold).astimezone(UTC).astimezone(zone).replace(tzinfo=None)
            == wall
        }
    )
    if not candidates:
        raise SafetyError("schedule_nonexistent_local_time")
    if len(candidates) > 1 and policy == "reject":
        raise SafetyError("schedule_ambiguous_local_time")
    return candidates[-1] if policy == "later" else candidates[0]


def expand_program(program, start_day, days):
    try:
        zone = ZoneInfo(program.timezone)
    except (ValueError, ZoneInfoNotFoundError):
        raise SafetyError("site_timezone_required") from None
    windows, gaps = [], []
    for day_offset in range(days):
        local_day = start_day + timedelta(days=day_offset)
        base = datetime.combine(local_day, time.min)
        slots = [s for s in program.slots if s.day == local_day.weekday()]
        position = 0
        for slot in slots:
            if slot.start_minute < position or not 0 <= slot.start_minute < slot.end_minute <= 1440:
                raise SafetyError("schedule_slot_overlap_or_range")
            if slot.start_minute > position:
                gaps.append(
                    {"date": str(local_day), "start_minute": position, "end_minute": slot.start_minute}
                )
            start = utc_boundary(base + timedelta(minutes=slot.start_minute), zone, program.dst_policy)
            end = utc_boundary(base + timedelta(minutes=slot.end_minute), zone, program.dst_policy)
            if end <= start:
                raise SafetyError("schedule_nonpositive_utc_duration")
            duration = int((end - start).total_seconds())
            changed = duration != (slot.end_minute - slot.start_minute) * 60
            if changed and program.dst_policy == "reject":
                raise SafetyError("schedule_crosses_dst_transition")
            windows.append(
                {
                    "date": str(local_day),
                    "day": slot.day,
                    "start_at": start.isoformat(),
                    "end_at": end.isoformat(),
                    "start_local": start.astimezone(zone).isoformat(),
                    "end_local": end.astimezone(zone).isoformat(),
                    "duration_seconds": duration,
                    "dst_adjusted": changed,
                    "mode": slot.mode,
                    "target_soc_pct": slot.target_soc_pct,
                    "power_w": slot.power_w,
                }
            )
            position = slot.end_minute
        if position < 1440:
            gaps.append({"date": str(local_day), "start_minute": position, "end_minute": 1440})
    return {
        "windows": windows,
        "gaps": gaps,
        "complete": not gaps,
        "gap_policy": program.gap_policy,
        "dst_policy": program.dst_policy,
        "timezone": program.timezone,
    }


def require_schedule_source(store, rollout):
    source = rollout.get("schedule_source")
    if source:
        row = store.get("schedule", source["id"])
        if not row or schedule_digest(row) != source["digest"]:
            raise SafetyError("schedule_changed_recompile_required")


def install_schedule_planning(app, controller, user):
    store = controller.store

    def operator(who=Depends(user)):
        if who.role == Role.VIEWER:
            raise HTTPException(403, "operator_required")
        return who

    def scoped(kind, id, who):
        row = store.get(kind, id)
        if row is None:
            raise HTTPException(404)
        if not who.can_access(row["site_id"]):
            raise HTTPException(403, "site_access_denied")
        return row

    @app.get("/api/schedule-compilations")
    async def list_plans(site_id: str = "", limit: int = Query(default=50, ge=1, le=100), who=Depends(user)):
        rows = [
            r
            for r in store.list("schedule_compilation")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        return sorted(rows, key=lambda r: r["created_at"], reverse=True)[:limit]

    @app.post("/api/schedules/{id}/compile", status_code=201)
    async def compile_schedule(id: str, body: ScheduleCompilation, who=Depends(operator)):
        source = scoped("schedule", id, who)
        if source.get("state") not in {"DRAFT", "VALIDATED"}:
            raise SafetyError("schedule_state_not_compilable")
        program = program_for(source, body)
        expansion = expand_program(program, date.fromisoformat(body.start_date), body.days)
        # Assess all seven days, even when the visualization covers a shorter interval.
        full_week = expand_program(program, date.fromisoformat(body.start_date), 7)
        targets = []
        for device_id in body.device_ids:
            device = controller.device(device_id)
            if device.site_id != source["site_id"]:
                raise SafetyError("schedule_device_site_mismatch")
            plugin = controller.registry.find(device.identity.vendor)
            target = {
                "device_id": device.id,
                "site_id": device.site_id,
                "device_name": device.name or device.vendor_id,
                "platform": device.identity.vendor,
                "status": "BLOCKED",
                "semantics": "unsupported",
                "reason": "adapter_schedule_contract_missing",
                "translation": None,
            }
            if full_week["gaps"] and body.gap_policy == "reject":
                target["reason"] = "schedule_has_uncovered_intervals"
            elif plugin and plugin.compile_schedule:
                try:
                    translated = ScheduleTranslation.model_validate(plugin.compile_schedule(device, program))
                    target.update(translation=translated.model_dump(), semantics=translated.semantics)
                    if translated.semantics != "exact" or translated.device_clock == "unknown":
                        raise SafetyError("schedule_mapping_not_exact")
                    if not translated.evidence_ids or not set(translated.evidence_ids) <= set(
                        plugin.evidence_ids
                    ):
                        raise SafetyError("schedule_mapping_evidence_missing")
                    capability = controller.capability(device, translated.intent)
                    controller.engine.validate(who, device, capability, translated.parameters)
                    target.update(status="COMPATIBLE", reason="fresh_preview_required")
                except SafetyError as exc:
                    target["reason"] = str(exc)
                except (ValueError, TypeError):
                    target["reason"] = "invalid_adapter_schedule_contract"
            targets.append(target)
        now = utcnow()
        row = {
            "id": uuid.uuid4().hex,
            "site_id": source["site_id"],
            "schedule_id": id,
            "schedule_name": source["name"],
            "source_revision": source.get("revision", 1),
            "source_digest": schedule_digest(source),
            "request": body.model_dump(),
            "targets": targets,
            "timeline": expansion,
            "weekly_gaps": full_week["gaps"],
            "owner_id": who.id,
            "created_at": now.isoformat(),
            "expires_at": (now + timedelta(minutes=15)).isoformat(),
            "state": "COMPATIBLE" if all(t["status"] == "COMPATIBLE" for t in targets) else "BLOCKED",
            "execution": "INSTALL_NATIVE_WEEKLY_SCHEDULE",
            "dispatch_enabled": False,
        }
        row["digest"] = hashlib.sha256(encoded(row).encode()).hexdigest()
        with store.transaction():
            store.put("schedule_compilation", row["id"], row)
            store.audit(
                "operations",
                {
                    "event": "schedule_compiled",
                    "id": row["id"],
                    "operator": who.id,
                    "state": row["state"],
                    "source_digest": row["source_digest"],
                },
                row["site_id"],
            )
        return row

    @app.post("/api/schedule-compilations/{id}/rollout", status_code=201)
    async def prepare_rollout(id: str, body: CompileConfirmation, who=Depends(operator)):
        with store.transaction():
            row = scoped("schedule_compilation", id, who)
            if row["owner_id"] != who.id or row["digest"] != body.digest:
                raise SafetyError("schedule_compilation_owner_or_digest_mismatch")
            if row["state"] != "COMPATIBLE" or datetime.fromisoformat(row["expires_at"]) <= utcnow():
                raise SafetyError("schedule_compilation_blocked_or_expired")
            reference = {"id": row["schedule_id"], "digest": row["source_digest"]}
            require_schedule_source(store, {"schedule_source": reference})
            existing = store.get("rollout", "schedule_" + id)
            if existing:
                return existing
            targets = []
            for target in row["targets"]:
                device = controller.device(target["device_id"])
                if device.site_id != row["site_id"]:
                    raise SafetyError("schedule_device_site_mismatch")
                mapping = target["translation"]
                capability = controller.capability(device, mapping["intent"])
                controller.engine.validate(who, device, capability, mapping["parameters"])
                targets.append(
                    {
                        "device_id": device.id,
                        "site_id": device.site_id,
                        "intent": mapping["intent"],
                        "parameters": mapping["parameters"],
                        "state": capability.state,
                        "status": "NOT_PREVIEWED",
                        "reason": None,
                    }
                )
            rollout = {
                "id": "schedule_" + id,
                "site_id": row["site_id"],
                "site_ids": [row["site_id"]],
                "name": row["schedule_name"],
                "note": "Native schedule compilation " + id,
                "targets": targets,
                "owner_id": who.id,
                "created_at": utcnow().isoformat(),
                "state": "DRAFT",
                "digest": None,
                "schedule_source": reference,
                "schedule_compilation_id": id,
            }
            store.put("rollout", rollout["id"], rollout)
            store.audit(
                "operations",
                {"event": "schedule_rollout_prepared", "id": rollout["id"], "operator": who.id},
                row["site_id"],
            )
            return rollout
