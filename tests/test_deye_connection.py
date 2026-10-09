"""Managed application/account workflow; synthetic identities and MockTransport only."""

import hashlib
import json

import httpx
import pytest
from test_workspaces import local as local
from test_workspaces import login

from solar_fleet.adapters.deye import Deye
from solar_fleet.domain import SafetyError

APP = {"app_id": "SYNTHETIC-APP-ID", "app_secret": "SYNTHETIC-APP-SECRET", "revision": None}
EMAIL = "synthetic@example.invalid"
PASSWORD = "SYNTHETIC-vendor-password"


def configure(client, headers, region="eu", revision=None):
    response = client.post(
        "/api/admin/deye-applications/" + region, json={**APP, "revision": revision}, headers=headers
    )
    assert response.status_code == 200, response.text
    return response.json()["revision"]


def payload(revision, **extra):
    return {"region": "eu", "application_revision": revision, "email": EMAIL, "password": PASSWORD, **extra}


def transport(monkeypatch, ctl, handler=None):
    requests, clients = [], []

    def response(request):
        requests.append(request)
        if handler:
            return handler(request)
        if request.url.path.endswith("/account/token"):
            return httpx.Response(
                200,
                json={"success": True, "code": 1000000, "accessToken": "SYNTHETIC-TOKEN", "expiresIn": 3600},
            )
        return httpx.Response(200, json={"success": True, "code": 1000000, "stationList": [], "total": 0})

    def factory(config, credentials, budgets):
        client = httpx.AsyncClient(transport=httpx.MockTransport(response))
        clients.append(client)
        return Deye(config, credentials, client=client, budgets=budgets)

    monkeypatch.setattr(ctl.registry, "create", factory)
    return requests, clients


@pytest.mark.parametrize(
    "region,host",
    [
        ("eu", "eu1-developer.deyecloud.com"),
        ("am", "us1-developer.deyecloud.com"),
        ("india", "india-developer.deyecloud.com"),
    ],
)
def test_authenticate_encrypt_persist_and_reuse_normal_adapter(local, monkeypatch, region, host):
    c, ctl = local
    h = login(local)
    revision = configure(c, h, region)
    requests, clients = transport(monkeypatch, ctl)
    result = c.post("/api/connections/deye", json=payload(revision, region=region), headers=h)
    assert result.status_code == 201, result.text
    id = result.json()["id"]
    assert result.json() == {
        "id": id,
        "state": "AUTHENTICATED",
        "inventory_synced": False,
        "write_enabled": False,
    }
    assert len(requests) == 1 and requests[0].url.host == host
    auth = json.loads(requests[0].content)
    assert auth == {
        "appSecret": APP["app_secret"],
        "email": EMAIL,
        "password": hashlib.sha256(PASSWORD.encode()).hexdigest(),
    }
    assert requests[0].url.params["appId"] == APP["app_id"]
    assert clients[0].is_closed
    stored = ctl.vault.get(id)
    assert "password" not in stored and stored["password_sha256"] == auth["password"]
    assert ctl.store.get("integration", id)["application_revision"] == revision
    for path in (
        "/api/connections/deye/options",
        "/api/integrations",
        "/api/accounts/overview",
        "/api/operations",
    ):
        public = c.get(path).text
        for secret in (APP["app_secret"], APP["app_id"], PASSWORD, "SYNTHETIC-TOKEN", auth["password"]):
            assert secret not in public
    dump = "\n".join(ctl.store.db.iterdump())
    assert APP["app_secret"] not in dump and PASSWORD not in dump and "SYNTHETIC-TOKEN" not in dump
    # Existing read workflow obtains a fresh token; no token returned to browser/persisted.
    checked = c.post(f"/api/integrations/{id}/check", json={}, headers=h)
    assert checked.status_code == 200 and checked.json()["state"] == "PASS"
    assert all("/order/" not in r.url.path for r in requests)
    assert not ctl.store.commands() and ctl.store.verify_audit()


@pytest.mark.parametrize("role", ["viewer", "operator", "scoped-admin", "engineer"])
def test_only_organization_admin_can_write_application_or_connect(local, role):
    c, ctl = local
    h = login(local, role)
    assert c.get("/api/connections/deye/options").status_code == 200
    assert c.post("/api/admin/deye-applications/eu", json=APP, headers=h).status_code == 403
    assert c.post("/api/connections/deye", json=payload("unknown"), headers=h).status_code == 403
    assert (
        c.post("/api/admin/deye-applications/eu/disable", json={"revision": "unknown"}, headers=h).status_code
        == 403
    )
    assert not ctl.store.list("deye_application") and not ctl.store.list("integration")


@pytest.mark.parametrize(
    "status,body",
    [
        (401, {"msg": PASSWORD}),
        (200, {"success": False, "msg": APP["app_secret"]}),
        (200, {"success": True, "code": 1000000}),
        (429, {"msg": "SYNTHETIC-TOKEN"}),
    ],
)
def test_rejected_or_malformed_auth_never_saves_or_leaks(local, monkeypatch, status, body):
    c, ctl = local
    h = login(local)
    revision = configure(c, h)
    _, clients = transport(monkeypatch, ctl, lambda request: httpx.Response(status, json=body))
    result = c.post("/api/connections/deye", json=payload(revision), headers=h)
    assert result.status_code == 400
    assert result.json()["detail"] == "deye_authentication_failed"
    assert not ctl.store.list("integration")
    assert ctl.store.db.execute("SELECT count(*) FROM secrets").fetchone()[0] == 1
    assert clients[0].is_closed


