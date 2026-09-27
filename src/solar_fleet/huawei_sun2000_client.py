"""Huawei SUN2000 Inverter & LUNA2000 ESS Protocol Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from public protocol specifications and community integration knowledge:
huawei-solar-lib (AGPL-3.0 clean-room independent reference).
Supports direct local communication with Huawei SUN2000 string & hybrid inverters,
LUNA2000 battery storage systems, and DTSU666-H smart power meters over Modbus TCP (port 502)
and Modbus RTU without vendor cloud dependency.

Key Capabilities:
- Multi-String PV Telemetry (Registers 32016..32023, 32064):
  * Up to 4 MPPT strings: PV1..PV4 voltages (0.1V), currents (0.01A), and computed powers.
  * Total DC input power (32064, u32 W).
- 3-Phase Grid Output Telemetry (Registers 32066..32085):
  * Phase A, B, C voltages (0.1V) and currents (0.001A).
  * Inverter active power (32080, signed s32 W), reactive power (32082, signed s32 var).
  * Power factor (32084, signed s16 / 1000) and grid frequency (32085, 0.01 Hz).
  * Daily yield (32114, 0.01 kWh) and total lifetime yield (32106, 0.01 kWh).
  * Internal inverter temperature (32087, 0.1 °C).
- LUNA2000 Energy Storage System (ESS) Telemetry (Registers 37000..37025, 37760..37782):
  * Storage running status (37762): Offline (0), Standby (1), Running (2), Fault (3), Sleep (4).
  * Pack State of Charge (SOC 37760, 0.1%).
  * Pack charge/discharge power (37765, signed s32 W; positive = charging, negative = discharging).
  * Bus voltage (37763, 0.1V) and bus current (37764, signed s16 0.1A).
  * Current day charge (37015) and discharge (37017) energy (0.01 kWh).
  * Lifetime total charge (37780) and discharge (37782) energy (0.01 kWh).
- DTSU666-H Smart Power Meter Telemetry (Registers 37100..37138):
  * Meter status (37100): Offline (0) / Normal (1).
  * Point of common coupling active power (37113, signed s32 W; positive = export, negative = import).
  * 3-phase individual active powers (37132, 37134, 37136).
  * Accumulated grid export (37119, 0.01 kWh) and import (37121, 0.01 kWh) energies.
- Safety-Gated Parameter Write Compilers (Holding Registers 40125..47299):
  * Active Power Derating: Percentage derating (40125, 0..1000 = 0..100.0%) and Fixed derating (40126, W).
  * Storage Working Mode: Maximise Self-Consumption (4), Time of Use (6), Fully Fed to Grid (5).
  * Grid Export Power Limit (47079, signed s32 W).
  * Storage Charge / Discharge Cutoff SOC (47081 & 47082, 0..1000 = 0..100.0%).
  * Max Charge / Discharge Power Caps (47075 & 47077, u32 W).
  * AC Grid Charging Toggle (47087, 0=Disable, 1=Enable).
  * LUNA2000 Time-of-Use (TOU) Schedule Compiler (Registers 47255..47297):
    Encodes up to 14 periods with start minute, end minute, charge/discharge mode, and 7-day effective mask.
  * All parameter writes strictly gated by LOCKED_PENDING_HARDWARE_ACCEPTANCE.
- Telemetry Normalizer: Translates Huawei telemetry into unified Solar Fleet EMS schema.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Tuple

# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

HUAWEI_DEFAULT_PORT = 502
DEFAULT_SLAVE_UNIT_ID = 1

MODBUS_READ_HOLDING = 0x03
MODBUS_WRITE_SINGLE = 0x06
MODBUS_WRITE_MULTIPLE = 0x10

# Inverter Operating Status (Register 32089)
DEVICE_STATUS_MAP: Dict[int, str] = {
    0x0000: "Standby: Initializing",
    0x0001: "Standby: Detecting Insulation Resistance",
    0x0002: "Standby: Detecting Irradiation",
    0x0003: "Standby: Grid Detecting",
    0x0100: "Starting",
    0x0200: "On-Grid (Normal)",
    0x0201: "Grid Connection: Power Limited",
    0x0202: "Grid Connection: Self-Derating",
    0x0203: "Off-Grid Mode: Running",
    0x0300: "Shutdown: Fault",
    0x0301: "Shutdown: Command",
    0x0302: "Shutdown: OVGR",
    0x0303: "Shutdown: Communication Disconnected",
    0x0304: "Shutdown: Power Limited",
    0x0305: "Shutdown: Manual Startup Required",
    0x0306: "Shutdown: DC Switches Disconnected",
    0x0307: "Shutdown: Rapid Cutoff",
    0x0308: "Shutdown: Input Underpowered",
    0x030C: "Shutdown: ESS End-of-Discharge",
    0xA000: "Standby: No Irradiation",
}

# LUNA2000 Storage Status (Register 37762)
STORAGE_STATUS_MAP: Dict[int, str] = {
    0: "Offline",
    1: "Standby",
    2: "Running",
    3: "Fault",
    4: "Sleep Mode",
}

# Storage Working Modes (Register 47004 / 37006)
STORAGE_WORKING_MODES: Dict[str, Tuple[int, str]] = {
    "self_consumption": (4, "Maximise Self-Consumption"),
    "fully_fed_to_grid": (5, "Fully Fed to Grid"),
    "time_of_use": (6, "Time of Use (LUNA2000)"),
    "remote_self_use": (7, "Remote Scheduling: Max Self-Use"),
    "remote_tou": (9, "Remote Scheduling: TOU"),
}

# Discrete Alarm Flags (Registers 32008..32011)
ALARM_BITFIELD_MAP: List[Tuple[int, str, str]] = [
    (0, "HighStringVoltage", "CRITICAL"),
    (1, "DCArcFault", "CRITICAL"),
    (2, "StringReverseConnection", "CRITICAL"),
    (3, "StringCurrentBackfeed", "WARNING"),
    (4, "AFCISelfCheckFailure", "CRITICAL"),
    (5, "GridPhaseFailure", "CRITICAL"),
    (6, "GridUnderVoltage", "CRITICAL"),
    (7, "GridOverVoltage", "CRITICAL"),
    (8, "GridUnderFrequency", "CRITICAL"),
    (9, "GridOverFrequency", "CRITICAL"),
    (10, "OutputOverCurrent", "CRITICAL"),
    (11, "InsulationResistanceLow", "CRITICAL"),
    (12, "GroundFaultGFCI", "CRITICAL"),
    (13, "OverTemperatureInternal", "WARNING"),
    (14, "DeviceFaultHardware", "CRITICAL"),
    (15, "CommunicationInterrupted", "WARNING"),
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class HuaweiPvString:
    """Telemetry for single PV string / MPPT."""
    string_id: int
    voltage_v: float
    current_a: float
    power_w: float


@dataclass
class HuaweiSun2000Telemetry:
    """Decoded Huawei SUN2000 Inverter, LUNA2000 ESS, and DTSU666-H Meter Telemetry."""
    model_name: str
    serial_number: str
    firmware_version: str
    timestamp: str
    device_status: str
    device_status_code: int
    inverter_temperature_c: float
    total_input_power_w: float
    pv_strings: List[HuaweiPvString]
    grid_voltage_a_v: float
    grid_voltage_b_v: float
    grid_voltage_c_v: float
    grid_current_a_a: float
    grid_current_b_a: float
    grid_current_c_a: float
    grid_active_power_w: float
    grid_reactive_power_var: float
    grid_power_factor: float
    grid_frequency_hz: float
    daily_yield_kwh: float
    total_yield_kwh: float
    meter_online: bool
    meter_active_power_w: float
    meter_exported_energy_kwh: float
    meter_imported_energy_kwh: float
    home_load_power_w: float
    storage_model: str
    storage_status: str
    storage_soc_percent: float
    storage_power_w: float
    storage_bus_voltage_v: float
    storage_bus_current_a: float
    storage_daily_charge_kwh: float
    storage_daily_discharge_kwh: float
    storage_total_charge_kwh: float
    storage_total_discharge_kwh: float
    alarms: List[Dict[str, str]]


# ---------------------------------------------------------------------------
# Modbus Protocol Helpers (Clean-Room Independent)
# ---------------------------------------------------------------------------

def calculate_modbus_crc16(data: bytes) -> int:
    """Calculate standard Modbus CRC-16 (poly 0xA001, init 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 1:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc & 0xFFFF


def build_modbus_tcp_header(trans_id: int, proto_id: int, length: int, unit_id: int) -> bytes:
    """Build standard 7-byte MBAP header for Modbus TCP."""
    return struct.pack(">HHHB", trans_id, proto_id, length, unit_id)


def build_modbus_rtu_frame(unit_id: int, func_code: int, reg_addr: int, data_val: int) -> bytes:
    """Build Modbus RTU request frame with CRC-16."""
    payload = struct.pack(">BBHH", unit_id, func_code, reg_addr, data_val)
    crc = calculate_modbus_crc16(payload)
    return payload + struct.pack("<H", crc)


def decode_ascii_string(registers: List[int]) -> str:
    """Decode string from sequence of 16-bit big-endian Modbus registers."""
    raw = bytearray()
    for reg in registers:
        raw.append((reg >> 8) & 0xFF)
        raw.append(reg & 0xFF)
    return raw.decode("latin-1", errors="ignore").replace("\x00", "").strip()


# ---------------------------------------------------------------------------
# Telemetry Decoders
# ---------------------------------------------------------------------------

def decode_sun2000_telemetry(
    holding_regs: Dict[int, int],
    model_name: str = "SUN2000-10KTL-M1",
    serial_number: str = "HV2026M100499",
    firmware_version: str = "V100R001C00SPC140",
) -> HuaweiSun2000Telemetry:
    """Decode raw Huawei SUN2000 holding registers into structured telemetry."""
    now_iso = datetime.now(timezone.utc).isoformat()

    def u16(addr: int, default: int = 0) -> int:
        return holding_regs.get(addr, default) & 0xFFFF

    def s16(addr: int, default: int = 0) -> int:
        v = u16(addr, default)
        return v - 0x10000 if v >= 0x8000 else v

    def u32(addr: int, default: int = 0) -> int:
        hi = u16(addr, default >> 16)
        lo = u16(addr + 1, default & 0xFFFF)
        return (hi << 16) | lo

    def s32(addr: int, default: int = 0) -> int:
        v = u32(addr, default)
        return v - 0x100000000 if v >= 0x80000000 else v

    # Device Status
    status_code = u16(32089, 0x0200)
    dev_status = DEVICE_STATUS_MAP.get(status_code, f"Status 0x{status_code:04X}")

    # Alarm code decoding
    alarms: List[Dict[str, str]] = []
    alarm_bits = (u16(32008) << 16) | u16(32009)
    for bit_idx, name, sev in ALARM_BITFIELD_MAP:
        if alarm_bits & (1 << bit_idx):
            alarms.append({"code": name, "severity": sev, "bit": str(bit_idx)})

    # Multi-string PV Trackers
    pv_strings: List[HuaweiPvString] = []
    pv_str_regs = [(1, 32016, 32017), (2, 32018, 32019), (3, 32020, 32021), (4, 32022, 32023)]
    for sid, v_addr, i_addr in pv_str_regs:
        v = round(u16(v_addr) * 0.1, 1)
        i = round(s16(i_addr) * 0.01, 2)
        p = round(v * i, 1) if v > 0 and i > 0 else 0.0
        pv_strings.append(HuaweiPvString(string_id=sid, voltage_v=v, current_a=i, power_w=p))

    total_dc_w = float(u32(32064, int(sum(s.power_w for s in pv_strings))))

    # 3-Phase Grid Output
    grid_va = round(u16(32069) * 0.1, 1)
    grid_vb = round(u16(32070) * 0.1, 1)
    grid_vc = round(u16(32071) * 0.1, 1)

    grid_ia = round(s32(32072) * 0.001, 3)
    grid_ib = round(s32(32074) * 0.001, 3)
    grid_ic = round(s32(32076) * 0.001, 3)

    inv_active_p = float(s32(32080))
    inv_reactive_p = float(s32(32082))
    inv_pf = round(s16(32084) * 0.001, 3)
    inv_freq = round(u16(32085) * 0.01, 2)
    inv_temp = round(s16(32087) * 0.1, 1)

    daily_yield = round(u32(32114) * 0.01, 2)
    total_yield = round(u32(32106) * 0.01, 2)

    # DTSU666-H Smart Power Meter
    meter_stat = u16(37100, 1)
    meter_online = (meter_stat == 1)
    meter_active_p = float(s32(37113, 0))
    meter_exp_kwh = round(u32(37119, 0) * 0.01, 2)
    meter_imp_kwh = round(u32(37121, 0) * 0.01, 2)

    # LUNA2000 Energy Storage
    storage_model_code = u16(47000, 2)
    storage_model_desc = "HUAWEI LUNA2000" if storage_model_code == 2 else ("LG RESU" if storage_model_code == 1 else "None")
    storage_stat_code = u16(37762, 2)
    storage_stat_desc = STORAGE_STATUS_MAP.get(storage_stat_code, f"Status {storage_stat_code}")
    storage_soc = round(u16(37760, 0) * 0.1, 1)
    storage_p = float(s32(37765, 0))
    storage_bus_v = round(u16(37763, 0) * 0.1, 1)
    storage_bus_i = round(s16(37764, 0) * 0.1, 1)
    storage_day_chg = round(u32(37015, 0) * 0.01, 2)
    storage_day_dis = round(u32(37017, 0) * 0.01, 2)
    storage_tot_chg = round(u32(37780, 0) * 0.01, 2)
    storage_tot_dis = round(u32(37782, 0) * 0.01, 2)

    # Home Load Calculation: Inverter Output - Meter Export (or + Meter Import)
    home_load_w = max(0.0, round(inv_active_p - meter_active_p, 1))

    return HuaweiSun2000Telemetry(
        model_name=model_name,
        serial_number=serial_number,
        firmware_version=firmware_version,
        timestamp=now_iso,
        device_status=dev_status,
        device_status_code=status_code,
        inverter_temperature_c=inv_temp,
        total_input_power_w=total_dc_w,
        pv_strings=pv_strings,
        grid_voltage_a_v=grid_va,
        grid_voltage_b_v=grid_vb,
        grid_voltage_c_v=grid_vc,
        grid_current_a_a=grid_ia,
        grid_current_b_a=grid_ib,
        grid_current_c_a=grid_ic,
        grid_active_power_w=inv_active_p,
        grid_reactive_power_var=inv_reactive_p,
        grid_power_factor=inv_pf,
        grid_frequency_hz=inv_freq,
        daily_yield_kwh=daily_yield,
        total_yield_kwh=total_yield,
        meter_online=meter_online,
        meter_active_power_w=meter_active_p,
        meter_exported_energy_kwh=meter_exp_kwh,
        meter_imported_energy_kwh=meter_imp_kwh,
        home_load_power_w=home_load_w,
        storage_model=storage_model_desc,
        storage_status=storage_stat_desc,
        storage_soc_percent=storage_soc,
        storage_power_w=storage_p,
        storage_bus_voltage_v=storage_bus_v,
        storage_bus_current_a=storage_bus_i,
        storage_daily_charge_kwh=storage_day_chg,
        storage_daily_discharge_kwh=storage_day_dis,
        storage_total_charge_kwh=storage_tot_chg,
        storage_total_discharge_kwh=storage_tot_dis,
        alarms=alarms,
    )


def normalize_huawei_to_ems(tel: HuaweiSun2000Telemetry) -> Dict[str, Any]:
    """Translate Huawei telemetry into standard Solar Fleet EMS schema."""
    return {
        "device_id": f"huawei-{tel.serial_number}",
        "serial_number": tel.serial_number,
        "vendor": "Huawei",
        "protocol": "Huawei-SUN2000-Modbus-TCP",
        "model_type": tel.model_name,
        "operating_mode": tel.device_status,
        "battery_mode": tel.storage_status,
        "timestamp": tel.timestamp,
        "power_flow": {
            "solar_power_w": tel.total_input_power_w,
            "grid_power_w": tel.grid_active_power_w,
            "battery_power_w": tel.storage_power_w,
            "load_power_w": tel.home_load_power_w,
            "meter_power_w": tel.meter_active_power_w,
        },
        "metrics": {
            "pv_power_w": tel.total_input_power_w,
            "grid_power_w": tel.grid_active_power_w,
            "grid_frequency_hz": tel.grid_frequency_hz,
            "power_factor": tel.grid_power_factor,
            "load_power_w": tel.home_load_power_w,
            "battery_soc_pct": int(tel.storage_soc_percent),
            "battery_power_w": tel.storage_power_w,
            "temperature_c": tel.inverter_temperature_c,
            "energy_today_kwh": tel.daily_yield_kwh,
            "energy_total_kwh": tel.total_yield_kwh,
        },
        "raw_snapshot": {
            "pv_strings": [
                {
                    "string": s.string_id,
                    "voltage_v": s.voltage_v,
                    "current_a": s.current_a,
                    "power_w": s.power_w,
                }
                for s in tel.pv_strings
            ],
            "grid_voltages": {
                "phase_a_v": tel.grid_voltage_a_v,
                "phase_b_v": tel.grid_voltage_b_v,
                "phase_c_v": tel.grid_voltage_c_v,
            },
            "grid_currents": {
                "phase_a_a": tel.grid_current_a_a,
                "phase_b_a": tel.grid_current_b_a,
                "phase_c_a": tel.grid_current_c_a,
            },
            "meter": {
                "online": tel.meter_online,
                "active_power_w": tel.meter_active_power_w,
                "exported_kwh": tel.meter_exported_energy_kwh,
                "imported_kwh": tel.meter_imported_energy_kwh,
            },
            "storage": {
                "model": tel.storage_model,
                "status": tel.storage_status,
                "soc_pct": tel.storage_soc_percent,
                "power_w": tel.storage_power_w,
                "bus_voltage_v": tel.storage_bus_voltage_v,
                "bus_current_a": tel.storage_bus_current_a,
                "daily_charge_kwh": tel.storage_daily_charge_kwh,
                "daily_discharge_kwh": tel.storage_daily_discharge_kwh,
                "total_charge_kwh": tel.storage_total_charge_kwh,
                "total_discharge_kwh": tel.storage_total_discharge_kwh,
            },
            "alarms": tel.alarms,
        },
    }


# ---------------------------------------------------------------------------
# Fleet Parameter Write Compilers with Safety Gating
# ---------------------------------------------------------------------------

def compile_huawei_active_power_derating(percentage: float) -> Dict[str, Any]:
    """Compile Active Power Percentage Derating (Holding Register 40125).

    Register: 40125 (0.1%, 0..1000 represents 0.0% .. 100.0%).
    """
    if not (0.0 <= percentage <= 100.0):
        raise ValueError(f"Derating percentage out of range (0.0..100.0%): {percentage}")

    reg_val = int(round(percentage * 10))
    req = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 40125, reg_val)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "register": 40125,
        "value": reg_val,
        "percentage": percentage,
        "frame_hex": req.hex(),
        "reason": "Huawei active power derating compiled. Gated by hardware acceptance.",
    }


