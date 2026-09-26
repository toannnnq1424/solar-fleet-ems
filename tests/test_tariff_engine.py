from datetime import datetime
from zoneinfo import ZoneInfo

from solar_fleet.tariff_engine import (
    TariffTierSchedule,
    analyze_site_tariff,
    calculate_power_factor_penalty,
)


def test_evn_tou_schedule_classification():
    tz = ZoneInfo("Asia/Ho_Chi_Minh")

    # Monday 02:00 -> Off-peak (22:00 - 04:00)
    mon_offpeak = datetime(2026, 9, 21, 2, 0, tzinfo=tz)  # Monday
    assert TariffTierSchedule.classify_hour(mon_offpeak) == "OFF_PEAK"

    # Monday 08:00 -> Normal (04:00 - 09:30)
    mon_normal = datetime(2026, 9, 21, 8, 0, tzinfo=tz)
    assert TariffTierSchedule.classify_hour(mon_normal) == "NORMAL"

    # Monday 10:00 -> Peak morning (09:30 - 11:30)
    mon_peak1 = datetime(2026, 9, 21, 10, 0, tzinfo=tz)
    assert TariffTierSchedule.classify_hour(mon_peak1) == "PEAK"

    # Monday 14:00 -> Normal (11:30 - 17:00)
    mon_normal2 = datetime(2026, 9, 21, 14, 0, tzinfo=tz)
    assert TariffTierSchedule.classify_hour(mon_normal2) == "NORMAL"

    # Monday 18:00 -> Peak evening (17:00 - 20:00)
    mon_peak2 = datetime(2026, 9, 21, 18, 0, tzinfo=tz)
    assert TariffTierSchedule.classify_hour(mon_peak2) == "PEAK"

    # Sunday 10:00 -> Sunday has NO peak hours per EVN rules! Must be NORMAL
    sun_morning = datetime(2026, 9, 27, 10, 0, tzinfo=tz)  # Sunday
    assert TariffTierSchedule.classify_hour(sun_morning) == "NORMAL"

    # Sunday 18:00 -> Normal
    sun_evening = datetime(2026, 9, 27, 18, 0, tzinfo=tz)
    assert TariffTierSchedule.classify_hour(sun_evening) == "NORMAL"

    # Sunday 23:00 -> Off-peak
    sun_night = datetime(2026, 9, 27, 23, 0, tzinfo=tz)
    assert TariffTierSchedule.classify_hour(sun_night) == "OFF_PEAK"


def test_circular_15_power_factor_penalty():
    # 1. Compliant case: cos phi = 0.95 >= 0.90 -> no penalty
    # P = 95 kWh, Q = 31.2 kvarh -> S = 100 kVAh, cos phi = 0.95
    res_compliant = calculate_power_factor_penalty(
        active_energy_kwh=95.0,
        reactive_energy_kvarh=31.2,
        active_bill_vnd=1000000.0,
    )
    assert res_compliant.is_compliant is True
    assert res_compliant.penalty_percent == 0.0
    assert res_compliant.estimated_penalty_vnd == 0.0
    assert res_compliant.cos_phi >= 0.90

    # 2. Non-compliant case: cos phi = 0.80
    # P = 80 kWh, Q = 60 kvarh -> S = 100 kVAh, cos phi = 0.80
    # Penalty k = (0.90 / 0.80 - 1.0) * 100 = 12.5%
    res_penalized = calculate_power_factor_penalty(
        active_energy_kwh=80.0,
        reactive_energy_kvarh=60.0,
        active_bill_vnd=10000000.0,
    )
    assert res_penalized.is_compliant is False
    assert res_penalized.cos_phi == 0.80
    assert res_penalized.penalty_percent == 12.5
    assert res_penalized.estimated_penalty_vnd == 1250000.0
    assert res_penalized.reactive_compensation_needed_kvar > 0.0

    # 3. Severe non-compliance: cos phi = 0.75
    # Penalty k = (0.90 / 0.75 - 1.0) * 100 = 20.0%
    res_severe = calculate_power_factor_penalty(
        active_energy_kwh=75.0,
        reactive_energy_kvarh=66.14,
        active_bill_vnd=5000000.0,
    )
    assert res_severe.penalty_percent == 20.0
    assert res_severe.estimated_penalty_vnd == 1000000.0


def test_site_tariff_analysis():
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    # Simulate a full week of hourly load
    hourly_imports = []
    base_dt = datetime(2026, 9, 21, 0, 0, tzinfo=tz)
    for h in range(168):  # 7 days
        current = base_dt.replace(hour=h % 24)
        hourly_imports.append((current, 20.0))  # 20 kWh each hour

    result = analyze_site_tariff(
        site_id="site-test-01",
        customer_class="MANUFACTURING",
        voltage_tier="MEDIUM_VOLTAGE_22_110KV",
        hourly_grid_import_kwh=hourly_imports,
        total_reactive_kvarh=500.0,
    )

    assert result.site_id == "site-test-01"
    assert result.total_active_energy_kwh > 0
    assert result.total_active_bill_vnd > 0
    assert result.energy_consumption_kwh["peak_kwh"] > 0
    assert result.energy_consumption_kwh["off_peak_kwh"] > 0
    assert result.power_factor_analysis.cos_phi > 0.90
    assert "recommended_battery_discharge_kw" in result.peak_shaving_opportunity
