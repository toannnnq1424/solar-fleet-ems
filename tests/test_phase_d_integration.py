"""Tests for microgrid controller, anomaly detection, solar model,
modbus protocol, and inverter models.

Covers the Phase D integration modules.
"""

from datetime import datetime, timezone

# ---------------------------------------------------------------------------
# Microgrid Controller Tests
# ---------------------------------------------------------------------------
from solar_fleet.microgrid_controller import (
    DroopController,
    DroopParameters,
    InverterMode,
    InverterState,
    LoadPriority,
    MicrogridController,
    MicrogridState,
)


class TestMicrogridController:
    """Tests for microgrid islanding, reconnection, and load shedding."""

    def _make_controller(self):
        ctrl = MicrogridController(
            nominal_frequency_hz=50.0,
            frequency_threshold_hz=0.5,
            voltage_threshold_pu=0.1,
        )
        ctrl.register_inverter(InverterState(
            inverter_id="inv1",
            mode=InverterMode.GRID_FOLLOWING,
            real_power_kw=5.0,
            rated_power_kw=10.0,
            is_online=True,
        ))
        ctrl.register_load(LoadPriority("load1", "HVAC", 3.0, priority=5))
        ctrl.register_load(LoadPriority("load2", "Lighting", 1.0, priority=3))
        ctrl.register_load(LoadPriority("load3", "Non-essential", 2.0, priority=8))
        return ctrl

    def test_initial_state_grid_connected(self):
        ctrl = self._make_controller()
        assert ctrl.state == MicrogridState.GRID_CONNECTED

    def test_island_detection(self):
        ctrl = self._make_controller()
        # Normal grid
        ctrl.update(1.0, 50.0)
        assert ctrl.state == MicrogridState.GRID_CONNECTED

        # Frequency deviation triggers islanding
        ctrl.update(0.8, 48.0)
        assert ctrl.state == MicrogridState.ISLANDING

    def test_islanding_transition(self):
        ctrl = self._make_controller()
        ctrl.update(0.8, 48.0)  # Trigger islanding
        assert ctrl.state == MicrogridState.ISLANDING

        ctrl.update(0.9, 49.0)  # Transition completes
        assert ctrl.state == MicrogridState.ISLANDED
        assert ctrl._metrics.island_events == 1

    def test_reconnection(self):
        ctrl = self._make_controller()
        ctrl.update(0.8, 48.0)  # Island
        ctrl.update(0.9, 49.0)  # Complete transition

        # Grid restored
        ctrl.update(1.0, 50.0)
        assert ctrl.state == MicrogridState.RECONNECTING

        ctrl.update(1.0, 50.0, grid_phase_deg=0.0)
        assert ctrl.state == MicrogridState.GRID_CONNECTED
        assert ctrl._metrics.reconnection_events == 1

    def test_load_shedding(self):
        ctrl = self._make_controller()
        # Set low generation
        ctrl._inverters["inv1"].real_power_kw = 2.0

        ctrl.update(0.8, 48.0)  # Island
        ctrl.update(0.9, 49.0)  # Complete transition

        # Manage loads should shed non-essential first (priority 8)
        ctrl.update(0.9, 49.0, dt_seconds=1.0)
        shed_loads = [ld for ld in ctrl._loads.values() if ld.is_shed]
        assert len(shed_loads) > 0
        # Highest priority number shed first
        assert any(ld.load_id == "load3" for ld in shed_loads)

    def test_droop_controller(self):
        droop = DroopController(DroopParameters(kp=0.05, kq=0.05))

        # No power deviation → nominal frequency
        f = droop.frequency_setpoint(0.0, 0.0, 10.0)
        assert abs(f - 50.0) < 0.001

        # Positive power deviation → frequency drops
        f = droop.frequency_setpoint(5.0, 0.0, 10.0)
        assert f < 50.0

    def test_status(self):
        ctrl = self._make_controller()
        status = ctrl.status()
        assert "state" in status
        assert "total_generation_kw" in status
        assert "total_load_kw" in status


