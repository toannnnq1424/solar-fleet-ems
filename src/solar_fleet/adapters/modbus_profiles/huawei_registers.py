"""Huawei SUN2000 Modbus register profiles.

Synthesized from huawei-solar-lib (wlcrs, MIT License):
  src/huawei_solar/registers.py
  src/huawei_solar/register_names.py
  src/huawei_solar/register_definitions/number.py

Source: https://github.com/wlcrs/huawei_solar (MIT, accessed 2026-10-01)
License: MIT — full usage rights confirmed per before_project acquisition.

Register addresses are the Modbus start register (0-based register address).
gain = divisor: value = raw / gain  (e.g. U16Register("V", 10, 32066) → V/10)
"""

from __future__ import annotations

from typing import NamedTuple


class HuaweiField(NamedTuple):
    """A single Huawei SUN2000 Modbus register field."""
    address: int          # Modbus start register (0-based)
    data_type: str        # "u16" | "u32" | "i16" | "i32"
    gain: int             # Divide raw by this → physical value (1 = no scaling)
    unit: str             # Physical unit (empty = dimensionless/enum)
    metric: str           # Canonical metric (from interfaces.py)
    description: str


# ---------------------------------------------------------------------------
# SUN2000 Input / Holding registers
# Source: huawei-solar registers.py (MIT)
# ---------------------------------------------------------------------------
HUAWEI_SUN2000_REGISTERS: list[HuaweiField] = [
    # --------------- Inverter DC input ---------------
    HuaweiField(32064, "i32", 1,    "W",   "pv_power",           "Total DC input power"),

    # --------------- Grid AC ---------------
    HuaweiField(32066, "u16", 10,   "V",   "grid_voltage_r",     "Line/phase A voltage"),
    HuaweiField(32067, "u16", 10,   "V",   "grid_voltage_s",     "Line voltage B-C"),
    HuaweiField(32068, "u16", 10,   "V",   "grid_voltage_t",     "Line voltage C-A"),
    HuaweiField(32069, "u16", 10,   "V",   "grid_voltage_r",     "Phase A voltage"),
    HuaweiField(32070, "u16", 10,   "V",   "grid_voltage_s",     "Phase B voltage"),
    HuaweiField(32071, "u16", 10,   "V",   "grid_voltage_t",     "Phase C voltage"),
    HuaweiField(32072, "i32", 1000, "A",   "grid_current_r",     "Phase A current"),
    HuaweiField(32074, "i32", 1000, "A",   "grid_current_s",     "Phase B current"),
    HuaweiField(32076, "i32", 1000, "A",   "grid_current_t",     "Phase C current"),
    HuaweiField(32080, "i32", 1,    "W",   "active_power",       "Active power output"),
    HuaweiField(32082, "i32", 1,    "var", "reactive_power",     "Reactive power"),
    HuaweiField(32084, "i16", 1000, "",    "power_factor",       "Power factor"),
    HuaweiField(32085, "u16", 100,  "Hz",  "grid_frequency",     "Grid frequency"),
    HuaweiField(32086, "u16", 100,  "%",   "inverter_efficiency","Inverter efficiency"),
    HuaweiField(32087, "i16", 10,   "°C",  "inverter_temp",      "Inverter internal temperature"),
    HuaweiField(32089, "u16", 1,    "",    "inverter_status",    "Device status"),
    HuaweiField(32090, "u16", 1,    "",    "fault_code",         "Fault code"),
    HuaweiField(32095, "i32", 1,    "W",   "active_power",       "Active power (fast)"),

    # --------------- Energy yields ---------------
    HuaweiField(32106, "u32", 100,  "kWh", "energy_total",       "Accumulated yield energy"),
    HuaweiField(32114, "u32", 100,  "kWh", "energy_today",       "Daily yield energy"),
    HuaweiField(32116, "u32", 100,  "kWh", "energy_monthly",     "Monthly yield energy"),
    HuaweiField(32118, "u32", 100,  "kWh", "energy_yearly",      "Yearly yield energy"),

    # --------------- MPPT / PV strings ---------------
    # Actual MPPT voltages are in device-specific extension registers (33000+)
    # These are the cumulative energy per MPPT
    HuaweiField(32212, "u32", 100,  "kWh", "pv1_energy_total",   "MPPT1 cumulative DC energy"),
    HuaweiField(32214, "u32", 100,  "kWh", "pv2_energy_total",   "MPPT2 cumulative DC energy"),

    # --------------- Storage Unit 1 (LUNA2000) ---------------
    HuaweiField(37000, "u16", 1,    "",    "inverter_status",    "Storage unit 1 running status"),
    HuaweiField(37001, "i32", 1,    "W",   "battery_power",      "Storage unit 1 charge/discharge power"),
    HuaweiField(37003, "u16", 10,   "V",   "battery_voltage",    "Storage unit 1 bus voltage"),
    HuaweiField(37004, "u16", 10,   "%",   "battery_soc",        "Storage unit 1 SOC"),
    HuaweiField(37015, "u32", 100,  "kWh", "battery_charge_today",     "Storage unit 1 day charge capacity"),
    HuaweiField(37017, "u32", 100,  "kWh", "battery_discharge_today",  "Storage unit 1 day discharge capacity"),
    HuaweiField(37021, "i16", 10,   "A",   "battery_current",   "Storage unit 1 bus current"),
    HuaweiField(37022, "i16", 10,   "°C",  "battery_temp",      "Storage unit 1 battery temperature"),
    HuaweiField(37046, "u32", 1,    "W",   "bms_max_charge_current",  "Storage max charge power"),
    HuaweiField(37048, "u32", 1,    "W",   "battery_discharge_power", "Storage max discharge power"),
    HuaweiField(37066, "u32", 100,  "kWh", "battery_charge_total",    "Storage unit 1 total charge"),
    HuaweiField(37068, "u32", 100,  "kWh", "battery_discharge_total", "Storage unit 1 total discharge"),

    # --------------- Combined storage (dual unit) ---------------
    HuaweiField(37760, "u16", 10,   "%",   "battery_soc",        "Combined storage SOC"),
    HuaweiField(37763, "u16", 10,   "V",   "battery_voltage",    "Combined storage bus voltage"),
    HuaweiField(37764, "i16", 10,   "A",   "battery_current",    "Combined storage bus current"),
    HuaweiField(37765, "i32", 1,    "W",   "battery_power",      "Combined storage charge/discharge power"),
    HuaweiField(37780, "u32", 100,  "kWh", "battery_charge_total",    "Combined storage total charge"),
    HuaweiField(37782, "u32", 100,  "kWh", "battery_discharge_total", "Combined storage total discharge"),
    HuaweiField(37784, "u32", 100,  "kWh", "battery_charge_today",    "Combined storage day charge"),
    HuaweiField(37786, "u32", 100,  "kWh", "battery_discharge_today", "Combined storage day discharge"),

    # --------------- Power meter / grid ---------------
    HuaweiField(37113, "i32", 1,    "W",   "grid_power",         "Power meter active power"),
    HuaweiField(37119, "i32", 1,    "W",   "grid_power_r",       "Power meter phase A power"),
    HuaweiField(37121, "i32", 1,    "W",   "grid_power_s",       "Power meter phase B power"),
    HuaweiField(37123, "i32", 1,    "W",   "grid_power_t",       "Power meter phase C power"),
    HuaweiField(37131, "i32", 1,    "Hz",  "grid_frequency",     "Power meter grid frequency"),
    HuaweiField(37163, "u32", 100,  "kWh", "total_export_energy","Grid exported energy"),
    HuaweiField(37165, "u32", 100,  "kWh", "total_import_energy","Grid accumulated energy"),
]

