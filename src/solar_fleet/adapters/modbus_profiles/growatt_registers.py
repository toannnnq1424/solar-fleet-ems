"""Growatt SPH/MIN/MIX Modbus register profiles.

Synthesized from:
- ha-growatt-modbus (MIT): Growatt Modbus RTU Protocol V1.20 / V3.05
  File: custom_components/growatt_modbus_lufi/registers.py
- Growatt_ModbusTCP (MIT): Protocol workbook and model list
- growatt_modbus (purchased): registers.py — 80+ sensor definitions

Register addresses follow the official Growatt Modbus RTU Protocol V1.20 (SPH series).
Identification: Holding reg 43 (DTC = Device Type Code), reg 44 (tracker/phase count).

Verified fields (from ha-growatt-modbus/registers.py, protocol V1.20):
- reg 43: DTC — device type code for model identification
- reg 44: high byte = MPPT tracker count, low byte = output phase count
         e.g. 0x0203 = 2 trackers, 3-phase output

Evidence: GROWATT_OSS_001, ha-growatt-modbus MIT, Growatt_ModbusTCP MIT
"""

from __future__ import annotations

from typing import NamedTuple


class GrowattField(NamedTuple):
    """A single Growatt Modbus register field definition."""
    register_type: str    # "input" | "holding"
    address: int          # Modbus register address
    data_type: str        # "u16" | "u32" | "i16" | "i32"
    scale: float          # Multiply raw value by this to get physical value
    unit: str             # Physical unit string
    metric: str           # Canonical metric name (from interfaces.py)
    description: str      # Human-readable field description


