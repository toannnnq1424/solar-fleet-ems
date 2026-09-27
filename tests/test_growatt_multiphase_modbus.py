"""Unit and contract tests for Growatt Multi-Phase (SPH & SPH TL3) Modbus Protocol.

Validates:
- DTC and Tracker/Phase identification (1-phase SPH vs 3-phase SPH TL3)
- ASCII serial number and firmware version decoding
- Time window encoding and decoding (hour in high byte, minute in low byte)
- 112-bit comprehensive fault and warning classification
- 1-phase and 3-phase telemetry normalization to Solar Fleet EMS schema
- Export limitation (zero feed-in) compilation (Regs 122 & 123)
- Grid First & Battery First 3-window schedule compilers with AC charge toggle
- Modbus block planning with gap tolerance
"""

from __future__ import annotations

import pytest

from solar_fleet.growatt_multiphase_modbus import (
    REG_AC_CHARGE_ENABLE,
    REG_BATTERY_FIRST_RATE,
    REG_BATTERY_FIRST_STOP_SOC,
    REG_EXPORT_LIMIT_ENABLE,
    REG_EXPORT_LIMIT_RATE,
    REG_GRID_FIRST_RATE,
    REG_GRID_FIRST_STOP_SOC,
    compile_battery_first_window_command,
    compile_export_limitation_command,
    compile_grid_first_window_command,
    decode_ascii_registers,
    decode_fault_registers,
    decode_growatt_identification,
    decode_growatt_multiphase_telemetry,
    decode_time_window,
    encode_time_value,
    parse_tracker_phase,
    plan_growatt_modbus_blocks,
)


def test_tracker_phase_parsing():
    """Verify holding register 44 bitfield splitting into tracker and phase counts."""
    # 0x0201: 2 trackers, 1 phase output
    t1, p1 = parse_tracker_phase(0x0201)
    assert t1 == 2
    assert p1 == 1

    # 0x0203: 2 trackers, 3 phase output (SPH TL3)
    t3, p3 = parse_tracker_phase(0x0203)
    assert t3 == 2
    assert p3 == 3


def test_ascii_registers_decoder():
    """Verify big-endian ASCII word decoding."""
    # "SPH4600001" in 5 registers (10 bytes)
    # 'S'=0x53, 'P'=0x50 -> 0x5350
    # 'H'=0x48, '4'=0x34 -> 0x4834
    # '6'=0x36, '0'=0x30 -> 0x3630
    # '0'=0x30, '0'=0x30 -> 0x3030
    # '0'=0x30, '1'=0x31 -> 0x3031
    regs = {
        23: 0x5350,
        24: 0x4834,
        25: 0x3630,
        26: 0x3030,
        27: 0x3031,
    }
    serial = decode_ascii_registers(regs, 23, 5)
    assert serial == "SPH4600001"


def test_time_encoding_and_window_decoding():
    """Verify (hour << 8 | min) time representation and time window decoding."""
    # "08:30" -> (8 << 8) | 30 = 2048 + 30 = 2078
    encoded = encode_time_value("08:30")
    assert encoded == 2078

    # "23:59" -> (23 << 8) | 59 = 5888 + 59 = 5947
    assert encode_time_value("23:59") == 5947

    with pytest.raises(ValueError):
        encode_time_value("24:00")
    with pytest.raises(ValueError):
        encode_time_value("12:60")

    # Decode window: Start 08:30, Stop 14:15, Enabled = 1
    start_val = encode_time_value("08:30")
    stop_val = encode_time_value("14:15")
    win = decode_time_window(start_val, stop_val, 1, 1, "Battery First 1")
    assert win.start_time == "08:30"
    assert win.stop_time == "14:15"
    assert win.enabled is True


def test_fault_registers_classification():
    """Verify decoding 112 fault bits into CRITICAL faults vs non-critical WARNINGs."""
    input_regs = {
        1001: 0x0001,  # Bit 0 = MasterForceINVFault (CRITICAL)
        1005: 0x0020,  # Bit 5 = PV1_VoltLowWarn (WARNING)
        1007: 0x0100,  # Bit 8 = BoostDriver1Warn (WARNING)
    }
    alarms = decode_fault_registers(input_regs)
    assert len(alarms) == 3

    a_crit = next(a for a in alarms if a.code == "MasterForceINVFault")
    assert a_crit.severity == "CRITICAL"
    assert a_crit.register == 1001

    a_warn1 = next(a for a in alarms if a.code == "PV1_VoltLowWarn")
    assert a_warn1.severity == "WARNING"

    a_warn2 = next(a for a in alarms if a.code == "BoostDriver1Warn")
    assert a_warn2.severity == "WARNING"


