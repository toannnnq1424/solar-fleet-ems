"""Modbus TCP/RTU protocol adapter for multi-vendor inverter communication.

Independently implemented for Solar Fleet EMS.
Register map concepts informed by virtual-power-plant-main (MIT) protocols/modbus.py
and Growatt_ModbusTCP-main (MIT) growatt_register_map.py.
Source provenance:
  - virtual-power-plant-main commit HEAD, src/vpp/protocols/modbus.py (MIT)
  - Growatt_ModbusTCP-main commit HEAD, custom_components/growatt_modbus/growatt_register_map.py (MIT)

Supports predefined register maps for common inverters and a generic mode
for custom register definitions. All operations are READ-ONLY in simulation;
actual Modbus communication requires verified hardware connections.
"""

from __future__ import annotations

import logging
import struct
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Register definitions
# ---------------------------------------------------------------------------

class RegisterType(str, Enum):
    """Modbus register types."""

    HOLDING = "holding"      # FC03
    INPUT = "input"          # FC04
    COIL = "coil"            # FC01
    DISCRETE = "discrete"    # FC02


class DataType(str, Enum):
    """Register data types."""

    UINT16 = "uint16"
    INT16 = "int16"
    UINT32 = "uint32"
    INT32 = "int32"
    FLOAT32 = "float32"
    UINT64 = "uint64"
    STRING = "string"


@dataclass
class RegisterDefinition:
    """A single Modbus register definition."""

    address: int
    count: int = 1
    register_type: RegisterType = RegisterType.HOLDING
    data_type: DataType = DataType.UINT16
    name: str = ""
    unit: str = ""
    scale: float = 1.0
    description: str = ""
    access: str = "RO"
    category: str = "general"
    # For paired registers (32-bit values split across 2x16-bit)
    paired_with: Optional[int] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "address": self.address,
            "count": self.count,
            "register_type": self.register_type.value,
            "data_type": self.data_type.value,
            "name": self.name,
            "unit": self.unit,
            "scale": self.scale,
            "description": self.description,
            "access": self.access,
            "category": self.category,
        }


@dataclass
class RegisterMap:
    """Collection of registers for a device profile."""

    name: str
    manufacturer: str
    model_series: str
    registers: Dict[int, RegisterDefinition] = field(default_factory=dict)
    unit_id: int = 1
    protocol_version: str = ""
    notes: str = ""

    @property
    def register_count(self) -> int:
        return len(self.registers)

    def get_registers_by_category(self, category: str) -> Dict[int, RegisterDefinition]:
        return {addr: reg for addr, reg in self.registers.items() if reg.category == category}

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "manufacturer": self.manufacturer,
            "model_series": self.model_series,
            "register_count": self.register_count,
            "protocol_version": self.protocol_version,
            "categories": list(set(r.category for r in self.registers.values())),
        }


# ---------------------------------------------------------------------------
# Pre-built register maps
# ---------------------------------------------------------------------------

# SMA Sunny Boy / Tripower — SunSpec compatible
SMA_SUNNYBOY_MAP = RegisterMap(
    name="SMA Sunny Boy / Tripower",
    manufacturer="SMA",
    model_series="SB/STP",
    registers={
        30775: RegisterDefinition(30775, 2, RegisterType.INPUT, DataType.INT32, "ac_power", "W", 1.0, "AC Power", category="power"),
        30773: RegisterDefinition(30773, 2, RegisterType.INPUT, DataType.INT32, "dc_power", "W", 1.0, "DC Power", category="power"),
        30517: RegisterDefinition(30517, 4, RegisterType.INPUT, DataType.UINT64, "daily_yield", "Wh", 1.0, "Daily Yield", category="energy"),
        30513: RegisterDefinition(30513, 4, RegisterType.INPUT, DataType.UINT64, "total_yield", "Wh", 1.0, "Total Yield", category="energy"),
        30803: RegisterDefinition(30803, 2, RegisterType.INPUT, DataType.UINT32, "grid_frequency", "Hz", 0.01, "Grid Frequency", category="grid"),
        30783: RegisterDefinition(30783, 2, RegisterType.INPUT, DataType.INT32, "grid_voltage_l1", "V", 0.01, "Grid Voltage L1", category="grid"),
        30785: RegisterDefinition(30785, 2, RegisterType.INPUT, DataType.INT32, "grid_voltage_l2", "V", 0.01, "Grid Voltage L2", category="grid"),
        30787: RegisterDefinition(30787, 2, RegisterType.INPUT, DataType.INT32, "grid_voltage_l3", "V", 0.01, "Grid Voltage L3", category="grid"),
        30953: RegisterDefinition(30953, 2, RegisterType.INPUT, DataType.INT32, "temperature", "°C", 0.1, "Inverter Temperature", category="thermal"),
    },
)

