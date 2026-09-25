"""Framing for explicitly identified SOLARMAN V5 loggers; not an Eybond protocol."""

from __future__ import annotations

import struct
from typing import Any

from ..domain import VendorError


def crc16_modbus(data: bytes) -> int:
    """Standard Modbus RTU CRC16 calculation."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def calculate_v5_checksum(frame_bytes: bytes) -> int:
    """Solarman V5 frame checksum: sum of bytes from index 1 to end-2 mod 256."""
    return sum(frame_bytes[1:]) & 0xFF


class SolarmanV5Frame:
    """Solarman V5 frame builder and parser for confirmed SOLARMAN V5 loggers."""

    START_BYTE = 0xA5
    END_BYTE = 0x15
    CONTROL_CODE_READ = 0x4510  # Little endian 0x1045

    @classmethod
    def encode_read_holding_registers(
        cls,
        logger_serial: int,
        slave_id: int,
        start_register: int,
        quantity: int,
    ) -> bytes:
        """Encode a Modbus RTU read request inside a Solarman V5 TCP frame."""
        if (
            not 1 <= logger_serial <= 0xFFFFFFFF
            or not 1 <= slave_id <= 247
            or not 1 <= quantity <= 125
            or not 0 <= start_register <= 65535
            or start_register + quantity > 65536
        ):
            raise VendorError("invalid_modbus_read_range")
        # Modbus RTU payload: [slave_id, 0x03, start_reg_high, start_reg_low, qty_high, qty_low] + CRC16
        mb_request = struct.pack(">BBHH", slave_id, 0x03, start_register, quantity)
        mb_crc = crc16_modbus(mb_request)
        mb_payload = mb_request + struct.pack("<H", mb_crc)

        # Solarman V5 header & payload
        # Header:
        # byte 0: 0xA5
        # byte 1-2: payload length (little endian)
        # byte 3-4: control code (0x4510)
        # byte 5-6: sequence number (0x0000)
        # byte 7-10: logger serial number (little endian uint32)
        # byte 11: frame type (0x02)
        # byte 12-13: sensor type (0x0000)
        # byte 14-25: delivery timestamps (all 0)
        v5_inner = (
            struct.pack("<H", cls.CONTROL_CODE_READ)
            + struct.pack("<H", 0x0001)  # sequence
            + struct.pack("<I", logger_serial)
            + b"\x02\x00\x00"  # frame type + sensor type
            + b"\x00" * 12  # timestamps
            + mb_payload
        )
        length = len(v5_inner) - 8
        frame_without_checksum = bytes([cls.START_BYTE]) + struct.pack("<H", length) + v5_inner
        checksum = calculate_v5_checksum(frame_without_checksum)
        return frame_without_checksum + bytes([checksum, cls.END_BYTE])

    @classmethod
    def decode_response(
        cls,
        raw: bytes,
        *,
        expected_logger_serial=None,
        expected_slave_id=None,
        expected_sequence=None,
        expected_quantity=None,
    ) -> dict[str, Any]:
        """Decode and validate a Solarman V5 frame and extract Modbus RTU payload."""
        if len(raw) < 32:
            raise VendorError("frame_too_short")
        if raw[0] != cls.START_BYTE:
            raise VendorError("invalid_start_byte")
        if raw[-1] != cls.END_BYTE:
            raise VendorError("invalid_end_byte")

        length = struct.unpack("<H", raw[1:3])[0]
        expected_len = length + 13  # start (1) + length (2) + payload (length) + checksum (1) + end (1)
        if len(raw) != expected_len:
            raise VendorError("frame_length_mismatch")

        # Validate checksum
        checksum = calculate_v5_checksum(raw[:-2])
        if checksum != raw[-2]:
            raise VendorError("invalid_frame_checksum")

        if raw[3:5] != b"\x10\x15" or raw[11] != 2:
            raise VendorError("unexpected_v5_response_type")
        # Extract logger serial
        serial = struct.unpack("<I", raw[7:11])[0]
        if expected_logger_serial is not None and serial != expected_logger_serial:
            raise VendorError("logger_response_mismatch")
        if expected_sequence is not None and raw[5] != expected_sequence:
            raise VendorError("sequence_response_mismatch")

        # Response ADU starts at 25, unlike the request ADU at 26.
        mb_payload = raw[25:-2]
        if len(mb_payload) < 5:
            raise VendorError("modbus_payload_too_short")

        # Validate Modbus CRC
        mb_data, mb_crc = mb_payload[:-2], struct.unpack("<H", mb_payload[-2:])[0]
        if crc16_modbus(mb_data) != mb_crc:
            raise VendorError("invalid_modbus_crc")

        slave_id = mb_data[0]
        if expected_slave_id is not None and slave_id != expected_slave_id:
            raise VendorError("slave_response_mismatch")
        function_code = mb_data[1]
        if function_code & 0x80:
            raise VendorError("modbus_exception_response")
        if function_code != 3 or not 1 <= slave_id <= 247:
            raise VendorError("unexpected_modbus_response")
        byte_count = mb_data[2]
        if byte_count == 0 or byte_count % 2 or len(mb_data) != byte_count + 3:
            raise VendorError("modbus_byte_count_mismatch")
        register_bytes = mb_data[3 : 3 + byte_count]
        if expected_quantity is not None and byte_count != expected_quantity * 2:
            raise VendorError("quantity_response_mismatch")

        # Parse 16-bit big endian registers
        registers = []
        for i in range(0, len(register_bytes), 2):
            registers.append(struct.unpack(">H", register_bytes[i : i + 2])[0])

        return {
            "logger_serial": serial,
            "slave_id": slave_id,
            "function_code": function_code,
            "registers": registers,
        }
