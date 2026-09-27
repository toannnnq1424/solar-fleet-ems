"""Tests for degradation models, weather forecast, and EV charger modules."""

import math

import pytest

# ---------------------------------------------------------------------------
# Degradation Model Tests
# ---------------------------------------------------------------------------
from solar_fleet.degradation_models import (
    BatteryHealthEstimator,
    CalendarDegradation,
    CombinedDegradation,
    RainflowDegradation,
    ThroughputDegradation,
)


class TestThroughputDegradation:

    def test_zero_cycling(self):
        model = ThroughputDegradation(nominal_capacity_kwh=10.0)
        soc = [0.5] * 100  # No cycling
        loss = model.predict_capacity_loss(soc, dt_hours=1.0)
        assert loss == 0.0

    def test_full_cycles(self):
        model = ThroughputDegradation(
            nominal_capacity_kwh=10.0,
            cycles_to_eol=6000,
            eol_capacity_fraction=0.80,
        )
        # Create trace with full 0→1→0 cycles
        soc = []
        for _ in range(100):
            soc.extend([0.0, 1.0])
        loss = model.predict_capacity_loss(soc, dt_hours=0.5)
        assert loss > 0
        assert loss < 1.0

    def test_deep_vs_shallow(self):
        model = ThroughputDegradation(nominal_capacity_kwh=10.0)
        # Deep cycles
        deep = []
        for _ in range(10):
            deep.extend([0.1, 0.9])
        loss_deep = model.predict_capacity_loss(deep, dt_hours=1.0)

        # Shallow cycles
        shallow = []
        for _ in range(10):
            shallow.extend([0.45, 0.55])
        loss_shallow = model.predict_capacity_loss(shallow, dt_hours=1.0)

        assert loss_deep > loss_shallow

    def test_validation(self):
        model = ThroughputDegradation()
        with pytest.raises(ValueError):
            model.predict_capacity_loss([0.5], dt_hours=1.0)
        with pytest.raises(ValueError):
            model.predict_capacity_loss([0.5, 0.6], dt_hours=-1.0)


class TestCalendarDegradation:

    def test_time_dependent(self):
        model = CalendarDegradation()
        soc_short = [0.5] * 10
        soc_long = [0.5] * 1000

        loss_short = model.predict_capacity_loss(
            soc_short, dt_hours=24.0, temperature_c=25.0,
        )
        loss_long = model.predict_capacity_loss(
            soc_long, dt_hours=24.0, temperature_c=25.0,
        )
        assert loss_long > loss_short

    def test_temperature_acceleration(self):
        model = CalendarDegradation()
        soc = [0.5] * 365

        loss_25 = model.predict_capacity_loss(
            soc, dt_hours=24.0, temperature_c=25.0,
        )
        loss_45 = model.predict_capacity_loss(
            soc, dt_hours=24.0, temperature_c=45.0,
        )
        assert loss_45 > loss_25

    def test_high_soc_stress(self):
        model = CalendarDegradation()
        soc_high = [0.9] * 365
        soc_low = [0.2] * 365

        loss_high = model.predict_capacity_loss(
            soc_high, dt_hours=24.0,
        )
        loss_low = model.predict_capacity_loss(
            soc_low, dt_hours=24.0,
        )
        assert loss_high > loss_low


class TestRainflowDegradation:

    def test_cycle_counting(self):
        model = RainflowDegradation()
        # Create a clear cycling pattern
        soc = [0.2, 0.8, 0.2, 0.8, 0.2, 0.8, 0.2]
        loss = model.predict_capacity_loss(soc, dt_hours=1.0)
        assert loss > 0

    def test_deeper_more_damage(self):
        model = RainflowDegradation()
        deep = [0.1, 0.9, 0.1, 0.9, 0.1]
        shallow = [0.4, 0.6, 0.4, 0.6, 0.4]

        loss_deep = model.predict_capacity_loss(deep, dt_hours=1.0)
        loss_shallow = model.predict_capacity_loss(
            shallow, dt_hours=1.0,
        )
        assert loss_deep > loss_shallow

    def test_cycle_life(self):
        model = RainflowDegradation(a=10000, b=-1.2)
        n_full = model._cycle_life(1.0)
        n_half = model._cycle_life(0.5)
        assert n_half > n_full  # Shallow cycles last longer


