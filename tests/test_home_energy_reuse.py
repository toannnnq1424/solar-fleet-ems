"""Local read contracts and advisory forecasts; no external services or hardware."""

from datetime import UTC, datetime, timedelta

import httpx
import pytest
from pydantic import ValidationError
from test_management_runtime import enroll
from test_workspaces import login

from solar_fleet.domain import utcnow
from solar_fleet.forecast_baseline import HourlyProfile, baseline
from solar_fleet.home_assistant_bridge import HomeAssistantProfile, collect_home_assistant

NOW = datetime(2026, 9, 27, 12, tzinfo=UTC)


def ha_profile(**changes):
    return HomeAssistantProfile.model_validate(
        {
            "agent_id": "SIM-AGENT",
            "base_url": "http://192.168.50.2:8123",
            "bindings": [{"entity_id": "sensor.pv", "device_id": "sim-device", "expected_unit": "W"}],
            "reviewed_by": "TEST",
            "evidence_reference": "SIMULATOR-ONLY",
            **changes,
        }
    )


def entity(**changes):
    return {
        "entity_id": "sensor.pv",
        "state": "1250.5",
        "attributes": {"unit_of_measurement": "W"},
        "last_reported": NOW.isoformat(),
        "last_updated": (NOW - timedelta(days=1)).isoformat(),
        **changes,
    }


def collect(payload, profile=None, status=200, now=NOW):
    calls = []

    def respond(request):
        calls.append(request)
        assert request.method == "GET" and request.url.path.startswith("/api/states/sensor.")
        assert request.headers["authorization"] == "Bearer TEST-ONLY"
        return httpx.Response(status, json=payload)

    with httpx.Client(transport=httpx.MockTransport(respond)) as client:
        points = collect_home_assistant(profile or ha_profile(), "TEST-ONLY", client=client, now=now)
    return points, calls


def test_ha_reads_explicit_entity_units_and_acquisition_time():
    points, calls = collect(entity())
    assert len(calls) == 1
    assert points == [
        {
            "device_id": "sim-device",
            "key": "ha.sensor.pv",
            "value": 1250.5,
            "unit": "W",
            "timestamp": NOW.isoformat(),
        }
    ]


@pytest.mark.parametrize("state", ["unknown", "unavailable", None])
def test_ha_missing_is_never_zero(state):
    points, _ = collect(entity(state=state))
    assert points[0]["value"] is None


@pytest.mark.parametrize(
    "changes",
    [
        {"entity_id": "sensor.unrequested"},
        {"attributes": {"unit_of_measurement": "kW"}},
        {"state": "NaN"},
        {"state": "Infinity"},
        {"state": True},
        {"state": "on"},
        {"last_reported": (NOW - timedelta(minutes=6)).isoformat()},
        {"last_reported": (NOW + timedelta(seconds=6)).isoformat()},
        {"last_reported": "2026-09-27T12:00:00"},
    ],
)
def test_ha_rejects_schema_semantics_or_freshness_changes(changes):
    with pytest.raises((ValueError, TypeError)):
        collect(entity(**changes))


def test_ha_legacy_timestamp_fallback_is_conservative():
    with pytest.raises(ValueError, match="stale"):
        collect(entity(last_reported=None))
    points, _ = collect(entity(last_reported=None, last_updated=NOW.isoformat()))
    assert points[0]["timestamp"] == NOW.isoformat()


@pytest.mark.parametrize("status", [301, 401, 403, 404, 429, 503])
def test_ha_http_failures_do_not_create_measurements(status):
    with pytest.raises(httpx.HTTPStatusError):
        collect(entity(), status=status)


def test_ha_response_size_is_bounded():
    with pytest.raises(ValueError, match="too large"):
        collect(entity(attributes={"unit_of_measurement": "W", "oversize": "x" * 128001}))


@pytest.mark.parametrize(
    "url",
    [
        "https://example.com",
        "http://127.0.0.1:8123",
        "http://8.8.8.8",
        "http://user:secret@192.168.1.2",
        "http://192.168.1.2/api",
        "http://192.168.1.2?token=x",
        "file:///tmp/ha",
    ],
)
def test_ha_requires_configured_local_origin_without_secrets(url):
    with pytest.raises(ValidationError):
        ha_profile(base_url=url)


def test_ha_configuration_scope_and_machine_ingestion(local):
    client, ctl = local
    agent, headers = enroll(local)
    config = ha_profile(agent_id=agent["id"])
    response = client.post(
        "/api/local-collection/home-assistant/validate", headers=headers, json=config.model_dump(mode="json")
    )
    assert response.status_code == 200 and not response.json()["connection_tested"]
    current = utcnow()
    points, _ = collect(entity(last_reported=current.isoformat()), config, now=current)
    client.cookies.clear()
    response = client.post(
        "/api/agent/inbox",
        headers={"Authorization": "Bearer " + agent["token"]},
        json={"agent_id": agent["id"], "sequence": 1, "version": "TEST", "points": points},
    )
    assert response.status_code == 200, response.text
    login(local)
    context = client.get("/api/devices/sim-device/mapping-context").json()
    channel = next(c for c in context["channels"] if c["metric"] == "agent.native.ha.sensor.pv")
    assert channel["quality"] == "UNVERIFIED" and channel["value"] == 1250.5
    assert not ctl.store.commands()


