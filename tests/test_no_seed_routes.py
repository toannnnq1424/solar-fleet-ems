import pytest
from test_workspaces import login

from solar_fleet.smartess_local_client import SmartEssLocalClient
from solar_fleet.vendor_registers import decode_vendor_alarm, get_vendor_registers


@pytest.mark.parametrize("simulated", [False, True])
def test_local_client_never_fabricates_poll_or_execution(simulated):
    client = SmartEssLocalClient(simulated=simulated)
    with pytest.raises(NotImplementedError, match="local_transport_unavailable"):
        client.poll_telemetry()
    for unlocked in (False, True):
        result = client.execute_command_safely("output_priority", {"priority": 1}, unlocked=unlocked)
        assert result["status"] == "LOCKED_PENDING_HARDWARE_ACCEPTANCE"
        assert result["readback_verified"] is False


@pytest.mark.parametrize("vendor", ["goodwe", "growatt", "not-goodwe"])
def test_unknown_model_never_gets_register_or_alarm_semantics(vendor):
    assert get_vendor_registers(vendor, "invented-model")["status"] == "UNKNOWN"
    assert get_vendor_registers(vendor, "invented-model")["registers"] == []
    assert decode_vendor_alarm(vendor, 1, "invented-model")["severity"] == "UNKNOWN"


@pytest.mark.parametrize("path,status", [
    ("/goodwe-sems/login", 409),
    ("/goodwe-sems/station-detail", 422),
    ("/goodwe-sems/monthly-report", 422),
    ("/smartess/poll", 409),
    ("/mpc/dispatch", 422),
    ("/predbat/plan", 422),
    ("/load-predictor/predict", 422),
    ("/tariffs/calculate-bill", 422),
    ("/ev-fleet/optimize-dlm", 422),
    ("/market-trader/submit-and-clear", 422),
])
def test_no_input_never_yields_seed_output(local, path, status):
    client, _ = local
    response = client.post("/api" + path, json={}, headers=login(local, "operator"))
    assert response.status_code == status
    assert "token" not in response.json()
    assert "authenticated" not in response.json()


def test_empty_health_and_dispatch_are_not_healthy_or_optimized(local):
    client, _ = local
    login(local, "operator")
    response = client.get("/api/devices/sim-device/battery-health")
    assert response.status_code == 200
    result = response.json()
    assert result["status"] == "INSUFFICIENT_DATA"
    assert result["soh_percent"] is None
    assert result["observed_discharge_kwh"] is None
    assert result["equivalent_full_cycles"] is None
    assert result["warranty_status"] == "UNKNOWN"
    assert client.get("/api/sites/sim-site/dispatch-schedule").status_code == 422


def test_health_uses_actual_latest_observation_and_preserves_zero(local):
    from datetime import timedelta

    from solar_fleet.domain import Sample, Source, utcnow

    client, controller = local
    now = utcnow()
    controller.store.add_samples([
        Sample(device_id="sim-device", metric="battery_soh", value=value, unit="%",
               source=Source.SIMULATOR, source_timestamp=now - timedelta(minutes=minutes),
               quality="GOOD", stale=False, binding_id="fixture-only")
        for minutes, value in [(5, 90), (1, 0)]
    ])
    login(local, "operator")
    result = client.get("/api/devices/sim-device/battery-health").json()
    assert result["soh_percent"] == 0
    assert result["status"] == "MEASURED"
    assert result["operating_temp_c"] is None
    assert result["estimated_remaining_years"] is None
    login(local, "other")
    assert client.get("/api/devices/sim-device/battery-health").status_code == 404


def test_dispatch_engine_uses_stored_history_soc_and_config(local):
    from datetime import timedelta

    from solar_fleet.domain import Sample, Source, utcnow
    from solar_fleet.predbat_planner import BatterySpecs

    client, controller = local
    now = utcnow()
    start = now.replace(minute=0, second=0, microsecond=0)
    site = controller.store.get("site", "sim-site")
    site["dispatch_device_id"] = "sim-device"
    site["dispatch_config"] = {
        **vars(BatterySpecs()),  # Explicit test-only nameplate/cost fixture.
        "currency": "USD", "tariff_source": "TEST_ONLY_NOT_A_REAL_TARIFF",
        "hourly_prices": [{"timestamp": (start + timedelta(hours=h)).isoformat(),
                           "import_per_kwh": 0.2, "export_per_kwh": 0.05} for h in range(24)],
    }
    controller.store.put("site", "sim-site", site)
    samples = [Sample(device_id="sim-device", metric=metric, value=value, unit="W",
                      source=Source.SIMULATOR, source_timestamp=start - timedelta(hours=h, minutes=minute),
                      quality="GOOD", stale=False, binding_id="test-only")
               for h in range(1, 97) for minute in (0, 15, 30, 45)
               for metric, value in (("pv_w", 1000), ("load_w", 1500))]
    samples.append(Sample(device_id="sim-device", metric="battery_soc", value=60, unit="%",
                          source=Source.SIMULATOR, source_timestamp=now - timedelta(seconds=1),
                          quality="GOOD", stale=False, binding_id="test-only"))
    controller.store.add_samples(samples)
    login(local, "operator")
    response = client.get("/api/sites/sim-site/dispatch-schedule")
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "ESTIMATED"
    assert result["dispatch_enabled"] is False
    assert len(result["slots"]) == 24
    assert all(slot["solar_kw"] == 1 and slot["load_kw"] == 1.5 for slot in result["slots"])
    assert controller.store.list("command") == []
    assert controller.store.list("schedule") == []