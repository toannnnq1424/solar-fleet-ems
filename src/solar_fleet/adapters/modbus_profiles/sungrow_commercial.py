"""Sungrow Commercial PV String Inverter Modbus Profile (SG110CX / SG125HX).

Official specification reference:
"Communication Protocol of PV Grid-Connected String Inverters" (Sungrow Power Corp.)
Protocol Type: Modbus RTU / Modbus TCP.
Addressing: Protocol Address = Communication Address + 1 (1-based index).
Features:
- 9 MPPT trackers (18 string inputs: voltage 0.1V, current 0.01A)
- Grid-code reactive power control Q(U) and active power derating P(f)
- Insulation resistance & grid frequency monitoring
"""

from __future__ import annotations

import enum
from dataclasses import dataclass
from typing import Any

from .sungrow_registers import SungrowField


class RegisterType(str, enum.Enum):
    U16 = "U16"
    S16 = "S16"
    U32 = "U32"
    S32 = "S32"


@dataclass
class ModbusRegisterDef:
    address: int
    name: str
    unit: str
    scale: float
    reg_type: RegisterType
    description: str


class SungrowCommercialProfile:
    """Decodes multi-MPPT high-power commercial string inverters (SG110CX / SG125HX / SG250HX)."""

    NAME = "sungrow_commercial_sg110cx"
    MODEL = "Sungrow SG110CX Commercial"

    def __init__(self) -> None:
        self.model = "SG110CX"
        self.mppt_count = 9
        self.string_count = 18
        self.is_1_based_indexing = True
        self.rated_power_kw = 110.0

    def to_wire_address(self, protocol_address: int) -> int:
        """Converts Sungrow 1-based protocol address to standard 0-based wire address."""
        return protocol_address - 1

    def to_protocol_address(self, wire_address: int) -> int:
        """Converts standard 0-based wire address to Sungrow 1-based protocol address."""
        return wire_address + 1

    # Input Registers (FC04)
    INPUT_REGISTERS: list[ModbusRegisterDef] = [
        ModbusRegisterDef(5000, "device_state", "", 1.0, RegisterType.U16, "Running state: 0=Stop, 1=Standby, 2=Run, 3=Fault"),
        ModbusRegisterDef(5001, "total_active_power", "kW", 0.01, RegisterType.U16, "Total Active Power (0.01 kW scale)"),
        ModbusRegisterDef(5003, "reactive_power", "kvar", 0.01, RegisterType.S16, "Reactive Power"),
        ModbusRegisterDef(5005, "power_factor", "", 0.001, RegisterType.S16, "Cos Phi Power factor"),
        ModbusRegisterDef(5006, "grid_frequency", "Hz", 0.01, RegisterType.U16, "Grid Frequency"),
    ]

    # Holding Registers (FC03/FC06/FC16) — Writable Grid Code Setpoints
    HOLDING_REGISTERS: list[ModbusRegisterDef] = [
        ModbusRegisterDef(6001, "active_power_derating_kw", "kW", 0.1, RegisterType.U16, "Active power limitation (0.1 kW scale)"),
        ModbusRegisterDef(6002, "reactive_power_mode", "", 1.0, RegisterType.U16, "0: Off, 1: Q(U), 2: CosPhi, 3: Q-Fixed"),
    ]

    def decode_telemetry(self, raw_registers: dict[int, int]) -> dict[str, Any]:
        """Decodes raw registers mapping into normalized engineering values."""
        state_code = raw_registers.get(5000, 0)
        state_map = {0: "STOP", 1: "STANDBY", 2: "RUN", 3: "FAULT"}

        total_kw = raw_registers.get(5001, 0) * 0.01
        freq = raw_registers.get(5006, 5000) * 0.01
        cos_phi = raw_registers.get(5005, 1000) * 0.001

        mppts_data = {}
        for m in range(1, 10):
            v_reg = 5010 + (m - 1) * 2
            i_reg = 5011 + (m - 1) * 2
            v_val = raw_registers.get(v_reg, 0) * 0.1
            i_val = raw_registers.get(i_reg, 0) * 0.1
            mppts_data[m] = {
                "voltage_v": round(v_val, 1),
                "current_a": round(i_val, 1),
                "power_w": round(v_val * i_val, 1),
            }

        return {
            "device_state": state_map.get(state_code, "UNKNOWN"),
            "total_active_power_kw": round(total_kw, 2),
            "grid_frequency_hz": round(freq, 2),
            "power_factor": round(cos_phi, 3),
            "mppts": mppts_data,
        }

    def build_active_power_command(self, power_kw: float) -> dict[str, Any]:
        """Constructs an active power setpoint command with strict physical limit checks."""
        if power_kw < 0.0 or power_kw > self.rated_power_kw:
            raise ValueError(
                f"Active power {power_kw} kW outside safe commercial rating (0..{self.rated_power_kw} kW)"
            )
        reg_protocol = 6001
        reg_wire = self.to_wire_address(reg_protocol)
        scaled_val = int(round(power_kw * 10))  # 0.1 kW unit
        return {
            "register": reg_protocol,
            "wire_register": reg_wire,
            "value": scaled_val,
            "unit": "kW",
            "scale": 0.1,
        }

    @classmethod
    def decode_input_block(cls, start_addr: int, raw_words: list[int]) -> dict[str, Any]:
        result = {}
        for reg in cls.INPUT_REGISTERS:
            idx = reg.address - start_addr
            if idx < 0:
                continue
            if reg.reg_type in (RegisterType.U16, RegisterType.S16):
                if idx < len(raw_words):
                    val = raw_words[idx]
                    if reg.reg_type == RegisterType.S16 and val >= 0x8000:
                        val -= 0x10000
                    result[reg.name] = round(val * reg.scale, 3)
            elif reg.reg_type == RegisterType.U32:
                if idx + 1 < len(raw_words):
                    val = (raw_words[idx] << 16) | raw_words[idx + 1]
                    result[reg.name] = round(val * reg.scale, 3)
        return result


