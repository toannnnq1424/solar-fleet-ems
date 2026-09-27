"""Unit and contract tests for Solis Hybrid S6 / RHI Storage Modbus & TOU Controller.

Derived from upstream project:
solis-modbus-ha-main (MIT License) - Clean-room independently implemented.
"""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from test_workspaces import login

from solar_fleet.solis_hybrid_controller import (
    DEFAULT_TOU_FIELD2,
    REG_CHARGE_SLOT_BASE,
    REG_DISCHARGE_SLOT_BASE,
    REG_STORAGE_MODE,
    SolisHybridDispatchEngine,
    SolisTouSlot,
    calculate_modbus_crc16,
    calculate_storage_mode,
    clear_tou_slot_registers,
    decode_storage_mode,
    decode_tou_slot,
    get_slot_base_register,
    parse_inverter_rtc,
    parse_solis_hybrid_telemetry,
    toggle_grid_charge_mode,
)

# ---------------------------------------------------------------------------
# Unit Tests: Storage Control Mode (Reg 43110) Bitfields
# ---------------------------------------------------------------------------

def test_decode_storage_mode():
    """Verify bitmask decoding into boolean states and human-readable flags."""
    # 0x0001 (BIT00: Self-consumption)
    dec1 = decode_storage_mode(0x0001)
    assert dec1["self_consumption"] is True
    assert dec1["time_charging"] is False
    assert dec1["grid_charge_allowed"] is False
    assert dec1["active_flags"] == ["Self-consumption"]

    # 0x0021 (BIT00 + BIT05: Self-consumption + Grid charge allowed)
    dec2 = decode_storage_mode(0x0021)
    assert dec2["self_consumption"] is True
    assert dec2["grid_charge_allowed"] is True
    assert "Grid charge allowed" in dec2["active_flags"]

    # 0x0032 (BIT01: Time-charging, BIT04: Battery reserve, BIT05: Grid charge allowed)
    dec3 = decode_storage_mode(0x0032)
    assert dec3["time_charging"] is True
    assert dec3["battery_reserve"] is True
    assert dec3["grid_charge_allowed"] is True
    assert dec3["self_consumption"] is False


def test_calculate_storage_mode_read_modify_write():
    """Verify atomic updates preserve unmanaged bits (like BIT04 battery reserve)."""
    # Start with 0x0011 (BIT00 Self-consumption + BIT04 Battery reserve)
    cur = 0x0011

    # Enable grid charge (BIT05)
    new1 = calculate_storage_mode(cur, grid_charge=True)
    assert new1 == 0x0031  # 0x0011 | 0x0020 = 0x0031
    assert (new1 & (1 << 4)) != 0  # Reserve preserved!

    # Switch from Self-consumption to Time-charging while preserving reserve and grid charge
    new2 = calculate_storage_mode(new1, self_consumption=False, time_charging=True)
    assert new2 == 0x0032  # BIT01, BIT04, BIT05 set; BIT00 cleared

    # Toggle grid charge off
    new3 = toggle_grid_charge_mode(new2, False)
    assert new3 == 0x0012  # BIT05 cleared, BIT01 & BIT04 preserved


# ---------------------------------------------------------------------------
# Unit Tests: TOU Schedule Slot Matrix
# ---------------------------------------------------------------------------

def test_slot_base_register_calculation():
    """Verify starting holding registers for all 6 charge and 6 discharge slots."""
    assert get_slot_base_register("charge", 0) == 43708
    assert get_slot_base_register("charge", 1) == 43715
    assert get_slot_base_register("charge", 5) == 43743

    assert get_slot_base_register("discharge", 0) == 43750
    assert get_slot_base_register("discharge", 1) == 43757
    assert get_slot_base_register("discharge", 5) == 43785

    with pytest.raises(ValueError):
        get_slot_base_register("charge", 6)


def test_tou_slot_encoding_and_decoding():
    """Verify bidirectional 7-register encoding and decoding."""
    slot = SolisTouSlot(
        slot_index=0,
        slot_type="charge",
        target_soc=95,
        current_a=45.5,
        field2=DEFAULT_TOU_FIELD2,
        start_hour=1,
        start_minute=30,
        end_hour=5,
        end_minute=45,
        base_register=43708,
    )

    regs = slot.to_registers()
    assert len(regs) == 7
    assert regs[0] == 95      # Target SOC
    assert regs[1] == 455     # Current in 0.1 A units (45.5 A -> 455)
    assert regs[2] == 490     # Field2 constant
    assert regs[3] == 1       # Start hour
    assert regs[4] == 30      # Start minute
    assert regs[5] == 5       # End hour
    assert regs[6] == 45      # End minute

    decoded = decode_tou_slot(regs, "charge", 0)
    assert decoded.target_soc == 95
    assert decoded.current_a == 45.5
    assert decoded.field2 == 490
    assert decoded.start_hour == 1
    assert decoded.start_minute == 30
    assert decoded.end_hour == 5
    assert decoded.end_minute == 45
    assert decoded.base_register == 43708


