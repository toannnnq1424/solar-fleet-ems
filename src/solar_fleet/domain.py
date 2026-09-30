from __future__ import annotations

import math
from datetime import UTC, datetime
from enum import StrEnum
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, PrivateAttr, field_validator, model_validator


def utcnow() -> datetime:
    return datetime.now(UTC)


class Model(BaseModel):
    model_config = ConfigDict(extra="forbid", validate_assignment=True)


class Role(StrEnum):
    VIEWER = "Viewer"
    OPERATOR = "Operator"
    INSTALLER = "Installer"
    ENGINEER = "Senior Engineer"
    ADMIN = "Administrator"


class Principal(Model):
    # Internal snapshots participate in equality but never in API serialization.
    _authority_revision: int = PrivateAttr(default=0)
    _session_revision: int = PrivateAttr(default=0)
    id: str
    role: Role
    site_ids: list[str] = Field(default_factory=list)
    permissions: list[str] = Field(default_factory=list)

    def can_access(self, site_id: str) -> bool:
        return "*" in self.site_ids or site_id in self.site_ids


class DeviceIdentity(Model):
    vendor: str
    model: str | None = None
    logger_model: str | None = None
    battery_model: str | None = None
    firmware: str | None = None
    protocol_version: str | None = None
    account_type: str | None = None
    privilege: str | None = None
    region: str | None = None
    product_family: str | None = None
    actual_oem: str | None = None


class Device(Model):
    id: str
    site_id: str
    integration_id: str
    vendor_id: str
    type: str
    identity: DeviceIdentity
    name: str | None = None
    logger_id: str | None = None
    last_seen: datetime | None = None
    online: bool = False
    metadata: dict[str, Any] = Field(default_factory=dict)


class Source(StrEnum):
    LOCAL = "LOCAL"
    AGENT = "SITE_AGENT"
    CLOUD = "VENDOR_CLOUD"
    SIMULATOR = "SIMULATOR"


class Sample(Model):
    device_id: str
    metric: str
    value: float | None
    unit: str | None
    source: Source
    source_timestamp: datetime | None
    received_at: datetime = Field(default_factory=utcnow)
    latency_ms: float | None = None
    quality: Literal["GOOD", "UNVERIFIED", "INVALID", "MISSING", "DISAGREEMENT"]
    stale: bool = True
    binding_id: str
    evidence_ids: list[str] = Field(default_factory=list)

    @field_validator("source_timestamp", "received_at")
    @classmethod
    def aware(cls, value: datetime | None) -> datetime | None:
        if value is not None and value.tzinfo is None:
            raise ValueError("timestamp must include timezone")
        return value

    @field_validator("value")
    @classmethod
    def finite(cls, value: float | None) -> float | None:
        if value is not None and not math.isfinite(value):
            raise ValueError("measurement must be finite")
        return value

    @model_validator(mode="after")
    def directional_nonnegative(self) -> Sample:
        if self.metric in {"grid_import_w", "grid_export_w", "battery_charge_w", "battery_discharge_w"}:
            if self.value is not None and self.value < 0:
                raise ValueError("canonical directional power cannot be negative")
        return self


class CommandStatus(StrEnum):
    CREATED = "CREATED"
    VALIDATING = "VALIDATING"
    READY = "READY"
    SENDING = "SENDING"
    ACCEPTED = "ACCEPTED"
    WAITING_DEVICE = "WAITING_DEVICE"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    FAILED = "FAILED"
    TIMEOUT = "TIMEOUT"
    UNSUPPORTED = "UNSUPPORTED"
    CANCELLED = "CANCELLED"


