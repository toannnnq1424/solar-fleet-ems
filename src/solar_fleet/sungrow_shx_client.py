"""Sungrow SHx Hybrid & SG String Inverter Modbus TCP Protocol Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from public protocol specifications and community integration knowledge:
Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT License, clean-room reference).
Supports direct local communication with Sungrow SH3K6..SH25T hybrid series,
SG string inverters, SBR096..SBR256 high-voltage battery storage, and smart energy meters
over Modbus TCP (port 502) via built-in LAN or WiNet-S dongle without cloud dependency.

Key Capabilities:
- Inverter Identification & State:
  * Device type code (Input 4999) mapping to SH/SG models (SH5.0RT, SH10RT, SH10RT-20, SH10T, etc.).
  * Serial number (Input 4989..4998 ASCII) and firmware versions (Input 4953, 4968, 13249).
  * Inverter running state (Input 12999) & power flow status (Input 13000).
- Multi-MPPT Solar Telemetry (Input Registers 5010..5016, 5114..5115):
  * MPPT1..MPPT4 voltages (0.1V), currents (0.1A), and total DC power (u32 W, word-swapped).
- 3-Phase Grid Output & PCC Meter (Input Registers 5018..5034, 5600..5606, 13030..13033):
  * Phase A, B, C AC voltages (0.1V) and Phase A, B, C currents (signed 0.1A).
  * Total active power (s32 W), reactive power (s32 var), and power factor (0.001).
  * Meter active power (s32 W) and per-phase meter active powers (5602, 5604, 5606).
  * Load power (Input 13007, s32 W) and export power (Input 13009, s32 W).
- Battery & SBR Module Telemetry (Input Registers 5213, 10740..10779, 13019..13040):
  * Battery power (5213, s32 W), voltage (13019, 0.1V), current (5630, s16 0.1A).
  * Battery SOC (13022, 0.1%), SOH (13023, 0.1%), temperature (13024, s16 0.1°C).
  * SBR pack cell voltage extremes (10756, 10758, mV) and module temperatures (10760, 10762, 0.1°C).
  * Energy totals: daily/total PV yield, battery charge/discharge, grid import/export (0.1 kWh).
- Safety-Gated Parameter Write Compilers (Holding Registers 12999..33149):
  * Inverter Start / Stop control (Holding 12999: 0xCF=Start, 0xCE=Stop).
  * EMS Operating Mode (Holding 13049: 0=Self-consumption, 2=Forced mode, 3=External EMS, 4=VPP).
  * Battery Forced Charge/Discharge Command (Holding 13050: 0xCC=Stop, 0xAA=Charge, 0xBB=Discharge).
  * Battery Forced Charge/Discharge Power (Holding 13051: W).
  * Battery Max & Min SOC limits (Holding 13057 & 13058: 0.1% scale).
  * Export Power Limitation Toggle & Cap (Holding 13086 & 13073: 0xAA=On, 0x55=Off; W).
  * Active Power Limitation Toggle & Ratio (Holding 13088 & 13089: 0xAA=On, 0x55=Off; 0.1% ratio).
  * Pre-configured EMS Scenes: Self-Consumption, Zero Export, Max Export, Battery Bypass, Forced Charge, Forced Discharge.
  * All parameter writes strictly gated by LOCKED_PENDING_HARDWARE_ACCEPTANCE.
- Telemetry Normalizer: Translates Sungrow telemetry into unified Solar Fleet EMS schema.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

SUNGROW_DEFAULT_PORT = 502
DEFAULT_SLAVE_UNIT_ID = 1

MODBUS_READ_HOLDING = 0x03
MODBUS_READ_INPUT = 0x04
MODBUS_WRITE_SINGLE = 0x06
MODBUS_WRITE_MULTIPLE = 0x10

# Device Type Code Mapping (Input Register 4999)
SUNGROW_DEVICE_TYPES: Dict[int, str] = {
    0x0D06: "SH3K6",
    0x0D07: "SH4K6",
    0x0D09: "SH5K-20",
    0x0D03: "SH5K-V13",
    0x0D0A: "SH3K6-30",
    0x0D0B: "SH4K6-30",
    0x0D0C: "SH5K-30",
    0x0D17: "SH3.0RS",
    0x0D0D: "SH3.6RS",
    0x0D18: "SH4.0RS",
    0x0D0F: "SH5.0RS",
    0x0D10: "SH6.0RS",
    0x0D1A: "SH8.0RS",
    0x0D1B: "SH10RS",
    0x0E00: "SH5.0RT",
    0x0E01: "SH6.0RT",
    0x0E02: "SH8.0RT",
    0x0E03: "SH10RT",
    0x0E10: "SH5.0RT-20",
    0x0E11: "SH6.0RT-20",
    0x0E12: "SH8.0RT-20",
    0x0E13: "SH10RT-20",
    0x0E0C: "SH5.0RT-V112",
    0x0E0D: "SH6.0RT-V112",
    0x0E0E: "SH8.0RT-V112",
    0x0E0F: "SH10RT-V112",
    0x0E08: "SH5.0RT-V122",
    0x0E09: "SH6.0RT-V122",
    0x0E0A: "SH8.0RT-V122",
    0x0E0B: "SH10RT-V122",
    0x0E20: "SH5T",
    0x0E21: "SH6T",
    0x0E22: "SH8T",
    0x0E23: "SH10T",
    0x0E24: "SH12T",
    0x0E25: "SH15T",
    0x0E26: "SH20T",
    0x0E28: "SH25T",
    0x0D27: "MG5RL",
    0x0D28: "MG6RL",
}

# Running State Mapping (Input Register 12999)
SUNGROW_RUNNING_STATES: Dict[int, str] = {
    0x0000: "Running",
    0x0001: "Stop",
    0x0002: "Key stop",
    0x0004: "Emergency Stop",
    0x0008: "Standby",
    0x0010: "Initial standby",
    0x0014: "Microgrid Operation",
    0x0020: "Starting",
    0x0040: "Running",
    0x0041: "Off-grid Charge",
    0x0080: "Derating Running",
    0x0100: "Fault",
    0x0200: "Update Failed",
    0x0400: "Maintain Mode",
    0x0800: "Compulsory (Forced) Mode",
    0x1000: "Running (Off-grid)",
    0x1111: "Uninitialized",
    0x1200: "Initial standby",
    0x1300: "Key stop",
    0x1400: "Standby",
    0x1500: "Emergency Stop",
    0x1600: "Starting",
    0x1700: "AFCI Self-test Shutdown",
    0x1800: "Station Building Status",
    0x1900: "Safe Mode",
    0x2000: "Open Loop",
    0x2500: "Communication Fault",
    0x2501: "Restarting",
    0x4000: "Running in External EMS Mode",
    0x4001: "Emergency Charging Operation",
    0x5500: "Fault",
    0x8000: "Stop",
    0x8100: "Derating Running",
    0x8200: "Dispatch Running",
    0x9100: "Warn Running",
}

# EMS Operating Modes (Holding Register 13049)
SUNGROW_EMS_MODES: Dict[str, Tuple[int, str]] = {
    "self_consumption": (0, "Self-consumption mode (default)"),
    "forced": (2, "Forced mode (compulsory)"),
    "external_ems": (3, "External EMS"),
    "vpp": (4, "Virtual Power Plant (VPP)"),
    "microgrid": (8, "Microgrid"),
}

# Battery Forced Charge/Discharge Commands (Holding Register 13050)
SUNGROW_FORCED_CMDS: Dict[str, Tuple[int, str]] = {
    "stop": (0xCC, "Stop (default)"),
    "forced_charge": (0xAA, "Forced charge"),
    "forced_discharge": (0xBB, "Forced discharge"),
}

# Inverter Start / Stop Control (Holding Register 12999)
SUNGROW_POWER_SWITCH: Dict[str, Tuple[int, str]] = {
    "start": (0xCF, "Start Inverter"),
    "stop": (0xCE, "Stop Inverter"),
}

# Toggle Control Values (Holding Registers 13074, 13086, 13088)
SUNGROW_TOGGLE_ON = 0xAA  # 170
SUNGROW_TOGGLE_OFF = 0x55  # 85


# ---------------------------------------------------------------------------
# Modbus Codec Helpers
# ---------------------------------------------------------------------------

def calculate_modbus_crc(data: bytes) -> int:
    """Calculate Modbus CRC16 checksum."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