def compile_huawei_storage_mode(mode_key: str) -> Dict[str, Any]:
    """Compile LUNA2000 Storage Working Mode (Holding Register 47004)."""
    key = mode_key.lower().replace("-", "_").replace(" ", "_")
    if key not in STORAGE_WORKING_MODES:
        raise ValueError(f"Invalid mode '{mode_key}'. Allowed: {list(STORAGE_WORKING_MODES.keys())}")

    val, desc = STORAGE_WORKING_MODES[key]
    req = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 47004, val)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "register": 47004,
        "value": val,
        "description": desc,
        "frame_hex": req.hex(),
        "reason": "Huawei storage working mode write compiled. Gated by hardware acceptance.",
    }


def compile_huawei_export_limit(limit_watts: int) -> Dict[str, Any]:
    """Compile Grid Export Power Limit (Holding Register 47079, signed 32-bit)."""
    if not (0 <= limit_watts <= 500000):
        raise ValueError(f"Export limit out of range (0..500,000 W): {limit_watts}")

    hi = (limit_watts >> 16) & 0xFFFF
    lo = limit_watts & 0xFFFF

    # Build FC10 multiple write for 32-bit register
    pdu = struct.pack(">BHHBBHH", DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_MULTIPLE, 47079, 2, 4, hi, lo)
    crc = calculate_modbus_crc16(pdu)
    req = pdu + struct.pack("<H", crc)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "register": 47079,
        "registers": {47079: hi, 47080: lo},
        "limit_watts": limit_watts,
        "frame_hex": req.hex(),
        "reason": "Huawei grid export power limit compiled. Gated by hardware acceptance.",
    }


