from datetime import timedelta

import pytest

from solar_fleet.domain import Constraint, Sample, Source, utcnow
from solar_fleet.telemetry import discrepancy, energy_ratios, normalize_points, refresh_quality, select_source


def sample(**values):
    return Sample(
        **(
            {
                "device_id": "SIM",
                "metric": "pv_power_w",
                "value": 1200,
                "unit": "W",
                "source": Source.CLOUD,
                "source_timestamp": utcnow(),
                "quality": "GOOD",
                "stale": False,
                "binding_id": "SIM-CLOUD",
            }
            | values
        )
    )


def test_local_priority_stale_fallback_no_fresh_source():
    cloud = sample()
    local = sample(source=Source.LOCAL, binding_id="SIM-LOCAL")
    assert select_source([cloud, local], 30).source == Source.LOCAL
    local.source_timestamp = utcnow() - timedelta(seconds=60)
    assert select_source([cloud, local], 30).source == Source.CLOUD
    cloud.source_timestamp = None
    assert select_source([cloud, local], 30) is None


def test_future_timestamp_invalid_and_stale():
    result = refresh_quality(sample(source_timestamp=utcnow() + timedelta(minutes=2)), 30)
    assert result.quality == "INVALID" and result.stale


def test_unknown_sign_is_never_inferred_from_vendor_key():
    result = normalize_points("SIM", "SIM", [{"key": "gridPower", "value": -4.2, "unit": "kW"}], utcnow())[0]
    assert (
        result.metric == "native.gridPower"
        and result.value == -4.2
        and result.unit == "kW"
        and result.quality == "UNVERIFIED"
    )


def test_reviewed_sign_and_unit_conversion():
    profile = {
        "simGrid": {
            "verified": True,
            "source_unit": "kW",
            "metric": "grid_export_w",
            "direction": "negative",
            "evidence_ids": ["SIM-TEST"],
        }
    }
    result = normalize_points(
        "SIM", "SIM", [{"key": "simGrid", "value": -4.2, "unit": "kW"}], utcnow(), profile
    )[0]
    assert (
        result.metric == "grid_export_w"
        and result.value == 4200
        and result.unit == "W"
        and result.quality == "GOOD"
    )


def test_wrong_unit_does_not_convert_and_negative_unidirectional_keeps_raw():
    profile = {
        "simPV": {"verified": True, "source_unit": "kW", "metric": "pv_power_w", "evidence_ids": ["SIM-TEST"]}
    }
    raw = normalize_points("SIM", "SIM", [{"key": "simPV", "value": -2, "unit": "kW"}], utcnow(), profile)[0]
    assert raw.metric == "native.simPV" and raw.value == -2 and raw.unit == "kW"
    wrong = normalize_points(
        "SIM", "SIM", [{"key": "simPV", "value": 2, "unit": "unknown"}], utcnow(), profile
    )[0]
    assert wrong.metric == "native.simPV" and wrong.quality == "UNVERIFIED"


@pytest.mark.parametrize("value", [float("nan"), float("inf"), "-Infinity"])
def test_non_finite_values_never_enter_database(value):
    raw = normalize_points("SIM", "SIM", [{"key": "sim", "value": value, "unit": "W"}], utcnow())[0]
    assert raw.value is None and raw.quality == "INVALID"


def test_discrepancy_only_compares_same_unit_device_and_close_time():
    a = sample()
    b = sample(source=Source.LOCAL, value=1500)
    assert discrepancy(a, b, 100) is True
    b.source_timestamp = utcnow() - timedelta(seconds=10)
    assert discrepancy(a, b, 100) is None
    b.unit = "kW"
    with pytest.raises(ValueError):
        discrepancy(a, b, 100)


def test_energy_ratios_do_not_invent_battery_provenance_or_divide_by_zero():
    assert energy_ratios(100, 100, 20, 30) == {"self_consumption_ratio": 0.8, "self_sufficiency_ratio": 0.7}
    assert energy_ratios(0, 0, 0, 0) == {"self_consumption_ratio": None, "self_sufficiency_ratio": None}
    assert energy_ratios(100, 100, 20, 30, battery_present=True) == {
        "self_consumption_ratio": None,
        "self_sufficiency_ratio": None,
    }


@pytest.mark.parametrize("value", [True, -1, 51, 20.5, "20", float("nan")])
def test_parameter_range_step_and_type_are_fail_closed(value):
    with pytest.raises(ValueError):
        Constraint(min=0, max=50, step=1).validate_value(value)


def test_enum_does_not_conflate_bool_and_integer():
    with pytest.raises(ValueError):
        Constraint(enum=[1, 2]).validate_value(True)


def test_undocumented_numeric_unit_stays_unknown_without_dropping_native_reading():
    rows = normalize_points(
        "SIM",
        "SIM",
        [{"key": "power", "value": 20, "unit": 1}],
        utcnow(),
        namespace="solis",
        evidence_ids=["SOLIS_DEV_DATA_002"],
    )
    assert rows[0].value == 20 and rows[0].unit is None and rows[0].quality == "UNVERIFIED"
    assert rows[0].evidence_ids == ["SOLIS_DEV_DATA_002"]


def test_history_deduplicates_original_timestamp_and_retains_distinct_sources(store):
    cloud = sample()
    local = sample(source=Source.LOCAL, binding_id="SIM-LOCAL", source_timestamp=cloud.source_timestamp)
    store.add_samples([cloud, cloud, local])
    assert len(store.history("SIM")) == 2
    for i in range(5):
        store.add_samples([sample(source_timestamp=utcnow() + timedelta(seconds=i))], max_points=3)
    assert store.db.execute("SELECT COUNT(*) FROM samples").fetchone()[0] == 3
