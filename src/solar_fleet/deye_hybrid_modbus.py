"""Deye Three-Phase Low-Voltage Hybrid Inverter Modbus Protocol Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
deye-modbus-ha-main (MIT License, author Developer089).
Per repository workflow and licensing rules, this is a clean-room independent
implementation of the protocol data structures, work mode control, 6-slot Time-of-Use
(TOU) schedule matrix, telemetry normalization, and Modbus FC06/FC16 write frame generation.

Key Capabilities:
- Full support for Deye SUN-xxK-SG04LP3 / SG05LP3 three-phase hybrid inverters (Device Type 0x0500)
- Holding register telemetry decoders: PV1..PV4, 3-Phase Grid, 3-Phase Load, 3-Phase Inverter,
  Battery DC, UPS backup port, and little-endian 32-bit energy counters
- Work Mode switching (Reg 142: Selling First, Zero Export to Load, Zero Export to CT)
- Solar Sell (Reg 145) and Grid Charge (Reg 130) control
- 6-Slot TOU Schedule Matrix:
  * Time points 1..6 (Regs 148..153, decimal HHMM format)
  * Power limits 1..6 (Regs 154..159, Watts)
  * Target SOC 1..6 (Regs 166..171, %)
  * Charge source 1..6 (Regs 172..177: Off, Grid, Generator, Grid+Generator)
- Safety gating ensuring all writable controls remain LOCKED_PENDING_HARDWARE_ACCEPTANCE
- Modbus RTU / TCP FC06 and FC16 frame compiler with CRC-16 Modbus validation
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional, Tuple

# ---------------------------------------------------------------------------
# Modbus CRC16 Standard Calculation
# ---------------------------------------------------------------------------

def calculate_modbus_crc16(data: bytes) -> int:
    """Calculate standard Modbus RTU 16-bit CRC (polynomial 0xA001, initial 0xFFFF)."""
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
# Deye Register Constants
# ---------------------------------------------------------------------------

# Control / Settings Registers (Holding FC03 / FC06 / FC16)
REG_ACTIVE_POWER_REGULATION = 77    # Active power regulation % (0..120%)
REG_INVERTER_ONOFF = 80             # Inverter On/Off (0: Standby, 1: On)
REG_BATT_CAPACITY_AH = 102          # Battery Capacity in Ah
REG_BATT_MAX_CHARGE_A = 108         # Battery Max Charge Current (A)
REG_BATT_MAX_DISCHARGE_A = 109      # Battery Max Discharge Current (A)
REG_BATT_SHUTDOWN_SOC = 115         # Battery Shutdown SOC (%)
REG_BATT_RESTART_SOC = 116          # Battery Restart SOC (%)
REG_BATT_LOW_SOC = 117              # Battery Low SOC (%)
REG_GRID_CHARGE_CURRENT = 128       # Grid Charge Current (A)
REG_GEN_CHARGE_ENABLE = 129         # Generator Charge Enable (0: Off, 1: On)
REG_GRID_CHARGE_ENABLE = 130        # Grid Charge Enable (0: Off, 1: On)
REG_WORK_MODE = 142                 # 0: Selling First, 1: Zero Export to Load, 2: Zero Export to CT
REG_MAX_GRID_OUTPUT_POWER = 143     # Max Grid Output Power (W)
REG_SOLAR_SELL = 145                # Solar Sell / Export Switch (0: Off, 1: On)
REG_MAX_SELL_POWER = 340            # Max Sell Power (W)

# TOU Registers (6 Slots)
REG_TOU_TIME_START = 148            # 148..153: Time 1..6 (HHMM decimal, e.g. 02:30 -> 230)
REG_TOU_POWER_START = 154           # 154..159: Power 1..6 (W, 0..16000)
REG_TOU_SOC_START = 166             # 166..171: SOC 1..6 (%, 0..100)
REG_TOU_CHARGE_SOURCE_START = 172   # 172..177: Charge source 1..6 (0: Off, 1: Grid, 2: Gen, 3: Both)

# Telemetry Registers (Holding FC03)
REG_RUN_STATE = 500                 # 0: standby, 1: self-check, 2: normal, 3: alarm, 4: fault
REG_DC_TEMP = 540                   # DC Temp ((raw - 1000) * 0.1 °C)
REG_AC_TEMP = 541                   # AC Temp ((raw - 1000) * 0.1 °C)

# Battery Telemetry
REG_BATT_TEMP = 586                 # Battery Temp ((raw - 1000) * 0.1 °C)
REG_BATT_VOLTAGE = 587              # Battery Voltage (0.01 V)
REG_BATT_SOC = 588                  # Battery SOC (%)
REG_BATT_POWER = 590                # Battery Power (W, signed)
REG_BATT_CURRENT = 591              # Battery Current (0.01 A, signed)
REG_BATT_CORRECTED_AH = 592         # Battery Corrected Capacity (Ah)

# Grid Telemetry
REG_GRID_VOLTAGE_L1 = 598           # 0.1 V
REG_GRID_VOLTAGE_L2 = 599           # 0.1 V
REG_GRID_VOLTAGE_L3 = 600           # 0.1 V
REG_GRID_FREQ = 609                 # 0.01 Hz
REG_GRID_CURRENT_L1 = 613           # 0.01 A, signed
REG_GRID_CURRENT_L2 = 614           # 0.01 A, signed
REG_GRID_CURRENT_L3 = 615           # 0.01 A, signed
REG_GRID_POWER_L1 = 616             # 1 W, signed
REG_GRID_POWER_L2 = 617             # 1 W, signed
REG_GRID_POWER_L3 = 618             # 1 W, signed
REG_GRID_POWER_TOTAL = 619          # 1 W, signed (+ export / - import)

# Inverter & Load Telemetry
REG_INVERTER_POWER_TOTAL = 636      # 1 W, signed
REG_UPS_POWER_TOTAL = 643           # Backup Power 1 W
REG_LOAD_POWER_TOTAL = 653          # Load Power 1 W, signed
REG_GEN_POWER_TOTAL = 667           # Generator Power 1 W, signed

# PV Input Telemetry
REG_PV1_POWER = 672                 # 1 W
REG_PV2_POWER = 673                 # 1 W
REG_PV3_POWER = 674                 # 1 W
REG_PV4_POWER = 675                 # 1 W
REG_PV1_VOLT = 676                  # 0.1 V
REG_PV1_CURR = 677                  # 0.1 A
REG_PV2_VOLT = 678                  # 0.1 V
REG_PV2_CURR = 679                  # 0.1 A

# Energy Counters (Today: 0.1 kWh, uint16)
REG_PV_ENERGY_TODAY = 529           # 0.1 kWh
REG_BATT_CHARGE_TODAY = 514         # 0.1 kWh
REG_BATT_DISCHARGE_TODAY = 515      # 0.1 kWh
REG_GRID_IMPORT_TODAY = 520         # 0.1 kWh
REG_GRID_EXPORT_TODAY = 521         # 0.1 kWh
REG_LOAD_ENERGY_TODAY = 526         # 0.1 kWh

# Energy Counters (Total: 0.1 kWh, uint32 little-endian words: low word at base)
REG_PV_ENERGY_TOTAL = 534           # 534..535 (32-bit LE words)
REG_BATT_CHARGE_TOTAL = 516         # 516..517
REG_BATT_DISCHARGE_TOTAL = 518      # 518..519
REG_GRID_IMPORT_TOTAL = 522         # 522..523
REG_GRID_EXPORT_TOTAL = 524         # 524..525
REG_LOAD_ENERGY_TOTAL = 527         # 527..528

# Work Mode Constants
WORK_MODE_SELLING_FIRST = 0
WORK_MODE_ZERO_EXPORT_TO_LOAD = 1
WORK_MODE_ZERO_EXPORT_TO_CT = 2

WORK_MODE_LABELS: Dict[int, str] = {
    WORK_MODE_SELLING_FIRST: "Selling First (Hòa lưới bán điện dư)",
    WORK_MODE_ZERO_EXPORT_TO_LOAD: "Zero Export To Load (Bám tải nội bộ không phát ngược)",
    WORK_MODE_ZERO_EXPORT_TO_CT: "Zero Export To CT (Bám tải qua biến dòng CT lưới)",
}

TOU_CHARGE_SOURCE_LABELS: Dict[int, str] = {
    0: "Off (Tự dùng / Xả pin theo tải)",
    1: "Grid (Sạc cưỡng bức từ lưới AC)",
    2: "Generator (Sạc từ máy phát)",
    3: "Grid + Generator (Sạc lưới & máy phát)",
}


# ---------------------------------------------------------------------------
# Helper Functions: Time Encoding & 32-bit Word Order
# ---------------------------------------------------------------------------

def encode_deye_time(time_str: str) -> int:
    """Encode 'HH:MM' string to Deye decimal format (hour * 100 + minute).

    Example: '02:30' -> 230, '00:00' -> 0, '23:59' -> 2359.
    """
    parts = time_str.strip().split(":")
    if len(parts) != 2:
        raise ValueError(f"Invalid time format '{time_str}', expected 'HH:MM'")
    hour = int(parts[0])
    minute = int(parts[1])
    if not (0 <= hour <= 23 and 0 <= minute <= 59):
        raise ValueError(f"Time out of range: {time_str}")
    return (hour * 100) + minute


def decode_deye_time(val: int) -> str:
    """Decode Deye decimal format (hour * 100 + minute) to 'HH:MM' string."""
    val = max(0, min(2359, val))
    hour = val // 100
    minute = val % 100
    return f"{hour:02d}:{minute:02d}"


def decode_u32_le_words(low_word: int, high_word: int) -> int:
    """Decode two 16-bit registers in Deye word order (little-endian: low word first)."""
    return (int(high_word) << 16) | (int(low_word) & 0xFFFF)


def encode_u32_le_words(val: int) -> Tuple[int, int]:
    """Encode 32-bit unsigned int into (low_word, high_word)."""
    val = val & 0xFFFFFFFF
    low_word = val & 0xFFFF
    high_word = (val >> 16) & 0xFFFF
    return low_word, high_word


def decode_s16(val: int) -> int:
    """Decode 16-bit signed integer (two's complement)."""
    val &= 0xFFFF
    return val if val < 0x8000 else val - 0x10000


def decode_deye_temp(val: int) -> float:
    """Decode temperature with 1000 offset and 0.1 scale: (val - 1000) * 0.1 °C."""
    return round((val - 1000) * 0.1, 1)


# ---------------------------------------------------------------------------
# TOU Slot Data Models
# ---------------------------------------------------------------------------

@dataclass
class DeyeTouSlot:
    """Represents one of the 6 Deye Time-of-Use schedule slots."""

    slot_number: int  # 1..6
    time_str: str     # 'HH:MM'
    time_raw: int     # decimal HHMM e.g. 230
    power_w: int      # max power in Watts (0..16000)
    target_soc: int   # target or floor SOC (0..100%)
    charge_source: int  # 0: Off, 1: Grid, 2: Gen, 3: Both
    charge_source_label: str = ""

    def __post_init__(self):
        if not self.charge_source_label:
            self.charge_source_label = TOU_CHARGE_SOURCE_LABELS.get(self.charge_source, "Unknown")

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ---------------------------------------------------------------------------
# Compiled Modbus Commands & Safety Frame Generation
# ---------------------------------------------------------------------------

@dataclass
class DeyeModbusWriteAction:
    """Atomic Modbus write action targeting Deye holding registers."""

    register_address: int
    values: List[int]
    function_code: int  # 0x06 or 0x10
    description: str

    def to_rtu_frame(self, slave_id: int = 1) -> bytes:
        """Compile action to Modbus RTU byte frame with CRC16."""
        if self.function_code == 0x06:
            val = self.values[0] & 0xFFFF
            payload = struct.pack(">BBHH", slave_id, 0x06, self.register_address, val)
        elif self.function_code == 0x10:
            qty = len(self.values)
            byte_count = qty * 2
            payload = struct.pack(">BBHHB", slave_id, 0x10, self.register_address, qty, byte_count)
            for v in self.values:
                payload += struct.pack(">H", v & 0xFFFF)
        else:
            raise ValueError(f"Unsupported write function code {self.function_code}")

        crc = calculate_modbus_crc16(payload)
        return payload + struct.pack("<H", crc)


@dataclass
class DeyeCompiledCommand:
    """Compiled, verified, and safety-gated Deye command."""

    command_id: str
    command_name: str
    description: str
    actions: List[DeyeModbusWriteAction]
    readback_registers: List[int]
    safety_gate: str = "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    reason: str = "Live Deye inverter writes require physical commissioning and safety lock release."
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "command_id": self.command_id,
            "command_name": self.command_name,
            "description": self.description,
            "safety_gate": self.safety_gate,
            "reason": self.reason,
            "readback_registers": self.readback_registers,
            "actions": [
                {
                    "register_address": a.register_address,
                    "values": a.values,
                    "function_code": f"0x{a.function_code:02X}",
                    "description": a.description,
                    "rtu_frame_hex": a.to_rtu_frame().hex().upper(),
                }
                for a in self.actions
            ],
            "metadata": self.metadata,
        }


