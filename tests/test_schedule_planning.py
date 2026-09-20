"""Pure schedule semantics and local compilation workflows; all hardware remains synthetic."""

from datetime import date

import pytest

from solar_fleet.domain import SafetyError
from solar_fleet.schedule_planning import ProgramSlot, WeeklyProgram, expand_program, require_schedule_source, schedule_digest
from test_workspaces import local as local, login
from test_capability_profiles import profile_for


def full_week(zone="Asia/Ho_Chi_Minh", dst="reject"):
    return WeeklyProgram(zone, tuple(ProgramSlot(day, 0, 1440, "self_use", None, None) for day in range(7)), "reject", dst)


def test_full_week_preserves_timezone_and_half_open_boundaries():
    result = expand_program(full_week(), date(2026, 9, 21), 7)
    assert len(result["windows"]) == 7 and not result["gaps"]
    assert result["windows"][0]["start_at"] == "2026-09-20T17:00:00+00:00"
    for left, right in zip(result["windows"], result["windows"][1:]):
        assert left["end_at"] == right["start_at"]


def test_dst_day_length_requires_explicit_policy():
    with pytest.raises(SafetyError, match="crosses_dst"):
        expand_program(full_week("America/New_York"), date(2026, 3, 8), 1)
    assert expand_program(full_week("America/New_York", "earlier"), date(2026, 3, 8), 1)["windows"][0]["duration_seconds"] == 23 * 3600
    assert expand_program(full_week("America/New_York", "later"), date(2026, 11, 1), 1)["windows"][0]["duration_seconds"] == 25 * 3600


def test_nonexistent_and_ambiguous_local_boundaries():
    nonexistent = WeeklyProgram("America/New_York", (ProgramSlot(6, 150, 240, "charge", 80, 5000),), "reject", "later")
    with pytest.raises(SafetyError, match="nonexistent"):
        expand_program(nonexistent, date(2026, 3, 8), 1)
    ambiguous = WeeklyProgram("America/New_York", (ProgramSlot(6, 90, 180, "charge", 80, 5000),), "reject", "reject")
    with pytest.raises(SafetyError, match="ambiguous"):
        expand_program(ambiguous, date(2026, 11, 1), 1)


def test_gap_and_overlap_detection():
    partial = WeeklyProgram("UTC", (ProgramSlot(0, 60, 120, "charge", 80, 5000),), "reject", "reject")
    result = expand_program(partial, date(2026, 9, 21), 1)
    assert result["gaps"] == [{"date": "2026-09-21", "start_minute": 0, "end_minute": 60}, {"date": "2026-09-21", "start_minute": 120, "end_minute": 1440}]
    overlap = WeeklyProgram("UTC", (*partial.slots, ProgramSlot(0, 90, 130, "discharge", 30, 5000)), "reject", "reject")
    with pytest.raises(SafetyError, match="overlap"):
        expand_program(overlap, date(2026, 9, 21), 1)


def create_schedule(local, full=True):
    c, _ = local
    headers = login(local, "engineer")
    response = c.post("/api/schedules", headers=headers, json={"site_id": "sim-site", "name": "SIMULATOR weekly program",
        "slots": [{"day": day, "start": "00:00" if full else "06:00", "end": "24:00", "mode": "self_use"} for day in range(7)]})
    assert response.status_code in {200, 201}
    return response.json(), headers


def test_compile_unknown_platform_is_persistent_explainable_and_cannot_rollout(local):
    c, ctl = local
    schedule, headers = create_schedule(local)
    compiled = c.post(f"/api/schedules/{schedule['id']}/compile", json={"device_ids": ["sim-device"], "start_date": "2026-09-21"}, headers=headers)
    assert compiled.status_code == 201
    row = compiled.json()
    assert row["targets"][0]["reason"] == "adapter_schedule_contract_missing"
    assert row["state"] == "BLOCKED" and row["dispatch_enabled"] is False
    assert ctl.store.get("schedule_compilation", row["id"])["source_digest"] == schedule_digest(schedule)
    assert c.post(f"/api/schedule-compilations/{row['id']}/rollout", json={"digest": row["digest"]}, headers=headers).status_code == 409
    assert not ctl.store.commands()


