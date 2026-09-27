"""Three-phase asymmetric phase balancing and rolling peak demand shaving engine.

Independently implemented for Solar Fleet EMS.
Concepts from OpenEMS io.openems.edge.controller.ess.asymmetric,
io.openems.edge.controller.ess.fixactivepower,
and io.openems.edge.controller.ess.limitationbyzeroexport.
No code copied.

Provides:
- Symmetrical component decomposition (Fortescue transform)
- Voltage Unbalance Factor (VUF) and Current Unbalance Factor (CUF) per IEC 61000-4-30
- Asymmetric per-phase active and reactive power dispatch (P_L1, P_L2, P_L3, Q_L1, Q_L2, Q_L3)
- Fast zero-export closed-loop control with anti-windup and ramp rate limiter
- 15-minute / 30-minute rolling utility demand window peak shaver
"""

from __future__ import annotations

import cmath
import math
from dataclasses import dataclass
from typing import Any, Dict, Tuple

# ---------------------------------------------------------------------------
# Symmetrical components helper (Fortescue transformation)
# ---------------------------------------------------------------------------

ALPHA = cmath.rect(1.0, 2.0 * math.pi / 3.0)  # e^(j * 120°)
ALPHA2 = ALPHA * ALPHA                          # e^(j * 240°)


def calculate_symmetrical_components(
    a: complex, b: complex, c: complex,
) -> Tuple[complex, complex, complex]:
    """Compute zero, positive, and negative sequence components.

    [V0] = 1/3 * [1  1  1 ] [Va]
    [V1] = 1/3 * [1  a  a2] [Vb]
    [V2] = 1/3 * [1  a2 a ] [Vc]
    """
    v0 = (a + b + c) / 3.0
    v1 = (a + ALPHA * b + ALPHA2 * c) / 3.0
    v2 = (a + ALPHA2 * b + ALPHA * c) / 3.0
    return v0, v1, v2


# ---------------------------------------------------------------------------
# 1. Three-Phase Power Quality & Unbalance Evaluator
# ---------------------------------------------------------------------------

@dataclass
class PhaseMeasurement:
    """Three-phase voltage, current, and active/reactive power."""

    v_l1: float = 230.0
    v_l2: float = 230.0
    v_l3: float = 230.0
    i_l1: float = 0.0
    i_l2: float = 0.0
    i_l3: float = 0.0
    p_l1: float = 0.0  # + import, - export
    p_l2: float = 0.0
    p_l3: float = 0.0
    q_l1: float = 0.0  # inductive (+) / capacitive (-)
    q_l2: float = 0.0
    q_l3: float = 0.0

    @property
    def p_total(self) -> float:
        return self.p_l1 + self.p_l2 + self.p_l3

    @property
    def q_total(self) -> float:
        return self.q_l1 + self.q_l2 + self.q_l3


class PhaseUnbalanceEvaluator:
    """Evaluates 3-phase grid unbalance per IEC 61000-4-30 standard."""

    @staticmethod
    def evaluate(measurement: PhaseMeasurement) -> Dict[str, Any]:
        """Compute VUF (Voltage Unbalance Factor) and CUF (Current Unbalance Factor)."""
        # Complex phase voltages assuming 120 degree phase displacement
        va = complex(measurement.v_l1, 0.0)
        vb = cmath.rect(measurement.v_l2, -2.0 * math.pi / 3.0)
        vc = cmath.rect(measurement.v_l3, 2.0 * math.pi / 3.0)

        v0, v1, v2 = calculate_symmetrical_components(va, vb, vc)
        v1_mag = abs(v1)
        v2_mag = abs(v2)
        vuf_pct = (v2_mag / v1_mag * 100.0) if v1_mag > 0 else 0.0

        # Current unbalance
        ia = complex(measurement.i_l1, 0.0)
        ib = cmath.rect(measurement.i_l2, -2.0 * math.pi / 3.0)
        ic = cmath.rect(measurement.i_l3, 2.0 * math.pi / 3.0)

        i0, i1, i2 = calculate_symmetrical_components(ia, ib, ic)
        i1_mag = abs(i1)
        i2_mag = abs(i2)
        cuf_pct = (i2_mag / i1_mag * 100.0) if i1_mag > 0 else 0.0

        # Neutral current estimation (I_N = Ia + Ib + Ic = 3 * I0)
        i_neutral = abs(ia + ib + ic)

        # Standard IEC 61000-2-2 / EN 50160 limit: VUF <= 2.0%
        is_compliant = vuf_pct <= 2.0

        return {
            "vuf_pct": round(vuf_pct, 3),
            "cuf_pct": round(cuf_pct, 3),
            "v_positive_seq": round(v1_mag, 1),
            "v_negative_seq": round(v2_mag, 1),
            "i_neutral_amps": round(i_neutral, 2),
            "is_compliant": is_compliant,
            "iec_threshold_pct": 2.0,
        }