# ---------------------------------------------------------------------------
# Deye Hybrid Controller Engine
# ---------------------------------------------------------------------------

class DeyeHybridEngine:
    """Protocol encoder, decoder, and command compiler for Deye Hybrid Inverters."""

    @staticmethod
    def decode_telemetry(registers: Dict[int, int]) -> Dict[str, Any]:
        """Decode Deye holding registers into normalized EMS telemetry."""
        # PV Power & Voltages
        pv1_w = registers.get(REG_PV1_POWER, 0)
        pv2_w = registers.get(REG_PV2_POWER, 0)
        pv3_w = registers.get(REG_PV3_POWER, 0)
        pv4_w = registers.get(REG_PV4_POWER, 0)
        pv_total_w = pv1_w + pv2_w + pv3_w + pv4_w

        # Battery Telemetry
        v_batt = registers.get(REG_BATT_VOLTAGE, 0) * 0.01
        i_batt = decode_s16(registers.get(REG_BATT_CURRENT, 0)) * 0.01
        p_batt = decode_s16(registers.get(REG_BATT_POWER, 0))
        soc = registers.get(REG_BATT_SOC, 0)
        t_batt = decode_deye_temp(registers.get(REG_BATT_TEMP, 1250))

        # Grid Telemetry
        p_grid = decode_s16(registers.get(REG_GRID_POWER_TOTAL, 0))
        freq_grid = registers.get(REG_GRID_FREQ, 0) * 0.01
        v_grid_l1 = registers.get(REG_GRID_VOLTAGE_L1, 0) * 0.1
        v_grid_l2 = registers.get(REG_GRID_VOLTAGE_L2, 0) * 0.1
        v_grid_l3 = registers.get(REG_GRID_VOLTAGE_L3, 0) * 0.1

        # Load & Inverter
        p_load = decode_s16(registers.get(REG_LOAD_POWER_TOTAL, 0))
        p_inv = decode_s16(registers.get(REG_INVERTER_POWER_TOTAL, 0))
        p_ups = registers.get(REG_UPS_POWER_TOTAL, 0)

        # Temperatures
        t_dc = decode_deye_temp(registers.get(REG_DC_TEMP, 1250))
        t_ac = decode_deye_temp(registers.get(REG_AC_TEMP, 1250))

        # Status
        run_state = registers.get(REG_RUN_STATE, 0)
        run_state_labels = {0: "STANDBY", 1: "SELF_CHECK", 2: "NORMAL", 3: "ALARM", 4: "FAULT"}

        # Energy Today
        pv_today_kwh = registers.get(REG_PV_ENERGY_TODAY, 0) * 0.1
        charge_today_kwh = registers.get(REG_BATT_CHARGE_TODAY, 0) * 0.1
        discharge_today_kwh = registers.get(REG_BATT_DISCHARGE_TODAY, 0) * 0.1
        grid_import_today_kwh = registers.get(REG_GRID_IMPORT_TODAY, 0) * 0.1
        grid_export_today_kwh = registers.get(REG_GRID_EXPORT_TODAY, 0) * 0.1
        load_today_kwh = registers.get(REG_LOAD_ENERGY_TODAY, 0) * 0.1

        # Energy Total (32-bit little-endian)
        pv_total_kwh = decode_u32_le_words(
            registers.get(REG_PV_ENERGY_TOTAL, 0),
            registers.get(REG_PV_ENERGY_TOTAL + 1, 0),
        ) * 0.1
        grid_import_total_kwh = decode_u32_le_words(
            registers.get(REG_GRID_IMPORT_TOTAL, 0),
            registers.get(REG_GRID_IMPORT_TOTAL + 1, 0),
        ) * 0.1
        grid_export_total_kwh = decode_u32_le_words(
            registers.get(REG_GRID_EXPORT_TOTAL, 0),
            registers.get(REG_GRID_EXPORT_TOTAL + 1, 0),
        ) * 0.1

        return {
            "run_state": run_state,
            "run_state_label": run_state_labels.get(run_state, "UNKNOWN"),
            "pv_total_power_w": pv_total_w,
            "pv_channels": {
                "pv1_w": pv1_w,
                "pv2_w": pv2_w,
                "pv3_w": pv3_w,
                "pv4_w": pv4_w,
                "pv1_v": round(registers.get(REG_PV1_VOLT, 0) * 0.1, 1),
                "pv1_a": round(registers.get(REG_PV1_CURR, 0) * 0.1, 1),
                "pv2_v": round(registers.get(REG_PV2_VOLT, 0) * 0.1, 1),
                "pv2_a": round(registers.get(REG_PV2_CURR, 0) * 0.1, 1),
            },
            "battery": {
                "voltage_v": round(v_batt, 2),
                "current_a": round(i_batt, 2),
                "power_w": p_batt,
                "soc_pct": soc,
                "temperature_c": t_batt,
                "capacity_ah": registers.get(REG_BATT_CORRECTED_AH, 0),
            },
            "grid": {
                "power_total_w": p_grid,
                "frequency_hz": round(freq_grid, 2),
                "voltage_l1_v": round(v_grid_l1, 1),
                "voltage_l2_v": round(v_grid_l2, 1),
                "voltage_l3_v": round(v_grid_l3, 1),
                "direction": "EXPORTING" if p_grid > 50 else ("IMPORTING" if p_grid < -50 else "BALANCED"),
            },
            "load": {
                "power_total_w": p_load,
                "ups_power_w": p_ups,
            },
            "inverter": {
                "power_total_w": p_inv,
                "dc_temp_c": t_dc,
                "ac_temp_c": t_ac,
            },
            "energy_today_kwh": {
                "pv": round(pv_today_kwh, 1),
                "battery_charge": round(charge_today_kwh, 1),
                "battery_discharge": round(discharge_today_kwh, 1),
                "grid_import": round(grid_import_today_kwh, 1),
                "grid_export": round(grid_export_today_kwh, 1),
                "load": round(load_today_kwh, 1),
            },
            "energy_total_kwh": {
                "pv": round(pv_total_kwh, 1),
                "grid_import": round(grid_import_total_kwh, 1),
                "grid_export": round(grid_export_total_kwh, 1),
            },
        }

    @staticmethod
    def decode_tou_schedule(registers: Dict[int, int]) -> List[Dict[str, Any]]:
        """Decode all 6 TOU slots from holding registers (148..153, 154..159, 166..171, 172..177)."""
        slots = []
        for i in range(6):
            time_raw = registers.get(REG_TOU_TIME_START + i, 0)
            power_w = registers.get(REG_TOU_POWER_START + i, 0)
            soc = registers.get(REG_TOU_SOC_START + i, 0)
            charge_src = registers.get(REG_TOU_CHARGE_SOURCE_START + i, 0)

            slot = DeyeTouSlot(
                slot_number=i + 1,
                time_str=decode_deye_time(time_raw),
                time_raw=time_raw,
                power_w=power_w,
                target_soc=soc,
                charge_source=charge_src,
            )
            slots.append(slot.to_dict())
        return slots

    @staticmethod
    def compile_work_mode(
        mode: int,
        solar_sell: Optional[bool] = None,
        max_sell_power_w: Optional[int] = None,
    ) -> DeyeCompiledCommand:
        """Compile Modbus write actions to configure Deye Work Mode and Solar Sell."""
        if mode not in (WORK_MODE_SELLING_FIRST, WORK_MODE_ZERO_EXPORT_TO_LOAD, WORK_MODE_ZERO_EXPORT_TO_CT):
            raise ValueError(f"Invalid work mode {mode}. Expected 0 (Selling First), 1 (Zero Export Load), or 2 (Zero Export CT)")

        actions = [
            DeyeModbusWriteAction(
                register_address=REG_WORK_MODE,
                values=[mode],
                function_code=0x06,
                description=f"Set Work Mode to {WORK_MODE_LABELS[mode]}",
            )
        ]
        readbacks = [REG_WORK_MODE]

        if solar_sell is not None:
            sell_val = 1 if solar_sell else 0
            actions.append(
                DeyeModbusWriteAction(
                    register_address=REG_SOLAR_SELL,
                    values=[sell_val],
                    function_code=0x06,
                    description=f"Set Solar Sell / Export switch to {'ON' if solar_sell else 'OFF'}",
                )
            )
            readbacks.append(REG_SOLAR_SELL)

        if max_sell_power_w is not None:
            sell_pwr = max(0, min(16000, max_sell_power_w))
            actions.append(
                DeyeModbusWriteAction(
                    register_address=REG_MAX_SELL_POWER,
                    values=[sell_pwr],
                    function_code=0x06,
                    description=f"Set Max Sell Power limit to {sell_pwr} W",
                )
            )
            readbacks.append(REG_MAX_SELL_POWER)

        return DeyeCompiledCommand(
            command_id=f"deye_set_work_mode_{mode}",
            command_name="Configure Deye Work Mode",
            description=f"Apply energy routing strategy: {WORK_MODE_LABELS[mode]}",
            actions=actions,
            readback_registers=readbacks,
            metadata={"mode": mode, "solar_sell": solar_sell, "max_sell_power_w": max_sell_power_w},
        )

    @staticmethod
    def compile_grid_charge(
        enable: bool,
        charge_current_a: Optional[int] = None,
    ) -> DeyeCompiledCommand:
        """Compile Modbus write actions to enable/disable grid charging and set current limit."""
        actions = [
            DeyeModbusWriteAction(
                register_address=REG_GRID_CHARGE_ENABLE,
                values=[1 if enable else 0],
                function_code=0x06,
                description=f"Set Grid Charge Enable to {'ON' if enable else 'OFF'}",
            )
        ]
        readbacks = [REG_GRID_CHARGE_ENABLE]

        if charge_current_a is not None:
            curr = max(0, min(120, charge_current_a))
            actions.append(
                DeyeModbusWriteAction(
                    register_address=REG_GRID_CHARGE_CURRENT,
                    values=[curr],
                    function_code=0x06,
                    description=f"Set Grid Charge Current limit to {curr} A",
                )
            )
            readbacks.append(REG_GRID_CHARGE_CURRENT)

        return DeyeCompiledCommand(
            command_id=f"deye_grid_charge_{'enable' if enable else 'disable'}",
            command_name="Toggle Grid Charging",
            description=f"Configure AC grid charging: {'ENABLED' if enable else 'DISABLED'}",
            actions=actions,
            readback_registers=readbacks,
            metadata={"enable": enable, "charge_current_a": charge_current_a},
        )

    @staticmethod
    def compile_tou_slot(
        slot_number: int,
        time_str: str,
        power_w: int,
        target_soc: int,
        charge_source: int,
    ) -> DeyeCompiledCommand:
        """Compile programming for a single TOU schedule slot (1..6)."""
        if not (1 <= slot_number <= 6):
            raise ValueError(f"Invalid slot number {slot_number}, must be 1..6")
        if charge_source not in (0, 1, 2, 3):
            raise ValueError(f"Invalid charge source {charge_source}. Must be 0 (Off), 1 (Grid), 2 (Gen), or 3 (Both)")

        idx = slot_number - 1
        time_raw = encode_deye_time(time_str)
        pwr = max(0, min(16000, power_w))
        soc = max(0, min(100, target_soc))

        actions = [
            DeyeModbusWriteAction(
                register_address=REG_TOU_TIME_START + idx,
                values=[time_raw],
                function_code=0x06,
                description=f"Set Slot {slot_number} Time to {time_str} ({time_raw})",
            ),
            DeyeModbusWriteAction(
                register_address=REG_TOU_POWER_START + idx,
                values=[pwr],
                function_code=0x06,
                description=f"Set Slot {slot_number} Power Limit to {pwr} W",
            ),
            DeyeModbusWriteAction(
                register_address=REG_TOU_SOC_START + idx,
                values=[soc],
                function_code=0x06,
                description=f"Set Slot {slot_number} Target SOC to {soc} %",
            ),
            DeyeModbusWriteAction(
                register_address=REG_TOU_CHARGE_SOURCE_START + idx,
                values=[charge_source],
                function_code=0x06,
                description=f"Set Slot {slot_number} Charge Source to {TOU_CHARGE_SOURCE_LABELS[charge_source]}",
            ),
        ]

        readbacks = [
            REG_TOU_TIME_START + idx,
            REG_TOU_POWER_START + idx,
            REG_TOU_SOC_START + idx,
            REG_TOU_CHARGE_SOURCE_START + idx,
        ]

        return DeyeCompiledCommand(
            command_id=f"deye_set_tou_slot_{slot_number}",
            command_name=f"Program Deye TOU Slot {slot_number}",
            description=f"Configure TOU Slot {slot_number}: {time_str} | {pwr} W | {soc} % | {TOU_CHARGE_SOURCE_LABELS[charge_source]}",
            actions=actions,
            readback_registers=readbacks,
            metadata={
                "slot_number": slot_number,
                "time_str": time_str,
                "time_raw": time_raw,
                "power_w": pwr,
                "target_soc": soc,
                "charge_source": charge_source,
            },
        )
