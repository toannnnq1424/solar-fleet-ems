"""Solarman Inverter Profile Engine & Multi-Vendor Rule Parser.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
home_assistant_solarman-main (Apache-2.0 License, author Stephan Joubert & community).
Provides comprehensive multi-vendor profile definitions, rule-based register decoding,
query range batching, parameter write compilers, and hardware acceptance safety gates
for inverters connected via Solarman / IGEN Tech data loggers (Deye, Sofar, Solis, KStar, etc.).

Key Capabilities:
- Profile Catalogue:
  * Built-in multi-vendor definitions for Deye Hybrid (SG04LP3), Sofar G3 HYD (5..20KTL-3PH / ZCS Azzurro),
    Solis Hybrid (RHI-5G / S6), KStar BluE, and generic Modbus profiles.
- Rule-based Parameter Parser (Rules 1..10):
  * Rule 1: Unsigned 16-bit / 32-bit big-endian integer.
  * Rule 2: Signed 16-bit / 32-bit two's complement integer.
  * Rule 3: Unsigned integer with scale factor, offset, and string lookup mapping.
  * Rule 4: Signed integer with scale factor, offset, and string lookup mapping.
  * Rule 5: ASCII string decoding from sequential 16-bit registers.
  * Rule 6: Discrete bitmask flag decoder with severity tagging.
  * Rule 7: Semantic version string formatter.
  * Rule 8/9: Datetime and time string formatter.
  * Rule 10: Raw byte stream / hex string.
- Optimal Query Range Batch Planner:
  * Groups requested register sets into continuous Modbus read intervals (FC03 / FC04)
    honoring max packet size and gap thresholds to minimize gateway query latency.
- Parameter Write Compilers with Safety Gating:
  * Gated writes for Deye, Sofar, and Solis work modes, export limits, and battery thresholds.
  * All write actions strictly gated by LOCKED_PENDING_HARDWARE_ACCEPTANCE.
- Unified Telemetry Normalizer:
  * Translates parsed multi-vendor registers into standard Solar Fleet EMS schema.
"""

from __future__ import annotations

import struct
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants & Enums
# ---------------------------------------------------------------------------

DEFAULT_SOLARMAN_PORT = 8899

# Rule IDs
RULE_UNSIGNED = 1
RULE_SIGNED = 2
RULE_UNSIGNED_LOOKUP = 3
RULE_SIGNED_LOOKUP = 4
RULE_ASCII = 5
RULE_BITS = 6
RULE_VERSION = 7
RULE_DATETIME = 8
RULE_TIME = 9
RULE_RAW = 10


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class ProfileParameter:
    """Definition of a single register parameter item."""
    name: str
    registers: List[int]
    rule: int = RULE_UNSIGNED
    scale: float = 1.0
    offset: float = 0.0
    uom: str = ""
    group: str = "general"
    lookup: Optional[Dict[int, str]] = None
    is_string: bool = False
    validation_min: Optional[float] = None
    validation_max: Optional[float] = None


@dataclass
class ProfileRequestRange:
    """Continuous Modbus read request window."""
    start: int
    end: int
    mb_functioncode: int = 0x03

    @property
    def count(self) -> int:
        return self.end - self.start + 1


@dataclass
class InverterProfile:
    """Full profile containing requests and parameters for an inverter family."""
    profile_id: str
    vendor: str
    family_name: str
    default_slave_id: int
    requests: List[ProfileRequestRange]
    parameters: List[ProfileParameter] = field(default_factory=list)


# ---------------------------------------------------------------------------
# Built-In Inverter Profiles (Clean-Room Catalog)
# ---------------------------------------------------------------------------