def test_growatt_identification():
    """Verify device profile resolution (sph vs sph_tl3)."""
    # 1-phase inverter
    regs_1p = {
        43: 15,
        44: 0x0201,  # 1-phase
        23: 0x5350,
        24: 0x4831,
    }
    ident_1p = decode_growatt_identification(regs_1p)
    assert ident_1p.profile_key == "sph"
    assert ident_1p.phase_count == 1
    assert ident_1p.tracker_count == 2

    # 3-phase inverter SPH TL3
    regs_3p = {
        43: 18,
        44: 0x0203,  # 3-phase
        23: 0x544C,
        24: 0x3331,
    }
    ident_3p = decode_growatt_identification(regs_3p)
    assert ident_3p.profile_key == "sph_tl3"
    assert ident_3p.phase_count == 3


def test_decode_growatt_multiphase_telemetry_3phase():
    """Verify 3-phase SPH TL3 telemetry decoding and normalization."""
    holding_regs = {
        43: 20,
        44: 0x0203,  # 3-phase
        23: 0x544C,
        24: 0x3330,  # Serial "TL30"
        122: 1,      # Export limitation enabled
        123: 500,    # 50.0% export limit rate
        608: 20,     # Discharge SOC min 20%
        1070: 80,    # Grid first rate 80%
        1071: 15,    # Grid first stop SOC 15%
        1080: encode_time_value("01:00"),
        1081: encode_time_value("05:00"),
        1082: 1,     # Grid first window 1 enabled
        1090: 90,    # Battery first rate 90%
        1091: 100,   # Battery first stop SOC 100%
        1092: 1,     # AC charge enabled
        1100: encode_time_value("22:00"),
        1101: encode_time_value("06:00"),
        1102: 1,     # Battery first window 1 enabled
    }

    input_regs = {
        0: 1,         # Status Normal
        1000: 5,      # PV + Battery Online
        1: 0, 2: 45000, # PV power 4500.0 W (u32: hi=0, lo=45000)
        3: 3500,      # PV1 voltage 350.0 V
        7: 3600,      # PV2 voltage 360.0 V
        38: 2300,     # L1 voltage 230.0 V
        40: 0, 41: 15000, # L1 power 1500.0 W
        42: 2310,     # L2 voltage 231.0 V
        44: 0, 45: 14800, # L2 power 1480.0 W
        46: 2295,     # L3 voltage 229.5 V
        48: 0, 49: 15200, # L3 power 1520.0 W
        1013: 524,    # Bat voltage 52.4 V
        1014: 250,    # Bat current 25.0 A
        1009: 1310,   # Bat power 1310 W
        1017: 85,     # Bat SOC 85%
        1037: 0, 1038: 12000, # Load power 1200.0 W
    }

    tel = decode_growatt_multiphase_telemetry(input_regs, holding_regs)
    assert tel["vendor"] == "Growatt"
    assert tel["profile"] == "sph_tl3"
    assert tel["phase_count"] == 3
    assert tel["power_flow"]["solar_power_w"] == 4500.0
    assert tel["power_flow"]["grid_power_w"] == 4500.0  # 1500 + 1480 + 1520
    assert tel["grid"]["voltage_l1_v"] == 230.0
    assert tel["grid"]["voltage_l2_v"] == 231.0
    assert tel["grid"]["voltage_l3_v"] == 229.5
    assert tel["battery"]["soc_percent"] == 85
    assert tel["export_limitation"]["enabled"] is True
    assert tel["export_limitation"]["rate_percent"] == 50.0
    assert tel["tou_schedule"]["ac_charge_enabled"] is True
    assert len(tel["tou_schedule"]["grid_first_windows"]) == 3


