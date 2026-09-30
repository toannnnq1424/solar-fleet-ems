"""Synthetic account checks, read-key isolation and bounded OSS collector calls."""

import asyncio
from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError
from test_control import Simulator
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.domain import VendorCall, utcnow
from solar_fleet.local_solarman import CollectionProfile, collect


def linked(ctl):
    config = {
        "id": "SIM-ACCOUNT",
        "name": "SIM ACCOUNT",
        "vendor": "SOLARMAN",
        "region": "global",
        "enabled": True,
        "equipment_brand": "Bluesun",
    }
    ctl.store.put("integration", config["id"], config)
    ctl.vault.put(
        config["id"],
        {
            "identity_value": "SIM@example.invalid",
            "app_secret": "SIM-PRIVATE-ONLY",
            "password_sha256": "a" * 64,
        },
    )

    class Account:
        async def stations(self):
            return [{"id": 1, "name": "SIM"}]

        async def devices(self, id):
            return [{"deviceSn": "SIM-SN"}]

        async def latest(self, ids):
            return [{"deviceSn": "SIM-SN", "dataList": [{"key": "raw", "value": 1}]}]

        async def close(self):
            pass

    ctl.adapters[config["id"]] = Account()
    return config


@pytest.mark.parametrize("pause", ["stations", "devices", "latest"])
@pytest.mark.parametrize("change", ["session", "role", "disabled", "config", "adapter", "unchanged"])
@pytest.mark.parametrize("alias", [False, True])
def test_connection_check_revalidates_after_each_await(local, pause, change, alias):
    client, ctl = local
    config = linked(ctl)
    headers = login(local)
    adapter = ctl.adapters[config["id"]]
    calls = []

    for name in ("stations", "devices", "latest"):
        original = getattr(adapter, name)

        async def wrapped(*args, name=name, original=original):
            calls.append(name)
            result = await original(*args)
            if name == pause:
                if change == "session":
                    ctl.store.db.execute("DELETE FROM sessions")
                elif change == "role":
                    ctl.store.db.execute("UPDATE users SET role='Viewer' WHERE id='admin'")
                elif change in ("disabled", "config"):
                    updated = {**config, "enabled": False} if change == "disabled" else {
                        **config, "region": "changed",
                    }
                    ctl.store.put("integration", config["id"], updated)
                elif change == "adapter":
                    ctl.adapters[config["id"]] = type(adapter)()
            return result

        setattr(adapter, name, wrapped)

    path = "/api/admin/cloud-accounts/check" if alias else f"/api/integrations/{config['id']}/check"
    response = client.post(path, json={"account_id": config["id"]}, headers=headers)
    if change == "unchanged":
        assert response.status_code == 200
        assert response.json()["state"] == "PASS"
        assert calls == ["stations", "devices", "latest"]
    else:
        assert response.status_code in (401, 403, 409)
        assert calls == ["stations", "devices", "latest"][:["stations", "devices", "latest"].index(pause) + 1]
        assert ctl.store.get("connection_check", config["id"])["state"] != "PASS"
        assert ctl.adapters.get(config["id"]) is not adapter
    assert not ctl.store.commands()


def test_accounts_overview_requires_full_admin_and_hides_secret(local):
    c, ctl = local
    linked(ctl)
    login(local, "operator")
    assert c.get("/api/accounts/overview").status_code == 403
    login(local, "scoped-admin")
    assert c.get("/api/accounts/overview").status_code == 403
    login(local)
    result = c.get("/api/accounts/overview")
    assert result.status_code == 200 and "SIM-PRIVATE-ONLY" not in result.text
    data = result.json()
    assert data["accounts"][0]["equipment_brand"] == "Bluesun"
    assert data["accounts"][0]["expires_at"] is None
    assert data["certificates"] == {"count": 0, "implemented": False}
    assert data["vault"]["state"] == "AVAILABLE"


def test_connection_checks_read_only_and_rate_limited(local):
    c, ctl = local
    config = linked(ctl)
    h = login(local)
    result = c.post(f"/api/integrations/{config['id']}/check", json={}, headers=h)
    assert result.status_code == 200 and result.json()["state"] == "PASS"
    checks = {c["key"]: c for c in result.json()["checks"]}
    assert checks["sample"]["count"] == 1 and checks["control"]["state"] == "NOT_COMMISSIONED"
    assert c.post(f"/api/integrations/{config['id']}/check", json={}, headers=h).status_code == 429
    assert not ctl.store.commands()


