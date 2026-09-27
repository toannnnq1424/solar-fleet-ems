"""Battery degradation models — throughput, calendar, and rainflow-based.

Independently implemented for Solar Fleet EMS.
Physical models based on published battery aging literature:
- NREL BLAST tool (Smith et al.)
- Wang et al., J. Power Sources 196 (2011) — LFP cycle-life curve
- Schmalstieg et al., J. Power Sources 257 (2014) — NMC calendar aging
- Vetter et al., J. Power Sources 147 (2005) — Arrhenius / SOC stress

Concepts informed by virtual-power-plant-main (MIT license)
degradation/models.py — no code copied.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, Dict, List, Sequence

# Boltzmann constant in eV/K
_K_B = 8.617333262e-5
_T_REF_K = 298.15  # 25°C reference


class DegradationModel(ABC):
    """Abstract base for fractional capacity-loss estimators."""

    @abstractmethod
    def predict_capacity_loss(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> float:
        """Return fractional capacity loss in [0, 1]."""

    @staticmethod
    def _validate_trace(
        soc_trace: Sequence[float], dt_hours: float,
    ) -> None:
        if dt_hours <= 0:
            raise ValueError("dt_hours must be positive")
        if len(soc_trace) < 2:
            raise ValueError("soc_trace must have at least 2 samples")


# ---------------------------------------------------------------------------
# Throughput-based degradation
# ---------------------------------------------------------------------------

@dataclass
class ThroughputDegradation(DegradationModel):
    """Linear capacity-loss proportional to cumulative kWh throughput.

    loss = (efc / cycles_to_eol) * (1 - eol_capacity_fraction)

    where efc = equivalent full cycles = total_throughput / (2 * capacity).
    """

    nominal_capacity_kwh: float = 10.0
    cycles_to_eol: float = 6000.0
    eol_capacity_fraction: float = 0.80

    def predict_capacity_loss(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> float:
        self._validate_trace(soc_trace, dt_hours)

        throughput_kwh = 0.0
        for i in range(1, len(soc_trace)):
            delta_soc = abs(soc_trace[i] - soc_trace[i - 1])
            throughput_kwh += delta_soc * self.nominal_capacity_kwh

        efc = throughput_kwh / (2 * self.nominal_capacity_kwh)
        loss_fraction = 1 - self.eol_capacity_fraction
        loss = (efc / self.cycles_to_eol) * loss_fraction
        return max(0.0, min(1.0, loss))


# ---------------------------------------------------------------------------
# Calendar degradation
# ---------------------------------------------------------------------------

@dataclass
class CalendarDegradation(DegradationModel):
    """Time-and-temperature-driven capacity loss.

    Uses Arrhenius acceleration and SOC-stress multiplier.

    loss = k_cal * sqrt(t) * arrhenius(T) * soc_stress(SOC_avg)

    Typical for NMC chemistry.
    """

    k_cal: float = 7.543e-4     # Calendar aging rate constant
    activation_energy_ev: float = 0.75  # Ea for Arrhenius
    soc_stress_factor: float = 1.04     # SOC stress exponent

    def predict_capacity_loss(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> float:
        self._validate_trace(soc_trace, dt_hours)

        # Total time
        total_hours = len(soc_trace) * dt_hours
        total_days = total_hours / 24.0

        # Average SOC
        avg_soc = sum(soc_trace) / len(soc_trace)

        # Arrhenius acceleration
        t_k = temperature_c + 273.15
        arrhenius = math.exp(
            (self.activation_energy_ev / _K_B)
            * (1 / _T_REF_K - 1 / t_k)
        )

        # SOC stress — higher SOC accelerates calendar aging
        soc_stress = math.exp(
            self.soc_stress_factor * (avg_soc - 0.5)
        )

        # sqrt(t) aging law
        loss = self.k_cal * math.sqrt(total_days) * arrhenius * soc_stress
        return max(0.0, min(1.0, loss))


# ---------------------------------------------------------------------------
# Rainflow (cycle-counting) degradation
# ---------------------------------------------------------------------------

@dataclass
class RainflowDegradation(DegradationModel):
    """Depth-of-discharge-aware cycle counting degradation.

    Counts half-cycles using a simplified rainflow algorithm,
    then maps each cycle depth to a cycle-life from a piecewise curve.

    The damage for one cycle of depth d is:
        damage = 1 / N(d)
    where N(d) = a * d^b (Wöhler curve).

    Total loss = sum(damage) * (1 - eol_capacity_fraction).
    """

    # Wöhler curve parameters (typical LFP)
    a: float = 10000.0   # Base cycle life at d=1.0
    b: float = -1.2       # Exponent (negative)
    eol_capacity_fraction: float = 0.80

    def _cycle_life(self, depth: float) -> float:
        """Cycles to failure at given depth of discharge."""
        if depth <= 0.001:
            return 1e9  # Negligible depth
        return self.a * (depth ** self.b)

    def _simple_rainflow(
        self, soc_trace: Sequence[float],
    ) -> List[float]:
        """Simplified rainflow cycle counting.

        Returns list of cycle depths (half-cycles combined).
        """
        # Find turning points
        peaks: List[float] = [soc_trace[0]]
        for i in range(1, len(soc_trace) - 1):
            prev, curr, nxt = soc_trace[i-1], soc_trace[i], soc_trace[i+1]
            if (curr - prev) * (nxt - curr) < 0:  # Direction change
                peaks.append(curr)
        peaks.append(soc_trace[-1])

        # Count half-cycles
        half_cycles: List[float] = []
        for i in range(1, len(peaks)):
            depth = abs(peaks[i] - peaks[i - 1])
            if depth > 0.001:
                half_cycles.append(depth)

        # Pair half-cycles into full cycles
        full_cycles: List[float] = []
        i = 0
        while i < len(half_cycles) - 1:
            d = (half_cycles[i] + half_cycles[i + 1]) / 2
            full_cycles.append(d)
            i += 2
        if i < len(half_cycles):
            full_cycles.append(half_cycles[-1] / 2)

        return full_cycles

    def predict_capacity_loss(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> float:
        self._validate_trace(soc_trace, dt_hours)

        cycles = self._simple_rainflow(soc_trace)
        total_damage = 0.0

        for depth in cycles:
            n_life = self._cycle_life(depth)
            if n_life > 0:
                total_damage += 1.0 / n_life

        loss_fraction = 1 - self.eol_capacity_fraction
        loss = total_damage * loss_fraction
        return max(0.0, min(1.0, loss))


# ---------------------------------------------------------------------------
# Combined degradation model
# ---------------------------------------------------------------------------

@dataclass
class CombinedDegradation(DegradationModel):
    """Combines throughput, calendar, and rainflow models.

    Total loss = max(throughput, calendar) + rainflow_penalty.
    Capped at 1.0 (100% capacity loss).
    """

    throughput: ThroughputDegradation = field(
        default_factory=ThroughputDegradation,
    )
    calendar: CalendarDegradation = field(
        default_factory=CalendarDegradation,
    )
    rainflow: RainflowDegradation = field(
        default_factory=RainflowDegradation,
    )
    rainflow_weight: float = 0.3

    def predict_capacity_loss(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> float:
        self._validate_trace(soc_trace, dt_hours)

        loss_tp = self.throughput.predict_capacity_loss(
            soc_trace, dt_hours, temperature_c,
        )
        loss_cal = self.calendar.predict_capacity_loss(
            soc_trace, dt_hours, temperature_c,
        )
        loss_rf = self.rainflow.predict_capacity_loss(
            soc_trace, dt_hours, temperature_c,
        )

        total = max(loss_tp, loss_cal) + self.rainflow_weight * loss_rf
        return max(0.0, min(1.0, total))

    def breakdown(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> Dict[str, float]:
        """Return per-model breakdown."""
        return {
            "throughput": self.throughput.predict_capacity_loss(
                soc_trace, dt_hours, temperature_c,
            ),
            "calendar": self.calendar.predict_capacity_loss(
                soc_trace, dt_hours, temperature_c,
            ),
            "rainflow": self.rainflow.predict_capacity_loss(
                soc_trace, dt_hours, temperature_c,
            ),
            "combined": self.predict_capacity_loss(
                soc_trace, dt_hours, temperature_c,
            ),
        }


# ---------------------------------------------------------------------------
# Battery health estimator
# ---------------------------------------------------------------------------

@dataclass
class BatteryHealthEstimate:
    """Battery health assessment result."""

    soh_pct: float
    capacity_loss_pct: float
    remaining_cycles: float
    estimated_eol_days: float
    degradation_rate_pct_per_year: float
    breakdown: Dict[str, float]

    def to_dict(self) -> dict[str, Any]:
        return {
            "soh_pct": round(self.soh_pct, 2),
            "capacity_loss_pct": round(self.capacity_loss_pct, 4),
            "remaining_cycles": round(self.remaining_cycles, 0),
            "estimated_eol_days": round(self.estimated_eol_days, 0),
            "degradation_rate_pct_per_year": round(
                self.degradation_rate_pct_per_year, 4,
            ),
            "breakdown": {
                k: round(v, 6) for k, v in self.breakdown.items()
            },
        }


class BatteryHealthEstimator:
    """Estimate battery health from operational data."""

    def __init__(
        self,
        nominal_capacity_kwh: float = 10.0,
        chemistry: str = "lfp",
    ) -> None:
        self.nominal_capacity_kwh = nominal_capacity_kwh
        self.chemistry = chemistry.lower()

        if self.chemistry == "nmc":
            self._model = CombinedDegradation(
                throughput=ThroughputDegradation(
                    nominal_capacity_kwh=nominal_capacity_kwh,
                    cycles_to_eol=3000,
                ),
                calendar=CalendarDegradation(
                    k_cal=7.543e-4,
                    activation_energy_ev=0.75,
                ),
                rainflow=RainflowDegradation(
                    a=5000, b=-1.5,
                ),
            )
        else:  # LFP
            self._model = CombinedDegradation(
                throughput=ThroughputDegradation(
                    nominal_capacity_kwh=nominal_capacity_kwh,
                    cycles_to_eol=6000,
                ),
                calendar=CalendarDegradation(
                    k_cal=3.5e-4,
                    activation_energy_ev=0.58,
                ),
                rainflow=RainflowDegradation(
                    a=10000, b=-1.2,
                ),
            )

    def assess(
        self,
        soc_trace: Sequence[float],
        dt_hours: float,
        temperature_c: float = 25.0,
    ) -> BatteryHealthEstimate:
        """Assess battery health from SOC trajectory."""

        breakdown = self._model.breakdown(
            soc_trace, dt_hours, temperature_c,
        )
        loss = breakdown["combined"]

        total_hours = len(soc_trace) * dt_hours
        total_days = total_hours / 24.0

        # Degradation rate
        if total_days > 0:
            rate_per_year = (loss * 100) / (total_days / 365.25)
        else:
            rate_per_year = 0.0

        # Remaining capacity to EOL (20% loss)
        eol_loss = 0.20
        remaining_loss = max(0, eol_loss - loss)
        if rate_per_year > 0:
            eol_days = remaining_loss / (rate_per_year / 100) * 365.25
        else:
            eol_days = 99999.0

        # Remaining cycles estimate
        tp_model = self._model.throughput
        remaining_cycles = tp_model.cycles_to_eol * (1 - loss / eol_loss)

        return BatteryHealthEstimate(
            soh_pct=round((1 - loss) * 100, 2),
            capacity_loss_pct=round(loss * 100, 4),
            remaining_cycles=max(0, remaining_cycles),
            estimated_eol_days=max(0, eol_days),
            degradation_rate_pct_per_year=rate_per_year,
            breakdown=breakdown,
        )
