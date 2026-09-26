"""Versioned community model candidates, independent of commissioned control profiles.

Plans operate on explicit (function, address) pairs. They never infer a transport,
canonical metric or write capability from a brand. Catalog data is licensed source
material; decoding and planning here are application code.
"""

from __future__ import annotations

import hashlib
import json
import math
import struct
from functools import lru_cache
from importlib.resources import files
from typing import Literal

from pydantic import Field, model_validator

from .domain import Model
from .local_solarman import RegisterBlock


class DecodeSpec(Model):
    function: Literal[3, 4]
    registers: list[int] = Field(min_length=1, max_length=64)
    encoding: Literal["unsigned", "signed", "magnitude", "ascii", "float32"] = "unsigned"
    word_order: Literal["big", "little"] = "big"
    scale: float = 1
    offset: float = 0
    post_offset: float = 0
    floor_divisor: float | None = None
    negate: bool = False
    mask: int | None = None
    bit: int | None = None
    raw_min: float | None = None
    raw_max: float | None = None
    minimum: float | None = None
    maximum: float | None = None

    @model_validator(mode="after")
    def valid(self):
        if any(type(r) is not int or not 0 <= r <= 65535 for r in self.registers):
            raise ValueError("register must be an unsigned 16-bit address")
        if len(set(self.registers)) != len(self.registers):
            raise ValueError("duplicate address within field")
        if self.encoding != "ascii" and len(self.registers) > 4:
            raise ValueError("numeric values wider than 64 bits are not supported")
        if self.encoding == "float32" and len(self.registers) != 2:
            raise ValueError("float32 needs exactly two registers")
        for value in (
            self.scale,
            self.offset,
            self.post_offset,
            self.floor_divisor,
            self.raw_min,
            self.raw_max,
            self.minimum,
            self.maximum,
        ):
            if value is not None and not math.isfinite(value):
                raise ValueError("non-finite transform")
        if self.floor_divisor is not None and self.floor_divisor <= 0:
            raise ValueError("divisor must be positive")
        if self.mask is not None and not 0 <= self.mask < 1 << (16 * len(self.registers)):
            raise ValueError("invalid mask")
        if self.bit is not None and not 0 <= self.bit < 16 * len(self.registers):
            raise ValueError("invalid bit")
        return self


class ModelField(Model):
    id: str = Field(pattern=r"^[a-z0-9_]{1,64}$")
    name: str
    unit: str | None = None
    group: str = "Measurements"
    decode: DecodeSpec | None = None
    blocked_reason: str | None = None
    # Native definitions retain conditional and writable fields for research;
    # they are never evaluated, executed or passed to a write method.
    native: dict = Field(default_factory=dict)


class ModelProfile(Model):
    id: str = Field(pattern=r"^[a-z0-9_-]+$")
    name: str
    manufacturer: str
    models: list[str]
    source_id: str
    source_path: str
    source_sha256: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_revision: str = Field(pattern=r"^[a-f0-9]{40}$")
    profile_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    source_url: str
    license: str
    transport_hint: str
    unit_id_hint: int | None = None
    max_block_size: int = Field(default=60, ge=1, le=125)
    fields: list[ModelField]
    limitations: list[str]

    @model_validator(mode="after")
    def unique_fields(self):
        if len({f.id for f in self.fields}) != len(self.fields):
            raise ValueError("duplicate model field")
        return self


def profile_hash(profile: dict) -> str:
    return hashlib.sha256(
        json.dumps(
            {k: v for k, v in profile.items() if k != "profile_digest"},
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        ).encode()
    ).hexdigest()


@lru_cache(maxsize=1)
def _catalog() -> dict[str, ModelProfile]:
    payload = json.loads(files("solar_fleet").joinpath("data/model-library.json").read_text("utf-8"))
    profiles = {}
    for row in payload["profiles"]:
        if profile_hash(row) != row["profile_digest"]:
            raise ValueError("catalog profile digest mismatch")
        profile = ModelProfile.model_validate(row)
        if profile.id in profiles:
            raise ValueError("duplicate catalog profile")
        profiles[profile.id] = profile
    return profiles


def profiles() -> list[ModelProfile]:
    return [p.model_copy(deep=True) for p in _catalog().values()]


def get_profile(profile_id: str, digest: str | None = None) -> ModelProfile:
    profile = _catalog().get(profile_id)
    if profile is None:
        raise ValueError("unknown model profile")
    if digest is not None and profile.profile_digest != digest:
        raise ValueError("model profile changed; review the new definition")
    return profile.model_copy(deep=True)


def native_label(metric: str) -> str | None:
    prefix = "agent.native.model."
    if not metric.startswith(prefix):
        return None
    pieces = metric[len(prefix) :].split(".", 1)
    if len(pieces) != 2:
        return None
    matches = [p for p in _catalog().values() if p.profile_digest[:16] == pieces[0]]
    if len(matches) != 1:
        return None
    field = next((f for f in matches[0].fields if f.id == pieces[1]), None)
    return f"{field.name} · {matches[0].name}" if field else None


