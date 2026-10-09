"""Synthetic SEMS+ contracts only. No account/session or equipment access."""

import base64
import hashlib
import json

import httpx
import pytest

from solar_fleet.adapters.goodwe import GoodWe
from solar_fleet.adapters.goodwe_plus import DEVICES, EQUIPMENT, FLOW, LOGIN, STATIONS, STATISTICS, GoodWePlus
from solar_fleet.adapters.plugins import builtins
from solar_fleet.domain import VendorError

CREDENTIALS = {"account": "synthetic@example.invalid", "password": "SYNTHETIC-password",
               "vendor_terms_accepted": True}
CONFIG = {"platform": "sems_plus", "region": "hk"}


def envelope(data, code="00000"):
    return httpx.Response(200, json={"code": code, "data": data})


def reply(req):
    if req.url.path == FLOW:
        return envelope({'id': 'fixture-plant', 'pSystem': 0, 'pAc': 9, 'pConsum': 1.2,
                         'pBat': -0.5, 'pGrid': -1.7, 'soc': 40, 'refreshTime': '2026-10-08T06:45:00'})
    if req.url.path == STATISTICS:
        body = json.loads(req.content)
        # hk live schema: no flat summaries for this item selection; bucket
        # labels depend on dimension. Deliberately no blanket YYYY-MM-DD stub.
        bucket = body['startTime'][:{'day': 10, 'month': 7, 'year': 4}[body['dimension']]]
        return envelope({
                         'dataList': [{'item': 'proSystemTotalStats', 'unit': 'kWh',
                                       'statisticsList': [{'date': bucket, 'val': 12.0}]}]})
    if req.url.path == LOGIN:
        return envelope({"uid": "fixture-user", "token": "fixture-token", "timestamp": 123,
                         "api": "https://hk-gateway.semsportal.com/web/sems"})
    if req.url.path == STATIONS:
        return envelope({"dataList": [{"id": "fixture-plant", "stationName": "Synthetic only"}]})
    if req.url.path == DEVICES:
        return envelope({"deviceDetailList": [
            {"deviceType": kind, "statusDetailList": [{"detailMap": {sn: {"sn": sn, "status": 5}}}]}
            for kind, sn in (("INVERTER", "fixture-inverter"), ("DATA_LOGGER", "fixture-logger"),
                             ("SMART_METER", "fixture-meter"))
        ]})
    if req.url.path.endswith("/relatedDevices"):
        return envelope([{"sn": "fixture-battery", "type": "BAT_SYS"}])
    if req.url.path.endswith('/telecounting'):
        return envelope([
            {'code': 'telecounting_real', 'factors': [{'code': 'ratedPower', 'unit': 'kW', 'data': '10'}]},
            {'code': 'telecounting_today', 'factors': [
                {'code': 'proPvStatsToday', 'unit': 'kWh', 'data': '7.5'},
                {'code': 'proCharStatsToday', 'unit': 'kWh', 'data': '0'},
                {'code': 'proDischarStatsToday', 'unit': 'kWh', 'data': None}]},
        ])
    if req.url.path.endswith("/telemetry"):
        return envelope([{"code": "ac", "factors": [
            {"code": "pAc", "data": 0, "unit": "kW"},
            {"code": "powerFactor", "data": None, "unit": ""},
        ]}])
    raise AssertionError(req.url.path)


