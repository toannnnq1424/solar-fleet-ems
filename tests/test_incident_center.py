"""Incident business workflows and fault ordering, using synthetic local data only."""

import sqlite3
from datetime import timedelta

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.domain import Principal, Role, SafetyError, utcnow
from solar_fleet.incident_models import AlarmObservation, IncidentChange
from solar_fleet.incidents import IncidentService, sla_status


def alarm(at, id="event-1", active=True):
    return AlarmObservation(
        namespace="simulator",
        code="TEST_CONNECTIVITY",
        source_event_id=id,
        title="SIMULATOR communication fault",
        description="Synthetic observation",
        severity="high",
        active=active,
        source_timestamp=at,
        evidence_ids=["SIMULATOR-CONTRACT"],
    )


def prepare(store, device):
    service = IncidentService(store)
    store.put("binding", "cloud", {"id": "cloud", "device_id": device.id, "telemetry_enabled": True})
    store.put("binding", "local", {"id": "local", "device_id": device.id, "telemetry_enabled": True})
    return service


def create(local, severity="high"):
    client, _ = local
    headers = login(local, "operator")
    response = client.post(
        "/api/records/incident",
        json={"site_id": "sim-site", "title": "SIMULATOR incident", "severity": severity},
        headers=headers,
    )
    assert response.status_code == 201
    return response.json(), headers


def test_duplicate_and_out_of_order_events_preserve_state(store, device):
    svc, now = prepare(store, device), utcnow()
    event = alarm(now)
    first = svc.apply_alarm(device, "cloud", event, now=now)
    assert svc.apply_alarm(device, "cloud", event, now=now)["state"] == "DUPLICATE"
    assert len(store.list("incident")) == 1
    assert store.get("incident", first["incident_id"])["revision"] == 1
    assert (
        svc.apply_alarm(device, "cloud", alarm(now - timedelta(seconds=1), "older", False), now=now)["state"]
        == "OUT_OF_ORDER"
    )
    assert store.get("incident", first["incident_id"])["equipment_state"] == "ACTIVE"
    with pytest.raises(SafetyError, match="event_id_conflict"):
        svc.apply_alarm(device, "cloud", alarm(now, active=False), now=now)


def test_two_sources_must_both_recover_and_ack_is_not_recovery(store, device):
    svc, now = prepare(store, device), utcnow()
    result = svc.apply_alarm(device, "cloud", alarm(now), now=now)
    id = result["incident_id"]
    svc.apply_alarm(device, "local", alarm(now, "local-start"), now=now)
    who = Principal(id="SIMULATOR", role=Role.OPERATOR, site_ids=[device.site_id])
    row = svc.get(id)
    row = svc.change(
        id, IncidentChange(revision=row["revision"], status="acknowledged", note="Observed"), who
    )
    assert row["equipment_state"] == "ACTIVE"
    with pytest.raises(SafetyError, match="not_recovered"):
        svc.change(id, IncidentChange(revision=row["revision"], status="resolved", note="Try close"), who)
    later = now + timedelta(seconds=2)
    svc.apply_alarm(device, "cloud", alarm(later, "cloud-clear", False), now=later)
    assert svc.get(id)["equipment_state"] == "ACTIVE"
    svc.apply_alarm(device, "local", alarm(later, "local-clear", False), now=later)
    assert svc.get(id)["equipment_state"] == "RECOVERED"
    row = svc.change(
        id, IncidentChange(revision=svc.get(id)["revision"], status="resolved", note="Both clear"), who
    )
    assert row["resolved_at"] and row["acknowledged_at"]
    later += timedelta(seconds=1)
    svc.apply_alarm(device, "cloud", alarm(later, "recurrence"), now=later)
    row = svc.get(id)
    assert row["status"] == "open" and row["occurrences"] == 2 and row["episode"] == 2
    assert row["resolved_at"] is None and row["acknowledged_at"] is None


