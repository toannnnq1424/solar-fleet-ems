import copy
from datetime import datetime, timedelta, timezone

import pytest
from test_workspaces import login

from solar_fleet.market_trader import MarketTrader, MarketType, OrderDirection


def ev_input():
    return {
        "site_breaker_limit_kw": 10, "available_solar_surplus_kw": 2,
        "building_base_load_kw": 1,
        "chargers": [{"id": "test-port", "name": "Test only", "vehicle_id": "test-car",
                      "soc_pct": 20, "target_soc_pct": 70, "mode": "pv", "priority": 1,
                      "min_current_amps": 6, "max_current_amps": 16,
                      "voltage_per_phase_v": 220, "phases": 1}],
    }


def test_ev_explicit_inputs_reach_engine_without_execution(local):
    client, controller = local
    response = client.post("/api/ev-fleet/optimize-dlm", json=ev_input(), headers=login(local, "operator"))
    assert response.status_code == 200, response.text
    result = response.json()
    assert result["status"] == "ESTIMATED"
    assert result["dispatch_enabled"] is False
    assert result["phase_switching_enabled"] is False
    assert result["total_ev_power_kw"] == 1.98
    assert result["chargers"][0]["vehicle_soc"] == 20
    assert result["chargers"][0]["allocated_amps"] == 9
    assert result["chargers"][0]["vehicle_id"] == "test-car"
    assert result["freshness"]["status"] == "UNKNOWN"
    assert result["freshness"]["telemetry_verified"] is False
    assert controller.store.list("command") == []


@pytest.mark.parametrize("scope", ["site", "charger"])
@pytest.mark.parametrize("value", ["stale", "future", "naive", "invalid"])
def test_ev_rejects_invalid_observation_times(local, scope, value):
    payload = ev_input()
    now = datetime.now(timezone.utc)
    timestamps = {
        "stale": (now - timedelta(seconds=301)).isoformat(),
        "future": (now + timedelta(minutes=1)).isoformat(),
        "naive": now.replace(tzinfo=None).isoformat(),
        "invalid": "not-a-timestamp",
    }
    target = payload if scope == "site" else payload["chargers"][0]
    target["observed_at"] = timestamps[value]
    client, controller = local
    response = client.post("/api/ev-fleet/optimize-dlm", json=payload,
                           headers=login(local, "operator"))
    assert response.status_code == 422
    assert controller.store.list("command") == []


@pytest.mark.parametrize("complete", [True, False])
def test_ev_recent_declarations_are_not_verified_telemetry(local, complete):
    payload = ev_input()
    timestamp = (datetime.now(timezone.utc) - timedelta(seconds=10)).astimezone(
        timezone(timedelta(hours=7))).isoformat()
    payload["observed_at"] = timestamp
    if complete:
        payload["chargers"][0]["observed_at"] = timestamp
    client, controller = local
    response = client.post("/api/ev-fleet/optimize-dlm", json=payload,
                           headers=login(local, "operator"))
    assert response.status_code == 200
    result = response.json()
    assert result["freshness"]["status"] == ("USER_REPORTED_RECENT" if complete else "UNKNOWN")
    assert 10 <= result["freshness"]["age_seconds"]["site"] < 300
    assert result["freshness"]["telemetry_verified"] is False
    assert result["dispatch_enabled"] is False
    assert result["phase_switching_enabled"] is False
    assert controller.store.list("command") == []


@pytest.mark.parametrize("case", ["missing", "duplicate", "mode", "limits", "soc", "nonfinite"])
def test_ev_invalid_inputs_fail_closed(local, case):
    payload = ev_input()
    charger = payload["chargers"][0]
    if case == "missing":
        del charger["voltage_per_phase_v"]
    elif case == "duplicate":
        payload["chargers"].append(copy.deepcopy(charger))
    elif case == "mode":
        charger["mode"] = "pv_plus_min"
    elif case == "limits":
        charger["min_current_amps"] = 20
    elif case == "soc":
        charger["soc_pct"] = None
    else:
        payload["available_solar_surplus_kw"] = "NaN"
    client, _ = local
    response = client.post("/api/ev-fleet/optimize-dlm", json=payload, headers=login(local, "operator"))
    assert response.status_code == 422


def test_three_phase_pv_does_not_draw_grid_to_meet_minimum(local):
    payload = ev_input()
    payload["chargers"][0]["phases"] = 3
    client, _ = local
    result = client.post("/api/ev-fleet/optimize-dlm", json=payload,
                         headers=login(local, "operator")).json()
    assert result["total_ev_power_kw"] == 0


def market_input():
    return {"fleet_capacity_mw": 2, "clearing_prices": {"12": 60},
            "bids": [{"id": "test-bid", "market": "day_ahead", "direction": "sell_discharge",
                      "delivery_hour": 12, "quantity_mw": 1, "price_eur_per_mwh": 40}]}


@pytest.mark.parametrize("case", ["missing_price", "duplicate", "over_capacity", "nonfinite"])
def test_market_invalid_inputs_fail_closed(local, case):
    payload = market_input()
    if case == "missing_price":
        payload["clearing_prices"] = {}
    elif case == "duplicate":
        payload["bids"] *= 2
    elif case == "over_capacity":
        payload["bids"].append({**payload["bids"][0], "id": "other", "quantity_mw": 2})
    else:
        payload["clearing_prices"]["12"] = "Infinity"
    client, _ = local
    response = client.post("/api/market-trader/submit-and-clear", json=payload,
                           headers=login(local, "operator"))
    assert response.status_code == 422


def test_market_calculation_is_not_provider_submission(local):
    client, _ = local
    response = client.post("/api/market-trader/submit-and-clear", json=market_input(),
                           headers=login(local, "operator"))
    assert response.status_code == 200
    assert response.json()["submitted_to_market"] is False
    assert response.json()["net_market_settlement_eur"] == 60


def test_market_engine_checks_all_prices_before_mutating_bids():
    trader = MarketTrader(2)
    first = trader.submit_bid("one", MarketType.DAY_AHEAD, OrderDirection.SELL_DISCHARGE, 12, 1, 40)
    trader.submit_bid("two", MarketType.DAY_AHEAD, OrderDirection.SELL_DISCHARGE, 13, 1, 40)
    with pytest.raises(ValueError, match="finite_delivery_hour_price_required"):
        trader.simulate_auction_clearing({12: 60})
    assert first.status.value == "submitted"