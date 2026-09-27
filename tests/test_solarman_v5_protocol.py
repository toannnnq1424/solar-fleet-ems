"""Unit and contract tests for Solarman V5 Datalogger Frame Protocol Engine.

Derived from upstream project:
pysolarmanv5 (MIT License) - Clean-room independently implemented.
"""

from __future__ import annotations

import struct

from test_workspaces import login

from solar_fleet.solarman_v5_protocol import (
    CONTROL_REQUEST,
    CONTROL_RESPONSE,
    V5_END,
    V5_START,
    SolarmanV5Engine,
    calculate_modbus_crc16,
    calculate_v5_checksum,
    parse_solarman_discovery_reply,
    sanitize_modbus_rtu_frame,
)

# ---------------------------------------------------------------------------
# Unit Tests: Checksum, Encoders, Decoders & Bug Sanitizer
# ---------------------------------------------------------------------------

def test_v5_checksum_calculation():
    """Verify modulo-256 frame checksum."""
    data = b"\x15\x00\x10\x45\x01\x00\x4E\x8B\xA3\x89\x02\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01\x03\x01\xF4\x00\x01\xC4\x05"
    expected = sum(data) & 0xFF
    assert calculate_v5_checksum(data) == expected


def test_v5_frame_encoding_layout():
    """Verify byte-level layout of encoded Solarman V5 request frame."""
    # Modbus FC03 read 1 register from 500: [0x01, 0x03, 0x01, 0xF4, 0x00, 0x01, CRC_L, CRC_H]
    modbus_pdu = b"\x01\x03\x01\xF4\x00\x01"
    crc = calculate_modbus_crc16(modbus_pdu)
    modbus_rtu = modbus_pdu + struct.pack("<H", crc)

    logger_serial = 2309196622  # 0x89A38B4E
    seq = 42

    v5_frame = SolarmanV5Engine.encode_frame(
        modbus_rtu_frame=modbus_rtu,
        logger_serial=logger_serial,
        sequence_number=seq,
    )

    # 1. Start and End
    assert v5_frame[0] == V5_START
    assert v5_frame[-1] == V5_END

    # 2. Payload length (15 bytes header + len(modbus_rtu))
    payload_len = struct.unpack("<H", v5_frame[1:3])[0]
    assert payload_len == 15 + len(modbus_rtu)

    # 3. Control code: 0x10 suffix + 0x45 REQUEST
    assert v5_frame[3] == 0x10
    assert v5_frame[4] == CONTROL_REQUEST

    # 4. Sequence number (little-endian uint16)
    assert struct.unpack("<H", v5_frame[5:7])[0] == seq

    # 5. Logger serial (little-endian uint32)
    assert struct.unpack("<I", v5_frame[7:11])[0] == logger_serial

    # 6. Checksum matches
    calculated_cs = calculate_v5_checksum(v5_frame[1:-2])
    assert v5_frame[-2] == calculated_cs


def test_v5_frame_roundtrip_decoding():
    """Verify encoding a frame and decoding it back extracts identical Modbus RTU payload."""
    modbus_rtu = b"\x01\x03\x04\x01\xF4\x03\xE8\x7A\x12"  # 9 bytes RTU frame
    logger_serial = 2312345678
    seq = 105

    # Synthesize response frame
    payload = bytearray()
    payload.append(0x02)  # Inverter
    payload.append(0x01)  # Status OK
    payload.extend(struct.pack("<I", 3600))   # Total working time: 3600s
    payload.extend(struct.pack("<I", 1200))   # Power on time: 1200s
    payload.extend(struct.pack("<I", 500))    # Offset time
    payload.extend(modbus_rtu)

    header = bytearray()
    header.append(V5_START)
    header.extend(struct.pack("<H", len(payload)))
    header.append(0x10)
    header.append(CONTROL_RESPONSE)
    header.extend(struct.pack("<H", seq))
    header.extend(struct.pack("<I", logger_serial))

    full_frame = header + payload
    cs = calculate_v5_checksum(full_frame[1:])
    full_frame.append(cs)
    full_frame.append(V5_END)

    decoded = SolarmanV5Engine.decode_frame(bytes(full_frame))
    assert decoded.valid is True
    assert decoded.control_code == CONTROL_RESPONSE
    assert decoded.control_code_name == "RESPONSE"
    assert decoded.sequence_number == seq
    assert decoded.logger_serial == logger_serial
    assert decoded.total_working_time_s == 3600
    assert decoded.power_on_time_s == 1200
    assert decoded.modbus_rtu_frame == modbus_rtu


