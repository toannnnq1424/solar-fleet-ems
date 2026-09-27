"""Sidebar regressions: isolated data, no delivery or equipment dispatch."""

import pytest
from test_workspaces import local as local
from test_workspaces import login


@pytest.mark.parametrize("path,key", [
    ("/api/fleet/devices-overview", "devices"),
    ("/api/fleet/firmware-matrix", "devices"),
])
def test_equipment_scope_and_missing_firmware(local, path, key):
    client, ctl = local
    other = ctl.store.get("device", "other-device")
    other["identity"]["firmware"] = None
    ctl.store.put("device", "other-device", other)
    login(local)
    response = client.get(path)
    assert response.status_code == 200
    assert len(response.json()[key]) == 2
    response = client.get(path, params={"site_id": "sim-site"})
    assert response.status_code == 200
    assert {r["site_id"] for r in response.json()[key]} == {"sim-site"}
    login(local, "viewer")
    assert client.get(path, params={"site_id": "other-site"}).status_code == 403
    assert {r["site_id"] for r in client.get(path).json()[key]} == {"sim-site"}
    assert not ctl.store.commands()


def test_notification_persistence_encryption_and_partial_update(local):
    client, ctl = local
    headers = login(local)
    secrets = {"smtp_password": "SIM-password", "telegram_bot_token": "SIM-token",
               "zalo_webhook": "https://example.invalid/SIM-secret"}
    response = client.post("/api/notifications/config", headers=headers,
                           json={"smtp_host": "example.invalid", **secrets})
    assert response.status_code == 200
    assert ctl.vault.get("notification") == secrets
    public = client.get("/api/notifications/config")
    assert public.status_code == 200
    stored = ctl.store.get("config", "notification")
    for key, value in secrets.items():
        assert key not in stored
        assert value not in public.text
    assert public.json()["channels"]["telegram_bot_token_configured"] is True
    assert client.post("/api/notifications/config", headers=headers,
                       json={"smtp_port": 465}).status_code == 200
    assert ctl.vault.get("notification") == secrets
    assert ctl.store.get("config", "notification")["smtp_host"] == "example.invalid"
    test_response = client.post("/api/notifications/test", headers=headers, json={})
    assert test_response.status_code == 200
    assert test_response.json()["status"] == "error"
    assert ctl.store.verify_audit()
    assert not ctl.store.commands()


@pytest.mark.parametrize("account", ["viewer", "operator", "scoped-admin"])
def test_notification_global_admin_boundary(local, account):
    client, ctl = local
    headers = login(local, account)
    assert client.get("/api/notifications/config").status_code == 403
    for path in ("/api/notifications/config", "/api/notifications/test"):
        assert client.post(path, headers=headers, json={}).status_code == 403
    assert ctl.store.get("config", "notification") is None


@pytest.mark.parametrize("body", [{"smtp_port": 0}, {"recipients_alarm": "bad"}, {"invented": 1}])
def test_notification_invalid_input_has_no_side_effects(local, body):
    client, ctl = local
    headers = login(local)
    assert client.post("/api/notifications/config", headers=headers, json=body).status_code == 422
    assert ctl.store.get("config", "notification") is None


def bill_input():
    return {"tariff_key": "vn_evn_commercial_tou", "import_kwh_hourly": [1] * 24,
            "export_kwh_hourly": [0] * 24, "peak_demand_kw": 0}


@pytest.mark.parametrize("patch", [
    {"import_kwh_hourly": [1]}, {"export_kwh_hourly": [0] * 25},
    {"import_kwh_hourly": [-1] * 24}, {"peak_demand_kw": -1},
    {"import_kwh_hourly": ["NaN"] * 24}, {"dispatch": True},
])
def test_bill_rejects_incomplete_or_invalid_scenarios(local, patch):
    client, ctl = local
    headers = login(local, "viewer")
    response = client.post("/api/tariffs/calculate-bill", headers=headers, json={**bill_input(), **patch})
    assert response.status_code == 422
    assert not ctl.store.commands()


def test_catalogue_bill_is_explicit_advisory_not_effective_billing(local):
    client, ctl = local
    assert client.post("/api/tariffs/calculate-bill", json=bill_input()).status_code in (401, 403)
    headers = login(local, "viewer")
    response = client.post("/api/tariffs/calculate-bill", headers=headers, json=bill_input())
    assert response.status_code == 200
    assert response.json()["billing_ready"] is False
    assert response.json()["effective_version_verified"] is False
    assert response.json()["total_import_kwh"] == 24
    assert not ctl.store.list("tariff")
    assert not ctl.store.commands()