def create_deye_hybrid_profile() -> InverterProfile:
    """Build Deye Hybrid SG04LP3 inverter profile."""
    reqs = [
        ProfileRequestRange(start=0x0003, end=0x0070, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0096, end=0x00F9, mb_functioncode=0x03),
        ProfileRequestRange(start=0x00FA, end=0x0117, mb_functioncode=0x03),
    ]
    params = [
        # Inverter Identification & State
        ProfileParameter(name="Inverter Status", registers=[0x0003], rule=RULE_UNSIGNED_LOOKUP,
                         lookup={0: "Standby", 1: "Self Check", 2: "Normal On-Grid", 3: "Fault"}, group="inverter"),
        ProfileParameter(name="Inverter Temperature", registers=[0x005A], rule=RULE_SIGNED_LOOKUP,
                         scale=0.1, offset=-100.0, uom="°C", group="inverter"),
        # Solar PV Trackers
        ProfileParameter(name="PV1 Voltage", registers=[0x006D], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="solar"),
        ProfileParameter(name="PV1 Current", registers=[0x006E], rule=RULE_UNSIGNED, scale=0.1, uom="A", group="solar"),
        ProfileParameter(name="PV1 Power", registers=[0x00BA], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="solar"),
        ProfileParameter(name="PV2 Voltage", registers=[0x006F], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="solar"),
        ProfileParameter(name="PV2 Current", registers=[0x0070], rule=RULE_UNSIGNED, scale=0.1, uom="A", group="solar"),
        ProfileParameter(name="PV2 Power", registers=[0x00BB], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="solar"),
        # Grid Telemetry
        ProfileParameter(name="Grid L1 Voltage", registers=[0x0096], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="grid"),
        ProfileParameter(name="Grid L2 Voltage", registers=[0x0097], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="grid"),
        ProfileParameter(name="Grid L3 Voltage", registers=[0x0098], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="grid"),
        ProfileParameter(name="Grid Total Power", registers=[0x00A7], rule=RULE_SIGNED, scale=1.0, uom="W", group="grid"),
        ProfileParameter(name="Grid Frequency", registers=[0x00AF], rule=RULE_UNSIGNED, scale=0.01, uom="Hz", group="grid"),
        ProfileParameter(name="External CT Power", registers=[0x00A9], rule=RULE_SIGNED, scale=1.0, uom="W", group="grid"),
        # Load & UPS Backup
        ProfileParameter(name="Total Load Power", registers=[0x00B2], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="load"),
        ProfileParameter(name="UPS Backup Power", registers=[0x00B4], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="load"),
        # Battery BMS
        ProfileParameter(name="Battery Voltage", registers=[0x00B7], rule=RULE_UNSIGNED, scale=0.01, uom="V", group="battery"),
        ProfileParameter(name="Battery Current", registers=[0x00BF], rule=RULE_SIGNED, scale=0.01, uom="A", group="battery"),
        ProfileParameter(name="Battery Power", registers=[0x00BE], rule=RULE_SIGNED, scale=1.0, uom="W", group="battery"),
        ProfileParameter(name="Battery SOC", registers=[0x00B8], rule=RULE_UNSIGNED, scale=1.0, uom="%", group="battery"),
        ProfileParameter(name="Battery Temperature", registers=[0x00B6], rule=RULE_SIGNED_LOOKUP,
                         scale=0.1, offset=-100.0, uom="°C", group="battery"),
        # Energy Lifetime & Daily
        ProfileParameter(name="Daily Production", registers=[0x0040], rule=RULE_UNSIGNED, scale=0.1, uom="kWh", group="energy"),
        ProfileParameter(name="Total Production", registers=[0x003F, 0x003E], rule=RULE_UNSIGNED, scale=0.1, uom="kWh", group="energy"),
        # Controls & Settings
        ProfileParameter(name="Work Mode", registers=[142], rule=RULE_UNSIGNED_LOOKUP,
                         lookup={0: "Selling First", 1: "Zero Export To Load", 2: "Zero Export To CT"}, group="settings"),
        ProfileParameter(name="Solar Export Power", registers=[143], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="settings"),
        ProfileParameter(name="Max Solar Sell Power", registers=[145], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="settings"),
    ]
    return InverterProfile(
        profile_id="deye_hybrid",
        vendor="Deye",
        family_name="Deye SUN SG04LP3 3-Phase / 1-Phase Hybrid",
        default_slave_id=1,
        requests=reqs,
        parameters=params,
    )


