"""Controller ingestion uses a test-only fake transport, not a shipping simulated integration."""

import asyncio

import pytest
from cryptography.fernet import Fernet

from solar_fleet.controller import Controller
from solar_fleet.domain import SafetyError
from solar_fleet.security import Vault


@pytest.mark.parametrize("change", ["disable", "replace", "site", "site_row", "binding", "missing", "aba", "unchanged", "unrelated", "heartbeat", "heartbeat_missing"])
async def test_poll_revalidates_snapshot_after_latest_wait(store, change):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    await controller.discover(config, adapter)
    original = adapter.latest
    entered, release = asyncio.Event(), asyncio.Event()

    async def latest(serials):
        entered.set()
        await release.wait()
        return [] if change in {"missing", "heartbeat_missing"} else await original(serials)

    adapter.latest = latest
    task = asyncio.create_task(controller.poll())
    try:
        await asyncio.wait_for(entered.wait(), 2)
        device = store.list("device")[0]
        if change in {"heartbeat", "heartbeat_missing"}:
            device["last_seen"] = "2026-09-28T12:00:00+00:00"
            store.put("device", device["id"], device)
        elif change == "unrelated":
            for kind in ("integration", "device", "binding", "site"):
                store.put(kind, "unrelated", {"id": "unrelated"})
        elif change == "disable":
            store.put("integration", "sim", config | {"enabled": False})
        elif change == "aba":
            store.put("integration", "sim", config | {"enabled": False})
            store.put("integration", "sim", config)
        elif change == "replace":
            controller.adapters["sim"] = SimulatedDiscovery()
        elif change in {"site", "missing"}:
            device["site_id"] = "SIM-NEW-SITE"
            store.put("device", device["id"], device)
        elif change == "binding":
            binding = store.list("binding")[0]
            store.put("binding", binding["id"], binding | {"telemetry_enabled": False})
        elif change == "site_row":
            site = store.get("site", device["site_id"])
            store.put("site", device["site_id"], site | {"vendor": "FOREIGN"})
        snapshot = store.get("device", device["id"])
    finally:
        release.set()
        await asyncio.wait_for(task, 2)
    if change in {"unchanged", "unrelated"}:
        assert len(store.list("latest")) == 1
        assert store.get("integration_state", "sim")["state"] == "CONNECTED"
    else:
        assert store.list("latest") == []
        assert store.report_samples(device["id"]) == []
        assert store.get("device", device["id"]) == snapshot
        assert store.get("integration_state", "sim")["error"] == "poll_context_changed"


@pytest.mark.parametrize("pause", ["stations", "devices"])
@pytest.mark.parametrize("change", [
    "disable", "replace", "binding", "aba", "delete_restore", "unchanged",
    "unrelated_integration", "unrelated_inventory_aba",
])
async def test_discovery_wait_does_not_overwrite_changed_context(store, pause, change):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    await controller.discover(config, adapter)
    entered, release = asyncio.Event(), asyncio.Event()
    original = getattr(adapter, pause)

    async def blocked(*args):
        entered.set()
        await release.wait()
        return await original(*args)

    setattr(adapter, pause, blocked)
    task = asyncio.create_task(controller.discover(config, adapter))
    try:
        await asyncio.wait_for(entered.wait(), 2)
        if change == "unrelated_integration":
            store.put("integration", "other", config | {"id": "other"})
        elif change == "unrelated_inventory_aba":
            store.put("device", "other", {"id": "other"})
            store.db.execute("DELETE FROM entities WHERE kind='device' AND id='other'")
        elif change == "delete_restore":
            store.db.execute("DELETE FROM entities WHERE kind='integration' AND id='sim'")
            store.put("integration", "sim", config)
        elif change == "disable":
            store.put("integration", "sim", config | {"enabled": False})
        elif change == "aba":
            store.put("integration", "sim", config | {"enabled": False})
            store.put("integration", "sim", config)
        elif change == "replace":
            controller.adapters["sim"] = SimulatedDiscovery()
        elif change == "binding":
            binding = store.list("binding")[0]
            store.put("binding", binding["id"], binding | {"telemetry_enabled": False})
        snapshot = {kind: store.list(kind) for kind in ("site", "device", "binding", "discovery")}
    finally:
        release.set()
        result = await asyncio.gather(task, return_exceptions=True)
    if change in {"unchanged", "unrelated_integration"}:
        assert result == [None]
    else:
        assert str(result[0]) == "discovery_context_changed"
        assert {kind: store.list(kind) for kind in snapshot} == snapshot


