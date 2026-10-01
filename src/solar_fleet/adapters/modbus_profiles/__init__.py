"""Modbus register profile registry.

Central lookup for vendor + model_series → register field list + decoder.

Usage:
    from solar_fleet.adapters.modbus_profiles import get_register_map, decode_registers

    fields = get_register_map("growatt", "SPH")
    points = decode_registers(raw_regs, "growatt", "SPH")
"""

from __future__ import annotations

from typing import Any

# ---------------------------------------------------------------------------
# Solis Modbus registers (condensed — Solis primarily uses cloud API)
# From solis-modbus-auto (MIT) and SolisCloud Modbus documentation
# ---------------------------------------------------------------------------
from typing import NamedTuple as _NT

from .deye_sunsynk_registers import (
    DEYE_SUNSYNK_REGISTERS,
    DeyeField,
)
from .deye_sunsynk_registers import (
    decode_raw_registers as _deye_decode,
)
from .foxess_registers import (
    FOXESS_H_REGISTERS,
    FoxessField,
)
from .foxess_registers import (
    decode_raw_registers as _foxess_decode,
)
from .growatt_registers import (
    GROWATT_MIN_INPUT_REGISTERS,
    GROWATT_SPH_INPUT_REGISTERS,
    GrowattField,
)
from .growatt_registers import (
    decode_raw_registers as _growatt_decode,
)
from .growatt_registers import (
    registers_for_series as _growatt_series,
)
from .huawei_registers import (
    HUAWEI_SUN2000_REGISTERS,
    HuaweiField,
)
from .huawei_registers import (
    decode_raw_registers as _huawei_decode,
)
from .sofar_registers import (
    SOFAR_HYD_REGISTERS,
    SofarField,
)
from .sofar_registers import (
    decode_raw_registers as _sofar_decode,
)
from .solax_registers import (
    SOLAX_HYBRID_REGISTERS,
    SolaxField,
)
from .solax_registers import (
    decode_raw_registers as _solax_decode,
)
from .sungrow_commercial import (
    SUNGROW_COMMERCIAL_REGISTERS,
    SungrowCommercialProfile,
)
from .sungrow_commercial import (
    decode_commercial_raw_registers as _sungrow_commercial_decode,
)
from .sungrow_registers import (
    SUNGROW_SHX_INPUT_REGISTERS,
    SungrowField,
)
from .sungrow_registers import (
    decode_raw_registers as _sungrow_decode,
)


class SolisField(_NT):
    """Solis Modbus register field."""
    address: int
    data_type: str
    scale: float
    unit: str
    metric: str
    description: str


SOLIS_S6_REGISTERS: list[SolisField] = [
    SolisField(3003, "u16", 0.1, "°C",  "inverter_temp",  "Inverter temperature"),
    SolisField(3005, "u16", 1.0, "",    "inverter_status","Inverter status"),
    SolisField(3006, "u32", 0.1, "kWh", "energy_today",   "Generated energy today"),
    SolisField(3008, "u32", 0.1, "kWh", "energy_total",   "Generated energy total"),
    SolisField(3021, "u16", 0.1, "V",   "pv1_voltage",    "PV1 voltage"),
    SolisField(3022, "u16", 0.1, "A",   "pv1_current",    "PV1 current"),
    SolisField(3023, "u16", 0.1, "V",   "pv2_voltage",    "PV2 voltage"),
    SolisField(3024, "u16", 0.1, "A",   "pv2_current",    "PV2 current"),
    SolisField(3035, "i32", 1.0, "W",   "active_power",   "Active output power"),
    SolisField(3042, "u16", 0.1, "V",   "grid_voltage_r", "Grid voltage A"),
    SolisField(3043, "u16", 0.1, "V",   "grid_voltage_s", "Grid voltage B"),
    SolisField(3044, "u16", 0.1, "V",   "grid_voltage_t", "Grid voltage C"),
    SolisField(3052, "u16", 0.01,"Hz",  "grid_frequency", "Grid frequency"),
    SolisField(3100, "u16", 1.0, "%",   "battery_soc",    "Battery SOC"),
    SolisField(3102, "u16", 0.1, "V",   "battery_voltage","Battery voltage"),
    SolisField(3103, "i16", 0.1, "A",   "battery_current","Battery current"),
    SolisField(3105, "i32", 1.0, "W",   "battery_power",  "Battery power"),
    SolisField(3110, "i16", 0.1, "°C",  "battery_temp",   "Battery temperature"),
    SolisField(3125, "i32", 1.0, "W",   "grid_power",     "Grid power"),
    SolisField(3178, "u32", 0.1, "kWh", "battery_charge_today",    "Battery charge today"),
    SolisField(3180, "u32", 0.1, "kWh", "battery_discharge_today", "Battery discharge today"),
    SolisField(3182, "u32", 0.1, "kWh", "import_energy_today",     "Grid import today"),
    SolisField(3184, "u32", 0.1, "kWh", "export_energy_today",     "Grid export today"),
    SolisField(3201, "i32", 1.0, "W",   "load_power",              "Load power"),
]


