"""Maintenance lifecycle contracts. All identities, devices and evidence are synthetic."""

import sqlite3
from datetime import timedelta

import pytest

from solar_fleet.domain import Role, Sample, Source, utcnow
from solar_fleet.security import create_user
from test_workspaces import PASSWORD, local as local, login


def job(local, *, device_id=None, due_date=None):
    client, controller = local
    if not controller.store.db.execute("SELECT id FROM users WHERE id='reviewer'").fetchone():
        create_user(controller.store, "reviewer", PASSWORD, Role.INSTALLER, ["sim-site"])
    response = client.post("/api/records/work_order", headers=login(local, "engineer"), json={
        "site_id": "sim-site", "title": "SIMULATOR inspection", "device_id": device_id, "due_date": due_date,
    })
    assert response.status_code == 201
    return response.json()["id"]


def detail(local, id):
    response = local[0].get(f"/api/maintenance/work-orders/{id}")
    assert response.status_code == 200
    return response.json()


def mutate(local, id, action, values=None, user="engineer"):
    client, _ = local
    headers = login(local, user)
    revision = detail(local, id)["work_order"]["revision"]
    return client.post(f"/api/maintenance/work-orders/{id}/{action}",
                       json={"revision": revision, **(values or {})}, headers=headers)


def plan(local, id, **overrides):
    values = {"steps": [{"id": "visual", "title": "Inspect the simulator", "instructions": "Record synthetic observation"}],
              "safety_note": "SIMULATOR only; no equipment actuation", "note": "Prepare the synthetic job", "team": ["engineer"]}
    response = mutate(local, id, "plan", {**values, **overrides})
    assert response.status_code == 200
    return response.json()


def ready(local, id, documents=None):
    plan(local, id)
    response = mutate(local, id, "step", {"step_id": "visual", "outcome": "pass", "note": "SIMULATOR measurements recorded", "document_ids": documents or []})
    assert response.status_code == 200
    now = utcnow()
    response = mutate(local, id, "time", {"start": (now - timedelta(hours=2)).isoformat(),
        "end": (now - timedelta(hours=1)).isoformat(), "activity": "Inspect synthetic logger"})
    assert response.status_code == 201
    response = mutate(local, id, "submit", {"note": "Please independently review the evidence"})
    assert response.status_code == 200
    return detail(local, id)


def status(local, id, value, user="engineer"):
    client, _ = local
    headers = login(local, user)
    row = detail(local, id)["work_order"]
    return client.post(f"/api/records/work_order/{id}", headers=headers, json={
        "revision": row["revision"], "status": value, "assigned_to": row["assigned_to"], "note": "SIMULATOR lifecycle transition",
    })


def test_execution_requires_independent_review_and_reopen_invalidates_it(local):
    id = job(local)
    ready(local, id)
    own = mutate(local, id, "review", {"decision": "approve", "note": "Attempt self approval"})
    assert own.status_code == 409 and own.json()["error"] == "maintenance_independent_reviewer_required"
    assert status(local, id, "in_progress").status_code == 200
    assert status(local, id, "resolved").json()["error"] == "maintenance_review_required"
    approval = mutate(local, id, "review", {"decision": "approve", "note": "Independent evidence check"}, user="reviewer")
    assert approval.status_code == 200
    assert len(approval.json()["review"]["execution_digest"]) == 64
    assert status(local, id, "resolved").status_code == 200
    assert status(local, id, "closed").status_code == 200
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "pass", "note": "Late edit"}).json()["error"] == "work_order_completed_reopen_first"
    assert status(local, id, "open").status_code == 200
    assert detail(local, id)["execution"]["review"] is None
    assert status(local, id, "in_progress").status_code == 200
    assert status(local, id, "resolved").json()["error"] == "maintenance_review_required"


def test_unstructured_generic_work_order_cannot_bypass_execution_gate(local):
    id = job(local)
    assert status(local, id, "in_progress").status_code == 200
    result = status(local, id, "resolved")
    assert result.status_code == 409
    assert result.json()["error"] == "maintenance_execution_incomplete"


