"""Official contract field names, synthetic payloads, httpx MockTransport only."""

import json

import httpx
import pytest

from solar_fleet.adapters.deye import Budgets, Deye, source_time
from solar_fleet.catalog import CONTRACTS, capabilities
from solar_fleet.domain import VendorCall, VendorError

SYNTHETIC_CREDENTIALS = {
    "app_id": "SIM-APP",
    "app_secret": "SIM-SECRET",
    "password_sha256": "a" * 64,
    "identity_field": "email",
    "identity_value": "simulator@example.invalid",
}


def make(handler):
    return Deye(
        {"id": "sim", "region": "eu"},
        SYNTHETIC_CREDENTIALS,
        client=httpx.AsyncClient(transport=httpx.MockTransport(handler), follow_redirects=False),
        budgets=Budgets(1000, 1000, 1000),
    )


def ok(**kwargs):
    return httpx.Response(200, json={"success": True, "code": 1000000, **kwargs})


def auth(request):
    if request.url.path.endswith("/account/token"):
        return ok(accessToken="SIM-TOKEN", expiresIn=3600)


@pytest.mark.asyncio
async def test_auth_uses_explicit_region_and_sha256_no_browser_token():
    requests = []

    def handler(request):
        requests.append(request)
        if request.url.path.endswith("/token"):
            body = json.loads(request.content)
            assert request.url.host == "eu1-developer.deyecloud.com"
            assert request.url.params["appId"] == "SIM-APP"
            assert body["password"] == "a" * 64 and body["appSecret"] == "SIM-SECRET"
            assert "Authorization" not in request.headers
            return ok(accessToken="Bearer SIM-TOKEN", expiresIn=3600)
        assert request.headers["authorization"] == "Bearer SIM-TOKEN"
        return ok(stationList=[], total=0)

    client = make(handler)
    assert await client.stations() == []
    await client.stations()
    assert len(requests) == 3
    client.expires_at = 0
    await client.stations()
    assert len(requests) == 5  # Re-auth using documented token endpoint, no invented refresh request.
    await client.close()


@pytest.mark.asyncio
async def test_pagination_does_not_stop_at_short_page_when_total_requires_more():
    seen = []

    def handler(request):
        if result := auth(request):
            return result
        body = json.loads(request.content)
        seen.append(body["page"])
        return ok(stationList=[{"id": body["page"], "name": "SIMULATOR"}], total=3)

    client = make(handler)
    assert len(await client.stations()) == 3 and seen == [1, 2, 3]
    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("problem", ["repeat", "incomplete"])
async def test_broken_pagination_fails_explicitly(problem):
    def handler(request):
        if result := auth(request):
            return result
        page = json.loads(request.content)["page"]
        rows = [{"id": 1}] if problem == "repeat" or page == 1 else []
        return ok(stationList=rows, total=3)

    client = make(handler)
    with pytest.raises(VendorError, match="pagination|repeated_page"):
        await client.stations()
    await client.close()


@pytest.mark.asyncio
async def test_latest_batches_at_ten():
    sizes = []

    def handler(request):
        if result := auth(request):
            return result
        rows = json.loads(request.content)["deviceList"]
        sizes.append(len(rows))
        return ok(deviceDataList=[{"deviceSn": sn, "dataList": []} for sn in rows])

    client = make(handler)
    rows = await client.latest([f"SIM-{i}" for i in range(23)])
    assert len(rows) == 23 and sizes == [10, 10, 3]
    await client.close()


@pytest.mark.asyncio
async def test_config_never_claims_freshness_from_cloud_cache(device):
    client = make(lambda request: auth(request) or ok(maxChargeCurrent=20))
    config = await client.configuration(device)
    assert (
        config.values["maxChargeCurrent"] == 20
        and not config.freshness_verified
        and config.device_timestamp is None
    )
    await client.close()


@pytest.mark.asyncio
async def test_acceptance_does_not_imply_success_and_order_codes_are_mapped():
    codes = iter([0, 100, 300, 400, 500, 666, 999])
    calls = []

    def handler(request):
        calls.append(request)
        if result := auth(request):
            return result
        if request.method == "GET":
            return ok(status=next(codes))
        assert json.loads(request.content)["paramterType"] == "MAX_CHARGE_CURRENT"
        return ok(orderId=7, connectionStatus=0)

    client = make(handler)
    ack = await client.send(
        VendorCall(
            path="/v1.0/order/battery/parameter/update",
            body={"deviceSn": "SIM", "paramterType": "MAX_CHARGE_CURRENT", "value": 20},
        )
    )
    assert ack.order_id == "7" and not ack.online
    results = [(await client.order("7")).state for _ in range(7)]
    assert results == ["PENDING", "PENDING", "PENDING", "CANCELLED", "FAILED", "SUCCEEDED", "PENDING"]
    await client.close()


