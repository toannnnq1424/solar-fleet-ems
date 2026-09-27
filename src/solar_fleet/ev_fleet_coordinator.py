"""Electric vehicle fleet coordinator with dynamic load management and 1p3p switching.

Independently implemented for Solar Fleet EMS.
Concepts from evcc-master (core/site.go, core/loadpoint.go, charger/, vehicle/)
and OpenEMS io.openems.edge.evcs.cluster.
No code copied.

Provides:
- Dynamic Load Management (DLM) across multiple EV chargers respecting site breaker limits
- Automated 1-phase to 3-phase (1p3p) contactor switching to optimize solar surplus charging
- Anti-chattering hysteretic phase-switching protection timer
- Vehicle target SOC cutoff (e.g. 80% battery wear protection threshold)
- Priority queuing for multi-vehicle charging
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class ChargePhaseMode(int, Enum):
    """Phases allocated to vehicle."""

    SINGLE_PHASE = 1
    THREE_PHASE = 3


class ChargingMode(str, Enum):
    """EV charge mode per evcc."""

    OFF = "off"
    NOW = "now"          # Maximum power regardless of solar
    MIN_PV = "min_pv"    # Guaranteed minimum current + surplus solar
    PV = "pv"            # Pure solar surplus only (stops if solar drops)


# ---------------------------------------------------------------------------
# Loadpoint (EV Charger) State
# ---------------------------------------------------------------------------

@dataclass
class Loadpoint:
    """An individual EV charging port."""

    charger_id: str
    name: str
    connected_vehicle_id: Optional[str] = None
    vehicle_soc_pct: Optional[float] = None
    target_soc_pct: float = 80.0
    mode: ChargingMode = ChargingMode.PV
    min_current_amps: float = 6.0    # J1772 / IEC 61851 minimum pilot current
    max_current_amps: float = 32.0   # Standard Type 2 maximum
    allocated_phases: ChargePhaseMode = ChargePhaseMode.SINGLE_PHASE
    allocated_current_amps: float = 0.0
    actual_power_kw: float = 0.0
    priority: int = 1                # 1 = high, 5 = low
    is_charging: bool = False
    last_phase_switch_time: float = 0.0
    phase_switch_cooldown_seconds: float = 180.0  # 3 minutes anti-chattering

    @property
    def voltage_per_phase(self) -> float:
        return 230.0

    def calculate_power_for_current(self, amps: float, phases: ChargePhaseMode) -> float:
        """Calculate kW for given current and phase count."""
        return (amps * self.voltage_per_phase * phases.value) / 1000.0


# ---------------------------------------------------------------------------
# EV Fleet Coordinator (Dynamic Load Management)
# ---------------------------------------------------------------------------

class EVFleetCoordinator:
    """Coordinates fleet of EV chargers with DLM and solar phase switching."""

    def __init__(
        self,
        site_breaker_limit_kw: float = 40.0,
        enable_1p3p_switching: bool = True,
    ):
        self.site_breaker_limit_kw = site_breaker_limit_kw
        self.enable_1p3p = enable_1p3p_switching
        self.loadpoints: Dict[str, Loadpoint] = {}

    def add_loadpoint(self, lp: Loadpoint) -> None:
        self.loadpoints[lp.charger_id] = lp

    def update(
        self,
        available_solar_surplus_kw: float,
        building_base_load_kw: float,
        current_timestamp_seconds: float = 0.0,
    ) -> Dict[str, Any]:
        """Execute one allocation step across all connected EV chargers."""
        # 1. Total site headroom available for EV charging
        site_headroom_kw = max(0.0, self.site_breaker_limit_kw - building_base_load_kw)

        # 2. Check SOC limits: stop any vehicle that has reached target SOC
        for lp in self.loadpoints.values():
            if lp.connected_vehicle_id and lp.vehicle_soc_pct is not None:
                if lp.vehicle_soc_pct >= lp.target_soc_pct:
                    lp.is_charging = False
                    lp.allocated_current_amps = 0.0
                    lp.actual_power_kw = 0.0

        # Active chargers requiring allocation
        active_chargers = [
            lp for lp in self.loadpoints.values()
            if lp.connected_vehicle_id and lp.mode != ChargingMode.OFF and (lp.vehicle_soc_pct is None or lp.vehicle_soc_pct < lp.target_soc_pct)
        ]

        # Sort by priority
        active_chargers.sort(key=lambda x: x.priority)

        remaining_solar_kw = max(0.0, available_solar_surplus_kw)
        remaining_site_kw = site_headroom_kw
        total_ev_allocated_kw = 0.0

        for lp in active_chargers:
            # Determine target power based on mode
            if lp.mode == ChargingMode.NOW:
                # Target max available from site breaker
                target_power = min(remaining_site_kw, lp.calculate_power_for_current(lp.max_current_amps, lp.allocated_phases))
            elif lp.mode == ChargingMode.MIN_PV:
                # Min current guaranteed + solar surplus
                min_p = lp.calculate_power_for_current(lp.min_current_amps, lp.allocated_phases)
                target_power = min(remaining_site_kw, min_p + remaining_solar_kw)
            elif lp.mode == ChargingMode.PV:
                # Pure solar surplus
                min_p_1p = lp.calculate_power_for_current(lp.min_current_amps, ChargePhaseMode.SINGLE_PHASE)
                if remaining_solar_kw < min_p_1p:
                    # Not enough surplus to charge even at 6A 1-phase
                    lp.is_charging = False
                    lp.allocated_current_amps = 0.0
                    lp.actual_power_kw = 0.0
                    continue
                target_power = min(remaining_site_kw, remaining_solar_kw)
            else:
                target_power = 0.0

            # Automated 1p3p phase switching decision
            # Threshold to switch to 3-phase: surplus >= 4.2 kW (6A * 230V * 3)
            # Threshold to switch to 1-phase: surplus < 3.8 kW (hysteresis)
            if self.enable_1p3p:
                time_since_switch = current_timestamp_seconds - lp.last_phase_switch_time
                if time_since_switch >= lp.phase_switch_cooldown_seconds:
                    if lp.allocated_phases == ChargePhaseMode.SINGLE_PHASE and target_power >= 4.2:
                        lp.allocated_phases = ChargePhaseMode.THREE_PHASE
                        lp.last_phase_switch_time = current_timestamp_seconds
                    elif lp.allocated_phases == ChargePhaseMode.THREE_PHASE and target_power < 3.8:
                        lp.allocated_phases = ChargePhaseMode.SINGLE_PHASE
                        lp.last_phase_switch_time = current_timestamp_seconds

            # Convert target power to pilot current (Amps)
            current_amps = (target_power * 1000.0) / (lp.voltage_per_phase * lp.allocated_phases.value)
            clamped_amps = max(lp.min_current_amps, min(lp.max_current_amps, current_amps))
            actual_kw = lp.calculate_power_for_current(clamped_amps, lp.allocated_phases)

            # Ensure we do not breach site breaker headroom
            if actual_kw <= remaining_site_kw:
                lp.is_charging = True
                lp.allocated_current_amps = round(clamped_amps, 1)
                lp.actual_power_kw = round(actual_kw, 2)
                remaining_site_kw -= actual_kw
                remaining_solar_kw = max(0.0, remaining_solar_kw - actual_kw)
                total_ev_allocated_kw += actual_kw
            else:
                lp.is_charging = False
                lp.allocated_current_amps = 0.0
                lp.actual_power_kw = 0.0

        return {
            "site_breaker_limit_kw": self.site_breaker_limit_kw,
            "building_base_load_kw": building_base_load_kw,
            "available_headroom_kw": round(site_headroom_kw, 2),
            "total_ev_power_kw": round(total_ev_allocated_kw, 2),
            "remaining_solar_kw": round(remaining_solar_kw, 2),
            "chargers": [
                {
                    "charger_id": lp.charger_id,
                    "name": lp.name,
                    "is_charging": lp.is_charging,
                    "mode": lp.mode.value,
                    "phases": lp.allocated_phases.value,
                    "allocated_amps": lp.allocated_current_amps,
                    "power_kw": lp.actual_power_kw,
                    "vehicle_soc": lp.vehicle_soc_pct,
                    "target_soc": lp.target_soc_pct,
                }
                for lp in self.loadpoints.values()
            ],
        }
