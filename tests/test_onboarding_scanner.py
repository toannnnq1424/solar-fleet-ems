"""Tests for Onboarding Barcode/QR Scanner Engine."""

from solar_fleet.onboarding_scanner import OnboardingScanner


def test_scan_deye_rating_plate():
    scanner = OnboardingScanner()
    raw_payload = "DEYE;MOD:SUN-12K-SG04LP3;SN:2308123456;KW:12.0;GRID:3P4W"
    result = scanner.parse_barcode_payload(raw_payload)
    assert result.vendor == "deye"
    assert result.model == "SUN-12K-SG04LP3"
    assert result.serial_number == "2308123456"
    assert result.rated_power_kw == 12.0
    assert result.grid_phase == "3P4W"
    assert result.matched_profile == "deye_sg04lp3"


def test_scan_sungrow_rating_plate():
    scanner = OnboardingScanner()
    raw_payload = "SG110CX-20240901-SN9988776655-P110KW"
    result = scanner.parse_barcode_payload(raw_payload)
    assert result.vendor == "sungrow"
    assert "SG110CX" in result.model
    assert result.serial_number == "SN9988776655"
    assert result.rated_power_kw == 110.0
    assert result.matched_profile == "sungrow_commercial_sg110cx"


def test_scan_huawei_rating_plate():
    scanner = OnboardingScanner()
    raw_payload = "HUAWEI-SUN2000-100KTL-M1;SN:2102312ABC10M1234567;100KW"
    result = scanner.parse_barcode_payload(raw_payload)
    assert result.vendor == "huawei"
    assert "SUN2000-100KTL" in result.model
    assert result.serial_number == "2102312ABC10M1234567"
    assert result.rated_power_kw == 100.0


def test_scan_bluesun_rating_plate():
    scanner = OnboardingScanner()
    raw_payload = "BLUESUN;MODEL:BSM-5500BLV-48DA;SN:BSM2024001122"
    result = scanner.parse_barcode_payload(raw_payload)
    assert result.vendor == "bluesun"
    assert result.model == "BSM-5500BLV-48DA"
    assert result.serial_number == "BSM2024001122"
    assert result.matched_profile == "bluesun_bsm_5500"


def test_scan_unknown_payload_fallback():
    scanner = OnboardingScanner()
    raw_payload = "SOME_RANDOM_TEXT_NOT_MATCHING_ANY_INVERTER"
    result = scanner.parse_barcode_payload(raw_payload)
    assert result.vendor == "unknown"
    assert result.matched_profile is None
    assert result.raw_payload == raw_payload
