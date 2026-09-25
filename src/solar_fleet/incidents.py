"""Alarm correlation and incident lifecycle with atomic audit, SLA and immutable event history."""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import datetime, timedelta

from .domain import Role, SafetyError, utcnow
from .incident_models import RANK, TRANSITIONS, AlarmObservation
from .security import principal
from .storage import encoded


def timestamp(value):
    return datetime.fromisoformat(value) if isinstance(value, str) else value


def initialize_incidents(store):
    store.db.executescript("""
        CREATE TABLE IF NOT EXISTS incident_events(
            seq INTEGER PRIMARY KEY AUTOINCREMENT, incident_id TEXT NOT NULL,
            site_id TEXT NOT NULL, event_id TEXT NOT NULL UNIQUE, at TEXT NOT NULL,
            kind TEXT NOT NULL, body TEXT NOT NULL);
        CREATE INDEX IF NOT EXISTS incident_event_lookup ON incident_events(incident_id,seq);
        CREATE TRIGGER IF NOT EXISTS incident_events_no_update BEFORE UPDATE ON incident_events
            BEGIN SELECT RAISE(ABORT,'incident events are append only'); END;
        CREATE TRIGGER IF NOT EXISTS incident_events_no_delete BEFORE DELETE ON incident_events
            BEGIN SELECT RAISE(ABORT,'incident events are append only'); END;
        CREATE TABLE IF NOT EXISTS alarm_receipts(
            source_key TEXT NOT NULL, event_id TEXT NOT NULL, digest TEXT NOT NULL,
            received_at TEXT NOT NULL, PRIMARY KEY(source_key,event_id));
    """)


DEFAULT_SLA = {
    "critical": {"response_minutes": 15, "resolution_minutes": 240},
    "high": {"response_minutes": 60, "resolution_minutes": 480},
    "medium": {"response_minutes": 240, "resolution_minutes": 1440},
    "low": {"response_minutes": 1440, "resolution_minutes": 4320},
}


def sla_snapshot(store, site_id, severity, now):
    policy = store.get("incident_sla_policy", site_id)
    target = (policy["targets"] if policy else DEFAULT_SLA)[severity]
    return {
        "policy_id": site_id if policy else "default_24x7",
        "policy_revision": policy["revision"] if policy else 1,
        "clock": "ELAPSED_24X7",
        "started_at": now.isoformat(),
        "response_due_at": (now + timedelta(minutes=target["response_minutes"])).isoformat(),
        "resolution_due_at": (now + timedelta(minutes=target["resolution_minutes"])).isoformat(),
        "response_minutes": target["response_minutes"],
        "resolution_minutes": target["resolution_minutes"],
        "escalation_roles": policy["escalation_roles"] if policy else ["Operator", "Senior Engineer"],
    }


def sla_status(row, now=None):
    now = now or utcnow()
    sla = row.get("sla")
    if not sla:
        return {"state": "NOT_CONFIGURED", "response_seconds": None, "resolution_seconds": None}
    start = timestamp(sla["started_at"])
    result = {"clock": sla["clock"], "started_at": sla["started_at"], "state": "ON_TRACK"}
    for name, completion in (
        ("response", row.get("acknowledged_at")),
        ("resolution", row.get("resolved_at")),
    ):
        end = timestamp(completion) if completion else now
        due = timestamp(sla[name + "_due_at"])
        breached = end > due
        result[name + "_due_at"] = due.isoformat()
        result[name + "_seconds"] = max(0, (end - start).total_seconds()) if completion else None
        result[name + "_remaining_seconds"] = None if completion else max(0, (due - now).total_seconds())
        result[name + "_breached"] = breached
        result[name + "_completed"] = bool(completion)
        if breached:
            result["state"] = "BREACHED"
    if row["status"] in {"resolved", "closed"} and result["state"] != "BREACHED":
        result["state"] = "MET"
    return result


