"""Management and scheduler acceptance using only synthetic, network-blocked fixtures."""

import io
import json
import zipfile
from datetime import timedelta
from xml.etree import ElementTree

import httpx
import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.agent import Outbox
from solar_fleet.analytics import counter_delta, workbook
from solar_fleet.domain import Sample, Source, utcnow


def save(c, headers, kind, data, **version):
    return c.post(
        "/api/workbench/" + kind,
        json={"data": {"site_id": "sim-site", "name": "SIMULATOR", **data}, **version},
        headers=headers,
    )


def test_management_crud_revision_scope_and_archive(local):
    c, ctl = local
    h = login(local, "operator")
    created = save(c, h, "customer", {"contact": "SIMULATOR", "email": "sim@example.invalid"})
    assert created.status_code == 200
    row = created.json()
    assert save(c, h, "customer", {"contact": "Updated"}, id=row["id"], revision=1).json()["revision"] == 2
    assert save(c, h, "customer", {}, id=row["id"], revision=1).status_code == 409
    login(local, "other")
    assert not c.get("/api/workbench").json()["customer"]
    h = login(local, "viewer")
    assert save(c, h, "customer", {}).status_code == 403
    h = login(local, "operator")
    assert c.post(f"/api/workbench/customer/{row['id']}/archive", json={"revision": 2}, headers=h).json()[
        "archived"
    ]
    assert ctl.store.verify_audit()


def test_topology_cannot_cross_site_and_network_is_only_draft(local):
    c, _ = local
    h = login(local, "engineer")
    assert (
        save(
            c,
            h,
            "topology",
            {"edges": [{"source": "sim-device", "target": "other-device", "connection": "AC"}]},
        ).status_code
        == 409
    )
    response = save(
        c,
        h,
        "network_profile",
        {"device_id": "sim-device", "connection": "Ethernet", "address": "192.168.1.2"},
    )
    assert response.status_code == 200
    assert response.json()["applied_to_device"] is False
    assert response.json()["state"] == "AWAITING_DEVICE_CONTRACT"
    h = login(local, "operator")
    assert (
        save(c, h, "network_profile", {"device_id": "sim-device", "connection": "Ethernet"}).status_code
        == 403
    )


def test_tariff_overlap_and_unique_source_policy(local):
    c, _ = local
    h = login(local, "engineer")
    slots = [
        {"day": 0, "start": "00:00", "end": "10:00", "price": 1},
        {"day": 0, "start": "09:00", "end": "12:00", "price": 2},
    ]
    assert (
        save(
            c, h, "tariff", {"reference": "TEST", "effective_from": "2026-09-19", "slots": slots}
        ).status_code
        == 409
    )
    policy = {"priority": ["LOCAL", "VENDOR_CLOUD"]}
    assert save(c, h, "source_policy", policy).status_code == 200
    assert save(c, h, "source_policy", policy).status_code == 409


def test_schedule_edit_versions_and_dst_gap(local):
    c, ctl = local
    h = login(local, "operator")
    form = {
        "name": "SIM schedule",
        "site_id": "sim-site",
        "slots": [{"day": 0, "start": "01:00", "end": "02:00", "mode": "charge"}],
    }
    row = c.post("/api/schedules", json=form, headers=h).json()
    edited = c.post(
        f"/api/schedules/{row['id']}/edit",
        json={"revision": 1, "data": {**form, "name": "Updated"}},
        headers=h,
    )
    assert edited.status_code == 200 and edited.json()["revision"] == 2
    versions = c.get(f"/api/schedules/{row['id']}/versions").json()
    assert versions[-1]["name"] == "Updated" and versions[0]["name"] == "SIM schedule"
    timeline = c.get(f"/api/schedules/{row['id']}/timeline", params={"day": "2026-09-21"}).json()
    assert timeline["dispatch_enabled"] is False and timeline["slots"][0]["start_at"].endswith("+07:00")
    record = ctl.store.get("schedule", row["id"])
    record.update(
        timezone="America/New_York", slots=[{"day": 6, "start": "02:15", "end": "03:30", "mode": "hold"}]
    )
    ctl.store.put("schedule", row["id"], record)
    assert c.get(f"/api/schedules/{row['id']}/timeline", params={"day": "2026-03-08"}).status_code == 409


