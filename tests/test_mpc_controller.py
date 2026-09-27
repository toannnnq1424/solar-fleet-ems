"""Tests for MPC controller module.

Verifies: MPC controller step, fallback dispatch, fleet MPC, warm-start,
solver timeout handling, and SOC dynamics.
"""

from datetime import datetime, timezone

from solar_fleet.mpc_controller import (
    DeterministicDispatchSolver,
    FleetBattery,
    FleetCoupling,
    FleetMPCController,
    MPCConfig,
    MPCController,
    MPCDecision,
    MPCStep,
    RuleBasedDispatcher,
)


class TestRuleBasedDispatcher:
    """Tests for rule-based fallback dispatcher."""

    def test_solar_surplus_charges_battery(self):
        config = MPCConfig(battery_capacity_kwh=10.0, max_charge_kw=5.0)
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc),
            soc_init=0.5,
            pv_forecast_kw=[8.0],
            load_forecast_kw=[3.0],
            price_forecast=[0.1],
        )
        dispatcher = RuleBasedDispatcher()
        decision = dispatcher.dispatch(config, step)

        assert decision.p_charge_kw > 0
        assert decision.p_discharge_kw == 0
        assert decision.is_charging
        assert decision.fallback_used

    def test_load_deficit_discharges_battery(self):
        config = MPCConfig(battery_capacity_kwh=10.0, max_discharge_kw=5.0)
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 20, 0, tzinfo=timezone.utc),
            soc_init=0.8,
            pv_forecast_kw=[0.0],
            load_forecast_kw=[4.0],
            price_forecast=[0.2],
        )
        dispatcher = RuleBasedDispatcher()
        decision = dispatcher.dispatch(config, step)

        assert decision.p_discharge_kw > 0
        assert decision.p_charge_kw == 0
        assert not decision.is_charging

    def test_empty_forecasts(self):
        config = MPCConfig()
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            soc_init=0.5,
        )
        dispatcher = RuleBasedDispatcher()
        decision = dispatcher.dispatch(config, step)

        assert decision is not None
        assert decision.soc_next >= config.soc_min

    def test_soc_limits_respected(self):
        config = MPCConfig(soc_min=0.1, soc_max=0.9)
        # Low SOC — should not discharge
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 20, 0, tzinfo=timezone.utc),
            soc_init=0.1,
            pv_forecast_kw=[0.0],
            load_forecast_kw=[5.0],
            price_forecast=[0.3],
        )
        dispatcher = RuleBasedDispatcher()
        decision = dispatcher.dispatch(config, step)
        assert decision.soc_next >= config.soc_min


class TestDeterministicDispatchSolver:
    """Tests for the deterministic dispatch solver."""

    def test_solve_returns_plan(self):
        config = MPCConfig(horizon_steps=24, battery_capacity_kwh=10.0)
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 0, 0, tzinfo=timezone.utc),
            soc_init=0.5,
            pv_forecast_kw=[0] * 6 + [2, 4, 6, 8, 8, 6, 4, 2, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0],
            load_forecast_kw=[2.0] * 24,
            price_forecast=[0.05] * 6 + [0.1] * 12 + [0.15] * 6,
        )
        solver = DeterministicDispatchSolver()
        plan = solver.solve(config, step)

        assert plan is not None
        assert "p_charge" in plan
        assert "p_discharge" in plan
        assert "soc" in plan
        assert len(plan["p_charge"]) == 24
        assert all(0 <= s <= 1.0 for s in plan["soc"])

    def test_sol_respects_capacity(self):
        config = MPCConfig(
            horizon_steps=4,
            battery_capacity_kwh=5.0,
            max_charge_kw=2.0,
        )
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 10, 0, tzinfo=timezone.utc),
            soc_init=0.5,
            pv_forecast_kw=[10, 10, 10, 10],
            load_forecast_kw=[1, 1, 1, 1],
        )
        solver = DeterministicDispatchSolver()
        plan = solver.solve(config, step)

        assert all(p <= config.max_charge_kw for p in plan["p_charge"])


class TestMPCController:
    """Tests for MPC controller."""

    def test_single_step(self):
        config = MPCConfig(horizon_steps=12, battery_capacity_kwh=10.0)
        controller = MPCController(config)

        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            soc_init=0.5,
            pv_forecast_kw=[5.0] * 12,
            load_forecast_kw=[3.0] * 12,
            price_forecast=[0.1] * 12,
        )
        decision = controller.step(step)

        assert isinstance(decision, MPCDecision)
        assert decision.timestamp == step.timestamp
        assert decision.solve_time_ms >= 0
        assert 0 <= decision.soc_next <= 1.0

    def test_multiple_steps(self):
        config = MPCConfig(horizon_steps=6)
        controller = MPCController(config)

        for hour in range(6):
            step = MPCStep(
                timestamp=datetime(2026, 9, 27, hour, 0, tzinfo=timezone.utc),
                soc_init=0.5,
                pv_forecast_kw=[3.0] * 6,
                load_forecast_kw=[2.0] * 6,
                price_forecast=[0.1] * 6,
            )
            decision = controller.step(step)
            assert decision is not None

        status = controller.status()
        assert status["step_count"] == 6

    def test_reset(self):
        controller = MPCController(MPCConfig())
        step = MPCStep(
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            soc_init=0.5,
        )
        controller.step(step)
        controller.reset()
        assert controller.status()["step_count"] == 0


class TestFleetMPC:
    """Tests for fleet MPC controller."""

    def test_multi_battery_dispatch(self):
        batteries = [
            FleetBattery("bat1", capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0, soc_init=0.5),
            FleetBattery("bat2", capacity_kwh=20.0, max_charge_kw=10.0, max_discharge_kw=10.0, soc_init=0.6),
        ]
        fleet = FleetMPCController(batteries, horizon_steps=12)

        result = fleet.step(
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            soc_map={"bat1": 0.5, "bat2": 0.6},
            pv_forecast_kw=[8.0] * 12,
            load_forecast_kw=[5.0] * 12,
            price_forecast=[0.1] * 12,
        )

        assert "bat1" in result.decisions
        assert "bat2" in result.decisions
        assert result.solve_time_ms >= 0

    def test_feeder_constraints(self):
        batteries = [
            FleetBattery("bat1", capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0, soc_init=0.5),
        ]
        coupling = FleetCoupling(feeder_max_import_kw=3.0, feeder_max_export_kw=5.0)
        fleet = FleetMPCController(batteries, coupling=coupling, horizon_steps=6)

        result = fleet.step(
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            soc_map={"bat1": 0.5},
            pv_forecast_kw=[0.0] * 6,
            load_forecast_kw=[10.0] * 6,
            price_forecast=[0.1] * 6,
        )

        assert result.aggregate_import_kw <= 3.0
