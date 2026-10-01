"""Modbus register definitions for Deye and Sunsynk hybrid inverters.

Deye and Sunsynk share the same inverter hardware and register architecture
(Ningbo Deye Inverter Technology Co., Ltd OEM).
Registers use Function Code 0x03 (Read Holding Registers).

Source:
- Deye Modbus RTU/TCP Protocol V1.1 (Function Code 0x03)
- Sunsynk Inverter Modbus Protocol Manual
- ha-solarman deye-hybrid profile (MIT, David Rapan)
- batpred/sunsynk.py (licensed usage per project owner)
"""

from __future__ import annotations

from typing import NamedTuple


class DeyeField(NamedTuple):
    """A single Modbus holding register field for Deye / Sunsynk."""
    address: int
    data_type: str       # "u16" | "i16" | "u32" | "i32"
    scale: float
    unit: str
    metric: str          # Canonical metric name from interfaces.py
    description: str


# ---------------------------------------------------------------------------
# Core Telemetry & Energy Registers (Holding Registers, FC 0x03)
# ---------------------------------------------------------------------------
DEYE_SUNSYNK_REGISTERS: list[DeyeField] = [
    # Status & Temperatures
    DeyeField(90,   "i16", 0.1,  "°C",   "grid_temp",                "DC / Heat-sink Temperature"),
    DeyeField(91,   "i16", 0.1,  "°C",   "inverter_temp",            "Inverter AC Temperature"),
    DeyeField(182,  "i16", 0.1,  "°C",   "battery_temp",             "Battery Ambient Temperature"),

    # PV DC Power & Strings
    DeyeField(53,   "u16", 1.0,  "W",    "pv_power",                 "Total PV Power"),
    DeyeField(186,  "u16", 0.1,  "V",    "pv1_voltage",              "PV1 Voltage"),
    DeyeField(187,  "u16", 0.1,  "A",    "pv1_current",              "PV1 Current"),
    DeyeField(188,  "u16", 0.1,  "V",    "pv2_voltage",              "PV2 Voltage"),
    DeyeField(189,  "u16", 0.1,  "A",    "pv2_current",              "PV2 Current"),
    DeyeField(176,  "u16", 1.0,  "W",    "pv1_power",                "PV1 Power"),
    DeyeField(177,  "u16", 1.0,  "W",    "pv2_power",                "PV2 Power"),

    # Battery & BMS
    DeyeField(183,  "u16", 0.01, "V",    "battery_voltage",          "Battery Terminal Voltage"),
    DeyeField(184,  "u16", 1.0,  "%",    "battery_soc",              "Battery Lead-Acid SOC"),
    DeyeField(190,  "i16", 1.0,  "W",    "battery_power",            "Battery Power (-charge, +discharge)"),
    DeyeField(191,  "i16", 0.01, "A",    "battery_current",          "Battery Current"),
    DeyeField(316,  "u16", 1.0,  "%",    "bms_soc",                  "Battery BMS SOC (Lithium)"),
    DeyeField(317,  "u16", 0.01, "V",    "bms_voltage",              "Battery BMS Voltage"),
    DeyeField(318,  "i16", 0.1,  "A",    "bms_current",              "Battery BMS Current"),
    DeyeField(324,  "u16", 1.0,  "%",    "battery_soh",              "Battery BMS SOH"),

    # Inverter AC & Grid
    DeyeField(172,  "i16", 1.0,  "W",    "active_power",             "Inverter Active Output Power"),
    DeyeField(173,  "u16", 0.01, "Hz",   "grid_frequency",           "Grid Frequency"),
    DeyeField(175,  "i16", 1.0,  "W",    "grid_power",               "Grid Total Power (-import, +export)"),
    DeyeField(178,  "u16", 1.0,  "W",    "load_power",               "Total Essential Load Power"),
    DeyeField(194,  "u16", 0.1,  "V",    "grid_voltage_r",           "Grid Voltage Phase A/L1"),
    DeyeField(195,  "u16", 0.1,  "V",    "grid_voltage_s",           "Grid Voltage Phase B/L2"),
    DeyeField(196,  "u16", 0.1,  "V",    "grid_voltage_t",           "Grid Voltage Phase C/L3"),
    DeyeField(197,  "i16", 0.1,  "A",    "grid_current_r",           "Grid Current Phase A/L1"),

    # Cumulative Daily and Total Energies
    DeyeField(60,   "u16", 0.1,  "kWh",  "pv_energy_today",          "PV Generation Today"),
    DeyeField(63,   "u32", 0.1,  "kWh",  "energy_total",             "Total Inverter Energy Generation"),
    DeyeField(70,   "u16", 0.1,  "kWh",  "battery_charge_today",     "Battery Charge Today"),
    DeyeField(71,   "u16", 0.1,  "kWh",  "battery_discharge_today",  "Battery Discharge Today"),
    DeyeField(76,   "u16", 0.1,  "kWh",  "import_energy_today",      "Grid Energy Import Today"),
    DeyeField(77,   "u16", 0.1,  "kWh",  "export_energy_today",      "Grid Energy Export Today"),
    DeyeField(84,   "u16", 0.1,  "kWh",  "load_energy_today",        "Load Consumption Today"),
]


# ---------------------------------------------------------------------------
# TOU / System Mode Setting Registers (Holding Registers, FC 0x03 read, 0x10 write)
# ---------------------------------------------------------------------------
DEYE_TOU_REGISTERS: dict[str, int] = {
    # Program 1..6 Times (Minutes or HHMM)
    "prog1_time": 250,
    "prog2_time": 251,
    "prog3_time": 252,
    "prog4_time": 253,
    "prog5_time": 254,
    "prog6_time": 255,
    # Program 1..6 Power limits (W)
    "prog1_power": 256,
    "prog2_power": 257,
    "prog3_power": 258,
    "prog4_power": 259,
    "prog5_power": 260,
    "prog6_power": 261,
    # Program 1..6 Target SOCs (%)
    "prog1_soc": 268,
    "prog2_soc": 269,
    "prog3_soc": 270,
    "prog4_soc": 271,
    "prog5_soc": 272,
    "prog6_soc": 273,
    # Program 1..6 Charge flags (bit 0: grid charge)
    "prog1_flags": 274,
    "prog2_flags": 275,
    "prog3_flags": 276,
    "prog4_flags": 277,
    "prog5_flags": 278,
    "prog6_flags": 279,
}


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[DeyeField] = DEYE_SUNSYNK_REGISTERS,
) -> dict[str, tuple[float | None, str]]:
    """Decode raw Deye/Sunsynk registers into canonical metrics.

    ``raw`` should be {str(register_address): int_value}.
    If Lithium BMS SOC (register 316) is available and > 0, it takes precedence
    over lead-acid battery_soc (register 184).
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
            low_str = str(f.address + 1)
            if low_str not in raw:
                continue
            combined = ((raw_val & 0xFFFF) << 16) | (raw[low_str] & 0xFFFF)
            value = float(combined) * f.scale
        elif f.data_type == "i32":
            low_str = str(f.address + 1)
            if low_str not in raw:
                continue
            combined = ((raw_val & 0xFFFF) << 16) | (raw[low_str] & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            value = float(combined) * f.scale
        else:
            continue

        result[f.metric] = (round(value, 3), f.unit)

    # Prefer BMS SOC over Lead-acid SOC if BMS SOC is reported (> 0)
    if "bms_soc" in result and result["bms_soc"][0] is not None and result["bms_soc"][0] > 0:
        result["battery_soc"] = result["bms_soc"]

    return result
