"""Tests for EV fleet coordinator (dynamic load management, 1p3p phase switching) and wholesale market trader.

Tests:
- Loadpoint power calculations and current bounds
- Dynamic Load Management (DLM) site breaker headroom protection
- Automated 1p3p phase switching with anti-chattering timer
- Vehicle target SOC cutoff (80% battery protection)
- Priority queuing for multiple EV chargers
- Wholesale market order submission (Buy/Sell, DAM/IDM)
- Auction clearing simulation and settlement accounting
- FCR (Frequency Containment Reserve) deadband, proportional response, and capacity revenue
- API endpoints: /api/ev-fleet/optimize-dlm, /api/market-trader/submit-and-clear, /api/market-trader/fcr-response
"""

import pytest

from solar_fleet.ev_fleet_coordinator import (
    ChargePhaseMode,
    ChargingMode,
    EVFleetCoordinator,
    Loadpoint,
)
from solar_fleet.market_trader import (
    FCRController,
    FCRSpecification,
    MarketTrader,
    MarketType,
    OrderDirection,
)

# ---------------------------------------------------------------------------
# EV Fleet Coordinator Tests
# ---------------------------------------------------------------------------

class TestEVFleetCoordinator:
    def test_loadpoint_power_calculation(self):
        lp = Loadpoint(charger_id="cp1", name="Charger 1")
        # 16A on 1-phase: 16 * 230 * 1 / 1000 = 3.68 kW
        p_1p = lp.calculate_power_for_current(16.0, ChargePhaseMode.SINGLE_PHASE)
        assert pytest.approx(p_1p, 0.01) == 3.68

        # 16A on 3-phase: 16 * 230 * 3 / 1000 = 11.04 kW
        p_3p = lp.calculate_power_for_current(16.0, ChargePhaseMode.THREE_PHASE)
        assert pytest.approx(p_3p, 0.01) == 11.04

    def test_dlm_site_breaker_protection(self):
        # 20 kW breaker limit, 12 kW base load -> 8 kW available for EVs
        coord = EVFleetCoordinator(site_breaker_limit_kw=20.0)
        lp1 = Loadpoint(
            charger_id="cp1",
            name="Charger 1",
            connected_vehicle_id="v1",
            mode=ChargingMode.NOW,
            max_current_amps=32.0,
        )
        coord.add_loadpoint(lp1)

        res = coord.update(available_solar_surplus_kw=0.0, building_base_load_kw=12.0)
        assert res["available_headroom_kw"] == 8.0
        assert res["total_ev_power_kw"] <= 8.0

    def test_target_soc_cutoff(self):
        coord = EVFleetCoordinator(site_breaker_limit_kw=40.0)
        lp = Loadpoint(
            charger_id="cp1",
            name="Charger 1",
            connected_vehicle_id="v1",
            vehicle_soc_pct=85.0,  # Over 80% target
            target_soc_pct=80.0,
            mode=ChargingMode.NOW,
        )
        coord.add_loadpoint(lp)

        coord.update(available_solar_surplus_kw=10.0, building_base_load_kw=5.0)
        assert lp.is_charging is False
        assert lp.actual_power_kw == 0.0

    def test_automated_1p3p_switching(self):
        coord = EVFleetCoordinator(site_breaker_limit_kw=40.0, enable_1p3p_switching=True)
        lp = Loadpoint(
            charger_id="cp1",
            name="Charger 1",
            connected_vehicle_id="v1",
            vehicle_soc_pct=50.0,
            mode=ChargingMode.PV,
            allocated_phases=ChargePhaseMode.SINGLE_PHASE,
        )
        coord.add_loadpoint(lp)

        # High solar surplus (8.0 kW >= 4.2 kW threshold) -> switch to 3-phase
        coord.update(
            available_solar_surplus_kw=8.0,
            building_base_load_kw=0.0,
            current_timestamp_seconds=200.0,
        )
        assert lp.allocated_phases == ChargePhaseMode.THREE_PHASE
        assert lp.is_charging is True

        # Solar drops to 2.5 kW (< 3.8 kW hysteresis) after cooldown -> switch back to 1-phase
        coord.update(
            available_solar_surplus_kw=2.5,
            building_base_load_kw=0.0,
            current_timestamp_seconds=400.0,  # 200s > 180s cooldown
        )
        assert lp.allocated_phases == ChargePhaseMode.SINGLE_PHASE


# ---------------------------------------------------------------------------
# Market Trader Tests
# ---------------------------------------------------------------------------

