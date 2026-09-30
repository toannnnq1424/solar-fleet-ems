"""Mapping authoring and review against synthetic observed channels; no hardware."""

from datetime import timedelta

import pytest
from test_extension_data_stream import binding, draft
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.data_workspace import MetricMapping
from solar_fleet.domain import Sample, Source, utcnow


def test_context_uses_observed_units_labels_and_scoped_permissions(local):
    c, ctl = binding(local)
    record = ctl.store.get("latest", "sim-device")
    record["native"] = {"dataList": [{"key": "lab.power", "title": "Measured AC flow"}]}
    ctl.store.put("latest", "sim-device", record)
    login(local, "viewer")
    response = c.get("/api/devices/sim-device/mapping-context")
    assert response.status_code == 200, response.text
    context = response.json()
    assert context["can_edit"] is False and context["drafts_activate_hardware"] is False
    assert context["bindings"] == [{"id": "69967848e4a53e16df385645", "name": "SIMULATOR cloud provenance", "kind": "binding"}]
    channel = context["channels"][0]
    assert (channel["label"], channel["metric"], channel["value"], channel["unit"]) == (
        "Measured AC flow",
        "lab.power",
        2.5,
        "kW",
    )
    assert channel["selectable"] and not channel["stale"] and channel["quality"] == "UNVERIFIED"
    assert context["unit_dimensions"]["kW"] == "W" and context["metrics"]["grid_voltage_v"] == "V"
    assert all(set(r) == {"id", "title", "url", "evidence_grade"} for r in context["evidence"])
    assert c.get("/api/devices/other-device/mapping-context").status_code == 403
    login(local, "engineer")
    assert c.get("/api/devices/sim-device/mapping-context").json()["can_edit"] is True


def test_context_excludes_revoked_cloud_connection_and_credentials(local):
    c, ctl = binding(local)
    connection = {"id": "lab-cloud", "name": "Lab cloud", "enabled": True, "password": "NEVER-EXPOSE"}
    ctl.store.put("integration", "lab-cloud", connection)
    row = ctl.store.get("binding", "69967848e4a53e16df385645") | {"integration_id": "lab-cloud"}
    ctl.store.put("binding", "69967848e4a53e16df385645", row)
    login(local)
    response = c.get("/api/devices/sim-device/mapping-context")
    assert "NEVER-EXPOSE" not in response.text and response.json()["bindings"][0]["name"] == "Lab cloud"
    ctl.store.put("integration", "lab-cloud", connection | {"enabled": False})
    context = c.get("/api/devices/sim-device/mapping-context").json()
    assert context["channels"] == [] and context["bindings"] == []


def test_context_retains_unsupported_units_without_allowing_mapping(local):
    c, ctl = binding(local)
    record = ctl.store.get("latest", "sim-device")
    record["samples"][0]["unit"] = "VA"
    ctl.store.put("latest", "sim-device", record)
    login(local)
    channel = c.get("/api/devices/sim-device/mapping-context").json()["channels"][0]
    assert channel["unit"] == "VA" and channel["value"] == 2.5 and not channel["selectable"]


def test_agent_context_and_revocation_do_not_require_cloud_binding(local):
    c, ctl = binding(local)
    agent = {
        "id": "lab-agent",
        "name": "Local meter",
        "site_id": "sim-site",
        "device_ids": ["sim-device"],
        "enabled": True,
        "key_hash": "NOT-FOR-UI",
    }
    ctl.store.put("agent", agent["id"], agent)
    sample = Sample(
        device_id="sim-device",
        metric="local.meter",
        value=-120,
        unit="W",
        source=Source.AGENT,
        source_timestamp=utcnow(),
        quality="UNVERIFIED",
        binding_id=agent["id"],
    )
    ctl.store.put(
        "agent_latest",
        "agent-reading",
        {"device_id": "sim-device", "agent_id": agent["id"], "site_id": "sim-site",
         "samples": [sample.model_dump(mode="json")]},
    )
    h = login(local)
    context = c.get("/api/devices/sim-device/mapping-context")
    assert "NOT-FOR-UI" not in context.text
    assert any(b["id"] == agent["id"] for b in context.json()["bindings"])
    assert any(s["metric"] == "local.meter" for s in context.json()["channels"])
    body = draft() | {
        "binding_id": agent["id"],
        "mappings": [
            {
                "source_key": "local.meter",
                "source_unit": "W",
                "metric": "grid_import_w",
                "direction": "negative",
            }
        ],
    }
    row = c.post("/api/mappings", json=body, headers=h).json()
    result = c.post(f"/api/mappings/{row['id']}/simulate", json={}, headers=h).json()
    assert result["results"][0]["value"] == 120
    ctl.store.put("agent", agent["id"], agent | {"device_ids": []})
    assert c.post(f"/api/mappings/{row['id']}/simulate", json={}, headers=h).status_code == 409
    assert all(
        b["id"] != agent["id"] for b in c.get("/api/devices/sim-device/mapping-context").json()["bindings"]
    )


