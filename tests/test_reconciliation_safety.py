"""Reconciliation must retain quarantine when authority changes during readback."""

import pytest
from test_control import Simulator
from test_security_revision_fences import security_aba
from test_workspaces import login

from solar_fleet.domain import CommandStatus, VendorCall


@pytest.mark.parametrize("pause", ["order", "configuration"])
@pytest.mark.parametrize("change", ["session", "role", "device", "integration", "aba", "unchanged",
                                    "role_aba", "permission_aba", "session_aba"])
def test_reconciliation_revalidates_before_releasing_quarantine(local, device, capability, pause, change):
    client, ctl = local
    headers = login(local, "engineer")
    sim = Simulator()

    async def close():
        pass

    sim.close = close
    config = {"id": device.integration_id, "vendor": "SIMULATOR", "enabled": True}
    ctl.store.put("integration", device.integration_id, config)
    ctl.adapters[device.integration_id] = sim
    ctl.capability = lambda d, i: capability
    ctl.engine.capability = ctl.capability
    ctl.engine.writes_enabled = True
    ctl.engine.compiler = lambda d, i, p: (
        [VendorCall(path="/simulator", body=p)], {"maxChargeCurrent": p["value"]},
    )

    async def prepare():
        plan = await ctl.engine.preview(ctl.engine.principal("engineer"), device.id, capability.intent, {"value": 10})
        ctl.store.claim_command(plan, "sim-reconciliation-key")
        ctl.engine.transition(plan, CommandStatus.TIMEOUT, orders=["SIM-ORDER"])
        return plan

    plan = client.portal.call(prepare)
    original = getattr(sim, pause)

    async def mutate(*args):
        result = await original(*args)
        if change.endswith("_aba"):
            security_aba(ctl.store, "engineer", change)
        elif change == "session":
            ctl.store.db.execute("DELETE FROM sessions")
        elif change == "role":
            ctl.store.db.execute("UPDATE users SET role='Viewer' WHERE id='engineer'")
        elif change == "device":
            row = ctl.store.get("device", device.id)
            ctl.store.put("device", device.id, row | {"vendor_id": "FOREIGN"})
        elif change == "integration":
            ctl.store.put("integration", device.integration_id, config | {"enabled": False})
        elif change == "aba":
            ctl.store.put("integration", device.integration_id, config | {"enabled": False})
            ctl.store.put("integration", device.integration_id, config)
        return result

    setattr(sim, pause, mutate)
    response = client.post(f"/api/commands/{plan.id}/reconcile", json={}, headers=headers)
    if change == "unchanged":
        assert response.status_code == 200, response.text
        assert ctl.store.command(plan.id)["status"] == "VERIFIED"
    else:
        assert response.status_code in (401, 403, 409), response.text
        assert ctl.store.command(plan.id)["status"] == "TIMEOUT"
    assert sim.sent == 0