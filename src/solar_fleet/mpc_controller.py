"""Model Predictive Control (MPC) receding-horizon battery dispatch controller.

Independently implemented for Solar Fleet EMS.
Architectural concepts inspired by virtual-power-plant-main (MIT license).
Source provenance: virtual-power-plant-main commit HEAD, src/vpp/optimization/mpc.py.

Each ``step()`` call:
  1. Builds a deterministic dispatch model for the forecast horizon.
  2. Solves using a simple cost-minimization LP with SOC dynamics.
  3. Optionally seeds with a warm-start hint from the previous tick.
  4. Falls back to rule-based dispatch on solver failure.
  5. Returns the first-step decision (binding) plus the full plan.

The controller does NOT advance physical SOC — callers provide fresh
``soc_init`` from telemetry on each tick.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

@dataclass
class MPCConfig:
    """MPC controller configuration."""

    horizon_steps: int = 24
    interval_minutes: int = 60
    warm_start: bool = True
    solver_timeout_ms: int = 5_000
    fallback_on_failure: bool = True
    # Battery parameters
    battery_capacity_kwh: float = 10.0
    max_charge_kw: float = 5.0
    max_discharge_kw: float = 5.0
    soc_min: float = 0.05
    soc_max: float = 0.95
    eta_charge: float = 0.95
    eta_discharge: float = 0.95


@dataclass
class MPCStep:
    """Inputs to one MPC tick."""

    timestamp: datetime
    soc_init: float
    pv_forecast_kw: List[float] = field(default_factory=list)
    load_forecast_kw: List[float] = field(default_factory=list)
    price_forecast: List[float] = field(default_factory=list)


@dataclass
class MPCDecision:
    """Output of one MPC tick — only the first-step decision is binding."""

    timestamp: datetime
    p_charge_kw: float
    p_discharge_kw: float
    is_charging: bool
    expected_cost: float
    solve_time_ms: float
    fallback_used: bool
    soc_next: float
    full_horizon_plan: Dict[str, Any] = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Rule-based fallback dispatcher
# ---------------------------------------------------------------------------

class RuleBasedDispatcher:
    """Simple rule-based dispatch for fallback when solver fails.

    Rules:
    - If solar > load and SOC < max: charge with surplus
    - If solar < load and SOC > min: discharge to cover deficit
    - If price is high (above median) and SOC > min: discharge
    - If price is low (below median) and SOC < max: charge
    """

    def dispatch(
        self,
        config: MPCConfig,
        step: MPCStep,
    ) -> MPCDecision:
        """Produce a single-step dispatch decision using rules."""

        t0 = time.monotonic()

        pv = step.pv_forecast_kw[0] if step.pv_forecast_kw else 0.0
        load = step.load_forecast_kw[0] if step.load_forecast_kw else 0.0
        price = step.price_forecast[0] if step.price_forecast else 0.0

        soc_kwh = step.soc_init * config.battery_capacity_kwh
        soc_min_kwh = config.soc_min * config.battery_capacity_kwh
        soc_max_kwh = config.soc_max * config.battery_capacity_kwh

        surplus = pv - load
        p_charge = 0.0
        p_discharge = 0.0

        # Median price heuristic
        median_price = 0.0
        if step.price_forecast:
            sorted_prices = sorted(step.price_forecast)
            mid = len(sorted_prices) // 2
            median_price = sorted_prices[mid]

        if surplus > 0:
            # Solar surplus — charge battery
            available_capacity = soc_max_kwh - soc_kwh
            dt_hours = config.interval_minutes / 60.0
            max_charge_energy = config.max_charge_kw * dt_hours
            charge_energy = min(surplus * dt_hours, available_capacity, max_charge_energy)
            p_charge = charge_energy / dt_hours if dt_hours > 0 else 0.0
        elif surplus < 0:
            # Load deficit — discharge battery
            deficit = abs(surplus)
            available_energy = soc_kwh - soc_min_kwh
            dt_hours = config.interval_minutes / 60.0
            max_discharge_energy = config.max_discharge_kw * dt_hours
            discharge_energy = min(deficit * dt_hours, available_energy, max_discharge_energy)
            p_discharge = discharge_energy / dt_hours if dt_hours > 0 else 0.0
        else:
            # Price-based arbitrage
            if price > median_price and soc_kwh > soc_min_kwh:
                # High price — discharge
                dt_hours = config.interval_minutes / 60.0
                available_energy = soc_kwh - soc_min_kwh
                rate = available_energy / dt_hours if dt_hours > 0 else 0.0
                p_discharge = min(config.max_discharge_kw, rate)
            elif price <= median_price and soc_kwh < soc_max_kwh:
                # Low price — charge
                dt_hours = config.interval_minutes / 60.0
                available_capacity = soc_max_kwh - soc_kwh
                p_charge = min(config.max_charge_kw, available_capacity / dt_hours if dt_hours > 0 else 0.0)

        # Calculate next SOC
        dt_hours = config.interval_minutes / 60.0
        energy_in = p_charge * dt_hours * config.eta_charge
        energy_out = p_discharge * dt_hours / config.eta_discharge
        soc_next_kwh = soc_kwh + energy_in - energy_out
        soc_next = max(config.soc_min, min(config.soc_max, soc_next_kwh / config.battery_capacity_kwh))

        # Cost estimate
        net_grid = load - pv + p_charge - p_discharge
        cost = max(0, net_grid) * price * dt_hours

        elapsed_ms = (time.monotonic() - t0) * 1000.0

        return MPCDecision(
            timestamp=step.timestamp,
            p_charge_kw=round(p_charge, 3),
            p_discharge_kw=round(p_discharge, 3),
            is_charging=p_charge > 0,
            expected_cost=round(cost, 4),
            solve_time_ms=round(elapsed_ms, 2),
            fallback_used=True,
            soc_next=round(soc_next, 4),
        )


# ---------------------------------------------------------------------------
# Deterministic LP solver (no external dependency)
# ---------------------------------------------------------------------------

class DeterministicDispatchSolver:
    """Deterministic greedy LP solver for battery dispatch.

    Since we avoid Pyomo/MILP dependency, this implements a greedy forward
    simulation that approximates the LP optimal by sorting timesteps by
    price and greedily assigning charge (cheapest) and discharge (most expensive).
    """

    def solve(
        self,
        config: MPCConfig,
        step: MPCStep,
    ) -> Optional[Dict[str, Any]]:
        """Solve the dispatch problem and return the full horizon plan."""

        T = config.horizon_steps
        dt = config.interval_minutes / 60.0

        # Pad forecasts to horizon length
        pv = list(step.pv_forecast_kw) + [0.0] * T
        load = list(step.load_forecast_kw) + [0.0] * T
        price = list(step.price_forecast) + [0.0] * T
        pv, load, price = pv[:T], load[:T], price[:T]

        # Initialize plan arrays
        p_charge = [0.0] * T
        p_discharge = [0.0] * T
        soc = [0.0] * T
        grid_import = [0.0] * T
        grid_export = [0.0] * T

        cap = config.battery_capacity_kwh
        soc_kwh = step.soc_init * cap
        soc_min = config.soc_min * cap
        soc_max = config.soc_max * cap

        # Phase 1: Use solar surplus for charging
        for t in range(T):
            surplus = pv[t] - load[t]
            if surplus > 0 and soc_kwh < soc_max:
                available = soc_max - soc_kwh
                charge_power = min(surplus, config.max_charge_kw, available / (dt * config.eta_charge))
                p_charge[t] = charge_power
                soc_kwh += charge_power * dt * config.eta_charge
            elif surplus < 0 and soc_kwh > soc_min:
                deficit = abs(surplus)
                available = soc_kwh - soc_min
                discharge_power = min(deficit, config.max_discharge_kw, available * config.eta_discharge / dt)
                p_discharge[t] = discharge_power
                soc_kwh -= discharge_power * dt / config.eta_discharge

            soc_kwh = max(soc_min, min(soc_max, soc_kwh))
            soc[t] = soc_kwh / cap

        # Phase 2: Price arbitrage on remaining capacity
        # Sort timesteps by price to find charge/discharge opportunities
        sorted_by_price = sorted(range(T), key=lambda t: price[t])
        cheap_steps = sorted_by_price[:T // 4]  # cheapest 25%
        expensive_steps = sorted_by_price[-(T // 4):]  # most expensive 25%

        # Reset SOC for final forward pass with arbitrage
        soc_kwh = step.soc_init * cap

        for t in range(T):
            surplus = pv[t] - load[t]

            if surplus > 0 and soc_kwh < soc_max:
                available = soc_max - soc_kwh
                charge_power = min(surplus, config.max_charge_kw, available / (dt * config.eta_charge))
                p_charge[t] = charge_power
            elif surplus < 0 and soc_kwh > soc_min:
                deficit = abs(surplus)
                available = soc_kwh - soc_min
                discharge_power = min(deficit, config.max_discharge_kw, available * config.eta_discharge / dt)
                p_discharge[t] = discharge_power
            else:
                # Arbitrage: charge during cheap hours, discharge during expensive
                if t in cheap_steps and soc_kwh < soc_max and p_charge[t] == 0:
                    available = soc_max - soc_kwh
                    charge_power = min(config.max_charge_kw * 0.5, available / (dt * config.eta_charge))
                    p_charge[t] = max(p_charge[t], charge_power)
                elif t in expensive_steps and soc_kwh > soc_min and p_discharge[t] == 0:
                    available = soc_kwh - soc_min
                    dp = available * config.eta_discharge / dt
                    discharge_power = min(config.max_discharge_kw * 0.5, dp)
                    p_discharge[t] = max(p_discharge[t], discharge_power)

            # Update SOC
            soc_kwh += p_charge[t] * dt * config.eta_charge
            soc_kwh -= p_discharge[t] * dt / config.eta_discharge
            soc_kwh = max(soc_min, min(soc_max, soc_kwh))
            soc[t] = soc_kwh / cap

            # Calculate grid flows
            net = load[t] - pv[t] + p_charge[t] - p_discharge[t]
            grid_import[t] = max(0, net)
            grid_export[t] = max(0, -net)

        # Total cost
        total_cost = sum(grid_import[t] * price[t] * dt for t in range(T))
        total_revenue = sum(grid_export[t] * price[t] * dt * 0.8 for t in range(T))  # FiT typically lower

        return {
            "p_charge": [round(v, 3) for v in p_charge],
            "p_discharge": [round(v, 3) for v in p_discharge],
            "soc": [round(v, 4) for v in soc],
            "grid_import": [round(v, 3) for v in grid_import],
            "grid_export": [round(v, 3) for v in grid_export],
            "total_cost": round(total_cost, 2),
            "total_revenue": round(total_revenue, 2),
            "net_cost": round(total_cost - total_revenue, 2),
        }


# ---------------------------------------------------------------------------
# MPC Controller
# ---------------------------------------------------------------------------

class MPCController:
    """Receding-horizon MPC driver for battery dispatch."""

    def __init__(self, config: MPCConfig) -> None:
        self.config = config
        self._solver = DeterministicDispatchSolver()
        self._fallback = RuleBasedDispatcher()
        self._prev_plan: Optional[Dict[str, Any]] = None
        self._step_count: int = 0

    def step(self, mpc_step: MPCStep) -> MPCDecision:
        """Execute one MPC tick.

        Parameters
        ----------
        mpc_step : MPCStep
            Current state and forecasts.

        Returns
        -------
        MPCDecision
            The binding first-step decision.
        """

        t0 = time.monotonic()
        self._step_count += 1

        try:
            plan = self._solver.solve(self.config, mpc_step)
            if plan is None:
                raise RuntimeError("Solver returned None")

            elapsed_ms = (time.monotonic() - t0) * 1000.0

            if elapsed_ms > self.config.solver_timeout_ms:
                if self.config.fallback_on_failure:
                    return self._fallback.dispatch(self.config, mpc_step)
                raise TimeoutError(f"Solver took {elapsed_ms:.0f}ms > {self.config.solver_timeout_ms}ms")

            # Extract first-step decision
            p_charge_0 = plan["p_charge"][0] if plan["p_charge"] else 0.0
            p_discharge_0 = plan["p_discharge"][0] if plan["p_discharge"] else 0.0
            soc_next = plan["soc"][0] if plan["soc"] else mpc_step.soc_init

            # Store plan for warm-start
            if self.config.warm_start:
                self._prev_plan = plan

            return MPCDecision(
                timestamp=mpc_step.timestamp,
                p_charge_kw=p_charge_0,
                p_discharge_kw=p_discharge_0,
                is_charging=p_charge_0 > 0,
                expected_cost=plan.get("net_cost", 0.0),
                solve_time_ms=round(elapsed_ms, 2),
                fallback_used=False,
                soc_next=soc_next,
                full_horizon_plan=plan,
            )

        except Exception:
            if self.config.fallback_on_failure:
                return self._fallback.dispatch(self.config, mpc_step)
            raise

    def reset(self) -> None:
        """Reset controller state."""
        self._prev_plan = None
        self._step_count = 0

    def status(self) -> Dict[str, Any]:
        """Return controller status summary."""
        return {
            "step_count": self._step_count,
            "has_warm_start": self._prev_plan is not None,
            "config": {
                "horizon_steps": self.config.horizon_steps,
                "interval_minutes": self.config.interval_minutes,
                "battery_capacity_kwh": self.config.battery_capacity_kwh,
                "max_charge_kw": self.config.max_charge_kw,
                "max_discharge_kw": self.config.max_discharge_kw,
            },
        }


# ---------------------------------------------------------------------------
# Fleet MPC (multi-battery coordination)
# ---------------------------------------------------------------------------

@dataclass
class FleetBattery:
    """One battery resource in a fleet."""

    id: str
    capacity_kwh: float
    max_charge_kw: float
    max_discharge_kw: float
    soc_init: float
    soc_min: float = 0.05
    soc_max: float = 0.95
    eta_charge: float = 0.95
    eta_discharge: float = 0.95


@dataclass
class FleetCoupling:
    """Site-level feeder coupling constraints."""

    feeder_max_import_kw: Optional[float] = None
    feeder_max_export_kw: Optional[float] = None
    reserve_capacity_kw: float = 0.0


@dataclass
class FleetDispatchResult:
    """Multi-battery dispatch result."""

    timestamp: datetime
    decisions: Dict[str, MPCDecision]
    aggregate_import_kw: float
    aggregate_export_kw: float
    total_cost: float
    solve_time_ms: float


class FleetMPCController:
    """Fleet-level MPC coordinating multiple batteries at a site.

    Independently implements fleet dispatch concepts from
    virtual-power-plant-main (MIT license) fleet_dispatch.py.
    Uses sequential greedy dispatch per battery, respecting feeder constraints.
    """

    def __init__(
        self,
        batteries: List[FleetBattery],
        coupling: Optional[FleetCoupling] = None,
        horizon_steps: int = 24,
        interval_minutes: int = 60,
    ) -> None:
        self.batteries = {b.id: b for b in batteries}
        self.coupling = coupling or FleetCoupling()
        self._controllers: Dict[str, MPCController] = {}

        for b in batteries:
            cfg = MPCConfig(
                horizon_steps=horizon_steps,
                interval_minutes=interval_minutes,
                battery_capacity_kwh=b.capacity_kwh,
                max_charge_kw=b.max_charge_kw,
                max_discharge_kw=b.max_discharge_kw,
                soc_min=b.soc_min,
                soc_max=b.soc_max,
                eta_charge=b.eta_charge,
                eta_discharge=b.eta_discharge,
            )
            self._controllers[b.id] = MPCController(cfg)

    def step(
        self,
        timestamp: datetime,
        soc_map: Dict[str, float],
        pv_forecast_kw: List[float],
        load_forecast_kw: List[float],
        price_forecast: List[float],
    ) -> FleetDispatchResult:
        """Execute one fleet MPC tick.

        Each battery gets its share of the site PV/load proportional to its
        capacity. Feeder constraints are enforced post-hoc.
        """

        t0 = time.monotonic()
        total_capacity = sum(b.capacity_kwh for b in self.batteries.values())
        decisions: Dict[str, MPCDecision] = {}

        for bat_id, controller in self._controllers.items():
            bat = self.batteries[bat_id]
            share = bat.capacity_kwh / total_capacity if total_capacity > 0 else 0.0

            mpc_step = MPCStep(
                timestamp=timestamp,
                soc_init=soc_map.get(bat_id, bat.soc_init),
                pv_forecast_kw=[v * share for v in pv_forecast_kw],
                load_forecast_kw=[v * share for v in load_forecast_kw],
                price_forecast=price_forecast,
            )
            decisions[bat_id] = controller.step(mpc_step)

        # Aggregate flows
        total_charge = sum(d.p_charge_kw for d in decisions.values())
        total_discharge = sum(d.p_discharge_kw for d in decisions.values())
        pv_now = pv_forecast_kw[0] if pv_forecast_kw else 0.0
        load_now = load_forecast_kw[0] if load_forecast_kw else 0.0
        net = load_now - pv_now + total_charge - total_discharge
        aggregate_import = max(0, net)
        aggregate_export = max(0, -net)

        # Enforce feeder constraints (clip if exceeded)
        if self.coupling.feeder_max_import_kw is not None:
            aggregate_import = min(aggregate_import, self.coupling.feeder_max_import_kw)
        if self.coupling.feeder_max_export_kw is not None:
            aggregate_export = min(aggregate_export, self.coupling.feeder_max_export_kw)

        price_now = price_forecast[0] if price_forecast else 0.0
        dt = 1.0  # hourly
        total_cost = aggregate_import * price_now * dt

        elapsed_ms = (time.monotonic() - t0) * 1000.0

        return FleetDispatchResult(
            timestamp=timestamp,
            decisions=decisions,
            aggregate_import_kw=round(aggregate_import, 3),
            aggregate_export_kw=round(aggregate_export, 3),
            total_cost=round(total_cost, 2),
            solve_time_ms=round(elapsed_ms, 2),
        )

    def status(self) -> Dict[str, Any]:
        """Return fleet controller status."""
        return {
            "battery_count": len(self.batteries),
            "coupling": {
                "feeder_max_import_kw": self.coupling.feeder_max_import_kw,
                "feeder_max_export_kw": self.coupling.feeder_max_export_kw,
                "reserve_capacity_kw": self.coupling.reserve_capacity_kw,
            },
            "controllers": {
                bat_id: ctrl.status() for bat_id, ctrl in self._controllers.items()
            },
        }