# Fronius Symo / Primo — SunSpec compatible
FRONIUS_SYMO_MAP = RegisterMap(
    name="Fronius Symo / Primo",
    manufacturer="Fronius",
    model_series="Symo/Primo",
    registers={
        40092: RegisterDefinition(40092, 1, RegisterType.HOLDING, DataType.FLOAT32, "ac_power", "W", 1.0, "AC Power", category="power"),
        40094: RegisterDefinition(40094, 2, RegisterType.HOLDING, DataType.FLOAT32, "ac_energy", "Wh", 1.0, "AC Energy Total", category="energy"),
        40101: RegisterDefinition(40101, 1, RegisterType.HOLDING, DataType.FLOAT32, "dc_power", "W", 1.0, "DC Power", category="power"),
        40086: RegisterDefinition(40086, 1, RegisterType.HOLDING, DataType.FLOAT32, "frequency", "Hz", 1.0, "Grid Frequency", category="grid"),
        40070: RegisterDefinition(40070, 1, RegisterType.HOLDING, DataType.FLOAT32, "ac_voltage_l1", "V", 1.0, "AC Voltage L1", category="grid"),
        40072: RegisterDefinition(40072, 1, RegisterType.HOLDING, DataType.FLOAT32, "ac_voltage_l2", "V", 1.0, "AC Voltage L2", category="grid"),
        40074: RegisterDefinition(40074, 1, RegisterType.HOLDING, DataType.FLOAT32, "ac_voltage_l3", "V", 1.0, "AC Voltage L3", category="grid"),
    },
)

# SolarEdge SE — SunSpec compatible
SOLAREDGE_SE_MAP = RegisterMap(
    name="SolarEdge SE",
    manufacturer="SolarEdge",
    model_series="SE",
    registers={
        40084: RegisterDefinition(40084, 1, RegisterType.HOLDING, DataType.INT16, "ac_power", "W", 1.0, "AC Power", category="power"),
        40085: RegisterDefinition(40085, 1, RegisterType.HOLDING, DataType.INT16, "ac_power_scale", "", 1.0, "AC Power Scale Factor", category="power"),
        40101: RegisterDefinition(40101, 1, RegisterType.HOLDING, DataType.INT16, "dc_power", "W", 1.0, "DC Power", category="power"),
        40104: RegisterDefinition(40104, 1, RegisterType.HOLDING, DataType.INT16, "temperature", "°C", 0.01, "Module Temperature", category="thermal"),
        40094: RegisterDefinition(40094, 2, RegisterType.HOLDING, DataType.UINT32, "ac_energy", "Wh", 1.0, "AC Energy Total", category="energy"),
        40071: RegisterDefinition(40071, 1, RegisterType.HOLDING, DataType.UINT16, "ac_voltage_l1", "V", 0.01, "AC Voltage L1", category="grid"),
        40080: RegisterDefinition(40080, 1, RegisterType.HOLDING, DataType.UINT16, "ac_frequency", "Hz", 0.01, "AC Frequency", category="grid"),
    },
)

