"""Tests for Solarman Profile Engine & Multi-Vendor Rule Parser.

Validates profile catalogue, rule-based register decoding (Rules 1..10),
query range optimization, parameter write compilers, hardware acceptance safety gates,
and REST API endpoints.
"""

from solar_fleet.solarman_profile_engine import (
    PROFILE_REGISTRY,
    RULE_ASCII,
    RULE_BITS,
    RULE_DATETIME,
    RULE_SIGNED,
    RULE_SIGNED_LOOKUP,
    RULE_TIME,
    RULE_UNSIGNED,
    RULE_UNSIGNED_LOOKUP,
    RULE_VERSION,
    InverterProfile,
    ProfileParameter,
    SolarmanProfileClient,
    SolarmanProfileParser,
    compile_profile_parameter_write,
    plan_optimal_modbus_requests,
)


def test_profile_registry():
    """Verify built-in profiles are present and well-formed."""
    assert "deye_hybrid" in PROFILE_REGISTRY
    assert "sofar_g3hyd" in PROFILE_REGISTRY
    assert "solis_hybrid" in PROFILE_REGISTRY

    deye = PROFILE_REGISTRY["deye_hybrid"]
    assert deye.vendor == "Deye"
    assert len(deye.requests) == 3
    assert len(deye.parameters) > 10


def test_rule_parser_unsigned_and_signed():
    """Verify Rule 1, 2, 3, 4 decoding."""
    dummy_prof = InverterProfile(
        profile_id="test",
        vendor="Test",
        family_name="Test",
        default_slave_id=1,
        requests=[],
        parameters=[
            ProfileParameter(name="U16", registers=[100], rule=RULE_UNSIGNED, scale=0.1),
            ProfileParameter(name="U32", registers=[101, 102], rule=RULE_UNSIGNED, scale=1.0),
            ProfileParameter(name="S16_Neg", registers=[103], rule=RULE_SIGNED, scale=0.1),
            ProfileParameter(name="S32_Neg", registers=[104, 105], rule=RULE_SIGNED, scale=1.0),
            ProfileParameter(name="Lookup", registers=[106], rule=RULE_UNSIGNED_LOOKUP, lookup={1: "Active", 2: "Standby"}),
            ProfileParameter(name="SignedLookup", registers=[107], rule=RULE_SIGNED_LOOKUP, scale=0.1, offset=-100.0),
        ],
    )
    parser = SolarmanProfileParser(dummy_prof)

    reg_map = {
        100: 2305,             # 230.5
        101: 0, 102: 50000,    # 50000
        103: 0xFF9C,           # -100 -> -10.0
        104: 0xFFFF, 105: 0xFD44, # -700
        106: 1,                # "Active"
        107: 1420,             # (1420 * 0.1) - 100 = 42.0
    }
    parsed = parser.parse_registers(reg_map)

    assert parsed["U16"] == 230.5
    assert parsed["U32"] == 50000
    assert parsed["S16_Neg"] == -10.0
    assert parsed["S32_Neg"] == -700
    assert parsed["Lookup"] == "Active"
    assert parsed["SignedLookup"] == 42.0


def test_rule_parser_string_bits_version_and_time():
    """Verify Rule 5 (ASCII), Rule 6 (Bits), Rule 7 (Version), Rule 8 (Datetime), Rule 9 (Time)."""
    dummy_prof = InverterProfile(
        profile_id="test2",
        vendor="Test",
        family_name="Test",
        default_slave_id=1,
        requests=[],
        parameters=[
            ProfileParameter(name="SN", registers=[200, 201], rule=RULE_ASCII),
            ProfileParameter(name="Alarms", registers=[202], rule=RULE_BITS, lookup={0: "Fault1", 2: "Fault3"}),
            ProfileParameter(name="Ver", registers=[203], rule=RULE_VERSION),
            ProfileParameter(name="Clock", registers=[204, 205, 206], rule=RULE_DATETIME),
            ProfileParameter(name="SlotTime", registers=[207], rule=RULE_TIME),
        ],
    )
    parser = SolarmanProfileParser(dummy_prof)

    reg_map = {
        200: 0x5445, 201: 0x5354,  # "TEST"
        202: 0x0005,               # Bits 0 and 2 set -> ["Fault1", "Fault3"]
        203: 0x1234,               # 1.2.52
        204: (26 << 8) | 9,        # 2026-09
        205: (27 << 8) | 12,       # 27 12:
        206: (30 << 8) | 45,       # :30:45
        207: (6 << 8) | 15,        # 06:15
    }
    parsed = parser.parse_registers(reg_map)

    assert parsed["SN"] == "TEST"
    assert parsed["Alarms"] == ["Fault1", "Fault3"]
    assert parsed["Ver"] == "1.2.52"
    assert parsed["Clock"] == "2026-09-27 12:30:45"
    assert parsed["SlotTime"] == "06:15"


def test_query_range_planner():
    """Verify partitioning arbitrary register lists into continuous chunks."""
    regs = [1, 2, 3, 5, 6, 20, 21, 22, 100]
    ranges = plan_optimal_modbus_requests(regs, max_chunk_size=10, max_gap=2)

    # 1..6 (gap between 3 and 5 is 1 <= 2)
    # 20..22
    # 100
    assert len(ranges) == 3
    assert ranges[0].start == 1 and ranges[0].end == 6
    assert ranges[1].start == 20 and ranges[1].end == 22
    assert ranges[2].start == 100 and ranges[2].end == 100


def test_compile_profile_parameter_write_and_safety():
    """Verify FC06/FC10 parameter write compilers with safety gating."""
    # Deye single register write
    w_deye = compile_profile_parameter_write("deye_hybrid", "Solar Export Power", 6000)
    assert w_deye["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert w_deye["registers"] == [143]
    assert w_deye["compiled_raw_value"] == 6000
    assert "Gated by hardware acceptance" in w_deye["reason"]

    # Client execute_command_safely
    client = SolarmanProfileClient(profile_id="deye_hybrid", simulated=True)
    res_locked = client.execute_command_safely("Solar Export Power", 5000, unlocked=False)
    assert res_locked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert "read-only state" in res_locked["message"]

    res_unlocked = client.execute_command_safely("Solar Export Power", 5000, unlocked=True)
    assert res_unlocked["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
    assert res_unlocked["compiled_raw_value"] == 5000


def test_telemetry_polling_and_normalizer():
    """Verify simulated polling for multiple vendor profiles."""
    for pid in ["deye_hybrid", "sofar_g3hyd", "solis_hybrid"]:
        client = SolarmanProfileClient(profile_id=pid, simulated=True)
        ems = client.poll_telemetry()
        assert ems["model_type"] == pid
        assert "solar_power_w" in ems["power_flow"]
        assert "grid_power_w" in ems["power_flow"]
        assert ems["metrics"]["battery_soc_pct"] > 0


def test_api_solarman_profile_endpoints(local):
    """Unwired production routes must not expose simulator outcomes."""
    from test_workspaces import login

    client, controller = local
    headers = login(local, "operator")
    response = client.post("/api/solarman-profile/telemetry", headers=headers, json={})
    assert response.status_code == 503
    assert "LIVE_TRANSPORT_UNAVAILABLE" in response.json()["detail"]
    response = client.post("/api/solarman-profile/command", headers=headers, json={"command_type": "workmode", "parameter_name": "workmode", "value": 0, "unlocked": True})
    assert response.status_code == 409
    assert "UNCOMMISSIONED_CONTROL" in response.json()["detail"]
    assert not controller.store.commands()