def compile_huawei_cutoff_soc(charge_soc_pct: float, discharge_soc_pct: float) -> Dict[str, Any]:
    """Compile LUNA2000 Cutoff Capacities (Registers 47081 & 47082).

    Register 47081: Charging cutoff capacity (0.1%, 0..1000 = 0.0..100.0%).
    Register 47082: Discharging cutoff capacity (0.1%, 0..1000 = 0.0..100.0%).
    """
    if not (50.0 <= charge_soc_pct <= 100.0):
        raise ValueError(f"Charge cutoff SOC out of range (50..100%): {charge_soc_pct}")
    if not (0.0 <= discharge_soc_pct <= 50.0):
        raise ValueError(f"Discharge cutoff SOC out of range (0..50%): {discharge_soc_pct}")

    val_chg = int(round(charge_soc_pct * 10))
    val_dis = int(round(discharge_soc_pct * 10))

    req_chg = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 47081, val_chg)
    req_dis = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 47082, val_dis)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "registers": {
            47081: val_chg,
            47082: val_dis,
        },
        "charge_cutoff_pct": charge_soc_pct,
        "discharge_cutoff_pct": discharge_soc_pct,
        "frames_hex": [req_chg.hex(), req_dis.hex()],
        "reason": "Huawei battery cutoff SOC parameters compiled. Gated by hardware acceptance.",
    }


