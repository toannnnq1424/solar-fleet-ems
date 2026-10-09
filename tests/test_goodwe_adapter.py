import json

import httpx
import pytest

from solar_fleet.adapters.goodwe import GoodWe
from solar_fleet.adapters.plugins import builtins
from solar_fleet.domain import VendorError


async def test_sems_full_token_invert_full_and_explicit_plant_scope():
    token = {"token": "fixture", "uid": "fixture-user", "timestamp": 1700000000, "version": "v2.0.4"}

    def handler(req):
        if req.url.path.endswith("CrossLogin"):
            return httpx.Response(
                200, json={"code": 0, "data": token, "api": "https://eu.semsportal.com/api/"}
            )
        assert req.url.host == "eu.semsportal.com"
        assert json.loads(req.headers["Token"]) == token
        assert json.loads(req.content) == {"powerStationId": "fixture-plant"}
        return httpx.Response(
            200,
            json={
                "code": 0,
                "data": {
                    "inverter": [
                        {
                            "sn": "fixture-SN",
                            "model_type": "Fixture",
                            "invert_full": {"vac_r": 230.5, "grid_frequency": 50.01, "battery_soc": 0},
                        }
                    ]
                },
            },
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        a = GoodWe(
            {"region": "global"},
            {"account": "fixture", "password": "fixture", "plant_ids": "fixture-plant"},
            client=c,
        )
        assert (await a.stations())[0]["id"] == "fixture-plant"
        await a.devices("fixture-plant")
        s = (await a.latest(["fixture-SN"]))[0]
        assert s["collectionTime"] is None
        assert s["deviceState"] is None
        assert builtins().require("GoodWe").measurement(s).online is None
        assert {p["key"]: p["value"] for p in s["dataList"]} == {
            "vac_r": 230.5,
            "grid_frequency": 50.01,
            "battery_soc": 0,
        }


@pytest.mark.parametrize(
    "route",
    ["https://attacker.invalid/api", "http://eu.semsportal.com/api", "https://eu.semsportal.com:444/api"],
)
async def test_sems_never_forwards_token_to_untrusted_route(route):
    calls = []

    def handler(req):
        calls.append(str(req.url))
        return httpx.Response(
            200, json={"code": 0, "data": {"token": "fixture", "uid": "fixture"}, "api": route}
        )

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        a = GoodWe({"region": "global"}, {"account": "fixture", "password": "fixture"}, client=c)
        with pytest.raises(VendorError, match="unrecognized_goodwe_api_route"):
            await a.stations()
    assert len(calls) == 1


@pytest.mark.parametrize("native_status", [None, 0, 1, "offline", "online"])
async def test_cached_sems_values_do_not_prove_connectivity(native_status):
    """Synthetic transport only; a status label is not a reviewed status enum."""
    row = {
        "sn": "fixture-cached-device",
        "status": native_status,
        "invert_full": {"battery_soc": 0, "active_power": 0},
    }

    def handler(req):
        if req.url.path.endswith("CrossLogin"):
            return httpx.Response(200, json={"code": 0, "data": {"token": "fixture", "uid": "fixture"}})
        return httpx.Response(200, json={"code": 0, "data": {"inverter": [row]}})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWe(
            {"region": "global"},
            {"account": "fixture", "password": "fixture", "plant_ids": "fixture-plant"},
            client=client,
        )
        discovered = (await adapter.devices("fixture-plant"))[0]
        latest = (await adapter.latest(["fixture-cached-device"]))[0]
        assert discovered["connectStatus"] is None
        assert latest["deviceState"] is None
        assert latest["native"]["status"] == native_status
        observation = builtins().require("GoodWe").measurement(latest)
        assert observation.online is None
        assert observation.timestamp is None
        assert all(point["value"] == 0 for point in observation.points)
