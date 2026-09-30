"""Rollout race regressions with synthetic adapters only."""

import asyncio
import json
from copy import deepcopy

import pytest
from test_control import Simulator
from test_security_revision_fences import security_aba
from test_workspaces import login

from solar_fleet.domain import VendorCall
from solar_fleet.schedule_planning import schedule_digest


def prepare(local, device, capability):
    client, ctl = local
    headers = login(local, "engineer")
    sim = Simulator()

    async def close():
        pass

    sim.close = close
    ctl.store.put("integration", device.integration_id, {"enabled": True})
    ctl.adapters[device.integration_id] = sim
    ctl.capability = ctl.engine.capability = lambda d, i: capability
    ctl.engine.compiler = lambda d, i, p: (
        [VendorCall(path="/simulator", body=p)], {"maxChargeCurrent": p["value"]},
    )
    second = device.model_copy(update={"id": "sim-second"})
    ctl.store.put("device", second.id, second.model_dump(mode="json"))
    response = client.post("/api/rollouts", headers=headers, json={
        "name": "Synthetic wave", "actions": [
            {"device_id": d, "intent": capability.intent, "parameters": {"value": 20}}
            for d in (device.id, second.id)
        ],
    })
    assert response.status_code == 201, response.text
    return headers, sim, response.json()


@pytest.mark.parametrize("change", [
    "session", "scope", "row", "schedule", "first_binding", "first_capability", "unchanged",
    "role_aba", "scope_aba", "permission_aba", "session_aba",
])
@pytest.mark.parametrize("fails", [False, True])
def test_wave_preview_denial_is_not_partial(local, device, capability, change, fails):
    client, ctl = local
    headers, sim, row = prepare(local, device, capability)
    schedule = {"id": "synthetic", "site_id": device.site_id, "revision": 1}
    ctl.store.put("schedule", schedule["id"], schedule)
    row["schedule_source"] = {"id": schedule["id"], "digest": schedule_digest(schedule)}
    ctl.store.put("rollout", row["id"], row)
    expected_row = deepcopy(row)
    original = sim.configuration

    async def configuration(current):
        if current.id == "sim-second":
            if change.endswith("_aba"):
                security_aba(ctl.store, "engineer", change)
            elif change == "session":
                ctl.store.db.execute("DELETE FROM sessions")
            elif change == "scope":
                ctl.store.db.execute("UPDATE users SET sites='[]' WHERE id='engineer'")
            elif change == "row":
                expected_row["state"] = "CANCELLED_UNSENT_ONLY"
                ctl.store.put("rollout", row["id"], expected_row)
            elif change == "schedule":
                ctl.store.put("schedule", schedule["id"], schedule | {"revision": 2})
            elif change == "first_binding":
                changed = device.model_copy(update={"vendor_id": "CHANGED"})
                ctl.store.put("device", device.id, changed.model_dump(mode="json"))
            elif change == "first_capability":
                ctl.engine.capability = lambda d, i: (
                    capability.model_copy(update={"reason": "Changed profile"})
                    if d.id == device.id else capability
                )
            if fails:
                from solar_fleet.domain import SafetyError

                raise SafetyError("synthetic_configuration_failure")
        return await original(current)

    sim.configuration = configuration
    response = client.post(f"/api/rollouts/{row['id']}/preview", headers=headers, json={})
    if change == "unchanged":
        assert response.status_code == 200, response.text
        assert response.json()["targets"][0]["status"] == "READY"
        assert response.json()["targets"][1]["status"] == ("BLOCKED" if fails else "READY")
        assert ctl.store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == (1 if fails else 2)
    else:
        assert response.status_code in (401, 403, 409), response.text
        assert "maxChargeCurrent" not in response.text
        assert ctl.store.get("rollout", row["id"]) == expected_row
        assert ctl.store.db.execute("SELECT COUNT(*) FROM plans").fetchone()[0] == 0
    assert not ctl.store.commands()
    assert sim.sent == 0


