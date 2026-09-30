from datetime import UTC, datetime, timedelta

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.import_tariffs import price_observations
from solar_fleet.observed_energy import integrate_directional_power

URL = "/api/sites/sim-site/import-tariffs"
START = datetime(2026, 9, 28, tzinfo=UTC)


def rate(**changes):
    return {"effective_start": START.isoformat(), "effective_end": (START + timedelta(days=1)).isoformat(),
            "import_vnd_per_kwh": 2000.0, "currency": "VND", "source": "SYNTHETIC contract", **changes}


def test_version_revision_overlap_and_scope(local):
    client, ctl = local
    headers = login(local)
    revision = client.get(URL).json()["revision"]
    assert client.post(URL, json=rate(), headers=headers).status_code == 422
    body = rate(expected_revision=revision)
    saved = client.post(URL, json=body, headers=headers)
    assert saved.status_code == 200, saved.text
    assert saved.json()["revision"] > revision
    assert client.get(URL).json() == saved.json()
    assert client.post(URL, json=body, headers=headers).status_code == 409
    assert client.post(URL, json=rate(expected_revision=saved.json()["revision"]), headers=headers).status_code == 422
    assert len(client.get(URL).json()["versions"]) == 1
    assert ctl.store.verify_audit()
    assert not ctl.store.commands()
    headers = login(local, "other")
    assert client.get(URL).status_code == 404
    assert client.post(URL, json=body, headers=headers).status_code == 403


@pytest.mark.parametrize("changes", [
    {"effective_start": "2026-09-28"}, {"effective_end": START.isoformat()},
    {"import_vnd_per_kwh": -1}, {"import_vnd_per_kwh": True}, {"currency": "USD"},
    {"source": " "}, {"extra": 1},
])
def test_invalid_rate_has_no_side_effect(local, changes):
    client, ctl = local
    headers = login(local)
    before = ctl.store.get("site", "sim-site")
    revision = client.get(URL).json()["revision"]
    assert client.post(URL, json=rate(expected_revision=revision, **changes), headers=headers).status_code == 422
    assert ctl.store.get("site", "sim-site") == before


def observations(values=(1000, 1000, 1000)):
    return [{"metric": "grid_import_w", "unit": "W", "quality": "GOOD", "binding_id": "synthetic",
             "source_timestamp": (START + timedelta(minutes=5 * i)).isoformat(), "value": value}
            for i, value in enumerate(values)]


def cost(rows, versions):
    result = integrate_directional_power(rows, "grid_import_w", START, START + timedelta(minutes=10))
    return price_observations(result, versions)


def test_aligned_cost_provenance_and_explicit_zero():
    priced = cost(observations(), [rate(id="v1")])
    assert priced["estimated_import_cost_vnd"] == pytest.approx(1000 / 3)
    assert priced["priced_seconds"] == 600
    assert priced["priced_intervals"][0]["tariff_version_id"] == "v1"
    assert cost(observations((0, 0, 0)), [rate(id="v1")])["estimated_import_cost_vnd"] == 0
    assert cost(observations(), [rate(id="v1", import_vnd_per_kwh=0)])["estimated_import_cost_vnd"] == 0
    assert cost(observations(), [])["estimated_import_cost_vnd"] is None


def test_boundary_is_not_prorated_and_bad_sample_is_barrier():
    boundary = (START + timedelta(minutes=3)).isoformat()
    result = cost(observations(), [rate(id="old", effective_end=boundary), rate(id="new", effective_start=boundary)])
    assert result["priced_seconds"] == 300
    assert len(result["unpriced_intervals"]) == 1
    rows = observations()
    rows[1]["quality"] = "BAD"
    assert cost(rows, [rate(id="v1")])["estimated_import_cost_vnd"] is None


def test_analysis_uses_declared_rate_not_legacy_defaults(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    site = ctl.store.get("site", "sim-site")
    meter = next(d for d in ctl.store.list("device") if d["site_id"] == "sim-site")
    ctl.store.put("site", "sim-site", {**site, "billing_meter_device_id": meter["id"]})
    revision = client.get(URL).json()["revision"]
    assert client.post(URL, json=rate(expected_revision=revision), headers=headers).status_code == 200
    monkeypatch.setattr("solar_fleet.tariff_engine.utcnow", lambda: START + timedelta(minutes=11))
    monkeypatch.setattr(ctl.store, "report_samples", lambda *args: observations())
    result = client.get("/api/sites/sim-site/tariff-analysis").json()
    assert result["estimated_import_cost_vnd"] == pytest.approx(1000 / 3)
    assert result["total_active_bill_vnd"] is None
    assert result["priced_coverage"] == pytest.approx(600 / (30 * 86400))
    assert result["binding_ids"] == ["synthetic"]
    assert result["solar_savings_vnd"] is None


def test_adjacent_versions_price_exact_boundary():
    boundary = (START + timedelta(minutes=5)).isoformat()
    result = cost(observations(), [rate(id="a", effective_end=boundary),
                                  rate(id="b", effective_start=boundary, import_vnd_per_kwh=4000)])
    assert result["estimated_import_cost_vnd"] == pytest.approx(500)
    assert [p["tariff_version_id"] for p in result["priced_intervals"]] == ["a", "b"]
    assert not result["unpriced_intervals"]


def test_audit_failure_rolls_back_version_and_revision(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    before = client.get(URL).json()

    def fail(*args, **kwargs):
        raise RuntimeError("synthetic audit failure")

    monkeypatch.setattr(ctl.store, "audit", fail)
    with pytest.raises(RuntimeError, match="synthetic audit"):
        client.post(URL, json=rate(expected_revision=before["revision"]), headers=headers)
    assert client.get(URL).json() == before


@pytest.mark.parametrize("role", ["viewer", "operator", "engineer"])
def test_rate_mutation_requires_admin(local, role):
    client, ctl = local
    headers = login(local, role)
    before = client.get(URL).json()
    assert client.post(URL, json=rate(expected_revision=before["revision"]), headers=headers).status_code == 403
    assert client.get(URL).json() == before


def test_site_aba_rejects_append(local):
    client, ctl = local
    headers = login(local)
    before = client.get(URL).json()
    site = ctl.store.get("site", "sim-site")
    ctl.store.put("site", "sim-site", {**site, "name": "transient"})
    ctl.store.put("site", "sim-site", site)
    assert client.post(URL, json=rate(expected_revision=before["revision"]), headers=headers).status_code == 409
    assert not client.get(URL).json()["versions"]