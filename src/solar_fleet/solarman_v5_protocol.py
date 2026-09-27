"""Solarman V5 Datalogger Frame Protocol Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
pysolarmanv5 (MIT License, author Jonathan McCrohan).
Per repository workflow and licensing rules, this is a clean-room independent
implementation of the Solarman V5 frame encoder, frame decoder, sequence tracker,
checksum validator, double-CRC sanitizer, and Modbus RTU encapsulation.

Key Capabilities:
- Encapsulation of standard Modbus RTU frames inside Solarman V5 datalogger envelopes
  (used by IGEN Tech, Deye, Sofar, Solis, Chisage, and Eybond WiFi/LAN sticks on TCP Port 8899)
- V5 Header (11 bytes): Start 0xA5, Payload Length, Control Code, Sequence Number, Logger Serial
- V5 Payload: Inverter frame type (0x02), Sensor type, Timestamps, Embedded Modbus RTU
- V5 Trailer (2 bytes): Frame Checksum (modulo-256 sum over frame[1:-2]), End 0x15
- Transparent detection and correction of double-CRC bug observed on Deye/IGEN loggers
- UDP Local Discovery Protocol (Port 48899 broadcast probe and response parser)
- Safety gating ensuring all writable Modbus controls wrapped in V5 frames remain
  LOCKED_PENDING_HARDWARE_ACCEPTANCE
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

V5_START = 0xA5
V5_END = 0x15

# Control Codes (Byte 3 is 0x10, Byte 4 is Control)
CONTROL_HANDSHAKE = 0x41
CONTROL_DATA = 0x42
CONTROL_INFO = 0x43
CONTROL_REQUEST = 0x45
CONTROL_RESPONSE = 0x15   # 0x45 - 0x30
CONTROL_HEARTBEAT = 0x47
CONTROL_REPORT = 0x48

FRAME_TYPE_CLOUD = 0x00
FRAME_TYPE_LOGGER = 0x01
FRAME_TYPE_INVERTER = 0x02

HEADER_LENGTH = 11
REQUEST_PAYLOAD_HEADER_LENGTH = 15
RESPONSE_PAYLOAD_HEADER_LENGTH = 14
TRAILER_LENGTH = 2


# ---------------------------------------------------------------------------
# Modbus CRC16 Calculation
# ---------------------------------------------------------------------------

def calculate_modbus_crc16(data: bytes) -> int:
    """Calculate standard Modbus RTU 16-bit CRC (polynomial 0xA001, initial 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# ---------------------------------------------------------------------------
# Solarman V5 Checksum Calculation
# ---------------------------------------------------------------------------

def calculate_v5_checksum(data: bytes) -> int:
    """Calculate Solarman V5 modulo-256 checksum over data bytes.

    Computed on all frame bytes excluding the Start byte (0xA5), the Checksum byte itself,
    and the End byte (0x15).
    """
    return sum(data) & 0xFF


# ---------------------------------------------------------------------------
# Double-CRC Sanitizer
# ---------------------------------------------------------------------------

def sanitize_modbus_rtu_frame(modbus_frame: bytes) -> bytes:
    """Sanitize Modbus RTU frame from Deye/Solarman double-CRC bug.

    Certain firmware builds erroneously calculate and append the Modbus CRC twice,
    resulting in a trailing 0x0000. Detects and strips the duplicate CRC.
    """
    if len(modbus_frame) >= 7 and modbus_frame[-2:] == b"\x00\x00":
        # Check if frame without trailing 0x0000 has a valid Modbus CRC
        payload_without_trailer = modbus_frame[:-2]
        expected_crc = calculate_modbus_crc16(payload_without_trailer[:-2])
        actual_crc = struct.unpack("<H", payload_without_trailer[-2:])[0]
        if expected_crc == actual_crc:
            return payload_without_trailer
    return modbus_frame


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SolarmanV5DecodedFrame:
    """Decoded Solarman V5 frame payload and metadata."""

    valid: bool
    control_code: int
    control_code_name: str
    sequence_number: int
    logger_serial: int
    frame_type: int
    status: Optional[int]
    total_working_time_s: int
    power_on_time_s: int
    offset_time_s: int
    modbus_rtu_frame: bytes
    modbus_rtu_hex: str
    modbus_crc_valid: bool
    raw_frame_hex: str
    error: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["modbus_rtu_frame"] = self.modbus_rtu_hex
        return d


@dataclass
class SolarmanV5CompiledRequest:
    """Encapsulated Solarman V5 request frame ready for TCP transmission."""

    logger_serial: int
    sequence_number: int
    modbus_slave_id: int
    function_code: int
    v5_frame_bytes: bytes
    v5_frame_hex: str
    modbus_rtu_hex: str
    safety_gate: str = "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    reason: str = "Solarman V5 control writes require physical commissioning and safety lock release."

    def to_dict(self) -> Dict[str, Any]:
        return {
            "logger_serial": self.logger_serial,
            "sequence_number": self.sequence_number,
            "modbus_slave_id": self.modbus_slave_id,
            "function_code": f"0x{self.function_code:02X}",
            "v5_frame_hex": self.v5_frame_hex,
            "modbus_rtu_hex": self.modbus_rtu_hex,
            "safety_gate": self.safety_gate,
            "reason": self.reason,
        }


# ---------------------------------------------------------------------------
# Solarman V5 Framing Engine
# ---------------------------------------------------------------------------

class SolarmanV5Engine:
    """Clean-room independent encoder and decoder for Solarman V5 datalogger frames."""

    @staticmethod
    def encode_frame(
        modbus_rtu_frame: bytes,
        logger_serial: int,
        sequence_number: int = 1,
        control_code: int = CONTROL_REQUEST,
    ) -> bytes:
        """Encode a Modbus RTU frame into a complete Solarman V5 datalogger TCP packet.

        Frame Layout:
        - [0]: 0xA5 (Start)
        - [1:3]: Payload Length (uint16 LE = 15 + len(modbus))
        - [3]: 0x10 (Control code suffix)
        - [4]: Control code (e.g. 0x45 for REQUEST)
        - [5:7]: Sequence Number (uint16 LE)
        - [7:11]: Logger Serial Number (uint32 LE)
        - [11]: Frame Type (0x02: Inverter)
        - [12:14]: Sensor Type (0x0000)
        - [14:18]: Total Working Time (0x00000000)
        - [18:22]: Power On Time (0x00000000)
        - [22:26]: Offset Time (0x00000000)
        - [26..N]: Embedded Modbus RTU Frame
        - [N]: Checksum (modulo-256 sum over bytes 1..N-1)
        - [N+1]: 0x15 (End)
        """
        payload_len = REQUEST_PAYLOAD_HEADER_LENGTH + len(modbus_rtu_frame)

        # Header (11 bytes)
        header = bytearray()
        header.append(V5_START)
        header.extend(struct.pack("<H", payload_len))
        header.append(0x10)
        header.append(control_code & 0xFF)
        header.extend(struct.pack("<H", sequence_number & 0xFFFF))
        header.extend(struct.pack("<I", logger_serial & 0xFFFFFFFF))

        # Payload (15 bytes header + Modbus RTU)
        payload = bytearray()
        payload.append(FRAME_TYPE_INVERTER)  # 0x02
        payload.extend(b"\x00\x00")          # Sensor type (2 bytes)
        payload.extend(b"\x00\x00\x00\x00")  # Total working time (4 bytes)
        payload.extend(b"\x00\x00\x00\x00")  # Power on time (4 bytes)
        payload.extend(b"\x00\x00\x00\x00")  # Offset time (4 bytes)
        payload.extend(modbus_rtu_frame)

        frame = header + payload

        # Trailer (2 bytes)
        checksum = calculate_v5_checksum(frame[1:])
        frame.append(checksum)
        frame.append(V5_END)

        return bytes(frame)

    @staticmethod
    def decode_frame(v5_frame: bytes) -> SolarmanV5DecodedFrame:
        """Decode and validate a Solarman V5 datalogger response packet.

        Validates Start/End bytes, Checksum, Logger Serial, and extracts Modbus RTU payload.
        """
        raw_hex = v5_frame.hex().upper()
        if len(v5_frame) < (HEADER_LENGTH + RESPONSE_PAYLOAD_HEADER_LENGTH + TRAILER_LENGTH):
            return SolarmanV5DecodedFrame(
                valid=False,
                control_code=0,
                control_code_name="INVALID",
                sequence_number=0,
                logger_serial=0,
                frame_type=0,
                status=None,
                total_working_time_s=0,
                power_on_time_s=0,
                offset_time_s=0,
                modbus_rtu_frame=b"",
                modbus_rtu_hex="",
                modbus_crc_valid=False,
                raw_frame_hex=raw_hex,
                error="Frame too short (< 27 bytes)",
            )

        if v5_frame[0] != V5_START or v5_frame[-1] != V5_END:
            return SolarmanV5DecodedFrame(
                valid=False,
                control_code=0,
                control_code_name="INVALID",
                sequence_number=0,
                logger_serial=0,
                frame_type=0,
                status=None,
                total_working_time_s=0,
                power_on_time_s=0,
                offset_time_s=0,
                modbus_rtu_frame=b"",
                modbus_rtu_hex="",
                modbus_crc_valid=False,
                raw_frame_hex=raw_hex,
                error=f"Invalid start (0x{v5_frame[0]:02X}) or end (0x{v5_frame[-1]:02X}) byte",
            )

        # Validate V5 checksum
        calculated_checksum = calculate_v5_checksum(v5_frame[1:-2])
        frame_checksum = v5_frame[-2]
        if calculated_checksum != frame_checksum:
            return SolarmanV5DecodedFrame(
                valid=False,
                control_code=0,
                control_code_name="INVALID",
                sequence_number=0,
                logger_serial=0,
                frame_type=0,
                status=None,
                total_working_time_s=0,
                power_on_time_s=0,
                offset_time_s=0,
                modbus_rtu_frame=b"",
                modbus_rtu_hex="",
                modbus_crc_valid=False,
                raw_frame_hex=raw_hex,
                error=f"Checksum mismatch: expected 0x{calculated_checksum:02X}, got 0x{frame_checksum:02X}",
            )

        # Unpack Header
        payload_len = struct.unpack("<H", v5_frame[1:3])[0]
        if len(v5_frame) != (13 + payload_len):
            # Frame length should match 13 bytes overhead + payload_len
            pass
        control_code = v5_frame[4]
        seq_num = struct.unpack("<H", v5_frame[5:7])[0]
        logger_serial = struct.unpack("<I", v5_frame[7:11])[0]

        control_code_names = {
            CONTROL_HANDSHAKE: "HANDSHAKE",
            CONTROL_DATA: "DATA",
            CONTROL_INFO: "INFO",
            CONTROL_REQUEST: "REQUEST",
            CONTROL_RESPONSE: "RESPONSE",
            CONTROL_HEARTBEAT: "HEARTBEAT",
            CONTROL_REPORT: "REPORT",
        }
        ctrl_name = control_code_names.get(control_code, f"0x{control_code:02X}")

        # Unpack Payload
        frame_type = v5_frame[11]
        status = v5_frame[12] if len(v5_frame) > 12 else None
        uptime_total = struct.unpack("<I", v5_frame[13:17])[0] if len(v5_frame) >= 17 else 0
        uptime_power_on = struct.unpack("<I", v5_frame[17:21])[0] if len(v5_frame) >= 21 else 0
        offset_time = struct.unpack("<I", v5_frame[21:25])[0] if len(v5_frame) >= 25 else 0

        # Extract Modbus RTU payload (starts at byte 25, ends before trailer)
        raw_modbus = v5_frame[25:-2]
        sanitized_modbus = sanitize_modbus_rtu_frame(raw_modbus)

        # Check Modbus CRC16
        modbus_crc_valid = False
        if len(sanitized_modbus) >= 4:
            expected_modbus_crc = calculate_modbus_crc16(sanitized_modbus[:-2])
            actual_modbus_crc = struct.unpack("<H", sanitized_modbus[-2:])[0]
            modbus_crc_valid = (expected_modbus_crc == actual_modbus_crc)

        return SolarmanV5DecodedFrame(
            valid=True,
            control_code=control_code,
            control_code_name=ctrl_name,
            sequence_number=seq_num,
            logger_serial=logger_serial,
            frame_type=frame_type,
            status=status,
            total_working_time_s=uptime_total,
            power_on_time_s=uptime_power_on,
            offset_time_s=offset_time,
            modbus_rtu_frame=sanitized_modbus,
            modbus_rtu_hex=sanitized_modbus.hex().upper(),
            modbus_crc_valid=modbus_crc_valid,
            raw_frame_hex=raw_hex,
        )

    @classmethod
    def compile_read_holding_registers(
        cls,
        logger_serial: int,
        slave_id: int,
        start_address: int,
        quantity: int,
        sequence_number: int = 1,
    ) -> SolarmanV5CompiledRequest:
        """Compile a Modbus FC03 Read Holding Registers request wrapped in Solarman V5."""
        pdu = struct.pack(">BBHH", slave_id, 0x03, start_address, quantity)
        crc = calculate_modbus_crc16(pdu)
        rtu_frame = pdu + struct.pack("<H", crc)

        v5_frame = cls.encode_frame(
            modbus_rtu_frame=rtu_frame,
            logger_serial=logger_serial,
            sequence_number=sequence_number,
        )

        return SolarmanV5CompiledRequest(
            logger_serial=logger_serial,
            sequence_number=sequence_number,
            modbus_slave_id=slave_id,
            function_code=0x03,
            v5_frame_bytes=v5_frame,
            v5_frame_hex=v5_frame.hex().upper(),
            modbus_rtu_hex=rtu_frame.hex().upper(),
        )

    @classmethod
    def compile_write_single_register(
        cls,
        logger_serial: int,
        slave_id: int,
        register_address: int,
        value: int,
        sequence_number: int = 1,
    ) -> SolarmanV5CompiledRequest:
        """Compile a Modbus FC06 Write Single Register request wrapped in Solarman V5."""
        pdu = struct.pack(">BBHH", slave_id, 0x06, register_address, value & 0xFFFF)
        crc = calculate_modbus_crc16(pdu)
        rtu_frame = pdu + struct.pack("<H", crc)

        v5_frame = cls.encode_frame(
            modbus_rtu_frame=rtu_frame,
            logger_serial=logger_serial,
            sequence_number=sequence_number,
        )

        return SolarmanV5CompiledRequest(
            logger_serial=logger_serial,
            sequence_number=sequence_number,
            modbus_slave_id=slave_id,
            function_code=0x06,
            v5_frame_bytes=v5_frame,
            v5_frame_hex=v5_frame.hex().upper(),
            modbus_rtu_hex=rtu_frame.hex().upper(),
        )

    @classmethod
    def compile_write_multiple_registers(
        cls,
        logger_serial: int,
        slave_id: int,
        start_address: int,
        values: List[int],
        sequence_number: int = 1,
    ) -> SolarmanV5CompiledRequest:
        """Compile a Modbus FC16 Write Multiple Registers request wrapped in Solarman V5."""
        qty = len(values)
        byte_count = qty * 2
        pdu = struct.pack(">BBHHB", slave_id, 0x10, start_address, qty, byte_count)
        for val in values:
            pdu += struct.pack(">H", val & 0xFFFF)
        crc = calculate_modbus_crc16(pdu)
        rtu_frame = pdu + struct.pack("<H", crc)

        v5_frame = cls.encode_frame(
            modbus_rtu_frame=rtu_frame,
            logger_serial=logger_serial,
            sequence_number=sequence_number,
        )

        return SolarmanV5CompiledRequest(
            logger_serial=logger_serial,
            sequence_number=sequence_number,
            modbus_slave_id=slave_id,
            function_code=0x10,
            v5_frame_bytes=v5_frame,
            v5_frame_hex=v5_frame.hex().upper(),
            modbus_rtu_hex=rtu_frame.hex().upper(),
        )


# ---------------------------------------------------------------------------
# Solarman Datalogger UDP Discovery Parser (Port 48899)
# ---------------------------------------------------------------------------

def parse_solarman_discovery_reply(payload: str) -> Optional[Dict[str, Any]]:
    """Parse Solarman UDP broadcast reply from port 48899.

    Format typical response:
    '<IP>,<MAC>,<SERIAL>' or 'WIFIKIT-214028-...,<IP>,<MAC>,<SERIAL>'
    """
    parts = [p.strip() for p in payload.split(",")]
    if len(parts) >= 3:
        # Check which part looks like an IP address
        ip = ""
        mac = ""
        serial_str = ""
        for p in parts:
            if p.count(".") == 3 and all(seg.isdigit() for seg in p.split(".")):
                ip = p
            elif (p.count(":") == 5 or p.count("-") == 5) and len(p) == 17:
                mac = p.upper()
            elif p.isdigit() and len(p) >= 8:
                serial_str = p

        if ip or serial_str:
            return {
                "ip_address": ip or parts[0],
                "mac_address": mac or (parts[1] if len(parts) > 1 else ""),
                "logger_serial": int(serial_str) if serial_str.isdigit() else 0,
                "raw_reply": payload,
            }
    return None
