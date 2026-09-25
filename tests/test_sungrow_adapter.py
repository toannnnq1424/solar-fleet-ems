import json

import httpx
import pytest

from solar_fleet.adapters.sungrow import Sungrow
from solar_fleet.domain import VendorError


async def test_openapi_transport_device_key_and_unmapped_native_points():
    calls = []

    def handler(req):
        calls.append(req.url.path)
        b = json.loads(req.content)
        assert (
            req.url.host == "gateway.isolarcloud.com.hk" and req.headers["x-access-key"] == "fixture-secret"
        )
        assert req.headers["sys_code"] == "901" and b["appkey"] == "fixture-app"
        if req.url.path == "/openapi/login":
            assert b["user_account"] == "fixture-user"
            data = {"login_state": "1", "token": "fixture-token"}
        elif req.url.path == "/openapi/getDeviceList":
            assert b["token"] == "fixture-token" and b["ps_id"] == "123"
            data = {"rowCount": 1, "pageList": [{"ps_key": "123_1_0_1", "device_type": 1, "dev_status": 1}]}
        else:
            assert req.url.path == "/openapi/getDeviceRealTimeData"
            assert b["ps_key_list"] == ["123_1_0_1"] and b["point_id_list"] == [24, 27]
            data = {
                "device_point_list": [
                    {"device_point": {"ps_key": "123_1_0_1", "p24": 230.5, "p27": 0, "dev_status": 1}}
                ]
            }
        return httpx.Response(200, json={"result_code": "1", "result_data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        a = Sungrow(
            {"region": "global"},
            {
                "app_key": "fixture-app",
                "app_secret": "fixture-secret",
                "user_account": "fixture-user",
                "user_password": "fixture-password",
                "plant_ids": "123",
                "point_ids": "24,27",
            },
            client=c,
        )
        await a.stations()
        await a.devices("123")
        s = (await a.latest(["123_1_0_1"]))[0]
        assert s["collectionTime"] is None
        assert s["dataList"] == [
            {"key": "p24", "value": 230.5, "unit": None},
            {"key": "p27", "value": 0, "unit": None},
        ]
        assert calls.count("/openapi/login") == 1


async def test_sungrow_rejects_login_failure_even_when_result_code_succeeds():
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(
            lambda r: httpx.Response(
                200, json={"result_code": 1, "result_data": {"login_state": 0, "token": "fixture"}}
            )
        )
    ) as c:
        a = Sungrow(
            {"region": "global"},
            {k: "fixture" for k in ("app_key", "app_secret", "user_account", "user_password")},
            client=c,
        )
        with pytest.raises(VendorError, match="invalid_token"):
            await a.authenticate()
