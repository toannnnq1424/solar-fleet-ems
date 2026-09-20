"""Commissioned control contracts, installed with adapter code, never promoted by a UI flag.

An acceptance is tied to one connection and physical device. Sharing a model is not
proof that another account has write grants or that its logger has the same semantics.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Literal

from pydantic import Field, field_validator, model_validator

from .domain import Capability, Constraint, Device, DeviceIdentity, Model, Role, SafetyError, utcnow


class AcceptanceRecord(Model):
    id: str = Field(min_length=1, max_length=160)
    device_id: str = Field(min_length=1)
    integration_id: str = Field(min_length=1)
    vendor_device_id: str = Field(min_length=1)
    tested_by: str = Field(min_length=1)
    reviewed_by: str = Field(min_length=1)
    accepted_at: datetime
    expires_at: datetime
    evidence_ids: list[str] = Field(min_length=1)
    evidence_grade: Literal["A", "B"]
    test_artifact_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    write_grant_verified: Literal[True]
    readback_verified: Literal[True]

    @field_validator("accepted_at", "expires_at")
    @classmethod
    def timezone_required(cls, value):
        if value.tzinfo is None:
            raise ValueError("acceptance_timezone_required")
        return value

    @model_validator(mode="after")
    def chronology(self):
        if self.tested_by == self.reviewed_by:
            raise ValueError("independent_acceptance_review_required")
        if self.expires_at <= self.accepted_at:
            raise ValueError("acceptance_expiry_invalid")
        return self


class IntentContract(Model):
    intent: str = Field(pattern=r"^[A-Z][A-Z0-9_]{1,99}$")
    semantics: Literal["exact", "equivalent", "partial", "unsupported"] = "exact"
    explanation_vi: str = Field(min_length=1, max_length=2000)
    explanation_en: str = Field(min_length=1, max_length=2000)
    constraints: dict[str, Constraint]
    readback_fields: list[str] = Field(default_factory=list)
    required_role: Role = Role.INSTALLER
    required_permission: str | None = None
    group: Literal["basic", "battery", "tou", "meter", "export", "generator", "grid", "advanced", "native"]

    @model_validator(mode="after")
    def complete(self):
        if self.required_role not in {Role.OPERATOR, Role.INSTALLER, Role.ENGINEER}:
            raise ValueError("technical_control_role_required")
        if self.group in {"grid", "native"} and not self.required_permission:
            raise ValueError("sensitive_native_permission_required")
        if self.semantics == "exact" and (not self.readback_fields or not self.constraints):
            raise ValueError("exact_contract_schema_and_readback_required")
        if len(set(self.readback_fields)) != len(self.readback_fields):
            raise ValueError("duplicate_readback_field")
        for constraint in self.constraints.values():
            if constraint.json_schema is not None:
                from jsonschema import Draft7Validator

                Draft7Validator.check_schema(constraint.json_schema)
                # References may not resolve arbitrary URLs during command validation.
                def check(value):
                    if isinstance(value, dict):
                        if "$ref" in value and not str(value["$ref"]).startswith("#/"):
                            raise ValueError("external_schema_reference_forbidden")
                        for item in value.values():
                            check(item)
                    elif isinstance(value, list):
                        for item in value:
                            check(item)
                check(constraint.json_schema)
            elif constraint.enum is not None:
                if not constraint.enum:
                    raise ValueError("empty_parameter_enum")
            elif constraint.min is None or constraint.max is None or constraint.min > constraint.max:
                raise ValueError("commissioned_parameter_range_required")
            elif not constraint.unit or (constraint.step is not None and constraint.step <= 0):
                raise ValueError("commissioned_unit_and_step_required")
        return self


class ControlProfile(Model):
    id: str = Field(min_length=1, max_length=160)
    version: str = Field(min_length=1, max_length=80)
    adapter_version: str = Field(min_length=1)
    vendor_api_version: str = Field(min_length=1)
    identity: DeviceIdentity
    transport: str = Field(min_length=1)
    acceptance: AcceptanceRecord
    contracts: list[IntentContract] = Field(min_length=1)

    @model_validator(mode="after")
    def exact_identity(self):
        for key in ("vendor", "model", "logger_model", "firmware", "protocol_version", "account_type", "privilege", "region"):
            value = getattr(self.identity, key)
            if not value or value.strip().upper() in {"*", "UNKNOWN", "ANY"}:
                raise ValueError("exact_profile_identity_required")
        if len({c.intent for c in self.contracts}) != len(self.contracts):
            raise ValueError("duplicate_profile_intent")
        return self

    def matches(self, device: Device) -> bool:
        return (
            device.identity == self.identity
            and device.id == self.acceptance.device_id
            and device.integration_id == self.acceptance.integration_id
            and device.vendor_id == self.acceptance.vendor_device_id
        )


@dataclass
class ProfileRegistry:
    _profiles: dict[str, ControlProfile] = field(default_factory=dict)
    _revoked: set[str] = field(default_factory=set)

    def register(self, profile: ControlProfile, *, vendor: str, adapter_version: str):
        # Revalidate even a model constructed with model_construct/model_copy.
        profile = ControlProfile.model_validate(profile.model_dump(mode="json"))
        if profile.id in self._profiles:
            raise ValueError("duplicate_control_profile")
        if profile.identity.vendor != vendor or profile.adapter_version != adapter_version:
            raise ValueError("profile_adapter_version_mismatch")
        self._profiles[profile.id] = profile

    def revoke(self, profile_id: str):
        if profile_id not in self._profiles:
            raise SafetyError("control_profile_not_found")
        self._revoked.add(profile_id)

    def candidates(self, device: Device):
        return [p for p in self._profiles.values() if p.matches(device)]

    def resolve(self, device: Device, intent: str, *, now=None) -> Capability | None:
        now = now or utcnow()
        matches = [(p, c) for p in self.candidates(device) for c in p.contracts if c.intent == intent]
        if not matches:
            return None
        if len(matches) != 1:
            return Capability(intent=intent, identity=device.identity, semantic_match="requires_manual_configuration",
                              transport="UNKNOWN", reason="ambiguous_control_profile")
        profile, contract = matches[0]
        acceptance = profile.acceptance
        reason = "commissioned_exact_contract"
        active = True
        if profile.id in self._revoked:
            active, reason = False, "control_profile_revoked"
        elif not acceptance.accepted_at <= now < acceptance.expires_at:
            active, reason = False, "control_acceptance_expired_or_future"
        elif contract.semantics != "exact":
            active, reason = False, "non_exact_mapping_requires_explicit_policy"
        return Capability(
            intent=intent, state="VERIFIED" if active else "UNSUPPORTED" if contract.semantics == "unsupported" else "UNKNOWN",
            identity=device.identity, semantic_match="exact" if contract.semantics == "exact" else "unsupported" if contract.semantics == "unsupported" else "approximate",
            evidence_ids=acceptance.evidence_ids, evidence_grade=acceptance.evidence_grade,
            constraints=contract.constraints, required_role=contract.required_role,
            required_permission=contract.required_permission, hardware_verified=active,
            transport=profile.transport, reason=reason, readback_fields=contract.readback_fields,
            adapter_version=profile.adapter_version, vendor_api_version=profile.vendor_api_version,
            last_verified_date=acceptance.accepted_at.isoformat(),
            profile_id=profile.id, profile_version=profile.version, acceptance_id=acceptance.id,
            acceptance_expires_at=acceptance.expires_at,
        )

    def explain(self, device: Device):
        rows = []
        for profile in self.candidates(device):
            for contract in profile.contracts:
                cap = self.resolve(device, contract.intent)
                rows.append({
                    "profile_id": profile.id, "profile_version": profile.version,
                    "intent": contract.intent, "group": contract.group,
                    "semantics": contract.semantics,
                    "explanation": {"vi": contract.explanation_vi, "en": contract.explanation_en},
                    "state": cap.state, "reason": cap.reason,
                    "acceptance_id": profile.acceptance.id,
                    "expires_at": profile.acceptance.expires_at.isoformat(),
                    "evidence_ids": profile.acceptance.evidence_ids,
                })
        return rows
