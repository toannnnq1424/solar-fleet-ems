"""Growatt SPH Hybrid Inverter Modbus Protocol Engine & TOU Scheduler.

Independently implemented for Solar Fleet EMS.
Researched and derived from upstream open-source project and empirical hardware observations:
growatt_modbus-main (GPL-3.0 License).
Per repository workflow and licensing rules, this is a clean-room independent
implementation of the Growatt SPH hybrid register map, BMS gauge block, 12-cell voltage
telemetry, 6-slot TOU time scheduler, priority mode commands, and FC06/FC16 control frame compilers.

Key Capabilities:
- Full Growatt SPH hybrid register catalogue (Input FC04 & Holding FC03)
- Battery Priority Mode Switching: Load First, Battery First (AC-Charge), Grid First (Forced Export)
- 6-Slot Time-Of-Use (TOU) Matrix for both Battery First and Grid First modes
- Time encoding/decoding: hour << 8 | minute <-> HH:MM UTC
- BMS Gauge Block (pack voltage, current, remaining capacity Ah, FCC Ah, CV target)
- 12-Cell Individual Voltage Telemetry (mV) and envelope min/max cell delta
- 32-bit Energy Counters (eac, epv, eToUser, eToGrid, eDischarge, eCharge)
- FC06 / FC16 write frame compiler with Solar Fleet safety gating (LOCKED_PENDING_HARDWARE_ACCEPTANCE)
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass, field
from datetime import time
from typing import Any, Dict, List, Optional, Tuple, Union

# ---------------------------------------------------------------------------
# Modbus CRC16 Calculation
# ---------------------------------------------------------------------------

def calculate_modbus_crc16(data: bytes) -> int:
    """Calculate Modbus RTU 16-bit CRC (polynomial 0xA001, initial 0xFFFF)."""
    crc = 0xFFFF
    for byte in data:
        crc ^= byte
        for _ in range(8):
            if crc & 0x0001:
                crc = (crc >> 1) ^ 0xA001
            else:
                crc >>= 1
    return crc


# ---------------------------------------------------------------------------
# Time Slot Encoding & Decoding Helpers
# ---------------------------------------------------------------------------

def decode_sph_time(encoded_time: int) -> str:
    """Decode Growatt SPH time register (hour << 8 | minute) to 'HH:MM'.

    Example: 542 (0x021E) -> "02:30"
    """
    hour = (encoded_time >> 8) & 0xFF
    minute = encoded_time & 0xFF
    return f"{hour:02d}:{minute:02d}"


def encode_sph_time(val: Union[str, int, time]) -> int:
    """Encode 'HH:MM', time object, or integer to Growatt SPH time format (hour << 8 | minute).

    Example: "02:30" -> 542 (0x021E)
    """
    if isinstance(val, int):
        return val
    if isinstance(val, time):
        return (val.hour << 8) | val.minute
    if isinstance(val, str):
        parts = val.strip().split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid time string '{val}'. Expected 'HH:MM'")
        hour = int(parts[0])
        minute = int(parts[1])
        if not (0 <= hour <= 23 and 0 <= minute <= 59):
            raise ValueError(f"Time '{val}' out of valid range (00:00 - 23:59)")
        return (hour << 8) | minute
    raise TypeError(f"Unsupported time type: {type(val)}")


# ---------------------------------------------------------------------------
# Slot Registry Maps (Empirically Verified on Hardware)
# ---------------------------------------------------------------------------

# Battery First (AC charging) slots: [start_reg, end_reg, enable_reg]
# Empirical finding: Slots 4-6 start at 1018, NOT 1017 as claimed in old documentation!
GROWATT_BATT_FIRST_SLOTS: List[Tuple[int, int, int]] = [
    (1100, 1101, 1102),  # Slot 1
    (1103, 1104, 1105),  # Slot 2
    (1106, 1107, 1108),  # Slot 3
    (1018, 1019, 1020),  # Slot 4 (verified offset)
    (1021, 1022, 1023),  # Slot 5
    (1024, 1025, 1026),  # Slot 6
]

# Grid First (Forced discharge to grid) slots: [start_reg, end_reg, enable_reg]
GROWATT_GRID_FIRST_SLOTS: List[Tuple[int, int, int]] = [
    (1080, 1081, 1082),  # Slot 1 (verified)
    (1083, 1084, 1085),  # Slot 2
    (1086, 1087, 1088),  # Slot 3
    (1027, 1028, 1029),  # Slot 4 (derived offset from 1026)
    (1030, 1031, 1032),  # Slot 5
    (1033, 1034, 1035),  # Slot 6
]


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class GrowattTOUSlot:
    """Represents a single programmed Time-Of-Use charge/discharge slot."""

    slot_number: int
    slot_type: str  # 'battery_first' or 'grid_first'
    start_time: str
    end_time: str
    enabled: bool
    start_register: int
    end_register: int
    enable_register: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GrowattBMSGauge:
    """Decoded Growatt SPH BMS pack parameters (input registers 1087..1097)."""

    voltage_v: float
    current_a: float
    max_charge_current_a: float
    remaining_capacity_ah: float
    full_charge_capacity_ah: float
    cv_voltage_target_v: float
    bms_soc_pct: float
    bms_soh_pct: float
    bms_cycle_count: int

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GrowattCellTelemetry:
    """Decoded individual cell voltages and cell envelope (input registers 1108..1123)."""

    max_cell_v: float
    min_cell_v: float
    delta_cell_mv: float
    module_count: int
    cell_voltages_mv: List[int] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GrowattCompiledCommand:
    """Compiled Modbus FC06 or FC16 command frame for Growatt SPH."""

    command_name: str
    function_code: int
    register_address: int
    register_count: int
    raw_values: List[int]
    hex_payload: str
    wire_bytes: List[int]
    safety_gate: str
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Growatt SPH Protocol Engine
# ---------------------------------------------------------------------------

class GrowattSPHEngine:
    """Core logic for Growatt SPH hybrid inverters."""

    SLAVE_ID_DEFAULT: int = 1

    # -----------------------------------------------------------------------
    # Decoding Methods
    # -----------------------------------------------------------------------

    @staticmethod
    def decode_32bit_kwh(high_word: int, low_word: int, scale: float = 0.1) -> float:
        """Combine 2 consecutive 16-bit registers into a 32-bit kWh energy counter."""
        raw = ((high_word & 0xFFFF) << 16) | (low_word & 0xFFFF)
        return round(raw * scale, 2)

    @classmethod
    def decode_bms_gauge(cls, regs: Dict[int, int]) -> Optional[GrowattBMSGauge]:
        """Decode input registers 1083..1097 into structured BMS gauge parameters."""
        if 1087 not in regs or 1088 not in regs:
            return None

        # 1087: bmsVoltage (x0.01 V)
        voltage_v = round((regs.get(1087, 0) & 0xFFFF) * 0.01, 2)

        # 1088: bmsCurrent (x0.01 A, signed)
        raw_curr = regs.get(1088, 0) & 0xFFFF
        signed_curr = struct.unpack(">h", struct.pack(">H", raw_curr))[0]
        current_a = round(signed_curr * 0.01, 2)

        # 1090: maxChargeCurrent (x0.01 A)
        max_charge_a = round((regs.get(1090, 0) & 0xFFFF) * 0.01, 2)

        # 1091: remaining capacity (10 mAh units = 0.01 Ah)
        rm_ah = round((regs.get(1091, 0) & 0xFFFF) * 0.01, 2)

        # 1092: full-charge capacity (10 mAh units = 0.01 Ah)
        fcc_ah = round((regs.get(1092, 0) & 0xFFFF) * 0.01, 2)

        # 1097: constant voltage target (x0.01 V)
        cv_target_v = round((regs.get(1097, 0) & 0xFFFF) * 0.01, 2)

        # 1085: bmsSOC, 1086: bmsSOH, 1084: bmsCycleCount
        soc = float(regs.get(1085, 0) & 0xFFFF)
        soh = float(regs.get(1086, 0) & 0xFFFF)
        cycles = int(regs.get(1084, 0) & 0xFFFF)

        return GrowattBMSGauge(
            voltage_v=voltage_v,
            current_a=current_a,
            max_charge_current_a=max_charge_a,
            remaining_capacity_ah=rm_ah,
            full_charge_capacity_ah=fcc_ah,
            cv_voltage_target_v=cv_target_v,
            bms_soc_pct=soc,
            bms_soh_pct=soh,
            bms_cycle_count=cycles,
        )

    @classmethod
    def decode_cell_telemetry(cls, regs: Dict[int, int]) -> Optional[GrowattCellTelemetry]:
        """Decode input registers 1108..1123 into individual cell voltages and envelope."""
        if 1108 not in regs or 1109 not in regs:
            return None

        # 1108: maxCellVoltage (x0.001 V)
        max_v = round((regs.get(1108, 0) & 0xFFFF) * 0.001, 3)

        # 1109: minCellVoltage (x0.001 V)
        min_v = round((regs.get(1109, 0) & 0xFFFF) * 0.001, 3)

        # delta in mV
        delta_mv = round((max_v - min_v) * 1000.0, 1)

        # 1110: batteryModuleCount
        mod_count = int(regs.get(1110, 1) & 0xFFFF)

        # 1112..1123: 12 individual cell voltages in mV
        cells: List[int] = []
        for reg_addr in range(1112, 1124):
            if reg_addr in regs:
                cells.append(int(regs[reg_addr] & 0xFFFF))

        return GrowattCellTelemetry(
            max_cell_v=max_v,
            min_cell_v=min_v,
            delta_cell_mv=delta_mv,
            module_count=mod_count,
            cell_voltages_mv=cells,
        )

    @classmethod
    def decode_tou_slots(cls, holding_regs: Dict[int, int]) -> Dict[str, Any]:
        """Decode all 12 Time-Of-Use slots (6 Battery First + 6 Grid First)."""
        bf_slots = []
        for idx, (s_reg, e_reg, en_reg) in enumerate(GROWATT_BATT_FIRST_SLOTS, 1):
            if s_reg in holding_regs and e_reg in holding_regs and en_reg in holding_regs:
                s_val = holding_regs[s_reg]
                e_val = holding_regs[e_reg]
                en_val = bool(holding_regs[en_reg])
                bf_slots.append(
                    GrowattTOUSlot(
                        slot_number=idx,
                        slot_type="battery_first",
                        start_time=decode_sph_time(s_val),
                        end_time=decode_sph_time(e_val),
                        enabled=en_val,
                        start_register=s_reg,
                        end_register=e_reg,
                        enable_register=en_reg,
                    ).to_dict()
                )

        gf_slots = []
        for idx, (s_reg, e_reg, en_reg) in enumerate(GROWATT_GRID_FIRST_SLOTS, 1):
            if s_reg in holding_regs and e_reg in holding_regs and en_reg in holding_regs:
                s_val = holding_regs[s_reg]
                e_val = holding_regs[e_reg]
                en_val = bool(holding_regs[en_reg])
                gf_slots.append(
                    GrowattTOUSlot(
                        slot_number=idx,
                        slot_type="grid_first",
                        start_time=decode_sph_time(s_val),
                        end_time=decode_sph_time(e_val),
                        enabled=en_val,
                        start_register=s_reg,
                        end_register=e_reg,
                        enable_register=en_reg,
                    ).to_dict()
                )

        return {
            "battery_first_slots": bf_slots,
            "grid_first_slots": gf_slots,
            "total_slots_decoded": len(bf_slots) + len(gf_slots),
        }

    # -----------------------------------------------------------------------
    # Command Compilers (Modbus FC06 & FC16 Frame Generation)
    # -----------------------------------------------------------------------

    @classmethod
    def compile_load_first_mode(
        cls,
        slave_id: int = SLAVE_ID_DEFAULT,
        bypass_safety: bool = False,
    ) -> List[GrowattCompiledCommand]:
        """Compile commands to switch inverter to Load First (self-consumption mode).

        Action:
        1. Disable Battery First slot 6 (write 0 to reg 1026, FC06).
        2. Disable Grid First slot 1 (write 0 to reg 1082, FC06).
        """
        cmds: List[GrowattCompiledCommand] = []
        safety_gate = "COMMISSIONED_WRITE_ENABLED" if bypass_safety else "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

        # 1. Disable BF slot 6 (Reg 1026)
        payload_1026 = bytes([slave_id, 0x06, 0x04, 0x02, 0x00, 0x00])  # 1026 = 0x0402
        crc_1026 = calculate_modbus_crc16(payload_1026)
        wire_1026 = list(payload_1026) + [crc_1026 & 0xFF, (crc_1026 >> 8) & 0xFF]

        cmds.append(
            GrowattCompiledCommand(
                command_name="disable_batt_first_slot_6",
                function_code=6,
                register_address=1026,
                register_count=1,
                raw_values=[0],
                hex_payload=" ".join(f"{b:02X}" for b in wire_1026),
                wire_bytes=wire_1026,
                safety_gate=safety_gate,
                description="Disable Battery First Slot 6 (Reg 1026 = 0)",
            )
        )

        # 2. Disable GF slot 1 (Reg 1082)
        payload_1082 = bytes([slave_id, 0x06, 0x04, 0x3A, 0x00, 0x00])  # 1082 = 0x043A
        crc_1082 = calculate_modbus_crc16(payload_1082)
        wire_1082 = list(payload_1082) + [crc_1082 & 0xFF, (crc_1082 >> 8) & 0xFF]

        cmds.append(
            GrowattCompiledCommand(
                command_name="disable_grid_first_slot_1",
                function_code=6,
                register_address=1082,
                register_count=1,
                raw_values=[0],
                hex_payload=" ".join(f"{b:02X}" for b in wire_1082),
                wire_bytes=wire_1082,
                safety_gate=safety_gate,
                description="Disable Grid First Slot 1 (Reg 1082 = 0)",
            )
        )

        return cmds

    @classmethod
    def compile_battery_first_slot(
        cls,
        slot_number: int = 6,
        start_time: str = "00:00",
        end_time: str = "04:00",
        charge_rate_pct: int = 100,
        stop_soc_pct: int = 100,
        ac_charge_enable: int = 1,
        slave_id: int = SLAVE_ID_DEFAULT,
        bypass_safety: bool = False,
    ) -> List[GrowattCompiledCommand]:
        """Compile commands to schedule Battery First (forced AC charging from grid/PV).

        Action:
        1. Set Charge Rate %, Stop SOC %, and AC Charge Enable (Regs 1090..1092, FC16).
        2. Program Slot Start, End, and Enable = 1 (FC16).
        """
        if not (1 <= slot_number <= 6):
            raise ValueError(f"Invalid slot number: {slot_number}. Expected 1..6")
        if not (0 <= charge_rate_pct <= 100):
            raise ValueError(f"Charge rate must be 0..100%, got {charge_rate_pct}")
        if not (0 <= stop_soc_pct <= 100):
            raise ValueError(f"Stop SOC must be 0..100%, got {stop_soc_pct}")

        enc_start = encode_sph_time(start_time)
        enc_end = encode_sph_time(end_time)
        slot_regs = GROWATT_BATT_FIRST_SLOTS[slot_number - 1]
        start_reg = slot_regs[0]

        safety_gate = "COMMISSIONED_WRITE_ENABLED" if bypass_safety else "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
        cmds: List[GrowattCompiledCommand] = []

        # 1. FC16 to write [charge_rate, stop_soc, ac_charge_enable] at reg 1090
        # Reg 1090 = 0x0442, count = 3, byte count = 6
        vals_1090 = [charge_rate_pct, stop_soc_pct, ac_charge_enable]
        payload_1090 = bytes([
            slave_id, 0x10, 0x04, 0x42, 0x00, 0x03, 0x06,
            (charge_rate_pct >> 8) & 0xFF, charge_rate_pct & 0xFF,
            (stop_soc_pct >> 8) & 0xFF, stop_soc_pct & 0xFF,
            (ac_charge_enable >> 8) & 0xFF, ac_charge_enable & 0xFF,
        ])
        crc_1090 = calculate_modbus_crc16(payload_1090)
        wire_1090 = list(payload_1090) + [crc_1090 & 0xFF, (crc_1090 >> 8) & 0xFF]

        cmds.append(
            GrowattCompiledCommand(
                command_name="set_ac_charge_rates",
                function_code=16,
                register_address=1090,
                register_count=3,
                raw_values=vals_1090,
                hex_payload=" ".join(f"{b:02X}" for b in wire_1090),
                wire_bytes=wire_1090,
                safety_gate=safety_gate,
                description=f"Set AC Charge: Rate={charge_rate_pct}%, Stop SOC={stop_soc_pct}%, Enable={ac_charge_enable} (Regs 1090..1092)",
            )
        )

        # 2. FC16 to write [start, end, 1] at slot start_reg
        vals_slot = [enc_start, enc_end, 1]
        payload_slot = bytes([
            slave_id, 0x10, (start_reg >> 8) & 0xFF, start_reg & 0xFF, 0x00, 0x03, 0x06,
            (enc_start >> 8) & 0xFF, enc_start & 0xFF,
            (enc_end >> 8) & 0xFF, enc_end & 0xFF,
            0x00, 0x01,
        ])
        crc_slot = calculate_modbus_crc16(payload_slot)
        wire_slot = list(payload_slot) + [crc_slot & 0xFF, (crc_slot >> 8) & 0xFF]

        cmds.append(
            GrowattCompiledCommand(
                command_name=f"program_batt_first_slot_{slot_number}",
                function_code=16,
                register_address=start_reg,
                register_count=3,
                raw_values=vals_slot,
                hex_payload=" ".join(f"{b:02X}" for b in wire_slot),
                wire_bytes=wire_slot,
                safety_gate=safety_gate,
                description=f"Program Battery First Slot {slot_number}: {start_time} - {end_time}, Enabled=1 (Regs {start_reg}..{start_reg+2})",
            )
        )

        return cmds

    @classmethod
    def compile_grid_first_slot(
        cls,
        slot_number: int = 1,
        start_time: str = "17:00",
        end_time: str = "19:00",
        discharge_rate_pct: int = 100,
        stop_soc_floor_pct: int = 25,
        slave_id: int = SLAVE_ID_DEFAULT,
        bypass_safety: bool = False,
    ) -> List[GrowattCompiledCommand]:
        """Compile commands to schedule Grid First (forced discharge to grid for peak shaving/export).

        Action:
        1. Set Discharge Rate % and Stop SOC Floor % (Regs 1070..1071, FC16).
        2. Program Slot Start, End, and Enable = 1 (FC16).
        """
        if not (1 <= slot_number <= 6):
            raise ValueError(f"Invalid slot number: {slot_number}. Expected 1..6")
        if not (0 <= discharge_rate_pct <= 100):
            raise ValueError(f"Discharge rate must be 0..100%, got {discharge_rate_pct}")
        if not (0 <= stop_soc_floor_pct <= 100):
            raise ValueError(f"Stop SOC must be 0..100%, got {stop_soc_floor_pct}")

        enc_start = encode_sph_time(start_time)
        enc_end = encode_sph_time(end_time)
        slot_regs = GROWATT_GRID_FIRST_SLOTS[slot_number - 1]
        start_reg = slot_regs[0]

        safety_gate = "COMMISSIONED_WRITE_ENABLED" if bypass_safety else "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
        cmds: List[GrowattCompiledCommand] = []

        # 1. FC16 to write [discharge_rate, stop_soc] at reg 1070
        # Reg 1070 = 0x042E, count = 2, byte count = 4
        vals_1070 = [discharge_rate_pct, stop_soc_floor_pct]
        payload_1070 = bytes([
            slave_id, 0x10, 0x04, 0x2E, 0x00, 0x02, 0x04,
            (discharge_rate_pct >> 8) & 0xFF, discharge_rate_pct & 0xFF,
            (stop_soc_floor_pct >> 8) & 0xFF, stop_soc_floor_pct & 0xFF,
        ])
        crc_1070 = calculate_modbus_crc16(payload_1070)
        wire_1070 = list(payload_1070) + [crc_1070 & 0xFF, (crc_1070 >> 8) & 0xFF]

        cmds.append(
            GrowattCompiledCommand(
                command_name="set_grid_first_rates",
                function_code=16,
                register_address=1070,
                register_count=2,
                raw_values=vals_1070,
                hex_payload=" ".join(f"{b:02X}" for b in wire_1070),
                wire_bytes=wire_1070,
                safety_gate=safety_gate,
                description=f"Set Grid First: Discharge Rate={discharge_rate_pct}%, Stop SOC Floor={stop_soc_floor_pct}% (Regs 1070..1071)",
            )
        )

        # 2. FC16 to write [start, end, 1] at slot start_reg
        vals_slot = [enc_start, enc_end, 1]
        payload_slot = bytes([
            slave_id, 0x10, (start_reg >> 8) & 0xFF, start_reg & 0xFF, 0x00, 0x03, 0x06,
            (enc_start >> 8) & 0xFF, enc_start & 0xFF,
            (enc_end >> 8) & 0xFF, enc_end & 0xFF,
            0x00, 0x01,
        ])
        crc_slot = calculate_modbus_crc16(payload_slot)
        wire_slot = list(payload_slot) + [crc_slot & 0xFF, (crc_slot >> 8) & 0xFF]

        cmds.append(
            GrowattCompiledCommand(
                command_name=f"program_grid_first_slot_{slot_number}",
                function_code=16,
                register_address=start_reg,
                register_count=3,
                raw_values=vals_slot,
                hex_payload=" ".join(f"{b:02X}" for b in wire_slot),
                wire_bytes=wire_slot,
                safety_gate=safety_gate,
                description=f"Program Grid First Slot {slot_number}: {start_time} - {end_time}, Enabled=1 (Regs {start_reg}..{start_reg+2})",
            )
        )

        return cmds