def test_rotation_disable_and_reconnect_preserve_id_but_block_old_credentials(local, monkeypatch):
    c, ctl = local
    h = login(local)
    revision = configure(c, h)
    transport(monkeypatch, ctl)
    first = c.post("/api/connections/deye", json=payload(revision), headers=h).json()["id"]
    before = ctl.store.get("integration", first)["credential_revision"]
    assert c.post("/api/connections/deye", json=payload(revision), headers=h).status_code == 409
    second = configure(c, h, revision=revision)
    assert not ctl.store.get("integration", first)["enabled"]
    assert c.post(f"/api/integrations/{first}/enabled", json={"enabled": True}, headers=h).status_code == 409
    # Even a direct stale enable cannot bypass the controller's application fence.
    row = ctl.store.get("integration", first)
    row["enabled"] = True
    ctl.store.put("integration", first, row)
    with pytest.raises(SafetyError, match="deye_application_reconnect_required"):
        ctl.integration_adapter(first)
    assert (
        c.post("/api/connections/deye", json=payload(revision, integration_id=first), headers=h).status_code
        == 409
    )
    assert (
        c.post(
            "/api/connections/deye",
            json=payload(second, integration_id=first, email="other@example.invalid"),
            headers=h,
        ).status_code
        == 409
    )
    result = c.post("/api/connections/deye", json=payload(second, integration_id=first), headers=h)
    assert result.status_code == 201 and result.json()["id"] == first
    assert ctl.store.get("integration", first)["credential_revision"] != before
    assert (
        c.post("/api/admin/deye-applications/eu/disable", json={"revision": second}, headers=h).status_code
        == 200
    )
    assert not ctl.store.get("integration", first)["enabled"]
    assert c.post("/api/connections/deye", json=payload(second), headers=h).status_code == 409
    assert not ctl.store.commands()


@pytest.mark.parametrize("change", ["application", "app_aba", "role", "session", "integration_aba"])
def test_context_rechecked_after_vendor_await_before_persistence(local, monkeypatch, change):
    c, ctl = local
    h = login(local)
    revision = configure(c, h)

    def handler(request):
        if change in ("application", "app_aba"):
            old = ctl.store.get("deye_application", "eu")
            ctl.store.put("deye_application", "eu", {**old, "enabled": False})
            if change == "app_aba":
                ctl.store.put("deye_application", "eu", old)
        elif change == "role":
            ctl.store.db.execute("UPDATE users SET role='Viewer' WHERE id='admin'")
        elif change == "session":
            ctl.store.db.execute("DELETE FROM sessions")
        return httpx.Response(
            200, json={"success": True, "code": 1000000, "accessToken": "SYNTHETIC-TOKEN", "expiresIn": 3600}
        )

    requests, clients = transport(monkeypatch, ctl, handler)
    if change == "integration_aba":
        original = ctl.registry.create

        def factory(config, credentials, budgets):
            adapter = original(config, credentials, budgets)
            authenticate = adapter.authenticate

            async def changed():
                token = await authenticate()
                ctl.store.put("integration", config["id"], config)
                ctl.store.db.execute(
                    "DELETE FROM entities WHERE kind='integration' AND id=?", (config["id"],)
                )
                return token

            adapter.authenticate = changed
            return adapter

        monkeypatch.setattr(ctl.registry, "create", factory)
    result = c.post("/api/connections/deye", json=payload(revision), headers=h)
    assert result.status_code == 409
    assert not ctl.store.list("integration")
    assert clients[0].is_closed and len(requests) == 1


def test_missing_config_revision_csrf_rate_limit_and_validation(local, monkeypatch):
    c, ctl = local
    h = login(local)
    assert c.post("/api/connections/deye", json=payload("none"), headers=h).status_code == 409
    assert c.post("/api/admin/deye-applications/eu", json=APP).status_code == 403
    revision = configure(c, h)
    assert c.post("/api/admin/deye-applications/eu", json=APP, headers=h).status_code == 409
    for update in (
        {"region": "https://invalid.test"},
        {"email": "invalid"},
        {"password": ""},
        {"app_secret": "injected"},
    ):
        result = c.post("/api/connections/deye", json=payload(revision, **update), headers=h)
        assert result.status_code == 422
        assert PASSWORD not in result.text
    requests, _ = transport(monkeypatch, ctl, lambda request: httpx.Response(403, json={}))
    for _ in range(6):
        assert c.post("/api/connections/deye", json=payload(revision), headers=h).status_code == 400
    assert c.post("/api/connections/deye", json=payload(revision), headers=h).status_code == 429
    assert len(requests) == 6


def test_application_save_rolls_back_vault_and_metadata_on_audit_failure(local, monkeypatch):
    c, ctl = local
    h = login(local)

    def fail(*args, **kwargs):
        raise RuntimeError("SYNTHETIC audit failure")

    monkeypatch.setattr(ctl.store, "audit", fail)
    with pytest.raises(RuntimeError, match="SYNTHETIC audit failure"):
        c.post("/api/admin/deye-applications/eu", json=APP, headers=h)
    assert not ctl.store.list("deye_application")
    assert ctl.store.db.execute("SELECT count(*) FROM secrets").fetchone()[0] == 0
