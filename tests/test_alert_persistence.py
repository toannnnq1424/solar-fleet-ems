"""SQLite second-connection ABA precisely before the alerts persistence lock."""

from contextlib import contextmanager

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.controller import entity_id
from solar_fleet.storage import Store


@pytest.fixture
def store(tmp_path):
    instance = Store(tmp_path / "alerts.sqlite")
    yield instance
    instance.close()


@pytest.mark.parametrize("kind", ["integration", "device", "binding", "site"])
def test_alerts_revalidate_after_acquiring_persistence_lock(local, monkeypatch, kind):
    client, ctl = local
    headers = login(local, "viewer")
    store = ctl.store
    device = store.get("device", "sim-device")
    device["identity"]["vendor"] = "Deye"
    store.put("device", device["id"], device)
    config = {"id": device["integration_id"], "vendor": "Deye", "enabled": True}
    store.put("integration", config["id"], config)
    bid = entity_id(config["id"], "binding", device["vendor_id"])
    store.put("binding", bid, {"id": bid, "device_id": device["id"], "site_id": device["site_id"],
                              "integration_id": config["id"], "vendor_device_sn": device["vendor_id"],
                              "source": "VENDOR_CLOUD", "telemetry_enabled": True})
    selected = {"integration": config["id"], "device": device["id"], "binding": bid, "site": device["site_id"]}
    path = store.db.execute("PRAGMA database_list").fetchone()[2]
    other = Store(path)
    transaction = store.transaction
    armed = False
    fired = False

    class Transport:
        async def alerts(self, *args):
            nonlocal armed
            assert not store.db.in_transaction
            armed = True
            return []

        async def close(self):
            pass

    @contextmanager
    def boundary():
        nonlocal fired
        # Only the route's outer persistence transaction, not nested guard reads.
        import inspect

        caller = inspect.currentframe().f_back
        is_alerts = False
        for _ in range(3):
            if caller is None:
                break
            if caller.f_code.co_name == "alerts":
                is_alerts = True
            caller = caller.f_back
        if armed and not fired and is_alerts and not store.db.in_transaction:
            fired = True
            original = other.get(kind, selected[kind])
            other.db.execute("DELETE FROM entities WHERE kind=? AND id=?", (kind, selected[kind]))
            other.put(kind, selected[kind], original)
        with transaction():
            yield

    ctl.adapters[config["id"]] = Transport()
    monkeypatch.setattr(store, "transaction", boundary)
    try:
        response = client.post("/api/devices/sim-device/alerts", json={}, headers=headers)
        assert fired, response.text
        assert response.status_code == 409, response.text
        assert store.get("alerts", "sim-device") is None
        assert store.list("incident") == []
    finally:
        other.close()