def test_recovery_before_open_never_creates_false_incident(store, device):
    svc, now = prepare(store, device), utcnow()
    assert svc.apply_alarm(device, "cloud", alarm(now, active=False))["state"] == "RECOVERY_WITHOUT_INCIDENT"
    assert not store.list("incident")
    with pytest.raises(SafetyError, match="binding_invalid"):
        svc.apply_alarm(device, "missing", alarm(now))
    with pytest.raises(SafetyError, match="clock_ahead"):
        svc.apply_alarm(device, "cloud", alarm(now + timedelta(minutes=5)), now=now)


def test_alarm_site_move_requires_reconciliation(store, device):
    svc, now = prepare(store, device), utcnow()
    svc.apply_alarm(device, "cloud", alarm(now), now=now)
    moved = device.model_copy(update={"site_id": "another-site"})
    with pytest.raises(SafetyError, match="site_changed"):
        svc.apply_alarm(moved, "cloud", alarm(now + timedelta(seconds=1), "new"))


def test_event_history_is_atomic_and_append_only(store, device):
    svc, now = prepare(store, device), utcnow()
    with pytest.raises(RuntimeError):
        with store.transaction():
            svc.apply_alarm(device, "cloud", alarm(now))
            raise RuntimeError("SIMULATOR rollback")
    assert not store.list("incident")
    assert store.db.execute("SELECT COUNT(*) FROM incident_events").fetchone()[0] == 0
    assert store.db.execute("SELECT COUNT(*) FROM alarm_receipts").fetchone()[0] == 0
    svc.apply_alarm(device, "cloud", alarm(now))
    for sql in ("UPDATE incident_events SET kind='edited'", "DELETE FROM incident_events"):
        with pytest.raises(sqlite3.IntegrityError, match="append only"):
            store.db.execute(sql)


def test_scoped_lists_counts_detail_and_viewer_writes(local):
    row, _ = create(local)
    client, ctl = local
    headers = login(local, "other")
    assert client.get("/api/incidents").json()["total"] == 0
    assert client.get("/api/incidents/summary").json()["open"] == 0
    assert client.get(f"/api/incidents/{row['id']}/detail").status_code != 200
    assert client.get(f"/api/incidents/{row['id']}/history").status_code != 200
    headers = login(local, "viewer")
    assert (
        client.post(
            f"/api/incidents/{row['id']}/notes", json={"revision": 1, "text": "No"}, headers=headers
        ).status_code
        == 403
    )
    detail = client.get(f"/api/incidents/{row['id']}/detail").json()
    assert all(p["id"] != "other" for p in detail["assignees"])
    assert ctl.store.get("incident", row["id"])["revision"] == 1


def test_assignment_revisions_and_linked_job_transaction(local):
    row, headers = create(local)
    client, ctl = local
    path = f"/api/incidents/{row['id']}"
    body = {"revision": 1, "status": "in_progress", "note": "Investigating", "assigned_to": "engineer"}
    assert client.post(path + "/transition", json=body, headers=headers).status_code == 200
    assert client.post(path + "/transition", json=body, headers=headers).status_code == 409
    job = client.post(
        path + "/work-order",
        json={
            "revision": 2,
            "title": "Repair",
            "instructions": "Inspect connectivity",
            "assigned_to": "engineer",
        },
        headers=headers,
    )
    assert job.status_code == 201
    assert job.json()["incident_id"] == row["id"]
    assert ctl.store.get("incident", row["id"])["revision"] == 3
    history = client.get(path + "/history?limit=2").json()
    assert len(history["items"]) == 2 and history["next_cursor"]
    second = client.get(path + f"/history?after={history['next_cursor']}").json()
    assert len(second["items"]) == 1


def test_sla_snapshot_breach_and_idempotent_escalation(local):
    row, _ = create(local, "critical")
    client, ctl = local
    later = utcnow() + timedelta(minutes=16)
    status = sla_status(row, later)
    assert status["response_breached"] and not status["resolution_breached"]
    ctl.incidents.escalate(later)
    ctl.incidents.escalate(later)
    assert len([n for n in ctl.store.list("notification") if n.get("reason") == "SLA_RESPONSE"]) == 1
    assert (
        len(
            [
                e
                for e in ctl.incidents.history(ctl.incidents.get(row["id"]))["items"]
                if e["kind"] == "incident_sla_breached"
            ]
        )
        == 1
    )


