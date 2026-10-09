"""SEMS+ account -> shared controller -> native observations, synthetic only."""

import httpx
import pytest
from test_goodwe_plus import CONFIG, CREDENTIALS, LOGIN, envelope, reply
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.adapters.goodwe import GoodWe

BODY = {"email": CREDENTIALS["account"], "password": CREDENTIALS["password"],
        "region": "hk", "vendor_terms_accepted": True}


def transport(monkeypatch, ctl, handler=reply):
    calls, clients = [], []

    def respond(req):
        calls.append(req)
        return handler(req)

    def factory(config, credentials, budgets):
        client = httpx.AsyncClient(transport=httpx.MockTransport(respond))
        clients.append(client)
        return GoodWe(config, credentials, client=client, budgets=budgets)

    monkeypatch.setattr(ctl.registry, "create", factory)
    return calls, clients


@pytest.mark.parametrize('null_devices', [False, True, 'omitted'])
def test_link_check_sync_native_scope_unknown_and_no_control(local, monkeypatch, null_devices):
    client, ctl = local
    headers = login(local)
    def handler(req):
        if null_devices and req.url.path.endswith(('fixture-logger/telemetry', 'fixture-battery/telemetry')):
            return httpx.Response(200, json={'code': '00000'}) if null_devices == 'omitted' else envelope(None)
        if null_devices == 'omitted' and req.url.path.endswith('/relatedDevices'):
            return envelope([{'sn': 'fixture-battery', 'type': 'BATTERY_BANK'}])
        return reply(req)

    calls, clients = transport(monkeypatch, ctl, handler)
    response = client.post("/api/connections/goodwe", json=BODY, headers=headers)
    assert response.status_code == 201, response.text
    id = response.json()["id"]
    assert response.json()["inventory_synced"] is False
    assert response.json()["write_enabled"] is False
    assert len(calls) == 1 and calls[0].url.path == LOGIN and clients[0].is_closed
    assert ctl.store.get("integration", id)["platform"] == CONFIG["platform"]
    assert ctl.vault.get(id) == CREDENTIALS
    checked = client.post(f"/api/integrations/{id}/check", json={}, headers=headers)
    assert checked.json()["state"] == "PASS", checked.text
    synced = client.post("/api/sync", json={}, headers=headers)
    assert synced.status_code == 200, synced.text
    fleet = client.get("/api/fleet").json()
    devices = [d for d in fleet["devices"] if d["integration_id"] == id]
    assert len(devices) == 4
    assert all(d["online"] is None and d["stale"] is True for d in devices)
    inventory = client.get('/api/fleet/devices-overview').json()
    imported = [d for d in inventory['devices'] if d['integration_id'] == id]
    assert all(d['online'] is None and d['status'] == 'UNKNOWN' for d in imported)
    assert inventory['summary']['unknown_connectivity_count'] >= len(imported)
    assert inventory['summary']['warning_count'] is None
    assert sum(d['reading_summary']['sample_count'] > 0 for d in imported) == (2 if null_devices else 4)
    assert all(d['reading_summary']['verified_recent_count'] == 0 for d in imported)
    assert {d["type"] for d in devices} == {"INVERTER", "DATA_LOGGER", "SMART_METER", "BATTERY_BANK" if null_devices == 'omitted' else "BAT_SYS"}
    assert ctl.store.get('integration_state', id)['state'] == 'CONNECTED'
    site_id = devices[0]['site_id']
    report = client.get('/api/sites/' + site_id + '/vendor-report').json()['report']
    assert report['power']['pv_w'] == 0 and report['power']['load_w'] == 1200
    assert report['control_eligible'] is False and report['source_timezone'] is None
    assert report['quality'] == 'VENDOR_REPORTED'
    overview = client.get('/api/sites/' + site_id + '/overview-summary').json()
    assert overview['vendor_report'] == report
    assert overview['energy_flow']['pv_w'] is None
    assert overview['plant_status']['today_yield_kwh'] is None
    for device in devices:
        reading = client.get('/api/devices/' + device['id']).json()['latest']
        if null_devices and device['type'] in ('DATA_LOGGER', 'BAT_SYS', 'BATTERY_BANK'):
            assert reading['state'] == 'NO_DATA' and not reading['samples']
        else:
            assert reading['samples'] and reading['native']['dataList'][0]['value'] == 0
    latest = client.get("/api/devices/" + devices[0]["id"])
    assert latest.status_code == 200
    assert all(s["quality"] != "GOOD" for s in latest.json()["latest"]["samples"])
    assert all(not b["control_enabled"] for b in ctl.store.list("binding") if b["integration_id"] == id)
    public = client.get("/api/accounts/overview").text + latest.text + str(fleet)
    assert CREDENTIALS["password"] not in public and "fixture-token" not in public
    dump = "\n".join(ctl.store.db.iterdump())
    assert CREDENTIALS["password"] not in dump and "fixture-token" not in dump
    assert not ctl.store.commands() and ctl.store.verify_audit()
    # Scope is still enforced by the shared API.
    login(local, "viewer")
    assert client.get("/api/devices/" + devices[0]["id"]).status_code == 403