# Growatt MIN/SPH/SPF (based on Growatt_ModbusTCP-main MIT register map)
GROWATT_MIN_MAP = RegisterMap(
    name="Growatt MIN-TL-X / SPH / SPF",
    manufacturer="Growatt",
    model_series="MIN/SPH/SPF",
    protocol_version="V1.39",
    registers={
        # Status and Power (Input FC04)
        0: RegisterDefinition(0, 1, RegisterType.INPUT, DataType.UINT16, "inverter_status", "", 1.0, "0=Waiting, 1=Normal, 3=Fault", category="status"),
        1: RegisterDefinition(1, 1, RegisterType.INPUT, DataType.UINT16, "input_power_h", "W", 0.1, "Total input power HIGH", category="power"),
        2: RegisterDefinition(2, 1, RegisterType.INPUT, DataType.UINT16, "input_power_l", "W", 0.1, "Total input power LOW", category="power"),
        # PV String 1
        3: RegisterDefinition(3, 1, RegisterType.INPUT, DataType.UINT16, "pv1_voltage", "V", 0.1, "PV1 DC voltage", category="pv"),
        4: RegisterDefinition(4, 1, RegisterType.INPUT, DataType.UINT16, "pv1_current", "A", 0.1, "PV1 DC current", category="pv"),
        5: RegisterDefinition(5, 1, RegisterType.INPUT, DataType.UINT16, "pv1_power_h", "W", 0.1, "PV1 power HIGH", category="pv"),
        6: RegisterDefinition(6, 1, RegisterType.INPUT, DataType.UINT16, "pv1_power_l", "W", 0.1, "PV1 power LOW", category="pv"),
        # PV String 2
        7: RegisterDefinition(7, 1, RegisterType.INPUT, DataType.UINT16, "pv2_voltage", "V", 0.1, "PV2 DC voltage", category="pv"),
        8: RegisterDefinition(8, 1, RegisterType.INPUT, DataType.UINT16, "pv2_current", "A", 0.1, "PV2 DC current", category="pv"),
        9: RegisterDefinition(9, 1, RegisterType.INPUT, DataType.UINT16, "pv2_power_h", "W", 0.1, "PV2 power HIGH", category="pv"),
        10: RegisterDefinition(10, 1, RegisterType.INPUT, DataType.UINT16, "pv2_power_l", "W", 0.1, "PV2 power LOW", category="pv"),
        # AC Output
        35: RegisterDefinition(35, 1, RegisterType.INPUT, DataType.UINT16, "output_power_h", "W", 0.1, "Total AC output HIGH", category="power"),
        36: RegisterDefinition(36, 1, RegisterType.INPUT, DataType.UINT16, "output_power_l", "W", 0.1, "Total AC output LOW", category="power"),
        # Grid
        37: RegisterDefinition(37, 1, RegisterType.INPUT, DataType.UINT16, "grid_frequency", "Hz", 0.01, "Grid frequency", category="grid"),
        38: RegisterDefinition(38, 1, RegisterType.INPUT, DataType.UINT16, "grid_voltage", "V", 0.1, "Grid voltage", category="grid"),
        39: RegisterDefinition(39, 1, RegisterType.INPUT, DataType.UINT16, "grid_current", "A", 0.1, "Grid current", category="grid"),
        # 3-Phase
        42: RegisterDefinition(42, 1, RegisterType.INPUT, DataType.UINT16, "vac2", "V", 0.1, "Phase 2 voltage", category="grid"),
        43: RegisterDefinition(43, 1, RegisterType.INPUT, DataType.UINT16, "iac2", "A", 0.1, "Phase 2 current", category="grid"),
        46: RegisterDefinition(46, 1, RegisterType.INPUT, DataType.UINT16, "vac3", "V", 0.1, "Phase 3 voltage", category="grid"),
        47: RegisterDefinition(47, 1, RegisterType.INPUT, DataType.UINT16, "iac3", "A", 0.1, "Phase 3 current", category="grid"),
        # Energy
        53: RegisterDefinition(53, 1, RegisterType.INPUT, DataType.UINT16, "energy_today_h", "kWh", 0.1, "Today energy HIGH", category="energy"),
        54: RegisterDefinition(54, 1, RegisterType.INPUT, DataType.UINT16, "energy_today_l", "kWh", 0.1, "Today energy LOW", category="energy"),
        55: RegisterDefinition(55, 1, RegisterType.INPUT, DataType.UINT16, "energy_total_h", "kWh", 0.1, "Total energy HIGH", category="energy"),
        56: RegisterDefinition(56, 1, RegisterType.INPUT, DataType.UINT16, "energy_total_l", "kWh", 0.1, "Total energy LOW", category="energy"),
        # Temperatures
        93: RegisterDefinition(93, 1, RegisterType.INPUT, DataType.UINT16, "inverter_temp", "°C", 0.1, "Inverter temperature", category="thermal"),
        94: RegisterDefinition(94, 1, RegisterType.INPUT, DataType.UINT16, "ipm_temp", "°C", 0.1, "IPM temperature", category="thermal"),
        95: RegisterDefinition(95, 1, RegisterType.INPUT, DataType.UINT16, "boost_temp", "°C", 0.1, "Boost converter temperature", category="thermal"),
        # Power Factor
        100: RegisterDefinition(100, 1, RegisterType.INPUT, DataType.UINT16, "power_factor", "", 1.0, "0-10000=underexcited, 10001-20000=overexcited", category="grid"),
        # Diagnostics
        104: RegisterDefinition(104, 1, RegisterType.INPUT, DataType.UINT16, "derating_mode", "", 1.0, "Derating reason", category="status"),
        105: RegisterDefinition(105, 1, RegisterType.INPUT, DataType.UINT16, "fault_code", "", 1.0, "Main fault code", category="fault"),
        107: RegisterDefinition(107, 1, RegisterType.INPUT, DataType.UINT16, "fault_subcode", "", 1.0, "Fault subcode", category="fault"),
        112: RegisterDefinition(112, 1, RegisterType.INPUT, DataType.UINT16, "warning_code", "", 1.0, "Main warning code", category="fault"),
        # Storage/Hybrid (offset 3000)
        3000: RegisterDefinition(3000, 1, RegisterType.INPUT, DataType.UINT16, "system_status", "", 1.0, "System mode + status", category="status"),
        3001: RegisterDefinition(3001, 1, RegisterType.INPUT, DataType.UINT16, "pv_total_power_h", "W", 0.1, "PV total power HIGH", category="pv"),
        3002: RegisterDefinition(3002, 1, RegisterType.INPUT, DataType.UINT16, "pv_total_power_l", "W", 0.1, "PV total power LOW", category="pv"),
        # Battery
        3125: RegisterDefinition(3125, 1, RegisterType.INPUT, DataType.UINT16, "battery_voltage", "V", 0.1, "Battery voltage", category="battery"),
        3126: RegisterDefinition(3126, 1, RegisterType.INPUT, DataType.UINT16, "battery_soc", "%", 1.0, "Battery SOC", category="battery"),
        3127: RegisterDefinition(3127, 1, RegisterType.INPUT, DataType.UINT16, "battery_charge_power_h", "W", 0.1, "Battery charge power HIGH", category="battery"),
        3128: RegisterDefinition(3128, 1, RegisterType.INPUT, DataType.UINT16, "battery_charge_power_l", "W", 0.1, "Battery charge power LOW", category="battery"),
        3129: RegisterDefinition(3129, 1, RegisterType.INPUT, DataType.UINT16, "battery_discharge_power_h", "W", 0.1, "Battery discharge power HIGH", category="battery"),
        3130: RegisterDefinition(3130, 1, RegisterType.INPUT, DataType.UINT16, "battery_discharge_power_l", "W", 0.1, "Battery discharge power LOW", category="battery"),
        3131: RegisterDefinition(3131, 1, RegisterType.INPUT, DataType.UINT16, "battery_current", "A", 0.1, "Battery current", category="battery"),
        3132: RegisterDefinition(3132, 1, RegisterType.INPUT, DataType.UINT16, "battery_temperature", "°C", 0.1, "Battery temperature", category="battery"),
        # Grid import/export
        3041: RegisterDefinition(3041, 1, RegisterType.INPUT, DataType.UINT16, "grid_import_power_h", "W", 0.1, "Grid import HIGH", category="grid"),
        3042: RegisterDefinition(3042, 1, RegisterType.INPUT, DataType.UINT16, "grid_import_power_l", "W", 0.1, "Grid import LOW", category="grid"),
        3043: RegisterDefinition(3043, 1, RegisterType.INPUT, DataType.UINT16, "grid_export_power_h", "W", 0.1, "Grid export HIGH", category="grid"),
        3044: RegisterDefinition(3044, 1, RegisterType.INPUT, DataType.UINT16, "grid_export_power_l", "W", 0.1, "Grid export LOW", category="grid"),
        # Load
        3045: RegisterDefinition(3045, 1, RegisterType.INPUT, DataType.UINT16, "load_power_h", "W", 0.1, "Load power HIGH", category="load"),
        3046: RegisterDefinition(3046, 1, RegisterType.INPUT, DataType.UINT16, "load_power_l", "W", 0.1, "Load power LOW", category="load"),
        # Energy counters
        3049: RegisterDefinition(3049, 1, RegisterType.INPUT, DataType.UINT16, "battery_charge_today_h", "kWh", 0.1, "Battery charge today HIGH", category="energy"),
        3050: RegisterDefinition(3050, 1, RegisterType.INPUT, DataType.UINT16, "battery_charge_today_l", "kWh", 0.1, "Battery charge today LOW", category="energy"),
        3051: RegisterDefinition(3051, 1, RegisterType.INPUT, DataType.UINT16, "battery_charge_total_h", "kWh", 0.1, "Battery charge total HIGH", category="energy"),
        3052: RegisterDefinition(3052, 1, RegisterType.INPUT, DataType.UINT16, "battery_charge_total_l", "kWh", 0.1, "Battery charge total LOW", category="energy"),
        3053: RegisterDefinition(3053, 1, RegisterType.INPUT, DataType.UINT16, "battery_discharge_today_h", "kWh", 0.1, "Battery discharge today HIGH", category="energy"),
        3054: RegisterDefinition(3054, 1, RegisterType.INPUT, DataType.UINT16, "battery_discharge_today_l", "kWh", 0.1, "Battery discharge today LOW", category="energy"),
        3059: RegisterDefinition(3059, 1, RegisterType.INPUT, DataType.UINT16, "grid_import_today_h", "kWh", 0.1, "Grid import today HIGH", category="energy"),
        3060: RegisterDefinition(3060, 1, RegisterType.INPUT, DataType.UINT16, "grid_import_today_l", "kWh", 0.1, "Grid import today LOW", category="energy"),
        3067: RegisterDefinition(3067, 1, RegisterType.INPUT, DataType.UINT16, "grid_export_today_h", "kWh", 0.1, "Grid export today HIGH", category="energy"),
        3068: RegisterDefinition(3068, 1, RegisterType.INPUT, DataType.UINT16, "grid_export_today_l", "kWh", 0.1, "Grid export today LOW", category="energy"),
        3075: RegisterDefinition(3075, 1, RegisterType.INPUT, DataType.UINT16, "load_today_h", "kWh", 0.1, "Load today HIGH", category="energy"),
        3076: RegisterDefinition(3076, 1, RegisterType.INPUT, DataType.UINT16, "load_today_l", "kWh", 0.1, "Load today LOW", category="energy"),
    },
)