def test_compile_checks_full_week_gaps_and_site_scope(local):
    c, _ = local
    schedule, headers = create_schedule(local, full=False)
    body = {"device_ids": ["sim-device"], "start_date": "2026-09-21", "days": 1}
    row = c.post(f"/api/schedules/{schedule['id']}/compile", json=body, headers=headers).json()
    assert len(row["weekly_gaps"]) == 7
    assert row["targets"][0]["reason"] == "schedule_has_uncovered_intervals"
    assert c.post(f"/api/schedules/{schedule['id']}/compile", json={**body, "device_ids": ["other-device"]}, headers=headers).status_code == 409
    login(local, "other")
    assert c.get("/api/schedule-compilations").json() == []


def test_changed_schedule_invalidates_rollout_source(store):
    schedule = {"id": "test", "site_id": "sim-site", "revision": 1, "timezone": "UTC", "slots": [], "state": "DRAFT"}
    store.put("schedule", "test", schedule)
    rollout = {"schedule_source": {"id": "test", "digest": schedule_digest(schedule)}}
    require_schedule_source(store, rollout)
    store.put("schedule", "test", {**schedule, "revision": 2})
    with pytest.raises(SafetyError, match="recompile"):
        require_schedule_source(store, rollout)


def install_simulated_translator(ctl):
    from solar_fleet.capability_profiles import IntentContract
    from solar_fleet.domain import Constraint
    from solar_fleet.integration import IntegrationPlugin

    device = ctl.device("sim-device")
    profile = profile_for(device)
    profile.contracts = [IntentContract(intent="SET_TOU", group="tou",
        explanation_vi="Lịch kiểm thử", explanation_en="Synthetic schedule contract",
        constraints={"slots": Constraint(json_schema={"type": "array", "minItems": 1, "maxItems": 168,
            "items": {"type": "object", "additionalProperties": False, "required": ["day", "start", "end"],
                "properties": {"day": {"type": "integer", "minimum": 0, "maximum": 6},
                    "start": {"type": "integer", "minimum": 0, "maximum": 1439},
                    "end": {"type": "integer", "minimum": 1, "maximum": 1440}}}})}, readback_fields=["slots"])]

    def translate(device, program):
        assert program.timezone == "Asia/Ho_Chi_Minh"
        return {"intent": "SET_TOU", "semantics": "exact", "device_clock": "plant_timezone",
            "reason_vi": "Chỉ simulator", "reason_en": "Simulator only", "evidence_ids": ["SIMULATOR-OFFICIAL-EVIDENCE"],
            "parameters": {"slots": [{"day": s.day, "start": s.start_minute, "end": s.end_minute} for s in program.slots]}}

    ctl.registry.register(IntegrationPlugin(id="SIMULATOR", version="test.1", factory=lambda *a, **kw: None,
        plant=lambda raw: None, device=lambda raw: None, measurement=lambda raw: None,
        namespace="simulator", evidence_ids=("SIMULATOR-OFFICIAL-EVIDENCE",), authentication="SIMULATOR",
        control_profiles=(profile,), compile_schedule=translate))


def test_native_schedule_handoff_uses_guarded_rollout_and_source_revision(local):
    c, ctl = local
    install_simulated_translator(ctl)
    schedule, headers = create_schedule(local)
    plan = c.post(f"/api/schedules/{schedule['id']}/compile", json={"device_ids": ["sim-device"], "start_date": "2026-09-21"}, headers=headers).json()
    assert plan["state"] == "COMPATIBLE"
    url = f"/api/schedule-compilations/{plan['id']}/rollout"
    rollout = c.post(url, json={"digest": plan["digest"]}, headers=headers)
    assert rollout.status_code == 201 and rollout.json()["state"] == "DRAFT"
    assert c.post(url, json={"digest": plan["digest"]}, headers=headers).json()["id"] == rollout.json()["id"]
    assert len(ctl.store.list("rollout")) == 1 and not ctl.store.commands()
    ctl.store.put("schedule", schedule["id"], {**schedule, "revision": 2})
    result = c.post(f"/api/rollouts/{rollout.json()['id']}/preview", json={}, headers=headers)
    assert result.status_code == 409 and result.json()["error"] == "schedule_changed_recompile_required"


def test_profile_revocation_between_compile_and_rollout_blocks_preparation(local):
    c, ctl = local
    install_simulated_translator(ctl)
    schedule, headers = create_schedule(local)
    plan = c.post(f"/api/schedules/{schedule['id']}/compile", json={"device_ids": ["sim-device"], "start_date": "2026-09-21"}, headers=headers).json()
    ctl.registry.profiles.revoke("SIMULATOR-PROFILE")
    assert c.post(f"/api/schedule-compilations/{plan['id']}/rollout", json={"digest": plan["digest"]}, headers=headers).status_code == 409
    assert not ctl.store.list("rollout")
