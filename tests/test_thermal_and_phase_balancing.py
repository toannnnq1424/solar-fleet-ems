"""Tests for thermal load management and 3-phase asymmetric phase balancing.

Tests:
- Heat pump Carnot COP calculations and bounds
- Stratified DHW buffer tank thermal storage dynamics
- 2R2C building envelope thermal inertia model
- SG-Ready 4-state controller and relay states
- Deferrable load scheduler under solar surplus and dynamic tariffs
- Symmetrical component decomposition (Fortescue transform)
- IEC 61000-4-30 Voltage and Current Unbalance Factor (VUF/CUF)
- Asymmetric per-phase active and reactive power dispatch
- Zero-export fast closed loop with PID and ramp rate limiting
- 15-minute / 30-minute rolling demand window peak shaver
"""

import pytest

from solar_fleet.phase_balancer import (
    AsymmetricPhaseBalancer,
    InverterPhaseLimits,
    PhaseMeasurement,
    PhaseUnbalanceEvaluator,
    RollingPeakDemandShaver,
    ZeroExportController,
    calculate_symmetrical_components,
)
from solar_fleet.thermal_load_manager import (
    BuildingThermalModel,
    DeferrableLoad,
    DeferrableLoadScheduler,
    HeatPumpModel,
    LoadCategory,
    SGReadyController,
    SGReadyState,
    ThermalStorageTank,
)

# ---------------------------------------------------------------------------
# Thermal Load Manager Tests
# ---------------------------------------------------------------------------

