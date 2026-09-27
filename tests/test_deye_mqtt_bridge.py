"""Unit and Contract Tests for Deye & SunSynk Multi-Family Inverter MQTT Bridge.

Validates multi-family sensor catalogues, telemetry decoders, MQTT topic routing,
command compilers, safety gates (LOCKED_PENDING_HARDWARE_ACCEPTANCE), Time-of-Use service,
multi-inverter parallel cluster aggregator, AT command bridge, and Phase D API endpoints.
"""

from __future__ import annotations

from solar_fleet.deye_mqtt_bridge import (
    DEYE_FAMILY_CATALOG,
    SAFETY_STATUS_LOCKED,
    SAFETY_STATUS_UNLOCKED,
    DeyeAtCommandBridge,
    DeyeCommandCompiler,
    DeyeDeviceFamily,
    DeyeMqttTopicRouter,
    DeyeMultiInverterAggregator,
    DeyeTelemetrySimulator,
    DeyeTimeOfUseService,
    DeyeTouSlot,
    DeyeWorkMode,
    normalize_deye_mqtt_telemetry,
)

# ---------------------------------------------------------------------------
# Catalog & Family Tests
# ---------------------------------------------------------------------------

def test_deye_device_families_enumeration():
    """Verify all 9 device families exist and have registered sensor descriptors."""
    assert len(DeyeDeviceFamily) == 9
    for fam in DeyeDeviceFamily:
        sensors = DEYE_FAMILY_CATALOG.get(fam)
        assert sensors is not None, f"Missing sensor catalog for {fam}"
        assert len(sensors) > 0, f"Empty sensor catalog for {fam}"


# ---------------------------------------------------------------------------
# Telemetry Simulation & Decoding Tests
# ---------------------------------------------------------------------------

def test_telemetry_simulation_and_decoding_sg01hp3():
    """Verify SG01HP3 High-Voltage 3-phase hybrid telemetry decoding."""
    raw = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.SG01HP3)
    decoded, mqtt_msgs = DeyeTelemetrySimulator.decode_family_telemetry(
        DeyeDeviceFamily.SG01HP3, raw, logger_sn="1234567890"
    )

    # Check high voltage battery stack
    assert decoded["battery/voltage"] == 420.0
    assert decoded["bms/stack_voltage"] == 420.0
    assert decoded["bms/stack_soc"] == 82.0
    assert decoded["bms/stack_soh"] == 98.0
    assert decoded["battery/soc"] == 82.0
    assert decoded["battery/temperature"] == 28.0

    # Check PV strings and grid
    assert decoded["dc/pv1/power"] == 4200.0
    assert decoded["dc/pv2/power"] == 3800.0
    assert decoded["ac/total_power"] == 5500.0
    assert decoded["day_energy"] == 38.5

    # Check MQTT messages generated
    topics = [m["topic"] for m in mqtt_msgs]
    assert "deye/1234567890/battery/voltage" in topics
    assert "deye/1234567890/bms/stack_voltage" in topics
    assert "deye/1234567890/dc/pv1/power" in topics


def test_telemetry_simulation_and_decoding_sg04lp3():
    """Verify SG04LP3 Low-Voltage 3-phase hybrid telemetry decoding."""
    raw = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.SG04LP3)
    decoded, mqtt_msgs = DeyeTelemetrySimulator.decode_family_telemetry(
        DeyeDeviceFamily.SG04LP3, raw, logger_sn="9876543210"
    )

    assert decoded["battery/voltage"] == 51.2
    assert decoded["battery/soc"] == 76.0
    assert decoded["battery/power"] == 1800.0
    assert decoded["dc/pv1/power"] == 2800.0
    assert decoded["dc/pv2/power"] == 2700.0
    assert decoded["settings/workmode"] == 1.0
    assert decoded["settings/solar_sell"] == 1.0
    assert decoded["settings/solar_sell_max_power"] == 5000.0


