"""Bounded integration of canonical observations; never invent missing intervals."""

import math
from bisect import bisect_left, bisect_right
from datetime import datetime


def accepted_points(rows, metric, unit, start, end):
    points = {}
    bindings = set()
    for row in rows:
        value = row.get("value")
        if (row.get("metric") != metric or row.get("unit") != unit
                or row.get("quality") != "GOOD" or not row.get("binding_id")
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value)):
            continue
        try:
            stamp = datetime.fromisoformat(row["source_timestamp"])
        except (KeyError, TypeError, ValueError):
            continue
        if stamp.tzinfo is None or not start <= stamp <= end:
            continue
        bindings.add(row["binding_id"])
        if stamp in points and points[stamp] != value:
            return []
        points[stamp] = value
    if len(bindings) != 1:
        return []
    return sorted(points.items())


def integrate_directional_power(rows, metric, start, end, max_gap_seconds=900):
    """Trapezoids in real elapsed time, on explicit nonnegative W channels only.

    No signed battery/grid inference, source mixing, gap filling, or lifetime
    extrapolation. Coverage is relative to the entire requested window.
    """
    if metric not in {"grid_import_w", "grid_export_w", "battery_discharge_w", "battery_charge_w"}:
        raise ValueError("explicit_directional_metric_required")
    if (start.tzinfo is None or end.tzinfo is None or end <= start
            or not math.isfinite(max_gap_seconds) or max_gap_seconds <= 0):
        raise ValueError("valid_window_and_gap_required")
    # Rejected observations are barriers, not permission to interpolate across
    # a known telemetry outage. An unlocatable bad timestamp fails this window closed.
    barriers = []
    invalid_timestamp = False
    for row in rows:
        if row.get("metric") != metric:
            continue
        try:
            stamp = datetime.fromisoformat(row["source_timestamp"])
            if stamp.tzinfo is None:
                raise ValueError("timezone_required")
        except (KeyError, TypeError, ValueError):
            invalid_timestamp = True
            continue
        if not start <= stamp <= end:
            continue
        value = row.get("value")
        if (row.get("unit") != "W" or row.get("quality") != "GOOD" or not row.get("binding_id")
                or isinstance(value, bool) or not isinstance(value, (int, float))
                or not math.isfinite(value) or value < 0):
            barriers.append(stamp)
    barriers.sort()
    points = accepted_points(rows, metric, "W", start, end)
    if invalid_timestamp:
        points = []
    intervals, seconds = [], 0.0
    for (left, a), (right, b) in zip(points, points[1:]):
        duration = (right - left).total_seconds()
        if a < 0 or b < 0 or not 0 < duration <= max_gap_seconds:
            continue
        if bisect_right(barriers, right) > bisect_left(barriers, left):
            continue
        intervals.append((left, (a + b) / 2 * duration / 3_600_000))
        seconds += duration
    window = (end - start).total_seconds()
    return {
        "energy_kwh": sum(value for _, value in intervals) if intervals else None,
        "intervals": intervals,
        "covered_seconds": seconds,
        "coverage": seconds / window if window > 0 else 0.0,
        "method": "OBSERVED_TRAPEZOIDAL_NO_GAP_FILL",
    }