def compile_huawei_charge_from_grid(enable: bool) -> Dict[str, Any]:
    """Compile AC Charge From Grid Toggle (Holding Register 47087)."""
    val = 1 if enable else 0
    req = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, MODBUS_WRITE_SINGLE, 47087, val)

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "register": 47087,
        "value": val,
        "enabled": enable,
        "frame_hex": req.hex(),
        "reason": "Huawei AC charge from grid compiled. Gated by hardware acceptance.",
    }


def compile_huawei_luna_tou_period(
    period_idx: int,
    start_time: str,
    stop_time: str,
    action: str = "charge",
    days_effective: int = 0x7F,  # All 7 days (Sunday..Saturday)
) -> Dict[str, Any]:
    """Compile LUNA2000 TOU Period (Holding Registers 47255..47297).

    Layout:
    Register 47255: Period Count
    Each period occupies 3 words (start_min u16, end_min u16, (charge_flag u8 << 8) | days_mask u8).
    """
    if not (1 <= period_idx <= 14):
        raise ValueError(f"Period index out of range (1..14): {period_idx}")

    s_parts = [int(p) for p in start_time.split(":")]
    e_parts = [int(p) for p in stop_time.split(":")]
    if len(s_parts) != 2 or len(e_parts) != 2:
        raise ValueError("Time must be formatted as 'HH:MM'")

    start_min = s_parts[0] * 60 + s_parts[1]
    stop_min = e_parts[0] * 60 + e_parts[1]
    if not (0 <= start_min <= 1440 and 0 <= stop_min <= 1440):
        raise ValueError("Time must be between 00:00 and 24:00")
    if start_min >= stop_min:
        raise ValueError(f"Start time ({start_time}) must be earlier than stop time ({stop_time})")

    charge_flag = 0 if action.lower() == "charge" else 1
    flag_day_word = ((charge_flag & 0xFF) << 8) | (days_effective & 0xFF)

    base_reg = 47255 + 1 + (period_idx - 1) * 3

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "period_index": period_idx,
        "registers": {
            base_reg: start_min,
            base_reg + 1: stop_min,
            base_reg + 2: flag_day_word,
        },
        "description": f"Period {period_idx}: {start_time}-{stop_time} ({action.upper()}) Days=0x{days_effective:02X}",
        "reason": "Huawei LUNA2000 TOU period compiled. Gated by hardware acceptance.",
    }


