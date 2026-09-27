"""Unit and contract tests for Growatt SPH Hybrid Modbus & TOU Protocol Engine.

Derived from upstream project:
growatt_modbus-main (GPL-3.0 License) - Clean-room independently implemented.
"""

from __future__ import annotations

import pytest
from test_workspaces import login

from solar_fleet.growatt_sph_modbus import (
    GROWATT_BATT_FIRST_SLOTS,
    GROWATT_GRID_FIRST_SLOTS,
    GrowattSPHEngine,
    calculate_modbus_crc16,
    decode_sph_time,
    encode_sph_time,
)

# ---------------------------------------------------------------------------
# Unit Tests: Time Encoding & Slot Addresses
# ---------------------------------------------------------------------------

def test_sph_time_encoding_decoding():
    """Verify bidirectional time conversion (HH:MM <-> hour << 8 | minute)."""
    assert encode_sph_time("02:30") == 542  # 2 << 8 | 30 = 512 + 30 = 542
    assert decode_sph_time(542) == "02:30"

    assert encode_sph_time("00:00") == 0
    assert decode_sph_time(0) == "00:00"

    assert encode_sph_time("23:59") == (23 << 8) | 59
    assert decode_sph_time((23 << 8) | 59) == "23:59"

    # Already integer passes through
    assert encode_sph_time(542) == 542

    with pytest.raises(ValueError):
        encode_sph_time("24:00")
    with pytest.raises(ValueError):
        encode_sph_time("invalid_time")


def test_slot_addresses_empirical_offset():
    """Verify ground-truth address offsets (Battery First slots 4-6 start at reg 1018)."""
    # Slot 1: 1100..1102
    assert GROWATT_BATT_FIRST_SLOTS[0] == (1100, 1101, 1102)
    # Slot 3: 1106..1108
    assert GROWATT_BATT_FIRST_SLOTS[2] == (1106, 1107, 1108)
    # Slot 4: 1018..1020 (Empirical hardware offset!)
    assert GROWATT_BATT_FIRST_SLOTS[3] == (1018, 1019, 1020)
    # Slot 6: 1024..1026
    assert GROWATT_BATT_FIRST_SLOTS[5] == (1024, 1025, 1026)

    # Grid First slots
    assert GROWATT_GRID_FIRST_SLOTS[0] == (1080, 1081, 1082)
    assert GROWATT_GRID_FIRST_SLOTS[3] == (1027, 1028, 1029)


# ---------------------------------------------------------------------------
# Unit Tests: BMS Gauge & 12-Cell Decoders
# ---------------------------------------------------------------------------

def test_decode_bms_gauge():
    """Verify decoding of input registers 1083..1097 into BMS pack parameters."""
    regs = {
        1084: 195,    # Cycle count = 195
        1085: 35,     # SOC = 35%
        1086: 94,     # SOH = 94%
        1087: 5375,   # bmsVoltage = 53.75 V
        1088: 5500,   # bmsCurrent = +55.00 A (charging)
        1090: 17620,  # maxChargeCurrent = 176.20 A
        1091: 7540,   # remaining capacity = 75.40 Ah
        1092: 21580,  # FCC = 215.80 Ah
        1097: 5680,   # CV target = 56.80 V
    }

    gauge = GrowattSPHEngine.decode_bms_gauge(regs)
    assert gauge is not None
    assert gauge.voltage_v == 53.75
    assert gauge.current_a == 55.00
    assert gauge.max_charge_current_a == 176.20
    assert gauge.remaining_capacity_ah == 75.40
    assert gauge.full_charge_capacity_ah == 215.80
    assert gauge.cv_voltage_target_v == 56.80
    assert gauge.bms_soc_pct == 35.0
    assert gauge.bms_soh_pct == 94.0
    assert gauge.bms_cycle_count == 195

    # Test negative signed current (discharging)
    # -40.00 A = -4000 = 65536 - 4000 = 61536 (0xF060)
    regs_disch = dict(regs)
    regs_disch[1088] = 61536
    gauge_disch = GrowattSPHEngine.decode_bms_gauge(regs_disch)
    assert gauge_disch is not None
    assert gauge_disch.current_a == -40.00


