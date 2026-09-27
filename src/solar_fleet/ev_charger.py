"""EV charger management and smart charging for solar fleet.

Independently implemented for Solar Fleet EMS.
Concepts informed by evcc-master (MIT license) —
charge planning and solar-surplus charging logic.
No code copied.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Enums and data structures
# ---------------------------------------------------------------------------

class ChargeMode(str, Enum):
    """EV charge mode."""

    OFF = "off"
    NOW = "now"             # Charge immediately at max rate
    SOLAR = "solar"         # Only charge from solar surplus
    MIN_SOLAR = "min+solar"  # Min grid + solar surplus
    SCHEDULED = "scheduled"  # Charge by target time
    SMART = "smart"          # AI/price-optimized


class ChargerStatus(str, Enum):
    """Charger hardware status."""

    AVAILABLE = "available"
    PREPARING = "preparing"
    CHARGING = "charging"
    SUSPENDED = "suspended"
    FINISHING = "finishing"
    FAULTED = "faulted"
    OFFLINE = "offline"


class PhaseMode(str, Enum):
    """Phase switching for charge optimization."""

    SINGLE = "1p"
    THREE = "3p"
    AUTO = "auto"


@dataclass
class EVSession:
    """Active EV charging session."""

    session_id: str
    charger_id: str
    vehicle_id: str = ""
    start_time: str = ""
    energy_kwh: float = 0.0
    target_soc_pct: float = 80.0
    target_time: str = ""
    current_soc_pct: float = 0.0
    battery_capacity_kwh: float = 60.0
    charge_mode: ChargeMode = ChargeMode.NOW
    max_current_a: float = 32.0
    min_current_a: float = 6.0
    phases: int = 3
    active_current_a: float = 0.0
    active_power_kw: float = 0.0
    is_active: bool = True

    @property
    def energy_needed_kwh(self) -> float:
        """Energy needed to reach target SOC."""
        delta_soc = max(0, self.target_soc_pct - self.current_soc_pct)
        return delta_soc / 100.0 * self.battery_capacity_kwh

    @property
    def time_to_full_hours(self) -> float:
        """Estimated hours to reach target at current power."""
        if self.active_power_kw <= 0:
            return float("inf")
        return self.energy_needed_kwh / self.active_power_kw

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "charger_id": self.charger_id,
            "vehicle_id": self.vehicle_id,
            "energy_kwh": round(self.energy_kwh, 2),
            "current_soc_pct": round(self.current_soc_pct, 1),
            "target_soc_pct": self.target_soc_pct,
            "charge_mode": self.charge_mode.value,
            "active_current_a": round(self.active_current_a, 1),
            "active_power_kw": round(self.active_power_kw, 2),
            "energy_needed_kwh": round(self.energy_needed_kwh, 2),
            "is_active": self.is_active,
        }


@dataclass
class Charger:
    """EV charger device."""

    charger_id: str
    name: str
    max_power_kw: float = 22.0
    min_power_kw: float = 1.38
    max_current_a: float = 32.0
    min_current_a: float = 6.0
    phases: int = 3
    voltage_v: float = 230.0
    status: ChargerStatus = ChargerStatus.AVAILABLE
    phase_mode: PhaseMode = PhaseMode.THREE
    active_session: Optional[EVSession] = None
    location: str = ""
    connector_type: str = "Type2"

    @property
    def max_power_actual_kw(self) -> float:
        """Actual max power considering phase mode."""
        if self.phase_mode == PhaseMode.SINGLE:
            return self.max_current_a * self.voltage_v / 1000.0
        return self.max_current_a * self.voltage_v * 3 / 1000.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "charger_id": self.charger_id,
            "name": self.name,
            "max_power_kw": self.max_power_kw,
            "max_current_a": self.max_current_a,
            "phases": self.phases,
            "status": self.status.value,
            "phase_mode": self.phase_mode.value,
            "connector_type": self.connector_type,
            "has_active_session": self.active_session is not None,
            "active_session": (
                self.active_session.to_dict()
                if self.active_session else None
            ),
        }


# ---------------------------------------------------------------------------
# Charge controller
# ---------------------------------------------------------------------------

class ChargeController:
    """EV charge controller — manages charger fleet and sessions.

    Implements solar-surplus charging, scheduled charging,
    and smart price-optimized charging.
    """

    def __init__(self, grid_voltage_v: float = 230.0) -> None:
        self.grid_voltage = grid_voltage_v
        self._chargers: Dict[str, Charger] = {}
        self._sessions: Dict[str, EVSession] = {}
        self._total_energy_kwh: float = 0.0

    def register_charger(self, charger: Charger) -> None:
        """Register a charger device."""
        self._chargers[charger.charger_id] = charger

    def start_session(self, session: EVSession) -> EVSession:
        """Start a new charging session."""
        if session.charger_id not in self._chargers:
            raise ValueError(f"Charger {session.charger_id} not found")

        charger = self._chargers[session.charger_id]
        charger.active_session = session
        charger.status = ChargerStatus.PREPARING
        self._sessions[session.session_id] = session

        if not session.start_time:
            session.start_time = datetime.now(timezone.utc).isoformat()

        return session

    def stop_session(self, session_id: str) -> Optional[EVSession]:
        """Stop a charging session."""
        session = self._sessions.get(session_id)
        if session is None:
            return None

        session.is_active = False
        session.active_current_a = 0.0
        session.active_power_kw = 0.0

        charger = self._chargers.get(session.charger_id)
        if charger:
            charger.active_session = None
            charger.status = ChargerStatus.AVAILABLE

        return session

    def update(
        self,
        dt_seconds: float,
        solar_surplus_kw: float = 0.0,
        grid_price: float = 0.1,
    ) -> Dict[str, Any]:
        """Update all active sessions for one time step.

        Parameters
        ----------
        dt_seconds : float
            Time step in seconds.
        solar_surplus_kw : float
            Available solar surplus power.
        grid_price : float
            Current grid electricity price ($/kWh).

        Returns
        -------
        dict
            Summary of current charging state.
        """
        remaining_surplus = solar_surplus_kw
        total_power = 0.0
        session_updates: List[Dict[str, Any]] = []

        for session in list(self._sessions.values()):
            if not session.is_active:
                continue

            charger = self._chargers.get(session.charger_id)
            if charger is None:
                continue

            # Calculate target power
            target_power = self._calculate_target_power(
                session, charger, remaining_surplus, grid_price,
            )

            # Apply power
            session.active_power_kw = target_power
            if charger.phases > 0 and self.grid_voltage > 0:
                session.active_current_a = (
                    target_power * 1000
                    / (self.grid_voltage * charger.phases)
                )

            # Update energy
            dt_hours = dt_seconds / 3600.0
            energy_step = target_power * dt_hours
            session.energy_kwh += energy_step
            self._total_energy_kwh += energy_step

            # Update SOC
            if session.battery_capacity_kwh > 0:
                soc_delta = energy_step / session.battery_capacity_kwh
                session.current_soc_pct += soc_delta * 100

            # Check completion
            if session.current_soc_pct >= session.target_soc_pct:
                session.current_soc_pct = session.target_soc_pct
                session.active_power_kw = 0.0
                session.active_current_a = 0.0
                charger.status = ChargerStatus.FINISHING

            # Deduct from surplus
            if session.charge_mode in (
                ChargeMode.SOLAR, ChargeMode.MIN_SOLAR,
            ):
                remaining_surplus -= target_power

            total_power += target_power
            charger.status = (
                ChargerStatus.CHARGING if target_power > 0.01
                else ChargerStatus.SUSPENDED
            )

            session_updates.append(session.to_dict())

        return {
            "total_power_kw": round(total_power, 2),
            "solar_surplus_used_kw": round(
                solar_surplus_kw - remaining_surplus, 2,
            ),
            "active_sessions": len(session_updates),
            "sessions": session_updates,
        }

    def _calculate_target_power(
        self,
        session: EVSession,
        charger: Charger,
        solar_surplus_kw: float,
        grid_price: float,
    ) -> float:
        """Calculate target charge power based on mode."""

        if session.current_soc_pct >= session.target_soc_pct:
            return 0.0

        max_kw = min(charger.max_power_kw, charger.max_power_actual_kw)

        if session.charge_mode == ChargeMode.OFF:
            return 0.0

        elif session.charge_mode == ChargeMode.NOW:
            return max_kw

        elif session.charge_mode == ChargeMode.SOLAR:
            if solar_surplus_kw > charger.min_power_kw:
                return min(max_kw, solar_surplus_kw)
            return 0.0

        elif session.charge_mode == ChargeMode.MIN_SOLAR:
            # Minimum charge rate + solar surplus
            min_kw = charger.min_power_kw
            solar_add = max(0, solar_surplus_kw)
            return min(max_kw, min_kw + solar_add)

        elif session.charge_mode == ChargeMode.SCHEDULED:
            return self._scheduled_power(session, max_kw)

        elif session.charge_mode == ChargeMode.SMART:
            return self._smart_power(
                session, max_kw, solar_surplus_kw, grid_price,
            )

        return 0.0

    def _scheduled_power(
        self, session: EVSession, max_kw: float,
    ) -> float:
        """Calculate power for scheduled charging."""
        if not session.target_time:
            return max_kw

        try:
            target = datetime.fromisoformat(session.target_time)
            now = datetime.now(timezone.utc)
            remaining_hours = max(
                0.1,
                (target - now).total_seconds() / 3600.0,
            )

            needed = session.energy_needed_kwh
            required_kw = needed / remaining_hours

            if required_kw > max_kw * 0.9:
                return max_kw  # Must charge now
            elif remaining_hours > session.time_to_full_hours * 2:
                return 0.0  # Can wait
            else:
                return min(max_kw, required_kw)
        except (ValueError, TypeError):
            return max_kw

    def _smart_power(
        self,
        session: EVSession,
        max_kw: float,
        solar_surplus_kw: float,
        grid_price: float,
    ) -> float:
        """Smart charging: prefer solar, avoid expensive grid."""
        # Price threshold for grid charging
        price_threshold = 0.15  # $/kWh

        if solar_surplus_kw > 1.0:
            return min(max_kw, solar_surplus_kw)
        elif grid_price < price_threshold:
            return max_kw * 0.7  # Charge at reduced rate
        elif session.energy_needed_kwh < 5.0:
            return max_kw * 0.3  # Nearly full, slow charge
        else:
            return 0.0  # Wait for cheaper electricity

    def status(self) -> Dict[str, Any]:
        """Get charger fleet status."""
        active = [
            s for s in self._sessions.values() if s.is_active
        ]
        return {
            "chargers": len(self._chargers),
            "active_sessions": len(active),
            "total_energy_kwh": round(self._total_energy_kwh, 2),
            "charger_list": [
                c.to_dict() for c in self._chargers.values()
            ],
        }
