"""Tests for predbat battery planner, genset controller, vendor device translator, and Phase D API.

Tests:
- Battery specs: round-trip efficiency and levelized degradation cost
- Predbat predictive forward simulation and dynamic tariff arbitrage
- Generator controller lifecycle: state transitions, fuel calculation, optimal loading
- Black-start multi-stage orchestration sequence
- Vendor device translator: GoodWe, Sungrow, Deye, Huawei, Solis, Growatt
- Extended Phase D API endpoints verification
"""

import pytest

from solar_fleet.genset_controller import (
    BlackStartOrchestrator,
    BlackStartStage,
    GeneratorController,
    GeneratorSpecs,
    GeneratorState,
)
from solar_fleet.predbat_planner import (
    BatterySpecs,
    PredbatPlanner,
)
from solar_fleet.vendor_device_translator import (
    ModbusFunctionCode,
    StandardWorkMode,
    VendorDeviceTranslator,
)

# ---------------------------------------------------------------------------
# Predbat Planner Tests
# ---------------------------------------------------------------------------

class TestPredbatPlanner:
    def test_battery_specs_degradation_cost(self):
        specs = BatterySpecs(
            capacity_kwh=10.0,
            rated_cycle_life=6000,
            replacement_cost_usd=3000.0,
        )
        assert specs.round_trip_efficiency == 0.95 * 0.95
        # Total throughput = 10 * 6000 * 0.8 = 48,000 kWh -> cost = 3000 / 48000 = ~0.0625 $/kWh
        assert 0.05 <= specs.degradation_cost_per_kwh <= 0.08

    def test_plan_horizon_execution(self):
        specs = BatterySpecs(capacity_kwh=10.0, max_charge_kw=5.0, max_discharge_kw=5.0)
        planner = PredbatPlanner(specs)

        # 24 hours of solar with midday peak
        solar = [0.0] * 6 + [1.0, 3.0, 5.0, 6.0, 5.0, 3.0, 1.0] + [0.0] * 11
        load = [1.5] * 24
        import_tariffs = [0.08] * 6 + [0.20] * 10 + [0.35] * 4 + [0.15] * 4
        export_tariffs = [0.03] * 6 + [0.08] * 10 + [0.25] * 4 + [0.05] * 4

        plan = planner.plan_horizon(
            solar_forecast_hourly=solar,
            load_forecast_hourly=load,
            import_tariffs_hourly=import_tariffs,
            export_tariffs_hourly=export_tariffs,
            current_soc_pct=50.0,
        )
        assert plan["status"] == "success"
        assert plan["horizon_hours"] == 24
        assert len(plan["slots"]) == 24
        assert len(plan["inverter_schedule"]) >= 1
        assert "estimated_savings_usd" in plan


# ---------------------------------------------------------------------------
# Generator Controller Tests
# ---------------------------------------------------------------------------

class TestGeneratorController:
    def test_generator_specs_fuel_curve(self):
        specs = GeneratorSpecs(
            rated_power_kw=50.0,
            fuel_idle_liters_per_hour=2.5,
            fuel_slope_liters_per_kwh=0.22,
        )
        assert specs.min_power_kw == 20.0       # 40%
        assert specs.optimal_power_kw == 37.5   # 75%
        assert specs.calculate_fuel_rate(0.0) == 0.0
        # Loaded at 37.5 kW -> 2.5 + (0.22 * 37.5) = 10.75 L/h
        assert pytest.approx(specs.calculate_fuel_rate(37.5), 0.1) == 10.75

    def test_generator_lifecycle_transitions(self):
        specs = GeneratorSpecs(
            rated_power_kw=50.0,
            warmup_time_seconds=60,
            cooldown_time_seconds=60,
            min_run_time_seconds=120,
        )
        ctrl = GeneratorController(specs)
        assert ctrl.state == GeneratorState.OFF

        # 1. Trigger auto-start with grid lost and low battery SOC (15%)
        ctrl.step(dt_seconds=1, microgrid_load_kw=10.0, battery_soc_pct=15.0, battery_max_charge_kw=10.0, is_grid_available=False)
        assert ctrl.state == GeneratorState.CRANKING

        # Advance cranking past 10 seconds
        ctrl.step(dt_seconds=15, microgrid_load_kw=10.0, battery_soc_pct=15.0, battery_max_charge_kw=10.0, is_grid_available=False)
        assert ctrl.state == GeneratorState.WARMUP

        # Advance warmup past 60 seconds
        ctrl.step(dt_seconds=70, microgrid_load_kw=10.0, battery_soc_pct=15.0, battery_max_charge_kw=10.0, is_grid_available=False)
        assert ctrl.state == GeneratorState.RUNNING_LOADED

        # While running loaded: genset should output at least min_power and charge battery
        step_run = ctrl.step(dt_seconds=60, microgrid_load_kw=10.0, battery_soc_pct=15.0, battery_max_charge_kw=20.0, is_grid_available=False)
        assert step_run["output_power_kw"] >= specs.min_power_kw
        assert step_run["battery_charge_kw"] > 0.0

    def test_black_start_orchestrator(self):
        specs = GeneratorSpecs(rated_power_kw=50.0)
        ctrl = GeneratorController(specs)
        orchestrator = BlackStartOrchestrator(ctrl)
        assert orchestrator.stage == BlackStartStage.IDLE

        # Stage 1: Dead bus check (< 10V)
        orchestrator.execute_next_stage(bus_voltage_v=0.0, pv_frequency_hz=0.0, critical_load_kw=0.0)
        assert orchestrator.stage == BlackStartStage.STAGE_1_DEAD_BUS_CHECK

        # Stage 2: Start generator
        orchestrator.execute_next_stage(bus_voltage_v=0.0, pv_frequency_hz=0.0, critical_load_kw=0.0)
        assert orchestrator.stage == BlackStartStage.STAGE_2_GENSET_START

        # Stage 3: Bus energization
        orchestrator.execute_next_stage(bus_voltage_v=400.0, pv_frequency_hz=50.0, critical_load_kw=0.0)
        assert orchestrator.stage == BlackStartStage.STAGE_3_BUS_ENERGIZATION

        # Stage 4: PV synchronization (freq = 50.0 Hz)
        orchestrator.execute_next_stage(bus_voltage_v=400.0, pv_frequency_hz=50.0, critical_load_kw=0.0)
        assert orchestrator.stage == BlackStartStage.STAGE_4_PV_SYNCHRONIZATION

        # Stage 5: Load restoration
        orchestrator.execute_next_stage(bus_voltage_v=400.0, pv_frequency_hz=50.0, critical_load_kw=25.0)
        assert orchestrator.stage == BlackStartStage.STAGE_5_LOAD_RESTORATION

        # Completion
        orchestrator.execute_next_stage(bus_voltage_v=400.0, pv_frequency_hz=50.0, critical_load_kw=25.0)
        assert orchestrator.stage == BlackStartStage.COMPLETED