# Generic power meter map
GENERIC_METER_MAP = RegisterMap(
    name="Generic Power Meter",
    manufacturer="Generic",
    model_series="Meter",
    registers={
        0: RegisterDefinition(0, 2, RegisterType.INPUT, DataType.FLOAT32, "voltage_l1", "V", 0.1, "Voltage L1", category="grid"),
        2: RegisterDefinition(2, 2, RegisterType.INPUT, DataType.FLOAT32, "voltage_l2", "V", 0.1, "Voltage L2", category="grid"),
        4: RegisterDefinition(4, 2, RegisterType.INPUT, DataType.FLOAT32, "voltage_l3", "V", 0.1, "Voltage L3", category="grid"),
        6: RegisterDefinition(6, 2, RegisterType.INPUT, DataType.FLOAT32, "current_l1", "A", 0.01, "Current L1", category="grid"),
        8: RegisterDefinition(8, 2, RegisterType.INPUT, DataType.FLOAT32, "current_l2", "A", 0.01, "Current L2", category="grid"),
        10: RegisterDefinition(10, 2, RegisterType.INPUT, DataType.FLOAT32, "current_l3", "A", 0.01, "Current L3", category="grid"),
        12: RegisterDefinition(12, 2, RegisterType.INPUT, DataType.FLOAT32, "power_total", "W", 1.0, "Total Active Power", category="power"),
        14: RegisterDefinition(14, 2, RegisterType.INPUT, DataType.FLOAT32, "reactive_power_total", "var", 1.0, "Total Reactive Power", category="power"),
        16: RegisterDefinition(16, 2, RegisterType.INPUT, DataType.FLOAT32, "apparent_power_total", "VA", 1.0, "Total Apparent Power", category="power"),
        18: RegisterDefinition(18, 2, RegisterType.INPUT, DataType.FLOAT32, "power_factor", "", 0.001, "Power Factor", category="grid"),
        20: RegisterDefinition(20, 2, RegisterType.INPUT, DataType.FLOAT32, "frequency", "Hz", 0.01, "Grid Frequency", category="grid"),
        72: RegisterDefinition(72, 2, RegisterType.INPUT, DataType.FLOAT32, "energy_total", "kWh", 0.1, "Total Energy", category="energy"),
    },
)

