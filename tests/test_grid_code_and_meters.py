"""Tests for grid-code compliance regulator and industrial smart meter drivers.

Tests:
- Volt-Watt P(V) active power curtailment curve
- Volt-Var Q(V) reactive power voltage support curve
- Frequency-Watt P(f) droop response
- Anti-islanding protection relay trip limits
- GridCodeRegulator coordinated evaluation
- Binary IEEE 754 float32 and int32 decoders
- Smart meter drivers: Eastron SDM630, Chint DTSU666, Carlo Gavazzi EM24,
  Janitza UMG96, Schneider iEM3000, ABB B23
- API endpoints: /api/grid-code/evaluate, /api/meters/supported-models, /api/meters/decode-registers
"""

import struct

import pytest

from solar_fleet.grid_code_regulator import (
    FreqWattDroop,
    GridCodeRegulator,
    GridConnectionState,
    VoltVarCurve,
    VoltWattCurve,
)
from solar_fleet.smart_meter_driver import (
    MeterModel,
    SmartMeterDriver,
    decode_float32,
    decode_int32,
)

# ---------------------------------------------------------------------------
# Grid Code Regulator Tests
# ---------------------------------------------------------------------------

class TestGridCodeRegulator:
    def test_volt_watt_curve(self):
        vw = VoltWattCurve(nominal_voltage_v=230.0, p_rated_kw=10.0)

        # Normal voltage (230V) -> 100% power
        p230 = vw.calculate_power_limit(230.0)
        assert p230["power_limit_kw"] == 10.0
        assert p230["is_curtailed"] is False

        # 253V: curtailment threshold
        p253 = vw.calculate_power_limit(253.0)
        assert p253["power_limit_kw"] == 10.0

        # 258V: 50% power (5.0 kW)
        p258 = vw.calculate_power_limit(258.0)
        assert pytest.approx(p258["power_limit_kw"], 0.1) == 5.0
        assert p258["is_curtailed"] is True

        # 265V: minimum power floor (20% = 2.0 kW)
        p265 = vw.calculate_power_limit(265.0)
        assert pytest.approx(p265["power_limit_kw"], 0.1) == 2.0

    def test_volt_var_curve(self):
        vv = VoltVarCurve(nominal_voltage_v=230.0, rated_kva=10.0, q_max_ratio=0.44)

        # Deadband between 220V and 240V -> Q = 0
        q230 = vv.calculate_reactive_power(230.0)
        assert q230["reactive_power_kvar"] == 0.0
        assert q230["mode"] == "deadband"

        # Low voltage (207V) -> capacitive boost (+4.4 kvar)
        q207 = vv.calculate_reactive_power(207.0)
        assert pytest.approx(q207["reactive_power_kvar"], 0.1) == 4.4
        assert q207["mode"] == "capacitive_boost"

        # High voltage (258V) -> inductive buck (-4.4 kvar)
        q258 = vv.calculate_reactive_power(258.0)
        assert pytest.approx(q258["reactive_power_kvar"], 0.1) == -4.4
        assert q258["mode"] == "inductive_buck"

    def test_freq_watt_droop(self):
        fw = FreqWattDroop(nominal_freq_hz=50.0, p_rated_kw=10.0, droop_pct=5.0)

        # 50.0 Hz: no droop
        p50 = fw.calculate_power_adjustment(50.0, current_power_kw=8.0)
        assert p50["target_power_kw"] == 8.0
        assert p50["is_droop_active"] is False

        # Over-frequency 50.3 Hz (> 50.2 Hz threshold) -> curtailment
        p_over = fw.calculate_power_adjustment(50.3, current_power_kw=8.0)
        assert p_over["target_power_kw"] < 8.0
        assert p_over["is_droop_active"] is True

        # Under-frequency 49.7 Hz (< 49.8 Hz threshold) -> power boost
        p_under = fw.calculate_power_adjustment(49.7, current_power_kw=6.0)
        assert p_under["target_power_kw"] > 6.0
        assert p_under["is_droop_active"] is True

    def test_protection_trips(self):
        reg = GridCodeRegulator()

        # Extreme overvoltage (266V >= 264.5V)
        trip_v = reg.evaluate(measured_voltage_v=266.0, measured_freq_hz=50.0, current_active_power_kw=8.0)
        assert trip_v["allow_inverter_run"] is False
        assert trip_v["state"] == GridConnectionState.TRIPPED_OVER_VOLTAGE.value

        # Extreme underfrequency (47.0 Hz <= 47.5 Hz)
        trip_f = reg.evaluate(measured_voltage_v=230.0, measured_freq_hz=47.0, current_active_power_kw=8.0)
        assert trip_f["allow_inverter_run"] is False
        assert trip_f["state"] == GridConnectionState.TRIPPED_UNDER_FREQUENCY.value


