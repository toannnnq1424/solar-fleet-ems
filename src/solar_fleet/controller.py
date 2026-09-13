from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime

from .adapters.deye import Budgets, Deye, source_time
from .catalog import capabilities
from .control import CommandEngine
from .domain import Device, DeviceIdentity, SafetyError, Sample, utcnow
from .security import Vault, principal, redact
from .storage import Store
from .telemetry import normalize_points, refresh_quality


def entity_id(*parts) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:24]


class Controller:
    """One local process. No fake integrations, vendor switching or writable protocol fallbacks."""

    def __init__(self, store: Store, vault: Vault, *, writes_enabled=False):
        self.store, self.vault = store, vault
        self.adapters = {}
        self.budgets = Budgets()
        self.poll_lock = asyncio.Lock()
        self.poll_task = None
        self.last_poll = 0.0
        self.engine = CommandEngine(
            store,
            self.device,
            self.adapter,
            self.capability,
            lambda id: principal(store, id),
            writes_enabled=writes_enabled,
        )

    def device(self, id: str) -> Device:
        row = self.store.get("device", id)
        if not row:
            raise SafetyError("device_not_found")
        return Device.model_validate(row)

    def adapter(self, device: Device) -> Deye:
        return self.integration_adapter(device.integration_id)

    def integration_adapter(self, id: str) -> Deye:
        if id not in self.adapters:
            config = self.store.get("integration", id)
            if not config or config.get("vendor") != "Deye" or not config.get("enabled"):
                raise SafetyError("integration_not_available")
            self.adapters[id] = Deye(config, self.vault.get(id), budgets=self.budgets)
        return self.adapters[id]

    def capability(self, device: Device, intent: str):
        candidate = next((c for c in capabilities(device) if c.intent == intent), None)
        if candidate is None:
            raise SafetyError("intent_unknown")
        return candidate

    async def start(self):
        self.store.recover_commands()
        self.poll_task = asyncio.create_task(self._loop())

    async def close(self):
        if self.poll_task:
            self.poll_task.cancel()
            await asyncio.gather(self.poll_task, return_exceptions=True)
        await self.engine.close()
        await asyncio.gather(*(a.close() for a in self.adapters.values()), return_exceptions=True)

    async def _loop(self):
        while True:
            try:
                await self.poll()
            except asyncio.CancelledError:
                raise
            except Exception:
                self.store.audit("system", {"event": "poll_failed", "reason": "internal_poll_error"})
            await asyncio.sleep(120)

    async def discover(self, config: dict, adapter: Deye):
        stations = await adapter.stations()
        discovered = []
        for station in stations:
            vendor_id = station.get("id")
            if not isinstance(vendor_id, int) or isinstance(vendor_id, bool):
                raise SafetyError("station_identity_invalid")
            site_id = entity_id("Deye", config["region"], "station", vendor_id)
            site = {
                "id": site_id,
                "integration_id": config["id"],
                "vendor_id": vendor_id,
                "name": str(station.get("name") or vendor_id),
                "vendor": "Deye",
                "timezone": station.get("regionTimezone"),
                "source": "VENDOR_CLOUD",
                "discovered_at": utcnow().isoformat(),
                "native": redact(station),
            }
            self.store.put("site", site_id, site)
            for raw in await adapter.devices(vendor_id):
                serial = raw.get("deviceSn")
                if not isinstance(serial, str) or not serial:
                    raise SafetyError("device_identity_invalid")
                # A serial seen through two accounts must not create two independent command queues.
                id = entity_id("Deye", "device", serial)
                binding_id = entity_id(config["id"], "binding", serial)
                if id in discovered:
                    raise SafetyError("ambiguous_device_site_binding")
                previous = self.store.get("device", id)
                device = Device(
                    id=id,
                    site_id=site_id,
                    integration_id=config["id"],
                    vendor_id=serial,
                    type=str(raw.get("deviceType") or "UNKNOWN"),
                    identity=DeviceIdentity(
                        vendor="Deye",
                        region=config["region"],
                        account_type=config.get("account_type"),
                        privilege=config.get("privilege"),
                    ),
                    last_seen=source_time(raw.get("collectionTime")),
                    online=raw.get("connectStatus") == 1,
                    metadata={
                        "discovery": redact(raw),
                        "product_id": raw.get("productId"),
                        "identity_state": "UNKNOWN",
                    },
                )
                if previous:
                    if previous["site_id"] != site_id or previous["type"] != device.type:
                        raise SafetyError("ambiguous_device_site_or_type_binding")
                    # Discovery is not commissioning; do not convert productId into a claimed model number.
                    device.last_seen = Device.model_validate(previous).last_seen
                    if previous["integration_id"] != config["id"]:
                        # Keep one explicit primary transport; additional account paths remain separate bindings.
                        device = Device.model_validate(previous)
                self.store.put("device", id, device.model_dump(mode="json"))
                self.store.put(
                    "binding",
                    binding_id,
                    {
                        "id": binding_id,
                        "device_id": id,
                        "site_id": site_id,
                        "source": "VENDOR_CLOUD",
                        "integration_id": config["id"],
                        "vendor_device_sn": serial,
                        "telemetry_enabled": True,
                        "control_enabled": False,
                        "evidence_ids": ["DEYE_API_001"],
                    },
                )
                discovered.append(id)
        for old in self.store.list("device"):
            if old["integration_id"] == config["id"] and old["id"] not in discovered:
                old["online"] = False
                old["metadata"]["discovery_missing"] = True
                self.store.put("device", old["id"], old)
        self.store.put("discovery", config["id"], {"last_success": utcnow().isoformat()})

    async def poll(self):
        if self.poll_lock.locked():
            raise SafetyError("poll_already_running")
        if time.monotonic() - self.last_poll < 15:
            raise SafetyError("poll_cooldown")
        async with self.poll_lock:
            self.last_poll = time.monotonic()
            for config in self.store.list("integration"):
                if not config.get("enabled"):
                    continue
                state = {"id": config["id"], "last_attempt": utcnow().isoformat(), "state": "CONNECTING"}
                try:
                    adapter = self.integration_adapter(config["id"])
                    discovery = self.store.get("discovery", config["id"])
                    if (
                        not discovery
                        or (utcnow() - datetime.fromisoformat(discovery["last_success"])).total_seconds()
                        > 900
                    ):
                        await self.discover(config, adapter)
                    devices = [
                        Device.model_validate(d)
                        for d in self.store.list("device")
                        if d["integration_id"] == config["id"] and not d["metadata"].get("discovery_missing")
                    ]
                    # Pilot budget: 50 devices per cycle; rotate fairly beyond that and report degradation.
                    cursor = (self.store.get("poll_cursor", config["id"]) or {}).get("offset", 0)
                    selected = (devices[cursor:] + devices[:cursor])[:50] if devices else []
                    wanted = {d.vendor_id: d for d in selected}
                    rows = await adapter.latest(list(wanted))
                    seen = set()
                    for raw in rows:
                        device = wanted.get(raw.get("deviceSn"))
                        if device is None:
                            raise SafetyError("latest_response_device_mismatch")
                        seen.add(device.id)
                        timestamp = source_time(raw.get("collectionTime"))
                        device.last_seen = timestamp
                        device.online = raw.get("deviceState") == 1
                        points = raw.get("dataList")
                        if not isinstance(points, list) or any(not isinstance(p, dict) for p in points):
                            raise SafetyError("vendor_invalid_measurements")
                        binding_id = entity_id(config["id"], "binding", device.vendor_id)
                        samples = normalize_points(device.id, binding_id, points, timestamp)
                        self.store.add_samples(samples)
                        self.store.put(
                            "latest",
                            device.id,
                            {
                                "device_id": device.id,
                                "received_at": utcnow().isoformat(),
                                "source": "VENDOR_CLOUD",
                                "samples": [s.model_dump(mode="json") for s in samples],
                                "native": redact(raw),
                            },
                        )
                        self.store.put("device", device.id, device.model_dump(mode="json"))
                    for device in selected:
                        if device.id not in seen:
                            device.online = False
                            self.store.put("device", device.id, device.model_dump(mode="json"))
                    self.store.put(
                        "poll_cursor", config["id"], {"offset": (cursor + 50) % max(1, len(devices))}
                    )
                    state.update(
                        state="PILOT_CAPACITY_EXCEEDED" if len(devices) > 50 else "CONNECTED",
                        last_success=utcnow().isoformat(),
                        devices=len(devices),
                        received=len(seen),
                    )
                except SafetyError as exc:
                    state.update(state="ERROR", error=str(exc))
                except Exception:
                    state.update(state="ERROR", error="invalid_vendor_response_or_internal_error")
                self.store.put("integration_state", config["id"], state)

    def latest(self, device: Device) -> dict:
        row = self.store.get("latest", device.id)
        if not row:
            return {"device_id": device.id, "samples": [], "state": "NO_DATA"}
        row["samples"] = [
            refresh_quality(Sample.model_validate(s), 300).model_dump(mode="json") for s in row["samples"]
        ]
        return row