def _solis_decode(raw: dict[str, int], _series: str) -> dict[str, tuple[float | None, str]]:
    result: dict[str, tuple[float | None, str]] = {}
    for f in SOLIS_S6_REGISTERS:
        addr_str = str(f.address)
        if addr_str not in raw:
            continue
        raw_val = raw[addr_str]
        if f.data_type == "u16":
            value: float | None = float(raw_val & 0xFFFF) * f.scale
        elif f.data_type == "i16":
            signed = raw_val if raw_val < 0x8000 else raw_val - 0x10000
            value = float(signed) * f.scale
        elif f.data_type == "u32":
            low = str(f.address + 1)
            if low not in raw:
                continue
            combined = (raw_val << 16) | (raw[low] & 0xFFFF)
            value = float(combined) * f.scale
        elif f.data_type == "i32":
            low = str(f.address + 1)
            if low not in raw:
                continue
            combined = (raw_val << 16) | (raw[low] & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            value = float(combined) * f.scale
        else:
            continue
        result[f.metric] = (value, f.unit)
    return result


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------
# Maps (vendor_lower, model_series_lower) → (field_list, decode_fn)
_REGISTRY: dict[tuple[str, str], tuple[list, Any]] = {
    # Growatt
    ("growatt", "sph"):   (GROWATT_SPH_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, _growatt_series("SPH"))),
    ("growatt", "spa"):   (GROWATT_SPH_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, _growatt_series("SPA"))),
    ("growatt", "mix"):   (GROWATT_SPH_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, _growatt_series("MIX"))),
    ("growatt", "min"):   (GROWATT_MIN_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, _growatt_series("MIN"))),
    ("growatt", "mid"):   (GROWATT_MIN_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, _growatt_series("MID"))),
    ("growatt", "max"):   (GROWATT_MIN_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, _growatt_series("MAX"))),
    ("growatt", ""):      (GROWATT_SPH_INPUT_REGISTERS, lambda r, s: _growatt_decode(r, GROWATT_SPH_INPUT_REGISTERS)),
    # Sungrow
    ("sungrow", "shx"):            (SUNGROW_SHX_INPUT_REGISTERS, lambda r, s: _sungrow_decode(r, SUNGROW_SHX_INPUT_REGISTERS)),
    ("sungrow", "sh"):             (SUNGROW_SHX_INPUT_REGISTERS, lambda r, s: _sungrow_decode(r, SUNGROW_SHX_INPUT_REGISTERS)),
    ("sungrow", "sg"):             (SUNGROW_SHX_INPUT_REGISTERS, lambda r, s: _sungrow_decode(r, SUNGROW_SHX_INPUT_REGISTERS)),
    ("sungrow", "sg110cx"):        (SUNGROW_COMMERCIAL_REGISTERS, lambda r, s: _sungrow_commercial_decode(r, s)),
    ("sungrow", "sg125hx"):        (SUNGROW_COMMERCIAL_REGISTERS, lambda r, s: _sungrow_commercial_decode(r, s)),
    ("sungrow", "sg250hx"):        (SUNGROW_COMMERCIAL_REGISTERS, lambda r, s: _sungrow_commercial_decode(r, s)),
    ("sungrow", "sg_commercial"):  (SUNGROW_COMMERCIAL_REGISTERS, lambda r, s: _sungrow_commercial_decode(r, s)),
    ("sungrow", "commercial"):     (SUNGROW_COMMERCIAL_REGISTERS, lambda r, s: _sungrow_commercial_decode(r, s)),
    ("sungrow", ""):               (SUNGROW_SHX_INPUT_REGISTERS, lambda r, s: _sungrow_decode(r, SUNGROW_SHX_INPUT_REGISTERS)),
    # Huawei
    ("huawei", "sun2000"):  (HUAWEI_SUN2000_REGISTERS, lambda r, s: _huawei_decode(r, HUAWEI_SUN2000_REGISTERS)),
    ("huawei", "sun2000-map10ku"):  (HUAWEI_SUN2000_REGISTERS, lambda r, s: _huawei_decode(r, HUAWEI_SUN2000_REGISTERS)),
    ("huawei", ""):  (HUAWEI_SUN2000_REGISTERS, lambda r, s: _huawei_decode(r, HUAWEI_SUN2000_REGISTERS)),
    # Solis (Modbus direct — less common; usually uses cloud)
    ("solis", "s6"):  (SOLIS_S6_REGISTERS, _solis_decode),
    ("solis", ""):    (SOLIS_S6_REGISTERS, _solis_decode),
    # Deye (Modbus TCP / RTU / SOLARMAN V5 logger)
    ("deye", "hybrid"):  (DEYE_SUNSYNK_REGISTERS, lambda r, s: _deye_decode(r, DEYE_SUNSYNK_REGISTERS)),
    ("deye", "sg04"):    (DEYE_SUNSYNK_REGISTERS, lambda r, s: _deye_decode(r, DEYE_SUNSYNK_REGISTERS)),
    ("deye", "sg01"):    (DEYE_SUNSYNK_REGISTERS, lambda r, s: _deye_decode(r, DEYE_SUNSYNK_REGISTERS)),
    ("deye", ""):        (DEYE_SUNSYNK_REGISTERS, lambda r, s: _deye_decode(r, DEYE_SUNSYNK_REGISTERS)),
    # Sunsynk (Modbus TCP / RTU - Deye OEM register compatible)
    ("sunsynk", "hybrid"): (DEYE_SUNSYNK_REGISTERS, lambda r, s: _deye_decode(r, DEYE_SUNSYNK_REGISTERS)),
    ("sunsynk", ""):       (DEYE_SUNSYNK_REGISTERS, lambda r, s: _deye_decode(r, DEYE_SUNSYNK_REGISTERS)),
    # Sofar Solar (HYD / ME series)
    ("sofar", "hyd"):      (SOFAR_HYD_REGISTERS, lambda r, s: _sofar_decode(r, SOFAR_HYD_REGISTERS)),
    ("sofar", "me"):       (SOFAR_HYD_REGISTERS, lambda r, s: _sofar_decode(r, SOFAR_HYD_REGISTERS)),
    ("sofar", ""):         (SOFAR_HYD_REGISTERS, lambda r, s: _sofar_decode(r, SOFAR_HYD_REGISTERS)),
    # SolaX Power (X1 / X3 Hybrid)
    ("solax", "hybrid"):   (SOLAX_HYBRID_REGISTERS, lambda r, s: _solax_decode(r, SOLAX_HYBRID_REGISTERS)),
    ("solax", "x1"):       (SOLAX_HYBRID_REGISTERS, lambda r, s: _solax_decode(r, SOLAX_HYBRID_REGISTERS)),
    ("solax", "x3"):       (SOLAX_HYBRID_REGISTERS, lambda r, s: _solax_decode(r, SOLAX_HYBRID_REGISTERS)),
    ("solax", ""):         (SOLAX_HYBRID_REGISTERS, lambda r, s: _solax_decode(r, SOLAX_HYBRID_REGISTERS)),
    # FoxESS (H1 / H3 / AC1 / KH)
    ("foxess", "h"):       (FOXESS_H_REGISTERS, lambda r, s: _foxess_decode(r, FOXESS_H_REGISTERS)),
    ("foxess", "kh"):      (FOXESS_H_REGISTERS, lambda r, s: _foxess_decode(r, FOXESS_H_REGISTERS)),
    ("foxess", ""):        (FOXESS_H_REGISTERS, lambda r, s: _foxess_decode(r, FOXESS_H_REGISTERS)),
}