@pytest.mark.parametrize("route", ["preview", "confirm", "cancel"])
@pytest.mark.parametrize("revoke", [True, False])
def test_rollout_session_after_runtime_lock(local, device, capability, route, revoke):
    client, ctl = local
    headers, sim, row = prepare(local, device, capability)
    if route == "confirm":
        response = client.post(f"/api/rollouts/{row['id']}/preview", headers=headers, json={})
        assert response.status_code == 200, response.text
        row = response.json()
        ctl.engine.writes_enabled = True
    runtime = client.app.state.operations_runtime
    real_lock = runtime.lock

    class Gate:
        async def __aenter__(self):
            await real_lock.acquire()
            await asyncio.sleep(0)
            if revoke:
                ctl.store.db.execute("DELETE FROM sessions")

        async def __aexit__(self, *args):
            real_lock.release()

    runtime.lock = Gate()
    try:
        response = client.post(f"/api/rollouts/{row['id']}/{route}", headers=headers,
                               json={"digest": row["digest"], "stage": "canary"} if route == "confirm" else {})
        if revoke:
            assert response.status_code in (401, 403, 409), response.text
            assert ctl.store.get("rollout", row["id"]) == row
            assert "maxChargeCurrent" not in response.text
            assert not ctl.store.commands()
            assert sim.sent == 0
        else:
            assert response.status_code == 200, response.text
    finally:
        runtime.lock = real_lock


@pytest.mark.parametrize("boundary", ["lock", "configuration", "transport", "readback", "order"])
@pytest.mark.parametrize("change", [
    "session", "cancel", "schedule", "other_binding", "other_capability", "integration", "site", "unchanged",
    "credentials", "credentials_aba", "other_credentials",
])
def test_claimed_rollout_retains_origin_guard(local, device, capability, boundary, change):
    client, ctl = local
    headers, sim, row = prepare(local, device, capability)
    credential_id = device.integration_id
    if change == "other_credentials":
        credential_id = "synthetic-other-integration"
        ctl.store.put("integration", credential_id, {"enabled": True})
        ctl.adapters[credential_id] = sim
        other = ctl.store.get("device", "sim-second")
        ctl.store.put("device", "sim-second", other | {"integration_id": credential_id})
    if change in ("credentials", "credentials_aba", "other_credentials"):
        ctl.vault.put(credential_id, {"password": "synthetic-old"})
    ctl.engine.compiler = lambda d, i, p: (
        [VendorCall(path="/simulator", body=p), VendorCall(path="/simulator", body=p)],
        {"maxChargeCurrent": p["value"]},
    )
    schedule = {"id": "queued-source", "site_id": device.site_id, "revision": 1}
    ctl.store.put("schedule", schedule["id"], schedule)
    row["schedule_source"] = {"id": schedule["id"], "digest": schedule_digest(schedule)}
    ctl.store.put("rollout", row["id"], row)
    response = client.post(f"/api/rollouts/{row['id']}/preview", headers=headers, json={})
    assert response.status_code == 200, response.text
    row = response.json()
    ctl.engine.writes_enabled = True
    original_configuration, original_send = sim.configuration, sim.send
    original_order = sim.order
    entered, release = asyncio.Event(), asyncio.Event()

    async def wait():
        entered.set()
        await release.wait()

    async def configuration(current):
        if boundary == "configuration" or (boundary == "readback" and sim.sent):
            await wait()
        return await original_configuration(current)

    async def send(call, *, before_send):
        if boundary == "transport":
            await wait()
        return await original_send(call, before_send=before_send)

    async def order(id):
        if boundary == "order":
            await wait()
        return await original_order(id)

    sim.configuration, sim.send, sim.order = configuration, send, order
    lock = ctl.engine.locks[device.id]
    if boundary == "lock":
        client.portal.call(lock.acquire)
    try:
        response = client.post(f"/api/rollouts/{row['id']}/confirm", headers=headers,
                               json={"digest": row["digest"], "stage": "canary"})
        assert response.status_code == 200, response.text
        command_id = response.json()["targets"][0]["command_id"]
        if boundary != "lock":
            async def reached():
                await asyncio.wait_for(entered.wait(), 5)
            client.portal.call(reached)

        def mutate():
            if change in ("credentials", "credentials_aba", "other_credentials"):
                ctl.vault.put(credential_id, {"password": "synthetic-new"})
                if change == "credentials_aba":
                    ctl.vault.put(credential_id, {"password": "synthetic-old"})
            elif change == "session":
                ctl.store.db.execute("DELETE FROM sessions")
            elif change == "schedule":
                ctl.store.put("schedule", schedule["id"], schedule | {"revision": 2})
            elif change == "other_binding":
                other = ctl.store.get("device", "sim-second")
                ctl.store.put("device", "sim-second", other | {"vendor_id": "CHANGED"})
            elif change == "other_capability":
                ctl.engine.capability = lambda d, i: (
                    capability.model_copy(update={"reason": "Changed profile"})
                    if d.id == "sim-second" else capability
                )
            elif change == "integration":
                integration = ctl.store.get("integration", device.integration_id)
                ctl.store.put("integration", device.integration_id, integration | {"revision": 2})
            elif change == "site":
                site = ctl.store.get("site", device.site_id)
                ctl.store.put("site", device.site_id, site | {"revision": 2})

        if change == "cancel":
            cancelled = client.post(f"/api/rollouts/{row['id']}/cancel", headers=headers, json={})
            assert cancelled.status_code == 200, cancelled.text
        else:
            client.portal.call(mutate)
    finally:
        def unblock():
            release.set()
            if boundary == "lock" and lock.locked():
                lock.release()
        client.portal.call(unblock)

    async def drained():
        await asyncio.wait_for(asyncio.gather(*list(ctl.engine.tasks)), 5)
    client.portal.call(drained)
    command = ctl.store.command(command_id)
    if change == "unchanged":
        assert command["status"] == "VERIFIED", command
        assert sim.sent == 2
    else:
        assert command["status"] == ("TIMEOUT" if boundary in ("transport", "readback", "order") else "FAILED")
        assert sim.sent == ({"readback": 2, "order": 1}.get(boundary, 0))
        assert not command.get("readback")
        if boundary == "order":
            assert json.loads(command["order_ids"]) == ["SIM-ORDER-1"]
    assert not ctl.store.get("rollout", row["id"])["targets"][1].get("command_id")


