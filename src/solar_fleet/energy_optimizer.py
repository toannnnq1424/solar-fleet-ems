"""Energy optimizer — site-level energy management coordinator.

Independently implemented for Solar Fleet EMS.
Integrates MPC dispatch, battery management, EV charging,
load scheduling, and tariff optimization into a single
coordinating engine.

Concepts from openems-develop (AGPL) edge core scheduler
and emhass-master (MIT) optimal scheduling.
No code copied — clean-room implementation.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Operating modes
# ---------------------------------------------------------------------------

class OptimizationMode(str, Enum):
    """Site energy optimization mode."""

    SELF_CONSUMPTION = "self_consumption"
    COST_MINIMUM = "cost_minimum"
    PEAK_SHAVING = "peak_shaving"
    GRID_EXPORT = "grid_export"
    BACKUP = "backup"
    MANUAL = "manual"


class BatteryStrategy(str, Enum):
    """Battery operating strategy."""

    SELF_CONSUME = "self_consume"
    TIME_OF_USE = "time_of_use"
    PEAK_SHAVE = "peak_shave"
    GRID_SUPPORT = "grid_support"
    BACKUP_RESERVE = "backup_reserve"
    IDLE = "idle"


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class EnergyState:
    """Instantaneous energy state of a site."""

    timestamp: str = ""
    pv_power_kw: float = 0.0
    load_power_kw: float = 0.0
    battery_power_kw: float = 0.0   # + charge, - discharge
    grid_power_kw: float = 0.0      # + import, - export
    ev_power_kw: float = 0.0
    battery_soc: float = 0.5
    grid_frequency_hz: float = 50.0
    grid_voltage_pu: float = 1.0

    @property
    def self_consumption_kw(self) -> float:
        """PV power consumed on-site."""
        return min(self.pv_power_kw, self.load_power_kw + max(0, self.battery_power_kw) + self.ev_power_kw)

    @property
    def self_consumption_ratio(self) -> float:
        """Fraction of PV consumed on-site."""
        if self.pv_power_kw <= 0:
            return 0.0
        return min(1.0, self.self_consumption_kw / self.pv_power_kw)

    @property
    def autarky_ratio(self) -> float:
        """Fraction of load served without grid."""
        total_load = self.load_power_kw + self.ev_power_kw
        if total_load <= 0:
            return 1.0
        grid_used = max(0, self.grid_power_kw)
        return max(0, 1.0 - grid_used / total_load)

    @property
    def net_power_kw(self) -> float:
        """Net power balance (positive = surplus)."""
        return self.pv_power_kw - self.load_power_kw - self.ev_power_kw

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "pv_power_kw": round(self.pv_power_kw, 2),
            "load_power_kw": round(self.load_power_kw, 2),
            "battery_power_kw": round(self.battery_power_kw, 2),
            "grid_power_kw": round(self.grid_power_kw, 2),
            "ev_power_kw": round(self.ev_power_kw, 2),
            "battery_soc": round(self.battery_soc, 4),
            "self_consumption_ratio": round(
                self.self_consumption_ratio, 4,
            ),
            "autarky_ratio": round(self.autarky_ratio, 4),
        }


@dataclass
class TariffSchedule:
    """Time-of-use tariff schedule."""

    name: str = "default"
    import_rates: List[float] = field(
        default_factory=lambda: [0.10] * 24,
    )
    export_rates: List[float] = field(
        default_factory=lambda: [0.05] * 24,
    )
    demand_charge_per_kw: float = 0.0
    peak_hours: List[int] = field(
        default_factory=lambda: list(range(17, 22)),
    )
    off_peak_hours: List[int] = field(
        default_factory=lambda: list(range(0, 6)),
    )

    def import_rate(self, hour: int) -> float:
        """Get import rate for given hour."""
        return self.import_rates[hour % 24]

    def export_rate(self, hour: int) -> float:
        """Get export rate for given hour."""
        return self.export_rates[hour % 24]

    def is_peak(self, hour: int) -> bool:
        return hour in self.peak_hours

    def is_off_peak(self, hour: int) -> bool:
        return hour in self.off_peak_hours


@dataclass
class OptimizationResult:
    """Result of energy optimization for a time period."""

    mode: str
    battery_strategy: str
    battery_setpoint_kw: float
    ev_setpoint_kw: float
    grid_setpoint_kw: float
    export_limit_kw: float
    import_limit_kw: float
    estimated_cost: float
    estimated_revenue: float
    recommendations: List[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "mode": self.mode,
            "battery_strategy": self.battery_strategy,
            "battery_setpoint_kw": round(self.battery_setpoint_kw, 2),
            "ev_setpoint_kw": round(self.ev_setpoint_kw, 2),
            "grid_setpoint_kw": round(self.grid_setpoint_kw, 2),
            "export_limit_kw": round(self.export_limit_kw, 2),
            "import_limit_kw": round(self.import_limit_kw, 2),
            "estimated_cost": round(self.estimated_cost, 4),
            "estimated_revenue": round(self.estimated_revenue, 4),
            "recommendations": self.recommendations,
        }


# ---------------------------------------------------------------------------
# Energy optimizer
# ---------------------------------------------------------------------------

class EnergyOptimizer:
    """Site-level energy management optimizer.

    Coordinates battery, PV, EV, and grid to minimize cost
    or maximize self-consumption.
    """

    def __init__(
        self,
        battery_capacity_kwh: float = 10.0,
        max_charge_kw: float = 5.0,
        max_discharge_kw: float = 5.0,
        grid_export_limit_kw: float = 50.0,
        grid_import_limit_kw: float = 100.0,
        backup_soc_min: float = 0.10,
    ) -> None:
        self.battery_capacity_kwh = battery_capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        self.grid_export_limit_kw = grid_export_limit_kw
        self.grid_import_limit_kw = grid_import_limit_kw
        self.backup_soc_min = backup_soc_min

        self.mode = OptimizationMode.SELF_CONSUMPTION
        self.tariff = TariffSchedule()

        # Tracking
        self._total_import_kwh: float = 0.0
        self._total_export_kwh: float = 0.0
        self._total_pv_kwh: float = 0.0
        self._total_load_kwh: float = 0.0
        self._total_cost: float = 0.0
        self._total_revenue: float = 0.0
        self._peak_import_kw: float = 0.0
        self._step_count: int = 0

    def optimize(
        self,
        state: EnergyState,
        hour: int = 12,
        pv_forecast_kw: Optional[List[float]] = None,
        load_forecast_kw: Optional[List[float]] = None,
    ) -> OptimizationResult:
        """Compute optimal setpoints for current state."""

        if self.mode == OptimizationMode.SELF_CONSUMPTION:
            return self._optimize_self_consumption(state, hour)
        elif self.mode == OptimizationMode.COST_MINIMUM:
            return self._optimize_cost(state, hour)
        elif self.mode == OptimizationMode.PEAK_SHAVING:
            return self._optimize_peak_shaving(state, hour)
        elif self.mode == OptimizationMode.GRID_EXPORT:
            return self._optimize_export(state, hour)
        elif self.mode == OptimizationMode.BACKUP:
            return self._optimize_backup(state, hour)
        else:
            return self._manual_mode(state)

    def _optimize_self_consumption(
        self, state: EnergyState, hour: int,
    ) -> OptimizationResult:
        """Maximize self-consumption of PV generation."""
        surplus = state.net_power_kw
        recommendations: List[str] = []
        bat_kw = 0.0
        ev_kw = state.ev_power_kw

        if surplus > 0:
            # PV surplus — charge battery
            bat_kw = min(surplus, self.max_charge_kw)
            remaining = surplus - bat_kw
            if remaining > 0:
                ev_kw = min(remaining, 22.0)  # EV charging
                remaining -= ev_kw
            if remaining > 0.5:
                recommendations.append(
                    f"Export {remaining:.1f} kW surplus to grid"
                )
        else:
            # Deficit — discharge battery
            deficit = abs(surplus)
            if state.battery_soc > self.backup_soc_min:
                bat_kw = -min(deficit, self.max_discharge_kw)
                deficit += bat_kw  # bat_kw is negative

        grid_kw = (
            state.load_power_kw + ev_kw + bat_kw - state.pv_power_kw
        )

        import_rate = self.tariff.import_rate(hour)
        export_rate = self.tariff.export_rate(hour)
        cost = max(0, grid_kw) * import_rate / 60
        revenue = max(0, -grid_kw) * export_rate / 60

        return OptimizationResult(
            mode=self.mode.value,
            battery_strategy=BatteryStrategy.SELF_CONSUME.value,
            battery_setpoint_kw=bat_kw,
            ev_setpoint_kw=ev_kw,
            grid_setpoint_kw=grid_kw,
            export_limit_kw=self.grid_export_limit_kw,
            import_limit_kw=self.grid_import_limit_kw,
            estimated_cost=cost,
            estimated_revenue=revenue,
            recommendations=recommendations,
        )

    def _optimize_cost(
        self, state: EnergyState, hour: int,
    ) -> OptimizationResult:
        """Minimize electricity cost using TOU tariffs."""
        recommendations: List[str] = []
        bat_kw = 0.0

        if self.tariff.is_peak(hour):
            # Peak — discharge battery, minimize import
            if state.battery_soc > self.backup_soc_min:
                deficit = max(0, state.load_power_kw - state.pv_power_kw)
                bat_kw = -min(deficit, self.max_discharge_kw)
                recommendations.append("Peak hour: discharging battery")
        elif self.tariff.is_off_peak(hour):
            # Off-peak — charge battery
            spare = self.max_charge_kw
            if state.pv_power_kw > state.load_power_kw:
                spare = min(spare, state.pv_power_kw - state.load_power_kw)
            bat_kw = spare
            recommendations.append("Off-peak: charging battery")
        else:
            # Mid-peak — self-consume
            surplus = state.net_power_kw
            if surplus > 0:
                bat_kw = min(surplus, self.max_charge_kw)

        grid_kw = (
            state.load_power_kw + state.ev_power_kw
            + bat_kw - state.pv_power_kw
        )

        import_rate = self.tariff.import_rate(hour)
        export_rate = self.tariff.export_rate(hour)
        cost = max(0, grid_kw) * import_rate / 60
        revenue = max(0, -grid_kw) * export_rate / 60

        return OptimizationResult(
            mode=self.mode.value,
            battery_strategy=BatteryStrategy.TIME_OF_USE.value,
            battery_setpoint_kw=bat_kw,
            ev_setpoint_kw=state.ev_power_kw,
            grid_setpoint_kw=grid_kw,
            export_limit_kw=self.grid_export_limit_kw,
            import_limit_kw=self.grid_import_limit_kw,
            estimated_cost=cost,
            estimated_revenue=revenue,
            recommendations=recommendations,
        )

    def _optimize_peak_shaving(
        self, state: EnergyState, hour: int,
    ) -> OptimizationResult:
        """Keep grid import below a threshold."""
        threshold = self.grid_import_limit_kw * 0.5
        net_import = (
            state.load_power_kw + state.ev_power_kw - state.pv_power_kw
        )
        bat_kw = 0.0
        recommendations: List[str] = []

        if net_import > threshold:
            excess = net_import - threshold
            if state.battery_soc > self.backup_soc_min:
                bat_kw = -min(excess, self.max_discharge_kw)
                recommendations.append(
                    f"Peak shaving: discharging {abs(bat_kw):.1f} kW",
                )
        elif net_import < 0:
            bat_kw = min(abs(net_import), self.max_charge_kw)

        grid_kw = net_import + bat_kw

        return OptimizationResult(
            mode=self.mode.value,
            battery_strategy=BatteryStrategy.PEAK_SHAVE.value,
            battery_setpoint_kw=bat_kw,
            ev_setpoint_kw=state.ev_power_kw,
            grid_setpoint_kw=grid_kw,
            export_limit_kw=self.grid_export_limit_kw,
            import_limit_kw=threshold,
            estimated_cost=0.0,
            estimated_revenue=0.0,
            recommendations=recommendations,
        )

    def _optimize_export(
        self, state: EnergyState, hour: int,
    ) -> OptimizationResult:
        """Maximize grid export revenue."""
        bat_kw = -self.max_discharge_kw  # Discharge max
        if state.battery_soc <= self.backup_soc_min:
            bat_kw = 0.0

        grid_kw = (
            state.load_power_kw + state.ev_power_kw
            + bat_kw - state.pv_power_kw
        )
        grid_kw = max(-self.grid_export_limit_kw, grid_kw)

        export_rate = self.tariff.export_rate(hour)
        revenue = max(0, -grid_kw) * export_rate / 60

        return OptimizationResult(
            mode=self.mode.value,
            battery_strategy=BatteryStrategy.GRID_SUPPORT.value,
            battery_setpoint_kw=bat_kw,
            ev_setpoint_kw=state.ev_power_kw,
            grid_setpoint_kw=grid_kw,
            export_limit_kw=self.grid_export_limit_kw,
            import_limit_kw=self.grid_import_limit_kw,
            estimated_cost=0.0,
            estimated_revenue=revenue,
            recommendations=["Maximizing grid export"],
        )

    def _optimize_backup(
        self, state: EnergyState, hour: int,
    ) -> OptimizationResult:
        """Maintain battery reserve for backup power."""
        target_soc = 0.80
        bat_kw = 0.0
        recommendations: List[str] = []

        if state.battery_soc < target_soc:
            bat_kw = self.max_charge_kw
            recommendations.append(
                f"Charging to backup target: {target_soc*100:.0f}%"
            )

        grid_kw = (
            state.load_power_kw + state.ev_power_kw
            + bat_kw - state.pv_power_kw
        )

        return OptimizationResult(
            mode=self.mode.value,
            battery_strategy=BatteryStrategy.BACKUP_RESERVE.value,
            battery_setpoint_kw=bat_kw,
            ev_setpoint_kw=state.ev_power_kw,
            grid_setpoint_kw=grid_kw,
            export_limit_kw=self.grid_export_limit_kw,
            import_limit_kw=self.grid_import_limit_kw,
            estimated_cost=0.0,
            estimated_revenue=0.0,
            recommendations=recommendations,
        )

    def _manual_mode(self, state: EnergyState) -> OptimizationResult:
        """Pass-through manual mode."""
        return OptimizationResult(
            mode=self.mode.value,
            battery_strategy=BatteryStrategy.IDLE.value,
            battery_setpoint_kw=0.0,
            ev_setpoint_kw=state.ev_power_kw,
            grid_setpoint_kw=(
                state.load_power_kw + state.ev_power_kw
                - state.pv_power_kw
            ),
            export_limit_kw=self.grid_export_limit_kw,
            import_limit_kw=self.grid_import_limit_kw,
            estimated_cost=0.0,
            estimated_revenue=0.0,
            recommendations=["Manual mode — no automatic optimization"],
        )

    # -----------------------------------------------------------------------
    # Step simulation
    # -----------------------------------------------------------------------

    def step(
        self,
        state: EnergyState,
        dt_minutes: float = 1.0,
    ) -> Dict[str, Any]:
        """Run one optimization step and update accumulators."""
        now = datetime.now(timezone.utc)
        hour = now.hour

        result = self.optimize(state, hour)

        dt_hours = dt_minutes / 60.0
        import_kw = max(0, result.grid_setpoint_kw)
        export_kw = max(0, -result.grid_setpoint_kw)

        self._total_import_kwh += import_kw * dt_hours
        self._total_export_kwh += export_kw * dt_hours
        self._total_pv_kwh += state.pv_power_kw * dt_hours
        self._total_load_kwh += state.load_power_kw * dt_hours
        self._total_cost += result.estimated_cost * dt_minutes
        self._total_revenue += result.estimated_revenue * dt_minutes
        self._peak_import_kw = max(self._peak_import_kw, import_kw)
        self._step_count += 1

        return {
            "state": state.to_dict(),
            "optimization": result.to_dict(),
            "accumulators": self.accumulators(),
        }

    def accumulators(self) -> Dict[str, Any]:
        """Get accumulated energy counters."""
        return {
            "total_import_kwh": round(self._total_import_kwh, 2),
            "total_export_kwh": round(self._total_export_kwh, 2),
            "total_pv_kwh": round(self._total_pv_kwh, 2),
            "total_load_kwh": round(self._total_load_kwh, 2),
            "total_cost": round(self._total_cost, 4),
            "total_revenue": round(self._total_revenue, 4),
            "net_cost": round(
                self._total_cost - self._total_revenue, 4,
            ),
            "peak_import_kw": round(self._peak_import_kw, 2),
            "step_count": self._step_count,
            "self_sufficiency_pct": round(
                (1 - self._total_import_kwh / self._total_load_kwh) * 100
                if self._total_load_kwh > 0 else 0, 2,
            ),
        }