def test_maintenance_tick_is_idempotent_and_revoked_owner_stops_it(local):
    c, ctl = local
    h = login(local, "operator")
    created = save(
        c,
        h,
        "maintenance_plan",
        {"interval_days": 30, "next_due": "2026-01-01", "instructions": "SIM inspection"},
    ).json()
    runtime = c.app.state.operations_runtime
    now = utcnow()
    runtime.maintenance(now)
    runtime.maintenance(now)
    assert len(ctl.store.list("work_order")) == 1
    plan = ctl.store.get("maintenance_plan", created["id"])
    assert plan["next_due"] > str(now.date())
    ctl.store.db.execute("UPDATE users SET active=0 WHERE id='operator'")
    runtime.maintenance(now + timedelta(days=60))
    assert len(ctl.store.list("work_order")) == 1


def test_monitor_hold_restarts_after_observation_gap_and_never_dispatches(local):
    c, ctl = local
    h = login(local, "operator")
    rule = {
        "name": "SIM rule",
        "site_id": "sim-site",
        "conditions": [
            {"device_id": "sim-device", "metric": "soc_pct", "comparison": "lt", "threshold": 30, "unit": "%"}
        ],
        "actions": [{"device_id": "sim-device", "intent": "SET_RESERVE_SOC", "parameters": {"value": 30}}],
    }
    response = c.post("/api/rules", json=rule, headers=h)
    assert response.status_code == 201
    id = response.json()["id"]
    c.post(
        f"/api/rules/{id}/monitor",
        json={"enabled": True, "hold_seconds": 30, "cooldown_seconds": 60},
        headers=h,
    )
    now = utcnow()
    runtime = c.app.state.operations_runtime
    sample = Sample(
        device_id="sim-device",
        metric="soc_pct",
        value=20,
        unit="%",
        quality="GOOD",
        source=Source.LOCAL,
        source_timestamp=now,
        binding_id="SIM",
    )
    ctl.store.put("latest", "sim-device", {"samples": [sample.model_dump(mode="json")]})
    for delta in [0, 15, 90, 105]:
        runtime.monitors(now + timedelta(seconds=delta))
    assert not ctl.store.list("rule_run")
    runtime.monitors(now + timedelta(seconds=120))
    runs = ctl.store.list("rule_run")
    assert len(runs) == 1 and runs[0]["dispatch_enabled"] is False
    assert not ctl.store.commands()


def test_rollout_requires_every_site_and_unknown_profiles_never_send(local):
    c, ctl = local
    h = login(local, "operator")
    action = {"device_id": "other-device", "intent": "SET_RESERVE_SOC", "parameters": {"value": 30}}
    assert (
        c.post("/api/rollouts", json={"name": "SIM rollout", "actions": [action]}, headers=h).status_code
        == 403
    )
    action["device_id"] = "sim-device"
    row = c.post("/api/rollouts", json={"name": "SIM rollout", "actions": [action]}, headers=h).json()
    preview = c.post(f"/api/rollouts/{row['id']}/preview", json={}, headers=h).json()
    assert preview["targets"][0]["status"] == "BLOCKED"
    assert (
        c.post(
            f"/api/rollouts/{row['id']}/confirm",
            json={"digest": preview["digest"], "stage": "canary"},
            headers=h,
        ).status_code
        == 409
    )
    assert not ctl.store.commands()
    assert (
        c.post(f"/api/rollouts/{row['id']}/cancel", json={}, headers=h).json()["state"]
        == "CANCELLED_UNSENT_ONLY"
    )


