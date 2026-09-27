from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from solar_fleet.observed_energy import accepted_points, integrate_directional_power


def point(stamp, value, **kwargs):
    return dict(metric="battery_discharge_w", unit="W", quality="GOOD", binding_id="test-only",
                source_timestamp=stamp.isoformat(), value=value, **kwargs)


def test_elapsed_time_integration_and_gaps():
    start = datetime(2026, 9, 27, tzinfo=UTC)
    end = start + timedelta(hours=1)
    rows = [point(start, 1000), point(start + timedelta(minutes=6), 2000), point(end, 2000)]
    result = integrate_directional_power(rows, "battery_discharge_w", start, end)
    assert result["energy_kwh"] == pytest.approx(0.15)
    assert result["coverage"] == pytest.approx(0.1)
    assert result["covered_seconds"] == 360


def test_missing_is_not_zero_and_signed_channels_are_rejected():
    now = datetime.now(UTC)
    assert integrate_directional_power([], "grid_import_w", now - timedelta(days=1), now)["energy_kwh"] is None
    with pytest.raises(ValueError, match="directional"):
        integrate_directional_power([], "battery_w", now - timedelta(days=1), now)


@pytest.mark.parametrize("month,day,start_hour,end_hour,elapsed", [
    (3, 8, 1, 3, 3600), (11, 1, 0, 3, 14400),
])
def test_coverage_uses_elapsed_time_across_dst(month, day, start_hour, end_hour, elapsed):
    zone = ZoneInfo("America/New_York")
    start = datetime(2026, month, day, start_hour, tzinfo=zone)
    end = datetime(2026, month, day, end_hour, tzinfo=zone)
    rows = [point(start, 1000), point(end, 1000)]
    result = integrate_directional_power(rows, "battery_discharge_w", start, end, elapsed)
    assert result["covered_seconds"] == elapsed
    assert result["coverage"] == 1
    assert result["energy_kwh"] == elapsed / 3600


def test_repeated_wall_clock_hour_is_a_valid_elapsed_window():
    zone = ZoneInfo("America/New_York")
    start = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=0)
    end = datetime(2026, 11, 1, 1, 30, tzinfo=zone, fold=1)
    result = integrate_directional_power(
        [point(start, 1000), point(end, 1000)], "battery_discharge_w", start, end, 3600,
    )
    assert result["energy_kwh"] == 1
    assert result["coverage"] == 1


def test_source_conflicts_and_unverified_samples_fail_closed():
    now = datetime.now(UTC)
    start = now - timedelta(minutes=5)
    rows = [point(start, 1000), point(now, 1000)]
    rows[1]["binding_id"] = "other-source"
    assert accepted_points(rows, "battery_discharge_w", "W", start, now) == []
    rows[1]["binding_id"] = "test-only"
    rows[0]["quality"] = "UNVERIFIED"
    assert integrate_directional_power(rows, "battery_discharge_w", start, now)["energy_kwh"] is None
    rows[0]["quality"] = "GOOD"
    rows.append(point(now, 1500))
    assert accepted_points(rows, "battery_discharge_w", "W", start, now) == []


@pytest.mark.parametrize("field,value", [
    ("quality", "STALE"), ("quality", "BAD"), ("unit", "kW"),
    ("binding_id", None), ("value", float("nan")), ("value", -1),
    ("source_timestamp", "invalid"), ("source_timestamp", "2026-09-27T00:05:00"),
])
def test_bad_samples_are_not_bridged(field, value):
    start = datetime(2026, 9, 27, tzinfo=UTC)
    end = start + timedelta(minutes=10)
    bad = point(start + timedelta(minutes=5), 1000)
    bad[field] = value
    rows = [point(start, 1000), bad, point(end, 1000)]
    result = integrate_directional_power(rows, "battery_discharge_w", start, end)
    assert result["energy_kwh"] is None
    assert result["coverage"] == 0


def test_bad_duplicate_blocks_adjacent_intervals_but_preserves_good_history():
    start = datetime(2026, 9, 27, tzinfo=UTC)
    rows = [point(start + timedelta(minutes=i), 1000) for i in (0, 5, 10, 15)]
    rows.append({**rows[1], "quality": "BAD"})
    result = integrate_directional_power(rows, "battery_discharge_w", start, start + timedelta(minutes=15))
    assert result["energy_kwh"] == pytest.approx(1 / 12)
    assert result["coverage"] == pytest.approx(1 / 3)