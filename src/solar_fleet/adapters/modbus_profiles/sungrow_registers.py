"""Sungrow SHx/SH/SG Modbus register profiles.

Synthesized from:
- Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT, mkaiser):
  modbus_sungrow.yaml — 167 sensor definitions, release 2026-06-19

Addresses follow the "reg XXXX" comments in the source YAML.
In the YAML, address: N means Modbus register N+1 (0-based address).
We store the 0-based address (as in the YAML's address: field).

Evidence: SUNGROW_DEV_001, Sungrow-SHx MIT
"""

from __future__ import annotations

from typing import NamedTuple


class SungrowField(NamedTuple):
    """A single Sungrow Modbus register field definition."""
    register_type: str    # "input" | "holding"
    address: int          # 0-based Modbus address (as used in HA YAML)
    data_type: str        # "uint16" | "uint32" | "int16" | "int32"
    scale: float
    unit: str
    metric: str
    description: str


# ---------------------------------------------------------------------------
# Sungrow SHx Input Registers (from modbus_sungrow.yaml)
# All addresses are the YAML address: field (Modbus 0-based)
# ---------------------------------------------------------------------------
SUNGROW_SHX_INPUT_REGISTERS: list[SungrowField] = [
    # Identification
    SungrowField("input", 4999, "uint16", 1.0,   "",     "device_type_code",          "Device type code"),
    SungrowField("input", 5000, "uint16", 100.0, "W",    "inverter_rated_power",      "Inverter rated output"),

    # Generation
    SungrowField("input", 5002, "uint16", 0.1,   "kWh",  "pv_energy_today",           "Daily PV generation"),
    SungrowField("input", 5003, "uint32", 0.1,   "kWh",  "energy_total",              "Total PV generation"),

    # Temperature
    SungrowField("input", 5007, "int16",  0.1,   "°C",   "inverter_temp",             "Inverter temperature"),

    # PV strings (MPPT)
    SungrowField("input", 5010, "uint16", 0.1,   "V",    "pv1_voltage",               "MPPT1 voltage"),
    SungrowField("input", 5011, "uint16", 0.1,   "A",    "pv1_current",               "MPPT1 current"),
    SungrowField("input", 5012, "uint16", 0.1,   "V",    "pv2_voltage",               "MPPT2 voltage"),
    SungrowField("input", 5013, "uint16", 0.1,   "A",    "pv2_current",               "MPPT2 current"),
    SungrowField("input", 5014, "uint16", 0.1,   "V",    "pv3_voltage",               "MPPT3 voltage"),
    SungrowField("input", 5015, "uint16", 0.1,   "A",    "pv3_current",               "MPPT3 current"),
    SungrowField("input", 5114, "uint16", 0.1,   "V",    "pv4_voltage",               "MPPT4 voltage"),
    SungrowField("input", 5115, "uint16", 0.1,   "A",    "pv4_current",               "MPPT4 current"),

    # DC total power
    SungrowField("input", 5016, "uint32", 1.0,   "W",    "pv_power",                  "Total DC power"),

    # Grid AC
    SungrowField("input", 5018, "uint16", 0.1,   "V",    "grid_voltage_r",            "Phase A voltage"),
    SungrowField("input", 5019, "uint16", 0.1,   "V",    "grid_voltage_s",            "Phase B voltage"),
    SungrowField("input", 5020, "uint16", 0.1,   "V",    "grid_voltage_t",            "Phase C voltage"),
    SungrowField("input", 5032, "int32",  1.0,   "var",  "reactive_power",            "Reactive power"),
    SungrowField("input", 5034, "int16",  0.001, "",     "power_factor",              "Power factor"),
    SungrowField("input", 5241, "uint16", 0.01,  "Hz",   "grid_frequency",            "Grid frequency"),

    # Active output power (AC)
    SungrowField("input", 5030, "int32",  1.0,   "W",    "active_power",              "Output active power"),

    # Battery
    SungrowField("input", 5213, "int32",  1.0,   "W",    "battery_power",             "Battery power (+charge/-discharge)"),
    SungrowField("input", 5217, "uint16", 1.0,   "%",    "battery_soc",               "Battery SOC"),
    SungrowField("input", 5220, "int16",  0.1,   "°C",   "battery_temp",              "Battery temperature"),
    SungrowField("input", 5228, "uint16", 0.1,   "V",    "battery_voltage",           "Battery voltage"),
    SungrowField("input", 5229, "int16",  0.1,   "A",    "battery_current",           "Battery current"),
    SungrowField("input", 5236, "uint16", 1.0,   "%",    "battery_soh",               "Battery SOH"),

    # Grid meter
    SungrowField("input", 5600, "int32",  1.0,   "W",    "grid_power",                "Meter active power (+export/-import)"),
    SungrowField("input", 5602, "int32",  1.0,   "W",    "grid_power_r",              "Meter phase A active power"),
    SungrowField("input", 5604, "int32",  1.0,   "W",    "grid_power_s",              "Meter phase B active power"),
    SungrowField("input", 5606, "int32",  1.0,   "W",    "grid_power_t",              "Meter phase C active power"),

    # Load power
    SungrowField("input", 5612, "int32",  1.0,   "W",    "load_power",                "Load power"),

    # Energy counters — daily
    SungrowField("input", 5003, "uint32", 0.1,   "kWh",  "energy_today",              "Daily generation"),
    SungrowField("input", 5008, "uint16", 0.1,   "kWh",  "export_energy_today",       "Daily export energy"),
    SungrowField("input", 5012, "uint16", 0.1,   "kWh",  "import_energy_today",       "Daily import energy"),
    SungrowField("input", 5080, "uint16", 0.1,   "kWh",  "battery_charge_today",      "Daily battery charge"),
    SungrowField("input", 5081, "uint16", 0.1,   "kWh",  "battery_discharge_today",   "Daily battery discharge"),
    SungrowField("input", 5082, "uint16", 0.1,   "kWh",  "load_energy_today",         "Daily load energy"),
    SungrowField("input", 5083, "uint16", 0.1,   "kWh",  "self_consumption_today",    "Daily self-consumption"),

    # Energy counters — total
    SungrowField("input", 5004, "uint32", 0.1,   "kWh",  "total_export_energy",       "Total export energy"),
    SungrowField("input", 5006, "uint32", 0.1,   "kWh",  "total_import_energy",       "Total import energy"),
    SungrowField("input", 5084, "uint32", 0.1,   "kWh",  "battery_charge_total",      "Total battery charge"),
    SungrowField("input", 5085, "uint32", 0.1,   "kWh",  "battery_discharge_total",   "Total battery discharge"),
    SungrowField("input", 5086, "uint32", 0.1,   "kWh",  "load_energy_total",         "Total load energy"),
]

