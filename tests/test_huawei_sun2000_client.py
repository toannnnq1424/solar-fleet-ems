"""Tests for Huawei SUN2000 Inverter & LUNA2000 ESS Protocol Engine.

Validates clean-room independent Modbus TCP/RTU codec, telemetry decoders,
multi-string PV metrics, 3-phase grid, DTSU666-H smart meter, LUNA2000 ESS,
parameter write compilers, hardware acceptance safety gates, and REST APIs.
"""

import pytest

from solar_fleet.huawei_sun2000_client import (
    HuaweiSun2000Client,
    build_modbus_rtu_frame,
    build_modbus_tcp_header,
    calculate_modbus_crc16,
    compile_huawei_active_power_derating,
    compile_huawei_charge_from_grid,
    compile_huawei_cutoff_soc,
    compile_huawei_export_limit,
    compile_huawei_luna_tou_period,
    compile_huawei_storage_mode,
    decode_ascii_string,
    decode_sun2000_telemetry,
    normalize_huawei_to_ems,
)


def test_modbus_crc16_and_frame_builders():
    """Verify CRC-16 Modbus polynomial 0xA001 and frame building."""
    data = bytes([0x01, 0x03, 0x7D, 0x00, 0x00, 0x02])
    crc = calculate_modbus_crc16(data)
    assert isinstance(crc, int)

    # Frame builder RTU
    rtu = build_modbus_rtu_frame(1, 0x06, 40125, 1000)
    assert len(rtu) == 8
    assert rtu[0] == 1
    assert rtu[1] == 0x06

    # MBAP Header TCP
    mbap = build_modbus_tcp_header(1, 0, 6, 1)
    assert len(mbap) == 7
    assert mbap[6] == 1


def test_decode_ascii_string():
    """Verify decoding ASCII string from Modbus registers."""
    regs = [0x5355, 0x4E32, 0x3030, 0x302D]  # "SUN2000-"
    decoded = decode_ascii_string(regs)
    assert decoded == "SUN2000-"


def test_decode_sun2000_telemetry_and_normalizer():
    """Verify decoding full SUN2000, LUNA2000, and DTSU666-H registers."""
    mock_regs = {
        32089: 0x0200,  # On-Grid Normal
        32008: 0, 32009: 0,
        32087: 420,     # 42.0 °C
        # PV Strings
        32016: 4000, 32017: 1000,  # PV1: 400.0V, 10.00A -> 4000.0W
        32018: 3900, 32019: 1000,  # PV2: 390.0V, 10.00A -> 3900.0W
        32020: 0, 32021: 0,
        32022: 0, 32023: 0,
        32064: 0, 32065: 7900,     # DC Power 7900W
        # 3-Phase Grid Output
        32069: 2300, 32070: 2300, 32071: 2300,  # 230.0V each
        32072: 0, 32073: 11000,  # 11.000A
        32074: 0, 32075: 11000,
        32076: 0, 32077: 11000,
        32080: 0, 32081: 7500,   # Active Power 7500W
        32082: 0, 32083: 100,    # Reactive Power 100 var
        32084: 999,              # PF 0.999
        32085: 5000,             # 50.00 Hz
        32114: 0, 32115: 3500,   # Daily Yield 35.00 kWh
        32106: 0, 32107: 1200000, # Total Yield 12,000.00 kWh
        # DTSU666-H Meter
        37100: 1,
        37113: 0, 37114: 2000,   # Meter +2000W (Export)
        37119: 0, 37120: 1800,   # Export 18.00 kWh
        37121: 0, 37122: 350,    # Import 3.50 kWh
        # LUNA2000 Battery
        47000: 2,
        37762: 2,       # Running
        37760: 920,     # SOC 92.0%
        37765: 0, 37766: 1500,  # Charge 1500W
        37763: 4200,    # 420.0V
        37764: 36,      # 3.6A
        37015: 0, 37016: 1200,  # 12.00 kWh charge today
        37017: 0, 37018: 800,   # 8.00 kWh discharge today
        37780: 0, 37781: 250000,
        37782: 0, 37783: 210000,
    }

    tel = decode_sun2000_telemetry(mock_regs, model_name="SUN2000-10KTL-M1")
    assert tel.device_status == "On-Grid (Normal)"
    assert tel.inverter_temperature_c == 42.0
    assert len(tel.pv_strings) == 4
    assert tel.pv_strings[0].power_w == 4000.0
    assert tel.pv_strings[1].power_w == 3900.0
    assert tel.grid_active_power_w == 7500.0
    assert tel.grid_voltage_a_v == 230.0
    assert tel.grid_frequency_hz == 50.00
    assert tel.meter_online is True
    assert tel.meter_active_power_w == 2000.0
    # Home load = inverter active power - meter export = 7500 - 2000 = 5500 W
    assert tel.home_load_power_w == 5500.0
    assert tel.storage_model == "HUAWEI LUNA2000"
    assert tel.storage_status == "Running"
    assert tel.storage_soc_percent == 92.0
    assert tel.storage_power_w == 1500.0

    # Normalizer
    norm = normalize_huawei_to_ems(tel)
    assert norm["vendor"] == "Huawei"
    assert norm["protocol"] == "Huawei-SUN2000-Modbus-TCP"
    assert norm["power_flow"]["solar_power_w"] == 7900.0
    assert norm["power_flow"]["grid_power_w"] == 7500.0
    assert norm["power_flow"]["load_power_w"] == 5500.0
    assert norm["metrics"]["battery_soc_pct"] == 92