# ---------------------------------------------------------------------------
# 2. Asymmetric Phase Balancing Controller
# ---------------------------------------------------------------------------

@dataclass
class InverterPhaseLimits:
    """Hardware capability constraints for hybrid multi-phase inverter."""

    max_total_kw: float = 10.0
    max_phase_kw: float = 3.68      # 16A @ 230V standard European residential per-phase limit
    max_phase_kvar: float = 2.5
    battery_max_charge_kw: float = 5.0
    battery_max_discharge_kw: float = 5.0
    allows_independent_phases: bool = True


class AsymmetricPhaseBalancer:
    """Calculates independent active and reactive power setpoints per phase.

    Aims to:
    1. Compensate phase unbalance so grid meter sees equal or zero exchange.
    2. Enforce zero export or balanced import constraints.
    3. Respect per-phase inverter IGBT limits and battery DC bus limits.
    """

    def __init__(self, limits: InverterPhaseLimits):
        self.limits = limits

    def calculate_dispatch(
        self,
        grid_meter: PhaseMeasurement,
        target_mode: str = "zero_export",
        target_grid_p_per_phase: float = 0.0,
    ) -> Dict[str, Any]:
        """Compute per-phase inverter active and reactive power commands."""
        # Desired inverter compensation per phase to cancel grid active power:
        # P_inv_phase = grid_meter.P_phase - target_grid_p_phase
        # Positive P_inv means inverter discharges/supplies power to load.
        raw_p_l1 = grid_meter.p_l1 - target_grid_p_per_phase
        raw_p_l2 = grid_meter.p_l2 - target_grid_p_per_phase
        raw_p_l3 = grid_meter.p_l3 - target_grid_p_per_phase

        if not self.limits.allows_independent_phases:
            # Symmetric inverter: dispatch average across all 3 phases
            avg_p = (raw_p_l1 + raw_p_l2 + raw_p_l3) / 3.0
            raw_p_l1 = raw_p_l2 = raw_p_l3 = avg_p

        # Clamp each phase to hardware phase limits
        p_l1 = max(-self.limits.max_phase_kw, min(self.limits.max_phase_kw, raw_p_l1))
        p_l2 = max(-self.limits.max_phase_kw, min(self.limits.max_phase_kw, raw_p_l2))
        p_l3 = max(-self.limits.max_phase_kw, min(self.limits.max_phase_kw, raw_p_l3))

        # Enforce total inverter active power and battery limits
        total_p = p_l1 + p_l2 + p_l3

        # The nameplate limit applies even when the battery can deliver more.
        throughput = abs(p_l1) + abs(p_l2) + abs(p_l3)
        if throughput > self.limits.max_total_kw:
            scale = self.limits.max_total_kw / throughput
            p_l1 *= scale
            p_l2 *= scale
            p_l3 *= scale
            total_p = p_l1 + p_l2 + p_l3

        if total_p > self.limits.battery_max_discharge_kw:
            # Scale down proportionally
            scale = self.limits.battery_max_discharge_kw / total_p
            p_l1 *= scale
            p_l2 *= scale
            p_l3 *= scale
        elif total_p < -self.limits.battery_max_charge_kw:
            # Scale up (charging) proportionally
            scale = -self.limits.battery_max_charge_kw / total_p
            p_l1 *= scale
            p_l2 *= scale
            p_l3 *= scale

        # Reactive power compensation for power factor correction (Q_target = -Q_measured)
        q_l1 = max(-self.limits.max_phase_kvar, min(self.limits.max_phase_kvar, -grid_meter.q_l1))
        q_l2 = max(-self.limits.max_phase_kvar, min(self.limits.max_phase_kvar, -grid_meter.q_l2))
        q_l3 = max(-self.limits.max_phase_kvar, min(self.limits.max_phase_kvar, -grid_meter.q_l3))

        # Expected residual grid exchange after compensation
        residual_grid_p_l1 = grid_meter.p_l1 - p_l1
        residual_grid_p_l2 = grid_meter.p_l2 - p_l2
        residual_grid_p_l3 = grid_meter.p_l3 - p_l3

        return {
            "p_l1_kw": round(p_l1, 3),
            "p_l2_kw": round(p_l2, 3),
            "p_l3_kw": round(p_l3, 3),
            "total_p_kw": round(p_l1 + p_l2 + p_l3, 3),
            "q_l1_kvar": round(q_l1, 3),
            "q_l2_kvar": round(q_l2, 3),
            "q_l3_kvar": round(q_l3, 3),
            "total_q_kvar": round(q_l1 + q_l2 + q_l3, 3),
            "residual_grid_p_kw": round(residual_grid_p_l1 + residual_grid_p_l2 + residual_grid_p_l3, 3),
            "residual_per_phase": [
                round(residual_grid_p_l1, 3),
                round(residual_grid_p_l2, 3),
                round(residual_grid_p_l3, 3),
            ],
        }


