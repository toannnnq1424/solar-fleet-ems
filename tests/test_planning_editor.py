"""Persisted advisory editor contracts: no physical commands or live accounts."""

import pytest
from test_explicit_operational_inputs import configuration
from test_workspaces import local as local
from test_workspaces import login

URL = "/api/sites/sim-site/planning-configuration"


def test_revision_required_and_stale_save_preserves_configuration(local):
    client, ctl = local
    headers = login(local)
    initial = client.get(URL).json()
    assert client.post(URL, json=configuration(), headers=headers).status_code == 422
    body = {**configuration(), "expected_revision": initial["revision"]}
    saved = client.post(URL, json=body, headers=headers)
    assert saved.status_code == 200
    assert saved.json()["revision"] > initial["revision"]
    before = ctl.store.get("site", "sim-site")
    assert client.post(URL, json=body, headers=headers).status_code == 409
    assert ctl.store.get("site", "sim-site") == before
    assert ctl.store.list("command") == []


def test_site_aba_invalidates_editor_snapshot(local):
    client, ctl = local
    headers = login(local)
    revision = client.get(URL).json()["revision"]
    site = ctl.store.get("site", "sim-site")
    ctl.store.put("site", "sim-site", {**site, "name": "temporary"})
    ctl.store.put("site", "sim-site", site)
    assert client.post(URL, json={**configuration(), "expected_revision": revision},
                       headers=headers).status_code == 409
    assert ctl.store.get("site", "sim-site") == site


@pytest.mark.parametrize("role", ["viewer", "operator", "engineer", "other"])
def test_non_admin_cannot_change_planning(local, role):
    client, ctl = local
    headers = login(local, role)
    before = ctl.store.get("site", "sim-site")
    response = client.post(URL, json={**configuration(), "expected_revision": 0}, headers=headers)
    assert response.status_code == 403
    assert ctl.store.get("site", "sim-site") == before


@pytest.mark.parametrize("field,value", [
    ("charge_efficiency", 0), ("usable_kwh", 100000), ("currency", "VND"),
    ("tariff_source", " "), ("hourly_prices", []), ("rated_cycle_life", 1.5),
])
def test_validation_with_current_revision_has_no_side_effect(local, field, value):
    client, ctl = local
    headers = login(local)
    body = {**configuration(), "expected_revision": client.get(URL).json()["revision"]}
    body["dispatch_config"][field] = value
    before = ctl.store.get("site", "sim-site")
    assert client.post(URL, json=body, headers=headers).status_code == 422
    assert ctl.store.get("site", "sim-site") == before