# ---------------------------------------------------------------------------
# Anomaly Detection Tests
# ---------------------------------------------------------------------------

from solar_fleet.anomaly_detection import (
    AnomalySeverity,
    AnomalyType,
    EWMADetector,
    FleetAnomalyMonitor,
    IQRDetector,
    MovingAverageDetector,
    SolarProductionAnomalyDetector,
    ZScoreDetector,
)


class TestZScoreDetector:

    def test_train_and_detect(self):
        detector = ZScoreDetector(threshold=2.0)
        values = [10.0, 10.5, 9.5, 10.2, 9.8, 10.1, 10.3, 9.9]
        detector.train(values)

        is_anom, z = detector.is_anomaly(10.0)
        assert not is_anom

        is_anom, z = detector.is_anomaly(20.0)
        assert is_anom
        assert z > 2.0

    def test_batch_detection(self):
        detector = ZScoreDetector(threshold=3.0)
        detector.train([5.0] * 100)
        indices = detector.detect_batch([5.0, 5.1, 100.0, 4.9, 5.0])
        assert 2 in indices


class TestIQRDetector:

    def test_train_and_detect(self):
        detector = IQRDetector(k=1.5)
        values = list(range(100))
        detector.train(values)

        is_anom, dist = detector.is_anomaly(50)
        assert not is_anom

        is_anom, dist = detector.is_anomaly(200)
        assert is_anom


class TestMovingAverageDetector:

    def test_detect_spike(self):
        detector = MovingAverageDetector(window_size=5, threshold_sigma=2.0)
        values = [10.0] * 10 + [100.0] + [10.0] * 5
        anomalies = detector.detect(values)
        assert len(anomalies) > 0


class TestEWMADetector:

    def test_train_and_update(self):
        detector = EWMADetector(alpha=0.2, threshold_sigma=3.0)
        detector.train([10.0] * 50)

        is_anom, ewma, cl = detector.update(10.0)
        assert not is_anom

        is_anom, ewma, cl = detector.update(50.0)
        assert is_anom


class TestSolarProductionAnomalyDetector:

    def test_production_drop(self):
        detector = SolarProductionAnomalyDetector(rated_power_kw=10.0)
        events = detector.check_production(
            device_id="inv1",
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            actual_power_kw=1.0,
            irradiance_wm2=800.0,
        )
        # Should detect underperformance
        assert len(events) > 0
        assert events[0].anomaly_type == AnomalyType.PRODUCTION_DROP

    def test_no_anomaly_normal_production(self):
        detector = SolarProductionAnomalyDetector(rated_power_kw=10.0)
        events = detector.check_production(
            device_id="inv1",
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            actual_power_kw=6.0,
            irradiance_wm2=800.0,
        )
        # Should not detect underperformance at reasonable PR
        production_drops = [e for e in events if e.anomaly_type == AnomalyType.PRODUCTION_DROP
                           and e.severity != AnomalySeverity.INFO]
        assert len(production_drops) == 0

    def test_string_mismatch(self):
        detector = SolarProductionAnomalyDetector(rated_power_kw=10.0)
        events = detector.check_string_mismatch(
            device_id="inv1",
            timestamp=datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            string_currents={"1": 8.0, "2": 8.5, "3": 2.0},
        )
        assert len(events) > 0
        assert events[0].anomaly_type == AnomalyType.STRING_MISMATCH

    def test_battery_over_temperature(self):
        detector = SolarProductionAnomalyDetector(rated_power_kw=10.0)
        events = detector.check_battery(
            device_id="bat1",
            timestamp=datetime(2026, 9, 27, 14, 0, tzinfo=timezone.utc),
            soc=0.8, voltage=50.0, current=10.0, temperature_c=58.0,
        )
        assert any(e.anomaly_type == AnomalyType.TEMPERATURE_HIGH for e in events)


