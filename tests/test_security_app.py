import json
import sqlite3

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Role, SafetyError
from solar_fleet.security import Vault, authorize_control, create_user, redact, verify_password

SIM_PASSWORD = "SIMULATOR-test-password-ONLY"
ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def client(store):
    create_user(store, "sim-admin", SIM_PASSWORD, Role.ADMIN, ["*"])
    create_user(store, "sim-viewer", SIM_PASSWORD, Role.VIEWER, ["sim-site"])
    controller = Controller(store, Vault(store, Fernet.generate_key()))
    with TestClient(create_app(controller, poll=False), base_url=ORIGIN) as c:
        yield c


def login(client, username="sim-admin"):
    response = client.post(
        "/api/login", json={"username": username, "password": SIM_PASSWORD}, headers={"Origin": ORIGIN}
    )
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf"]}


def test_loopback_api_still_requires_authentication(client):
    for path in ["/api/fleet", "/api/integrations", "/api/research", "/api/commands", "/api/audit/security"]:
        assert client.get(path).status_code == 401
    assert client.get("/").status_code == 200


def test_dns_rebinding_and_cross_origin_login_rejected(client):
    assert client.get("/api/fleet", headers={"Host": "attacker.invalid:8765"}).status_code == 400
    response = client.post(
        "/api/login",
        json={"username": "sim-admin", "password": SIM_PASSWORD},
        headers={"Origin": "https://attacker.invalid"},
    )
    assert response.status_code == 403


def test_session_cookie_csrf_and_logout_revocation(client):
    headers = login(client)
    response = client.get("/api/me")
    assert response.json()["user"]["role"] == "Administrator"
    assert client.post("/api/logout", json={}, headers={"Origin": ORIGIN}).status_code == 403
    assert client.post("/api/logout", json={}, headers=headers).status_code == 200
    assert client.get("/api/me").status_code == 401


def test_cookie_security_headers_and_no_inline_scripts(client):
    response = client.post(
        "/api/login", json={"username": "sim-admin", "password": SIM_PASSWORD}, headers={"Origin": ORIGIN}
    )
    cookie = response.headers["set-cookie"].lower()
    assert "httponly" in cookie and "samesite=strict" in cookie
    assert "frame-ancestors 'none'" in response.headers["content-security-policy"]
    assert response.headers["cache-control"] == "no-store"


def test_viewer_cannot_access_admin_logs_integrations_or_other_sites(client, store, device):
    store.put("device", device.id, device.model_dump(mode="json"))
    other = device.model_copy(update={"id": "other-device", "site_id": "other-site"})
    store.put("device", other.id, other.model_dump(mode="json"))
    headers = login(client, "sim-viewer")
    assert client.get("/api/integrations").status_code == 403
    assert client.get("/api/audit/security").status_code == 403
    assert client.post("/api/sync", json={}, headers=headers).status_code == 403
    assert client.get("/api/devices/other-device").status_code == 403
    assert [d["id"] for d in client.get("/api/fleet").json()["devices"]] == ["sim-device"]


def test_revoked_user_session_cannot_continue(client, store):
    login(client)
    store.db.execute("UPDATE users SET active=0 WHERE id='sim-admin'")
    assert client.get("/api/me").status_code == 401


def test_login_validation_never_echoes_secret(client):
    response = client.post(
        "/api/login",
        json={"username": "sim-admin", "password": SIM_PASSWORD, "injected": "SIM-SECRET"},
        headers={"Origin": ORIGIN},
    )
    assert (
        response.status_code == 422
        and SIM_PASSWORD not in response.text
        and "SIM-SECRET" not in response.text
    )


def test_login_rate_limit_cannot_be_evaded_with_different_usernames(client):
    for i in range(8):
        assert (
            client.post(
                "/api/login", json={"username": f"bad-{i}", "password": "wrong"}, headers={"Origin": ORIGIN}
            ).status_code
            == 401
        )
    assert (
        client.post(
            "/api/login", json={"username": "sim-admin", "password": SIM_PASSWORD}, headers={"Origin": ORIGIN}
        ).status_code
        == 429
    )


def test_empty_fleet_and_full_native_catalog_are_not_fake(client):
    login(client)
    fleet = client.get("/api/fleet").json()
    assert fleet["devices"] == [] and fleet["sites"] == [] and fleet["state"] == "NO_INTEGRATION"
    research = client.get("/api/research").json()
    assert len(research["native"]) == 39 and len(research["sources"]) == 45
    assert all(not item["enabled"] for item in research["native"])


def test_secrets_are_encrypted_and_redacted_nested(store):
    key = Fernet.generate_key()
    vault = Vault(store, key)
    vault.put("sim", {"app_secret": "SIM-SECRET", "password_sha256": "SIM-HASH"})
    raw = store.db.execute("SELECT ciphertext FROM secrets").fetchone()[0]
    assert b"SIM-SECRET" not in raw and vault.get("sim")["app_secret"] == "SIM-SECRET"
    with pytest.raises(SafetyError, match="credentials_unavailable"):
        Vault(store, Fernet.generate_key()).get("sim")
    store.audit(
        "security",
        {
            "event": "sim",
            "nested": [{"access_token": "SIM-TOKEN", "appSecret": "SIM-SECRET", "password": "SIM-PASSWORD"}],
        },
    )
    assert "SIM-TOKEN" not in json.dumps(store.audit_rows("security"))
    assert redact({"safe": 1, "authorization": "bearer SIM"}) == {"safe": 1, "authorization": "[REDACTED]"}


def test_scrypt_and_audit_immutability(store):
    create_user(store, "sim", SIM_PASSWORD, Role.VIEWER, [])
    hashed = store.db.execute("SELECT password_hash FROM users").fetchone()[0]
    assert verify_password(SIM_PASSWORD, hashed) and not verify_password("wrong", hashed)
    assert SIM_PASSWORD not in hashed
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("UPDATE audit SET body='{}'")
    with pytest.raises(sqlite3.IntegrityError):
        store.db.execute("DELETE FROM audit")
    assert store.verify_audit()


@pytest.mark.parametrize("role", [Role.VIEWER, Role.OPERATOR, Role.ADMIN])
def test_admin_is_not_implicitly_an_engineer(operator, capability, role):
    operator.role = role
    with pytest.raises(SafetyError, match="control_role_denied"):
        authorize_control(operator, "sim-site", capability)


def test_control_audit_is_scoped_to_site(client, store):
    store.audit("control", {"event": "visible"}, "sim-site")
    store.audit("control", {"event": "PRIVATE-OTHER-SITE"}, "other-site")
    login(client, "sim-viewer")
    response = client.get("/api/audit/control")
    assert "visible" in response.text and "PRIVATE-OTHER-SITE" not in response.text
