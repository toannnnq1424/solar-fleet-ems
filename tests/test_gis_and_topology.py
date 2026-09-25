"""Tests for GIS spatial engine and topology SLD validation."""

from solar_fleet.gis_engine import cluster_plants, haversine_distance_km
from solar_fleet.topology_engine import TopologyValidator


def test_haversine_distance_calculation():
    """Verify distance calculation between Ho Chi Minh City and Binh Duong."""
    # HCMC: (10.7769, 106.7009), Thu Dau Mot, Binh Duong: (10.9804, 106.6745)
    dist_km = haversine_distance_km(10.7769, 106.7009, 10.9804, 106.6745)
    assert 20.0 < dist_km < 30.0


def test_gis_plant_clustering():
    """Verify clustering groups nearby plants within distance threshold."""
    plants = [
        {"id": "p1", "name": "Plant 1", "latitude": 10.80, "longitude": 106.70, "capacity_kwp": 50.0},
        {"id": "p2", "name": "Plant 2", "latitude": 10.82, "longitude": 106.71, "capacity_kwp": 100.0},
        {"id": "p3", "name": "Hanoi Plant", "latitude": 21.02, "longitude": 105.83, "capacity_kwp": 200.0},
    ]

    clusters = cluster_plants(plants, distance_threshold_km=15.0)
    assert len(clusters) == 2

    # p1 and p2 should be clustered together
    clustered_group = next(c for c in clusters if c["type"] == "CLUSTER")
    assert clustered_group["count"] == 2
    assert clustered_group["total_capacity_kwp"] == 150.0

    # p3 should remain a single plant marker
    single_marker = next(c for c in clusters if c["type"] == "PLANT")
    assert single_marker["id"] == "p3"


def test_topology_dc_ac_ratio_validation():
    """Verify DC/AC ratio checks and advisory."""
    optimal = TopologyValidator.validate_dc_ac_oversizing_ratio(120.0, 100.0)
    assert optimal["status"] == "OPTIMAL"
    assert optimal["ratio"] == 1.2

    high_clip = TopologyValidator.validate_dc_ac_oversizing_ratio(180.0, 100.0)
    assert high_clip["status"] == "HIGH_CLIPPING"


def test_topology_rs485_bus_validation():
    """Verify RS485 bus collision detection."""
    bus_devices = [
        {"slave_id": 1, "baud_rate": 9600},
        {"slave_id": 2, "baud_rate": 9600},
        {"slave_id": 1, "baud_rate": 9600},  # Duplicate ID collision!
    ]
    check = TopologyValidator.validate_rs485_bus(bus_devices)
    assert check["valid"] is False
    assert len(check["issues"]) > 0


def test_topology_three_phase_balance():
    """Verify three-phase power imbalance percentage calculation."""
    balanced = TopologyValidator.check_three_phase_balance(1000.0, 1000.0, 1000.0)
    assert balanced["status"] == "BALANCED"
    assert balanced["imbalance_pct"] == 0.0

    unbalanced = TopologyValidator.check_three_phase_balance(3000.0, 1000.0, 1000.0)
    assert unbalanced["status"] == "UNBALANCED"
    assert unbalanced["imbalance_pct"] > 10.0


def test_fleet_map_data_endpoint(local):
    """Verify GET /api/fleet/map-data returns plants with GPS coordinates, weather, and clusters."""
    from tests.test_workspaces import login

    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/fleet/map-data", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "summary" in data
    assert "plants" in data
    assert "clusters" in data

    summary = data["summary"]
    assert "total_plants" in summary
    assert "geocoded_plants" in summary
    assert "total_mwp" in summary
    assert "current_mw" in summary

    for plant in data["plants"]:
        assert "id" in plant
        assert "name" in plant
        assert "capacity_kwp" in plant
        assert "current_power_kw" in plant
        assert "today_yield_kwh" in plant
        assert plant["status"] in ("NORMAL", "WARNING", "OFFLINE", "UNKNOWN")
        assert "weather" in plant
        assert "irradiance_w_per_m2" in plant["weather"]
        assert "temperature_c" in plant["weather"]


def test_fleet_topology_summary_and_site_detail(local):
    """Verify fleet topology summary and site-level detailed SLD electrical endpoints."""
    from tests.test_workspaces import login

    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/fleet/topology-summary", headers=headers)
    assert resp.status_code == 200
    summary = resp.json()
    assert "total_sites" in summary
    assert "total_inverters" in summary
    assert "total_bess_systems" in summary
    assert "sites" in summary
    assert len(summary["sites"]) > 0

    first_site_id = summary["sites"][0]["id"]

    resp_detail = client.get(f"/api/sites/{first_site_id}/topology-detail", headers=headers)
    assert resp_detail.status_code == 200
    detail = resp_detail.json()

    assert "site" in detail
    assert "electrical" in detail
    assert "validation" in detail
    assert "hierarchy" in detail

    ele = detail["electrical"]
    assert "pv_strings" in ele
    assert ele["pv_strings"] == []
    assert "bess" in ele
    assert "inverter" in ele
    assert "ac_panel" in ele
    assert "meter" in ele
    assert "eps_backup" in ele
    assert "grid" in ele

    val = detail["validation"]
    assert "dc_ac_ratio" in val
    assert "rs485_bus" in val
    assert "phase_balance" in val
    assert val["dc_ac_ratio"]["status"] == "UNKNOWN"
    assert val["rs485_bus"]["status"] == "UNKNOWN"
    assert val["phase_balance"]["status"] == "UNKNOWN"