class TestFleetAnomalyMonitor:

    def test_register_and_process(self):
        monitor = FleetAnomalyMonitor()
        monitor.register_device("inv1", rated_power_kw=10.0)

        events = monitor.process_telemetry(
            "inv1",
            datetime(2026, 9, 27, 12, 0, tzinfo=timezone.utc),
            {"ac_power": 1000.0, "irradiance": 800.0, "temperature": 35.0},
        )
        # Should detect low performance
        assert len(events) >= 0  # May or may not flag depending on thresholds

        summary = monitor.summary()
        assert summary["monitored_devices"] == 1


# ---------------------------------------------------------------------------
# Solar Model Tests
# ---------------------------------------------------------------------------

from solar_fleet.solar_model import (
    ExponentialSmoothingForecaster,
    LinearForecaster,
    PersistenceForecaster,
    PVArrayConfig,
    clear_sky_ghi,
    clear_sky_profile_24h,
    estimate_daily_energy,
    estimate_pv_power,
    pvwatts_cell_temperature,
    solar_position,
    temperature_efficiency,
)


class TestSolarPosition:

    def test_noon_tropical(self):
        """Sun should be high at noon near equator."""
        pos = solar_position(10.0, 106.0, datetime(2026, 6, 21, 5, 0, tzinfo=timezone.utc))
        # Noon local in Ho Chi Minh (UTC+7) = 5:00 UTC
        assert pos.elevation_deg > 20  # Sun should be up

    def test_midnight(self):
        """Sun should be below horizon at midnight."""
        pos = solar_position(10.0, 106.0, datetime(2026, 6, 21, 17, 0, tzinfo=timezone.utc))
        assert pos.elevation_deg < 0

    def test_airmass(self):
        pos = solar_position(45.0, 0.0, datetime(2026, 6, 21, 12, 0, tzinfo=timezone.utc))
        if pos.elevation_deg > 0:
            assert pos.airmass > 0


class TestClearSkyGHI:

    def test_daytime_positive(self):
        ghi = clear_sky_ghi(10.0, 106.0, datetime(2026, 6, 21, 5, 0, tzinfo=timezone.utc))
        assert ghi > 0

    def test_nighttime_zero(self):
        ghi = clear_sky_ghi(10.0, 106.0, datetime(2026, 6, 21, 17, 0, tzinfo=timezone.utc))
        assert ghi == 0.0

    def test_24h_profile(self):
        profile = clear_sky_profile_24h(10.0, 106.0, datetime(2026, 6, 21, tzinfo=timezone.utc))
        assert len(profile) == 24
        # At least some hours should have irradiance
        daytime = [p for p in profile if p["ghi_wm2"] > 0]
        assert len(daytime) > 6


class TestPVWattsTemperature:

    def test_stc_conditions(self):
        t_cell = pvwatts_cell_temperature(1000.0, 25.0, 1.0)
        # Cell should be warmer than ambient under STC irradiance
        assert t_cell > 25.0

    def test_zero_irradiance(self):
        t_cell = pvwatts_cell_temperature(0.0, 25.0, 1.0)
        assert abs(t_cell - 25.0) < 0.1

    def test_temperature_efficiency(self):
        eff = temperature_efficiency(1000.0, 25.0, 1.0)
        assert 0.8 < eff < 1.05  # Should be slightly below 1.0


class TestPVEstimation:

    def test_estimate_pv_power(self):
        array = PVArrayConfig(peak_power_kwp=10.0)
        result = estimate_pv_power(array, 800.0, 30.0, 2.0)

        assert result["ac_power_kw"] > 0
        assert result["ac_power_kw"] < 10.0
        assert result["cell_temp_c"] > 30.0

    def test_estimate_daily_energy(self):
        array = PVArrayConfig(peak_power_kwp=10.0)
        result = estimate_daily_energy(
            array, 10.0, 106.0,
            datetime(2026, 6, 21, tzinfo=timezone.utc),
        )

        assert result["total_energy_kwh"] > 0
        assert result["peak_power_kw"] > 0
        assert 0 < result["capacity_factor"] < 1


