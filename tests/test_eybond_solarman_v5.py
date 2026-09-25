"""Tests for SOLARMAN V5 framing and Bluesun's unknown-protocol boundary."""

import struct

import pytest

from solar_fleet.adapters.bluesun import BluesunAdapter
from solar_fleet.adapters.eybond import (
    SolarmanV5Frame,
    calculate_v5_checksum,
    crc16_modbus,
)
from solar_fleet.domain import VendorError


def test_modbus_crc16_calculation():
    """Verify standard Modbus RTU CRC16 checksum."""
    data = b"123456789"
    crc = crc16_modbus(data)
    assert isinstance(crc, int)
    assert crc == 0x4B37  # CRC-16/MODBUS check vector


def test_solarman_v5_frame_encoding():
    """Verify encoding a Modbus read request inside Solarman V5 TCP frame."""
    logger_serial = 2712345678
    frame = SolarmanV5Frame.encode_read_holding_registers(
        logger_serial=logger_serial,
        slave_id=1,
        start_register=0x0100,
        quantity=10,
    )

    assert frame[0] == 0xA5  # Start byte
    assert frame[-1] == 0x15  # End byte
    assert len(frame) > 28

    # Verify logger serial embedded in header
    extracted_serial = struct.unpack("<I", frame[7:11])[0]
    assert extracted_serial == logger_serial

    # Verify checksum
    calc_checksum = calculate_v5_checksum(frame[:-2])
    assert frame[-2] == calc_checksum


def test_solarman_v5_frame_decoding():
    """Verify decoding a valid Solarman V5 frame with register values."""
    logger_serial = 2712345678
    # Construct a valid simulated response frame
    slave_id = 1
    func_code = 3
    # 2 registers: [1000, 250] -> 4 bytes
    reg_bytes = struct.pack(">HH", 1000, 250)
    mb_data = bytes([slave_id, func_code, len(reg_bytes)]) + reg_bytes
    mb_crc = crc16_modbus(mb_data)
    mb_payload = mb_data + struct.pack("<H", mb_crc)

    v5_inner = (
        struct.pack("<H", 0x1510)  # response control code
        + struct.pack("<H", 0x0001)
        + struct.pack("<I", logger_serial)
        + b"\x02\x00"
        + b"\x00" * 12
        + mb_payload
    )
    length = len(v5_inner) - 8
    frame_no_chk = bytes([0xA5]) + struct.pack("<H", length) + v5_inner
    chk = calculate_v5_checksum(frame_no_chk)
    valid_frame = frame_no_chk + bytes([chk, 0x15])

    result = SolarmanV5Frame.decode_response(
        valid_frame,
        expected_logger_serial=logger_serial,
        expected_slave_id=1,
        expected_sequence=1,
        expected_quantity=2,
    )
    for expected in (
        {"expected_logger_serial": 1},
        {"expected_slave_id": 2},
        {"expected_sequence": 2},
        {"expected_quantity": 3},
    ):
        with pytest.raises(VendorError, match="mismatch"):
            SolarmanV5Frame.decode_response(valid_frame, **expected)
    assert result["logger_serial"] == logger_serial
    assert result["slave_id"] == 1
    assert result["function_code"] == 3
    assert result["registers"] == [1000, 250]


def test_solarman_v5_corrupted_frame_rejection():
    """Verify corrupted frames or bad checksums are strictly rejected."""
    corrupted_frame = b"\xa5\x05\x00\x00\x00\x00\x00\x00\x00\x00\x00\x15"
    with pytest.raises(VendorError):
        SolarmanV5Frame.decode_response(corrupted_frame)


def test_bluesun_multi_oem_routing():
    for model in ("BSM-10K", "BSE15KH3", "BSE12KH3"):
        adapter = BluesunAdapter({"model_family": model}, {"logger_serial": 27001})
        assert adapter.resolve_oem() == "UNKNOWN_COMMISSIONING_REQUIRED"
        with pytest.raises(VendorError, match="exact_logger_protocol_required"):
            adapter.build_query(1, 260, 1)
        with pytest.raises(VendorError, match="uncommissioned_bluesun_model"):
            adapter.decode_registers(260, [6500])