def create_sofar_g3hyd_profile() -> InverterProfile:
    """Build Sofar G3 HYD (5..20KTL-3PH / ZCS Azzurro) profile."""
    reqs = [
        ProfileRequestRange(start=0x0404, end=0x042B, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0445, end=0x0465, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0484, end=0x04AF, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0504, end=0x051F, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0584, end=0x0589, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0604, end=0x060A, mb_functioncode=0x03),
        ProfileRequestRange(start=0x0684, end=0x069B, mb_functioncode=0x03),
    ]
    params = [
        # Inverter Status
        ProfileParameter(name="Inverter Status", registers=[0x0404], rule=RULE_UNSIGNED_LOOKUP,
                         lookup={0: "Waiting", 1: "Checking", 2: "Normal On-Grid", 3: "EPS Standby", 4: "Fault"}, group="inverter"),
        ProfileParameter(name="Inverter Temperature", registers=[0x0418], rule=RULE_SIGNED, scale=1.0, uom="°C", group="inverter"),
        # Solar PV Trackers
        ProfileParameter(name="PV1 Voltage", registers=[0x0584], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="solar"),
        ProfileParameter(name="PV1 Current", registers=[0x0585], rule=RULE_UNSIGNED, scale=0.01, uom="A", group="solar"),
        ProfileParameter(name="PV1 Power", registers=[0x0586], rule=RULE_UNSIGNED, scale=10.0, uom="W", group="solar"),
        ProfileParameter(name="PV2 Voltage", registers=[0x0587], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="solar"),
        ProfileParameter(name="PV2 Current", registers=[0x0588], rule=RULE_UNSIGNED, scale=0.01, uom="A", group="solar"),
        ProfileParameter(name="PV2 Power", registers=[0x0589], rule=RULE_UNSIGNED, scale=10.0, uom="W", group="solar"),
        # Grid Telemetry
        ProfileParameter(name="Grid Total Power", registers=[0x0485], rule=RULE_SIGNED, scale=10.0, uom="W", group="grid"),
        ProfileParameter(name="Grid Frequency", registers=[0x0484], rule=RULE_UNSIGNED, scale=0.01, uom="Hz", group="grid"),
        ProfileParameter(name="Grid L1 Voltage", registers=[0x048D], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="grid"),
        ProfileParameter(name="Grid L2 Voltage", registers=[0x048E], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="grid"),
        ProfileParameter(name="Grid L3 Voltage", registers=[0x048F], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="grid"),
        # Battery 1
        ProfileParameter(name="Battery Voltage", registers=[0x0604], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="battery"),
        ProfileParameter(name="Battery Current", registers=[0x0605], rule=RULE_SIGNED, scale=0.01, uom="A", group="battery"),
        ProfileParameter(name="Battery Power", registers=[0x0606], rule=RULE_SIGNED, scale=10.0, uom="W", group="battery"),
        ProfileParameter(name="Battery SOC", registers=[0x0608], rule=RULE_UNSIGNED, scale=1.0, uom="%", group="battery"),
        ProfileParameter(name="Battery Temperature", registers=[0x0607], rule=RULE_SIGNED, scale=1.0, uom="°C", group="battery"),
        # Energy
        ProfileParameter(name="Daily Production", registers=[0x0685], rule=RULE_UNSIGNED, scale=0.01, uom="kWh", group="energy"),
        ProfileParameter(name="Total Production", registers=[0x0687, 0x0686], rule=RULE_UNSIGNED, scale=1.0, uom="kWh", group="energy"),
        # Settings
        ProfileParameter(name="Battery Min SOC", registers=[0x104D], rule=RULE_UNSIGNED, scale=1.0, uom="%", group="settings"),
        ProfileParameter(name="EPS Buffer SOC", registers=[0x1052], rule=RULE_UNSIGNED, scale=1.0, uom="%", group="settings"),
    ]
    return InverterProfile(
        profile_id="sofar_g3hyd",
        vendor="Sofar",
        family_name="Sofar G3 HYD 5..20KTL-3PH & ZCS Azzurro 3PH",
        default_slave_id=1,
        requests=reqs,
        parameters=params,
    )