# ---------------------------------------------------------------------------
# SPH (Growatt SPH3000/5000/6000/8000/10000 hybrid) — Input Registers
# Source: Growatt Modbus RTU Protocol V1.20, ha-growatt-modbus/registers.py
# ---------------------------------------------------------------------------
GROWATT_SPH_INPUT_REGISTERS: list[GrowattField] = [
    # System status
    GrowattField("input", 0,  "u16", 1.0,   "",    "inverter_status",        "Inverter status"),
    # PV DC input
    GrowattField("input", 1,  "u16", 0.1,   "V",   "pv1_voltage",            "PV1 voltage"),
    GrowattField("input", 2,  "u16", 0.1,   "A",   "pv1_current",            "PV1 current"),
    GrowattField("input", 3,  "u32", 0.1,   "W",   "pv1_power",              "PV1 power"),
    GrowattField("input", 5,  "u16", 0.1,   "V",   "pv2_voltage",            "PV2 voltage"),
    GrowattField("input", 6,  "u16", 0.1,   "A",   "pv2_current",            "PV2 current"),
    GrowattField("input", 7,  "u32", 0.1,   "W",   "pv2_power",              "PV2 power"),
    # Grid AC output
    GrowattField("input", 35, "u16", 0.1,   "V",   "grid_voltage_r",         "Grid voltage R"),
    GrowattField("input", 36, "u16", 0.1,   "A",   "grid_current_r",         "Grid current R"),
    GrowattField("input", 37, "u32", 0.1,   "W",   "active_power",           "Active output power"),
    GrowattField("input", 39, "u16", 0.01,  "Hz",  "grid_frequency",         "Grid frequency"),
    GrowattField("input", 40, "u16", 0.1,   "V",   "grid_voltage_s",         "Grid voltage S"),
    GrowattField("input", 41, "u16", 0.1,   "A",   "grid_current_s",         "Grid current S"),
    GrowattField("input", 42, "u16", 0.1,   "V",   "grid_voltage_t",         "Grid voltage T"),
    GrowattField("input", 43, "u16", 0.1,   "A",   "grid_current_t",         "Grid current T"),
    # Inverter temperature
    GrowattField("input", 93, "u16", 0.1,   "°C",  "inverter_temp",          "Inverter temperature"),
    GrowattField("input", 94, "u16", 0.1,   "°C",  "grid_temp",              "Grid relay temperature"),
    # Battery
    GrowattField("input", 168, "u16", 0.01, "V",   "battery_voltage",        "Battery voltage"),
    GrowattField("input", 169, "u16", 0.1,  "A",   "battery_current",        "Battery current (charge +)"),
    GrowattField("input", 170, "u16", 0.1,  "W",   "battery_charge_power",   "Battery charge power"),
    GrowattField("input", 171, "u16", 1.0,  "%",   "battery_soc",            "Battery SOC"),
    GrowattField("input", 172, "u16", 0.1,  "°C",  "battery_temp",           "Battery temperature"),
    GrowattField("input", 174, "u16", 0.1,  "W",   "battery_discharge_power","Battery discharge power"),
    # BMS
    GrowattField("input", 168, "u16", 0.01, "V",   "bms_voltage",            "BMS voltage"),
    GrowattField("input", 169, "u16", 0.1,  "A",   "bms_current",            "BMS current"),
    GrowattField("input", 171, "u16", 1.0,  "%",   "bms_soc",                "BMS SOC"),
    GrowattField("input", 234, "u16", 1.0,  "%",   "battery_soh",            "Battery SOH"),
    GrowattField("input", 235, "u16", 1.0,  "",    "bms_cycle_count",        "BMS cycle count"),
    GrowattField("input", 236, "u16", 0.1,  "A",   "bms_max_charge_current", "BMS max charge current"),
    GrowattField("input", 240, "u16", 0.01, "V",   "cell_voltage_max",       "Max cell voltage"),
    GrowattField("input", 241, "u16", 0.01, "V",   "cell_voltage_min",       "Min cell voltage"),
    GrowattField("input", 242, "u16", 0.01, "mV",  "cell_voltage_delta",     "Cell delta voltage"),
    # Load
    GrowattField("input", 178, "u32", 0.1,  "W",   "load_power",             "Local load power"),
    GrowattField("input", 181, "u32", 0.1,  "W",   "grid_import_power",      "Grid import power"),
    GrowattField("input", 183, "u32", 0.1,  "W",   "grid_export_power",      "Grid export power"),
    # EPS / backup
    GrowattField("input", 186, "u16", 0.1,  "V",   "eps_voltage",            "EPS voltage"),
    GrowattField("input", 187, "u16", 0.01, "Hz",  "eps_frequency",          "EPS frequency"),
    GrowattField("input", 188, "u32", 0.1,  "W",   "eps_power",              "EPS power"),
    # Energy counters (kWh) — today
    GrowattField("input", 93,  "u32", 0.1,  "kWh", "energy_today",           "PV output energy today"),
    GrowattField("input", 80,  "u32", 0.1,  "kWh", "battery_charge_today",   "Battery charge today"),
    GrowattField("input", 82,  "u32", 0.1,  "kWh", "battery_discharge_today","Battery discharge today"),
    GrowattField("input", 84,  "u32", 0.1,  "kWh", "import_energy_today",    "Grid import today"),
    GrowattField("input", 86,  "u32", 0.1,  "kWh", "export_energy_today",    "Grid export today"),
    GrowattField("input", 88,  "u32", 0.1,  "kWh", "load_energy_today",      "Load energy today"),
    # Energy counters — total
    GrowattField("input", 91,  "u32", 0.1,  "kWh", "energy_total",           "PV output energy total"),
    GrowattField("input", 95,  "u32", 0.1,  "kWh", "battery_charge_total",   "Battery charge total"),
    GrowattField("input", 97,  "u32", 0.1,  "kWh", "battery_discharge_total","Battery discharge total"),
    GrowattField("input", 99,  "u32", 0.1,  "kWh", "total_import_energy",    "Grid import total"),
    GrowattField("input", 101, "u32", 0.1,  "kWh", "total_export_energy",    "Grid export total"),
    GrowattField("input", 103, "u32", 0.1,  "kWh", "load_energy_total",      "Load energy total"),
    GrowattField("input", 105, "u32", 0.1,  "kWh", "self_consumption_today", "Self-consumption today"),
]

# ---------------------------------------------------------------------------
# SPH Holding Registers (configuration / settings)
# ---------------------------------------------------------------------------
GROWATT_SPH_HOLDING_REGISTERS: list[GrowattField] = [
    GrowattField("holding", 0,   "u16", 1.0,   "",    "work_mode",              "Work mode"),
    GrowattField("holding", 21,  "u16", 1.0,   "%",   "battery_target_soc",     "Battery charge target SOC"),
    GrowattField("holding", 22,  "u16", 1.0,   "%",   "battery_reserve_soc",    "Battery discharge cutoff SOC"),
    GrowattField("holding", 25,  "u16", 0.1,   "A",   "max_charge_current",     "Max battery charge current"),
    GrowattField("holding", 26,  "u16", 0.1,   "A",   "max_discharge_current",  "Max battery discharge current"),
    # Identification
    GrowattField("holding", 43,  "u16", 1.0,   "",    "device_type_code",       "Device Type Code (DTC)"),
    GrowattField("holding", 44,  "u16", 1.0,   "",    "tracker_phase_config",   "Tracker count (high) / Phase count (low)"),
]

