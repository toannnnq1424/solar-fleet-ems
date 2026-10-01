"""Tests for Sungrow Commercial Multi-MPPT profile (SG110CX/SG125HX)."""

import pytest

from solar_fleet.adapters.modbus_profiles.sungrow_commercial import (
    SungrowCommercialProfile,
)


def test_sungrow_commercial_mppt_architecture():
    profile = SungrowCommercialProfile()
    assert profile.model == "SG110CX"
    assert profile.mppt_count == 9
    assert profile.string_count == 18
    assert profile.is_1_based_indexing is True


def test_sungrow_commercial_address_conversion():
    profile = SungrowCommercialProfile()
    # In Sungrow protocol: Protocol address = Wire address + 1
    # Wire address for Active Power Limit register 6001 is 6000
    assert profile.to_wire_address(6001) == 6000
    assert profile.to_protocol_address(6000) == 6001


def test_sungrow_commercial_telemetry_decode():
    profile = SungrowCommercialProfile()
    # Mock Modbus raw registers
    raw_registers = {
        5000: 2,         # Running state: Run
        5001: 10500,     # Total Active Power: 105.0 kW (scale 0.01)
        5003: 0,         # Reactive Power: 0.0 kvar
        5005: 1000,      # Power Factor: 1.000
        5006: 5002,      # Grid Frequency: 50.02 Hz
    }
    # Populate 9 MPPTs V and I
    for m in range(1, 10):
        raw_registers[5010 + (m - 1) * 2] = 6800  # 680.0 V
        raw_registers[5011 + (m - 1) * 2] = 185   # 18.5 A

    decoded = profile.decode_telemetry(raw_registers)
    assert decoded["device_state"] == "RUN"
    assert decoded["total_active_power_kw"] == 105.0
    assert decoded["grid_frequency_hz"] == 50.02
    assert len(decoded["mppts"]) == 9
    assert decoded["mppts"][1]["voltage_v"] == 680.0
    assert decoded["mppts"][1]["current_a"] == 18.5
    assert decoded["mppts"][1]["power_w"] == pytest.approx(12580.0)


def test_sungrow_commercial_control_validation():
    profile = SungrowCommercialProfile()
    # Valid active power limit (0..110 kW)
    cmd = profile.build_active_power_command(power_kw=88.0)
    assert cmd["register"] == 6001
    assert cmd["wire_register"] == 6000
    assert cmd["value"] == 880  # 0.1 kW scale

    # Out of range command rejected
    with pytest.raises(ValueError):
        profile.build_active_power_command(power_kw=150.0)


def test_sungrow_commercial_registry_lookup():
    from solar_fleet.adapters.modbus_profiles import get_register_map
    fields_110 = get_register_map("sungrow", "sg110cx")
    fields_125 = get_register_map("sungrow", "sg125hx")
    fields_comm = get_register_map("sungrow", "commercial")
    assert len(fields_110) > 0
    assert len(fields_125) == len(fields_110)
    assert len(fields_comm) == len(fields_110)


def test_sungrow_commercial_exact_profile():
    from solar_fleet.adapters.modbus_profiles import get_exact_profile
    fields, decoder = get_exact_profile("sungrow", "sg110cx")
    assert len(fields) > 0
    assert callable(decoder)

    fields_125, _ = get_exact_profile("sungrow", "sg125hx")
    assert len(fields_125) > 0


def test_sungrow_commercial_decode_registers_wire_addresses():
    from solar_fleet.adapters.modbus_profiles import decode_registers
    # Wire 0-based addresses:
    # 4999: running state (2 = RUN)
    # 5000: active power (10500 * 10 = 105000 W)
    # 5005: grid freq (5002 * 0.01 = 50.02 Hz)
    # 5009: pv1_voltage (6800 * 0.1 = 680.0 V)
    # 5010: pv1_current (185 * 0.1 = 18.5 A)
    raw = {
        "4999": 2,
        "5000": 10500,
        "5005": 5002,
        "5009": 6800,
        "5010": 185,
    }
    decoded = decode_registers(raw, "sungrow", "sg110cx")
    assert decoded["inverter_status"] == (2.0, "")
    assert decoded["active_power"] == (105000.0, "W")
    assert decoded["grid_frequency"] == (50.02, "Hz")
    assert decoded["pv1_voltage"] == (680.0, "V")
    assert decoded["pv1_current"] == (18.5, "A")
    assert "pv_power" in decoded
    assert decoded["pv_power"][0] == pytest.approx(12580.0)


def test_sungrow_commercial_decode_registers_protocol_addresses():
    from solar_fleet.adapters.modbus_profiles import decode_registers
    # Protocol 1-based addresses:
    # 5000: running state
    # 5001: active power
    # 5006: grid freq
    raw = {
        "5000": 2,
        "5001": 10500,
        "5006": 5002,
    }
    decoded = decode_registers(raw, "sungrow", "sg125hx")
    assert decoded["inverter_status"] == (2.0, "")
    assert decoded["active_power"] == (105000.0, "W")
    assert decoded["grid_frequency"] == (50.02, "Hz")
