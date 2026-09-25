"""Tests for Incident Center workspace (listing, multi-filters, quick acknowledge, close, work orders, analytics, CSV export)."""

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
def incident_app(store, device):
    for uid, role, sites in [
        ("admin", Role.ADMIN, ["*"]),
        ("operator", Role.OPERATOR, ["site-deye", "site-solis"]),
        ("viewer", Role.VIEWER, ["site-deye"]),
    ]:
        create_user(store, uid, PASSWORD, role, sites)

    store.put(
        "site",
        "site-deye",
        {
            "id": "site-deye",
            "name": "NM Bình Minh",
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
            "name": "NM Trường An",
            "capacity_kwp": 50.0,
            "vendor": "Solis",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )
    store.put(
        "site",
        "site-huawei",
        {
            "id": "site-huawei",
            "name": "NM Hòa Phú",
            "capacity_kwp": 120.0,
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


def test_incidents_empty_store(incident_app):
    client, _ = incident_app
    headers = auth_headers(client, "admin")

    res = client.get("/api/incidents", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["items"] == []
    assert data["total"] == 0

    sum_res = client.get("/api/incidents/summary", headers=headers)
    assert sum_res.status_code == 200
    summary = sum_res.json()
    assert summary["open"] == 0
    assert summary["critical"] == 0
    assert "root_causes" in summary


def test_incidents_listing_and_filtering(incident_app):
    client, _ = incident_app
    headers = auth_headers(client, "admin")

    # Create 3 incidents across different sites and severities
    inc1 = client.post(
        "/api/records/incident",
        json={
            "site_id": "site-deye",
            "title": "Mất kết nối Deye Cloud",
            "description": "Không thể kết nối tới Deye Cloud trong hơn 30 phút.",
            "severity": "critical",
            "category": "connectivity",
            "vendor": "Deye",
        },
        headers=headers,
    )
    assert inc1.status_code == 201

    inc2 = client.post(
        "/api/records/incident",
        json={
            "site_id": "site-solis",
            "title": "Điện áp lưới cao",
            "description": "Điện áp tại điểm đấu nối vượt ngưỡng 253V.",
            "severity": "high",
            "category": "grid",
            "vendor": "Solis",
        },
        headers=headers,
    )
    assert inc2.status_code == 201

    inc3 = client.post(
        "/api/records/incident",
        json={
            "site_id": "site-huawei",
            "title": "Nhiệt độ inverter cao",
            "description": "Nhiệt độ lên tới 78 độ C (ngưỡng 75).",
            "severity": "low",
            "category": "inverter",
            "vendor": "Huawei",
        },
        headers=headers,
    )
    assert inc3.status_code == 201

    # Total check
    res = client.get("/api/incidents", headers=headers)
    assert res.status_code == 200
    assert res.json()["total"] == 3

    # Filter by vendor
    res_deye = client.get("/api/incidents?vendor=Deye", headers=headers)
    assert res_deye.status_code == 200
    assert res_deye.json()["total"] == 1
    assert res_deye.json()["items"][0]["vendor"] == "Deye"

    # Filter by severity
    res_crit = client.get("/api/incidents?severity=critical", headers=headers)
    assert res_crit.status_code == 200
    assert res_crit.json()["total"] == 1
    assert res_crit.json()["items"][0]["severity"] == "critical"

    # Search query
    res_search = client.get("/api/incidents?q=Deye", headers=headers)
    assert res_search.status_code == 200
    assert res_search.json()["total"] == 1


def test_incident_quick_acknowledge_and_close(incident_app):
    client, _ = incident_app
    headers = auth_headers(client, "operator")

    create_res = client.post(
        "/api/records/incident",
        json={
            "site_id": "site-deye",
            "title": "Sự cố kiểm tra tiếp nhận",
            "description": "Kiểm tra chu trình xử lý.",
            "severity": "medium",
            "category": "connectivity",
            "vendor": "Deye",
        },
        headers=headers,
    )
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # 1. Quick acknowledge
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", json={}, headers=headers)
    assert ack_res.status_code == 200
    assert ack_res.json()["status"] == "acknowledged"
    assert ack_res.json()["acknowledged_at"] is not None

    # 2. Add investigation note
    note_res = client.post(
        f"/api/incidents/{inc_id}/notes",
        json={"revision": ack_res.json()["revision"], "text": "Đã kiểm tra cáp mạng tại trạm."},
        headers=headers,
    )
    assert note_res.status_code == 200

    # 3. Quick close
    close_res = client.post(
        f"/api/incidents/{inc_id}/close",
        json={"note": "Hoàn tất xử lý sự cố an toàn."},
        headers=headers,
    )
    assert close_res.status_code == 200
    assert close_res.json()["status"] in ("resolved", "closed")
    assert close_res.json()["resolved_at"] is not None


def test_incidents_analytics_and_root_causes(incident_app):
    client, _ = incident_app
    headers = auth_headers(client, "admin")

    client.post(
        "/api/records/incident",
        json={
            "site_id": "site-deye",
            "title": "Mất kết nối Internet",
            "severity": "critical",
            "category": "connectivity",
        },
        headers=headers,
    )

    sum_res = client.get("/api/incidents/summary?days=7", headers=headers)
    assert sum_res.status_code == 200
    data = sum_res.json()
    assert data["open"] >= 1
    assert "root_causes" in data
    assert len(data["root_causes"]) == 5
    assert any(rc["category"] == "connectivity" and rc["count"] >= 1 for rc in data["root_causes"])


def test_incidents_export_csv(incident_app):
    client, _ = incident_app
    headers = auth_headers(client, "admin")

    client.post(
        "/api/records/incident",
        json={
            "site_id": "site-deye",
            "title": "Sự cố xuất CSV",
            "severity": "medium",
            "category": "other",
        },
        headers=headers,
    )

    export_res = client.get("/api/incidents/export", headers=headers)
    assert export_res.status_code == 200
    assert "text/csv" in export_res.headers.get("content-type", "")
    assert "attachment; filename=incidents_export.csv" in export_res.headers.get("content-disposition", "")
    content = export_res.text
    assert "ID,Title,Site ID,Severity,Status" in content
    assert "Sự cố xuất CSV" in content


def test_incident_security_permissions(incident_app):
    client, _ = incident_app
    admin_headers = auth_headers(client, "admin")

    create_res = client.post(
        "/api/records/incident",
        json={
            "site_id": "site-deye",
            "title": "Cảnh báo bảo mật",
            "severity": "high",
        },
        headers=admin_headers,
    )
    assert create_res.status_code == 201
    inc_id = create_res.json()["id"]

    # Now switch to viewer
    viewer_headers = auth_headers(client, "viewer")

    # Viewer cannot acknowledge
    ack_res = client.post(f"/api/incidents/{inc_id}/acknowledge", json={}, headers=viewer_headers)
    assert ack_res.status_code == 403
