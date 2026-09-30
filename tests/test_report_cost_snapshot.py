import io
import zipfile
from datetime import timedelta

import pytest
from test_import_tariffs import START, URL, rate
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.domain import Sample, Source


def setup_cost(local):
    client, ctl = local
    headers = login(local)
    site = ctl.store.get("site", "sim-site")
    ctl.store.put("site", "sim-site", {**site, "billing_meter_device_id": "sim-device"})
    revision = client.get(URL).json()["revision"]
    saved = client.post(URL, headers=headers, json=rate(expected_revision=revision))
    assert saved.status_code == 200
    ctl.store.add_samples([
        Sample(device_id="sim-device", metric="grid_import_w", unit="W", value=1000,
               source=Source.SIMULATOR, source_timestamp=START + timedelta(minutes=i),
               quality="GOOD", binding_id="snapshot-fixture") for i in (0, 5, 10)
    ])
    body = {"site_id": "sim-site", "start": START.isoformat(),
            "end": (START + timedelta(minutes=11)).isoformat(), "include_import_estimate": True}
    return headers, body


@pytest.mark.parametrize("fmt", ["csv", "excel", "html"])
def test_frozen_import_inputs_and_artifacts(local, fmt):
    client, ctl = local
    headers, body = setup_cost(local)
    response = client.post("/api/reports/generate", headers=headers, json={**body, "format": fmt})
    assert response.status_code == 201, response.text
    record = response.json()
    snapshot = record["snapshot"]["import_cost_snapshot"]["sites"][0]
    assert snapshot["estimated_import_cost_vnd"] == pytest.approx(1000 / 3)
    assert snapshot["priced_coverage"] == pytest.approx(10 / 11)
    assert len(snapshot["sample_rows"]) == 3
    assert snapshot["sample_rows"][0]["binding_id"] == "snapshot-fixture"
    assert snapshot["revisions"]["site"]["sim-site"] == client.get(URL).json()["revision"]
    assert snapshot["priced_intervals"][0]["tariff_version_id"] == snapshot["tariff_versions"][0]["id"]
    artifact = client.get(record["download_url"]).content
    text = (zipfile.ZipFile(io.BytesIO(artifact)).read("xl/worksheets/sheet1.xml")
            if fmt == "excel" else artifact)
    assert b"not a utility bill" in text
    assert b"snapshot-fixture" in text
    ctl.store.db.execute("DELETE FROM samples")
    site = ctl.store.get("site", "sim-site")
    ctl.store.put("site", "sim-site", {**site, "import_tariff_versions": []})
    assert client.get(record["download_url"]).content == artifact
    assert client.get("/api/reports/recent").json()[0]["snapshot"] == record["snapshot"]
    login(local, "other")
    assert client.get(record["download_url"]).status_code == 403


def test_missing_price_is_null_and_audit_failure_rolls_back(local, monkeypatch):
    client, ctl = local
    headers, body = setup_cost(local)
    site = ctl.store.get("site", "sim-site")
    ctl.store.put("site", "sim-site", {**site, "import_tariff_versions": []})
    response = client.post("/api/reports/generate", headers=headers, json=body)
    data = response.json()["snapshot"]["import_cost_snapshot"]["sites"][0]
    assert data["estimated_import_cost_vnd"] is None
    assert len(data["unpriced_intervals"]) == 2
    before = ctl.store.list("report_archive")

    def fail(*args, **kwargs):
        raise RuntimeError("audit failure")

    monkeypatch.setattr(ctl.store, "audit", fail)
    with pytest.raises(RuntimeError, match="audit failure"):
        client.post("/api/reports/generate", headers=headers, json=body)
    assert ctl.store.list("report_archive") == before


@pytest.mark.parametrize("reason", ["meter", "window", "samples"])
def test_snapshot_limits_reject_without_archive(local, monkeypatch, reason):
    client, ctl = local
    headers, body = setup_cost(local)
    if reason == "meter":
        site = ctl.store.get("site", "sim-site")
        ctl.store.put("site", "sim-site", {**site, "billing_meter_device_id": "missing"})
    elif reason == "window":
        body["end"] = (START + timedelta(days=31)).isoformat()
    else:
        monkeypatch.setattr(ctl.store, "report_samples", lambda *args: [{}] * 10001)
    response = client.post("/api/reports/generate", headers=headers, json=body)
    assert response.status_code == 422, response.text
    assert not ctl.store.list("report_archive")