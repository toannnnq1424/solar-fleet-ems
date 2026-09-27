"""Unit and contract tests for Solis MQTT Bridge and Home Assistant Auto-Discovery.

Derived from community integration knowledge:
solis2mqtt-main (GPL-3.0, incub77) - Clean-room independently implemented.
"""

from __future__ import annotations

import pytest

from solar_fleet.solis_mqtt_bridge import (
    SOLIS_STRING_REGISTERS,
    HomeAssistantMqttDiscoveryGenerator,
    SolisControlCompiler,
    SolisOfflineSanitizer,
    SolisTelemetryDecoder,
    calculate_modbus_crc16,
)

# ---------------------------------------------------------------------------
# Unit Tests: Core Data Models & Helpers
# ---------------------------------------------------------------------------

def test_solis_registers_catalogue():
    """Verify all 13 Solis string registers are properly registered."""
    assert len(SOLIS_STRING_REGISTERS) == 13
    reg_names = {r.name for r in SOLIS_STRING_REGISTERS}

    expected_names = {
        "active_power",
        "inverter_temp",
        "total_power",
        "generation_today",
        "generation_yesterday",
        "total_dc_output_power",
        "energy_this_month",
        "generation_last_month",
        "generation_this_year",
        "generation_last_year",
        "system_datetime",
        "power_limitation",
        "on_off",
    }
    assert expected_names.issubset(reg_names)

    # Check writable controls
    power_lim = next(r for r in SOLIS_STRING_REGISTERS if r.name == "power_limitation")
    assert power_lim.function_code == 3
    assert power_lim.write_function_code == 6
    assert power_lim.ha_device == "number"
    assert power_lim.ha_min == 0.0
    assert power_lim.ha_max == 100.0

    switch = next(r for r in SOLIS_STRING_REGISTERS if r.name == "on_off")
    assert switch.function_code == 3
    assert switch.write_function_code == 6
    assert switch.ha_device == "switch"
    assert switch.ha_payload_on == 190
    assert switch.ha_payload_off == 222


def test_modbus_crc16():
    """Verify Modbus RTU CRC16 implementation against standard test frame."""
    # Standard Modbus request: Slave 1, FC 04, Reg 3004 (0x0BBC), Count 2 (0x0002)
    frame = bytes([0x01, 0x04, 0x0B, 0xBC, 0x00, 0x02])
    crc = calculate_modbus_crc16(frame)
    # Check that CRC is a 16-bit integer
    assert 0 <= crc <= 0xFFFF
    # Test reversibility: CRC of frame + little-endian CRC should equal 0
    full_frame = frame + bytes([crc & 0xFF, (crc >> 8) & 0xFF])
    assert calculate_modbus_crc16(full_frame) == 0


def test_composed_datetime_decoder():
    """Verify ISO 8601 formatting of 6-register Solis datetime block."""
    raw_regs = [26, 9, 27, 9, 45, 12]  # [YY, MM, DD, hh, mm, ss]
    iso_str = SolisTelemetryDecoder.decode_composed_datetime(raw_regs)
    assert iso_str == "2026-09-27T09:45:12"

    # Year with 4 digits directly
    raw_regs_4dig = [2026, 12, 31, 23, 59, 59]
    iso_str_4dig = SolisTelemetryDecoder.decode_composed_datetime(raw_regs_4dig)
    assert iso_str_4dig == "2026-12-31T23:59:59"

    # Incomplete register array raises ValueError
    with pytest.raises(ValueError):
        SolisTelemetryDecoder.decode_composed_datetime([26, 9, 27])


# ---------------------------------------------------------------------------
# Unit Tests: Home Assistant Auto-Discovery Generator
# ---------------------------------------------------------------------------

def test_home_assistant_discovery_generation():
    """Verify HA MQTT discovery configs for sensors, numbers, and switches."""
    configs = HomeAssistantMqttDiscoveryGenerator.generate_all(
        discovery_prefix="homeassistant",
        base_topic="solis2mqtt",
    )
    assert len(configs) == 13

    # Check a sensor
    pwr_sensor = next(c for c in configs if c["entity_name"] == "active_power")
    assert pwr_sensor["discovery_topic"] == "homeassistant/sensor/solis2mqtt/active_power/config"
    assert pwr_sensor["state_topic"] == "solis2mqtt/active_power"
    assert pwr_sensor["payload"]["device_class"] == "power"
    assert pwr_sensor["payload"]["state_class"] == "measurement"
    assert pwr_sensor["payload"]["unit_of_measurement"] == "W"
    assert pwr_sensor["payload"]["device"]["manufacturer"] == "Ginlong Technologies"

    # Check number entity (Power Limitation)
    num_cfg = next(c for c in configs if c["entity_name"] == "power_limitation")
    assert num_cfg["entity_type"] == "number"
    assert num_cfg["discovery_topic"] == "homeassistant/number/solis2mqtt/power_limitation/config"
    assert num_cfg["command_topic"] == "solis2mqtt/power_limitation/set"
    assert num_cfg["payload"]["min"] == 0.0
    assert num_cfg["payload"]["max"] == 100.0
    assert num_cfg["payload"]["step"] == 0.01

    # Check switch entity (On/Off)
    sw_cfg = next(c for c in configs if c["entity_name"] == "on_off")
    assert sw_cfg["entity_type"] == "switch"
    assert sw_cfg["discovery_topic"] == "homeassistant/switch/solis2mqtt/on_off/config"
    assert sw_cfg["command_topic"] == "solis2mqtt/on_off/set"
    assert sw_cfg["payload"]["payload_on"] == "190"
    assert sw_cfg["payload"]["payload_off"] == "222"


