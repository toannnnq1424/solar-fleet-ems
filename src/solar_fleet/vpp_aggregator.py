"""Virtual Power Plant aggregator — fleet-level energy coordination.

Independently implemented for Solar Fleet EMS.
Concepts informed by virtual-power-plant-main (MIT license)
aggregator.py and fleet_dispatch.py — no code copied.

Aggregates distributed energy resources (DERs) across multiple sites
into a virtual portfolio that can participate in energy markets and
provide grid services (frequency regulation, demand response, etc.).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class DERType(str, Enum):
    """Distributed Energy Resource type."""

    SOLAR_PV = "solar_pv"
    BATTERY = "battery"
    EV_CHARGER = "ev_charger"
    LOAD = "load"
    GENERATOR = "generator"
    WIND = "wind"


class GridService(str, Enum):
    """Grid services a VPP can provide."""

    ENERGY_ARBITRAGE = "energy_arbitrage"
    FREQUENCY_REG = "frequency_regulation"
    DEMAND_RESPONSE = "demand_response"
    PEAK_SHAVING = "peak_shaving"
    VOLTAGE_SUPPORT = "voltage_support"
    SPINNING_RESERVE = "spinning_reserve"
    CAPACITY = "capacity"


class VPPState(str, Enum):
    """VPP operating state."""

    IDLE = "idle"
    DISPATCHING = "dispatching"
    DR_EVENT = "dr_event"
    CURTAILING = "curtailing"
    EMERGENCY = "emergency"


@dataclass
class DERAsset:
    """A distributed energy resource within the VPP."""

    asset_id: str
    site_id: str
    der_type: DERType
    rated_power_kw: float
    current_power_kw: float = 0.0
    # Battery-specific
    capacity_kwh: float = 0.0
    soc: float = 0.5
    soc_min: float = 0.05
    soc_max: float = 0.95
    # Availability
    is_available: bool = True
    is_controllable: bool = True
    # Flexibility
    flex_up_kw: float = 0.0
    flex_down_kw: float = 0.0
    ramp_rate_kw_per_min: float = 100.0
    # Cost
    marginal_cost: float = 0.0

    @property
    def available_charge_kw(self) -> float:
        """Available charge power (positive for batteries)."""
        if self.der_type != DERType.BATTERY:
            return 0.0
        if not self.is_available or self.soc >= self.soc_max:
            return 0.0
        return self.rated_power_kw

    @property
    def available_discharge_kw(self) -> float:
        """Available discharge power (positive for batteries)."""
        if self.der_type != DERType.BATTERY:
            return 0.0
        if not self.is_available or self.soc <= self.soc_min:
            return 0.0
        return self.rated_power_kw

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "site_id": self.site_id,
            "der_type": self.der_type.value,
            "rated_power_kw": self.rated_power_kw,
            "current_power_kw": round(self.current_power_kw, 2),
            "soc": round(self.soc, 4) if self.capacity_kwh else None,
            "is_available": self.is_available,
            "flex_up_kw": round(self.flex_up_kw, 2),
            "flex_down_kw": round(self.flex_down_kw, 2),
        }


@dataclass
class DispatchCommand:
    """Dispatch command for a DER asset."""

    asset_id: str
    target_power_kw: float
    duration_minutes: float = 15.0
    priority: int = 5
    service: GridService = GridService.ENERGY_ARBITRAGE
    timestamp: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "asset_id": self.asset_id,
            "target_power_kw": round(self.target_power_kw, 2),
            "duration_minutes": self.duration_minutes,
            "priority": self.priority,
            "service": self.service.value,
            "timestamp": self.timestamp,
        }


@dataclass
class VPPPortfolio:
    """Summary of VPP portfolio capabilities."""

    total_rated_kw: float
    total_generation_kw: float
    total_load_kw: float
    total_battery_kwh: float
    total_flex_up_kw: float
    total_flex_down_kw: float
    asset_count: int
    site_count: int
    available_services: List[str]

    def to_dict(self) -> dict[str, Any]:
        return {
            "total_rated_kw": round(self.total_rated_kw, 1),
            "total_generation_kw": round(self.total_generation_kw, 2),
            "total_load_kw": round(self.total_load_kw, 2),
            "total_battery_kwh": round(self.total_battery_kwh, 1),
            "total_flex_up_kw": round(self.total_flex_up_kw, 2),
            "total_flex_down_kw": round(self.total_flex_down_kw, 2),
            "asset_count": self.asset_count,
            "site_count": self.site_count,
            "available_services": self.available_services,
        }


# ---------------------------------------------------------------------------
# VPP Aggregator
# ---------------------------------------------------------------------------

class VPPAggregator:
    """Virtual Power Plant aggregator.

    Manages a portfolio of distributed energy resources across
    multiple sites and dispatches them to provide grid services.
    """

    def __init__(
        self,
        vpp_id: str = "vpp-1",
        name: str = "Solar Fleet VPP",
    ) -> None:
        self.vpp_id = vpp_id
        self.name = name
        self.state = VPPState.IDLE
        self._assets: Dict[str, DERAsset] = {}
        self._dispatch_history: List[Dict[str, Any]] = []
        self._dr_events: List[Dict[str, Any]] = []

    def register_asset(self, asset: DERAsset) -> None:
        """Register a DER asset."""
        self._assets[asset.asset_id] = asset
        self._update_flexibility(asset)
        logger.info("Registered DER: %s (%s)", asset.asset_id, asset.der_type)

    def remove_asset(self, asset_id: str) -> Optional[DERAsset]:
        """Remove a DER asset."""
        return self._assets.pop(asset_id, None)

    def update_telemetry(
        self,
        asset_id: str,
        power_kw: float,
        soc: Optional[float] = None,
    ) -> None:
        """Update real-time telemetry for an asset."""
        asset = self._assets.get(asset_id)
        if asset is None:
            return
        asset.current_power_kw = power_kw
        if soc is not None:
            asset.soc = soc
        self._update_flexibility(asset)

    def _update_flexibility(self, asset: DERAsset) -> None:
        """Recalculate flexibility for an asset."""
        if not asset.is_available or not asset.is_controllable:
            asset.flex_up_kw = 0.0
            asset.flex_down_kw = 0.0
            return

        if asset.der_type == DERType.BATTERY:
            asset.flex_up_kw = asset.available_discharge_kw
            asset.flex_down_kw = asset.available_charge_kw
        elif asset.der_type == DERType.SOLAR_PV:
            asset.flex_up_kw = 0.0  # Can't increase solar
            asset.flex_down_kw = max(0, asset.current_power_kw)
        elif asset.der_type == DERType.LOAD:
            asset.flex_up_kw = 0.0
            asset.flex_down_kw = max(0, asset.current_power_kw)
        elif asset.der_type == DERType.EV_CHARGER:
            asset.flex_up_kw = 0.0
            asset.flex_down_kw = max(0, asset.current_power_kw)

    # -----------------------------------------------------------------------
    # Portfolio queries
    # -----------------------------------------------------------------------

    def portfolio(self) -> VPPPortfolio:
        """Get current portfolio summary."""
        total_rated = sum(a.rated_power_kw for a in self._assets.values())
        total_gen = sum(
            a.current_power_kw for a in self._assets.values()
            if a.der_type in (DERType.SOLAR_PV, DERType.WIND, DERType.GENERATOR)
        )
        total_load = sum(
            abs(a.current_power_kw) for a in self._assets.values()
            if a.der_type in (DERType.LOAD, DERType.EV_CHARGER)
        )
        total_bat = sum(
            a.capacity_kwh for a in self._assets.values()
            if a.der_type == DERType.BATTERY
        )
        total_up = sum(a.flex_up_kw for a in self._assets.values())
        total_down = sum(a.flex_down_kw for a in self._assets.values())
        sites = set(a.site_id for a in self._assets.values())

        services = self._available_services()

        return VPPPortfolio(
            total_rated_kw=total_rated,
            total_generation_kw=total_gen,
            total_load_kw=total_load,
            total_battery_kwh=total_bat,
            total_flex_up_kw=total_up,
            total_flex_down_kw=total_down,
            asset_count=len(self._assets),
            site_count=len(sites),
            available_services=services,
        )

    def _available_services(self) -> List[str]:
        """Determine services based on portfolio composition."""
        services = []
        has_battery = any(
            a.der_type == DERType.BATTERY for a in self._assets.values()
        )
        has_solar = any(
            a.der_type == DERType.SOLAR_PV for a in self._assets.values()
        )
        has_load = any(
            a.der_type in (DERType.LOAD, DERType.EV_CHARGER)
            for a in self._assets.values()
        )

        if has_battery:
            services.extend([
                GridService.ENERGY_ARBITRAGE.value,
                GridService.FREQUENCY_REG.value,
                GridService.PEAK_SHAVING.value,
                GridService.SPINNING_RESERVE.value,
            ])
        if has_solar:
            services.append(GridService.CAPACITY.value)
        if has_load or has_battery:
            services.append(GridService.DEMAND_RESPONSE.value)
        if has_battery:
            services.append(GridService.VOLTAGE_SUPPORT.value)

        return services

    # -----------------------------------------------------------------------
    # Dispatch
    # -----------------------------------------------------------------------

    def dispatch(
        self,
        target_power_kw: float,
        service: GridService = GridService.ENERGY_ARBITRAGE,
        duration_min: float = 15.0,
    ) -> List[DispatchCommand]:
        """Dispatch DER fleet to meet target power.

        Positive target = export/discharge to grid.
        Negative target = import/charge from grid.

        Uses merit-order dispatch (cheapest first).
        """
        self.state = VPPState.DISPATCHING
        commands: List[DispatchCommand] = []
        remaining = target_power_kw

        # Sort assets by marginal cost
        assets = sorted(
            [a for a in self._assets.values()
             if a.is_available and a.is_controllable],
            key=lambda a: a.marginal_cost,
        )

        ts = datetime.now(timezone.utc).isoformat()

        if target_power_kw >= 0:
            # Need to discharge / export
            for asset in assets:
                if remaining <= 0:
                    break
                avail = asset.flex_up_kw
                if avail <= 0:
                    continue
                dispatch_kw = min(remaining, avail)
                cmd = DispatchCommand(
                    asset_id=asset.asset_id,
                    target_power_kw=dispatch_kw,
                    duration_minutes=duration_min,
                    service=service,
                    timestamp=ts,
                )
                commands.append(cmd)
                remaining -= dispatch_kw
        else:
            # Need to charge / absorb
            for asset in assets:
                if remaining >= 0:
                    break
                avail = asset.flex_down_kw
                if avail <= 0:
                    continue
                dispatch_kw = min(abs(remaining), avail)
                cmd = DispatchCommand(
                    asset_id=asset.asset_id,
                    target_power_kw=-dispatch_kw,
                    duration_minutes=duration_min,
                    service=service,
                    timestamp=ts,
                )
                commands.append(cmd)
                remaining += dispatch_kw

        self._dispatch_history.append({
            "timestamp": ts,
            "target_kw": target_power_kw,
            "dispatched_kw": target_power_kw - remaining,
            "shortfall_kw": remaining,
            "commands": len(commands),
            "service": service.value,
        })

        self.state = VPPState.IDLE
        return commands

    # -----------------------------------------------------------------------
    # Demand Response
    # -----------------------------------------------------------------------

    def trigger_dr_event(
        self,
        reduction_kw: float,
        duration_min: float = 60.0,
        event_type: str = "economic",
    ) -> Dict[str, Any]:
        """Trigger a demand response event.

        Sheds loads and discharges batteries to reduce grid import.
        """
        self.state = VPPState.DR_EVENT
        commands = self.dispatch(
            reduction_kw,
            service=GridService.DEMAND_RESPONSE,
            duration_min=duration_min,
        )

        achieved = sum(
            abs(c.target_power_kw) for c in commands
        )

        event = {
            "event_type": event_type,
            "requested_kw": reduction_kw,
            "achieved_kw": round(achieved, 2),
            "compliance_pct": round(
                min(100, achieved / reduction_kw * 100)
                if reduction_kw > 0 else 100, 1,
            ),
            "duration_min": duration_min,
            "commands": [c.to_dict() for c in commands],
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._dr_events.append(event)

        self.state = VPPState.IDLE
        return event

    # -----------------------------------------------------------------------
    # Peak shaving
    # -----------------------------------------------------------------------

    def peak_shave(
        self,
        current_import_kw: float,
        limit_kw: float,
    ) -> List[DispatchCommand]:
        """Dispatch batteries to keep grid import below limit."""
        excess = current_import_kw - limit_kw
        if excess <= 0:
            return []
        return self.dispatch(
            excess,
            service=GridService.PEAK_SHAVING,
        )

    # -----------------------------------------------------------------------
    # Status
    # -----------------------------------------------------------------------

    def status(self) -> Dict[str, Any]:
        """Get VPP aggregator status."""
        portfolio = self.portfolio()
        return {
            "vpp_id": self.vpp_id,
            "name": self.name,
            "state": self.state.value,
            "portfolio": portfolio.to_dict(),
            "dispatch_count": len(self._dispatch_history),
            "dr_events_count": len(self._dr_events),
            "assets": [
                a.to_dict() for a in self._assets.values()
            ],
        }