def test_decode_cell_telemetry():
    """Verify decoding of input registers 1108..1123 into 12 cell voltages and envelope."""
    regs = {
        1108: 3358,  # maxCellVoltage = 3.358 V
        1109: 3346,  # minCellVoltage = 3.346 V
        1110: 2,     # moduleCount = 2
        1112: 3355, 1113: 3358, 1114: 3350, 1115: 3352,
        1116: 3348, 1117: 3346, 1118: 3354, 1119: 3351,
        1120: 3353, 1121: 3349, 1122: 3356, 1123: 3352,
    }

    cells = GrowattSPHEngine.decode_cell_telemetry(regs)
    assert cells is not None
    assert cells.max_cell_v == 3.358
    assert cells.min_cell_v == 3.346
    assert cells.delta_cell_mv == 12.0
    assert cells.module_count == 2
    assert len(cells.cell_voltages_mv) == 12
    assert cells.cell_voltages_mv[0] == 3355
    assert cells.cell_voltages_mv[1] == 3358  # Max
    assert cells.cell_voltages_mv[5] == 3346  # Min


def test_decode_tou_slots():
    """Verify decoding of holding registers into 12 TOU slots."""
    holding = {
        # BF Slot 1: 00:00 - 04:00, enabled
        1100: encode_sph_time("00:00"), 1101: encode_sph_time("04:00"), 1102: 1,
        # BF Slot 6: 02:30 - 04:30, enabled
        1024: encode_sph_time("02:30"), 1025: encode_sph_time("04:30"), 1026: 1,
        # GF Slot 1: 17:00 - 19:00, enabled
        1080: encode_sph_time("17:00"), 1081: encode_sph_time("19:00"), 1082: 1,
    }

    res = GrowattSPHEngine.decode_tou_slots(holding)
    assert res["total_slots_decoded"] == 3
    bf_slots = res["battery_first_slots"]
    gf_slots = res["grid_first_slots"]

    assert any(s["slot_number"] == 1 and s["start_time"] == "00:00" and s["end_time"] == "04:00" and s["enabled"] for s in bf_slots)
    assert any(s["slot_number"] == 6 and s["start_time"] == "02:30" and s["end_time"] == "04:30" and s["enabled"] for s in bf_slots)
    assert any(s["slot_number"] == 1 and s["start_time"] == "17:00" and s["end_time"] == "19:00" and s["enabled"] for s in gf_slots)


# ---------------------------------------------------------------------------
# Unit Tests: Command Compilers
# ---------------------------------------------------------------------------

def test_compile_load_first_mode():
    """Verify compilation of Load First mode disabling BF slot 6 and GF slot 1."""
    cmds = GrowattSPHEngine.compile_load_first_mode(slave_id=1)
    assert len(cmds) == 2

    cmd_bf = cmds[0]
    assert cmd_bf.function_code == 6
    assert cmd_bf.register_address == 1026
    assert cmd_bf.raw_values == [0]
    assert cmd_bf.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert calculate_modbus_crc16(bytes(cmd_bf.wire_bytes)) == 0

    cmd_gf = cmds[1]
    assert cmd_gf.function_code == 6
    assert cmd_gf.register_address == 1082
    assert cmd_gf.raw_values == [0]
    assert calculate_modbus_crc16(bytes(cmd_gf.wire_bytes)) == 0


def test_compile_battery_first_slot():
    """Verify compilation of Battery First mode writing rates and programming slot."""
    cmds = GrowattSPHEngine.compile_battery_first_slot(
        slot_number=6,
        start_time="00:00",
        end_time="04:00",
        charge_rate_pct=100,
        stop_soc_pct=100,
        slave_id=1,
    )
    assert len(cmds) == 2

    # Command 1: write regs 1090..1092
    c1 = cmds[0]
    assert c1.function_code == 16
    assert c1.register_address == 1090
    assert c1.register_count == 3
    assert c1.raw_values == [100, 100, 1]
    assert calculate_modbus_crc16(bytes(c1.wire_bytes)) == 0

    # Command 2: write slot 6 (regs 1024..1026)
    c2 = cmds[1]
    assert c2.function_code == 16
    assert c2.register_address == 1024
    assert c2.register_count == 3
    assert c2.raw_values == [0, (4 << 8) | 0, 1]
    assert calculate_modbus_crc16(bytes(c2.wire_bytes)) == 0


