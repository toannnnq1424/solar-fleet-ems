"""Unit and contract tests for Deye Three-Phase Low-Voltage Hybrid Modbus Engine.

Derived from upstream project:
deye-modbus-ha-main (MIT License) - Clean-room independently implemented.
"""

from __future__ import annotations

import pytest
from test_workspaces import login

from solar_fleet.deye_hybrid_modbus import (
    REG_GRID_CHARGE_CURRENT,
    REG_GRID_CHARGE_ENABLE,
    REG_MAX_SELL_POWER,
    REG_SOLAR_SELL,
    REG_TOU_CHARGE_SOURCE_START,
    REG_TOU_POWER_START,
    REG_TOU_SOC_START,
    REG_TOU_TIME_START,
    REG_WORK_MODE,
    WORK_MODE_SELLING_FIRST,
    DeyeHybridEngine,
    calculate_modbus_crc16,
    decode_deye_temp,
    decode_deye_time,
    decode_s16,
    decode_u32_le_words,
    encode_deye_time,
    encode_u32_le_words,
)

# ---------------------------------------------------------------------------
# Unit Tests: Primitive Encoders, Decoders & Word Order
# ---------------------------------------------------------------------------

def test_deye_time_encoding_and_decoding():
    """Verify bidirectional HH:MM <-> decimal HHMM conversion."""
    assert encode_deye_time("00:00") == 0
    assert decode_deye_time(0) == "00:00"

    assert encode_deye_time("02:30") == 230
    assert decode_deye_time(230) == "02:30"

    assert encode_deye_time("18:45") == 1845
    assert decode_deye_time(1845) == "18:45"

    assert encode_deye_time("23:59") == 2359
    assert decode_deye_time(2359) == "23:59"

    with pytest.raises(ValueError):
        encode_deye_time("24:00")
    with pytest.raises(ValueError):
        encode_deye_time("invalid")


def test_deye_u32_little_endian_words():
    """Verify 32-bit unsigned decoding with low word first (Deye convention)."""
    # 25400 low word, 0 high word -> 25400
    assert decode_u32_le_words(25400, 0) == 25400

    # 1000 low word, 2 high word -> 2 * 65536 + 1000 = 132072
    assert decode_u32_le_words(1000, 2) == 132072

    low, high = encode_u32_le_words(132072)
    assert (low, high) == (1000, 2)


def test_decode_s16_and_temp():
    """Verify 16-bit two's complement and temperature offset/scale."""
    assert decode_s16(0x0000) == 0
    assert decode_s16(500) == 500
    assert decode_s16(0xFFFF) == -1
    assert decode_s16(0xFFFE) == -2

    # Temperature: (raw - 1000) * 0.1
    assert decode_deye_temp(1250) == 25.0
    assert decode_deye_temp(1000) == 0.0
    assert decode_deye_temp(850) == -15.0


# ---------------------------------------------------------------------------
# Unit Tests: Telemetry & TOU Schedule Decoders
# ---------------------------------------------------------------------------

def test_deye_telemetry_decoder():
    """Verify normalization of full 68-parameter holding register dictionary."""
    regs = {
        500: 2,  # Normal
        672: 3000, 676: 4200, 677: 71,  # PV1: 3000W, 420.0V, 7.1A
        673: 2000, 678: 4100, 679: 49,  # PV2: 2000W, 410.0V, 4.9A
        587: 5120, 588: 80, 590: 1200, 591: 2340, 586: 1270, 592: 200,  # Batt: 51.2V, 80%, 1200W, 23.4A, 27.0C, 200Ah
        598: 2300, 599: 2310, 600: 2290, 609: 5000, 619: -1500,  # Grid: -1500W (importing)
        653: 3800, 643: 0, 636: 3800,  # Load: 3800W, Inverter: 3800W
        540: 1320, 541: 1350,  # DC: 32.0C, AC: 35.0C
        529: 250, 514: 90, 515: 30, 520: 150, 521: 200, 526: 300,  # Energy today
        534: 30000, 535: 0,  # PV Total 3000.0 kWh (32-bit LE)
        522: 15000, 523: 0,  # Grid Import Total 1500.0 kWh
        524: 20000, 525: 0,  # Grid Export Total 2000.0 kWh
    }

    telem = DeyeHybridEngine.decode_telemetry(regs)
    assert telem["run_state_label"] == "NORMAL"
    assert telem["pv_total_power_w"] == 5000
    assert telem["battery"]["voltage_v"] == 51.2
    assert telem["battery"]["soc_pct"] == 80
    assert telem["battery"]["temperature_c"] == 27.0
    assert telem["grid"]["direction"] == "IMPORTING"
    assert telem["grid"]["power_total_w"] == -1500
    assert telem["energy_today_kwh"]["pv"] == 25.0
    assert telem["energy_total_kwh"]["pv"] == 3000.0


