"""Unit and contract tests for SmartESS / Eybond Local Protocol and Client.

Validates:
- Eybond Modbus binary framing (Header, FC_HEARTBEAT, FC_FORWARD2DEVICE)
- P17 and Q-protocol frame encoding, CRC-16/XMODEM with byte-stuffing
- Response parser handling P17 data, short ACK/NAK, and Q-protocol data/ACK/NAK
- Telemetry parsers for GS (General Status), MOD (Mode), PIRI (Rated info), ET (Energy)
- Parameter command builders with strict bounds validation
- Solar Fleet EMS telemetry normalization
- SmartEssLocalClient simulation and safety gating under LOCKED_PENDING_HARDWARE_ACCEPTANCE
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest

from solar_fleet.smartess_local_client import (
    DEVCODE_SOLAR_P17,
    FC_FORWARD2DEVICE,
    FC_HEARTBEAT,
    SmartEssLocalClient,
    _stuff_crc_byte,
    build_battery_bulk_float_command,
    build_battery_cutoff_voltage_command,
    build_battery_recharge_redischarge_command,
    build_charger_priority_command,
    build_forward2device,
    build_heartbeat_request,
    build_max_ac_charge_current_command,
    build_max_charge_current_command,
    build_output_priority_command,
    build_p17_poll,
    build_p17_set,
    crc16_xmodem,
    decode_eybond_header,
    encode_eybond_header,
    normalize_smartess_telemetry,
    parse_et_telemetry,
    parse_forward2device_response,
    parse_gs_telemetry,
    parse_heartbeat_response,
    parse_inverter_response,
    parse_mod_telemetry,
    parse_piri_telemetry,
)

# ---------------------------------------------------------------------------
# Eybond Header & Framing Tests
# ---------------------------------------------------------------------------

def test_eybond_header_encoding_and_decoding():
    """Verify 8-byte Eybond header packing and unpacking."""
    hdr_bytes = encode_eybond_header(tid=1234, devcode=0x0994, total_len=24, devaddr=1, fc=0x04)
    assert len(hdr_bytes) == 8

    decoded = decode_eybond_header(hdr_bytes)
    assert decoded.tid == 1234
    assert decoded.devcode == 0x0994
    assert decoded.total_len == 24
    assert decoded.devaddr == 1
    assert decoded.fc == 0x04


def test_eybond_heartbeat_roundtrip():
    """Verify heartbeat request framing and response decoding."""
    dt = datetime(2026, 9, 27, 10, 30, 0, tzinfo=timezone.utc)
    hb_req = build_heartbeat_request(tid=42, interval=60, dt=dt)
    assert len(hb_req) == 16  # 8 hdr + 8 payload
    hdr = decode_eybond_header(hb_req)
    assert hdr.fc == FC_HEARTBEAT
    assert hdr.tid == 42
    assert hdr.total_len == 16

    # Simulate heartbeat response: 8 header + 14 PN bytes
    mock_resp = encode_eybond_header(tid=42, devcode=0, total_len=22, devaddr=1, fc=FC_HEARTBEAT) + b"EYB12345678901"
    resp_hdr, pn = parse_heartbeat_response(mock_resp)
    assert resp_hdr.tid == 42
    assert pn == "EYB12345678901"


def test_eybond_forward2device_roundtrip():
    """Verify FC=4 forward2device wrapping and unwrapping."""
    p17_payload = b"^P005GS\x12\x34\x0D"
    fwd_frame = build_forward2device(tid=99, p17_frame=p17_payload, devcode=DEVCODE_SOLAR_P17, devaddr=2)
    assert len(fwd_frame) == 8 + len(p17_payload)

    hdr, extracted_payload = parse_forward2device_response(fwd_frame)
    assert hdr.tid == 99
    assert hdr.devaddr == 2
    assert hdr.fc == FC_FORWARD2DEVICE
    assert extracted_payload == p17_payload


# ---------------------------------------------------------------------------
# CRC-16 & P17 Framing Tests
# ---------------------------------------------------------------------------

def test_crc16_xmodem_and_stuffing():
    """Verify CRC-16/XMODEM calculation and framing byte stuffing."""
    # Test known string
    test_bytes = b"123456789"
    crc = crc16_xmodem(test_bytes)
    assert crc == 0x31C3

    # Test stuffing for delimiters: 0x28 '(', 0x0D '\r', 0x0A '\n'
    assert _stuff_crc_byte(0x28) == 0x29
    assert _stuff_crc_byte(0x0D) == 0x0E
    assert _stuff_crc_byte(0x0A) == 0x0B
    assert _stuff_crc_byte(0x40) == 0x40


def test_build_p17_poll_and_set():
    """Verify P17 poll (^P) and set (^S) frame structure."""
    poll_frame = build_p17_poll("GS")
    assert poll_frame.startswith(b"^P005GS")
    assert poll_frame.endswith(b"\r")
    assert len(poll_frame) == 2 + 3 + 2 + 2 + 1  # ^P + 005 + GS + 2 CRC + \r = 10 bytes

    set_frame = build_p17_set("POP01")
    assert set_frame.startswith(b"^S008POP01")
    assert set_frame.endswith(b"\r")


def test_parse_inverter_response_variants():
    """Verify parsing P17 standard data, short ACK/NAK, and Q-protocol variants."""
    # 1. P17 data response: ^D010TESTING<crc><crc>\r
    p17_data = b"^D010TESTING\x11\x22\r"
    cmd_type, payload = parse_inverter_response(p17_data)
    assert cmd_type == "D"
    assert payload == "TESTING"

    # 2. P17 short ACK: ^1<crc><crc>\r (5 bytes)
    p17_ack = b"^1\x33\x44\r"
    cmd_type, payload = parse_inverter_response(p17_ack)
    assert cmd_type == "A"
    assert payload == ""

    # 3. P17 short NAK: ^0<crc><crc>\r (5 bytes)
    p17_nak = b"^0\x33\x44\r"
    cmd_type, payload = parse_inverter_response(p17_nak)
    assert cmd_type == "N"
    assert payload == ""

    # 4. Q-protocol data: (230.0 50.0<crc><crc>\r
    q_data = b"(230.0 50.0\x55\x66\r"
    cmd_type, payload = parse_inverter_response(q_data)
    assert cmd_type == "D"
    assert payload == "230.0 50.0"

    # 5. Q-protocol ACK: (ACK<crc><crc>\r
    q_ack = b"(ACK\x55\x66\r"
    cmd_type, payload = parse_inverter_response(q_ack)
    assert cmd_type == "A"
    assert payload == ""

    # 6. Q-protocol NAK: (NAK<crc><crc>\r
    q_nak = b"(NAK\x55\x66\r"
    cmd_type, payload = parse_inverter_response(q_nak)
    assert cmd_type == "N"
    assert payload == ""


# ---------------------------------------------------------------------------
# Telemetry Parsing Tests
# ---------------------------------------------------------------------------

def test_parse_gs_telemetry():
    """Verify parsing of 28-field GS telemetry response."""
    # Realistic P17 GS payload string
    # 0: Grid V (230.5V), 1: Grid Hz (50.0Hz), 2: Out V (230.1V), 3: Out Hz (50.0Hz)
    # 4: Apparent VA (1500), 5: Active W (1420), 6: Load % (28%)
    # 7: Bat V (53.2V), 8: Bat SCC V (53.2V), 9: Chg A (25A), 10: Dischg A (0A)
    # 12: SOC (85%), 13: Temp (38C), 16: PV1 W (2400W), 18: PV1 V (350.0V), 19: PV2 W (0W)
    gs_str = (
        "2305 500 2301 500 1500 1420 028 532 532 025 000 000 085 038 000 000 "
        "2400 000 3500 0000 00000001 0 0 0 0 0 0 0"
    )
    gs = parse_gs_telemetry(gs_str)
    assert gs.grid_voltage_v == 230.5
    assert gs.grid_freq_hz == 50.0
    assert gs.ac_output_voltage_v == 230.1
    assert gs.ac_output_active_power_w == 1420
    assert gs.ac_output_apparent_power_va == 1500
    assert gs.output_load_percent == 28
    assert gs.battery_voltage_v == 53.2
    assert gs.battery_charge_current_a == 25
    assert gs.battery_discharge_current_a == 0
    assert gs.battery_capacity_percent == 85
    assert gs.heatsink_temp_c == 38
    assert gs.pv1_power_w == 2400
    assert gs.pv1_voltage_v == 350.0
    assert gs.device_status == "00000001"


def test_parse_mod_telemetry():
    """Verify parsing of MOD working mode codes."""
    assert parse_mod_telemetry("L") == "Line / Grid Mode"
    assert parse_mod_telemetry("B") == "Battery Mode"
    assert parse_mod_telemetry("P") == "Power On Mode"
    assert parse_mod_telemetry("S") == "Standby Mode"
    assert parse_mod_telemetry("F") == "Fault Mode"
    assert parse_mod_telemetry("X") == "Unknown Mode (X)"


def test_parse_piri_telemetry():
    """Verify parsing of PIRI rated configuration fields."""
    # 0: In V (230.0), 1: In A (21.7), 2: Out V (230.0), 3: Out Hz (50.0), 4: Active W (5000)
    # 5: Bat V (48.0), 6: Recharge V (50.0), 7: Under V (42.0), 8: Bulk V (56.4), 9: Float V (54.0)
    # 11: Bat Type (3=Pylontech), 12: Max AC Chg (30A), 13: Max Chg (60A), 14: Input Range (0)
    # 15: Out Priority (1=SBU), 16: Chg Priority (1=Solar First)
    piri_str = (
        "2300 217 2300 500 5000 480 500 420 564 540 000 003 030 060 000 001 001 "
        "0 0 0 0 0 0 0 0 0"
    )
    piri = parse_piri_telemetry(piri_str)
    assert piri.ac_input_voltage_rating == 230.0
    assert piri.ac_output_active_power_rating == 5000
    assert piri.battery_voltage_rating == 48.0
    assert piri.battery_bulk_voltage == 56.4
    assert piri.battery_float_voltage == 54.0
    assert piri.battery_under_voltage == 42.0
    assert piri.battery_type == 3
    assert piri.battery_type_name == "Pylontech"
    assert piri.max_ac_charge_current == 30
    assert piri.max_charge_current == 60
    assert piri.output_source_priority == 1
    assert "SBU" in piri.output_source_priority_name
    assert piri.charger_source_priority == 1
    assert "Solar First" in piri.charger_source_priority_name


def test_parse_et_telemetry():
    """Verify parsing energy counters."""
    stats = parse_et_telemetry("12.5 3450.8")
    assert stats.day_energy_kwh == 12.5
    assert stats.total_energy_kwh == 3450.8


# ---------------------------------------------------------------------------
# Control Command Builders & Validation Tests
# ---------------------------------------------------------------------------

def test_command_builders_success_and_bounds():
    """Verify generation and range enforcement for all P17 control commands."""
    # Output priority: 0 (USB), 1 (SBU)
    assert build_output_priority_command(0) == "POP0"
    assert build_output_priority_command(1) == "POP1"
    with pytest.raises(ValueError):
        build_output_priority_command(2)

    # Charger priority: 0..3
    assert build_charger_priority_command(0) == "PSP0"
    assert build_charger_priority_command(3) == "PSP3"
    with pytest.raises(ValueError):
        build_charger_priority_command(4)

    # Max charge current
    assert build_max_charge_current_command(60) == "MCHGC0,060"
    with pytest.raises(ValueError):
        build_max_charge_current_command(200)

    # Max AC charge current
    assert build_max_ac_charge_current_command(30) == "MUCHGC0,030"
    with pytest.raises(ValueError):
        build_max_ac_charge_current_command(150)

    # Cut-off voltage: 42.0V -> PSDV420
    assert build_battery_cutoff_voltage_command(42.0) == "PSDV420"
    with pytest.raises(ValueError):
        build_battery_cutoff_voltage_command(35.0)

    # Bulk & float voltages: 56.4V, 54.0V -> MCHGV564,540
    assert build_battery_bulk_float_command(56.4, 54.0) == "MCHGV564,540"
    with pytest.raises(ValueError):
        build_battery_bulk_float_command(70.0, 54.0)

    # Recharge & redischarge: 50.0V, 54.0V -> BUCD500,540
    assert build_battery_recharge_redischarge_command(50.0, 54.0) == "BUCD500,540"
    with pytest.raises(ValueError):
        build_battery_recharge_redischarge_command(30.0, 54.0)


# ---------------------------------------------------------------------------
# Normalization & Client Simulation Tests
# ---------------------------------------------------------------------------

def test_normalize_smartess_telemetry():
    """Verify that normalized telemetry conforms to Solar Fleet EMS schema."""
    gs_str = (
        "2300 500 2300 500 1500 1350 027 534 534 020 000 000 090 035 000 000 "
        "2500 000 3400 0000 00000000 0 0 0 0 0 0 0"
    )
    piri_str = (
        "2300 217 2300 500 5000 480 500 420 564 540 000 003 030 060 000 001 001 "
        "0 0 0 0 0 0 0 0 0"
    )
    gs = parse_gs_telemetry(gs_str)
    mod = parse_mod_telemetry("L")
    piri = parse_piri_telemetry(piri_str)
    et = parse_et_telemetry("14.2 1250.0")

    ems = normalize_smartess_telemetry(gs, mod, piri, et, collector_pn="COLLECTOR-999", devaddr=1)

    assert ems["vendor"] == "SmartESS / Eybond"
    assert ems["protocol"] == "Eybond-Modbus-P17"
    assert ems["device_id"] == "smartess-COLLECTOR-999-addr1"
    assert ems["power_flow"]["solar_power_w"] == 2500.0
    assert ems["power_flow"]["load_power_w"] == 1350.0
    assert ems["battery"]["soc_percent"] == 90
    assert ems["battery"]["voltage_v"] == 53.4
    assert ems["battery"]["type"] == "Pylontech"
    assert ems["energy"]["today_kwh"] == 14.2


def test_smartess_client_simulation_and_safety_gates():
    """Verify SmartEssLocalClient polling, TID tracking, and safety gates."""
    client = SmartEssLocalClient(collector_pn="WIFI-DEMO-01", simulated=True)

    # 1. Telemetry Polling
    telemetry = client.poll_telemetry(devaddr=1)
    assert telemetry["collector_pn"] == "WIFI-DEMO-01"
    assert telemetry["battery"]["soc_percent"] == 88

    # 2. Safety Gate (Read-only by default)
    res_locked = client.execute_command_safely("output_priority", {"priority": 0}, unlocked=False)
    assert res_locked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # 3. Authorized Execution
    res_unlocked = client.execute_command_safely("output_priority", {"priority": 0}, unlocked=True)
    assert res_unlocked["status"] == "EXECUTED"
    assert res_unlocked["p17_command"] == "POP0"
    assert res_unlocked["readback_verified"] is True

    # 4. Verify Readback in Polled Telemetry
    updated = client.poll_telemetry(devaddr=1)
    assert "USB" in updated["configuration"]["output_source_priority"]


# ---------------------------------------------------------------------------
# Phase D REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_smartess_poll(local):
    """Verify POST /api/smartess/poll returns normalized EMS telemetry."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/smartess/poll",
        json={"collector_pn": "EYBOND-TEST-01", "devaddr": 1},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "ha-smartess-local" in data["source"]
    assert data["telemetry"]["collector_pn"] == "EYBOND-TEST-01"
    assert data["telemetry"]["vendor"] == "SmartESS / Eybond"
    assert data["telemetry"]["power_flow"]["solar_power_w"] > 0


