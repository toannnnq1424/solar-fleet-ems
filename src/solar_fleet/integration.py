"""Vendor-neutral integration extension contracts. Registration happens at composition time."""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from datetime import datetime
from typing import Callable, Literal, Protocol

from pydantic import BaseModel, ConfigDict, Field, field_validator

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
    online: bool | None
    timestamp: datetime | None
    product_id: str | int | None = None


@dataclass(frozen=True)
class MeasurementObservation:
    serial: str
    online: bool | None
    timestamp: datetime | None
    points: list[dict]
    reported: DeviceReport | None = None


class DeviceEnergyReport(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)
    generation_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    charge_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    discharge_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class DeviceReport(BaseModel):
    """Per-device monitoring values; never copied from a station aggregate."""

    model_config = ConfigDict(extra="forbid", strict=True)
    serial: str
    ac_kw: float | None = Field(default=None, allow_inf_nan=False)
    pv_dc_kw: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    rated_kw: float | None = Field(default=None, gt=0, allow_inf_nan=False)
    temperature_c: float | None = Field(default=None, allow_inf_nan=False)
    periods: dict[Literal["today", "week", "month", "year", "total"], DeviceEnergyReport] = Field(default_factory=dict)
    counters_available: bool = False
    source_clock: str | None = None
    evidence_ids: list[str] = Field(default_factory=list)


class ReadAdapter(Protocol):
    async def stations(self) -> list[dict]: ...
    async def devices(self, station_id: str | int) -> list[dict]: ...
    async def latest(self, serials: list[str]) -> list[dict]: ...
    async def close(self): ...


class ReportedEnergy(BaseModel):
    """Vendor calendar totals, not locally integrated/billing-grade counters."""

    model_config = ConfigDict(extra="forbid", strict=True)
    start_date: str
    end_date: str
    generation_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    consumption_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    import_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)
    export_kwh: float | None = Field(default=None, ge=0, allow_inf_nan=False)


class StationReport(BaseModel):
    """Optional shared monitoring contract. Never an input to command gates.

    Source clock stays verbatim: a vendor-local clock without an offset must not
    acquire the server/browser timezone. The controller records receipt separately.
    """

    model_config = ConfigDict(extra="forbid", strict=True)
    station_id: str
    source_clock: str | None = Field(default=None, max_length=64)
    power: dict[Literal["pv_w", "load_w", "battery_w", "grid_w", "battery_soc"], float] = Field(default_factory=dict)
    periods: dict[Literal["today", "month", "year"], ReportedEnergy] = Field(default_factory=dict)
    daily_energy: list[ReportedEnergy] = Field(default_factory=list, max_length=31)
    evidence_ids: list[str] = Field(default_factory=list)
    unavailable_periods: list[Literal["today", "month", "year"]] = Field(default_factory=list)

    @field_validator("power")
    @classmethod
    def finite_power(cls, values):
        if any(not math.isfinite(value) for value in values.values()):
            raise ValueError("nonfinite_reported_power")
        if any(values.get(key, 0) < 0 for key in ("pv_w", "load_w", "battery_soc")) or values.get("battery_soc", 0) > 100:
            raise ValueError("invalid_reported_power_range")
        return values


class StationReportReader(Protocol):
    """Opt-in; adapters without a supported station aggregate need not implement."""

    async def station_report(self, station_id: str) -> StationReport: ...


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