def test_cross_site_rollout_is_not_exposed_by_first_site(local):
    c, ctl = local
    h = login(local, "admin")
    actions = [
        {"device_id": d, "intent": "SET_RESERVE_SOC", "parameters": {"value": 30}}
        for d in ["sim-device", "other-device"]
    ]
    assert c.post("/api/rollouts", json={"name": "SIM", "actions": actions}, headers=h).status_code == 201
    login(local, "operator")
    assert not c.get("/api/workbench").json()["rollout"]


def test_handover_requires_all_checks_and_blocks_critical_incident(local):
    c, ctl = local
    h = login(local, "engineer")
    data = {
        "site_id": "sim-site",
        "inspector_name": "SIM Tech",
        "customer_name": "SIM Owner",
        "acknowledgement": True,
    }
    assert c.post("/api/handovers", json=data, headers=h).status_code == 409
    for check in ["topology", "meter_ct", "power_direction", "battery", "control_readback", "alarms"]:
        assert (
            c.post(
                "/api/commissioning",
                json={"site_id": "sim-site", "check": check, "result": "pass", "evidence": "SIM ONLY"},
                headers=h,
            ).status_code
            == 200
        )
    assert c.get("/api/sites/sim-site/handover").json()["ready"]
    signed = c.post("/api/handovers", json=data, headers=h).json()
    assert signed["unlocks_control"] is False and "NOT_DIGITAL" in signed["signature_type"]
    assert (
        c.post(
            "/api/records/incident",
            json={"site_id": "sim-site", "title": "SIM critical", "severity": "critical"},
            headers=h,
        ).status_code
        == 201
    )
    assert not c.get("/api/sites/sim-site/handover").json()["ready"]


def test_report_escapes_user_content_and_uses_global_style(local):
    c, _ = local
    h = login(local)
    c.post("/api/sites/sim-site/profile", json={"name": "<script>unsafe()</script>"}, headers=h)
    report = c.get("/api/sites/sim-site/report?format=html")
    assert "<script>" not in report.text and "&lt;script&gt;" in report.text
    assert "/static/app.css" in report.text and "/static/report.css" not in report.text
    login(local, "other")
    assert c.get("/api/sites/sim-site/report?format=html").status_code == 403


def enroll(local):
    c, _ = local
    h = login(local)
    row = c.post(
        "/api/agents",
        json={"name": "SIM agent", "site_id": "sim-site", "device_ids": ["sim-device"]},
        headers=h,
    ).json()
    return row, h


def batch(row, **point):
    return {
        "agent_id": row["id"],
        "sequence": 1,
        "version": "TEST",
        "points": [
            {
                "device_id": "sim-device",
                "key": "pv_w",
                "value": 10,
                "unit": "W",
                "timestamp": utcnow().isoformat(),
                **point,
            }
        ],
    }


def test_agent_scope_replay_and_no_native_promotion(local):
    c, ctl = local
    row, h = enroll(local)
    auth = {"Authorization": "Bearer " + row["token"]}
    payload = batch(row)
    assert c.post("/api/agent/inbox", json=payload, headers=h).status_code == 403
    assert c.post("/api/agent/inbox", json=payload, headers={}).status_code == 401
    assert (
        c.post("/api/agent/inbox", json=batch(row, device_id="other-device"), headers=auth).status_code == 403
    )
    first = c.post("/api/agent/inbox", json=payload, headers=auth)
    assert first.status_code == 200 and first.json()["duplicate"] is False
    assert c.post("/api/agent/inbox", json=payload, headers=auth).json()["duplicate"] is True
    payload["points"][0]["value"] = 20
    assert c.post("/api/agent/inbox", json=payload, headers=auth).status_code == 409
    sample = ctl.latest(ctl.device("sim-device"))["samples"][0]
    assert sample["metric"] == "agent.native.pv_w" and sample["quality"] == "UNVERIFIED"
    assert "token_hash" not in json.dumps(c.get("/api/workbench").json())
    c.post(f"/api/agents/{row['id']}/revoke", json={}, headers=h)
    assert c.post("/api/agent/inbox", json=payload, headers=auth).status_code == 401
    assert not ctl.latest(ctl.device("sim-device"))["samples"]


