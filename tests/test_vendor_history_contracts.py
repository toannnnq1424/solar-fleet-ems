import json
from unittest.mock import AsyncMock

import httpx
import pytest

from solar_fleet.adapters.huawei import Huawei
from solar_fleet.adapters.solis import Solis
from solar_fleet.domain import VendorError


async def test_solis_native_history_fields_and_alarm_completeness():
    calls = []

    def handler(request):
        body = json.loads(request.content)
        calls.append((request.url.path, body))
        data = (
            {"page": {"total": 1, "records": [{"alarmDeviceSn": "SIM-SN"}]}}
            if request.url.path.endswith("alarmList")
            else []
        )
        return httpx.Response(200, json={"success": True, "code": "0", "data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = Solis({"region": "global"}, {"key_id": "fixture", "key_secret": "fixture"}, client=client)
        await adapter.history_day("SIM-SN", "2026-09-22", money="VND", time_zone=7)
        await adapter.history_month("SIM-SN", "2026-09", money="VND")
        await adapter.history_year("SIM-SN", "2026", money="VND")
        assert await adapter.alerts(station_id=23, serial="SIM-SN", begin_date="2026-09-01")
    assert calls == [
        ("/v1/api/inverterDay", {"sn": "SIM-SN", "time": "2026-09-22", "money": "VND", "timeZone": 7}),
        ("/v1/api/inverterMonth", {"sn": "SIM-SN", "month": "2026-09", "money": "VND"}),
        ("/v1/api/inverterYear", {"sn": "SIM-SN", "year": "2026", "money": "VND"}),
        ("/v1/api/alarmList", {"stationId": 23, "alarmDeviceSn": "SIM-SN", "alarmBeginTime": "2026-09-01"}),
    ]


async def test_solis_rejects_invalid_dates_and_truncated_alarms():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda req: httpx.Response(
                200, json={"success": True, "code": "0", "data": {"page": {"total": 3, "records": []}}}
            )
        )
    ) as client:
        adapter = Solis({"region": "global"}, {"key_id": "fixture", "key_secret": "fixture"}, client=client)
        with pytest.raises(VendorError, match="invalid_history_date"):
            await adapter.history_day("SIM", "2026-02-30", money="USD", time_zone=0)
        with pytest.raises(VendorError, match="invalid_history_currency"):
            await adapter.history_year("SIM", "2026", money="usd")
        with pytest.raises(VendorError, match="pagination_contract_incomplete"):
            await adapter.alerts(serial="SIM")


async def test_huawei_history_uses_milliseconds_and_documented_endpoint():
    adapter = Huawei({"region": "global"}, {"user_name": "fixture", "system_code": "fixture"})
    adapter.read = AsyncMock(return_value={"success": True, "data": []})
    await adapter.history("71", 38, 1700000000000)
    adapter.read.assert_awaited_once_with(
        "/thirdData/getDevFiveMinutes", {"devIds": "71", "devTypeId": 38, "collectTime": 1700000000000}
    )
    for invalid in (1700000000, True, "1700000000000", float("nan")):
        with pytest.raises(VendorError, match="milliseconds"):
            await adapter.history_station_day("SIM", invalid)
    assert adapter.read.await_count == 1