def test_command_compilers():
    """Verify holding register mappings for Export Limitation and TOU windows."""
    # 1. Export limitation
    cmd_exp = compile_export_limitation_command(enable=True, limit_rate_pct=75.5)
    assert cmd_exp["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd_exp["registers"][REG_EXPORT_LIMIT_ENABLE] == 1
    assert cmd_exp["registers"][REG_EXPORT_LIMIT_RATE] == 755  # 75.5 * 10

    # 2. Grid first window 1
    cmd_gf = compile_grid_first_window_command(
        window_index=1,
        start_time="02:00",
        stop_time="06:00",
        enable=True,
        discharge_rate_pct=80,
        stop_soc_pct=20,
    )
    assert cmd_gf["registers"][1080] == encode_time_value("02:00")
    assert cmd_gf["registers"][1081] == encode_time_value("06:00")
    assert cmd_gf["registers"][1082] == 1
    assert cmd_gf["registers"][REG_GRID_FIRST_RATE] == 80
    assert cmd_gf["registers"][REG_GRID_FIRST_STOP_SOC] == 20

    # 3. Battery first window 2 with AC charging
    cmd_bf = compile_battery_first_window_command(
        window_index=2,
        start_time="10:00",
        stop_time="14:00",
        enable=True,
        ac_charge_enable=True,
        charge_rate_pct=100,
        stop_soc_pct=95,
    )
    assert cmd_bf["registers"][1103] == encode_time_value("10:00")
    assert cmd_bf["registers"][1104] == encode_time_value("14:00")
    assert cmd_bf["registers"][1105] == 1
    assert cmd_bf["registers"][REG_AC_CHARGE_ENABLE] == 1
    assert cmd_bf["registers"][REG_BATTERY_FIRST_RATE] == 100
    assert cmd_bf["registers"][REG_BATTERY_FIRST_STOP_SOC] == 95


def test_modbus_block_optimizer():
    """Verify gap-tolerant block merging."""
    # Addresses: 1, 3, 5, 7, 38, 40, 1000
    addrs = [1, 3, 5, 7, 38, 40, 1000]
    blocks = plan_growatt_modbus_blocks(addrs, max_gap=30, max_block=110)
    # [1, 3, 5, 7, 38, 40] -> max gap between 7 and 38 is 31 (>30), so splits!
    # Block 1: 1..7 (start 1, count 7)
    # Block 2: 38..40 (start 38, count 3)
    # Block 3: 1000 (start 1000, count 1)
    assert len(blocks) == 3
    assert blocks[0] == (1, 7)
    assert blocks[1] == (38, 3)
    assert blocks[2] == (1000, 1)


# ---------------------------------------------------------------------------
# Phase D REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_growatt_multiphase_decode_telemetry(local):
    """Verify POST /api/growatt-multiphase/decode-telemetry."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-multiphase/decode-telemetry",
        json={
            "input_registers": {"1": 0, "2": 25000, "38": 2300, "1017": 75},
            "holding_registers": {"43": 15, "44": 513, "23": 21328, "122": 1, "123": 800},
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "ha-growatt-modbus" in data["source"]
    assert data["telemetry"]["vendor"] == "Growatt"
    assert data["telemetry"]["power_flow"]["solar_power_w"] == 2500.0
    assert data["telemetry"]["export_limitation"]["rate_percent"] == 80.0


def test_api_growatt_multiphase_compile_export_limit(local):
    """Verify POST /api/growatt-multiphase/compile-export-limit."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-multiphase/compile-export-limit",
        json={"enable": True, "limit_rate_percent": 65.5},
        headers=headers,
    )
    assert resp.status_code == 200
    cmd = resp.json()["command"]
    assert cmd["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd["registers"]["122"] == 1
    assert cmd["registers"]["123"] == 655


def test_api_growatt_multiphase_compile_window(local):
    """Verify POST /api/growatt-multiphase/compile-window."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-multiphase/compile-window",
        json={
            "window_type": "battery_first",
            "window_index": 1,
            "start_time": "01:30",
            "stop_time": "05:45",
            "enable": True,
            "rate_percent": 90,
            "stop_soc_percent": 95,
            "ac_charge_enable": True,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    cmd = resp.json()["command"]
    assert cmd["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert cmd["registers"]["1100"] == encode_time_value("01:30")
    assert cmd["registers"]["1101"] == encode_time_value("05:45")
    assert cmd["registers"]["1102"] == 1
    assert cmd["registers"][str(REG_AC_CHARGE_ENABLE)] == 1


def test_api_growatt_multiphase_decode_faults(local):
    """Verify POST /api/growatt-multiphase/decode-faults."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/growatt-multiphase/decode-faults",
        json={"fault_registers": {"1001": 1, "1005": 32}},
        headers=headers,
    )
    assert resp.status_code == 200
    alarms = resp.json()["alarms"]
    assert len(alarms) == 2
    assert any(a["code"] == "MasterForceINVFault" and a["severity"] == "CRITICAL" for a in alarms)
    assert any(a["code"] == "PV1_VoltLowWarn" and a["severity"] == "WARNING" for a in alarms)