# ---------------------------------------------------------------------------
# Vendor Device Translator Tests
# ---------------------------------------------------------------------------

class TestVendorDeviceTranslator:
    def test_translate_goodwe(self):
        reqs = VendorDeviceTranslator.translate_goodwe(
            slave_id=1,
            work_mode=StandardWorkMode.BACKUP_UPS,
            export_limit_w=5000,
        )
        assert len(reqs) == 2
        # Mode register 45352, Backup = 4
        assert reqs[0].register_address == 45352
        assert reqs[0].values == [4]
        # Export limit register 45354
        assert reqs[1].register_address == 45354
        assert reqs[1].values == [5000]

    def test_translate_sungrow(self):
        reqs = VendorDeviceTranslator.translate_sungrow(
            slave_id=1,
            work_mode=StandardWorkMode.FORCE_CHARGE_GRID,
            max_charge_w=4000,
        )
        assert len(reqs) == 3
        # Mode = 2 (forced), Command = 171 (charge), Power = 4000W
        assert reqs[0].register_address == 13000
        assert reqs[0].values == [2]
        assert reqs[1].register_address == 13001
        assert reqs[1].values == [171]
        assert reqs[2].register_address == 13002
        assert reqs[2].values == [4000]

    def test_translate_deye(self):
        reqs = VendorDeviceTranslator.translate_deye(
            slave_id=1,
            work_mode=StandardWorkMode.FORCE_CHARGE_GRID,
            max_charge_amps=60,
            max_discharge_amps=80,
        )
        assert len(reqs) == 3
        assert reqs[0].register_address == 143
        assert reqs[0].values == [60]
        assert reqs[1].register_address == 144
        assert reqs[1].values == [80]
        # TOU grid charge enable bitmask
        assert reqs[2].register_address == 142

    def test_translate_huawei(self):
        reqs = VendorDeviceTranslator.translate_huawei(
            slave_id=1,
            work_mode=StandardWorkMode.SELF_CONSUMPTION,
            max_charge_w=5000,
            active_power_derating_pct=80.0,
        )
        assert len(reqs) == 3
        # Storage mode register 47081
        assert reqs[0].register_address == 47081
        # uint32 power write FC16
        assert reqs[1].function_code == ModbusFunctionCode.WRITE_MULTIPLE
        assert reqs[1].register_address == 47087
        # Derating: 80.0% * 10 = 800
        assert reqs[2].register_address == 47077
        assert reqs[2].values == [800]

    def test_translate_solis_and_growatt(self):
        solis_reqs = VendorDeviceTranslator.translate_solis(
            slave_id=1,
            work_mode=StandardWorkMode.FEED_IN_PRIORITY,
            export_limit_w=3000,
        )
        assert len(solis_reqs) == 2
        assert solis_reqs[0].register_address == 43110

        growatt_reqs = VendorDeviceTranslator.translate_growatt(
            slave_id=1,
            work_mode=StandardWorkMode.FORCE_CHARGE_GRID,
            charge_power_rate_pct=100,
        )
        assert len(growatt_reqs) == 2
        assert growatt_reqs[0].register_address == 1044