# ---------------------------------------------------------------------------
# Unit Tests: Telemetry Decoding
# ---------------------------------------------------------------------------

def test_telemetry_decoder():
    """Verify conversion of raw register blocks into engineering values."""
    simulated_regs = {
        3004: 0, 3005: 4500,        # active_power = 4500 W (32-bit uint)
        3006: 0, 3007: 4800,        # total_dc_output_power = 4800 W (32-bit uint)
        3008: 0, 3009: 15420,       # total_power = 15420 kWh (32-bit int)
        3010: 0, 3011: 320,         # energy_this_month = 320 kWh
        3012: 0, 3013: 450,         # generation_last_month = 450 kWh
        3014: 215,                  # generation_today = 21.5 kWh (1 decimal)
        3015: 280,                  # generation_yesterday = 28.0 kWh (1 decimal)
        3016: 0, 3017: 2100,        # generation_this_year = 2100 kWh
        3018: 0, 3019: 3100,        # generation_last_year = 3100 kWh
        3041: 365,                  # inverter_temp = 36.5 °C (1 decimal)
        3051: 7500,                 # power_limitation = 75.00% (2 decimals)
        3072: 26, 3073: 9, 3074: 27, 3075: 10, 3076: 15, 3077: 30,  # 2026-09-27T10:15:30
    }

    result = SolisTelemetryDecoder.decode_all_telemetry(simulated_regs, base_topic="solis2mqtt")
    metrics = result["metrics"]
    msgs = {m["topic"]: m["payload"] for m in result["mqtt_messages"]}

    assert metrics["active_power"]["value"] == 4500
    assert msgs["solis2mqtt/active_power"] == "4500"

    assert metrics["generation_today"]["value"] == 21.5
    assert msgs["solis2mqtt/generation_today"] == "21.5"

    assert metrics["inverter_temp"]["value"] == 36.5
    assert msgs["solis2mqtt/inverter_temp"] == "36.5"

    assert metrics["power_limitation"]["value"] == 75.0
    assert msgs["solis2mqtt/power_limitation"] == "75.0"

    assert metrics["system_datetime"]["value"] == "2026-09-27T10:15:30"
    assert msgs["solis2mqtt/system_datetime"] == "2026-09-27T10:15:30"


# ---------------------------------------------------------------------------
# Unit Tests: Night-Time Offline Sanitization
# ---------------------------------------------------------------------------

def test_offline_sanitizer():
    """Verify that measurements drop to 0 while energy statistics are preserved."""
    daytime_metrics = {
        "active_power": {"value": 4500},
        "total_dc_output_power": {"value": 4800},
        "inverter_temp": {"value": 36.5},
        "generation_today": {"value": 21.5},
        "total_power": {"value": 15420},
        "energy_this_month": {"value": 320},
    }

    sanitized = SolisOfflineSanitizer.sanitize_offline_state(daytime_metrics)
    assert sanitized["inverter_offline"] is True
    assert sanitized["recommended_poll_interval_sec"] == 600

    out_metrics = sanitized["sanitized_metrics"]
    # Measurements zeroed
    assert out_metrics["active_power"]["value"] == 0
    assert out_metrics["total_dc_output_power"]["value"] == 0
    assert out_metrics["inverter_temp"]["value"] == 0

    # Total increasing energy counters preserved!
    assert out_metrics["generation_today"]["value"] == 21.5
    assert out_metrics["total_power"]["value"] == 15420
    assert out_metrics["energy_this_month"]["value"] == 320


# ---------------------------------------------------------------------------
# Unit Tests: FC06 Modbus Write Command Compiler
# ---------------------------------------------------------------------------

