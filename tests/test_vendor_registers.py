import pytest

from solar_fleet.vendor_registers import decode_vendor_alarm


@pytest.mark.parametrize(
    "brand", ["GoodWe", "Sungrow", "Deye", "Solis", "Growatt", "Huawei", "Bluesun", "UNKNOWN"]
)
def test_brand_alone_does_not_identify_register_or_fault_semantics(brand):
    result = decode_vendor_alarm(brand, 1)
    assert result["severity"] == "UNKNOWN"
    assert result["fault_code"] == 1
