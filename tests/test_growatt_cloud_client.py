"""Unit and contract tests for Growatt Cloud OpenAPI V1 & ShineServer Client.

Validates:
- Growatt password hashing algorithm
- Multi-region server URL mapping (global, cn, us)
- Normalization of SPH cloud telemetry to Solar Fleet EMS schema
- Cloud parameter write compilers (SPH priority, AC charge, power limits, MIN time segments)
- Bounds checking and format validation
- GrowattCloudClient simulation, plant/device registry, and hardware acceptance safety gates
"""

from __future__ import annotations

import pytest

from solar_fleet.growatt_cloud_client import (
    GROWATT_SERVERS,
    GrowattCloudClient,
    compile_min_time_segment,
    compile_sph_ac_charge_setting,
    compile_sph_charge_discharge_powers,
    compile_sph_priority_setting,
    hash_growatt_password,
    normalize_sph_cloud_data,
)


def test_growatt_password_hash():
    """Verify ShinePhone legacy password MD5 transformation."""
    h = hash_growatt_password("secret123")
    assert isinstance(h, str)
    assert len(h) == 32
    # Verify deterministic behavior
    assert hash_growatt_password("secret123") == h


def test_growatt_regional_endpoints():
    """Verify regional endpoint resolutions."""
    client_global = GrowattCloudClient(region="global")
    assert client_global.base_url == GROWATT_SERVERS["global"]

    client_cn = GrowattCloudClient(region="cn")
    assert client_cn.base_url == GROWATT_SERVERS["cn"]

    client_us = GrowattCloudClient(region="us")
    assert client_us.base_url == GROWATT_SERVERS["us"]


def test_normalize_sph_cloud_data():
    """Verify normalization of Growatt Cloud SPH response to EMS schema."""
    raw = {
        "serialNum": "SPH-TEST-99",
        "fwVersion": "YA1.0",
        "pmax": 5000,
        "ppv": 4200.0,
        "ppv1": 2200.0,
        "vpv1": 380.0,
        "ppv2": 2000.0,
        "vpv2": 375.0,
        "gridPower": 1500.0,
        "loadPower": 1800.0,
        "pcharge": 900.0,
        "soc": 88,
        "vbat": 53.6,
        "priorityChoose": 1,
        "acChargeEnable": 1,
        "chargePowerCommand": 90,
        "disChargePowerCommand": 100,
        "wdisChargeSOCLowLimit1": 15,
        "forcedChargeTimeStart1": "01:00",
        "forcedChargeTimeStop1": "05:00",
        "forcedDischargeTimeStart1": "17:30",
        "forcedDischargeTimeStop1": "19:30",
    }
    ems = normalize_sph_cloud_data(raw)
    assert ems["vendor"] == "Growatt"
    assert ems["protocol"] == "Growatt-OpenAPI-V1"
    assert ems["serial_number"] == "SPH-TEST-99"
    assert ems["power_flow"]["solar_power_w"] == 4200.0
    assert ems["power_flow"]["grid_power_w"] == 1500.0
    assert ems["battery"]["soc_percent"] == 88
    assert ems["battery"]["voltage_v"] == 53.6
    assert "Battery First" in ems["configuration"]["priority_mode"]
    assert ems["configuration"]["ac_charge_enabled"] is True
    assert ems["configuration"]["charge_windows"][0]["start"] == "01:00"


