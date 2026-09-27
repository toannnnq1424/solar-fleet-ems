"""ESS (Energy Storage System) controller — advanced battery strategies.

Independently implemented for Solar Fleet EMS.
Concepts from OpenEMS edge controllers:
- ess.gridoptimizedcharge: grid-optimized charging
- ess.delaycharge: delayed charging
- ess.emergencycapacityreserve: emergency reserve
- ess.limittotaldischarge: total discharge limiter
- ess.cycle: cycle management
- ess.fixstateofcharge: SOC targeting
No code copied — clean-room implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional


class ESSMode(str, Enum):
    """ESS operating mode."""

    GRID_OPTIMIZED = "grid_optimized"
    DELAYED_CHARGE = "delayed_charge"
    EMERGENCY_RESERVE = "emergency_reserve"
    LIMIT_DISCHARGE = "limit_discharge"
    FIX_SOC = "fix_soc"
    SELF_CONSUMPTION = "self_consumption"
    MANUAL = "manual"
    IDLE = "idle"


class ESSState(str, Enum):
    CHARGING = "charging"
    DISCHARGING = "discharging"
    IDLE = "idle"
    STANDBY = "standby"
    FAULT = "fault"


@dataclass
class ESSStatus:
    """ESS real-time status."""

    soc_pct: float = 50.0
    power_w: int = 0          # + charge, - discharge
    voltage_v: float = 48.0
    current_a: float = 0.0
    temperature_c: float = 25.0
    state: ESSState = ESSState.IDLE
    mode: ESSMode = ESSMode.SELF_CONSUMPTION
    capacity_kwh: float = 10.0
    max_charge_w: int = 5000
    max_discharge_w: int = 5000
    energy_kwh: float = 5.0  # Current stored energy
    cycles: float = 0.0

    @property
    def soh_pct(self) -> float:
        """Estimated State of Health."""
        if self.cycles <= 0:
            return 100.0
        # Simple linear degradation model
        return max(0, 100 - self.cycles * 0.01)

    def to_dict(self) -> dict[str, Any]:
        return {
            "soc_pct": round(self.soc_pct, 1),
            "power_w": self.power_w,
            "voltage_v": round(self.voltage_v, 1),
            "current_a": round(self.current_a, 1),
            "temperature_c": round(self.temperature_c, 1),
            "state": self.state.value,
            "mode": self.mode.value,
            "capacity_kwh": self.capacity_kwh,
            "energy_kwh": round(self.energy_kwh, 2),
            "soh_pct": round(self.soh_pct, 1),
            "cycles": round(self.cycles, 1),
        }


# ---------------------------------------------------------------------------
# ESS Controller
# ---------------------------------------------------------------------------

class ESSController:
    """Advanced ESS controller with multiple strategies.

    Implements grid-optimized charge, delayed charge,
    emergency reserve, discharge limiting, SOC targeting,
    and self-consumption optimization.
    """

    def __init__(
        self,
        capacity_kwh: float = 10.0,
        max_charge_w: int = 5000,
        max_discharge_w: int = 5000,
        min_soc_pct: float = 5.0,
        max_soc_pct: float = 95.0,
    ) -> None:
        self.capacity_kwh = capacity_kwh
        self.max_charge_w = max_charge_w
        self.max_discharge_w = max_discharge_w
        self.min_soc_pct = min_soc_pct
        self.max_soc_pct = max_soc_pct

        self.status = ESSStatus(
            capacity_kwh=capacity_kwh,
            max_charge_w=max_charge_w,
            max_discharge_w=max_discharge_w,
        )

        # Strategy parameters
        self._emergency_reserve_pct: float = 20.0
        self._target_soc_pct: float = 50.0
        self._grid_charge_limit_w: int = 3000
        self._delay_until: Optional[str] = None
        self._discharge_limit_kwh: float = 0.0
        self._total_discharge_kwh: float = 0.0

    def set_mode(self, mode: ESSMode) -> None:
        self.status.mode = mode

    def compute_setpoint(
        self,
        grid_power_w: int = 0,
        pv_power_w: int = 0,
        load_power_w: int = 0,
        hour: int = 12,
        import_price: float = 0.1,
        export_price: float = 0.05,
    ) -> int:
        """Compute battery power setpoint based on active mode.

        Returns setpoint in watts (+ charge, - discharge).
        """
        mode = self.status.mode

        if mode == ESSMode.SELF_CONSUMPTION:
            return self._self_consumption(
                grid_power_w, pv_power_w, load_power_w,
            )
        elif mode == ESSMode.GRID_OPTIMIZED:
            return self._grid_optimized(
                grid_power_w, pv_power_w, load_power_w,
                import_price, export_price,
            )
        elif mode == ESSMode.DELAYED_CHARGE:
            return self._delayed_charge(
                pv_power_w, load_power_w, hour,
            )
        elif mode == ESSMode.EMERGENCY_RESERVE:
            return self._emergency_reserve(
                pv_power_w, load_power_w,
            )
        elif mode == ESSMode.LIMIT_DISCHARGE:
            return self._limit_discharge(
                grid_power_w, pv_power_w, load_power_w,
            )
        elif mode == ESSMode.FIX_SOC:
            return self._fix_soc()
        elif mode == ESSMode.MANUAL:
            return self.status.power_w
        else:
            return 0

    def apply_setpoint(
        self, setpoint_w: int, dt_seconds: float,
    ) -> ESSStatus:
        """Apply power setpoint and update state."""
        # Clamp to limits
        if setpoint_w > 0:
            setpoint_w = min(setpoint_w, self.max_charge_w)
            # Check SOC ceiling
            if self.status.soc_pct >= self.max_soc_pct:
                setpoint_w = 0
        elif setpoint_w < 0:
            setpoint_w = max(setpoint_w, -self.max_discharge_w)
            # Check SOC floor
            if self.status.soc_pct <= self.min_soc_pct:
                setpoint_w = 0

        # Update energy
        dt_hours = dt_seconds / 3600.0
        energy_delta_kwh = setpoint_w * dt_hours / 1000.0
        self.status.energy_kwh += energy_delta_kwh
        self.status.energy_kwh = max(
            0, min(self.capacity_kwh, self.status.energy_kwh),
        )

        # Update SOC
        if self.capacity_kwh > 0:
            self.status.soc_pct = (
                self.status.energy_kwh / self.capacity_kwh * 100
            )

        # Update state
        self.status.power_w = setpoint_w
        if setpoint_w > 10:
            self.status.state = ESSState.CHARGING
        elif setpoint_w < -10:
            self.status.state = ESSState.DISCHARGING
            self._total_discharge_kwh += abs(energy_delta_kwh)
        else:
            self.status.state = ESSState.IDLE

        # Update cycles (throughput-based)
        self.status.cycles = (
            self._total_discharge_kwh / self.capacity_kwh
        )

        return self.status

    # -----------------------------------------------------------------------
    # Strategy implementations
    # -----------------------------------------------------------------------

    def _self_consumption(
        self, grid_w: int, pv_w: int, load_w: int,
    ) -> int:
        """Maximize self-consumption of PV."""
        surplus = pv_w - load_w
        if surplus > 0:
            return min(surplus, self.max_charge_w)
        elif surplus < 0:
            return max(surplus, -self.max_discharge_w)
        return 0

    def _grid_optimized(
        self,
        grid_w: int,
        pv_w: int,
        load_w: int,
        import_price: float,
        export_price: float,
    ) -> int:
        """Grid-optimized charge — minimize cost.

        Charge from grid only when price is very low.
        Discharge when price is high.
        """
        surplus = pv_w - load_w

        if surplus > 0:
            # PV surplus — always charge from solar
            return min(surplus, self.max_charge_w)
        elif import_price < 0.08:
            # Very cheap grid — charge from grid
            return min(self._grid_charge_limit_w, self.max_charge_w)
        elif import_price > 0.20 and self.status.soc_pct > 20:
            # Expensive — discharge
            deficit = abs(surplus)
            return max(-deficit, -self.max_discharge_w)
        else:
            # Mid-price — minimize grid usage
            if surplus < 0 and self.status.soc_pct > 30:
                return max(surplus, -self.max_discharge_w)
            return 0

    def _delayed_charge(
        self, pv_w: int, load_w: int, hour: int,
    ) -> int:
        """Delay charging until PV is available or off-peak.

        OpenEMS ess.delaycharge concept.
        """
        surplus = pv_w - load_w

        # Only charge from surplus during day
        if 6 <= hour <= 18 and surplus > 0:
            return min(surplus, self.max_charge_w)
        # Off-peak grid charge (night)
        elif hour < 6 or hour >= 22:
            return min(
                self._grid_charge_limit_w, self.max_charge_w,
            )
        # Discharge to cover load during peak
        elif surplus < 0 and self.status.soc_pct > 20:
            return max(surplus, -self.max_discharge_w)
        return 0

    def _emergency_reserve(
        self, pv_w: int, load_w: int,
    ) -> int:
        """Maintain emergency capacity reserve.

        OpenEMS ess.emergencycapacityreserve concept.
        """
        if self.status.soc_pct < self._emergency_reserve_pct:
            # Must charge to reserve level
            return min(self.max_charge_w, max(pv_w, 2000))
        elif self.status.soc_pct < self._emergency_reserve_pct + 5:
            # Near reserve — only charge from surplus
            surplus = pv_w - load_w
            return max(0, min(surplus, self.max_charge_w))
        else:
            # Normal operation — self-consume
            surplus = pv_w - load_w
            if surplus > 0:
                return min(surplus, self.max_charge_w)
            elif surplus < 0:
                # Don't discharge below reserve
                margin = (
                    self.status.soc_pct - self._emergency_reserve_pct
                )
                if margin > 5:
                    return max(surplus, -self.max_discharge_w)
            return 0

    def _limit_discharge(
        self, grid_w: int, pv_w: int, load_w: int,
    ) -> int:
        """Limit total discharge energy.

        OpenEMS ess.limittotaldischarge concept.
        """
        surplus = pv_w - load_w

        if surplus > 0:
            return min(surplus, self.max_charge_w)
        elif surplus < 0:
            # Check discharge limit
            if self._discharge_limit_kwh > 0:
                remaining = (
                    self._discharge_limit_kwh
                    - self._total_discharge_kwh
                )
                if remaining <= 0:
                    return 0  # Limit reached
            return max(surplus, -self.max_discharge_w)
        return 0

    def _fix_soc(self) -> int:
        """Drive SOC toward target.

        OpenEMS ess.fixstateofcharge concept.
        """
        delta = self._target_soc_pct - self.status.soc_pct
        if abs(delta) < 1.0:
            return 0  # Close enough

        # Proportional control
        power_w = int(
            delta / 100.0 * self.capacity_kwh * 1000 * 0.5
        )
        if power_w > 0:
            return min(power_w, self.max_charge_w)
        else:
            return max(power_w, -self.max_discharge_w)

    def set_emergency_reserve(self, pct: float) -> None:
        self._emergency_reserve_pct = max(5, min(95, pct))

    def set_target_soc(self, pct: float) -> None:
        self._target_soc_pct = max(
            self.min_soc_pct, min(self.max_soc_pct, pct),
        )

    def set_discharge_limit(self, kwh: float) -> None:
        self._discharge_limit_kwh = max(0, kwh)

    def set_grid_charge_limit(self, watts: int) -> None:
        self._grid_charge_limit_w = max(0, min(watts, self.max_charge_w))

    def get_status(self) -> Dict[str, Any]:
        return self.status.to_dict()
