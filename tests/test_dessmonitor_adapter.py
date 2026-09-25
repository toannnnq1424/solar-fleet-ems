"""Synthetic cloud contracts; no vendor account, local logger or physical write."""

import asyncio
import hashlib
import logging
from urllib.parse import parse_qs

import httpx
import pytest

from solar_fleet.adapters.dessmonitor import PLATFORMS, Dessmonitor
from solar_fleet.budgets import Budgets
from solar_fleet.domain import VendorError

CREDENTIALS = {
    "user_name": "SIMULATOR + thử@example.invalid",
    "password": "SIMULATOR password + & 中文",
    "company_key": "SIMULATOR-company+key",
}
SESSION = {"token": "SIMULATOR-token+&=", "secret": "SIMULATOR-secret", "expire": 3600}
POINTS = [
    {"title": "PV energy", "val": "1234", "unit": "Wh"},
    {"title": "Battery energy", "val": "1.234", "unit": "kWh"},
    {"title": "Apparent power", "val": "650", "unit": "VA"},
    {"title": "Operating state", "val": "Charging", "unit": ""},
    {"title": "Nhiệt độ", "val": "-3.5", "unit": "°C"},
]


class CloudFixture:
    def __init__(self):
        self.calls = []
        self.overrides = {}
        self.plants = [{"pid": 1, "name": "SIMULATOR plant"}]
        self.collectors = [{"pn": "SIMULATOR-PN", "pid": 1}]
        self.devices = [{"sn": "SIMULATOR-SN", "devcode": 518, "devaddr": 1}]
        self.points = POINTS

    def __call__(self, request):
        query = parse_qs(request.url.query.decode("ascii"))
        action = query["action"][0]
        self.calls.append((request, query))
        assert request.method == "GET"
        if action in self.overrides:
            value = self.overrides[action]
            if isinstance(value, Exception):
                raise value
            if callable(value):
                value = value(query)
            if isinstance(value, httpx.Response):
                return value
            return httpx.Response(200, json=value)
        if action in ("auth", "authSource"):
            data = SESSION
        elif action == "queryPlants":
            data = {"plant": self.plants, "total": len(self.plants)}
        elif action == "webQueryCollectorsEs":
            offset = int(query["page"][0]) * 50
            data = {"collector": self.collectors[offset : offset + 50], "total": len(self.collectors)}
        elif action == "queryCollectorDevices":
            data = {"dev": self.devices}
        elif action == "queryDeviceLastData":
            data = self.points
        else:
            raise AssertionError("Fixture rejects any undocumented or write action")
        return httpx.Response(200, json={"err": 0, "dat": data})


def adapter(cloud, platform="dessmonitor"):
    return Dessmonitor(
        {"id": "SIMULATOR-account", "vendor": "Eybond / SmartESS", "region": platform},
        CREDENTIALS,
        transport=httpx.MockTransport(cloud),
        budgets=Budgets(1000, 1000, 1000),
    )


async def discover(client):
    await client.stations()
    return await client.devices(1)


@pytest.mark.parametrize("platform", list(PLATFORMS))
async def test_wire_signatures_platform_encoding_and_native_values(platform, caplog):
    cloud = CloudFixture()
    client = adapter(cloud, platform)
    public_requests = []

    async def hook(request):
        public_requests.append((str(request.url), repr(request.extensions)))

    client.client.event_hooks["request"] = [hook]
    with caplog.at_level(logging.INFO, logger="httpx"):
        devices = await discover(client)
        readings = await client.latest(["SIMULATOR-SN"])
    assert devices[0]["productId"] == 518
    assert devices[0]["model"] is None
    assert devices[0]["connectStatus"] is None
    assert readings[0]["collectionTime"] is None
    assert readings[0]["timestamp_state"] == "SOURCE_TIMESTAMP_NOT_PROVIDED"
    assert [(p["title"], p["value"], p["unit"]) for p in readings[0]["dataList"]] == [
        (p["title"], p["val"], p["unit"]) for p in POINTS
    ]
    expected_host, expected_auth, expected_source = PLATFORMS[platform]
    assert cloud.calls[0][1]["action"] == [expected_auth]
    assert cloud.calls[0][1]["source"] == [expected_source]
    assert cloud.calls[0][1]["usr"] == [CREDENTIALS["user_name"]]
    assert cloud.calls[0][1]["_app_id_"] == ["solar-fleet-ems"]
    for request, query in cloud.calls:
        assert str(request.url).startswith(expected_host + "/public/?")
        wire_query = request.url.query.decode("ascii")
        action_string = "&action=" + wire_query.split("&action=", 1)[1]
        login = query["action"][0] in ("auth", "authSource")
        prefix = (
            hashlib.sha1(CREDENTIALS["password"].encode()).hexdigest()
            if login
            else SESSION["secret"] + SESSION["token"]
        )
        expected = hashlib.sha1((query["salt"][0] + prefix + action_string).encode()).hexdigest()
        assert query["sign"] == [expected]
        if not login:
            assert query["token"] == [SESSION["token"]]
    assert all(url == expected_host + "/public/" for url, _ in public_requests)
    assert "SIMULATOR" not in caplog.text
    assert all("SIMULATOR" not in extensions for _, extensions in public_requests)
    assert client.signed_transport.query.get() is None
    before = len(cloud.calls)
    with pytest.raises(VendorError, match="read_endpoint_not_allowed"):
        await client.read("ctrlDevice", {})
    with pytest.raises(VendorError, match="read_only_adapter"):
        await client.send({})
    assert len(cloud.calls) == before
    await client.close()


