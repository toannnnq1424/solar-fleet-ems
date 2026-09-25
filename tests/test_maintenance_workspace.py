"""Tests for Maintenance & Work Orders Center workspace (Summary KPIs, Plans, Firmware Staging, RBAC, Site Isolation)."""

from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Device, DeviceIdentity, Role, Sample, Source, utcnow
from solar_fleet.security import Vault, create_user

PASSWORD = "SIMULATOR-workspace-password-only"
ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def maint_app(store):
    for uid, role, sites in [
        ("admin", Role.ADMIN, ["*"]),
        ("engineer", Role.ENGINEER, ["site-deye", "site-solis"]),
        ("operator", Role.OPERATOR, ["site-deye", "site-solis"]),
        ("reviewer", Role.INSTALLER, ["site-deye", "site-solis"]),
        ("viewer", Role.VIEWER, ["site-deye"]),
    ]:
        create_user(store, uid, PASSWORD, role, sites)

    store.put(
        "site",
        "site-deye",
        {
            "id": "site-deye",
            "name": "Site Alpha",
            "capacity_kwp": 100.0,
            "vendor": "Deye",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    store.put(
        "site",
        "site-solis",
        {
            "id": "site-solis",
            "name": "Site Beta",
            "capacity_kwp": 50.0,
            "vendor": "Solis",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )

    dev1 = Device(
        id="dev-deye-1",
        site_id="site-deye",
        integration_id="int-deye",
        vendor_id="deye-001",
        type="INVERTER",
        name="Inverter Alpha 1",
        online=True,
        last_seen=utcnow(),
        identity=DeviceIdentity(
            vendor="Deye",
            model="SUN-50K",
            logger_model="LOGGER-1",
            firmware="v2.0.41",
            protocol_version="MODBUS-RTU",
            account_type="INSTALLER",
            privilege="RW",
            region="VN",
        ),
        metadata={"serial": "SN-DEYE-001"},
    )
    store.put("device", dev1.id, dev1.model_dump(mode="json"))

    dev2 = Device(
        id="dev-solis-1",
        site_id="site-solis",
        integration_id="int-solis",
        vendor_id="solis-001",
        type="INVERTER",
        name="Inverter Beta 1",
        online=True,
        last_seen=utcnow(),
        identity=DeviceIdentity(
            vendor="Solis",
            model="Solis-50K",
            logger_model="LOGGER-2",
            firmware="v1.12.08",
            protocol_version="MODBUS-RTU",
            account_type="INSTALLER",
            privilege="RW",
            region="VN",
        ),
        metadata={"serial": "SN-SOLIS-002"},
    )
    store.put("device", dev2.id, dev2.model_dump(mode="json"))

    ctl = Controller(store, Vault(store, Fernet.generate_key()))
    with TestClient(create_app(ctl, poll=False), base_url=ORIGIN) as client:
        yield client, ctl, store


def auth_headers(client, username="admin"):
    res = client.post(
        "/api/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
    csrf = res.json()["csrf"]
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf, "Content-Type": "application/json"}


def test_maintenance_summary_empty_and_populated(maint_app):
    client, ctl, store = maint_app
    headers = auth_headers(client, "admin")

    # 1. Summary on initial state (no work orders, no plans, no firmware requests)
    res = client.get("/api/maintenance/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["devices"]["total"] == 2
    assert data["work_orders"]["total"] == 0
    assert data["work_orders"]["open"] == 0
    assert data["plans"]["total"] == 0
    assert data["plans"]["active"] == 0
    assert data["firmware"]["total_requests"] == 0
    assert data["total_labor_minutes"] == 0.0

    # 2. Add sample telemetry so dev-deye-1 has fresh and verified data
    now = utcnow()
    sample = Sample(
        device_id="dev-deye-1",
        metric="pv_power",
        value=25000.0,
        unit="W",
        source=Source.CLOUD,
        source_timestamp=now,
        quality="GOOD",
        stale=False,
        binding_id="pv1_power",
    )
    store.put(
        "latest",
        "dev-deye-1",
        {
            "device_id": "dev-deye-1",
            "received_at": now.isoformat(),
            "source": "VENDOR_CLOUD",
            "samples": [sample.model_dump(mode="json")],
        },
    )

    # Add a work order
    wo_res = client.post(
        "/api/records/work_order",
        headers=headers,
        json={
            "site_id": "site-deye",
            "title": "Panel cleaning",
            "description": "Clean dust on arrays",
            "device_id": "dev-deye-1",
            "severity": "medium",
            "due_date": (now.date() - timedelta(days=1)).isoformat(),  # Overdue
        },
    )
    assert wo_res.status_code == 201

    # Query summary again
    res2 = client.get("/api/maintenance/summary", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert data2["devices"]["fresh"] >= 1
    assert data2["work_orders"]["total"] == 1
    assert data2["work_orders"]["open"] == 1
    assert data2["work_orders"]["overdue"] == 1


def test_maintenance_plans_crud_and_manual_trigger(maint_app):
    client, ctl, store = maint_app
    headers = auth_headers(client, "engineer")

    # 1. Create maintenance plan via workbench
    now = utcnow()
    from zoneinfo import ZoneInfo

    tomorrow = (now.astimezone(ZoneInfo("Asia/Ho_Chi_Minh")).date() + timedelta(days=1)).isoformat()
    create_res = client.post(
        "/api/workbench/maintenance_plan",
        headers=headers,
        json={
            "data": {
                "site_id": "site-deye",
                "device_id": "dev-deye-1",
                "name": "Quarterly Inverter Heat Sink Cleaning",
                "interval_days": 90,
                "next_due": tomorrow,
                "severity": "high",
                "instructions": "Clean fans and heat sink fins with compressed air.",
                "enabled": True,
            }
        },
    )
    assert create_res.status_code == 200
    plan_id = create_res.json()["id"]

    # 2. List plans via /api/maintenance/plans
    list_res = client.get("/api/maintenance/plans", headers=headers)
    assert list_res.status_code == 200
    items = list_res.json()["items"]
    assert len(items) == 1
    assert items[0]["id"] == plan_id
    assert items[0]["name"] == "Quarterly Inverter Heat Sink Cleaning"
    assert items[0]["days_until_due"] == 1
    assert items[0]["overdue"] is False
    assert items[0]["device"]["name"] == "Inverter Alpha 1"
    assert items[0]["work_orders_generated"] == 0

    # 3. Trigger work order manually from plan
    trig_res = client.post(f"/api/maintenance/plans/{plan_id}/trigger", headers=headers)
    assert trig_res.status_code == 201
    job = trig_res.json()
    assert job["site_id"] == "site-deye"
    assert job["title"] == "Quarterly Inverter Heat Sink Cleaning"
    assert job["source"] == "MAINTENANCE_PLAN"
    assert job["status"] == "open"
    assert job["device_id"] == "dev-deye-1"

    # Verify generated count updated
    list_res2 = client.get("/api/maintenance/plans", headers=headers)
    assert list_res2.json()["items"][0]["work_orders_generated"] == 1

    # 4. Viewer cannot trigger plan (RBAC)
    viewer_headers = auth_headers(client, "viewer")
    viewer_trig = client.post(f"/api/maintenance/plans/{plan_id}/trigger", headers=viewer_headers)
    assert viewer_trig.status_code == 403


def test_maintenance_firmware_overview_and_stage(maint_app):
    client, ctl, store = maint_app
    headers = auth_headers(client, "engineer")

    # 1. Overview should list devices and empty requests
    res = client.get("/api/maintenance/firmware", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["inventory"]) == 2
    dev1 = next(d for d in data["inventory"] if d["device_id"] == "dev-deye-1")
    assert dev1["current_firmware"] == "v2.0.41"
    assert dev1["online"] is True
    assert dev1["preflight"]["online"] is True
    assert dev1["preflight"]["no_critical_alarms"] is True
    assert dev1["preflight"]["passed"] is True
    assert len(data["requests"]) == 0

    # 2. Stage a valid firmware upgrade
    sha = "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855"
    window = (utcnow() + timedelta(days=2)).isoformat()
    stage_res = client.post(
        "/api/maintenance/firmware/stage",
        headers=headers,
        json={
            "site_id": "site-deye",
            "device_id": "dev-deye-1",
            "target_version": "v2.1.05",
            "sha256": sha.upper(),  # Should be normalized to lower
            "release_reference": "https://deye.example.com/rel/v2.1.05",
            "maintenance_window": window,
            "notes": "Nighttime upgrade window",
        },
    )
    assert stage_res.status_code == 201
    staged = stage_res.json()
    assert staged["sha256"] == sha.lower()
    assert staged["state"] == "QUEUED_FOR_MAINTENANCE_WINDOW"

    # 3. Overview should now show 1 staged request
    res2 = client.get("/api/maintenance/firmware", headers=headers)
    assert res2.status_code == 200
    data2 = res2.json()
    assert len(data2["requests"]) == 1
    assert data2["requests"][0]["target_version"] == "v2.1.05"
    assert data2["requests"][0]["device_name"] == "Inverter Alpha 1"

    # 4. Invalid sha256 rejected
    bad_res = client.post(
        "/api/maintenance/firmware/stage",
        headers=headers,
        json={
            "site_id": "site-deye",
            "device_id": "dev-deye-1",
            "target_version": "v2.1.05",
            "sha256": "not-a-valid-sha",
            "release_reference": "ref",
            "maintenance_window": window,
        },
    )
    assert bad_res.status_code == 422


def test_site_isolation_and_rbac(maint_app):
    client, ctl, store = maint_app
    viewer_headers = auth_headers(client, "viewer")  # only has access to site-deye

    # Viewer can read site-deye summary
    res = client.get("/api/maintenance/summary", headers=viewer_headers)
    assert res.status_code == 200
    # Viewer sees only 1 device (site-deye), not site-solis
    assert res.json()["devices"]["total"] == 1

    # Viewer querying site-solis directly gets 0 items
    res_solis = client.get("/api/maintenance/summary?site_id=site-solis", headers=viewer_headers)
    assert res_solis.status_code == 200
    assert res_solis.json()["devices"]["total"] == 0

    # Viewer cannot stage firmware (requires technical role)
    res_stage = client.post(
        "/api/maintenance/firmware/stage",
        headers=viewer_headers,
        json={
            "site_id": "site-deye",
            "device_id": "dev-deye-1",
            "target_version": "v2.1.05",
            "sha256": "e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855",
            "release_reference": "ref",
            "maintenance_window": utcnow().isoformat(),
        },
    )
    assert res_stage.status_code == 403


def test_work_order_workflow_and_safety_gate(maint_app):
    client, ctl, store = maint_app

    # 1. Create work order as engineer
    eng_headers = auth_headers(client, "engineer")
    res = client.post(
        "/api/records/work_order",
        headers=eng_headers,
        json={
            "site_id": "site-deye",
            "title": "Grounding and Insulation Test",
            "description": "Measure grounding resistance",
            "device_id": "dev-deye-1",
            "severity": "high",
            "due_date": (utcnow().date() + timedelta(days=5)).isoformat(),
        },
    )
    assert res.status_code == 201
    job_id = res.json()["id"]

    # 2. Try to close directly -> Safety Error: maintenance_execution_incomplete (409)
    close_res = client.post(
        f"/api/records/work_order/{job_id}",
        headers=eng_headers,
        json={
            "revision": 1,
            "status": "resolved",
            "assigned_to": "engineer",
            "note": "Closing early without checklist",
        },
    )
    assert close_res.status_code == 409

    # 3. Plan the work order with 1 step
    plan_res = client.post(
        f"/api/maintenance/work-orders/{job_id}/plan",
        headers=eng_headers,
        json={
            "revision": 1,
            "safety_note": "Lockout / Tagout applied",
            "note": "Initial plan",
            "team": ["engineer", "reviewer"],
            "steps": [
                {
                    "id": "ground_test",
                    "title": "Measure resistance",
                    "instructions": "Value must be < 4 Ohm",
                    "required": True,
                }
            ],
        },
    )
    assert plan_res.status_code == 200

    # 4. Record checklist step outcome as pass
    step_res = client.post(
        f"/api/maintenance/work-orders/{job_id}/step",
        headers=eng_headers,
        json={
            "revision": 2,
            "step_id": "ground_test",
            "outcome": "pass",
            "note": "Measured 1.8 Ohm - Pass",
        },
    )
    assert step_res.status_code == 200

    # 5. Record work time
    now = utcnow()
    time_res = client.post(
        f"/api/maintenance/work-orders/{job_id}/time",
        headers=eng_headers,
        json={
            "revision": 3,
            "start": (now - timedelta(hours=2)).isoformat(),
            "end": (now - timedelta(hours=1)).isoformat(),
            "activity": "Ground resistance measurement using 3-point fall-of-potential tester",
        },
    )
    assert time_res.status_code == 201

    # 6. Submit for independent review
    sub_res = client.post(
        f"/api/maintenance/work-orders/{job_id}/submit",
        headers=eng_headers,
        json={
            "revision": 4,
            "note": "Ready for 4-eyes review",
        },
    )
    assert sub_res.status_code == 200

    # Engineer tries to review their own submission -> blocked by 4-eyes rule (409)
    self_rev = client.post(
        f"/api/maintenance/work-orders/{job_id}/review",
        headers=eng_headers,
        json={
            "revision": 5,
            "decision": "approve",
            "note": "Self approval",
        },
    )
    assert self_rev.status_code == 409

    # Reviewer logs in and approves
    rev_headers = auth_headers(client, "reviewer")
    ok_rev = client.post(
        f"/api/maintenance/work-orders/{job_id}/review",
        headers=rev_headers,
        json={
            "revision": 5,
            "decision": "approve",
            "note": "Ground test verified under 4 Ohm",
        },
    )
    assert ok_rev.status_code == 200

    # 7. Transition to in_progress first, then resolve
    eng_headers2 = auth_headers(client, "engineer")
    job_detail = client.get(f"/api/maintenance/work-orders/{job_id}", headers=eng_headers2).json()[
        "work_order"
    ]
    prog_res = client.post(
        f"/api/records/work_order/{job_id}",
        headers=eng_headers2,
        json={
            "revision": job_detail["revision"],
            "status": "in_progress",
            "assigned_to": "engineer",
            "note": "Work in progress",
        },
    )
    assert prog_res.status_code == 200

    # Now resolving the work order succeeds!
    job_detail2 = client.get(f"/api/maintenance/work-orders/{job_id}", headers=eng_headers2).json()[
        "work_order"
    ]
    resolve_res = client.post(
        f"/api/records/work_order/{job_id}",
        headers=eng_headers2,
        json={
            "revision": job_detail2["revision"],
            "status": "resolved",
            "assigned_to": "engineer",
            "note": "Completed with verified safety gates",
        },
    )
    assert resolve_res.status_code == 200
    assert resolve_res.json()["status"] == "resolved"