@pytest.mark.parametrize("missing", [False, True])
async def test_poll_snapshot_capture_blocks_interleaved_device_write(tmp_path, monkeypatch, missing):
    import sqlite3

    from solar_fleet.storage import Store

    store = Store(tmp_path / "capture.sqlite")
    other = Store(tmp_path / "capture.sqlite")
    try:
        other.db.execute("PRAGMA busy_timeout=0")
        config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
        store.put("integration", "sim", config)
        controller = Controller(store, Vault(store, Fernet.generate_key()))
        adapter = SimulatedDiscovery()
        controller.adapters["sim"] = adapter
        await controller.discover(config, adapter)
        original_list = store.list
        attempted = False
        blocked = False

        def interleaved_list(kind):
            nonlocal attempted, blocked
            rows = original_list(kind)
            if kind == "device" and not attempted:
                attempted = True
                try:
                    other.put("device", rows[0]["id"], rows[0] | {"name": "newer name"})
                except sqlite3.OperationalError as exc:
                    assert "locked" in str(exc)
                    blocked = True
            return rows

        latest = adapter.latest

        async def response(serials):
            assert not store.db.in_transaction
            rows = await latest(serials)
            return [] if missing else rows

        monkeypatch.setattr(store, "list", interleaved_list)
        adapter.latest = response
        await controller.poll()
        assert attempted and blocked
        assert store.get("integration_state", "sim")["state"] == "CONNECTED"
        assert len(store.list("latest")) == (0 if missing else 1)
    finally:
        other.close()
        store.close()


@pytest.mark.parametrize("missing", [False, True])
async def test_poll_rechecks_aba_after_acquiring_write_lock(tmp_path, monkeypatch, missing):
    from contextlib import contextmanager

    from solar_fleet.storage import Store

    store = Store(tmp_path / "poll.sqlite")
    other = Store(tmp_path / "poll.sqlite")
    try:
        config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
        store.put("integration", "sim", config)
        controller = Controller(store, Vault(store, Fernet.generate_key()))
        adapter = SimulatedDiscovery()
        controller.adapters["sim"] = adapter
        await controller.discover(config, adapter)
        device = store.list("device")[0]
        latest = adapter.latest
        transaction = store.transaction
        armed = False
        injected = False

        @contextmanager
        def interleaved_transaction():
            nonlocal injected
            # Revision checks also use transactions. Inject only at the poll
            # persistence scope, after preflight but before acquiring its lock.
            import inspect

            caller = inspect.currentframe().f_back.f_back
            if armed and not injected and caller.f_code.co_name == "poll":
                injected = True
                other.put("device", device["id"], device | {"name": "interleaved"})
                other.put("device", device["id"], device)
            with transaction() as db:
                yield db

        async def response(serials):
            nonlocal armed
            rows = await latest(serials)
            armed = True
            return [] if missing else rows

        monkeypatch.setattr(store, "transaction", interleaved_transaction)
        adapter.latest = response
        await controller.poll()
        assert injected
        assert store.get("device", device["id"]) == device
        assert store.list("latest") == []
        assert store.report_samples(device["id"]) == []
        assert store.get("poll_cursor", "sim") is None
        assert store.get("integration_state", "sim")["error"] == "poll_context_changed"
    finally:
        other.close()
        store.close()


@pytest.mark.parametrize("rediscover", [False, True])
async def test_disabled_binding_is_not_reenabled_or_polled(store, rediscover):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    await controller.discover(config, adapter)
    binding = store.list("binding")[0]
    store.put("binding", binding["id"], binding | {"telemetry_enabled": False})
    if rediscover:
        await controller.discover(config, adapter)
    requested = []

    async def latest(serials):
        requested.append(serials)
        return []

    adapter.latest = latest
    await controller.poll()
    assert requested == []
    assert store.get("binding", binding["id"])["telemetry_enabled"] is False
    assert store.list("latest") == []