# ---------------------------------------------------------------------------
# SUN2000 Holding Registers (writable configuration)
# Source: huawei-solar registers.py (MIT) — writeable=True entries
# ---------------------------------------------------------------------------
HUAWEI_HOLDING_REGISTERS: list[HuaweiField] = [
    HuaweiField(40200, "u16", 1,    "",    "work_mode",              "Storage control mode"),
    HuaweiField(47086, "u16", 10,   "%",   "battery_reserve_soc",    "Storage charge cutoff SOC"),
    HuaweiField(47087, "u16", 10,   "%",   "battery_target_soc",     "Backup power reserve SOC"),
    HuaweiField(47100, "u32", 1,    "W",   "max_charge_power",       "Storage maximum charge power"),
    HuaweiField(47102, "u32", 1,    "W",   "max_discharge_power",    "Storage maximum discharge power"),
    HuaweiField(47415, "u16", 1,    "",    "tou_periods_of_charging", "TOU charging periods count"),
]

# ---------------------------------------------------------------------------
# Storage work mode enum
# Source: huawei-solar register_values.py StorageWorkingModesC
# ---------------------------------------------------------------------------
HUAWEI_STORAGE_MODES: dict[int, str] = {
    0: "maximise_self_consumption",
    1: "time_of_use",
    2: "fixed_charge_discharge",
    3: "fully_fed_to_grid",
}


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[HuaweiField],
) -> dict[str, tuple[float | None, str]]:
    """Decode raw Modbus register dict to {metric: (value, unit)}.

    ``raw`` is {str(address): int_register_value}.
    Raw value is divided by ``gain`` (not multiplied, matching huawei-solar convention).
    """
    result: dict[str, tuple[float | None, str]] = {}
    for f in fields:
        addr_str = str(f.address)
        if addr_str not in raw:
            continue
        raw_val = raw[addr_str]
        if f.data_type == "u16":
            value = float(raw_val & 0xFFFF) / f.gain
        elif f.data_type == "i16":
            signed = raw_val if raw_val < 0x8000 else raw_val - 0x10000
            value = float(signed) / f.gain
        elif f.data_type == "u32":
            high_str = str(f.address)
            low_str = str(f.address + 1)
            if low_str not in raw:
                continue
            combined = (raw[high_str] << 16) | (raw[low_str] & 0xFFFF)
            value = float(combined) / f.gain
        elif f.data_type == "i32":
            high_str = str(f.address)
            low_str = str(f.address + 1)
            if low_str not in raw:
                continue
            combined = (raw[high_str] << 16) | (raw[low_str] & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            value = float(combined) / f.gain
        else:
            continue
        result[f.metric] = (value, f.unit)
    return result
