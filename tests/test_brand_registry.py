"""Comprehensive test suite for multi-brand device drivers and protocol registry.

Validates that all 30 brand ecosystems from before_project:
- Have verified holding registers and alarm code dictionaries
- Strictly enforce the exact-model invariant (brand alone returns UNKNOWN)
- Translate vendor-neutral EMS dispatch commands to correct Modbus write packets
"""

import pytest

from solar_fleet.brand_registry import (
    EXTENDED_BRAND_ALARMS,
    EXTENDED_BRAND_REGISTERS,
    EXTENDED_KNOWN_MODELS,
)
from solar_fleet.vendor_device_translator import (
    ModbusFunctionCode,
    StandardWorkMode,
    VendorDeviceTranslator,
)
from solar_fleet.vendor_registers import (
    KNOWN_MODELS_PER_VENDOR,
    VENDOR_ALARM_TABLES,
    VENDOR_REGISTER_TABLES,
    decode_vendor_alarm,
    get_vendor_registers,
)

# ============================================================================
# 1. Verification of Brand Registry Completeness
# ============================================================================

def test_extended_brand_coverage_count():
    """Verify that brand_registry defines exactly 24 extended brands."""
    assert len(EXTENDED_BRAND_REGISTERS) == 24
    assert len(EXTENDED_BRAND_ALARMS) == 24
    assert len(EXTENDED_KNOWN_MODELS) == 24


def test_total_vendor_coverage_30_brands():
    """Verify that vendor_registers merges all 30 brands."""
    assert len(VENDOR_REGISTER_TABLES) >= 30
    assert len(VENDOR_ALARM_TABLES) >= 30
    assert len(KNOWN_MODELS_PER_VENDOR) >= 30

    expected_brands = [
        "goodwe", "deye", "sungrow", "huawei", "growatt", "solis",
        "victron", "fronius", "solaredge", "sma", "sofar", "solax",
        "alphaess", "enphase", "foxess", "givenergy", "hoymiles",
        "sigenergy", "pylontech", "byd", "kaco", "kostal", "srne",
        "must", "anenji", "afore", "kstar", "tsun", "megarevo", "tesla"
    ]
    for brand in expected_brands:
        assert brand in VENDOR_REGISTER_TABLES, f"Missing register table for {brand}"
        assert brand in VENDOR_ALARM_TABLES, f"Missing alarm table for {brand}"
        assert brand in KNOWN_MODELS_PER_VENDOR, f"Missing known models for {brand}"


@pytest.mark.parametrize("brand", list(EXTENDED_BRAND_REGISTERS.keys()))
def test_extended_brand_register_richness(brand: str):
    """Verify that every brand has at least 10 registers with required metadata fields."""
    regs = EXTENDED_BRAND_REGISTERS[brand]
    assert len(regs) >= 10, f"{brand} must have >= 10 holding registers"
    for addr, details in regs.items():
        assert isinstance(addr, int)
        assert "name" in details
        assert "type" in details
        assert "unit" in details
        assert "scale" in details
        assert "access" in details
        assert "desc" in details


@pytest.mark.parametrize("brand", list(EXTENDED_BRAND_ALARMS.keys()))
def test_extended_brand_alarm_richness(brand: str):
    """Verify that every brand has at least 5 alarm codes with actionable SOPs."""
    alarms = EXTENDED_BRAND_ALARMS[brand]
    assert len(alarms) >= 5, f"{brand} must have >= 5 alarm codes"
    for code, details in alarms.items():
        assert isinstance(code, int)
        assert "name" in details
        assert details["severity"] in ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
        assert len(details["sop"]) > 10, f"SOP too short for {brand} alarm {code}"
        assert "category" in details


# ============================================================================
# 2. Strict Exact-Model Invariant Tests
# ============================================================================

@pytest.mark.parametrize("brand", [
    "victron", "fronius", "solaredge", "sma", "sofar", "solax",
    "alphaess", "enphase", "foxess", "givenergy", "hoymiles",
    "sigenergy", "pylontech", "byd", "kaco", "kostal", "srne",
    "must", "anenji", "afore", "kstar", "tsun", "megarevo", "tesla"
])
def test_brand_alone_returns_unknown_status(brand: str):
    """Calling get_vendor_registers without exact model must return UNKNOWN status."""
    res_none = get_vendor_registers(brand, model=None)
    assert res_none["status"] == "UNKNOWN"
    assert res_none["reason"] == "exact_model_protocol_evidence_required"
    assert res_none["registers"] == []
    assert res_none["alarms"] == []

    res_empty = get_vendor_registers(brand, model="")
    assert res_empty["status"] == "UNKNOWN"

    res_generic = get_vendor_registers(brand, model="generic")
    assert res_generic["status"] == "UNKNOWN"