def test_telemetry_simulation_and_decoding_sg02lp1():
    """Verify SG02LP1 Low-Voltage single-phase hybrid telemetry decoding."""
    raw = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.SG02LP1)
    decoded, _ = DeyeTelemetrySimulator.decode_family_telemetry(
        DeyeDeviceFamily.SG02LP1, raw, logger_sn="11223344"
    )

    assert decoded["battery/voltage"] == 51.4
    assert decoded["battery/soc"] == 88.0
    assert decoded["dc/pv1/power"] == 2200.0
    assert decoded["dc/pv2/power"] == 2100.0
    assert decoded["ac/l1/voltage"] == 228.5
    assert decoded["ac/active_power"] == 2850.0


def test_telemetry_simulation_and_decoding_string_and_micro():
    """Verify String inverter and Microinverter telemetry decoding."""
    # String
    raw_str = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.STRING)
    decoded_str, _ = DeyeTelemetrySimulator.decode_family_telemetry(
        DeyeDeviceFamily.STRING, raw_str, logger_sn="string_01"
    )
    assert decoded_str["ac/l1/voltage"] == 230.0
    assert decoded_str["ac/l2/voltage"] == 231.0
    assert decoded_str["ac/l3/voltage"] == 229.5
    assert decoded_str["igbt_temp"] == 45.0
    assert decoded_str["settings/active_power_regulation"] == 100.0

    # Micro
    raw_mic = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.MICRO)
    decoded_mic, _ = DeyeTelemetrySimulator.decode_family_telemetry(
        DeyeDeviceFamily.MICRO, raw_mic, logger_sn="micro_01"
    )
    assert decoded_mic["ac/l1/voltage"] == 230.5
    assert decoded_mic["ac/l1/current"] == 8.6
    assert decoded_mic["day_energy"] == 8.5


def test_telemetry_simulation_and_decoding_igen_dtsd422():
    """Verify IGEN DTSD422 3-phase CT smart power meter telemetry decoding."""
    raw = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.IGEN_DTSD422)
    decoded, _ = DeyeTelemetrySimulator.decode_family_telemetry(
        DeyeDeviceFamily.IGEN_DTSD422, raw, logger_sn="meter_01"
    )

    assert decoded["ct1/voltage"] == 230.2
    assert decoded["ct1/current"] == 15.4
    assert decoded["ct1/active_power"] == 3540.0
    assert decoded["ct2/voltage"] == 229.8
    assert decoded["ct2/current"] == 14.9
    assert decoded["ct3/voltage"] == 230.5
    assert decoded["ct3/current"] == 15.2
    assert decoded["total_positive_energy"] == 1850.0
    assert decoded["total_negative_energy"] == 450.0


# ---------------------------------------------------------------------------
# MQTT Topic Router Tests
# ---------------------------------------------------------------------------

def test_mqtt_topic_router():
    """Verify publication and command topic routing."""
    router = DeyeMqttTopicRouter("deye")

    pub_top = router.build_publish_topic("1234567890", "battery/soc")
    assert pub_top == "deye/1234567890/battery/soc"

    cmd_top = router.build_command_topic("1234567890", "settings/workmode")
    assert cmd_top == "deye/1234567890/settings/workmode/command"

    # Extract command suffix
    extracted = router.extract_command_suffix("1234567890", cmd_top)
    assert extracted == "settings/workmode"

    # Non-command or wrong sn topic extraction
    assert router.extract_command_suffix("1234567890", "deye/1234567890/battery/soc") is None
    assert router.extract_command_suffix("9999", cmd_top) is None


# ---------------------------------------------------------------------------
# Parameter Write Compiler Tests
# ---------------------------------------------------------------------------

