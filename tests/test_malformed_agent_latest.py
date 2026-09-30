"""Stored synthetic telemetry must not break unrelated, authorized reads."""

import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.domain import Sample, Source, utcnow


@pytest.mark.parametrize("malformed", [
    {}, {"device_id": "sim-device"},
    {"device_id": "sim-device", "agent_id": []},
    {"samples": None}, {"samples": {}}, {"samples": "invalid"},
    {"samples": [None, 42, "invalid"]},
    {"sample_patch": {"value": "not-numeric"}},
    {"sample_patch": {"source_timestamp": "2026-01-01T00:00:00"}},
    {"sample_patch": {"quality": "INVENTED"}},
    {"sample_patch": {"device_id": "other-device"}},
    {"sample_patch": {"binding_id": "other-agent"}},
    {"sample_patch": {"source": "VENDOR_CLOUD"}},
])
def test_malformed_agent_latest_preserves_valid_observations(local, malformed):
    client, ctl = local
    login(local, "viewer")
    agent = {"id": "sim-agent", "site_id": "sim-site", "enabled": True,
             "device_ids": ["sim-device"]}
    ctl.store.put("agent", agent["id"], agent)
    sample = Sample(device_id="sim-device", binding_id=agent["id"],
                    metric="agent.native.power", value=10, unit="W", source=Source.AGENT,
                    source_timestamp=utcnow(), quality="UNVERIFIED").model_dump(mode="json")
    valid = {"device_id": "sim-device", "agent_id": agent["id"], "site_id": "sim-site",
             "samples": [sample]}
    if "sample_patch" in malformed:
        # A bad sample must not suppress its valid sibling.
        bad = valid | {"samples": [sample | malformed["sample_patch"], sample]}
    elif "samples" in malformed:
        bad = valid | malformed
    else:
        bad = malformed
    ctl.store.put("agent_latest", "a-malformed", bad)
    if "sample_patch" not in malformed:
        ctl.store.put("agent_latest", "z-valid", valid)
    response = client.get("/api/devices/sim-device")
    assert response.status_code == 200
    latest = response.json()["latest"]
    assert latest["state"] == "HAS_DATA"
    assert len(latest["samples"]) == 1
    assert latest["samples"][0]["value"] == 10
    assert latest["samples"][0]["quality"] == "UNVERIFIED"
    assert ctl.store.get("agent_latest", "a-malformed") == bad


def test_invalid_agent_sample_does_not_claim_has_data(local):
    client, ctl = local
    login(local, "viewer")
    ctl.store.put("agent", "sim-agent", {
        "id": "sim-agent", "site_id": "sim-site", "enabled": True, "device_ids": ["sim-device"],
    })
    ctl.store.put("agent_latest", "bad", {
        "device_id": "sim-device", "agent_id": "sim-agent", "site_id": "sim-site",
        "samples": [{"device_id": "sim-device", "binding_id": "sim-agent", "source": Source.AGENT}],
    })
    response = client.get("/api/devices/sim-device")
    assert response.status_code == 200
    assert response.json()["latest"] == {"device_id": "sim-device", "samples": [], "state": "NO_DATA"}