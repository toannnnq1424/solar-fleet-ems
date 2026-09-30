"""Account -> encrypted credentials -> cloud adapter -> data views, using only synthetic HTTP."""

import asyncio
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from test_dessmonitor_adapter import CREDENTIALS, CloudFixture, adapter
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.controller import Controller, entity_id
from solar_fleet.data_workspace import collection_due, connection_status
from solar_fleet.domain import SafetyError, utcnow
from solar_fleet.security import Vault


async def test_rejected_discovery_cache_requires_complete_refresh_before_poll(store):
    cloud = CloudFixture()
    client = adapter(cloud)
    config = {"id": "SIMULATOR-account", "vendor": "Eybond / SmartESS", "region": "dessmonitor", "enabled": True}
    store.put("integration", config["id"], config)
    ctl = Controller(store, Vault(store, Fernet.generate_key()))
    ctl.adapters[config["id"]] = client
    entered, release = asyncio.Event(), asyncio.Event()
    original = client.devices

    async def blocked(id):
        rows = await original(id)
        entered.set()
        await release.wait()
        return rows

    try:
        await ctl.discover(config, client)
        assert client.inventory_ready
        client.devices = blocked
        task = asyncio.create_task(ctl.discover(config, client))
        try:
            await asyncio.wait_for(entered.wait(), 2)
            binding = store.list("binding")[0]
            store.put("binding", binding["id"], binding | {"telemetry_enabled": False})
        finally:
            release.set()
            with pytest.raises(SafetyError, match="discovery_context_changed"):
                await asyncio.wait_for(task, 2)
        assert client.routes  # Transport cache exists, but is not accepted inventory.
        assert not client.inventory_ready
        client.devices = original
        before = len(cloud.calls)
        await ctl.poll()
        actions = [query["action"][0] for _, query in cloud.calls[before:]]
        assert "queryPlants" in actions and "queryCollectorDevices" in actions
        assert "queryDeviceLastData" not in actions
        assert client.inventory_ready
        assert store.get("binding", binding["id"])["telemetry_enabled"] is False
        assert store.list("latest") == []
    finally:
        await client.close()


def connect(local):
    client, ctl = local
    headers = login(local)
    response = client.post(
        "/api/integrations",
        headers=headers,
        json={
            "name": "SIMULATOR Bluesun SmartESS",
            "vendor": "Eybond / SmartESS",
            "region": "dessmonitor",
            "credentials": CREDENTIALS,
            "equipment_brand": "Bluesun",
        },
    )
    assert response.status_code == 201, response.text
    id = response.json()["id"]
    cloud = CloudFixture()
    ctl.adapters[id] = adapter(cloud)
    return client, ctl, headers, id, cloud


def test_account_to_native_telemetry_without_fabricating_canonical_metrics(local):
    c, ctl, headers, id, cloud = connect(local)
    assert ctl.vault.get(id) == CREDENTIALS
    assert CREDENTIALS["password"] not in str(ctl.store.list("integration"))
    assert c.post("/api/sync", headers=headers, json={}).status_code == 200
    state = ctl.store.get("integration_state", id)
    assert state["state"] == "CONNECTED", state
    device_id = entity_id("Eybond / SmartESS", "device", "SIMULATOR-SN")
    data = c.get("/api/devices/" + device_id).json()
    assert data["device"]["metadata"]["declared_equipment_brand"] == "Bluesun"
    assert data["device"]["identity"]["vendor"] == "Eybond / SmartESS"
    assert data["device"]["last_seen"] is None
    assert data["bindings"][0]["control_enabled"] is False
    assert data["latest"]["native"]["dataList"][3]["value"] == "Charging"
    samples = data["latest"]["samples"]
    assert len(samples) == 5
    assert all(s["metric"].startswith("eybond.point_") for s in samples)
    assert all(s["source_timestamp"] is None and s["stale"] for s in samples)
    assert all(s["quality"] == "UNVERIFIED" for s in samples)
    assert {s["unit"] for s in samples} >= {"Wh", "kWh", "VA"}
    assert not any(cap["hardware_verified"] for cap in data["capabilities"])
    equipment = c.get("/api/fleet/devices-overview").json()
    native_device = next(d for d in equipment["devices"] if d["id"] == device_id)
    assert native_device["brand"] == "Bluesun"
    assert native_device["status"] == "UNKNOWN"
    assert native_device["temp_c"] is None
    site_id = data["device"]["site_id"]
    sources = c.get("/api/data-sources", params={"site_id": site_id}).json()
    assert sources["sources"][0]["status"] == "CONNECTED"
    assert sources["collection_config"]["polling_cycle_seconds"] == 300
    assert sources["status"] == "NO_VERIFIED_DATA"
    summary = c.get(f"/api/sites/{site_id}/overview-summary").json()
    assert summary["energy_flow"]["pv_w"] is None
    assert summary["plant_status"]["today_yield_kwh"] is None
    history = c.get(f"/api/devices/{device_id}/history").json()["samples"]
    assert history and all(s["source_timestamp"] is None for s in history)
    assert "SIMULATOR-secret" not in c.get("/api/accounts/overview").text
    before = len(cloud.calls)
    ctl.last_poll = 0
    assert c.post("/api/sync", headers=headers, json={}).status_code == 200
    assert len(cloud.calls) == before  # no repeated calls inside 300 s
    login(local, "other")
    assert c.get("/api/devices/" + device_id).status_code == 403
    assert c.get("/api/data-sources", params={"site_id": site_id}).status_code == 403
    assert c.get("/api/accounts/overview").status_code == 403