def test_compile_sph_settings_success_and_bounds():
    """Verify SPH setting compilers and range enforcements."""
    # 1. Priority mode: 0, 1, 2
    cmd_p = compile_sph_priority_setting(1)
    assert cmd_p["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_p["parameter_values"]["priorityChoose"] == 1
    with pytest.raises(ValueError):
        compile_sph_priority_setting(3)

    # 2. AC Charge: True / False
    cmd_ac = compile_sph_ac_charge_setting(True)
    assert cmd_ac["parameter_values"]["acChargeEnable"] == 1

    # 3. Power commands
    cmd_pwr = compile_sph_charge_discharge_powers(80, 100)
    assert cmd_pwr["parameter_values"]["chargePowerCommand"] == 80
    assert cmd_pwr["parameter_values"]["disChargePowerCommand"] == 100
    with pytest.raises(ValueError):
        compile_sph_charge_discharge_powers(110, 50)


def test_compile_min_time_segments_success_and_bounds():
    """Verify MIN / TLX 9-segment schedule compiler."""
    cmd_seg = compile_min_time_segment(
        segment_id=2,
        batt_mode=1,
        start_time="02:30",
        end_time="05:30",
        enabled=True,
    )
    assert cmd_seg["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_seg["parameter_values"]["segment_id"] == 2
    assert cmd_seg["parameter_values"]["batt_mode"] == 1
    assert cmd_seg["parameter_values"]["start_time"] == "02:30"

    with pytest.raises(ValueError):
        compile_min_time_segment(10, 1, "00:00", "01:00")
    with pytest.raises(ValueError):
        compile_min_time_segment(1, 4, "00:00", "01:00")
    with pytest.raises(ValueError):
        compile_min_time_segment(1, 0, "25:00", "01:00")


def test_growatt_cloud_client_simulation_and_safety():
    """Verify GrowattCloudClient plant listing, SPH detail, and safety gates."""
    client = GrowattCloudClient(token="TEST-TOKEN", region="global", simulated=True)

    # Plant list
    plants = client.list_plants()
    assert len(plants) >= 1
    assert plants[0]["plant_name"] == "Hanoi Solar Rooftop Plant #1"

    # Device list
    devices = client.list_devices(plants[0]["plant_id"])
    assert len(devices) == 2

    # SPH Detail
    sph_detail = client.get_sph_detail("SPH460001")
    assert sph_detail["serial_number"] == "SPH460001"
    assert sph_detail["battery"]["soc_percent"] == 86

    # Safety gate: locked by default
    res_locked = client.execute_command_safely("sph_priority", {"priority_code": 0}, unlocked=False)
    assert res_locked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # Safety gate: authorized
    res_unlocked = client.execute_command_safely("sph_priority", {"priority_code": 0}, unlocked=True)
    assert res_unlocked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"  # command itself marks acceptance gate
    assert res_unlocked["parameter_values"]["priorityChoose"] == 0


def test_api_growatt_cloud_plants(local):
    """Verify POST /api/growatt-cloud/plants."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-cloud/plants",
        json={"token": "DEMO-KEY", "region": "global"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "PyPi_GrowattServer (MIT clean-room independent)"
    assert len(data["plants"]) >= 1
    assert data["plants"][0]["plant_name"] == "Hanoi Solar Rooftop Plant #1"


def test_api_growatt_cloud_devices(local):
    """Verify POST /api/growatt-cloud/devices."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-cloud/devices",
        json={"plant_id": "PLANT-GW-8801"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["plant_id"] == "PLANT-GW-8801"
    assert len(data["devices"]) == 2
    assert data["devices"][0]["device_type"] == "sph"


def test_api_growatt_cloud_sph_detail(local):
    """Verify POST /api/growatt-cloud/sph-detail."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-cloud/sph-detail",
        json={"device_sn": "SPH460001"},
        headers=headers,
    )
    assert resp.status_code == 200
    tel = resp.json()["telemetry"]
    assert tel["vendor"] == "Growatt"
    assert tel["serial_number"] == "SPH460001"
    assert tel["power_flow"]["solar_power_w"] == 3850.0
    assert tel["battery"]["soc_percent"] == 86
    assert tel["configuration"]["priority_mode"] == "Battery First (Forced AC/PV charge)"


def test_api_growatt_cloud_command(local):
    """Verify POST /api/growatt-cloud/command with safety gate."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # 1. Locked command
    resp_locked = client.post(
        "/api/growatt-cloud/command",
        json={
            "command_type": "sph_ac_charge",
            "params": {"enable": True},
            "unlocked": False,
        },
        headers=headers,
    )
    assert resp_locked.status_code == 200
    res_data = resp_locked.json()["result"]
    assert res_data["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # 2. Unlocked command compiles correctly
    resp_unlocked = client.post(
        "/api/growatt-cloud/command",
        json={
            "command_type": "sph_ac_charge",
            "params": {"enable": True},
            "unlocked": True,
        },
        headers=headers,
    )
    assert resp_unlocked.status_code == 200
    res_unlocked_data = resp_unlocked.json()["result"]
    assert res_unlocked_data["parameter_values"]["acChargeEnable"] == 1
