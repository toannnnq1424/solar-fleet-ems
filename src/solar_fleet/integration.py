"""Vendor-neutral integration extension contracts. Registration happens at composition time."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Protocol

from .capability_profiles import ProfileRegistry
from .domain import Device, SafetyError, VendorCall


@dataclass(frozen=True)
class PlantObservation:
    external_id: str | int
    name: str
    timezone: str | None = None


@dataclass(frozen=True)
class DeviceObservation:
    serial: str
    type: str
    model: str | None
    online: bool
    timestamp: datetime | None
    product_id: str | int | None = None


@dataclass(frozen=True)
class MeasurementObservation:
    serial: str
    online: bool
    timestamp: datetime | None
    points: list[dict]


class ReadAdapter(Protocol):
    async def stations(self) -> list[dict]: ...
    async def devices(self, station_id: str | int) -> list[dict]: ...
    async def latest(self, serials: list[str]) -> list[dict]: ...
    async def close(self): ...


Compiler = Callable[[Device, str, dict], tuple[list[VendorCall], dict]]


def no_mapping(device: Device, intent: str, parameters: dict):
    raise SafetyError("intent_mapping_unknown")


@dataclass(frozen=True)
class IntegrationPlugin:
    id: str
    version: str
    factory: Callable[..., ReadAdapter]
    plant: Callable[[dict], PlantObservation]
    device: Callable[[dict], DeviceObservation]
    measurement: Callable[[dict], MeasurementObservation]
    namespace: str
    evidence_ids: tuple[str, ...]
    authentication: str
    features: frozenset[str] = frozenset()
    compile_intent: Compiler = no_mapping
    native_groups: tuple[dict, ...] = ()
    documentation: tuple[dict, ...] = ()
    telemetry_profiles: tuple = ()
    control_profiles: tuple = ()
    decode_alarm: Callable[[dict], object] | None = None
    compile_schedule: Callable[[Device, object], object] | None = None
    registration: dict = field(default_factory=dict)
    prepare_credentials: Callable[[dict, dict], dict] | None = None

    def describe(self):
        return {
            "id": self.id,
            "version": self.version,
            "authentication": self.authentication,
            "features": sorted(self.features),
            "groups": list(self.native_groups),
            "documentation": list(self.documentation),
            "evidence_ids": list(self.evidence_ids),
            "hardware_accepted": False,
        }


@dataclass
class IntegrationRegistry:
    _plugins: dict[str, IntegrationPlugin] = field(default_factory=dict)
    profiles: ProfileRegistry = field(default_factory=ProfileRegistry)

    def register(self, plugin: IntegrationPlugin):
        if not plugin.id or plugin.id in self._plugins:
            raise ValueError("duplicate_or_empty_integration_plugin")
        if not plugin.namespace or not plugin.evidence_ids:
            raise ValueError("integration_provenance_required")
        # Stage profile registration so a malformed plugin cannot register half its contracts.
        staged = ProfileRegistry(dict(self.profiles._profiles), set(self.profiles._revoked))
        for profile in plugin.control_profiles:
            staged.register(profile, vendor=plugin.id, adapter_version=plugin.version)
        self.profiles = staged
        self._plugins[plugin.id] = plugin

    def find(self, id: str) -> IntegrationPlugin | None:
        return self._plugins.get(id)

    def require(self, id: str) -> IntegrationPlugin:
        plugin = self.find(id)
        if plugin is None:
            raise SafetyError("adapter_not_implemented")
        return plugin

    def create(self, config: dict, credentials: dict, budgets):
        return self.require(config["vendor"]).factory(config, credentials, budgets=budgets)

    def registration_catalog(self):
        return [
            dict(p.registration, id=p.id, implemented=True) for p in self._plugins.values() if p.registration
        ]

    def credentials(self, id: str, values: dict, options: dict):
        plugin = self.require(id)
        if plugin.prepare_credentials is None:
            raise SafetyError("registration_contract_not_implemented")
        return plugin.prepare_credentials(values, options)

    def compile(self, device: Device, intent: str, parameters: dict):
        return self.require(device.identity.vendor).compile_intent(device, intent, parameters)

    def describe(self, id: str):
        plugin = self.find(id)
        return (
            plugin.describe()
            if plugin
            else {
                "id": id,
                "version": None,
                "authentication": "UNKNOWN",
                "features": [],
                "groups": [],
                "documentation": [],
                "evidence_ids": [],
                "hardware_accepted": False,
            }
        )
