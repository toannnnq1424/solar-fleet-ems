"""Explainable hourly baseline adapted from SEM's MIT HourlyProfile algorithm.

Copyright (c) 2025 belinea4071; see data/licenses/sem-community-MIT.txt.
Source: traktore-org/sem-community, analytics/consumption_predictor.py.
Changes: train from bounded verified history, actual dates/UTC buckets, explicit
missing values, sampling coverage and source isolation. This is not an optimizer
or a forecast-accuracy estimate, and never proposes or sends device commands.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException

from .domain import utcnow


class HourlyProfile:
    """SEM's exponentially weighted weekday/hour bins and same-hour fallback."""

    def __init__(self, alpha=0.3):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.bins = {}
        self.counts = defaultdict(int)

    def update(self, dow, hour, value):
        if not 0 <= dow <= 6 or not 0 <= hour <= 23 or not math.isfinite(value) or value < 0:
            raise ValueError("invalid hourly observation")
        key = (dow, hour)
        self.bins[key] = (
            value if key not in self.bins else self.alpha * value + (1 - self.alpha) * self.bins[key]
        )
        self.counts[key] += 1

    def predict(self, dow, hour):
        key = (dow, hour)
        if key in self.bins:
            return self.bins[key], "WEEKDAY_HOUR", self.counts[key]
        values = [value for (_, h), value in self.bins.items() if h == hour]
        if values:
            return (
                sum(values) / len(values),
                "SAME_HOUR_FALLBACK",
                sum(count for (_, h), count in self.counts.items() if h == hour),
            )
        return None, "NO_OBSERVATIONS", 0


def baseline(rows: list[dict], timezone: str, now: datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("timezone-aware forecast timestamp required")
    zone = ZoneInfo(timezone)
    start = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    result = {
        "method": "HOURLY_EWMA",
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "horizon_hours": 24,
        "accuracy": None,
        "dispatch_enabled": False,
        "metrics": {},
    }
    for metric in ("pv_w", "load_w"):
        valid = []
        for row in rows:
            if row["metric"] != metric or row["quality"] != "GOOD" or row["unit"] != "W":
                continue
            value = row["value"]
            if value is None or not math.isfinite(value) or value < 0 or not row["source_timestamp"]:
                continue
            stamp = datetime.fromisoformat(row["source_timestamp"])
            if stamp.tzinfo is not None and start - timedelta(days=7) <= stamp < start:
                valid.append((stamp.astimezone(UTC), value, row["binding_id"]))
        series = {"training_days": 0, "training_hours": 0, "points": [], "status": "COLD_START"}
        result["metrics"][metric] = series
        bindings = {binding for _, _, binding in valid}
        if len(bindings) != 1 or None in bindings:
            series["status"] = "SINGLE_VERIFIED_SOURCE_REQUIRED"
            continue
        # Equal weight to quarter-hour bins prevents a noisy high-rate source
        # from dominating an hourly average. A missing quarter stays missing.
        hours = defaultdict(lambda: defaultdict(list))
        seen = {}
        for stamp, value, _ in valid:
            if stamp in seen and seen[stamp] != value:
                series["status"] = "CONFLICTING_OBSERVATIONS"
                break
            seen[stamp] = value
        if series["status"] == "CONFLICTING_OBSERVATIONS":
            continue
        for stamp, value in seen.items():
            hours[stamp.replace(minute=0, second=0, microsecond=0)][stamp.minute // 15].append(value)
        model = HourlyProfile()
        days = set()
        latest = None
        for stamp, quarters in sorted(hours.items()):
            if len(quarters) < 3:
                continue
            local = stamp.astimezone(zone)
            hourly_mean = sum(sum(q) / len(q) for q in quarters.values()) / len(quarters)
            model.update(local.weekday(), local.hour, hourly_mean)
            days.add(local.date())
            series["training_hours"] += 1
            latest = stamp
        series["training_days"] = len(days)
        if len(days) < 3 or series["training_hours"] < 24:
            continue
        if latest is None or start - latest > timedelta(hours=3):
            series["status"] = "STALE_TRAINING_DATA"
            continue
        series["status"] = "BASELINE_ONLY"
        for offset in range(24):
            stamp = start + timedelta(hours=offset)
            local = stamp.astimezone(zone)
            value, method, observations = model.predict(local.weekday(), local.hour)
            series["points"].append(
                {
                    "timestamp": stamp.isoformat(),
                    "local_time": local.isoformat(),
                    "value_w": value,
                    "method": method,
                    "observations": observations,
                }
            )
    return result


def install_forecast_baseline(app, controller, user):
    @app.get("/api/devices/{device_id}/forecast-baseline")
    def forecast(device_id: str, who=Depends(user)):
        device = controller.store.get("device", device_id)
        if not device or not who.can_access(device["site_id"]):
            raise HTTPException(404, "device_not_found")
        site = controller.store.get("site", device["site_id"])
        now = utcnow()
        rows = []
        for metric in ("pv_w", "load_w"):
            selected = controller.store.report_samples(device_id, now - timedelta(days=7), now, metric, 10001)
            if len(selected) > 10000:
                raise HTTPException(422, "forecast_history_limit; use a reviewed rollup before training")
            rows.extend(selected)
        return baseline(rows, site.get("timezone", "UTC"), now)
