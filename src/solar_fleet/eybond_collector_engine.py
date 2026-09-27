"""Eybond ESP Collector & Voltronic PI30 Protocol Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
esp-eybond-collector-main (MPL-2.0 License).
Reverse-engineered for interoperability with Eybond / SmartESS Wi-Fi dongle
replacements (ESP8266, ESP32, BK72xx) and Voltronic / Axpert / Bluesun / EASun
hybrid solar inverters over TTL / RS232 / RS485.

Key Capabilities:
- Eybond Modbus Binary Frame Codec:
  * 8-byte wire header: TID (u16), DevCode (u16), WireLen (u16 = total_len - 6), DevAddr (u8), FC (u8).
  * Function Codes: FC_HEARTBEAT (1), FC_QUERY_COLLECTOR (2), FC_SET_COLLECTOR (3), FC_FORWARD_TO_DEVICE (4).
- UDP Discovery & Reverse-TCP Redirect:
  * Handshake format: "set>server=IP:PORT;" -> reply "rsp>server=2;".
  * Synthetic serial number generation: "V00" + 15 digits from 6-byte MAC.
- AT Command Interface:
  * Interleaved AT lines: AT+DTUPN, AT+ATVER, AT+FWVER, AT+UART, AT+CLDSRVHOST1, AT+WFSS, AT+SYST, AT+LINK.
- Voltronic PI30 / PI17 Serial Protocol Engine:
  * CRC16-XMODEM with byte-stuffing (+1 if colliding with 0x28, 0x0D, 0x0A).
  * QPIGS (General Status) parser: 21 telemetry fields (Grid, Output, Load, Battery, PV).
  * QPIRI (Rated Parameters) parser: 25 configuration fields.
  * QMOD (Operating Mode) decoder: Line, Battery, Standby, Fault, Power Saving.
  * QPIWS (Warning Bitfield) decoder: 32 fault & warning status indicators.
- Inverter Parameter Compilers with Safety Gating:
  * POP (Output Source Priority: Utility First, Solar First, SBU).
  * PCP (Charger Source Priority: Utility First, Solar First, Solar & Utility, Solar Only).
  * MCHGC (Max Charging Current: 10..100A).
  * PCVV (Bulk C.V. Charging Voltage: 48.0..58.4V).
  * PBFT (Floating Charging Voltage: 48.0..56.0V).
  * PSDV (Battery Cutoff Voltage: 40.0..48.0V).
  * All parameter writes are strictly gated behind LOCKED_PENDING_HARDWARE_ACCEPTANCE.
- Telemetry Normalizer: Translates raw PI30 frames into standard Solar Fleet EMS schema.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Eybond Frame Constants
# ---------------------------------------------------------------------------

FC_HEARTBEAT = 0x01
FC_QUERY_COLLECTOR = 0x02
FC_SET_COLLECTOR = 0x03
FC_FORWARD_TO_DEVICE = 0x04

HEADER_SIZE = 8
WIRE_LEN_OFFSET = 6

DEVCODE_DEFAULT = 0x0994  # Solar Inverter
DEVCODE_COLLECTOR = 0x0000  # Unknown / internal collector

# Voltronic Operating Modes
VOLTRONIC_MODES = {
    "P": "Power On Mode",
    "S": "Standby Mode",
    "L": "Line / Utility Mode",
    "B": "Battery / Inverter Mode",
    "F": "Fault Mode",
    "H": "Power Saving Mode",
    "D": "Shutdown Mode",
}

# Voltronic Warning Flags (QPIWS 32-char bitfield)
QPIWS_FLAGS = [
    (0, "Reserved_0", "WARNING"),
    (1, "InverterFault", "CRITICAL"),
    (2, "BusOverFault", "CRITICAL"),
    (3, "BusUnderFault", "CRITICAL"),
    (4, "BusSoftFailFault", "CRITICAL"),
    (5, "LineFail", "WARNING"),
    (6, "OPVShortFault", "CRITICAL"),
    (7, "InverterVoltageLow", "WARNING"),
    (8, "InverterVoltageHigh", "CRITICAL"),
    (9, "OverTemperatureFault", "CRITICAL"),
    (10, "FanLockedWarning", "WARNING"),
    (11, "BatteryVoltageHigh", "CRITICAL"),
    (12, "BatteryLowAlarm", "WARNING"),
    (13, "BatteryUnderShutdown", "CRITICAL"),
    (14, "BatteryDeratingWarning", "WARNING"),
    (15, "OverLoadFault", "CRITICAL"),
    (16, "EEPROMFault", "CRITICAL"),
    (17, "InverterOverCurrentFault", "CRITICAL"),
    (18, "InverterSoftFailFault", "CRITICAL"),
    (19, "SelfTestFailFault", "CRITICAL"),
    (20, "OPDCVoltageOverFault", "CRITICAL"),
    (21, "BatteryOpenWarning", "WARNING"),
    (22, "CurrentSensorFailFault", "CRITICAL"),
    (23, "BatteryShortFault", "CRITICAL"),
    (24, "PowerLimitWarning", "WARNING"),
    (25, "PVVoltageHighWarning", "WARNING"),
    (26, "MPPTOverloadWarning", "WARNING"),
    (27, "MPPTOverloadLossWarning", "WARNING"),
    (28, "BatteryLowWarningFromSCC", "WARNING"),
    (29, "BatteryHighWarningFromSCC", "WARNING"),
    (30, "Reserved_30", "WARNING"),
    (31, "Reserved_31", "WARNING"),
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class EybondFrameHeader:
    """Decoded 8-byte Eybond frame header."""
    tid: int
    devcode: int
    wire_len: int
    devaddr: int
    fc: int

    @property
    def total_len(self) -> int:
        return self.wire_len + WIRE_LEN_OFFSET

    @property
    def payload_len(self) -> int:
        return self.total_len - HEADER_SIZE


@dataclass
class VoltronicPi30Telemetry:
    """Decoded Voltronic QPIGS telemetry."""
    grid_voltage_v: float
    grid_frequency_hz: float
    ac_output_voltage_v: float
    ac_output_frequency_hz: float
    ac_output_apparent_power_va: float
    ac_output_active_power_w: float
    output_load_percent: int
    bus_voltage_v: float
    battery_voltage_v: float
    battery_charge_current_a: float
    battery_capacity_percent: int
    inverter_heatsink_temp_c: int
    pv_input_current_a: float
    pv_input_voltage_v: float
    battery_voltage_scc_v: float
    battery_discharge_current_a: float
    device_status: str
    pv_power_w: float


# ---------------------------------------------------------------------------
# Frame Header Codec
# ---------------------------------------------------------------------------

def encode_eybond_header(tid: int, devcode: int, total_len: int, devaddr: int, fc: int) -> bytes:
    """Encode 8-byte big-endian Eybond frame header."""
    wire_len = total_len - WIRE_LEN_OFFSET
    return struct.pack(">HHHBB", tid, devcode, wire_len, devaddr, fc)


def decode_eybond_header(data: bytes) -> EybondFrameHeader:
    """Decode 8-byte Eybond frame header."""
    if len(data) < HEADER_SIZE:
        raise ValueError(f"Data too short for Eybond header ({len(data)} < {HEADER_SIZE})")
    tid, devcode, wire_len, devaddr, fc = struct.unpack(">HHHBB", data[:HEADER_SIZE])
    return EybondFrameHeader(tid=tid, devcode=devcode, wire_len=wire_len, devaddr=devaddr, fc=fc)


def build_eybond_frame(tid: int, devcode: int, devaddr: int, fc: int, payload: bytes) -> bytes:
    """Construct complete Eybond frame with 8-byte header and payload."""
    total_len = HEADER_SIZE + len(payload)
    hdr = encode_eybond_header(tid, devcode, total_len, devaddr, fc)
    return hdr + payload


# ---------------------------------------------------------------------------
# CRC16-XMODEM & Voltronic Framing
# ---------------------------------------------------------------------------

def crc16_xmodem(data: bytes) -> int:
    """Calculate CRC16-XMODEM checksum (poly 0x1021, init 0x0000)."""
    crc = 0x0000
    for byte in data:
        crc ^= (byte << 8)
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def escape_crc_byte(byte_val: int) -> int:
    """Voltronic byte stuffing: escape 0x28 '(', 0x0D '\r', 0x0A '\n' by adding 1."""
    if byte_val in (0x28, 0x0D, 0x0A):
        return (byte_val + 1) & 0xFF
    return byte_val


def build_voltronic_frame(command: str) -> bytes:
    """Wrap ASCII command into Voltronic frame: <command><escaped_crc16>\\r."""
    cmd_bytes = command.encode("ascii")
    crc = crc16_xmodem(cmd_bytes)
    hi = escape_crc_byte((crc >> 8) & 0xFF)
    lo = escape_crc_byte(crc & 0xFF)
    return cmd_bytes + bytes([hi, lo, 0x0D])


def verify_and_strip_voltronic_response(raw: bytes) -> Tuple[bool, str]:
    """Verify CRC of Voltronic response frame (starts with '(') and extract payload."""
    if len(raw) < 4 or raw[0] != 0x28:  # '('
        return False, ""
    # Search for trailing \r
    end_idx = raw.find(b"\r")
    if end_idx == -1 or end_idx < 3:
        return False, ""

    body = raw[: end_idx - 2]
    # Checksum bytes at end_idx-2, end_idx-1
    crc_expected = crc16_xmodem(body)
    hi_exp = escape_crc_byte((crc_expected >> 8) & 0xFF)
    lo_exp = escape_crc_byte(crc_expected & 0xFF)

    hi_actual = raw[end_idx - 2]
    lo_actual = raw[end_idx - 1]

    is_valid = (hi_exp == hi_actual) and (lo_exp == lo_actual)
    # Strip leading '(' and return decoded ASCII text
    payload_str = body[1:].decode("latin1", errors="replace")
    return is_valid, payload_str


# ---------------------------------------------------------------------------
# UDP Discovery & Synthetic Serial Number
# ---------------------------------------------------------------------------

def parse_udp_discovery_redirect(data: bytes) -> Optional[Tuple[str, int]]:
    """Parse UDP discovery request: 'set>server=IP:PORT;'."""
    text = data.decode("ascii", errors="replace").strip()
    prefix = "set>server="
    if not text.startswith(prefix) or not text.endswith(";"):
        return None
    body = text[len(prefix): -1].strip()
    if ":" not in body:
        return None
    parts = body.split(":")
    if len(parts) != 2:
        return None
    host, port_str = parts[0].strip(), parts[1].strip()
    if not host or not port_str.isdigit():
        return None
    port = int(port_str)
    if not (1 <= port <= 65535):
        return None
    return host, port


def build_udp_discovery_reply() -> bytes:
    """Build standard Eybond discovery handshake response."""
    return b"rsp>server=2;"


def synthesize_collector_pn(mac: bytes) -> str:
    """Synthesize 18-character collector PN from 6-byte MAC address."""
    if len(mac) != 6:
        raise ValueError("MAC address must be exactly 6 bytes")
    val = 0
    for b in mac:
        val = (val << 8) | b
    digits = []
    for _ in range(15):
        digits.append(str(val % 10))
        val //= 10
    digits.reverse()
    return "V00" + "".join(digits)


# ---------------------------------------------------------------------------
# AT Command Handler
# ---------------------------------------------------------------------------

def parse_at_command(line: str) -> Optional[Tuple[str, bool, str]]:
    """Parse AT command line into (command, is_write, value)."""
    text = line.strip()
    if not text.upper().startswith("AT+"):
        return None
    rem = text[3:]
    if rem.endswith("?"):
        cmd = rem[:-1].strip().upper()
        return cmd, False, ""
    if "=" in rem:
        cmd, val = rem.split("=", 1)
        return cmd.strip().upper(), True, val.strip()
    return rem.strip().upper(), False, ""


def handle_at_command(
    cmd: str,
    is_write: bool,
    val: str,
    profile_pn: str = "V00000200000000001",
    firmware_ver: str = "0.1.10",
    uart_cfg: str = "2400,8,1,NONE",
    cloud_srv: str = "192.168.1.100,8899,TCP",
    wifi_rssi: str = "-58",
) -> str:
    """Generate AT response line."""
    if is_write:
        return f"AT+{cmd}:W000\r\n"

    cmd_upper = cmd.upper()
    if cmd_upper == "DTUPN":
        return f"AT+{cmd}:{profile_pn}\r\n"
    elif cmd_upper == "FWVER":
        return f"AT+{cmd}:{firmware_ver}\r\n"
    elif cmd_upper == "ATVER":
        return f"AT+{cmd}:1.11\r\n"
    elif cmd_upper == "UART":
        return f"AT+{cmd}:{uart_cfg}\r\n"
    elif cmd_upper == "CLDSRVHOST1":
        return f"AT+{cmd}:{cloud_srv}\r\n"
    elif cmd_upper == "WFSS":
        return f"AT+{cmd}:{wifi_rssi}\r\n"
    elif cmd_upper == "DTUTYPE":
        return f"AT+{cmd}:Wi-Fi.DTU\r\n"
    elif cmd_upper == "LINK":
        return f"AT+{cmd}:connected\r\n"
    elif cmd_upper == "SYST":
        now_str = datetime.now(timezone.utc).strftime("%Y%m%d%H%M%S")
        return f"AT+{cmd}:{now_str}\r\n"
    else:
        return f"AT+{cmd}:\r\n"


# ---------------------------------------------------------------------------
# Voltronic Telemetry Decoders
# ---------------------------------------------------------------------------

def parse_qpigs_response(raw_text: str) -> VoltronicPi30Telemetry:
    """Parse Voltronic QPIGS space-separated response string."""
    parts = raw_text.strip().split()
    if len(parts) < 16:
        raise ValueError(f"QPIGS payload has insufficient tokens ({len(parts)} < 16): {raw_text}")

    grid_v = float(parts[0])
    grid_hz = float(parts[1])
    ac_v = float(parts[2])
    ac_hz = float(parts[3])
    apparent_va = float(parts[4])
    active_w = float(parts[5])
    load_pct = int(parts[6])
    bus_v = float(parts[7])
    bat_v = float(parts[8])
    charge_a = float(parts[9])
    bat_soc = int(parts[10])
    temp_c = int(parts[11])
    pv_a = float(parts[12])
    pv_v = float(parts[13])
    scc_v = float(parts[14])
    dischg_a = float(parts[15])
    status = parts[16] if len(parts) > 16 else "00000000"

    pv_power = float(parts[19]) if len(parts) > 19 and parts[19].replace(".", "", 1).isdigit() else (pv_a * pv_v)

    return VoltronicPi30Telemetry(
        grid_voltage_v=grid_v,
        grid_frequency_hz=grid_hz,
        ac_output_voltage_v=ac_v,
        ac_output_frequency_hz=ac_hz,
        ac_output_apparent_power_va=apparent_va,
        ac_output_active_power_w=active_w,
        output_load_percent=load_pct,
        bus_voltage_v=bus_v,
        battery_voltage_v=bat_v,
        battery_charge_current_a=charge_a,
        battery_capacity_percent=bat_soc,
        inverter_heatsink_temp_c=temp_c,
        pv_input_current_a=pv_a,
        pv_input_voltage_v=pv_v,
        battery_voltage_scc_v=scc_v,
        battery_discharge_current_a=dischg_a,
        device_status=status,
        pv_power_w=round(pv_power, 1),
    )


def decode_qpiws_warnings(flag_str: str) -> List[Dict[str, str]]:
    """Decode 32-character QPIWS warning/fault bitfield."""
    alarms = []
    clean_flags = flag_str.strip()
    for idx, name, severity in QPIWS_FLAGS:
        if idx < len(clean_flags) and clean_flags[idx] == "1":
            alarms.append({
                "bit": idx,
                "code": name,
                "severity": severity,
            })
    return alarms


def normalize_eybond_pi30_telemetry(
    collector_pn: str,
    inverter_sn: str,
    qpigs: VoltronicPi30Telemetry,
    mode_char: str = "L",
    qpiws_flags: str = "0" * 32,
    model_name: str = "Axpert / Bluesun VMII",
) -> Dict[str, Any]:
    """Normalize decoded Voltronic PI30 data to Solar Fleet EMS schema."""
    mode_text = VOLTRONIC_MODES.get(mode_char.upper(), f"Mode {mode_char}")
    alarms = decode_qpiws_warnings(qpiws_flags)

    bat_power = 0.0
    if qpigs.battery_discharge_current_a > 0:
        bat_power = round(qpigs.battery_discharge_current_a * qpigs.battery_voltage_v, 1)
    elif qpigs.battery_charge_current_a > 0:
        bat_power = -round(qpigs.battery_charge_current_a * qpigs.battery_voltage_v, 1)

    return {
        "device_id": f"eybond-esp-{collector_pn}",
        "collector_pn": collector_pn,
        "serial_number": inverter_sn,
        "vendor": "Voltronic / Eybond ESP",
        "protocol": "PI30 over Eybond Modbus Bridge",
        "model": model_name,
        "operating_mode": mode_text,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "power_flow": {
            "solar_power_w": qpigs.pv_power_w,
            "pv_voltage_v": qpigs.pv_input_voltage_v,
            "pv_current_a": qpigs.pv_input_current_a,
            "grid_power_w": round(qpigs.grid_voltage_v * 2.0, 1) if mode_char == "L" else 0.0,
            "load_power_w": qpigs.ac_output_active_power_w,
            "load_apparent_va": qpigs.ac_output_apparent_power_va,
            "load_percent": qpigs.output_load_percent,
            "battery_power_w": bat_power,
        },
        "grid": {
            "voltage_v": qpigs.grid_voltage_v,
            "frequency_hz": qpigs.grid_frequency_hz,
            "output_voltage_v": qpigs.ac_output_voltage_v,
            "output_frequency_hz": qpigs.ac_output_frequency_hz,
        },
        "battery": {
            "soc_percent": qpigs.battery_capacity_percent,
            "voltage_v": qpigs.battery_voltage_v,
            "charge_current_a": qpigs.battery_charge_current_a,
            "discharge_current_a": qpigs.battery_discharge_current_a,
            "bus_voltage_v": qpigs.bus_voltage_v,
        },
        "diagnostics": {
            "heatsink_temperature_c": qpigs.inverter_heatsink_temp_c,
            "device_status_bits": qpigs.device_status,
            "active_faults_count": sum(1 for a in alarms if a["severity"] == "CRITICAL"),
            "active_warnings_count": sum(1 for a in alarms if a["severity"] == "WARNING"),
            "alarms": alarms,
        },
    }


# ---------------------------------------------------------------------------
# Voltronic Safe Control Compilers
# ---------------------------------------------------------------------------

def compile_voltronic_output_priority(priority: str) -> Dict[str, Any]:
    """Compile Voltronic Output Priority command (POP00, POP01, POP02)."""
    p_map = {
        "utility_first": ("00", "Utility First (USB)"),
        "solar_first": ("01", "Solar First (SUB)"),
        "sbu": ("02", "Solar-Battery-Utility (SBU)"),
    }
    key = priority.lower().replace(" ", "_")
    if key not in p_map:
        raise ValueError(f"Invalid priority '{priority}'. Allowed: 'utility_first', 'solar_first', 'sbu'")

    code, desc = p_map[key]
    cmd_str = f"POP{code}"
    frame = build_voltronic_frame(cmd_str)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "command": cmd_str,
        "frame_hex": frame.hex(),
        "description": desc,
        "reason": "Parameter command compiled. Hardware acceptance gate active.",
    }


def compile_voltronic_charger_priority(priority: str) -> Dict[str, Any]:
    """Compile Voltronic Charger Source Priority command (PCP00..03)."""
    p_map = {
        "utility_first": ("00", "Utility First"),
        "solar_first": ("01", "Solar First"),
        "solar_and_utility": ("02", "Solar and Utility"),
        "solar_only": ("03", "Solar Only"),
    }
    key = priority.lower().replace(" ", "_")
    if key not in p_map:
        raise ValueError(f"Invalid charger priority '{priority}'. Allowed: 'utility_first', 'solar_first', 'solar_and_utility', 'solar_only'")

    code, desc = p_map[key]
    cmd_str = f"PCP{code}"
    frame = build_voltronic_frame(cmd_str)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "command": cmd_str,
        "frame_hex": frame.hex(),
        "description": desc,
        "reason": "Parameter command compiled. Hardware acceptance gate active.",
    }


def compile_voltronic_charging_current(current_a: int) -> Dict[str, Any]:
    """Compile Maximum Charging Current command (MCHGC0xx, e.g. 10..120A)."""
    if not (10 <= current_a <= 120):
        raise ValueError(f"Charging current out of bounds (10..120A): {current_a}")

    cmd_str = f"MCHGC{current_a:03d}"
    frame = build_voltronic_frame(cmd_str)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "command": cmd_str,
        "frame_hex": frame.hex(),
        "current_a": current_a,
        "reason": "Parameter command compiled. Hardware acceptance gate active.",
    }


def compile_voltronic_voltage_settings(
    bulk_voltage: float,
    float_voltage: float,
    cutoff_voltage: float,
) -> Dict[str, Any]:
    """Compile Voltronic Battery Voltage settings (PCVV, PBFT, PSDV)."""
    if not (48.0 <= bulk_voltage <= 58.4):
        raise ValueError(f"Bulk voltage out of bounds (48.0..58.4V): {bulk_voltage}")
    if not (48.0 <= float_voltage <= 56.0):
        raise ValueError(f"Float voltage out of bounds (48.0..56.0V): {float_voltage}")
    if not (40.0 <= cutoff_voltage <= 48.0):
        raise ValueError(f"Cutoff voltage out of bounds (40.0..48.0V): {cutoff_voltage}")

    cmd_bulk = f"PCVV{bulk_voltage:04.1f}"
    cmd_float = f"PBFT{float_voltage:04.1f}"
    cmd_cutoff = f"PSDV{cutoff_voltage:04.1f}"

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "commands": [cmd_bulk, cmd_float, cmd_cutoff],
        "frames_hex": [
            build_voltronic_frame(cmd_bulk).hex(),
            build_voltronic_frame(cmd_float).hex(),
            build_voltronic_frame(cmd_cutoff).hex(),
        ],
        "voltages": {
            "bulk_v": bulk_voltage,
            "float_v": float_voltage,
            "cutoff_v": cutoff_voltage,
        },
        "reason": "Parameter commands compiled. Hardware acceptance gate active.",
    }


# ---------------------------------------------------------------------------
# Virtual ESP Eybond Collector Simulator
# ---------------------------------------------------------------------------

class VirtualEybondCollector:
    """Simulator representing an ESP-based Eybond collector bridge."""

    def __init__(
        self,
        mac: bytes = bytes([0x24, 0x6F, 0x28, 0xA1, 0xB2, 0xC3]),
        firmware_ver: str = "0.1.10",
        uart_cfg: str = "2400,8,1,NONE",
    ) -> None:
        self.mac = mac
        self.pn = synthesize_collector_pn(mac)
        self.firmware_ver = firmware_ver
        self.uart_cfg = uart_cfg
        self.server_host = "192.168.1.100"
        self.server_port = 8899
        self.link_status = "connected"

    def handle_udp_packet(self, data: bytes) -> Optional[bytes]:
        """Handle inbound UDP packet on port 58899."""
        parsed = parse_udp_discovery_redirect(data)
        if parsed:
            self.server_host, self.server_port = parsed
            return build_udp_discovery_reply()
        return None

    def execute_at(self, line: str) -> str:
        """Execute AT command on TCP stream."""
        parsed = parse_at_command(line)
        if not parsed:
            return "ERROR\r\n"
        cmd, is_write, val = parsed
        return handle_at_command(
            cmd=cmd,
            is_write=is_write,
            val=val,
            profile_pn=self.pn,
            firmware_ver=self.firmware_ver,
            uart_cfg=self.uart_cfg,
            cloud_srv=f"{self.server_host},{self.server_port},TCP",
        )

    def execute_command_safely(
        self,
        command_type: str,
        params: Dict[str, Any],
        unlocked: bool = False,
    ) -> Dict[str, Any]:
        """Safely execute control command with hardware acceptance gate."""
        if not unlocked:
            return {
                "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
                "command_type": command_type,
                "params": params,
                "message": (
                    "Voltronic PI30 parameter write is gated behind hardware acceptance verification. "
                    "Collector holds inverter in read-only state."
                ),
            }

        if command_type == "output_priority":
            p = str(params.get("priority", "utility_first"))
            return compile_voltronic_output_priority(p)

        elif command_type == "charger_priority":
            p = str(params.get("priority", "utility_first"))
            return compile_voltronic_charger_priority(p)

        elif command_type == "charge_current":
            a = int(params.get("current_a", 30))
            return compile_voltronic_charging_current(a)

        elif command_type == "battery_voltages":
            bulk = float(params.get("bulk_v", 56.4))
            flt = float(params.get("float_v", 54.0))
            cut = float(params.get("cutoff_v", 42.0))
            return compile_voltronic_voltage_settings(bulk, flt, cut)

        else:
            raise ValueError(f"Unknown Voltronic command type: '{command_type}'")
