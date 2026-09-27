"""Microgrid controller — islanding, reconnection, and load management.

Independently implemented for Solar Fleet EMS.
Architectural concepts inspired by virtual-power-plant-main (MIT license).
Source provenance: virtual-power-plant-main commit HEAD, src/vpp/grid/microgrid.py.

Manages transitions between grid-connected and islanded operation,
coordinates grid-forming inverters, and implements priority-based
load shedding when generation is insufficient.
"""

from __future__ import annotations

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Grid states and data structures
# ---------------------------------------------------------------------------

class MicrogridState(str, Enum):
    """Microgrid operating mode."""

    GRID_CONNECTED = "grid_connected"
    ISLANDING = "islanding"
    ISLANDED = "islanded"
    RECONNECTING = "reconnecting"
    FAULT = "fault"


class InverterMode(str, Enum):
    """Inverter operating mode."""

    GRID_FOLLOWING = "grid_following"
    GRID_FORMING = "grid_forming"
    STANDBY = "standby"
    FAULT = "fault"


@dataclass
class LoadPriority:
    """A load with a shedding priority.

    Priority 1 = critical (never shed), 10 = lowest priority.
    """

    load_id: str
    name: str
    power_kw: float
    priority: int = 5
    is_shed: bool = False
    is_critical: bool = False

    def to_dict(self) -> dict[str, Any]:
        return {
            "load_id": self.load_id,
            "name": self.name,
            "power_kw": round(self.power_kw, 2),
            "priority": self.priority,
            "is_shed": self.is_shed,
            "is_critical": self.is_critical,
        }


@dataclass
class InverterState:
    """Instantaneous inverter operating point."""

    inverter_id: str
    mode: InverterMode = InverterMode.STANDBY
    real_power_kw: float = 0.0
    reactive_power_kvar: float = 0.0
    voltage_pu: float = 1.0
    frequency_hz: float = 50.0
    power_factor: float = 1.0
    rated_power_kw: float = 10.0
    is_online: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "inverter_id": self.inverter_id,
            "mode": self.mode.value,
            "real_power_kw": round(self.real_power_kw, 3),
            "reactive_power_kvar": round(self.reactive_power_kvar, 3),
            "voltage_pu": round(self.voltage_pu, 4),
            "frequency_hz": round(self.frequency_hz, 3),
            "power_factor": round(self.power_factor, 3),
            "rated_power_kw": self.rated_power_kw,
            "is_online": self.is_online,
        }

    @property
    def available_power_kw(self) -> float:
        """Headroom above current output."""
        if not self.is_online:
            return 0.0
        return max(0, self.rated_power_kw - abs(self.real_power_kw))


@dataclass
class MicrogridMetrics:
    """Runtime metrics for the microgrid controller."""

    island_events: int = 0
    reconnection_events: int = 0
    load_shed_events: int = 0
    total_island_duration_s: float = 0.0
    total_shed_energy_kwh: float = 0.0
    last_island_at: Optional[float] = None
    last_reconnect_at: Optional[float] = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "island_events": self.island_events,
            "reconnection_events": self.reconnection_events,
            "load_shed_events": self.load_shed_events,
            "total_island_duration_s": round(self.total_island_duration_s, 1),
            "total_shed_energy_kwh": round(self.total_shed_energy_kwh, 3),
        }


# ---------------------------------------------------------------------------
# Droop control model
# ---------------------------------------------------------------------------

@dataclass
class DroopParameters:
    """Droop control parameters for grid-forming inverters."""

    # Frequency droop: delta_f / f_nom = -Kp * (P - P_ref) / P_rated
    kp: float = 0.05  # 5% droop
    # Voltage droop: delta_V / V_nom = -Kq * (Q - Q_ref) / Q_rated
    kq: float = 0.05


class DroopController:
    """Simple droop control for grid-forming inverters.

    Implements P-f and Q-V droop characteristic for voltage and frequency
    regulation during island mode.
    """

    def __init__(
        self,
        params: DroopParameters,
        nominal_frequency_hz: float = 50.0,
        nominal_voltage_pu: float = 1.0,
    ) -> None:
        self.params = params
        self.f_nom = nominal_frequency_hz
        self.v_nom = nominal_voltage_pu

    def frequency_setpoint(
        self,
        p_kw: float,
        p_ref_kw: float,
        p_rated_kw: float,
    ) -> float:
        """Calculate frequency setpoint from active power via P-f droop."""
        if p_rated_kw <= 0:
            return self.f_nom
        delta_p_pu = (p_kw - p_ref_kw) / p_rated_kw
        return self.f_nom * (1.0 - self.params.kp * delta_p_pu)

    def voltage_setpoint(
        self,
        q_kvar: float,
        q_ref_kvar: float,
        q_rated_kvar: float,
    ) -> float:
        """Calculate voltage setpoint from reactive power via Q-V droop."""
        if q_rated_kvar <= 0:
            return self.v_nom
        delta_q_pu = (q_kvar - q_ref_kvar) / q_rated_kvar
        return self.v_nom * (1.0 - self.params.kq * delta_q_pu)