class TestThermalLoadManager:
    def test_heat_pump_cop_calculation(self):
        hp = HeatPumpModel(nominal_cop=3.8, carnot_efficiency=0.50)
        # Ambient 7°C, Supply 35°C (delta_T = 28°C)
        cop_7c = hp.calculate_cop(ambient_temp_c=7.0, supply_temp_c=35.0)
        assert 3.0 <= cop_7c <= 6.0

        # Cold ambient (-5°C) -> lower COP
        cop_cold = hp.calculate_cop(ambient_temp_c=-5.0, supply_temp_c=35.0)
        assert cop_cold < cop_7c
        assert cop_cold >= 1.5

    def test_heat_pump_power_modulation(self):
        hp = HeatPumpModel(min_electric_kw=0.5, max_electric_kw=3.5)
        p_zero = hp.calculate_power(required_thermal_kw=0.0, ambient_temp_c=7.0)
        assert p_zero["electric_power_kw"] == 0.0
        assert p_zero["thermal_power_kw"] == 0.0

        p_mod = hp.calculate_power(required_thermal_kw=6.0, ambient_temp_c=7.0)
        assert p_mod["electric_power_kw"] >= 0.5
        assert p_mod["electric_power_kw"] <= 3.5
        assert p_mod["thermal_power_kw"] > 0.0

    def test_thermal_storage_tank(self):
        tank = ThermalStorageTank(volume_liters=300.0, current_temp_c=50.0, cold_water_inlet_c=10.0)
        assert tank.water_mass_kg == 300.0
        assert tank.stored_energy_kwh > 0.0
        assert tank.maximum_surplus_capacity_kwh > 0.0

        # Simulate 1 hour with 4 kW thermal input and 50 liters draw
        res = tank.simulate_step(thermal_input_kw=4.0, hot_water_draw_liters=50.0, duration_hours=1.0)
        assert "tank_temp_c" in res
        assert res["standby_loss_kwh"] >= 0.0
        assert res["draw_energy_kwh"] > 0.0

    def test_building_thermal_model(self):
        building = BuildingThermalModel(indoor_temp_c=20.0, wall_temp_c=19.0)
        # Cold outdoor (-5°C) without heating should cause indoor temp to drop
        step_unheated = building.simulate_hour(
            heating_cooling_thermal_kw=0.0,
            outdoor_temp_c=-5.0,
            solar_irradiance_w_m2=0.0,
        )
        assert step_unheated["indoor_temp_c"] < 20.0

        # Heating with 5 kW thermal should raise indoor temp
        step_heated = building.simulate_hour(
            heating_cooling_thermal_kw=5.0,
            outdoor_temp_c=-5.0,
            solar_irradiance_w_m2=300.0,
        )
        assert step_heated["indoor_temp_c"] > step_unheated["indoor_temp_c"]

    def test_sg_ready_controller(self):
        ctrl = SGReadyController(surplus_threshold_kw=2.0, forced_surplus_kw=4.0)
        tank = ThermalStorageTank(current_temp_c=45.0, boost_setpoint_c=65.0)

        # 1. Normal state with low surplus
        res_normal = ctrl.evaluate(pv_surplus_kw=0.5, grid_price=0.20, tank=tank)
        assert res_normal["sg_ready_state"] == SGReadyState.STATE_2_NORMAL.value
        assert res_normal["relay_terminal_1"] == 0
        assert res_normal["relay_terminal_2"] == 0

        # 2. State 3 Surplus with 2.5 kW surplus
        res_surplus = ctrl.evaluate(pv_surplus_kw=2.5, grid_price=0.20, tank=tank)
        assert res_surplus["sg_ready_state"] == SGReadyState.STATE_3_SURPLUS.value
        assert res_surplus["relay_terminal_1"] == 0
        assert res_surplus["relay_terminal_2"] == 1

        # 3. State 4 Forced with 5.0 kW surplus
        res_forced = ctrl.evaluate(pv_surplus_kw=5.0, grid_price=0.20, tank=tank)
        assert res_forced["sg_ready_state"] == SGReadyState.STATE_4_FORCED.value
        assert res_forced["relay_terminal_1"] == 1
        assert res_forced["relay_terminal_2"] == 1

        # 4. State 1 Grid Peak Lock
        res_lock = ctrl.evaluate(pv_surplus_kw=5.0, grid_price=0.20, tank=tank, is_grid_peak_lock=True)
        assert res_lock["sg_ready_state"] == SGReadyState.STATE_1_LOCK.value
        assert res_lock["relay_terminal_1"] == 1
        assert res_lock["relay_terminal_2"] == 0

    def test_deferrable_load_scheduler(self):
        scheduler = DeferrableLoadScheduler([
            DeferrableLoad(
                load_id="pool_pump",
                name="Pool Filtration",
                category=LoadCategory.POOL_PUMP,
                nominal_power_kw=1.5,
                required_run_hours=4.0,
                earliest_start_hour=8,
                latest_finish_hour=16,
                priority=2,
            ),
            DeferrableLoad(
                load_id="dhw_heater",
                name="Water Heater",
                category=LoadCategory.WATER_HEATER_RESISTIVE,
                nominal_power_kw=2.0,
                required_run_hours=2.0,
                earliest_start_hour=10,
                latest_finish_hour=18,
                priority=1,
            ),
        ])

        surplus = [0.0] * 8 + [3.0] * 8 + [0.0] * 8  # 3kW surplus between 8am and 4pm
        tariffs = [0.10] * 24

        res = scheduler.optimize_schedule(surplus, tariffs)
        assert res["loads_count"] == 2
        assert len(res["schedules"]["pool_pump"]) == 4
        assert len(res["schedules"]["dhw_heater"]) == 2
        # All chosen hours must be in the day window where surplus is high
        for slot in res["schedules"]["pool_pump"]:
            assert 8 <= slot["hour"] < 16
            assert slot["reason"] == "solar_surplus"


# ---------------------------------------------------------------------------
# Phase Balancer & Unbalance Tests
# ---------------------------------------------------------------------------

