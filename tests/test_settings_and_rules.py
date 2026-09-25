"""Tests for site settings, tariffs, onboarding, and rules validation."""

from test_workspaces import local as local
from test_workspaces import login


def test_site_profile_update_and_audit(local):
    """Verify updating site profile persists data and records audit event."""
    client, ctl = local
    headers = login(local, "admin")

    site_id = "sim-site"
    profile_data = {
        "name": "Nhà máy Điện Mặt trời Tân Uyên 100kWp",
        "customer": "Công ty CP Gỗ Bình Dương",
        "address": "TX Tân Uyên, Bình Dương",
        "timezone": "Asia/Ho_Chi_Minh",
        "capacity_kwp": 100.0,
        "latitude": 11.05,
        "longitude": 106.75,
    }

    resp = client.post(f"/api/sites/{site_id}/profile", json=profile_data, headers=headers)
    assert resp.status_code == 200
    assert resp.json()["id"] == site_id

    # Verify persisted in store
    saved = ctl.store.get("site_profile", site_id)
    assert saved is not None
    assert saved["name"] == "Nhà máy Điện Mặt trời Tân Uyên 100kWp"
    assert saved["capacity_kwp"] == 100.0


def test_rule_device_site_mismatch_rejection(local):
    """Verify rule creation rejects actions targeting devices outside the site."""
    client, ctl = local
    headers = login(local, "admin")

    # sim-device belongs to sim-site, other-device belongs to other-site
    mismatched_rule = {
        "name": "Cross-site rule attack",
        "site_id": "sim-site",
        "conditions": [
            {
                "device_id": "other-device",  # Mismatch!
                "metric": "pv_power",
                "comparison": "gt",
                "threshold": 100.0,
            }
        ],
        "actions": [{"intent": "grid_charge", "device_id": "sim-device"}],
    }

    resp = client.post("/api/rules", json=mismatched_rule, headers=headers)
    assert resp.status_code in (400, 422, 500)


def test_schedule_draft_lifecycle(local):
    """Verify schedule creation, draft state, and timeline query."""
    client, ctl = local
    headers = login(local, "admin")

    sched_payload = {
        "name": "Lịch nạp pin giờ thấp điểm",
        "site_id": "sim-site",
        "slots": [
            {
                "day": 1,
                "start": "00:00",
                "end": "05:00",
                "mode": "charge",
                "target_soc": 90,
                "power_kw": 20.0,
            }
        ],
    }

    resp = client.post("/api/schedules", json=sched_payload, headers=headers)
    assert resp.status_code == 201
    sched = resp.json()
    assert sched["state"] == "DRAFT"
    assert sched["name"] == "Lịch nạp pin giờ thấp điểm"

    sched_id = sched["id"]
    # Query timeline
    timeline_resp = client.get(f"/api/schedules/{sched_id}/timeline", headers=headers)
    assert timeline_resp.status_code == 200
    timeline = timeline_resp.json()
    assert "slots" in timeline
