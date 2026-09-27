"""Tests for power quality monitor and component scheduler."""


# ---------------------------------------------------------------------------
# Power Quality Tests
# ---------------------------------------------------------------------------

from solar_fleet.power_quality import (
    PowerQualityMonitor,
    PQEventType,
    PQMeasurement,
    PQSeverity,
)


class TestPowerQualityMonitor:

    def test_normal_conditions(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=230.0, voltage_l2_v=231.0, voltage_l3_v=229.0,
            frequency_hz=50.0, thd_voltage_pct=2.0,
        )
        events = monitor.analyze(m)
        assert len(events) == 0

    def test_voltage_sag(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=200.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=50.0,
        )
        events = monitor.analyze(m)
        sags = [e for e in events if e.event_type == PQEventType.SAG]
        assert len(sags) == 1
        assert sags[0].phase == "L1"
        assert sags[0].severity == PQSeverity.WARNING

    def test_voltage_swell(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=260.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=50.0,
        )
        events = monitor.analyze(m)
        swells = [e for e in events if e.event_type == PQEventType.SWELL]
        assert len(swells) == 1

    def test_voltage_interruption(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=10.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=50.0,
        )
        events = monitor.analyze(m)
        ints = [
            e for e in events
            if e.event_type == PQEventType.INTERRUPTION
        ]
        assert len(ints) == 1
        assert ints[0].severity == PQSeverity.CRITICAL

    def test_frequency_deviation(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=230.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=48.5,
        )
        events = monitor.analyze(m)
        freq = [
            e for e in events
            if e.event_type == PQEventType.FREQUENCY_DEV
        ]
        assert len(freq) == 1

    def test_harmonic_violation(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=230.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=50.0, thd_voltage_pct=8.0,
        )
        events = monitor.analyze(m)
        harms = [
            e for e in events if e.event_type == PQEventType.HARMONIC
        ]
        assert len(harms) == 1

    def test_voltage_unbalance(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=230.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=50.0, voltage_unbalance_pct=3.5,
        )
        events = monitor.analyze(m)
        unbal = [
            e for e in events if e.event_type == PQEventType.UNBALANCE
        ]
        assert len(unbal) == 1

    def test_flicker(self):
        monitor = PowerQualityMonitor()
        m = PQMeasurement(
            voltage_l1_v=230.0, voltage_l2_v=230.0, voltage_l3_v=230.0,
            frequency_hz=50.0, flicker_pst=1.5,
        )
        events = monitor.analyze(m)
        flick = [
            e for e in events if e.event_type == PQEventType.FLICKER
        ]
        assert len(flick) == 1

    def test_summary(self):
        monitor = PowerQualityMonitor()
        for _ in range(10):
            monitor.analyze(PQMeasurement(
                voltage_l1_v=230.0, voltage_l2_v=230.0,
                voltage_l3_v=230.0, frequency_hz=50.0,
            ))
        summary = monitor.summary()
        assert summary["measurements"] == 10
        assert summary["compliance"]["voltage_ok"] is True
        assert summary["compliance"]["frequency_ok"] is True

    def test_calculate_unbalance(self):
        unbal = PowerQualityMonitor.calculate_voltage_unbalance(
            240.0, 230.0, 220.0,
        )
        assert unbal > 0

    def test_calculate_thd(self):
        thd = PowerQualityMonitor.calculate_thd(
            100.0, [5.0, 3.0, 2.0],
        )
        assert 0 < thd < 10


# ---------------------------------------------------------------------------
# Component Scheduler Tests
# ---------------------------------------------------------------------------

from solar_fleet.component_scheduler import (
    BatteryComponent,
    Channel,
    ChannelAccess,
    ComponentScheduler,
    ComponentState,
    InverterComponent,
    MeterComponent,
    SelfConsumptionController,
)


class TestChannel:

    def test_set_value(self):
        ch = Channel("test", "c1", access=ChannelAccess.READ_WRITE)
        ch.set_value(42.0)
        assert ch.value == 42.0
        assert len(ch._history) == 1

    def test_history_limit(self):
        ch = Channel("test", "c1", access=ChannelAccess.READ_WRITE)
        for i in range(1100):
            ch.set_value(i)
        assert len(ch._history) <= 1000


class TestComponents:

    def test_meter(self):
        m = MeterComponent("meter0")
        m.activate()
        assert m.state == ComponentState.ACTIVE
        m.execute()
        m.deactivate()
        assert m.state == ComponentState.INACTIVE

    def test_battery(self):
        b = BatteryComponent("bat0", capacity_kwh=10.0)
        b.activate()
        assert b.get_channel("soc").value == 50.0

        b.get_channel("setpoint_power").set_value(3000)
        b.execute()
        assert b.get_channel("active_power").value == 3000

    def test_battery_clamping(self):
        b = BatteryComponent(
            "bat0", max_charge_w=5000, max_discharge_w=5000,
        )
        b.activate()
        b.get_channel("setpoint_power").set_value(10000)
        b.execute()
        assert b.get_channel("active_power").value == 5000

    def test_inverter(self):
        inv = InverterComponent("inv0", rated_power_w=10000)
        inv.activate()
        inv.get_channel("dc_power").set_value(8000)
        inv.get_channel("power_limit_pct").set_value(50)
        inv.execute()
        assert inv.get_channel("active_power").value == 4000


class TestComponentScheduler:

    def _make_scheduler(self):
        sched = ComponentScheduler(cycle_time_ms=100)
        sched.register(MeterComponent("meter0"))
        sched.register(BatteryComponent("bat0"))
        sched.register(InverterComponent("inv0"))
        return sched

    def test_start_stop(self):
        sched = self._make_scheduler()
        sched.start()
        assert sched._is_running
        for c in sched._components.values():
            assert c.state == ComponentState.ACTIVE
        sched.stop()
        assert not sched._is_running

    def test_execute_cycle(self):
        sched = self._make_scheduler()
        sched.start()
        result = sched.execute_cycle()
        assert result["cycle"] == 1
        assert result["components_active"] == 3

    def test_execution_order(self):
        sched = self._make_scheduler()
        ordered = sched._ordered_components()
        types = [c.component_type for c in ordered]
        assert types.index("meter") < types.index("inverter")
        assert types.index("inverter") < types.index("battery")

    def test_controller_integration(self):
        sched = ComponentScheduler()
        meter = MeterComponent("meter0")
        battery = BatteryComponent("bat0")
        ctrl = SelfConsumptionController(
            "ctrl0", "meter0", "bat0",
        )
        sched.register(meter)
        sched.register(battery)
        sched.register(ctrl)

        sched.start()

        # Simulate grid importing 3000W
        meter.get_channel("active_power").set_value(3000)

        sched.execute_cycle()

        # Controller should set battery to discharge
        bat_sp = battery.get_channel("setpoint_power").value
        assert bat_sp is not None
        assert bat_sp < 0  # Discharge

    def test_status(self):
        sched = self._make_scheduler()
        sched.start()
        sched.execute_cycle()
        status = sched.status()
        assert status["is_running"] is True
        assert status["cycle_count"] == 1
        assert "meter0" in status["components"]