# ---------------------------------------------------------------------------
# Smart Meter Driver Tests
# ---------------------------------------------------------------------------

class TestSmartMeterDriver:
    def test_binary_decoders(self):
        # Pack 230.5 as float32
        packed = struct.pack(">f", 230.5)
        high, low = struct.unpack(">HH", packed)
        assert pytest.approx(decode_float32(high, low), 0.01) == 230.5

        # Int32 decoder
        val = decode_int32(0x0001, 0x86A0, signed=True)  # 100,000
        assert val == 100000

        val_neg = decode_int32(0xFFFF, 0xD8F0, signed=True)  # -10,000
        assert val_neg == -10000

    def test_decode_eastron_sdm630(self):
        # Create float32 encoded registers
        def float_words(val: float):
            p = struct.pack(">f", val)
            return struct.unpack(">HH", p)

        v1_h, v1_l = float_words(231.2)
        v2_h, v2_l = float_words(229.8)
        v3_h, v3_l = float_words(230.1)
        p_tot_h, p_tot_l = float_words(5432.0)
        imp_h, imp_l = float_words(1234.5)

        regs = {
            0: v1_h, 1: v1_l,
            2: v2_h, 3: v2_l,
            4: v3_h, 5: v3_l,
            52: p_tot_h, 53: p_tot_l,
            70: float_words(50.0)[0], 71: float_words(50.0)[1],
            72: imp_h, 73: imp_l,
        }

        telemetry = SmartMeterDriver.decode(MeterModel.EASTRON_SDM630, slave_id=1, registers=regs)
        assert pytest.approx(telemetry.v_l1, 0.1) == 231.2
        assert pytest.approx(telemetry.p_total_w, 1.0) == 5432.0
        assert pytest.approx(telemetry.import_active_kwh, 0.1) == 1234.5
        d = telemetry.to_dict()
        assert d["meter_model"] == "eastron_sdm630"
        assert d["p_total_kw"] == 5.432

    def test_decode_chint_dtsu666(self):
        regs = {
            8192: 0, 8193: 3500,     # Total power = 3500W
            8198: 2305,              # V1 = 230.5V
            8204: 1520,              # I1 = 15.20A
            4126: 0, 4127: 50000,    # Import = 500.00 kWh
        }
        telemetry = SmartMeterDriver.decode(MeterModel.CHINT_DTSU666, slave_id=2, registers=regs)
        assert telemetry.v_l1 == 230.5
        assert telemetry.p_total_w == 3500.0
        assert telemetry.import_active_kwh == 500.0

    def test_decode_carlo_gavazzi_em24(self):
        regs = {
            0: 2310,                 # V1 = 231.0V
            7: 10500,                # I1 = 10.5A
            40: 0, 41: 24200,        # P_tot = 2420.0W
            52: 0, 53: 8800,         # Import = 880.0 kWh
        }
        telemetry = SmartMeterDriver.decode(MeterModel.CARLO_GAVAZZI_EM24, slave_id=1, registers=regs)
        assert telemetry.v_l1 == 231.0
        assert telemetry.p_total_w == 2420.0
        assert telemetry.import_active_kwh == 880.0


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

class TestGridCodeAndMeterAPI:
    def _login(self, local):
        client, _ = local
        origin = "http://127.0.0.1:8765"
        password = "SIMULATOR-workspace-password-only"
        res = client.post("/api/login", json={"username": "admin", "password": password}, headers={"Origin": origin})
        assert res.status_code == 200
        return client, {"Origin": origin, "X-CSRF-Token": res.json()["csrf"]}

    def test_grid_code_api(self, local):
        client, headers = self._login(local)
        res = client.post(
            "/api/grid-code/evaluate",
            json={"voltage_v": 258.0, "frequency_hz": 50.0, "current_power_kw": 10.0},
            headers=headers,
        )
        assert res.status_code == 200
        data = res.json()
        assert data["allow_inverter_run"] is True
        assert data["target_p_kw"] <= 5.1  # Curtailed by Volt-Watt

    def test_meter_models_and_decode_api(self, local):
        client, headers = self._login(local)
        # Supported models endpoint
        models_res = client.get("/api/meters/supported-models", headers=headers)
        assert models_res.status_code == 200
        assert len(models_res.json()["models"]) == 6

        # Decode endpoint
        regs = {"8192": 0, "8193": 2500, "8198": 2300}
        decode_res = client.post(
            "/api/meters/decode-registers",
            json={"model": "chint_dtsu666", "slave_id": 1, "registers": regs},
            headers=headers,
        )
        assert decode_res.status_code == 200
        d = decode_res.json()
        assert d["p_total_w"] == 2500.0
        assert d["v_l1"] == 230.0