@pytest.mark.parametrize("pause", ["stations", "devices", "latest"])
def test_connection_check_holds_poll_lock_across_transport_awaits(local, pause):
    client, ctl = local
    config = linked(ctl)
    headers = login(local)
    adapter = ctl.adapters[config["id"]]
    original = getattr(adapter, pause)
    entered, release = asyncio.Event(), asyncio.Event()

    async def paused(*args):
        entered.set()
        await release.wait()
        return await original(*args)

    setattr(adapter, pause, paused)

    async def wait():
        await asyncio.wait_for(entered.wait(), 2)

    async def finish():
        release.set()

    with ThreadPoolExecutor(max_workers=1) as pool:
        future = pool.submit(client.post, f"/api/integrations/{config['id']}/check",
                             json={}, headers=headers)
        try:
            client.portal.call(wait)
            response = client.post("/api/sync", json={}, headers=headers)
            assert response.status_code == 409
            assert response.json()["error"] == "poll_already_running"
            response = client.post(f"/api/integrations/{config['id']}/enabled",
                                   json={"enabled": False}, headers=headers)
            assert response.status_code == 409
            assert ctl.store.get("integration", config["id"])["enabled"]
        finally:
            client.portal.call(finish)
        assert future.result(timeout=5).json()["state"] == "PASS"
    assert not ctl.poll_lock.locked()
    assert not ctl.store.commands()


def test_connection_failure_does_not_echo_vendor_payload(local):
    c, ctl = local
    config = linked(ctl)
    h = login(local)

    async def broken():
        raise ValueError("SIM-VENDOR-SECRET")

    ctl.adapters[config["id"]].stations = broken
    response = c.post(f"/api/integrations/{config['id']}/check", json={}, headers=h)
    assert response.json()["state"] == "FAILED"
    assert "SIM-VENDOR-SECRET" not in response.text


def test_bluesun_cloud_declaration_does_not_change_transport(local):
    c, ctl = local
    h = login(local)
    body = {
        "name": "SIM BLUESUN",
        "vendor": "SOLARMAN",
        "equipment_brand": "Bluesun",
        "region": "global",
        "credentials": {
            "app_id": "SIM",
            "app_secret": "SIM",
            "identity_value": "sim@example.invalid",
            "password": "SIMULATOR",
        },
    }
    response = c.post("/api/integrations", json=body, headers=h)
    assert response.status_code == 201
    row = ctl.store.get("integration", response.json()["id"])
    assert row["vendor"] == "SOLARMAN" and row["equipment_brand"] == "Bluesun"
    assert c.post("/api/integrations", json={**body, "vendor": "Bluesun"}, headers=h).status_code == 409


def key(local):
    c, _ = local
    h = login(local)
    response = c.post(
        "/api/access-keys", json={"name": "SIM READ", "site_ids": ["sim-site"], "expires_days": 1}, headers=h
    )
    assert response.status_code == 201
    return response.json(), h


def test_api_key_scope_revocation_and_no_privileged_routes(local):
    c, ctl = local
    row, h = key(local)
    auth = {"Authorization": "Bearer " + row["token"]}
    assert row["key"]["scope"] == "fleet:read"
    assert row["token"] not in c.get("/api/accounts/overview").text
    c.cookies.clear()
    result = c.get("/api/public/v1/fleet", headers=auth)
    assert result.status_code == 200
    assert {s["id"] for s in result.json()["sites"]} == {"sim-site"}
    assert {d["id"] for d in result.json()["devices"]} == {"sim-device"}
    assert "identity" not in result.json()["devices"][0]
    assert c.get("/api/fleet", headers=auth).status_code == 401
    assert c.get("/api/public/v1/fleet", headers={"Authorization": row["token"]}).status_code == 401
    h = login(local)
    assert c.post(f"/api/access-keys/{row['key']['id']}/revoke", json={}, headers=h).status_code == 200
    assert c.get("/api/public/v1/fleet", headers=auth).status_code == 401
    assert ctl.store.verify_audit()


@pytest.mark.parametrize("change", ["expired", "disabled_creator", "demoted_creator"])
def test_api_keys_expire_and_follow_creator_authorization(local, change):
    c, ctl = local
    row, _ = key(local)
    if change == "expired":
        record = ctl.store.get("read_api_key", row["key"]["id"])
        record["expires_at"] = (utcnow() - timedelta(seconds=1)).isoformat()
        ctl.store.put("read_api_key", record["id"], record)
    elif change == "disabled_creator":
        ctl.store.db.execute("UPDATE users SET active=0 WHERE id='admin'")
    else:
        ctl.store.db.execute("UPDATE users SET role='Viewer' WHERE id='admin'")
    assert (
        c.get("/api/public/v1/fleet", headers={"Authorization": "Bearer " + row["token"]}).status_code == 401
    )


def test_api_key_cannot_grant_future_or_unknown_sites(local):
    c, _ = local
    h = login(local)
    for ids in [["*"], ["missing"]]:
        assert c.post("/api/access-keys", json={"name": "SIM", "site_ids": ids}, headers=h).status_code == 422