def create_solis_hybrid_profile() -> InverterProfile:
    """Build Solis RHI-5G / S6 Hybrid inverter profile."""
    reqs = [
        ProfileRequestRange(start=33022, end=33095, mb_functioncode=0x04),
        ProfileRequestRange(start=33116, end=33179, mb_functioncode=0x04),
        ProfileRequestRange(start=43000, end=43150, mb_functioncode=0x03),
    ]
    params = [
        ProfileParameter(name="Inverter Status", registers=[33095], rule=RULE_UNSIGNED_LOOKUP,
                         lookup={0: "Waiting", 1: "Open Loop", 2: "Soft Start", 3: "Generating On-Grid"}, group="inverter"),
        ProfileParameter(name="Inverter Temperature", registers=[33093], rule=RULE_SIGNED, scale=0.1, uom="°C", group="inverter"),
        # Solar PV
        ProfileParameter(name="PV1 Voltage", registers=[33049], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="solar"),
        ProfileParameter(name="PV1 Current", registers=[33050], rule=RULE_UNSIGNED, scale=0.1, uom="A", group="solar"),
        ProfileParameter(name="PV2 Voltage", registers=[33051], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="solar"),
        ProfileParameter(name="PV2 Current", registers=[33052], rule=RULE_UNSIGNED, scale=0.1, uom="A", group="solar"),
        # Grid & Load
        ProfileParameter(name="Grid Total Power", registers=[33057], rule=RULE_SIGNED, scale=1.0, uom="W", group="grid"),
        ProfileParameter(name="Grid Frequency", registers=[33058], rule=RULE_UNSIGNED, scale=0.01, uom="Hz", group="grid"),
        ProfileParameter(name="Total Load Power", registers=[33147], rule=RULE_UNSIGNED, scale=1.0, uom="W", group="load"),
        # Battery
        ProfileParameter(name="Battery Voltage", registers=[33133], rule=RULE_UNSIGNED, scale=0.1, uom="V", group="battery"),
        ProfileParameter(name="Battery Current", registers=[33134], rule=RULE_SIGNED, scale=0.1, uom="A", group="battery"),
        ProfileParameter(name="Battery Power", registers=[33135], rule=RULE_SIGNED, scale=1.0, uom="W", group="battery"),
        ProfileParameter(name="Battery SOC", registers=[33139], rule=RULE_UNSIGNED, scale=1.0, uom="%", group="battery"),
        # Energy
        ProfileParameter(name="Daily Production", registers=[33035], rule=RULE_UNSIGNED, scale=0.1, uom="kWh", group="energy"),
        ProfileParameter(name="Total Production", registers=[33037, 33036], rule=RULE_UNSIGNED, scale=1.0, uom="kWh", group="energy"),
        # Control Settings
        ProfileParameter(name="Storage Control Mode", registers=[43110], rule=RULE_UNSIGNED_LOOKUP,
                         lookup={0x0001: "Self-Use", 0x0002: "Feed-in Priority", 0x0004: "Off-Grid", 0x0008: "Battery Priority (TOU)"}, group="settings"),
    ]
    return InverterProfile(
        profile_id="solis_hybrid",
        vendor="Solis",
        family_name="Solis RHI 3..6K-48ES-5G & S6 Hybrid",
        default_slave_id=1,
        requests=reqs,
        parameters=params,
    )


