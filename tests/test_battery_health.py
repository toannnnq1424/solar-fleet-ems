
from solar_fleet.battery_health import (
    BatterySpecification,
    calculate_dod_stress_factor,
    calculate_temperature_stress,
    estimate_battery_health,
)


def test_temperature_stress_arrhenius():
    # At 25 C reference temperature, stress is 1.0
    assert calculate_temperature_stress(25.0, 25.0) == 1.0
    # At 35 C (10 C rise), rate doubles to 2.0
    assert calculate_temperature_stress(35.0, 25.0) == 2.0
    # At 45 C (20 C rise), rate quadruples to 4.0
    assert calculate_temperature_stress(45.0, 25.0) == 4.0
    # Below 10 C, slight cold stress
    assert calculate_temperature_stress(5.0, 25.0) == 1.15


def test_dod_stress_factor():
    stress_50 = calculate_dod_stress_factor(50.0)
    stress_80 = calculate_dod_stress_factor(80.0)
    stress_100 = calculate_dod_stress_factor(100.0)
    assert stress_50 < stress_80 < stress_100
    assert stress_80 == 1.0


def test_battery_health_estimation():
    spec = BatterySpecification(
        nominal_capacity_kwh=10.0,
        chemistry="LFP",
        warranty_cycles=6000,
        warranty_years=10,
        eol_soh_percent=70.0,
    )

    # Brand new battery with zero throughput
    state_new = estimate_battery_health(
        device_id="batt-01",
        spec=spec,
        total_discharge_kwh=0.0,
        calendar_days=0,
        avg_temp_c=25.0,
    )
    assert state_new.soh_percent == 100.0
    assert state_new.equivalent_full_cycles == 0.0
    assert state_new.warranty_status == "WITHIN_WARRANTY"

    # Aged battery: 3000 EFC cycles (30,000 kWh discharge on 10kWh pack) after 1500 days
    state_aged = estimate_battery_health(
        device_id="batt-02",
        spec=spec,
        total_discharge_kwh=30000.0,
        calendar_days=1500,
        avg_temp_c=28.0,
    )
    assert state_aged.equivalent_full_cycles == 3000.0
    assert 75.0 <= state_aged.soh_percent < 100.0
    assert state_aged.warranty_status == "WITHIN_WARRANTY"
    assert state_aged.warranty_remaining_cycles == 3000

    # Over-cycled battery: 7000 EFC cycles exceeds 6000 warranty
    state_exceeded = estimate_battery_health(
        device_id="batt-03",
        spec=spec,
        total_discharge_kwh=70000.0,
        calendar_days=2000,
        avg_temp_c=25.0,
    )
    assert state_exceeded.warranty_status == "EXCEEDED_CYCLES"
    assert state_exceeded.warranty_remaining_cycles == 0


def test_battery_bms_soh_fusion():
    spec = BatterySpecification(nominal_capacity_kwh=10.0)
    # Physical model predicts ~92%, reported BMS is 90%
    state = estimate_battery_health(
        device_id="batt-04",
        spec=spec,
        total_discharge_kwh=15000.0,
        calendar_days=700,
        avg_temp_c=26.0,
        reported_bms_soh=90.0,
    )
    assert state.reported_bms_soh == 90.0
    # Final SOH fuses reported BMS Coulomb counting
    assert 88.0 <= state.soh_percent <= 95.0
