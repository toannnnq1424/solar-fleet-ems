"""Sofar Solar (HYD 3000-6000-ES, HYD 5K-20KTL-3PH, ME3000SP) Modbus register profile.

Evidence & Sources:
- Brand Registry: SOFAR_HOLDING_REGISTERS
- solarman_profile_engine: Sofar G3 HYD 5..20KTL-3PH & ZCS Azzurro 3PH
- ha-solarman: sofar_g3hyd.yaml, sofar_hybrid.yaml
"""

from __future__ import annotations

from typing import NamedTuple


class SofarField(NamedTuple):
    """Sofar Modbus register field definition."""
    register_type: str    # "holding" | "input"
    address: int          # Modbus register address
    data_type: str        # "uint16" | "int16" | "uint32" | "int32"
    scale: float
    unit: str
    metric: str
    description: str


# ---------------------------------------------------------------------------
# Sofar HYD Series (Single-phase ES & Three-phase KTL)
# ---------------------------------------------------------------------------
SOFAR_HYD_REGISTERS: list[SofarField] = [
    SofarField("holding", 512, "uint16", 1.0,  "",    "operating_state",   "0=Standby, 1=Self-test, 2=Normal, 4=Fault"),
    SofarField("holding", 518, "uint16", 0.1,  "V",   "pv1_voltage",       "PV1 input voltage"),
    SofarField("holding", 520, "uint16", 10.0, "W",   "pv1_power",         "PV1 input power"),
    SofarField("holding", 521, "uint16", 0.1,  "V",   "pv2_voltage",       "PV2 input voltage"),
    SofarField("holding", 523, "uint16", 10.0, "W",   "pv2_power",         "PV2 input power"),
    SofarField("holding", 524, "uint16", 0.1,  "V",   "grid_voltage_r",    "Grid AC line voltage"),
    SofarField("holding", 526, "int16",  10.0, "W",   "grid_power",        "Grid active power (+ import / - export)"),
    SofarField("holding", 528, "uint16", 0.1,  "V",   "battery_voltage",   "Battery terminal voltage"),
    SofarField("holding", 529, "int16",  0.01, "A",   "battery_current",   "Battery current (+ charge / - discharge)"),
    SofarField("holding", 530, "int16",  10.0, "W",   "battery_power",     "Battery active power"),
    SofarField("holding", 531, "uint16", 1.0,  "%",   "battery_soc",       "Battery state of charge"),
    SofarField("holding", 532, "int16",  1.0,  "°C",  "battery_temp",      "Battery internal temperature"),
    # Control registers (RW)
    SofarField("holding", 4352, "uint16", 1.0, "",    "work_mode",         "0=Self Use, 1=TOU, 2=Timing, 3=Passive"),
    SofarField("holding", 4353, "uint16", 10.0, "W",  "max_charge_power",  "Max battery charge power limit"),
    SofarField("holding", 4354, "uint16", 10.0, "W",  "max_discharge_power", "Max battery discharge power limit"),
    SofarField("holding", 4355, "uint16", 10.0, "W",  "export_power_limit","Export power limit ceiling"),
]


def decode_raw_registers(
    raw: dict[str, int],
    fields: list[SofarField] | None = None,
) -> dict[str, tuple[float | None, str]]:
    """Decode raw register dict to canonical {metric: (value, unit)}.

    Args:
        raw: {str(register_address): int_value}
        fields: field list to use; defaults to SOFAR_HYD_REGISTERS
    """
    if fields is None:
        fields = SOFAR_HYD_REGISTERS

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

    # Derive total pv_power if pv1 & pv2 are available
    if "pv_power" not in result and (pv1_w > 0 or pv2_w > 0):
        result["pv_power"] = (pv1_w + pv2_w, "W")

    return result