async def test_semsplus_auth_typed_inventory_native_read_through_same_plugin():
    calls = []

    def handler(req):
        calls.append(req)
        return reply(req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWe(CONFIG, CREDENTIALS, client=client)
        assert isinstance(adapter, GoodWePlus)
        stations = await adapter.stations()
        devices = await adapter.devices(stations[0]["id"])
        assert {d["deviceType"] for d in devices} == {"INVERTER", "DATA_LOGGER", "SMART_METER", "BAT_SYS"}
        latest = await adapter.latest(["fixture-inverter"])
        observation = builtins().require("GoodWe").measurement(latest[0])
        assert observation.online is None and observation.timestamp is None
        assert observation.points[0] == {"key": "telemetry:ac:pAc", "value": 0, "unit": "kW", "group_id": "ac"}
        assert observation.points[1]["value"] is None
        assert not adapter.inventory_ready  # only the controller commits complete discovery
    auth = calls[0]
    assert auth.url.host == "hk-semsplus.goodwe.com"
    payload = json.loads(auth.content)
    expected = hashlib.md5(CREDENTIALS["password"].encode(), usedforsecurity=False).hexdigest()
    assert payload["pwd"] == base64.b64encode(expected.encode()).decode()
    assert payload["agreement"] == 1
    assert all(r.url.host == "hk-gateway.semsportal.com" for r in calls[1:])
    assert all(CREDENTIALS["password"] not in str(r.headers) for r in calls)
    for req in calls:
        token = json.loads(req.headers["token"])
        digest, stamp = base64.b64decode(req.headers["x-signature"]).decode().split("@")
        assert digest == hashlib.sha256(f'{stamp}@{token["uid"]}@{token["token"]}'.encode()).hexdigest()


@pytest.mark.parametrize("route", ["https://attacker.invalid/web/sems", "http://hk-gateway.semsportal.com/web/sems",
                                  "https://eu-gateway.semsportal.com/web/sems", "https://hk-gateway.semsportal.com:444/web/sems",
                                  "https://hk-gateway.semsportal.com/web/sems?token=leak", "https://[malformed"])
async def test_no_redirect_region_fallback_or_second_login(route):
    calls = []

    def handler(req):
        calls.append(req)
        return envelope({"uid": "fixture", "token": "fixture", "api": route})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        with pytest.raises(VendorError, match="unrecognized_goodwe_api_route"):
            await adapter.stations()
        assert adapter.access_token is None
    assert len(calls) == 1


@pytest.mark.parametrize("code", ["C0602", "GY0429", "unknown", "SYNTHETIC-password"])
async def test_errors_never_leak_vendor_message_or_retry_login(code):
    calls = []

    def handler(req):
        calls.append(req)
        return httpx.Response(200, json={"code": code, "msg": CREDENTIALS["password"]})

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        with pytest.raises(VendorError) as error:
            await adapter.stations()
        assert CREDENTIALS["password"] not in str(error.value)
        if code == "GY0429":
            with pytest.raises(VendorError, match="vendor_backoff_active"):
                await adapter.stations()
    assert len(calls) == 1


async def test_discovery_bounds_repeated_pages_and_scope():
    def handler(req):
        if req.url.path == STATIONS:
            return envelope({"dataList": [{"id": f"fixture-{i}"} for i in range(50)]})
        return reply(req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        with pytest.raises(VendorError, match="station_discovery_required"):
            await adapter.devices("unrelated")
        with pytest.raises(VendorError, match="read_endpoint_not_allowed"):
            await adapter.read("/write")
        with pytest.raises(VendorError, match="vendor_duplicate_station"):
            await adapter.stations()
        assert not adapter.plant_ids and not adapter.device_routes


async def test_partial_related_discovery_is_not_cached_and_unknown_devices_not_read():
    def handler(req):
        if req.url.path.endswith("/relatedDevices"):
            return envelope([{"sn": "fixture-logger", "type": "BAT_SYS"}])
        return reply(req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await adapter.stations()
        with pytest.raises(VendorError, match="ambiguous_device_site_binding"):
            await adapter.devices("fixture-plant")
        assert not adapter.device_routes
        with pytest.raises(VendorError, match="device_discovery_required"):
            await adapter.latest(["fixture-inverter"])
        with pytest.raises(VendorError, match="read_endpoint_not_allowed"):
            await adapter.read(EQUIPMENT + "unrelated/telemetry")


def test_factory_and_consent_fail_closed_before_network():
    assert builtins().require("GoodWe").version == "0.4.0"
    with pytest.raises(VendorError, match="goodwe_terms_confirmation_required"):
        GoodWePlus(CONFIG, {**CREDENTIALS, "vendor_terms_accepted": False})
    with pytest.raises(VendorError, match="unsupported_data_center"):
        GoodWePlus({**CONFIG, "region": "auto"}, CREDENTIALS)


@pytest.mark.parametrize('omitted', [False, True])
async def test_null_readings_do_not_discard_healthy_siblings_or_invent_connectivity(omitted):
    def handler(req):
        if req.url.path.endswith(('fixture-logger/telemetry', 'fixture-battery/telemetry')):
            return httpx.Response(200, json={'code': '00000'}) if omitted else envelope(None)
        if req.url.path.endswith('/relatedDevices'):
            return envelope([{'sn': 'fixture-battery', 'type': 'BATTERY_BANK'}])
        return reply(req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await adapter.stations()
        devices = await adapter.devices('fixture-plant')
        rows = await adapter.latest([d['deviceSn'] for d in devices])
        assert len(rows) == 4
        assert sum(bool(row['dataList']) for row in rows) == 2
        for row in rows:
            assert row['deviceState'] is None and row['collectionTime'] is None
            if not row['dataList']:
                assert row['reading_state'] == 'NO_VENDOR_TELEMETRY'
            observation = builtins().require('GoodWe').measurement(row)
            assert observation.timestamp is None and observation.online is None


@pytest.mark.parametrize('suffix', ['telemetry', 'telecounting', 'relatedDevices'])
@pytest.mark.parametrize('code', ['00000', 'AUTH_DENIED'])
async def test_missing_data_is_tolerated_only_on_known_empty_telemetry_kinds(suffix, code):
    def handler(req):
        if req.url.path.endswith('fixture-logger/' + suffix):
            return httpx.Response(200, json={'code': code})
        return reply(req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await adapter.stations()
        await adapter.devices('fixture-plant')
        path = EQUIPMENT + 'fixture-logger/' + suffix
        if suffix == 'telemetry' and code == '00000':
            assert await adapter.read(path) is None
        else:
            with pytest.raises(VendorError):
                await adapter.read(path)


@pytest.mark.parametrize('payload', [
    {'code': '00000'}, {'code': '00000', 'data': {}},
    {'code': '00000', 'data': 'null'}, {'code': '00000', 'data': [None]},
    {'code': 'GY0429', 'data': None}, {'code': 'AUTH_DENIED', 'data': None},
])
async def test_no_data_exception_is_not_a_blanket_error_fallback(payload):
    def handler(req):
        if req.url.path.endswith('/telemetry'):
            return httpx.Response(200, json=payload)
        return reply(req)

    async with httpx.AsyncClient(transport=httpx.MockTransport(handler)) as client:
        adapter = GoodWePlus(CONFIG, CREDENTIALS, client=client)
        await adapter.stations()
        await adapter.devices('fixture-plant')
        with pytest.raises(VendorError):
            await adapter.latest(['fixture-inverter'])


def test_native_aliases_are_display_metadata_not_semantic_mapping():
    points = GoodWePlus.points([{'code': 'test', 'alias': 'Synthetic group', 'factors': [
        {'code': 'test-power', 'alias': '<b>Untrusted alias</b>', 'data': '0', 'unit': 'kW'},
        {'code': 'missing', 'alias': {'invalid': True}, 'data': None},
    ]}], 'telemetry')
    assert points[0] == {'key': 'telemetry:test:test-power', 'value': '0', 'unit': 'kW',
                         'title': '<b>Untrusted alias</b>', 'group': 'Synthetic group', 'group_id': 'test'}
    assert 'title' not in points[1] and points[1]['value'] is None
