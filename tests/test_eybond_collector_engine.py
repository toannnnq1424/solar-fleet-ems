"""Unit and contract tests for Eybond ESP Collector Engine and Voltronic PI30.

Validates:
- Eybond Modbus binary header encoding and decoding
- CRC16-XMODEM calculation and byte-stuffing escape rules
- UDP Port 58899 discovery request parsing and response generation
- Synthetic serial number generation from MAC address
- AT command parser and reply generation
- Voltronic QPIGS telemetry parsing and normalization to EMS schema
- QMOD and QPIWS warning matrix decoding
- Voltronic parameter compilers (POP, PCP, MCHGC, voltages) and safety gates
- VirtualEybondCollector simulation
"""

from __future__ import annotations

import pytest

from solar_fleet.eybond_collector_engine import (
    FC_FORWARD_TO_DEVICE,
    VirtualEybondCollector,
    build_eybond_frame,
    build_udp_discovery_reply,
    build_voltronic_frame,
    compile_voltronic_charger_priority,
    compile_voltronic_charging_current,
    compile_voltronic_output_priority,
    compile_voltronic_voltage_settings,
    crc16_xmodem,
    decode_eybond_header,
    decode_qpiws_warnings,
    encode_eybond_header,
    escape_crc_byte,
    handle_at_command,
    normalize_eybond_pi30_telemetry,
    parse_at_command,
    parse_qpigs_response,
    parse_udp_discovery_redirect,
    synthesize_collector_pn,
    verify_and_strip_voltronic_response,
)


def test_eybond_frame_header_codec():
    """Verify 8-byte big-endian frame header encoding and decoding."""
    tid = 0x1234
    devcode = 0x0994
    total_len = 18  # 8 header + 10 payload -> wire_len = 12
    devaddr = 0x01
    fc = FC_FORWARD_TO_DEVICE

    hdr_bytes = encode_eybond_header(tid, devcode, total_len, devaddr, fc)
    assert len(hdr_bytes) == 8

    decoded = decode_eybond_header(hdr_bytes)
    assert decoded.tid == tid
    assert decoded.devcode == devcode
    assert decoded.wire_len == 12
    assert decoded.total_len == 18
    assert decoded.payload_len == 10
    assert decoded.devaddr == devaddr
    assert decoded.fc == fc

    # Build full frame with payload
    payload = b"QPIGS\r"
    full_frame = build_eybond_frame(tid, devcode, devaddr, fc, payload)
    assert len(full_frame) == 8 + len(payload)
    assert full_frame[:8] == encode_eybond_header(tid, devcode, 8 + len(payload), devaddr, fc)
    assert full_frame[8:] == payload


def test_crc16_xmodem_and_voltronic_framing():
    """Verify CRC16-XMODEM calculation and escape byte-stuffing."""
    # Test vector: 'QPI'
    cmd = "QPI"
    crc = crc16_xmodem(cmd.encode("ascii"))
    assert isinstance(crc, int)
    assert 0 <= crc <= 0xFFFF

    # Escape bytes: 0x28 '(', 0x0D '\r', 0x0A '\n' must increment by 1
    assert escape_crc_byte(0x28) == 0x29
    assert escape_crc_byte(0x0D) == 0x0E
    assert escape_crc_byte(0x0A) == 0x0B
    assert escape_crc_byte(0x40) == 0x40

    # Build frame
    frame = build_voltronic_frame(cmd)
    assert frame.startswith(b"QPI")
    assert frame.endswith(b"\r")
    assert len(frame) == len(cmd) + 3

    # Simulated valid response
    resp_body = b"(PI30"
    resp_crc = crc16_xmodem(resp_body)
    hi = escape_crc_byte((resp_crc >> 8) & 0xFF)
    lo = escape_crc_byte(resp_crc & 0xFF)
    raw_resp = resp_body + bytes([hi, lo, 0x0D])

    valid, text = verify_and_strip_voltronic_response(raw_resp)
    assert valid is True
    assert text == "PI30"

    # Invalid CRC or malformed frame
    invalid_resp = b"(PI30\x00\x00\r"
    valid_inv, _ = verify_and_strip_voltronic_response(invalid_resp)
    assert valid_inv is False


