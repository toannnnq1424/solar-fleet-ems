"""FoxESS (H1, H3, AC1, KH Series) Modbus register profile.

Evidence & Sources:
- Brand Registry: FOXESS_HOLDING_REGISTERS
- ha-foxess-modbus & FoxESS Modbus protocol specification
"""

from __future__ import annotations

from typing import NamedTuple


class FoxessField(NamedTuple):
    """FoxESS Modbus register field definition."""
    register_type: str    # "holding" | "input"
    address: int          # Modbus register address
    data_type: str        # "uint16" | "int16" | "uint32" | "int32"
    scale: float
    unit: str
    metric: str
    description: str


FOXESS_H_REGISTERS: list[FoxessField] = [
    FoxessField("holding", 12544, "uint16", 0.1,  "V",   "grid_voltage_r",     "AC grid line voltage"),
    FoxessField("holding", 12546, "int16",  1.0,  "W",   "grid_power",         "Grid active power (+ imp / - exp)"),
    FoxessField("holding", 12547, "uint16", 0.01, "Hz",  "grid_frequency",     "Grid line frequency"),
    FoxessField("holding", 12549, "uint16", 1.0,  "W",   "pv1_power",          "PV1 solar power"),
    FoxessField("holding", 12550, "uint16", 1.0,  "W",   "pv2_power",          "PV2 solar power"),
    FoxessField("holding", 12553, "int16",  1.0,  "°C",  "inverter_temp",      "Inverter internal temperature"),
    FoxessField("holding", 12570, "uint16", 0.1,  "V",   "battery_voltage",    "Battery pack voltage"),
    FoxessField("holding", 12571, "int16",  0.1,  "A",   "battery_current",    "Battery current (+ charge / - discharge)"),
    FoxessField("holding", 12572, "int16",  1.0,  "W",   "battery_power",      "Battery power"),
    FoxessField("holding", 12574, "uint16", 1.0,  "%",   "battery_soc",        "Battery state of charge"),
    FoxessField("holding", 12576, "uint16", 1.0,  "%",   "battery_soh",        "Battery state of health"),
    # Control registers (RW)
    FoxessField("holding", 4352,  "uint16", 1.0,  "",    "work_mode",          "0=Self Use, 1=Feed-in, 2=Backup, 3=Force Charge"),
    FoxessField("holding", 4354,  "uint16", 1.0,  "W",   "force_charge_power", "Grid forced charge power setting"),
    FoxessField("holding", 4357,  "uint16", 1.0,  "%",   "min_soc_floor",      "Minimum battery discharge floor SOC"),
]


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[FoxessField] | None = None,
) -> dict[str, tuple[float | None, str]]:
    """Decode raw register dict to canonical {metric: (value, unit)}.

    Args:
        raw: {str(register_address): int_value}
        fields: field list to use; defaults to FOXESS_H_REGISTERS
    """
    if fields is None:
        fields = FOXESS_H_REGISTERS

    result: dict[str, tuple[float | None, str]] = {}
    pv1_w: float = 0.0
    pv2_w: float = 0.0

    for f in fields:
        addr_str = str(f.address)
        if addr_str not in raw:
            continue
        raw_val = raw[addr_str]

        if f.data_type == "uint16":
            value: float | None = float(raw_val & 0xFFFF) * f.scale
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
        if f.metric == "pv1_power" and value is not None:
            pv1_w = value
        elif f.metric == "pv2_power" and value is not None:
            pv2_w = value

    if "pv_power" not in result and (pv1_w > 0 or pv2_w > 0):
        result["pv_power"] = (pv1_w + pv2_w, "W")

    return result