def test_clear_tou_slot():
    """Verify clearing a slot leaves field2 intact and zeros out active fields."""
    regs = clear_tou_slot_registers(field2=490)
    assert regs == [0, 0, 490, 0, 0, 0, 0]


# ---------------------------------------------------------------------------
# Unit Tests: Dynamic Dispatch & Software Watchdog
# ---------------------------------------------------------------------------

def test_dispatch_engine_power_to_current():
    """Verify power (W) to current (A) conversion across voltages."""
    engine = SolisHybridDispatchEngine(nominal_voltage=51.2, max_current_a=100.0)

    # 2560 W @ 51.2 V -> 50.0 A
    assert engine.power_to_current(2560.0, 51.2) == 50.0
    # Zero or negative power
    assert engine.power_to_current(0.0, 51.2) == 0.0
    assert engine.power_to_current(-500.0, 51.2) == 0.0
    # Over current limit clamped to max (100.0 A)
    assert engine.power_to_current(10000.0, 50.0) == 100.0


def test_dispatch_engine_calculate_window():
    """Verify TTL time window calculation and midnight clamping."""
    engine = SolisHybridDispatchEngine()
    base_time = datetime(2026, 9, 27, 10, 0, 0, tzinfo=timezone.utc)

    # 1200 seconds = 20 minutes
    sh, sm, eh, em = engine.calculate_window(base_time, 1200)
    assert (sh, sm) == (10, 0)
    assert (eh, em) == (10, 20)

    # Crossing midnight clamps to 23:59
    late_time = datetime(2026, 9, 27, 23, 45, 0, tzinfo=timezone.utc)
    sh2, sm2, eh2, em2 = engine.calculate_window(late_time, 1800)  # 30 mins
    assert (sh2, sm2) == (23, 45)
    assert (eh2, em2) == (23, 59)


def test_compile_dispatch_auto_mode():
    """Verify auto mode compiles slot clearing and reverts storage mode to self-consumption."""
    engine = SolisHybridDispatchEngine()
    cmd = engine.compile_dispatch("auto", current_storage_mode=0x0032)

    assert cmd.command_id == "solis_dispatch_auto"
    assert cmd.safety_gate == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert len(cmd.actions) == 3

    # Action 0: clear charge slot 0 (FC16)
    assert cmd.actions[0].register_address == REG_CHARGE_SLOT_BASE
    assert cmd.actions[0].function_code == 0x10
    # Action 1: clear discharge slot 0 (FC16)
    assert cmd.actions[1].register_address == REG_DISCHARGE_SLOT_BASE
    assert cmd.actions[1].function_code == 0x10
    # Action 2: set storage mode to self-consumption (FC06)
    assert cmd.actions[2].register_address == REG_STORAGE_MODE
    assert cmd.actions[2].function_code == 0x06
    # 0x0032 with self_consumption=1, time_charging=0, grid_charge=0 -> 0x0011 (battery reserve preserved)
    assert cmd.actions[2].values[0] == 0x0011


def test_compile_dispatch_force_charge_mode():
    """Verify force charge programs slot 0 and enables BIT01 & BIT05."""
    engine = SolisHybridDispatchEngine()
    base_time = datetime(2026, 9, 27, 2, 0, 0, tzinfo=timezone.utc)
    cmd = engine.compile_dispatch(
        "charge",
        power_w=3000.0,
        battery_voltage=50.0,
        ttl_seconds=1800,
        current_storage_mode=0x0001,
        target_soc=90,
        base_time=base_time,
    )

    assert cmd.command_id == "solis_dispatch_force_charge"
    assert cmd.watchdog_ttl_seconds == 1800

    # 3000 W / 50.0 V = 60.0 A
    assert cmd.metadata["calculated_current_a"] == 60.0
    assert cmd.metadata["window"]["start"] == "02:00"
    assert cmd.metadata["window"]["end"] == "02:30"

    # Verify RTU frame generation with CRC16
    for a in cmd.actions:
        frame = a.to_rtu_frame()
        crc = int.from_bytes(frame[-2:], byteorder="little")
        expected_crc = calculate_modbus_crc16(frame[:-2])
        assert crc == expected_crc


