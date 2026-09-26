from datetime import UTC, datetime, timedelta

from solar_fleet.operational_views import flow_snapshot

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


def channel(metric, value, **changes):
    return {
        "device_id": "SIM",
        "binding_id": "SIM-BIND",
        "source": "AGENT",
        "metric": metric,
        "unit": "W",
        "quality": "GOOD",
        "source_timestamp": NOW.isoformat(),
        "value": value,
        **changes,
    }


def test_flow_reports_direction_and_expiry_without_allocating_source_to_load():
    channels = {
        key: channel(key, value)
        for key, value in {
            "pv_w": 5000,
            "load_w": 3000,
            "grid_import_w": 0,
            "grid_export_w": 500,
            "battery_charge_w": 1500,
            "battery_discharge_w": 0,
        }.items()
    }
    result = flow_snapshot([channels], now=NOW)
    assert result["grid_w"] == -500 and result["battery_w"] == 1500
    assert result["channels"]["grid_w"]["quality"] == "GOOD"
    assert result["channels"]["pv_w"]["valid_until"] == (NOW + timedelta(seconds=300)).isoformat()
    assert result["eps_w"] is None and not result["topology_verified"]
    assert "solar_to_load" not in result


def test_flow_does_not_net_different_devices_sources_or_unaligned_timestamps():
    for changes, reason in [
        ({"device_id": "OTHER"}, "SOURCE_MISMATCH"),
        ({"binding_id": "OTHER"}, "SOURCE_MISMATCH"),
        ({"source": "CLOUD"}, "SOURCE_MISMATCH"),
        ({"source_timestamp": (NOW - timedelta(seconds=6)).isoformat()}, "TIME_SKEW"),
    ]:
        result = flow_snapshot(
            [
                {"grid_import_w": channel("grid_import_w", 100)},
                {"grid_export_w": channel("grid_export_w", 10, **changes)},
            ],
            now=NOW,
        )
        assert result["grid_w"] is None and result["channels"]["grid_w"]["quality"] == reason


def test_flow_ambiguous_stale_invalid_and_missing_stay_null():
    row = {"pv_w": channel("pv_w", 500)}
    result = flow_snapshot([row, row], now=NOW)
    assert result["pv_w"] is None and result["channels"]["pv_w"]["quality"] == "AMBIGUOUS"
    for changes in [
        {"quality": "UNVERIFIED"},
        {"value": -1},
        {"unit": "kW"},
        {"source_timestamp": (NOW - timedelta(seconds=301)).isoformat()},
    ]:
        assert flow_snapshot([{"pv_w": channel("pv_w", 500) | changes}], now=NOW)["pv_w"] is None
    assert flow_snapshot([], now=NOW)["has_readings"] is False