def test_command_compiler_workmode():
    """Test WorkMode compilation and safety lock."""
    # Valid mode with default locked gate
    res_locked = DeyeCommandCompiler.compile_workmode(DeyeWorkMode.ZERO_EXPORT_TO_LOAD, confirm_hardware_acceptance=False)
    assert res_locked.success is True
    assert res_locked.target_register == 142
    assert res_locked.raw_value == 1
    assert res_locked.status == SAFETY_STATUS_LOCKED
    assert res_locked.dry_run is True

    # Valid mode with explicit unlock
    res_unlocked = DeyeCommandCompiler.compile_workmode(DeyeWorkMode.SELLING_FIRST, confirm_hardware_acceptance=True)
    assert res_unlocked.success is True
    assert res_unlocked.status == SAFETY_STATUS_UNLOCKED
    assert res_unlocked.dry_run is False

    # Invalid mode
    res_invalid = DeyeCommandCompiler.compile_workmode(99)
    assert res_invalid.success is False
    assert "Work mode must be 0" in (res_invalid.error_message or "")


def test_command_compiler_solar_sell_and_max_power():
    """Test Solar Sell and Solar Sell Max Power compilers."""
    # Solar sell toggle
    sell_res = DeyeCommandCompiler.compile_solar_sell(True, confirm_hardware_acceptance=False)
    assert sell_res.success is True
    assert sell_res.target_register == 145
    assert sell_res.raw_value == 1
    assert sell_res.status == SAFETY_STATUS_LOCKED

    # Max power
    pwr_res = DeyeCommandCompiler.compile_solar_sell_max_power(4500, confirm_hardware_acceptance=True)
    assert pwr_res.success is True
    assert pwr_res.target_register == 143
    assert pwr_res.raw_value == 4500
    assert pwr_res.status == SAFETY_STATUS_UNLOCKED

    # Max power out of bounds
    pwr_err = DeyeCommandCompiler.compile_solar_sell_max_power(15000)
    assert pwr_err.success is False
    assert "between 0 and 12000" in (pwr_err.error_message or "")


def test_command_compiler_active_power_regulation():
    """Test Active Power Regulation compiler."""
    # 80.5% regulation
    reg_res = DeyeCommandCompiler.compile_active_power_regulation(80.5, confirm_hardware_acceptance=False)
    assert reg_res.success is True
    assert reg_res.target_register == 40
    assert reg_res.raw_value == 805  # scaled by 10
    assert reg_res.status == SAFETY_STATUS_LOCKED

    # Out of range
    reg_err = DeyeCommandCompiler.compile_active_power_regulation(150.0)
    assert reg_err.success is False
    assert "between 0.0% and 120.0%" in (reg_err.error_message or "")


def test_command_compiler_battery_settings():
    """Test battery parameter compilers."""
    # Grid charge enable
    gc_res = DeyeCommandCompiler.compile_battery_setting("grid_charge", 1, confirm_hardware_acceptance=False)
    assert gc_res.success is True
    assert gc_res.target_register == 130
    assert gc_res.raw_value == 1

    # Max charge current
    chg_res = DeyeCommandCompiler.compile_battery_setting("maximum_charge_current", 120, confirm_hardware_acceptance=True)
    assert chg_res.success is True
    assert chg_res.target_register == 108
    assert chg_res.raw_value == 120
    assert chg_res.status == SAFETY_STATUS_UNLOCKED

    # Max discharge current
    dis_res = DeyeCommandCompiler.compile_battery_setting("maximum_discharge_current", 150)
    assert dis_res.success is True
    assert dis_res.target_register == 109
    assert dis_res.raw_value == 150

    # Invalid setting
    inv_res = DeyeCommandCompiler.compile_battery_setting("invalid_setting", 50)
    assert inv_res.success is False


# ---------------------------------------------------------------------------
# Time of Use Service Tests
# ---------------------------------------------------------------------------

