"""Read-only model collection on an explicitly configured local agent.

This transport is deliberately not exposed as a web-server network proxy.
Partial/malformed polls fail before any points enter the durable outbox.
"""

from __future__ import annotations

import ipaddress
import logging
import socket
import struct
import time
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import Model, utcnow
from .model_library import RegisterReading, decode, get_profile, plan


def private_ipv4(value: str) -> str:
    address = ipaddress.ip_address(value)
    if address.version != 4 or not any(
        address in ipaddress.ip_network(network)
        for network in ("10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16")
    ):
        raise ValueError("an explicit RFC1918 IPv4 address is required")
    return str(address)


class ModelCollectionProfile(Model):
    agent_id: str = Field(min_length=1, max_length=100)
    device_id: str = Field(min_length=1, max_length=100)
    profile_id: str
    profile_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    field_ids: list[str] = Field(min_length=1, max_length=100)
    transport: Literal["modbus_tcp", "solarman_v5"]
    address: str
    port: int = Field(strict=True, ge=1, le=65535)
    unit_id: int = Field(strict=True, ge=1, le=247)
    logger_serial: int | None = Field(default=None, strict=True, ge=1, le=0xFFFFFFFF)
    inverter_model: str = Field(min_length=1, max_length=200)
    inverter_firmware: str = Field(min_length=1, max_length=200)
    logger_model: str = Field(min_length=1, max_length=200)
    logger_firmware: str = Field(min_length=1, max_length=200)
    reviewed_by: str = Field(min_length=1, max_length=200)
    evidence_reference: str = Field(min_length=1, max_length=500)
    timeout_seconds: float = Field(default=5, ge=1, le=30, allow_inf_nan=False)
    request_delay_seconds: float = Field(default=0.1, ge=0, le=5, allow_inf_nan=False)
    max_poll_seconds: float = Field(default=60, ge=1, le=120, allow_inf_nan=False)

    _private = field_validator("address")(private_ipv4)

    @model_validator(mode="after")
    def verified_selection(self):
        profile = get_profile(self.profile_id, self.profile_digest)
        plan(profile, self.field_ids)
        selected = [f for f in profile.fields if f.id in self.field_ids]
        if any(f.decode.encoding == "ascii" for f in selected):
            raise ValueError("agent measurements must be numeric; preview identity strings in the inspector")
        if self.transport == "solarman_v5" and self.logger_serial is None:
            raise ValueError("SOLARMAN V5 requires an explicitly reviewed logger serial")
        return self


class ModbusTcpReader:
    """FC03/FC04 only, MBAP correlation and exact response validation.

    Wire contract: Modbus TCP Implementation Guide V1.0b, sections 3.1.3/4.4;
    Application Protocol V1.1b3 sections 6.3/6.4. No writes or discovery scans.
    """

    def __init__(self, profile: ModelCollectionProfile, connector=None):
        connector = connector or socket.create_connection
        self.socket = connector((profile.address, profile.port), timeout=profile.timeout_seconds)
        self.unit = profile.unit_id
        self.timeout = profile.timeout_seconds
        self.transaction = 0

    def _recv(self, size, deadline):
        chunks = bytearray()
        while len(chunks) < size:
            remaining = deadline - time.monotonic()
            if remaining <= 0:
                raise TimeoutError("Modbus response deadline exceeded")
            self.socket.settimeout(remaining)
            part = self.socket.recv(size - len(chunks))
            if not part:
                raise ValueError("truncated Modbus response")
            chunks.extend(part)
        return bytes(chunks)

    def read(self, function, address, count):
        if function not in (3, 4) or not 1 <= count <= 125 or not 0 <= address <= 65536 - count:
            raise ValueError("invalid read request")
        self.transaction = self.transaction % 65535 + 1
        frame = struct.pack(">HHHBBHH", self.transaction, 0, 6, self.unit, function, address, count)
        deadline = time.monotonic() + self.timeout
        self.socket.settimeout(self.timeout)
        self.socket.sendall(frame)
        tx, protocol, length, unit = struct.unpack(">HHHB", self._recv(7, deadline))
        if (tx, protocol, unit) != (self.transaction, 0, self.unit) or not 2 <= length <= 254:
            raise ValueError("Modbus MBAP correlation or length mismatch")
        pdu = self._recv(length - 1, deadline)
        if pdu[0] == function | 0x80:
            if len(pdu) != 2:
                raise ValueError("invalid Modbus exception response")
            raise ValueError(f"Modbus device rejected read (exception {pdu[1]})")
        if len(pdu) != 2 + count * 2 or pdu[0] != function or pdu[1] != count * 2:
            raise ValueError("Modbus function or byte count mismatch")
        return list(struct.unpack(">" + "H" * count, pdu[2:]))

    def close(self):
        self.socket.close()


class SolarmanReader:
    def __init__(self, profile: ModelCollectionProfile):
        from pysolarmanv5 import PySolarmanV5

        logger = logging.getLogger("solar_fleet.local_models.solarman")
        logger.handlers = [logging.NullHandler()]
        logger.propagate = False
        self.client = PySolarmanV5(
            profile.address,
            profile.logger_serial,
            port=profile.port,
            mb_slave_id=profile.unit_id,
            socket_timeout=profile.timeout_seconds,
            verbose=False,
            logger=logger,
        )

    def read(self, function, address, count):
        method = self.client.read_holding_registers if function == 3 else self.client.read_input_registers
        return method(address, count)

    def close(self):
        self.client.disconnect()


def collect_model(config: ModelCollectionProfile, factory=None) -> list[dict]:
    profile = get_profile(config.profile_id, config.profile_digest)
    read_plan = plan(profile, config.field_ids)
    started = time.monotonic()
    timestamp = utcnow().isoformat()  # oldest acquisition time, never manufacture fresh backfill
    factory = factory or (ModbusTcpReader if config.transport == "modbus_tcp" else SolarmanReader)
    reader = factory(config)
    readings = []
    try:
        for index, block in enumerate(read_plan.blocks):
            if index and config.request_delay_seconds:
                time.sleep(config.request_delay_seconds)
            if time.monotonic() - started >= config.max_poll_seconds:
                raise TimeoutError("model poll exceeded freshness budget")
            values = reader.read(block.function, block.address, block.count)
            if not isinstance(values, list) or len(values) != block.count:
                raise ValueError("incomplete model read")
            for offset, value in enumerate(values):
                readings.append(
                    RegisterReading(function=block.function, address=block.address + offset, value=value)
                )
        if time.monotonic() - started > config.max_poll_seconds:
            raise TimeoutError("model poll exceeded freshness budget")
        results = decode(profile, config.field_ids, readings)
        if any(r["quality"] != "UNVERIFIED" or not isinstance(r["value"], (int, float)) for r in results):
            raise ValueError("invalid or missing model values; poll was not queued")
        return [
            {
                "device_id": config.device_id,
                "key": r["native_key"],
                "value": r["value"],
                "unit": r["unit"],
                "timestamp": timestamp,
            }
            for r in results
        ]
    finally:
        reader.close()
