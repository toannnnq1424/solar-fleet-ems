from datetime import datetime
from zoneinfo import ZoneInfo

from solar_fleet.forecast_baseline import (
    calculate_clearsky_pv_profile,
    optimize_economic_dispatch,
)


def test_clearsky_pv_profile():
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    # Noon on sunny equinox date in Ho Chi Minh City (Lat ~10.8, Lon ~106.7)
    start_dt = datetime(2026, 9, 21, 0, 0, tzinfo=tz)
    profile = calculate_clearsky_pv_profile(
        latitude=10.7769,
        longitude=106.7009,
        peak_kwp=50.0,
        start_dt=start_dt,
        hours=24,
    )

    assert len(profile) == 24
    # Midnight hours (0, 1, 2, 3, 22, 23) must produce 0 W
    assert profile[0]["pv_power_w"] == 0.0
    assert profile[2]["pv_power_w"] == 0.0
    assert profile[23]["pv_power_w"] == 0.0

    # Solar midday (11:00 - 13:00) must produce substantial solar power
    midday = [p for p in profile if 11 <= p["hour"] <= 13]
    for p in midday:
        assert p["pv_power_w"] > 25000.0  # > 25 kW on a 50 kWp system
        assert p["ghi_w_per_m2"] > 500.0


def test_economic_dispatch_optimizer_saves_cost():
    tz = ZoneInfo("Asia/Ho_Chi_Minh")
    start_dt = datetime(2026, 9, 21, 0, 0, tzinfo=tz)

    pv_profile = calculate_clearsky_pv_profile(
        latitude=10.7769,
        longitude=106.7009,
        peak_kwp=50.0,
        start_dt=start_dt,
        hours=24,
    )

    # Synthetic factory load profile: 20kW baseline, 45kW peak
    load_profile = []
    for h in range(24):
        load_w = 40000.0 if 8 <= h <= 19 else 15000.0
        load_profile.append({
            "timestamp": (start_dt.replace(hour=h)).isoformat(),
            "value_w": load_w,
        })

    # Optimize with a 30 kWh / 10 kW battery storage
    result = optimize_economic_dispatch(
        pv_profile=pv_profile,
        load_profile=load_profile,
        battery_capacity_kwh=30.0,
        initial_soc_percent=50.0,
        max_charge_power_w=10000.0,
        max_discharge_power_w=10000.0,
    )

    assert result["horizon_hours"] == 24
    assert result["total_cost_without_ems_vnd"] > 0
    assert result["total_cost_with_ems_vnd"] > 0
    # Crucial property: EMS optimization must reduce overall cost!
    assert result["total_cost_with_ems_vnd"] <= result["total_cost_without_ems_vnd"]
    assert result["total_savings_vnd"] >= 0
    assert len(result["dispatch_points"]) == 24

    # Check that battery was charged during high solar hours and discharged during peak
    points = result["dispatch_points"]
    peak_points = [p for p in points if p["tariff_tier"] == "PEAK"]
    # During peak hours, battery should discharge (battery_power_w < 0)
    discharging_peak_count = sum(1 for p in peak_points if p["battery_power_w"] < 0)
    assert discharging_peak_count > 0
