"""Component scheduler — OpenEMS-inspired edge controller.

Independently implemented for Solar Fleet EMS.
Architecture concepts informed by openems-develop (AGPL)
io.openems.edge.core — no code copied.

Implements a component-based scheduler that orchestrates
multiple energy system components (inverters, batteries,
meters, controllers) in a deterministic execution cycle.
"""

from __future__ import annotations

import logging
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


class ComponentState(str, Enum):
    """Component lifecycle state."""

    INACTIVE = "inactive"
    STARTING = "starting"
    ACTIVE = "active"
    STOPPING = "stopping"
    FAULTED = "faulted"


class ChannelAccess(str, Enum):
    """Channel access level."""

    READ_ONLY = "ro"
    READ_WRITE = "rw"
    WRITE_ONLY = "wo"


@dataclass
class Channel:
    """A data channel on a component."""

    name: str
    component_id: str
    value: Any = None
    unit: str = ""
    access: ChannelAccess = ChannelAccess.READ_ONLY
    description: str = ""
    _history: List[Any] = field(default_factory=list)

    def set_value(self, value: Any) -> None:
        """Set channel value and record history."""
        self._history.append(self.value)
        if len(self._history) > 1000:
            self._history = self._history[-500:]
        self.value = value

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "component_id": self.component_id,
            "value": self.value,
            "unit": self.unit,
            "access": self.access.value,
        }