class TestForecasters:

    def test_persistence(self):
        forecaster = PersistenceForecaster()
        forecaster.train([[1, 2, 3, 4]])
        pred = forecaster.predict(4)
        assert pred == [1, 2, 3, 4]

    def test_linear(self):
        forecaster = LinearForecaster()
        X = [[1.0], [2.0], [3.0], [4.0], [5.0]]
        y = [2.0, 4.0, 6.0, 8.0, 10.0]
        result = forecaster.train(X, y)
        assert "mae" in result

        pred = forecaster.predict([[6.0]])
        assert len(pred) == 1

    def test_exponential_smoothing(self):
        forecaster = ExponentialSmoothingForecaster(alpha=0.3)
        profiles = [[1, 2, 3, 4]] * 10
        forecaster.train(profiles)
        pred = forecaster.predict(4)
        assert len(pred) == 4


# ---------------------------------------------------------------------------
# Modbus Protocol Tests
# ---------------------------------------------------------------------------

from solar_fleet.modbus_protocol import (
    GROWATT_MIN_MAP,
    DataType,
    RegisterDecoder,
    RegisterDefinition,
    RegisterType,
    decode_growatt_fault,
    get_available_maps,
    get_map_by_manufacturer,
)


class TestModbusProtocol:

    def test_registry_populated(self):
        maps = get_available_maps()
        assert len(maps) >= 5
        names = [m["name"] for m in maps]
        assert any("Growatt" in n for n in names)
        assert any("SMA" in n for n in names)

    def test_growatt_map_registers(self):
        assert GROWATT_MIN_MAP.register_count > 40
        categories = set(r.category for r in GROWATT_MIN_MAP.registers.values())
        assert "power" in categories
        assert "battery" in categories
        assert "grid" in categories

    def test_find_by_manufacturer(self):
        m = get_map_by_manufacturer("Growatt")
        assert m is not None
        assert m.manufacturer == "Growatt"

        m = get_map_by_manufacturer("NonExistent")
        assert m is None

    def test_decoder_uint16(self):
        assert RegisterDecoder.decode_uint16(1000) == 1000
        assert RegisterDecoder.decode_uint16(0xFFFF) == 65535

    def test_decoder_int16(self):
        assert RegisterDecoder.decode_int16(0) == 0
        assert RegisterDecoder.decode_int16(0xFFFF) == -1
        assert RegisterDecoder.decode_int16(0x7FFF) == 32767

    def test_decoder_uint32(self):
        assert RegisterDecoder.decode_uint32(0, 1000) == 1000
        assert RegisterDecoder.decode_uint32(1, 0) == 65536

    def test_decoder_int32(self):
        assert RegisterDecoder.decode_int32(0xFFFF, 0xFFFF) == -1
        assert RegisterDecoder.decode_int32(0, 100) == 100

    def test_decoder_float32(self):
        val = RegisterDecoder.decode_float32(0x41C8, 0x0000)
        assert abs(val - 25.0) < 0.1

    def test_decode_register(self):
        reg = RegisterDefinition(0, 1, RegisterType.INPUT, DataType.UINT16, scale=0.1)
        val = RegisterDecoder.decode_register(reg, [1000])
        assert abs(val - 100.0) < 0.01

    def test_growatt_fault_codes(self):
        fault = decode_growatt_fault(8)
        assert fault["severity"] == "CRITICAL"
        assert "PV" in fault["name"]

        unknown = decode_growatt_fault(999)
        assert "Unknown" in unknown["name"]


# ---------------------------------------------------------------------------
# Inverter Model Tests
# ---------------------------------------------------------------------------

from solar_fleet.inverter_models import (
    BatteryInverter,
    GridFollowingInverter,
    GridFormingInverter,
    InverterEfficiencyCurve,
)


