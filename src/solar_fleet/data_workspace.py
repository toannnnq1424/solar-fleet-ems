"""Collection policies, versioned mapping drafts and code-registered telemetry acceptance."""

from __future__ import annotations

import hashlib
import uuid
from datetime import datetime
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import Field, model_validator

from .catalog import data
from .domain import Device, DeviceIdentity, Model, Role, SafetyError, utcnow
from .storage import encoded
from .telemetry import UNITS

METRICS = {
    "pv_w": "W",
    "load_w": "W",
    "grid_import_w": "W",
    "grid_export_w": "W",
    "battery_charge_w": "W",
    "battery_discharge_w": "W",
    "soc_pct": "%",
    "pv_total_wh": "Wh",
    "load_total_wh": "Wh",
    "grid_import_total_wh": "Wh",
    "grid_export_total_wh": "Wh",
    "battery_charge_total_wh": "Wh",
    "battery_discharge_total_wh": "Wh",
    "grid_voltage_v": "V",
    "grid_frequency_hz": "Hz",
    "battery_voltage_v": "V",
    "inverter_temperature_c": "°C",
    "battery_temperature_c": "°C",
}


class MetricMapping(Model):
    source_key: str = Field(min_length=1, max_length=160, pattern=r"^[A-Za-z0-9_.:-]+$")
    source_unit: str
    metric: str
    direction: Literal["nonnegative", "positive", "negative", "signed"] = "nonnegative"

    @model_validator(mode="after")
    def supported(self):
        if self.metric not in METRICS or self.source_unit not in UNITS:
            raise ValueError("unsupported metric or unit")
        if UNITS[self.source_unit][0] != METRICS[self.metric]:
            raise ValueError("incompatible metric unit")
        if self.direction in ("positive", "negative") and METRICS[self.metric] != "W":
            raise ValueError("direction split only applies to power")
        if self.direction == "signed" and METRICS[self.metric] != "°C":
            raise ValueError("canonical energy channels cannot be signed")
        return self

    def convert(self, value, unit):
        if value is None or unit != self.source_unit:
            return None, "source_missing_or_unit_mismatch"
        value *= UNITS[unit][1]
        if self.direction == "positive":
            value = max(0, value)
        elif self.direction == "negative":
            value = max(0, -value)
        elif self.direction == "nonnegative" and value < 0:
            return None, "negative_value_requires_direction_evidence"
        if METRICS[self.metric] == "%" and not 0 <= value <= 100:
            return None, "percentage_out_of_range"
        return value, "CANDIDATE_ONLY"


class MappingDraft(Model):
    device_id: str
    name: str = Field(min_length=1, max_length=120)
    binding_id: str = Field(min_length=1, max_length=120)
    mappings: list[MetricMapping] = Field(min_length=1, max_length=100)
    evidence_ids: list[str] = Field(default_factory=list, max_length=30)
    notes: str = Field(default="", max_length=3000)
    revision: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def unique(self):
        if len({m.metric for m in self.mappings}) != len(self.mappings):
            raise ValueError("duplicate output metric")
        return self


class MappingReview(Model):
    revision: int = Field(ge=1)
    outcome: Literal["REVIEWED", "CHANGES_REQUESTED"]
    notes: str = Field(min_length=10, max_length=3000)


class CollectionPolicy(Model):
    interval_seconds: int = Field(default=120, ge=120, le=3600)
    max_devices_per_poll: int = Field(default=10, ge=1, le=50)
    revision: int = Field(default=0, ge=0)


class CommissionedTelemetryProfile(Model):
    """Only instantiated by reviewed adapter packages. Never deserialized from a UI draft."""

    id: str
    identity: DeviceIdentity
    evidence_ids: list[str] = Field(min_length=1)
    acceptance_id: str = Field(min_length=1)
    reviewer: str = Field(min_length=1)
    mappings: list[MetricMapping] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def exact(self):
        required = (
            "model",
            "logger_model",
            "firmware",
            "protocol_version",
            "account_type",
            "privilege",
            "region",
        )
        if any(not getattr(self.identity, key) or getattr(self.identity, key) == "*" for key in required):
            raise ValueError("exact commissioned identity required")
        if len({m.metric for m in self.mappings}) != len(self.mappings):
            raise ValueError("duplicate output metric")
        return self


def accepted_profile(profiles, device):
    matches = [p for p in profiles if p.identity == device.identity]
    if len(matches) > 1:
        raise SafetyError("ambiguous_telemetry_profile")
    return matches[0] if matches else None