# ---------------------------------------------------------------------------
# 3. Fast Zero-Export Controller with Ramp Rate Limiting
# ---------------------------------------------------------------------------

class ZeroExportController:
    """Closed-loop fast zero-export limiter with PID and ramp rate limiting.

    Ensures zero reverse active power flows into utility grid with configurable
    safety margin (e.g. 100W buffer to absorb sudden load shedding).
    """

    def __init__(
        self,
        target_grid_import_kw: float = 0.05,  # 50W safety import margin
        kp: float = 0.8,
        ki: float = 0.1,
        kd: float = 0.02,
        max_ramp_rate_kw_per_sec: float = 2.0,
        inverter_rated_kw: float = 10.0,
    ):
        self.target_grid_import_kw = target_grid_import_kw
        self.kp = kp
        self.ki = ki
        self.kd = kd
        self.max_ramp = max_ramp_rate_kw_per_sec
        self.inverter_rated_kw = inverter_rated_kw

        self._integral_error = 0.0
        self._last_error = 0.0
        self._current_export_limit_kw = inverter_rated_kw

    def update(
        self,
        measured_grid_power_kw: float,  # + is import, - is export
        dt_seconds: float = 1.0,
    ) -> Dict[str, float]:
        """Compute updated inverter output power limit."""
        # Error: how much measured grid power exceeds target import
        # If exporting (-0.5kW), error = 0.05 - (-0.5) = +0.55kW (need to curtail)
        error = self.target_grid_import_kw - measured_grid_power_kw

        # PID terms
        p_term = self.kp * error
        self._integral_error += error * dt_seconds
        # Anti-windup clamping
        self._integral_error = max(-self.inverter_rated_kw, min(self.inverter_rated_kw, self._integral_error))
        i_term = self.ki * self._integral_error
        d_term = self.kd * (error - self._last_error) / dt_seconds if dt_seconds > 0 else 0.0
        self._last_error = error

        # Adjustment to current power limit
        adjustment = -(p_term + i_term + d_term)

        # Apply ramp-rate limiting
        max_delta = self.max_ramp * dt_seconds
        adjustment_clamped = max(-max_delta, min(max_delta, adjustment))

        new_limit = max(0.0, min(self.inverter_rated_kw, self._current_export_limit_kw + adjustment_clamped))
        self._current_export_limit_kw = new_limit

        return {
            "inverter_power_limit_kw": round(new_limit, 3),
            "measured_grid_kw": measured_grid_power_kw,
            "error_kw": round(error, 4),
            "curtailment_active": new_limit < self.inverter_rated_kw,
        }