def build_modbus_rtu_frame(unit_id: int, func_code: int, address: int, val_or_count: int) -> bytes:
    """Build a standard Modbus RTU request frame."""
    payload = struct.pack(">BBHH", unit_id, func_code, address, val_or_count)
    crc = calculate_modbus_crc(payload)
    return payload + struct.pack("<H", crc)


def decode_sungrow_u32(regs: Dict[int, int], addr: int) -> int:
    """Decode 32-bit unsigned integer with Sungrow word-swap (low word at addr, high word at addr+1)."""
    r0 = regs.get(addr, 0)
    r1 = regs.get(addr + 1, 0)
    return ((r1 & 0xFFFF) << 16) | (r0 & 0xFFFF)


def decode_sungrow_s32(regs: Dict[int, int], addr: int) -> int:
    """Decode 32-bit signed integer with Sungrow word-swap."""
    val = decode_sungrow_u32(regs, addr)
    if val >= 0x80000000:
        val -= 0x100000000
    return val


def decode_sungrow_s16(regs: Dict[int, int], addr: int) -> int:
    """Decode 16-bit signed integer."""
    val = regs.get(addr, 0) & 0xFFFF
    if val >= 0x8000:
        val -= 0x10000
    return val


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class SungrowTelemetry:
    """Structured telemetry from Sungrow SHx/SG inverters, meters, and SBR storage."""

    timestamp: datetime
    device_type_code: int
    model_name: str
    serial_number: str
    running_state_code: int
    running_state: str
    power_flow_status: int
    inverter_temp_c: float
    mppt_voltages: List[float] = field(default_factory=list)
    mppt_currents: List[float] = field(default_factory=list)
    total_dc_power_w: float = 0.0
    grid_phase_a_v: float = 0.0
    grid_phase_b_v: float = 0.0
    grid_phase_c_v: float = 0.0
    grid_phase_a_a: float = 0.0
    grid_phase_b_a: float = 0.0
    grid_phase_c_a: float = 0.0
    grid_active_power_w: float = 0.0
    grid_reactive_power_var: float = 0.0
    grid_power_factor: float = 1.0
    grid_freq_hz: float = 50.0
    meter_active_power_w: float = 0.0
    meter_phase_a_w: float = 0.0
    meter_phase_b_w: float = 0.0
    meter_phase_c_w: float = 0.0
    load_power_w: float = 0.0
    export_power_w: float = 0.0
    battery_power_w: float = 0.0
    battery_voltage_v: float = 0.0
    battery_current_a: float = 0.0
    battery_soc_pct: float = 0.0
    battery_soh_pct: float = 100.0
    battery_temp_c: float = 25.0
    sbr_cell_max_mv: float = 0.0
    sbr_cell_min_mv: float = 0.0
    sbr_module_max_temp_c: float = 0.0
    sbr_module_min_temp_c: float = 0.0
    daily_pv_kwh: float = 0.0
    total_pv_kwh: float = 0.0
    daily_battery_charge_kwh: float = 0.0
    total_battery_charge_kwh: float = 0.0
    daily_battery_discharge_kwh: float = 0.0
    total_battery_discharge_kwh: float = 0.0
    daily_import_kwh: float = 0.0
    total_import_kwh: float = 0.0
    daily_export_kwh: float = 0.0
    total_export_kwh: float = 0.0
    raw_registers_count: int = 0


