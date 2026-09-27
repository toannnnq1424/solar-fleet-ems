"""Tests for VPP aggregator and energy optimizer modules."""


import pytest

# ---------------------------------------------------------------------------
# VPP Aggregator Tests
# ---------------------------------------------------------------------------
from solar_fleet.vpp_aggregator import (
    DERAsset,
    DERType,
    GridService,
    VPPAggregator,
)


class TestDERAsset:

    def test_battery_flexibility(self):
        asset = DERAsset(
            "bat1", "site1", DERType.BATTERY,
            rated_power_kw=10.0, capacity_kwh=20.0,
            soc=0.5, soc_min=0.1, soc_max=0.9,
        )
        assert asset.available_charge_kw == 10.0
        assert asset.available_discharge_kw == 10.0

    def test_empty_battery_no_discharge(self):
        asset = DERAsset(
            "bat1", "site1", DERType.BATTERY,
            rated_power_kw=10.0, capacity_kwh=20.0,
            soc=0.05, soc_min=0.05,
        )
        assert asset.available_discharge_kw == 0.0

    def test_full_battery_no_charge(self):
        asset = DERAsset(
            "bat1", "site1", DERType.BATTERY,
            rated_power_kw=10.0, capacity_kwh=20.0,
            soc=0.95, soc_max=0.95,
        )
        assert asset.available_charge_kw == 0.0

    def test_solar_no_battery_flex(self):
        asset = DERAsset(
            "pv1", "site1", DERType.SOLAR_PV,
            rated_power_kw=50.0,
        )
        assert asset.available_charge_kw == 0.0
        assert asset.available_discharge_kw == 0.0


class TestVPPAggregator:

    def _make_vpp(self):
        vpp = VPPAggregator("vpp1", "Test VPP")
        vpp.register_asset(DERAsset(
            "pv1", "site1", DERType.SOLAR_PV,
            rated_power_kw=50.0, current_power_kw=30.0,
        ))
        vpp.register_asset(DERAsset(
            "bat1", "site1", DERType.BATTERY,
            rated_power_kw=10.0, capacity_kwh=20.0,
            soc=0.6,
        ))
        vpp.register_asset(DERAsset(
            "bat2", "site2", DERType.BATTERY,
            rated_power_kw=15.0, capacity_kwh=30.0,
            soc=0.7,
        ))
        vpp.register_asset(DERAsset(
            "ev1", "site1", DERType.EV_CHARGER,
            rated_power_kw=22.0, current_power_kw=11.0,
        ))
        return vpp

    def test_portfolio(self):
        vpp = self._make_vpp()
        p = vpp.portfolio()
        assert p.asset_count == 4
        assert p.site_count == 2
        assert p.total_rated_kw > 0
        assert p.total_battery_kwh == 50.0
        assert len(p.available_services) > 0

    def test_dispatch_discharge(self):
        vpp = self._make_vpp()
        commands = vpp.dispatch(15.0, GridService.ENERGY_ARBITRAGE)
        assert len(commands) > 0
        total = sum(c.target_power_kw for c in commands)
        assert total <= 15.0
        assert total > 0

    def test_dispatch_charge(self):
        vpp = self._make_vpp()
        commands = vpp.dispatch(-10.0, GridService.ENERGY_ARBITRAGE)
        assert len(commands) > 0
        total = sum(c.target_power_kw for c in commands)
        assert total < 0

    def test_dr_event(self):
        vpp = self._make_vpp()
        event = vpp.trigger_dr_event(
            reduction_kw=10.0, duration_min=30.0,
        )
        assert event["requested_kw"] == 10.0
        assert event["achieved_kw"] > 0
        assert event["compliance_pct"] > 0

    def test_peak_shave(self):
        vpp = self._make_vpp()
        commands = vpp.peak_shave(
            current_import_kw=80.0, limit_kw=50.0,
        )
        assert len(commands) > 0

    def test_peak_shave_no_action(self):
        vpp = self._make_vpp()
        commands = vpp.peak_shave(
            current_import_kw=30.0, limit_kw=50.0,
        )
        assert len(commands) == 0

    def test_update_telemetry(self):
        vpp = self._make_vpp()
        vpp.update_telemetry("bat1", 5.0, soc=0.55)
        assert vpp._assets["bat1"].current_power_kw == 5.0
        assert vpp._assets["bat1"].soc == 0.55

    def test_status(self):
        vpp = self._make_vpp()
        status = vpp.status()
        assert status["vpp_id"] == "vpp1"
        assert "portfolio" in status
        assert status["state"] == "idle"

    def test_remove_asset(self):
        vpp = self._make_vpp()
        removed = vpp.remove_asset("ev1")
        assert removed is not None
        assert vpp.portfolio().asset_count == 3