async def test_invalid_discovery_rolls_back_inventory(store):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    original = adapter.devices

    async def duplicate(id):
        rows = await original(id)
        return rows + rows

    adapter.devices = duplicate
    with pytest.raises(SafetyError, match="ambiguous_device_site_binding"):
        await controller.discover(config, adapter)
    for kind in ("site", "device", "binding", "discovery"):
        assert store.list(kind) == []


@pytest.mark.parametrize("failure", ["foreign", "malformed", "write", "unchanged"])
async def test_latest_batch_is_atomic(store, monkeypatch, failure):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    await controller.discover(config, adapter)
    device = store.list("device")[0]
    original = adapter.latest

    async def latest(serials):
        rows = await original(serials)
        if failure == "foreign":
            rows.append(rows[0] | {"deviceSn": "FOREIGN"})
        elif failure == "malformed":
            rows.append(None)
        return rows

    adapter.latest = latest
    original_put = store.put

    def put(kind, id, body):
        if failure == "write" and kind == "poll_cursor":
            raise RuntimeError("simulated_storage_failure")
        return original_put(kind, id, body)

    monkeypatch.setattr(store, "put", put)
    await controller.poll()
    if failure == "unchanged":
        assert store.list("latest")
        assert store.report_samples(device["id"])
        assert store.get("integration_state", "sim")["state"] == "CONNECTED"
    else:
        assert store.list("latest") == []
        assert store.report_samples(device["id"]) == []
        assert store.get("device", device["id"]) == device
        assert store.list("poll_cursor") == []
        assert store.get("integration_state", "sim")["state"] == "ERROR"


@pytest.mark.parametrize("field", ["id", "device_id", "site_id", "integration_id", "vendor_device_sn", "source"])
@pytest.mark.parametrize("missing_response", [False, True])
async def test_poll_rejects_preexisting_binding_identity_mismatch(store, field, missing_response):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    await controller.discover(config, adapter)
    binding = store.list("binding")[0]
    store.put("binding", binding["id"], binding | {field: "FOREIGN"})
    device = store.list("device")[0]
    original = adapter.latest
    calls = []

    async def latest(serials):
        calls.append(serials)
        return [] if missing_response else await original(serials)

    adapter.latest = latest
    await controller.poll()
    assert calls == []
    assert store.list("latest") == []
    assert store.report_samples(device["id"]) == []
    assert store.get("device", device["id"]) == device
    assert store.get("integration_state", "sim")["error"] == "poll_binding_identity_mismatch"


@pytest.mark.parametrize("corruption", ["device_vendor", "site_id", "site_vendor", "site_source"])
async def test_poll_rejects_corrupt_site_or_vendor_before_transport(store, corruption):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    adapter = SimulatedDiscovery()
    controller.adapters["sim"] = adapter
    await controller.discover(config, adapter)
    device = store.list("device")[0]
    if corruption == "device_vendor":
        device["identity"]["vendor"] = "FOREIGN"
        store.put("device", device["id"], device)
    else:
        site = store.get("site", device["site_id"])
        site[corruption.removeprefix("site_")] = "FOREIGN"
        store.put("site", device["site_id"], site)
    calls = []

    async def latest(serials):
        calls.append(serials)
        return []

    adapter.latest = latest
    await controller.poll()
    assert calls == []
    assert store.list("latest") == []
    assert store.list("poll_cursor") == []
    assert store.report_samples(device["id"]) == []
    assert store.get("device", device["id"]) == device
    assert store.get("integration_state", "sim")["error"] == "poll_site_vendor_identity_mismatch"