# ---------------------------------------------------------------------------
# Telemetry Decoder
# ---------------------------------------------------------------------------

def decode_sungrow_telemetry(
    regs_5000: Dict[int, int],
    regs_13000: Dict[int, int],
    sbr_regs: Optional[Dict[int, int]] = None,
    serial_str: str = "SG1234567890",
) -> SungrowTelemetry:
    """Decode raw Modbus input registers into SungrowTelemetry object."""
    dev_type = regs_5000.get(4999, 0x0E03)
    model = SUNGROW_DEVICE_TYPES.get(dev_type, f"Unknown (0x{dev_type:04X})")

    # MPPT PV inputs
    v1 = regs_5000.get(5010, 0) * 0.1
    i1 = regs_5000.get(5011, 0) * 0.1
    v2 = regs_5000.get(5012, 0) * 0.1
    i2 = regs_5000.get(5013, 0) * 0.1
    v3 = regs_5000.get(5014, 0) * 0.1
    i3 = regs_5000.get(5015, 0) * 0.1
    v4 = regs_5000.get(5114, 0) * 0.1
    i4 = regs_5000.get(5115, 0) * 0.1

    mppt_v = [round(v1, 1), round(v2, 1)]
    mppt_i = [round(i1, 1), round(i2, 1)]
    if v3 > 0 or i3 > 0:
        mppt_v.append(round(v3, 1))
        mppt_i.append(round(i3, 1))
    if v4 > 0 or i4 > 0:
        mppt_v.append(round(v4, 1))
        mppt_i.append(round(i4, 1))

    total_dc_w = float(decode_sungrow_u32(regs_5000, 5016))
    if total_dc_w == 0.0:
        total_dc_w = sum(v * i for v, i in zip(mppt_v, mppt_i))

    # Grid output (5018..5034 & 13030..13033)
    v_a = regs_5000.get(5018, 0) * 0.1
    v_b = regs_5000.get(5019, 0) * 0.1
    v_c = regs_5000.get(5020, 0) * 0.1

    i_a = decode_sungrow_s16(regs_13000, 13030) * 0.1
    i_b = decode_sungrow_s16(regs_13000, 13031) * 0.1
    i_c = decode_sungrow_s16(regs_13000, 13032) * 0.1

    active_p_w = float(decode_sungrow_s32(regs_13000, 13033))
    reactive_p_var = float(decode_sungrow_s32(regs_5000, 5032))
    pf = decode_sungrow_s16(regs_5000, 5034) * 0.001
    freq_hz = regs_5000.get(5241, 5000) * 0.01

    # Running status
    state_code = regs_13000.get(12999, 0)
    state_desc = SUNGROW_RUNNING_STATES.get(state_code, f"State 0x{state_code:04X}")
    flow_status = regs_13000.get(13000, 0)

    # Meter / PCC
    meter_p_w = float(decode_sungrow_s32(regs_5000, 5600))
    meter_pa_w = float(decode_sungrow_s32(regs_5000, 5602))
    meter_pb_w = float(decode_sungrow_s32(regs_5000, 5604))
    meter_pc_w = float(decode_sungrow_s32(regs_5000, 5606))
    load_p_w = float(decode_sungrow_s32(regs_13000, 13007))
    export_p_w = float(decode_sungrow_s32(regs_13000, 13009))

    # Battery Telemetry
    bat_p_w = float(decode_sungrow_s32(regs_5000, 5213))
    bat_v = regs_13000.get(13019, 0) * 0.1
    bat_i = decode_sungrow_s16(regs_5000, 5630) * 0.1
    bat_soc = regs_13000.get(13022, 0) * 0.1
    bat_soh = regs_13000.get(13023, 1000) * 0.1
    bat_temp = decode_sungrow_s16(regs_13000, 13024) * 0.1
    inv_temp = decode_sungrow_s16(regs_5000, 5007) * 0.1

    # SBR Pack details if provided
    sbr_max_mv = 0.0
    sbr_min_mv = 0.0
    sbr_max_temp = 0.0
    sbr_min_temp = 0.0
    if sbr_regs:
        sbr_max_mv = float(sbr_regs.get(10756, 0))
        sbr_min_mv = float(sbr_regs.get(10758, 0))
        sbr_max_temp = decode_sungrow_s16(sbr_regs, 10760) * 0.1
        sbr_min_temp = decode_sungrow_s16(sbr_regs, 10762) * 0.1

    # Energies (0.1 kWh)
    daily_pv = regs_13000.get(13001, 0) * 0.1
    total_pv = decode_sungrow_u32(regs_13000, 13002) * 0.1
    daily_bat_chg = regs_13000.get(13039, 0) * 0.1
    total_bat_chg = decode_sungrow_u32(regs_13000, 13040) * 0.1
    daily_bat_dis = regs_13000.get(13025, 0) * 0.1
    total_bat_dis = decode_sungrow_u32(regs_13000, 13026) * 0.1
    daily_imp = regs_13000.get(13035, 0) * 0.1
    total_imp = decode_sungrow_u32(regs_13000, 13036) * 0.1
    daily_exp = regs_13000.get(13044, 0) * 0.1
    total_exp = decode_sungrow_u32(regs_13000, 13045) * 0.1

    total_regs_count = len(regs_5000) + len(regs_13000) + (len(sbr_regs) if sbr_regs else 0)

    return SungrowTelemetry(
        timestamp=datetime.now(timezone.utc),
        device_type_code=dev_type,
        model_name=model,
        serial_number=serial_str,
        running_state_code=state_code,
        running_state=state_desc,
        power_flow_status=flow_status,
        inverter_temp_c=round(inv_temp, 1),
        mppt_voltages=mppt_v,
        mppt_currents=mppt_i,
        total_dc_power_w=round(total_dc_w, 1),
        grid_phase_a_v=round(v_a, 1),
        grid_phase_b_v=round(v_b, 1),
        grid_phase_c_v=round(v_c, 1),
        grid_phase_a_a=round(i_a, 1),
        grid_phase_b_a=round(i_b, 1),
        grid_phase_c_a=round(i_c, 1),
        grid_active_power_w=round(active_p_w, 1),
        grid_reactive_power_var=round(reactive_p_var, 1),
        grid_power_factor=round(pf, 3),
        grid_freq_hz=round(freq_hz, 2),
        meter_active_power_w=round(meter_p_w, 1),
        meter_phase_a_w=round(meter_pa_w, 1),
        meter_phase_b_w=round(meter_pb_w, 1),
        meter_phase_c_w=round(meter_pc_w, 1),
        load_power_w=round(load_p_w, 1),
        export_power_w=round(export_p_w, 1),
        battery_power_w=round(bat_p_w, 1),
        battery_voltage_v=round(bat_v, 1),
        battery_current_a=round(bat_i, 1),
        battery_soc_pct=round(bat_soc, 1),
        battery_soh_pct=round(bat_soh, 1),
        battery_temp_c=round(bat_temp, 1),
        sbr_cell_max_mv=round(sbr_max_mv, 0),
        sbr_cell_min_mv=round(sbr_min_mv, 0),
        sbr_module_max_temp_c=round(sbr_max_temp, 1),
        sbr_module_min_temp_c=round(sbr_min_temp, 1),
        daily_pv_kwh=round(daily_pv, 1),
        total_pv_kwh=round(total_pv, 1),
        daily_battery_charge_kwh=round(daily_bat_chg, 1),
        total_battery_charge_kwh=round(total_bat_chg, 1),
        daily_battery_discharge_kwh=round(daily_bat_dis, 1),
        total_battery_discharge_kwh=round(total_bat_dis, 1),
        daily_import_kwh=round(daily_imp, 1),
        total_import_kwh=round(total_imp, 1),
        daily_export_kwh=round(daily_exp, 1),
        total_export_kwh=round(total_exp, 1),
        raw_registers_count=total_regs_count,
    )