# ---------------------------------------------------------------------------
# 4. Rolling Window Peak Demand Shaver
# ---------------------------------------------------------------------------

class RollingPeakDemandShaver:
    """15-minute or 30-minute sliding window utility billing peak shaver.

    Calculates projected average demand at the end of the interval:
    P_projected = (E_accumulated + P_current * remaining_time) / window_duration
    If projected demand exceeds peak threshold, activates battery discharge.
    """

    def __init__(
        self,
        peak_threshold_kw: float = 15.0,
        window_duration_minutes: int = 15,
        battery_max_discharge_kw: float = 10.0,
    ):
        self.peak_threshold_kw = peak_threshold_kw
        self.window_duration_minutes = window_duration_minutes
        self.battery_max_discharge_kw = battery_max_discharge_kw

        self.window_duration_seconds = window_duration_minutes * 60
        self._energy_accumulated_kwh = 0.0
        self._elapsed_seconds = 0.0
        self._peak_recorded_kw = 0.0

    def step(
        self,
        grid_load_kw: float,
        dt_seconds: float = 1.0,
    ) -> Dict[str, Any]:
        """Update window integration and determine battery peak shaving command."""
        self._elapsed_seconds += dt_seconds
        self._energy_accumulated_kwh += (grid_load_kw * dt_seconds) / 3600.0

        remaining_seconds = max(0.0, self.window_duration_seconds - self._elapsed_seconds)

        # Projected average demand at end of window assuming current load persists
        if self._elapsed_seconds > 0:
            projected_total_kwh = self._energy_accumulated_kwh + (grid_load_kw * remaining_seconds) / 3600.0
            projected_avg_demand_kw = (projected_total_kwh / self.window_duration_seconds) * 3600.0
        else:
            projected_avg_demand_kw = grid_load_kw

        # Check if projected demand exceeds threshold
        required_discharge_kw = 0.0
        if projected_avg_demand_kw > self.peak_threshold_kw:
            excess_kwh = projected_total_kwh - (self.peak_threshold_kw * self.window_duration_seconds / 3600.0)
            if remaining_seconds > 0:
                required_discharge_kw = (excess_kwh / remaining_seconds) * 3600.0
            else:
                required_discharge_kw = grid_load_kw - self.peak_threshold_kw

        # Clamp discharge power to battery physical capability
        battery_discharge_kw = max(0.0, min(self.battery_max_discharge_kw, required_discharge_kw))

        # Check for window reset (e.g. at 15 or 30 minutes boundary)
        window_reset = False
        if self._elapsed_seconds >= self.window_duration_seconds:
            final_interval_demand = (self._energy_accumulated_kwh / self.window_duration_seconds) * 3600.0
            self._peak_recorded_kw = max(self._peak_recorded_kw, final_interval_demand)
            self._elapsed_seconds = 0.0
            self._energy_accumulated_kwh = 0.0
            window_reset = True

        return {
            "projected_avg_demand_kw": round(projected_avg_demand_kw, 3),
            "peak_threshold_kw": self.peak_threshold_kw,
            "battery_discharge_kw": round(battery_discharge_kw, 3),
            "is_shaving_active": battery_discharge_kw > 0.0,
            "elapsed_seconds": round(self._elapsed_seconds, 1),
            "remaining_seconds": round(remaining_seconds, 1),
            "peak_recorded_kw": round(self._peak_recorded_kw, 3),
            "window_reset": window_reset,
        }
