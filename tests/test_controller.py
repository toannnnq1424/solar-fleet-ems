"""Controller ingestion uses a test-only fake transport, not a shipping simulated integration."""

from cryptography.fernet import Fernet

from solar_fleet.controller import Controller
from solar_fleet.security import Vault


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