def apply_profile(profile, samples):
    """Keep native readings alongside canonical copies, with acceptance provenance."""
    if profile is None:
        return samples
    output = list(samples)
    for mapping in profile.mappings:
        for sample in samples:
            if sample.metric != mapping.source_key:
                continue
            value, result = mapping.convert(sample.value, sample.unit)
            quality = "GOOD" if value is not None else "INVALID"
            if sample.quality == "INVALID":
                value, quality = None, "INVALID"
            output.append(
                sample.model_copy(
                    update={
                        "metric": mapping.metric,
                        "value": value,
                        "unit": METRICS[mapping.metric],
                        "quality": quality,
                        "evidence_ids": [*profile.evidence_ids, profile.acceptance_id],
                    }
                )
            )
    return output


def install_data_workspace(app, controller, user, admin):
    store = controller.store

    def device_for(id, who, *, edit=False):
        device = controller.device(id)
        if not who.can_access(device.site_id):
            raise HTTPException(403, "site_access_denied")
        if edit and who.role not in (Role.INSTALLER, Role.ENGINEER, Role.ADMIN):
            raise HTTPException(403, "mapping_editor_required")
        return device

    def binding_exists(device, binding_id):
        binding = store.get("binding", binding_id)
        agent = store.get("agent", binding_id)
        return bool(
            binding
            and binding["device_id"] == device.id
            and binding.get("telemetry_enabled")
            or agent
            and agent.get("enabled")
            and agent["site_id"] == device.site_id
            and device.id in agent["device_ids"]
        )

    def get_draft(id, who, edit=False):
        row = store.get("mapping_draft", id)
        if not row:
            raise HTTPException(404, "mapping_not_found")
        device_for(row["device_id"], who, edit=edit)
        return row

    def save_draft(id, body, who):
        device = device_for(body.device_id, who, edit=True)
        if not binding_exists(device, body.binding_id):
            raise SafetyError("mapping_binding_not_available")
        valid_evidence = {r["id"] for r in data("source-registry.json")}
        if any(e not in valid_evidence for e in body.evidence_ids):
            raise SafetyError("mapping_evidence_unknown")
        with store.transaction():
            old = store.get("mapping_draft", id)
            if (old["revision"] if old else 0) != body.revision:
                raise SafetyError("revision_conflict")
            if old and old["device_id"] != body.device_id:
                raise SafetyError("mapping_device_immutable")
            row = body.model_dump(mode="json") | {
                "id": id,
                "site_id": device.site_id,
                "revision": body.revision + 1,
                "identity": device.identity.model_dump(mode="json"),
                "author": who.id,
                "state": "DRAFT",
                "updated_at": utcnow().isoformat(),
                "active": False,
            }
            row["digest"] = hashlib.sha256(encoded(row).encode()).hexdigest()
            store.put("mapping_draft", id, row)
            store.put("mapping_version", f"{id}:{row['revision']:08d}", row)
            store.audit(
                "operations",
                {"event": "mapping_saved", "id": id, "operator": who.id, "revision": row["revision"]},
                device.site_id,
            )
        return row

    @app.get("/api/data-workspace")
    async def overview(who=Depends(user)):
        devices = [Device.model_validate(d) for d in store.list("device") if who.can_access(d["site_id"])]
        readings = []
        for device in devices:
            samples = controller.latest(device)["samples"]
            readings.append(
                {
                    "device_id": device.id,
                    "site_id": device.site_id,
                    "channels": len(samples),
                    "fresh": sum(not s["stale"] for s in samples),
                    "verified": sum(s["quality"] == "GOOD" and not s["stale"] for s in samples),
                    "invalid": sum(s["quality"] == "INVALID" for s in samples),
                }
            )
        return {
            "devices": readings,
            "metrics": METRICS,
            "units": list(UNITS),
            "mappings": [r for r in store.list("mapping_draft") if who.can_access(r["site_id"])],
            "bindings": [b for b in store.list("binding") if who.can_access(b["site_id"])],
            "retention": {"days": 7, "max_points": 200000},
            "runtime": "SINGLE_CONTROLLER_PILOT",
            "drafts_activate_hardware": False,
        }

    @app.post("/api/mappings", status_code=201)
    async def create(body: MappingDraft, who=Depends(user)):
        if body.revision:
            raise SafetyError("new_mapping_revision_must_be_zero")
        return save_draft(uuid.uuid4().hex, body, who)

    @app.post("/api/mappings/{id}")
    async def update(id: str, body: MappingDraft, who=Depends(user)):
        get_draft(id, who, edit=True)
        return save_draft(id, body, who)

    @app.get("/api/mappings/{id}/versions")
    async def versions(id: str, who=Depends(user)):
        get_draft(id, who)
        return [r for r in store.list("mapping_version") if r["id"] == id]

    @app.post("/api/mappings/{id}/simulate")
    async def simulate(id: str, who=Depends(user)):
        row = get_draft(id, who)
        device = device_for(row["device_id"], who)
        if device.identity.model_dump(mode="json") != row["identity"]:
            raise SafetyError("mapping_identity_changed")
        if not binding_exists(device, row["binding_id"]):
            raise SafetyError("mapping_binding_not_available")
        samples = controller.latest(device)["samples"]
        results = []
        for raw in row["mappings"]:
            mapping = MetricMapping.model_validate(raw)
            candidates = [
                s
                for s in samples
                if s["binding_id"] == row["binding_id"] and s["metric"] == mapping.source_key
            ]
            value, result = None, "source_missing"
            selected = None
            if len(candidates) == 1:
                selected = candidates[0]
                value, result = mapping.convert(selected["value"], selected["unit"])
                if selected["stale"] or selected["quality"] == "INVALID":
                    result = "source_stale_or_invalid"
            elif candidates:
                result = "ambiguous_source"
            results.append(
                {
                    "mapping": raw,
                    "value": value,
                    "unit": METRICS[mapping.metric],
                    "result": result,
                    "source": selected,
                    "quality": "UNVERIFIED",
                }
            )
        return {
            "revision": row["revision"],
            "digest": row["digest"],
            "results": results,
            "mode": "SIMULATION_ONLY",
            "stored_canonical_points": 0,
        }

    @app.post("/api/mappings/{id}/review")
    async def review(id: str, body: MappingReview, who=Depends(user)):
        row = get_draft(id, who, edit=True)
        if who.role != Role.ENGINEER or row["author"] == who.id:
            raise HTTPException(403, "independent_engineer_required")
        with store.transaction():
            row = get_draft(id, who, edit=True)
            if row["revision"] != body.revision or row["state"] != "DRAFT":
                raise SafetyError("revision_or_review_conflict")
            row.update(
                state=body.outcome,
                review={
                    "reviewer": who.id,
                    "notes": body.notes,
                    "at": utcnow().isoformat(),
                    "digest": row["digest"],
                },
            )
            store.put("mapping_draft", id, row)
            store.put("mapping_version", f"{id}:{row['revision']:08d}", row)
            store.audit(
                "operations",
                {"event": "mapping_reviewed", "id": id, "operator": who.id, "outcome": body.outcome},
                row["site_id"],
            )
        return row

    @app.get("/api/collection")
    async def collection(who=Depends(admin)):
        result = []
        for config in store.list("integration"):
            result.append(
                {
                    "integration_id": config["id"],
                    "name": config["name"],
                    "policy": store.get("collection_policy", config["id"]) or CollectionPolicy().model_dump(),
                    "state": store.get("integration_state", config["id"]),
                    "cursor": store.get("poll_cursor", config["id"]),
                    "enabled": config.get("enabled", False),
                }
            )
        return {
            "connections": result,
            "base_tick_seconds": 120,
            "retention_days": 7,
            "max_points": 200000,
            "history_backfill": "NOT_IMPLEMENTED",
        }

    @app.post("/api/collection/{id}")
    async def save_collection(id: str, body: CollectionPolicy, who=Depends(admin)):
        config = store.get("integration", id)
        if not config:
            raise HTTPException(404, "integration_not_found")
        with store.transaction():
            old = store.get("collection_policy", id) or {"revision": 0}
            if old["revision"] != body.revision:
                raise SafetyError("revision_conflict")
            row = body.model_dump() | {
                "revision": body.revision + 1,
                "updated_by": who.id,
                "updated_at": utcnow().isoformat(),
            }
            store.put("collection_policy", id, row)
            store.put("collection_version", f"{id}:{row['revision']:08d}", dict(row, integration_id=id))
            store.audit(
                "security",
                {
                    "event": "collection_policy_saved",
                    "id": id,
                    "operator": who.id,
                    "revision": row["revision"],
                },
            )
        return row


def collection_due(store, config, now=None):
    policy = store.get("collection_policy", config["id"])
    state = store.get("integration_state", config["id"])
    if not policy or not state or not state.get("last_attempt"):
        return True
    age = ((now or utcnow()) - datetime.fromisoformat(state["last_attempt"])).total_seconds()
    return age < 0 or age >= policy["interval_seconds"]
