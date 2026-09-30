"""Reports preserve measured counter boundaries, artifact bytes and site scope."""

import io
import zipfile
from datetime import timedelta

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.domain import Sample, Source, utcnow


def measured_interval(ctl):
    end = utcnow() - timedelta(seconds=1)
    start = end - timedelta(minutes=10)
    samples = []
    for metric, delta in [("pv", 1200), ("load", 900), ("grid_import", 100), ("grid_export", 300)]:
        for at, v in [(start, 10000), (end, 10000 + delta)]:
            samples.append(
                Sample(
                    device_id="sim-device",
                    metric=metric + "_total_wh",
                    unit="Wh",
                    value=v,
                    source=Source.SIMULATOR,
                    source_timestamp=at,
                    quality="GOOD",
                    binding_id="test-" + metric,
                )
            )
    ctl.store.add_samples(samples)
    return {
        "site_id": "sim-site",
        "start": start.isoformat(),
        "end": (end + timedelta(seconds=1)).isoformat(),
    }


def test_reports_empty_store(local):
    c, _ = local
    h = login(local)
    d = c.get("/api/reports/analytics/summary", headers=h).json()
    for k in (
        "pv_generation_kwh",
        "load_consumption_kwh",
        "co2_avoided_ton",
        "evn_savings_vnd",
        "battery_cycles",
        "uptime_pct",
    ):
        assert d[k] is None
    assert c.get("/api/reports/recent", headers=h).json() == []


@pytest.mark.parametrize("fmt", ["csv", "excel", "html"])
def test_archive_download_rechecks_scope_for_existing_session(local, fmt):
    c, ctl = local
    headers = login(local, "engineer")
    response = c.post("/api/reports/generate", headers=headers,
                      json={"site_id": "sim-site", "format": fmt})
    assert response.status_code == 201
    url = response.json()["download_url"]
    assert c.get(url).status_code == 200
    ctl.store.db.execute("UPDATE users SET sites=? WHERE id=?", ('["other-site"]', "engineer"))
    assert c.get(url).status_code == 403
    assert c.get("/api/reports/recent").json() == []


def test_counter_delta_and_storage_provenance(local):
    c, ctl = local
    h = login(local)
    interval = measured_interval(ctl)
    url = "/api/reports/analytics/summary"
    d = c.get(url, params=interval, headers=h).json()
    assert d["pv_generation_kwh"] == 1.2
    assert d["load_consumption_kwh"] == 0.9
    assert d["grid_export_kwh"] == 0.3
    assert d["self_consumption_kwh"] is None
    ctl.store.put("site_acceptance", "sim-site", {"battery_absent_verified": True})
    d = c.get(url, params=interval, headers=h).json()
    assert d["self_consumption_kwh"] == pytest.approx(0.9)
    assert d["evn_savings_vnd"] is None
    assert d["co2_avoided_ton"] is None


@pytest.mark.parametrize(
    "fmt,extension,mime",
    [("csv", "csv", "text/csv"), ("excel", "xlsx", "spreadsheetml"), ("html", "html", "text/html")],
)
def test_report_artifact_snapshot_and_scope(local, fmt, extension, mime):
    c, ctl = local
    h = login(local)
    interval = measured_interval(ctl)
    r = c.post(
        "/api/reports/generate",
        headers=h,
        json={**interval, "format": fmt, "title": "<script>alert(1)</script>"},
    )
    assert r.status_code == 201, r.text
    record = r.json()
    assert "artifact_base64" not in record
    assert record["extension"] == extension
    url = record["download_url"]
    download = c.get(url, headers=h)
    assert download.status_code == 200
    assert mime in download.headers["content-type"]
    if fmt == "excel":
        assert zipfile.is_zipfile(io.BytesIO(download.content))
    elif fmt == "html":
        assert b"<script>" not in download.content
        assert b"&lt;script&gt;" in download.content
    else:
        assert "1.2" in download.text
    ctl.store.db.execute("DELETE FROM samples")
    assert c.get(url, headers=h).content == download.content
    h = login(local, "other")
    assert c.get(url, headers=h).status_code == 403
    assert c.get("/api/reports/recent", headers=h).json() == []


def test_fleet_archive_requires_access_to_all_original_sites(local):
    c, _ = local
    h = login(local)
    r = c.post("/api/reports/generate", headers=h, json={"format": "csv"})
    assert r.status_code == 201
    h = login(local, "viewer")
    assert c.get(r.json()["download_url"], headers=h).status_code == 403
    assert c.get("/api/reports/analytics/summary?site_id=other-site", headers=h).status_code == 403


def test_engineer_can_generate_scoped_report_but_viewer_and_other_site_cannot(local):
    c, ctl = local
    interval = measured_interval(ctl)
    headers = login(local, "engineer")
    response = c.post("/api/reports/generate", headers=headers, json={**interval, "format": "csv"})
    assert response.status_code == 201, response.text
    assert c.get(response.json()["download_url"], headers=headers).status_code == 200
    for account in ("viewer", "other"):
        headers = login(local, account)
        assert (
            c.post("/api/reports/generate", headers=headers, json={**interval, "format": "csv"}).status_code
            == 403
        )
    assert len(ctl.store.list("report_archive")) == 1


@pytest.mark.parametrize(
    "payload",
    [
        {"format": "pdf"},
        {"report_type": "performance"},
        {"email_recipient": "nobody@example.invalid"},
        {"start": "2026-01-01", "end": "2026-01-02"},
    ],
)
def test_unimplemented_or_ambiguous_report_is_rejected(local, payload):
    c, ctl = local
    h = login(local)
    assert c.post("/api/reports/generate", headers=h, json=payload).status_code == 422
    assert ctl.store.list("report_archive") == []
