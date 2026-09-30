"""Tests for Realtime Monitoring & Audit Journal workspace (Mockup #11 & Mockup #26)."""

import json

import pytest
from cloud_fixture import cloud_latest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Device, DeviceIdentity, Role, Sample, Source, utcnow
from solar_fleet.security import Vault, create_user

PASSWORD = "SIMULATOR-workspace-password-only"
ORIGIN = "http://127.0.0.1:8765"


def insert_test_command(
    store,
    id: str,
    plan_id: str,
    site_id: str,
    device_id: str,
    operator_id: str = "admin",
    status: str = "COMPLETED",
    intent: str = "SET_WORK_MODE",
    parameters: dict | None = None,
    updated_at: str | None = None,
    error: str | None = None,
    readback: dict | None = None,
):
    ts = updated_at or utcnow().isoformat()
    plan_body = {
        "id": plan_id,
        "device_id": device_id,
        "site_id": site_id,
        "operator_id": operator_id,
        "intent": intent,
        "parameters": parameters or {},
        "previous": {},
        "expected": {},
        "calls": [],
        "capability": {
            "intent": intent,
            "display_name": intent,
            "description": "",
            "category": "WORK_MODE",
            "parameters_schema": {},
            "idempotent": True,
            "safe_range": None,
            "readback_metrics": [],
            "settle_time_seconds": 5,
        },
        "created_at": ts,
        "expires_at": ts,
        "risks": [],
        "digest": "test-digest",
    }
    store.db.execute("INSERT INTO plans VALUES(?,?)", (plan_id, json.dumps(plan_body)))
    store.db.execute(
        "INSERT INTO commands VALUES(?,?,?,?,?,?,?,?,?,?,?)",
        (
            id,
            f"idem-{id}",
            plan_id,
            device_id,
            site_id,
            operator_id,
            status,
            "[]",
            ts,
            error,
            json.dumps(readback) if readback else None,
        ),
    )


