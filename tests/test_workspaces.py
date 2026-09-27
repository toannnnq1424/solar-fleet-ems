"""Synthetic local workflow acceptance; no vendor accounts or equipment."""

import csv
import io
import json
from datetime import timedelta

import pytest
from cryptography.fernet import Fernet
from fastapi.testclient import TestClient

from solar_fleet.app import create_app
from solar_fleet.controller import Controller
from solar_fleet.domain import Role, Sample, Source, utcnow
from solar_fleet.security import Vault, create_user
from solar_fleet.workspaces import csv_text

PASSWORD = "SIMULATOR-workspace-password-only"
ORIGIN = "http://127.0.0.1:8765"


@pytest.fixture
def local(store, device):
    for id, role, sites in [
        ("admin", Role.ADMIN, ["*"]),
        ("scoped-admin", Role.ADMIN, ["sim-site"]),
        ("operator", Role.OPERATOR, ["sim-site"]),
        ("viewer", Role.VIEWER, ["sim-site"]),
        ("engineer", Role.ENGINEER, ["sim-site"]),
        ("other", Role.OPERATOR, ["other-site"]),
    ]:
        create_user(store, id, PASSWORD, role, sites)
    for id in ["sim-site", "other-site"]:
        store.put("site", id, {"id": id, "name": id, "vendor": "SIMULATOR", "timezone": "Asia/Ho_Chi_Minh"})
    store.put("device", device.id, device.model_dump(mode="json"))
    other = device.model_copy(update={"id": "other-device", "site_id": "other-site"})
    store.put("device", other.id, other.model_dump(mode="json"))
    ctl = Controller(store, Vault(store, Fernet.generate_key()))
    with TestClient(create_app(ctl, poll=False), base_url=ORIGIN) as client:
        yield client, ctl


def login(local, name="admin"):
    client, _ = local
    response = client.post(
        "/api/login", json={"username": name, "password": PASSWORD}, headers={"Origin": ORIGIN}
    )
    assert response.status_code == 200
    return {"Origin": ORIGIN, "X-CSRF-Token": response.json()["csrf"]}


def test_declared_specs_persist_without_operational_side_effects(local):
    c, ctl = local
    headers = login(local)
    specs = {"plant_type": "RESIDENTIAL", "battery_capacity_kwh": 12.5,
             "grid_limit_kw": 0, "tariff_type": "FLAT_RATE", "inverter_vendor": "Declared vendor"}
    response = c.post("/api/sites", json={"name": "SIMULATOR inventory", "declared_specs": specs}, headers=headers)
    assert response.status_code == 201
    row = response.json()
    assert row["declared_specs"] == specs
    assert row["vendor"] is None
    assert ctl.store.get("site", row["id"])["declared_specs"] == specs
    assert ctl.store.get("site_config", row["id"]) is None
    assert not ctl.store.commands()
    update = c.post(f"/api/sites/{row['id']}/profile", json={"name": "Renamed"}, headers=headers)
    assert update.status_code == 200
    assert update.json()["declared_specs"] == specs
    assert ctl.store.verify_audit()


@pytest.mark.parametrize("specs", [
    {"battery_capacity_kwh": -1}, {"grid_limit_kw": -1}, {"grid_limit_kw": "NaN"},
    {"plant_type": "unknown"}, {"tariff_type": "invented"}, {"dispatch": True},
])
def test_invalid_declared_specs_rejected(local, specs):
    c, ctl = local
    headers = login(local)
    before = ctl.store.list("site")
    assert c.post("/api/sites", json={"name": "Invalid", "declared_specs": specs}, headers=headers).status_code == 422
    assert ctl.store.list("site") == before


@pytest.mark.parametrize("account", ["operator", "viewer", "other"])
def test_declared_specs_require_admin(local, account):
    c, ctl = local
    headers = login(local, account)
    payload = {"name": "Forbidden", "declared_specs": {"grid_limit_kw": 0}}
    assert c.post("/api/sites", json=payload, headers=headers).status_code == 403
    assert c.post("/api/sites/sim-site/profile", json=payload, headers=headers).status_code == 403
    assert not ctl.store.commands()


