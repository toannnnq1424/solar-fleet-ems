"""Synthetic contract fixtures only. No browser credentials or external HTTP."""

import base64
import hashlib
import hmac
import json

import httpx
import pytest
from cryptography.fernet import Fernet

from solar_fleet.adapters.solarman import Solarman
from solar_fleet.adapters.solis import Solis, signed_headers
from solar_fleet.controller import Controller
from solar_fleet.domain import VendorError, utcnow
from solar_fleet.security import Vault

SOLIS_KEYS = {"key_id": "SIM-ID", "key_secret": "SIM-SECRET"}
SOLARMAN_KEYS = {
    "app_id": "SIM-APP",
    "app_secret": "SIM-SECRET",
    "identity_field": "email",
    "identity_value": "sim@example.invalid",
    "password_sha256": "a" * 64,
    "org_id": 123,
}


def token():
    return {"success": True, "access_token": "SIM-TOKEN", "token_type": "bearer", "expires_in": "3600"}


def test_solis_signature_covers_exact_utf8_bytes_path_and_headers():
    body = '{"name":"Điện"}'.encode()
    date = "Sun, 13 Sep 2026 10:00:00 GMT"
    headers = signed_headers("/v1/api/inverterList", body, "SIM-ID", "SIM-SECRET", date)
    md5 = base64.b64encode(hashlib.md5(body).digest()).decode()
    expected = base64.b64encode(
        hmac.new(
            b"SIM-SECRET",
            (
                "POST\n" + md5 + "\napplication/json;charset=UTF-8\n" + date + "\n/v1/api/inverterList"
            ).encode(),
            hashlib.sha1,
        ).digest()
    ).decode()
    assert headers["Authorization"] == "API SIM-ID:" + expected
    assert headers["Content-MD5"] == md5
    assert headers != signed_headers("/v1/api/inverterDetail", body, "SIM-ID", "SIM-SECRET", date)


async def test_solis_discovery_and_telemetry_keep_namespace_and_unknown_timestamp(store):
    def handler(request):
        assert request.url.host == "www.soliscloud.com" and request.url.port == 13333
        body = json.loads(request.content)
        path = request.url.path
        if path.endswith("userStationList"):
            data = {"page": {"records": [{"id": 101, "stationName": "SIM-PLANT"}], "total": 1}}
        elif path.endswith("inverterList"):
            assert body == {"stationId": 101}
            data = {
                "page": {
                    "records": [{"sn": "SIM-INV", "stationId": 101, "state": 1, "productModel": "SIM-MODEL"}],
                    "total": 1,
                }
            }
        else:
            assert body == {"sn": "SIM-INV"}
            data = {"sn": "SIM-INV", "state": 1, "pac": 5.1, "pacStr": "kW", "dataTimestamp": 1234567890000}
        return httpx.Response(200, json={"success": True, "code": "0", "data": data})

    config = {"id": "sim", "vendor": "Solis", "region": "global", "enabled": True}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = Solis(config, SOLIS_KEYS, client=httpx.AsyncClient(transport=httpx.MockTransport(handler)))
    controller.adapters["sim"] = adapter
    await controller.poll()
    assert store.get("integration_state", "sim")["state"] == "CONNECTED"
    device = controller.device(store.list("device")[0]["id"])
    assert device.identity.vendor == "Solis" and device.identity.model == "SIM-MODEL"
    sample = controller.latest(device)["samples"][0]
    assert sample["metric"] == "solis.pac" and sample["value"] == 5.1 and sample["unit"] == "kW"
    assert sample["source_timestamp"] is None and sample["stale"] is True
    assert sample["quality"] == "UNVERIFIED"
    await adapter.close()


@pytest.mark.parametrize("total,records", [(101, [{"id": 1}]), (None, []), (0, [{"id": 1}])])
async def test_solis_never_claims_incomplete_discovery_is_complete(total, records):
    adapter = Solis(
        {"region": "global"},
        SOLIS_KEYS,
        client=httpx.AsyncClient(
            transport=httpx.MockTransport(
                lambda _: httpx.Response(
                    200,
                    json={
                        "success": True,
                        "code": "0",
                        "data": {"page": {"total": total, "records": records}},
                    },
                )
            )
        ),
    )
    with pytest.raises(VendorError):
        await adapter.stations()
    await adapter.close()