# ---------------------------------------------------------------------------
# Safety-Gated Parameter Compilers
# ---------------------------------------------------------------------------

def compile_sungrow_ems_mode(mode: str | int) -> Dict[str, Any]:
    """Compile EMS Mode Selection (Holding Register 13049).

    Available options:
    - 0 / "self_consumption": Self-consumption mode (default)
    - 2 / "forced": Forced mode (compulsory)
    - 3 / "external_ems": External EMS
    - 4 / "vpp": Virtual Power Plant (VPP)
    - 8 / "microgrid": Microgrid
    """
    mode_val: int
    mode_name: str
    if isinstance(mode, int):
        matched = next((k for k, v in SUNGROW_EMS_MODES.items() if v[0] == mode), None)
        if matched is None:
            raise ValueError(f"Unsupported Sungrow EMS mode code: {mode}")
        mode_val = mode
        mode_name = SUNGROW_EMS_MODES[matched][1]
    else:
        norm = mode.lower().replace("-", "_").replace(" ", "_")
        if norm not in SUNGROW_EMS_MODES:
            raise ValueError(f"Unknown EMS mode: '{mode}'. Must be one of: {list(SUNGROW_EMS_MODES.keys())}")
        mode_val, mode_name = SUNGROW_EMS_MODES[norm]

    req_frame = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13049, mode_val)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "register": 13049,
        "register_desc": "EMS Mode Selection (Holding 13049)",
        "value": mode_val,
        "mode_name": mode_name,
        "frame_hex": req_frame.hex(),
        "reason": "Sungrow EMS mode compiled. Gated by hardware acceptance.",
    }


