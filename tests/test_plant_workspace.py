"""Tests for Plant Workspace: Benchmarking, Regions, Portfolio, and Onboarding."""

from test_workspaces import local as local
from test_workspaces import login


def test_fleet_plants_benchmarking_api(local):
    """Verify GET /api/fleet/plants-benchmarking returns ranking, PR, and specific yield."""
    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/fleet/plants-benchmarking", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "total_plants" in data
    assert "fleet_avg_pr_pct" in data
    assert "fleet_avg_specific_yield" in data
    assert "plants" in data
    assert "top_performers" in data

    assert data["fleet_avg_pr_pct"] is None
    assert data["fleet_avg_specific_yield"] is None

    for plant in data["plants"]:
        assert "id" in plant
        assert "name" in plant
        assert "capacity_kwp" in plant
        assert "today_yield_kwh" in plant
        assert "specific_yield_kwh_per_kwp" in plant
        assert "performance_ratio_pct" in plant
        assert plant["status"] == "IRRADIANCE_REFERENCE_REQUIRED"


def test_fleet_regions_summary_api(local):
    """Verify GET /api/fleet/regions-summary aggregates plants by geographical regions."""
    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/fleet/regions-summary", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "total_sites" in data
    assert "regions" in data
    regions = data["regions"]
    assert "north" in regions
    assert "central" in regions
    assert "south" in regions

    for r_key, r_info in regions.items():
        assert "name" in r_info
        assert "plants_count" in r_info
        assert "total_kwp" in r_info
        assert "today_kwh" in r_info
        assert "sites" in r_info


def test_plant_onboarding_and_profile_lifecycle(local):
    """Verify onboarding a new plant with capacity, coordinates and timezone."""
    client, _ = local
    headers = login(local, "admin")

    # Create new plant via onboarding payload
    payload = {
        "name": "Binh Duong Logistics Hub Solar",
        "customer": "Logistics Corp Vietnam",
        "address": "VSIP II, Binh Duong",
        "timezone": "Asia/Ho_Chi_Minh",
        "capacity_kwp": 250.0,
        "latitude": 11.0542,
        "longitude": 106.6668,
    }
    resp = client.post("/api/sites", json=payload, headers=headers)
    assert resp.status_code in (200, 201)
    new_site = resp.json()
    assert new_site["name"] == "Binh Duong Logistics Hub Solar"
    assert new_site["capacity_kwp"] == 250.0
    site_id = new_site["id"]

    # Verify site appears in regions summary
    resp_regions = client.get("/api/fleet/regions-summary", headers=headers)
    assert resp_regions.status_code == 200
    south_sites = [s["id"] for s in resp_regions.json()["regions"]["south"]["sites"]]
    assert site_id in south_sites

    # Update plant profile
    update_payload = dict(new_site)
    update_payload["capacity_kwp"] = 300.0
    resp_update = client.post(f"/api/sites/{site_id}/profile", json=update_payload, headers=headers)
    assert resp_update.status_code == 200
    updated_site = resp_update.json()
    assert updated_site["capacity_kwp"] == 300.0