PROFILE = {
    "agent_id": "SIM-AGENT",
    "device_id": "SIM-DEVICE",
    "address": "192.168.1.10",
    "logger_serial": 12345,
    "unit_id": 1,
    "inverter_model": "SIMULATOR",
    "inverter_firmware": "TEST",
    "logger_model": "SIMULATOR",
    "logger_firmware": "TEST",
    "evidence_reference": "SIMULATOR-ONLY",
    "reviewed_by": "SIM-TEST",
    "blocks": [{"function": 3, "address": 10, "count": 2}, {"function": 4, "address": 20, "count": 1}],
}


@pytest.mark.parametrize(
    "update",
    [
        {"address": "8.8.8.8"},
        {"address": "logger.local"},
        {"logger_serial": 0},
        {"unit_id": 248},
        {"blocks": [{"function": 6, "address": 10, "count": 1}]},
        {"blocks": [{"function": 3, "address": 65535, "count": 2}]},
    ],
)
def test_local_profile_rejects_unbounded_or_write_requests(update):
    with pytest.raises(ValidationError):
        CollectionProfile.model_validate({**PROFILE, **update})


def test_local_collector_only_calls_read_methods_and_disconnects():
    calls = []

    class Reader:
        def __init__(self, address, serial, **kwargs):
            assert address == PROFILE["address"] and kwargs["socket_timeout"] == 5

        def read_holding_registers(self, address, count):
            calls.append((3, address, count))
            return [32768, 10]

        def read_input_registers(self, address, count):
            calls.append((4, address, count))
            return [15]

        def disconnect(self):
            calls.append("closed")

    points = collect(CollectionProfile.model_validate(PROFILE), Reader)
    assert calls == [(3, 10, 2), (4, 20, 1), "closed"]
    assert [p["value"] for p in points] == [32768, 10, 15]
    assert all(p["unit"] is None for p in points)
    assert points[0]["key"] == "solarman_v5.fc3.r10"


def test_local_read_failure_does_not_return_partial_collection():
    closed = []

    class Reader:
        def __init__(self, *a, **kw):
            pass

        def read_holding_registers(self, *a):
            return [12]  # wrong quantity

        def disconnect(self):
            closed.append(True)

    with pytest.raises(ValueError):
        collect(CollectionProfile.model_validate(PROFILE), Reader)
    assert closed == [True]


def test_rollout_canary_then_remaining_uses_authoritative_readback(local, capability):
    c, ctl = local
    h = login(local, "engineer")
    first = ctl.device("sim-device")
    second = first.model_copy(update={"id": "sim-device-2", "vendor_id": "SIM-2"})
    ctl.store.put("device", second.id, second.model_dump(mode="json"))
    simulators = {first.id: Simulator(), second.id: Simulator()}
    ctl.capability = lambda device, intent: capability.model_copy(update={"identity": device.identity})
    ctl.engine.capability = ctl.capability
    ctl.engine.adapter = lambda d: simulators[d.id]
    ctl.engine.compiler = lambda d, i, p: (
        [VendorCall(path="/simulator", body=p)],
        {"maxChargeCurrent": p["value"]},
    )
    ctl.engine.writes_enabled = True
    ctl.engine.poll_seconds = 0.001
    actions = [
        {"device_id": d.id, "intent": "SET_MAX_CHARGE_CURRENT", "parameters": {"value": 20}}
        for d in [first, second]
    ]
    created = c.post("/api/rollouts", json={"name": "SIM canary", "actions": actions}, headers=h)
    assert created.status_code == 201
    path = "/api/rollouts/" + created.json()["id"]
    preview = c.post(path + "/preview", json={}, headers=h).json()
    assert all(t["status"] == "READY" for t in preview["targets"])
    assert (
        c.post(
            path + "/confirm", json={"digest": preview["digest"], "stage": "remaining"}, headers=h
        ).status_code
        == 409
    )
    assert (
        c.post(
            path + "/confirm", json={"digest": preview["digest"], "stage": "canary"}, headers=h
        ).status_code
        == 200
    )

    async def settle():
        await asyncio.gather(*list(ctl.engine.tasks))

    c.portal.call(settle)
    current = c.get("/api/workbench").json()["rollout"][0]
    assert current["state"] == "CANARY_VERIFIED" and simulators[second.id].sent == 0
    preview = c.post(path + "/preview", json={}, headers=h).json()
    assert (
        c.post(
            path + "/confirm", json={"digest": preview["digest"], "stage": "remaining"}, headers=h
        ).status_code
        == 200
    )
    c.portal.call(settle)
    assert c.get("/api/workbench").json()["rollout"][0]["state"] == "VERIFIED"
    assert [sim.sent for sim in simulators.values()] == [1, 1]


def test_all_pages_share_one_global_stylesheet():
    assets = Path(__file__).resolve().parents[1] / "src/solar_fleet/static"
    assert [p.name for p in assets.glob("*.css")] == ["app.css"]
    for file in assets.glob("*.js"):
        source = file.read_text(encoding="utf-8")
        assert (
            'document.createElement("style")' not in source
            and "document.createElement('style')" not in source
        )
        assert ".style." not in source