def test_lowering_severity_does_not_erase_original_deadline(local):
    row, headers = create(local, "critical")
    client, _ = local
    updated = client.post(
        f"/api/incidents/{row['id']}/triage",
        json={
            "revision": 1,
            "severity": "low",
            "category": "connectivity",
            "root_cause": "SIMULATOR diagnosis",
            "tags": ["sim", "sim"],
            "note": "Reclassified",
        },
        headers=headers,
    ).json()
    assert updated["sla"]["response_due_at"] == row["sla"]["response_due_at"]
    assert updated["tags"] == ["sim"]


def test_policy_change_applies_to_future_incidents_only(local):
    row, _ = create(local)
    client, _ = local
    headers = login(local, "engineer")
    old = client.get("/api/incident-policies/sim-site").json()
    payload = {k: old[k] for k in ("site_id", "revision", "name", "targets", "escalation_roles")}
    payload["targets"]["high"] = {"response_minutes": 5, "resolution_minutes": 10}
    assert client.post("/api/incident-policies", json=payload, headers=headers).status_code == 200
    assert client.post("/api/incident-policies", json=payload, headers=headers).status_code == 409
    existing = client.get(f"/api/incidents/{row['id']}/detail").json()["incident"]
    assert existing["sla"]["response_minutes"] == 60
    newer, _ = create(local)
    assert newer["sla"]["response_minutes"] == 5


def test_playbook_snapshot_required_evidence_and_resolution_gate(local):
    row, _ = create(local)
    client, _ = local
    headers = login(local, "engineer")
    body = {
        "site_id": "sim-site",
        "name": "SIMULATOR runbook",
        "steps": [
            {
                "id": "network",
                "instruction_vi": "Kiểm tra kết nối",
                "instruction_en": "Inspect connectivity",
                "requires_evidence": True,
            }
        ],
    }
    book = client.post("/api/incident-playbooks", json=body, headers=headers).json()
    path = f"/api/incidents/{row['id']}"
    response = client.post(
        path + "/playbook", json={"revision": 1, "playbook_id": book["id"]}, headers=headers
    )
    assert response.json()["revision"] == 2
    updated = {**body, "revision": 1, "name": "SIMULATOR runbook revised"}
    assert (
        client.post("/api/incident-playbooks/" + book["id"], json=updated, headers=headers).status_code == 200
    )
    assert client.get(path + "/detail").json()["incident"]["playbook"]["revision"] == 1
    assert (
        client.post(
            path + "/check", json={"revision": 2, "step_id": "network", "outcome": "pass"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/transition",
            json={"revision": 2, "status": "acknowledged", "note": "Accepted"},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            path + "/transition", json={"revision": 3, "status": "resolved", "note": "Done"}, headers=headers
        ).status_code
        == 409
    )
    assert (
        client.post(
            path + "/check",
            json={"revision": 3, "step_id": "network", "outcome": "pass", "note": "SIMULATOR evidence"},
            headers=headers,
        ).status_code
        == 200
    )
    assert (
        client.post(
            path + "/transition",
            json={"revision": 4, "status": "resolved", "note": "Completed"},
            headers=headers,
        ).status_code
        == 200
    )


def test_summary_distinguishes_no_measurement_from_zero(local):
    row, headers = create(local)
    client, _ = local
    summary = client.get("/api/incidents/summary").json()
    assert summary["mean_response_seconds"] is None and summary["sla_met_percent"] is None
    assert client.get("/api/incidents?limit=0").status_code == 422
    assert client.get("/api/incidents?severity=invalid").status_code == 422
    assert client.get("/api/incidents?q=missing").json()["total"] == 0
    assert client.get("/api/incidents?unassigned=true").json()["total"] == 1