@pytest.mark.parametrize("change", ["session", "cancel", "schedule"])
def test_remaining_wave_denies_both_claimed_targets(local, device, capability, change):
    client, ctl = local
    headers, sim, row = prepare(local, device, capability)
    schedule = {"id": "multi-source", "site_id": device.site_id, "revision": 1}
    ctl.store.put("schedule", schedule["id"], schedule)
    row["schedule_source"] = {"id": schedule["id"], "digest": schedule_digest(schedule)}
    ctl.store.put("rollout", row["id"], row)
    response = client.post(f"/api/rollouts/{row['id']}/preview", headers=headers, json={})
    assert response.status_code == 200
    row = response.json()
    # Synthetic journal setup isolates the remaining-wave queue from canary acceptance.
    row["state"] = "CANARY_VERIFIED"
    ctl.store.put("rollout", row["id"], row)
    ctl.engine.writes_enabled = True
    locks = [ctl.engine.locks[target["device_id"]] for target in row["targets"]]
    for lock in locks:
        client.portal.call(lock.acquire)
    try:
        response = client.post(f"/api/rollouts/{row['id']}/confirm", headers=headers,
                               json={"digest": row["digest"], "stage": "remaining"})
        assert response.status_code == 200, response.text
        assert all(target.get("command_id") for target in response.json()["targets"])
        if change == "cancel":
            assert client.post(f"/api/rollouts/{row['id']}/cancel", headers=headers, json={}).status_code == 200
        elif change == "session":
            ctl.store.db.execute("DELETE FROM sessions")
        else:
            ctl.store.put("schedule", schedule["id"], schedule | {"revision": 2})
    finally:
        for lock in locks:
            client.portal.call(lock.release)

    async def drained():
        await asyncio.wait_for(asyncio.gather(*list(ctl.engine.tasks)), 5)
    client.portal.call(drained)
    assert sim.sent == 0
    assert len(ctl.store.commands()) == 2
    assert all(command["status"] == "FAILED" for command in ctl.store.commands())