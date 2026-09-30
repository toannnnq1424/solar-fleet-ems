"""Authorized cloud observations are validated independently, without persistence repair."""

import pytest
from cloud_fixture import cloud_latest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.domain import Sample, Source, utcnow


@pytest.mark.parametrize("patch", [
    {"value": "invalid"}, {"quality": "INVENTED"},
    {"source_timestamp": "2026-01-01T00:00:00"},
    {"device_id": "foreign"}, {"binding_id": "foreign"}, {"source": Source.AGENT},
])
@pytest.mark.parametrize("sibling", [False, True])
def test_cloud_samples_fail_closed_and_preserve_siblings(local, patch, sibling):
    client, ctl = local
    login(local, "viewer")
    sample = Sample(device_id="sim-device", binding_id="sim", metric="power", value=10,
                    unit="W", source=Source.CLOUD, source_timestamp=utcnow(),
                    quality="UNVERIFIED").model_dump(mode="json")
    cloud_latest(ctl.store, "sim-device", {"samples": [sample], "state": "HAS_DATA"})
    row = ctl.store.get("latest", "sim-device")
    good = row["samples"][0]
    row["samples"] = [good | patch] + ([good] if sibling else [])
    ctl.store.put("latest", "sim-device", row)
    response = client.get("/api/devices/sim-device")
    assert response.status_code == 200
    latest = response.json()["latest"]
    assert len(latest["samples"]) == int(sibling)
    assert latest["state"] == ("HAS_DATA" if sibling else "NO_DATA")
    assert ctl.store.get("latest", "sim-device") == row