@pytest.mark.asyncio
async def test_write_timeout_has_no_retry():
    writes = []

    def handler(request):
        if result := auth(request):
            return result
        writes.append(request)
        raise httpx.ReadTimeout("SIM-SECRET should never be exposed")

    client = make(handler)
    with pytest.raises(VendorError, match="vendor_network_outcome_unknown") as exc:
        await client.send(
            VendorCall(
                path="/v1.0/order/sys/workMode/update", body={"deviceSn": "SIM", "workMode": "SELLING_FIRST"}
            )
        )
    assert len(writes) == 1 and "SIM-SECRET" not in str(exc.value)
    await client.close()


@pytest.mark.asyncio
@pytest.mark.parametrize("status", [302, 401, 403, 429, 500])
async def test_http_errors_do_not_leak_secrets_or_follow_redirect(status):
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(
            status,
            headers={"location": "https://example.invalid/steal", "retry-after": "60"},
            text="SIM-SECRET",
        )

    client = make(handler)
    with pytest.raises(VendorError) as exc:
        await client.stations()
    assert "SIM-SECRET" not in str(exc.value) and len(calls) == 1
    if status == 429:
        with pytest.raises(VendorError, match="backoff"):
            await client.stations()
        assert len(calls) == 1
    await client.close()


@pytest.mark.asyncio
async def test_error_body_and_false_success_are_not_accepted():
    client = make(
        lambda request: httpx.Response(
            200, json={"success": False, "msg": "SIM-SECRET", "accessToken": "SIM-SECRET"}
        )
    )
    with pytest.raises(VendorError, match="vendor_request_rejected"):
        await client.stations()
    await client.close()


@pytest.mark.asyncio
async def test_read_surface_rejects_every_mutation_before_network():
    client = make(lambda request: pytest.fail("network must not be reached"))
    for path, contract in CONTRACTS.items():
        if contract["mode"] in ("CONTROL", "LOCKED_ADMIN"):
            with pytest.raises(VendorError):
                await client.read(path, {})
    with pytest.raises(VendorError, match="raw_control_locked"):
        await client.send(VendorCall(path="/v1.0/order/customControl", body={}))
    await client.close()


def test_contract_rejects_lookalike_parameter_spelling():
    with pytest.raises(VendorError):
        Deye.validate(
            "/v1.0/order/battery/parameter/update",
            {"deviceSn": "SIM", "parameterType": "MAX_CHARGE_CURRENT", "value": 20},
        )


def test_no_shipping_capability_becomes_verified_due_to_web_evidence(device):
    all_caps = capabilities(device)
    assert len(all_caps) == 34 and all(c.state == "UNKNOWN" and not c.hardware_verified for c in all_caps)


@pytest.mark.parametrize("value", [None, "2026-09-13", 1789260000000, True, -1])
def test_ambiguous_timestamps_are_unknown(value):
    assert source_time(value) is None


@pytest.mark.asyncio
async def test_budgets_cover_vendor_account_and_device():
    budget = Budgets(3, 2, 1)
    await budget.acquire("A", ["1"])
    with pytest.raises(VendorError):
        await budget.acquire("A", ["1"])
    await budget.acquire("A", ["2"])
    with pytest.raises(VendorError):
        await budget.acquire("A", ["3"])
    with pytest.raises(VendorError):
        await budget.acquire("B", ["1"])  # Same physical target through another account shares its budget.
    await budget.acquire("B", ["4"])
    with pytest.raises(VendorError):
        await budget.acquire("C", ["1"])


@pytest.mark.asyncio
async def test_duplicate_integrations_share_account_budget():
    shared = Budgets(100, 1, 100)
    a = make(lambda request: ok(accessToken="SIM-TOKEN", expiresIn=3600))
    b = make(lambda request: ok(accessToken="SIM-TOKEN", expiresIn=3600))
    a.budgets = b.budgets = shared
    b.integration = {"id": "second-integration", "region": "eu"}
    await a.authenticate()
    with pytest.raises(VendorError, match="local_rate_budget_exhausted"):
        await b.authenticate()
    await a.close()
    await b.close()


def test_host_cannot_be_overridden():
    with pytest.raises(VendorError, match="unsupported_data_center"):
        Deye({"id": "sim", "region": "https://example.invalid"}, SYNTHETIC_CREDENTIALS)
