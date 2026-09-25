"""Tests for Settings, Administration, Users & Onboarding Workspace (Mockup #19, #21, #15, #13)."""

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
def test_setup(store):
    for uid, role, sites, perms in [
        (
            "admin",
            Role.ADMIN,
            ["*"],
            ["grid_settings", "raw_commands", "firmware_upgrade", "battery_settings"],
        ),
        ("viewer", Role.VIEWER, ["site-01"], []),
        ("operator", Role.OPERATOR, ["site-01"], []),
        ("engineer", Role.ENGINEER, ["site-01"], ["grid_settings", "raw_commands"]),
    ]:
        create_user(store, uid, PASSWORD, role, sites, perms)

    store.put("site", "site-01", {"id": "site-01", "name": "Nhà máy Tân Thuận", "capacity_kwp": 150.0})

    vault = Vault(store, Fernet.generate_key().decode())
    ctrl = Controller(store, vault)
    with TestClient(create_app(ctrl, port=8765, poll=False), base_url=ORIGIN) as client:
        # Login as admin
        res = client.post(
            "/api/login",
            json={"username": "admin", "password": PASSWORD},
            headers={"Origin": ORIGIN},
        )
        assert res.status_code == 200, res.text
        admin_csrf = res.json()["csrf"]
        admin_cookie = res.cookies["solar_session"]

        # Login as viewer
        res_v = client.post(
            "/api/login",
            json={"username": "viewer", "password": PASSWORD},
            headers={"Origin": ORIGIN},
        )
        assert res_v.status_code == 200, res_v.text
        viewer_csrf = res_v.json()["csrf"]
        viewer_cookie = res_v.cookies["solar_session"]

        yield {
            "ctrl": ctrl,
            "store": store,
            "client": client,
            "admin_csrf": admin_csrf,
            "admin_cookie": admin_cookie,
            "viewer_csrf": viewer_csrf,
            "viewer_cookie": viewer_cookie,
        }


def test_admin_summary_api(test_setup):
    client = test_setup["client"]
    cookie = test_setup["admin_cookie"]

    res = client.get("/api/admin/summary", cookies={"solar_session": cookie})
    assert res.status_code == 200, res.text
    data = res.json()

    assert data["total_users"] >= 4
    assert data["active_users"] >= 4
    assert data["roles_count"] == 5
    assert data["linked_cloud_accounts"] == 0
    assert data["sensitive_perms_count"] >= 2
    assert data["hash_chain_valid"] is True
    assert "vault_status" in data


def test_admin_users_api_filtering_and_enrichment(test_setup):
    client = test_setup["client"]
    cookie = test_setup["admin_cookie"]

    # 1. Fetch all users
    res = client.get("/api/admin/users", cookies={"solar_session": cookie})
    assert res.status_code == 200, res.text
    data = res.json()
    assert len(data["items"]) >= 4

    # Check enrichment
    admin_entry = next(u for u in data["items"] if u["id"] == "admin")
    assert admin_entry["role"] == "Administrator"
    assert admin_entry["active"] is True
    assert "*" in admin_entry["site_ids"]
    assert "role_name_vi" in admin_entry

    # 2. Filter by search query
    res_q = client.get("/api/admin/users?q=engineer", cookies={"solar_session": cookie})
    assert res_q.status_code == 200
    items_q = res_q.json()["items"]
    assert len(items_q) == 1
    assert items_q[0]["id"] == "engineer"

    # 3. Filter by role
    res_r = client.get("/api/admin/users?role=operator", cookies={"solar_session": cookie})
    assert res_r.status_code == 200
    items_r = res_r.json()["items"]
    assert len(items_r) == 1
    assert items_r[0]["id"] == "operator"

    # 4. Filter by status
    res_s = client.get("/api/admin/users?status=active", cookies={"solar_session": cookie})
    assert res_s.status_code == 200
    assert len(res_s.json()["items"]) >= 4


def test_admin_roles_matrix_api(test_setup):
    client = test_setup["client"]
    cookie = test_setup["admin_cookie"]

    res = client.get("/api/admin/roles-matrix", cookies={"solar_session": cookie})
    assert res.status_code == 200, res.text
    data = res.json()

    assert "roles" in data
    assert len(data["roles"]) == 5
    roles_dict = {r["role"]: r for r in data["roles"]}

    # Viewer has no control rights
    viewer_perms = roles_dict["Viewer"]["permissions"]
    assert viewer_perms["view_data"] is True
    assert viewer_perms["quick_control"] is False
    assert viewer_perms["grid_settings"] is False

    # Administrator has credential and audit rights
    admin_perms = roles_dict["Administrator"]["permissions"]
    assert admin_perms["quick_control"] is False
    assert roles_dict["Operator"]["permissions"]["edit_tou"] is True
    assert admin_perms["manage_credentials"] is True
    assert admin_perms["view_security_log"] is True