def test_manual_site_metadata_does_not_replace_discovery_identity(local):
    c, ctl = local
    headers = login(local)
    response = c.post(
        "/api/sites/sim-site/profile",
        json={"name": "SIMULATOR customer", "capacity_kwp": 10},
        headers=headers,
    )
    assert response.status_code == 200
    assert ctl.store.get("site", "sim-site")["vendor"] == "SIMULATOR"
    assert (
        next(s for s in c.get("/api/fleet").json()["sites"] if s["id"] == "sim-site")["name"]
        == "SIMULATOR customer"
    )
    assert c.post("/api/sites", json={"name": "x", "latitude": 10}, headers=headers).status_code == 422
    assert (
        c.post("/api/sites", json={"name": "x", "timezone": "not/a/zone"}, headers=headers).status_code == 422
    )


@pytest.mark.parametrize(
    "vendor,region,credentials",
    [
        ("Solis", "global", {"key_id": "SIMULATOR-KEY", "key_secret": "SIMULATOR-SECRET"}),
        (
            "SOLARMAN",
            "global",
            {
                "app_id": "SIMULATOR-APP",
                "app_secret": "SIMULATOR-SECRET",
                "identity_value": "SIMULATOR-ID",
                "password": "SIMULATOR-PASSWORD",
            },
        ),
        (
            "Deye",
            "eu",
            {
                "app_id": "SIMULATOR-APP",
                "app_secret": "SIMULATOR-SECRET",
                "identity_value": "SIMULATOR-ID",
                "password": "SIMULATOR-PASSWORD",
            },
        ),
    ],
)
def test_connector_form_encrypts_secrets_without_network_or_echo(local, vendor, region, credentials):
    c, ctl = local
    headers = login(local)
    response = c.post(
        "/api/integrations",
        json={"name": "SIMULATOR", "vendor": vendor, "region": region, "credentials": credentials},
        headers=headers,
    )
    assert response.status_code == 201
    id = response.json()["id"]
    assert response.json()["write_enabled"] is False
    assert ctl.vault.get(id)
    exported = (
        json.dumps([dict(r) for r in ctl.store.db.execute("SELECT * FROM entities")])
        + c.get("/api/audit/security").text
    )
    assert "SIMULATOR-SECRET" not in exported
    assert "SIMULATOR-PASSWORD" not in exported
    assert not ctl.adapters  # Saving is not a hidden network request.
    assert (
        c.post(f"/api/integrations/{id}/enabled", json={"enabled": False}, headers=headers).status_code == 200
    )
    assert ctl.store.get("integration", id)["enabled"] is False


def test_unsupported_or_injected_connector_contracts_are_rejected(local):
    c, _ = local
    headers = login(local)
    for body in [
        {"vendor": "GoodWe", "region": "global", "credentials": {}},
        {"vendor": "Solis", "region": "http://localhost", "credentials": {}},
        {
            "vendor": "Solis",
            "region": "global",
            "credentials": {"key_id": "X", "key_secret": "Y", "url": "https://attacker.invalid"},
        },
    ]:
        assert (
            c.post("/api/integrations", json={"name": "SIMULATOR", **body}, headers=headers).status_code
            == 409
        )


def test_incident_lifecycle_optimistic_concurrency_and_linked_work(local):
    c, ctl = local
    headers = login(local, "operator")
    record = c.post(
        "/api/records/incident",
        json={"site_id": "sim-site", "title": "SIMULATOR fault", "assigned_to": "engineer"},
        headers=headers,
    ).json()
    assert record["revision"] == 1
    path = "/api/records/incident/" + record["id"]
    update = {
        "revision": 1,
        "status": "in_progress",
        "assigned_to": "engineer",
        "note": "SIMULATOR inspection",
    }
    assert c.post(path, json=update, headers=headers).json()["revision"] == 2
    assert c.post(path, json=update, headers=headers).json()["error"] == "record_changed_reload"
    assert (
        c.post(path, json={**update, "revision": 2, "status": "closed"}, headers=headers).status_code == 409
    )
    work = c.post(
        "/api/records/work_order",
        json={"site_id": "sim-site", "title": "SIMULATOR repair", "incident_id": record["id"]},
        headers=headers,
    )
    assert work.status_code == 201
    assert work.json()["incident_id"] == record["id"]
    assert len(ctl.store.get("incident", record["id"])["timeline"]) == 2
    assert ctl.store.verify_audit()