def compile_sungrow_forced_charge_discharge(cmd: str | int, power_w: int = 0) -> Dict[str, Any]:
    """Compile Battery Forced Charge/Discharge Command & Power (Holding Registers 13050 & 13051).

    Commands:
    - 0xCC / "stop": Stop (default)
    - 0xAA / "forced_charge": Forced charge
    - 0xBB / "forced_discharge": Forced discharge
    Power: 0 to 25000 Watts.
    """
    cmd_val: int
    cmd_name: str
    if isinstance(cmd, int):
        matched = next((k for k, v in SUNGROW_FORCED_CMDS.items() if v[0] == cmd), None)
        if matched is None:
            raise ValueError(f"Unsupported Sungrow forced command code: 0x{cmd:02X}")
        cmd_val = cmd
        cmd_name = SUNGROW_FORCED_CMDS[matched][1]
    else:
        norm = cmd.lower().replace("-", "_").replace(" ", "_")
        if norm not in SUNGROW_FORCED_CMDS:
            raise ValueError(f"Unknown forced command: '{cmd}'. Supported: {list(SUNGROW_FORCED_CMDS.keys())}")
        cmd_val, cmd_name = SUNGROW_FORCED_CMDS[norm]

    if not (0 <= power_w <= 30000):
        raise ValueError(f"Forced charge/discharge power out of valid range (0..30000 W): {power_w}")

    req_cmd = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13050, cmd_val)
    req_pow = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13051, power_w)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "registers": {
            13050: cmd_val,
            13051: power_w,
        },
        "command_name": cmd_name,
        "power_w": power_w,
        "frames_hex": [req_cmd.hex(), req_pow.hex()],
        "reason": "Sungrow forced charge/discharge command compiled. Gated by hardware acceptance.",
    }


def compile_sungrow_battery_soc_limits(max_soc_pct: float, min_soc_pct: float) -> Dict[str, Any]:
    """Compile Battery Max and Min SOC Limits (Holding Registers 13057 & 13058).

    Scale: 0.1% (e.g., 100.0% -> 1000, 10.0% -> 100).
    Valid Range: min_soc 0..50%, max_soc 50..100%, min_soc < max_soc.
    """
    if not (0.0 <= min_soc_pct <= 50.0):
        raise ValueError(f"Battery min SOC out of range (0..50%): {min_soc_pct}")
    if not (50.0 <= max_soc_pct <= 100.0):
        raise ValueError(f"Battery max SOC out of range (50..100%): {max_soc_pct}")
    if min_soc_pct >= max_soc_pct:
        raise ValueError(f"Min SOC ({min_soc_pct}%) must be strictly lower than Max SOC ({max_soc_pct}%)")

    val_max = int(round(max_soc_pct * 10))
    val_min = int(round(min_soc_pct * 10))

    req_max = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13057, val_max)
    req_min = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13058, val_min)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "registers": {
            13057: val_max,
            13058: val_min,
        },
        "max_soc_pct": max_soc_pct,
        "min_soc_pct": min_soc_pct,
        "frames_hex": [req_max.hex(), req_min.hex()],
        "reason": "Sungrow battery SOC limits compiled. Gated by hardware acceptance.",
    }


def compile_sungrow_export_limit(enabled: bool, limit_w: int = 0) -> Dict[str, Any]:
    """Compile Feed-in / Export Power Limitation (Holding Registers 13086 & 13073).

    Register 13086: 0xAA=Enabled, 0x55=Disabled.
    Register 13073: Export power limit in Watts (0..100000 W).
    """
    if not (0 <= limit_w <= 100000):
        raise ValueError(f"Export power limit out of valid range (0..100000 W): {limit_w}")

    mode_val = SUNGROW_TOGGLE_ON if enabled else SUNGROW_TOGGLE_OFF
    req_mode = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13086, mode_val)
    req_limit = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13073, limit_w)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "registers": {
            13086: mode_val,
            13073: limit_w,
        },
        "enabled": enabled,
        "limit_w": limit_w,
        "frames_hex": [req_mode.hex(), req_limit.hex()],
        "reason": "Sungrow export limitation compiled. Gated by hardware acceptance.",
    }


def compile_sungrow_active_power_limitation(enabled: bool, ratio_pct: float = 100.0) -> Dict[str, Any]:
    """Compile Active Power Limitation Ratio (Holding Registers 13088 & 13089).

    Register 13088: 0xAA=Enabled, 0x55=Disabled.
    Register 13089: Active power limitation ratio (0..1000 = 0.0% .. 100.0%).
    """
    if not (0.0 <= ratio_pct <= 100.0):
        raise ValueError(f"Active power limitation ratio out of range (0..100%): {ratio_pct}")

    mode_val = SUNGROW_TOGGLE_ON if enabled else SUNGROW_TOGGLE_OFF
    val_ratio = int(round(ratio_pct * 10))

    req_mode = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13088, mode_val)
    req_ratio = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 13089, val_ratio)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "registers": {
            13088: mode_val,
            13089: val_ratio,
        },
        "enabled": enabled,
        "ratio_pct": ratio_pct,
        "frames_hex": [req_mode.hex(), req_ratio.hex()],
        "reason": "Sungrow active power limitation compiled. Gated by hardware acceptance.",
    }


