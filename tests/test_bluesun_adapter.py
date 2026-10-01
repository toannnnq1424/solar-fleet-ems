"""Tests for Bluesun Multi-Platform Adapter (BSM, BSE, Battery BMS)."""

import pytest

from solar_fleet.adapters.bluesun_adapter import (
    BluesunAdapter,
    BluesunBranch,
    BluesunDeviceConfig,
)


@pytest.mark.asyncio
async def test_bluesun_fail_closed_without_transport():
    """Fail-closed test: If no active transport or live credentials exist, status is UNAVAILABLE."""
    adapter = BluesunAdapter(credentials={})
    config = BluesunDeviceConfig(
        device_id="bsm_inv_01",
        branch=BluesunBranch.BSM_OFFGRID,
        serial_number="BSM5500A1234",
    )
    result = await adapter.read_telemetry(config)
    assert result["branch"] == "bsm_offgrid"
    assert result["status"] == "UNAVAILABLE"
    assert result["reason"] == "NO_PHYSICAL_TRANSPORT_CONFIGURED"
    assert result["telemetry"] == {}


@pytest.mark.asyncio
async def test_bluesun_bsm_branch_decoding_with_raw_payload():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bsm_inv_01",
        branch=BluesunBranch.BSM_OFFGRID,
        serial_number="BSM5500A1234",
        modbus_slave_id=1,
    )
    raw_payload = {
        "work_mode": "SolarFirst",
        "pv_power_w": 3200.0,
        "pv1_v": 340.0,
        "soc": 85.0,
        "bat_v": 52.1,
        "ac_power_w": 3000.0,
        "grid_v": 229.0,
        "load_pct": 60.0,
    }
    result = await adapter.read_telemetry(config, raw_data=raw_payload)
    assert result["branch"] == "bsm_offgrid"
    assert result["status"] == "ok"
    assert result["inverter_mode"] == "SolarFirst"
    assert result["telemetry"]["pv_power_w"] == 3200.0
    assert result["telemetry"]["battery_soc"] == 85.0


@pytest.mark.asyncio
async def test_bluesun_bse_branch_decoding_with_raw_payload():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bse_inv_02",
        branch=BluesunBranch.BSE_HYBRID,
        serial_number="BSE6KL19876",
        cloud_station_id="station_bse_01",
    )
    raw_payload = {
        "anti_feed_in": True,
        "export_limit_w": 0.0,
        "grid_p_w": 2500.0,
        "pv_p_w": 5000.0,
        "bat_p_w": -2000.0,
        "load_p_w": 3000.0,
        "soc": 70.0,
        "mode": "Economic",
    }
    result = await adapter.read_telemetry(config, raw_data=raw_payload)
    assert result["branch"] == "bse_hybrid"
    assert result["status"] == "ok"
    assert result["feed_in_limiter_enabled"] is True
    assert result["telemetry"]["grid_active_power_w"] == 2500.0
    assert result["telemetry"]["battery_soc"] == 70.0


@pytest.mark.asyncio
async def test_bluesun_battery_bms_branch():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bat_pack_01",
        branch=BluesunBranch.ESS_BATTERY,
        serial_number="BSBAT4810001",
        bms_pack_id=1,
    )
    raw_bms = {
        "pack_voltage_v": 53.1,
        "pack_current_a": 20.0,
        "soc": 80.0,
        "soh": 99.0,
        "temp_c": 28.0,
        "cell_voltages_v": [3.318] * 16,
        "cycle_count": 150,
    }
    result = await adapter.read_telemetry(config, raw_data=raw_bms)
    assert result["branch"] == "ess_battery"
    assert result["chemistry"] == "LiFePO4"
    assert result["telemetry"]["nominal_voltage_v"] == 51.2
    assert result["telemetry"]["max_continuous_c_rate"] == 0.5
    assert result["telemetry"]["cell_voltages_v"] == [3.318] * 16


@pytest.mark.asyncio
async def test_bluesun_write_safeguard_lock():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bsm_inv_01",
        branch=BluesunBranch.BSM_OFFGRID,
        serial_number="BSM5500A1234",
    )
    with pytest.raises(PermissionError) as exc_info:
        await adapter.write_parameter(config, register=100, value=50)
    assert "Remote control write locked" in str(exc_info.value)