# ---------------------------------------------------------------------------
# Microgrid controller
# ---------------------------------------------------------------------------

class MicrogridController:
    """Microgrid controller managing island/reconnect transitions.

    Coordinates:
    - Island detection (frequency/voltage deviation beyond thresholds)
    - Transition to island mode (switch grid-following → grid-forming)
    - Priority-based load shedding when generation < demand
    - Resynchronisation and reconnection to the main grid
    """

    def __init__(
        self,
        nominal_frequency_hz: float = 50.0,
        nominal_voltage_pu: float = 1.0,
        frequency_threshold_hz: float = 0.5,
        voltage_threshold_pu: float = 0.1,
        resync_frequency_tolerance_hz: float = 0.05,
        resync_voltage_tolerance_pu: float = 0.02,
        resync_phase_tolerance_deg: float = 5.0,
    ) -> None:
        self.nominal_frequency_hz = nominal_frequency_hz
        self.nominal_voltage_pu = nominal_voltage_pu
        self.frequency_threshold_hz = frequency_threshold_hz
        self.voltage_threshold_pu = voltage_threshold_pu
        self.resync_frequency_tolerance_hz = resync_frequency_tolerance_hz
        self.resync_voltage_tolerance_pu = resync_voltage_tolerance_pu
        self.resync_phase_tolerance_deg = resync_phase_tolerance_deg

        self._state = MicrogridState.GRID_CONNECTED
        self._inverters: Dict[str, InverterState] = {}
        self._loads: Dict[str, LoadPriority] = {}
        self._metrics = MicrogridMetrics()
        self._island_start: Optional[float] = None
        self._droop = DroopController(DroopParameters())

    @property
    def state(self) -> MicrogridState:
        """Current microgrid state."""
        return self._state

    def register_inverter(self, inverter: InverterState) -> None:
        """Register an inverter with the controller."""
        self._inverters[inverter.inverter_id] = inverter
        logger.info("Registered inverter %s", inverter.inverter_id)

    def register_load(self, load: LoadPriority) -> None:
        """Register a load with priority for shedding."""
        self._loads[load.load_id] = load
        logger.info("Registered load %s (priority %d)", load.load_id, load.priority)

    def update(
        self,
        grid_voltage_pu: float,
        grid_frequency_hz: float,
        grid_phase_deg: float = 0.0,
        dt_seconds: float = 1.0,
    ) -> Dict[str, Any]:
        """Update microgrid state based on current measurements.

        Parameters
        ----------
        grid_voltage_pu : float
            Measured grid voltage in per-unit.
        grid_frequency_hz : float
            Measured grid frequency in Hz.
        grid_phase_deg : float
            Phase angle difference for resync check.
        dt_seconds : float
            Time since last update.

        Returns
        -------
        dict
            Status update including state transitions and actions taken.
        """

        now = time.monotonic()
        actions: List[str] = []
        prev_state = self._state

        if self._state == MicrogridState.GRID_CONNECTED:
            if self._detect_island(grid_voltage_pu, grid_frequency_hz):
                self._state = MicrogridState.ISLANDING
                actions.append("island_detected")
                logger.warning("Island condition detected: V=%.3f pu, f=%.2f Hz",
                               grid_voltage_pu, grid_frequency_hz)

        elif self._state == MicrogridState.ISLANDING:
            self._transition_to_island(now)
            self._state = MicrogridState.ISLANDED
            actions.append("island_transition_complete")
            logger.info("Islanded mode active")

        elif self._state == MicrogridState.ISLANDED:
            # Track duration
            if self._island_start is not None:
                self._metrics.total_island_duration_s += dt_seconds

            # Check load balance
            shed_result = self._manage_loads(dt_seconds)
            if shed_result:
                actions.extend(shed_result)

            # Check for grid restoration
            if self._detect_grid_restoration(grid_voltage_pu, grid_frequency_hz):
                self._state = MicrogridState.RECONNECTING
                actions.append("grid_restoration_detected")
                logger.info("Grid restoration detected, starting resync")

        elif self._state == MicrogridState.RECONNECTING:
            if self._check_resync(grid_voltage_pu, grid_frequency_hz, grid_phase_deg):
                self._reconnect(now)
                self._state = MicrogridState.GRID_CONNECTED
                actions.append("reconnected")
                logger.info("Reconnected to grid")
            else:
                actions.append("resync_pending")

        return {
            "state": self._state.value,
            "previous_state": prev_state.value,
            "actions": actions,
            "metrics": self._metrics.to_dict(),
            "inverter_count": len(self._inverters),
            "load_count": len(self._loads),
            "shed_loads": [ld.load_id for ld in self._loads.values() if ld.is_shed],
        }

    def _detect_island(self, voltage_pu: float, frequency_hz: float) -> bool:
        """Detect islanding by frequency/voltage deviation."""
        freq_deviation = abs(frequency_hz - self.nominal_frequency_hz)
        volt_deviation = abs(voltage_pu - self.nominal_voltage_pu)
        return (
            freq_deviation > self.frequency_threshold_hz
            or volt_deviation > self.voltage_threshold_pu
        )

    def _detect_grid_restoration(self, voltage_pu: float, frequency_hz: float) -> bool:
        """Detect if grid has been restored (within normal bounds)."""
        freq_deviation = abs(frequency_hz - self.nominal_frequency_hz)
        volt_deviation = abs(voltage_pu - self.nominal_voltage_pu)
        return (
            freq_deviation < self.frequency_threshold_hz * 0.5
            and volt_deviation < self.voltage_threshold_pu * 0.5
        )

    def _transition_to_island(self, now: float) -> None:
        """Transition inverters to island mode."""
        self._island_start = now
        self._metrics.island_events += 1
        self._metrics.last_island_at = now

        # Switch first capable inverter to grid-forming
        for inv in self._inverters.values():
            if inv.is_online and inv.mode == InverterMode.GRID_FOLLOWING:
                inv.mode = InverterMode.GRID_FORMING
                logger.info("Inverter %s switched to grid-forming", inv.inverter_id)
                break

    def _check_resync(
        self,
        grid_voltage_pu: float,
        grid_frequency_hz: float,
        grid_phase_deg: float,
    ) -> bool:
        """Check if resynchronisation conditions are met."""
        freq_ok = abs(grid_frequency_hz - self.nominal_frequency_hz) < self.resync_frequency_tolerance_hz
        volt_ok = abs(grid_voltage_pu - self.nominal_voltage_pu) < self.resync_voltage_tolerance_pu
        phase_ok = abs(grid_phase_deg) < self.resync_phase_tolerance_deg
        return freq_ok and volt_ok and phase_ok

    def _reconnect(self, now: float) -> None:
        """Reconnect to grid: restore all loads and inverter modes."""
        self._metrics.reconnection_events += 1
        self._metrics.last_reconnect_at = now

        if self._island_start is not None:
            duration = now - self._island_start
            self._metrics.total_island_duration_s += duration
            self._island_start = None

        # Restore inverters to grid-following
        for inv in self._inverters.values():
            if inv.mode == InverterMode.GRID_FORMING:
                inv.mode = InverterMode.GRID_FOLLOWING

        # Restore shed loads
        for load in self._loads.values():
            load.is_shed = False

    def _manage_loads(self, dt_seconds: float) -> List[str]:
        """Manage load shedding during island mode.

        Sheds loads in priority order (highest priority number first)
        until generation meets demand.
        """

        actions: List[str] = []

        total_generation = sum(
            inv.real_power_kw for inv in self._inverters.values()
            if inv.is_online and inv.real_power_kw > 0
        )
        total_load = sum(
            load.power_kw for load in self._loads.values()
            if not load.is_shed
        )

        if total_load > total_generation * 1.05:  # 5% margin
            # Need to shed loads
            # Sort by priority descending (shed lowest priority first)
            shed_candidates = sorted(
                [ld for ld in self._loads.values() if not ld.is_shed and not ld.is_critical],
                key=lambda ld: -ld.priority,
            )

            excess = total_load - total_generation
            for load in shed_candidates:
                if excess <= 0:
                    break
                load.is_shed = True
                excess -= load.power_kw
                self._metrics.load_shed_events += 1
                self._metrics.total_shed_energy_kwh += load.power_kw * dt_seconds / 3600.0
                actions.append(f"shed:{load.load_id}")
                logger.warning("Shed load %s (%.1f kW, priority %d)",
                               load.load_id, load.power_kw, load.priority)

        elif total_load < total_generation * 0.8:
            # Restore loads that were shed (highest priority first)
            restore_candidates = sorted(
                [ld for ld in self._loads.values() if ld.is_shed],
                key=lambda ld: ld.priority,
            )
            for load in restore_candidates:
                if total_load + load.power_kw < total_generation * 0.9:
                    load.is_shed = False
                    total_load += load.power_kw
                    actions.append(f"restore:{load.load_id}")
                    logger.info("Restored load %s", load.load_id)

        return actions

    def get_inverters(self) -> List[Dict[str, Any]]:
        """Return inverter states."""
        return [inv.to_dict() for inv in self._inverters.values()]

    def get_loads(self) -> List[Dict[str, Any]]:
        """Return load states."""
        return [load.to_dict() for load in self._loads.values()]

    def status(self) -> Dict[str, Any]:
        """Return full microgrid status."""
        total_generation = sum(
            inv.real_power_kw for inv in self._inverters.values()
            if inv.is_online and inv.real_power_kw > 0
        )
        total_load = sum(
            load.power_kw for load in self._loads.values()
            if not load.is_shed
        )
        total_capacity = sum(
            inv.rated_power_kw for inv in self._inverters.values()
            if inv.is_online
        )

        return {
            "state": self._state.value,
            "total_generation_kw": round(total_generation, 2),
            "total_load_kw": round(total_load, 2),
            "total_capacity_kw": round(total_capacity, 2),
            "utilization_pct": round(
                total_generation / total_capacity * 100 if total_capacity > 0 else 0, 1
            ),
            "inverters": self.get_inverters(),
            "loads": self.get_loads(),
            "metrics": self._metrics.to_dict(),
        }