# ---------------------------------------------------------------------------
# Sungrow Holding Registers (configuration / settings)
# ---------------------------------------------------------------------------
SUNGROW_HOLDING_REGISTERS: list[SungrowField] = [
    SungrowField("holding", 13000, "uint16", 1.0,  "%",   "battery_reserve_soc",    "Battery minimum SOC"),
    SungrowField("holding", 13001, "uint16", 1.0,  "%",   "battery_target_soc",     "Battery charge target SOC"),
    SungrowField("holding", 13002, "uint16", 1.0,  "W",   "max_charge_power",       "Max charge power"),
    SungrowField("holding", 13003, "uint16", 1.0,  "W",   "max_discharge_power",    "Max discharge power"),
    SungrowField("holding", 13049, "uint16", 1.0,  "",    "work_mode",              "Work mode"),
    SungrowField("holding", 13050, "uint16", 1.0,  "",    "ems_mode",               "EMS mode"),
]

# ---------------------------------------------------------------------------
# Work mode enum (Sungrow)
# ---------------------------------------------------------------------------
SUNGROW_WORK_MODES: dict[int, str] = {
    0: "self_use",
    1: "feed_in",
    2: "backup",
    3: "time_of_use",
}


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[SungrowField],
) -> dict[str, tuple[float | None, str]]:
    """Decode raw Modbus register values for Sungrow.

    ``raw`` should be {str(0-based-address): int_value}.
    """
    result: dict[str, tuple[float | None, str]] = {}
    for f in fields:
        addr_str = str(f.address)
        if addr_str not in raw:
            continue
        raw_val = raw[addr_str]
        if f.data_type == "uint16":
            value = float(raw_val & 0xFFFF) * f.scale
        elif f.data_type == "int16":
            signed = raw_val if raw_val < 0x8000 else raw_val - 0x10000
            value = float(signed) * f.scale
        elif f.data_type == "uint32":
            low_str = str(f.address + 1)
            if low_str not in raw:
                continue
            combined = (raw_val << 16) | (raw[low_str] & 0xFFFF)
            value = float(combined) * f.scale
        elif f.data_type == "int32":
            low_str = str(f.address + 1)
            if low_str not in raw:
                continue
            combined = (raw_val << 16) | (raw[low_str] & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            value = float(combined) * f.scale
        else:
            continue
        result[f.metric] = (value, f.unit)
    return result
