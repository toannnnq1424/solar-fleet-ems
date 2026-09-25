"""Tests for overview summary 11-blocks API and TOU/EMS rule conflict detection."""

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.runtime import detect_schedule_rule_conflicts


def test_site_overview_summary_11_blocks(local):
    """Verify that /api/sites/{id}/overview-summary returns all 11 required blocks with safe lock states."""
    client, _ = local
    headers = login(local, "admin")

    # Create a test site
    site_resp = client.post(
        "/api/sites",
        json={
            "name": "Bình Dương Factory Solar 50kWp",
            "customer": "Công ty TNHH May Mặc Sài Gòn",
            "address": "KCN VSIP II, Bến Cát, Bình Dương",
            "timezone": "Asia/Ho_Chi_Minh",
            "capacity_kwp": 50.0,
            "latitude": 11.0823,
            "longitude": 106.6631,
        },
        headers=headers,
    )
    assert site_resp.status_code == 201
    site_id = site_resp.json()["id"]

    # Request overview summary
    resp = client.get(f"/api/sites/{site_id}/overview-summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    # 1. Site info & location
    assert data["site"]["name"] == "Bình Dương Factory Solar 50kWp"
    assert data["location_info"]["latitude"] == 11.0823
    assert data["location_info"]["capacity_kwp"] == 50.0

    # 2. Energy flow
    assert "energy_flow" in data
    assert "pv_w" in data["energy_flow"]
    assert "battery_w" in data["energy_flow"]
    assert "grid_w" in data["energy_flow"]
    assert "load_w" in data["energy_flow"]

    # 3. Quick presets - MUST be locked safely (unknown-can't-click)
    presets = data["quick_presets"]
    assert len(presets) >= 4
    for p in presets:
        assert p["can_actuate"] is False
        assert p["status"] == "LOCKED_UNKNOWN"
        assert "reason" in p and len(p["reason"]) > 0

    # 4. Plant status & periods
    ps = data["plant_status"]
    assert "today_yield_kwh" in ps
    assert "month_yield_kwh" in ps
    assert "year_yield_kwh" in ps
    assert "total_yield_kwh" in ps

    # 5. Self-consumption
    sc = data["self_consumption"]
    assert sc["self_consumption_pct"] is None
    assert sc["self_sufficiency_pct"] is None

    # 6. Weather & forecast
    w = data["weather"]
    assert "temperature_c" in w
    assert "irradiance_wm2" in w
    assert "hourly_forecast" in w
    assert isinstance(w["hourly_forecast"], list)

    # 7. Equipment
    assert "equipment" in data
    assert "items" in data["equipment"]

    # 8. Connectivity
    conn = data["connectivity"]
    assert "local_agent" in conn
    assert "cloud_api" in conn

    # 9 & 10. Alerts and commands
    assert "recent_alerts" in data
    assert "recent_commands" in data


@pytest.mark.asyncio
async def test_schedule_rule_conflict_detector():
    """Verify that detect_schedule_rule_conflicts flags contradictory operational modes."""
    slots = [
        {
            "day": 0,
            "start": "17:00",
            "end": "20:00",
            "mode": "discharge",
            "target_soc": 20,
            "power_kw": 15.0,
        },
        {
            "day": 0,
            "start": "22:00",
            "end": "24:00",
            "mode": "charge",
            "target_soc": 25,  # Low target SOC warning
            "power_kw": 10.0,
        },
    ]

    rules = [
        {
            "id": "rule_peak_charge",
            "name": "Bảo vệ lưới cao điểm",
            "actions": [{"intent": "force_grid_charge", "device_id": "inv-1"}],
        }
    ]

    conflicts = detect_schedule_rule_conflicts(slots, rules)
    assert len(conflicts) >= 2

    # Verify mode contradiction
    mode_conflict = next(c for c in conflicts if c["conflict_type"] == "MODE_CONTRADICTION")
    assert mode_conflict["slot_day"] == 0
    assert mode_conflict["severity"] == "WARNING"
    assert "17:00-20:00" in mode_conflict["time_window"]

    # Verify low SOC advisory
    soc_conflict = next(c for c in conflicts if c["conflict_type"] == "LOW_TARGET_SOC_WARNING")
    assert soc_conflict["severity"] == "INFO"


def test_schedule_conflict_api_endpoint(local):
    """Verify the /api/schedules/{id}/detect-conflicts endpoint."""
    client, ctl = local
    headers = login(local, "admin")

    site_id = "sim-site"
    rule_id = "rule-emergency-charge"
    sched_id = "sched-daily-tou"

    # Store a rule for sim-site
    ctl.store.put(
        "rule",
        rule_id,
        {
            "id": rule_id,
            "name": "Bảo vệ lưới cao điểm",
            "site_id": site_id,
            "actions": [{"intent": "force_grid_charge", "device_id": "sim-device"}],
            "state": "ACTIVE",
        },
    )

    # Store a schedule with discharge during peak hours (17:00-20:00)
    ctl.store.put(
        "schedule",
        sched_id,
        {
            "id": sched_id,
            "name": "Daily TOU Schedule",
            "site_id": site_id,
            "slots": [
                {
                    "day": 0,
                    "start": "17:00",
                    "end": "20:00",
                    "mode": "discharge",
                    "target_soc": 20,
                    "power_kw": 10.0,
                }
            ],
            "state": "ACTIVE",
        },
    )

    conflict_resp = client.post(f"/api/schedules/{sched_id}/detect-conflicts", json={}, headers=headers)
    assert conflict_resp.status_code == 200
    data = conflict_resp.json()
    assert data["schedule_id"] == sched_id
    assert data["total_conflicts"] >= 1
    assert any(c["conflict_type"] == "MODE_CONTRADICTION" for c in data["conflicts"])


def test_overview_charts_and_comparison_data(local):
    c, _ = local
    h = login(local)
    data = c.get("/api/sites/sim-site/overview-summary", headers=h).json()
    assert data["generation_chart_24h"] == []
    for period in ("today", "month", "year"):
        assert data["comparison_yield_load"][period]["yield_kwh"] is None
    assert data["weather"]["forecast_24h"] == []


def test_vendor_registers_api(local):
    c, _ = local
    h = login(local)
    for brand in ("goodwe", "sungrow", "huawei", "growatt", "generic_unknown"):
        r = c.get("/api/vendor-registers/" + brand, headers=h)
        assert r.status_code == 200
        assert r.json()["registers"] == []
        assert r.json()["alarms"] == []


def test_site_diagnostics_iec62446_and_sign(local):
    c, ctl = local
    h = login(local, "engineer")
    url = "/api/sites/sim-site/diagnostics-checklist"
    diag = c.get(url, headers=h).json()
    assert diag["standard"] is None
    assert diag["certificate"] is None
    assert len(diag["steps"]) == 6
    assert c.post(url, headers=h, json={"notes": "Everything passed"}).status_code == 422
    for check in ("topology", "meter_ct", "power_direction", "battery", "control_readback", "alarms"):
        r = c.post(
            url,
            headers=h,
            json={
                "site_id": "sim-site",
                "check": check,
                "result": "pass",
                "evidence": "Local simulator observation only",
            },
        )
        assert r.status_code == 200
        assert r.json()["unlocks_control"] is False
    assert len(ctl.store.list("commissioning")) == 6
    assert c.get(url, headers=h).json()["certificate"] is None
    bad = c.post(
        url,
        headers=h,
        json={"site_id": "other-site", "check": "battery", "result": "pass", "evidence": "Wrong site"},
    )
    assert bad.status_code == 422


def test_site_network_status_api(local):
    c, ctl = local
    h = login(local)
    url = "/api/sites/sim-site/network-status"
    net = c.get(url, headers=h).json()
    assert net["local_agent"]["enrolled"] is False
    assert net["local_agent"]["latency_ms"] is None
    assert net["rs485_bus"]["baudrate"] is None
    ctl.store.put(
        "agent", "a", {"id": "a", "site_id": "sim-site", "enabled": True, "token_hash": "must-not-leak"}
    )
    r = c.get(url, headers=h)
    assert r.json()["local_agent"]["enrolled"] is True
    assert r.json()["local_agent"]["connected"] is None
    assert "must-not-leak" not in r.text


def test_site_telemetry_timeseries_stored_points_api(local):
    from solar_fleet.domain import Sample, Source, utcnow

    c, ctl = local
    h = login(local)
    url = "/api/sites/sim-site/telemetry-timeseries?metric=pv_power"
    assert c.get(url, headers=h).json()["samples"] == []
    ctl.store.add_samples(
        [
            Sample(
                device_id="sim-device",
                metric="pv_w",
                unit="W",
                value=1234,
                source=Source.SIMULATOR,
                source_timestamp=utcnow() - __import__("datetime").timedelta(seconds=1),
                quality="GOOD",
                binding_id="test",
            )
        ]
    )
    row = c.get(url, headers=h).json()
    assert row["metric"] == "pv_w"
    assert len(row["samples"]) == 1
    assert row["samples"][0]["value"] == 1234