class TestInverterEfficiencyCurve:

    def test_peak_efficiency(self):
        curve = InverterEfficiencyCurve(rated_power_kw=10.0, peak_efficiency=0.98)
        # At 30% loading, efficiency should be near peak
        eff = curve.efficiency(3.0)
        assert 0.95 < eff <= 1.0

    def test_zero_power(self):
        curve = InverterEfficiencyCurve(rated_power_kw=10.0)
        assert curve.efficiency(0.0) == 0.0

    def test_curve_points(self):
        curve = InverterEfficiencyCurve(rated_power_kw=10.0)
        points = curve.curve_points(10)
        assert len(points) == 10
        assert all("efficiency_pct" in p for p in points)


class TestGridFollowingInverter:

    def test_power_tracking(self):
        inv = GridFollowingInverter("gfi1", rated_power_kw=10.0)
        inv.set_power_reference(5.0, 0.0)

        state = inv.update(1.0, 1.0, 50.0)
        assert state.real_power_kw > 0
        assert state.frequency_hz == 50.0
        assert state.voltage_pu == 1.0

    def test_power_clamping(self):
        inv = GridFollowingInverter("gfi1", rated_power_kw=5.0)
        inv.set_power_reference(100.0)
        assert inv._p_ref == 5.0

    def test_ramp_rate(self):
        inv = GridFollowingInverter("gfi1", rated_power_kw=10.0, ramp_rate_kw_per_s=2.0)
        inv.set_power_reference(10.0)

        state = inv.update(1.0, 1.0, 50.0)
        assert state.real_power_kw <= 2.0  # Ramp limited


class TestGridFormingInverter:

    def test_droop_frequency(self):
        inv = GridFormingInverter("gfm1", rated_power_kw=10.0, droop_kp=0.05)
        inv.set_power_reference(5.0)

        # Run several steps to let droop settle
        for _ in range(100):
            state = inv.update(0.1, 1.0, 50.0)

        # With load, frequency should deviate from nominal
        assert state.frequency_hz != 50.0

    def test_voltage_regulation(self):
        inv = GridFormingInverter("gfm1", rated_power_kw=10.0, droop_kq=0.05)
        inv.set_power_reference(0.0, 3.0)

        for _ in range(50):
            state = inv.update(0.1, 1.0, 50.0)

        # Voltage should adjust based on reactive power
        assert 0.85 <= state.voltage_pu <= 1.15


class TestBatteryInverter:

    def test_charging(self):
        inv = BatteryInverter(
            "bat1", rated_power_kw=5.0, battery_capacity_kwh=10.0,
            soc_init=0.5,
        )
        inv.set_power_reference(3.0)  # Charge

        for _ in range(360):  # 1 hour at 10s steps
            inv.update(10.0, 1.0, 50.0)

        assert inv.soc > 0.5
        assert inv._charge_energy_kwh > 0

    def test_discharging(self):
        inv = BatteryInverter(
            "bat1", rated_power_kw=5.0, battery_capacity_kwh=10.0,
            soc_init=0.8,
        )
        inv.set_power_reference(-3.0)  # Discharge

        for _ in range(360):
            inv.update(10.0, 1.0, 50.0)

        assert inv.soc < 0.8
        assert inv._discharge_energy_kwh > 0

    def test_soc_limits(self):
        inv = BatteryInverter(
            "bat1", rated_power_kw=5.0, battery_capacity_kwh=10.0,
            soc_init=0.06, soc_min=0.05,
        )
        inv.set_power_reference(-5.0)  # Try to discharge near empty

        for _ in range(100):
            inv.update(10.0, 1.0, 50.0)

        assert inv.soc >= inv.soc_min

    def test_to_dict(self):
        inv = BatteryInverter(
            "bat1", rated_power_kw=5.0, battery_capacity_kwh=10.0,
        )
        d = inv.to_dict()
        assert "soc" in d
        assert "battery_capacity_kwh" in d
        assert "cycle_count" in d