def test_time_of_use_service():
    """Test 6-slot TOU schedule staging, batch compilation, and reset."""
    tou = DeyeTimeOfUseService()

    slot1 = DeyeTouSlot(slot_index=1, time_hhmm="05:00", power_watts=3500, target_soc=80, voltage=51.2, charge_enabled=True)
    slot2 = DeyeTouSlot(slot_index=2, time_hhmm="12:30", power_watts=4000, target_soc=90, voltage=52.0, charge_enabled=False)

    staged1 = tou.stage_slot(slot1)
    assert staged1[148] == 500   # 05:00 -> 500
    assert staged1[154] == 3500  # power
    assert staged1[160] == 5120  # voltage * 100
    assert staged1[166] == 80    # SOC
    assert staged1[172] == 1     # enabled

    staged2 = tou.stage_slot(slot2)
    assert staged2[149] == 1230  # 12:30 -> 1230
    assert staged2[173] == 0     # disabled

    # Compile write batches in locked dry-run
    batches = tou.compile_write_batches(confirm_hardware_acceptance=False, dry_run=True)
    assert len(batches) == 10
    assert all(b.status == SAFETY_STATUS_LOCKED for b in batches)
    assert all(b.dry_run is True for b in batches)

    # Clear staged
    tou.clear_staged()
    assert len(tou.modifications) == 0


# ---------------------------------------------------------------------------
# Multi-Inverter Parallel Aggregator Tests
# ---------------------------------------------------------------------------

def test_multi_inverter_aggregator():
    """Test multi-inverter parallel cluster aggregation and date rollover."""
    aggregator = DeyeMultiInverterAggregator()

    aggregator.record_inverter_metrics("inv_01", ac_active_power_w=5000.0, daily_energy_kwh=25.0, total_energy_kwh=10000.0, battery_power_w=1500.0)
    aggregator.record_inverter_metrics("inv_02", ac_active_power_w=4800.0, daily_energy_kwh=24.0, total_energy_kwh=9600.0, battery_power_w=1400.0)

    cluster = aggregator.get_aggregated_cluster_metrics()
    assert cluster["cluster_size"] == 2
    assert cluster["aggregated_ac_active_power_w"] == 9800.0
    assert cluster["aggregated_daily_energy_kwh"] == 49.0
    assert cluster["aggregated_total_energy_kwh"] == 19600.0
    assert cluster["aggregated_battery_power_w"] == 2900.0
    assert "inv_01" in cluster["member_loggers"]
    assert "inv_02" in cluster["member_loggers"]


# ---------------------------------------------------------------------------
# AT Command Bridge Tests
# ---------------------------------------------------------------------------

def test_at_command_bridge():
    """Test AT command parser responses."""
    bridge = DeyeAtCommandBridge(mac_address="00:11:22:33:44:55", fw_version="MW3_16U_TEST_1.0")

    assert bridge.execute_command("AT+WNTYPE") == "+ok=ESP32_WIFI"
    assert bridge.execute_command("AT+WSKEY") == "+ok=WPA2PSK,AES,solar_fleet_mesh"
    assert bridge.execute_command("AT+MID") == "+ok=00:11:22:33:44:55"
    assert bridge.execute_command("AT+VER") == "+ok=MW3_16U_TEST_1.0"
    assert bridge.execute_command("AT+Z") == "+ok=REBOOTING"
    assert bridge.execute_command("AT+H").startswith("+ok=")
    assert bridge.execute_command("AT+UNKNOWN") == "+err=-1"


# ---------------------------------------------------------------------------
# Normalization Tests
# ---------------------------------------------------------------------------

