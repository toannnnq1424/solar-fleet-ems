"""Tests for Sungrow SHx & SG Modbus TCP Client and Protocol Engine."""

import pytest

from src.solar_fleet.sungrow_shx_client import (
    DEFAULT_SLAVE_UNIT_ID,
    SUNGROW_DEVICE_TYPES,
    SUNGROW_FORCED_CMDS,
    SUNGROW_RUNNING_STATES,
    SUNGROW_TOGGLE_OFF,
    SUNGROW_TOGGLE_ON,
    SungrowShxClient,
    build_modbus_rtu_frame,
    calculate_modbus_crc,
    compile_sungrow_active_power_limitation,
    compile_sungrow_battery_soc_limits,
    compile_sungrow_ems_mode,
    compile_sungrow_ems_scene,
    compile_sungrow_export_limit,
    compile_sungrow_forced_charge_discharge,
    compile_sungrow_inverter_power_switch,
    decode_sungrow_s16,
    decode_sungrow_s32,
    decode_sungrow_telemetry,
    decode_sungrow_u32,
    normalize_sungrow_telemetry,
)


def test_modbus_crc16_and_frame_builder():
    """Verify standard Modbus CRC16 and RTU frame synthesis."""
    frame = build_modbus_rtu_frame(DEFAULT_SLAVE_UNIT_ID, 0x06, 13049, 2)
    assert len(frame) == 8  # 1 unit, 1 fn, 2 addr, 2 val, 2 crc
    crc = calculate_modbus_crc(frame[:-2])
    assert frame[-2:] == crc.to_bytes(2, "little")


def test_sungrow_word_swap_decoders():
    """Test 32-bit little-endian word / big-endian byte decoding."""
    # Value: 123456972 -> Hex 0x075BCDCC -> Low word: 0xCDCC (52684), High word: 0x075B (1883)
    regs = {5000: 52684, 5001: 1883}
    assert decode_sungrow_u32(regs, 5000) == 123456972
    assert decode_sungrow_s32(regs, 5000) == 123456972

    # Negative 32-bit signed: -2500 -> 0xFFFF F63C -> Low word: 0xF63C (63036), High word: 0xFFFF (65535)
    regs_neg = {5010: 63036, 5011: 65535}
    assert decode_sungrow_s32(regs_neg, 5010) == -2500

    # Signed 16-bit
    assert decode_sungrow_s16({100: 65535}, 100) == -1
    assert decode_sungrow_s16({100: 32767}, 100) == 32767
    assert decode_sungrow_s16({100: 32768}, 100) == -32768


def test_sungrow_device_model_and_running_states():
    """Verify known Sungrow models and operating states."""
    assert SUNGROW_DEVICE_TYPES[0x0E03] == "SH10RT"
    assert SUNGROW_DEVICE_TYPES[0x0E13] == "SH10RT-20"
    assert SUNGROW_DEVICE_TYPES[0x0E23] == "SH10T"
    assert SUNGROW_DEVICE_TYPES[0x0D09] == "SH5K-20"

    assert SUNGROW_RUNNING_STATES[0x0000] == "Running"
    assert SUNGROW_RUNNING_STATES[0x0100] == "Fault"
    assert SUNGROW_RUNNING_STATES[0x4000] == "Running in External EMS Mode"