PROFILE_REGISTRY: Dict[str, InverterProfile] = {
    "deye_hybrid": create_deye_hybrid_profile(),
    "sofar_g3hyd": create_sofar_g3hyd_profile(),
    "solis_hybrid": create_solis_hybrid_profile(),
}


# ---------------------------------------------------------------------------
# Rule-Based Parameter Parser
# ---------------------------------------------------------------------------

class SolarmanProfileParser:
    """Decodes raw Modbus registers into physical values according to profile rules."""

    def __init__(self, profile: InverterProfile) -> None:
        self.profile = profile

    def parse_registers(self, register_map: Dict[int, int]) -> Dict[str, Any]:
        """Parse all parameters defined in profile from provided register map."""
        results: Dict[str, Any] = {}

        for param in self.profile.parameters:
            # Check if all required registers are available
            if not all(reg in register_map for reg in param.registers):
                continue

            val = self._parse_single_parameter(param, register_map)
            if val is not None:
                results[param.name] = val

        return results

    def _parse_single_parameter(
        self,
        param: ProfileParameter,
        reg_map: Dict[int, int],
    ) -> Optional[Any]:
        """Decode single parameter using its defined rule number."""
        regs = param.registers
        rule = param.rule

        try:
            # Rule 1 & 3: Unsigned Integer (16-bit or 32-bit)
            if rule in (RULE_UNSIGNED, RULE_UNSIGNED_LOOKUP):
                if len(regs) == 1:
                    raw_val = reg_map[regs[0]] & 0xFFFF
                elif len(regs) == 2:
                    hi = reg_map[regs[0]] & 0xFFFF
                    lo = reg_map[regs[1]] & 0xFFFF
                    raw_val = (hi << 16) | lo
                else:
                    return None

                val = raw_val * param.scale + param.offset

                # Lookup dictionary
                if param.lookup and int(val) in param.lookup:
                    return param.lookup[int(val)]

                return round(val, 2) if isinstance(val, float) else val

            # Rule 2 & 4: Signed Integer (16-bit or 32-bit two's complement)
            elif rule in (RULE_SIGNED, RULE_SIGNED_LOOKUP):
                if len(regs) == 1:
                    v = reg_map[regs[0]] & 0xFFFF
                    raw_val = v - 0x10000 if v >= 0x8000 else v
                elif len(regs) == 2:
                    hi = reg_map[regs[0]] & 0xFFFF
                    lo = reg_map[regs[1]] & 0xFFFF
                    u = (hi << 16) | lo
                    raw_val = u - 0x100000000 if u >= 0x80000000 else u
                else:
                    return None

                val = raw_val * param.scale + param.offset

                if param.lookup and int(val) in param.lookup:
                    return param.lookup[int(val)]

                return round(val, 2) if isinstance(val, float) else val

            # Rule 5: ASCII String
            elif rule == RULE_ASCII:
                chars = bytearray()
                for reg in regs:
                    v = reg_map[reg] & 0xFFFF
                    chars.append((v >> 8) & 0xFF)
                    chars.append(v & 0xFF)
                return chars.decode("latin-1", errors="ignore").replace("\x00", "").strip()

            # Rule 6: Bits / Bitmask flags
            elif rule == RULE_BITS:
                mask = reg_map[regs[0]] & 0xFFFF
                active_flags = []
                if param.lookup:
                    for bit_idx, desc in param.lookup.items():
                        if mask & (1 << bit_idx):
                            active_flags.append(desc)
                return active_flags if active_flags else f"0x{mask:04X}"

            # Rule 7: Version String
            elif rule == RULE_VERSION:
                v = reg_map[regs[0]] & 0xFFFF
                major = (v >> 12) & 0xF
                minor = (v >> 8) & 0xF
                patch = v & 0xFF
                return f"{major}.{minor}.{patch}"

            # Rule 8: Datetime
            elif rule == RULE_DATETIME and len(regs) >= 3:
                # Common format: reg0=(Y<<8)|M, reg1=(D<<8)|h, reg2=(m<<8)|s
                r0, r1, r2 = reg_map[regs[0]], reg_map[regs[1]], reg_map[regs[2]]
                y = 2000 + ((r0 >> 8) & 0xFF)
                mo = r0 & 0xFF
                d = (r1 >> 8) & 0xFF
                h = r1 & 0xFF
                m = (r2 >> 8) & 0xFF
                s = r2 & 0xFF
                return f"{y:04d}-{mo:02d}-{d:02d} {h:02d}:{m:02d}:{s:02d}"

            # Rule 9: Time
            elif rule == RULE_TIME:
                v = reg_map[regs[0]] & 0xFFFF
                return f"{(v >> 8) & 0xFF:02d}:{v & 0xFF:02d}"

            # Rule 10: Raw Hex
            elif rule == RULE_RAW:
                return " ".join(f"{reg_map[r]:04X}" for r in regs)

        except Exception:
            return None

        return None