class IncidentService:
    def __init__(self, store):
        self.store = store
        initialize_incidents(store)

    def get(self, id, who=None):
        row = self.store.get("incident", id)
        if not row:
            raise SafetyError("incident_not_found")
        if who and not who.can_access(row["site_id"]):
            raise SafetyError("site_access_denied")
        return row

    def assignee(self, id, site_id):
        if id:
            user = principal(self.store, id)
            if not user or not user.can_access(site_id) or user.role == Role.VIEWER:
                raise SafetyError("incident_assignee_not_authorized")

    def expected(self, row, revision):
        if row["revision"] != revision:
            raise SafetyError("record_changed_reload")

    def append(self, row, kind, actor, note, *, now=None, details=None):
        now = now or utcnow()
        event = {
            "id": uuid.uuid4().hex,
            "at": now.isoformat(),
            "actor": actor,
            "kind": kind,
            "status": row["status"],
            "note": note,
            "details": details or {},
        }
        self.store.db.execute(
            "INSERT INTO incident_events(incident_id,site_id,event_id,at,kind,body) VALUES(?,?,?,?,?,?)",
            (row["id"], row["site_id"], event["id"], event["at"], kind, encoded(event)),
        )
        row["timeline"] = [*row.get("timeline", []), event][-250:]
        row["updated_at"] = now.isoformat()
        row["revision"] += 1
        self.store.put("incident", row["id"], row)
        self.store.audit(
            "operations",
            {"event": kind, "id": row["id"], "operator": actor, "revision": row["revision"]},
            row["site_id"],
        )
        return row

    def create_manual(self, body, who):
        now = utcnow()
        self.assignee(body.assigned_to, body.site_id)
        row = {
            "id": uuid.uuid4().hex,
            "status": "open",
            "revision": 0,
            "created_at": now.isoformat(),
            "source": "MANUAL",
            "category": "other",
            "tags": [],
            "occurrences": 1,
            "episode": 1,
            "equipment_state": "UNKNOWN",
            **body.model_dump(),
            "sla": sla_snapshot(self.store, body.site_id, body.severity, now),
        }
        with self.store.transaction():
            return self.append(row, "incident_created", who.id, body.description, now=now)

    def change(self, id, body, who):
        with self.store.transaction():
            row = self.get(id, who)
            self.expected(row, body.revision)
            self.assignee(body.assigned_to, row["site_id"])
            if body.status not in TRANSITIONS[row["status"]]:
                raise SafetyError("invalid_status_transition")
            if body.status in {"resolved", "closed"} and row.get("source") == "ADAPTER_ALARM":
                if row.get("equipment_state") != "RECOVERED":
                    raise SafetyError("equipment_alarm_not_recovered")
            if body.status in {"resolved", "closed"}:
                pending = [
                    s
                    for s in row.get("playbook", {}).get("steps", [])
                    if row.get("playbook_results", {}).get(s["id"], {}).get("outcome")
                    not in {"pass", "not_applicable"}
                ]
                if pending:
                    raise SafetyError("playbook_steps_incomplete")
            now = utcnow()
            previous = row["status"]
            if previous in {"resolved", "closed"} and body.status == "open":
                row.update(
                    episode=row.get("episode", 1) + 1,
                    acknowledged_at=None,
                    resolved_at=None,
                    closed_at=None,
                    playbook_results={},
                    sla=sla_snapshot(self.store, row["site_id"], row["severity"], now),
                )
            if body.status in {"acknowledged", "in_progress", "resolved"} and not row.get("acknowledged_at"):
                row["acknowledged_at"] = now.isoformat()
            if body.status == "resolved" and not row.get("resolved_at"):
                row["resolved_at"] = now.isoformat()
            if body.status == "closed" and not row.get("closed_at"):
                row["closed_at"] = now.isoformat()
            row.update(status=body.status, assigned_to=body.assigned_to)
            return self.append(
                row,
                "incident_transition",
                who.id,
                body.note,
                now=now,
                details={"from": previous, "to": body.status},
            )

    def note(self, id, body, who):
        with self.store.transaction():
            row = self.get(id, who)
            self.expected(row, body.revision)
            return self.append(row, "incident_note", who.id, body.text)

    def triage(self, id, body, who):
        with self.store.transaction():
            row = self.get(id, who)
            self.expected(row, body.revision)
            previous = row["severity"]
            row.update(
                severity=body.severity, category=body.category, root_cause=body.root_cause, tags=body.tags
            )
            # Raising urgency may shorten the original deadline; lowering it never hides a breach.
            if RANK[body.severity] < RANK[previous] and row.get("sla"):
                updated = sla_snapshot(
                    self.store, row["site_id"], body.severity, timestamp(row["sla"]["started_at"])
                )
                for key in ("response_due_at", "resolution_due_at"):
                    row["sla"][key] = min(row["sla"][key], updated[key])
            return self.append(
                row,
                "incident_triaged",
                who.id,
                body.note,
                details={"severity_from": previous, "severity_to": body.severity},
            )

    def apply_alarm(self, device, binding_id, observation: AlarmObservation, *, now=None):
        now = now or utcnow()
        binding = self.store.get("binding", binding_id)
        if (
            not binding
            or binding.get("device_id") != device.id
            or not binding.get("telemetry_enabled", binding.get("enabled", False))
        ):
            raise SafetyError("alarm_binding_invalid")
        if observation.source_timestamp > now + timedelta(seconds=60):
            raise SafetyError("alarm_clock_ahead")
        fingerprint = hashlib.sha256(
            encoded([device.id, observation.namespace, observation.code]).encode()
        ).hexdigest()
        source_key = hashlib.sha256(encoded([fingerprint, binding_id]).encode()).hexdigest()
        digest = hashlib.sha256(observation.model_dump_json().encode()).hexdigest()
        with self.store.transaction():
            receipt = self.store.db.execute(
                "SELECT digest FROM alarm_receipts WHERE source_key=? AND event_id=?",
                (source_key, observation.source_event_id),
            ).fetchone()
            if receipt:
                if receipt[0] != digest:
                    raise SafetyError("alarm_event_id_conflict")
                return {
                    "state": "DUPLICATE",
                    "incident_id": (self.store.get("alarm_correlation", fingerprint) or {}).get(
                        "incident_id"
                    ),
                }
            source = self.store.get("alarm_source", source_key)
            if source and observation.source_timestamp <= timestamp(source["source_timestamp"]):
                return {"state": "OUT_OF_ORDER", "incident_id": source.get("incident_id")}
            correlation = self.store.get("alarm_correlation", fingerprint)
            row = self.store.get("incident", correlation["incident_id"]) if correlation else None
            if row and row["site_id"] != device.site_id:
                raise SafetyError("alarm_device_site_changed")
            self.store.db.execute(
                "INSERT INTO alarm_receipts VALUES(?,?,?,?)",
                (source_key, observation.source_event_id, digest, now.isoformat()),
            )
            # Sources persist their newest timestamp after receipt compaction, retaining replay protection.
            self.store.db.execute(
                "DELETE FROM alarm_receipts WHERE received_at<?", ((now - timedelta(days=30)).isoformat(),)
            )
            self.store.put(
                "alarm_source",
                source_key,
                {
                    "id": source_key,
                    "site_id": device.site_id,
                    "device_id": device.id,
                    "fingerprint": fingerprint,
                    "binding_id": binding_id,
                    "active": observation.active,
                    "source_timestamp": observation.source_timestamp.isoformat(),
                    "received_at": now.isoformat(),
                    "incident_id": row["id"] if row else None,
                    "evidence_ids": observation.evidence_ids,
                },
            )
            if row is None and not observation.active:
                return {"state": "RECOVERY_WITHOUT_INCIDENT", "incident_id": None}
            if row is None:
                row = {
                    "id": uuid.uuid4().hex,
                    "site_id": device.site_id,
                    "device_id": device.id,
                    "title": observation.title,
                    "description": observation.description,
                    "severity": observation.severity,
                    "source": "ADAPTER_ALARM",
                    "category": "other",
                    "alarm_code": observation.code,
                    "namespace": observation.namespace,
                    "fingerprint": fingerprint,
                    "status": "open",
                    "assigned_to": "",
                    "revision": 0,
                    "created_at": now.isoformat(),
                    "first_observed_at": observation.source_timestamp.isoformat(),
                    "occurrences": 1,
                    "episode": 1,
                    "tags": [],
                    "sla": sla_snapshot(self.store, device.site_id, observation.severity, now),
                }
                kind = "alarm_opened"
            elif observation.active and row.get("equipment_state") == "RECOVERED":
                row["occurrences"] = row.get("occurrences", 1) + 1
                kind = "alarm_recurred"
                if row["status"] in {"resolved", "closed"}:
                    row.update(
                        status="open",
                        episode=row.get("episode", 1) + 1,
                        acknowledged_at=None,
                        resolved_at=None,
                        closed_at=None,
                        playbook_results={},
                        sla=sla_snapshot(self.store, row["site_id"], observation.severity, now),
                    )
            else:
                kind = "alarm_observed" if observation.active else "alarm_source_recovered"
            sources = [s for s in self.store.list("alarm_source") if s["fingerprint"] == fingerprint]
            row["equipment_state"] = "ACTIVE" if any(s["active"] for s in sources) else "RECOVERED"
            row["last_observed_at"] = max(s["source_timestamp"] for s in sources)
            row["alarm_sources"] = [s["id"] for s in sources]
            if row["equipment_state"] == "RECOVERED":
                row["recovered_at"] = now.isoformat()
            else:
                row["recovered_at"] = None
            self.append(
                row,
                kind,
                "adapter",
                observation.description,
                now=now,
                details={
                    "binding_id": binding_id,
                    "active": observation.active,
                    "source_timestamp": observation.source_timestamp.isoformat(),
                    "evidence_ids": observation.evidence_ids,
                },
            )
            self.store.put(
                "alarm_correlation",
                fingerprint,
                {"id": fingerprint, "incident_id": row["id"], "site_id": row["site_id"]},
            )
            current = self.store.get("alarm_source", source_key)
            current["incident_id"] = row["id"]
            self.store.put("alarm_source", source_key, current)
            return {"state": kind.upper(), "incident_id": row["id"]}

    def history(self, row, *, after=0, limit=100):
        events = self.store.db.execute(
            "SELECT seq,body FROM incident_events WHERE incident_id=? AND seq>? ORDER BY seq LIMIT ?",
            (row["id"], after, limit + 1),
        ).fetchall()
        items = [{**json.loads(r["body"]), "seq": r["seq"]} for r in events[:limit]]
        return {
            "items": items,
            "next_cursor": items[-1]["seq"] if len(events) > limit else None,
            "legacy_timeline": row.get("timeline", []) if not events and after == 0 else [],
        }

    def attach_playbook(self, id, body, who):
        with self.store.transaction():
            row = self.get(id, who)
            self.expected(row, body.revision)
            book = self.store.get("incident_playbook", body.playbook_id)
            if not book or book["site_id"] != row["site_id"] or not book["enabled"]:
                raise SafetyError("playbook_unavailable_for_site")
            if row["status"] in {"resolved", "closed"}:
                raise SafetyError("incident_already_resolved")
            row.update(playbook=book, playbook_results={})
            return self.append(
                row,
                "playbook_attached",
                who.id,
                book["name"],
                details={"playbook_id": book["id"], "revision": book["revision"]},
            )

    def check_step(self, id, body, who):
        with self.store.transaction():
            row = self.get(id, who)
            self.expected(row, body.revision)
            if row["status"] in {"resolved", "closed"}:
                raise SafetyError("incident_already_resolved")
            step = next(
                (s for s in row.get("playbook", {}).get("steps", []) if s["id"] == body.step_id), None
            )
            if not step:
                raise SafetyError("playbook_step_not_found")
            if (
                body.outcome != "pending"
                and (step["requires_evidence"] or body.outcome == "not_applicable")
                and not body.note.strip()
            ):
                raise SafetyError("playbook_evidence_required")
            row.setdefault("playbook_results", {})[body.step_id] = {
                "outcome": body.outcome,
                "note": body.note,
                "actor": who.id,
                "at": utcnow().isoformat(),
            }
            return self.append(
                row,
                "playbook_step_recorded",
                who.id,
                body.note,
                details={"step_id": body.step_id, "outcome": body.outcome},
            )

    def work_order(self, id, body, who):
        with self.store.transaction():
            row = self.get(id, who)
            self.expected(row, body.revision)
            self.assignee(body.assigned_to, row["site_id"])
            now = utcnow().isoformat()
            job = {
                "id": uuid.uuid4().hex,
                "site_id": row["site_id"],
                "incident_id": id,
                "device_id": row.get("device_id"),
                "title": body.title,
                "description": body.instructions,
                "severity": row["severity"],
                "assigned_to": body.assigned_to,
                "due_date": body.due_date,
                "status": "open",
                "revision": 1,
                "source": "INCIDENT",
                "created_at": now,
                "updated_at": now,
                "timeline": [{"at": now, "actor": who.id, "status": "open", "note": body.instructions}],
            }
            self.store.put("work_order", job["id"], job)
            self.append(
                row,
                "incident_work_order_created",
                who.id,
                body.instructions,
                details={"work_order_id": job["id"]},
            )
            return job

    def escalate(self, now=None):
        now = now or utcnow()
        for row in self.store.list("incident"):
            if row["status"] in {"resolved", "closed"} or not row.get("sla"):
                continue
            status = sla_status(row, now)
            for stage in ("response", "resolution"):
                if not status[stage + "_breached"] or status[stage + "_completed"]:
                    continue
                key = f"incident-sla:{row['id']}:{row.get('episode', 1)}:{stage}"
                with self.store.transaction():
                    if self.store.get("notification", key):
                        continue
                    self.store.put(
                        "notification",
                        key,
                        {
                            "id": key,
                            "site_id": row["site_id"],
                            "title": row["title"],
                            "severity": row["severity"],
                            "reference": {"kind": "incident", "id": row["id"]},
                            "created_at": now.isoformat(),
                            "channel": "in_app",
                            "read_by": [],
                            "reason": "SLA_" + stage.upper(),
                            "escalation_roles": row["sla"]["escalation_roles"],
                        },
                    )
                    self.append(row, "incident_sla_breached", "scheduler", stage, now=now)