async def test_concurrent_auth_once_and_expired_session_renews():
    cloud = CloudFixture()
    client = adapter(cloud)
    await asyncio.gather(*(client.authenticate() for _ in range(8)))
    assert len(cloud.calls) == 1
    client.expires_at = 0
    await client.stations()
    assert [q["action"][0] for _, q in cloud.calls] == ["authSource", "authSource", "queryPlants"]
    await client.close()


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"err": False, "dat": SESSION},
        {"err": "0", "dat": SESSION},
        {"err": 1, "desc": "SIMULATOR-secret echoed"},
        {"err": 0, "dat": {}},
        {"err": 0, "dat": {**SESSION, "expire": True}},
        {"err": 0, "dat": {**SESSION, "expire": -1}},
    ],
)
async def test_invalid_auth_is_not_success_or_secret_bearing_error(payload):
    cloud = CloudFixture()
    cloud.overrides["authSource"] = payload
    client = adapter(cloud)
    with pytest.raises(VendorError) as raised:
        await client.stations()
    assert "SIMULATOR" not in str(raised.value)
    assert client.access_token is None
    assert len(cloud.calls) == 1
    assert client.signed_transport.query.get() is None
    await client.close()


@pytest.mark.parametrize("status", [401, 403, 429, 302, 500])
async def test_http_error_no_replay_no_platform_fallback(status):
    cloud = CloudFixture()
    cloud.overrides["queryPlants"] = httpx.Response(
        status, headers={"Retry-After": "120", "Location": "https://example.invalid/?token=SECRET"}
    )
    client = adapter(cloud)
    with pytest.raises(VendorError):
        await client.stations()
    assert len(cloud.calls) == 2
    if status in (401, 403):
        assert client.access_token is None
    if status == 429:
        with pytest.raises(VendorError, match="vendor_backoff_active"):
            await client.stations()
        assert len(cloud.calls) == 2
    assert all(req.url.host == "api.dessmonitor.com" for req, _ in cloud.calls)
    await client.close()


async def test_network_error_drops_signed_url_and_context():
    cloud = CloudFixture()
    cloud.overrides["authSource"] = httpx.ConnectError("SIMULATOR signed request secret")
    client = adapter(cloud)
    with pytest.raises(VendorError, match="vendor_network_outcome_unknown") as raised:
        await client.stations()
    assert "SIMULATOR" not in str(raised.value)
    assert raised.value.__suppress_context__
    assert client.signed_transport.query.get() is None
    await client.close()


async def test_collector_pagination_and_unique_device_routes():
    cloud = CloudFixture()
    cloud.collectors = [{"pn": f"SIMULATOR-PN-{i}", "pid": 1} for i in range(51)]
    cloud.overrides["queryCollectorDevices"] = lambda q: {
        "err": 0,
        "dat": {"dev": [{"sn": q["pn"][0] + "-SN", "devcode": 2477, "devaddr": 0}]},
    }
    client = adapter(cloud)
    devices = await discover(client)
    assert len(devices) == 51
    assert [q["page"][0] for _, q in cloud.calls if q["action"] == ["webQueryCollectorsEs"]] == ["0", "1"]
    await client.latest([devices[-1]["deviceSn"]])
    assert cloud.calls[-1][1]["pn"] == ["SIMULATOR-PN-50"]
    assert cloud.calls[-1][1]["devcode"] == ["2477"]
    await client.close()


@pytest.mark.parametrize(
    "kind",
    [
        "unknown_plant_page",
        "duplicate_plant",
        "duplicate_collector",
        "wrong_collector_plant",
        "wrong_device_collector",
        "duplicate_serial",
        "missing_code",
    ],
)
async def test_inventory_anomalies_are_rejected(kind):
    cloud = CloudFixture()
    if kind == "unknown_plant_page":
        cloud.overrides["queryPlants"] = {"err": 0, "dat": {"plant": [{"pid": i} for i in range(50)]}}
    elif kind == "duplicate_plant":
        cloud.plants *= 2
    elif kind == "duplicate_collector":
        cloud.collectors *= 2
    elif kind == "wrong_collector_plant":
        cloud.collectors[0]["pid"] = 2
    elif kind == "wrong_device_collector":
        cloud.devices[0]["pn"] = "OTHER-COLLECTOR"
    elif kind == "duplicate_serial":
        cloud.devices *= 2
    elif kind == "missing_code":
        del cloud.devices[0]["devcode"]
    client = adapter(cloud)
    with pytest.raises(VendorError):
        await discover(client)
    assert not client.routes
    await client.close()


async def test_unknown_device_and_partial_discovery_do_not_create_routes():
    cloud = CloudFixture()
    client = adapter(cloud)
    with pytest.raises(VendorError, match="device_discovery_required"):
        await client.latest(["SIMULATOR-SN"])
    assert cloud.calls == []
    await discover(client)
    cloud.points = [POINTS[0], POINTS[0]]
    with pytest.raises(VendorError, match="invalid_point_identity"):
        await client.latest(["SIMULATOR-SN"])
    # A check/rediscovery clears previous routes; old serials cannot survive revocation.
    cloud.plants = []
    await client.stations()
    with pytest.raises(VendorError, match="device_discovery_required"):
        await client.latest(["SIMULATOR-SN"])
    await client.close()


async def test_point_keys_are_stable_across_response_order():
    cloud = CloudFixture()
    client = adapter(cloud)
    await discover(client)
    first = (await client.latest(["SIMULATOR-SN"]))[0]["dataList"]
    cloud.points = list(reversed(POINTS))
    second = (await client.latest(["SIMULATOR-SN"]))[0]["dataList"]
    assert {p["title"]: p["key"] for p in first} == {p["title"]: p["key"] for p in second}
    await client.close()
