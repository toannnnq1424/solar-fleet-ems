"""Authenticated offline model inspection. None of these routes opens a socket."""

from __future__ import annotations

from fastapi import Depends, HTTPException, Query
from pydantic import Field, ValidationError

from .domain import Model
from .home_assistant_bridge import HomeAssistantProfile
from .local_models import ModelCollectionProfile
from .model_library import RegisterReading, decode, get_profile, plan, profiles


class ModelSelection(Model):
    profile_digest: str = Field(pattern=r"^[a-f0-9]{64}$")
    field_ids: list[str] = Field(min_length=1, max_length=100)


class DecodeRequest(ModelSelection):
    readings: list[RegisterReading] = Field(max_length=1000)


def install_model_library(app, controller, user):
    @app.get("/api/model-library")
    def catalog(q: str = Query(default="", max_length=160), who=Depends(user)):
        rows = []
        for profile in profiles():
            if q.casefold() not in " ".join([profile.name, profile.manufacturer, *profile.models]).casefold():
                continue
            rows.append(
                {k: v for k, v in profile.model_dump().items() if k != "fields"}
                | {
                    "field_count": len(profile.fields),
                    "readable_count": sum(f.decode is not None for f in profile.fields),
                    "hardware_verified": False,
                    "write_enabled": False,
                }
            )
        return {"profiles": rows, "count": len(rows), "status": "COMMUNITY_CANDIDATES"}

    def profile_or_404(profile_id, digest=None):
        try:
            return get_profile(profile_id, digest)
        except ValueError as exc:
            raise HTTPException(409 if digest else 404, str(exc)) from None

    @app.get("/api/model-library/{profile_id}")
    def detail(profile_id: str, who=Depends(user)):
        return profile_or_404(profile_id)

    @app.post("/api/model-library/{profile_id}/plan")
    def preview(profile_id: str, body: ModelSelection, who=Depends(user)):
        profile = profile_or_404(profile_id, body.profile_digest)
        try:
            return plan(profile, body.field_ids)
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/api/model-library/{profile_id}/decode")
    def decode_registers(profile_id: str, body: DecodeRequest, who=Depends(user)):
        profile = profile_or_404(profile_id, body.profile_digest)
        try:
            return {
                "profile_digest": profile.profile_digest,
                "hardware_verified": False,
                "results": decode(profile, body.field_ids, body.readings),
            }
        except ValueError as exc:
            raise HTTPException(422, str(exc)) from None

    @app.post("/api/local-collection/{kind}/validate")
    def validate_collection(kind: str, body: dict, who=Depends(user)):
        try:
            if kind == "model":
                config = ModelCollectionProfile.model_validate(body)
                device_ids = {config.device_id}
            elif kind == "home-assistant":
                config = HomeAssistantProfile.model_validate(body)
                device_ids = {binding.device_id for binding in config.bindings}
            else:
                raise HTTPException(404, "unknown_collection_kind")
        except ValidationError as exc:
            # Do not echo invalid config values, possibly including a pasted token.
            errors = [{"loc": list(error["loc"]), "type": error["type"]} for error in exc.errors()]
            raise HTTPException(422, errors) from None
        agent = controller.store.get("agent", config.agent_id)
        if not agent or not who.can_access(agent["site_id"]):
            raise HTTPException(404, "agent_not_found")
        if not agent["enabled"] or not device_ids.issubset(set(agent["device_ids"])):
            raise HTTPException(409, "agent_disabled_or_device_not_bound")
        for device_id in device_ids:
            device = controller.store.get("device", device_id)
            if not device or device["site_id"] != agent["site_id"] or not who.can_access(device["site_id"]):
                raise HTTPException(404, "device_not_found")
        return {
            "config": config.model_dump(mode="json"),
            "status": "CONFIG_VALID",
            "connection_tested": False,
            "hardware_verified": False,
            "write_enabled": False,
        }