def test_decode_sungrow_telemetry_sh10rt():
    """Test full telemetry decoder with simulated SH10RT + SBR096 pack fixtures."""
    client = SungrowShxClient(simulated=True)
    regs_5000, regs_13000, sbr_regs = client.get_simulated_fixtures()

    telemetry = decode_sungrow_telemetry(
        regs_5000=regs_5000,
        regs_13000=regs_13000,
        sbr_regs=sbr_regs,
        serial_str="SH10RT-DEMO-001",
    )

    assert telemetry.model_name == "SH10RT"
    assert telemetry.running_state == "Running"
    assert telemetry.total_dc_power_w == 8667.0
    assert len(telemetry.mppt_voltages) >= 2
    assert telemetry.mppt_voltages[0] == 520.0
    assert telemetry.mppt_voltages[1] == 518.0

    # 3-Phase Grid
    assert telemetry.grid_phase_a_v == 231.5
    assert telemetry.grid_phase_b_v == 230.8
    assert telemetry.grid_phase_c_v == 232.1
    assert telemetry.grid_active_power_w == 6817.0
    assert telemetry.grid_freq_hz == 50.02

    # Meter & Battery
    assert telemetry.meter_active_power_w == 2500.0
    assert telemetry.load_power_w == 4317.0
    assert telemetry.export_power_w == 2500.0
    assert telemetry.battery_power_w == 1850.0
    assert telemetry.battery_soc_pct == 78.5
    assert telemetry.battery_soh_pct == 98.0
    assert telemetry.battery_temp_c == 26.5

    # SBR Pack details
    assert telemetry.sbr_cell_max_mv == 3345.0
    assert telemetry.sbr_cell_min_mv == 3328.0
    assert telemetry.sbr_module_max_temp_c == 27.2

    # Energies
    assert telemetry.daily_pv_kwh == 22.0
    assert telemetry.total_pv_kwh == 1450.0
    assert telemetry.daily_battery_charge_kwh == 12.5
    assert telemetry.daily_battery_discharge_kwh == 4.2
    assert telemetry.daily_export_kwh == 15.2


