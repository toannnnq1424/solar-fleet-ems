"""Synthetic route/barrier tests; no external accounts or hardware."""

import asyncio
from concurrent.futures import ThreadPoolExecutor

import pytest
from test_security_revision_fences import security_aba
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.controller import entity_id
from solar_fleet.domain import Sample, Source, utcnow


@pytest.mark.parametrize("route", ["alerts", "history", "configuration"])
@pytest.mark.parametrize("change", ["scope", "session", "disable", "replace", "device", "binding", "site", "aba", "unchanged",
                                    "scope_aba", "permission_aba", "session_aba", "unrelated"])
def test_vendor_reads_revalidate_after_transport_wait(local, change, route):
    client, ctl = local
    headers = login(local, "viewer")
    device = ctl.store.get("device", "sim-device")
    device["identity"]["vendor"] = "Deye"
    ctl.store.put("device", device["id"], device)
    config = {"id": device["integration_id"], "vendor": "Deye", "region": "eu", "enabled": True}
    ctl.store.put("integration", config["id"], config)
    bid = entity_id(config["id"], "binding", device["vendor_id"])
    binding = {"id": bid, "device_id": device["id"], "site_id": device["site_id"],
               "integration_id": config["id"], "vendor_device_sn": device["vendor_id"],
               "source": "VENDOR_CLOUD", "telemetry_enabled": True}
    ctl.store.put("binding", bid, binding)
    entered, release = asyncio.Event(), asyncio.Event()

    class Transport:
        async def alerts(self, *args):
            entered.set()
            await release.wait()
            return []

        async def close(self):
            pass

        history = alerts
        configuration = alerts

    ctl.adapters[config["id"]] = Transport()

    async def wait():
        await asyncio.wait_for(entered.wait(), 2)

    async def mutate():
        if change == "unrelated":
            for kind in ("integration", "device", "binding", "site"):
                ctl.store.put(kind, "unrelated", {"id": "unrelated"})
        elif change.endswith("_aba"):
            security_aba(ctl.store, "viewer", change)
        elif change == "scope":
            ctl.store.db.execute("UPDATE users SET sites='[]' WHERE id='viewer'")
        elif change == "session":
            ctl.store.db.execute("DELETE FROM sessions WHERE user_id='viewer'")
        elif change == "disable":
            ctl.store.put("integration", config["id"], config | {"enabled": False})
        elif change == "aba":
            ctl.store.put("integration", config["id"], config | {"enabled": False})
            ctl.store.put("integration", config["id"], config)
        elif change == "replace":
            ctl.adapters[config["id"]] = Transport()
        elif change == "device":
            ctl.store.put("device", device["id"], device | {"site_id": "other-site"})
        elif change == "binding":
            ctl.store.put("binding", bid, binding | {"telemetry_enabled": False})
        elif change == "site":
            site = ctl.store.get("site", device["site_id"])
            ctl.store.put("site", device["site_id"], site | {"name": "Changed during read"})
        release.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        body = {"start": 1, "end": 2, "points": ["power"]} if route == "history" else {}
        future = pool.submit(client.post, f"/api/devices/sim-device/{route}", json=body, headers=headers)
        try:
            client.portal.call(wait)
        finally:
            client.portal.call(mutate)
        response = future.result(timeout=5)
    if change in {"unchanged", "unrelated"}:
        assert response.status_code == 200
        if route == "alerts":
            assert ctl.store.get("alerts", device["id"]) is not None
    else:
        assert response.status_code in (401, 403, 409)
        assert ctl.store.get("alerts", device["id"]) is None


@pytest.mark.parametrize("change", ["scope", "site", "sample_device", "sample_binding", "unchanged"])
def test_agent_latest_respects_current_scope_and_sample_provenance(local, change):
    client, ctl = local
    login(local, "viewer")
    agent = {"id": "sim-agent", "site_id": "sim-site", "enabled": True,
             "device_ids": [] if change == "scope" else ["sim-device"]}
    ctl.store.put("agent", agent["id"], agent)
    sample = Sample(device_id="other-device" if change == "sample_device" else "sim-device",
                    binding_id="other-agent" if change == "sample_binding" else agent["id"],
                    metric="agent.native.power", value=10, unit="W", source=Source.AGENT,
                    source_timestamp=utcnow(), quality="UNVERIFIED")
    ctl.store.put("agent_latest", "sim-agent:sim-device", {
        "device_id": "sim-device", "agent_id": agent["id"],
        "site_id": "other-site" if change == "site" else "sim-site",
        "samples": [sample.model_dump(mode="json")],
    })
    response = client.get("/api/devices/sim-device")
    assert response.status_code == 200
    assert len(response.json()["latest"]["samples"]) == (1 if change == "unchanged" else 0)