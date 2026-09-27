"""Deye & SunSynk Multi-Family Inverter MQTT Bridge and Telemetry Protocol Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
deye-inverter-mqtt-main (Apache-2.0 License, Author: Krzysztof Kliś and community).
Per repository workflow and licensing rules, this is a clean-room independent
implementation of the multi-family metric definitions, Modbus holding register
decoders, MQTT topic routing, parameter write compilers, 6-slot Time-of-Use service,
multi-inverter parallel cluster data aggregator, and AT command bridge connector.

Supported Deye / SunSynk Device Families:
1. deye_sg01hp3: High-Voltage 3-Phase Hybrid (6..50kW) (stack voltage 150..800V, BMS stack regs 210..250, UPS, Gen)
2. deye_sg04lp3: Low-Voltage 3-Phase Hybrid (5..12kW) (48V battery, regs 142..177, 500..653)
3. deye_sg02lp1: Low-Voltage Single-Phase Hybrid (3.6..8kW) (regs 3..114, 150..279, BMS 312..319)
4. deye_sg03lp1: Low-Voltage Single-Phase Hybrid
5. deye_string: Grid-tied string inverters (PV1..PV4, 3-phase grid AC, regs 60..116, 198..210)
6. deye_micro: Microinverters (SUN300..2000G3, individual channel DC inputs, AC grid output)
7. igen_dtsd422: IGEN smart power meter (bidirectional energy counters, per-phase PCC power)
8. deye_hybrid: Classic hybrid
9. deye_aggregated: Multi-inverter cluster data aggregation (summed active power & daily energy)

Safety Notice:
All remote write commands and parameter mutations are strictly gated by
LOCKED_PENDING_HARDWARE_ACCEPTANCE until physical on-site acceptance is confirmed.
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Optional, Union

# ---------------------------------------------------------------------------
# Device Family Enumeration
# ---------------------------------------------------------------------------

class DeyeDeviceFamily(str, enum.Enum):
    """Supported Deye and SunSynk device families."""
    SG01HP3 = "deye_sg01hp3"        # High-Voltage 3-Phase Hybrid (6..50kW)
    SG04LP3 = "deye_sg04lp3"        # Low-Voltage 3-Phase Hybrid (5..12kW)
    SG02LP1 = "deye_sg02lp1"        # Low-Voltage 1-Phase Hybrid (3.6..8kW)
    SG03LP1 = "deye_sg03lp1"        # Low-Voltage 1-Phase Hybrid
    STRING = "deye_string"          # Grid-tied String Inverters
    MICRO = "deye_micro"            # Microinverters (SUN300..SUN2000G3)
    IGEN_DTSD422 = "igen_dtsd422"    # IGEN DTSD-422-D3 Smart Power Meter
    HYBRID = "deye_hybrid"          # Classic Hybrid Inverters
    AGGREGATED = "deye_aggregated"  # Multi-Inverter Aggregation Cluster


# ---------------------------------------------------------------------------
# Work Mode Constants
# ---------------------------------------------------------------------------

class DeyeWorkMode(int, enum.Enum):
    """Deye Work Mode settings (Holding Register 142)."""
    SELLING_FIRST = 0        # Priority: Load -> Battery -> Grid Export
    ZERO_EXPORT_TO_LOAD = 1  # Inverter powers local load, zero export beyond inverter terminals
    ZERO_EXPORT_TO_CT = 2    # External CT / meter at PCC ensures zero feed-in to utility grid


# ---------------------------------------------------------------------------
# Safety Lock Constants
# ---------------------------------------------------------------------------

SAFETY_STATUS_LOCKED = "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
SAFETY_STATUS_UNLOCKED = "UNLOCKED_TEST_ONLY"


# ---------------------------------------------------------------------------
# Sensor Descriptor & Register Mapping
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class DeyeSensorDescriptor:
    """Descriptor for a Deye Modbus register sensor."""
    name: str
    reg_addr: int
    scale: float
    mqtt_topic_suffix: str
    unit: str = ""
    offset: float = 0.0
    signed: bool = False
    is_double_reg: bool = False
    groups: tuple[str, ...] = ()


# ---------------------------------------------------------------------------
# Multi-Family Sensor Catalogues
# ---------------------------------------------------------------------------

# High-Voltage 3-Phase Hybrid (SG01HP3)
SG01HP3_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("Daily Production", 529, 0.1, "day_energy", "kWh", groups=("sg01hp3",)),
    DeyeSensorDescriptor("Total Production", 534, 0.1, "total_energy", "kWh", is_double_reg=True, groups=("sg01hp3",)),
    DeyeSensorDescriptor("PV1 Power", 672, 1.0, "dc/pv1/power", "W", groups=("sg01hp3",)),
    DeyeSensorDescriptor("PV2 Power", 673, 1.0, "dc/pv2/power", "W", groups=("sg01hp3",)),
    DeyeSensorDescriptor("PV1 Voltage", 676, 0.1, "dc/pv1/voltage", "V", groups=("sg01hp3",)),
    DeyeSensorDescriptor("PV1 Current", 677, 0.1, "dc/pv1/current", "A", groups=("sg01hp3",)),
    DeyeSensorDescriptor("PV2 Voltage", 678, 0.1, "dc/pv2/voltage", "V", groups=("sg01hp3",)),
    DeyeSensorDescriptor("PV2 Current", 679, 0.1, "dc/pv2/current", "A", groups=("sg01hp3",)),
    DeyeSensorDescriptor("High-Voltage Battery Power", 590, 1.0, "battery/power", "W", signed=True, groups=("sg01hp3_battery",)),
    DeyeSensorDescriptor("High-Voltage Battery Voltage", 587, 0.1, "battery/voltage", "V", groups=("sg01hp3_battery",)),
    DeyeSensorDescriptor("High-Voltage Battery Current", 591, 0.01, "battery/current", "A", signed=True, groups=("sg01hp3_battery",)),
    DeyeSensorDescriptor("Battery SOC", 588, 1.0, "battery/soc", "%", groups=("sg01hp3_battery",)),
    DeyeSensorDescriptor("Battery Temperature", 586, 0.1, "battery/temperature", "°C", offset=-100.0, groups=("sg01hp3_battery",)),
    DeyeSensorDescriptor("BMS Stack Voltage", 210, 0.1, "bms/stack_voltage", "V", groups=("sg01hp3_bms",)),
    DeyeSensorDescriptor("BMS Stack Current", 211, 0.1, "bms/stack_current", "A", signed=True, groups=("sg01hp3_bms",)),
    DeyeSensorDescriptor("BMS Stack SOC", 214, 1.0, "bms/stack_soc", "%", groups=("sg01hp3_bms",)),
    DeyeSensorDescriptor("BMS Stack SOH", 215, 1.0, "bms/stack_soh", "%", groups=("sg01hp3_bms",)),
    DeyeSensorDescriptor("Grid Voltage L1", 598, 0.1, "ac/l1/voltage", "V", groups=("sg01hp3",)),
    DeyeSensorDescriptor("Grid Voltage L2", 599, 0.1, "ac/l2/voltage", "V", groups=("sg01hp3",)),
    DeyeSensorDescriptor("Grid Voltage L3", 600, 0.1, "ac/l3/voltage", "V", groups=("sg01hp3",)),
    DeyeSensorDescriptor("Grid Current L1", 604, 0.1, "ac/l1/current", "A", signed=True, groups=("sg01hp3",)),
    DeyeSensorDescriptor("Grid Current L2", 605, 0.1, "ac/l2/current", "A", signed=True, groups=("sg01hp3",)),
    DeyeSensorDescriptor("Grid Current L3", 606, 0.1, "ac/l3/current", "A", signed=True, groups=("sg01hp3",)),
    DeyeSensorDescriptor("Total Grid Power", 625, 1.0, "ac/total_power", "W", signed=True, groups=("sg01hp3",)),
    DeyeSensorDescriptor("Inverter Status", 500, 1.0, "inverter/status", groups=("sg01hp3",)),
    DeyeSensorDescriptor("Daily Energy Bought", 522, 0.1, "ac/daily_energy_bought", "kWh", groups=("sg01hp3",)),
    DeyeSensorDescriptor("Daily Energy Sold", 524, 0.1, "ac/daily_energy_sold", "kWh", groups=("sg01hp3",)),
]

# Low-Voltage 3-Phase Hybrid (SG04LP3)
SG04LP3_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("Daily Production", 529, 0.1, "day_energy", "kWh", groups=("sg04lp3",)),
    DeyeSensorDescriptor("Total Production", 534, 0.1, "total_energy", "kWh", is_double_reg=True, groups=("sg04lp3",)),
    DeyeSensorDescriptor("PV1 Power", 672, 1.0, "dc/pv1/power", "W", groups=("sg04lp3",)),
    DeyeSensorDescriptor("PV2 Power", 673, 1.0, "dc/pv2/power", "W", groups=("sg04lp3",)),
    DeyeSensorDescriptor("PV1 Voltage", 676, 0.1, "dc/pv1/voltage", "V", groups=("sg04lp3",)),
    DeyeSensorDescriptor("PV1 Current", 677, 0.1, "dc/pv1/current", "A", groups=("sg04lp3",)),
    DeyeSensorDescriptor("PV2 Voltage", 678, 0.1, "dc/pv2/voltage", "V", groups=("sg04lp3",)),
    DeyeSensorDescriptor("PV2 Current", 679, 0.1, "dc/pv2/current", "A", groups=("sg04lp3",)),
    DeyeSensorDescriptor("Battery Power", 590, 1.0, "battery/power", "W", signed=True, groups=("sg04lp3_battery",)),
    DeyeSensorDescriptor("Battery Voltage", 587, 0.01, "battery/voltage", "V", groups=("sg04lp3_battery",)),
    DeyeSensorDescriptor("Battery Current", 591, 0.01, "battery/current", "A", signed=True, groups=("sg04lp3_battery",)),
    DeyeSensorDescriptor("Battery SOC", 588, 1.0, "battery/soc", "%", groups=("sg04lp3_battery",)),
    DeyeSensorDescriptor("Battery Temperature", 586, 0.1, "battery/temperature", "°C", offset=-100.0, groups=("sg04lp3_battery",)),
    DeyeSensorDescriptor("Grid Voltage L1", 598, 0.1, "ac/l1/voltage", "V", groups=("sg04lp3",)),
    DeyeSensorDescriptor("Grid Voltage L2", 599, 0.1, "ac/l2/voltage", "V", groups=("sg04lp3",)),
    DeyeSensorDescriptor("Grid Voltage L3", 600, 0.1, "ac/l3/voltage", "V", groups=("sg04lp3",)),
    DeyeSensorDescriptor("Total Grid Power", 625, 1.0, "ac/total_power", "W", signed=True, groups=("sg04lp3",)),
    DeyeSensorDescriptor("Work Mode Setting", 142, 1.0, "settings/workmode", groups=("sg04lp3_settings",)),
    DeyeSensorDescriptor("Solar Sell Setting", 145, 1.0, "settings/solar_sell", groups=("sg04lp3_settings",)),
    DeyeSensorDescriptor("Solar Sell Max Power", 143, 1.0, "settings/solar_sell_max_power", "W", groups=("sg04lp3_settings",)),
]

# Low-Voltage Single-Phase Hybrid (SG02LP1)
SG02LP1_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("Daily Production", 70, 0.1, "day_energy", "kWh", groups=("sg02lp1",)),
    DeyeSensorDescriptor("Total Production", 72, 0.1, "total_energy", "kWh", is_double_reg=True, groups=("sg02lp1",)),
    DeyeSensorDescriptor("PV1 Power", 186, 1.0, "dc/pv1/power", "W", groups=("sg02lp1",)),
    DeyeSensorDescriptor("PV2 Power", 187, 1.0, "dc/pv2/power", "W", groups=("sg02lp1",)),
    DeyeSensorDescriptor("Battery Power", 190, 1.0, "battery/power", "W", signed=True, groups=("sg02lp1_battery",)),
    DeyeSensorDescriptor("Battery Voltage", 183, 0.01, "battery/voltage", "V", groups=("sg02lp1_battery",)),
    DeyeSensorDescriptor("Battery SOC", 184, 1.0, "battery/soc", "%", groups=("sg02lp1_battery",)),
    DeyeSensorDescriptor("AC Grid Voltage", 73, 0.1, "ac/l1/voltage", "V", groups=("sg02lp1",)),
    DeyeSensorDescriptor("AC Grid Current", 76, 0.1, "ac/l1/current", "A", groups=("sg02lp1",)),
    DeyeSensorDescriptor("AC Active Power", 86, 1.0, "ac/active_power", "W", signed=True, groups=("sg02lp1",)),
]

# Grid-Tied String Inverter (STRING)
STRING_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("Daily Production", 60, 0.1, "day_energy", "kWh", groups=("string",)),
    DeyeSensorDescriptor("Total Production", 63, 0.1, "total_energy", "kWh", is_double_reg=True, groups=("string",)),
    DeyeSensorDescriptor("Grid L1 Voltage", 0x49, 0.1, "ac/l1/voltage", "V", groups=("string",)),
    DeyeSensorDescriptor("Grid L1 Current", 0x4C, 0.1, "ac/l1/current", "A", groups=("string",)),
    DeyeSensorDescriptor("Grid L2 Voltage", 0x4A, 0.1, "ac/l2/voltage", "V", groups=("string",)),
    DeyeSensorDescriptor("Grid L2 Current", 0x4D, 0.1, "ac/l2/current", "A", groups=("string",)),
    DeyeSensorDescriptor("Grid L3 Voltage", 0x4B, 0.1, "ac/l3/voltage", "V", groups=("string",)),
    DeyeSensorDescriptor("Grid L3 Current", 0x4E, 0.1, "ac/l3/current", "A", groups=("string",)),
    DeyeSensorDescriptor("Active Power Regulation", 40, 0.1, "settings/active_power_regulation", "%", groups=("settings",)),
    DeyeSensorDescriptor("IGBT Temperature", 0x5B, 0.1, "igbt_temp", "°C", offset=-100.0, groups=("string",)),
]

# Microinverters (MICRO)
MICRO_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("Daily Production", 60, 0.1, "day_energy", "kWh", groups=("micro",)),
    DeyeSensorDescriptor("Total Production", 63, 0.1, "total_energy", "kWh", is_double_reg=True, groups=("micro",)),
    DeyeSensorDescriptor("Grid Voltage", 0x49, 0.1, "ac/l1/voltage", "V", groups=("micro",)),
    DeyeSensorDescriptor("Grid Current", 0x4C, 0.1, "ac/l1/current", "A", groups=("micro",)),
    DeyeSensorDescriptor("Active Power Regulation", 40, 1.0, "settings/active_power_regulation", "%", groups=("settings_micro",)),
]

# IGEN DTSD422 3-Phase CT Smart Power Meter
IGEN_DTSD422_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("CT1 Voltage", 0x01, 0.1, "ct1/voltage", "V", groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT1 Current", 0x07, 0.001, "ct1/current", "A", signed=True, is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT1 Active Power", 0x0D, 1.0, "ct1/active_power", "W", signed=True, is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT2 Voltage", 0x03, 0.1, "ct2/voltage", "V", groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT2 Current", 0x09, 0.001, "ct2/current", "A", signed=True, is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT2 Active Power", 0x0F, 1.0, "ct2/active_power", "W", signed=True, is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT3 Voltage", 0x05, 0.1, "ct3/voltage", "V", groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT3 Current", 0x0B, 0.001, "ct3/current", "A", signed=True, is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("CT3 Active Power", 0x11, 1.0, "ct3/active_power", "W", signed=True, is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("Total Positive Energy", 0x15, 0.01, "total_positive_energy", "kWh", is_double_reg=True, groups=("igen_dtsd422",)),
    DeyeSensorDescriptor("Total Negative Energy", 0x19, 0.01, "total_negative_energy", "kWh", is_double_reg=True, groups=("igen_dtsd422",)),
]

# Aggregated Sensor Catalog
AGGREGATED_SENSORS: list[DeyeSensorDescriptor] = [
    DeyeSensorDescriptor("Aggregated AC Active Power", 0, 1.0, "ac/active_power", "W", groups=("aggregated",)),
    DeyeSensorDescriptor("Aggregated Daily Energy", 0, 1.0, "day_energy", "kWh", groups=("aggregated",)),
    DeyeSensorDescriptor("Aggregated Total Energy", 0, 1.0, "total_energy", "kWh", groups=("aggregated",)),
    DeyeSensorDescriptor("Aggregated Battery Power", 0, 1.0, "battery/power", "W", groups=("aggregated",)),
]

DEYE_FAMILY_CATALOG: dict[DeyeDeviceFamily, list[DeyeSensorDescriptor]] = {
    DeyeDeviceFamily.SG01HP3: SG01HP3_SENSORS,
    DeyeDeviceFamily.SG04LP3: SG04LP3_SENSORS,
    DeyeDeviceFamily.SG02LP1: SG02LP1_SENSORS,
    DeyeDeviceFamily.SG03LP1: SG02LP1_SENSORS,
    DeyeDeviceFamily.STRING: STRING_SENSORS,
    DeyeDeviceFamily.MICRO: MICRO_SENSORS,
    DeyeDeviceFamily.IGEN_DTSD422: IGEN_DTSD422_SENSORS,
    DeyeDeviceFamily.HYBRID: SG04LP3_SENSORS,
    DeyeDeviceFamily.AGGREGATED: AGGREGATED_SENSORS,
}


# ---------------------------------------------------------------------------
# MQTT Topic Router
# ---------------------------------------------------------------------------

class DeyeMqttTopicRouter:
    """Constructs and parses Deye MQTT publication and command topics."""

    def __init__(self, topic_prefix: str = "deye"):
        self.topic_prefix = topic_prefix.rstrip("/")

    def build_publish_topic(self, logger_sn_or_idx: Union[int, str], topic_suffix: str) -> str:
        """Build telemetry publication topic: {prefix}/{sn}/{suffix}."""
        pfx = str(logger_sn_or_idx) if str(logger_sn_or_idx) != "0" else ""
        if pfx:
            return f"{self.topic_prefix}/{pfx}/{topic_suffix.lstrip('/')}"
        return f"{self.topic_prefix}/{topic_suffix.lstrip('/')}"

    def build_command_topic(self, logger_sn_or_idx: Union[int, str], topic_suffix: str) -> str:
        """Build command subscription topic: {prefix}/{sn}/{suffix}/command."""
        base = self.build_publish_topic(logger_sn_or_idx, topic_suffix)
        return f"{base}/command"

    def extract_command_suffix(self, logger_sn_or_idx: Union[int, str], full_topic: str) -> Optional[str]:
        """Extract setting topic suffix from incoming command topic."""
        pfx = str(logger_sn_or_idx) if str(logger_sn_or_idx) != "0" else ""
        expected_start = f"{self.topic_prefix}/{pfx}/" if pfx else f"{self.topic_prefix}/"
        if full_topic.startswith(expected_start) and full_topic.endswith("/command"):
            trimmed = full_topic[len(expected_start):-len("/command")]
            return trimmed
        return None


# ---------------------------------------------------------------------------
# Parameter Write Compilers
# ---------------------------------------------------------------------------

@dataclass
class DeyeWriteResult:
    """Result of a compiled Deye configuration write command."""
    success: bool
    command_name: str
    target_register: int
    raw_value: int
    human_readable: str
    status: str = SAFETY_STATUS_LOCKED
    dry_run: bool = False
    modbus_request_hex: str = ""
    error_message: Optional[str] = None


class DeyeCommandCompiler:
    """Validates and compiles Deye control commands into Modbus holding register write operations."""

    @staticmethod
    def compile_workmode(mode: Union[int, DeyeWorkMode], confirm_hardware_acceptance: bool = False) -> DeyeWriteResult:
        """Compile Work Mode setting (Reg 142). Values: 0=Selling First, 1=Zero Export Load, 2=Zero Export CT."""
        mode_val = int(mode)
        if mode_val not in (0, 1, 2):
            return DeyeWriteResult(
                success=False,
                command_name="workmode",
                target_register=142,
                raw_value=mode_val,
                human_readable=f"Invalid work mode: {mode_val}",
                error_message=f"Work mode must be 0 (Selling First), 1 (Zero Export Load), or 2 (Zero Export CT), got {mode_val}",
            )

        mode_names = {
            0: "Selling First",
            1: "Zero Export to Load",
            2: "Zero Export to CT",
        }
        human = f"WorkMode -> {mode_names[mode_val]} (Reg 142 = {mode_val})"

        if not confirm_hardware_acceptance:
            return DeyeWriteResult(
                success=True,
                command_name="workmode",
                target_register=142,
                raw_value=mode_val,
                human_readable=human,
                status=SAFETY_STATUS_LOCKED,
                dry_run=True,
                modbus_request_hex=f"0106008E{mode_val:04X}",
            )

        return DeyeWriteResult(
            success=True,
            command_name="workmode",
            target_register=142,
            raw_value=mode_val,
            human_readable=human,
            status=SAFETY_STATUS_UNLOCKED,
            dry_run=False,
            modbus_request_hex=f"0106008E{mode_val:04X}",
        )

    @staticmethod
    def compile_solar_sell(enable: bool, confirm_hardware_acceptance: bool = False) -> DeyeWriteResult:
        """Compile Solar Sell enable/disable (Reg 145)."""
        val = 1 if enable else 0
        human = f"Solar Sell -> {'Enabled' if enable else 'Disabled'} (Reg 145 = {val})"

        if not confirm_hardware_acceptance:
            return DeyeWriteResult(
                success=True,
                command_name="solar_sell",
                target_register=145,
                raw_value=val,
                human_readable=human,
                status=SAFETY_STATUS_LOCKED,
                dry_run=True,
                modbus_request_hex=f"01060091{val:04X}",
            )

        return DeyeWriteResult(
            success=True,
            command_name="solar_sell",
            target_register=145,
            raw_value=val,
            human_readable=human,
            status=SAFETY_STATUS_UNLOCKED,
            dry_run=False,
            modbus_request_hex=f"01060091{val:04X}",
        )

    @staticmethod
    def compile_solar_sell_max_power(watts: int, confirm_hardware_acceptance: bool = False) -> DeyeWriteResult:
        """Compile Solar Sell Max Power limit (Reg 143, 0..12000 W)."""
        if watts < 0 or watts > 12000:
            return DeyeWriteResult(
                success=False,
                command_name="solar_sell_max_power",
                target_register=143,
                raw_value=watts,
                human_readable=f"Invalid max power: {watts}W",
                error_message=f"Solar sell max power must be between 0 and 12000 W, got {watts}",
            )

        human = f"Solar Sell Max Power -> {watts} W (Reg 143 = {watts})"
        if not confirm_hardware_acceptance:
            return DeyeWriteResult(
                success=True,
                command_name="solar_sell_max_power",
                target_register=143,
                raw_value=watts,
                human_readable=human,
                status=SAFETY_STATUS_LOCKED,
                dry_run=True,
                modbus_request_hex=f"0106008F{watts:04X}",
            )

        return DeyeWriteResult(
            success=True,
            command_name="solar_sell_max_power",
            target_register=143,
            raw_value=watts,
            human_readable=human,
            status=SAFETY_STATUS_UNLOCKED,
            dry_run=False,
            modbus_request_hex=f"0106008F{watts:04X}",
        )

    @staticmethod
    def compile_active_power_regulation(percentage: float, confirm_hardware_acceptance: bool = False) -> DeyeWriteResult:
        """Compile Active Power Regulation percentage (Reg 40, 0..120%, scale 0.1 -> 0..1200)."""
        if percentage < 0.0 or percentage > 120.0:
            return DeyeWriteResult(
                success=False,
                command_name="active_power_regulation",
                target_register=40,
                raw_value=int(percentage * 10),
                human_readable=f"Invalid power regulation: {percentage}%",
                error_message=f"Active power regulation must be between 0.0% and 120.0%, got {percentage}",
            )

        raw_val = int(round(percentage * 10.0))
        human = f"Active Power Regulation -> {percentage:.1f}% (Reg 40 = {raw_val})"
        if not confirm_hardware_acceptance:
            return DeyeWriteResult(
                success=True,
                command_name="active_power_regulation",
                target_register=40,
                raw_value=raw_val,
                human_readable=human,
                status=SAFETY_STATUS_LOCKED,
                dry_run=True,
                modbus_request_hex=f"01060028{raw_val:04X}",
            )

        return DeyeWriteResult(
            success=True,
            command_name="active_power_regulation",
            target_register=40,
            raw_value=raw_val,
            human_readable=human,
            status=SAFETY_STATUS_UNLOCKED,
            dry_run=False,
            modbus_request_hex=f"01060028{raw_val:04X}",
        )

    @staticmethod
    def compile_battery_setting(setting_name: str, value: int, confirm_hardware_acceptance: bool = False) -> DeyeWriteResult:
        """Compile Battery Settings: grid_charge (130), maximum_charge_current (108),

        maximum_discharge_current (109), maximum_grid_charge_current (128).
        """
        reg_map = {
            "grid_charge": 130,
            "maximum_charge_current": 108,
            "maximum_discharge_current": 109,
            "maximum_grid_charge_current": 128,
        }
        if setting_name not in reg_map:
            return DeyeWriteResult(
                success=False,
                command_name=f"battery_settings/{setting_name}",
                target_register=0,
                raw_value=value,
                human_readable=f"Unknown setting: {setting_name}",
                error_message=f"Unknown battery setting '{setting_name}'. Must be one of {list(reg_map.keys())}",
            )

        reg_addr = reg_map[setting_name]
        if setting_name == "grid_charge":
            if value not in (0, 1):
                return DeyeWriteResult(
                    success=False,
                    command_name=f"battery_settings/{setting_name}",
                    target_register=reg_addr,
                    raw_value=value,
                    human_readable=f"Invalid grid_charge value: {value}",
                    error_message=f"grid_charge value must be 0 or 1, got {value}",
                )
        else:
            if value < 0 or value > 240:
                return DeyeWriteResult(
                    success=False,
                    command_name=f"battery_settings/{setting_name}",
                    target_register=reg_addr,
                    raw_value=value,
                    human_readable=f"Invalid current value: {value}A",
                    error_message=f"Battery current setting '{setting_name}' must be 0..240 A, got {value}",
                )

        human = f"Battery Setting {setting_name} -> {value} (Reg {reg_addr} = {value})"
        if not confirm_hardware_acceptance:
            return DeyeWriteResult(
                success=True,
                command_name=f"battery_settings/{setting_name}",
                target_register=reg_addr,
                raw_value=value,
                human_readable=human,
                status=SAFETY_STATUS_LOCKED,
                dry_run=True,
                modbus_request_hex=f"0106{reg_addr:04X}{value:04X}",
            )

        return DeyeWriteResult(
            success=True,
            command_name=f"battery_settings/{setting_name}",
            target_register=reg_addr,
            raw_value=value,
            human_readable=human,
            status=SAFETY_STATUS_UNLOCKED,
            dry_run=False,
            modbus_request_hex=f"0106{reg_addr:04X}{value:04X}",
        )


# ---------------------------------------------------------------------------
# 6-Slot Time-Of-Use (TOU) Service
# ---------------------------------------------------------------------------

@dataclass
class DeyeTouSlot:
    """Represents one of 6 Deye Time-of-Use schedule slots."""
    slot_index: int       # 1..6
    time_hhmm: str        # "05:00" or "0500"
    power_watts: int      # 0..12000 W
    target_soc: int       # 0..100 %
    voltage: float        # 40.0..60.0 V
    charge_enabled: bool  # True/False

    def encode_time_register(self) -> int:
        clean = self.time_hhmm.replace(":", "").strip()
        val = int(clean)
        hour = val // 100
        minute = val % 100
        return (hour << 8) | minute if hour > 24 else (hour * 100 + minute)


class DeyeTimeOfUseService:
    """Manages 6-slot Time-of-Use schedule state, staged modifications, and Modbus write batching."""

    def __init__(self):
        self.modifications: dict[int, int] = {}  # reg_addr -> raw_value
        self.read_state: dict[int, int] = {}      # reg_addr -> raw_value

    def stage_slot(self, slot: DeyeTouSlot) -> dict[int, int]:
        """Stage registers for slot (1..6)."""
        idx = slot.slot_index - 1
        if idx < 0 or idx > 5:
            raise ValueError("Slot index must be 1..6")

        time_reg = 148 + idx
        power_reg = 154 + idx
        volt_reg = 160 + idx
        soc_reg = 166 + idx
        en_reg = 172 + idx

        staged = {
            time_reg: slot.encode_time_register(),
            power_reg: slot.power_watts,
            volt_reg: int(round(slot.voltage * 100.0)),
            soc_reg: slot.target_soc,
            en_reg: 1 if slot.charge_enabled else 0,
        }
        self.modifications.update(staged)
        return staged

    def clear_staged(self) -> None:
        """Clear uncommitted modifications."""
        self.modifications.clear()

    def compile_write_batches(
        self,
        confirm_hardware_acceptance: bool = False,
        dry_run: bool = False,
    ) -> list[DeyeWriteResult]:
        """Compile staged modifications into contiguous register write blocks."""
        combined = {**self.read_state, **self.modifications}
        if not combined:
            return []

        results = []
        status = SAFETY_STATUS_UNLOCKED if (confirm_hardware_acceptance and not dry_run) else SAFETY_STATUS_LOCKED
        is_dry = dry_run or not confirm_hardware_acceptance

        sorted_regs = sorted(self.modifications.items())
        for reg, val in sorted_regs:
            results.append(
                DeyeWriteResult(
                    success=True,
                    command_name=f"timeofuse_reg_{reg}",
                    target_register=reg,
                    raw_value=val,
                    human_readable=f"TOU Register {reg} -> {val}",
                    status=status,
                    dry_run=is_dry,
                    modbus_request_hex=f"0106{reg:04X}{val:04X}",
                )
            )

        if not is_dry:
            self.read_state.update(self.modifications)
            self.modifications.clear()

        return results


# ---------------------------------------------------------------------------
# Multi-Inverter Parallel Cluster Data Aggregator
# ---------------------------------------------------------------------------

class DeyeMultiInverterAggregator:
    """Aggregates metrics from multiple inverters operating in a parallel cluster."""

    def __init__(self):
        self._ac_power_by_logger: dict[str, float] = {}
        self._day_energy_by_logger: dict[str, float] = {}
        self._total_energy_by_logger: dict[str, float] = {}
        self._battery_power_by_logger: dict[str, float] = {}
        self._last_aggregation_date: int = datetime.now().day

    def record_inverter_metrics(
        self,
        logger_id: str,
        ac_active_power_w: float,
        daily_energy_kwh: float,
        total_energy_kwh: float,
        battery_power_w: float = 0.0,
    ) -> None:
        """Ingest observation metrics for a single inverter."""
        now = datetime.now()
        if now.day != self._last_aggregation_date:
            self._day_energy_by_logger.clear()
            self._last_aggregation_date = now.day

        self._ac_power_by_logger[logger_id] = ac_active_power_w
        self._day_energy_by_logger[logger_id] = daily_energy_kwh
        self._total_energy_by_logger[logger_id] = total_energy_kwh
        self._battery_power_by_logger[logger_id] = battery_power_w

    def get_aggregated_cluster_metrics(self) -> dict[str, Any]:
        """Compute summed cluster telemetry."""
        total_ac = sum(self._ac_power_by_logger.values())
        total_day = sum(self._day_energy_by_logger.values())
        total_yield = sum(self._total_energy_by_logger.values())
        total_bat = sum(self._battery_power_by_logger.values())

        return {
            "cluster_size": len(self._ac_power_by_logger),
            "aggregated_ac_active_power_w": round(total_ac, 1),
            "aggregated_daily_energy_kwh": round(total_day, 2),
            "aggregated_total_energy_kwh": round(total_yield, 1),
            "aggregated_battery_power_w": round(total_bat, 1),
            "member_loggers": list(self._ac_power_by_logger.keys()),
        }


# ---------------------------------------------------------------------------
# AT Command Bridge Simulator
# ---------------------------------------------------------------------------

class DeyeAtCommandBridge:
    """Parses and executes Deye / Solarman Wi-Fi dongle AT commands."""

    def __init__(self, mac_address: str = "A0:B1:C2:D3:E4:F5", fw_version: str = "MW3_16U_5406_1.57"):
        self.mac_address = mac_address
        self.fw_version = fw_version

    def execute_command(self, cmd_str: str) -> str:
        """Execute an AT command string and return standard dongle response."""
        clean = cmd_str.strip().upper()
        if clean in ("AT+WNTYPE", "AT+WNTYPE?"):
            return "+ok=ESP32_WIFI"
        elif clean in ("AT+WSKEY", "AT+WSKEY?"):
            return "+ok=WPA2PSK,AES,solar_fleet_mesh"
        elif clean in ("AT+MID", "AT+MID?"):
            return f"+ok={self.mac_address}"
        elif clean in ("AT+VER", "AT+VER?"):
            return f"+ok={self.fw_version}"
        elif clean == "AT+Z":
            return "+ok=REBOOTING"
        elif clean in ("AT+H", "AT+HELP"):
            return "+ok=WNTYPE,WSKEY,MID,VER,Z,H"
        else:
            return "+err=-1"


# ---------------------------------------------------------------------------
# Telemetry Simulator & Decoder Engine
# ---------------------------------------------------------------------------

class DeyeTelemetrySimulator:
    """Generates realistic telemetry register maps and simulated MQTT topic streams."""

    @staticmethod
    def generate_simulated_registers(family: DeyeDeviceFamily) -> dict[int, int]:
        """Return typical operational register dictionary for the specified family."""
        if family == DeyeDeviceFamily.SG01HP3:
            return {
                500: 2,           # Inverter Status: Normal / On-grid
                529: 385,         # Daily Production: 38.5 kWh
                534: 12540,       # Total Production: 1254.0 kWh
                672: 4200,        # PV1 Power: 4200 W
                673: 3800,        # PV2 Power: 3800 W
                676: 6200,        # PV1 Voltage: 620.0 V
                677: 68,          # PV1 Current: 6.8 A
                678: 6150,        # PV2 Voltage: 615.0 V
                679: 62,          # PV2 Current: 6.2 A
                587: 4200,        # Battery Voltage: 420.0 V (HV Stack)
                590: 2500,        # Battery Power: 2500 W (Charging)
                591: 600,         # Battery Current: 6.00 A
                588: 82,          # Battery SOC: 82%
                586: 1280,        # Battery Temp: (1280*0.1) - 100 = 28.0°C
                210: 4200,        # BMS Stack Voltage: 420.0 V
                211: 60,          # BMS Stack Current: 6.0 A
                214: 82,          # BMS Stack SOC: 82%
                215: 98,          # BMS Stack SOH: 98%
                598: 2310,        # Grid Voltage L1: 231.0 V
                599: 2295,        # Grid Voltage L2: 229.5 V
                600: 2305,        # Grid Voltage L3: 230.5 V
                604: 120,         # Grid Current L1: 12.0 A
                605: 118,         # Grid Current L2: 11.8 A
                606: 121,         # Grid Current L3: 12.1 A
                625: 5500,        # Total Grid Power: 5500 W (Exporting)
                522: 45,          # Daily Bought: 4.5 kWh
                524: 280,         # Daily Sold: 28.0 kWh
            }
        elif family == DeyeDeviceFamily.SG04LP3:
            return {
                529: 245,         # Daily Production: 24.5 kWh
                534: 8450,        # Total Production: 845.0 kWh
                672: 2800,        # PV1 Power: 2800 W
                673: 2700,        # PV2 Power: 2700 W
                676: 3800,        # PV1 Voltage: 380.0 V
                677: 74,          # PV1 Current: 7.4 A
                678: 3750,        # PV2 Voltage: 375.0 V
                679: 72,          # PV2 Current: 7.2 A
                587: 5120,        # Battery Voltage: 51.20 V (48V LV)
                590: 1800,        # Battery Power: 1800 W
                591: 3515,        # Battery Current: 35.15 A
                588: 76,          # Battery SOC: 76%
                586: 1260,        # Battery Temp: 26.0°C
                598: 2300,        # Grid L1: 230.0 V
                599: 2305,        # Grid L2: 230.5 V
                600: 2298,        # Grid L3: 229.8 V
                625: 3700,        # Total Grid Power: 3700 W
                142: 1,           # Work Mode: Zero Export to Load
                145: 1,           # Solar Sell: Enabled
                143: 5000,        # Solar Sell Max Power: 5000 W
            }
        elif family in (DeyeDeviceFamily.SG02LP1, DeyeDeviceFamily.SG03LP1):
            return {
                70: 165,          # Daily Production: 16.5 kWh
                72: 4200,         # Total Production: 420.0 kWh
                186: 2200,        # PV1 Power: 2200 W
                187: 2100,        # PV2 Power: 2100 W
                183: 5140,        # Battery Voltage: 51.40 V
                184: 88,          # Battery SOC: 88%
                190: 1400,        # Battery Power: 1400 W
                73: 2285,         # AC Voltage: 228.5 V
                76: 125,          # AC Current: 12.5 A
                86: 2850,         # AC Active Power: 2850 W
            }
        elif family == DeyeDeviceFamily.STRING:
            return {
                60: 450,          # Daily: 45.0 kWh
                63: 15200,        # Total: 1520.0 kWh
                0x49: 2300,       # L1 Voltage: 230.0 V
                0x4C: 250,        # L1 Current: 25.0 A
                0x4A: 2310,       # L2 Voltage: 231.0 V
                0x4D: 248,        # L2 Current: 24.8 A
                0x4B: 2295,       # L3 Voltage: 229.5 V
                0x4E: 252,        # L3 Current: 25.2 A
                40: 1000,         # Active Power Reg: 100.0%
                0x5B: 1450,       # IGBT Temp: 45.0°C
            }
        elif family == DeyeDeviceFamily.MICRO:
            return {
                60: 85,           # Daily: 8.5 kWh
                63: 2400,         # Total: 240.0 kWh
                0x49: 2305,       # Grid Voltage: 230.5 V
                0x4C: 86,         # Grid Current: 8.6 A
                40: 100,          # Active Power Reg: 100%
            }
        elif family == DeyeDeviceFamily.IGEN_DTSD422:
            return {
                0x01: 2302,       # CT1 Voltage: 230.2 V
                0x07: 15400,      # CT1 Current: 15.400 A
                0x0D: 3540,       # CT1 Active Power: 3540 W
                0x03: 2298,       # CT2 Voltage: 229.8 V
                0x09: 14900,      # CT2 Current: 14.900 A
                0x0F: 3420,       # CT2 Active Power: 3420 W
                0x05: 2305,       # CT3 Voltage: 230.5 V
                0x0B: 15200,      # CT3 Current: 15.200 A
                0x11: 3500,       # CT3 Active Power: 3500 W
                0x15: 185000,     # Total Pos Energy: 1850.00 kWh
                0x19: 45000,      # Total Neg Energy: 450.00 kWh
            }
        return {}

    @staticmethod
    def decode_family_telemetry(
        family: DeyeDeviceFamily,
        raw_registers: dict[int, int],
        logger_sn: str = "1234567890",
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Decode raw registers into typed values and MQTT observation topic payloads."""
        sensors = DEYE_FAMILY_CATALOG.get(family, [])
        router = DeyeMqttTopicRouter("deye")

        decoded_values: dict[str, Any] = {}
        mqtt_messages: list[dict[str, Any]] = []

        for sensor in sensors:
            if sensor.reg_addr in raw_registers:
                raw = raw_registers[sensor.reg_addr]
                if sensor.signed and raw > 32767:
                    raw = raw - 65536
                val = round((raw * sensor.scale) + sensor.offset, 3)
                decoded_values[sensor.mqtt_topic_suffix] = val

                topic = router.build_publish_topic(logger_sn, sensor.mqtt_topic_suffix)
                mqtt_messages.append({
                    "topic": topic,
                    "payload": str(val),
                    "name": sensor.name,
                    "unit": sensor.unit,
                })

        return decoded_values, mqtt_messages


