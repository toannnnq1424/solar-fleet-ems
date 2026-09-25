"""Week view is a projection of real schedule drafts, never an implicit dispatch."""

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.workspaces import WEEKDAYS


def test_tariff_requires_explicit_site_contract(local):
    c, _ = local
    h = login(local)
    r = c.get("/api/tariffs/evn-current", headers=h).json()
    assert r["rates"] == {}
    assert r["tariffs"] == []


def test_weekly_plan_initially_empty(local):
    c, _ = local
    h = login(local)
    r = c.get("/api/schedules/weekly-plan/sim-site", headers=h).json()
    assert r["schedule_matrix"] == {day: [] for day in WEEKDAYS}
    assert r["can_deploy_physical"] is False
    assert r["impact_projection_7d"] == {}


def test_weekly_save_links_shared_schedule_record(local):
    c, ctl = local
    h = login(local)
    matrix = {day: [] for day in WEEKDAYS}
    matrix["monday"] = [
        {"start": "01:00", "end": "03:00", "action": "CHARGE", "target_soc": 80, "max_power_kw": 3}
    ]
    r = c.post(
        "/api/schedules/weekly-plan/sim-site",
        headers=h,
        json={"name": "Night draft", "schedule_matrix": matrix},
    )
    assert r.status_code == 200, r.text
    row = ctl.store.get("schedule", r.json()["schedule_id"])
    assert row["state"] == "DRAFT"
    assert row["slots"][0] == {
        "day": 0,
        "start": "01:00",
        "end": "03:00",
        "mode": "charge",
        "target_soc": 80,
        "power_kw": 3,
    }
    assert ctl.store.commands() == []
    assert c.get("/api/schedules/weekly-plan/sim-site", headers=h).json()["schedule_id"] == row["id"]
    assert any(s["id"] == row["id"] for s in c.get("/api/operations", headers=h).json()["schedule"])


@pytest.mark.parametrize(
    "slot",
    [
        None,
        {"start": "bad", "end": "03:00", "action": "CHARGE"},
        {"start": "01:00", "end": "00:30", "action": "CHARGE"},
    ],
)
def test_malformed_weekly_slot_is_validation_error(local, slot):
    c, ctl = local
    h = login(local)
    matrix = {day: [] for day in WEEKDAYS}
    matrix["monday"] = [slot]
    r = c.post("/api/schedules/weekly-plan/sim-site", headers=h, json={"schedule_matrix": matrix})
    assert r.status_code == 422
    assert ctl.store.list("schedule") == []


def test_attestation_alone_does_not_dispatch_schedule(local):
    c, ctl = local
    h = login(local)
    ctl.store.put("commissioning", "c", {"id": "c", "site_id": "sim-site", "status": "APPROVED"})
    r = c.post("/api/schedules/deploy-to-hardware", headers=h, json={"site_id": "sim-site"})
    assert r.status_code == 409
    assert ctl.store.commands() == []