def test_missing_failed_and_not_applicable_check_results(local):
    id = job(local)
    plan(local, id)
    gate = detail(local, id)["completion"]
    assert gate["reasons"] == ["required_step_incomplete:visual", "work_time_entry_required"]
    assert mutate(local, id, "submit", {"note": "Premature submission"}).status_code == 409
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "fail", "note": "Synthetic fault"}).status_code == 200
    assert "failed_step:visual" in detail(local, id)["completion"]["reasons"]
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "not_applicable", "note": ""}).status_code == 422
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "not_applicable", "note": "This synthetic device lacks the component"}).status_code == 200
    assert detail(local, id)["completion"]["reasons"] == ["work_time_entry_required"]


def test_new_plan_clears_results_and_preserves_previous_version_and_events(local):
    client, controller = local
    id = job(local)
    ready(local, id)
    assert mutate(local, id, "review", {"decision": "approve", "note": "Accepted"}, user="reviewer").status_code == 200
    updated = plan(local, id, steps=[{"id": "visual", "title": "Changed instructions", "instructions": "Repeat inspection"}])
    assert updated["version"] == 2 and updated["results"] == {} and updated["review"] is None
    archived = controller.store.get("work_execution_version", f"{id}:1")
    assert archived["review"]["decision"] == "approve"
    assert archived["results"]["visual"]["outcome"] == "pass"
    events = client.get(f"/api/maintenance/work-orders/{id}/events").json()["items"]
    assert any(event["details"].get("result", {}).get("note") == "SIMULATOR measurements recorded" for event in events)
    with pytest.raises(sqlite3.IntegrityError, match="append only"):
        controller.store.db.execute("DELETE FROM maintenance_events")
    with pytest.raises(sqlite3.IntegrityError, match="append only"):
        controller.store.db.execute("UPDATE maintenance_events SET body='{}'")
    assert controller.store.verify_audit()


def test_time_overlap_across_orders_and_void_keep_evidence(local):
    first, second = job(local), job(local)
    now = utcnow()
    period = {"start": (now - timedelta(hours=2)).isoformat(), "end": (now - timedelta(hours=1)).isoformat(), "activity": "Synthetic work"}
    entry = mutate(local, first, "time", period).json()
    assert mutate(local, second, "time", period).json()["error"] == "work_time_overlap"
    assert mutate(local, first, "time/" + entry["id"] + "/void", {"note": "Wrong order"}, user="reviewer").status_code == 409
    assert mutate(local, first, "time/" + entry["id"] + "/void", {"note": "Wrong order"}).status_code == 200
    assert detail(local, first)["total_minutes"] == 0
    assert detail(local, first)["time_entries"][0]["void_reason"] == "Wrong order"
    assert mutate(local, second, "time", period).status_code == 201
    adjacent = {**period, "start": period["end"], "end": (now - timedelta(minutes=30)).isoformat()}
    assert mutate(local, second, "time", adjacent).status_code == 201


@pytest.mark.parametrize("values", [
    {"start": "2026-01-01T08:00:00", "end": "2026-01-01T09:00:00"},
    {"start": "2026-01-01T08:00:00Z", "end": "2026-01-01T08:00:00Z"},
    {"start": "2026-01-01T08:00:00Z", "end": "2026-01-02T09:00:00Z"},
])
def test_invalid_time_ranges_rejected(local, values):
    id = job(local)
    assert mutate(local, id, "time", {**values, "activity": "Invalid period"}).status_code == 422