# ---------------------------------------------------------------------------
# Unit Tests: Telemetry and RTC Parsing
# ---------------------------------------------------------------------------

def test_parse_inverter_rtc():
    """Verify decoding of input registers 33022-33027 into ISO UTC timestamp."""
    # [26, 9, 27, 10, 30, 45] -> Year 2026, Sept 27, 10:30:45 UTC
    regs = [26, 9, 27, 10, 30, 45]
    iso_str = parse_inverter_rtc(regs)
    assert iso_str == "2026-09-27T10:30:45Z"

    # Truncated registers
    assert parse_inverter_rtc([26, 9]) is None


def test_parse_solis_hybrid_telemetry():
    """Verify normalization of Solis Hybrid telemetry dictionary."""
    data = {
        "battery_voltage": 52.4,
        "battery_power": 1500.0,  # Charging
        "grid_port_power": -1200.0,
        "total_dc_power": 2800.0,
        "battery_soc": 85,
        "storage_mode_raw": 0x0021,  # Grid charge allowed
    }
    telem = parse_solis_hybrid_telemetry(data)
    assert telem["battery_voltage_v"] == 52.4
    assert telem["battery_soc_pct"] == 85
    assert telem["battery_state"] == "CHARGING"
    assert telem["grid_charge_allowed"] is True


# ---------------------------------------------------------------------------
# Contract / Integration Tests: REST API Endpoints
# ---------------------------------------------------------------------------

def test_api_solis_hybrid_decode_storage_mode(local):
    """Verify POST /api/solis-hybrid/decode-storage-mode."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/solis-hybrid/decode-storage-mode",
        json={"value": 33},  # 0x0021
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "solis-modbus-ha-main" in data["source"]
    mode = data["storage_mode"]
    assert mode["raw_value"] == 33
    assert mode["self_consumption"] is True
    assert mode["grid_charge_allowed"] is True


def test_api_solis_hybrid_compile_grid_charge(local):
    """Verify POST /api/solis-hybrid/compile-grid-charge."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/solis-hybrid/compile-grid-charge",
        json={"current_mode_value": 1, "enable_grid_charge": True},
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    cmd = data["command"]
    assert cmd["safety_gate"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert len(cmd["actions"]) == 1
    assert cmd["actions"][0]["register_address"] == REG_STORAGE_MODE
    assert cmd["actions"][0]["values"] == [33]  # 1 | 0x20 = 33


def test_api_solis_hybrid_compile_dispatch(local):
    """Verify POST /api/solis-hybrid/compile-dispatch."""
    client, _ = local
    headers = login(local, "operator")

    resp = client.post(
        "/api/solis-hybrid/compile-dispatch",
        json={
            "mode": "charge",
            "power_w": 2500,
            "battery_voltage": 50.0,
            "ttl_seconds": 1200,
            "current_storage_mode": 1,
            "target_soc": 95,
        },
        headers=headers,
    )
    assert resp.status_code == 200
    data = resp.json()
    cmd = data["command"]
    assert cmd["command_id"] == "solis_dispatch_force_charge"
    assert cmd["watchdog_ttl_seconds"] == 1200
    assert cmd["safety_gate"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"


def test_api_solis_hybrid_decode_tou_slots(local):
    """Verify POST /api/solis-hybrid/decode-tou-slots."""
    client, _ = local
    headers = login(local, "operator")

    payload = {
        "registers": {
            43708: 100, 43709: 500, 43710: 490, 43711: 0, 43712: 0, 43713: 4, 43714: 0,
            43750: 20, 43751: 600, 43752: 490, 43753: 17, 43754: 0, 43755: 21, 43756: 0,
        }
    }
    resp = client.post("/api/solis-hybrid/decode-tou-slots", json=payload, headers=headers)
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["charge_slots"]) == 6
    assert len(data["discharge_slots"]) == 6
    assert data["charge_slots"][0]["target_soc"] == 100
    assert data["charge_slots"][0]["current_a"] == 50.0
    assert data["discharge_slots"][0]["target_soc"] == 20
    assert data["discharge_slots"][0]["current_a"] == 60.0
