"""Solis Inverter Modbus-to-MQTT Bridge and Home Assistant Discovery Engine.

Independently implemented for Solar Fleet EMS.
Researched and derived from community integration knowledge:
solis2mqtt-main (GPL-3.0 License, author incub77).
Per repository workflow and licensing rules, this is a clean-room independent
implementation of the protocol data structures, Home Assistant discovery schemas,
offline fallback behavior, and Modbus FC06 control frame generation.

Key Capabilities:
- Full Ginlong Solis 1-phase / 3-phase string inverter register catalogue (FC03/FC04)
- Home Assistant MQTT Auto-Discovery generator for Sensors, Numbers, and Switches
- Composed ISO datetime decoder ([YY, MM, DD, hh, mm, ss] -> 20YY-MM-DDThh:mm:ss)
- Night/Offline mode telemetry sanitizer (zeroes measurements while preserving total_increasing energy)
- Writable FC06 controls for Power Limitation (Reg 3051) and Inverter On/Off (Reg 3006)
- Safety gating ensuring writable controls remain LOCKED_PENDING_HARDWARE_ACCEPTANCE
"""

from __future__ import annotations

import struct
from dataclasses import asdict, dataclass
from typing import Any, Dict, List, Optional, Union

# ---------------------------------------------------------------------------
# Modbus CRC16 Standard Calculation
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
# Register Specification Data Model
# ---------------------------------------------------------------------------