def test_future_time_rejected_and_work_contributor_cannot_review(local):
    id = job(local)
    ready(local, id)
    now = utcnow()
    future = {"start": now.isoformat(), "end": (now + timedelta(hours=1)).isoformat(), "activity": "Future work"}
    assert mutate(local, id, "time", future).json()["error"] == "work_time_in_future"
    own_time = {"start": (now - timedelta(hours=4)).isoformat(), "end": (now - timedelta(hours=3)).isoformat(), "activity": "Reviewer's earlier participation"}
    assert mutate(local, id, "time", own_time, user="reviewer").status_code == 201
    assert mutate(local, id, "submit", {"note": "All time recorded"}).status_code == 200
    assert mutate(local, id, "review", {"decision": "approve", "note": "Attempt approval"}, user="reviewer").json()["error"] == "maintenance_independent_reviewer_required"


def test_void_after_approval_invalidates_review_and_completion(local):
    id = job(local)
    data = ready(local, id)
    assert mutate(local, id, "review", {"decision": "approve", "note": "Checked"}, user="reviewer").status_code == 200
    entry = data["time_entries"][0]
    assert mutate(local, id, f"time/{entry['id']}/void", {"note": "Time recorded incorrectly"}).status_code == 200
    result = detail(local, id)
    assert result["execution"]["review"] is None
    assert not result["completion"]["ready"]


def test_revoked_reviewer_or_archived_evidence_blocks_completion(local):
    client, controller = local
    id = job(local)
    controller.store.put("document", "evidence", {"id": "evidence", "site_id": "sim-site", "name": "SIMULATOR evidence", "archived": False})
    ready(local, id, ["evidence"])
    assert mutate(local, id, "review", {"decision": "approve", "note": "Checked"}, user="reviewer").status_code == 200
    assert status(local, id, "in_progress").status_code == 200
    controller.store.db.execute("UPDATE users SET active=0 WHERE id='reviewer'")
    assert status(local, id, "resolved").json()["error"] == "maintenance_reviewer_no_longer_authorized"
    controller.store.db.execute("UPDATE users SET active=1 WHERE id='reviewer'")
    doc = controller.store.get("document", "evidence")
    controller.store.put("document", "evidence", {**doc, "archived": True})
    assert status(local, id, "resolved").json()["error"] == "maintenance_execution_incomplete"
    assert "evidence_unavailable:visual" in detail(local, id)["completion"]["reasons"]


def test_replaced_document_version_requires_fresh_step_evidence(local):
    _, controller = local
    id = job(local)
    original = {"id": "versioned", "site_id": "sim-site", "name": "SIMULATOR evidence", "revision": 1, "sha256": "1" * 64}
    controller.store.put("document", "versioned", original)
    ready(local, id, ["versioned"])
    assert mutate(local, id, "review", {"decision": "approve", "note": "Reviewed original"}, user="reviewer").status_code == 200
    controller.store.put("document", "versioned", {**original, "revision": 2, "sha256": "2" * 64})
    assert "evidence_changed:visual" in detail(local, id)["completion"]["reasons"]
    assert status(local, id, "in_progress").status_code == 200
    assert status(local, id, "resolved").status_code == 409
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "pass", "note": "Checked replacement evidence", "document_ids": ["versioned"]}).status_code == 200
    assert detail(local, id)["completion"]["ready"] is True
    assert detail(local, id)["execution"]["review"] is None


def test_scope_roles_team_and_documents_enforced(local):
    client, controller = local
    id = job(local)
    plan(local, id)
    for user in ["viewer", "admin"]:
        assert mutate(local, id, "step", {"step_id": "visual", "outcome": "pass", "note": "Restricted action"}, user=user).status_code == 403
    rejected = mutate(local, id, "plan", {"steps": [{"id": "x", "title": "New step"}], "team": ["other"], "safety_note": "Simulator", "note": "Cross-site member"})
    assert rejected.status_code == 409
    controller.store.put("document", "foreign", {"id": "foreign", "site_id": "other-site", "name": "Foreign evidence"})
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "pass", "note": "Attempt foreign evidence", "document_ids": ["foreign"]}).status_code == 409
    login(local, "other")
    assert client.get(f"/api/maintenance/work-orders/{id}").status_code == 403
    assert client.get(f"/api/maintenance/work-orders/{id}/events").status_code == 403
    assert client.get("/api/maintenance/work-orders").json()["items"] == []
    assert client.get("/api/maintenance/calendar?start=2026-01-01&end=2026-02-01").json()["items"] == []


