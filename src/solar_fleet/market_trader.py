"""Wholesale electricity market bidding engine and fast frequency response trader.

Independently implemented for Solar Fleet EMS.
Concepts from virtual-power-plant-main (src/vpp/trading/, src/vpp/grid/)
and vpplib-dev.
No code copied.

Provides:
- Day-Ahead (DAM) and Intraday (IDM) wholesale power market bid generation and clearing
- Frequency Containment Reserve (FCR) primary frequency response service
- automatic Frequency Restoration Reserve (aFRR) AGC tracking
- Settlement accounting for capacity reservation and energy activation
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class MarketType(str, Enum):
    DAY_AHEAD = "day_ahead"
    INTRADAY = "intraday"
    FCR_PRIMARY_RESERVE = "fcr_primary_reserve"
    AFRR_SECONDARY_RESERVE = "afrr_secondary_reserve"


class OrderDirection(str, Enum):
    BUY_CHARGE = "buy_charge"      # Buy power from wholesale market to charge batteries
    SELL_DISCHARGE = "sell_discharge"  # Sell stored battery/solar power to grid


class OrderStatus(str, Enum):
    DRAFT = "draft"
    SUBMITTED = "submitted"
    CLEARED = "cleared"
    PARTIALLY_CLEARED = "partially_cleared"
    REJECTED = "rejected"
    SETTLED = "settled"


# ---------------------------------------------------------------------------
# Market Order & Bids
# ---------------------------------------------------------------------------

@dataclass
class MarketBid:
    """An individual market bid order."""

    bid_id: str
    market: MarketType
    direction: OrderDirection
    delivery_hour: int
    quantity_mw: float
    price_eur_per_mwh: float
    status: OrderStatus = OrderStatus.SUBMITTED
    cleared_quantity_mw: float = 0.0
    settlement_amount_eur: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "bid_id": self.bid_id,
            "market": self.market.value,
            "direction": self.direction.value,
            "delivery_hour": self.delivery_hour,
            "quantity_mw": round(self.quantity_mw, 3),
            "price_eur_per_mwh": round(self.price_eur_per_mwh, 2),
            "status": self.status.value,
            "cleared_quantity_mw": round(self.cleared_quantity_mw, 3),
            "settlement_eur": round(self.settlement_amount_eur, 2),
        }


# ---------------------------------------------------------------------------
# Market Trader Engine
# ---------------------------------------------------------------------------

class MarketTrader:
    """Orchestrates market bidding, auction clearing simulation, and settlements."""

    def __init__(self, fleet_capacity_mw: float = 5.0):
        self.fleet_capacity_mw = fleet_capacity_mw
        self._bids: Dict[str, MarketBid] = {}

    def submit_bid(
        self,
        bid_id: str,
        market: MarketType,
        direction: OrderDirection,
        delivery_hour: int,
        quantity_mw: float,
        price_eur_per_mwh: float,
    ) -> MarketBid:
        """Submit a new wholesale market bid."""
        clamped_mw = max(0.01, min(self.fleet_capacity_mw, quantity_mw))
        bid = MarketBid(
            bid_id=bid_id,
            market=market,
            direction=direction,
            delivery_hour=delivery_hour,
            quantity_mw=clamped_mw,
            price_eur_per_mwh=price_eur_per_mwh,
            status=OrderStatus.SUBMITTED,
        )
        self._bids[bid_id] = bid
        return bid

    def simulate_auction_clearing(
        self,
        clearing_prices_by_hour: Dict[int, float],
    ) -> Dict[str, Any]:
        """Simulate market clearing against hourly market clearing prices."""
        total_revenue_eur = 0.0
        cleared_count = 0
        rejected_count = 0

        for bid in self._bids.values():
            if bid.status != OrderStatus.SUBMITTED:
                continue

            clearing_price = clearing_prices_by_hour.get(bid.delivery_hour, 50.0)

            # Buy orders clear if bid price >= clearing price
            if bid.direction == OrderDirection.BUY_CHARGE:
                if bid.price_eur_per_mwh >= clearing_price:
                    bid.status = OrderStatus.CLEARED
                    bid.cleared_quantity_mw = bid.quantity_mw
                    # Buyer pays clearing price
                    bid.settlement_amount_eur = -(bid.quantity_mw * clearing_price)
                    cleared_count += 1
                else:
                    bid.status = OrderStatus.REJECTED
                    rejected_count += 1

            # Sell orders clear if offer price <= clearing price
            elif bid.direction == OrderDirection.SELL_DISCHARGE:
                if bid.price_eur_per_mwh <= clearing_price:
                    bid.status = OrderStatus.CLEARED
                    bid.cleared_quantity_mw = bid.quantity_mw
                    # Seller receives clearing price
                    bid.settlement_amount_eur = bid.quantity_mw * clearing_price
                    cleared_count += 1
                else:
                    bid.status = OrderStatus.REJECTED
                    rejected_count += 1

            total_revenue_eur += bid.settlement_amount_eur

        return {
            "total_bids": len(self._bids),
            "cleared_bids": cleared_count,
            "rejected_bids": rejected_count,
            "net_market_settlement_eur": round(total_revenue_eur, 2),
        }


# ---------------------------------------------------------------------------
# FCR (Frequency Containment Reserve) Response Model
# ---------------------------------------------------------------------------

@dataclass
class FCRSpecification:
    """ENTSO-E standard FCR primary reserve parameters."""

    nominal_freq_hz: float = 50.0
    deadband_hz: float = 0.010       # +/- 10 mHz deadband
    full_activation_hz: float = 0.200 # +/- 200 mHz full activation
    committed_capacity_mw: float = 2.0
    capacity_price_eur_per_mw_h: float = 18.5  # Availability payment


class FCRController:
    """Sub-second Frequency Containment Reserve activation controller."""

    def __init__(self, spec: Optional[FCRSpecification] = None):
        self.spec = spec or FCRSpecification()

    def calculate_response(self, measured_freq_hz: float) -> Dict[str, Any]:
        """Compute active power response for frequency deviation."""
        delta_f = measured_freq_hz - self.spec.nominal_freq_hz

        if abs(delta_f) <= self.spec.deadband_hz:
            # Inside deadband: zero response
            power_response_mw = 0.0
            mode = "deadband"
        else:
            # Effective deviation beyond deadband
            effective_delta = delta_f - (math.copysign(self.spec.deadband_hz, delta_f))
            # Proportional scaling up to full activation
            activation_range = self.spec.full_activation_hz - self.spec.deadband_hz
            ratio = min(1.0, max(-1.0, effective_delta / activation_range))

            # If freq drops (delta_f < 0), inject power (+ response)
            # If freq rises (delta_f > 0), absorb power (- response)
            power_response_mw = -ratio * self.spec.committed_capacity_mw
            mode = "under_frequency_injection" if power_response_mw > 0 else "over_frequency_absorption"

        return {
            "measured_freq_hz": round(measured_freq_hz, 3),
            "delta_f_hz": round(delta_f, 3),
            "power_response_mw": round(power_response_mw, 3),
            "power_response_kw": round(power_response_mw * 1000.0, 1),
            "activation_mode": mode,
            "committed_capacity_mw": self.spec.committed_capacity_mw,
            "hourly_capacity_revenue_eur": round(self.spec.committed_capacity_mw * self.spec.capacity_price_eur_per_mw_h, 2),
        }