class Constraint(Model):
    min: float | None = Field(default=None, allow_inf_nan=False)
    max: float | None = Field(default=None, allow_inf_nan=False)
    step: float | None = Field(default=None, allow_inf_nan=False)
    enum: list[Any] | None = None
    unit: str | None = None
    json_schema: dict[str, Any] | None = None

    def validate_value(self, value: Any) -> None:
        if self.json_schema is not None:
            from jsonschema import Draft7Validator

            if not Draft7Validator(self.json_schema).is_valid(value):
                raise ValueError("value outside structured device schema")
            return
        if self.enum is not None:
            if not any(type(value) is type(item) and value == item for item in self.enum):
                raise ValueError("value outside allowed enum")
            return
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            raise ValueError("finite numeric value required")
        if self.min is None or self.max is None:
            raise ValueError("device range unverified")
        if not self.min <= value <= self.max:
            raise ValueError("value outside device range")
        if self.step is not None:
            if self.step <= 0:
                raise ValueError("invalid step")
            n = (value - self.min) / self.step
            if not math.isclose(n, round(n), abs_tol=1e-8):
                raise ValueError("value does not match device step")


class Capability(Model):
    intent: str
    state: Literal["VERIFIED", "UNKNOWN", "UNSUPPORTED"] = "UNKNOWN"
    semantic_match: Literal["exact", "approximate", "unsupported", "requires_manual_configuration"]
    identity: DeviceIdentity
    evidence_ids: list[str] = Field(default_factory=list)
    evidence_grade: Literal["A", "B", "C", "D", "E", "F"] = "F"
    constraints: dict[str, Constraint] = Field(default_factory=dict)
    required_role: Role = Role.INSTALLER
    required_permission: str | None = None
    hardware_verified: bool = False
    transport: str
    reason: str
    readback_fields: list[str] = Field(default_factory=list)
    adapter_version: str = "0.1.0"
    vendor_api_version: str | None = None
    last_verified_date: str | None = None
    profile_id: str | None = None
    profile_version: str | None = None
    acceptance_id: str | None = None
    acceptance_expires_at: datetime | None = None

    def validate_for(self, device: Device, values: dict[str, Any]) -> None:
        if self.acceptance_expires_at is not None:
            if self.acceptance_expires_at.tzinfo is None or self.acceptance_expires_at <= utcnow():
                raise ValueError("hardware acceptance expired")
        if self.state != "VERIFIED" or self.evidence_grade == "F" or not self.evidence_ids:
            raise ValueError("capability not verified")
        if not self.hardware_verified:
            raise ValueError("hardware acceptance required")
        if self.semantic_match != "exact":
            raise ValueError("exact semantic mapping required for this release")
        # Identity equality is exact: unknown/wildcard profiles must never match arbitrary hardware.
        if self.identity != device.identity:
            raise ValueError("device identity/firmware differs from capability profile")
        required = (
            "model",
            "logger_model",
            "firmware",
            "protocol_version",
            "account_type",
            "privilege",
            "region",
        )
        if any(not getattr(self.identity, f) for f in required):
            raise ValueError("incomplete device profile")
        if set(values) != set(self.constraints):
            raise ValueError("parameter set differs from capability schema")
        for field, constraint in self.constraints.items():
            constraint.validate_value(values[field])
        if not self.readback_fields:
            raise ValueError("readback contract required")


class Configuration(Model):
    values: dict[str, Any]
    device_timestamp: datetime | None = None
    received_at: datetime = Field(default_factory=utcnow)
    freshness_verified: bool = False


class VendorCall(Model):
    path: str
    body: dict[str, Any]


class CommandPlan(Model):
    id: str
    device_id: str
    site_id: str
    operator_id: str
    intent: str
    parameters: dict[str, Any]
    previous: dict[str, Any]
    expected: dict[str, Any]
    calls: list[VendorCall]
    capability: Capability
    created_at: datetime
    expires_at: datetime
    risks: list[str]
    digest: str = ""
    binding_digest: str = ""
    authority_revisions: dict[str, dict[str, int]] = Field(default_factory=dict)
    operator_revision: int | None = None
    revision_scope: Literal["kind_wide", "selected_objects_v1"] = "kind_wide"


class Ack(Model):
    order_id: str
    online: bool


class OrderResult(Model):
    state: Literal["PENDING", "SUCCEEDED", "FAILED", "CANCELLED"]
    vendor_status: str


class SafetyError(Exception):
    """Only static, non-sensitive messages may be returned to clients or persisted."""


class VendorError(SafetyError):
    pass
