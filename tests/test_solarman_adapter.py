"""Tests for Solarman adapter: HOSTS, READS, auth, history, alerts, control stub."""

import pytest

from solar_fleet.adapters.solarman import HOSTS, READS, Solarman
from solar_fleet.adapters.solarman_control import compile_solarman
from solar_fleet.domain import Device, DeviceIdentity, SafetyError, VendorError


def test_hosts_regions():
    assert "global" in HOSTS
    assert "cn" in HOSTS
    for url in HOSTS.values():
        assert url.startswith("https://")


def test_reads_explicit_coverage():
    assert len(READS) >= 7
    assert "/station/v1.0/list" in READS
    assert "/station/v1.0/device" in READS
    assert "/station/v1.0/history" in READS
    assert "/device/v1.0/currentData" in READS
    assert "/device/v1.0/list" in READS
    assert "/device/v1.0/historical" in READS
    assert "/device/v1.0/alertList" in READS


def test_credentials_incomplete():
    with pytest.raises(VendorError, match="credentials_incomplete"):
        Solarman({"region": "global"}, {"app_id": "a"})


def test_unsupported_region():
    with pytest.raises(VendorError, match="unsupported_data_center"):
        Solarman(
            {"region": "mars"},
            {
                "app_id": "a",
                "app_secret": "s",
                "identity_value": "v",
                "password_sha256": "p",
                "identity_field": "email",
            },
        )


def test_identity_method_not_supported():
    with pytest.raises(VendorError, match="identity_method_not_supported"):
        Solarman(
            {"region": "global"},
            {
                "app_id": "a",
                "app_secret": "s",
                "identity_value": "v",
                "password_sha256": "p",
                "identity_field": "phone",
            },
        )


def test_control_stub_raises_safety_error():
    """Solarman is transport-only; control requires OEM identification."""
    device = Device(
        id="SM001",
        site_id="S1",
        integration_id="I1",
        vendor_id="SN555",
        type="INVERTER",
        identity=DeviceIdentity(vendor="SOLARMAN"),
    )
    with pytest.raises(SafetyError, match="intent_mapping_unknown"):
        compile_solarman(device, "SET_WORK_MODE", {"value": 0})


def test_control_stub_any_intent():
    device = Device(
        id="SM001",
        site_id="S1",
        integration_id="I1",
        vendor_id="SN555",
        type="INVERTER",
        identity=DeviceIdentity(vendor="SOLARMAN"),
    )
    for intent in ("SET_EXPORT_LIMIT", "ENABLE_GRID_CHARGE", "SET_TOU", "SET_MAX_CHARGE_CURRENT"):
        with pytest.raises(SafetyError, match="intent_mapping_unknown"):
            compile_solarman(device, intent, {})