def test_expired_agent_batch_acknowledged_without_poisoning_queue(local):
    c, ctl = local
    row, _ = enroll(local)
    auth = {"Authorization": "Bearer " + row["token"]}
    response = c.post(
        "/api/agent/inbox",
        json=batch(row, timestamp=(utcnow() - timedelta(days=8)).isoformat()),
        headers=auth,
    )
    assert response.status_code == 200 and response.json()["dropped_expired"] == 1
    assert not ctl.latest(ctl.device("sim-device"))["samples"]
    assert c.post("/api/agent/inbox", json={**batch(row), "sequence": 2}, headers=auth).status_code == 200


def test_outbox_failed_ack_retains_sequence_and_identity(tmp_path):
    path = tmp_path / "queue.db"
    out = Outbox(path)
    points = batch({"id": "SIM"})["points"]
    assert out.enqueue("SIM", points) == 1
    with pytest.raises(ValueError):
        out.enqueue("OTHER", points)
    seen = []

    def fail(request):
        seen.append(json.loads(request.content))
        return httpx.Response(503)

    with httpx.Client(transport=httpx.MockTransport(fail)) as client:
        with pytest.raises(httpx.HTTPStatusError):
            out.flush("http://127.0.0.1:8765", "SIM", client)
    out.close()
    out = Outbox(path)

    def success(request):
        seen.append(json.loads(request.content))
        return httpx.Response(200, json={"accepted": True, "sequence": 1})

    with httpx.Client(transport=httpx.MockTransport(success)) as client:
        assert out.flush("http://127.0.0.1:8765", "SIM", client) == 1
    assert seen[0] == seen[1]
    assert out.enqueue("SIM", points) == 2
    with pytest.raises(ValueError):
        out.flush("http://example.invalid", "SIM")
    out.close()


def test_energy_never_accepts_wrong_unit_or_two_physical_meters(local):
    c, ctl = local
    login(local)
    now = utcnow()
    sample = Sample(
        device_id="sim-device",
        metric="pv_w",
        value=220,
        unit="V",
        source=Source.LOCAL,
        quality="GOOD",
        source_timestamp=now,
        binding_id="SIM",
    )
    ctl.store.put("latest", "sim-device", {"samples": [sample.model_dump(mode="json")]})
    assert c.get("/api/sites/sim-site/energy").json()["metrics"]["pv_w"]["value"] is None
    sample.unit = "W"
    ctl.store.put("latest", "sim-device", {"samples": [sample.model_dump(mode="json")]})
    assert c.get("/api/sites/sim-site/energy").json()["metrics"]["pv_w"]["value"] == 220


def test_energy_counters_require_boundary_coverage_single_meter_and_no_reset():
    now = utcnow()
    end = now + timedelta(hours=1)

    def reading(time, value, device="SIM"):
        return {
            "device_id": device,
            "binding_id": "SIM",
            "source_timestamp": time.isoformat(),
            "value": value,
            "unit": "Wh",
            "quality": "GOOD",
        }

    rows = [reading(now, 100), reading(end, 350)]
    assert counter_delta(rows, now, end)["wh"] == 250
    assert counter_delta([*rows, reading(end, 400, "SIM-2")], now, end)["wh"] is None
    assert (
        counter_delta([reading(now, 100), reading(end, 50)], now, end)["reason"]
        == "COUNTER_RESET_OR_ROLLOVER"
    )
    assert (
        counter_delta([reading(now + timedelta(minutes=6), 100), reading(end, 150)], now, end)["wh"] is None
    )


def test_xlsx_uses_inline_strings_not_formulas():
    blob = workbook([{"name": '=HYPERLINK("https://example.invalid")', "value": 1}], ["name", "value"])
    with zipfile.ZipFile(io.BytesIO(blob)) as archive:
        sheet = ElementTree.fromstring(archive.read("xl/worksheets/sheet1.xml"))
        assert not sheet.findall(".//{*}f")
        assert len(sheet.findall(".//{*}row")) == 2