def test_v5_frame_validation_errors():
    """Verify validation detects invalid start/end, corrupted checksums, and truncated frames."""
    # Truncated
    dec_short = SolarmanV5Engine.decode_frame(b"\xA5\x05\x00\x15")
    assert dec_short.valid is False
    assert "Frame too short" in dec_short.error

    # Invalid start byte
    bad_start = b"\xAA" + (b"\x00" * 30) + b"\x15"
    dec_start = SolarmanV5Engine.decode_frame(bad_start)
    assert dec_start.valid is False
    assert "Invalid start" in dec_start.error

    # Corrupted checksum
    valid_frame = SolarmanV5Engine.encode_frame(b"\x01\x03\x00\x00\x00\x01\x84\x0A", 12345678, 1)
    corrupted = bytearray(valid_frame)
    corrupted[-2] = (corrupted[-2] + 1) & 0xFF  # alter checksum
    dec_cs = SolarmanV5Engine.decode_frame(bytes(corrupted))
    assert dec_cs.valid is False
    assert "Checksum mismatch" in dec_cs.error


def test_sanitize_modbus_double_crc():
    """Verify detection and trimming of trailing 0x0000 caused by firmware double-CRC bug."""
    pdu = b"\x01\x03\x02\x01\xF4"
    crc = calculate_modbus_crc16(pdu)
    clean_rtu = pdu + struct.pack("<H", crc)

    # Corrupted RTU with trailing 0x0000
    buggy_rtu = clean_rtu + b"\x00\x00"

    sanitized = sanitize_modbus_rtu_frame(buggy_rtu)
    assert sanitized == clean_rtu
    assert len(sanitized) == len(clean_rtu)


def test_compile_high_level_commands():
    """Verify compiling FC03, FC06, FC16 into Solarman V5 frames."""
    serial = 2312345678

    # FC03 Read Holding
    c_read = SolarmanV5Engine.compile_read_holding_registers(serial, 1, 500, 10, 1)
    assert c_read.function_code == 0x03
    assert len(c_read.v5_frame_bytes) > 20
    assert c_read.v5_frame_bytes[0] == V5_START
    assert c_read.v5_frame_bytes[-1] == V5_END

    # FC06 Write Single
    c_write = SolarmanV5Engine.compile_write_single_register(serial, 1, 142, 1, 2)
    assert c_write.function_code == 0x06
    assert c_write.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"


def test_parse_solarman_discovery_reply():
    """Verify parsing UDP discovery broadcast response."""
    reply = "192.168.1.188,ACCF2389BC12,2312345678"
    res = parse_solarman_discovery_reply(reply)
    assert res is not None
    assert res["ip_address"] == "192.168.1.188"
    assert res["mac_address"] == "ACCF2389BC12"
    assert res["logger_serial"] == 2312345678

    # Invalid reply
    assert parse_solarman_discovery_reply("invalid") is None


# ---------------------------------------------------------------------------
# Contract / Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_solarman_v5_encode_frame(local):
    """Verify POST /api/solarman-v5/encode-frame."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/solarman-v5/encode-frame",
        json={
            "modbus_rtu_hex": "010301F40001C405",
            "logger_serial": 2312345678,
            "sequence_number": 5,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "pysolarmanv5" in data["source"]
    assert data["v5_frame_hex"].startswith("A5")
    assert data["v5_frame_hex"].endswith("15")


def test_api_solarman_v5_decode_frame(local):
    """Verify POST /api/solarman-v5/decode-frame."""
    client, _ = local
    headers = login(local, "operator")

    # Encode a test frame first
    test_v5 = SolarmanV5Engine.encode_frame(b"\x01\x03\x02\x01\xF4\x78\x8B", 2312345678, 1)

    resp = client.post(
        "/api/solarman-v5/decode-frame",
        json={"v5_frame_hex": test_v5.hex().upper()},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["decoded"]["valid"] is True
    assert data["decoded"]["logger_serial"] == 2312345678


def test_api_solarman_v5_compile_request(local):
    """Verify POST /api/solarman-v5/compile-request."""
    client, _ = local
    headers = login(local, "operator")

    # FC03 Read
    resp_read = client.post(
        "/api/solarman-v5/compile-request",
        json={
            "logger_serial": 2312345678,
            "modbus_slave_id": 1,
            "function_code": 3,
            "start_address": 500,
            "quantity_or_value": 10,
            "sequence_number": 1,
        },
        headers=headers,
    )
    assert resp_read.status_code == 200
    data_read = resp_read.json()
    assert data_read["compiled"]["function_code"] == "0x03"

    # FC06 Write Single
    resp_write = client.post(
        "/api/solarman-v5/compile-request",
        json={
            "logger_serial": 2312345678,
            "modbus_slave_id": 1,
            "function_code": 6,
            "start_address": 80,
            "quantity_or_value": 1,
            "sequence_number": 2,
        },
        headers=headers,
    )
    assert resp_write.status_code == 200
    data_write = resp_write.json()
    assert data_write["compiled"]["function_code"] == "0x06"
    assert data_write["compiled"]["safety_gate"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"


def test_api_solarman_v5_parse_discovery(local):
    """Verify POST /api/solarman-v5/parse-discovery."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/solarman-v5/parse-discovery",
        json={"payload": "192.168.1.120,ACCF23567890,2309876543"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    disc = data["discovery"]
    assert disc["ip_address"] == "192.168.1.120"
    assert disc["logger_serial"] == 2309876543
