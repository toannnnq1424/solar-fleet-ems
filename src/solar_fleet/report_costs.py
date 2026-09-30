"""Frozen inputs for optional observed import estimates, never utility bills."""

from datetime import timedelta

from fastapi import HTTPException

from .import_tariffs import price_observations
from .observed_energy import integrate_directional_power


def import_cost_snapshot(store, site_ids, start, end):
    """Caller holds the same read transaction as the report energy snapshot."""
    if end - start > timedelta(days=30):
        raise HTTPException(422, "import_estimate_window_limit_30_days")
    if len(site_ids) > 20:
        raise HTTPException(422, "import_estimate_site_limit_20")
    snapshots = []
    for site_id in site_ids:
        site = store.get("site", site_id)
        meter_id = site.get("billing_meter_device_id")
        meter = store.get("device", meter_id) if meter_id else None
        if not meter or meter.get("site_id") != site_id:
            raise HTTPException(422, "site_billing_meter_required")
        rows = store.report_samples(meter_id, start, end, "grid_import_w", 10001)
        if len(rows) > 10000:
            raise HTTPException(422, "tariff_history_limit; reviewed_rollup_required")
        result = integrate_directional_power(rows, "grid_import_w", start, end)
        versions = site.get("import_tariff_versions", [])
        costs = price_observations(result, versions)
        snapshots.append({
            "site_id": site_id, "meter_device_id": meter_id,
            "revisions": store.object_revisions({"site": [site_id], "device": [meter_id]}),
            "tariff_versions": versions, "sample_rows": rows,
            "method": result["method"], "observed_energy_kwh": result["energy_kwh"],
            "observed_coverage": result["coverage"],
            "priced_coverage": costs["priced_seconds"] / (end - start).total_seconds(),
            **costs,
        })
    return {"schema_version": 1, "start": start.isoformat(), "end": end.isoformat(),
            "disclaimer": "Observed import cost estimate only; not a utility bill.",
            "sites": snapshots}