def test_scope_applies_to_records_assignees_exports_and_bulk(local):
    c, _ = local
    headers = login(local, "operator")
    assert (
        c.post(
            "/api/records/incident", json={"site_id": "other-site", "title": "X"}, headers=headers
        ).status_code
        == 403
    )
    assert (
        c.post(
            "/api/records/incident",
            json={"site_id": "sim-site", "title": "X", "assigned_to": "other"},
            headers=headers,
        ).status_code
        == 409
    )
    assert (
        c.post(
            "/api/compatibility",
            json={"device_ids": ["sim-device", "other-device"], "intent": "SET_RESERVE_SOC"},
            headers=headers,
        ).status_code
        == 403
    )
    result = c.get("/api/operations").json()
    assert {a["id"] for a in result["assignees"]} == {
        "admin",
        "scoped-admin",
        "operator",
        "viewer",
        "engineer",
    }
    assert all(set(a) == {"id"} for a in result["assignees"])
    assert "other-site" not in c.get("/api/reports/records/incident").text
    assert c.get("/api/reports/telemetry?device_id=other-device").status_code == 403


def test_scoped_administrator_cannot_grant_global_access(local):
    c, _ = local
    headers = login(local, "scoped-admin")
    assert c.get("/api/users").status_code == 403
    assert c.get("/api/integrations").status_code == 403
    assert c.get("/api/audit/security").status_code == 403
    assert (
        c.post(
            "/api/users",
            json={"username": "intruder", "password": PASSWORD, "role": "Administrator", "site_ids": ["*"]},
            headers=headers,
        ).status_code
        == 403
    )
    assert c.post("/api/users/admin/enabled", json={"enabled": False}, headers=headers).status_code == 403


def test_viewer_can_assess_but_cannot_change_operations(local):
    c, ctl = local
    headers = login(local, "viewer")
    assert (
        c.post(
            "/api/records/incident", json={"site_id": "sim-site", "title": "X"}, headers=headers
        ).status_code
        == 403
    )
    assessment = c.post(
        "/api/compatibility",
        json={"device_ids": ["sim-device"], "intent": "SET_RESERVE_SOC"},
        headers=headers,
    )
    assert assessment.status_code == 200
    assert assessment.json()["targets"][0]["dispatch_enabled"] is False
    assert assessment.json()["targets"][0]["state"] == "UNKNOWN"
    assert ctl.store.commands() == []


def test_schedule_validation_and_manual_acceptance_never_dispatch(local):
    c, ctl = local
    headers = login(local, "engineer")
    slot = {"day": 0, "start": "22:00", "end": "24:00", "mode": "charge", "target_soc": 80, "power_kw": 2}
    body = {"name": "SIMULATOR schedule", "site_id": "sim-site", "slots": [slot]}
    response = c.post("/api/schedules", json=body, headers=headers)
    assert response.status_code == 201 and response.json()["state"] == "DRAFT"
    assert response.json()["timezone"] == "Asia/Ho_Chi_Minh"
    for slots in [
        [slot, slot],
        [{**slot, "end": "02:00"}],
        [{**slot, "target_soc": 101}],
        [{**slot, "power_kw": -1}],
    ]:
        assert c.post("/api/schedules", json={**body, "slots": slots}, headers=headers).status_code == 422
    result = c.post(
        "/api/commissioning",
        json={
            "site_id": "sim-site",
            "check": "control_readback",
            "result": "pass",
            "evidence": "SIMULATOR manual note",
        },
        headers=headers,
    )
    assert result.json()["unlocks_control"] is False
    assert c.get("/api/me").json()["hardware_profiles"] == 0
    assert ctl.store.commands() == []


