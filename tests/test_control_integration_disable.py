"""Real local route/controller; synthetic Deye HTTP only, no equipment."""

import asyncio

import pytest
from test_deye import auth, make, ok
from test_workspaces import login

from solar_fleet.domain import Configuration, Role, SafetyError, VendorCall, utcnow
from solar_fleet.security import create_user


@pytest.mark.parametrize("pause", ["auth", "budget"])
def test_disable_route_stops_waiting_control_request(local, device, capability, pause):
    client, ctl = local
    headers = login(local)
    create_user(ctl.store, "sender", "SIMULATOR-sender-password", Role.INSTALLER, [device.site_id])
    writes = []
    entered, release = asyncio.Event(), asyncio.Event()

    async def handler(request):
        if result := auth(request):
            if pause == "auth":
                entered.set()
                await release.wait()
            return result
        writes.append(request)
        return ok(orderId="SIM-ORDER", connectionStatus=1)

    transport = make(handler)
    acquire_original = transport.budgets.acquire

    async def acquire(account, devices):
        if pause == "budget" and devices:
            entered.set()
            await release.wait()
        await acquire_original(account, devices)

    async def configuration(d):
        return Configuration(values={"maxChargeCurrent": 10}, freshness_verified=True, device_timestamp=utcnow())

    transport.budgets.acquire = acquire
    transport.configuration = configuration
    ctl.store.put("integration", device.integration_id, {
        "id": device.integration_id, "vendor": "Deye", "region": "eu", "enabled": True,
    })
    ctl.adapters[device.integration_id] = transport
    engine = ctl.engine
    engine.writes_enabled = True
    engine.timeout_seconds = 5
    engine.capability = lambda d, i: capability
    engine.compiler = lambda d, i, p: ([VendorCall(
        path="/v1.0/order/battery/parameter/update",
        body={"deviceSn": d.vendor_id, "paramterType": "MAX_CHARGE_CURRENT", "value": p["value"]},
    )], {"maxChargeCurrent": p["value"]})

    async def start():
        user = engine.principal("sender")
        plan = await engine.preview(user, device.id, capability.intent, {"value": 20})
        await engine.confirm(user, plan.id, plan.digest, "sim-disable-route-key")
        return plan.id

    async def wait():
        await asyncio.wait_for(entered.wait(), 2)

    async def finish():
        release.set()
        await asyncio.gather(*list(engine.tasks))

    plan_id = client.portal.call(start)
    try:
        client.portal.call(wait)
        response = client.post(
            f"/api/integrations/{device.integration_id}/enabled",
            json={"enabled": False}, headers=headers,
        )
        assert response.status_code == 200
        assert ctl.store.get("integration", device.integration_id)["enabled"] is False
        assert device.integration_id not in ctl.adapters
    finally:
        client.portal.call(finish)
    assert writes == []
    command = ctl.store.command(plan_id)
    assert command["status"] == "TIMEOUT"
    # Durable fencing detects the revocation before resolving the evicted adapter.
    assert command["error"] == "authority_revision_changed"
    with pytest.raises(SafetyError, match="device_has_unresolved_command"):
        engine.assert_clear(device.id)
    assert ctl.store.verify_audit()