def test_api_smartess_command_locked_and_unlocked(local):
    """Verify POST /api/smartess/command safety gating and execution."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # 1. Gated write without unlock
    resp_locked = client.post(
        "/api/smartess/command",
        json={
            "collector_pn": "EYBOND-TEST-01",
            "devaddr": 1,
            "command_type": "output_priority",
            "params": {"priority": 0},
            "unlocked": False,
        },
        headers=headers,
    )
    assert resp_locked.status_code == 200
    data_locked = resp_locked.json()
    assert data_locked["result"]["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # 2. Authorized write with unlock
    resp_unlocked = client.post(
        "/api/smartess/command",
        json={
            "collector_pn": "EYBOND-TEST-01",
            "devaddr": 1,
            "command_type": "output_priority",
            "params": {"priority": 0},
            "unlocked": True,
        },
        headers=headers,
    )
    assert resp_unlocked.status_code == 200
    data_unlocked = resp_unlocked.json()
    assert data_unlocked["result"]["status"] == "EXECUTED"
    assert data_unlocked["result"]["p17_command"] == "POP0"


def test_api_smartess_parse_frame(local):
    """Verify POST /api/smartess/parse-frame decodes raw Eybond Modbus frames."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # Encode a test heartbeat request frame
    dt = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)
    hb_frame = build_heartbeat_request(tid=55, interval=30, dt=dt)
    resp = client.post(
        "/api/smartess/parse-frame",
        json={"raw_frame_hex": hb_frame.hex()},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["frame"]["tid"] == 55
    assert data["frame"]["fc"] == FC_HEARTBEAT