@pytest.mark.parametrize("brand", [
    "victron", "fronius", "solaredge", "sma", "sofar", "solax",
    "alphaess", "enphase", "foxess", "givenergy", "hoymiles",
    "sigenergy", "pylontech", "byd", "kaco", "kostal", "srne",
    "must", "anenji", "afore", "kstar", "tsun", "megarevo", "tesla"
])
def test_exact_model_returns_verified_status(brand: str):
    """Calling get_vendor_registers with a known model returns VERIFIED_AUDITED."""
    known_model = KNOWN_MODELS_PER_VENDOR[brand][0]
    res = get_vendor_registers(brand, model=known_model)
    assert res["status"] == "VERIFIED_AUDITED"
    assert res["registers_count"] >= 10
    assert res["alarms_count"] >= 5
    assert len(res["registers"]) == res["registers_count"]
    assert len(res["alarms"]) == res["alarms_count"]


def test_alarm_decoding_exact_model_vs_brand_alone():
    """Verify alarm decoding with exact model vs brand alone."""
    # Victron: Alarm code 2 (Low Battery Alarm)
    victron_model = "MultiPlus-II 48/5000"
    alarm_with_model = decode_vendor_alarm("Victron", 2, model=victron_model)
    assert alarm_with_model["severity"] == "CRITICAL"
    assert "Low Battery" in alarm_with_model["title"]
    assert "cutoff voltage" in alarm_with_model["remediation_advice"]

    alarm_without_model = decode_vendor_alarm("Victron", 2, model=None)
    assert alarm_without_model["severity"] == "UNKNOWN"
    assert "Exact model" in alarm_without_model["remediation_advice"]

    # Tesla: Alarm code 1 (Grid Outage)
    tesla_model = "Powerwall 2"
    tesla_with_model = decode_vendor_alarm("Tesla", 1, model=tesla_model)
    assert tesla_with_model["severity"] == "MEDIUM"
    assert "Island" in tesla_with_model["title"]

    tesla_without_model = decode_vendor_alarm("Tesla", 1, model=None)
    assert tesla_without_model["severity"] == "UNKNOWN"

    # BYD: Alarm code 1 (Cell Overvoltage)
    byd_model = "Battery-Box Premium HVS"
    byd_with_model = decode_vendor_alarm("BYD", 1, model=byd_model)
    assert byd_with_model["severity"] == "CRITICAL"
    assert "Overvoltage" in byd_with_model["title"]

    byd_without_model = decode_vendor_alarm("BYD", 1, model=None)
    assert byd_without_model["severity"] == "UNKNOWN"


# ============================================================================
# 3. Vendor Device Command Translation Tests
# ============================================================================

def test_translate_victron_commands():
    reqs = VendorDeviceTranslator.translate_command(
        vendor="Victron",
        slave_id=100,
        work_mode=StandardWorkMode.BACKUP_UPS,
        power_w=3000,
    )
    assert len(reqs) >= 2
    # Check ESS mode write
    mode_req = next(r for r in reqs if r.register_address == 2700)
    assert mode_req.values == [3]
    assert mode_req.function_code == ModbusFunctionCode.WRITE_SINGLE

    # Check grid setpoint write
    setpoint_req = next(r for r in reqs if r.register_address == 2701)
    assert setpoint_req.values == [3000]


def test_translate_fronius_curtailment():
    reqs = VendorDeviceTranslator.translate_command(
        vendor="Fronius",
        slave_id=1,
        power_w=5000,  # 50.0%
    )
    assert len(reqs) == 1
    assert reqs[0].register_address == 40232
    assert reqs[0].values == [5000]
    assert reqs[0].vendor == "Fronius"


def test_translate_solaredge_modes():
    reqs = VendorDeviceTranslator.translate_command(
        vendor="SolarEdge",
        slave_id=1,
        work_mode=StandardWorkMode.PEAK_SHAVING,
        power_w=8000,  # 80%
    )
    assert len(reqs) == 2
    limit_req = next(r for r in reqs if r.register_address == 40224)
    assert limit_req.values == [80]
    mode_req = next(r for r in reqs if r.register_address == 57348)
    assert mode_req.values == [3]


def test_translate_tesla_reserve():
    reqs = VendorDeviceTranslator.translate_command(
        vendor="Tesla",
        slave_id=1,
        work_mode=StandardWorkMode.SELF_CONSUMPTION,
        power_w=20,  # 20% backup reserve
    )
    assert len(reqs) == 2
    res_req = next(r for r in reqs if r.register_address == 40086)
    assert res_req.values == [20]
    mode_req = next(r for r in reqs if r.register_address == 40088)
    assert mode_req.values == [0]


def test_translate_unsupported_vendor_raises_error():
    with pytest.raises(ValueError, match="Unsupported vendor"):
        VendorDeviceTranslator.translate_command(
            vendor="CompletelyUnknownVendorXYZ",
            slave_id=1,
            work_mode=StandardWorkMode.SELF_CONSUMPTION,
        )
