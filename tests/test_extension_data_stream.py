"""Extension, data provenance and realtime tests use synthetic accounts only."""

from dataclasses import replace
from datetime import timedelta
from pathlib import Path

import pytest
from cryptography.fernet import Fernet
from starlette.websockets import WebSocketDisconnect
from test_workspaces import ORIGIN, login
from test_workspaces import local as local

from solar_fleet.adapters.plugins import builtins
from solar_fleet.controller import Controller, entity_id
from solar_fleet.data_workspace import (
    CommissionedTelemetryProfile,
    MetricMapping,
    accepted_profile,
    apply_profile,
    collection_due,
)
from solar_fleet.domain import DeviceIdentity, Principal, Role, SafetyError, Sample, Source, utcnow
from solar_fleet.integration import (
    DeviceObservation,
    IntegrationPlugin,
    IntegrationRegistry,
    MeasurementObservation,
    PlantObservation,
)
from solar_fleet.security import Vault
from solar_fleet.streams import events_since


class ExtraVendor:
    """Deliberately uses a different response shape from every shipping adapter."""

    per_poll = 7

    def __init__(self, config, credentials, **kwargs):
        self.closed = False

    async def stations(self):
        return [{"plant_ref": "LAB-1"}]

    async def devices(self, station):
        return [{"serial_number": "LAB-INVERTER", "connected": True}]

    async def latest(self, serials):
        return [{"serial_number": "LAB-INVERTER", "watts": 1250}]

    async def close(self):
        self.closed = True


def extra_plugin():
    return IntegrationPlugin(
        id="TEST-ECOSYSTEM-10",
        version="test",
        factory=ExtraVendor,
        plant=lambda raw: PlantObservation(raw["plant_ref"], "Synthetic lab"),
        device=lambda raw: DeviceObservation(
            raw["serial_number"], "INVERTER", "LAB-MODEL", raw["connected"], utcnow()
        ),
        measurement=lambda raw: MeasurementObservation(
            raw["serial_number"], True, utcnow(), [{"key": "power", "value": raw["watts"], "unit": "W"}]
        ),
        namespace="lab10",
        evidence_ids=("TEST-ONLY",),
        authentication="TEST",
        features=frozenset({"discovery", "latest"}),
    )


@pytest.mark.asyncio
async def test_tenth_ecosystem_discovery_poll_without_any_core_branch(store):
    registry = IntegrationRegistry()
    registry.register(extra_plugin())
    vault = Vault(store, Fernet.generate_key())
    config = {"id": "lab", "vendor": "TEST-ECOSYSTEM-10", "region": "lab", "enabled": True}
    store.put("integration", "lab", config)
    vault.put("lab", {"password": "TEST-ONLY"})
    ctl = Controller(store, vault, registry=registry)
    await ctl.poll()
    device = ctl.device(entity_id(config["vendor"], "device", "LAB-INVERTER"))
    assert device.online and device.identity.model == "LAB-MODEL"
    assert ctl.latest(device)["samples"][0]["metric"] == "lab10.power"
    assert ctl.latest(device)["samples"][0]["quality"] == "UNVERIFIED"
    assert store.get("integration_state", "lab")["state"] == "CONNECTED"
    with pytest.raises(SafetyError, match="intent_mapping_unknown"):
        registry.compile(device, "SET_RESERVE_SOC", {"value": 30})
    await ctl.close()


def test_registry_rejects_duplicate_and_unknown_plugins():
    r = IntegrationRegistry()
    r.register(extra_plugin())
    with pytest.raises(ValueError):
        r.register(extra_plugin())
    with pytest.raises(SafetyError, match="adapter_not_implemented"):
        r.require("unknown")


def test_core_and_ui_do_not_branch_on_vendor_names():
    root = Path(__file__).parents[1] / "src/solar_fleet"
    for name in ["controller.py", "control.py", "accounts.py", "integration.py", "static/native-device.js"]:
        text = (root / name).read_text(encoding="utf-8")
        assert not any(
            f'== "{vendor}"' in text or f'=== "{vendor}"' in text for vendor in ["Deye", "Solis", "SOLARMAN"]
        )
    assert "compile_deye" not in (root / "control.py").read_text(encoding="utf-8")