class Component(ABC):
    """Abstract base for all EMS components."""

    def __init__(
        self,
        component_id: str,
        component_type: str = "generic",
    ) -> None:
        self.component_id = component_id
        self.component_type = component_type
        self.state = ComponentState.INACTIVE
        self._channels: Dict[str, Channel] = {}
        self._enabled = True

    def add_channel(self, channel: Channel) -> None:
        self._channels[channel.name] = channel

    def get_channel(self, name: str) -> Optional[Channel]:
        return self._channels.get(name)

    def set_channel_value(self, name: str, value: Any) -> None:
        ch = self._channels.get(name)
        if ch and ch.access != ChannelAccess.READ_ONLY:
            ch.set_value(value)

    @abstractmethod
    def activate(self) -> None:
        """Initialize the component."""

    @abstractmethod
    def execute(self) -> None:
        """Execute one cycle of the component."""

    @abstractmethod
    def deactivate(self) -> None:
        """Shut down the component."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "component_id": self.component_id,
            "component_type": self.component_type,
            "state": self.state.value,
            "enabled": self._enabled,
            "channels": {
                n: c.to_dict() for n, c in self._channels.items()
            },
        }


# ---------------------------------------------------------------------------
# Concrete components
# ---------------------------------------------------------------------------

class MeterComponent(Component):
    """Grid meter component — reads grid power."""

    def __init__(self, component_id: str) -> None:
        super().__init__(component_id, "meter")
        self.add_channel(Channel(
            "active_power", component_id,
            unit="W", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "reactive_power", component_id,
            unit="var", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "voltage_l1", component_id,
            unit="V", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "frequency", component_id,
            unit="Hz", access=ChannelAccess.READ_ONLY,
        ))

    def activate(self) -> None:
        self.state = ComponentState.ACTIVE

    def execute(self) -> None:
        """Read meter values (simulation placeholder)."""
        pass

    def deactivate(self) -> None:
        self.state = ComponentState.INACTIVE


class BatteryComponent(Component):
    """Battery storage component."""

    def __init__(
        self,
        component_id: str,
        capacity_kwh: float = 10.0,
        max_charge_w: int = 5000,
        max_discharge_w: int = 5000,
    ) -> None:
        super().__init__(component_id, "battery")
        self.capacity_kwh = capacity_kwh
        self.max_charge_w = max_charge_w
        self.max_discharge_w = max_discharge_w

        self.add_channel(Channel(
            "soc", component_id,
            unit="%", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "active_power", component_id,
            unit="W", access=ChannelAccess.READ_WRITE,
        ))
        self.add_channel(Channel(
            "voltage", component_id,
            unit="V", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "temperature", component_id,
            unit="°C", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "setpoint_power", component_id,
            unit="W", access=ChannelAccess.READ_WRITE,
        ))

    def activate(self) -> None:
        self.state = ComponentState.ACTIVE
        self._channels["soc"].set_value(50.0)

    def execute(self) -> None:
        """Execute battery logic (apply setpoint)."""
        setpoint = self._channels["setpoint_power"].value
        if setpoint is not None:
            clamped = max(
                -self.max_discharge_w,
                min(self.max_charge_w, setpoint),
            )
            self._channels["active_power"].set_value(clamped)

    def deactivate(self) -> None:
        self._channels["active_power"].set_value(0)
        self.state = ComponentState.INACTIVE


class InverterComponent(Component):
    """PV inverter component."""

    def __init__(
        self,
        component_id: str,
        rated_power_w: int = 10000,
    ) -> None:
        super().__init__(component_id, "inverter")
        self.rated_power_w = rated_power_w

        self.add_channel(Channel(
            "active_power", component_id,
            unit="W", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "dc_power", component_id,
            unit="W", access=ChannelAccess.READ_ONLY,
        ))
        self.add_channel(Channel(
            "power_limit_pct", component_id,
            unit="%", access=ChannelAccess.READ_WRITE,
            value=100,
        ))

    def activate(self) -> None:
        self.state = ComponentState.ACTIVE

    def execute(self) -> None:
        """Apply power limit."""
        limit = self._channels["power_limit_pct"].value or 100
        dc = self._channels["dc_power"].value or 0
        limited = dc * min(100, max(0, limit)) / 100
        self._channels["active_power"].set_value(limited)

    def deactivate(self) -> None:
        self.state = ComponentState.INACTIVE


# ---------------------------------------------------------------------------
# Controller components
# ---------------------------------------------------------------------------

class SelfConsumptionController(Component):
    """Controller that optimizes self-consumption.

    Reads meter and PV, sets battery setpoint to absorb surplus
    or discharge to cover deficit.
    """

    def __init__(
        self,
        component_id: str,
        meter_id: str,
        battery_id: str,
    ) -> None:
        super().__init__(component_id, "controller")
        self.meter_id = meter_id
        self.battery_id = battery_id
        self._scheduler: Optional[ComponentScheduler] = None

    def bind_scheduler(self, scheduler: ComponentScheduler) -> None:
        self._scheduler = scheduler

    def activate(self) -> None:
        self.state = ComponentState.ACTIVE

    def execute(self) -> None:
        """Read grid power and set battery accordingly."""
        if self._scheduler is None:
            return

        meter = self._scheduler.get_component(self.meter_id)
        battery = self._scheduler.get_component(self.battery_id)
        if meter is None or battery is None:
            return

        grid_power = meter.get_channel("active_power")
        bat_setpoint = battery.get_channel("setpoint_power")

        if grid_power is None or bat_setpoint is None:
            return

        grid_w = grid_power.value or 0

        # Positive grid power = importing → discharge battery
        # Negative grid power = exporting → charge battery
        if grid_w > 0:
            # Import — try to discharge
            setpoint = -min(
                grid_w,
                battery.max_discharge_w
                if hasattr(battery, "max_discharge_w") else 5000,
            )
        else:
            # Export — try to charge
            setpoint = min(
                abs(grid_w),
                battery.max_charge_w
                if hasattr(battery, "max_charge_w") else 5000,
            )

        bat_setpoint.set_value(setpoint)

    def deactivate(self) -> None:
        self.state = ComponentState.INACTIVE


# ---------------------------------------------------------------------------
# Scheduler
# ---------------------------------------------------------------------------

class ComponentScheduler:
    """Component scheduler — orchestrates EMS components.

    Executes all registered components in a deterministic order
    within each cycle. Controllers run after sensors/actuators.
    """

    EXECUTION_ORDER = [
        "meter",
        "inverter",
        "battery",
        "controller",
    ]

    def __init__(self, cycle_time_ms: int = 1000) -> None:
        self.cycle_time_ms = cycle_time_ms
        self._components: Dict[str, Component] = {}
        self._cycle_count: int = 0
        self._total_cycle_time_ms: float = 0.0
        self._max_cycle_time_ms: float = 0.0
        self._is_running = False

    def register(self, component: Component) -> None:
        """Register a component with the scheduler."""
        self._components[component.component_id] = component
        if hasattr(component, "bind_scheduler"):
            component.bind_scheduler(self)

    def get_component(self, component_id: str) -> Optional[Component]:
        return self._components.get(component_id)

    def start(self) -> None:
        """Start all components."""
        self._is_running = True
        for comp in self._ordered_components():
            try:
                comp.activate()
                logger.info(
                    "Started component: %s", comp.component_id,
                )
            except Exception as e:
                comp.state = ComponentState.FAULTED
                logger.error(
                    "Failed to start %s: %s", comp.component_id, e,
                )

    def stop(self) -> None:
        """Stop all components."""
        self._is_running = False
        for comp in reversed(self._ordered_components()):
            try:
                comp.deactivate()
            except Exception as e:
                logger.error(
                    "Failed to stop %s: %s", comp.component_id, e,
                )

    def execute_cycle(self) -> Dict[str, Any]:
        """Execute one scheduler cycle.

        Runs all active components in order.
        """
        start = time.monotonic()

        for comp in self._ordered_components():
            if comp.state != ComponentState.ACTIVE:
                continue
            if not comp._enabled:
                continue
            try:
                comp.execute()
            except Exception as e:
                comp.state = ComponentState.FAULTED
                logger.error(
                    "Component %s faulted: %s", comp.component_id, e,
                )

        elapsed_ms = (time.monotonic() - start) * 1000
        self._cycle_count += 1
        self._total_cycle_time_ms += elapsed_ms
        self._max_cycle_time_ms = max(
            self._max_cycle_time_ms, elapsed_ms,
        )

        return {
            "cycle": self._cycle_count,
            "elapsed_ms": round(elapsed_ms, 3),
            "components_active": sum(
                1 for c in self._components.values()
                if c.state == ComponentState.ACTIVE
            ),
        }

    def _ordered_components(self) -> List[Component]:
        """Return components in execution order."""
        buckets: Dict[str, List[Component]] = {
            t: [] for t in self.EXECUTION_ORDER
        }
        other: List[Component] = []

        for comp in self._components.values():
            if comp.component_type in buckets:
                buckets[comp.component_type].append(comp)
            else:
                other.append(comp)

        result: List[Component] = []
        for t in self.EXECUTION_ORDER:
            result.extend(buckets[t])
        result.extend(other)
        return result

    def status(self) -> Dict[str, Any]:
        """Get scheduler status."""
        avg_ms = (
            self._total_cycle_time_ms / self._cycle_count
            if self._cycle_count > 0 else 0
        )
        return {
            "is_running": self._is_running,
            "cycle_count": self._cycle_count,
            "cycle_time_ms": self.cycle_time_ms,
            "avg_cycle_time_ms": round(avg_ms, 3),
            "max_cycle_time_ms": round(self._max_cycle_time_ms, 3),
            "components": {
                cid: c.to_dict()
                for cid, c in self._components.items()
            },
        }