@pytest.mark.parametrize("mutation", ["firmware", "binding", "integration", "site"])
def test_review_revalidates_identity_and_live_binding_without_mutating_revision(local, mutation):
    c, ctl = binding(local)
    h = login(local)
    row = c.post("/api/mappings", json=draft(), headers=h).json()
    if mutation == "firmware":
        device = ctl.store.get("device", "sim-device")
        device["identity"]["firmware"] = "CHANGED"
        ctl.store.put("device", "sim-device", device)
    else:
        bound = ctl.store.get("binding", "69967848e4a53e16df385645")
        if mutation == "binding":
            bound["telemetry_enabled"] = False
        elif mutation == "site":
            bound["site_id"] = "other-site"
        else:
            bound["integration_id"] = "MISSING-INTEGRATION"
        ctl.store.put("binding", "69967848e4a53e16df385645", bound)
    h = login(local, "engineer")
    response = c.post(
        f"/api/mappings/{row['id']}/review",
        json={"revision": 1, "outcome": "REVIEWED", "notes": "Reviewed synthetic source contract"},
        headers=h,
    )
    assert response.status_code == 409, response.text
    expected = "mapping_identity_changed" if mutation == "firmware" else "mapping_binding_not_available"
    assert response.json()["error"] == expected
    assert c.get("/api/data-workspace").json()["mappings"][0]["applicability"] == expected
    stored = ctl.store.get("mapping_draft", row["id"])
    assert stored == row and "review" not in stored


@pytest.mark.parametrize(
    "source_patch",
    [
        {"source_timestamp": None},
        {"source_timestamp": (utcnow() - timedelta(hours=2)).isoformat()},
        {"quality": "INVALID"},
    ],
)
def test_simulation_never_outputs_stale_or_invalid_values(local, source_patch):
    c, ctl = binding(local)
    h = login(local)
    row = c.post("/api/mappings", json=draft(), headers=h).json()
    record = ctl.store.get("latest", "sim-device")
    record["samples"][0].update(source_patch)
    ctl.store.put("latest", "sim-device", record)
    result = c.post(f"/api/mappings/{row['id']}/simulate", json={}, headers=h).json()
    assert result["results"][0]["value"] is None
    assert result["results"][0]["result"] == "source_stale_or_invalid"
    assert result["results"][0]["source"]["value"] == 2.5  # Diagnostic evidence stays available.
    assert ctl.store.history("sim-device") == []


def test_duplicate_sample_and_changed_unit_require_resolution(local):
    c, ctl = binding(local)
    h = login(local)
    row = c.post("/api/mappings", json=draft(), headers=h).json()
    url = f"/api/mappings/{row['id']}/simulate"
    record = ctl.store.get("latest", "sim-device")
    sample = record["samples"][0]
    record["samples"] = [sample, sample]
    ctl.store.put("latest", "sim-device", record)
    assert c.post(url, json={}, headers=h).json()["results"][0]["result"] == "ambiguous_source"
    record["samples"] = [sample | {"unit": "W"}]
    ctl.store.put("latest", "sim-device", record)
    output = c.post(url, json={}, headers=h).json()["results"][0]
    assert output["value"] is None and output["result"] == "source_missing_or_unit_mismatch"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), True, "2.5", 1e308])
def test_conversion_rejects_nonfinite_or_non_numeric_sources(value):
    mapping = MetricMapping.model_validate(draft()["mappings"][0])
    assert mapping.convert(value, "kW") == (None, "source_not_finite")


def test_two_editors_and_review_then_edit_preserve_versions_and_invalidate_review(local):
    c, ctl = binding(local)
    h = login(local)
    body = draft() | {"evidence_ids": ["DEYE_API_001"], "notes": "Synthetic documentation reference"}
    row = c.post("/api/mappings", json=body, headers=h).json()
    path = f"/api/mappings/{row['id']}"
    h = login(local, "engineer")
    assert (
        c.post(
            path + "/review",
            json={"revision": 1, "outcome": "REVIEWED", "notes": "Synthetic review with independent author"},
            headers=h,
        ).status_code
        == 200
    )
    h = login(local)
    revision = body | {"revision": 1, "name": "Revised mapping"}
    updated = c.post(path, json=revision, headers=h)
    assert updated.status_code == 200
    assert updated.json()["state"] == "DRAFT" and updated.json()["active"] is False
    assert "review" not in updated.json()
    assert c.post(path, json=revision, headers=h).status_code == 409
    versions = c.get(path + "/versions").json()
    assert len(versions) == 2 and versions[0]["state"] == "REVIEWED"
    assert versions[0]["digest"] != versions[1]["digest"]
    assert ctl.latest(ctl.device("sim-device"))["samples"][0]["metric"] == "lab.power"