def test_normalization_to_solar_fleet_schema():
    """Verify normalizer maps multi-family decoded telemetry into unified schema."""
    raw = DeyeTelemetrySimulator.generate_simulated_registers(DeyeDeviceFamily.SG04LP3)
    decoded, _ = DeyeTelemetrySimulator.decode_family_telemetry(DeyeDeviceFamily.SG04LP3, raw)
    norm = normalize_deye_mqtt_telemetry(DeyeDeviceFamily.SG04LP3, decoded, device_id="deye_site_01")

    assert norm["device_id"] == "deye_site_01"
    assert norm["vendor"] == "Deye / SunSynk"
    assert norm["family"] == "deye_sg04lp3"
    assert norm["pv"]["total_power_w"] == 5500.0
    assert norm["battery"]["power_w"] == 1800.0
    assert norm["battery"]["voltage_v"] == 51.2
    assert norm["battery"]["soc_pct"] == 76.0
    assert norm["battery"]["state"] == "charging"
    assert norm["grid"]["active_power_w"] == 3700.0
    assert norm["energy"]["daily_yield_kwh"] == 24.5


# ---------------------------------------------------------------------------
# Phase D REST API Contract Tests
# ---------------------------------------------------------------------------

def test_phase_d_api_deye_mqtt_families(local):
    """Test GET /api/deye-mqtt/families returns all families and command schema."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    response = client.get("/api/deye-mqtt/families", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "supported_families" in data
    assert len(data["supported_families"]) == 9
    assert "workmode" in data["supported_commands"]
    assert "AT+VER" in data["at_commands_supported"]


def test_phase_d_api_deye_mqtt_telemetry(local):
    """Test POST /api/deye-mqtt/telemetry polls and decodes telemetry."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    payload = {
        "family": "deye_sg01hp3",
        "logger_sn": "1234567890",
        "topic_prefix": "deye",
    }
    response = client.post("/api/deye-mqtt/telemetry", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["family"] == "deye_sg01hp3"
    assert data["logger_sn"] == "1234567890"
    assert "decoded_values" in data
    assert "mqtt_messages" in data
    assert len(data["mqtt_messages"]) > 0
    assert "normalized" in data
    assert data["normalized"]["pv"]["total_power_w"] > 0


def test_phase_d_api_deye_mqtt_command(local):
    """Test POST /api/deye-mqtt/command executes commands with safety gating."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    # WorkMode command (locked)
    payload_wm = {
        "family": "deye_sg04lp3",
        "logger_sn": "1234567890",
        "command_type": "workmode",
        "params": {"mode": 2},
        "unlocked": False,
    }
    resp_wm = client.post("/api/deye-mqtt/command", json=payload_wm, headers=headers)
    assert resp_wm.status_code == 200
    res_data = resp_wm.json()["result"]
    assert res_data["success"] is True
    assert res_data["target_register"] == 142
    assert res_data["status"] == SAFETY_STATUS_LOCKED

    # AT command
    payload_at = {
        "family": "deye_sg04lp3",
        "logger_sn": "1234567890",
        "command_type": "at_command",
        "params": {"command": "AT+VER"},
        "unlocked": False,
    }
    resp_at = client.post("/api/deye-mqtt/command", json=payload_at, headers=headers)
    assert resp_at.status_code == 200
    assert resp_at.json()["dongle_response"].startswith("+ok=")


def test_phase_d_api_deye_mqtt_aggregate(local):
    """Test POST /api/deye-mqtt/aggregate aggregates cluster inverters."""
    from test_workspaces import login

    client, _ = local
    headers = login(local, "operator")

    payload = {
        "inverters": [
            {"logger_id": "master", "ac_power_w": 6000.0, "day_energy_kwh": 30.0, "total_energy_kwh": 10000.0, "battery_power_w": 2000.0},
            {"logger_id": "slave", "ac_power_w": 4000.0, "day_energy_kwh": 20.0, "total_energy_kwh": 8000.0, "battery_power_w": 1500.0},
        ]
    }
    response = client.post("/api/deye-mqtt/aggregate", json=payload, headers=headers)
    assert response.status_code == 200
    data = response.json()["aggregated"]
    assert data["cluster_size"] == 2
    assert data["aggregated_ac_active_power_w"] == 10000.0
    assert data["aggregated_daily_energy_kwh"] == 50.0