class TestMarketTrader:
    def test_market_order_bidding_and_clearing(self):
        trader = MarketTrader(fleet_capacity_mw=10.0)

        # Submit Buy bid: Willing to pay up to 40 EUR/MWh to charge at hour 2
        trader.submit_bid(
            bid_id="buy_1",
            market=MarketType.DAY_AHEAD,
            direction=OrderDirection.BUY_CHARGE,
            delivery_hour=2,
            quantity_mw=2.0,
            price_eur_per_mwh=40.0,
        )

        # Submit Sell offer: Willing to discharge at hour 19 for at least 80 EUR/MWh
        trader.submit_bid(
            bid_id="sell_1",
            market=MarketType.DAY_AHEAD,
            direction=OrderDirection.SELL_DISCHARGE,
            delivery_hour=19,
            quantity_mw=3.0,
            price_eur_per_mwh=80.0,
        )

        # Simulate clearing with clearing prices: Hour 2 = 25 EUR/MWh, Hour 19 = 110 EUR/MWh
        clearing_prices = {2: 25.0, 19: 110.0}
        res = trader.simulate_auction_clearing(clearing_prices)

        assert res["total_bids"] == 2
        assert res["cleared_bids"] == 2
        # Buy cleared: pays 2 MW * 25 EUR = -50 EUR
        # Sell cleared: receives 3 MW * 110 EUR = +330 EUR
        # Net = +280 EUR
        assert res["net_market_settlement_eur"] == 280.0

    def test_fcr_controller_frequency_response(self):
        spec = FCRSpecification(
            nominal_freq_hz=50.0,
            deadband_hz=0.010,
            full_activation_hz=0.200,
            committed_capacity_mw=2.0,
        )
        fcr = FCRController(spec)

        # Inside deadband (50.005 Hz) -> 0 MW response
        r_dead = fcr.calculate_response(50.005)
        assert r_dead["power_response_mw"] == 0.0
        assert r_dead["activation_mode"] == "deadband"

        # Under-frequency drop (49.800 Hz = full activation -200 mHz) -> full +2.0 MW injection
        r_under = fcr.calculate_response(49.800)
        assert pytest.approx(r_under["power_response_mw"], 0.01) == 2.0
        assert r_under["activation_mode"] == "under_frequency_injection"

        # Over-frequency rise (50.200 Hz = full activation +200 mHz) -> full -2.0 MW absorption
        r_over = fcr.calculate_response(50.200)
        assert pytest.approx(r_over["power_response_mw"], 0.01) == -2.0
        assert r_over["activation_mode"] == "over_frequency_absorption"

        # Check capacity reservation revenue
        assert r_over["hourly_capacity_revenue_eur"] > 0


# ---------------------------------------------------------------------------
# API Integration Tests
# ---------------------------------------------------------------------------

class TestEVFleetAndMarketAPI:
    def _login(self, local):
        client, _ = local
        origin = "http://127.0.0.1:8765"
        password = "SIMULATOR-workspace-password-only"
        res = client.post("/api/login", json={"username": "admin", "password": password}, headers={"Origin": origin})
        assert res.status_code == 200
        return client, {"Origin": origin, "X-CSRF-Token": res.json()["csrf"]}

    def test_ev_fleet_dlm_api(self, local):
        client, headers = self._login(local)
        payload = {
            "site_breaker_limit_kw": 30.0,
            "building_base_load_kw": 5.0,
            "available_solar_surplus_kw": 12.0,
            "chargers": [
                {"id": "cp1", "name": "Bay 1", "vehicle_id": "car1", "soc_pct": 50.0, "mode": "pv", "priority": 1},
                {"id": "cp2", "name": "Bay 2", "vehicle_id": "car2", "soc_pct": 40.0, "mode": "pv", "priority": 2},
            ],
        }
        res = client.post("/api/ev-fleet/optimize-dlm", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["total_ev_power_kw"] > 0
        assert len(data["chargers"]) == 2

    def test_market_trader_api(self, local):
        client, headers = self._login(local)
        payload = {
            "fleet_capacity_mw": 5.0,
            "bids": [
                {"id": "b1", "market": "day_ahead", "direction": "sell_discharge", "delivery_hour": 18, "quantity_mw": 1.5, "price_eur_per_mwh": 60.0}
            ],
            "clearing_prices": {"18": 75.0},
        }
        res = client.post("/api/market-trader/submit-and-clear", json=payload, headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["cleared_bids"] == 1
        assert data["net_market_settlement_eur"] > 0

    def test_fcr_response_api(self, local):
        client, headers = self._login(local)
        res = client.get("/api/market-trader/fcr-response?frequency_hz=49.85&committed_mw=2.0", headers=headers)
        assert res.status_code == 200
        data = res.json()
        assert data["power_response_mw"] > 0  # Under frequency injection
