"""Unit and contract tests for GoodWe Local Client and Protocol Engine.

Validates:
- Modbus RTU-over-UDP CRC16 calculation and request/response validation
- AA55 frame codec for single-phase hybrid inverters
- GoodWe ET 3-phase hybrid telemetry decoding (PV, 3-phase grid, backup, BMS, meter)
- Telemetry normalization to Solar Fleet EMS schema
- Parameter write compilers (Operation Mode, Export Limitation, Battery Cutoff, Eco Mode TOU)
- Bounds enforcement and hardware acceptance safety gates
- GoodWeLocalClient simulation and API endpoints
"""

from __future__ import annotations

import pytest

from solar_fleet.goodwe_local_client import (
    DEFAULT_COMM_ADDR,
    MODBUS_READ_CMD,
    GoodWeLocalClient,
    build_aa55_frame,
    build_modbus_rtu_request,
    calculate_modbus_crc16,
    compile_goodwe_battery_cutoff_soc,
    compile_goodwe_eco_mode_v1_window,
    compile_goodwe_export_limit,
    compile_goodwe_operation_mode,
    decode_et_telemetry_registers,
    normalize_goodwe_et_to_ems,
    validate_aa55_frame,
    validate_modbus_rtu_response,
)


def test_modbus_crc16_and_frame_codec():
    """Verify Modbus CRC16 calculation and RTU request/response validation."""
    # Test vector: [0xF7, 0x03, 0x89, 0x1C, 0x00, 0x7D] (read 125 regs from 35100)
    req = build_modbus_rtu_request(DEFAULT_COMM_ADDR, MODBUS_READ_CMD, 35100, 125)
    assert len(req) == 8
    assert req[0] == DEFAULT_COMM_ADDR
    assert req[1] == MODBUS_READ_CMD
    assert (req[2] << 8) | req[3] == 35100
    assert (req[4] << 8) | req[5] == 125

    # Checksum verification
    crc = calculate_modbus_crc16(req[:-2])
    assert req[-2] == (crc & 0xFF)
    assert req[-1] == ((crc >> 8) & 0xFF)

    # Simulated response: [0xF7, 0x03, 0x04, 0x12, 0x34, 0x56, 0x78, CRC_LO, CRC_HI]
    resp_body = bytes([DEFAULT_COMM_ADDR, MODBUS_READ_CMD, 0x04, 0x12, 0x34, 0x56, 0x78])
    resp_crc = calculate_modbus_crc16(resp_body)
    full_resp = resp_body + bytes([resp_crc & 0xFF, (resp_crc >> 8) & 0xFF])

    ok, payload = validate_modbus_rtu_response(full_resp, DEFAULT_COMM_ADDR, MODBUS_READ_CMD)
    assert ok is True
    assert payload == bytes([0x12, 0x34, 0x56, 0x78])

    # Corrupt response
    bad_resp = full_resp[:-1] + b"\x00"
    ok_bad, _ = validate_modbus_rtu_response(bad_resp, DEFAULT_COMM_ADDR, MODBUS_READ_CMD)
    assert ok_bad is False


def test_aa55_frame_codec():
    """Verify AA55 binary frame construction and validation."""
    cmd_code = 0x06  # Running data request
    payload = bytes([0x01, 0x02, 0x03])
    frame = build_aa55_frame(cmd_code, payload)
    assert frame[:2] == b"\xaa\x55"
    assert frame[4] == 0x06
    assert frame[5] == len(payload)

    valid, cmd, extracted = validate_aa55_frame(frame)
    assert valid is True
    assert cmd == 0x06
    assert extracted == payload


def test_decode_et_telemetry_and_normalization():
    """Verify GoodWe ET registers decoding and normalization to EMS schema."""
    regs = {
        35103: 3850,  # PV1 385.0 V
        35104: 120,   # PV1 12.0 A
        35105: 0, 35106: 4620,  # PV1 4620 W
        35107: 3800,  # PV2 380.0 V
        35108: 110,   # PV2 11.0 A
        35109: 0, 35110: 4180,  # PV2 4180 W
        35121: 2310,  # Grid L1 231.0 V
        35125: 2900,  # Grid L1 2900 W
        35126: 2300,  # Grid L2 230.0 V
        35130: 2950,  # Grid L2 2950 W
        35131: 2305,  # Grid L3 230.5 V
        35135: 2920,  # Grid L3 2920 W
        35138: 8770,  # Total grid active power
        35140: -1800, # Meter export 1800 W (negative)
        35145: 2300,  # Backup L1 230 V
        35151: 2300,  # Backup L2 230 V
        35157: 2300,  # Backup L3 230 V
        35170: 500,   # Backup load 500 W
        35172: 6970,  # Total home load
        35176: 410,   # Inverter temp 41.0 °C
        35180: 5240,  # Battery 524.0 V
        35181: -250,  # Battery charge current -25.0 A
        35182: 0, 35183: 1310,  # Battery power 1310 W
        35184: 3,     # Battery Mode: Charging
        35187: 1,     # Work Mode: Normal On-Grid
        35189: 0, 35190: 2,     # Bit 1: BMSWarning
        35191: 0, 35192: 150000,# Total PV 15000.0 kWh
        35193: 0, 35194: 425,   # Today PV 42.5 kWh
        35199: 210,   # Today export 21.0 kWh
        35202: 50,    # Today import 5.0 kWh
        35208: 140,   # Today battery charge 14.0 kWh
        35211: 90,    # Today battery discharge 9.0 kWh
        37003: 250,   # BMS temp 25.0 °C
        37007: 85,    # Battery SOC 85%
        37008: 99,    # Battery SOH 99%
    }

    tel = decode_et_telemetry_registers(regs, inverter_sn="GW10K-TEST", model_name="GW10K-ET")
    assert tel.inverter_sn == "GW10K-TEST"
    assert tel.pv_power_w == 8800.0  # 4620 + 4180
    assert tel.grid_total_power_w == 8770.0
    assert tel.meter_active_power_w == -1800.0
    assert tel.battery_soc_percent == 85
    assert tel.battery_voltage_v == 524.0
    assert len(tel.errors) == 1
    assert tel.errors[0]["code"] == "BMSWarning"

    # Normalize to EMS
    ems = normalize_goodwe_et_to_ems(tel)
    assert ems["vendor"] == "GoodWe"
    assert ems["serial_number"] == "GW10K-TEST"
    assert ems["power_flow"]["solar_power_w"] == 8800.0
    assert ems["power_flow"]["meter_power_w"] == -1800.0
    assert ems["grid"]["voltage_l1_v"] == 231.0
    assert ems["battery"]["soc_percent"] == 85