def test_disabling_user_revokes_existing_session_and_cannot_disable_self(local):
    c, ctl = local
    login(local, "viewer")
    old_token = c.cookies.get("solar_session")
    headers = login(local)
    assert c.post("/api/users/admin/enabled", json={"enabled": False}, headers=headers).status_code == 409
    assert c.post("/api/users/viewer/enabled", json={"enabled": False}, headers=headers).status_code == 200
    assert ctl.store.db.execute("SELECT COUNT(*) FROM sessions WHERE user_id='viewer'").fetchone()[0] == 0
    c.cookies.clear()
    c.cookies.set("solar_session", old_token)
    assert c.get("/api/me").status_code == 401


def test_report_filters_before_limit_uses_offsets_and_does_not_sum_power(local):
    c, ctl = local
    login(local, "viewer")
    now = utcnow().replace(microsecond=0)
    samples = [
        Sample(
            device_id="sim-device",
            metric="sim.power",
            value=i,
            unit="W",
            source=Source.SIMULATOR,
            source_timestamp=now - timedelta(seconds=i),
            quality="UNVERIFIED",
            binding_id="sim-binding",
        )
        for i in range(10002)
    ]
    ctl.store.add_samples(samples)
    assert c.get("/api/reports/telemetry?device_id=sim-device").json()["truncated"] is True
    result = c.get(
        "/api/reports/telemetry",
        params={
            "device_id": "sim-device",
            "metric": "sim.power",
            "start": (now - timedelta(seconds=2)).isoformat(),
            "end": now.isoformat(),
        },
    ).json()
    assert result["sample_count"] == 2 and result["min"] == 1 and result["max"] == 2
    assert result["energy_total"] is None and result["truncated"] is False
    assert c.get("/api/reports/telemetry?device_id=sim-device&start=2026-01-01T00:00:00").status_code == 409
    assert (
        c.get("/api/reports/telemetry?device_id=sim-device&download=true").headers["x-data-truncated"]
        == "true"
    )


def test_csv_neutralizes_formula_text_preserves_numeric_and_vietnamese():
    result = list(
        csv.reader(
            io.StringIO(
                csv_text([{"text": "=SUM(1,2)", "n": -2}, {"text": "Nhà máy", "n": 0}], ["text", "n"]).lstrip(
                    "\ufeff"
                )
            )
        )
    )
    assert result[1] == ["'=SUM(1,2)", "-2"]
    assert result[2] == ["Nhà máy", "0"]


def test_nested_audit_does_not_commit_failed_outer_write(store):
    with pytest.raises(ValueError):
        with store.transaction():
            store.put("incident", "SIMULATOR", {"id": "SIMULATOR"})
            store.audit("operations", {"event": "SIMULATOR created"}, "sim-site")
            raise ValueError("SIMULATOR failure before commit")
    assert store.get("incident", "SIMULATOR") is None
    assert store.audit_rows("operations") == []
    with store.transaction():
        store.put("incident", "SIMULATOR", {"id": "SIMULATOR"})
        store.audit("operations", {"event": "SIMULATOR created"}, "sim-site")
    assert store.get("incident", "SIMULATOR") is not None and store.verify_audit()


def test_rule_save_evaluation_scope_and_audit_are_connected(local):
    c, ctl = local
    headers = login(local, "engineer")
    body = {
        "site_id": "sim-site",
        "name": "SIMULATOR rule",
        "description": "",
        "conditions": [
            {
                "device_id": "sim-device",
                "metric": "battery_soc_percent",
                "unit": "%",
                "comparison": "lt",
                "threshold": 30,
            }
        ],
        "actions": [{"device_id": "sim-device", "intent": "SET_RESERVE_SOC", "parameters": {"value": 40}}],
    }
    saved = c.post("/api/rules", json=body, headers=headers)
    assert saved.status_code == 201
    path = "/api/rules/" + saved.json()["id"] + "/evaluate"
    result = c.post(path, json={}, headers=headers)
    assert result.status_code == 200
    assert result.json()["condition_state"] == "UNKNOWN"
    assert result.json()["dispatch_enabled"] is False
    assert len(c.get("/api/operations").json()["rule_run"]) == 1
    assert not ctl.store.commands() and ctl.store.verify_audit()
    foreign = login(local, "other")
    assert c.post(path, json={}, headers=foreign).status_code == 403