def test_compile_grid_first_slot():
    """Verify compilation of Grid First mode writing rates and programming slot."""
    cmds = GrowattSPHEngine.compile_grid_first_slot(
        slot_number=1,
        start_time="17:00",
        end_time="19:00",
        discharge_rate_pct=80,
        stop_soc_floor_pct=30,
        slave_id=1,
        bypass_safety=True,
    )
    assert len(cmds) == 2

    # Command 1: write regs 1070..1071
    c1 = cmds[0]
    assert c1.function_code == 16
    assert c1.register_address == 1070
    assert c1.register_count == 2
    assert c1.raw_values == [80, 30]
    assert c1.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert calculate_modbus_crc16(bytes(c1.wire_bytes)) == 0

    # Command 2: write slot 1 (regs 1080..1082)
    c2 = cmds[1]
    assert c2.function_code == 16
    assert c2.register_address == 1080
    assert c2.register_count == 3
    assert c2.raw_values == [(17 << 8) | 0, (19 << 8) | 0, 1]
    assert calculate_modbus_crc16(bytes(c2.wire_bytes)) == 0


# ---------------------------------------------------------------------------
# Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_growatt_sph_routes(local):
    """Test REST API endpoints under /api/growatt-sph."""
    client, _ctl = local
    headers = login(local, "operator")

    # 1. Decode BMS
    res_bms = client.post(
        "/api/growatt-sph/decode-bms",
        json={"registers": {"1087": 5370, "1088": 5750, "1090": 17620, "1091": 6110, "1092": 21580, "1085": 28}},
        headers=headers,
    )
    assert res_bms.status_code == 200
    bms_data = res_bms.json()
    assert bms_data["bms_gauge"]["voltage_v"] == 53.70
    assert bms_data["bms_gauge"]["current_a"] == 57.50

    # 2. Decode Cells
    res_cells = client.post(
        "/api/growatt-sph/decode-cells",
        json={"registers": {"1108": 3358, "1109": 3346, "1110": 2, "1112": 3355, "1113": 3358}},
        headers=headers,
    )
    assert res_cells.status_code == 200
    cells_data = res_cells.json()
    assert cells_data["cell_telemetry"]["max_cell_v"] == 3.358
    assert cells_data["cell_telemetry"]["min_cell_v"] == 3.346
    assert cells_data["cell_telemetry"]["delta_cell_mv"] == 12.0

    # 3. Decode Slots
    res_slots = client.post(
        "/api/growatt-sph/decode-tou-slots",
        json={"holding_registers": {"1100": 0, "1101": 1024, "1102": 1}},
        headers=headers,
    )
    assert res_slots.status_code == 200
    slots_data = res_slots.json()
    assert slots_data["total_slots_decoded"] >= 1

    # 4. Compile Mode Commands
    # Load first
    res_lf = client.post(
        "/api/growatt-sph/compile-mode-command",
        json={"mode": "load_first"},
        headers=headers,
    )
    assert res_lf.status_code == 200
    lf_data = res_lf.json()
    assert lf_data["total_commands"] == 2

    # Battery first
    res_bf = client.post(
        "/api/growatt-sph/compile-mode-command",
        json={"mode": "battery_first", "slot_number": 6, "start_time": "00:00", "end_time": "04:00"},
        headers=headers,
    )
    assert res_bf.status_code == 200
    bf_data = res_bf.json()
    assert bf_data["total_commands"] == 2

    # Grid first
    res_gf = client.post(
        "/api/growatt-sph/compile-mode-command",
        json={"mode": "grid_first", "slot_number": 1, "start_time": "17:00", "end_time": "19:00"},
        headers=headers,
    )
    assert res_gf.status_code == 200
    gf_data = res_gf.json()
    assert gf_data["total_commands"] == 2