class TestCombinedDegradation:

    def test_combines_all_models(self):
        model = CombinedDegradation()
        soc = [0.2, 0.8, 0.2, 0.8, 0.2, 0.8] * 50
        loss = model.predict_capacity_loss(soc, dt_hours=1.0)
        assert loss > 0

    def test_breakdown(self):
        model = CombinedDegradation()
        soc = [0.3, 0.7, 0.3, 0.7] * 100
        bd = model.breakdown(soc, dt_hours=1.0, temperature_c=30.0)
        assert "throughput" in bd
        assert "calendar" in bd
        assert "rainflow" in bd
        assert "combined" in bd
        assert bd["combined"] >= max(bd["throughput"], bd["calendar"])


class TestBatteryHealthEstimator:

    def test_lfp_assessment(self):
        estimator = BatteryHealthEstimator(
            nominal_capacity_kwh=10.0, chemistry="lfp",
        )
        soc = [0.3, 0.7, 0.3, 0.7] * 100
        result = estimator.assess(soc, dt_hours=1.0, temperature_c=25.0)
        assert result.soh_pct > 90
        assert result.remaining_cycles > 0
        assert result.estimated_eol_days > 0

    def test_nmc_assessment(self):
        estimator = BatteryHealthEstimator(
            nominal_capacity_kwh=10.0, chemistry="nmc",
        )
        soc = [0.3, 0.7, 0.3, 0.7] * 100
        result = estimator.assess(soc, dt_hours=1.0, temperature_c=25.0)
        assert result.soh_pct > 90

    def test_to_dict(self):
        estimator = BatteryHealthEstimator()
        soc = [0.4, 0.6] * 50
        result = estimator.assess(soc, dt_hours=1.0)
        d = result.to_dict()
        assert "soh_pct" in d
        assert "degradation_rate_pct_per_year" in d
        assert "breakdown" in d


# ---------------------------------------------------------------------------
# Weather Forecast Tests
# ---------------------------------------------------------------------------

from solar_fleet.weather_forecast import (
    CloudCoverGHIEstimator,
    HourlyWeather,
    PVProductionForecaster,
    WeatherForecast,
)


class TestCloudCoverGHIEstimator:

    def test_clear_sky(self):
        estimator = CloudCoverGHIEstimator(k=0.75)
        ghi = estimator.estimate_ghi(1000.0, 0.0)
        assert ghi == 1000.0

    def test_overcast(self):
        estimator = CloudCoverGHIEstimator(k=0.75)
        ghi = estimator.estimate_ghi(1000.0, 100.0)
        assert ghi == 250.0

    def test_partial_cloud(self):
        estimator = CloudCoverGHIEstimator(k=0.75)
        ghi = estimator.estimate_ghi(1000.0, 50.0)
        assert 500 < ghi < 700

    def test_profile(self):
        estimator = CloudCoverGHIEstimator()
        clear = [0, 0, 200, 500, 800, 1000, 800, 500, 200, 0]
        clouds = [80, 70, 50, 30, 10, 5, 20, 40, 60, 90]
        result = estimator.estimate_profile(clear, clouds)
        assert len(result) == 10
        assert all(r >= 0 for r in result)


class TestWeatherForecast:

    def _make_forecast(self, n_hours=24):
        hourly = []
        for i in range(n_hours):
            ghi = max(0, 800 * math.sin(math.pi * i / 14) - 100)
            hourly.append(HourlyWeather(
                timestamp_utc=f"2026-09-27T{i:02d}:00",
                temperature_c=25.0 + 5.0 * math.sin(math.pi * i / 12),
                humidity_pct=60.0,
                wind_speed_ms=3.0,
                wind_direction_deg=180.0,
                cloud_cover_pct=20.0,
                precipitation_mm=0.0,
                ghi_wm2=ghi,
                dni_wm2=ghi * 0.7,
                dhi_wm2=ghi * 0.3,
                pressure_hpa=1013.25,
            ))
        return WeatherForecast(
            latitude=10.0, longitude=106.0,
            timezone_str="Asia/Ho_Chi_Minh", elevation_m=10.0,
            fetched_at_utc="2026-09-27T00:00:00Z",
            hourly=hourly,
        )

    def test_ghi_profile(self):
        f = self._make_forecast()
        profile = f.ghi_profile
        assert len(profile) == 24
        assert max(profile) > 0

    def test_temperature_profile(self):
        f = self._make_forecast()
        temps = f.temperature_profile
        assert len(temps) == 24
        assert all(15 < t < 35 for t in temps)

    def test_to_dict(self):
        f = self._make_forecast()
        d = f.to_dict()
        assert d["hours"] == 24
        assert d["source"] == "open-meteo"


