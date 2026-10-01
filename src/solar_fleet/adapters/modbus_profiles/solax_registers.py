"""SolaX Power (X1-Hybrid, X3-Hybrid G3/G4) Modbus register profile.

Evidence & Sources:
- Brand Registry: SOLAX_HOLDING_REGISTERS
- SolaX Modbus RTU / TCP documentation & ha-solax-modbus
"""

from __future__ import annotations

from typing import NamedTuple


class SolaxField(NamedTuple):
    """SolaX Modbus register field definition."""
    register_type: str    # "holding" | "input"
    address: int          # Modbus register address
    data_type: str        # "uint16" | "int16" | "uint32" | "int32"
    scale: float
    unit: str
    metric: str
    description: str


SOLAX_HYBRID_REGISTERS: list[SolaxField] = [
    SolaxField("holding", 0,  "uint16", 0.1,  "V",   "grid_voltage_r",    "Grid voltage L1"),
    SolaxField("holding", 1,  "int16",  0.1,  "A",   "grid_current_r",    "Grid current L1"),
    SolaxField("holding", 2,  "int16",  1.0,  "W",   "grid_power",        "Total grid power (+ imp / - exp)"),
    SolaxField("holding", 10, "uint16", 0.1,  "V",   "pv1_voltage",       "PV1 input voltage"),
    SolaxField("holding", 12, "uint16", 1.0,  "W",   "pv1_power",         "PV1 input power"),
    SolaxField("holding", 13, "uint16", 1.0,  "W",   "pv2_power",         "PV2 input power"),
    SolaxField("holding", 19, "uint16", 0.01, "V",   "battery_voltage",   "Battery terminal voltage"),
    SolaxField("holding", 20, "int16",  0.1,  "A",   "battery_current",   "Battery current (+ charge / - discharge)"),
    SolaxField("holding", 21, "int16",  1.0,  "W",   "battery_power",     "Battery active power"),
    SolaxField("holding", 22, "uint16", 1.0,  "%",   "battery_soc",       "Battery state of charge"),
    SolaxField("holding", 24, "int16",  1.0,  "°C",  "battery_temp",      "Battery internal temperature"),
    # Control registers (RW)
    SolaxField("holding", 31, "uint16", 1.0,  "",    "work_mode",         "0=Self Use, 1=Feed-in, 2=Backup, 3=Manual"),
    SolaxField("holding", 32, "uint16", 0.1,  "A",   "manual_rate_amps",  "Manual charge/discharge rate"),
    SolaxField("holding", 38, "uint16", 1.0,  "W",   "export_limit_w",    "Backflow export limit in Watts"),
]


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[SolaxField] | None = None,
) -> dict[str, tuple[float | None, str]]:
    """Decode raw register dict to canonical {metric: (value, unit)}.

    Args:
        raw: {str(register_address): int_value}
        fields: field list to use; defaults to SOLAX_HYBRID_REGISTERS
    """
    if fields is None:
        fields = SOLAX_HYBRID_REGISTERS

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
