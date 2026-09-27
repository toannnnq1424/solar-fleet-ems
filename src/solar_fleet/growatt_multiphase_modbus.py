"""Growatt Multi-Phase (SPH & SPH TL3) Modbus Protocol and Controller.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
ha-growatt-modbus (MIT License, author @Lu-Fi).
Based on official Growatt PV Inverter Modbus RS485 RTU Protocol V1.20 and V3.05,
with empirical hardware verifications.

Key Capabilities:
- Automatic Device & Architecture Detection:
  * Holding Reg 43: Device Type Code (DTC)
  * Holding Reg 44: Tracker / Phase Register:
    - High byte = MPPT Tracker Count
    - Low byte = Output Phase Count (1-phase SPH vs 3-phase SPH TL3)
  * Holding Reg 23..27: Serial Number ASCII Decoder (5 words = 10 characters)
  * Holding Reg 9..11 & 12..14: Firmware & Control Firmware ASCII Decoders
  * Holding Reg 45..50: RTC System Clock Synchronization (Y, M, D, h, m, s)
- Export Limitation & Power Flow Regulators:
  * Holding Reg 0: Inverter Power State (0: Off, 1: On)
  * Holding Reg 122: Export Limitation Switch (0: Disabled, 1: Enabled)
  * Holding Reg 123: Export Limit Rate (0.0..100.0%, 0.1% resolution)
  * Holding Reg 3: Max Active Power Limit (0..100%)
  * Holding Reg 4: Max Reactive Power Limit (0..100%)
  * Holding Reg 608: Discharge Minimum SOC Limit (10..100%)
- Structured 3-Window TOU Programmers:
  * Grid First Windows (1080..1088):
    - Window 1: start 1080, stop 1081, enable 1082
    - Window 2: start 1083, stop 1084, enable 1085
    - Window 3: start 1086, stop 1087, enable 1088
    - Discharge Power Rate (1070: 0..100%), Stop SOC (1071: 0..100%)
  * Battery First Windows (1100..1108):
    - Window 1: start 1100, stop 1101, enable 1102
    - Window 2: start 1103, stop 1104, enable 1105
    - Window 3: start 1106, stop 1107, enable 1108
    - Charge Power Rate (1090: 0..100%), Stop SOC (1091: 0..100%)
    - AC Grid Charge Enable (1092: 0 = Off, 1 = On)
  * Time encoding: (hour << 8) | minute
- 112-Bit Comprehensive Fault / Warning Matrix (Input Regs 1001..1007):
  * Decodes 7 fault words into discrete, classified alerts (faults vs benign warnings).
- SPH TL3 3-Phase Symmetrical Telemetry Decoder:
  * Per-phase grid voltages (L1=38, L2=42, L3=46), powers (L1=40, L2=44, L3=48),
    line-to-line voltages (50..52), and 3-phase EPS backup outputs (1072..1079).
- Automatic Modbus Block Optimizer for Growatt:
  * Generates optimized read blocks for Fast, Energy, and Settings groups.
- All write commands remain locked under LOCKED_PENDING_HARDWARE_ACCEPTANCE.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants & Register Addresses
# ---------------------------------------------------------------------------

REG_DEVICE_TYPE_CODE = 43
REG_TRACKER_PHASE = 44
REG_SERIAL_START = 23
REG_SERIAL_COUNT = 5
REG_FW_ASCII_START = 9
REG_FW_ASCII_COUNT = 3
REG_CTRL_FW_START = 12
REG_CTRL_FW_COUNT = 3
REG_CLOCK_START = 45
REG_MODBUS_VERSION = 88

# Export & Control Holding Registers
REG_POWER_STATE = 0
REG_MAX_ACTIVE_POWER = 3
REG_MAX_REACTIVE_POWER = 4
REG_EXPORT_LIMIT_ENABLE = 122
REG_EXPORT_LIMIT_RATE = 123
REG_DISCHARGE_SOC_MIN = 608

# Grid First (Forced Discharge) Holding Registers
REG_GRID_FIRST_RATE = 1070
REG_GRID_FIRST_STOP_SOC = 1071
GRID_FIRST_WINDOWS = [
    {"start": 1080, "stop": 1081, "enable": 1082},
    {"start": 1083, "stop": 1084, "enable": 1085},
    {"start": 1086, "stop": 1087, "enable": 1088},
]

# Battery First (Forced Charge) Holding Registers
REG_BATTERY_FIRST_RATE = 1090
REG_BATTERY_FIRST_STOP_SOC = 1091
REG_AC_CHARGE_ENABLE = 1092
BATTERY_FIRST_WINDOWS = [
    {"start": 1100, "stop": 1101, "enable": 1102},
    {"start": 1103, "stop": 1104, "enable": 1105},
    {"start": 1106, "stop": 1107, "enable": 1108},
]

# Status & Derating Maps
INVERTER_STATUS_MAP = {
    0: "Waiting",
    1: "Normal",
    2: "Normal (Standby)",
    3: "Fault",
    4: "Flash / Programming",
    5: "Normal Hybrid",
    6: "Normal Hybrid (Battery)",
    7: "Normal Hybrid (Grid)",
    8: "Normal Hybrid (Bypass)",
}

INVERTER_MODE_MAP = {
    0: "Waiting",
    1: "Self Test",
    2: "Reserved",
    3: "System Fault",
    4: "Flash / Programming",
    5: "PV + Battery Online",
    6: "Battery Online",
    7: "PV Offline",
    8: "Battery Offline",
}

DERATING_MODE_MAP = {
    0: "No Derating",
    1: "PV Voltage High/Low",
    3: "Grid Voltage High/Low",
    4: "Grid Frequency High/Low",
    5: "Boost Temperature",
    6: "Inverter Temperature",
    7: "Remote / Command Control",
    9: "Overtemperature Recovery",
}


# ---------------------------------------------------------------------------
# Fault Bitfield Definitions (112 bits across Regs 1001..1007)
# ---------------------------------------------------------------------------

FAULT_MAPS: Dict[int, Dict[int, str]] = {
    1001: {
        0: "MasterForceINVFault",
        1: "MasterForceSPFault",
        2: "BusVoltHigh_TZ",
        3: "BusVoltHigh_ISR",
        8: "GridZClossFault",
        11: "GFCIHigh",
        12: "GridR_VFault",
        13: "GridS_VFault",
        14: "GridT_VFault",
        15: "GridFFault",
    },
    1002: {
        0: "RelayFault",
        1: "GFCIDamage",
        2: "GridR_VLowFault",
        3: "GridR_VHighFault",
        4: "GridS_VLowFault",
        5: "GridS_VHighFault",
        6: "GridT_VLowFault",
        7: "GridT_VHighFault",
        8: "INVCurrOCP_ISR",
        9: "INVCurrOCP_TZ",
        10: "DCIHigh",
        12: "INVR_CurrOCP_Rms",
        13: "INVS_CurrOCP_Rms",
        14: "INVT_CurrOCP_Rms",
        15: "NoUtility",
    },
    1003: {
        0: "GridFLowFault",
        1: "GridFHighFault",
        2: "GridVolt_Unbalance_Fault",
        3: "AC_PLL_Fault",
        4: "OverLoadFault",
        8: "EPS_LineVoltR_Loss",
        9: "EPS_LineVoltS_Loss",
        10: "EPS_LineVoltT_Loss",
    },
    1004: {
        0: "BatTerminalReversed",
        1: "BMS_Battery_Open",
        2: "BatteryVoltageLow",
    },
    1005: {
        5: "PV1_VoltLowWarn",
        6: "PV2_VoltLowWarn",
    },
    1006: {
        0: "NE_DetectFault",
        1: "PVISOFault",
        3: "BusVoltHighFault_ISR",
        4: "BusSampleFault",
        5: "UHCTFault",
        6: "AComFault",
        7: "BComFault",
        9: "AutoTestFault",
        11: "NTCOpenFault",
        13: "BBHeatsink_TempOver",
        14: "BBOCP_FaultISR",
        15: "INVHeatsink_Overtemp",
    },
    1007: {
        0: "PV1_VoltHighFault",
        1: "PV2_VoltHighFault",
        2: "BTHeatsink_Overtemp",
        3: "INVHeatsink_Overtemp",
        8: "BoostDriver1Warn",
        9: "BoostDriver2Warn",
        10: "WARN104",
        11: "PV1_ShortFault",
        12: "PV2_ShortFault",
        13: "Meter_COM_Loss",
        14: "PairingTimeOut",
        15: "CT_LN_Reversed",
    },
}

# Bits classified strictly as warnings rather than critical trip faults
WARNING_BITS: Dict[int, set[int]] = {
    1005: {5, 6},
    1007: {8, 9, 10},
}


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class DeviceIdentification:
    """Growatt Inverter Identity metadata."""
    device_type_code: int
    tracker_count: int
    phase_count: int
    profile_key: str
    serial_number: str
    firmware_version: str
    control_firmware_version: str
    modbus_version: int


@dataclass
class TimeWindow:
    """Parsed Growatt Time Window."""
    index: int
    name: str
    start_time: str
    stop_time: str
    enabled: bool


@dataclass
class GrowattAlarm:
    """Decoded Growatt Alarm or Warning."""
    register: int
    bit: int
    code: str
    severity: str  # "CRITICAL" or "WARNING"


# ---------------------------------------------------------------------------
# Decoder & Parser Helpers
# ---------------------------------------------------------------------------

def parse_tracker_phase(value: int) -> Tuple[int, int]:
    """Split holding register 44 into (tracker_count, phase_count)."""
    trackers = (value >> 8) & 0xFF
    phases = value & 0xFF
    return trackers, phases


def decode_ascii_registers(registers: Dict[int, int], start_addr: int, count: int) -> str:
    """Decode a range of 16-bit registers containing ASCII characters (big-endian)."""
    chars = []
    for i in range(count):
        val = registers.get(start_addr + i, 0)
        hi = (val >> 8) & 0xFF
        lo = val & 0xFF
        if hi != 0:
            chars.append(chr(hi))
        if lo != 0:
            chars.append(chr(lo))
    return "".join(chars).strip("\x00 \t\r\n")


def decode_time_window(start_val: int, stop_val: int, enable_val: int, index: int, name: str) -> TimeWindow:
    """Decode 16-bit time window registers (hour in high byte, minute in low byte)."""
    s_h = (start_val >> 8) & 0xFF
    s_m = start_val & 0xFF
    e_h = (stop_val >> 8) & 0xFF
    e_m = stop_val & 0xFF
    enabled = enable_val == 1

    return TimeWindow(
        index=index,
        name=name,
        start_time=f"{s_h:02d}:{s_m:02d}",
        stop_time=f"{e_h:02d}:{e_m:02d}",
        enabled=enabled,
    )


def encode_time_value(time_str: str) -> int:
    """Encode 'HH:MM' string into 16-bit integer (hour << 8 | min)."""
    parts = time_str.split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format '{time_str}'. Expected 'HH:MM'.")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Time out of bounds ({hour}:{minute}). Expected 00:00..23:59.")
    return ((hour & 0xFF) << 8) | (minute & 0xFF)


def decode_fault_registers(registers: Dict[int, int]) -> List[GrowattAlarm]:
    """Decode input registers 1001..1007 into structured GrowattAlarm instances."""
    alarms: List[GrowattAlarm] = []
    for reg_addr, bit_map in FAULT_MAPS.items():
        raw_val = registers.get(reg_addr, 0)
        if raw_val == 0:
            continue
        warn_set = WARNING_BITS.get(reg_addr, set())
        for bit_pos, code_name in bit_map.items():
            if (raw_val >> bit_pos) & 1:
                severity = "WARNING" if bit_pos in warn_set else "CRITICAL"
                alarms.append(GrowattAlarm(
                    register=reg_addr,
                    bit=bit_pos,
                    code=code_name,
                    severity=severity,
                ))
    return alarms


# ---------------------------------------------------------------------------
# Inverter Identification & Telemetry Decoder
# ---------------------------------------------------------------------------

def decode_growatt_identification(registers: Dict[int, int]) -> DeviceIdentification:
    """Decode identification registers into structured metadata."""
    dtc = registers.get(REG_DEVICE_TYPE_CODE, 0)
    tp_val = registers.get(REG_TRACKER_PHASE, 0x0201)
    trackers, phases = parse_tracker_phase(tp_val)
    if phases not in (1, 3):
        phases = 1

    profile_key = "sph_tl3" if phases == 3 else "sph"
    serial = decode_ascii_registers(registers, REG_SERIAL_START, REG_SERIAL_COUNT) or "UNKNOWN-SERIAL"
    fw_ver = decode_ascii_registers(registers, REG_FW_ASCII_START, REG_FW_ASCII_COUNT) or "UNKNOWN-FW"
    ctrl_fw = decode_ascii_registers(registers, REG_CTRL_FW_START, REG_CTRL_FW_COUNT) or "UNKNOWN-CTRL"
    mb_ver = registers.get(REG_MODBUS_VERSION, 0)

    return DeviceIdentification(
        device_type_code=dtc,
        tracker_count=trackers,
        phase_count=phases,
        profile_key=profile_key,
        serial_number=serial,
        firmware_version=fw_ver,
        control_firmware_version=ctrl_fw,
        modbus_version=mb_ver,
    )


def decode_growatt_multiphase_telemetry(
    input_regs: Dict[int, int],
    holding_regs: Dict[int, int],
) -> Dict[str, Any]:
    """Decode full 1-phase or 3-phase SPH telemetry and normalize to Solar Fleet EMS schema."""
    ident = decode_growatt_identification(holding_regs)

    def u32_val(high_addr: int) -> int:
        hi = input_regs.get(high_addr, 0)
        lo = input_regs.get(high_addr + 1, 0)
        return (hi << 16) | lo

    def s16_val(addr: int) -> int:
        v = input_regs.get(addr, 0)
        return v - 65536 if v >= 32768 else v

    # PV inputs
    pv_power_w = round(u32_val(1) * 0.1, 1)
    pv1_v = round(input_regs.get(3, 0) * 0.1, 1)
    pv1_a = round(input_regs.get(4, 0) * 0.1, 1)
    pv1_w = round(u32_val(5) * 0.1, 1)
    pv2_v = round(input_regs.get(7, 0) * 0.1, 1)
    pv2_a = round(input_regs.get(8, 0) * 0.1, 1)
    pv2_w = round(u32_val(9) * 0.1, 1)

    # Grid L1
    grid_v_l1 = round(input_regs.get(38, 0) * 0.1, 1)
    grid_p_l1 = round(u32_val(40) * 0.1, 1)

    # Grid L2 and L3 for 3-Phase SPH TL3
    is_3p = ident.phase_count == 3
    grid_v_l2 = round(input_regs.get(42, 0) * 0.1, 1) if is_3p else 0.0
    grid_p_l2 = round(u32_val(44) * 0.1, 1) if is_3p else 0.0
    grid_v_l3 = round(input_regs.get(46, 0) * 0.1, 1) if is_3p else 0.0
    grid_p_l3 = round(u32_val(48) * 0.1, 1) if is_3p else 0.0

    total_grid_w = round(grid_p_l1 + grid_p_l2 + grid_p_l3, 1) if is_3p else grid_p_l1

    # Battery
    bat_v = round(input_regs.get(1013, 0) * 0.1, 1)
    bat_a = round(s16_val(1014) * 0.1, 1)
    bat_w = round(s16_val(1009) * 1.0, 1)
    bat_soc = input_regs.get(1017, 0)

    # Load & EPS
    load_w = round(u32_val(1037) * 0.1, 1)
    eps_w = round(u32_val(1029) * 0.1, 1)

    # Inverter Status & Mode
    status_code = input_regs.get(0, 0)
    mode_code = input_regs.get(1000, 0)
    derating_code = input_regs.get(104, 0)

    # Alarms
    alarms = decode_fault_registers(input_regs)

    # Export limitation settings
    export_limit_enabled = holding_regs.get(REG_EXPORT_LIMIT_ENABLE, 0) == 1
    export_limit_rate = round(holding_regs.get(REG_EXPORT_LIMIT_RATE, 0) * 0.1, 1)
    discharge_soc_min = holding_regs.get(REG_DISCHARGE_SOC_MIN, 10)
    max_active_pwr = holding_regs.get(REG_MAX_ACTIVE_POWER, 100)

    # Time Windows
    grid_first_wins = [
        decode_time_window(
            holding_regs.get(w["start"], 0),
            holding_regs.get(w["stop"], 0),
            holding_regs.get(w["enable"], 0),
            idx + 1,
            f"Grid First Window {idx + 1}",
        )
        for idx, w in enumerate(GRID_FIRST_WINDOWS)
    ]
    bat_first_wins = [
        decode_time_window(
            holding_regs.get(w["start"], 0),
            holding_regs.get(w["stop"], 0),
            holding_regs.get(w["enable"], 0),
            idx + 1,
            f"Battery First Window {idx + 1}",
        )
        for idx, w in enumerate(BATTERY_FIRST_WINDOWS)
    ]

    return {
        "device_id": f"growatt-{ident.serial_number}",
        "vendor": "Growatt",
        "profile": ident.profile_key,
        "phase_count": ident.phase_count,
        "tracker_count": ident.tracker_count,
        "serial_number": ident.serial_number,
        "firmware_version": ident.firmware_version,
        "control_firmware_version": ident.control_firmware_version,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "status": {
            "code": status_code,
            "description": INVERTER_STATUS_MAP.get(status_code, f"Status {status_code}"),
            "mode_code": mode_code,
            "mode_description": INVERTER_MODE_MAP.get(mode_code, f"Mode {mode_code}"),
            "derating_code": derating_code,
            "derating_description": DERATING_MODE_MAP.get(derating_code, f"Derating {derating_code}"),
        },
        "power_flow": {
            "solar_power_w": pv_power_w,
            "pv1_power_w": pv1_w,
            "pv1_voltage_v": pv1_v,
            "pv1_current_a": pv1_a,
            "pv2_power_w": pv2_w,
            "pv2_voltage_v": pv2_v,
            "pv2_current_a": pv2_a,
            "grid_power_w": total_grid_w,
            "grid_l1_power_w": grid_p_l1,
            "grid_l2_power_w": grid_p_l2,
            "grid_l3_power_w": grid_p_l3,
            "load_power_w": load_w,
            "eps_backup_power_w": eps_w,
            "battery_power_w": bat_w,
        },
        "grid": {
            "voltage_l1_v": grid_v_l1,
            "voltage_l2_v": grid_v_l2,
            "voltage_l3_v": grid_v_l3,
        },
        "battery": {
            "soc_percent": bat_soc,
            "voltage_v": bat_v,
            "current_a": bat_a,
            "discharge_min_soc": discharge_soc_min,
        },
        "export_limitation": {
            "enabled": export_limit_enabled,
            "rate_percent": export_limit_rate,
            "max_active_power_percent": max_active_pwr,
        },
        "tou_schedule": {
            "grid_first_rate": holding_regs.get(REG_GRID_FIRST_RATE, 100),
            "grid_first_stop_soc": holding_regs.get(REG_GRID_FIRST_STOP_SOC, 10),
            "grid_first_windows": [asdict(w) for w in grid_first_wins],
            "battery_first_rate": holding_regs.get(REG_BATTERY_FIRST_RATE, 100),
            "battery_first_stop_soc": holding_regs.get(REG_BATTERY_FIRST_STOP_SOC, 100),
            "ac_charge_enabled": holding_regs.get(REG_AC_CHARGE_ENABLE, 0) == 1,
            "battery_first_windows": [asdict(w) for w in bat_first_wins],
        },
        "alarms": [
            {"register": a.register, "bit": a.bit, "code": a.code, "severity": a.severity}
            for a in alarms
        ],
    }


# ---------------------------------------------------------------------------
# Command Compilers with Strict Enforcements
# ---------------------------------------------------------------------------

def compile_export_limitation_command(enable: bool, limit_rate_pct: float = 100.0) -> Dict[str, Any]:
    """Compile Holding Registers 122 & 123 for Growatt Zero Feed-in / Export Limitation."""
    if not (0.0 <= limit_rate_pct <= 100.0):
        raise ValueError(f"Export limit rate out of range (0..100%): {limit_rate_pct}")
    raw_rate = int(round(limit_rate_pct * 10.0))

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "action": "export_limitation",
        "registers": {
            REG_EXPORT_LIMIT_ENABLE: 1 if enable else 0,
            REG_EXPORT_LIMIT_RATE: raw_rate,
        },
        "reason": "Export limitation command compiled. Hardware acceptance gate active.",
    }


def compile_grid_first_window_command(
    window_index: int,
    start_time: str,
    stop_time: str,
    enable: bool,
    discharge_rate_pct: int = 100,
    stop_soc_pct: int = 10,
) -> Dict[str, Any]:
    """Compile Grid First (Forced Discharge) window and limits."""
    if not (1 <= window_index <= 3):
        raise ValueError(f"Window index out of bounds (1..3): {window_index}")
    if not (0 <= discharge_rate_pct <= 100):
        raise ValueError(f"Discharge rate out of bounds: {discharge_rate_pct}")
    if not (0 <= stop_soc_pct <= 100):
        raise ValueError(f"Stop SOC out of bounds: {stop_soc_pct}")

    w = GRID_FIRST_WINDOWS[window_index - 1]
    start_raw = encode_time_value(start_time)
    stop_raw = encode_time_value(stop_time)

    regs = {
        w["start"]: start_raw,
        w["stop"]: stop_raw,
        w["enable"]: 1 if enable else 0,
        REG_GRID_FIRST_RATE: discharge_rate_pct,
        REG_GRID_FIRST_STOP_SOC: stop_soc_pct,
    }

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "action": f"grid_first_window_{window_index}",
        "registers": regs,
        "reason": f"Grid First window {window_index} command compiled. Hardware acceptance gate active.",
    }


def compile_battery_first_window_command(
    window_index: int,
    start_time: str,
    stop_time: str,
    enable: bool,
    ac_charge_enable: bool = True,
    charge_rate_pct: int = 100,
    stop_soc_pct: int = 100,
) -> Dict[str, Any]:
    """Compile Battery First (Forced Charge) window, AC charging toggle, and limits."""
    if not (1 <= window_index <= 3):
        raise ValueError(f"Window index out of bounds (1..3): {window_index}")
    if not (0 <= charge_rate_pct <= 100):
        raise ValueError(f"Charge rate out of bounds: {charge_rate_pct}")
    if not (0 <= stop_soc_pct <= 100):
        raise ValueError(f"Stop SOC out of bounds: {stop_soc_pct}")

    w = BATTERY_FIRST_WINDOWS[window_index - 1]
    start_raw = encode_time_value(start_time)
    stop_raw = encode_time_value(stop_time)

    regs = {
        w["start"]: start_raw,
        w["stop"]: stop_raw,
        w["enable"]: 1 if enable else 0,
        REG_AC_CHARGE_ENABLE: 1 if ac_charge_enable else 0,
        REG_BATTERY_FIRST_RATE: charge_rate_pct,
        REG_BATTERY_FIRST_STOP_SOC: stop_soc_pct,
    }

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "action": f"battery_first_window_{window_index}",
        "registers": regs,
        "reason": f"Battery First window {window_index} command compiled. Hardware acceptance gate active.",
    }


# ---------------------------------------------------------------------------
# Modbus Block Optimizer for Growatt
# ---------------------------------------------------------------------------

def plan_growatt_modbus_blocks(addresses: List[int], max_gap: int = 30, max_block: int = 110) -> List[Tuple[int, int]]:
    """Merge sorted addresses into compact, gap-tolerant read blocks (start_address, count)."""
    if not addresses:
        return []
    sorted_addrs = sorted(set(addresses))
    blocks: List[Tuple[int, int]] = []
    start = prev = sorted_addrs[0]

    for addr in sorted_addrs[1:]:
        if (addr - prev > max_gap) or (addr - start + 1 > max_block):
            blocks.append((start, prev - start + 1))
            start = addr
        prev = addr
    blocks.append((start, prev - start + 1))
    return blocks
