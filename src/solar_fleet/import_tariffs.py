"""Declared, versioned import rates. Estimates only, not utility invoices."""

from datetime import UTC, datetime
from typing import Literal
from uuid import uuid4

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, ConfigDict, Field, model_validator

from .security import require_session_principal


class ImportRate(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True, allow_inf_nan=False)

    effective_start: str
    effective_end: str
    import_vnd_per_kwh: float = Field(ge=0, le=1_000_000_000)
    currency: Literal["VND"]
    source: str = Field(min_length=1, max_length=1000)
    expected_revision: int = Field(ge=0)

    @model_validator(mode="after")
    def valid_window(self):
        start, end = (datetime.fromisoformat(s) for s in (self.effective_start, self.effective_end))
        if start.tzinfo is None or end.tzinfo is None or end <= start:
            raise ValueError("aware_ordered_effective_window_required")
        if not self.source.strip():
            raise ValueError("tariff_source_required")
        self.effective_start = start.astimezone(UTC).isoformat()
        self.effective_end = end.astimezone(UTC).isoformat()
        self.source = self.source.strip()
        return self


def price_observations(result, versions):
    """Never divide an observed trapezoid across a price boundary or fill gaps."""
    priced = []
    excluded = []
    for interval in result["bounded_intervals"]:
        left, right = interval["start"], interval["end"]
        matches = [v for v in versions if datetime.fromisoformat(v["effective_start"]) <= left
                   and right <= datetime.fromisoformat(v["effective_end"])]
        if len(matches) != 1:
            excluded.append({"start": left.isoformat(), "end": right.isoformat(),
                             "reason": "MISSING_OR_UNALIGNED_TARIFF"})
            continue
        version = matches[0]
        priced.append({"start": left.isoformat(), "end": right.isoformat(),
                       "energy_kwh": interval["energy_kwh"],
                       "start_w": interval["start_w"], "end_w": interval["end_w"],
                       "cost_vnd": interval["energy_kwh"] * version["import_vnd_per_kwh"],
                       "tariff_version_id": version["id"], "source": version["source"],
                       "rate_vnd_per_kwh": version["import_vnd_per_kwh"],
                       "seconds": (right - left).total_seconds()})
    return {"estimated_import_cost_vnd": sum(p["cost_vnd"] for p in priced) if priced else None,
            "priced_seconds": sum(p["seconds"] for p in priced),
            "priced_intervals": priced, "unpriced_intervals": excluded,
            "tariff_basis": "USER_DECLARED_NOT_UTILITY_VERIFIED", "currency": "VND",
            "excluded_charges": ["VAT", "FIXED_CHARGES", "DEMAND", "REACTIVE_ENERGY", "EXPORT_CREDITS"]}


def install_import_tariffs(app, controller, user, admin):
    store = controller.store

    def site_for(site_id, who):
        site = store.get("site", site_id)
        if not site or not who.can_access(site_id):
            raise HTTPException(404, "site_not_found")
        return site

    def snapshot(site_id, who):
        site = site_for(site_id, who)
        return {"versions": site.get("import_tariff_versions", []),
                "revision": store.object_revisions({"site": [site_id]})["site"][site_id],
                "status": "USER_DECLARED_NOT_UTILITY_VERIFIED"}

    @app.get("/api/sites/{site_id}/import-tariffs")
    def read(site_id: str, request: Request, who=Depends(user)):
        with store.transaction():
            require_session_principal(store, request.cookies.get("solar_session"), who)
            return snapshot(site_id, who)

    @app.post("/api/sites/{site_id}/import-tariffs")
    def append(site_id: str, body: ImportRate, request: Request, who=Depends(admin)):
        with store.transaction():
            require_session_principal(store, request.cookies.get("solar_session"), who)
            site = site_for(site_id, who)
            before = snapshot(site_id, who)
            if before["revision"] != body.expected_revision:
                raise HTTPException(409, "import_tariff_changed_reload_required")
            versions = before["versions"]
            if len(versions) >= 1000:
                raise HTTPException(422, "tariff_version_limit")
            start, end = datetime.fromisoformat(body.effective_start), datetime.fromisoformat(body.effective_end)
            if any(start < datetime.fromisoformat(v["effective_end"])
                   and datetime.fromisoformat(v["effective_start"]) < end for v in versions):
                raise HTTPException(422, "overlapping_tariff_versions")
            version = {**body.model_dump(exclude={"expected_revision"}), "id": uuid4().hex,
                       "created_at": datetime.now(UTC).isoformat(), "created_by": who.id}
            site["import_tariff_versions"] = sorted([*versions, version], key=lambda v: v["effective_start"])
            store.put("site", site_id, site)
            store.audit("security", {"event": "import_tariff_version_added", "operator": who.id,
                                     "site_id": site_id, "version": version,
                                     "previous_revision": before["revision"]}, site_id)
            return snapshot(site_id, who)