"""Tariff catalogue and dynamic pricing engine.

Independently implemented for Solar Fleet EMS.
Concepts from evcc-master tariff/ (awattar, tibber, octopus, fixed),
batpred-main tariff_catalogue.py and futurerate.py,
and OpenEMS controller.ess.timeofusetariff — no code copied.

Supports: fixed, time-of-use, dynamic spot, feed-in, demand charges,
carbon intensity, multi-rate, and tariff comparison.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class TariffType(str, Enum):
    FIXED = "fixed"
    TIME_OF_USE = "time_of_use"
    DYNAMIC_SPOT = "dynamic_spot"
    FEED_IN = "feed_in"
    DEMAND = "demand_charge"
    CARBON = "carbon_intensity"


class TimeSlot(str, Enum):
    PEAK = "peak"
    SHOULDER = "shoulder"
    OFF_PEAK = "off_peak"
    SUPER_OFF_PEAK = "super_off_peak"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class PriceSlot:
    """A single price period."""

    start_hour: int
    end_hour: int
    price_per_kwh: float
    slot_type: TimeSlot = TimeSlot.SHOULDER
    currency: str = "USD"

    def contains_hour(self, hour: int) -> bool:
        if self.start_hour <= self.end_hour:
            return self.start_hour <= hour < self.end_hour
        # Wraps midnight
        return hour >= self.start_hour or hour < self.end_hour

    def to_dict(self) -> dict[str, Any]:
        return {
            "start_hour": self.start_hour,
            "end_hour": self.end_hour,
            "price_per_kwh": round(self.price_per_kwh, 4),
            "slot_type": self.slot_type.value,
            "currency": self.currency,
        }


@dataclass
class TariffPlan:
    """Complete tariff plan definition."""

    name: str
    tariff_type: TariffType
    currency: str = "USD"
    import_slots: List[PriceSlot] = field(default_factory=list)
    export_slots: List[PriceSlot] = field(default_factory=list)
    demand_charge_per_kw: float = 0.0
    fixed_daily_charge: float = 0.0
    gst_pct: float = 0.0

    def import_rate(self, hour: int) -> float:
        """Get import rate for hour."""
        for slot in self.import_slots:
            if slot.contains_hour(hour):
                return slot.price_per_kwh
        return 0.10  # fallback

    def export_rate(self, hour: int) -> float:
        """Get export rate for hour."""
        for slot in self.export_slots:
            if slot.contains_hour(hour):
                return slot.price_per_kwh
        return 0.04

    def hourly_import_rates(self) -> List[float]:
        """Get 24-hour import rate profile."""
        return [self.import_rate(h) for h in range(24)]

    def hourly_export_rates(self) -> List[float]:
        """Get 24-hour export rate profile."""
        return [self.export_rate(h) for h in range(24)]

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "type": self.tariff_type.value,
            "currency": self.currency,
            "import_slots": [s.to_dict() for s in self.import_slots],
            "export_slots": [s.to_dict() for s in self.export_slots],
            "demand_charge_per_kw": self.demand_charge_per_kw,
            "fixed_daily_charge": self.fixed_daily_charge,
        }


# ---------------------------------------------------------------------------
# Pre-built tariff plans
# ---------------------------------------------------------------------------

TARIFF_CATALOGUE: Dict[str, TariffPlan] = {
    "vn_evn_residential": TariffPlan(
        name="Vietnam EVN Residential",
        tariff_type=TariffType.FIXED,
        currency="VND",
        import_slots=[
            PriceSlot(0, 24, 1920.0, TimeSlot.SHOULDER, "VND"),
        ],
        export_slots=[
            PriceSlot(0, 24, 1300.0, TimeSlot.SHOULDER, "VND"),
        ],
    ),
    "vn_evn_commercial_tou": TariffPlan(
        name="Vietnam EVN Commercial TOU",
        tariff_type=TariffType.TIME_OF_USE,
        currency="VND",
        import_slots=[
            PriceSlot(22, 4, 1100.0, TimeSlot.OFF_PEAK, "VND"),
            PriceSlot(4, 10, 1800.0, TimeSlot.SHOULDER, "VND"),
            PriceSlot(10, 12, 2800.0, TimeSlot.PEAK, "VND"),
            PriceSlot(12, 17, 1800.0, TimeSlot.SHOULDER, "VND"),
            PriceSlot(17, 20, 2800.0, TimeSlot.PEAK, "VND"),
            PriceSlot(20, 22, 1800.0, TimeSlot.SHOULDER, "VND"),
        ],
        export_slots=[
            PriceSlot(0, 24, 1500.0, TimeSlot.SHOULDER, "VND"),
        ],
        demand_charge_per_kw=50000.0,
    ),
    "au_amber_spot": TariffPlan(
        name="Australia Amber Spot",
        tariff_type=TariffType.DYNAMIC_SPOT,
        currency="AUD",
        import_slots=[
            PriceSlot(0, 6, 0.08, TimeSlot.OFF_PEAK, "AUD"),
            PriceSlot(6, 15, 0.15, TimeSlot.SHOULDER, "AUD"),
            PriceSlot(15, 21, 0.35, TimeSlot.PEAK, "AUD"),
            PriceSlot(21, 24, 0.12, TimeSlot.SHOULDER, "AUD"),
        ],
        export_slots=[
            PriceSlot(0, 6, 0.02, TimeSlot.OFF_PEAK, "AUD"),
            PriceSlot(6, 15, 0.08, TimeSlot.SHOULDER, "AUD"),
            PriceSlot(15, 21, 0.12, TimeSlot.PEAK, "AUD"),
            PriceSlot(21, 24, 0.04, TimeSlot.SHOULDER, "AUD"),
        ],
    ),
    "de_awattar": TariffPlan(
        name="Germany Awattar HOURLY",
        tariff_type=TariffType.DYNAMIC_SPOT,
        currency="EUR",
        import_slots=[
            PriceSlot(0, 6, 0.20, TimeSlot.OFF_PEAK, "EUR"),
            PriceSlot(6, 8, 0.28, TimeSlot.SHOULDER, "EUR"),
            PriceSlot(8, 20, 0.32, TimeSlot.PEAK, "EUR"),
            PriceSlot(20, 24, 0.22, TimeSlot.OFF_PEAK, "EUR"),
        ],
        export_slots=[
            PriceSlot(0, 24, 0.08, TimeSlot.SHOULDER, "EUR"),
        ],
    ),
    "uk_octopus_agile": TariffPlan(
        name="UK Octopus Agile",
        tariff_type=TariffType.DYNAMIC_SPOT,
        currency="GBP",
        import_slots=[
            PriceSlot(0, 5, 0.07, TimeSlot.SUPER_OFF_PEAK, "GBP"),
            PriceSlot(5, 16, 0.20, TimeSlot.SHOULDER, "GBP"),
            PriceSlot(16, 19, 0.35, TimeSlot.PEAK, "GBP"),
            PriceSlot(19, 24, 0.15, TimeSlot.SHOULDER, "GBP"),
        ],
        export_slots=[
            PriceSlot(0, 24, 0.15, TimeSlot.SHOULDER, "GBP"),
        ],
    ),
    "us_tou_residential": TariffPlan(
        name="US Residential TOU",
        tariff_type=TariffType.TIME_OF_USE,
        currency="USD",
        import_slots=[
            PriceSlot(0, 7, 0.08, TimeSlot.OFF_PEAK),
            PriceSlot(7, 14, 0.12, TimeSlot.SHOULDER),
            PriceSlot(14, 19, 0.28, TimeSlot.PEAK),
            PriceSlot(19, 21, 0.12, TimeSlot.SHOULDER),
            PriceSlot(21, 24, 0.08, TimeSlot.OFF_PEAK),
        ],
        export_slots=[
            PriceSlot(0, 24, 0.05, TimeSlot.SHOULDER),
        ],
        demand_charge_per_kw=5.0,
    ),
}


# ---------------------------------------------------------------------------
# Dynamic pricing feed
# ---------------------------------------------------------------------------

@dataclass
class SpotPrice:
    """A single spot price point."""

    timestamp_utc: str
    price: float
    currency: str = "EUR"
    source: str = ""


class DynamicPricingFeed:
    """Dynamic spot price feed adapter.

    Concept from evcc awattar/tibber/octopus clients.
    Provides hourly spot prices for optimization.
    """

    def __init__(self, source: str = "manual") -> None:
        self.source = source
        self._prices: List[SpotPrice] = []

    def set_prices(self, prices: List[SpotPrice]) -> None:
        """Set spot prices manually (for simulation)."""
        self._prices = prices

    def get_current_price(self) -> Optional[SpotPrice]:
        """Get current spot price."""
        if not self._prices:
            return None
        return self._prices[0]

    def get_hourly_prices(self, hours: int = 24) -> List[float]:
        """Get next N hours of prices."""
        return [p.price for p in self._prices[:hours]]

    def cheapest_hours(
        self, n_hours: int, window: int = 24,
    ) -> List[int]:
        """Find N cheapest hours in the next window.

        Used for optimal charge scheduling.
        """
        prices_window = self._prices[:window]
        if not prices_window:
            return list(range(n_hours))

        indexed = list(enumerate(prices_window))
        indexed.sort(key=lambda x: x[1].price)
        cheapest = sorted([i for i, _ in indexed[:n_hours]])
        return cheapest

    def most_expensive_hours(
        self, n_hours: int, window: int = 24,
    ) -> List[int]:
        """Find N most expensive hours for discharge."""
        prices_window = self._prices[:window]
        if not prices_window:
            return list(range(n_hours))

        indexed = list(enumerate(prices_window))
        indexed.sort(key=lambda x: x[1].price, reverse=True)
        expensive = sorted([i for i, _ in indexed[:n_hours]])
        return expensive


# ---------------------------------------------------------------------------
# Carbon intensity tracker
# ---------------------------------------------------------------------------

@dataclass
class CarbonIntensity:
    """Carbon intensity of grid electricity."""

    timestamp_utc: str = ""
    intensity_gco2_per_kwh: float = 400.0
    source: str = "average"
    forecast: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "intensity_gco2_per_kwh": round(
                self.intensity_gco2_per_kwh, 1,
            ),
            "source": self.source,
        }


class CarbonTracker:
    """Track and optimize for carbon intensity.

    Concept from evcc-master electricitymaps tariff.
    """

    def __init__(self, default_intensity: float = 400.0) -> None:
        self.default_intensity = default_intensity
        self._data: List[CarbonIntensity] = []

    def set_forecast(
        self, intensities: List[CarbonIntensity],
    ) -> None:
        self._data = intensities

    def current_intensity(self) -> float:
        if self._data:
            return self._data[0].intensity_gco2_per_kwh
        return self.default_intensity

    def greenest_hours(
        self, n_hours: int, window: int = 24,
    ) -> List[int]:
        """Find hours with lowest carbon intensity."""
        data = self._data[:window]
        if not data:
            return list(range(n_hours))
        indexed = list(enumerate(data))
        indexed.sort(key=lambda x: x[1].intensity_gco2_per_kwh)
        return sorted([i for i, _ in indexed[:n_hours]])

    def carbon_savings(
        self,
        shifted_kwh: float,
        from_intensity: float,
        to_intensity: float,
    ) -> float:
        """Calculate CO₂ savings from load shifting."""
        return shifted_kwh * (from_intensity - to_intensity) / 1000  # kg

    def hourly_profile(self) -> List[float]:
        """Get hourly carbon intensity profile."""
        return [d.intensity_gco2_per_kwh for d in self._data[:24]]


# ---------------------------------------------------------------------------
# Bill calculator
# ---------------------------------------------------------------------------

class BillCalculator:
    """Calculate electricity bill from usage data and tariff."""

    def __init__(self, tariff: TariffPlan) -> None:
        self.tariff = tariff

    def calculate_daily(
        self,
        import_kwh_hourly: List[float],
        export_kwh_hourly: List[float],
        peak_demand_kw: float = 0.0,
    ) -> Dict[str, Any]:
        """Calculate daily bill."""
        import_cost = 0.0
        export_revenue = 0.0

        for h in range(min(24, len(import_kwh_hourly))):
            import_cost += (
                import_kwh_hourly[h] * self.tariff.import_rate(h)
            )
        for h in range(min(24, len(export_kwh_hourly))):
            export_revenue += (
                export_kwh_hourly[h] * self.tariff.export_rate(h)
            )

        demand_cost = peak_demand_kw * self.tariff.demand_charge_per_kw
        daily_fixed = self.tariff.fixed_daily_charge
        subtotal = import_cost - export_revenue + demand_cost + daily_fixed
        gst = subtotal * self.tariff.gst_pct / 100
        total = subtotal + gst

        return {
            "import_cost": round(import_cost, 2),
            "export_revenue": round(export_revenue, 2),
            "demand_cost": round(demand_cost, 2),
            "fixed_charge": round(daily_fixed, 2),
            "subtotal": round(subtotal, 2),
            "gst": round(gst, 2),
            "total": round(total, 2),
            "total_import_kwh": round(sum(import_kwh_hourly[:24]), 2),
            "total_export_kwh": round(sum(export_kwh_hourly[:24]), 2),
            "currency": self.tariff.currency,
        }

    def compare_tariffs(
        self,
        import_profile: List[float],
        export_profile: List[float],
        tariff_names: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Compare bills across multiple tariffs."""
        names = tariff_names or list(TARIFF_CATALOGUE.keys())
        results = []

        for name in names:
            plan = TARIFF_CATALOGUE.get(name)
            if plan is None:
                continue
            calc = BillCalculator(plan)
            bill = calc.calculate_daily(import_profile, export_profile)
            results.append({
                "tariff_name": plan.name,
                "tariff_key": name,
                "currency": plan.currency,
                "total": bill["total"],
                "import_cost": bill["import_cost"],
                "export_revenue": bill["export_revenue"],
            })

        results.sort(key=lambda x: x["total"])
        return results
