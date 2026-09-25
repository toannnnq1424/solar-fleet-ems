"""UI entry points must use the shared command engine; previews are not writes."""

import pytest
from test_workspaces import local as local
from test_workspaces import login


def test_control_state_has_no_invented_readback(local):
    c, ctl = local
    h = login(local)
    state = c.get("/api/control/device-state/sim-device", headers=h).json()
    assert state["parameters"] == {}
    assert state["telemetry"]["v_grid_v"] is None
    assert state["telemetry"]["work_mode"] is None
    assert state["safety"]["can_write"] is False
    assert ctl.store.commands() == []


@pytest.mark.parametrize("role", ["admin", "operator"])
def test_unknown_intent_cannot_simulate_verified_write(local, role):
    c, ctl = local
    h = login(local, role)
    r = c.post(
        "/api/control/execute",
        headers=h,
        json={"device_id": "sim-device", "intent": "SET_GRID_PROTECTION", "parameters": {"v_nominal": 240}},
    )
    assert r.status_code == 409
    assert "readback_verified" not in r.json()
    assert ctl.store.commands() == []


def test_control_journal_only_contains_recorded_events(local):
    c, ctl = local
    h = login(local)
    assert c.get("/api/control/journal/sim-device", headers=h).json()["journal"] == []
    ctl.store.audit(
        "control", {"device_id": "sim-device", "event": "preview_rejected", "operator": "admin"}, "sim-site"
    )
    row = c.get("/api/control/journal/sim-device", headers=h).json()["journal"][0]
    assert row["action"] == "preview_rejected"
    assert row["time"] == row["details"]["timestamp"]


def test_batch_requires_shared_preview_even_for_known_device(local):
    c, ctl = local
    h = login(local)
    r = c.post(
        "/api/control/batch-dispatch",
        headers=h,
        json={"device_ids": ["sim-device"], "action": "SET_ZERO_EXPORT"},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "use_rollout_preview_and_confirm"
    assert ctl.store.commands() == []


def test_quarantine_policy_and_site_access(local):
    c, _ = local
    h = login(local)
    q = c.get("/api/control/safety-quarantine", headers=h).json()
    assert q["quarantined_count"] == 0
    assert q["safety_policy"]["mode"] == "UNKNOWN_OUTCOME_BLOCKS_RETRY"
    h = login(local, "other")
    assert c.get("/api/control/device-state/sim-device", headers=h).status_code == 403


def test_unknown_device_cannot_be_created_by_control(local):
    c, ctl = local
    h = login(local)
    r = c.post(
        "/api/control/execute",
        headers=h,
        json={"device_id": "missing", "intent": "SET_WORK_MODE", "parameters": {"mode": "Zero-export"}},
    )
    assert r.status_code == 409
    assert ctl.store.get("device", "missing") is None
    assert ctl.store.commands() == []
