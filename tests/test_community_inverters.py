"""Contract and unit tests for Community Inverter Modbus Register Engine and Polling Optimizer.

Provenance: solar-inverter-modbus-registers-main (MIT, Copyright (c) 2026 Daniel Szlaski).
"""

from __future__ import annotations

from solar_fleet.community_registers_engine import CommunityRegistersEngine

# ---------------------------------------------------------------------------
# Engine Unit Tests
# ---------------------------------------------------------------------------

def test_list_all_10_community_profiles():
    """Verify that all 10 profiles from solar-inverter-modbus-registers are loaded correctly."""
    profiles = CommunityRegistersEngine.list_profiles()
    assert len(profiles) == 10

    brand_names = {p["brand_name"] for p in profiles}
    assert "Solis" in brand_names
    assert "Sofar Solar" in brand_names
    assert "SolaX Power" in brand_names
    assert "Growatt" in brand_names
    assert "GoodWe" in brand_names

    model_ids = {p["model_id"] for p in profiles}
    expected_ids = {
        "rhi-s6-hybrid",
        "s5-s6-string",
        "hyd-es-legacy",
        "hyd-ktl-3ph",
        "x1-x3-hybrid-g3-g4",
        "x1-x3-mic-string-g1",
        "sph-tl-bh",
        "min-tl-x-string",
        "et-eh-hybrid",
        "dt-ns-string",
    }
    assert expected_ids.issubset(model_ids)


def test_get_profile_schema_details():
    """Verify detailed profile schema retrieval."""
    p_solis = CommunityRegistersEngine.get_profile("rhi-s6-hybrid")
    assert p_solis is not None
    assert p_solis["brandId"] == "solis"
    assert p_solis["unitId"] == 1
    assert p_solis["polling"]["maxBlockSize"] == 70
    assert p_solis["polling"]["gapTolerance"] == 35
    assert len(p_solis["fields"]) == 21
    assert len(p_solis["alarms"]) == 1

    p_none = CommunityRegistersEngine.get_profile("nonexistent-model-xyz")
    assert p_none is None


def test_block_polling_optimization_with_gap_tolerance():
    """Verify that gap tolerance merges nearby registers into larger blocks, saving network packets."""
    res_gap = CommunityRegistersEngine.optimize_polling_blocks("rhi-s6-hybrid", enable_gap_tolerance=True)
    assert res_gap["status"] == "success"
    assert res_gap["baseline_requests"] == 12
    # With gapTolerance=35, it collapses 12 requests into 3 blocks
    assert res_gap["optimized_requests"] == 3
    assert res_gap["packets_saved"] == 9
    assert res_gap["savings_pct"] == 75.0

    # Without gap tolerance, contiguous blocks only
    res_no_gap = CommunityRegistersEngine.optimize_polling_blocks("rhi-s6-hybrid", enable_gap_tolerance=False)
    assert res_no_gap["status"] == "success"
    assert res_no_gap["optimized_requests"] > res_gap["optimized_requests"]


def test_address_offset_handling():
    """Verify address offset (-1) for Solis string inverters."""
    p_string = CommunityRegistersEngine.get_profile("s5-s6-string")
    assert p_string["addressOffset"] == -1

    res = CommunityRegistersEngine.optimize_polling_blocks("s5-s6-string")
    assert res["status"] == "success"
    assert res["address_offset"] == -1
    # Check that wire addresses have been shifted by -1
    for block in res["blocks"]:
        assert block["start_address"] >= 0


def test_telemetry_decoding_16bit_and_32bit():
    """Verify decoding of 16-bit unsigned and 32-bit signed big-endian registers with scale factors."""
    raw_regs = {
        33057: 0,
        33058: 4500,     # powerKW: 4500 * 0.001 = 4.5 kW
        33139: 92,       # batteryPercent: 92 * 1.0 = 92.0%
        33147: 1500,     # familyLoadPowerKW: 1500 * 0.001 = 1.5 kW
    }
    decoded = CommunityRegistersEngine.decode_telemetry("rhi-s6-hybrid", raw_regs)
    assert decoded["status"] == "success"
    fields = decoded["decoded_fields"]

    assert "powerKW" in fields
    assert fields["powerKW"]["value"] == 4.5
    assert fields["powerKW"]["unit"] == "kW"
    assert fields["powerKW"]["valid"] is True

    assert "batteryPercent" in fields
    assert fields["batteryPercent"]["value"] == 92.0
    assert fields["batteryPercent"]["unit"] == "%"
    assert fields["batteryPercent"]["valid"] is True

    assert "familyLoadPowerKW" in fields
    assert fields["familyLoadPowerKW"]["value"] == 1.5