def test_huawei_control_compilers():
    """Verify parameter compilers and strict hardware acceptance gating."""
    # Active power derating
    derate = compile_huawei_active_power_derating(80.0)
    assert derate["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert derate["register"] == 40125
    assert derate["value"] == 800

    with pytest.raises(ValueError, match="out of range"):
        compile_huawei_active_power_derating(110.0)

    # Storage working mode
    mode = compile_huawei_storage_mode("time_of_use")
    assert mode["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert mode["register"] == 47004
    assert mode["value"] == 6

    with pytest.raises(ValueError, match="Invalid mode"):
        compile_huawei_storage_mode("unsupported_mode")

    # Export limit
    exp = compile_huawei_export_limit(6000)
    assert exp["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert exp["limit_watts"] == 6000

    with pytest.raises(ValueError, match="out of range"):
        compile_huawei_export_limit(-10)

    # Cutoff SOC
    cutoff = compile_huawei_cutoff_soc(95.0, 15.0)
    assert cutoff["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cutoff["registers"][47081] == 950
    assert cutoff["registers"][47082] == 150

    with pytest.raises(ValueError, match="out of range"):
        compile_huawei_cutoff_soc(40.0, 10.0)

    # Charge from grid
    cfg = compile_huawei_charge_from_grid(True)
    assert cfg["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cfg["value"] == 1

    # LUNA2000 TOU period
    tou = compile_huawei_luna_tou_period(1, "01:30", "05:00", action="charge", days_effective=0x7F)
    assert tou["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert tou["period_index"] == 1
    # 01:30 = 90 min, 05:00 = 300 min
    assert tou["registers"][47256] == 90
    assert tou["registers"][47257] == 300
    # charge_flag = 0, days = 0x7F -> (0 << 8) | 0x7F = 0x007F = 127
    assert tou["registers"][47258] == 127

    with pytest.raises(ValueError, match="earlier than stop"):
        compile_huawei_luna_tou_period(1, "06:00", "04:00")


def test_huawei_client_safety_gate():
    """Verify Huawei client enforces locked read-only safety gate."""
    client = HuaweiSun2000Client(simulated=True)
    res_locked = client.execute_command_safely("active_power_derating", {"percentage": 75.0}, unlocked=False)
    assert res_locked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert "gated behind hardware acceptance" in res_locked["message"]

    res_unlocked = client.execute_command_safely("active_power_derating", {"percentage": 75.0}, unlocked=True)
    assert res_unlocked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res_unlocked["value"] == 750


def test_api_huawei_sun2000_endpoints(local):
    """Verify REST API endpoints for Huawei SUN2000."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # Telemetry
    r_tel = client.post(
        "/api/huawei-sun2000/telemetry",
        json={"host": "192.168.200.1", "port": 502, "slave_unit_id": 1},
        headers=headers,
    )
    assert r_tel.status_code == 200
    data_tel = r_tel.json()
    assert "huawei-solar-lib" in data_tel["source"]
    assert data_tel["telemetry"]["vendor"] == "Huawei"
    assert data_tel["telemetry"]["model_type"] == "SUN2000-10KTL-M1"

    # Command gated
    r_cmd = client.post(
        "/api/huawei-sun2000/command",
        json={
            "host": "192.168.200.1",
            "port": 502,
            "slave_unit_id": 1,
            "command_type": "storage_mode",
            "params": {"mode": "self_consumption"},
            "unlocked": False,
        },
        headers=headers,
    )
    assert r_cmd.status_code == 200
    data_cmd = r_cmd.json()
    assert data_cmd["result"]["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