# ---------------------------------------------------------------------------
# Huawei SUN2000 Local Client & Simulator
# ---------------------------------------------------------------------------

class HuaweiSun2000Client:
    """Client for communicating with Huawei SUN2000 & LUNA2000 systems.

    Supports Modbus TCP port 502 and simulated testing loopbacks.
    Strictly gates write operations under LOCKED_PENDING_HARDWARE_ACCEPTANCE.
    """

    def __init__(
        self,
        host: str = "192.168.200.1",
        port: int = HUAWEI_DEFAULT_PORT,
        slave_unit_id: int = DEFAULT_SLAVE_UNIT_ID,
        simulated: bool = True,
    ) -> None:
        self.host = host
        self.port = port
        self.slave_unit_id = slave_unit_id
        self.simulated = simulated

    def poll_telemetry(self) -> Dict[str, Any]:
        """Poll and normalize SUN2000 / LUNA2000 telemetry."""
        if self.simulated:
            mock_regs = {
                # Inverter Running Status & Internal Temp
                32089: 0x0200,  # On-Grid Normal
                32008: 0, 32009: 0,  # No Alarms
                32087: 415,     # Internal Temp 41.5 °C
                # Multi-string PV (Dual MPPT)
                32016: 3820,    # PV1 382.0 V
                32017: 1250,    # PV1 12.50 A (Power ~ 4775 W)
                32018: 3850,    # PV2 385.0 V
                32019: 1240,    # PV2 12.40 A (Power ~ 4774 W)
                32064: 0, 32065: 9549,  # Total DC Power 9549 W
                # 3-Phase Grid Output
                32069: 2305,    # Phase A 230.5 V
                32070: 2310,    # Phase B 231.0 V
                32071: 2298,    # Phase C 229.8 V
                32072: 0, 32073: 13010,  # Phase A Current 13.010 A
                32074: 0, 32075: 12980,  # Phase B Current 12.980 A
                32076: 0, 32077: 13020,  # Phase C Current 13.020 A
                32080: 0, 32081: 9000,   # Active Power 9000 W
                32082: 0, 32083: 150,    # Reactive Power 150 var
                32084: 998,     # Power Factor 0.998
                32085: 5000,    # Frequency 50.00 Hz
                32114: 0, 32115: 4250,   # Daily Yield 42.50 kWh
                32106: 0, 32107: 1485000, # Total Yield 14,850.00 kWh
                # DTSU666-H Smart Power Meter
                37100: 1,       # Meter Online
                37113: 0, 37114: 2500,   # Meter Active Power +2500 W (Exporting)
                37119: 0, 37120: 2150,   # Meter Exported Energy 21.50 kWh
                37121: 0, 37122: 480,    # Meter Imported Energy 4.80 kWh
                # LUNA2000 Energy Storage System
                47000: 2,       # Storage Model: HUAWEI LUNA2000
                37762: 2,       # Storage Status: Running
                37760: 845,     # Storage SOC: 84.5%
                37765: 0, 37766: 1800,   # Storage Power: 1800 W (Charging)
                37763: 4100,    # Bus Voltage: 410.0 V
                37764: 44,      # Bus Current: 4.4 A
                37015: 0, 37016: 1420,   # Today Charge: 14.20 kWh
                37017: 0, 37018: 980,    # Today Discharge: 9.80 kWh
                37780: 0, 37781: 345000, # Lifetime Charge: 3,450.00 kWh
                37782: 0, 37783: 312000, # Lifetime Discharge: 3,120.00 kWh
            }
            tel = decode_sun2000_telemetry(
                mock_regs,
                model_name="SUN2000-10KTL-M1",
                serial_number="HV2026M100499",
                firmware_version="V100R001C00SPC140",
            )
            return normalize_huawei_to_ems(tel)

        raise NotImplementedError("Real Modbus TCP transport is activated via controller worker.")

    def execute_command_safely(
        self,
        command_type: str,
        params: Dict[str, Any],
        unlocked: bool = False,
    ) -> Dict[str, Any]:
        """Execute command safely gated by hardware acceptance."""
        if not unlocked:
            return {
                "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
                "command_type": command_type,
                "params": params,
                "message": (
                    "Huawei SUN2000 / LUNA2000 parameter write is gated behind hardware acceptance verification. "
                    "Device held in read-only state."
                ),
            }

        if command_type == "active_power_derating":
            pct = float(params.get("percentage", 100.0))
            return compile_huawei_active_power_derating(pct)

        elif command_type == "storage_mode":
            mode = str(params.get("mode", "self_consumption"))
            return compile_huawei_storage_mode(mode)

        elif command_type == "export_limit":
            limit = int(params.get("limit_watts", 5000))
            return compile_huawei_export_limit(limit)

        elif command_type == "cutoff_soc":
            chg = float(params.get("charge_cutoff_pct", 100.0))
            dis = float(params.get("discharge_cutoff_pct", 10.0))
            return compile_huawei_cutoff_soc(chg, dis)

        elif command_type == "charge_from_grid":
            en = bool(params.get("enable", False))
            return compile_huawei_charge_from_grid(en)

        elif command_type == "luna_tou_period":
            pidx = int(params.get("period_index", 1))
            st = str(params.get("start_time", "01:00"))
            sp = str(params.get("stop_time", "06:00"))
            act = str(params.get("action", "charge"))
            days = int(params.get("days_effective", 0x7F))
            return compile_huawei_luna_tou_period(pidx, st, sp, act, days)

        else:
            raise ValueError(f"Unknown Huawei SUN2000 command type: '{command_type}'")
