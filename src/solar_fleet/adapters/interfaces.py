"""Unified vendor interface layer for Solar Fleet EMS.

All vendor adapters (cloud and local) expose the same method surface so the
fleet controller, EMS engine, and UI layer can be written once and work across
every brand.  Adapters implement what they support; everything else raises
VendorError with a documented reason code.

Design rationale (adapted from batpred/inverter.py Inverter abstraction):
- ``ReadAdapter`` — telemetry, discovery, history, alarms (cloud or local)
- ``ControlAdapter`` — write path: SOC target, TOU schedule, work mode, etc.
- ``LocalReadAdapter`` — extends ReadAdapter for local Modbus/V5/UDP transports
- ``VendorAdapter`` — combines all three for adapters that support everything

All adapters are async-first; synchronous transports must be wrapped.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from datetime import UTC, datetime
from typing import Any, Protocol, runtime_checkable

from ..domain import Ack, Configuration, Device, OrderResult, Sample, VendorCall


# ---------------------------------------------------------------------------
# Canonical metric names used across every vendor
# ---------------------------------------------------------------------------
# Power (W) — positive = production/export, negative = consumption/import
METRIC_PV_POWER = "pv_power"              # Total PV DC power into inverter
METRIC_ACTIVE_POWER = "active_power"      # Inverter AC output power
METRIC_LOAD_POWER = "load_power"          # On-site load power
METRIC_GRID_POWER = "grid_power"          # Grid power (+export / −import)
METRIC_GRID_EXPORT = "grid_export_power"
METRIC_GRID_IMPORT = "grid_import_power"
METRIC_BATTERY_POWER = "battery_power"   # Battery power (+charge / −discharge)
METRIC_BATTERY_CHARGE = "battery_charge_power"
METRIC_BATTERY_DISCHARGE = "battery_discharge_power"
METRIC_BACKUP_POWER = "backup_power"      # EPS/backup output power

# Voltage (V)
METRIC_PV1_VOLTAGE = "pv1_voltage"
METRIC_PV2_VOLTAGE = "pv2_voltage"
METRIC_PV3_VOLTAGE = "pv3_voltage"
METRIC_PV4_VOLTAGE = "pv4_voltage"
METRIC_GRID_VOLTAGE_R = "grid_voltage_r"
METRIC_GRID_VOLTAGE_S = "grid_voltage_s"
METRIC_GRID_VOLTAGE_T = "grid_voltage_t"
METRIC_BATTERY_VOLTAGE = "battery_voltage"
METRIC_BMS_VOLTAGE = "bms_voltage"

# Current (A)
METRIC_PV1_CURRENT = "pv1_current"
METRIC_PV2_CURRENT = "pv2_current"
METRIC_PV3_CURRENT = "pv3_current"
METRIC_PV4_CURRENT = "pv4_current"
METRIC_GRID_CURRENT_R = "grid_current_r"
METRIC_GRID_CURRENT_S = "grid_current_s"
METRIC_GRID_CURRENT_T = "grid_current_t"
METRIC_BATTERY_CURRENT = "battery_current"
METRIC_BMS_CURRENT = "bms_current"

# Battery / BMS
METRIC_BATTERY_SOC = "battery_soc"       # State of Charge (%)
METRIC_BATTERY_SOH = "battery_soh"       # State of Health (%)
METRIC_BATTERY_TEMP = "battery_temp"     # Temperature (°C)
METRIC_BMS_SOC = "bms_soc"
METRIC_BMS_CYCLE_COUNT = "bms_cycle_count"
METRIC_BMS_MAX_CHARGE_CURRENT = "bms_max_charge_current"
METRIC_CELL_VOLTAGE_MIN = "cell_voltage_min"
METRIC_CELL_VOLTAGE_MAX = "cell_voltage_max"
METRIC_CELL_VOLTAGE_DELTA = "cell_voltage_delta"

# Temperatures (°C)
METRIC_INVERTER_TEMP = "inverter_temp"
METRIC_GRID_TEMP = "grid_temp"

# Frequency (Hz)
METRIC_GRID_FREQUENCY = "grid_frequency"

# Energy (kWh) — cumulative counters, monotonically increasing
METRIC_ENERGY_TODAY = "energy_today"
METRIC_ENERGY_TOTAL = "energy_total"
METRIC_PV_ENERGY_TODAY = "pv_energy_today"
METRIC_PV_ENERGY_TOTAL = "pv_energy_total"
METRIC_EXPORT_TODAY = "export_energy_today"
METRIC_EXPORT_TOTAL = "total_export_energy"
METRIC_IMPORT_TODAY = "import_energy_today"
METRIC_IMPORT_TOTAL = "total_import_energy"
METRIC_BATTERY_CHARGE_TODAY = "battery_charge_today"
METRIC_BATTERY_DISCHARGE_TODAY = "battery_discharge_today"
METRIC_BATTERY_CHARGE_TOTAL = "battery_charge_total"
METRIC_BATTERY_DISCHARGE_TOTAL = "battery_discharge_total"
METRIC_LOAD_TODAY = "load_energy_today"
METRIC_LOAD_TOTAL = "load_energy_total"
METRIC_SELF_CONSUMPTION_TODAY = "self_consumption_today"

# Status (string / enum)
METRIC_INVERTER_STATUS = "inverter_status"   # raw vendor status code
METRIC_WORK_MODE = "work_mode"               # Self-use / TOU / Backup / Feed-in
METRIC_FAULT_CODE = "fault_code"

# EPS / backup
METRIC_EPS_VOLTAGE = "eps_voltage"
METRIC_EPS_FREQUENCY = "eps_frequency"
METRIC_EPS_POWER = "eps_power"

# Power Factor
METRIC_POWER_FACTOR = "power_factor"


# ---------------------------------------------------------------------------
# Work mode constants — vendor-neutral
# ---------------------------------------------------------------------------
class WorkMode:
    """Vendor-neutral work mode constants."""
    SELF_USE = "self_use"           # Self-consumption priority
    FEED_IN = "feed_in"             # Feed excess to grid
    BACKUP = "backup"               # Backup / emergency power
    TIME_OF_USE = "time_of_use"     # TOU schedule-driven
    PEAK_SHAVING = "peak_shaving"   # Demand charge reduction
    IDLE = "idle"                   # Standby
    MANUAL = "manual"               # Direct power setpoint


# ---------------------------------------------------------------------------
# TOU slot — vendor-neutral schedule entry
# ---------------------------------------------------------------------------
class TouSlot:
    """A single time-of-use slot, vendor-neutral.

    Constraints (from batpred/tou_schedule.py — confirmed by Sunsynk docs):
    - Slots must be chronological: start_hm must be strictly increasing
    - Slot 1 must start at "00:00"
    - No slot may span midnight (split required if a window crosses 00:00)
    - A slot runs until the next slot's start_hm

    Args:
        start_hm: "HH:MM" wall-clock start time
        grid_charge: Whether grid charging is enabled in this slot
        force_discharge: Whether forced discharge is enabled
        target_soc: Target SOC at end of this slot (%)
        charge_power_pct: Charge power as % of rated (0–100)
        discharge_power_pct: Discharge power as % of rated (0–100)
    """

    def __init__(
        self,
        start_hm: str,
        *,
        grid_charge: bool = False,
        force_discharge: bool = False,
        target_soc: int = 100,
        charge_power_pct: int = 100,
        discharge_power_pct: int = 100,
    ):
        parts = start_hm.split(":")
        if len(parts) != 2:
            raise ValueError(f"Invalid TOU slot time: {start_hm!r}")
        try:
            h, m = int(parts[0]), int(parts[1])
        except ValueError:
            raise ValueError(f"Invalid TOU slot time: {start_hm!r}")
        if not (0 <= h <= 23 and 0 <= m <= 59):
            raise ValueError(f"TOU slot time out of range: {start_hm!r}")
        if not (0 <= target_soc <= 100):
            raise ValueError(f"TOU target_soc out of range: {target_soc}")
        if not (0 <= charge_power_pct <= 100):
            raise ValueError(f"TOU charge_power_pct out of range: {charge_power_pct}")
        if not (0 <= discharge_power_pct <= 100):
            raise ValueError(f"TOU discharge_power_pct out of range: {discharge_power_pct}")
        self.start_hm = f"{h:02d}:{m:02d}"
        self.start_minutes = h * 60 + m
        self.grid_charge = grid_charge
        self.force_discharge = force_discharge
        self.target_soc = target_soc
        self.charge_power_pct = charge_power_pct
        self.discharge_power_pct = discharge_power_pct

    def __repr__(self) -> str:
        return (
            f"TouSlot({self.start_hm!r}, grid_charge={self.grid_charge}, "
            f"force_discharge={self.force_discharge}, target_soc={self.target_soc})"
        )


# ---------------------------------------------------------------------------
# Telemetry snapshot — normalized across vendors
# ---------------------------------------------------------------------------
class TelemetrySnapshot:
    """Normalized device telemetry snapshot, vendor-neutral.

    ``points`` is a dict of canonical metric name → (value, unit).
    ``raw`` carries the vendor's original response for audit/debugging.
    ``timestamp`` is UTC time of measurement (None if vendor does not provide).
    ``freshness_state`` documents timestamp reliability per vendor evidence.
    """

    def __init__(
        self,
        device_sn: str,
        points: dict[str, tuple[float | str | None, str | None]],
        *,
        timestamp: datetime | None = None,
        freshness_state: str = "UNKNOWN",
        raw: dict | None = None,
        online: bool = True,
    ):
        self.device_sn = device_sn
        self.points = points          # {metric: (value, unit)}
        self.timestamp = timestamp
        self.freshness_state = freshness_state
        self.raw = raw or {}
        self.online = online

    def get(self, metric: str) -> float | str | None:
        """Return the value for a canonical metric, or None."""
        entry = self.points.get(metric)
        return entry[0] if entry else None

    def get_with_unit(self, metric: str) -> tuple[float | str | None, str | None]:
        """Return (value, unit) for a canonical metric."""
        return self.points.get(metric, (None, None))

    def to_samples(self, device_id: str, source) -> list[Sample]:
        """Convert to domain Sample list for storage."""
        samples = []
        for metric, (value, unit) in self.points.items():
            if value is None:
                continue
            try:
                float_val = float(value)
            except (TypeError, ValueError):
                continue
            samples.append(
                Sample(
                    device_id=device_id,
                    metric=metric,
                    value=float_val,
                    unit=unit,
                    source=source,
                )
            )
        return samples


# ---------------------------------------------------------------------------
# Read adapter protocol — all cloud and local read adapters
# ---------------------------------------------------------------------------
@runtime_checkable
class ReadAdapterProtocol(Protocol):
    """Protocol satisfied by all read adapters (cloud and local).

    Implementors raise VendorError for all failure modes.
    """

    evidence_ids: list[str]
    version: str

    async def stations(self) -> list[dict]:
        """Return list of stations/plants accessible by this account."""
        ...

    async def devices(self, station_id: Any) -> list[dict]:
        """Return list of devices for a given station."""
        ...

    async def latest(self, serials: list[str]) -> list[dict]:
        """Return latest telemetry for listed device serials."""
        ...

    async def configuration(self, device: Device) -> Configuration:
        """Return current device configuration (battery, grid, TOU settings)."""
        ...

    async def history(self, *args: Any, **kwargs: Any) -> Any:
        """Return historical data for a device over a time range."""
        ...

    async def alerts(self, *args: Any, **kwargs: Any) -> Any:
        """Return alarms/alerts for a device or station."""
        ...

    async def close(self) -> None:
        """Release any held resources (connections, sockets)."""
        ...


# ---------------------------------------------------------------------------
# Write adapter protocol — all adapters that support control
# ---------------------------------------------------------------------------
@runtime_checkable
class WriteAdapterProtocol(Protocol):
    """Protocol for adapters that support inverter control commands."""

    async def send(self, call: VendorCall, *, before_send=None) -> Ack:
        """Send a control command. Exactly one dispatch; no retries on timeout."""
        ...

    async def order(self, order_id: str) -> OrderResult:
        """Poll the status of a previously dispatched control order."""
        ...


# ---------------------------------------------------------------------------
# Control interface — vendor-neutral inverter control methods
# All concrete adapters should implement as many of these as their API allows.
# Raise VendorError("capability_not_commissioned") for unsupported operations.
# ---------------------------------------------------------------------------
class InverterControlMixin:
    """Mixin that translates vendor-neutral control requests to VendorCall objects.

    Adapters that support write operations should inherit this mixin and
    implement the abstract _build_* methods that translate requests to the
    vendor's native API format.

    Derived from batpred/inverter.py Inverter abstraction.
    """

    async def set_battery_target_soc(self, device: Device, soc: int) -> Ack:
        """Set the battery target SOC (0–100%).

        This is the most universally supported control command.
        """
        if not 0 <= soc <= 100:
            raise ValueError(f"SOC must be 0–100, got {soc}")
        return await self.send(await self._build_set_soc(device, soc))

    async def set_charge_rate(self, device: Device, watts: int) -> Ack:
        """Set the maximum battery charge rate in watts."""
        if watts < 0:
            raise ValueError("Charge rate must be non-negative")
        return await self.send(await self._build_set_charge_rate(device, watts))

    async def set_discharge_rate(self, device: Device, watts: int) -> Ack:
        """Set the maximum battery discharge rate in watts."""
        if watts < 0:
            raise ValueError("Discharge rate must be non-negative")
        return await self.send(await self._build_set_discharge_rate(device, watts))

    async def set_reserve_soc(self, device: Device, soc: int) -> Ack:
        """Set the battery reserve SOC — minimum allowed SOC during normal discharge."""
        if not 0 <= soc <= 100:
            raise ValueError(f"Reserve SOC must be 0–100, got {soc}")
        return await self.send(await self._build_set_reserve(device, soc))

    async def set_work_mode(self, device: Device, mode: str) -> Ack:
        """Set the inverter work mode (self_use, feed_in, backup, time_of_use…)."""
        return await self.send(await self._build_set_work_mode(device, mode))

    async def set_tou_schedule(self, device: Device, slots: list[TouSlot]) -> Ack:
        """Program a Time-of-Use schedule.

        Constraints (validated before dispatch):
        - Slots must be chronological
        - First slot must start at 00:00
        - No slot may span midnight
        """
        self._validate_tou_slots(slots)
        return await self.send(await self._build_set_tou(device, slots))

    async def pause_charge(self, device: Device) -> Ack:
        """Pause battery charging immediately."""
        return await self.send(await self._build_pause_charge(device))

    async def pause_discharge(self, device: Device) -> Ack:
        """Pause battery discharging immediately."""
        return await self.send(await self._build_pause_discharge(device))

    @staticmethod
    def _validate_tou_slots(slots: list[TouSlot]) -> None:
        """Validate TOU slot list before dispatch.

        Rules from batpred/tou_schedule.py (confirmed against Sunsynk firmware docs):
        - Must have at least 1 slot
        - Slots must be sorted chronologically by start_minutes
        - First slot must start at 00:00 (start_minutes == 0)
        - No two slots may share the same start_minutes
        """
        if not slots:
            raise ValueError("TOU schedule must have at least one slot")
        if slots[0].start_minutes != 0:
            raise ValueError(
                f"First TOU slot must start at 00:00, got {slots[0].start_hm!r}"
            )
        prev = -1
        for slot in slots:
            if slot.start_minutes <= prev:
                raise ValueError(
                    f"TOU slots must be chronologically ordered and unique; "
                    f"slot {slot.start_hm!r} conflicts"
                )
            prev = slot.start_minutes

    # ------------------------------------------------------------------
    # Abstract builder methods — each vendor overrides what it supports
    # ------------------------------------------------------------------
    async def _build_set_soc(self, device: Device, soc: int) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_set_charge_rate(self, device: Device, watts: int) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_set_discharge_rate(self, device: Device, watts: int) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_set_reserve(self, device: Device, soc: int) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_set_work_mode(self, device: Device, mode: str) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_set_tou(self, device: Device, slots: list[TouSlot]) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_pause_charge(self, device: Device) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def _build_pause_discharge(self, device: Device) -> VendorCall:
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")


# ---------------------------------------------------------------------------
# Local (Modbus/V5/UDP) adapter protocol
# ---------------------------------------------------------------------------
@runtime_checkable
class LocalReadAdapterProtocol(Protocol):
    """Protocol for local-network adapter transports."""

    transport: str    # "modbus_tcp" | "solarman_v5" | "goodwe_udp" | "eybond_udp"
    address: str      # IPv4 address
    port: int

    async def read_telemetry(self) -> TelemetrySnapshot:
        """Read a full telemetry snapshot synchronously over local network."""
        ...

    async def discover(self) -> list[dict]:
        """Broadcast/probe to discover devices on the local network."""
        ...

    async def close(self) -> None:
        """Release socket / connection."""
        ...


# ---------------------------------------------------------------------------
# Normalize a vendor's raw data-list to canonical TelemetrySnapshot
# ---------------------------------------------------------------------------
def normalize_points(
    native_map: dict[str, dict],
    raw_data: dict[str, Any],
) -> dict[str, tuple[float | str | None, str | None]]:
    """Map vendor-native field names to canonical metrics using a NATIVE_POINTS map.

    ``native_map`` is a dict of ``{native_field: {"metric": canonical, "unit": "W"}}``
    ``raw_data`` is the vendor's flat dict from their API response.

    Returns ``{canonical_metric: (value, unit)}``.
    """
    result: dict[str, tuple[float | str | None, str | None]] = {}
    for native_key, cfg in native_map.items():
        if native_key not in raw_data:
            continue
        raw_val = raw_data[native_key]
        canonical = cfg.get("metric")
        unit = cfg.get("unit")
        if not canonical:
            continue
        if isinstance(raw_val, (int, float)) and not isinstance(raw_val, bool):
            scale = cfg.get("scale", 1.0)
            value: float | str | None = float(raw_val) * scale
        elif isinstance(raw_val, str):
            try:
                value = float(raw_val) * cfg.get("scale", 1.0)
            except (ValueError, TypeError):
                value = raw_val
        else:
            value = None
        result[canonical] = (value, unit)
    return result


# ---------------------------------------------------------------------------
# Capability query helpers (for UI / API)
# ---------------------------------------------------------------------------
def adapter_capabilities(adapter: Any) -> set[str]:
    """Return a set of capability strings for an adapter instance.

    Capability strings: "cloud_read", "local_read", "control_soc",
    "control_rate", "control_tou", "control_mode", "history", "alarms"
    """
    caps: set[str] = set()
    if isinstance(adapter, ReadAdapterProtocol):
        caps.add("cloud_read")
    if isinstance(adapter, LocalReadAdapterProtocol):
        caps.add("local_read")
    if isinstance(adapter, WriteAdapterProtocol):
        caps.add("write")
    if isinstance(adapter, InverterControlMixin):
        caps.add("control_interface")
    return caps


# ---------------------------------------------------------------------------
# Unified Inverter Adapter Layer (High-Level Interface Facade)
# ---------------------------------------------------------------------------
class UnifiedInverterAdapter(ABC):
    """Unified interface unifying all inverter brands and transport mechanisms (Cloud & Local).

    This provides a single, uniform method surface for the Fleet EMS controller,
    EMS optimization engine, and API/UI layers regardless of whether the inverter
    is connected via Cloud API, direct Modbus TCP, SOLARMAN V5 logger, Eybond, or GoodWe UDP.
    """

    def __init__(
        self,
        device_id: str,
        vendor: str,
        model: str = "",
        transport_type: str = "unknown",
        site_id: str = "",
    ):
        self.device_id = device_id
        self.vendor = vendor.lower()
        self.model = model
        self.transport_type = transport_type
        self.site_id = site_id

    @abstractmethod
    async def get_telemetry(self) -> TelemetrySnapshot:
        """Fetch latest standardized telemetry snapshot."""
        ...

    @abstractmethod
    async def get_device_info(self) -> dict[str, Any]:
        """Fetch device identity, model, firmware, serial number, and status."""
        ...

    async def get_work_mode(self) -> str | None:
        """Get current inverter work mode (WorkMode enum value), or None if unsupported."""
        telemetry = await self.get_telemetry()
        val = telemetry.get(METRIC_WORK_MODE)
        return str(val) if val is not None else None

    async def set_work_mode(self, mode: str) -> Ack:
        """Set inverter work mode (WorkMode.SELF_USE, FEED_IN, BACKUP, TIME_OF_USE, etc.)."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def set_battery_target_soc(self, soc: int) -> Ack:
        """Set battery target SOC (0-100%)."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def set_reserve_soc(self, soc: int) -> Ack:
        """Set battery reserve / backup SOC (0-100%)."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def set_charge_rate(self, watts: int) -> Ack:
        """Set maximum battery charge rate in Watts."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def set_discharge_rate(self, watts: int) -> Ack:
        """Set maximum battery discharge rate in Watts."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def get_tou_schedule(self) -> list[TouSlot] | None:
        """Get current Time-of-Use schedule, or None if unsupported."""
        return None

    async def set_tou_schedule(self, slots: list[TouSlot]) -> Ack:
        """Set Time-of-Use schedule."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def pause_charge(self) -> Ack:
        """Emergency pause battery charging."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    async def pause_discharge(self) -> Ack:
        """Emergency pause battery discharging."""
        from ..domain import VendorError
        raise VendorError("capability_not_commissioned")

    def capabilities(self) -> set[str]:
        """Return supported capability tags."""
        return {"unified_adapter"}

    async def close(self) -> None:
        """Release underlying connections or sockets."""
        pass