# ---------------------------------------------------------------------------
# MIN series (Growatt MIN 2500-6000TL-XH, string inverters with AC coupling)
# Source: Growatt_ModbusTCP MIT, Growatt MIN protocol
# ---------------------------------------------------------------------------
GROWATT_MIN_INPUT_REGISTERS: list[GrowattField] = [
    GrowattField("input", 0,  "u16", 1.0,   "",    "inverter_status",    "Inverter status"),
    GrowattField("input", 1,  "u16", 0.1,   "V",   "pv1_voltage",        "PV1 voltage"),
    GrowattField("input", 2,  "u16", 0.1,   "A",   "pv1_current",        "PV1 current"),
    GrowattField("input", 3,  "u32", 0.1,   "W",   "pv1_power",          "PV1 power"),
    GrowattField("input", 5,  "u16", 0.1,   "V",   "pv2_voltage",        "PV2 voltage"),
    GrowattField("input", 6,  "u16", 0.1,   "A",   "pv2_current",        "PV2 current"),
    GrowattField("input", 7,  "u32", 0.1,   "W",   "pv2_power",          "PV2 power"),
    GrowattField("input", 35, "u16", 0.1,   "V",   "grid_voltage_r",     "Grid voltage R"),
    GrowattField("input", 37, "u32", 0.1,   "W",   "active_power",       "Active power output"),
    GrowattField("input", 39, "u16", 0.01,  "Hz",  "grid_frequency",     "Grid frequency"),
    GrowattField("input", 55, "u16", 0.1,   "°C",  "inverter_temp",      "Inverter temperature"),
    GrowattField("input", 53, "u32", 0.1,   "kWh", "energy_today",       "Energy generated today"),
    GrowattField("input", 55, "u32", 0.1,   "kWh", "energy_total",       "Energy generated total"),
]

# ---------------------------------------------------------------------------
# Work mode enum (Growatt SPH)
# Source: ha-growatt-modbus EnumDef, Growatt protocol
# ---------------------------------------------------------------------------
GROWATT_WORK_MODES: dict[int, str] = {
    0: "self_use",
    1: "feed_in",
    2: "backup",
    3: "peak_shaving",
}

# ---------------------------------------------------------------------------
# Device Type Code → model series mapping
# Source: ha-growatt-modbus registers.py REG_DEVICE_TYPE_CODE
# ---------------------------------------------------------------------------
GROWATT_DTC_SERIES: dict[int, str] = {
    0x00: "MIN",
    0x01: "MAX",
    0x04: "MID",
    0x05: "MIX",
    0x0A: "SPH",
    0x0B: "SPA",
    0x13: "SPF",
}


def parse_tracker_phase(reg44_value: int) -> tuple[int, int]:
    """Split holding register 44 into (tracker_count, phase_count).

    Source: ha-growatt-modbus/registers.py parse_tracker_phase
    """
    return (reg44_value >> 8) & 0xFF, reg44_value & 0xFF


def get_series_from_dtc(dtc: int) -> str:
    """Return inverter series name from Device Type Code register 43."""
    return GROWATT_DTC_SERIES.get(dtc, f"UNKNOWN_DTC_{dtc:#04x}")


def registers_for_series(series: str) -> list[GrowattField]:
    """Return the appropriate register list for a given Growatt series."""
    if series in ("SPH", "SPA", "MIX"):
        return GROWATT_SPH_INPUT_REGISTERS
    if series in ("MIN", "MID", "MAX"):
        return GROWATT_MIN_INPUT_REGISTERS
    # Fall back to SPH as the most complete set
    return GROWATT_SPH_INPUT_REGISTERS


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[GrowattField],
) -> dict[str, tuple[float | None, str]]:
    """Decode raw Modbus register values to {metric: (value, unit)}.

    Handles u16, u32 (two consecutive registers), i16 (signed), i32.
    ``raw`` should be {str(address): int_value}.
    """
    result: dict[str, tuple[float | None, str]] = {}
    for f in fields:
        addr_str = str(f.address)
        if addr_str not in raw:
            continue
        raw_val = raw[addr_str]
        if f.data_type == "u16":
            value = float(raw_val & 0xFFFF) * f.scale
        elif f.data_type == "i16":
            signed = raw_val if raw_val < 0x8000 else raw_val - 0x10000
            value = float(signed) * f.scale
        elif f.data_type == "u32":
            high_str = str(f.address)
            low_str = str(f.address + 1)
            if high_str not in raw or low_str not in raw:
                continue
            combined = (raw[high_str] << 16) | (raw[low_str] & 0xFFFF)
            value = float(combined) * f.scale
        elif f.data_type == "i32":
            high_str = str(f.address)
            low_str = str(f.address + 1)
            if high_str not in raw or low_str not in raw:
                continue
            combined = (raw[high_str] << 16) | (raw[low_str] & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            value = float(combined) * f.scale
        else:
            continue
        result[f.metric] = (value, f.unit)
    return result
