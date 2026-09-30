"""Synthetic preview authority changes must not persist or disclose a plan."""

import asyncio

import pytest
from test_control import Simulator, setup
from test_security_revision_fences import security_aba
from test_workspaces import login

from solar_fleet.domain import Role, SafetyError, VendorCall


@pytest.mark.parametrize("pause", ["lock", "configuration"])
@pytest.mark.parametrize("change", ["revoke", "role", "scope", "capability", "adapter", "integration", "unchanged"])
async def test_preview_live_context(store, device, operator, capability, pause, change):
    engine, sim = setup(store, device, operator, capability)
    config = {"enabled": True}
    store.put("integration", device.integration_id, config)
    entered, release = asyncio.Event(), asyncio.Event()
    original = sim.configuration
    reads = []

    async def configuration(current):
        reads.append(current.id)
        entered.set()
        await release.wait()
        return await original(current)

    sim.configuration = configuration
    lock = engine.locks[device.id]
    if pause == "lock":
        await lock.acquire()
    task = asyncio.create_task(engine.preview(operator, device.id, capability.intent, {"value": 20}))
    try:
        if pause == "configuration":
            await asyncio.wait_for(entered.wait(), 2)
        else:
            await asyncio.sleep(0)
        if change == "revoke":
            engine.principal = lambda id: None
        elif change == "role":
            engine.principal = lambda id: operator.model_copy(update={"role": Role.VIEWER})
        elif change == "scope":
            engine.principal = lambda id: operator.model_copy(update={"site_ids": []})
        elif change == "capability":
            engine.capability = lambda d, i: capability.model_copy(update={"readback_fields": ["different"]})
        elif change == "adapter":
            engine.adapter = lambda d: Simulator()
        elif change == "integration":
            store.put("integration", device.integration_id, {"enabled": False})
    finally:
        release.set()
        if pause == "lock":
            lock.release()
    if change == "unchanged":
        plan = await asyncio.wait_for(task, 2)
        assert store.plan(plan.id) == plan
    else:
        with pytest.raises(SafetyError):
            await asyncio.wait_for(task, 2)
        assert store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0
        if pause == "lock":
            assert reads == []
    assert sim.sent == 0


@pytest.mark.parametrize("route", ["/api/plans", "/api/control/execute"])
@pytest.mark.parametrize("change", ["session", "role", "scope", "integration", "unchanged",
                                    "role_aba", "scope_aba", "permission_aba", "session_aba"])
def test_preview_routes_revalidate_before_persistence(local, device, capability, route, change):
    client, ctl = local
    headers = login(local, "engineer")
    sim = Simulator()

    async def close():
        pass

    sim.close = close
    config = {"id": device.integration_id, "vendor": "SIMULATOR", "enabled": True}
    ctl.store.put("integration", device.integration_id, config)
    ctl.adapters[device.integration_id] = sim
    ctl.engine.capability = lambda d, i: capability
    ctl.engine.compiler = lambda d, i, p: (
        [VendorCall(path="/simulator", body=p)], {"maxChargeCurrent": p["value"]},
    )
    original = sim.configuration

    async def configuration(current):
        result = await original(current)
        if change.endswith("_aba"):
            security_aba(ctl.store, "engineer", change)
        elif change == "session":
            ctl.store.db.execute("DELETE FROM sessions")
        elif change == "role":
            ctl.store.db.execute("UPDATE users SET role='Viewer' WHERE id='engineer'")
        elif change == "scope":
            ctl.store.db.execute("UPDATE users SET sites='[]' WHERE id='engineer'")
        elif change == "integration":
            ctl.store.put("integration", device.integration_id, config | {"enabled": False})
        return result

    sim.configuration = configuration
    response = client.post(route, headers=headers, json={
        "device_id": device.id, "intent": capability.intent, "parameters": {"value": 20},
    })
    if change == "unchanged":
        assert response.status_code == 200, response.text
        assert ctl.store.plan(response.json()["id"]) is not None
    else:
        assert response.status_code in (401, 403, 409), response.text
        assert ctl.store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0
        assert "maxChargeCurrent" not in response.text
    assert sim.sent == 0