async def test_solarman_org_token_pagination_and_native_timestamp(store):
    calls = []

    def handler(request):
        calls.append(request.url.path)
        body = json.loads(request.content)
        if request.url.path.endswith("token"):
            assert request.url.params["appId"] == "SIM-APP"
            assert body["orgId"] == 123 and body["password"] == "a" * 64
            assert "Authorization" not in request.headers
            return httpx.Response(200, json=token())
        assert request.headers["Authorization"] == "bearer SIM-TOKEN"
        if request.url.path.endswith("list"):
            response = {
                "stationList": [{"id": 11, "name": "SIM-STATION", "regionTimezone": "UTC"}],
                "total": 1,
            }
        elif request.url.path.endswith("device"):
            response = {
                "deviceListItems": [{"deviceSn": "SIM-SN", "deviceType": "INVERTER", "connectStatus": 1}],
                "total": 1,
            }
        else:
            response = {
                "deviceSn": "SIM-SN",
                "deviceState": 2,
                "collectionTime": int(utcnow().timestamp()),
                "dataList": [{"key": "SIM-POWER", "value": "1500", "unit": "W"}],
            }
        return httpx.Response(200, json={"success": True, "code": None, **response})

    config = {"id": "sim", "vendor": "SOLARMAN", "region": "global", "enabled": True}
    adapter = Solarman(
        config, SOLARMAN_KEYS, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    controller.adapters["sim"] = adapter
    await controller.poll()
    assert calls.count("/account/v1.0/token") == 1
    device = controller.device(store.list("device")[0]["id"])
    assert device.identity.actual_oem is None and device.online is True
    sample = controller.latest(device)["samples"][0]
    assert sample["metric"] == "solarman.SIM-POWER" and not sample["stale"]
    assert sample["quality"] == "UNVERIFIED" and sample["value"] == 1500
    await adapter.close()


@pytest.mark.parametrize("factory,credentials", [(Solis, SOLIS_KEYS), (Solarman, SOLARMAN_KEYS)])
async def test_new_transports_deny_non_read_endpoints_and_writes(factory, credentials):
    calls = []
    adapter = factory(
        {"region": "global"},
        credentials,
        client=httpx.AsyncClient(transport=httpx.MockTransport(lambda req: calls.append(req))),
    )
    for path in ["/v2/api/control", "//attacker.invalid", "/station/v1.0/delete"]:
        with pytest.raises(VendorError, match="read_endpoint_not_allowed"):
            await adapter.read(path, {})
    with pytest.raises(VendorError, match="read_only_adapter"):
        await adapter.send({})
    assert calls == []
    await adapter.close()


@pytest.mark.parametrize("factory,credentials", [(Solis, SOLIS_KEYS), (Solarman, SOLARMAN_KEYS)])
@pytest.mark.parametrize("status", [302, 401, 429, 500])
async def test_errors_never_leak_vendor_response_or_follow_redirect(factory, credentials, status):
    calls = []

    def handler(req):
        calls.append(req.url.host)
        return httpx.Response(
            status, headers={"Location": "https://attacker.invalid"}, text="SIM-SECRET-LEAK"
        )

    adapter = factory(
        {"region": "global"}, credentials, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(VendorError) as caught:
        await adapter.stations()
    assert "SIM-SECRET" not in str(caught.value)
    assert len(calls) == 1
    await adapter.close()


async def test_solarman_repeated_page_fails_instead_of_looping_forever():
    def handler(req):
        if req.url.path.endswith("token"):
            return httpx.Response(200, json=token())
        return httpx.Response(200, json={"success": True, "total": 5, "stationList": [{"id": 1}]})

    adapter = Solarman(
        {"region": "global"}, SOLARMAN_KEYS, client=httpx.AsyncClient(transport=httpx.MockTransport(handler))
    )
    with pytest.raises(VendorError, match="vendor_pagination_repeated"):
        await adapter.stations()
    await adapter.close()