@pytest.mark.parametrize(
    "status,expected", [(0, False), (1, True), (2, True), (3, False), (True, False), ("1", False)]
)
def test_platform_status_semantics_are_owned_by_plugin(status, expected):
    plugin = builtins().require("SOLARMAN")
    observed = plugin.device({"deviceSn": "LAB", "connectStatus": status})
    assert observed.online is expected
    if status == 2:
        assert not builtins().require("Deye").device({"deviceSn": "LAB", "connectStatus": status}).online


def test_read_descriptors_do_not_imply_write_acceptance():
    registry = builtins()
    assert "configuration" in registry.describe("Deye")["features"]
    assert "configuration" not in registry.describe("Solis")["features"]
    assert not registry.describe("Deye")["hardware_accepted"]
    assert len(registry.describe("SOLARMAN")["groups"]) == 9
    assert registry.describe("Unknown")["features"] == []


def binding(local):
    c, ctl = local
    ctl.store.put(
        "binding",
        "SIM-BIND",
        {"id": "SIM-BIND", "device_id": "sim-device", "site_id": "sim-site", "telemetry_enabled": True},
    )
    sample = Sample(
        device_id="sim-device",
        metric="lab.power",
        value=2.5,
        unit="kW",
        source=Source.CLOUD,
        source_timestamp=utcnow(),
        quality="UNVERIFIED",
        binding_id="SIM-BIND",
    )
    ctl.store.put(
        "latest", "sim-device", {"device_id": "sim-device", "samples": [sample.model_dump(mode="json")]}
    )
    return c, ctl


def draft():
    return {
        "device_id": "sim-device",
        "name": "Lab mapping",
        "binding_id": "SIM-BIND",
        "mappings": [
            {"source_key": "lab.power", "source_unit": "kW", "metric": "pv_w", "direction": "nonnegative"}
        ],
        "revision": 0,
    }


def test_mapping_draft_simulates_without_promoting_data(local):
    c, ctl = binding(local)
    h = login(local, "admin")
    r = c.post("/api/mappings", json=draft(), headers=h)
    assert r.status_code == 201, r.text
    row = r.json()
    assert row["active"] is False and row["revision"] == 1
    result = c.post(f"/api/mappings/{row['id']}/simulate", json={}, headers=h).json()
    assert result["results"][0]["value"] == 2500
    assert result["results"][0]["quality"] == "UNVERIFIED"
    assert result["stored_canonical_points"] == 0
    assert ctl.store.history("sim-device") == []
    assert ctl.latest(ctl.device("sim-device"))["samples"][0]["metric"] == "lab.power"


def test_mapping_review_is_independent_revisioned_and_never_activates(local):
    c, ctl = binding(local)
    h = login(local, "engineer")
    row = c.post("/api/mappings", json=draft(), headers=h).json()
    path = f"/api/mappings/{row['id']}"
    review = {"revision": 1, "outcome": "REVIEWED", "notes": "Synthetic evidence reviewed"}
    assert c.post(path + "/review", json=review, headers=h).status_code == 403
    # Save a new revision by installer/admin, then independent engineering review.
    h = login(local)
    assert c.post(path, json=draft(), headers=h).status_code == 409
    assert c.post(path, json=draft() | {"revision": 1}, headers=h).status_code == 200
    h = login(local, "engineer")
    result = c.post(path + "/review", json=review | {"revision": 2}, headers=h)
    assert result.status_code == 200, result.text
    assert result.json()["state"] == "REVIEWED" and result.json()["active"] is False
    assert c.post(path + "/review", json=review | {"revision": 2}, headers=h).status_code == 409
    versions = c.get(path + "/versions").json()
    assert len(versions) == 2 and versions[-1]["review"]["reviewer"] == "engineer"


