"""Explicit synthetic cloud provenance for tests; never uses a transport."""

from solar_fleet.controller import entity_id


def cloud_latest(store, device_id, row):
    device = store.get("device", device_id)
    vendor = device["identity"]["vendor"]
    integration_id = device["integration_id"]
    binding_id = entity_id(integration_id, "binding", device["vendor_id"])
    store.put("integration", integration_id, {
        "id": integration_id, "vendor": vendor, "enabled": True,
        "name": "SIMULATOR cloud provenance", "region": "TEST",
    })
    site = store.get("site", device["site_id"]) or {"id": device["site_id"]}
    store.put("site", device["site_id"], site | {"vendor": vendor, "source": "VENDOR_CLOUD"})
    store.put("binding", binding_id, {
        "id": binding_id, "device_id": device_id, "site_id": device["site_id"],
        "integration_id": integration_id, "vendor_device_sn": device["vendor_id"],
        "source": "VENDOR_CLOUD", "telemetry_enabled": True,
    })
    row = row | {
        "device_id": device_id, "site_id": device["site_id"],
        "binding_id": binding_id, "source": "VENDOR_CLOUD",
        "samples": [s | {"binding_id": binding_id, "source": "VENDOR_CLOUD"} for s in row["samples"]],
    }
    store.put("latest", device_id, row)
    return binding_id