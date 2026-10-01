"""Unit and API tests for EMS Optimizer and Multi-Inverter Fleet Balancer."""

from __future__ import annotations

import pytest

from solar_fleet.ems_optimizer import (
    EVNTOUOptimizer,
    FleetInverterBalancer,
    InverterFleetMember,
)
ORIGIN = "http://127.0.0.1:8765"
PASSWORD = "SIMULATOR-workspace-password-only"


def _auth_headers(client, username="admin"):
    res = client.post(
        "/api/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
    csrf = res.json()["csrf"]
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf, "Content-Type": "application/json"}


class TestFleetInverterBalancer:
    def test_charge_allocation_favors_empty_battery(self):
        """Inverter with 20% SOC should get more charge power than one with 80% SOC."""
        inv1 = InverterFleetMember("inv-01", rated_power_kw=10.0, battery_capacity_kwh=10.0, current_soc_pct=20.0, max_charge_kw=6.0)
        inv2 = InverterFleetMember("inv-02", rated_power_kw=10.0, battery_capacity_kwh=10.0, current_soc_pct=80.0, max_charge_kw=6.0)

        res = FleetInverterBalancer.balance_fleet([inv1, inv2], target_total_kw=8.0, mode="charge")
        assert res.mode == "charge"
        assert res.allocations["inv-01"] > res.allocations["inv-02"]
        # inv1 had 80% headroom, inv2 had 20% headroom -> 4:1 ratio
        assert res.allocations["inv-01"] >= 5.0
        assert res.allocations["inv-02"] <= 3.0

    def test_discharge_allocation_favors_full_battery(self):
        """Inverter with 90% SOC should discharge more power than one with 25% SOC."""
        inv1 = InverterFleetMember("inv-01", rated_power_kw=10.0, battery_capacity_kwh=10.0, current_soc_pct=90.0, max_discharge_kw=6.0)
        inv2 = InverterFleetMember("inv-02", rated_power_kw=10.0, battery_capacity_kwh=10.0, current_soc_pct=25.0, max_discharge_kw=6.0)

        res = FleetInverterBalancer.balance_fleet([inv1, inv2], target_total_kw=6.0, mode="discharge")
        assert res.mode == "discharge"
        assert res.allocations["inv-01"] > res.allocations["inv-02"]

    def test_offline_member_gets_zero_allocation(self):
        inv1 = InverterFleetMember("inv-01", rated_power_kw=5.0, battery_capacity_kwh=10.0, current_soc_pct=50.0, online=True)
        inv2 = InverterFleetMember("inv-02", rated_power_kw=5.0, battery_capacity_kwh=10.0, current_soc_pct=50.0, online=False)

        res = FleetInverterBalancer.balance_fleet([inv1, inv2], target_total_kw=4.0, mode="charge")
        assert res.allocations["inv-02"] == 0.0
        assert res.allocations["inv-01"] == 4.0


class TestEVNTOUOptimizer:
    def test_optimizer_achieves_net_savings_on_manufacturing_tariff(self):
        optimizer = EVNTOUOptimizer(
            tariff_category="MANUFACTURING",
            voltage_level="LOW_VOLTAGE_UNDER_22KV",
            battery_capacity_kwh=15.0,
            max_charge_kw=6.0,
            max_discharge_kw=6.0,
        )
        typical_solar = [
            0.0, 0.0, 0.0, 0.0, 0.0, 0.2, 0.8, 2.0, 4.2, 6.5, 7.8, 8.5,
            8.2, 7.1, 5.2, 3.1, 1.2, 0.3, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0,
        ]
        typical_load = [
            1.5, 1.5, 1.5, 1.5, 2.0, 3.5, 5.0, 6.5, 7.0, 7.2, 7.0, 6.0,
            6.2, 7.1, 7.3, 6.8, 6.5, 7.0, 6.8, 5.5, 3.5, 2.5, 2.0, 1.8,
        ]

        res = optimizer.optimize_24h("site-01", typical_solar, typical_load, initial_soc_pct=40.0)
        assert res.total_baseline_cost_vnd > res.total_optimized_cost_vnd
        assert res.net_savings_vnd > 0.0
        assert res.savings_pct > 0.0  # Net positive savings via off-peak charge & peak shave
        assert len(res.slots_24h) == 24
        assert len(res.tou_programme) == 6
        assert res.battery_degradation_cost_vnd >= 0.0
        assert res.net_profit_vnd >= 0.0

    def test_optimizer_scenarios_p10_p90(self):
        optimizer = EVNTOUOptimizer(tariff_category="MANUFACTURING")
        solar = [0.0]*6 + [2.0, 5.0, 8.0, 9.0, 7.0, 3.0] + [0.0]*12
        load = [2.0]*24
        scenarios = optimizer.optimize_scenarios("site-01", solar, load)
        assert "nominal" in scenarios
        assert "p10_gloomy" in scenarios
        assert "p90_sunny" in scenarios
        assert scenarios["robust_savings_vnd"] <= scenarios["nominal"].net_savings_vnd


class TestEMSAPI:
    def test_ems_optimization_route(self, local):
        client, ctl = local
        headers = _auth_headers(client, "admin")

        from datetime import datetime, timedelta
        from zoneinfo import ZoneInfo
        from solar_fleet.domain import Sample, Source

        now = datetime.now(ZoneInfo("Asia/Ho_Chi_Minh"))
        samples = [
            Sample(
                device_id="sim-device",
                binding_id="bind-01",
                metric="pv_power",
                value=4500.0,
                unit="W",
                source=Source.CLOUD,
                source_timestamp=now - timedelta(hours=2),
                received_at=now - timedelta(hours=2),
                quality="GOOD",
            ),
            Sample(
                device_id="sim-device",
                binding_id="bind-01",
                metric="load_power",
                value=6500.0,
                unit="W",
                source=Source.CLOUD,
                source_timestamp=now - timedelta(hours=2),
                received_at=now - timedelta(hours=2),
                quality="GOOD",
            ),
        ]
        ctl.store.add_samples(samples)

        resp = client.get("/api/sites/sim-site/ems-optimization?category=MANUFACTURING", headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["site_id"] == "sim-site"
        assert data["total_baseline_cost_vnd"] > 0
        assert data["net_savings_vnd"] >= 0
        assert len(data["slots_24h"]) == 24
        assert len(data["tou_programme"]["slots"]) == 6

    def test_fleet_balance_route(self, local):
        client, ctl = local
        headers = _auth_headers(client, "admin")

        payload = {
            "target_total_kw": 12.0,
            "mode": "charge",
            "duration_hours": 1.0,
        }
        resp = client.post("/api/sites/sim-site/fleet-balance", json=payload, headers=headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["target_total_kw"] == 5.0  # Clamped by single device max_charge_kw = 5.0
        assert data["mode"] == "charge"
        assert len(data["allocations"]) > 0