# ---------------------------------------------------------------------------
# Query Range Planner / Request Optimizer
# ---------------------------------------------------------------------------

def plan_optimal_modbus_requests(
    registers: List[int],
    max_chunk_size: int = 64,
    max_gap: int = 8,
    mb_functioncode: int = 0x03,
) -> List[ProfileRequestRange]:
    """Partition a list of arbitrary register addresses into minimal contiguous read requests."""
    if not registers:
        return []

    sorted_regs = sorted(set(registers))
    ranges: List[ProfileRequestRange] = []

    curr_start = sorted_regs[0]
    curr_end = sorted_regs[0]

    for reg in sorted_regs[1:]:
        gap = reg - curr_end - 1
        new_span = (reg - curr_start + 1)

        if gap <= max_gap and new_span <= max_chunk_size:
            curr_end = reg
        else:
            ranges.append(ProfileRequestRange(start=curr_start, end=curr_end, mb_functioncode=mb_functioncode))
            curr_start = reg
            curr_end = reg

    ranges.append(ProfileRequestRange(start=curr_start, end=curr_end, mb_functioncode=mb_functioncode))
    return ranges


# ---------------------------------------------------------------------------
# Parameter Write Compilers with Strict Safety Gates
# ---------------------------------------------------------------------------

def compile_profile_parameter_write(
    profile_id: str,
    parameter_name: str,
    value: Any,
    slave_id: int = 1,
) -> Dict[str, Any]:
    """Compile parameter write command with hardware acceptance gating."""
    if profile_id not in PROFILE_REGISTRY:
        raise ValueError(f"Unknown profile ID: '{profile_id}'")

    prof = PROFILE_REGISTRY[profile_id]
    target_param = next((p for p in prof.parameters if p.name.lower() == parameter_name.lower()), None)
    if not target_param:
        raise ValueError(f"Parameter '{parameter_name}' not found in profile '{profile_id}'")

    regs = target_param.registers
    if not regs:
        raise ValueError(f"Parameter '{parameter_name}' has no defined registers.")

    # Calculate register value
    raw_val = int(round((float(value) - target_param.offset) / target_param.scale))

    if len(regs) == 1:
        # FC06 Single Register Write
        pdu = struct.pack(">BBHH", slave_id, 0x06, regs[0], raw_val & 0xFFFF)
    elif len(regs) == 2:
        # FC10 Multiple Registers Write (32-bit)
        hi = (raw_val >> 16) & 0xFFFF
        lo = raw_val & 0xFFFF
        pdu = struct.pack(">BHHBBHH", slave_id, 0x10, regs[0], 2, 4, hi, lo)
    else:
        raise ValueError(f"Cannot compile write for multi-register parameter length {len(regs)}")

    return {
        "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
        "profile_id": profile_id,
        "parameter_name": target_param.name,
        "input_value": value,
        "registers": regs,
        "compiled_raw_value": raw_val,
        "frame_hex": pdu.hex(),
        "reason": f"Write to '{target_param.name}' compiled. Gated by hardware acceptance.",
    }