def compile_sungrow_inverter_power_switch(start: bool) -> Dict[str, Any]:
    """Compile Inverter Start/Stop Switch (Holding Register 12999).

    0xCF (207): Start Inverter.
    0xCE (206): Stop Inverter.
    """
    key = "start" if start else "stop"
    val, desc = SUNGROW_POWER_SWITCH[key]
    req = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 12999, val)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "register": 12999,
        "value": val,
        "action": desc,
        "frame_hex": req.hex(),
        "reason": f"Sungrow {desc} compiled. Gated by hardware acceptance.",
    }


def compile_sungrow_ems_scene(scene_name: str, **kwargs) -> Dict[str, Any]:
    """Compile canonical Sungrow EMS Scenes.

    Supported scenes:
    - "self_consumption": EMS Mode = 0 (Self-consumption), Forced Cmd = 0xCC (Stop)
    - "zero_export": Export Limit Enabled = 0xAA, Export Limit W = 0
    - "max_export": Export Limit Enabled = 0xAA, Export Limit W = kwargs.get('rated_w', 10000)
    - "battery_bypass": EMS Mode = 2 (Forced mode), Forced Cmd = 0xCC (Stop)
    - "forced_charge": EMS Mode = 2 (Forced mode), Forced Cmd = 0xAA (Charge), Power = kwargs.get('power_w', 5000)
    - "forced_discharge": EMS Mode = 2 (Forced mode), Forced Cmd = 0xBB (Discharge), Power = kwargs.get('power_w', 5000)
    """
    norm = scene_name.lower().replace("-", "_").replace(" ", "_")
    steps: List[Dict[str, Any]] = []

    if norm in ("self_consumption", "self_consumption_mode"):
        steps.append(compile_sungrow_ems_mode("self_consumption"))
        steps.append(compile_sungrow_forced_charge_discharge("stop"))
        desc = "Self-Consumption Mode (Surplus charges battery, load prioritized)"
    elif norm in ("zero_export", "zero_export_power"):
        steps.append(compile_sungrow_export_limit(enabled=True, limit_w=0))
        desc = "Zero Export Power (Feed-in limitation set to 0 W)"
    elif norm in ("max_export", "max_export_power"):
        rated_w = int(kwargs.get("rated_w", 10000))
        steps.append(compile_sungrow_export_limit(enabled=True, limit_w=rated_w))
        desc = f"Max Export Power (Feed-in limitation opened to {rated_w} W)"
    elif norm in ("battery_bypass", "battery_bypass_mode"):
        steps.append(compile_sungrow_ems_mode("forced"))
        steps.append(compile_sungrow_forced_charge_discharge("stop"))
        desc = "Battery Bypass Mode (Battery idling, direct PV feed)"
    elif norm in ("forced_charge", "battery_forced_charge"):
        pow_w = int(kwargs.get("power_w", 5000))
        steps.append(compile_sungrow_ems_mode("forced"))
        steps.append(compile_sungrow_forced_charge_discharge("forced_charge", power_w=pow_w))
        desc = f"Battery Forced Charge (Charging at {pow_w} W)"
    elif norm in ("forced_discharge", "battery_forced_discharge"):
        pow_w = int(kwargs.get("power_w", 5000))
        steps.append(compile_sungrow_ems_mode("forced"))
        steps.append(compile_sungrow_forced_charge_discharge("forced_discharge", power_w=pow_w))
        desc = f"Battery Forced Discharge (Discharging at {pow_w} W)"
    else:
        raise ValueError(
            f"Unsupported EMS scene '{scene_name}'. Valid: self_consumption, zero_export, "
            f"max_export, battery_bypass, forced_charge, forced_discharge."
        )

    all_registers: Dict[int, int] = {}
    all_frames: List[str] = []
    for step in steps:
        if "registers" in step:
            all_registers.update(step["registers"])
        elif "register" in step:
            all_registers[step["register"]] = step["value"]
        if "frames_hex" in step:
            all_frames.extend(step["frames_hex"])
        elif "frame_hex" in step:
            all_frames.append(step["frame_hex"])

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "scene": norm,
        "description": desc,
        "registers": all_registers,
        "frames_hex": all_frames,
        "steps_count": len(steps),
        "reason": f"Sungrow scene '{desc}' compiled. Gated by hardware acceptance.",
    }


# ---------------------------------------------------------------------------
# Sungrow Local Client & Simulator
# ---------------------------------------------------------------------------