def test_deye_decode_tou_schedule():
    """Verify decoding of all 6 sequential TOU slots."""
    regs = {
        148: 100, 149: 500, 150: 900, 151: 1300, 152: 1700, 153: 2100,
        154: 5000, 155: 6000, 156: 4000, 157: 5000, 158: 8000, 159: 5000,
        166: 100, 167: 90, 168: 50, 169: 80, 170: 20, 171: 40,
        172: 1, 173: 0, 174: 0, 175: 1, 176: 0, 177: 0,
    }

    slots = DeyeHybridEngine.decode_tou_schedule(regs)
    assert len(slots) == 6

    # Slot 1: 01:00 @ 5000W, 100% target, Grid charge source
    assert slots[0]["slot_number"] == 1
    assert slots[0]["time_str"] == "01:00"
    assert slots[0]["power_w"] == 5000
    assert slots[0]["target_soc"] == 100
    assert slots[0]["charge_source"] == 1
    assert "Grid" in slots[0]["charge_source_label"]

    # Slot 5: 17:00 @ 8000W, 20% target (peak shave), Off charge source
    assert slots[4]["slot_number"] == 5
    assert slots[4]["time_str"] == "17:00"
    assert slots[4]["target_soc"] == 20
    assert slots[4]["charge_source"] == 0


# ---------------------------------------------------------------------------
# Unit Tests: Command Compilers & CRC16 Frames
# ---------------------------------------------------------------------------

def test_compile_work_mode():
    """Verify work mode command compilation with solar sell and max sell power."""
    cmd = DeyeHybridEngine.compile_work_mode(
        mode=WORK_MODE_SELLING_FIRST,
        solar_sell=True,
        max_sell_power_w=8000,
    )

    assert cmd.command_id == "deye_set_work_mode_0"
    assert cmd.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert len(cmd.actions) == 3

    # Action 0: Work mode 0
    assert cmd.actions[0].register_address == REG_WORK_MODE
    assert cmd.actions[0].values == [0]

    # Action 1: Solar sell 1
    assert cmd.actions[1].register_address == REG_SOLAR_SELL
    assert cmd.actions[1].values == [1]

    # Action 2: Max sell power 8000
    assert cmd.actions[2].register_address == REG_MAX_SELL_POWER
    assert cmd.actions[2].values == [8000]

    # Check RTU frames and CRC16
    for a in cmd.actions:
        frame = a.to_rtu_frame()
        crc = int.from_bytes(frame[-2:], byteorder="little")
        expected_crc = calculate_modbus_crc16(frame[:-2])
        assert crc == expected_crc


def test_compile_grid_charge():
    """Verify grid charge enable and current limit command compilation."""
    cmd = DeyeHybridEngine.compile_grid_charge(enable=True, charge_current_a=50)

    assert cmd.command_id == "deye_grid_charge_enable"
    assert len(cmd.actions) == 2
    assert cmd.actions[0].register_address == REG_GRID_CHARGE_ENABLE
    assert cmd.actions[0].values == [1]
    assert cmd.actions[1].register_address == REG_GRID_CHARGE_CURRENT
    assert cmd.actions[1].values == [50]


