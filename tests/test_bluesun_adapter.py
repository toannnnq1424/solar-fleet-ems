"""Tests for Bluesun Multi-Platform Adapter (BSM, BSE, Battery BMS)."""

import pytest
from solar_fleet.adapters.bluesun_adapter import (
    BluesunAdapter,
    BluesunBranch,
    BluesunDeviceConfig,
)


@pytest.mark.asyncio
async def test_bluesun_bsm_branch_routing():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bsm_inv_01",
        branch=BluesunBranch.BSM_OFFGRID,
        serial_number="BSM5500A1234",
        modbus_slave_id=1,
    )
    result = await adapter.read_telemetry(config)
    assert result["branch"] == "bsm_offgrid"
    assert result["status"] == "ok"
    assert result["inverter_mode"] == "solar_first"
    assert "battery_soc" in result["telemetry"]
    assert result["telemetry"]["battery_soc"] == 88.0


@pytest.mark.asyncio
async def test_bluesun_bse_branch_routing():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bse_inv_02",
        branch=BluesunBranch.BSE_HYBRID,
        serial_number="BSE6KL19876",
        cloud_station_id="station_bse_01",
    )
    result = await adapter.read_telemetry(config)
    assert result["branch"] == "bse_hybrid"
    assert result["status"] == "ok"
    assert result["feed_in_limiter_enabled"] is True
    assert result["telemetry"]["grid_active_power_w"] == 3500.0


@pytest.mark.asyncio
async def test_bluesun_battery_bms_branch():
    adapter = BluesunAdapter()
    config = BluesunDeviceConfig(
        device_id="bat_pack_01",
        branch=BluesunBranch.ESS_BATTERY,
        serial_number="BSBAT4810001",
        bms_pack_id=1,
    )
    result = await adapter.read_telemetry(config)
    assert result["branch"] == "ess_battery"
    assert result["chemistry"] == "LiFePO4"
    assert result["telemetry"]["nominal_voltage_v"] == 51.2
    assert result["telemetry"]["max_continuous_c_rate"] == 0.5
    assert len(result["telemetry"]["cell_voltages_v"]) == 16


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