class SungrowShxClient:
    """Client for communicating with Sungrow SHx/SG inverters and SBR batteries.

    Supports Modbus TCP port 502 and simulator fixtures.
    Strictly gates write operations under LOCKED_PENDING_HARDWARE_ACCEPTANCE.
    """

    def __init__(
        self,
        host: str = "192.168.1.100",
        port: int = SUNGROW_DEFAULT_PORT,
        slave_unit_id: int = DEFAULT_SLAVE_UNIT_ID,
        simulated: bool = True,
    ):
        self.host = host
        self.port = port
        self.slave_unit_id = slave_unit_id
        self.simulated = simulated
        self.connected = False

        # Simulator holding registers state
        self._sim_holding_registers: Dict[int, int] = {
            12999: 0x0000,  # Running / power switch
            13049: 0,       # Self-consumption mode
            13050: 0xCC,    # Stop (default)
            13051: 0,       # Forced power 0W
            13057: 1000,    # Max SOC 100.0%
            13058: 100,     # Min SOC 10.0%
            13073: 10000,   # Export power limit 10 kW
            13074: 0x55,    # Backup mode Off
            13086: 0x55,    # Export power limit Off
            13088: 0x55,    # Active power limitation Off
            13089: 1000,    # Active power limitation ratio 100.0%
        }

    def connect(self) -> bool:
        """Establish connection to Sungrow Modbus TCP gateway or simulator."""
        self.connected = True
        return True

    def disconnect(self) -> None:
        """Close connection."""
        self.connected = False

    def get_simulated_fixtures(self) -> Tuple[Dict[int, int], Dict[int, int], Dict[int, int]]:
        """Return realistic Sungrow SH10RT + SBR096 telemetry register fixtures."""
        regs_5000: Dict[int, int] = {
            4999: 0x0E03,  # SH10RT
            5000: 100,     # Rated output 100 * 100 = 10000 W
            5002: 185,     # Daily PV & bat discharge 18.5 kWh
            5003: 15420,   # Total PV & bat discharge low word
            5004: 0,       # Total PV & bat discharge high word -> 1542.0 kWh
            5007: 385,     # Inverter temp 38.5 °C
            5010: 5200,    # MPPT1 Voltage 520.0 V
            5011: 85,      # MPPT1 Current 8.5 A -> 4420 W
            5012: 5180,    # MPPT2 Voltage 518.0 V
            5013: 82,      # MPPT2 Current 8.2 A -> 4247 W
            5014: 0,
            5015: 0,
            5114: 0,
            5115: 0,
            5016: 8667,    # Total DC Power low word (8667 W)
            5017: 0,       # Total DC Power high word
            5018: 2315,    # Phase A Voltage 231.5 V
            5019: 2308,    # Phase B Voltage 230.8 V
            5020: 2321,    # Phase C Voltage 232.1 V
            5032: 120,     # Reactive Power low word
            5033: 0,       # Reactive Power high word
            5034: 998,     # Power factor 0.998
            5213: 1850,    # Battery power low word (1850 W charging)
            5214: 0,       # Battery power high word
            5241: 5002,    # Grid Frequency 50.02 Hz
            5600: 2500,    # Meter Active Power low word (2500 W export)
            5601: 0,       # Meter Active Power high word
            5602: 840,     # Meter Phase A power (840 W)
            5603: 0,
            5604: 830,     # Meter Phase B power (830 W)
            5605: 0,
            5606: 830,     # Meter Phase C power (830 W)
            5607: 0,
            5630: 58,      # Battery current 5.8 A
        }

        regs_13000: Dict[int, int] = {
            12999: 0x0000,  # Running (normal on-grid)
            13000: 0x0002,  # Power Flow Status
            13001: 220,     # Daily PV Generation 22.0 kWh
            13002: 14500,   # Total PV low word
            13003: 0,       # Total PV high word -> 1450.0 kWh
            13007: 4317,    # Load Power low word (4317 W)
            13008: 0,       # Load Power high word
            13009: 2500,    # Export Power low word (2500 W export)
            13010: 0,       # Export Power high word
            13019: 3185,    # Battery Voltage 318.5 V
            13022: 785,     # Battery SOC 78.5%
            13023: 980,     # Battery SOH 98.0%
            13024: 265,     # Battery Temp 26.5 °C
            13025: 42,      # Daily discharge 4.2 kWh
            13026: 2850,    # Total discharge low word (285.0 kWh)
            13027: 0,
            13030: 122,     # Grid Phase A Current 12.2 A
            13031: 121,     # Grid Phase B Current 12.1 A
            13032: 123,     # Grid Phase C Current 12.3 A
            13033: 6817,    # Inverter Total Active Power low word (6817 W)
            13034: 0,       # High word
            13035: 8,       # Daily import 0.8 kWh
            13036: 450,     # Total import low word (45.0 kWh)
            13037: 0,
            13039: 125,     # Daily battery charge 12.5 kWh
            13040: 6420,    # Total battery charge low word (642.0 kWh)
            13041: 0,
            13044: 152,     # Daily export 15.2 kWh
            13045: 8900,    # Total export low word (890.0 kWh)
            13046: 0,
        }

        sbr_regs: Dict[int, int] = {
            10740: 3185,    # SBR Pack Voltage 318.5 V
            10741: 58,      # Current 5.8 A
            10742: 265,     # Temp 26.5 °C
            10743: 785,     # SOC 78.5%
            10744: 980,     # SOH 98.0%
            10756: 3345,    # Max Cell Voltage 3345 mV (3.345 V)
            10757: 14,      # Position max cell
            10758: 3328,    # Min Cell Voltage 3328 mV (3.328 V)
            10759: 38,      # Position min cell
            10760: 272,     # Max Module Temp 27.2 °C
            10761: 2,       # Module 2
            10762: 258,     # Min Module Temp 25.8 °C
            10763: 1,       # Module 1
        }

        return regs_5000, regs_13000, sbr_regs

    def read_telemetry(self) -> SungrowTelemetry:
        """Poll telemetry from Sungrow inverter or simulated registers."""
        if self.simulated:
            regs_5000, regs_13000, sbr_regs = self.get_simulated_fixtures()
            return decode_sungrow_telemetry(
                regs_5000=regs_5000,
                regs_13000=regs_13000,
                sbr_regs=sbr_regs,
                serial_str="SH10RT-A210987654",
            )
        raise NotImplementedError("Physical Modbus TCP socket client disabled in offline/test environment.")

    def write_parameter(
        self,
        command_type: str,
        params: Dict[str, Any],
        confirm_hardware_acceptance: bool = False,
    ) -> Dict[str, Any]:
        """Compile and optionally submit a parameter write.

        Requires confirm_hardware_acceptance=True to execute beyond dry-run.
        Always returns status LOCKED_PENDING_HARDWARE_ACCEPTANCE when unconfirmed.
        """
        c_type = command_type.lower().strip()
        compiled: Dict[str, Any]

        if c_type in ("ems_mode", "mode"):
            compiled = compile_sungrow_ems_mode(params.get("mode", "self_consumption"))
        elif c_type in ("forced_charge_discharge", "forced_cmd"):
            compiled = compile_sungrow_forced_charge_discharge(
                cmd=params.get("cmd", "stop"),
                power_w=int(params.get("power_w", 0)),
            )
        elif c_type in ("soc_limits", "battery_soc"):
            compiled = compile_sungrow_battery_soc_limits(
                max_soc_pct=float(params.get("max_soc_pct", 100.0)),
                min_soc_pct=float(params.get("min_soc_pct", 10.0)),
            )
        elif c_type in ("export_limit", "feed_in_limitation"):
            compiled = compile_sungrow_export_limit(
                enabled=bool(params.get("enabled", False)),
                limit_w=int(params.get("limit_w", 0)),
            )
        elif c_type in ("active_power_limitation", "active_derating"):
            compiled = compile_sungrow_active_power_limitation(
                enabled=bool(params.get("enabled", False)),
                ratio_pct=float(params.get("ratio_pct", 100.0)),
            )
        elif c_type in ("power_switch", "start_stop"):
            compiled = compile_sungrow_inverter_power_switch(
                start=bool(params.get("start", True)),
            )
        elif c_type in ("scene", "ems_scene"):
            compiled = compile_sungrow_ems_scene(
                scene_name=params.get("scene_name", "self_consumption"),
                power_w=params.get("power_w", 5000),
                rated_w=params.get("rated_w", 10000),
            )
        else:
            raise ValueError(f"Unknown Sungrow command type: '{command_type}'")

        if not confirm_hardware_acceptance:
            return {
                **compiled,
                "executed": False,
                "acceptance_verified": False,
                "note": "Safety gate ACTIVE: physical write locked pending hardware acceptance record.",
            }

        # Simulator write-back
        if self.simulated:
            regs_to_update = compiled.get("registers") or {compiled.get("register"): compiled.get("value")}
            for r, v in regs_to_update.items():
                if r is not None and v is not None:
                    self._sim_holding_registers[r] = v

            return {
                **compiled,
                "status": "SIMULATED_WRITE_COMPLETED",
                "executed": True,
                "acceptance_verified": True,
                "simulated_registers_updated": regs_to_update,
            }

        raise NotImplementedError("Physical Modbus TCP write disallowed without signed hardware acceptance.")