def get_register_map(vendor: str, model_series: str = "", *, exact: bool = False) -> list:
    """Return the register field list for a (vendor, model_series) pair.

    Case-insensitive.
    If exact=True, requires an exact match for both vendor and model_series without
    fallback (mandatory for operational/control safety gating).
    If exact=False, diagnostic fallback to vendor default is allowed.

    Raises:
        KeyError: if profile not registered (or UNKNOWN_PROFILE if exact=True and no exact match)
    """
    key = (vendor.lower(), model_series.lower())
    if key in _REGISTRY and (not exact or model_series.strip() != ""):
        return _REGISTRY[key][0]
    if exact:
        raise KeyError(
            f"UNKNOWN_PROFILE: Exact profile required for operational/control resolution "
            f"(vendor={vendor!r}, series={model_series!r})"
        )
    # Try vendor default
    default_key = (vendor.lower(), "")
    if default_key in _REGISTRY:
        return _REGISTRY[default_key][0]
    raise KeyError(
        f"No Modbus register profile for vendor={vendor!r} series={model_series!r}. "
        f"Known vendors: {sorted({k[0] for k in _REGISTRY})}"
    )


def get_exact_profile(vendor: str, model_series: str) -> tuple[list, Any]:
    """Retrieve operational/control profile with strict exact matching and no fallback."""
    if not model_series:
        raise KeyError(f"UNKNOWN_PROFILE: model_series required for exact profile (vendor={vendor!r})")
    key = (vendor.lower(), model_series.lower())
    if key in _REGISTRY:
        return _REGISTRY[key]
    raise KeyError(
        f"UNKNOWN_PROFILE: No exact profile registered for vendor={vendor!r} series={model_series!r}"
    )


