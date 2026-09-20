"""Deterministic EMS rule evaluation. This module never sends or queues commands."""

from __future__ import annotations

import operator
from datetime import datetime
from typing import Literal

from pydantic import Field

from .domain import Model, Sample, utcnow
from .telemetry import refresh_quality


class Condition(Model):
    device_id: str
    metric: str = Field(min_length=1, max_length=160)
    unit: str = Field(min_length=1, max_length=40)
    comparison: Literal["lt", "lte", "gt", "gte", "eq"]
    threshold: float = Field(allow_inf_nan=False)
    max_age_seconds: int = Field(default=300, ge=1, le=300)


class RuleAction(Model):
    device_id: str
    intent: str = Field(min_length=1, max_length=100)
    parameters: dict = Field(default_factory=dict, max_length=30)


class RuleForm(Model):
    site_id: str
    name: str = Field(min_length=1, max_length=120)
    description: str = Field(default="", max_length=2000)
    conditions: list[Condition] = Field(min_length=1, max_length=12)
    actions: list[RuleAction] = Field(min_length=1, max_length=12)


def evaluate(rule: RuleForm, samples: list[Sample], now: datetime | None = None) -> dict:
    """AND conditions, exact units, verified fresh samples, no choice between competing bindings."""
    now = now or utcnow()
    comparisons = {
        "lt": operator.lt,
        "lte": operator.le,
        "gt": operator.gt,
        "gte": operator.ge,
        "eq": operator.eq,
    }
    results = []
    for condition in rule.conditions:
        candidates = [
            refresh_quality(s, condition.max_age_seconds, now)
            for s in samples
            if (s.device_id, s.metric) == (condition.device_id, condition.metric)
        ]
        result = {
            "device_id": condition.device_id,
            "metric": condition.metric,
            "state": "UNKNOWN",
            "reason": "missing_measurement",
            "value": None,
        }
        if len(candidates) > 1:
            result["reason"] = "ambiguous_measurement_source"
        elif candidates:
            sample = candidates[0]
            result.update(source_timestamp=sample.source_timestamp, binding_id=sample.binding_id)
            if sample.stale or sample.quality != "GOOD" or sample.value is None:
                result["reason"] = "fresh_verified_measurement_required"
            elif sample.unit != condition.unit:
                result["reason"] = "unit_mismatch"
            else:
                matches = comparisons[condition.comparison](sample.value, condition.threshold)
                result.update(state="TRUE" if matches else "FALSE", reason="evaluated", value=sample.value)
        results.append(result)
    condition_state = (
        "UNKNOWN"
        if any(r["state"] == "UNKNOWN" for r in results)
        else ("TRUE" if all(r["state"] == "TRUE" for r in results) else "FALSE")
    )
    return {
        "evaluated_at": now,
        "condition_state": condition_state,
        "conditions": results,
        "proposed_actions": [a.model_dump() for a in rule.actions] if condition_state == "TRUE" else [],
        "dispatch_enabled": False,
        "mode": "DRY_RUN",
        "reason": "execution_not_commissioned",
    }