def test_udp_discovery_and_pn_synthesis():
    """Verify UDP Port 58899 discovery parsing and synthetic PN generation."""
    # 1. Valid discovery packet
    raw = b"set>server=192.168.1.150:8899;\r\n"
    res = parse_udp_discovery_redirect(raw)
    assert res is not None
    host, port = res
    assert host == "192.168.1.150"
    assert port == 8899

    # Reply
    reply = build_udp_discovery_reply()
    assert reply == b"rsp>server=2;"

    # 2. Malformed packet
    assert parse_udp_discovery_redirect(b"get>server;") is None
    assert parse_udp_discovery_redirect(b"set>server=192.168.1.1:99999;") is None

    # 3. Synthetic PN from MAC
    mac = bytes([0x24, 0x6F, 0x28, 0x11, 0x22, 0x33])
    pn = synthesize_collector_pn(mac)
    assert pn.startswith("V00")
    assert len(pn) == 18
    assert pn[3:].isdigit()


def test_at_command_parser_and_handler():
    """Verify AT command parser and response generation."""
    # 1. Query command
    p_query = parse_at_command("AT+DTUPN?\r\n")
    assert p_query == ("DTUPN", False, "")

    resp_pn = handle_at_command("DTUPN", False, "", profile_pn="V00123456789012345")
    assert resp_pn == "AT+DTUPN:V00123456789012345\r\n"

    # 2. Firmware version & UART query
    assert handle_at_command("FWVER", False, "") == "AT+FWVER:0.1.10\r\n"
    assert handle_at_command("UART", False, "", uart_cfg="9600,8,1,NONE") == "AT+UART:9600,8,1,NONE\r\n"
    assert handle_at_command("LINK", False, "") == "AT+LINK:connected\r\n"

    # 3. Write command
    p_write = parse_at_command("AT+UART=2400,8,1,NONE\r\n")
    assert p_write == ("UART", True, "2400,8,1,NONE")
    assert handle_at_command("UART", True, "2400,8,1,NONE") == "AT+UART:W000\r\n"


def test_qpigs_parsing_and_normalization():
    """Verify Voltronic QPIGS response parsing and EMS schema normalization."""
    # Synthetic QPIGS vector from real Axpert VMII inverter
    raw_qpigs = "239.5 49.9 239.5 49.9 0927 0924 015 396 53.20 000 100 0028 002.2 315.9 00.00 00000 00010000 00 00 00665 000"
    tel = parse_qpigs_response(raw_qpigs)
    assert tel.grid_voltage_v == 239.5
    assert tel.grid_frequency_hz == 49.9
    assert tel.ac_output_voltage_v == 239.5
    assert tel.ac_output_active_power_w == 924.0
    assert tel.output_load_percent == 15
    assert tel.bus_voltage_v == 396.0
    assert tel.battery_voltage_v == 53.2
    assert tel.battery_capacity_percent == 100
    assert tel.pv_input_voltage_v == 315.9
    assert tel.pv_power_w == 665.0

    # Test QPIWS warning decoder
    qpiws_raw = "00000100000000000000000000000000"  # Bit 5: LineFail
    alarms = decode_qpiws_warnings(qpiws_raw)
    assert len(alarms) == 1
    assert alarms[0]["code"] == "LineFail"
    assert alarms[0]["severity"] == "WARNING"

    # Normalize to Solar Fleet EMS
    ems = normalize_eybond_pi30_telemetry(
        collector_pn="V00123456789012345",
        inverter_sn="553555355535552",
        qpigs=tel,
        mode_char="L",
        qpiws_flags=qpiws_raw,
        model_name="Axpert VMII 5KW",
    )
    assert ems["vendor"] == "Voltronic / Eybond ESP"
    assert ems["protocol"] == "PI30 over Eybond Modbus Bridge"
    assert ems["operating_mode"] == "Line / Utility Mode"
    assert ems["power_flow"]["solar_power_w"] == 665.0
    assert ems["power_flow"]["load_power_w"] == 924.0
    assert ems["battery"]["soc_percent"] == 100
    assert ems["diagnostics"]["active_warnings_count"] == 1