class ReadPlan(Model):
    profile_id: str
    profile_digest: str
    field_ids: list[str]
    blocks: list[RegisterBlock]
    total_registers: int
    hardware_verified: Literal[False] = False
    write_enabled: Literal[False] = False


def plan(profile: ModelProfile, field_ids: list[str]) -> ReadPlan:
    if not 1 <= len(field_ids) <= 100 or len(set(field_ids)) != len(field_ids):
        raise ValueError("select 1–100 distinct fields")
    by_id = {f.id: f for f in profile.fields}
    addresses: dict[int, set[int]] = {3: set(), 4: set()}
    for key in field_ids:
        field = by_id.get(key)
        if not field or field.decode is None:
            reason = field.blocked_reason if field else "unknown field"
            raise ValueError(f"{key}: {reason}")
        addresses[field.decode.function].update(field.decode.registers)
    total = sum(len(values) for values in addresses.values())
    if total > 1000:
        raise ValueError("read budget exceeded")
    blocks = []
    for function, values in addresses.items():
        # Never bridge undocumented holes even if the upstream poller does so.
        for address in sorted(values):
            if (
                blocks
                and blocks[-1].function == function
                and address == blocks[-1].address + blocks[-1].count
                and blocks[-1].count < profile.max_block_size
            ):
                blocks[-1].count += 1
            else:
                blocks.append(RegisterBlock(function=function, address=address, count=1))
    if len(blocks) > 64:
        raise ValueError("too many non-contiguous read blocks; select fewer fields")
    return ReadPlan(
        profile_id=profile.id,
        profile_digest=profile.profile_digest,
        field_ids=field_ids,
        blocks=blocks,
        total_registers=total,
    )


class RegisterReading(Model):
    function: Literal[3, 4]
    address: int = Field(strict=True, ge=0, le=65535)
    value: int = Field(strict=True, ge=0, le=65535)


def decode_value(spec: DecodeSpec, registers: dict[tuple[int, int], int]) -> float | str:
    words = [registers[spec.function, address] for address in spec.registers]
    if any(type(w) is not int or not 0 <= w <= 65535 for w in words):
        raise ValueError("invalid register response")
    if spec.encoding == "ascii":
        return b"".join(w.to_bytes(2, "big") for w in words).decode("ascii").rstrip("\x00 ")
    ordered = list(reversed(words)) if spec.word_order == "little" else words
    raw = b"".join(w.to_bytes(2, "big") for w in ordered)
    if spec.encoding == "float32":
        value = struct.unpack(">f", raw)[0]
    else:
        value = int.from_bytes(raw, "big", signed=spec.encoding == "signed")
        if spec.encoding == "magnitude" and value & (1 << (len(raw) * 8 - 1)):
            value = -(value & ((1 << (len(raw) * 8 - 1)) - 1))
    if spec.raw_min is not None and value < spec.raw_min:
        raise ValueError("raw value below profile range")
    if spec.raw_max is not None and value > spec.raw_max:
        raise ValueError("raw value above profile range")
    if spec.mask is not None:
        value = int(value) & spec.mask
    if spec.bit is not None:
        value = (int(value) >> spec.bit) & 1
    value = (value + spec.offset) * spec.scale + spec.post_offset
    if spec.floor_divisor is not None:
        value //= spec.floor_divisor
    if spec.negate:
        value = -value
    if not math.isfinite(value):
        raise ValueError("non-finite decoded value")
    if spec.minimum is not None and value < spec.minimum:
        raise ValueError("decoded value below profile range")
    if spec.maximum is not None and value > spec.maximum:
        raise ValueError("decoded value above profile range")
    return value


def decode(profile: ModelProfile, field_ids: list[str], readings: list[RegisterReading]) -> list[dict]:
    read_plan = plan(profile, field_ids)
    allowed = {(b.function, a) for b in read_plan.blocks for a in range(b.address, b.address + b.count)}
    registers = {}
    for reading in readings:
        key = (reading.function, reading.address)
        if key in registers or key not in allowed:
            raise ValueError("duplicate or unrequested register response")
        registers[key] = reading.value
    selected = {f.id: f for f in profile.fields}
    results = []
    for key in field_ids:
        field = selected[key]
        result = {
            "field_id": key,
            "name": field.name,
            "unit": field.unit,
            "native_key": f"model.{profile.profile_digest[:16]}.{key}",
            "value": None,
            "quality": "UNVERIFIED",
            "reason": None,
        }
        try:
            result["value"] = decode_value(field.decode, registers)
        except KeyError:
            result.update(quality="MISSING", reason="incomplete register response")
        except (ValueError, UnicodeError) as exc:
            result.update(quality="INVALID", reason=str(exc))
        results.append(result)
    return results