@pytest.fixture
def journal_app(store):
    for uid, role, sites in [
        ("admin", Role.ADMIN, ["*"]),
        ("engineer", Role.ENGINEER, ["site-deye", "site-solis"]),
        ("operator", Role.OPERATOR, ["site-deye", "site-solis"]),
        ("viewer", Role.VIEWER, ["site-deye"]),
    ]:
        create_user(store, uid, PASSWORD, role, sites)

    store.put(
        "site",
        "site-deye",
        {
            "id": "site-deye",
            "name": "Nhà anh Minh",
            "capacity_kwp": 10.0,
            "vendor": "Deye",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    store.put(
        "site",
        "site-solis",
        {
            "id": "site-solis",
            "name": "NM Bình Minh",
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
        name="Biến tần Deye SUN-10K",
        online=True,
        last_seen=utcnow(),
        identity=DeviceIdentity(
            vendor="Deye",
            model="SUN-10K-SG04LP3-EU",
            logger_model="LOGGER-1",
            firmware="V1.0.8",
            protocol_version="MODBUS-RTU",
            account_type="INSTALLER",
            privilege="RW",
            region="VN",
        ),
        metadata={
            "serial": "2408A1256E78",
            "model": "SUN-10K-SG04LP3-EU",
            "location": "Tầng mái - Khu inverter",
            "firmware_version": "V1.0.8",
        },
    )
    store.put("device", dev1.id, dev1.model_dump(mode="json"))

    dev2 = Device(
        id="dev-solis-1",
        site_id="site-solis",
        integration_id="int-solis",
        vendor_id="solis-001",
        type="INVERTER",
        name="Biến tần Solis 50K",
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
        metadata={"serial": "SN-SOLIS-001", "model": "Solis-50K"},
    )
    store.put("device", dev2.id, dev2.model_dump(mode="json"))

    vault = Vault(store, Fernet.generate_key().decode())
    ctl = Controller(store, vault)
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


def test_journal_summary_empty_and_populated(journal_app):
    client, _, store = journal_app
    headers = auth_headers(client, "admin")

    # 1. Summary on empty database
    res = client.get("/api/journal/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_today"] == 0
    assert data["success_count"] == 0
    assert data["failed_count"] == 0
    assert data["pending_count"] == 0
    assert data["need_readback_count"] == 0
    assert data["hash_chain_valid"] is True
    assert data["total_commands_all_time"] == 0

    # 2. Insert commands into store
    insert_test_command(
        store,
        id="cmd-1",
        plan_id="plan-1",
        site_id="site-deye",
        device_id="dev-deye-1",
        operator_id="admin",
        status="COMPLETED",
        intent="SET_WORK_MODE",
        parameters={"mode": "Self-use"},
    )
    insert_test_command(
        store,
        id="cmd-2",
        plan_id="plan-2",
        site_id="site-deye",
        device_id="dev-deye-1",
        operator_id="admin",
        status="FAILED",
        intent="SET_ZERO_EXPORT",
        parameters={"limit_kw": 0},
    )
    insert_test_command(
        store,
        id="cmd-3",
        plan_id="plan-3",
        site_id="site-solis",
        device_id="dev-solis-1",
        operator_id="admin",
        status="WAITING_DEVICE",
        intent="ENABLE_GRID_CHARGE",
        parameters={"enabled": True},
    )

    # Also log audit rows
    store.audit(
        "control", {"command_id": "cmd-1", "action": "SET_WORK_MODE", "status": "SUCCESS"}, "site-deye"
    )
    store.audit(
        "control", {"command_id": "cmd-2", "action": "SET_ZERO_EXPORT", "status": "FAILED"}, "site-deye"
    )

    # 3. Check summary again
    res = client.get("/api/journal/summary", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_today"] == 3
    assert data["success_count"] == 0  # COMPLETED without verified readback is not success.
    assert data["failed_count"] == 1
    assert data["need_readback_count"] == 1
    assert data["hash_chain_valid"] is True
    assert data["total_commands_all_time"] == 3


def test_commands_listing_and_filtering(journal_app):
    client, _, store = journal_app
    headers = auth_headers(client, "admin")

    # Insert diverse commands
    insert_test_command(
        store,
        id="cmd-10",
        plan_id="p-10",
        site_id="site-deye",
        device_id="dev-deye-1",
        operator_id="admin",
        status="COMPLETED",
        intent="SET_WORK_MODE",
    )
    insert_test_command(
        store,
        id="cmd-11",
        plan_id="p-11",
        site_id="site-deye",
        device_id="dev-deye-1",
        operator_id="admin",
        status="FAILED",
        intent="SET_ZERO_EXPORT",
    )
    insert_test_command(
        store,
        id="cmd-12",
        plan_id="p-12",
        site_id="site-solis",
        device_id="dev-solis-1",
        operator_id="operator",
        status="COMPLETED",
        intent="REBOOT",
    )

    # List all
    res = client.get("/api/journal/commands", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_items"] == 3
    assert len(data["items"]) == 3

    # Filter by site
    res_site = client.get("/api/journal/commands?site_id=site-deye", headers=headers)
    assert res_site.status_code == 200
    assert res_site.json()["total_items"] == 2

    # Filter by status
    res_st = client.get("/api/journal/commands?status=FAILED", headers=headers)
    assert res_st.status_code == 200
    assert res_st.json()["total_items"] == 1
    assert res_st.json()["items"][0]["id"] == "cmd-11"

    # Filter by query
    res_q = client.get("/api/journal/commands?q=Reboot", headers=headers)
    assert res_q.status_code == 200
    assert res_q.json()["total_items"] == 1
    assert res_q.json()["items"][0]["id"] == "cmd-12"


def test_command_detail_and_5_stages(journal_app):
    c, _, store = journal_app
    h = auth_headers(c)
    insert_test_command(
        store, id="cmd", plan_id="plan", site_id="site-deye", device_id="dev-deye-1", status="ACCEPTED"
    )
    url = "/api/journal/commands/cmd"
    assert c.get(url, headers=h).json()["stages"] == []
    store.audit("control", {"command_id": "cmd", "event": "state", "status": "ACCEPTED"}, "site-deye")
    data = c.get(url, headers=h).json()
    assert len(data["stages"]) == 1
    assert data["stages"][0]["status"] == "ACCEPTED"
    assert data["stages"][0]["timestamp"] == data["events"][0]["timestamp"]


def test_device_realtime_monitoring_data(journal_app):
    c, _, store = journal_app
    h = auth_headers(c)
    now = utcnow()
    samples = [
        Sample(
            device_id="dev-deye-1",
            metric=m,
            value=v,
            unit=u,
            source=Source.SIMULATOR,
            source_timestamp=now,
            quality="GOOD",
            binding_id="test",
        )
        for m, v, u in [
            ("pv_w", 6420, "W"),
            ("inverter_ac_w", 5890, "W"),
            ("soc_pct", 78, "%"),
            ("inverter_temperature_c", 42, "°C"),
        ]
    ]
    store.add_samples(samples)
    cloud_latest(store, "dev-deye-1",
        {
            "device_id": "dev-deye-1",
            "state": "HAS_DATA",
            "samples": [s.model_dump(mode="json") for s in samples],
        },
    )
    data = c.get("/api/journal/realtime/dev-deye-1", headers=h).json()
    assert data["device"]["serial"] == "deye-001"
    assert data["kpis"]["p_pv_kw"] == 6.42
    assert data["kpis"]["p_ac_kw"] == 5.89
    assert data["kpis"]["soc_pct"] == 78
    assert data["kpis"]["temp_c"] == 42
    assert all(v == [] for v in data["curves"].values())
    assert all(p["threshold"] is None for p in data["parameters"])
    assert data["connectivity"]["cloud_connection"] == "UNKNOWN"


def test_audit_trail_and_hash_chain_verification(journal_app):
    client, _, store = journal_app
    admin_headers = auth_headers(client, "admin")

    # Insert audit rows
    store.audit("control", {"action": "SET_WORK_MODE", "status": "SUCCESS"}, "site-deye")
    store.audit("security", {"event": "login", "user": "admin"}, None)

    # Fetch audit
    res = client.get("/api/journal/audit?category=all", headers=admin_headers)
    assert res.status_code == 200
    data = res.json()
    assert data["hash_chain_valid"] is True
    assert data["total_items"] >= 2

    # Viewer cannot access security category
    viewer_headers = auth_headers(client, "viewer")
    res_sec = client.get("/api/journal/audit?category=security", headers=viewer_headers)
    assert res_sec.status_code == 403


def test_journal_site_isolation_and_export(journal_app):
    client, _, store = journal_app

    # Insert commands on both sites
    insert_test_command(
        store,
        id="cmd-deye-a",
        plan_id="p-iso-1",
        site_id="site-deye",
        device_id="dev-deye-1",
        operator_id="admin",
        status="COMPLETED",
    )
    insert_test_command(
        store,
        id="cmd-solis-b",
        plan_id="p-iso-2",
        site_id="site-solis",
        device_id="dev-solis-1",
        operator_id="admin",
        status="COMPLETED",
    )

    # Viewer only has access to site-deye
    viewer_headers = auth_headers(client, "viewer")

    # 1. Viewer querying commands should only see site-deye
    res = client.get("/api/journal/commands", headers=viewer_headers)
    assert res.status_code == 200
    items = res.json()["items"]
    assert len(items) == 1
    assert items[0]["site_id"] == "site-deye"

    # 2. Viewer attempting to query site-solis directly gets 403
    res_solis = client.get("/api/journal/commands?site_id=site-solis", headers=viewer_headers)
    assert res_solis.status_code == 403

    # 3. Viewer attempting to read realtime data for dev-solis-1 gets 403
    res_dev = client.get("/api/journal/realtime/dev-solis-1", headers=viewer_headers)
    assert res_dev.status_code == 403

    # 4. CSV Export for admin
    admin_headers = auth_headers(client, "admin")
    res_exp = client.get("/api/journal/export", headers=admin_headers)
    assert res_exp.status_code == 200
    assert "text/csv" in res_exp.headers["content-type"]
    content = res_exp.text
    assert "Mã lệnh" in content
    assert "cmd-deye-a" in content
    assert "cmd-solis-b" in content
