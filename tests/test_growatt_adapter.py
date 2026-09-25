from urllib.parse import parse_qs

import httpx
import pytest

from solar_fleet.adapters.growatt import Growatt
from solar_fleet.domain import VendorError


@pytest.mark.parametrize(
    "kind,path,param", [(5, "mix/mix_last_data", "mix_sn"), (7, "tlx/tlx_last_data", "tlx_sn")]
)
async def test_family_transport_and_no_modbus_rescaling(kind, path, param):
    def handler(req):
        assert req.headers["token"] == "fixture-token"
        if req.url.path == "/v1/plant/list":
            assert req.method == "GET" and req.url.params["page"] == "1"
            data = {"count": 1, "plants": [{"plant_id": 21, "name": "Fixture"}]}
        elif req.url.path == "/v1/device/list":
            assert req.method == "GET" and req.url.params["plant_id"] == "21"
            data = {"count": 1, "devices": [{"device_sn": "fixture-SN", "type": kind, "lost": False}]}
        else:
            assert req.url.path == "/v1/device/" + path and req.method == "POST"
            assert parse_qs(req.content.decode()) == {param: ["fixture-SN"]}
            data = {"vac1": 230.5, "frequency": 50.01, "pac": 0}
        return httpx.Response(200, json={"error_code": 0, "data": data})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as c:
        a = Growatt({"region": "global"}, {"token": "fixture-token"}, client=c)
        await a.stations()
        await a.devices(21)
        sample = (await a.latest(["fixture-SN"]))[0]
        assert sample["collectionTime"] is None
        assert {p["key"]: p["value"] for p in sample["dataList"]} == {
            "vac1": 230.5,
            "frequency": 50.01,
            "pac": 0,
        }
        with pytest.raises(VendorError, match="family_contract"):
            await a.latest(["unknown-SN"])


async def test_growatt_rejects_error_envelope_and_no_password_fallback():
    with pytest.raises(VendorError):
        Growatt({"region": "global"}, {"user_name": "x", "password": "x"})
    async with httpx.AsyncClient(
        transport=httpx.MockTransport(lambda r: httpx.Response(200, json={"error_code": 10001, "data": {}}))
    ) as c:
        a = Growatt({"region": "global"}, {"token": "fixture"}, client=c)
        with pytest.raises(VendorError, match="request_rejected"):
            await a.stations()