# Registry of all available maps
REGISTER_MAP_REGISTRY: Dict[str, RegisterMap] = {
    "sma_sunnyboy": SMA_SUNNYBOY_MAP,
    "fronius_symo": FRONIUS_SYMO_MAP,
    "solaredge_se": SOLAREDGE_SE_MAP,
    "growatt_min": GROWATT_MIN_MAP,
    "generic_meter": GENERIC_METER_MAP,
}


# ---------------------------------------------------------------------------
# Register value decoder
# ---------------------------------------------------------------------------

class RegisterDecoder:
    """Decode raw Modbus register values into engineering units."""

    @staticmethod
    def decode_uint16(raw: int) -> int:
        """Decode unsigned 16-bit value."""
        return raw & 0xFFFF

    @staticmethod
    def decode_int16(raw: int) -> int:
        """Decode signed 16-bit value."""
        raw = raw & 0xFFFF
        if raw >= 0x8000:
            return raw - 0x10000
        return raw

    @staticmethod
    def decode_uint32(high: int, low: int) -> int:
        """Decode unsigned 32-bit value from two 16-bit registers."""
        return ((high & 0xFFFF) << 16) | (low & 0xFFFF)

    @staticmethod
    def decode_int32(high: int, low: int) -> int:
        """Decode signed 32-bit value from two 16-bit registers."""
        val = ((high & 0xFFFF) << 16) | (low & 0xFFFF)
        if val >= 0x80000000:
            return val - 0x100000000
        return val

    @staticmethod
    def decode_float32(high: int, low: int) -> float:
        """Decode IEEE 754 float from two 16-bit registers."""
        raw_bytes = struct.pack(">HH", high & 0xFFFF, low & 0xFFFF)
        return struct.unpack(">f", raw_bytes)[0]

    @classmethod
    def decode_register(
        cls,
        reg_def: RegisterDefinition,
        raw_values: List[int],
    ) -> float:
        """Decode a register value using its definition.

        Parameters
        ----------
        reg_def : RegisterDefinition
            Register definition.
        raw_values : list of int
            Raw 16-bit register values (1 or 2 values).

        Returns
        -------
        float
            Decoded and scaled value.
        """
        if not raw_values:
            return 0.0

        if reg_def.data_type == DataType.UINT16:
            raw = cls.decode_uint16(raw_values[0])
        elif reg_def.data_type == DataType.INT16:
            raw = cls.decode_int16(raw_values[0])
        elif reg_def.data_type == DataType.UINT32:
            raw = cls.decode_uint32(raw_values[0], raw_values[1] if len(raw_values) > 1 else 0)
        elif reg_def.data_type == DataType.INT32:
            raw = cls.decode_int32(raw_values[0], raw_values[1] if len(raw_values) > 1 else 0)
        elif reg_def.data_type == DataType.FLOAT32:
            raw = cls.decode_float32(raw_values[0], raw_values[1] if len(raw_values) > 1 else 0)
        else:
            raw = raw_values[0]

        return raw * reg_def.scale