class SimulatedDiscovery:
    bad_serial = False

    async def stations(self):
        return [{"id": 1, "name": "SIM-SITE", "regionTimezone": "Asia/Bangkok"}]

    async def devices(self, id):
        return [
            {"deviceSn": "SIM-INV", "deviceType": "INVERTER", "connectStatus": 1, "productId": "SIM-PRODUCT"}
        ]

    async def latest(self, serials):
        from solar_fleet.domain import utcnow

        if not serials:
            return []
        return [
            {
                "deviceSn": "WRONG-DEVICE" if self.bad_serial else "SIM-INV",
                "deviceType": "INVERTER",
                "deviceState": 1,
                "collectionTime": int(utcnow().timestamp()),
                "dataList": [{"key": "sim-PV", "value": 1.2, "unit": "kW"}],
            }
        ]


async def test_discovery_and_ingestion_preserve_unknown_identity_and_native_provenance(store):
    store.put("integration", "sim", {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"})
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    controller.adapters["sim"] = SimulatedDiscovery()
    await controller.poll()
    devices = store.list("device")
    assert len(store.list("site")) == 1 and len(devices) == 1 and len(store.list("binding")) == 1
    device = controller.device(devices[0]["id"])
    assert device.identity.model is None and device.identity.logger_model is None
    latest = controller.latest(device)
    assert latest["samples"][0]["source"] == "VENDOR_CLOUD"
    assert latest["samples"][0]["metric"] == "deye.sim-PV" and latest["samples"][0]["quality"] == "UNVERIFIED"


@pytest.mark.parametrize("change", [
    "row_device", "row_site", "row_binding", "legacy", "sample_device", "sample_binding",
    "sample_source", "disabled", "binding_disabled", "binding_site", "vendor", "stale_device", "unchanged",
])
async def test_cloud_latest_rejects_invalid_provenance_without_mutating_storage(store, change):
    config = {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"}
    store.put("integration", "sim", config)
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    controller.adapters["sim"] = SimulatedDiscovery()
    await controller.poll()
    device = controller.device(store.list("device")[0]["id"])
    row = store.get("latest", device.id)
    if change.startswith("row_"):
        row[change.removeprefix("row_") + "_id"] = "FOREIGN"
    elif change == "legacy":
        row.pop("site_id", None)
    elif change.startswith("sample_"):
        field = change.removeprefix("sample_")
        row["samples"][0][field if field == "source" else field + "_id"] = (
            "AGENT" if field == "source" else "FOREIGN"
        )
    elif change == "disabled":
        store.put("integration", "sim", config | {"enabled": False})
    elif change.startswith("binding_"):
        binding = store.list("binding")[0]
        binding.update({"telemetry_enabled": False} if change == "binding_disabled" else {"site_id": "FOREIGN"})
        store.put("binding", binding["id"], binding)
    elif change == "vendor":
        store.put("integration", "sim", config | {"vendor": "FOREIGN"})
    elif change == "stale_device":
        current = store.get("device", device.id)
        store.put("device", device.id, current | {"site_id": "FOREIGN"})
    store.put("latest", device.id, row)
    result = controller.latest(device)
    if change == "unchanged":
        assert result["samples"]
        assert result["native"] == row["native"]
    else:
        assert result == {"device_id": device.id, "samples": [], "state": "NO_DATA"}
    assert store.get("latest", device.id) == row


async def test_foreign_serial_response_cannot_poison_measurements(store):
    store.put("integration", "sim", {"id": "sim", "vendor": "Deye", "enabled": True, "region": "eu"})
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    simulated = SimulatedDiscovery()
    simulated.bad_serial = True
    controller.adapters["sim"] = simulated
    await controller.poll()
    assert store.list("latest") == []
    assert store.get("integration_state", "sim")["error"] == "latest_response_device_mismatch"


async def test_same_hardware_in_two_accounts_has_one_identity_and_two_bindings(store):
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    for id in ["account-a", "account-b"]:
        store.put("integration", id, {"id": id, "vendor": "Deye", "enabled": True, "region": "eu"})
        controller.adapters[id] = SimulatedDiscovery()
    await controller.poll()
    assert len(store.list("device")) == 1
    assert len(store.list("site")) == 1
    assert len(store.list("binding")) == 2
    assert store.list("device")[0]["integration_id"] == "account-a"
