import json

import httpx
import pytest

from solar_fleet.adapters.huawei import Huawei
from solar_fleet.domain import VendorError


async def test_header_auth_typed_identity_and_engineering_values():
    calls = []

    def handler(req):
        calls.append(req.url.path)
        body = json.loads(req.content)
        if req.url.path.endswith("/login"):
            assert body == {"userName": "fixture-user", "systemCode": "fixture-system"}
            return httpx.Response(
                200, json={"success": True, "data": None}, headers={"XSRF-TOKEN": "fixture-xsrf"}
            )
        assert req.headers["XSRF-TOKEN"] == "fixture-xsrf"
        if req.url.path.endswith("getStationList"):
            data = [{"stationCode": "plant-A", "stationName": "Fixture"}]
        elif req.url.path.endswith("getDevList"):
            data = [{"id": 71, "sn": "physical-SN", "devTypeId": 38, "model": "Fixture"}]
        else:
            assert body == {"devIds": "71", "devTypeId": 38}
            data = [
                {
                    "devId": 71,
                    "collectTime": 1700000000000,
                    "dataItemMap": {"a_u": 230.5, "grid_frequency": 50.01},
                }
            ]
        return httpx.Response(200, json={"success": True, "data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        a = Huawei(
            {"region": "global"},
            {"user_name": "fixture-user", "system_code": "fixture-system"},
            client=client,
        )
        assert (await a.stations())[0]["id"] == "plant-A"
        assert (await a.devices("plant-A"))[0]["deviceSn"] == "71"
        sample = (await a.latest(["71"]))[0]
        assert sample["collectionTime"] == 1700000000
        assert next(p for p in sample["dataList"] if p["key"] == "a_u")["value"] == 230.5
        assert calls.count("/thirdData/login") == 1


async def test_huawei_rejects_body_token_and_observes_quota():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(200, json={"success": True, "data": {"token": "not-a-header"}})
        )
    ) as c:
        a = Huawei({"region": "global"}, {"user_name": "fixture", "system_code": "fixture"}, client=c)
        with pytest.raises(VendorError, match="invalid_token"):
            await a.authenticate()
        with pytest.raises(VendorError, match="rate_limited"):
            a.validate_response({"success": False, "failCode": 407})
        with pytest.raises(VendorError):
            await a.authenticate()