def test_stale_revision_does_not_overwrite_new_result(local):
    client, _ = local
    id = job(local)
    plan(local, id)
    headers = login(local, "engineer")
    revision = detail(local, id)["work_order"]["revision"]
    values = {"revision": revision, "step_id": "visual", "outcome": "pass", "note": "First observation"}
    assert client.post(f"/api/maintenance/work-orders/{id}/step", headers=headers, json=values).status_code == 200
    response = client.post(f"/api/maintenance/work-orders/{id}/step", headers=headers, json={**values, "outcome": "fail"})
    assert response.status_code == 409 and response.json()["error"] == "record_changed_reload"
    assert detail(local, id)["execution"]["results"]["visual"]["outcome"] == "pass"


def test_calendar_uses_plant_timezone_and_projects_without_creating_orders(local):
    client, controller = local
    id = job(local)
    plan(local, id, planned_start="2026-09-20T18:00:00Z", planned_end="2026-09-20T20:00:00Z")
    controller.store.put("maintenance_plan", "recurring", {"id": "recurring", "name": "SIMULATOR cycle", "site_id": "sim-site",
        "enabled": True, "next_due": "2026-09-01", "interval_days": 7})
    page = client.get("/api/maintenance/calendar?start=2026-09-21&end=2026-10-01").json()
    real = next(row for row in page["items"] if row["kind"] == "work_order")
    assert real["date"] == "2026-09-21" and real["start_at"].endswith("+07:00")
    projected = [row for row in page["items"] if row["kind"] == "recurrence"]
    assert [row["date"] for row in projected] == ["2026-09-22", "2026-09-29"]
    assert all(row["overdue_anchor"] == "2026-09-01" for row in projected)
    assert len(controller.store.list("work_order")) == 1
    assert client.get("/api/maintenance/calendar?start=2026-01-01&end=2027-01-01").status_code == 409


def test_health_reports_observation_limits_without_invented_health_or_firmware(local, device):
    client, controller = local
    job(local, device_id=device.id, due_date="2020-01-01")
    login(local, "engineer")
    first = client.get("/api/maintenance/health").json()["items"]
    assert len(first) == 1 and first[0]["state"] == "NEEDS_ATTENTION"
    assert first[0]["electrical_health_score"] is None and first[0]["firmware_currency"] == "UNKNOWN"
    assert first[0]["open_work_orders"] == 1
    assert client.get("/api/maintenance/work-orders?overdue=true").json()["total"] == 1
    sample = Sample(device_id=device.id, metric="pv_power_w", value=1000, unit="W", source=Source.SIMULATOR,
                    source_timestamp=utcnow(), quality="GOOD", stale=False, binding_id="SIMULATOR")
    controller.store.put("latest", device.id, {"device_id": device.id, "samples": [sample.model_dump(mode="json")]})
    second = client.get("/api/maintenance/health").json()["items"][0]
    assert second["state"] == "OBSERVABLE" and second["verified_channels"] == 1
    assert second["electrical_health_score"] is None


def test_return_for_changes_requires_new_submission(local):
    id = job(local)
    ready(local, id)
    response = mutate(local, id, "review", {"decision": "return", "note": "Need a clearer evidence note"}, user="reviewer")
    assert response.status_code == 200 and response.json()["state"] == "CHANGES_REQUESTED"
    assert mutate(local, id, "review", {"decision": "approve", "note": "No fresh submission"}, user="reviewer").status_code == 409
    assert mutate(local, id, "step", {"step_id": "visual", "outcome": "pass", "note": "Updated synthetic measurements"}).status_code == 200
    assert mutate(local, id, "submit", {"note": "Additional evidence recorded"}).status_code == 200
    assert mutate(local, id, "review", {"decision": "approve", "note": "Accepted after changes"}, user="reviewer").status_code == 200