def test_mapping_scope_identity_and_binding_revocation(local):
    c, ctl = binding(local)
    h = login(local)
    row = c.post("/api/mappings", json=draft(), headers=h).json()
    path = f"/api/mappings/{row['id']}"
    h = login(local, "other")
    assert c.get(path + "/versions").status_code == 403
    assert c.post(path + "/simulate", json={}, headers=h).status_code == 403
    assert c.get("/api/data-workspace").json()["mappings"] == []
    h = login(local, "viewer")
    assert c.post("/api/mappings", json=draft(), headers=h).status_code == 403
    h = login(local)
    d = ctl.store.get("device", "sim-device")
    d["identity"]["firmware"] = "DIFFERENT"
    ctl.store.put("device", d["id"], d)
    assert c.post(path + "/simulate", json={}, headers=h).json()["error"] == "mapping_identity_changed"
    ctl.store.put(
        "binding", "SIM-BIND", {"device_id": "sim-device", "site_id": "sim-site", "telemetry_enabled": False}
    )
    assert c.post("/api/mappings", json=draft(), headers=h).status_code == 409


@pytest.mark.parametrize(
    "patch",
    [
        {"source_unit": "V"},
        {"metric": "UNREVIEWED.custom"},
        {"direction": "signed"},
        {"source_key": "../../unsafe"},
        {"source_unit": "arbitrary"},
    ],
)
def test_mapping_rejects_dimension_and_metric_confusion(patch):
    with pytest.raises(ValueError):
        MetricMapping.model_validate(draft()["mappings"][0] | patch)


def test_negative_direction_and_signed_temperature():
    m = MetricMapping(source_key="lab.p", source_unit="kW", metric="grid_import_w", direction="negative")
    assert m.convert(-2, "kW")[0] == 2000
    assert m.convert(2, "kW")[0] == 0
    assert m.convert(2, "W")[0] is None
    assert (
        MetricMapping(
            source_key="lab.t", source_unit="°C", metric="battery_temperature_c", direction="signed"
        ).convert(-5, "°C")[0]
        == -5
    )


def accepted(device):
    return CommissionedTelemetryProfile(
        id="LAB-PROFILE",
        identity=device.identity,
        evidence_ids=["TEST-ONLY"],
        acceptance_id="LAB-ACCEPTANCE",
        reviewer="Test engineer",
        mappings=[MetricMapping.model_validate(draft()["mappings"][0])],
    )


def test_only_exact_code_registered_acceptance_can_produce_canonical_samples(device):
    profile = accepted(device)
    sample = Sample(
        device_id=device.id,
        metric="lab.power",
        value=2,
        unit="kW",
        source=Source.CLOUD,
        source_timestamp=utcnow(),
        binding_id="LAB",
        quality="UNVERIFIED",
    )
    output = apply_profile(accepted_profile([profile], device), [sample])
    assert len(output) == 2 and output[0] == sample
    assert output[1].value == 2000 and output[1].quality == "GOOD"
    assert "LAB-ACCEPTANCE" in output[1].evidence_ids
    changed = device.model_copy(update={"identity": device.identity.model_copy(update={"firmware": "other"})})
    assert accepted_profile([profile], changed) is None
    with pytest.raises(SafetyError, match="ambiguous_telemetry_profile"):
        accepted_profile([profile, profile], device)
    bad = sample.model_copy(update={"quality": "INVALID"})
    assert apply_profile(profile, [bad])[1].value is None
    with pytest.raises(ValueError):
        accepted(device.model_copy(update={"identity": DeviceIdentity(vendor="test")}))


def test_collection_interval_revision_and_scope(local):
    c, ctl = local
    ctl.store.put("integration", "LAB", {"id": "LAB", "name": "Lab", "vendor": "SIMULATOR", "enabled": True})
    h = login(local, "operator")
    assert c.get("/api/collection").status_code == 403
    h = login(local)
    policy = {"interval_seconds": 600, "max_devices_per_poll": 4, "revision": 0}
    assert c.post("/api/collection/LAB", json=policy, headers=h).status_code == 200
    assert c.post("/api/collection/LAB", json=policy, headers=h).status_code == 409
    now = utcnow()
    ctl.store.put("integration_state", "LAB", {"last_attempt": now.isoformat()})
    assert not collection_due(ctl.store, {"id": "LAB"}, now + timedelta(seconds=599))
    assert collection_due(ctl.store, {"id": "LAB"}, now + timedelta(seconds=600))
    assert c.post("/api/collection/LAB", json=policy | {"interval_seconds": 1}, headers=h).status_code == 422