# ---------------------------------------------------------------------------
# Normalizer to Solar Fleet EMS Unified Schema
# ---------------------------------------------------------------------------

def normalize_deye_mqtt_telemetry(
    family: DeyeDeviceFamily,
    decoded: dict[str, Any],
    device_id: str = "deye_unit_01",
) -> dict[str, Any]:
    """Map Deye multi-family decoded telemetry into unified Solar Fleet EMS model."""
    pv1_p = float(decoded.get("dc/pv1/power", 0.0))
    pv2_p = float(decoded.get("dc/pv2/power", 0.0))
    total_pv = pv1_p + pv2_p

    grid_p = float(decoded.get("ac/total_power", decoded.get("ac/active_power", 0.0)))
    bat_p = float(decoded.get("battery/power", 0.0))
    bat_soc = float(decoded.get("battery/soc", decoded.get("bms/stack_soc", 0.0)))
    bat_v = float(decoded.get("battery/voltage", decoded.get("bms/stack_voltage", 0.0)))

    day_yield = float(decoded.get("day_energy", 0.0))
    total_yield = float(decoded.get("total_energy", 0.0))

    grid_v1 = float(decoded.get("ac/l1/voltage", 230.0))
    grid_v2 = float(decoded.get("ac/l2/voltage", 0.0))
    grid_v3 = float(decoded.get("ac/l3/voltage", 0.0))

    # Calculate load estimate: Solar + Battery Discharge - Grid Export
    est_load = max(0.0, total_pv - bat_p - grid_p)

    return {
        "device_id": device_id,
        "vendor": "Deye / SunSynk",
        "family": family.value,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "pv": {
            "total_power_w": round(total_pv, 1),
            "pv1_power_w": round(pv1_p, 1),
            "pv2_power_w": round(pv2_p, 1),
        },
        "battery": {
            "power_w": round(bat_p, 1),
            "voltage_v": round(bat_v, 2),
            "soc_pct": round(bat_soc, 1),
            "state": "charging" if bat_p > 50 else ("discharging" if bat_p < -50 else "idle"),
        },
        "grid": {
            "active_power_w": round(grid_p, 1),
            "voltage_l1_v": round(grid_v1, 1),
            "voltage_l2_v": round(grid_v2, 1) if grid_v2 > 0 else None,
            "voltage_l3_v": round(grid_v3, 1) if grid_v3 > 0 else None,
        },
        "load": {
            "active_power_w": round(est_load, 1),
        },
        "energy": {
            "daily_yield_kwh": round(day_yield, 2),
            "total_yield_kwh": round(total_yield, 1),
        },
    }