def test_admin_cloud_accounts_and_diagnostic_test(test_setup):
    c = test_setup["client"]
    c.cookies.set("solar_session", test_setup["admin_cookie"])
    h = {"Origin": ORIGIN, "X-CSRF-Token": test_setup["admin_csrf"]}
    assert c.get("/api/admin/cloud-accounts", headers=h).json()["items"] == []
    r = c.post(
        "/api/admin/cloud-accounts/check", headers=h, json={"vendor": "growatt", "account_id": "missing"}
    )
    assert r.status_code == 404
    assert test_setup["store"].list("integration_state") == []


def test_admin_site_config_get_and_update(test_setup):
    c = test_setup["client"]
    c.cookies.set("solar_session", test_setup["admin_cookie"])
    h = {"Origin": ORIGIN, "X-CSRF-Token": test_setup["admin_csrf"]}
    url = "/api/admin/site-config/site-01"
    assert c.get("/api/admin/site-config/missing", headers=h).status_code == 404
    initial = c.get(url, headers=h).json()
    assert initial["config"]["tou_rates"] == {}
    assert initial["all_valid"] is False
    first = c.post(url, headers=h, json={"battery_limits": {"reserve_soc_pct": 30, "max_charge_power_kw": 3}})
    assert first.status_code == 200
    second = c.post(url, headers=h, json={"battery_limits": {"reserve_soc_pct": 40}})
    assert second.status_code == 200
    cfg = second.json()["config"]
    assert cfg["battery_limits"] == {"reserve_soc_pct": 40, "max_charge_power_kw": 3}
    assert cfg["state"] == "DRAFT" and cfg["dispatch_enabled"] is False
    assert not any(s["valid"] for s in second.json()["checklist"])
    assert c.post(url, headers=h, json={"site_id": "foreign"}).status_code == 422
    assert c.get(url, headers=h).json()["config"]["site_id"] == "site-01"


def test_admin_site_config_validation_rejects_unsafe_soc(test_setup):
    c = test_setup["client"]
    c.cookies.set("solar_session", test_setup["admin_cookie"])
    h = {"Origin": ORIGIN, "X-CSRF-Token": test_setup["admin_csrf"]}
    for soc, status in [(101, 400), (-1, 400), ("invalid", 422)]:
        r = c.post(
            "/api/admin/site-config/site-01", headers=h, json={"battery_limits": {"reserve_soc_pct": soc}}
        )
        assert r.status_code == status
    assert test_setup["store"].get("site_config", "site-01") is None


def test_device_onboarding_scan_and_complete(test_setup):
    c = test_setup["client"]
    c.cookies.set("solar_session", test_setup["admin_cookie"])
    h = {"Origin": ORIGIN, "X-CSRF-Token": test_setup["admin_csrf"]}
    assert c.post("/api/admin/devices/onboard-scan", headers=h, json={"vendor": "deye"}).status_code == 409
    r = c.post(
        "/api/admin/devices/onboard-complete",
        headers=h,
        json={
            "site_id": "site-01",
            "vendor": "deye",
            "device_name": "Unknown inverter",
            "serial_number": "unobserved",
        },
    )
    assert r.status_code == 409
    assert test_setup["store"].list("device") == []


def test_admin_security_log_and_export(test_setup):
    client = test_setup["client"]
    cookie = test_setup["admin_cookie"]

    # 1. Security log
    res_sec = client.get("/api/admin/security-log", cookies={"solar_session": cookie})
    assert res_sec.status_code == 200, res_sec.text
    sec_data = res_sec.json()
    assert "entries" in sec_data
    assert "hash_chain_valid" in sec_data
    assert sec_data["hash_chain_valid"] is True

    # 2. CSV Export
    res_csv = client.get("/api/admin/export-users", cookies={"solar_session": cookie})
    assert res_csv.status_code == 200, res_csv.text
    assert "text/csv" in res_csv.headers["content-type"]
    csv_content = res_csv.text
    assert "Tài khoản (ID)" in csv_content
    assert "admin" in csv_content
    assert "viewer" in csv_content


def test_admin_rbac_permission_denial_for_viewer(test_setup):
    client = test_setup["client"]
    v_cookie = test_setup["viewer_cookie"]
    v_csrf = test_setup["viewer_csrf"]

    # Viewer cannot access admin summary
    res = client.get("/api/admin/summary", cookies={"solar_session": v_cookie})
    assert res.status_code == 403

    # Viewer cannot post site config
    res_cfg = client.post(
        "/api/admin/site-config/site-01",
        json={"site_id": "site-01"},
        headers={"origin": ORIGIN, "x-csrf-token": v_csrf},
        cookies={"solar_session": v_cookie},
    )
    assert res_cfg.status_code in (403, 422)

    # Viewer cannot export users
    res_exp = client.get("/api/admin/export-users", cookies={"solar_session": v_cookie})
    assert res_exp.status_code == 403
