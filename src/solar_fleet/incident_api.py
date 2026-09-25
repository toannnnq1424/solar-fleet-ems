import csv
import io
import json
import uuid
from collections import Counter
from datetime import timedelta

from fastapi import Depends, HTTPException, Query
from fastapi.responses import PlainTextResponse

from .domain import Role, SafetyError, utcnow
from .incident_models import (
    RANK,
    IncidentChange,
    IncidentNote,
    IncidentWorkOrder,
    PlaybookAttach,
    PlaybookCheck,
    PlaybookForm,
    Severity,
    SLAPolicy,
    Status,
    TriageForm,
)
from .incidents import DEFAULT_SLA, sla_status, timestamp


def install_incidents(app, controller, user):
    service, store = controller.incidents, controller.store

    def operator(who=Depends(user)):
        if who.role == Role.VIEWER:
            raise HTTPException(403, "operator_required")
        return who

    def configure(who=Depends(operator)):
        if who.role not in {Role.ADMIN, Role.ENGINEER, Role.INSTALLER}:
            raise HTTPException(403, "technical_role_required")
        return who

    def site(id, who):
        if not who.can_access(id):
            raise HTTPException(403, "site_access_denied")
        if not store.get("site", id):
            raise HTTPException(404, "site_not_found")

    def visible(who, site_id=""):
        if site_id:
            site(site_id, who)
        return [
            r
            for r in store.list("incident")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]

    def present(row, now):
        vendor = row.get("vendor")
        if not vendor and row.get("site_id"):
            s_row = store.get("site", row["site_id"])
            if s_row and s_row.get("vendor"):
                vendor = s_row["vendor"]
        if not vendor and row.get("device_id"):
            d_row = store.get("device", row["device_id"])
            if d_row and d_row.get("vendor"):
                vendor = d_row["vendor"]
        devices = row.get("affected_devices") or ([row["device_id"]] if row.get("device_id") else [])
        return {
            **row,
            "vendor": vendor or "Deye",
            "affected_devices": devices,
            "affected_count": max(1, len(devices)) if devices else 1,
            "sla_status": sla_status(row, now),
        }

    @app.get("/api/incidents")
    async def listing(
        site_id: str = "",
        q: str = Query(default="", max_length=200),
        severity: Severity | None = None,
        status: Status | None = None,
        vendor: str = "",
        assigned_to: str = "",
        unassigned: bool = False,
        only_breached: bool = False,
        source: str = "",
        offset: int = Query(default=0, ge=0),
        limit: int = Query(default=30, ge=1, le=100),
        who=Depends(user),
    ):
        now = utcnow()
        rows = visible(who, site_id)
        if q:
            needle = q.casefold()
            rows = [
                r
                for r in rows
                if needle
                in " ".join(
                    str(r.get(k, ""))
                    for k in ("title", "description", "alarm_code", "device_id", "root_cause")
                ).casefold()
            ]
        rows = [
            r
            for r in rows
            if (not severity or r["severity"] == severity)
            and (not status or r["status"] == status)
            and (
                not vendor
                or (r.get("vendor") or (store.get("site", r["site_id"]) or {}).get("vendor", "Deye")).lower()
                == vendor.lower()
            )
            and (not assigned_to or r.get("assigned_to") == assigned_to)
            and (not unassigned or not r.get("assigned_to"))
            and (not source or r.get("source") == source)
            and (not only_breached or sla_status(r, now)["state"] == "BREACHED")
        ]
        rows.sort(
            key=lambda r: (
                r["status"] in {"resolved", "closed"},
                RANK[r["severity"]],
                -timestamp(r["created_at"]).timestamp(),
                r["id"],
            )
        )
        return {
            "items": [present(r, now) for r in rows[offset : offset + limit]],
            "total": len(rows),
            "offset": offset,
            "limit": limit,
            "as_of": now.isoformat(),
        }

    @app.get("/api/incidents/summary")
    async def summary(site_id: str = "", days: int = Query(default=7, ge=1, le=366), who=Depends(user)):
        now = utcnow()
        rows = visible(who, site_id)
        open_rows = [r for r in rows if r["status"] not in {"resolved", "closed"}]
        recent = [r for r in rows if timestamp(r["created_at"]) >= now - timedelta(days=days)]
        measured = [(r, sla_status(r, now)) for r in recent if r.get("sla")]
        responses = [s["response_seconds"] for _, s in measured if s["response_seconds"] is not None]
        resolutions = [s["resolution_seconds"] for _, s in measured if s["resolution_seconds"] is not None]
        completed = [s for r, s in measured if r["status"] in {"resolved", "closed"}]
        trend = Counter(r["created_at"][:10] for r in recent)

        conn_cnt = sum(1 for r in recent if r.get("category") == "connectivity")
        dev_cnt = sum(1 for r in recent if r.get("category") in ("inverter", "device", "battery"))
        grid_cnt = sum(1 for r in recent if r.get("category") in ("grid", "meter"))
        op_cnt = sum(1 for r in recent if r.get("category") in ("operation", "yield"))
        other_cnt = sum(
            1
            for r in recent
            if r.get("category")
            not in ("connectivity", "inverter", "device", "battery", "grid", "meter", "operation", "yield")
        )
        total_rc = max(1, len(recent))
        root_causes = [
            {
                "name": "Mất kết nối Internet",
                "category": "connectivity",
                "count": conn_cnt,
                "pct": round(conn_cnt / total_rc * 100, 1),
                "color": "#ef4444",
            },
            {
                "name": "Sự cố thiết bị",
                "category": "inverter",
                "count": dev_cnt,
                "pct": round(dev_cnt / total_rc * 100, 1),
                "color": "#3b82f6",
            },
            {
                "name": "Điện áp/ Tần số lưới",
                "category": "grid",
                "count": grid_cnt,
                "pct": round(grid_cnt / total_rc * 100, 1),
                "color": "#f97316",
            },
            {
                "name": "Cấu hình/ Vận hành",
                "category": "operation",
                "count": op_cnt,
                "pct": round(op_cnt / total_rc * 100, 1),
                "color": "#a855f7",
            },
            {
                "name": "Khác",
                "category": "other",
                "count": other_cnt,
                "pct": round(other_cnt / total_rc * 100, 1),
                "color": "#94a3b8",
            },
        ]

        return {
            "open": len(open_rows),
            "critical": sum(r["severity"] == "critical" for r in open_rows),
            "in_progress": sum(r["status"] == "in_progress" for r in rows),
            "unassigned": sum(not r.get("assigned_to") for r in open_rows),
            "resolved_today": sum(
                bool(r.get("resolved_at")) and timestamp(r["resolved_at"]).date() == now.date() for r in rows
            ),
            "equipment_active": sum(r.get("equipment_state") == "ACTIVE" for r in rows),
            "sla_breached_open": sum(sla_status(r, now)["state"] == "BREACHED" for r in open_rows),
            "mean_response_seconds": sum(responses) / len(responses) if responses else None,
            "mean_resolution_seconds": sum(resolutions) / len(resolutions) if resolutions else None,
            "sla_met_percent": 100 * sum(s["state"] == "MET" for s in completed) / len(completed)
            if completed
            else None,
            "sla_completed_sample": len(completed),
            "sla_response_sample": len(responses),
            "by_category": dict(Counter(r.get("category", "other") for r in recent)),
            "by_severity": dict(Counter(r["severity"] for r in open_rows)),
            "root_causes": root_causes,
            "trend": [
                {
                    "date": (now - timedelta(days=d)).date().isoformat(),
                    "count": trend[(now - timedelta(days=d)).date().isoformat()],
                }
                for d in reversed(range(days))
            ],
            "clock": "UTC_ELAPSED_24X7",
            "days": days,
            "as_of": now.isoformat(),
        }

    @app.get("/api/incidents/{id}/detail")
    async def detail(id: str, who=Depends(user)):
        row = service.get(id, who)
        people = []
        for person in store.db.execute("SELECT id,role,sites FROM users WHERE active=1"):
            if person["role"] != Role.VIEWER and {row["site_id"], "*"} & set(json.loads(person["sites"])):
                people.append({"id": person["id"], "role": person["role"]})
        sources = [store.get("alarm_source", key) for key in row.get("alarm_sources", [])]
        return {
            "incident": present(row, utcnow()),
            "assignees": people,
            "sources": [s for s in sources if s and s["site_id"] == row["site_id"]],
            "work_orders": [
                r
                for r in store.list("work_order")
                if r.get("incident_id") == id and r["site_id"] == row["site_id"]
            ],
            "playbooks": [
                r for r in store.list("incident_playbook") if r["site_id"] == row["site_id"] and r["enabled"]
            ],
        }

    @app.get("/api/incidents/{id}/history")
    async def history(
        id: str,
        after: int = Query(default=0, ge=0),
        limit: int = Query(default=100, ge=1, le=200),
        who=Depends(user),
    ):
        return service.history(service.get(id, who), after=after, limit=limit)

    @app.post("/api/incidents/{id}/transition")
    async def change(id: str, body: IncidentChange, who=Depends(operator)):
        return service.change(id, body, who)

    @app.post("/api/incidents/{id}/notes")
    async def note(id: str, body: IncidentNote, who=Depends(operator)):
        return service.note(id, body, who)

    @app.post("/api/incidents/{id}/triage")
    async def triage(id: str, body: TriageForm, who=Depends(operator)):
        return service.triage(id, body, who)

    @app.post("/api/incidents/{id}/playbook")
    async def attach(id: str, body: PlaybookAttach, who=Depends(operator)):
        return service.attach_playbook(id, body, who)

    @app.post("/api/incidents/{id}/check")
    async def check(id: str, body: PlaybookCheck, who=Depends(operator)):
        return service.check_step(id, body, who)

    @app.post("/api/incidents/{id}/work-order", status_code=201)
    async def work_order(id: str, body: IncidentWorkOrder, who=Depends(operator)):
        return service.work_order(id, body, who)

    @app.post("/api/incidents/{id}/acknowledge")
    async def acknowledge_incident(id: str, who=Depends(operator)):
        row = service.get(id, who)
        if row["status"] != "open":
            return present(row, utcnow())
        change_body = IncidentChange(
            revision=row["revision"],
            status="acknowledged",
            assigned_to=row.get("assigned_to") or who.id,
            note=f"Kỹ sư {who.id} đã xác nhận tiếp nhận sự cố.",
        )
        return service.change(id, change_body, who)

    @app.post("/api/incidents/{id}/close")
    async def close_incident(id: str, body: dict = {}, who=Depends(operator)):
        row = service.get(id, who)
        note_text = body.get("note") or f"Kỹ sư {who.id} đã đóng sự cố."
        target_status = "resolved" if row["status"] in ("open", "acknowledged", "in_progress") else "closed"
        change_body = IncidentChange(
            revision=row["revision"],
            status=target_status,
            assigned_to=row.get("assigned_to") or who.id,
            note=note_text,
        )
        return service.change(id, change_body, who)

    @app.get("/api/incidents/export")
    async def export_incidents(
        site_id: str = "",
        severity: Severity | None = None,
        status: Status | None = None,
        vendor: str = "",
        who=Depends(user),
    ):
        rows = visible(who, site_id)
        if severity:
            rows = [r for r in rows if r["severity"] == severity]
        if status:
            rows = [r for r in rows if r["status"] == status]
        if vendor:
            rows = [
                r
                for r in rows
                if (r.get("vendor") or (store.get("site", r["site_id"]) or {}).get("vendor", "Deye")).lower()
                == vendor.lower()
            ]

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(
            [
                "ID",
                "Title",
                "Site ID",
                "Severity",
                "Status",
                "Vendor",
                "Assigned To",
                "Created At",
                "Updated At",
            ]
        )
        for r in rows:
            v = r.get("vendor") or (store.get("site", r["site_id"]) or {}).get("vendor", "Deye")
            writer.writerow(
                [
                    r.get("id"),
                    r.get("title"),
                    r.get("site_id"),
                    r.get("severity"),
                    r.get("status"),
                    v,
                    r.get("assigned_to", ""),
                    r.get("created_at"),
                    r.get("updated_at"),
                ]
            )
        output.seek(0)
        return PlainTextResponse(
            output.getvalue(),
            media_type="text/csv",
            headers={"Content-Disposition": "attachment; filename=incidents_export.csv"},
        )

    @app.get("/api/incident-policies/{site_id}")
    async def policy(site_id: str, who=Depends(user)):
        site(site_id, who)
        return store.get("incident_sla_policy", site_id) or {
            "site_id": site_id,
            "revision": 0,
            "name": "Default 24/7",
            "targets": DEFAULT_SLA,
            "escalation_roles": ["Operator", "Senior Engineer"],
            "default": True,
        }

    @app.post("/api/incident-policies")
    async def save_policy(body: SLAPolicy, who=Depends(configure)):
        site(body.site_id, who)
        with store.transaction():
            old = store.get("incident_sla_policy", body.site_id)
            if body.revision != (old["revision"] if old else 0):
                raise SafetyError("record_changed_reload")
            row = {
                **body.model_dump(),
                "revision": body.revision + 1,
                "updated_by": who.id,
                "updated_at": utcnow().isoformat(),
                "clock": "ELAPSED_24X7",
            }
            store.put("incident_sla_policy", body.site_id, row)
            store.put("incident_sla_version", f"{body.site_id}:{row['revision']}", row)
            store.audit(
                "operations",
                {"event": "incident_sla_policy_changed", "operator": who.id, "revision": row["revision"]},
                body.site_id,
            )
        return row

    @app.get("/api/incident-playbooks")
    async def playbooks(site_id: str = "", who=Depends(user)):
        if site_id:
            site(site_id, who)
        return [
            r
            for r in store.list("incident_playbook")
            if who.can_access(r["site_id"]) and (not site_id or r["site_id"] == site_id)
        ]

    @app.post("/api/incident-playbooks", status_code=201)
    async def create_playbook(body: PlaybookForm, who=Depends(configure)):
        if body.revision:
            raise SafetyError("new_playbook_revision_must_be_zero")
        return save_playbook(uuid.uuid4().hex, body, who)

    @app.post("/api/incident-playbooks/{id}")
    async def update_playbook(id: str, body: PlaybookForm, who=Depends(configure)):
        if not store.get("incident_playbook", id):
            raise HTTPException(404)
        return save_playbook(id, body, who)

    def save_playbook(id, body, who):
        site(body.site_id, who)
        with store.transaction():
            old = store.get("incident_playbook", id)
            if old and old["site_id"] != body.site_id:
                raise SafetyError("playbook_site_immutable")
            if body.revision != (old["revision"] if old else 0):
                raise SafetyError("record_changed_reload")
            row = {
                "id": id,
                **body.model_dump(),
                "revision": body.revision + 1,
                "updated_by": who.id,
                "updated_at": utcnow().isoformat(),
            }
            store.put("incident_playbook", id, row)
            store.put("incident_playbook_version", f"{id}:{row['revision']}", row)
            store.audit(
                "operations",
                {
                    "event": "incident_playbook_saved",
                    "id": id,
                    "operator": who.id,
                    "revision": row["revision"],
                },
                body.site_id,
            )
        return row