# ---------------------------------------------------------------------------
# Canonical Sungrow Commercial Register Field Definitions (0-based wire address)
# ---------------------------------------------------------------------------
SUNGROW_COMMERCIAL_REGISTERS: list[SungrowField] = [
    # Status & Power (Protocol 5000-5006 -> Wire 4999-5005)
    SungrowField("input", 4999, "uint16", 1.0,   "",     "inverter_status", "Running state: 0=Stop, 1=Standby, 2=Run, 3=Fault"),
    SungrowField("input", 5000, "uint16", 10.0,  "W",    "active_power",    "Total Active Power"),
    SungrowField("input", 5002, "int16",  10.0,  "var",  "reactive_power",  "Reactive Power"),
    SungrowField("input", 5004, "int16",  0.001, "",     "power_factor",    "Cos Phi Power factor"),
    SungrowField("input", 5005, "uint16", 0.01,  "Hz",   "grid_frequency",  "Grid Frequency"),
    # 9 MPPT string inputs (Protocol 5010-5027 -> Wire 5009-5026)
    SungrowField("input", 5009, "uint16", 0.1,   "V",    "pv1_voltage",     "MPPT1 Voltage"),
    SungrowField("input", 5010, "uint16", 0.1,   "A",    "pv1_current",     "MPPT1 Current"),
    SungrowField("input", 5011, "uint16", 0.1,   "V",    "pv2_voltage",     "MPPT2 Voltage"),
    SungrowField("input", 5012, "uint16", 0.1,   "A",    "pv2_current",     "MPPT2 Current"),
    SungrowField("input", 5013, "uint16", 0.1,   "V",    "pv3_voltage",     "MPPT3 Voltage"),
    SungrowField("input", 5014, "uint16", 0.1,   "A",    "pv3_current",     "MPPT3 Current"),
    SungrowField("input", 5015, "uint16", 0.1,   "V",    "pv4_voltage",     "MPPT4 Voltage"),
    SungrowField("input", 5016, "uint16", 0.1,   "A",    "pv4_current",     "MPPT4 Current"),
    SungrowField("input", 5017, "uint16", 0.1,   "V",    "pv5_voltage",     "MPPT5 Voltage"),
    SungrowField("input", 5018, "uint16", 0.1,   "A",    "pv5_current",     "MPPT5 Current"),
    SungrowField("input", 5019, "uint16", 0.1,   "V",    "pv6_voltage",     "MPPT6 Voltage"),
    SungrowField("input", 5020, "uint16", 0.1,   "A",    "pv6_current",     "MPPT6 Current"),
    SungrowField("input", 5021, "uint16", 0.1,   "V",    "pv7_voltage",     "MPPT7 Voltage"),
    SungrowField("input", 5022, "uint16", 0.1,   "A",    "pv7_current",     "MPPT7 Current"),
    SungrowField("input", 5023, "uint16", 0.1,   "V",    "pv8_voltage",     "MPPT8 Voltage"),
    SungrowField("input", 5024, "uint16", 0.1,   "A",    "pv8_current",     "MPPT8 Current"),
    SungrowField("input", 5025, "uint16", 0.1,   "V",    "pv9_voltage",     "MPPT9 Voltage"),
    SungrowField("input", 5026, "uint16", 0.1,   "A",    "pv9_current",     "MPPT9 Current"),
    # Holding registers for control
    SungrowField("holding", 6000, "uint16", 0.1, "kW",   "active_power_derating_kw", "Active power derating setpoint"),
    SungrowField("holding", 6001, "uint16", 1.0, "",     "reactive_power_mode",      "Reactive power mode"),
]