def get_function_code(vendor: str, model_series: str = "") -> int:
    """Return expected Modbus function code (0x03 Holding or 0x04 Input Registers)."""
    v = vendor.lower()
    s = model_series.lower()
    if v == "sungrow":
        return 0x04
    if v == "growatt" and any(x in s for x in ("sph", "min", "mix", "spa", "mid", "max", "")):
        return 0x04
    return 0x03


def decode_registers(
    raw: dict[str, int],
    vendor: str,
    model_series: str = "",
) -> dict[str, tuple[float | None, str]]:
    """Decode raw register dict to canonical {metric: (value, unit)}.

    Case-insensitive. Falls back to vendor default.

    Args:
        raw: {str(register_address): int_value}
        vendor: vendor name
        model_series: model series (optional)

    Returns:
        {canonical_metric: (value, unit)}
    """
    key = (vendor.lower(), model_series.lower())
    if key in _REGISTRY:
        return _REGISTRY[key][1](raw, model_series)
    default_key = (vendor.lower(), "")
    if default_key in _REGISTRY:
        return _REGISTRY[default_key][1](raw, model_series)
    raise KeyError(
        f"No register decoder for vendor={vendor!r} series={model_series!r}"
    )


def list_supported_profiles() -> list[dict]:
    """Return all supported (vendor, model_series) combinations."""
    return [
        {"vendor": v, "model_series": s}
        for v, s in sorted(_REGISTRY.keys())
    ]


__all__ = [
    "DeyeField",
    "FoxessField",
    "GrowattField",
    "HuaweiField",
    "SUNGROW_COMMERCIAL_REGISTERS",
    "SofarField",
    "SolaxField",
    "SolisField",
    "SungrowCommercialProfile",
    "SungrowField",
    "decode_registers",
    "get_exact_profile",
    "get_function_code",
    "get_register_map",
    "list_supported_profiles",
]
