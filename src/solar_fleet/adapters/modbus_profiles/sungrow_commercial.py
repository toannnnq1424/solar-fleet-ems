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