def test_events_scope_cursor_reset_and_transaction_rollback(local):
    c, ctl = local
    who = Principal(id="viewer", role=Role.VIEWER, site_ids=["sim-site"])
    newest = ctl.store.db.execute("SELECT MAX(seq) FROM ui_events").fetchone()[0]
    ctl.store.put("latest", "other-device", {"device_id": "other-device", "secret": "MUST-NOT-LEAK"})
    packet = events_since(ctl.store, who, newest)
    assert packet["type"] == "heartbeat" and "MUST-NOT-LEAK" not in str(packet)
    count = ctl.store.db.execute("SELECT COUNT(*) FROM ui_events").fetchone()[0]
    with pytest.raises(ValueError):
        with ctl.store.transaction():
            ctl.store.put("incident", "lab", {"site_id": "sim-site"})
            raise ValueError()
    assert ctl.store.db.execute("SELECT COUNT(*) FROM ui_events").fetchone()[0] == count
    assert events_since(ctl.store, who, packet["cursor"] + 100)["type"] == "reset"


def test_websocket_auth_origin_scope_and_no_command_channel(local):
    c, ctl = local
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("ws://127.0.0.1:8765/api/stream", headers={"Origin": ORIGIN}):
            pass
    login(local, "viewer")
    with pytest.raises(WebSocketDisconnect):
        with c.websocket_connect("ws://127.0.0.1:8765/api/stream", headers={"Origin": "https://untrusted.example"}):
            pass
    with c.websocket_connect("ws://127.0.0.1:8765/api/stream", headers={"Origin": ORIGIN}) as ws:
        assert ws.receive_json()["type"] == "ready"
        packet = ws.receive_json()
        assert all(r["site_id"] == "sim-site" for r in packet["changes"])
        ws.send_text('{"command":"WRITE"}')
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008
    assert ctl.store.commands() == []


def test_websocket_revokes_existing_stream_after_session_deleted(local):
    c, ctl = local
    login(local, "viewer")
    with c.websocket_connect("ws://127.0.0.1:8765/api/stream", headers={"Origin": ORIGIN}) as ws:
        ws.receive_json()
        ws.receive_json()
        ctl.store.db.execute("DELETE FROM sessions")
        ws.send_text("ping")
        with pytest.raises(WebSocketDisconnect) as exc:
            ws.receive_json()
        assert exc.value.code == 1008


def test_adapter_feature_gates_before_constructing_network_client(local):
    c, ctl = local
    h = login(local, "viewer")
    for action in ["configuration", "alerts"]:
        r = c.post(f"/api/devices/sim-device/{action}", json={}, headers=h)
        assert r.status_code == 409 and r.json()["error"] == "adapter_feature_not_implemented"
    assert not ctl.adapters


def test_new_plugin_registration_flows_through_generic_api(local):
    c, ctl = local
    plugin = replace(
        extra_plugin(),
        registration={"regions": ["lab"], "fields": ["lab_key"], "identity": False},
        prepare_credentials=lambda values, options: values,
    )
    ctl.registry.register(plugin)
    headers = login(local)
    providers = c.get("/api/providers").json()
    assert any(p["id"] == plugin.id and p["implemented"] for p in providers)
    result = c.post(
        "/api/integrations",
        json={
            "name": "Synthetic extra platform",
            "vendor": plugin.id,
            "region": "lab",
            "credentials": {"lab_key": "TEST-ONLY-KEY"},
        },
        headers=headers,
    )
    assert result.status_code == 201, result.text
    assert ctl.vault.get(result.json()["id"]) == {"lab_key": "TEST-ONLY-KEY"}
    assert "TEST-ONLY-KEY" not in c.get("/api/integrations").text
