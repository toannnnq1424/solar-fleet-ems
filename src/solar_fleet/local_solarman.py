"""Opt-in, read-only SOLARMAN V5 collection using pysolarmanv5 (MIT).

No discovery, write methods, OEM inference or bundled wildcard register map.
Raw registers are sent to the existing agent outbox as unverified native points.
"""

from __future__ import annotations

import ipaddress
import logging
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import Model, utcnow


class RegisterBlock(Model):
    function: Literal[3, 4]
    address: int = Field(ge=0, le=65535, strict=True)
    count: int = Field(ge=1, le=125, strict=True)

    @model_validator(mode="after")
    def range_valid(self):
        if self.address + self.count > 65536:
            raise ValueError("register range overflow")
        return self


class CollectionProfile(Model):
    agent_id: str = Field(min_length=1, max_length=100)
    device_id: str = Field(min_length=1, max_length=100)
    address: str
    port: int = Field(default=8899, ge=1, le=65535, strict=True)
    logger_serial: int = Field(ge=1, le=4294967295, strict=True)
    unit_id: int = Field(ge=1, le=247, strict=True)
    inverter_model: str = Field(min_length=1, max_length=120)
    inverter_firmware: str = Field(min_length=1, max_length=120)
    logger_model: str = Field(min_length=1, max_length=120)
    logger_firmware: str = Field(min_length=1, max_length=120)
    evidence_reference: str = Field(min_length=1, max_length=500)
    reviewed_by: str = Field(min_length=1, max_length=120)
    blocks: list[RegisterBlock] = Field(min_length=1, max_length=64)

    @field_validator("address")
    @classmethod
    def local_address(cls, value):
        ip = ipaddress.ip_address(value)
        # Explicit RFC1918 IPv4 address avoids DNS rebinding and public WAN loggers.
        if ip.version != 4 or not any(
            ip in ipaddress.ip_network(n) for n in ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16"]
        ):
            raise ValueError("explicit private IPv4 required")
        return str(ip)

    @model_validator(mode="after")
    def bounded(self):
        if sum(b.count for b in self.blocks) > 1000:
            raise ValueError("maximum 1000 registers per collection")
        seen = set()
        for b in self.blocks:
            for address in range(b.address, b.address + b.count):
                key = (b.function, address)
                if key in seen:
                    raise ValueError("overlapping register blocks")
                seen.add(key)
        return self


def collect(profile: CollectionProfile, factory=None):
    if factory is None:
        try:
            from pysolarmanv5 import PySolarmanV5
        except ImportError:
            raise ValueError("install solar-fleet-ems[local-solarman] on the site agent") from None
        factory = PySolarmanV5
    logger = logging.getLogger("solar_fleet.solarman.readonly")
    logger.handlers = [logging.NullHandler()]
    logger.propagate = False
    logger.setLevel(logging.CRITICAL)
    reader = factory(
        profile.address,
        profile.logger_serial,
        port=profile.port,
        mb_slave_id=profile.unit_id,
        socket_timeout=5,
        verbose=False,
        logger=logger,
    )
    points = []
    try:
        for block in profile.blocks:
            method = reader.read_holding_registers if block.function == 3 else reader.read_input_registers
            registers = method(block.address, block.count)
            if (
                not isinstance(registers, list)
                or len(registers) != block.count
                or any(type(v) is not int or not 0 <= v <= 65535 for v in registers)
            ):
                raise ValueError("invalid register response")
            received = utcnow().isoformat()
            points.extend(
                {
                    "device_id": profile.device_id,
                    "key": f"solarman_v5.fc{block.function}.r{block.address + offset}",
                    "value": value,
                    "unit": None,
                    "timestamp": received,
                }
                for offset, value in enumerate(registers)
            )
    finally:
        reader.disconnect()
    return points