class TestPVProductionForecaster:

    def test_forecast_from_weather(self):
        forecast = TestWeatherForecast()._make_forecast()
        pv = PVProductionForecaster(peak_power_kwp=10.0)
        result = pv.forecast_from_weather(forecast)
        assert len(result) == 24
        assert any(h["ac_power_kw"] > 0 for h in result)

    def test_daily_summary(self):
        forecast = TestWeatherForecast()._make_forecast()
        pv = PVProductionForecaster(peak_power_kwp=10.0)
        hourly = pv.forecast_from_weather(forecast)
        summary = pv.daily_summary(hourly)
        assert summary["total_energy_kwh"] > 0
        assert summary["peak_power_kw"] > 0
        assert 0 < summary["capacity_factor"] < 1


# ---------------------------------------------------------------------------
# EV Charger Tests
# ---------------------------------------------------------------------------

from solar_fleet.ev_charger import (
    ChargeController,
    ChargeMode,
    Charger,
    ChargerStatus,
    EVSession,
)


class TestCharger:

    def test_max_power_3phase(self):
        c = Charger("c1", "Test", max_current_a=32)
        assert c.max_power_actual_kw == pytest.approx(22.08, rel=0.01)

    def test_to_dict(self):
        c = Charger("c1", "Test")
        d = c.to_dict()
        assert d["charger_id"] == "c1"
        assert d["has_active_session"] is False


class TestEVSession:

    def test_energy_needed(self):
        s = EVSession(
            "s1", "c1", battery_capacity_kwh=60.0,
            current_soc_pct=20.0, target_soc_pct=80.0,
        )
        assert s.energy_needed_kwh == pytest.approx(36.0)

    def test_time_to_full(self):
        s = EVSession(
            "s1", "c1", battery_capacity_kwh=60.0,
            current_soc_pct=50.0, target_soc_pct=80.0,
            active_power_kw=11.0,
        )
        assert s.time_to_full_hours == pytest.approx(
            18.0 / 11.0, rel=0.01,
        )


class TestChargeController:

    def _make_controller(self):
        ctrl = ChargeController()
        ctrl.register_charger(Charger("c1", "Wallbox 1", max_power_kw=22.0))
        ctrl.register_charger(Charger("c2", "Wallbox 2", max_power_kw=11.0))
        return ctrl

    def test_start_session(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.NOW,
            battery_capacity_kwh=60.0, current_soc_pct=30.0,
        )
        result = ctrl.start_session(session)
        assert result.is_active
        assert ctrl._chargers["c1"].status == ChargerStatus.PREPARING

    def test_now_mode_charges(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.NOW,
            battery_capacity_kwh=60.0, current_soc_pct=30.0,
        )
        ctrl.start_session(session)

        result = ctrl.update(60.0, solar_surplus_kw=0.0)
        assert result["total_power_kw"] > 0
        assert result["active_sessions"] == 1

    def test_solar_mode_no_surplus(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.SOLAR,
            battery_capacity_kwh=60.0, current_soc_pct=30.0,
        )
        ctrl.start_session(session)

        result = ctrl.update(60.0, solar_surplus_kw=0.0)
        assert result["total_power_kw"] == 0.0

    def test_solar_mode_with_surplus(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.SOLAR,
            battery_capacity_kwh=60.0, current_soc_pct=30.0,
        )
        ctrl.start_session(session)

        result = ctrl.update(60.0, solar_surplus_kw=8.0)
        assert result["total_power_kw"] > 0
        assert result["solar_surplus_used_kw"] > 0

    def test_stop_session(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.NOW,
            battery_capacity_kwh=60.0,
        )
        ctrl.start_session(session)
        stopped = ctrl.stop_session("s1")
        assert stopped is not None
        assert not stopped.is_active
        assert ctrl._chargers["c1"].status == ChargerStatus.AVAILABLE

    def test_soc_reaches_target(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.NOW,
            battery_capacity_kwh=10.0, current_soc_pct=78.0,
            target_soc_pct=80.0,
        )
        ctrl.start_session(session)

        # Charge for many steps
        for _ in range(100):
            ctrl.update(60.0)

        assert session.current_soc_pct >= 80.0
        assert session.active_power_kw == 0.0

    def test_status(self):
        ctrl = self._make_controller()
        status = ctrl.status()
        assert status["chargers"] == 2
        assert status["active_sessions"] == 0

    def test_smart_mode(self):
        ctrl = self._make_controller()
        session = EVSession(
            "s1", "c1", charge_mode=ChargeMode.SMART,
            battery_capacity_kwh=60.0, current_soc_pct=30.0,
        )
        ctrl.start_session(session)

        # High solar surplus → should charge
        result = ctrl.update(60.0, solar_surplus_kw=10.0, grid_price=0.2)
        assert result["total_power_kw"] > 0