# ---------------------------------------------------------------------------
# Growatt fault codes (from Growatt_ModbusTCP-main MIT)
# ---------------------------------------------------------------------------

GROWATT_FAULT_CODES: Dict[int, Dict[str, Any]] = {
    0: {"name": "No Fault", "severity": "NONE", "description": "Normal operation"},
    1: {"name": "Communication Error", "severity": "MEDIUM", "description": "Internal communication failure", "sop": "Power cycle inverter. Check internal wiring."},
    2: {"name": "Bus Voltage Error", "severity": "HIGH", "description": "DC bus voltage out of range", "sop": "Check PV string voltage and DC isolator."},
    3: {"name": "Grid Under Voltage", "severity": "HIGH", "description": "AC grid voltage below minimum", "sop": "Check grid connection and measure incoming AC voltage."},
    4: {"name": "Grid Over Voltage", "severity": "HIGH", "description": "AC grid voltage above maximum", "sop": "Check grid connection and AC distribution panel."},
    5: {"name": "Grid Under Frequency", "severity": "HIGH", "description": "Grid frequency below minimum", "sop": "Check grid stability and local generator."},
    6: {"name": "Grid Over Frequency", "severity": "HIGH", "description": "Grid frequency above maximum", "sop": "Check grid stability and local generator."},
    7: {"name": "DCI Over Current", "severity": "HIGH", "description": "DC injection current too high", "sop": "Check AC wiring and transformer connection."},
    8: {"name": "PV Over Voltage", "severity": "CRITICAL", "description": "PV voltage exceeds maximum", "sop": "Disconnect DC isolator immediately. Reconfigure strings."},
    9: {"name": "ISO Fault", "severity": "HIGH", "description": "PV insulation resistance low", "sop": "Inspect PV cabling, connectors, and module junction boxes."},
    10: {"name": "GFCI Fault", "severity": "CRITICAL", "description": "Ground fault detected", "sop": "Check grounding system and PV negative earthing."},
    11: {"name": "Relay Check Fail", "severity": "CRITICAL", "description": "Grid relay test failed", "sop": "Internal relay malfunction. Schedule service."},
    12: {"name": "PV Over Current", "severity": "HIGH", "description": "PV input current exceeds rating", "sop": "Check PV array configuration and string fuses."},
    13: {"name": "Inverter Over Temperature", "severity": "HIGH", "description": "Internal temperature too high", "sop": "Check ventilation and ambient temperature."},
    14: {"name": "Fan Fault", "severity": "MEDIUM", "description": "Cooling fan malfunction", "sop": "Replace cooling fan."},
    15: {"name": "Arc Fault", "severity": "CRITICAL", "description": "DC arc detected", "sop": "Disconnect DC immediately. Inspect all PV connections."},
    24: {"name": "Auto Test Fail", "severity": "MEDIUM", "description": "Self-test failed", "sop": "Power cycle and re-run self-test."},
    25: {"name": "No Utility", "severity": "MEDIUM", "description": "Grid not detected", "sop": "Check grid connection and main breaker."},
    26: {"name": "Battery Over Voltage", "severity": "HIGH", "description": "Battery voltage too high", "sop": "Check BMS and battery connections."},
    27: {"name": "Battery Low Voltage", "severity": "HIGH", "description": "Battery voltage too low", "sop": "Check battery state and BMS low-voltage protection."},
    29: {"name": "Battery Over Temperature", "severity": "HIGH", "description": "Battery temperature too high", "sop": "Check battery ventilation and cooling."},
    30: {"name": "Battery Communication Error", "severity": "MEDIUM", "description": "Cannot communicate with BMS", "sop": "Check BMS communication cable."},
}