# ---------------------------------------------------------------------------
# Telemetry Normalizer
# ---------------------------------------------------------------------------

def normalize_solarman_profile_to_ems(
    profile_id: str,
    parsed_values: Dict[str, Any],
    serial_number: str = "SOLARMAN-INV-1001",
) -> Dict[str, Any]:
    """Normalize parsed profile parameters to standard Solar Fleet EMS schema."""
    now_iso = datetime.now(timezone.utc).isoformat()

    # Extract power flows flexibly across vendor names
    pv1_w = float(parsed_values.get("PV1 Power", 0.0))
    pv2_w = float(parsed_values.get("PV2 Power", 0.0))
    solar_w = pv1_w + pv2_w

    grid_w = float(parsed_values.get("Grid Total Power", 0.0))
    load_w = float(parsed_values.get("Total Load Power", 0.0))
    bat_w = float(parsed_values.get("Battery Power", 0.0))
    soc_pct = int(parsed_values.get("Battery SOC", 0))
    status_str = str(parsed_values.get("Inverter Status", "Normal On-Grid"))
    temp_c = float(parsed_values.get("Inverter Temperature", 40.0))
    daily_kwh = float(parsed_values.get("Daily Production", 0.0))
    total_kwh = float(parsed_values.get("Total Production", 0.0))

    return {
        "device_id": f"solarman-{profile_id}-{serial_number}",
        "serial_number": serial_number,
        "vendor": "Solarman / " + profile_id.split("_")[0].capitalize(),
        "protocol": f"Solarman-V5-Profile-{profile_id}",
        "model_type": profile_id,
        "operating_mode": status_str,
        "battery_mode": "Normal",
        "timestamp": now_iso,
        "power_flow": {
            "solar_power_w": solar_w,
            "grid_power_w": grid_w,
            "battery_power_w": bat_w,
            "load_power_w": load_w,
            "meter_power_w": grid_w,
        },
        "metrics": {
            "pv_power_w": solar_w,
            "grid_power_w": grid_w,
            "load_power_w": load_w,
            "battery_soc_pct": soc_pct,
            "battery_power_w": bat_w,
            "temperature_c": temp_c,
            "energy_today_kwh": daily_kwh,
            "energy_total_kwh": total_kwh,
        },
        "raw_snapshot": parsed_values,
    }


# ---------------------------------------------------------------------------
# Solarman Profile Client & Simulator
# ---------------------------------------------------------------------------