def test_restart_and_access_check_force_complete_session_inventory(local):
    c, ctl, headers, id, cloud = connect(local)
    assert c.post("/api/sync", headers=headers, json={}).status_code == 200
    assert ctl.adapters[id].inventory_ready
    # check() visits just the first plant, so must invalidate the controller's route cache.
    result = c.post(f"/api/integrations/{id}/check", headers=headers, json={})
    assert result.status_code == 200 and result.json()["state"] == "PASS"
    assert not ctl.adapters[id].inventory_ready
    for restart in (False, True):
        if restart:
            # A new adapter has no in-memory routes although DB discovery is recent.
            ctl.adapters[id] = adapter(cloud)
        state = ctl.store.get("integration_state", id)
        state["last_attempt"] = (utcnow() - timedelta(seconds=301)).isoformat()
        ctl.store.put("integration_state", id, state)
        ctl.last_poll = 0
        before = len(cloud.calls)
        assert c.post("/api/sync", headers=headers, json={}).status_code == 200
        assert ctl.store.get("integration_state", id)["state"] == "CONNECTED"
        assert any(q["action"] == ["queryPlants"] for _, q in cloud.calls[before:])
        assert ctl.adapters[id].inventory_ready


def test_collection_floor_and_revision_are_enforced_by_backend(local):
    c, ctl, headers, id, _ = connect(local)
    row = next(r for r in c.get("/api/collection").json()["connections"] if r["integration_id"] == id)
    assert row["minimum_interval_seconds"] == row["policy"]["interval_seconds"] == 300
    url = "/api/collection/" + id
    assert c.post(url, headers=headers, json={"interval_seconds": 120}).status_code == 422
    saved = c.post(url, headers=headers, json={"interval_seconds": 600})
    assert saved.status_code == 200 and saved.json()["revision"] == 1
    assert c.post(url, headers=headers, json={"interval_seconds": 300}).status_code == 409
    now = utcnow()
    ctl.store.put("integration_state", id, {"last_attempt": now.isoformat()})
    config = ctl.store.get("integration", id)
    assert not collection_due(ctl.store, config, now + timedelta(seconds=599), minimum_interval=300)
    assert collection_due(ctl.store, config, now + timedelta(seconds=600), minimum_interval=300)
    # Old pre-upgrade policies cannot undercut a newly registered adapter's floor.
    ctl.store.put("collection_policy", id, {"interval_seconds": 120})
    assert not collection_due(ctl.store, config, now + timedelta(seconds=299), minimum_interval=300)
    assert collection_due(ctl.store, config, now + timedelta(seconds=300), minimum_interval=300)


@pytest.mark.parametrize(
    "state,age,enabled,expected",
    [
        ("CONNECTED", 0, True, "CONNECTED"),
        ("CONNECTED", 721, True, "STALE"),
        ("CONNECTED", -30, True, "STALE"),
        ("CONNECTED", 0, False, "DISABLED"),
        ("PILOT_CAPACITY_EXCEEDED", 0, True, "PILOT_CAPACITY_EXCEEDED"),
    ],
)
def test_connection_freshness_not_measurement_acceptance(state, age, enabled, expected):
    now = utcnow()
    observed = {"state": state, "last_success": (now - timedelta(seconds=age)).isoformat()}
    assert connection_status({"enabled": enabled}, observed, 300, now) == expected
    assert connection_status({"enabled": True}, {"state": "CONNECTED"}, 300, now) == "UNKNOWN"
    assert (
        connection_status({"enabled": True}, {"error": "vendor_auth_or_permission_denied"}, 300)
        == "AUTH_REQUIRED"
    )