@pytest.mark.parametrize("role", ["viewer", "operator", "scoped-admin", "engineer"])
def test_link_requires_org_admin(local, role):
    client, ctl = local
    headers = login(local, role)
    response = client.post("/api/connections/goodwe", json=BODY, headers=headers)
    assert response.status_code == 403
    assert not ctl.store.list("integration")


@pytest.mark.parametrize("change", [{"vendor_terms_accepted": False}, {"region": "auto"},
                                   {"email": "not-an-email"}, {"password": ""}])
def test_invalid_input_never_persists_or_leaks_password(local, change):
    client, ctl = local
    headers = login(local)
    response = client.post("/api/connections/goodwe", json={**BODY, **change}, headers=headers)
    assert response.status_code == 422
    assert CREDENTIALS["password"] not in response.text
    assert not ctl.store.list("integration")


def test_failed_login_no_save_or_host_fallback(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    calls, clients = transport(monkeypatch, ctl, lambda req: httpx.Response(
        200, json={"code": "C0602", "msg": CREDENTIALS["password"]}))
    response = client.post("/api/connections/goodwe", json=BODY, headers=headers)
    assert response.status_code == 400
    assert CREDENTIALS["password"] not in response.text
    assert not ctl.store.list("integration") and clients[0].is_closed and len(calls) == 1


def test_reconnect_revision_duplicate_and_csrf(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    calls, _ = transport(monkeypatch, ctl)
    assert client.post("/api/connections/goodwe", json=BODY).status_code == 403
    id = client.post("/api/connections/goodwe", json=BODY, headers=headers).json()["id"]
    assert client.post("/api/connections/goodwe", json=BODY, headers=headers).status_code == 409
    reconnect = {**BODY, "integration_id": id, "revision": 1}
    assert client.post("/api/connections/goodwe", json=reconnect, headers=headers).status_code == 201
    assert client.post("/api/connections/goodwe", json=reconnect, headers=headers).status_code == 409
    assert len(calls) == 2 and len(ctl.store.list("integration")) == 1


def test_logout_during_auth_never_saves(local, monkeypatch):
    client, ctl = local
    headers = login(local)

    def handler(req):
        ctl.store.db.execute("DELETE FROM sessions")
        return reply(req)

    _, clients = transport(monkeypatch, ctl, handler)
    response = client.post("/api/connections/goodwe", json=BODY, headers=headers)
    assert response.status_code == 409
    assert response.json() == {"error": "session_authority_changed"}
    assert not ctl.store.list("integration") and clients[0].is_closed


def test_vendor_rate_limit_survives_temporary_adapter_close(local, monkeypatch):
    client, ctl = local
    headers = login(local)
    calls, clients = transport(monkeypatch, ctl, lambda req: httpx.Response(
        200, json={"code": "GY0429"}))
    for _ in range(2):
        response = client.post("/api/connections/goodwe", json=BODY, headers=headers)
        assert response.status_code == 429
    assert len(calls) == 1 and clients[0].is_closed
    assert not ctl.store.list("integration")


def test_network_unavailable_is_not_a_wrong_password(local, monkeypatch):
    client, ctl = local
    headers = login(local)

    def unavailable(req):
        raise httpx.ConnectError("SYNTHETIC-password", request=req)

    calls, clients = transport(monkeypatch, ctl, unavailable)
    response = client.post("/api/connections/goodwe", json=BODY, headers=headers)
    assert response.status_code == 503
    assert response.json() == {"detail": "goodwe_authentication_unavailable"}
    assert len(calls) == 1 and clients[0].is_closed
    assert not ctl.store.list("integration")