def test_compile_sungrow_ems_mode():
    """Verify EMS mode compilation and safety gating."""
    # Self-consumption
    res = compile_sungrow_ems_mode("self_consumption")
    assert res["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res["register"] == 13049
    assert res["value"] == 0

    # Forced mode
    res2 = compile_sungrow_ems_mode("forced")
    assert res2["value"] == 2

    # External EMS mode
    res3 = compile_sungrow_ems_mode("external_ems")
    assert res3["value"] == 3

    # Invalid mode
    with pytest.raises(ValueError, match="Unknown EMS mode"):
        compile_sungrow_ems_mode("ultra_mode")


def test_compile_sungrow_forced_charge_discharge():
    """Verify forced charge/discharge compiler and power constraints."""
    res_chg = compile_sungrow_forced_charge_discharge("forced_charge", power_w=6500)
    assert res_chg["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res_chg["registers"][13050] == SUNGROW_FORCED_CMDS["forced_charge"][0]
    assert res_chg["registers"][13051] == 6500

    res_stop = compile_sungrow_forced_charge_discharge("stop", power_w=0)
    assert res_stop["registers"][13050] == 0xCC

    with pytest.raises(ValueError, match="Forced charge/discharge power out of valid range"):
        compile_sungrow_forced_charge_discharge("forced_charge", power_w=40000)


def test_compile_sungrow_battery_soc_limits():
    """Verify battery max and min SOC limits with range checking."""
    res = compile_sungrow_battery_soc_limits(max_soc_pct=95.0, min_soc_pct=15.0)
    assert res["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res["registers"][13057] == 950  # 95.0% -> 950
    assert res["registers"][13058] == 150  # 15.0% -> 150

    # Range violations
    with pytest.raises(ValueError, match="Min SOC .* must be strictly lower than Max SOC"):
        compile_sungrow_battery_soc_limits(max_soc_pct=50.0, min_soc_pct=50.0)

    with pytest.raises(ValueError, match="Battery min SOC out of range"):
        compile_sungrow_battery_soc_limits(max_soc_pct=90.0, min_soc_pct=60.0)


def test_compile_sungrow_export_limit_and_active_power():
    """Verify export feed-in limitation and active derating compilers."""
    # Export limit
    res_exp = compile_sungrow_export_limit(enabled=True, limit_w=5000)
    assert res_exp["registers"][13086] == SUNGROW_TOGGLE_ON
    assert res_exp["registers"][13073] == 5000

    res_dis = compile_sungrow_export_limit(enabled=False, limit_w=0)
    assert res_dis["registers"][13086] == SUNGROW_TOGGLE_OFF

    # Active power derating
    res_der = compile_sungrow_active_power_limitation(enabled=True, ratio_pct=75.5)
    assert res_der["registers"][13088] == SUNGROW_TOGGLE_ON
    assert res_der["registers"][13089] == 755  # 75.5% * 10


def test_compile_sungrow_power_switch_and_scenes():
    """Verify power switch and pre-configured EMS scenes."""
    # Start / Stop
    res_start = compile_sungrow_inverter_power_switch(start=True)
    assert res_start["register"] == 12999
    assert res_start["value"] == 0xCF

    res_stop = compile_sungrow_inverter_power_switch(start=False)
    assert res_stop["value"] == 0xCE

    # Scenes
    scene_self = compile_sungrow_ems_scene("self_consumption")
    assert scene_self["registers"][13049] == 0
    assert scene_self["registers"][13050] == 0xCC

    scene_zero = compile_sungrow_ems_scene("zero_export")
    assert scene_zero["registers"][13086] == SUNGROW_TOGGLE_ON
    assert scene_zero["registers"][13073] == 0

    scene_chg = compile_sungrow_ems_scene("forced_charge", power_w=8000)
    assert scene_chg["registers"][13049] == 2
    assert scene_chg["registers"][13050] == 0xAA
    assert scene_chg["registers"][13051] == 8000


def test_sungrow_client_safety_gates_and_normalization():
    """Test client operation, acceptance verification requirement, and schema normalizer."""
    client = SungrowShxClient(host="192.168.1.150", port=502, simulated=True)
    assert client.connect() is True

    telemetry = client.read_telemetry()
    assert telemetry.model_name == "SH10RT"

    normalized = normalize_sungrow_telemetry(telemetry)
    assert normalized["vendor"] == "Sungrow"
    assert normalized["model"] == "SH10RT"
    assert normalized["safety_status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert "pv_power_w" in normalized["solar"]
    assert "active_power_w" in normalized["grid"]
    assert "pcc_active_power_w" in normalized["meter"]
    assert "soc_pct" in normalized["battery"]

    # Parameter write without confirmation -> strictly locked
    unconfirmed = client.write_parameter(
        command_type="forced_charge_discharge",
        params={"cmd": "forced_charge", "power_w": 5000},
        confirm_hardware_acceptance=False,
    )
    assert unconfirmed["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert unconfirmed["executed"] is False

    # Parameter write with confirmation -> allowed in simulation
    confirmed = client.write_parameter(
        command_type="forced_charge_discharge",
        params={"cmd": "forced_charge", "power_w": 5000},
        confirm_hardware_acceptance=True,
    )
    assert confirmed["status"] == "SIMULATED_WRITE_COMPLETED"
    assert confirmed["executed"] is True
    assert client._sim_holding_registers[13050] == 0xAA
    assert client._sim_holding_registers[13051] == 5000

    client.disconnect()
    assert client.connected is False


def test_api_sungrow_shx_endpoints(local):
    """Verify REST API endpoints for Sungrow SHx/SG inverter protocol engine."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # 1. Info endpoint
    resp_info = client.get("/api/sungrow-shx/info", headers=headers)
    assert resp_info.status_code == 200
    d_info = resp_info.json()
    assert "Sungrow-SHx-Inverter-Modbus-Home-Assistant" in d_info["source"]
    assert len(d_info["supported_models"]) >= 10
    assert len(d_info["scenes"]) >= 5

    # 2. Telemetry endpoint
    resp_tel = client.post(
        "/api/sungrow-shx/telemetry",
        json={"host": "192.168.1.100", "port": 502, "slave_unit_id": 1},
        headers=headers,
    )
    assert resp_tel.status_code == 200
    d_tel = resp_tel.json()
    assert d_tel["telemetry"]["model_name"] == "SH10RT"
    assert d_tel["normalized"]["vendor"] == "Sungrow"
    assert d_tel["normalized"]["battery"]["soc_pct"] == 78.5

    # 3. Command endpoint with hardware acceptance lock
    resp_cmd = client.post(
        "/api/sungrow-shx/command",
        json={
            "command_type": "scene",
            "params": {"scene_name": "zero_export"},
            "unlocked": False,
        },
        headers=headers,
    )
    assert resp_cmd.status_code == 200
    d_cmd = resp_cmd.json()
    assert d_cmd["result"]["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert d_cmd["result"]["executed"] is False

    # 4. Command endpoint with confirmation in simulation
    resp_cmd2 = client.post(
        "/api/sungrow-shx/command",
        json={
            "command_type": "scene",
            "params": {"scene_name": "zero_export"},
            "unlocked": True,
        },
        headers=headers,
    )
    assert resp_cmd2.status_code == 200
    d_cmd2 = resp_cmd2.json()
    assert d_cmd2["result"]["status"] == "SIMULATED_WRITE_COMPLETED"
    assert d_cmd2["result"]["executed"] is True