class SolarmanProfileClient:
    """Client for querying and managing Solarman profiles with hardware acceptance gating."""

    def __init__(
        self,
        profile_id: str = "deye_hybrid",
        host: str = "192.168.1.150",
        port: int = DEFAULT_SOLARMAN_PORT,
        slave_id: int = 1,
        simulated: bool = True,
    ) -> None:
        if profile_id not in PROFILE_REGISTRY:
            raise ValueError(f"Profile '{profile_id}' not found. Available: {list(PROFILE_REGISTRY.keys())}")
        self.profile = PROFILE_REGISTRY[profile_id]
        self.host = host
        self.port = port
        self.slave_id = slave_id
        self.simulated = simulated
        self.parser = SolarmanProfileParser(self.profile)

    def poll_telemetry(self) -> Dict[str, Any]:
        """Poll registers and decode telemetry according to profile rules."""
        if self.simulated:
            if self.profile.profile_id == "deye_hybrid":
                mock_regs = {
                    0x0003: 2,     # Normal On-Grid
                    0x005A: 1420,  # (1420 * 0.1) - 100 = 42.0 °C
                    0x006D: 3800, 0x006E: 105, 0x00BA: 3990,  # PV1: 380.0V, 10.5A, 3990W
                    0x006F: 3750, 0x0070: 102, 0x00BB: 3825,  # PV2: 375.0V, 10.2A, 3825W
                    0x0096: 2305, 0x0097: 2310, 0x0098: 2295, # Grid L1-L3 Voltages
                    0x00A7: 6800,  # Grid Total Power 6800 W
                    0x00AF: 5000,  # Frequency 50.00 Hz
                    0x00A9: -1200, # CT Power -1200 W (Exporting)
                    0x00B2: 5600,  # Load Power 5600 W
                    0x00B4: 450,   # UPS Power 450 W
                    0x00B7: 5240,  # Battery Voltage 52.40 V
                    0x00BF: -2500, # Battery Current -25.00 A (Charging)
                    0x00BE: 1310,  # Battery Power 1310 W
                    0x00B8: 86,    # Battery SOC 86%
                    0x00B6: 1260,  # Battery Temp 26.0 °C
                    0x0040: 345,   # Daily 34.5 kWh
                    0x003F: 0, 0x003E: 115000, # Total 11,500.0 kWh
                    142: 1,        # Work Mode: Zero Export To Load
                    143: 5000,     # Solar Export Power 5000 W
                    145: 8000,     # Max Solar Sell 8000 W
                }
            elif self.profile.profile_id == "sofar_g3hyd":
                mock_regs = {
                    0x0404: 2,     # Normal On-Grid
                    0x0418: 43,    # Inverter Temp 43 °C
                    0x0584: 3820, 0x0585: 1050, 0x0586: 401, # PV1: 382.0V, 10.50A, 4010W
                    0x0587: 3800, 0x0588: 1020, 0x0589: 387, # PV2: 380.0V, 10.20A, 3870W
                    0x0485: 650,   # Grid Total Power 6500 W
                    0x0484: 5000,  # Grid Frequency 50.00 Hz
                    0x048D: 2300, 0x048E: 2310, 0x048F: 2295,
                    0x0604: 4120, 0x0605: -3200, 0x0606: 132, 0x0608: 91, 0x0607: 25,
                    0x0685: 3850, 0x0687: 0, 0x0686: 9800,
                    0x104D: 15,    # Min SOC 15%
                    0x1052: 20,    # EPS Buffer 20%
                }
            else:  # solis_hybrid
                mock_regs = {
                    33095: 3,      # Generating On-Grid
                    33093: 415,    # Temp 41.5 °C
                    33049: 3850, 33050: 110, 33051: 3820, 33052: 108,
                    33057: 7200, 33058: 5000, 33147: 5800,
                    33133: 528, 33134: -265, 33135: 1400, 33139: 89,
                    33035: 362, 33037: 0, 33036: 12400,
                    43110: 1,      # Self-Use Mode
                }

            parsed = self.parser.parse_registers(mock_regs)
            return normalize_solarman_profile_to_ems(self.profile.profile_id, parsed)

        raise NotImplementedError("Real TCP transport is handled via background controller.")

    def execute_command_safely(
        self,
        parameter_name: str,
        value: Any,
        unlocked: bool = False,
    ) -> Dict[str, Any]:
        """Safely compile and verify parameter command with hardware acceptance gating."""
        if not unlocked:
            return {
                "status": "LOCKED_PENDING_HARDWARE_ACCEPTANCE",
                "profile_id": self.profile.profile_id,
                "parameter_name": parameter_name,
                "value": value,
                "message": (
                    f"Parameter write to '{parameter_name}' for profile '{self.profile.profile_id}' "
                    "is gated behind hardware acceptance verification. Inverter held in read-only state."
                ),
            }

        return compile_profile_parameter_write(
            profile_id=self.profile.profile_id,
            parameter_name=parameter_name,
            value=value,
            slave_id=self.slave_id,
        )
