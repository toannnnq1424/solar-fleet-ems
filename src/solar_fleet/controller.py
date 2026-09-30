from __future__ import annotations

import asyncio
import hashlib
import time
from datetime import datetime

from pydantic import ValidationError

from .adapters.plugins import builtins
from .budgets import Budgets
from .catalog import capabilities
from .control import CommandEngine
from .data_workspace import accepted_profile, apply_profile, collection_due
from .domain import Device, DeviceIdentity, SafetyError, Sample, Source, utcnow
from .incidents import IncidentService
from .integration import ReadAdapter
from .security import Vault, principal, redact
from .storage import Store
from .telemetry import normalize_points, refresh_quality
from .transport_guard import guarded_read


def entity_id(*parts) -> str:
    return hashlib.sha256("|".join(str(x) for x in parts).encode()).hexdigest()[:24]


class Controller:
    """One local process. No fake integrations, vendor switching or writable protocol fallbacks."""

    def __init__(self, store: Store, vault: Vault, *, writes_enabled=False, registry=None):
        self.store, self.vault = store, vault
        self.incidents = IncidentService(store)
        self.adapters = {}
        self.adapter_credentials = {}
        self.registry = registry if registry is not None else builtins()
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
            compiler=self.registry.compile,
        )

    def device(self, id: str) -> Device:
        row = self.store.get("device", id)
        if not row:
            raise SafetyError("device_not_found")
        return Device.model_validate(row)

    def devices(self) -> list[Device]:
        return [Device.model_validate(d) for d in self.store.list("device")]

    def adapter(self, device: Device) -> ReadAdapter:
        return self.integration_adapter(device.integration_id)

    def integration_adapter(self, id: str) -> ReadAdapter:
        config = self.store.get("integration", id)
        if not config or not config.get("enabled"):
            raise SafetyError("integration_not_available")
        revision = config.get("credential_revision")
        if id in self.adapters:
            cached = self.adapter_credentials.get(id)
            if cached is not None and cached[0] is self.adapters[id] and cached[1] != revision:
                # Fail closed until explicitly evicted/reopened. Do not close an
                # in-flight transport from this synchronous accessor.
                raise SafetyError("integration_credentials_changed")
        if id not in self.adapters:
            self.adapters[id] = self.registry.create(config, self.vault.get(id), self.budgets)
        self.adapter_credentials[id] = (self.adapters[id], revision)
        return self.adapters[id]

    def capability(self, device: Device, intent: str):
        commissioned = self.registry.profiles.resolve(device, intent)
        if commissioned is not None:
            return commissioned
        candidate = next((c for c in capabilities(device) if c.intent == intent), None)
        if candidate is None:
            raise SafetyError("intent_unknown")
        return candidate

    def capabilities(self, device: Device):
        intents = dict.fromkeys(c.intent for c in capabilities(device))
        for profile in self.registry.profiles.candidates(device):
            intents.update(dict.fromkeys(c.intent for c in profile.contracts))
        return [self.capability(device, intent) for intent in intents]

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

    async def discover(self, config: dict, adapter: ReadAdapter):
        plugin = self.registry.require(config["vendor"])
        # Stage network reads without mutating inventory. Conservative snapshots
        # also protect shared devices/sites discovered through another account.
        with self.store.transaction():
            snapshot = {kind: self.store.list(kind) for kind in ("site", "device", "binding", "discovery")}
            revisions = self.store.revisions(*snapshot)
            # Transport identity is known before I/O, unlike discovered inventory.
            integration_revisions = self.store.object_revisions({"integration": [config["id"]]})

        def check_context():
            if (
                not config.get("enabled")
                or self.store.revisions(*revisions) != revisions
                or self.store.object_revisions(integration_revisions) != integration_revisions
                or self.store.get("integration", config["id"]) != config
                or self.adapters.get(config["id"]) is not adapter
                or any(self.store.list(kind) != rows for kind, rows in snapshot.items())
            ):
                raise SafetyError("discovery_context_changed")

        check_context()
        stations = await guarded_read(check_context, adapter.stations)
        check_context()
        inventory = []
        for station in stations:
            vendor_id = plugin.plant(station).external_id
            if type(vendor_id) not in (int, str) or str(vendor_id).strip() == "":
                raise SafetyError("station_identity_invalid")
            rows = await guarded_read(check_context, adapter.devices, vendor_id)
            check_context()
            inventory.append((station, rows))
        with self.store.transaction():
            check_context()
            self._persist_discovery(config, inventory)
        if hasattr(adapter, "inventory_ready"):
            adapter.inventory_ready = True

    def _persist_discovery(self, config: dict, inventory: list):
        """Synchronous, atomic inventory update; never await inside its transaction."""
        plugin = self.registry.require(config["vendor"])
        vendor = config["vendor"]
        discovered = []
        for station, rows in inventory:
            observed_plant = plugin.plant(station)
            vendor_id = observed_plant.external_id
            if type(vendor_id) not in (int, str) or str(vendor_id).strip() == "":
                raise SafetyError("station_identity_invalid")
            site_id = entity_id(vendor, config["region"], "station", vendor_id)
            site = {
                "id": site_id,
                "integration_id": config["id"],
                "vendor_id": vendor_id,
                "name": observed_plant.name,
                "vendor": vendor,
                "timezone": observed_plant.timezone,
                "source": "VENDOR_CLOUD",
                "discovered_at": utcnow().isoformat(),
                "native": redact(station),
            }
            self.store.put("site", site_id, site)
            for raw in rows:
                observed = plugin.device(raw)
                serial = observed.serial
                if not isinstance(serial, str) or not serial:
                    raise SafetyError("device_identity_invalid")
                # A serial seen through two accounts must not create two independent command queues.
                id = entity_id(vendor, "device", serial)
                binding_id = entity_id(config["id"], "binding", serial)
                if id in discovered:
                    raise SafetyError("ambiguous_device_site_binding")
                previous = self.store.get("device", id)
                device = Device(
                    id=id,
                    site_id=site_id,
                    integration_id=config["id"],
                    vendor_id=serial,
                    type=observed.type,
                    identity=DeviceIdentity(
                        vendor=vendor,
                        model=observed.model,
                        region=config["region"],
                        account_type=config.get("account_type"),
                        privilege=config.get("privilege"),
                    ),
                    last_seen=observed.timestamp,
                    online=observed.online,
                    metadata={
                        "discovery": redact(raw),
                        "product_id": observed.product_id,
                        "identity_state": "UNKNOWN",
                        "declared_equipment_brand": config.get("equipment_brand"),
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
                previous_binding = self.store.get("binding", binding_id) or {}
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
                        "telemetry_enabled": previous_binding.get("telemetry_enabled", True),
                        "control_enabled": False,
                        "evidence_ids": list(plugin.evidence_ids),
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
                plugin = self.registry.find(config["vendor"])
                minimum = plugin.registration.get("minimum_poll_seconds", 120) if plugin else 120
                if not config.get("enabled") or not collection_due(
                    self.store, config, minimum_interval=minimum
                ):
                    continue
                state = {"id": config["id"], "last_attempt": utcnow().isoformat(), "state": "CONNECTING"}
                try:
                    adapter = self.integration_adapter(config["id"])
                    plugin = self.registry.require(config["vendor"])
                    discovery = self.store.get("discovery", config["id"])
                    if (
                        not discovery
                        or not getattr(adapter, "inventory_ready", True)
                        or (utcnow() - datetime.fromisoformat(discovery["last_success"])).total_seconds()
                        > 900
                    ):
                        await self.discover(config, adapter)
                    # Capture models, provenance and revisions from one database
                    # state; a newer snapshot must never authorize an older body.
                    # Release the lock before any transport await.
                    with self.store.transaction():
                        devices = [
                            Device.model_validate(d)
                            for d in self.store.list("device")
                            if d["integration_id"] == config["id"] and not d["metadata"].get("discovery_missing")
                            and (self.store.get("binding", entity_id(config["id"], "binding", d["vendor_id"])) or {}).get(
                                "telemetry_enabled", False
                            )
                        ]
                        for device in devices:
                            site = self.store.get("site", device.site_id)
                            if (
                                device.identity.vendor != config["vendor"]
                                or not site
                                or site.get("id") != device.site_id
                                or site.get("vendor") != config["vendor"]
                                or site.get("source") != "VENDOR_CLOUD"
                            ):
                                raise SafetyError("poll_site_vendor_identity_mismatch")
                            binding_id = entity_id(config["id"], "binding", device.vendor_id)
                            binding = self.store.get("binding", binding_id)
                            expected = {
                                "id": binding_id,
                                "device_id": device.id,
                                "site_id": device.site_id,
                                "integration_id": config["id"],
                                "vendor_device_sn": device.vendor_id,
                                "source": "VENDOR_CLOUD",
                            }
                            if any(binding.get(key) != value for key, value in expected.items()):
                                raise SafetyError("poll_binding_identity_mismatch")
                        # Pilot budget: 50 devices per cycle; rotate fairly beyond that and report degradation.
                        cursor = (self.store.get("poll_cursor", config["id"]) or {}).get("offset", 0)
                        batch = min(
                            getattr(adapter, "per_poll", 50),
                            (self.store.get("collection_policy", config["id"]) or {}).get(
                                "max_devices_per_poll", 50
                            ),
                        )
                        selected = (devices[cursor:] + devices[:cursor])[:batch] if devices else []
                        wanted = {d.vendor_id: d for d in selected}
                        # Include omitted devices: their offline path also writes state.
                        device_snapshot = {d.id: self.store.get("device", d.id) for d in selected}
                        site_snapshot = {d.site_id: self.store.get("site", d.site_id) for d in selected}
                        binding_snapshot = {
                            entity_id(config["id"], "binding", d.vendor_id): self.store.get(
                                "binding", entity_id(config["id"], "binding", d.vendor_id)
                            ) for d in selected
                        }
                        revisions = self.store.object_revisions({
                            "integration": [config["id"]], "device": device_snapshot,
                            "binding": binding_snapshot, "site": site_snapshot,
                        })

                    def check_poll():
                        if (
                            self.store.object_revisions(revisions) != revisions
                            or self.store.get("integration", config["id"]) != config
                            or self.adapters.get(config["id"]) is not adapter
                            or any(self.store.get("device", k) != v for k, v in device_snapshot.items())
                            or any(self.store.get("binding", k) != v for k, v in binding_snapshot.items())
                            or any(self.store.get("site", k) != v for k, v in site_snapshot.items())
                        ):
                            raise SafetyError("poll_context_changed")

                    rows = await guarded_read(check_poll, adapter.latest, list(wanted)) if wanted else []
                    check_poll()
                    with self.store.transaction():
                        # Revalidate after acquiring the write lock as another SQLite
                        # connection can commit between the preflight check and BEGIN.
                        check_poll()
                        seen = set()
                        for raw in rows:
                            observed = plugin.measurement(raw)
                            device = wanted.get(observed.serial)
                            if device is None:
                                raise SafetyError("latest_response_device_mismatch")
                            seen.add(device.id)
                            timestamp = observed.timestamp
                            device.last_seen = timestamp
                            device.online = observed.online
                            points = observed.points
                            binding_id = entity_id(config["id"], "binding", device.vendor_id)
                            samples = normalize_points(
                                device.id,
                                binding_id,
                                points,
                                timestamp,
                                namespace=plugin.namespace,
                                evidence_ids=list(plugin.evidence_ids),
                            )
                            samples = apply_profile(accepted_profile(plugin.telemetry_profiles, device), samples)
                            self.store.add_samples(samples)
                            self.store.put(
                                "latest",
                                device.id,
                                {
                                    "device_id": device.id,
                                    "site_id": device.site_id,
                                    "binding_id": binding_id,
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
                            "poll_cursor", config["id"], {"offset": (cursor + batch) % max(1, len(devices))}
                        )
                    state.update(
                        state="PILOT_CAPACITY_EXCEEDED" if len(devices) > batch else "CONNECTED",
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
        current = self.store.get("device", device.id)
        if current is None or Device.model_validate(current) != device:
            # A caller's authorized snapshot must not read through an old binding.
            # Do not silently substitute the newly assigned device/site here.
            return {"device_id": device.id, "samples": [], "state": "NO_DATA"}
        row = self.store.get("latest", device.id)
        binding_id = entity_id(device.integration_id, "binding", device.vendor_id)
        binding = self.store.get("binding", binding_id) or {}
        config = self.store.get("integration", device.integration_id) or {}
        site = self.store.get("site", device.site_id) or {}
        expected_binding = {
            "id": binding_id, "device_id": device.id, "site_id": device.site_id,
            "integration_id": device.integration_id, "vendor_device_sn": device.vendor_id,
            "source": "VENDOR_CLOUD",
        }
        if not (
            isinstance(row, dict)
            and row.get("device_id") == device.id
            and row.get("site_id") == device.site_id
            and row.get("binding_id") == binding_id
            and row.get("source") == "VENDOR_CLOUD"
            and config.get("enabled")
            and config.get("vendor") == device.identity.vendor
            and site.get("id") == device.site_id
            and site.get("vendor") == device.identity.vendor
            and site.get("source") == "VENDOR_CLOUD"
            and binding.get("telemetry_enabled")
            and all(binding.get(key) == value for key, value in expected_binding.items())
            and isinstance(row.get("samples"), list)
        ):
            # Legacy snapshots lack provenance: do not relabel them using today's binding.
            # Drop native payload too; valid agent observations can still be added below.
            row = None
        if row is not None:
            samples = []
            for raw in row["samples"]:
                if not (
                    isinstance(raw, dict) and raw.get("device_id") == device.id
                    and raw.get("binding_id") == binding_id and raw.get("source") == Source.CLOUD
                ):
                    continue
                try:
                    sample = Sample.model_validate(raw)
                except ValidationError:
                    continue
                samples.append(sample.model_dump(mode="json"))
            # Invalid-only observations cannot advertise HAS_DATA or expose native payload.
            row = (row | {"samples": samples}) if samples else None
        row = row or {
            "device_id": device.id,
            "samples": [],
            "state": "NO_DATA",
        }
        for source in self.store.list("agent_latest"):
            if (
                isinstance(source, dict)
                and source.get("device_id") == device.id
                and isinstance(source.get("agent_id"), str)
                and isinstance(source.get("samples"), list)
            ):
                agent = self.store.get("agent", source["agent_id"])
                if (
                    agent
                    and agent["enabled"]
                    and agent["site_id"] == device.site_id
                    and device.id in agent.get("device_ids", [])
                    and source.get("site_id") == device.site_id
                ):
                    samples = []
                    for raw in source["samples"]:
                        if not (
                            isinstance(raw, dict)
                            and raw.get("device_id") == device.id
                            and raw.get("binding_id") == source["agent_id"]
                            and raw.get("source") == Source.AGENT
                        ):
                            continue
                        try:
                            sample = Sample.model_validate(raw)
                        except ValidationError:
                            # Persisted observations are untrusted. Do not promote,
                            # repair, log or expose a malformed sample.
                            continue
                        samples.append(sample.model_dump(mode="json"))
                    row["samples"].extend(samples)
                    if samples:
                        row["state"] = "HAS_DATA"
        row["samples"] = [
            refresh_quality(Sample.model_validate(s), 300).model_dump(mode="json") for s in row["samples"]
        ]
        return row

    def collect_alarms(self, device: Device, rows: list[dict]):
        from .incident_models import AlarmObservation

        plugin = self.registry.require(device.identity.vendor)
        if plugin.decode_alarm is None:
            return {"state": "NATIVE_ONLY", "correlated": 0}
        # Validate the whole response before changing the incident store. An empty
        # response is never evidence that previously active alarms recovered.
        observations = [AlarmObservation.model_validate(plugin.decode_alarm(row)) for row in rows]
        if any(
            o.namespace != plugin.namespace or not set(o.evidence_ids) <= set(plugin.evidence_ids)
            for o in observations
        ):
            raise SafetyError("alarm_mapping_provenance_invalid")
        binding_id = entity_id(device.integration_id, "binding", device.vendor_id)
        with self.store.transaction():
            results = [
                self.incidents.apply_alarm(device, binding_id, o)
                for o in sorted(observations, key=lambda o: o.source_timestamp)
            ]
        return {"state": "CORRELATED", "correlated": len(results), "results": results}
