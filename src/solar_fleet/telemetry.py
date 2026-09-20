from __future__ import annotations

from datetime import datetime
from typing import Any

from .domain import Sample, Source, utcnow

UNITS = {
    "W": ("W", 1),
    "kW": ("W", 1000),
    "Wh": ("Wh", 1),
    "kWh": ("Wh", 1000),
    "V": ("V", 1),
    "A": ("A", 1),
    "Hz": ("Hz", 1),
    "%": ("%", 1),
    "°C": ("°C", 1),
}


def refresh_quality(sample: Sample, max_age_seconds: float, now: datetime | None = None) -> Sample:
    now = now or utcnow()
    t = sample.source_timestamp
    age = (now - t).total_seconds() if t else None
    invalid_clock = age is not None and age < -5
    latency = (sample.received_at - t).total_seconds() * 1000 if t else None
    return sample.model_copy(
        update={
            "stale": age is None or age > max_age_seconds or invalid_clock,
            "quality": "INVALID" if invalid_clock else sample.quality,
            "latency_ms": latency,
        }
    )


def select_source(
    samples: list[Sample],
    max_age_seconds: float,
    now: datetime | None = None,
    priority_order: list[str] | None = None,
) -> Sample | None:
    """Select one metric/device; never silently merge different targets or stale sources."""
    if len({(s.device_id, s.metric) for s in samples}) > 1:
        raise ValueError("source selection requires the same device and metric")
    ranked = [refresh_quality(s, max_age_seconds, now) for s in samples]
    valid = [s for s in ranked if not s.stale and s.quality == "GOOD" and s.value is not None]
    priority = {Source.LOCAL: 0, Source.AGENT: 1, Source.CLOUD: 2, Source.SIMULATOR: 3}
    if priority_order is not None:
        priority = {Source(value): index for index, value in enumerate(priority_order)}
        valid = [s for s in valid if s.source in priority]
    if not valid:
        return None
    return min(valid, key=lambda s: (priority[s.source], -s.source_timestamp.timestamp()))


def discrepancy(left: Sample, right: Sample, tolerance: float, max_skew_seconds: float = 5) -> bool | None:
    if (left.device_id, left.metric, left.unit) != (right.device_id, right.metric, right.unit):
        raise ValueError("incompatible samples")
    if any(
        s.quality != "GOOD" or s.stale or s.value is None or s.source_timestamp is None for s in (left, right)
    ):
        return None
    if abs((left.source_timestamp - right.source_timestamp).total_seconds()) > max_skew_seconds:
        return None
    return abs(left.value - right.value) > tolerance


def normalize_points(
    device_id: str,
    binding_id: str,
    points: list[dict[str, Any]],
    timestamp: datetime | None,
    profile: dict[str, dict[str, Any]] | None = None,
    *,
    namespace: str = "native",
    evidence_ids: list[str] | None = None,
) -> list[Sample]:
    """Keep unknown keys raw; adapter profiles supply reviewed metric and sign semantics."""
    result = []
    for point in points:
        key = str(point.get("key", "unknown"))
        mapping = (profile or {}).get(key)
        unit = point.get("unit") if isinstance(point.get("unit"), str) else None
        value = point.get("value")
        try:
            value = float(value) if value is not None and not isinstance(value, bool) else None
        except (ValueError, TypeError):
            value = None
        canonical = bool(
            mapping
            and mapping.get("evidence_ids")
            and mapping.get("verified")
            and unit in UNITS
            and mapping.get("source_unit") == unit
        )
        original_value, original_unit = value, unit
        if canonical and value is not None:
            unit, factor = UNITS[unit]
            value *= factor
            direction = mapping.get("direction", "nonnegative")
            if direction == "positive":
                value = max(0, value)
            elif direction == "negative":
                value = max(0, -value)
            elif value < 0 and mapping["metric"].endswith("_w"):
                canonical = False
        if not canonical:
            value, unit = original_value, original_unit
        try:
            sample = Sample(
                device_id=device_id,
                metric=mapping["metric"] if canonical else f"{namespace}.{key}",
                value=value,
                unit=unit,
                source=Source.CLOUD,
                source_timestamp=timestamp,
                quality="GOOD" if canonical and value is not None else "UNVERIFIED",
                binding_id=binding_id,
                evidence_ids=mapping["evidence_ids"] if canonical else (evidence_ids or []),
            )
        except ValueError:
            sample = Sample(
                device_id=device_id,
                metric=f"{namespace}.{key}",
                value=None,
                unit=original_unit,
                source=Source.CLOUD,
                source_timestamp=timestamp,
                quality="INVALID",
                binding_id=binding_id,
            )
        result.append(refresh_quality(sample, 300))
    return result


def energy_ratios(
    pv_wh: float | None,
    load_wh: float | None,
    export_wh: float | None,
    import_wh: float | None,
    *,
    battery_present: bool = False,
) -> dict[str, float | None]:
    # Battery provenance is required before allocating battery exports/imports to PV.
    if battery_present:
        return {"self_consumption_ratio": None, "self_sufficiency_ratio": None}
    consumed = None if pv_wh is None or export_wh is None or pv_wh <= 0 else (pv_wh - export_wh) / pv_wh
    supplied = (
        None if load_wh is None or import_wh is None or load_wh <= 0 else (load_wh - import_wh) / load_wh
    )
    return {
        "self_consumption_ratio": consumed if consumed is not None and 0 <= consumed <= 1 else None,
        "self_sufficiency_ratio": supplied if supplied is not None and 0 <= supplied <= 1 else None,
    }