class UnifiedLocalAdapter(UnifiedInverterAdapter):
    """Unified wrapper around local hardware adapters (Modbus TCP, UDP, V5)."""

    def __init__(
        self,
        inner: Any,
        device_id: str,
        vendor: str,
        model: str = "",
        site_id: str = "",
        device_entity: Device | None = None,
    ):
        transport = getattr(inner, "transport", "local")
        super().__init__(
            device_id=device_id,
            vendor=vendor,
            model=model,
            transport_type=f"local_{transport}",
            site_id=site_id,
        )
        self.inner = inner
        self.device_entity = device_entity

    async def get_telemetry(self) -> TelemetrySnapshot:
        if hasattr(self.inner, "read_telemetry"):
            return await self.inner.read_telemetry()
        from ..domain import VendorError
        raise VendorError("local_read_unsupported")

    async def get_device_info(self) -> dict[str, Any]:
        info: dict[str, Any] = {
            "device_id": self.device_id,
            "vendor": self.vendor,
            "model": self.model,
            "transport": self.transport_type,
            "site_id": self.site_id,
        }
        if hasattr(self.inner, "address"):
            info["address"] = self.inner.address
        if hasattr(self.inner, "port"):
            info["port"] = self.inner.port
        return info

    def _get_device_obj(self) -> Device:
        if self.device_entity:
            return self.device_entity
        from ..domain import DeviceIdentity
        return Device(
            id=self.device_id,
            site_id=self.site_id or "default",
            integration_id=f"local-{self.vendor}",
            vendor_id=self.vendor,
            type="inverter",
            identity=DeviceIdentity(vendor=self.vendor, model=self.model or "Generic"),
            name=f"{self.vendor.capitalize()} {self.model}".strip(),
        )

    async def set_battery_target_soc(self, soc: int) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_battery_target_soc(self._get_device_obj(), soc)
        return await super().set_battery_target_soc(soc)

    async def set_reserve_soc(self, soc: int) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_reserve_soc(self._get_device_obj(), soc)
        return await super().set_reserve_soc(soc)

    async def set_charge_rate(self, watts: int) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_charge_rate(self._get_device_obj(), watts)
        return await super().set_charge_rate(watts)

    async def set_discharge_rate(self, watts: int) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_discharge_rate(self._get_device_obj(), watts)
        return await super().set_discharge_rate(watts)

    async def set_work_mode(self, mode: str) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_work_mode(self._get_device_obj(), mode)
        return await super().set_work_mode(mode)

    async def set_tou_schedule(self, slots: list[TouSlot]) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_tou_schedule(self._get_device_obj(), slots)
        return await super().set_tou_schedule(slots)

    async def pause_charge(self) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.pause_charge(self._get_device_obj())
        return await super().pause_charge()

    async def pause_discharge(self) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.pause_discharge(self._get_device_obj())
        return await super().pause_discharge()

    def capabilities(self) -> set[str]:
        caps = adapter_capabilities(self.inner)
        caps.add("unified_adapter")
        caps.add("local")
        return caps

    async def close(self) -> None:
        if hasattr(self.inner, "close"):
            await self.inner.close()