def samples(now=NOW, days=4, quarter_count=4, **overrides):
    start = now.replace(minute=0, second=0, microsecond=0) - timedelta(days=days)
    return [
        {
            "metric": "load_w",
            "quality": "GOOD",
            "unit": "W",
            "value": 1000,
            "source_timestamp": (start + timedelta(hours=h, minutes=q * 15)).isoformat(),
            "binding_id": "SIM-BINDING",
            **overrides,
        }
        for h in range(days * 24)
        for q in range(quarter_count)
    ]


def test_hourly_ewma_fallback_and_missing_values():
    model = HourlyProfile()
    model.update(0, 8, 1000)
    model.update(0, 8, 2000)
    assert model.predict(0, 8) == (1300, "WEEKDAY_HOUR", 2)
    assert model.predict(1, 8) == (1300, "SAME_HOUR_FALLBACK", 2)
    assert model.predict(1, 9) == (None, "NO_OBSERVATIONS", 0)


def test_baseline_counts_dates_and_requires_verified_source():
    result = baseline(samples(), "Asia/Ho_Chi_Minh", NOW)
    series = result["metrics"]["load_w"]
    assert series["status"] == "BASELINE_ONLY" and series["training_hours"] == 96
    assert series["training_days"] == 5  # four UTC days straddle five local dates
    assert len(series["points"]) == 24 and all(p["value_w"] == 1000 for p in series["points"])
    assert result["accuracy"] is None and not result["dispatch_enabled"]
    assert result["metrics"]["pv_w"]["points"] == []


@pytest.mark.parametrize(
    "changes",
    [
        {"quality": "UNVERIFIED"},
        {"unit": "kW"},
        {"binding_id": None},
        {"value": -1},
        {"value": None},
        {"value": float("nan")},
    ],
)
def test_baseline_does_not_train_on_native_missing_or_wrong_unit(changes):
    assert baseline(samples(**changes), "UTC", NOW)["metrics"]["load_w"]["points"] == []


def test_baseline_rejects_binding_mixes_and_conflicting_duplicates():
    rows = samples()
    rows[-1]["binding_id"] = "OTHER"
    assert baseline(rows, "UTC", NOW)["metrics"]["load_w"]["status"] == "SINGLE_VERIFIED_SOURCE_REQUIRED"
    rows = samples()
    rows.append(rows[-1] | {"value": 999})
    assert baseline(rows, "UTC", NOW)["metrics"]["load_w"]["status"] == "CONFLICTING_OBSERVATIONS"


def test_baseline_sparse_stale_history_and_future_samples():
    assert baseline(samples(quarter_count=2), "UTC", NOW)["metrics"]["load_w"]["status"] == "COLD_START"
    rows = samples(now=NOW - timedelta(hours=4))
    assert baseline(rows, "UTC", NOW)["metrics"]["load_w"]["status"] == "STALE_TRAINING_DATA"
    rows = samples()
    rows.append(rows[-1] | {"value": 99999, "source_timestamp": (NOW + timedelta(hours=1)).isoformat()})
    result = baseline(rows, "UTC", NOW)["metrics"]["load_w"]
    assert all(p["value_w"] == 1000 for p in result["points"])


def test_baseline_dst_fall_back_keeps_distinct_instants():
    now = datetime(2026, 10, 25, tzinfo=UTC)
    series = baseline(samples(now=now), "Europe/Berlin", now)["metrics"]["load_w"]
    assert len({p["timestamp"] for p in series["points"]}) == 24
    assert "T02:00:00+02:00" in series["points"][0]["local_time"]
    assert "T02:00:00+01:00" in series["points"][1]["local_time"]


def test_forecast_api_enforces_scope_and_history_limit(local, monkeypatch):
    client, ctl = local
    assert client.get("/api/devices/sim-device/forecast-baseline").status_code == 401
    login(local, "other")
    assert client.get("/api/devices/sim-device/forecast-baseline").status_code == 404
    login(local, "viewer")
    result = client.get("/api/devices/sim-device/forecast-baseline")
    assert result.status_code == 200 and not result.json()["dispatch_enabled"]
    monkeypatch.setattr(ctl.store, "report_samples", lambda *args: [{}] * 10001)
    assert client.get("/api/devices/sim-device/forecast-baseline").status_code == 422
    assert not ctl.store.commands()
