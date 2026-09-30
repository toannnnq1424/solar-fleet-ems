"""HTTP command owners retain the confirming session across queue waits."""

import asyncio

import pytest
from test_rollout_authorization import prepare
from test_security_revision_fences import security_aba


@pytest.mark.parametrize("route", ["/api/commands", "/api/control/execute"])
@pytest.mark.parametrize("revoke", [False, True, "credentials", "credentials_aba",
                                    "role_aba", "scope_aba", "permission_aba", "session_aba"])
def test_confirm_origin_after_device_lock(local, device, capability, route, revoke):
    client, ctl = local
    headers, sim, _ = prepare(local, device, capability)
    if revoke in ("credentials", "credentials_aba"):
        ctl.vault.put(device.integration_id, {"password": "synthetic-old"})
    response = client.post("/api/plans", headers=headers, json={
        "device_id": device.id, "intent": capability.intent, "parameters": {"value": 20},
    })
    assert response.status_code == 200, response.text
    plan = response.json()
    ctl.engine.writes_enabled = True
    lock = ctl.engine.locks[device.id]
    client.portal.call(lock.acquire)
    try:
        payload = {"plan_id": plan["id"], "digest": plan["digest"],
                   "idempotency_key": "origin_test_123456789"}
        if route == "/api/control/execute":
            payload["device_id"] = device.id
        response = client.post(route, headers=headers, json=payload)
        assert response.status_code in (200, 202), response.text
        if revoke in ("credentials", "credentials_aba"):
            def replace_credentials():
                ctl.vault.put(device.integration_id, {"password": "synthetic-new"})
                if revoke == "credentials_aba":
                    ctl.vault.put(device.integration_id, {"password": "synthetic-old"})
            client.portal.call(replace_credentials)
        elif isinstance(revoke, str):
            client.portal.call(lambda: security_aba(ctl.store, "engineer", revoke))
        elif revoke:
            client.portal.call(lambda: ctl.store.db.execute("DELETE FROM sessions"))
    finally:
        client.portal.call(lock.release)

    async def drained():
        await asyncio.wait_for(asyncio.gather(*list(ctl.engine.tasks)), 5)
    client.portal.call(drained)
    command = ctl.store.command(plan["id"])
    assert command["status"] == ("FAILED" if revoke else "VERIFIED"), command
    assert sim.sent == (0 if revoke else 1)
    if revoke:
        assert command["error"] == (
            "integration_credentials_changed" if revoke in ("credentials", "credentials_aba")
            else "session_authority_changed"
        )
        assert not command.get("readback")