class UnifiedCloudAdapter(UnifiedInverterAdapter):
    """Unified wrapper around vendor Cloud adapters (Solis, Deye, Growatt, etc.)."""

    def __init__(
        self,
        inner: Any,
        device_id: str,
        serial: str,
        vendor: str,
        model: str = "",
        site_id: str = "",
        station_id: Any = None,
        device_entity: Device | None = None,
    ):
        super().__init__(
            device_id=device_id,
            vendor=vendor,
            model=model,
            transport_type="cloud",
            site_id=site_id,
        )
        self.inner = inner
        self.serial = serial
        self.station_id = station_id
        self.device_entity = device_entity

    async def get_telemetry(self) -> TelemetrySnapshot:
        from ..domain import VendorError
        if not hasattr(self.inner, "latest"):
            raise VendorError("cloud_latest_unsupported")

        results = await self.inner.latest([self.serial])
        if not results:
            return TelemetrySnapshot(
                device_sn=self.serial,
                points={},
                timestamp=datetime.now(UTC),
                freshness_state="UNKNOWN",
                online=False,
            )

        row = results[0]
        # In cloud adapters, points are stored under "points" or flattened in row
        raw_points = row.get("points") if isinstance(row, dict) and "points" in row else row
        points: dict[str, tuple[float | str | None, str | None]] = {}

        if isinstance(raw_points, dict):
            for k, v in raw_points.items():
                if isinstance(v, tuple) and len(v) == 2:
                    points[k] = v
                else:
                    points[k] = (v, None)

        return TelemetrySnapshot(
            device_sn=self.serial,
            points=points,
            timestamp=datetime.now(UTC),
            freshness_state="MEASURED",
            raw=row if isinstance(row, dict) else {},
            online=True,
        )

    async def get_device_info(self) -> dict[str, Any]:
        return {
            "device_id": self.device_id,
            "serial": self.serial,
            "vendor": self.vendor,
            "model": self.model,
            "transport": "cloud",
            "site_id": self.site_id,
            "station_id": self.station_id,
        }

    def _get_device_obj(self) -> Device:
        if self.device_entity:
            return self.device_entity
        from ..domain import DeviceIdentity
        return Device(
            id=self.device_id,
            site_id=self.site_id or "default",
            integration_id=f"cloud-{self.vendor}",
            vendor_id=self.vendor,
            type="inverter",
            identity=DeviceIdentity(vendor=self.vendor, model=self.model or "Generic"),
            name=f"{self.vendor.capitalize()} {self.model}".strip(),
        )

    async def set_battery_target_soc(self, soc: int) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_battery_target_soc(self._get_device_obj(), soc)
        return await super().set_battery_target_soc(soc)

    async def set_reserve_soc(self, soc: int) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_reserve_soc(self._get_device_obj(), soc)
        return await super().set_reserve_soc(soc)

    async def set_work_mode(self, mode: str) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_work_mode(self._get_device_obj(), mode)
        return await super().set_work_mode(mode)

    async def set_tou_schedule(self, slots: list[TouSlot]) -> Ack:
        if isinstance(self.inner, InverterControlMixin):
            return await self.inner.set_tou_schedule(self._get_device_obj(), slots)
        return await super().set_tou_schedule(slots)

    def capabilities(self) -> set[str]:
        caps = adapter_capabilities(self.inner)
        caps.add("unified_adapter")
        caps.add("cloud")
        return caps

    async def close(self) -> None:
        if hasattr(self.inner, "close"):
            await self.inner.close()


def create_unified_adapter(
    adapter_instance: Any,
    device_id: str,
    vendor: str,
    model: str = "",
    serial: str = "",
    site_id: str = "",
    device_entity: Device | None = None,
) -> UnifiedInverterAdapter:
    """Factory creating a UnifiedInverterAdapter around any underlying adapter instance.

    Auto-detects whether the adapter is a local poller or a cloud client.
    """
    if isinstance(adapter_instance, (LocalReadAdapterProtocol, InverterControlMixin)) or hasattr(adapter_instance, "read_telemetry"):
        return UnifiedLocalAdapter(
            inner=adapter_instance,
            device_id=device_id,
            vendor=vendor,
            model=model,
            site_id=site_id,
            device_entity=device_entity,
        )
    return UnifiedCloudAdapter(
        inner=adapter_instance,
        device_id=device_id,
        serial=serial or device_id,
        vendor=vendor,
        model=model,
        site_id=site_id,
        device_entity=device_entity,
    )