class TestPhaseBalancer:
    def test_symmetrical_components_balanced(self):
        # Perfectly balanced 3-phase voltages
        va = complex(230.0, 0.0)
        vb = complex(-115.0, -199.1858)
        vc = complex(-115.0, 199.1858)
        v0, v1, v2 = calculate_symmetrical_components(va, vb, vc)
        # Balanced: V0 ~ 0, V2 ~ 0, V1 ~ 230
        assert abs(v0) < 1.0
        assert abs(v2) < 1.0
        assert pytest.approx(abs(v1), 1.0) == 230.0

    def test_phase_unbalance_evaluator(self):
        # Unbalanced phase voltages: L1=240, L2=220, L3=210
        meas = PhaseMeasurement(
            v_l1=240.0, v_l2=220.0, v_l3=210.0,
            i_l1=15.0, i_l2=5.0, i_l3=0.0,
            p_l1=3.6, p_l2=1.1, p_l3=0.0,
        )
        res = PhaseUnbalanceEvaluator.evaluate(meas)
        assert res["vuf_pct"] > 0.0
        assert res["cuf_pct"] > 0.0
        assert res["i_neutral_amps"] > 0.0

    def test_asymmetric_phase_balancer_dispatch(self):
        limits = InverterPhaseLimits(
            max_total_kw=10.0,
            max_phase_kw=3.68,
            battery_max_discharge_kw=5.0,
            allows_independent_phases=True,
        )
        balancer = AsymmetricPhaseBalancer(limits)

        # Unbalanced load: L1 = 3.0 kW, L2 = 1.0 kW, L3 = 0.0 kW
        meas = PhaseMeasurement(p_l1=3.0, p_l2=1.0, p_l3=0.0, q_l1=0.5, q_l2=0.0, q_l3=0.0)
        dispatch = balancer.calculate_dispatch(meas)

        # Inverter should provide 3.0 kW on L1 and 1.0 kW on L2
        assert pytest.approx(dispatch["p_l1_kw"], 0.1) == 3.0
        assert pytest.approx(dispatch["p_l2_kw"], 0.1) == 1.0
        assert pytest.approx(dispatch["p_l3_kw"], 0.1) == 0.0
        assert pytest.approx(dispatch["total_p_kw"], 0.1) == 4.0
        # Reactive power compensation
        assert dispatch["q_l1_kvar"] < 0  # opposite sign to cancel inductive load

    def test_asymmetric_phase_balancer_battery_limit_scaling(self):
        # If requested total discharge exceeds battery limit (5 kW), scale down
        limits = InverterPhaseLimits(
            max_total_kw=10.0,
            max_phase_kw=3.68,
            battery_max_discharge_kw=4.0,  # 4 kW battery limit
            allows_independent_phases=True,
        )
        balancer = AsymmetricPhaseBalancer(limits)
        meas = PhaseMeasurement(p_l1=3.0, p_l2=3.0, p_l3=2.0)  # total 8 kW
        dispatch = balancer.calculate_dispatch(meas)
        assert dispatch["total_p_kw"] <= 4.01

    def test_zero_export_controller(self):
        ctrl = ZeroExportController(target_grid_import_kw=0.1, inverter_rated_kw=10.0)
        # Exporting 2 kW (measured = -2.0 kW) -> need to curtail
        res = ctrl.update(measured_grid_power_kw=-2.0, dt_seconds=1.0)
        assert res["inverter_power_limit_kw"] < 10.0
        assert res["curtailment_active"] is True

    def test_rolling_peak_demand_shaver(self):
        shaver = RollingPeakDemandShaver(
            peak_threshold_kw=10.0,
            window_duration_minutes=15,
            battery_max_discharge_kw=8.0,
        )
        # Moderate load (6 kW) -> no shaving
        res1 = shaver.step(grid_load_kw=6.0, dt_seconds=60.0)
        assert res1["is_shaving_active"] is False
        assert res1["battery_discharge_kw"] == 0.0

        # Massive load spike (16 kW) -> activates peak shaving
        res2 = shaver.step(grid_load_kw=16.0, dt_seconds=60.0)
        assert res2["is_shaving_active"] is True
        assert res2["battery_discharge_kw"] > 0.0
