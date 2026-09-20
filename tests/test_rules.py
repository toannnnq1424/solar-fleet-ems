from datetime import timedelta

import pytest

from solar_fleet.domain import Sample, Source, utcnow
from solar_fleet.rules import RuleForm, evaluate


@pytest.fixture
def rule():
    return RuleForm(
        site_id="sim-site",
        name="SIMULATOR reserve",
        conditions=[
            {
                "device_id": "sim-device",
                "metric": "battery_soc_percent",
                "unit": "%",
                "comparison": "lt",
                "threshold": 30,
            }
        ],
        actions=[{"device_id": "sim-device", "intent": "SET_RESERVE_SOC", "parameters": {"value": 40}}],
    )


def sample(**kwargs):
    return Sample.model_validate(
        {
            "device_id": "sim-device",
            "metric": "battery_soc_percent",
            "value": 20,
            "unit": "%",
            "source": Source.SIMULATOR,
            "source_timestamp": utcnow(),
            "quality": "GOOD",
            "binding_id": "SIMULATOR",
            **kwargs,
        }
    )


@pytest.mark.parametrize(
    "change",
    [
        {"source_timestamp": None},
        {"source_timestamp": utcnow() - timedelta(hours=1)},
        {"source_timestamp": utcnow() + timedelta(hours=1)},
        {"quality": "UNVERIFIED"},
        {"unit": "kW"},
        {"value": None},
    ],
)
def test_unknown_or_invalid_measurement_never_proposes_action(rule, change):
    result = evaluate(rule, [sample(**change)])
    assert result["condition_state"] == "UNKNOWN" and result["proposed_actions"] == []
    assert result["dispatch_enabled"] is False


def test_competing_sources_are_not_implicitly_selected(rule):
    result = evaluate(rule, [sample(), sample(binding_id="SIMULATOR-other")])
    assert result["conditions"][0]["reason"] == "ambiguous_measurement_source"


def test_dry_run_proposes_only_when_all_conditions_match(rule):
    result = evaluate(rule, [sample()])
    assert result["condition_state"] == "TRUE" and len(result["proposed_actions"]) == 1
    assert result["dispatch_enabled"] is False and result["mode"] == "DRY_RUN"
    assert evaluate(rule, [sample(value=50)])["condition_state"] == "FALSE"
    assert evaluate(rule, [])["condition_state"] == "UNKNOWN"