def test_compile_tou_slot():
    """Verify compilation of single TOU slot programming (4 registers)."""
    cmd = DeyeHybridEngine.compile_tou_slot(
        slot_number=2,
        time_str="05:30",
        power_w=6500,
        target_soc=85,
        charge_source=1,
    )

    assert cmd.command_id == "deye_set_tou_slot_2"
    assert len(cmd.actions) == 4

    # Slot 2 index is 1:
    assert cmd.actions[0].register_address == REG_TOU_TIME_START + 1  # 149
    assert cmd.actions[0].values == [530]  # 05:30 -> 530
    assert cmd.actions[1].register_address == REG_TOU_POWER_START + 1  # 155
    assert cmd.actions[1].values == [6500]
    assert cmd.actions[2].register_address == REG_TOU_SOC_START + 1  # 167
    assert cmd.actions[2].values == [85]
    assert cmd.actions[3].register_address == REG_TOU_CHARGE_SOURCE_START + 1  # 173
    assert cmd.actions[3].values == [1]


# ---------------------------------------------------------------------------
# Contract / Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_deye_hybrid_decode_telemetry(local):
    """Verify POST /api/deye-hybrid/decode-telemetry."""
    client, _ = local
    headers = login(local, "operator")

    payload = {
        "registers": {
            500: 2,
            672: 2500, 676: 4000, 677: 62,
            587: 5120, 588: 90, 590: 1000, 591: 1950,
            619: 1500,
        }
    }
    resp = client.post("/api/deye-hybrid/decode-telemetry", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert "deye-modbus-ha-main" in data["source"]
    t = data["telemetry"]
    assert t["run_state_label"] == "NORMAL"
    assert t["pv_total_power_w"] == 2500
    assert t["battery"]["soc_pct"] == 90
    assert t["grid"]["direction"] == "EXPORTING"


def test_api_deye_hybrid_decode_tou_schedule(local):
    """Verify POST /api/deye-hybrid/decode-tou-schedule."""
    client, _ = local
    headers = login(local, "operator")

    payload = {
        "registers": {
            148: 200, 149: 600, 150: 1000, 151: 1400, 152: 1800, 153: 2200,
            154: 4000, 155: 5000, 156: 3000, 157: 4000, 158: 6000, 159: 4000,
            166: 100, 167: 90, 168: 70, 169: 80, 170: 25, 171: 50,
            172: 1, 173: 0, 174: 0, 175: 1, 176: 0, 177: 0,
        }
    }
    resp = client.post("/api/deye-hybrid/decode-tou-schedule", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    slots = data["slots"]
    assert len(slots) == 6
    assert slots[0]["time_str"] == "02:00"
    assert slots[0]["charge_source"] == 1


def test_api_deye_hybrid_compile_work_mode(local):
    """Verify POST /api/deye-hybrid/compile-work-mode."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/deye-hybrid/compile-work-mode",
        json={"mode": 1, "solar_sell": False, "max_sell_power_w": 0},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    cmd = data["command"]
    assert cmd["safety_gate"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert len(cmd["actions"]) == 3
    assert cmd["actions"][0]["register_address"] == REG_WORK_MODE
    assert cmd["actions"][0]["values"] == [1]


def test_api_deye_hybrid_compile_grid_charge(local):
    """Verify POST /api/deye-hybrid/compile-grid-charge."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/deye-hybrid/compile-grid-charge",
        json={"enable": True, "charge_current_a": 60},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    cmd = data["command"]
    assert len(cmd["actions"]) == 2
    assert cmd["actions"][0]["register_address"] == REG_GRID_CHARGE_ENABLE
    assert cmd["actions"][1]["values"] == [60]


def test_api_deye_hybrid_compile_tou_slot(local):
    """Verify POST /api/deye-hybrid/compile-tou-slot."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/deye-hybrid/compile-tou-slot",
        json={
            "slot_number": 3,
            "time_str": "09:15",
            "power_w": 4500,
            "target_soc": 75,
            "charge_source": 0,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    cmd = data["command"]
    assert cmd["command_id"] == "deye_set_tou_slot_3"
    assert len(cmd["actions"]) == 4
    assert cmd["actions"][0]["values"] == [915]  # 09:15 -> 915
