"""Tests for full workspace navigation, site commissioning, and inter-workspace linking."""

from test_workspaces import local as local
from test_workspaces import login


def test_full_site_onboarding_and_workspace_navigation(local):
    """Verify full end-to-end site onboarding, overview summary, and handover checklist."""
    client, ctl = local
    headers = login(local, "admin")

    # 1. Create a new plant via API
    create_payload = {
        "name": "Nhà máy May Bình Dương 250kWp",
        "customer": "Công ty TNHH May Quốc Tế",
        "address": "KCN Sóng Thần 3, Thủ Dầu Một, Bình Dương",
        "timezone": "Asia/Ho_Chi_Minh",
        "capacity_kwp": 250.0,
        "latitude": 10.9804,
        "longitude": 106.6745,
    }
    resp = client.post("/api/sites", json=create_payload, headers=headers)
    assert resp.status_code == 201
    site = resp.json()
    site_id = site["id"]

    # 2. Access overview summary (11 blocks)
    overview_resp = client.get(f"/api/sites/{site_id}/overview-summary", headers=headers)
    assert overview_resp.status_code == 200
    ov_data = overview_resp.json()
    assert ov_data["site"]["name"] == "Nhà máy May Bình Dương 250kWp"
    assert len(ov_data["quick_presets"]) >= 4

    # 3. Check handover protocol API
    handover_resp = client.get(f"/api/sites/{site_id}/handover", headers=headers)
    assert handover_resp.status_code == 200

    # 4. Check energy analytics endpoint
    energy_resp = client.get(f"/api/sites/{site_id}/energy", headers=headers)
    assert energy_resp.status_code == 200


def test_journal_and_realtime_navigation_links(local):
    """Verify journal and realtime monitoring navigation endpoints."""
    client, ctl = local
    headers = login(local, "admin")

    res_sum = client.get("/api/journal/summary", headers=headers)
    assert res_sum.status_code == 200
    assert "total_today" in res_sum.json()

    res_cmds = client.get("/api/journal/commands", headers=headers)
    assert res_cmds.status_code == 200
    assert "items" in res_cmds.json()

    res_audit = client.get("/api/journal/audit", headers=headers)
    assert res_audit.status_code == 200
    assert res_audit.json()["hash_chain_valid"] is True

    res_export = client.get("/api/journal/export", headers=headers)
    assert res_export.status_code == 200
    assert "text/csv" in res_export.headers["content-type"]
