"""Persisted, scoped inputs for advisory planning; never authorizes dispatch."""

from datetime import datetime, timedelta, timezone
from typing import Literal

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .security import require_session_principal


class ExplicitModel(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False, strict=True)


class BatteryParameters(ExplicitModel):
    capacity_kwh: float = Field(gt=0)
    usable_kwh: float = Field(gt=0)
    max_charge_kw: float = Field(gt=0)
    max_discharge_kw: float = Field(gt=0)
    charge_efficiency: float = Field(gt=0, le=1)
    discharge_efficiency: float = Field(gt=0, le=1)
    min_soc_pct: float = Field(ge=0, le=100)
    max_soc_pct: float = Field(ge=0, le=100)
    reserve_soc_pct: float = Field(ge=0, le=100)
    replacement_cost_usd: float = Field(ge=0)
    rated_cycle_life: int = Field(gt=0)

    @model_validator(mode="after")
    def ordered_limits(self):
        if self.usable_kwh > self.capacity_kwh or not self.min_soc_pct <= self.reserve_soc_pct < self.max_soc_pct:
            raise ValueError("invalid_battery_specifications")
        return self


class HourlyPrice(ExplicitModel):
    timestamp: str
    import_per_kwh: float
    export_per_kwh: float

    @model_validator(mode="after")
    def utc_hour(self):
        dt = datetime.fromisoformat(self.timestamp)
        if dt.tzinfo is None or dt.utcoffset() != timedelta(0) or dt.minute or dt.second or dt.microsecond:
            raise ValueError("utc_hour_timestamp_required")
        self.timestamp = dt.isoformat()
        return self


class DispatchConfiguration(BatteryParameters):
    currency: Literal["USD"]
    tariff_source: str = Field(min_length=1, max_length=1000)
    hourly_prices: list[HourlyPrice] = Field(min_length=24, max_length=24)

    @model_validator(mode="after")
    def aligned_prices(self):
        if not self.tariff_source.strip():
            raise ValueError("tariff_source_required")
        stamps = [datetime.fromisoformat(p.timestamp) for p in self.hourly_prices]
        if any(b - a != timedelta(hours=1) for a, b in zip(stamps, stamps[1:])):
            raise ValueError("consecutive_hourly_prices_required")
        return self


class PlanningConfiguration(ExplicitModel):
    dispatch_device_id: str | None
    billing_meter_device_id: str | None
    dispatch_config: DispatchConfiguration | None

    @model_validator(mode="after")
    def paired_dispatch(self):
        if (self.dispatch_device_id is None) != (self.dispatch_config is None):
            raise ValueError("dispatch_device_and_configuration_required_together")
        return self


class PlanningUpdate(PlanningConfiguration):
    expected_revision: int = Field(ge=0)


def install_planning_configuration(app, controller, user, admin):
    from .import_tariffs import install_import_tariffs

    install_import_tariffs(app, controller, user, admin)
    store = controller.store

    def scoped_site(site_id, who):
        site = store.get("site", site_id)
        if not site or not who.can_access(site_id):
            raise HTTPException(404, "site_not_found")
        return site

    @app.get("/api/sites/{site_id}/planning-configuration")
    def read_configuration(site_id: str, who=Depends(user)):
        with store.transaction():
            site = scoped_site(site_id, who)
            return {"configuration": {key: site.get(key) for key in PlanningConfiguration.model_fields},
                    "revision": store.object_revisions({"site": [site_id]})["site"][site_id],
                    "dispatch_enabled": False, "status": "ADVISORY_CONFIGURATION",
                    "updated_at": site.get("planning_configuration_updated_at")}

    @app.post("/api/sites/{site_id}/planning-configuration")
    def save_configuration(site_id: str, body: PlanningUpdate, request: Request, who=Depends(admin)):
        scoped_site(site_id, who)
        with store.transaction():
            require_session_principal(store, request.cookies.get("solar_session"), who)
            site = scoped_site(site_id, who)
            revision = store.object_revisions({"site": [site_id]})["site"][site_id]
            if body.expected_revision != revision:
                raise HTTPException(409, "planning_configuration_changed_reload_required")
            for device_id in (body.dispatch_device_id, body.billing_meter_device_id):
                if device_id is not None:
                    device = store.get("device", device_id)
                    if not device or device.get("site_id") != site_id:
                        raise HTTPException(422, "measurement_device_must_belong_to_site")
            site.update(body.model_dump(exclude={"expected_revision"}))
            site["planning_configuration_updated_at"] = datetime.now(timezone.utc).isoformat()
            store.put("site", site_id, site)
            store.audit("security", {"event": "planning_configuration_updated", "operator": who.id,
                                     "site_id": site_id, "previous_revision": revision,
                                     "dispatch_enabled": False}, site_id)
            return read_configuration(site_id, who)