def test_alarm_bitfield_multiword_decoding():
    """Verify decoding of multi-word alarm bitfields across 80 bits (Solis hybrid)."""
    # Register 33116 (word 0): bit 0 (NO-Grid) and bit 1 (OV-G-V)
    # Register 33120 (word 4): bit 66 (OV-TEM: 66 // 16 = 4, 66 % 16 = 2 -> 1 << 2 = 4)
    raw_alarms = {
        33116: 0b0011,  # bit 0 and bit 1
        33120: 0b0100,  # bit 66
    }
    result = CommunityRegistersEngine.decode_alarm_bitfield("rhi-s6-hybrid", raw_alarms)
    assert result["status"] == "success"
    assert result["active_alarm_count"] == 3

    alarms_by_bit = {a["bit_index"]: a for a in result["alarms"]}
    assert 0 in alarms_by_bit
    assert alarms_by_bit[0]["fault_code"] == "1015"
    assert alarms_by_bit[0]["message"] == "NO-Grid"
    assert alarms_by_bit[0]["category"] == "GRID"

    assert 1 in alarms_by_bit
    assert alarms_by_bit[1]["fault_code"] == "1010"
    assert alarms_by_bit[1]["message"] == "OV-G-V"
    assert alarms_by_bit[1]["severity"] == "CRITICAL"

    assert 66 in alarms_by_bit
    assert alarms_by_bit[66]["fault_code"] == "1032"
    assert alarms_by_bit[66]["message"] == "OV-TEM"
    assert alarms_by_bit[66]["category"] == "TEMPERATURE"
    assert "Clean inverter heat sink fins" in alarms_by_bit[66]["sop"]


from test_workspaces import login

# ---------------------------------------------------------------------------
# REST API Endpoint Tests
# ---------------------------------------------------------------------------

def test_api_list_community_profiles(local):
    client, _ctl = local
    headers = login(local, "operator")
    response = client.get(
        "/api/community-inverters/profiles",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["total_profiles"] == 10
    assert len(data["profiles"]) == 10


def test_api_get_community_profile(local):
    client, _ctl = local
    headers = login(local, "operator")
    response = client.get(
        "/api/community-inverters/profile/et-eh-hybrid",
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["model_id"] == "et-eh-hybrid"
    assert data["profile"]["unitId"] == 247

    # Nonexistent
    err_res = client.get(
        "/api/community-inverters/profile/unknown-device-1234",
        headers=headers,
    )
    assert err_res.status_code == 404


def test_api_optimize_polling(local):
    client, _ctl = local
    headers = login(local, "operator")
    response = client.post(
        "/api/community-inverters/optimize-polling",
        json={
            "model_id": "rhi-s6-hybrid",
            "enable_gap_tolerance": True,
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["baseline_requests"] == 12
    assert data["optimized_requests"] == 3
    assert data["packets_saved"] == 9
    assert len(data["blocks"]) == 3


def test_api_decode_telemetry(local):
    client, _ctl = local
    headers = login(local, "operator")
    response = client.post(
        "/api/community-inverters/decode-telemetry",
        json={
            "model_id": "rhi-s6-hybrid",
            "registers": {
                33057: 0,
                33058: 3200,
                33139: 78,
            },
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["decoded_fields"]["powerKW"]["value"] == 3.2
    assert data["decoded_fields"]["batteryPercent"]["value"] == 78.0


def test_api_decode_alarms(local):
    client, _ctl = local
    headers = login(local, "operator")
    response = client.post(
        "/api/community-inverters/decode-alarms",
        json={
            "model_id": "rhi-s6-hybrid",
            "registers": {
                33116: 1,  # Bit 0 NO-Grid
            },
        },
        headers=headers,
    )
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["active_alarm_count"] == 1
    assert data["alarms"][0]["message"] == "NO-Grid"

