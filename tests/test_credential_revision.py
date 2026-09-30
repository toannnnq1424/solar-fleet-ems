"""Synthetic vault replacement must invalidate existing integration contexts."""

import pytest
from test_rollout_authorization import prepare

from solar_fleet.domain import SafetyError


@pytest.mark.parametrize("restore", [False, True])
def test_preview_rejects_credential_replacement(local, device, capability, restore):
    client, ctl = local
    headers, sim, _ = prepare(local, device, capability)
    ctl.vault.put(device.integration_id, {"password": "synthetic-old"})
    original = sim.configuration

    async def configuration(current):
        result = await original(current)
        ctl.vault.put(device.integration_id, {"password": "synthetic-new"})
        if restore:
            ctl.vault.put(device.integration_id, {"password": "synthetic-old"})
        return result

    sim.configuration = configuration
    response = client.post("/api/plans", headers=headers, json={
        "device_id": device.id, "intent": capability.intent, "parameters": {"value": 20},
    })
    assert response.status_code == 409, response.text
    assert "maxChargeCurrent" not in response.text
    assert not ctl.store.db.execute("SELECT * FROM plans").fetchall()
    assert sim.sent == 0


def test_cached_adapter_rejects_replaced_credentials(local, device, capability):
    _, ctl = local
    _, sim, _ = prepare(local, device, capability)
    ctl.vault.put(device.integration_id, {"password": "synthetic-old"})
    assert ctl.adapter(device) is sim
    ctl.vault.put(device.integration_id, {"password": "synthetic-new"})
    with pytest.raises(SafetyError, match="integration_credentials_changed"):
        ctl.adapter(device)


def test_vault_revision_rollback(local, device, capability):
    _, ctl = local
    prepare(local, device, capability)
    ctl.vault.put(device.integration_id, {"password": "synthetic-old"})
    before = ctl.store.get("integration", device.integration_id)
    with pytest.raises(RuntimeError):
        with ctl.store.transaction():
            ctl.vault.put(device.integration_id, {"password": "synthetic-new"})
            raise RuntimeError("synthetic rollback")
    assert ctl.store.get("integration", device.integration_id) == before
    assert ctl.vault.get(device.integration_id) == {"password": "synthetic-old"}