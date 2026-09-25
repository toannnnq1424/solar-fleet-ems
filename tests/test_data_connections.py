"""Tests for Data & Connections workspace APIs (sources, priority, collection config, test-connection)."""

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Role
from solar_fleet.security import Vault, create_user

PASSWORD = "SIMULATOR-workspace-password-only"
ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def local_env(store, device):
    for id, role, sites in [
        ("admin", Role.ADMIN, ["*"]),
        ("operator", Role.OPERATOR, ["site_alpha"]),
        ("viewer", Role.VIEWER, ["site_alpha"]),
    ]:
        create_user(store, id, PASSWORD, role, sites)

    store.put(
        "site",
        "site_alpha",
        {
            "id": "site_alpha",
            "name": "Site Alpha Test Plant",
            "address": "KCN Tan Binh, TP HCM",
            "timezone": "Asia/Ho_Chi_Minh",
        },
    )

    ctl = Controller(store, Vault(store, Fernet.generate_key()))
    with TestClient(create_app(ctl, poll=False), base_url=ORIGIN) as client:
        yield client, ctl, store


def auth_headers(client, username="admin"):
    res = client.post(
        "/api/login",
        json={"username": username, "password": PASSWORD},
        headers={"Origin": ORIGIN},
    )
    assert res.status_code == 200
    csrf = res.json()["csrf"]
    return {"Origin": ORIGIN, "X-CSRF-Token": csrf}


def test_get_data_sources_empty(local_env):
    """When no integrations or agents are registered, sources should be empty, not hardcoded dummy."""
    client, _, _ = local_env
    headers = auth_headers(client, "admin")

    res = client.get("/api/data-sources?site_id=site_alpha", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert data["site_id"] == "site_alpha"
    assert data["site_name"] == "Site Alpha Test Plant"
    assert isinstance(data["sources"], list)
    # No agents or integrations registered yet
    assert len(data["sources"]) == 0
    assert data["kpis"]["total_sources"] == 0
    assert "priority" in data
    assert "diagnostics" in data
    assert "collection_config" in data


def test_get_data_sources_with_registered_agent(local_env):
    """When a site agent is registered in the store, it must appear in sources."""
    client, _, store = local_env
    headers = auth_headers(client, "admin")

    store.put(
        "agent",
        "agent_01",
        {
            "id": "agent_01",
            "name": "Local Edge Gateway",
            "site_id": "site_alpha",
            "enabled": True,
            "device_ids": [],
            "last_heartbeat": "2026-09-20T10:00:00Z",
        },
    )

    res = client.get("/api/data-sources?site_id=site_alpha", headers=headers)
    assert res.status_code == 200
    data = res.json()
    assert len(data["sources"]) == 1
    src = data["sources"][0]
    assert src["id"] == "agent_agent_01"
    assert src["name"] == "Local Edge Gateway"
    assert src["type"] == "Site Agent"
    assert src["status"] == "ENROLLED"
    assert data["kpis"]["total_sources"] == 1
    assert data["kpis"]["online_count"] == 0


def test_set_data_sources_priority(local_env):
    client, _, store = local_env
    h = auth_headers(client, "operator")
    r = client.post(
        "/api/data-sources/priority",
        headers=h,
        json={"site_id": "site_alpha", "priorities": ["LOCAL", "SITE_AGENT", "VENDOR_CLOUD"]},
    )
    assert r.status_code == 409
    assert store.get("site_data_priority", "site_alpha") is None
    assert "overall_status" not in r.json()


def test_update_collection_config(local_env):
    client, _, store = local_env
    h = auth_headers(client, "operator")
    r = client.post("/api/data-sources/collection-config", headers=h, json={"site_id": "site_alpha"})
    assert r.status_code == 409
    assert store.get("site_collection_config", "site_alpha") is None
    assert "overall_status" not in r.json()


def test_test_data_sources_connection(local_env):
    client, _, store = local_env
    h = auth_headers(client, "operator")
    r = client.post("/api/data-sources/test-connection", headers=h, json={"site_id": "site_alpha"})
    assert r.status_code == 409
    assert store.get("site_collection_config", "site_alpha") is None
    assert "overall_status" not in r.json()
