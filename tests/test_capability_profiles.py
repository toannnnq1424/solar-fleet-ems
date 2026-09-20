"""Synthetic acceptance records only. No shipping profile or equipment is commissioned here."""

from datetime import timedelta

import pytest

from solar_fleet.capability_profiles import AcceptanceRecord, ControlProfile, IntentContract, ProfileRegistry
from solar_fleet.domain import Constraint, Role, utcnow


def profile_for(device, **changes):
    now = utcnow()
    profile = ControlProfile(
        id="SIMULATOR-PROFILE", version="1", adapter_version="test.1", vendor_api_version="fixture.1",
        identity=device.identity, transport="SIMULATOR",
        acceptance=AcceptanceRecord(
            id="SIMULATOR-ACCEPTANCE", device_id=device.id, integration_id=device.integration_id,
            vendor_device_id=device.vendor_id, tested_by="SIMULATOR-TESTER", reviewed_by="SIMULATOR-REVIEWER",
            accepted_at=now - timedelta(hours=1), expires_at=now + timedelta(days=1),
            evidence_ids=["SIMULATOR-OFFICIAL-EVIDENCE"], evidence_grade="A",
            test_artifact_digest="a" * 64, write_grant_verified=True, readback_verified=True,
        ),
        contracts=[IntentContract(intent="SET_RESERVE_SOC", constraints={"value": Constraint(min=10, max=90, step=1, unit="%")},
            readback_fields=["reserve"], group="battery", explanation_vi="Hồ sơ kiểm thử", explanation_en="Test profile")],
    )
    return ControlProfile.model_validate({**profile.model_dump(), **changes})


def registered(device):
    registry = ProfileRegistry()
    registry.register(profile_for(device), vendor="SIMULATOR", adapter_version="test.1")
    return registry


def test_profile_resolves_exact_acceptance_and_validates_constraints(device):
    cap = registered(device).resolve(device, "SET_RESERVE_SOC")
    assert cap.state == "VERIFIED" and cap.acceptance_id == "SIMULATOR-ACCEPTANCE"
    cap.validate_for(device, {"value": 30})
    for value in (9, 91, 30.5, True, "30"):
        with pytest.raises(ValueError):
            cap.validate_for(device, {"value": value})


@pytest.mark.parametrize("field,value", [("id", "other-device"), ("integration_id", "other-account"), ("vendor_id", "OTHER-SERIAL")])
def test_profile_never_grants_other_devices_or_accounts(device, field, value):
    other = device.model_copy(update={field: value})
    assert registered(device).resolve(other, "SET_RESERVE_SOC") is None


@pytest.mark.parametrize("field", ["firmware", "logger_model", "protocol_version", "region", "account_type", "privilege"])
def test_identity_change_removes_acceptance(device, field):
    other = device.model_copy(update={"identity": device.identity.model_copy(update={field: "DIFFERENT"})})
    assert registered(device).resolve(other, "SET_RESERVE_SOC") is None


def test_revocation_expiry_and_ambiguity_fail_closed(device):
    registry = registered(device)
    assert registry.resolve(device, "SET_RESERVE_SOC", now=utcnow() + timedelta(days=2)).state == "UNKNOWN"
    registry.revoke("SIMULATOR-PROFILE")
    assert registry.resolve(device, "SET_RESERVE_SOC").reason == "control_profile_revoked"
    registry = registered(device)
    registry.register(profile_for(device, id="SIMULATOR-SECOND"), vendor="SIMULATOR", adapter_version="test.1")
    assert registry.resolve(device, "SET_RESERVE_SOC").reason == "ambiguous_control_profile"


@pytest.mark.parametrize("semantics", ["equivalent", "partial", "unsupported"])
def test_approximation_is_explainable_but_never_silent_write(device, semantics):
    profile = profile_for(device)
    profile.contracts[0].semantics = semantics
    registry = ProfileRegistry()
    registry.register(profile, vendor="SIMULATOR", adapter_version="test.1")
    cap = registry.resolve(device, "SET_RESERVE_SOC")
    assert not cap.hardware_verified and cap.state != "VERIFIED"
    assert registry.explain(device)[0]["semantics"] == semantics


def test_registration_requires_review_and_pinned_adapter(device):
    profile = profile_for(device)
    with pytest.raises(ValueError, match="adapter_version"):
        ProfileRegistry().register(profile, vendor="SIMULATOR", adapter_version="test.2")
    invalid = profile.model_dump()
    invalid["acceptance"]["reviewed_by"] = invalid["acceptance"]["tested_by"]
    with pytest.raises(ValueError, match="independent_acceptance"):
        ControlProfile.model_validate(invalid)
    invalid = profile.model_dump()
    invalid["identity"]["firmware"] = "*"
    with pytest.raises(ValueError, match="exact_profile"):
        ControlProfile.model_validate(invalid)


def test_native_grid_contract_requires_dedicated_permission():
    with pytest.raises(ValueError, match="sensitive_native"):
        IntentContract(intent="SET_GRID_CODE", group="grid", required_role=Role.ENGINEER,
                       constraints={"value": Constraint(enum=["SIMULATOR"] )}, readback_fields=["grid"],
                       explanation_vi="Kiểm thử", explanation_en="Fixture")


def test_schema_reference_cannot_fetch_remote_resource():
    with pytest.raises(ValueError, match="external_schema_reference"):
        IntentContract(intent="SET_TOU", group="tou", constraints={"slots": Constraint(json_schema={"$ref": "https://example.invalid/schema"})},
                       readback_fields=["slots"], explanation_vi="Kiểm thử", explanation_en="Fixture")
