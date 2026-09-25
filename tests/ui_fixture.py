"""Manual browser QA only: in-memory SIMULATOR data, no outbound connections.

Run from repository root: python tests/ui_fixture.py
Never installed into the production wheel. Stop the process to discard all data.
"""

import os
from datetime import timedelta

import httpx
import uvicorn
from cryptography.fernet import Fernet

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import (
    Ack,
    Capability,
    Configuration,
    Constraint,
    Device,
    DeviceIdentity,
    OrderResult,
    Role,
    Sample,
    Source,
    utcnow,
)
from solar_fleet.security import Vault, create_user
from solar_fleet.storage import Store


def fixture_app(port=8767):
    async def block_async(*args, **kwargs):
        raise RuntimeError("SIMULATOR fixture forbids outbound HTTP")

    def block_sync(*args, **kwargs):
        raise RuntimeError("SIMULATOR fixture forbids outbound HTTP")

    httpx.AsyncHTTPTransport.handle_async_request = block_async
    httpx.HTTPTransport.handle_request = block_sync
    store = Store(":memory:")
    create_user(store, "ui-review", "LOCAL-UI-REVIEW-ONLY-2026", Role.ENGINEER, ["*"])
    create_user(store, "ui-admin", "LOCAL-UI-REVIEW-ONLY-2026", Role.ADMIN, ["*"])
    create_user(store, "ui-viewer", "LOCAL-UI-REVIEW-ONLY-2026", Role.VIEWER, ["*"])
    create_user(store, "ui-reviewer", "LOCAL-UI-REVIEW-ONLY-2026", Role.INSTALLER, ["*"])
    ctl = Controller(store, Vault(store, Fernet.generate_key()), writes_enabled=True)
    now = utcnow()
    for index, vendor in enumerate(("Deye", "Solis", "SOLARMAN")):
        site_id, device_id = f"SIM-SITE-{index}", f"SIM-DEVICE-{index}"
        store.put(
            "site",
            site_id,
            {
                "id": site_id,
                "name": f"SIMULATOR plant {index + 1}",
                "vendor": vendor,
                "timezone": "Asia/Ho_Chi_Minh",
                "source": "SIMULATOR",
            },
        )
        device = Device(
            id=device_id,
            site_id=site_id,
            integration_id="SIMULATOR",
            vendor_id=device_id,
            name=f"SIMULATOR {vendor}",
            type="INVERTER",
            online=True,
            last_seen=now,
            identity=DeviceIdentity(
                vendor=vendor,
                model="SIMULATOR",
                logger_model="SIMULATOR",
                firmware="TEST",
                protocol_version="TEST",
                account_type="TEST",
                privilege="TEST",
                region="TEST",
            ),
            metadata={"test_only": True},
        )
        store.put("device", device.id, device.model_dump(mode="json"))
        samples = [
            Sample(
                device_id=device_id,
                metric="sim.power",
                value=100 + point * 10,
                unit="W",
                source=Source.SIMULATOR,
                source_timestamp=now - timedelta(minutes=point),
                quality="UNVERIFIED",
                binding_id="SIMULATOR",
                evidence_ids=["SIMULATOR_ONLY"],
            )
            for point in range(48)
        ]
        store.add_samples(samples)
        store.put(
            "latest",
            device_id,
            {
                "samples": [samples[0].model_dump(mode="json")],
                "source": "SIMULATOR",
                "received_at": now.isoformat(),
                "native": {
                    "dataList": [
                        {
                            "key": "SIMULATOR-state",
                            "title": "SIMULATOR operating state",
                            "value": "Charging",
                            "unit": "",
                        },
                        {
                            "key": "SIMULATOR-energy",
                            "title": "SIMULATOR energy",
                            "value": "1.234",
                            "unit": "kWh",
                        },
                    ]
                },
            },
        )
    # Dedicated observed source for mapping browser flows; remains UNVERIFIED.
    store.put(
        "binding",
        "SIM-MAPPING-BIND",
        {
            "id": "SIM-MAPPING-BIND",
            "device_id": "SIM-DEVICE-0",
            "site_id": "SIM-SITE-0",
            "telemetry_enabled": True,
            "name": "SIMULATOR meter source",
        },
    )
    mapping_sample = Sample(
        device_id="SIM-DEVICE-0",
        metric="deye.lab_power",
        value=2.5,
        unit="kW",
        source=Source.SIMULATOR,
        source_timestamp=now,
        quality="UNVERIFIED",
        binding_id="SIM-MAPPING-BIND",
    )
    latest = store.get("latest", "SIM-DEVICE-0")
    latest["samples"].append(mapping_sample.model_dump(mode="json"))
    latest["native"]["dataList"].append(
        {"key": "lab_power", "title": "SIMULATOR AC flow", "value": "2.5", "unit": "kW"}
    )
    store.put("latest", "SIM-DEVICE-0", latest)
    original = ctl.capability

    def capability(device, intent):
        if device.id == "SIM-DEVICE-0" and intent == "SET_MAX_CHARGE_CURRENT":
            return Capability(
                intent=intent,
                state="VERIFIED",
                semantic_match="exact",
                identity=device.identity,
                evidence_ids=["SIMULATOR_ONLY"],
                evidence_grade="E",
                hardware_verified=True,
                constraints={"value": Constraint(min=0, max=50, step=1, unit="A")},
                transport="SIMULATOR",
                reason="TEST ONLY; no real hardware",
                readback_fields=["maxChargeCurrent"],
            )
        return original(device, intent)

    class FixtureTransport:
        version = "0.1.0"
        value = 10

        async def configuration(self, device):
            return Configuration(
                values={"maxChargeCurrent": self.value}, device_timestamp=utcnow(), freshness_verified=True
            )

        async def send(self, call):
            self.value = call.body["value"]
            return Ack(order_id="SIMULATOR-ORDER", online=True)

        async def order(self, id):
            return OrderResult(state="SUCCEEDED", vendor_status="SIMULATOR")

        async def close(self):
            pass

    ctl.adapters["SIMULATOR"] = FixtureTransport()

    class FixtureAccount:
        async def stations(self):
            return [{"id": "SIM-PLANT", "name": "SIMULATOR connection check"}]

        async def devices(self, id):
            return [{"deviceSn": "SIM-LOGGER"}]

        async def latest(self, ids):
            return [{"deviceSn": "SIM-LOGGER", "dataList": [{"key": "SIM-POWER", "value": 100}]}]

        async def close(self):
            pass

    for i, vendor in enumerate(
        ["Deye", "Solis", "GoodWe", "Sungrow", "Huawei", "Growatt", "SOLARMAN", "Bluesun"]
    ):
        id = f"SIM-ACCOUNT-{i}"
        store.put(
            "integration",
            id,
            {
                "id": id,
                "name": "SIMULATOR · " + vendor,
                "vendor": "SOLARMAN" if vendor == "Bluesun" else vendor,
                "equipment_brand": "Bluesun" if vendor == "Bluesun" else None,
                "region": "TEST",
                "enabled": True,
            },
        )
        ctl.vault.put(id, {"identity_value": "simulator@example.invalid"})
        ctl.adapters[id] = FixtureAccount()
        store.put("integration_state", id, {"state": "CONNECTED", "last_success": now.isoformat()})
        store.put(
            "binding",
            id,
            {"id": id, "integration_id": id, "site_id": "SIM-SITE-0", "device_id": "SIM-DEVICE-0"},
        )
    ctl.capability = capability
    ctl.engine.capability = capability
    ctl.engine.poll_seconds = 0.01
    app = create_app(ctl, port=port, poll=False)

    @app.get("/api/fixture-marker")
    async def marker():
        return {"fixture": "SIMULATOR", "run_id": os.environ.get("SOLAR_UI_FIXTURE_RUN_ID", "manual")}

    return app


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, default=8767)
    args = parser.parse_args()
    uvicorn.run(
        fixture_app(args.port), host="127.0.0.1", port=args.port, access_log=False, log_level="warning"
    )