def test_goodwe_parameter_compilers():
    """Verify holding register compilers for Operation Mode, Export Limit, and Eco Mode."""
    # 1. Operation Mode
    cmd_mode = compile_goodwe_operation_mode("backup")
    assert cmd_mode["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_mode["register"] == 47000
    assert cmd_mode["value"] == 2
    assert "frame_hex" in cmd_mode

    with pytest.raises(ValueError):
        compile_goodwe_operation_mode("unsupported_mode")

    # 2. Export Limit
    cmd_exp = compile_goodwe_export_limit(enabled=True, limit_watts=6000)
    assert cmd_exp["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_exp["registers"][47509] == 1
    assert cmd_exp["registers"][47510] == 6000
    assert len(cmd_exp["frames_hex"]) == 2

    with pytest.raises(ValueError):
        compile_goodwe_export_limit(enabled=True, limit_watts=200000)

    # 3. Battery Cutoff SOC
    cmd_soc = compile_goodwe_battery_cutoff_soc(18)
    assert cmd_soc["register"] == 47500
    assert cmd_soc["value"] == 18

    with pytest.raises(ValueError):
        compile_goodwe_battery_cutoff_soc(5)

    # 4. Eco Mode V1 Window
    cmd_eco = compile_goodwe_eco_mode_v1_window(
        group_idx=1,
        start_time="02:30",
        stop_time="06:45",
        power_pct=80,
        enable=True,
    )
    assert cmd_eco["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_eco["group"] == 1
    assert cmd_eco["registers"][47515] == (2 << 8) | 30
    assert cmd_eco["registers"][47516] == (6 << 8) | 45
    assert cmd_eco["registers"][47517] == 80
    assert cmd_eco["registers"][47518] == (1 << 8)

    with pytest.raises(ValueError):
        compile_goodwe_eco_mode_v1_window(5, "00:00", "01:00", 50)


def test_goodwe_local_client_simulation_and_safety():
    """Verify GoodWeLocalClient simulation and safety gates."""
    client = GoodWeLocalClient(host="192.168.1.180", model_family="ET", simulated=True)

    # Poll telemetry
    ems = client.poll_telemetry()
    assert ems["vendor"] == "GoodWe"
    assert ems["serial_number"] == "GW10K-ET-1023"
    assert ems["power_flow"]["solar_power_w"] == 8117.0
    assert ems["battery"]["soc_percent"] == 88

    # Safety gate: locked by default
    res_locked = client.execute_command_safely("operation_mode", {"mode": "eco"}, unlocked=False)
    assert res_locked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # Safety gate: authorized
    res_unlocked = client.execute_command_safely("operation_mode", {"mode": "eco"}, unlocked=True)
    assert res_unlocked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res_unlocked["value"] == 3


def test_api_goodwe_local_telemetry(local):
    """Verify POST /api/goodwe-local/telemetry."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/goodwe-local/telemetry",
        json={"host": "192.168.1.180", "model_family": "ET"},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert data["source"] == "goodwe-master (MIT clean-room independent)"
    assert data["telemetry"]["vendor"] == "GoodWe"
    assert data["telemetry"]["battery"]["soc_percent"] == 88


def test_api_goodwe_local_command(local):
    """Verify POST /api/goodwe-local/command with safety gate."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # 1. Locked command
    resp_locked = client.post(
        "/api/goodwe-local/command",
        json={
            "command_type": "export_limit",
            "params": {"enabled": True, "limit_watts": 4500},
            "unlocked": False,
        },
        headers=headers,
    )
    assert resp_locked.status_code == 200
    res_data = resp_locked.json()["result"]
    assert res_data["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"

    # 2. Unlocked command compiles correctly
    resp_unlocked = client.post(
        "/api/goodwe-local/command",
        json={
            "command_type": "export_limit",
            "params": {"enabled": True, "limit_watts": 4500},
            "unlocked": True,
        },
        headers=headers,
    )
    assert resp_unlocked.status_code == 200
    res_unlocked_data = resp_unlocked.json()["result"]
    assert res_unlocked_data["registers"]["47510"] == 4500