def test_voltronic_control_compilers():
    """Verify parameter compilers for Output Priority, Charger Priority, and Voltages."""
    # 1. Output priority
    cmd_pop = compile_voltronic_output_priority("solar_first")
    assert cmd_pop["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_pop["command"] == "POP01"
    assert "frame_hex" in cmd_pop

    with pytest.raises(ValueError):
        compile_voltronic_output_priority("invalid_mode")

    # 2. Charger priority
    cmd_pcp = compile_voltronic_charger_priority("solar_only")
    assert cmd_pcp["command"] == "PCP03"

    # 3. Charging current
    cmd_a = compile_voltronic_charging_current(60)
    assert cmd_a["command"] == "MCHGC060"

    with pytest.raises(ValueError):
        compile_voltronic_charging_current(150)

    # 4. Battery voltages
    cmd_v = compile_voltronic_voltage_settings(
        bulk_voltage=56.4,
        float_voltage=54.0,
        cutoff_voltage=42.0,
    )
    assert cmd_v["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert "PCVV56.4" in cmd_v["commands"]
    assert "PBFT54.0" in cmd_v["commands"]
    assert "PSDV42.0" in cmd_v["commands"]


def test_virtual_eybond_collector_simulation():
    """Verify VirtualEybondCollector simulator."""
    sim = VirtualEybondCollector(firmware_ver="0.1.10", uart_cfg="2400,8,1,NONE")
    assert sim.pn.startswith("V00")

    # UDP Discovery
    udp_reply = sim.handle_udp_packet(b"set>server=10.0.0.50:8899;")
    assert udp_reply == b"rsp>server=2;"
    assert sim.server_host == "10.0.0.50"
    assert sim.server_port == 8899

    # AT Command
    at_res = sim.execute_at("AT+FWVER?\r\n")
    assert at_res == "AT+FWVER:0.1.10\r\n"

    # Gated command: locked by default
    res_locked = sim.execute_command_safely("output_priority", {"priority": "sbu"}, unlocked=False)
    assert res_locked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # Unlocked command
    res_unlocked = sim.execute_command_safely("output_priority", {"priority": "sbu"}, unlocked=True)
    assert res_unlocked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res_unlocked["command"] == "POP02"


def test_api_eybond_collector_discover(local):
    """Verify POST /api/eybond-collector/discover."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/eybond-collector/discover",
        json={"raw_udp_text": "set>server=192.168.1.200:8899;"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "esp-eybond-collector (MPL-2.0 clean-room independent)"
    assert data["server_host"] == "192.168.1.200"
    assert data["server_port"] == 8899
    assert data["udp_reply"] == "rsp>server=2;"


def test_api_eybond_collector_parse_at(local):
    """Verify POST /api/eybond-collector/parse-at."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/eybond-collector/parse-at",
        json={"at_line": "AT+DTUPN?", "profile_pn": "V00999888777666555"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["command"] == "DTUPN"
    assert "V00999888777666555" in data["response"]


def test_api_eybond_collector_decode_pigs(local):
    """Verify POST /api/eybond-collector/decode-pigs."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/eybond-collector/decode-pigs",
        json={
            "raw_qpigs": "230.0 50.0 230.0 50.0 1200 1150 025 400 52.8 010 095 0035 005.0 320.0 00.00 00000 00010000 00 00 01600 000",
            "mode_char": "L",
            "qpiws_flags": "0" * 32,
            "collector_pn": "V00123456789012345",
            "inverter_sn": "INV-VOLT-8801",
        },
        headers=headers,
    )
    assert resp.status_code == 200
    tel = resp.json()["telemetry"]
    assert tel["vendor"] == "Voltronic / Eybond ESP"
    assert tel["serial_number"] == "INV-VOLT-8801"
    assert tel["power_flow"]["solar_power_w"] == 1600.0
    assert tel["battery"]["soc_percent"] == 95


def test_api_eybond_collector_command(local):
    """Verify POST /api/eybond-collector/command with safety gate."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # 1. Locked command
    resp_locked = client.post(
        "/api/eybond-collector/command",
        json={
            "command_type": "output_priority",
            "params": {"priority": "sbu"},
            "unlocked": False,
        },
        headers=headers,
    )
    assert resp_locked.status_code == 200
    res_data = resp_locked.json()["result"]
    assert res_data["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # 2. Unlocked command compiles correctly
    resp_unlocked = client.post(
        "/api/eybond-collector/command",
        json={
            "command_type": "output_priority",
            "params": {"priority": "sbu"},
            "unlocked": True,
        },
        headers=headers,
    )
    assert resp_unlocked.status_code == 200
    res_unlocked_data = resp_unlocked.json()["result"]
    assert res_unlocked_data["command"] == "POP02"