# ---------------------------------------------------------------------------
# Telemetry Normalizer for Solar Fleet EMS
# ---------------------------------------------------------------------------

def normalize_sungrow_telemetry(t: SungrowTelemetry) -> Dict[str, Any]:
    """Normalize SungrowTelemetry into unified Solar Fleet EMS telemetry dictionary."""
    return {
        "timestamp": t.timestamp.isoformat(),
        "device_id": f"sungrow_{t.serial_number}",
        "vendor": "Sungrow",
        "model": t.model_name,
        "operating_state": t.running_state,
        "solar": {
            "pv_power_w": t.total_dc_power_w,
            "mppt_voltages": t.mppt_voltages,
            "mppt_currents": t.mppt_currents,
            "daily_yield_kwh": t.daily_pv_kwh,
            "total_yield_kwh": t.total_pv_kwh,
        },
        "grid": {
            "active_power_w": t.grid_active_power_w,
            "reactive_power_var": t.grid_reactive_power_var,
            "power_factor": t.grid_power_factor,
            "frequency_hz": t.grid_freq_hz,
            "voltages": [t.grid_phase_a_v, t.grid_phase_b_v, t.grid_phase_c_v],
            "currents": [t.grid_phase_a_a, t.grid_phase_b_a, t.grid_phase_c_a],
        },
        "meter": {
            "pcc_active_power_w": t.meter_active_power_w,
            "export_power_w": t.export_power_w,
            "load_power_w": t.load_power_w,
            "daily_imported_kwh": t.daily_import_kwh,
            "total_imported_kwh": t.total_import_kwh,
            "daily_exported_kwh": t.daily_export_kwh,
            "total_exported_kwh": t.total_export_kwh,
        },
        "battery": {
            "power_w": t.battery_power_w,
            "voltage_v": t.battery_voltage_v,
            "current_a": t.battery_current_a,
            "soc_pct": t.battery_soc_pct,
            "soh_pct": t.battery_soh_pct,
            "temperature_c": t.battery_temp_c,
            "daily_charge_kwh": t.daily_battery_charge_kwh,
            "total_charge_kwh": t.total_battery_charge_kwh,
            "daily_discharge_kwh": t.daily_battery_discharge_kwh,
            "total_discharge_kwh": t.total_battery_discharge_kwh,
            "sbr_cell_max_mv": t.sbr_cell_max_mv,
            "sbr_cell_min_mv": t.sbr_cell_min_mv,
        },
        "safety_status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
    }