def decode_commercial_raw_registers(
    raw: dict[str, int],
    series: str = "",
) -> dict[str, tuple[float | None, str]]:
    """Decode raw registers for Sungrow Commercial inverters (SG110CX/SG125HX/SG250HX).

    Transparently supports both 0-based wire address keys and 1-based protocol address keys.
    """
    result: dict[str, tuple[float | None, str]] = {}
    pv_power_total = 0.0
    has_pv_power = False

    is_protocol_indexed = ("4999" not in raw and 4999 not in raw and ("5001" in raw or 5001 in raw))

    for f in SUNGROW_COMMERCIAL_REGISTERS:
        target_addr = (f.address + 1) if is_protocol_indexed else f.address
        addr_str = str(target_addr)
        raw_val = raw.get(addr_str)
        if raw_val is None:
            raw_val = raw.get(target_addr)
        if raw_val is None:
            continue

        if f.data_type == "uint16":
            value = float(raw_val & 0xFFFF) * f.scale
        elif f.data_type == "int16":
            signed = raw_val if raw_val < 0x8000 else raw_val - 0x10000
            value = float(signed) * f.scale
        elif f.data_type == "uint32":
            low_addr = target_addr + 1
            low_val = raw.get(str(low_addr))
            if low_val is None:
                low_val = raw.get(low_addr)
            if low_val is None:
                continue
            combined = (raw_val << 16) | (low_val & 0xFFFF)
            value = float(combined) * f.scale
        elif f.data_type == "int32":
            low_addr = target_addr + 1
            low_val = raw.get(str(low_addr))
            if low_val is None:
                low_val = raw.get(low_addr)
            if low_val is None:
                continue
            combined = (raw_val << 16) | (low_val & 0xFFFF)
            if combined >= 0x80000000:
                combined -= 0x100000000
            value = float(combined) * f.scale
        else:
            continue

        result[f.metric] = (round(value, 3), f.unit)

    # Calculate MPPT aggregate DC power if MPPT voltages and currents are present
    for m in range(1, 10):
        v_key = f"pv{m}_voltage"
        i_key = f"pv{m}_current"
        if v_key in result and i_key in result:
            v_val = result[v_key][0]
            i_val = result[i_key][0]
            if v_val is not None and i_val is not None:
                pv_power_total += v_val * i_val
                has_pv_power = True

    if has_pv_power and "pv_power" not in result:
        result["pv_power"] = (round(pv_power_total, 1), "W")

    return result