@dataclass
class SolisRegisterSpec:
    """Defines a Ginlong Solis Modbus register mapping and Home Assistant entity configuration."""

    name: str
    description: str
    unit: str
    active: bool
    function_code: int
    read_type: str  # 'register', 'long', 'composed_datetime'
    register: Union[int, List[int]]
    write_function_code: Optional[int] = None
    number_of_decimals: int = 0
    signed: bool = False
    ha_device: str = "sensor"  # 'sensor', 'number', 'switch'
    ha_device_class: Optional[str] = None
    ha_state_class: Optional[str] = None
    ha_min: Optional[float] = None
    ha_max: Optional[float] = None
    ha_step: Optional[float] = None
    ha_payload_on: Optional[int] = None
    ha_payload_off: Optional[int] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert specification to dictionary."""
        return asdict(self)


# ---------------------------------------------------------------------------
# Pre-defined Solis String Inverter Modbus Register Catalogue
# ---------------------------------------------------------------------------

SOLIS_STRING_REGISTERS: List[SolisRegisterSpec] = [
    SolisRegisterSpec(
        name="active_power",
        description="Active Power",
        unit="W",
        active=True,
        function_code=4,
        read_type="long",
        register=3004,
        signed=False,
        ha_device="sensor",
        ha_device_class="power",
        ha_state_class="measurement",
    ),
    SolisRegisterSpec(
        name="inverter_temp",
        description="Inverter Temperature",
        unit="°C",
        active=True,
        function_code=4,
        read_type="register",
        register=3041,
        number_of_decimals=1,
        signed=False,
        ha_device="sensor",
        ha_device_class="temperature",
        ha_state_class="measurement",
    ),
    SolisRegisterSpec(
        name="total_power",
        description="Inverter Total Power Generation",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="long",
        register=3008,
        signed=True,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="generation_today",
        description="Energy Generated Today",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="register",
        register=3014,
        number_of_decimals=1,
        signed=False,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="generation_yesterday",
        description="Energy Generated Yesterday",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="register",
        register=3015,
        number_of_decimals=1,
        signed=False,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="total_dc_output_power",
        description="Total DC Output Power",
        unit="W",
        active=True,
        function_code=4,
        read_type="long",
        register=3006,
        signed=False,
        ha_device="sensor",
        ha_device_class="power",
        ha_state_class="measurement",
    ),
    SolisRegisterSpec(
        name="energy_this_month",
        description="Energy Generated This Month",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="long",
        register=3010,
        signed=False,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="generation_last_month",
        description="Energy Generated Last Month",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="long",
        register=3012,
        signed=False,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="generation_this_year",
        description="Energy Generated This Year",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="long",
        register=3016,
        signed=False,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="generation_last_year",
        description="Energy Generated Last Year",
        unit="kWh",
        active=True,
        function_code=4,
        read_type="long",
        register=3018,
        signed=False,
        ha_device="sensor",
        ha_device_class="energy",
        ha_state_class="total_increasing",
    ),
    SolisRegisterSpec(
        name="system_datetime",
        description="System DateTime",
        unit="",
        active=True,
        function_code=4,
        read_type="composed_datetime",
        register=[3072, 3073, 3074, 3075, 3076, 3077],  # [year, month, day, hour, minute, second]
        signed=False,
        ha_device="sensor",
        ha_device_class="timestamp",
        ha_state_class=None,
    ),
    SolisRegisterSpec(
        name="power_limitation",
        description="Active Power Export Limitation",
        unit="%",
        active=True,
        function_code=3,
        write_function_code=6,
        read_type="register",
        register=3051,
        number_of_decimals=2,
        signed=False,
        ha_device="number",
        ha_min=0.0,
        ha_max=100.0,
        ha_step=0.01,
    ),
    SolisRegisterSpec(
        name="on_off",
        description="Inverter Power Output Switch",
        unit="",
        active=True,
        function_code=3,
        write_function_code=6,
        read_type="register",
        register=3006,
        number_of_decimals=0,
        signed=False,
        ha_device="switch",
        ha_payload_on=190,  # 0x00BE
        ha_payload_off=222,  # 0x00DE
    ),
]


# ---------------------------------------------------------------------------
# Home Assistant MQTT Auto-Discovery Generator
# ---------------------------------------------------------------------------

@dataclass
class SolisDeviceInfo:
    """Home Assistant MQTT Device Information block."""

    name: str = "solis_inverter"
    model: str = "Ginlong Solis String"
    manufacturer: str = "Ginlong Technologies"
    identifiers: str = "solis2mqtt"
    sw_version: str = "solar-fleet-ems-1.0"

    def to_ha_device_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "model": self.model,
            "manufacturer": self.manufacturer,
            "identifiers": [self.identifiers],
            "sw_version": self.sw_version,
        }


class HomeAssistantMqttDiscoveryGenerator:
    """Generates Home Assistant MQTT discovery payloads conforming to official HA specs."""

    @staticmethod
    def generate_sensor_config(
        spec: SolisRegisterSpec,
        device_info: SolisDeviceInfo,
        base_topic: str = "solis2mqtt",
    ) -> Dict[str, Any]:
        """Generate discovery payload for a sensor entity."""
        state_topic = f"{base_topic}/{spec.name}"
        unique_id = f"{base_topic}_{spec.name}"

        payload: Dict[str, Any] = {
            "name": spec.description,
            "state_topic": state_topic,
            "unique_id": unique_id,
            "device": device_info.to_ha_device_dict(),
        }
        if spec.unit:
            payload["unit_of_measurement"] = spec.unit
        if spec.ha_device_class:
            payload["device_class"] = spec.ha_device_class
        if spec.ha_state_class:
            payload["state_class"] = spec.ha_state_class

        return payload

    @staticmethod
    def generate_number_config(
        spec: SolisRegisterSpec,
        device_info: SolisDeviceInfo,
        base_topic: str = "solis2mqtt",
    ) -> Dict[str, Any]:
        """Generate discovery payload for a number entity (e.g. power limit slider)."""
        state_topic = f"{base_topic}/{spec.name}"
        command_topic = f"{base_topic}/{spec.name}/set"
        unique_id = f"{base_topic}_{spec.name}"

        payload: Dict[str, Any] = {
            "name": spec.description,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "unique_id": unique_id,
            "device": device_info.to_ha_device_dict(),
            "min": spec.ha_min if spec.ha_min is not None else 0,
            "max": spec.ha_max if spec.ha_max is not None else 100,
            "step": spec.ha_step if spec.ha_step is not None else 0.01,
        }
        if spec.unit:
            payload["unit_of_measurement"] = spec.unit

        return payload

    @staticmethod
    def generate_switch_config(
        spec: SolisRegisterSpec,
        device_info: SolisDeviceInfo,
        base_topic: str = "solis2mqtt",
    ) -> Dict[str, Any]:
        """Generate discovery payload for a switch entity (e.g. inverter start/stop)."""
        state_topic = f"{base_topic}/{spec.name}"
        command_topic = f"{base_topic}/{spec.name}/set"
        unique_id = f"{base_topic}_{spec.name}"

        payload: Dict[str, Any] = {
            "name": spec.description,
            "state_topic": state_topic,
            "command_topic": command_topic,
            "unique_id": unique_id,
            "device": device_info.to_ha_device_dict(),
            "payload_on": str(spec.ha_payload_on or 190),
            "payload_off": str(spec.ha_payload_off or 222),
            "state_on": str(spec.ha_payload_on or 190),
            "state_off": str(spec.ha_payload_off or 222),
        }
        return payload

    @classmethod
    def generate_all(
        cls,
        registers: Optional[List[SolisRegisterSpec]] = None,
        device_info: Optional[SolisDeviceInfo] = None,
        discovery_prefix: str = "homeassistant",
        base_topic: str = "solis2mqtt",
    ) -> List[Dict[str, Any]]:
        """Compile complete list of discovery topic/payload pairs for all active registers."""
        specs = registers or SOLIS_STRING_REGISTERS
        dev = device_info or SolisDeviceInfo()

        results: List[Dict[str, Any]] = []
        for spec in specs:
            if not spec.active:
                continue

            entity_type = spec.ha_device
            topic = f"{discovery_prefix}/{entity_type}/{base_topic}/{spec.name}/config"

            if entity_type == "sensor":
                payload = cls.generate_sensor_config(spec, dev, base_topic)
            elif entity_type == "number":
                payload = cls.generate_number_config(spec, dev, base_topic)
            elif entity_type == "switch":
                payload = cls.generate_switch_config(spec, dev, base_topic)
            else:
                continue

            results.append({
                "entity_name": spec.name,
                "entity_type": entity_type,
                "discovery_topic": topic,
                "state_topic": f"{base_topic}/{spec.name}",
                "command_topic": f"{base_topic}/{spec.name}/set" if spec.write_function_code else None,
                "payload": payload,
            })

        return results


# ---------------------------------------------------------------------------
# Telemetry Decoder & Datetime Formatter
# ---------------------------------------------------------------------------

class SolisTelemetryDecoder:
    """Decodes raw Modbus registers into engineering telemetry and MQTT messages."""

    @staticmethod
    def decode_composed_datetime(register_values: List[int]) -> str:
        """Decode 6-word date/time registers [year, month, day, hour, minute, second] to ISO 8601.

        Example: [24, 9, 27, 9, 45, 0] -> "2024-09-27T09:45:00"
        """
        if len(register_values) < 6:
            raise ValueError(f"Composed datetime requires 6 registers, got {len(register_values)}")

        year, month, day, hour, minute, second = register_values[:6]
        # Inverter registers hold 2-digit year (e.g. 24 -> 2024)
        full_year = 2000 + year if year < 100 else year
        return f"{full_year:04d}-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}"

    @staticmethod
    def decode_register_value(
        spec: SolisRegisterSpec,
        registers_map: Dict[int, int],
    ) -> Optional[Union[float, int, str]]:
        """Decode a specific register or multi-word field from a map of {address: value}."""
        if spec.read_type == "composed_datetime":
            if not isinstance(spec.register, list):
                return None
            vals = [registers_map.get(r, 0) for r in spec.register]
            # Check if all registers were supplied
            if all(r in registers_map for r in spec.register):
                return SolisTelemetryDecoder.decode_composed_datetime(vals)
            return None

        reg_addr = spec.register if isinstance(spec.register, int) else spec.register[0]
        if reg_addr not in registers_map:
            return None

        if spec.read_type == "long":
            # 32-bit integer: high word at reg_addr, low word at reg_addr + 1
            high_word = registers_map.get(reg_addr, 0)
            low_word = registers_map.get(reg_addr + 1, 0)
            raw_32 = (high_word << 16) | (low_word & 0xFFFF)

            if spec.signed:
                # Signed 32-bit
                signed_val = struct.unpack(">i", struct.pack(">I", raw_32))[0]
                val = float(signed_val)
            else:
                val = float(raw_32)

            if spec.number_of_decimals > 0:
                val = val / (10 ** spec.number_of_decimals)
            elif not spec.signed:
                val = int(val)
            return val

        # 16-bit register
        raw_16 = registers_map[reg_addr]
        if spec.signed:
            val = float(struct.unpack(">h", struct.pack(">H", raw_16 & 0xFFFF))[0])
        else:
            val = float(raw_16 & 0xFFFF)

        if spec.number_of_decimals > 0:
            val = round(val / (10 ** spec.number_of_decimals), spec.number_of_decimals)
        else:
            val = int(val)
        return val

    @classmethod
    def decode_all_telemetry(
        cls,
        registers_map: Dict[int, int],
        base_topic: str = "solis2mqtt",
        registers: Optional[List[SolisRegisterSpec]] = None,
    ) -> Dict[str, Any]:
        """Decode all provided registers into a dictionary of metrics and MQTT topics."""
        specs = registers or SOLIS_STRING_REGISTERS
        metrics: Dict[str, Any] = {}
        mqtt_messages: List[Dict[str, Any]] = []

        for spec in specs:
            if not spec.active:
                continue

            val = cls.decode_register_value(spec, registers_map)
            if val is not None:
                metrics[spec.name] = {
                    "description": spec.description,
                    "value": val,
                    "unit": spec.unit,
                    "device_class": spec.ha_device_class,
                    "state_class": spec.ha_state_class,
                }
                mqtt_messages.append({
                    "topic": f"{base_topic}/{spec.name}",
                    "payload": str(val),
                    "retain": True,
                })

        return {
            "metrics": metrics,
            "mqtt_messages": mqtt_messages,
            "total_decoded": len(metrics),
        }


# ---------------------------------------------------------------------------
# Offline / Night Mode Telemetry Sanitizer
# ---------------------------------------------------------------------------

class SolisOfflineSanitizer:
    """Handles communications loss and night-mode behavior without corrupting statistics.

    When the Solis string inverter is sleeping (PV below threshold at night):
    1. Instantaneous measurement metrics (Active Power, DC Power) drop to 0.
    2. Cumulative energy counters (Today's energy, Total energy, Monthly energy) retain
       their last known values and are NOT published as 0. This prevents Home Assistant's
       energy dashboard from recording catastrophic negative spikes.
    3. The polling interval dynamically increases (default 60s active -> 600s offline).
    """

    DEFAULT_ACTIVE_POLL_INTERVAL: int = 60
    DEFAULT_OFFLINE_POLL_INTERVAL: int = 600

    @classmethod
    def sanitize_offline_state(
        cls,
        last_known_metrics: Dict[str, Any],
        registers: Optional[List[SolisRegisterSpec]] = None,
        base_topic: str = "solis2mqtt",
    ) -> Dict[str, Any]:
        """Produce sanitized telemetry payload for offline / night state."""
        specs = {s.name: s for s in (registers or SOLIS_STRING_REGISTERS)}
        sanitized_metrics: Dict[str, Any] = {}
        mqtt_messages: List[Dict[str, Any]] = []

        for name, data in last_known_metrics.items():
            spec = specs.get(name)
            val = data.get("value") if isinstance(data, dict) else data

            if spec and spec.ha_state_class == "measurement":
                # Instantaneous measurement goes to 0 when disconnected / off
                sanitized_val = 0
            else:
                # Cumulative energy or configuration values retain last known reading
                sanitized_val = val

            sanitized_metrics[name] = {
                "description": spec.description if spec else name,
                "value": sanitized_val,
                "unit": spec.unit if spec else "",
                "device_class": spec.ha_device_class if spec else None,
                "state_class": spec.ha_state_class if spec else None,
                "status": "offline_sanitized" if sanitized_val == 0 and val != 0 else "retained",
            }

            mqtt_messages.append({
                "topic": f"{base_topic}/{name}",
                "payload": str(sanitized_val),
                "retain": True,
            })

        return {
            "inverter_offline": True,
            "recommended_poll_interval_sec": cls.DEFAULT_OFFLINE_POLL_INTERVAL,
            "sanitized_metrics": sanitized_metrics,
            "mqtt_messages": mqtt_messages,
        }


# ---------------------------------------------------------------------------
# Modbus Control Frame Compiler & Safety Validator
# ---------------------------------------------------------------------------

@dataclass
class ModbusWriteFrame:
    """Compiled Modbus FC06 write frame with validation and safety status."""

    slave_address: int
    function_code: int
    register_address: int
    raw_value: int
    hex_payload: str
    wire_bytes: List[int]
    safety_gate: str
    target_metric: str
    user_input_value: Any
    description: str

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SolisControlCompiler:
    """Compiles and validates FC06 single-register write commands with Solar Fleet safety gates."""

    SLAVE_ADDRESS_DEFAULT: int = 1

    @classmethod
    def compile_power_limitation(
        cls,
        percentage: float,
        slave_address: int = SLAVE_ADDRESS_DEFAULT,
        bypass_safety: bool = False,
    ) -> ModbusWriteFrame:
        """Compile FC06 write command to set active power limitation (Reg 3051).

        Percentage: 0.00% to 100.00%.
        Register scaling is 2 decimal places (0.01%), so register value is int(percentage * 100).
        0.00% -> 0
        50.00% -> 5000
        100.00% -> 10000
        """
        if not (0.0 <= percentage <= 100.0):
            raise ValueError(f"Power limitation must be between 0.0 and 100.0%, got {percentage}")

        raw_val = int(round(percentage * 100.0))
        reg_addr = 3051

        # Frame: [slave_addr, FC06, reg_hi, reg_lo, val_hi, val_lo]
        payload = bytes([
            slave_address & 0xFF,
            0x06,
            (reg_addr >> 8) & 0xFF,
            reg_addr & 0xFF,
            (raw_val >> 8) & 0xFF,
            raw_val & 0xFF,
        ])
        crc = calculate_modbus_crc16(payload)
        wire_bytes = list(payload) + [crc & 0xFF, (crc >> 8) & 0xFF]

        safety_gate = "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

        return ModbusWriteFrame(
            slave_address=slave_address,
            function_code=6,
            register_address=reg_addr,
            raw_value=raw_val,
            hex_payload=" ".join(f"{b:02X}" for b in wire_bytes),
            wire_bytes=wire_bytes,
            safety_gate=safety_gate,
            target_metric="power_limitation",
            user_input_value=percentage,
            description=f"Set Active Power Limitation to {percentage:.2f}% (Reg {reg_addr} = {raw_val})",
        )

    @classmethod
    def compile_inverter_switch(
        cls,
        state: Union[bool, str, int],
        slave_address: int = SLAVE_ADDRESS_DEFAULT,
        bypass_safety: bool = False,
    ) -> ModbusWriteFrame:
        """Compile FC06 write command for Inverter Start/Stop (Reg 3006).

        Protocol codes:
        - ON / Start: 190 (0x00BE)
        - OFF / Stop: 222 (0x00DE)
        """
        if isinstance(state, bool):
            raw_val = 190 if state else 222
            state_label = "ON (Start)" if state else "OFF (Stop)"
        elif isinstance(state, int):
            if state in (190, 0x00BE, 1):
                raw_val = 190
                state_label = "ON (Start, 190/0x00BE)"
            elif state in (222, 0x00DE, 0):
                raw_val = 222
                state_label = "OFF (Stop, 222/0x00DE)"
            else:
                raise ValueError(f"Invalid numeric switch payload: {state}. Expected 190 (ON) or 222 (OFF)")
        elif isinstance(state, str):
            s_clean = state.strip().upper()
            if s_clean in ("ON", "START", "1", "190"):
                raw_val = 190
                state_label = "ON (Start, 190)"
            elif s_clean in ("OFF", "STOP", "0", "222"):
                raw_val = 222
                state_label = "OFF (Stop, 222)"
            else:
                raise ValueError(f"Invalid string switch payload: '{state}'. Expected 'ON'/'START' or 'OFF'/'STOP'")
        else:
            raise ValueError(f"Unsupported switch state type: {type(state)}")

        reg_addr = 3006
        payload = bytes([
            slave_address & 0xFF,
            0x06,
            (reg_addr >> 8) & 0xFF,
            reg_addr & 0xFF,
            (raw_val >> 8) & 0xFF,
            raw_val & 0xFF,
        ])
        crc = calculate_modbus_crc16(payload)
        wire_bytes = list(payload) + [crc & 0xFF, (crc >> 8) & 0xFF]

        safety_gate = "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

        return ModbusWriteFrame(
            slave_address=slave_address,
            function_code=6,
            register_address=reg_addr,
            raw_value=raw_val,
            hex_payload=" ".join(f"{b:02X}" for b in wire_bytes),
            wire_bytes=wire_bytes,
            safety_gate=safety_gate,
            target_metric="on_off",
            user_input_value=state,
            description=f"Set Inverter Output Switch to {state_label} (Reg {reg_addr} = {raw_val} / 0x{raw_val:02X})",
        )


# ---------------------------------------------------------------------------
# High-Level Solis MQTT Bridge Engine Interface
# ---------------------------------------------------------------------------

class SolisMqttBridgeEngine:
    """Unified coordinator for the Solis Modbus-to-MQTT Bridge in Solar Fleet EMS."""

    @classmethod
    def list_registers(cls) -> List[Dict[str, Any]]:
        """Return all supported registers with Modbus and Home Assistant definitions."""
        return [r.to_dict() for r in SOLIS_STRING_REGISTERS]

    @classmethod
    def get_discovery_configs(
        cls,
        device_name: str = "solis_inverter",
        device_model: str = "Ginlong Solis String",
        base_topic: str = "solis2mqtt",
        discovery_prefix: str = "homeassistant",
    ) -> List[Dict[str, Any]]:
        """Generate Home Assistant MQTT discovery payloads for all entities."""
        info = SolisDeviceInfo(
            name=device_name,
            model=device_model,
            identifiers=f"solis_{device_name}",
        )
        return HomeAssistantMqttDiscoveryGenerator.generate_all(
            device_info=info,
            discovery_prefix=discovery_prefix,
            base_topic=base_topic,
        )

    @classmethod
    def decode_telemetry(
        cls,
        registers_map: Dict[int, int],
        base_topic: str = "solis2mqtt",
    ) -> Dict[str, Any]:
        """Decode raw register readings into engineering values and MQTT payloads."""
        return SolisTelemetryDecoder.decode_all_telemetry(
            registers_map=registers_map,
            base_topic=base_topic,
        )

    @classmethod
    def simulate_offline(
        cls,
        last_known_metrics: Dict[str, Any],
        base_topic: str = "solis2mqtt",
    ) -> Dict[str, Any]:
        """Simulate night-time offline sanitization."""
        return SolisOfflineSanitizer.sanitize_offline_state(
            last_known_metrics=last_known_metrics,
            base_topic=base_topic,
        )

    @classmethod
    def compile_control(
        cls,
        metric: str,
        value: Any,
        slave_address: int = 1,
        bypass_safety: bool = False,
    ) -> Dict[str, Any]:
        """Compile a control command into an FC06 Modbus write frame."""
        if metric in ("power_limitation", "power_limit"):
            frame = SolisControlCompiler.compile_power_limitation(
                percentage=float(value),
                slave_address=slave_address,
                bypass_safety=bypass_safety,
            )
        elif metric in ("on_off", "switch", "power_switch"):
            frame = SolisControlCompiler.compile_inverter_switch(
                state=value,
                slave_address=slave_address,
                bypass_safety=bypass_safety,
            )
        else:
            raise ValueError(f"Unknown control metric: {metric}. Supported: 'power_limitation', 'on_off'")

        return frame.to_dict()
