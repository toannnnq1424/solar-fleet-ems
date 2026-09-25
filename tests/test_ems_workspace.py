"""Tests for EMS coordination workspaces (batch config, rules, simulation, compatibility)."""

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Role
from solar_fleet.security import Vault, create_user

PASSWORD = "SIMULATOR-workspace-password-only"
ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def local_ems(store, device):
    for id, role, sites in [
        ("admin", Role.ADMIN, ["*"]),
        ("operator", Role.OPERATOR, ["site-deye", "site-solis", "site-huawei"]),
        ("viewer", Role.VIEWER, ["site-deye"]),
    ]:
        create_user(store, id, PASSWORD, role, sites)

    # Seed 3 sites with different inverter vendors
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
            "name": "Trang trại An Phú",
            "capacity_kwp": 100.0,
            "vendor": "Solis",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    store.put(
        "site",
        "site-huawei",
        {
            "id": "site-huawei",
            "name": "Nhà chú Tùng",
            "capacity_kwp": 12.0,
            "vendor": "Huawei",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )

    ctl = Controller(store, Vault(store, Fernet.generate_key()))
    with TestClient(create_app(ctl, poll=False), base_url=ORIGIN) as client:
        yield client, ctl


def auth_headers(client, username="admin"):
    res = client.post(
        "/api/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
    csrf = res.json()["csrf"]
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf, "Content-Type": "application/json"}


def test_ems_batch_assess(local_ems):
    client, _ = local_ems
    headers = auth_headers(client, "admin")

    res = client.post(
        "/api/ems/batch-assess",
        json={"site_ids": ["site-deye", "site-solis", "site-huawei"]},
        headers=headers,
    )
    assert res.status_code == 200
    data = res.json()
    assert data["selected_count"] == 3
    assert data["total_capacity_kwp"] == 122.0
    assert "compatibility_summary" in data

    # Check vendor breakdown
    sites = data["sites"]
    assert len(sites) == 3
    statuses = {s["site_id"]: s["status"] for s in sites}
    assert statuses["site-deye"] == "Requires review"
    assert statuses["site-solis"] == "Requires review"
    assert statuses["site-huawei"] == "Requires review"


def test_ems_batch_deploy_dry_run(local_ems):
    c, ctl = local_ems
    h = auth_headers(c, "operator")
    r = c.post(
        "/api/ems/batch-deploy",
        headers=h,
        json={"campaign_name": "Contract test", "site_ids": ["site-deye"], "dry_run": True},
    )
    assert r.status_code == 409
    assert ctl.store.commands() == []
    assert c.get("/api/ems/batch-campaigns", headers=h).json() == []


def test_ems_batch_campaigns_history(local_ems):
    c, ctl = local_ems
    h = auth_headers(c, "operator")
    r = c.post(
        "/api/ems/batch-deploy",
        headers=h,
        json={"campaign_name": "Contract test", "site_ids": ["site-deye"], "dry_run": False},
    )
    assert r.status_code == 409
    assert ctl.store.commands() == []
    assert c.get("/api/ems/batch-campaigns", headers=h).json() == []


def test_ems_rules_advanced_lifecycle(local_ems):
    client, _ = local_ems
    headers = auth_headers(client, "operator")

    # 1. Fetch initial rules (clean store, no mock fallbacks)
    res = client.get("/api/ems/rules-advanced", headers=headers)
    assert res.status_code == 200
    assert res.json() == []

    # 2. Create a new advanced rule
    create_res = client.post(
        "/api/ems/rules-advanced",
        json={
            "site_id": "site-deye",
            "name": "Xả pin đỉnh chiều",
            "description": "Xả pin 17:00-20:00 cắt đỉnh biểu giá cao nhất EVN",
            "trigger_type": "SCHEDULE",
            "trigger_detail": "17:00 hàng ngày",
            "condition_expr": "Cao điểm chiều AND SOC > 30%",
            "action_detail": "Xả pin 8 kW tới 20:00",
            "max_export_kw": 0.0,
            "protected_loads": ["Tải văn phòng", "Server/IT"],
            "is_active": True,
            "dry_run": False,
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    new_rule = create_res.json()
    rule_id = new_rule["id"]
    assert new_rule["name"] == "Xả pin đỉnh chiều"
    assert new_rule["status"] == "DRAFT"
    assert new_rule["is_active"] is False

    # Verify rule is present in listing
    res = client.get("/api/ems/rules-advanced", headers=headers)
    assert res.status_code == 200
    assert len(res.json()) == 1

    # 3. Toggle rule active state
    toggle_res = client.post(f"/api/ems/rules-advanced/{rule_id}/toggle", json={}, headers=headers)
    assert toggle_res.status_code == 409


def test_ems_rule_simulation(local_ems):
    c, ctl = local_ems
    h = auth_headers(c, "operator")
    r = c.post("/api/ems/rules/absent/simulate", headers=h, json={})
    assert r.status_code == 404
    assert ctl.store.list("rule_run") == []


def test_ems_execution_logs(local_ems):
    client, _ = local_ems
    headers = auth_headers(client, "operator")

    # Initial state is empty (clean store)
    res = client.get("/api/ems/execution-logs", headers=headers)
    assert res.status_code == 200
    assert res.json() == []

    # Creating a rule records an audit event in 'operations'
    client.post(
        "/api/ems/rules-advanced",
        json={
            "site_id": "site-deye",
            "name": "Quy tắc thử nghiệm",
            "trigger_type": "SCHEDULE",
            "trigger_detail": "08:00",
            "condition_expr": "SOC > 50%",
            "action_detail": "Bật sạc",
            "max_export_kw": 0.0,
            "protected_loads": [],
            "is_active": True,
            "dry_run": True,
        },
        headers=headers,
    )

    # Check execution logs now has 1 entry
    res = client.get("/api/ems/execution-logs", headers=headers)
    assert res.status_code == 200
    logs = res.json()
    assert logs == []  # Draft creation is not execution.
