"""Tests for Device Workspace 6 tabs and device operations."""

from test_workspaces import local as local
from test_workspaces import login


def test_device_detail_structure(local):
    """Verify GET /api/devices/{id} returns comprehensive identity, adapter, latest, and capabilities."""
    client, ctl = local
    headers = login(local, "admin")

    # sim-device is in store from local fixture
    resp = client.get("/api/devices/sim-device", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "device" in data
    assert data["device"]["id"] == "sim-device"
    assert "adapter" in data
    assert "latest" in data
    assert "capabilities" in data
    assert "control_profiles" in data
    assert "bindings" in data


def test_device_history_retention(local):
    """Verify GET /api/devices/{id}/history returns 7-day retention scope."""
    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/devices/sim-device/history", headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "samples" in data
    assert data["scope"] == "LOCAL_RETENTION_7_DAYS"


def test_device_configuration_feature_guard(local):
    """Verify POST /api/devices/{id}/configuration requires adapter feature."""
    client, _ = local
    headers = login(local, "admin")

    # SIMULATOR adapter does not have "configuration" feature by default
    resp = client.post("/api/devices/sim-device/configuration", json={}, headers=headers)
    assert resp.status_code == 409


def test_device_site_isolation_access(local):
    """Verify operator scoped to other-site cannot access sim-device."""
    client, _ = local
    other_headers = login(local, "other")

    resp = client.get("/api/devices/sim-device", headers=other_headers)
    assert resp.status_code in (403, 404)


def test_fleet_devices_overview_api(local):
    """Verify GET /api/fleet/devices-overview returns aggregated device stats and inventory."""
    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/fleet/devices-overview", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "summary" in data
    assert "devices" in data
    summary = data["summary"]
    assert "total_devices" in summary
    assert "online_count" in summary
    assert "by_type" in summary

    for dev in data["devices"]:
        assert "id" in dev
        assert "type" in dev
        assert "vendor" in dev
        assert "status" in dev


def test_device_modbus_inspect_api(local):
    c, _ = local
    h = login(local)
    r = c.post(
        "/api/devices/sim-device/modbus-inspect",
        headers=h,
        json={"start_register": 34816, "quantity": 5, "slave_id": 1},
    )
    assert r.status_code == 409
    assert r.json()["error"] == "local_register_reader_not_connected"


def test_device_native_config_groups_safety_locks(local):
    """Verify GET /api/devices/{id}/native-config-groups enforces acceptance safety locks."""
    client, _ = local
    headers = login(local, "admin")

    resp = client.get("/api/devices/sim-device/native-config-groups", headers=headers)
    assert resp.status_code == 200
    data = resp.json()

    assert "groups" in data
    assert data["groups"] == []  # Simulator has no vendor-native groups.
    for grp in data["groups"]:
        assert grp["locked"] is True
        assert grp["lock_reason"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"


def test_fleet_firmware_matrix_api(local):
    c, ctl = local
    h = login(local)
    r = c.get("/api/fleet/firmware-matrix", headers=h)
    assert r.status_code == 200
    assert r.json()["total_devices"] == len(ctl.devices())
    assert "sha256_hash" not in r.text  # No fabricated image hash from a device id.