GROWATT_DERATING_CODES: Dict[int, str] = {
    0: "Normal (no derating)",
    1: "PV input power limit",
    2: "High temperature",
    3: "Input over-current",
    4: "Output over-current",
    5: "Grid frequency deviation",
    6: "Grid voltage deviation",
    7: "Island mode detected",
    8: "Low AC voltage",
    9: "String voltage imbalance",
}


# ---------------------------------------------------------------------------
# Protocol message types
# ---------------------------------------------------------------------------

@dataclass
class ModbusRequest:
    """A Modbus read/write request."""

    unit_id: int
    function_code: int
    start_address: int
    quantity: int
    data: Optional[List[int]] = None

    def to_bytes(self) -> bytes:
        """Serialize to Modbus TCP frame (without MBAP header)."""
        if self.function_code in (1, 2, 3, 4):  # Read operations
            return struct.pack(
                ">BBH H",
                self.unit_id,
                self.function_code,
                self.start_address,
                self.quantity,
            )
        return b""


@dataclass
class ModbusResponse:
    """A Modbus read response."""

    unit_id: int
    function_code: int
    data: List[int]
    error: Optional[str] = None

    @property
    def is_error(self) -> bool:
        return self.error is not None


# ---------------------------------------------------------------------------
# Query helpers
# ---------------------------------------------------------------------------

def get_available_maps() -> List[Dict[str, Any]]:
    """List all available register maps."""
    return [m.to_dict() for m in REGISTER_MAP_REGISTRY.values()]


def get_map_by_manufacturer(manufacturer: str) -> Optional[RegisterMap]:
    """Find a register map by manufacturer name (case-insensitive)."""
    manufacturer_lower = manufacturer.lower()
    for reg_map in REGISTER_MAP_REGISTRY.values():
        if reg_map.manufacturer.lower() == manufacturer_lower:
            return reg_map
    return None


def decode_growatt_fault(code: int) -> Dict[str, Any]:
    """Decode a Growatt fault code."""
    if code in GROWATT_FAULT_CODES:
        return GROWATT_FAULT_CODES[code]
    return {
        "name": f"Unknown Fault ({code})",
        "severity": "UNKNOWN",
        "description": f"Unrecognized fault code {code}",
    }