def test_control_compiler_power_limitation():
    """Verify compilation of Reg 3051 FC06 write frames with safety gates."""
    # 50.00% -> raw 5000 (0x1388)
    frame = SolisControlCompiler.compile_power_limitation(50.0, slave_address=1)
    assert frame.function_code == 6
    assert frame.register_address == 3051
    assert frame.raw_value == 5000
    assert frame.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert frame.wire_bytes[:6] == [0x01, 0x06, 0x0B, 0xEB, 0x13, 0x88]

    # Verify CRC on wire bytes
    assert calculate_modbus_crc16(bytes(frame.wire_bytes)) == 0

    # 100.00% -> raw 10000 (0x2710)
    frame_max = SolisControlCompiler.compile_power_limitation(100.0, slave_address=1, bypass_safety=True)
    assert frame_max.raw_value == 10000
    assert frame_max.safety_gate == "COMMISSIONED_WRITE_ENABLED"

    # Invalid range bounds
    with pytest.raises(ValueError):
        SolisControlCompiler.compile_power_limitation(-5.0)
    with pytest.raises(ValueError):
        SolisControlCompiler.compile_power_limitation(105.0)


def test_control_compiler_inverter_switch():
    """Verify compilation of Reg 3006 FC06 start/stop switch frames."""
    # Test ON states
    for state in (True, 190, "ON", "START"):
        frame_on = SolisControlCompiler.compile_inverter_switch(state, slave_address=1)
        assert frame_on.register_address == 3006
        assert frame_on.raw_value == 190  # 0x00BE
        assert frame_on.wire_bytes[:6] == [0x01, 0x06, 0x0B, 0xBE, 0x00, 0xBE]
        assert calculate_modbus_crc16(bytes(frame_on.wire_bytes)) == 0
        assert frame_on.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # Test OFF states
    for state in (False, 222, "OFF", "STOP"):
        frame_off = SolisControlCompiler.compile_inverter_switch(state, slave_address=1)
        assert frame_off.register_address == 3006
        assert frame_off.raw_value == 222  # 0x00DE
        assert frame_off.wire_bytes[:6] == [0x01, 0x06, 0x0B, 0xBE, 0x00, 0xDE]
        assert calculate_modbus_crc16(bytes(frame_off.wire_bytes)) == 0

    # Invalid state
    with pytest.raises(ValueError):
        SolisControlCompiler.compile_inverter_switch("INVALID_ACTION")


from test_workspaces import login

# ---------------------------------------------------------------------------
# Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_solis_mqtt_routes(local):
    """Test REST API endpoints under /api/solis-mqtt."""
    client, _ctl = local
    headers = login(local, "operator")

    # 1. Get registers
    res = client.get("/api/solis-mqtt/registers", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["total_registers"] == 13
    assert any(r["name"] == "power_limitation" for r in data["registers"])

    # 2. Generate HA discovery
    res = client.post(
        "/api/solis-mqtt/discovery-topics",
        json={
            "device_name": "solis_test",
            "device_model": "Ginlong Solis String",
            "base_topic": "solis2mqtt",
            "discovery_prefix": "homeassistant",
        },
        headers=headers,
    )
    assert res.status_code == 200
    disc_data = res.json()
    assert disc_data["total_entities"] == 13
    assert any(c["entity_name"] == "on_off" for c in disc_data["discovery_configs"])

    # 3. Decode telemetry
    res = client.post(
        "/api/solis-mqtt/decode-telemetry",
        json={
            "registers": {
                "3004": 0,
                "3005": 3500,
                "3014": 185,
                "3041": 420,
            },
            "base_topic": "solis2mqtt",
        },
        headers=headers,
    )
    assert res.status_code == 200
    dec_data = res.json()
    assert dec_data["metrics"]["active_power"]["value"] == 3500
    assert dec_data["metrics"]["generation_today"]["value"] == 18.5
    assert dec_data["metrics"]["inverter_temp"]["value"] == 42.0

    # 4. Simulate offline
    res = client.post(
        "/api/solis-mqtt/simulate-offline",
        json={
            "last_known_metrics": {
                "active_power": {"value": 3500},
                "generation_today": {"value": 18.5},
            },
            "base_topic": "solis2mqtt",
        },
        headers=headers,
    )
    assert res.status_code == 200
    off_data = res.json()
    assert off_data["inverter_offline"] is True
    assert off_data["sanitized_metrics"]["active_power"]["value"] == 0
    assert off_data["sanitized_metrics"]["generation_today"]["value"] == 18.5

    # 5. Compile control frame
    res = client.post(
        "/api/solis-mqtt/compile-control",
        json={
            "metric": "power_limitation",
            "value": 80.0,
            "slave_address": 1,
            "bypass_safety": False,
        },
        headers=headers,
    )
    assert res.status_code == 200
    ctrl_data = res.json()
    assert ctrl_data["register_address"] == 3051
    assert ctrl_data["raw_value"] == 8000
    assert ctrl_data["safety_gate"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # Switch control compile
    res_sw = client.post(
        "/api/solis-mqtt/compile-control",
        json={
            "metric": "on_off",
            "value": "ON",
            "slave_address": 1,
        },
        headers=headers,
    )
    assert res_sw.status_code == 200
    sw_data = res_sw.json()
    assert sw_data["register_address"] == 3006
    assert sw_data["raw_value"] == 190

