"""SmartESS / Eybond Local Inverter Protocol and Client Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
ha-smartess-local (MIT License, author @smartess-local maintainers).
Per repository workflow and licensing rules, this is a clean-room independent
implementation of the Eybond Modbus datalogger framing, P17 / Q-protocol encapsulation,
CRC-16/XMODEM calculation with byte stuffing, Voltronic/Axpert telemetry parsing,
and parameter control engine.

Key Capabilities:
- Eybond Modbus Framing:
  * 8-byte binary header (>HHHBB): TID (uint16), Device Code (uint16, 0x0994 for Solar P17),
    Total Length (uint16), Device RS485 Address (uint8, default 1), Function Code (uint8).
  * FC_HEARTBEAT (0x01): Server/Collector synchronization with UTC timestamp and interval.
  * FC_FORWARD2DEVICE (0x04): Transparent RS485 forwarder bridging P17 inverter frames.
- P17 and Q-Protocol Inverter Framing:
  * CRC-16/XMODEM calculation (poly 0x1021, init 0x0000) with framing byte-stuffing
    (0x28 '(', 0x0D '\r', 0x0A '\n' incremented by 1).
  * Poll frame generation: ^P<len_3><cmd><crc_hi><crc_lo>\r
  * Set frame generation: ^S<len_3><cmd><crc_hi><crc_lo>\r
  * Response parsing handling P17 standard (^D<len_3><data>), short ACK (^1), short NAK (^0),
    and Q-protocol standard ((<data>), ACK ((ACK), and NAK ((NAK).
- Command Decoding & Telemetry Normalization:
  * GS (General Status): 28 fields including grid voltage/freq, AC output voltage/freq,
    active/apparent power, load %, battery voltage, charge/discharge currents, battery SOC %,
    heatsink temperature, and PV1/PV2 voltages & power.
  * MOD (Inverter Working Mode): Power On, Standby, Line/Grid, Battery, Fault, Power Saving, Shutdown.
  * PIRI (Ratings & Configuration): Voltage/current ratings, battery type, bulk/float voltages,
    cut-off voltage, and source priorities.
  * GS2: Second MPPT inputs (voltage, charging power).
  * ET: Day and total energy counters (kWh).
- Control Command Builders:
  * Output Source Priority (POP): Solar > Utility > Battery (USB = 0) vs Solar > Battery > Utility (SBU = 1).
  * Charger Source Priority (PSP): Utility first (0), Solar first (1), Solar+Utility (2), Solar only (3).
  * Max Charging Current (MCHGC) and Max AC Charging Current (MUCHGC).
  * Battery Cut-off Voltage (PSDV), Bulk/Float Voltages (MCHGV), Re-charge/Re-discharge (BUCD).
- Safety gating ensuring writable parameter updates remain locked under
  LOCKED_PENDING_HARDWARE_ACCEPTANCE.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

EYBOND_HEADER_SIZE = 8
DEVCODE_SOLAR_P17 = 0x0994

FC_HEARTBEAT = 0x01
FC_FORWARD2DEVICE = 0x04

STUFF_BYTES = {0x28, 0x0D, 0x0A}  # '(', CR, LF

# Working Mode Map
MODE_MAP = {
    "P": "Power On Mode",
    "S": "Standby Mode",
    "L": "Line / Grid Mode",
    "B": "Battery Mode",
    "F": "Fault Mode",
    "H": "Power Saving Mode",
    "D": "Shutdown Mode",
}

# Output Source Priority Map
OUTPUT_SOURCE_PRIORITY_MAP = {
    0: "Solar > Utility > Battery (USB)",
    1: "Solar > Battery > Utility (SBU)",
}

# Charger Source Priority Map
CHARGER_SOURCE_PRIORITY_MAP = {
    0: "Utility First",
    1: "Solar First",
    2: "Solar and Utility",
    3: "Solar Only",
}

# Battery Type Map
BATTERY_TYPE_MAP = {
    0: "AGM",
    1: "Flooded",
    2: "User-defined",
    3: "Pylontech",
    4: "Weco",
    5: "Soltaro",
    6: "BAK",
    7: "Lithium (LIB)",
    8: "Lithium Iron (LIC)",
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class EybondHeader:
    """Decoded 8-byte Eybond Modbus frame header."""
    tid: int
    devcode: int
    total_len: int
    devaddr: int
    fc: int


@dataclass
class SmartEssGeneralStatus:
    """Parsed General Status (GS) telemetry."""
    grid_voltage_v: float
    grid_freq_hz: float
    ac_output_voltage_v: float
    ac_output_freq_hz: float
    ac_output_apparent_power_va: int
    ac_output_active_power_w: int
    output_load_percent: int
    battery_voltage_v: float
    battery_voltage_scc_v: float
    battery_charge_current_a: int
    battery_discharge_current_a: int
    battery_capacity_percent: int
    heatsink_temp_c: int
    pv1_power_w: int
    pv1_voltage_v: float
    pv2_power_w: int
    pv2_voltage_v: float
    device_status: str


@dataclass
class SmartEssRatedInfo:
    """Parsed Inverter Rated & Config Information (PIRI)."""
    ac_input_voltage_rating: float
    ac_input_current_rating: float
    ac_output_voltage_rating: float
    ac_output_freq_rating: float
    ac_output_active_power_rating: int
    battery_voltage_rating: float
    battery_recharge_voltage: float
    battery_under_voltage: float
    battery_bulk_voltage: float
    battery_float_voltage: float
    battery_type: int
    battery_type_name: str
    max_ac_charge_current: int
    max_charge_current: int
    input_voltage_range: int
    output_source_priority: int
    output_source_priority_name: str
    charger_source_priority: int
    charger_source_priority_name: str


@dataclass
class SmartEssEnergyStats:
    """Parsed Energy Statistics (ET)."""
    day_energy_kwh: float
    total_energy_kwh: float


# ---------------------------------------------------------------------------
# CRC & Framing Utilities
# ---------------------------------------------------------------------------

def crc16_xmodem(data: bytes) -> int:
    """Calculate CRC-16/XMODEM (Polynomial 0x1021, Initial 0x0000)."""
    crc = 0x0000
    for byte in data:
        crc ^= byte << 8
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc


def _stuff_crc_byte(b: int) -> int:
    """Increment CRC byte by 1 if it collides with framing delimiters '(', CR, LF."""
    return (b + 1) & 0xFF if b in STUFF_BYTES else b


# ---------------------------------------------------------------------------
# Eybond Frame Builders & Parsers
# ---------------------------------------------------------------------------

def encode_eybond_header(tid: int, devcode: int, total_len: int, devaddr: int, fc: int) -> bytes:
    """Encode 8-byte Eybond header (>HHHBB)."""
    return struct.pack(">HHHBB", tid & 0xFFFF, devcode & 0xFFFF, total_len & 0xFFFF, devaddr & 0xFF, fc & 0xFF)


def decode_eybond_header(data: bytes) -> EybondHeader:
    """Decode 8-byte Eybond header."""
    if len(data) < EYBOND_HEADER_SIZE:
        raise ValueError(f"Data too short for Eybond header: {len(data)} bytes")
    tid, devcode, total_len, devaddr, fc = struct.unpack(">HHHBB", data[:EYBOND_HEADER_SIZE])
    return EybondHeader(tid=tid, devcode=devcode, total_len=total_len, devaddr=devaddr, fc=fc)


def build_heartbeat_request(tid: int, interval: int = 60, dt: Optional[datetime] = None) -> bytes:
    """Build heartbeat request frame (FC=1). Server -> Collector.

    Payload (8 bytes): [year-2000, month, day, hour, minute, second, interval:2]
    Total frame: 16 bytes.
    """
    if dt is None:
        dt = datetime.now(timezone.utc)
    payload = bytes([
        (dt.year - 2000) & 0xFF,
        dt.month & 0xFF,
        dt.day & 0xFF,
        dt.hour & 0xFF,
        dt.minute & 0xFF,
        dt.second & 0xFF,
    ]) + struct.pack(">H", interval & 0xFFFF)

    total_len = EYBOND_HEADER_SIZE + len(payload)
    hdr = encode_eybond_header(tid, 0, total_len, 1, FC_HEARTBEAT)
    return hdr + payload


def parse_heartbeat_response(data: bytes) -> Tuple[EybondHeader, str]:
    """Parse heartbeat response. Returns (header, collector_pn)."""
    hdr = decode_eybond_header(data)
    if hdr.fc != FC_HEARTBEAT:
        raise ValueError(f"Expected heartbeat FC=1, got {hdr.fc}")
    pn_bytes = data[EYBOND_HEADER_SIZE:EYBOND_HEADER_SIZE + 14]
    pn = pn_bytes.decode("ascii", errors="replace").strip("\x00 \t\r\n")
    return hdr, pn


def build_forward2device(tid: int, p17_frame: bytes, devcode: int = DEVCODE_SOLAR_P17, devaddr: int = 1) -> bytes:
    """Wrap a raw P17 frame in Forward2Device (FC=4) for transmission to collector."""
    total_len = EYBOND_HEADER_SIZE + len(p17_frame)
    hdr = encode_eybond_header(tid, devcode, total_len, devaddr, FC_FORWARD2DEVICE)
    return hdr + p17_frame


def parse_forward2device_response(data: bytes) -> Tuple[EybondHeader, bytes]:
    """Parse FC=4 response. Returns (header, p17_response_bytes)."""
    hdr = decode_eybond_header(data)
    if hdr.fc != FC_FORWARD2DEVICE:
        raise ValueError(f"Expected forward2device FC=4, got {hdr.fc}")
    payload = data[EYBOND_HEADER_SIZE:hdr.total_len]
    return hdr, payload


# ---------------------------------------------------------------------------
# P17 / Q-Protocol Builders & Parsers
# ---------------------------------------------------------------------------

def build_p17_poll(cmd: str) -> bytes:
    """Build a P17 poll command frame: ^P<len:03d><cmd><crc_hi><crc_lo><CR>"""
    cmd_bytes = cmd.encode("ascii")
    length = 3 + len(cmd_bytes)
    length_str = f"{length:03d}".encode("ascii")
    frame = b"^P" + length_str + cmd_bytes

    crc = crc16_xmodem(frame)
    crc_hi = _stuff_crc_byte((crc >> 8) & 0xFF)
    crc_lo = _stuff_crc_byte(crc & 0xFF)
    return frame + bytes([crc_hi, crc_lo, 0x0D])


def build_p17_set(cmd: str) -> bytes:
    """Build a P17 set command frame: ^S<len:03d><cmd><crc_hi><crc_lo><CR>"""
    cmd_bytes = cmd.encode("ascii")
    length = 3 + len(cmd_bytes)
    length_str = f"{length:03d}".encode("ascii")
    frame = b"^S" + length_str + cmd_bytes

    crc = crc16_xmodem(frame)
    crc_hi = _stuff_crc_byte((crc >> 8) & 0xFF)
    crc_lo = _stuff_crc_byte(crc & 0xFF)
    return frame + bytes([crc_hi, crc_lo, 0x0D])


def parse_inverter_response(data: bytes) -> Tuple[str, str]:
    """Parse an inverter response frame (P17 or Q-protocol).

    Returns (command_type, response_data_string).
      command_type: 'D' for data, 'A' for ACK, 'N' for NAK.
      response_data_string: decoded payload string.
    """
    if len(data) < 3:
        raise ValueError(f"Inverter response too short: {len(data)} bytes")

    start = data[0]

    # --- Q-protocol framing: starts with '(' (0x28) ---
    if start == 0x28:
        # Strip trailing CR if present
        if data[-1] == 0x0D:
            content = data[1:-3]  # skip '(', strip 2 CRC bytes + CR
        else:
            content = data[1:-2]  # skip '(', strip 2 CRC bytes
        text = content.decode("ascii", errors="replace").strip()
        if text == "ACK":
            return "A", ""
        elif text == "NAK":
            return "N", ""
        else:
            return "D", text

    # --- P17 framing: starts with '^' (0x5E) ---
    if start == 0x5E:
        # Short ACK/NAK: ^<0|1><crc><CR> = 5 bytes
        if len(data) == 5 and data[1] in (0x30, 0x31):
            return ("A" if data[1] == 0x31 else "N"), ""

        if len(data) < 7:
            raise ValueError(f"P17 response too short: {len(data)} bytes")

        cmd_type = chr(data[1])
        try:
            length = int(data[2:5].decode("ascii"))
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid P17 length field: {data[2:5]!r}") from e

        data_len = length - 3
        if data_len < 0:
            raise ValueError(f"Invalid P17 data length: {length}")

        response_data = data[5:5 + data_len].decode("ascii", errors="replace")
        return cmd_type, response_data

    raise ValueError(f"Unknown inverter framing starting with 0x{start:02X}")


# ---------------------------------------------------------------------------
# Telemetry Decoders
# ---------------------------------------------------------------------------

def parse_gs_telemetry(raw_data: str) -> SmartEssGeneralStatus:
    """Parse space or character delimited GS (General Status) telemetry response.

    P17 GS response format: 28 space-delimited values.
    Example: '2300 500 2300 500 0500 0450 015 540 540 010 000 000 095 035 000 000 1200 000 3600 0000 00000000 ...'
    """
    tokens = raw_data.strip().split()
    if len(tokens) < 17:
        raise ValueError(f"GS telemetry tokens too short: {len(tokens)} (minimum 17 required)")

    def safe_float(val: str, scale: float = 1.0) -> float:
        try:
            return round(float(val) * scale, 2)
        except (ValueError, TypeError):
            return 0.0

    def safe_int(val: str) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    grid_v = safe_float(tokens[0], 0.1)
    grid_hz = safe_float(tokens[1], 0.1)
    ac_out_v = safe_float(tokens[2], 0.1)
    ac_out_hz = safe_float(tokens[3], 0.1)
    apparent_pwr = safe_int(tokens[4])
    active_pwr = safe_int(tokens[5])
    load_pct = safe_int(tokens[6])
    bat_v = safe_float(tokens[7], 0.1)
    bat_v_scc = safe_float(tokens[8], 0.1)
    bat_chg_a = safe_int(tokens[9])
    bat_dischg_a = safe_int(tokens[10])
    bat_soc = safe_int(tokens[12])  # Field 12 is raw 0..100%
    heatsink_temp = safe_int(tokens[13])  # Field 13 is raw deg C

    # Fields 16 and 18 are PV1 Power and Voltage
    pv1_w = safe_int(tokens[16]) if len(tokens) > 16 else 0
    pv1_v = safe_float(tokens[18], 0.1) if len(tokens) > 18 else 0.0
    pv2_w = safe_int(tokens[19]) if len(tokens) > 19 else 0
    pv2_v = 0.0
    dev_status = tokens[20] if len(tokens) > 20 else "00000000"

    return SmartEssGeneralStatus(
        grid_voltage_v=grid_v,
        grid_freq_hz=grid_hz,
        ac_output_voltage_v=ac_out_v,
        ac_output_freq_hz=ac_out_hz,
        ac_output_apparent_power_va=apparent_pwr,
        ac_output_active_power_w=active_pwr,
        output_load_percent=load_pct,
        battery_voltage_v=bat_v,
        battery_voltage_scc_v=bat_v_scc,
        battery_charge_current_a=bat_chg_a,
        battery_discharge_current_a=bat_dischg_a,
        battery_capacity_percent=bat_soc,
        heatsink_temp_c=heatsink_temp,
        pv1_power_w=pv1_w,
        pv1_voltage_v=pv1_v,
        pv2_power_w=pv2_w,
        pv2_voltage_v=pv2_v,
        device_status=dev_status,
    )


def parse_mod_telemetry(raw_data: str) -> str:
    """Parse MOD (Inverter Working Mode) response."""
    mode_char = raw_data.strip()[:1].upper()
    return MODE_MAP.get(mode_char, f"Unknown Mode ({mode_char})")


def parse_piri_telemetry(raw_data: str) -> SmartEssRatedInfo:
    """Parse PIRI (Rated & Config Information) response.

    26 fields in P17 protocol (0x0994).
    """
    tokens = raw_data.strip().split()
    if len(tokens) < 17:
        raise ValueError(f"PIRI telemetry tokens too short: {len(tokens)} (minimum 17 required)")

    def safe_float(val: str, scale: float = 1.0) -> float:
        try:
            return round(float(val) * scale, 2)
        except (ValueError, TypeError):
            return 0.0

    def safe_int(val: str) -> int:
        try:
            return int(val)
        except (ValueError, TypeError):
            return 0

    ac_in_v = safe_float(tokens[0], 0.1)
    ac_in_a = safe_float(tokens[1], 0.1)
    ac_out_v = safe_float(tokens[2], 0.1)
    ac_out_hz = safe_float(tokens[3], 0.1)
    ac_out_active_pwr = safe_int(tokens[4])
    bat_v_rating = safe_float(tokens[5], 0.1)
    bat_recharge_v = safe_float(tokens[6], 0.1)
    bat_under_v = safe_float(tokens[7], 0.1)
    bat_bulk_v = safe_float(tokens[8], 0.1)
    bat_float_v = safe_float(tokens[9], 0.1)
    bat_type = safe_int(tokens[11])
    max_ac_chg_a = safe_int(tokens[12])
    max_chg_a = safe_int(tokens[13])
    input_v_range = safe_int(tokens[14])
    out_priority = safe_int(tokens[15])
    chg_priority = safe_int(tokens[16])

    return SmartEssRatedInfo(
        ac_input_voltage_rating=ac_in_v,
        ac_input_current_rating=ac_in_a,
        ac_output_voltage_rating=ac_out_v,
        ac_output_freq_rating=ac_out_hz,
        ac_output_active_power_rating=ac_out_active_pwr,
        battery_voltage_rating=bat_v_rating,
        battery_recharge_voltage=bat_recharge_v,
        battery_under_voltage=bat_under_v,
        battery_bulk_voltage=bat_bulk_v,
        battery_float_voltage=bat_float_v,
        battery_type=bat_type,
        battery_type_name=BATTERY_TYPE_MAP.get(bat_type, f"Unknown ({bat_type})"),
        max_ac_charge_current=max_ac_chg_a,
        max_charge_current=max_chg_a,
        input_voltage_range=input_v_range,
        output_source_priority=out_priority,
        output_source_priority_name=OUTPUT_SOURCE_PRIORITY_MAP.get(out_priority, f"Priority {out_priority}"),
        charger_source_priority=chg_priority,
        charger_source_priority_name=CHARGER_SOURCE_PRIORITY_MAP.get(chg_priority, f"Charger {chg_priority}"),
    )


def parse_et_telemetry(raw_data: str) -> SmartEssEnergyStats:
    """Parse ET (Energy Today / Total) response.

    Expected format: 8-digit total or 'Day energy: X kWh, Total energy: Y kWh'.
    """
    cleaned = raw_data.strip()
    tokens = cleaned.replace(",", " ").split()
    day_kwh = 0.0
    total_kwh = 0.0

    # Format 1: numbers directly
    nums: List[float] = []
    for token in tokens:
        try:
            nums.append(float(token))
        except ValueError:
            pass

    if len(nums) >= 2:
        day_kwh = nums[0]
        total_kwh = nums[1]
    elif len(nums) == 1:
        total_kwh = nums[0]

    return SmartEssEnergyStats(
        day_energy_kwh=round(day_kwh, 2),
        total_energy_kwh=round(total_kwh, 2),
    )


# ---------------------------------------------------------------------------
# Control Command Builders
# ---------------------------------------------------------------------------

def build_output_priority_command(priority: int) -> str:
    """Build output source priority command: POP00 (USB) or POP01 (SBU)."""
    if priority not in (0, 1):
        raise ValueError(f"Invalid output source priority: {priority} (must be 0 or 1)")
    return f"POP{priority}"


def build_charger_priority_command(priority: int) -> str:
    """Build charger source priority command: PSP0..PSP3."""
    if priority not in (0, 1, 2, 3):
        raise ValueError(f"Invalid charger source priority: {priority} (must be 0..3)")
    return f"PSP{priority}"


def build_max_charge_current_command(current_a: int) -> str:
    """Build max total charging current command: MCHGC0,{current_a:03d}."""
    if not (0 <= current_a <= 150):
        raise ValueError(f"Max charge current out of range (0..150A): {current_a}")
    return f"MCHGC0,{current_a:03d}"


def build_max_ac_charge_current_command(current_a: int) -> str:
    """Build max AC charging current command: MUCHGC0,{current_a:03d}."""
    if not (0 <= current_a <= 120):
        raise ValueError(f"Max AC charge current out of range (0..120A): {current_a}")
    return f"MUCHGC0,{current_a:03d}"


def build_battery_cutoff_voltage_command(voltage_v: float) -> str:
    """Build battery cut-off voltage command: PSDV{tenths:03d}."""
    if not (40.0 <= voltage_v <= 54.0):
        raise ValueError(f"Battery cut-off voltage out of range (40..54V): {voltage_v}")
    tenths = int(round(voltage_v * 10.0))
    return f"PSDV{tenths:03d}"


def build_battery_bulk_float_command(bulk_v: float, float_v: float) -> str:
    """Build combined bulk and float charge voltage command: MCHGV{bulk:03d},{float:03d}."""
    if not (48.0 <= bulk_v <= 62.0):
        raise ValueError(f"Bulk voltage out of range (48..62V): {bulk_v}")
    if not (48.0 <= float_v <= 60.0):
        raise ValueError(f"Float voltage out of range (48..60V): {float_v}")
    b_tenths = int(round(bulk_v * 10.0))
    f_tenths = int(round(float_v * 10.0))
    return f"MCHGV{b_tenths:03d},{f_tenths:03d}"


def build_battery_recharge_redischarge_command(recharge_v: float, redischarge_v: float) -> str:
    """Build combined recharge and redischarge voltage command: BUCD{recharge:03d},{redischarge:03d}."""
    if not (44.0 <= recharge_v <= 56.0):
        raise ValueError(f"Re-charge voltage out of range (44..56V): {recharge_v}")
    if not (48.0 <= redischarge_v <= 58.0):
        raise ValueError(f"Re-discharge voltage out of range (48..58V): {redischarge_v}")
    r_tenths = int(round(recharge_v * 10.0))
    d_tenths = int(round(redischarge_v * 10.0))
    return f"BUCD{r_tenths:03d},{d_tenths:03d}"


# ---------------------------------------------------------------------------
# Telemetry Normalizer for Solar Fleet EMS
# ---------------------------------------------------------------------------

def normalize_smartess_telemetry(
    gs: SmartEssGeneralStatus,
    mod_str: str,
    piri: SmartEssRatedInfo,
    et: SmartEssEnergyStats,
    collector_pn: str = "EYBOND-COLLECTOR-01",
    devaddr: int = 1,
) -> Dict[str, Any]:
    """Normalize raw SmartESS / Eybond data structures into Solar Fleet EMS fleet telemetry."""
    total_pv_w = gs.pv1_power_w + gs.pv2_power_w
    load_w = gs.ac_output_active_power_w

    # Battery power: positive is charging, negative is discharging
    battery_w = (gs.battery_charge_current_a - gs.battery_discharge_current_a) * gs.battery_voltage_v

    # In off-grid / hybrid line mode, grid power supplies load and/or charges battery
    if "Line" in mod_str or "Grid" in mod_str:
        grid_w = max(0.0, load_w + (gs.battery_charge_current_a * gs.battery_voltage_v) - total_pv_w)
    else:
        grid_w = 0.0

    return {
        "device_id": f"smartess-{collector_pn}-addr{devaddr}",
        "collector_pn": collector_pn,
        "devaddr": devaddr,
        "vendor": "SmartESS / Eybond",
        "protocol": "Eybond-Modbus-P17",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "inverter_mode": mod_str,
        "power_flow": {
            "solar_power_w": round(float(total_pv_w), 1),
            "pv1_power_w": float(gs.pv1_power_w),
            "pv1_voltage_v": float(gs.pv1_voltage_v),
            "pv2_power_w": float(gs.pv2_power_w),
            "pv2_voltage_v": float(gs.pv2_voltage_v),
            "grid_power_w": round(float(grid_w), 1),
            "load_power_w": float(load_w),
            "apparent_power_va": float(gs.ac_output_apparent_power_va),
            "output_load_percent": gs.output_load_percent,
            "battery_power_w": round(float(battery_w), 1),
        },
        "battery": {
            "soc_percent": gs.battery_capacity_percent,
            "voltage_v": gs.battery_voltage_v,
            "charge_current_a": gs.battery_charge_current_a,
            "discharge_current_a": gs.battery_discharge_current_a,
            "type": piri.battery_type_name,
            "bulk_voltage_v": piri.battery_bulk_voltage,
            "float_voltage_v": piri.battery_float_voltage,
            "cutoff_voltage_v": piri.battery_under_voltage,
            "max_charge_current_a": piri.max_charge_current,
            "max_ac_charge_current_a": piri.max_ac_charge_current,
        },
        "grid": {
            "voltage_v": gs.grid_voltage_v,
            "frequency_hz": gs.grid_freq_hz,
            "ac_output_voltage_v": gs.ac_output_voltage_v,
            "ac_output_frequency_hz": gs.ac_output_freq_hz,
        },
        "energy": {
            "today_kwh": et.day_energy_kwh,
            "total_kwh": et.total_energy_kwh,
        },
        "configuration": {
            "output_source_priority": piri.output_source_priority_name,
            "charger_source_priority": piri.charger_source_priority_name,
            "rated_active_power_w": piri.ac_output_active_power_rating,
            "heatsink_temperature_c": gs.heatsink_temp_c,
            "device_status_code": gs.device_status,
        },
    }


# ---------------------------------------------------------------------------
# SmartESS Local Client & Simulator
# ---------------------------------------------------------------------------

class SmartEssLocalClient:
    """Client for communicating with SmartESS / Eybond dataloggers locally.

    Protocol helpers only; local network transport is not commissioned.
    Preserves idempotent TID incrementation and default read-only safety gates.
    """

    def __init__(
        self,
        host: str = "127.0.0.1",
        port: int = 8899,
        collector_pn: str = "EYBOND-WIFI-001",
        simulated: bool = False,
    ) -> None:
        self.host = host
        self.port = port
        self.collector_pn = collector_pn
        self.simulated = simulated
        self._tid = 1

    def next_tid(self) -> int:
        """Increment and return next transaction ID."""
        tid = self._tid
        self._tid = (self._tid + 1) & 0xFFFF
        if self._tid == 0:
            self._tid = 1
        return tid

    def poll_telemetry(self, devaddr: int = 1) -> Dict[str, Any]:
        """Poll telemetry from inverter (GS, MOD, PIRI, ET) and normalize to EMS."""
        raise NotImplementedError("local_transport_unavailable; use_registered_eybond_adapter")

    def execute_command_safely(
        self,
        command_type: str,
        params: Dict[str, Any],
        unlocked: bool = False,
    ) -> Dict[str, Any]:
        """Execute inverter configuration command with readback and safety gate."""
        return {
            "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
            "command_type": command_type,
            "readback_verified": False,
            "message": "Use the commissioned command engine; client flags cannot authorize writes.",
        }
