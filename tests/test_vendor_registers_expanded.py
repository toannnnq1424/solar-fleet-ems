
from solar_fleet.vendor_registers import (
    DEYE_ALARM_CODES,
    GOODWE_ALARM_CODES,
    GROWATT_ALARM_CODES,
    HUAWEI_ALARM_CODES,
    SOLIS_ALARM_CODES,
    SUNGROW_ALARM_CODES,
    decode_vendor_alarm,
    get_vendor_registers,
)


def test_alarm_counts_populated():
    # Verify our tables are richly populated with verified codes
    assert len(GOODWE_ALARM_CODES) >= 15
    assert len(DEYE_ALARM_CODES) >= 15
    assert len(SUNGROW_ALARM_CODES) >= 15
    assert len(HUAWEI_ALARM_CODES) >= 10
    assert len(GROWATT_ALARM_CODES) >= 10
    assert len(SOLIS_ALARM_CODES) >= 10


def test_exact_model_alarm_decoding():
    # GoodWe ET model
    gw_alarm = decode_vendor_alarm("GoodWe", 1, model="GW5K-ET")
    assert gw_alarm["severity"] == "CRITICAL"
    assert "Relay" in gw_alarm["title"]
    assert "remediation_advice" in gw_alarm
    assert gw_alarm["vendor"] == "GoodWe"
    assert gw_alarm["model"] == "GW5K-ET"

    # Deye SUN-SG04LP3 model
    deye_alarm = decode_vendor_alarm("Deye", 8, model="SUN-SG04LP3-EU")
    assert deye_alarm["severity"] == "CRITICAL"
    assert "DC Bus" in deye_alarm["title"]

    # Sungrow SH10RT model
    sg_alarm = decode_vendor_alarm("Sungrow", 2, model="SH10RT")
    assert sg_alarm["severity"] == "HIGH"
    assert "Over Voltage" in sg_alarm["title"]

    # Huawei SUN2000
    hw_alarm = decode_vendor_alarm("Huawei", 2062, model="SUN2000-10KTL-M1")
    assert hw_alarm["severity"] == "CRITICAL"
    assert "Arc Fault" in hw_alarm["title"]


def test_brand_alone_invariant_preserved():
    # Brand alone WITHOUT model must still return UNKNOWN severity
    assert decode_vendor_alarm("GoodWe", 1, model=None)["severity"] == "UNKNOWN"
    assert decode_vendor_alarm("Deye", 8, model="")["severity"] == "UNKNOWN"
    assert decode_vendor_alarm("Sungrow", 2, model="UNKNOWN")["severity"] == "UNKNOWN"


def test_get_vendor_registers_query():
    # Exact model provided returns verified registers
    gw_regs = get_vendor_registers("GoodWe", model="GW5K-ET")
    assert gw_regs["status"] == "UNCOMMISSIONED_REFERENCE"
    assert gw_regs["registers_count"] >= 20
    assert gw_regs["alarms_count"] >= 15
    assert "GW5K-ET" in gw_regs["supported_models"]

    # Brand alone without exact model preserves UNKNOWN and empty lists
    brand_only = get_vendor_registers("GoodWe")
    assert brand_only["status"] == "UNKNOWN"
    assert brand_only["registers"] == []
    assert brand_only["alarms"] == []

    # Unknown brand returns UNKNOWN
    unknown_regs = get_vendor_registers("NonExistentBrand123")
    assert unknown_regs["status"] == "UNKNOWN"
    assert unknown_regs["registers_count"] == 0