# ---------------------------------------------------------------------------
# Energy Optimizer Tests
# ---------------------------------------------------------------------------

from solar_fleet.energy_optimizer import (
    EnergyOptimizer,
    EnergyState,
    OptimizationMode,
    TariffSchedule,
)


class TestEnergyState:

    def test_self_consumption_ratio(self):
        state = EnergyState(
            pv_power_kw=10.0, load_power_kw=8.0,
        )
        assert state.self_consumption_ratio == pytest.approx(0.8)

    def test_autarky_100(self):
        state = EnergyState(
            pv_power_kw=10.0, load_power_kw=5.0, grid_power_kw=-5.0,
        )
        assert state.autarky_ratio == 1.0

    def test_no_pv(self):
        state = EnergyState(
            pv_power_kw=0.0, load_power_kw=5.0, grid_power_kw=5.0,
        )
        assert state.self_consumption_ratio == 0.0
        assert state.autarky_ratio == 0.0

    def test_net_power(self):
        state = EnergyState(
            pv_power_kw=10.0, load_power_kw=3.0, ev_power_kw=2.0,
        )
        assert state.net_power_kw == 5.0


class TestTariffSchedule:

    def test_peak_detection(self):
        tariff = TariffSchedule(peak_hours=[17, 18, 19, 20, 21])
        assert tariff.is_peak(18)
        assert not tariff.is_peak(12)

    def test_off_peak(self):
        tariff = TariffSchedule(off_peak_hours=[0, 1, 2, 3, 4, 5])
        assert tariff.is_off_peak(3)
        assert not tariff.is_off_peak(12)


class TestEnergyOptimizer:

    def _make_optimizer(self):
        opt = EnergyOptimizer(
            battery_capacity_kwh=10.0,
            max_charge_kw=5.0,
            max_discharge_kw=5.0,
        )
        opt.tariff = TariffSchedule(
            import_rates=[0.05] * 6 + [0.10] * 11 + [0.20] * 5 + [0.10] * 2,
            export_rates=[0.04] * 24,
            peak_hours=list(range(17, 22)),
            off_peak_hours=list(range(0, 6)),
        )
        return opt

    def test_self_consumption_surplus(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.SELF_CONSUMPTION
        state = EnergyState(
            pv_power_kw=10.0, load_power_kw=3.0, battery_soc=0.5,
        )
        result = opt.optimize(state, hour=12)
        assert result.battery_setpoint_kw > 0  # Should charge
        assert result.mode == "self_consumption"

    def test_self_consumption_deficit(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.SELF_CONSUMPTION
        state = EnergyState(
            pv_power_kw=2.0, load_power_kw=8.0, battery_soc=0.6,
        )
        result = opt.optimize(state, hour=20)
        assert result.battery_setpoint_kw < 0  # Should discharge

    def test_cost_minimum_peak(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.COST_MINIMUM
        state = EnergyState(
            pv_power_kw=0.0, load_power_kw=5.0, battery_soc=0.7,
        )
        result = opt.optimize(state, hour=19)
        assert result.battery_setpoint_kw < 0
        assert result.battery_strategy == "time_of_use"

    def test_cost_minimum_off_peak(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.COST_MINIMUM
        state = EnergyState(
            pv_power_kw=0.0, load_power_kw=2.0, battery_soc=0.3,
        )
        result = opt.optimize(state, hour=3)
        assert result.battery_setpoint_kw > 0  # Should charge

    def test_peak_shaving(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.PEAK_SHAVING
        state = EnergyState(
            pv_power_kw=5.0, load_power_kw=80.0, battery_soc=0.7,
        )
        result = opt.optimize(state, hour=18)
        assert result.battery_setpoint_kw < 0

    def test_backup_mode(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.BACKUP
        state = EnergyState(
            pv_power_kw=10.0, load_power_kw=3.0, battery_soc=0.3,
        )
        result = opt.optimize(state, hour=12)
        assert result.battery_setpoint_kw > 0
        assert result.battery_strategy == "backup_reserve"

    def test_step_accumulates(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.SELF_CONSUMPTION
        state = EnergyState(
            pv_power_kw=8.0, load_power_kw=5.0, battery_soc=0.5,
        )
        for _ in range(60):
            opt.step(state, dt_minutes=1.0)

        acc = opt.accumulators()
        assert acc["step_count"] == 60
        assert acc["total_pv_kwh"] > 0
        assert acc["total_load_kwh"] > 0

    def test_manual_mode(self):
        opt = self._make_optimizer()
        opt.mode = OptimizationMode.MANUAL
        state = EnergyState(
            pv_power_kw=5.0, load_power_kw=3.0,
        )
        result = opt.optimize(state)
        assert result.battery_setpoint_kw == 0.0
        assert "Manual" in result.recommendations[0]
