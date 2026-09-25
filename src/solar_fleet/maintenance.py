"""Work execution, checklist evidence and service planning on top of shared work orders."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import UTC, date, datetime, timedelta
from typing import Literal
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from fastapi import Depends, HTTPException, Query
from pydantic import Field, field_validator, model_validator

from .domain import Model, Role, SafetyError, utcnow
from .security import principal
from .storage import encoded


class JobStep(Model):
    id: str = Field(pattern=r"^[A-Za-z0-9_-]{1,80}$")
    title: str = Field(min_length=1, max_length=300)
    instructions: str = Field(default="", max_length=3000)
    required: bool = True


class JobPlan(Model):
    revision: int = Field(ge=1)
    planned_start: datetime | None = None
    planned_end: datetime | None = None
    team: list[str] = Field(default_factory=list, max_length=20)
    steps: list[JobStep] = Field(min_length=1, max_length=50)
    safety_note: str = Field(min_length=1, max_length=3000)
    note: str = Field(min_length=1, max_length=2000)

    @field_validator("planned_start", "planned_end")
    @classmethod
    def aware(cls, value):
        if value is not None:
            if value.tzinfo is None:
                raise ValueError("maintenance_timezone_required")
            return value.astimezone(UTC)
        return value

    @model_validator(mode="after")
    def valid(self):
        if (self.planned_start is None) != (self.planned_end is None):
            raise ValueError("both_planning_times_required")
        if self.planned_start and (
            self.planned_end <= self.planned_start
            or self.planned_end - self.planned_start > timedelta(days=30)
        ):
            raise ValueError("maintenance_time_range_invalid")
        if len(set(self.team)) != len(self.team) or len({s.id for s in self.steps}) != len(self.steps):
            raise ValueError("duplicate_team_or_checklist_step")
        return self


class JobStepResult(Model):
    revision: int = Field(ge=1)
    step_id: str
    outcome: Literal["pass", "fail", "not_applicable", "pending"]
    note: str = Field(min_length=1, max_length=3000)
    document_ids: list[str] = Field(default_factory=list, max_length=10)


class JobTime(Model):
    revision: int = Field(ge=1)
    start: datetime
    end: datetime
    activity: str = Field(min_length=1, max_length=2000)

    @field_validator("start", "end")
    @classmethod
    def aware(cls, value):
        if value.tzinfo is None:
            raise ValueError("work_time_timezone_required")
        return value.astimezone(UTC)

    @model_validator(mode="after")
    def ordered(self):
        if not timedelta() < self.end - self.start <= timedelta(hours=24):
            raise ValueError("work_time_duration_invalid")
        return self


class JobRevision(Model):
    revision: int = Field(ge=1)
    note: str = Field(min_length=1, max_length=2000)


class ReviewDecision(JobRevision):
    decision: Literal["approve", "return"]


class FirmwareStageForm(Model):
    site_id: str
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
            raise ValueError("maintenance_window_timezone_required")
        return value.astimezone(UTC)


def editable(row):
    if row["status"] in {"resolved", "closed"}:
        raise SafetyError("work_order_completed_reopen_first")


def document_snapshot(row):
    return {key: row.get(key) for key in ("id", "revision", "sha256", "reference", "name")}


def completion_requirements(store, row):
    plan = store.get("work_execution", row["id"])
    if not plan:
        return {"ready": False, "reasons": ["work_execution_plan_required"]}
    reasons = []
    for step in plan["steps"]:
        result = plan.get("results", {}).get(step["id"])
        if step["required"] and (not result or result["outcome"] not in {"pass", "not_applicable"}):
            reasons.append("required_step_incomplete:" + step["id"])
        if result and result["outcome"] == "fail":
            reasons.append("failed_step:" + step["id"])
        for doc_id in (result or {}).get("document_ids", []):
            document = store.get("document", doc_id)
            if not document or document.get("archived") or document["site_id"] != row["site_id"]:
                reasons.append("evidence_unavailable:" + step["id"])
            elif document_snapshot(document) not in result.get("documents", []):
                reasons.append("evidence_changed:" + step["id"])
    entries = [r for r in store.list("work_time") if r["work_order_id"] == row["id"] and not r.get("voided")]
    if not entries:
        reasons.append("work_time_entry_required")
    return {"ready": not reasons, "reasons": reasons}


def execution_digest(store, row):
    plan = store.get("work_execution", row["id"])
    entries = sorted(
        (r for r in store.list("work_time") if r["work_order_id"] == row["id"] and not r.get("voided")),
        key=lambda r: r["id"],
    )
    snapshot = {
        "version": plan["version"],
        "steps": plan["steps"],
        "results": plan["results"],
        "time_entries": entries,
    }
    return hashlib.sha256(encoded(snapshot).encode()).hexdigest()


def guard_work_order_completion(store, row, new_status):
    plan = store.get("work_execution", row["id"])
    if new_status in {"resolved", "closed"}:
        gate = completion_requirements(store, row)
        if not gate["ready"]:
            raise SafetyError("maintenance_execution_incomplete")
        review = plan.get("review")
        if not review or review["decision"] != "approve" or review["plan_version"] != plan["version"]:
            raise SafetyError("maintenance_review_required")
        reviewer = principal(store, review["reviewer"])
        if (
            not reviewer
            or reviewer.role not in {Role.INSTALLER, Role.ENGINEER}
            or not reviewer.can_access(row["site_id"])
        ):
            raise SafetyError("maintenance_reviewer_no_longer_authorized")
        if review.get("execution_digest") != execution_digest(store, row):
            raise SafetyError("maintenance_execution_changed")
    elif new_status == "open" and row["status"] in {"resolved", "closed"} and plan:
        plan.update(review=None, submitted_by=None, submitted_at=None, state="IN_PROGRESS")
        store.put("work_execution", row["id"], plan)


def install_maintenance(app, controller, user):
    store = controller.store
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS maintenance_events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, work_order_id TEXT NOT NULL,
            site_id TEXT NOT NULL, body TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS maintenance_event_lookup ON maintenance_events(work_order_id,seq);
        CREATE TRIGGER IF NOT EXISTS maintenance_events_no_update BEFORE UPDATE ON maintenance_events
            BEGIN SELECT RAISE(ABORT,'maintenance events are append only'); END;
        CREATE TRIGGER IF NOT EXISTS maintenance_events_no_delete BEFORE DELETE ON maintenance_events
            BEGIN SELECT RAISE(ABORT,'maintenance events are append only'); END;
    """)

    def operator(who=Depends(user)):
        if who.role == Role.VIEWER:
            raise HTTPException(403, "operator_required")
        return who

    def technical(who=Depends(operator)):
        if who.role not in {Role.INSTALLER, Role.ENGINEER}:
            raise HTTPException(403, "maintenance_technical_role_required")
        return who

    def get(id, who, revision=None):
        row = store.get("work_order", id)
        if not row:
            raise HTTPException(404)
        if not who.can_access(row["site_id"]):
            raise HTTPException(403, "site_access_denied")
        if revision is not None and row["revision"] != revision:
            raise SafetyError("record_changed_reload")
        return row

    def event(row, who, kind, note, details=None):
        now = utcnow().isoformat()
        row.update(revision=row["revision"] + 1, updated_at=now)
        saved = {
            "id": uuid.uuid4().hex,
            "at": now,
            "actor": who.id,
            "status": row["status"],
            "kind": kind,
            "note": note,
            "details": details or {},
        }
        row["timeline"] = [*row.get("timeline", []), saved][-250:]
        store.db.execute(
            "INSERT INTO maintenance_events(work_order_id,site_id,body) VALUES(?,?,?)",
            (row["id"], row["site_id"], encoded(saved)),
        )
        store.put("work_order", row["id"], row)
        store.audit(
            "operations",
            {"event": kind, "id": row["id"], "operator": who.id, "revision": row["revision"]},
            row["site_id"],
        )
        return row

    def execution(id):
        row = store.get("work_execution", id)
        if not row:
            raise SafetyError("work_execution_plan_required")
        return row

    def invalidate_review(plan):
        plan.update(review=None, submitted_by=None, submitted_at=None, state="IN_PROGRESS")

    @app.get("/api/maintenance/work-orders")
    async def listing(
        site_id: str = "",
        status: str = "",
        q: str = Query(default="", max_length=200),
        overdue: bool = False,
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=30, ge=1, le=100),
        who=Depends(user),
    ):
        rows = [
            r
            for r in store.list("work_order")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        items = []
        now = utcnow()
        for row in rows:
            if status and row["status"] != status:
                continue
            if q.casefold() not in (row["title"] + " " + row.get("description", "")).casefold():
                continue
            plant = {
                **(store.get("site", row["site_id"]) or {}),
                **(store.get("site_profile", row["site_id"]) or {}),
            }
            try:
                today = now.astimezone(ZoneInfo(plant.get("timezone") or "")).date()
                late = (
                    bool(row.get("due_date"))
                    and date.fromisoformat(row["due_date"]) < today
                    and row["status"] not in {"resolved", "closed"}
                )
            except (ValueError, ZoneInfoNotFoundError):
                late = None
            if overdue and late is not True:
                continue
            plan = store.get("work_execution", row["id"])
            items.append(
                {
                    **row,
                    "overdue": late,
                    "execution_state": plan["state"] if plan else "UNPLANNED",
                    "checklist_completed": sum(
                        v["outcome"] in {"pass", "not_applicable"} for v in plan.get("results", {}).values()
                    )
                    if plan
                    else 0,
                    "checklist_total": len(plan["steps"]) if plan else 0,
                }
            )
        items.sort(
            key=lambda r: (r["status"] in {"resolved", "closed"}, r.get("due_date") or "9999", r["id"])
        )
        return {
            "items": items[offset : offset + limit],
            "total": len(items),
            "offset": offset,
            "limit": limit,
        }

    @app.get("/api/maintenance/work-orders/{id}")
    async def detail(id: str, who=Depends(user)):
        row = get(id, who)
        plan = store.get("work_execution", id)
        entries = [
            r for r in store.list("work_time") if r["work_order_id"] == id and r["site_id"] == row["site_id"]
        ]
        minutes = sum(
            (datetime.fromisoformat(r["end"]) - datetime.fromisoformat(r["start"])).total_seconds() / 60
            for r in entries
            if not r.get("voided")
        )
        return {
            "work_order": row,
            "execution": plan,
            "time_entries": entries,
            "total_minutes": minutes,
            "completion": completion_requirements(store, row),
            "assignees": [
                {"id": person.id, "role": person.role}
                for item in store.db.execute("SELECT id FROM users WHERE active=1")
                if (person := principal(store, item["id"]))
                and person.role != Role.VIEWER
                and person.can_access(row["site_id"])
            ],
            "documents": [
                r for r in store.list("document") if r["site_id"] == row["site_id"] and not r.get("archived")
            ],
        }

    @app.get("/api/maintenance/work-orders/{id}/events")
    async def events(
        id: str,
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=50, ge=1, le=200),
        who=Depends(user),
    ):
        row = get(id, who)
        items = store.db.execute(
            "SELECT seq,body FROM maintenance_events WHERE work_order_id=? AND site_id=? AND seq>? ORDER BY seq LIMIT ?",
            (id, row["site_id"], after, limit),
        ).fetchall()
        return {
            "items": [{"seq": r["seq"], **json.loads(r["body"])} for r in items],
            "next_cursor": items[-1]["seq"] if items else after,
        }

    @app.post("/api/maintenance/work-orders/{id}/plan")
    async def plan(id: str, body: JobPlan, who=Depends(technical)):
        with store.transaction():
            row = get(id, who, body.revision)
            editable(row)
            for member in body.team:
                person = principal(store, member)
                if not person or person.role == Role.VIEWER or not person.can_access(row["site_id"]):
                    raise SafetyError("maintenance_team_member_not_authorized")
            previous = store.get("work_execution", id)
            if previous:
                store.put("work_execution_version", f"{id}:{previous['version']}", previous)
            saved = {
                "id": id,
                "site_id": row["site_id"],
                **body.model_dump(mode="json", exclude={"revision", "note"}),
                "version": previous["version"] + 1 if previous else 1,
                "state": "PLANNED",
                "results": {},
                "review": None,
                "updated_by": who.id,
                "updated_at": utcnow().isoformat(),
            }
            # Every plan revision invalidates prior results instead of silently carrying
            # evidence to a step whose instructions could have changed.
            store.put("work_execution", id, saved)
            event(row, who, "maintenance_plan_saved", body.note, {"plan": saved})
        return saved

    @app.post("/api/maintenance/work-orders/{id}/step")
    async def record_step(id: str, body: JobStepResult, who=Depends(technical)):
        with store.transaction():
            row = get(id, who, body.revision)
            editable(row)
            plan = execution(id)
            if not any(s["id"] == body.step_id for s in plan["steps"]):
                raise SafetyError("maintenance_step_not_found")
            documents = []
            for doc_id in body.document_ids:
                doc = store.get("document", doc_id)
                if not doc or doc["site_id"] != row["site_id"] or doc.get("archived"):
                    raise SafetyError("maintenance_evidence_not_available")
                documents.append(document_snapshot(doc))
            invalidate_review(plan)
            plan["results"][body.step_id] = {
                **body.model_dump(exclude={"revision"}),
                "documents": documents,
                "actor": who.id,
                "at": utcnow().isoformat(),
            }
            store.put("work_execution", id, plan)
            event(
                row,
                who,
                "maintenance_step_recorded",
                body.note,
                {"version": plan["version"], "result": plan["results"][body.step_id]},
            )
        return plan

    @app.post("/api/maintenance/work-orders/{id}/time", status_code=201)
    async def record_time(id: str, body: JobTime, who=Depends(operator)):
        if body.end > utcnow() + timedelta(seconds=60):
            raise SafetyError("work_time_in_future")
        with store.transaction():
            row = get(id, who, body.revision)
            editable(row)
            # A person's time cannot be billed to overlapping jobs, even across sites.
            for existing in store.list("work_time"):
                if existing["actor"] == who.id and not existing.get("voided"):
                    if body.start < datetime.fromisoformat(
                        existing["end"]
                    ) and body.end > datetime.fromisoformat(existing["start"]):
                        raise SafetyError("work_time_overlap")
            entry = {
                "id": uuid.uuid4().hex,
                "work_order_id": id,
                "site_id": row["site_id"],
                **body.model_dump(mode="json", exclude={"revision"}),
                "actor": who.id,
                "voided": False,
                "created_at": utcnow().isoformat(),
            }
            store.put("work_time", entry["id"], entry)
            plan = store.get("work_execution", id)
            if plan:
                invalidate_review(plan)
                store.put("work_execution", id, plan)
            event(row, who, "maintenance_time_recorded", body.activity, {"entry": entry})
        return entry

    @app.post("/api/maintenance/work-orders/{id}/time/{entry_id}/void")
    async def void_time(id: str, entry_id: str, body: JobRevision, who=Depends(operator)):
        with store.transaction():
            row = get(id, who, body.revision)
            editable(row)
            entry = store.get("work_time", entry_id)
            if not entry or entry["work_order_id"] != id or entry["actor"] != who.id or entry["voided"]:
                raise SafetyError("work_time_entry_not_editable")
            entry.update(voided=True, void_reason=body.note, void_at=utcnow().isoformat())
            store.put("work_time", entry_id, entry)
            plan = store.get("work_execution", id)
            if plan:
                invalidate_review(plan)
                store.put("work_execution", id, plan)
            event(row, who, "maintenance_time_voided", body.note, {"entry_id": entry_id})
        return entry

    @app.post("/api/maintenance/work-orders/{id}/submit")
    async def submit(id: str, body: JobRevision, who=Depends(technical)):
        with store.transaction():
            row = get(id, who, body.revision)
            editable(row)
            gate = completion_requirements(store, row)
            if not gate["ready"]:
                raise SafetyError("maintenance_execution_incomplete")
            plan = execution(id)
            plan.update(
                state="AWAITING_REVIEW", submitted_by=who.id, submitted_at=utcnow().isoformat(), review=None
            )
            store.put("work_execution", id, plan)
            event(row, who, "maintenance_submitted", body.note)
        return plan

    @app.post("/api/maintenance/work-orders/{id}/review")
    async def review(id: str, body: ReviewDecision, who=Depends(technical)):
        with store.transaction():
            row = get(id, who, body.revision)
            editable(row)
            plan = execution(id)
            if plan["state"] != "AWAITING_REVIEW":
                raise SafetyError("maintenance_not_awaiting_review")
            own_time = any(
                r["actor"] == who.id and r["work_order_id"] == id and not r.get("voided")
                for r in store.list("work_time")
            )
            if (
                who.id == plan.get("submitted_by")
                or any(r["actor"] == who.id for r in plan.get("results", {}).values())
                or own_time
            ):
                raise SafetyError("maintenance_independent_reviewer_required")
            if body.decision == "approve" and not completion_requirements(store, row)["ready"]:
                raise SafetyError("maintenance_execution_incomplete")
            plan.update(
                state="APPROVED" if body.decision == "approve" else "CHANGES_REQUESTED",
                review={
                    "decision": body.decision,
                    "note": body.note,
                    "reviewer": who.id,
                    "plan_version": plan["version"],
                    "execution_digest": execution_digest(store, row),
                    "at": utcnow().isoformat(),
                },
            )
            store.put("work_execution", id, plan)
            event(row, who, "maintenance_reviewed", body.note, {"review": plan["review"]})
        return plan

    @app.get("/api/maintenance/calendar")
    async def calendar(start: date, end: date, site_id: str = "", who=Depends(user)):
        if not timedelta() < end - start <= timedelta(days=93):
            raise SafetyError("maintenance_calendar_range_invalid")
        items = []
        for plan in store.list("maintenance_plan"):
            if (
                not who.can_access(plan["site_id"])
                or (site_id and plan["site_id"] != site_id)
                or plan.get("archived")
                or not plan["enabled"]
            ):
                continue
            first = date.fromisoformat(plan["next_due"])
            due = first
            if due < start:
                periods = max(0, (start - due).days // plan["interval_days"])
                due += timedelta(days=periods * plan["interval_days"])
                if due < start:
                    due += timedelta(days=plan["interval_days"])
            while due < end:
                items.append(
                    {
                        "kind": "recurrence",
                        "id": plan["id"],
                        "site_id": plan["site_id"],
                        "title": plan["name"],
                        "date": due.isoformat(),
                        "overdue_anchor": first.isoformat() if first < start else None,
                    }
                )
                due += timedelta(days=plan["interval_days"])
                if len(items) > 10000:
                    raise SafetyError("maintenance_calendar_too_large")
        for plan in store.list("work_execution"):
            if (
                not who.can_access(plan["site_id"])
                or (site_id and plan["site_id"] != site_id)
                or not plan.get("planned_start")
            ):
                continue
            row = store.get("work_order", plan["id"])
            if not row:
                continue
            plant = {
                **(store.get("site", row["site_id"]) or {}),
                **(store.get("site_profile", row["site_id"]) or {}),
            }
            try:
                zone = ZoneInfo(plant.get("timezone") or "")
            except (ValueError, ZoneInfoNotFoundError):
                continue
            local_start = datetime.fromisoformat(plan["planned_start"]).astimezone(zone)
            local_end = datetime.fromisoformat(plan["planned_end"]).astimezone(zone)
            range_start = datetime.combine(start, datetime.min.time(), zone)
            range_end = datetime.combine(end, datetime.min.time(), zone)
            if local_start < range_end and local_end > range_start:
                items.append(
                    {
                        "kind": "work_order",
                        "id": row["id"],
                        "site_id": row["site_id"],
                        "title": row["title"],
                        "date": local_start.date().isoformat(),
                        "start_at": local_start.isoformat(),
                        "end_at": local_end.isoformat(),
                        "status": row["status"],
                        "team": plan["team"],
                    }
                )
                if len(items) > 10000:
                    raise SafetyError("maintenance_calendar_too_large")
        return {
            "items": sorted(items, key=lambda r: (r["date"], r["site_id"], r["id"])),
            "end_exclusive": True,
        }

    @app.get("/api/maintenance/health")
    async def health(site_id: str = "", who=Depends(user)):
        devices = [
            controller.device(r["id"])
            for r in store.list("device")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        items = []
        all_incidents = store.list("incident")
        all_work = store.list("work_order")
        for device in devices:
            samples = controller.latest(device)["samples"]
            fresh = [s for s in samples if not s["stale"]]
            incidents = [
                r
                for r in all_incidents
                if r.get("device_id") == device.id
                and r["site_id"] == device.site_id
                and r["status"] not in {"resolved", "closed"}
            ]
            work = [
                r
                for r in all_work
                if r.get("device_id") == device.id
                and r["site_id"] == device.site_id
                and r["status"] not in {"resolved", "closed"}
            ]
            reasons = []
            if not device.online or not fresh:
                reasons.append("connectivity_or_data_stale")
            if incidents:
                reasons.append("open_incidents")
            if not any(s["quality"] == "GOOD" for s in fresh):
                reasons.append("no_verified_telemetry")
            items.append(
                {
                    "device_id": device.id,
                    "site_id": device.site_id,
                    "name": device.name or device.vendor_id,
                    "type": device.type,
                    "firmware": device.identity.firmware,
                    "online": device.online,
                    "last_seen": device.last_seen,
                    "fresh_channels": len(fresh),
                    "verified_channels": sum(s["quality"] == "GOOD" for s in fresh),
                    "open_incidents": len(incidents),
                    "open_work_orders": len(work),
                    "state": "NEEDS_ATTENTION" if reasons else "OBSERVABLE",
                    "reasons": reasons,
                    "firmware_currency": "UNKNOWN",
                    "electrical_health_score": None,
                }
            )
        return {
            "items": items,
            "as_of": utcnow().isoformat(),
            "scope": "OBSERVATION_QUALITY_AND_OPEN_WORK_NOT_ELECTRICAL_CERTIFICATION",
        }

    @app.get("/api/maintenance/summary")
    async def summary(site_id: str = "", who=Depends(user)):
        devices = [
            controller.device(r["id"])
            for r in store.list("device")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        all_incidents = [
            r
            for r in store.list("incident")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        all_work = [
            r
            for r in store.list("work_order")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        all_plans = [
            r
            for r in store.list("maintenance_plan")
            if who.can_access(r["site_id"])
            and not r.get("archived")
            and (not site_id or r["site_id"] == site_id)
        ]
        all_firmware_reqs = [
            r
            for r in store.list("firmware_request")
            if who.can_access(r["site_id"])
            and not r.get("archived")
            and (not site_id or r["site_id"] == site_id)
        ]
        all_work_time = [
            r
            for r in store.list("work_time")
            if who.can_access(r["site_id"])
            and not r.get("voided")
            and (not site_id or r["site_id"] == site_id)
        ]

        now = utcnow()
        devices_attention = 0
        devices_fresh = 0
        for device in devices:
            samples = controller.latest(device)["samples"]
            fresh = [s for s in samples if not s["stale"]]
            if fresh:
                devices_fresh += 1
            incidents = [
                r
                for r in all_incidents
                if r.get("device_id") == device.id and r["status"] not in {"resolved", "closed"}
            ]
            if not device.online or not fresh or incidents or not any(s["quality"] == "GOOD" for s in fresh):
                devices_attention += 1

        work_open = 0
        work_in_progress = 0
        work_overdue = 0
        work_awaiting_review = 0
        work_resolved = 0
        for row in all_work:
            st = row.get("status", "open")
            if st in {"open", "acknowledged"}:
                work_open += 1
            elif st == "in_progress":
                work_in_progress += 1
            elif st in {"resolved", "closed"}:
                work_resolved += 1
            plan = store.get("work_execution", row["id"])
            if plan and plan.get("state") == "AWAITING_REVIEW":
                work_awaiting_review += 1
            if row.get("due_date") and st not in {"resolved", "closed"}:
                try:
                    if date.fromisoformat(row["due_date"]) < now.date():
                        work_overdue += 1
                except ValueError:
                    pass

        plans_active = sum(1 for p in all_plans if p.get("enabled", True))
        plans_due_soon = 0
        for p in all_plans:
            if not p.get("enabled", True):
                continue
            try:
                due_d = date.fromisoformat(p.get("next_due", ""))
                if 0 <= (due_d - now.date()).days <= 7:
                    plans_due_soon += 1
            except ValueError:
                pass

        total_labor_minutes = sum(
            (datetime.fromisoformat(r["end"]) - datetime.fromisoformat(r["start"])).total_seconds() / 60
            for r in all_work_time
        )

        return {
            "devices": {
                "total": len(devices),
                "attention": devices_attention,
                "fresh": devices_fresh,
                "healthy": len(devices) - devices_attention,
            },
            "work_orders": {
                "total": len(all_work),
                "open": work_open,
                "in_progress": work_in_progress,
                "overdue": work_overdue,
                "awaiting_review": work_awaiting_review,
                "resolved": work_resolved,
            },
            "plans": {
                "total": len(all_plans),
                "active": plans_active,
                "due_soon": plans_due_soon,
            },
            "firmware": {
                "total_requests": len(all_firmware_reqs),
                "pending_requests": sum(1 for r in all_firmware_reqs if r.get("state") != "COMPLETED"),
            },
            "total_labor_minutes": round(total_labor_minutes, 1),
            "as_of": now.isoformat(),
        }

    @app.get("/api/maintenance/plans")
    async def list_plans(site_id: str = "", who=Depends(user)):
        all_plans = [
            r
            for r in store.list("maintenance_plan")
            if who.can_access(r["site_id"])
            and not r.get("archived")
            and (not site_id or r["site_id"] == site_id)
        ]
        now = utcnow()
        items = []
        all_work = store.list("work_order")
        for plan in all_plans:
            plant = {
                **(store.get("site", plan["site_id"]) or {}),
                **(store.get("site_profile", plan["site_id"]) or {}),
            }
            try:
                today = now.astimezone(ZoneInfo(plant.get("timezone") or "")).date()
            except (ValueError, ZoneInfoNotFoundError):
                today = now.date()
            try:
                due = date.fromisoformat(plan.get("next_due", ""))
                days_left = (due - today).days
                overdue = days_left < 0
            except ValueError:
                days_left = None
                overdue = False
            device_info = None
            if plan.get("device_id"):
                dev = store.get("device", plan["device_id"])
                if dev:
                    device_info = {
                        "id": dev["id"],
                        "name": dev.get("name") or dev.get("vendor_id"),
                        "vendor": dev.get("identity", {}).get("vendor"),
                    }
            gen_count = sum(
                1
                for w in all_work
                if w.get("source") == "MAINTENANCE_PLAN"
                and w.get("title") == plan.get("name")
                and w.get("site_id") == plan["site_id"]
            )
            items.append(
                {
                    **plan,
                    "days_until_due": days_left,
                    "overdue": overdue,
                    "device": device_info,
                    "work_orders_generated": gen_count,
                }
            )
        items.sort(key=lambda r: (not r.get("overdue", False), r.get("next_due") or "9999"))
        return {"items": items, "total": len(items)}

    @app.post("/api/maintenance/plans/{id}/trigger", status_code=201)
    async def trigger_plan(id: str, who=Depends(operator)):
        plan = store.get("maintenance_plan", id)
        if not plan or plan.get("archived"):
            raise HTTPException(404)
        if not who.can_access(plan["site_id"]):
            raise HTTPException(403, "site_access_denied")
        now = utcnow()
        today_str = now.date().isoformat()
        job_id = hashlib.sha256(f"{id}:manual:{now.isoformat()}".encode()).hexdigest()[:32]
        with store.transaction():
            job = {
                "id": job_id,
                "site_id": plan["site_id"],
                "title": plan["name"],
                "description": plan["instructions"],
                "device_id": plan.get("device_id"),
                "severity": plan.get("severity", "medium"),
                "status": "open",
                "revision": 1,
                "assigned_to": who.id,
                "due_date": today_str,
                "incident_id": None,
                "created_at": now.isoformat(),
                "updated_at": now.isoformat(),
                "source": "MAINTENANCE_PLAN",
                "timeline": [
                    {
                        "at": now.isoformat(),
                        "actor": who.id,
                        "status": "open",
                        "note": f"Manual trigger from plan: {plan['name']}",
                    }
                ],
            }
            store.put("work_order", job_id, job)
            store.audit(
                "operations",
                {"event": "maintenance_plan_triggered", "plan_id": id, "job_id": job_id, "operator": who.id},
                plan["site_id"],
            )
        return job

    @app.get("/api/maintenance/firmware")
    async def firmware_overview(site_id: str = "", who=Depends(user)):
        devices = [
            controller.device(r["id"])
            for r in store.list("device")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]
        all_incidents = store.list("incident")
        all_requests = [
            r
            for r in store.list("firmware_request")
            if who.can_access(r["site_id"])
            and not r.get("archived")
            and (not site_id or r["site_id"] == site_id)
        ]
        all_rollouts = [
            r
            for r in store.list("rollout")
            if who.can_access(r.get("site_id", "")) and (not site_id or r.get("site_id") == site_id)
        ]

        now = utcnow()
        inventory = []
        for d in devices:
            crit_incidents = [
                r
                for r in all_incidents
                if r.get("device_id") == d.id
                and r.get("severity") == "critical"
                and r.get("status") not in {"resolved", "closed"}
            ]
            samples = controller.latest(d)["samples"]
            fresh = [s for s in samples if not s["stale"]]
            soc_sample = next((s for s in fresh if s.get("metric") in {"battery_soc", "soc", "SOC"}), None)
            battery_soc_ok = True
            if d.type == "BATTERY" and soc_sample:
                try:
                    battery_soc_ok = float(soc_sample["value"]) >= 30.0
                except (ValueError, TypeError):
                    battery_soc_ok = False

            preflight = {
                "online": bool(d.online),
                "no_critical_alarms": len(crit_incidents) == 0,
                "battery_soc_ok": battery_soc_ok,
                "passed": bool(d.online) and len(crit_incidents) == 0 and battery_soc_ok,
            }

            active_req = next((r for r in all_requests if r.get("device_id") == d.id), None)

            inventory.append(
                {
                    "device_id": d.id,
                    "site_id": d.site_id,
                    "name": d.name or d.vendor_id,
                    "type": d.type,
                    "vendor": d.identity.vendor,
                    "model": d.identity.model,
                    "serial": d.metadata.get("serial", d.vendor_id),
                    "current_firmware": d.identity.firmware or "UNKNOWN",
                    "online": bool(d.online),
                    "last_seen": d.last_seen,
                    "preflight": preflight,
                    "active_request": active_req,
                }
            )

        requests_enriched = []
        for req in all_requests:
            dev = store.get("device", req.get("device_id"))
            requests_enriched.append(
                {
                    **req,
                    "device_name": (dev.get("name") or dev.get("vendor_id")) if dev else req.get("device_id"),
                    "vendor": dev.get("identity", {}).get("vendor") if dev else "UNKNOWN",
                    "current_firmware": dev.get("identity", {}).get("firmware") if dev else "UNKNOWN",
                }
            )

        return {
            "inventory": inventory,
            "requests": requests_enriched,
            "rollouts": all_rollouts,
            "as_of": now.isoformat(),
        }

    @app.post("/api/maintenance/firmware/stage", status_code=201)
    async def stage_firmware(body: FirmwareStageForm, who=Depends(technical)):
        if not who.can_access(body.site_id):
            raise HTTPException(403, "site_access_denied")
        dev = controller.device(body.device_id)
        if dev.site_id != body.site_id:
            raise SafetyError("device_site_mismatch")
        now = utcnow()
        req_id = uuid.uuid4().hex
        row = {
            "id": req_id,
            "site_id": body.site_id,
            "device_id": body.device_id,
            "target_version": body.target_version,
            "sha256": body.sha256.lower(),
            "release_reference": body.release_reference,
            "maintenance_window": body.maintenance_window.isoformat(),
            "notes": body.notes,
            "state": "QUEUED_FOR_MAINTENANCE_WINDOW",
            "applied_to_device": False,
            "archived": False,
            "revision": 1,
            "created_at": now.isoformat(),
            "updated_at": now.isoformat(),
            "created_by": who.id,
        }
        with store.transaction():
            store.put("firmware_request", req_id, row)
            store.audit(
                "operations",
                {
                    "event": "firmware_upgrade_staged",
                    "id": req_id,
                    "device_id": body.device_id,
                    "target_version": body.target_version,
                    "operator": who.id,
                },
                body.site_id,
            )
        return row