# ---------------------------------------------------------------------------
# Phase D Extended API Route Tests
# ---------------------------------------------------------------------------

class TestPhaseDExtendedAPI:
    def _login(self, local):
        client, _ = local
        origin = "http://127.0.0.1:8765"
        password = "SIMULATOR-workspace-password-only"
        res = client.post("/api/login", json={"username": "admin", "password": password}, headers={"Origin": origin})
        assert res.status_code == 200
        return client, {"Origin": origin, "X-CSRF-Token": res.json()["csrf"]}

    def test_load_predictor_api(self, local):
        client, headers = self._login(local)
        res = client.get("/api/load-predictor/models", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert len(data["models"]) == 5

        # Test predict endpoint
        payload = {
            "model": "persistence",
            "history": [{"values": [1.5] * 24}],
        }
        res_pred = client.post("/api/load-predictor/predict", json=payload, headers=headers)
        assert res_pred.status_code == 200
        pred_data = res_pred.json()
        assert len(pred_data["predicted_hourly_kw"]) == 24
        assert pred_data["predicted_hourly_kw"][0] == 1.5

    def test_tariffs_api(self, local):
        client, headers = self._login(local)
        res = client.get("/api/tariffs/catalogue", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert "tariffs" in data
        assert "vn_evn_residential" in data["tariffs"]

        # Calculate bill endpoint
        bill_res = client.post(
            "/api/tariffs/calculate-bill",
            json={
                "tariff_key": "vn_evn_commercial_tou",
                "import_kwh_hourly": [2.0] * 24,
                "export_kwh_hourly": [0.0] * 24,
                "peak_demand_kw": 5.0,
            },
            headers=headers,
        )
        assert bill_res.status_code == 200
        bill = bill_res.json()
        assert bill["total"] > 0
        assert bill["currency"] == "VND"

    def test_thermal_api(self, local):
        client, headers = self._login(local)
        cop_res = client.get("/api/thermal/heat-pump-cop?ambient_temp_c=7.0&supply_temp_c=35.0", headers=headers)
        assert cop_res.status_code == 200
        assert cop_res.json()["cop"] > 0

        sg_res = client.post(
            "/api/thermal/sg-ready-evaluate",
            json={
                "pv_surplus_kw": 3.0,
                "grid_price": 0.15,
                "tank_temp_c": 45.0,
            },
            headers=headers,
        )
        assert sg_res.status_code == 200
        assert sg_res.json()["sg_ready_state"] == 3  # State 3 surplus

    def test_phase_balancer_api(self, local):
        client, headers = self._login(local)
        res = client.post(
            "/api/phase-balancer/dispatch",
            json={
                "p_l1": 2.5,
                "p_l2": 1.0,
                "p_l3": 0.0,
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "unbalance_metrics" in data
        assert "dispatch_setpoints" in data
        assert data["dispatch_setpoints"]["p_l1_kw"] == 2.5

    def test_vendor_translator_api(self, local):
        client, headers = self._login(local)
        res = client.post(
            "/api/vendor-translator/translate-command",
            json={
                "vendor": "sungrow",
                "slave_id": 1,
                "work_mode": "force_charge_grid",
                "power_w": 5000,
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["modbus_requests"]) == 3

    def test_genset_dispatch_api(self, local):
        client, headers = self._login(local)
        res = client.post(
            "/api/genset/evaluate-dispatch",
            json={
                "rated_power_kw": 50.0,
                "microgrid_load_kw": 35.0,
                "battery_soc_pct": 15.0,
                "is_grid_available": False,
                "dt_seconds": 60,
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "genset_specs" in data
        assert "dispatch" in data
        assert data["genset_specs"]["rated_power_kw"] == 50.0

    def test_genset_black_start_api(self, local):
        client, headers = self._login(local)
        res = client.post(
            "/api/genset/black-start-sequence",
            json={
                "advance_steps": 2,
                "bus_voltage_v": 0.0,
                "pv_frequency_hz": 50.0,
                "critical_load_kw": 8.0,
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert "current_stage" in data
        assert "event_log" in data

    def test_thermal_building_simulation_api(self, local):
        client, headers = self._login(local)
        res = client.post(
            "/api/thermal/building-simulation",
            json={
                "initial_indoor_temp_c": 21.0,
                "initial_wall_temp_c": 20.0,
                "outdoor_temps_hourly": [5.0, 7.0, 10.0, 12.0],
                "heating_thermal_kw": 3.0,
            },
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert len(data["hourly_simulation"]) == 4
        assert "final_state" in data

    def test_vendor_translator_supported_brands_api(self, local):
        client, headers = self._login(local)
        res = client.get("/api/vendor-translator/supported-brands", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total_brands"] == 30
        assert len(data["supported_modes"]) > 0
