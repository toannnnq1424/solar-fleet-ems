"""Vendor adapters — cloud and local.

All adapters satisfy the interfaces defined in .interfaces.

Cloud adapters (ReadAdapterProtocol):
    Deye, Solis, Solarman, Growatt, Sungrow, Huawei, GoodWe

Local adapters (LocalReadAdapterProtocol):
    EybondLocalAdapter, GoodWeLocalAdapter, ModbusTcpPoller, SolarmanV5Poller

Daemon:
    LocalAgentDaemon, LocalDeviceConfig

Unified interface and helpers:
    ReadAdapterProtocol, WriteAdapterProtocol, LocalReadAdapterProtocol
    InverterControlMixin, TelemetrySnapshot, TouSlot, WorkMode
    normalize_points, adapter_capabilities
    METRIC_* constants

TOU:
    TouSlotProgramme, build_tou_programme, encode_deye_tou, encode_sunsynk_tou
    simple_offpeak_programme
"""

from .interfaces import (
    ReadAdapterProtocol,
    WriteAdapterProtocol,
    LocalReadAdapterProtocol,
    InverterControlMixin,
    TelemetrySnapshot,
    TouSlot,
    WorkMode,
    normalize_points,
    adapter_capabilities,
    UnifiedInverterAdapter,
    UnifiedLocalAdapter,
    UnifiedCloudAdapter,
    create_unified_adapter,
    # Canonical metric names
    METRIC_PV_POWER,
    METRIC_ACTIVE_POWER,
    METRIC_LOAD_POWER,
    METRIC_GRID_POWER,
    METRIC_GRID_EXPORT,
    METRIC_GRID_IMPORT,
    METRIC_BATTERY_POWER,
    METRIC_BATTERY_CHARGE,
    METRIC_BATTERY_DISCHARGE,
    METRIC_BATTERY_SOC,
    METRIC_BATTERY_SOH,
    METRIC_BATTERY_TEMP,
    METRIC_BATTERY_VOLTAGE,
    METRIC_BATTERY_CURRENT,
    METRIC_INVERTER_TEMP,
    METRIC_GRID_FREQUENCY,
    METRIC_ENERGY_TODAY,
    METRIC_ENERGY_TOTAL,
    METRIC_EXPORT_TODAY,
    METRIC_EXPORT_TOTAL,
    METRIC_IMPORT_TODAY,
    METRIC_IMPORT_TOTAL,
    METRIC_INVERTER_STATUS,
    METRIC_WORK_MODE,
)

from .tou_builder import (
    TouSlotProgramme,
    build_tou_programme,
    encode_deye_tou,
    encode_sunsynk_tou,
    simple_offpeak_programme,
    hm_to_minutes,
    minutes_to_hm,
)

# Cloud adapters
from .deye import Deye
from .solis import Solis
from .solarman import Solarman
from .growatt import Growatt
from .sungrow import Sungrow
from .huawei import Huawei
from .goodwe import GoodWe

# Local adapters
from .eybond_local import EybondLocalAdapter
from .goodwe_local import GoodWeLocalAdapter
from .modbus_local import ModbusTcpPoller
from .solarman_local import SolarmanV5Poller
from .sunsynk_local import SunsynkLocalAdapter

# Daemon
from .local_daemon import LocalAgentDaemon, LocalDeviceConfig, PollResult, PollFailure

__all__ = [
    # Interface
    "ReadAdapterProtocol",
    "WriteAdapterProtocol",
    "LocalReadAdapterProtocol",
    "InverterControlMixin",
    "TelemetrySnapshot",
    "TouSlot",
    "WorkMode",
    "normalize_points",
    "adapter_capabilities",
    "UnifiedInverterAdapter",
    "UnifiedLocalAdapter",
    "UnifiedCloudAdapter",
    "create_unified_adapter",
    # TOU
    "TouSlotProgramme",
    "build_tou_programme",
    "encode_deye_tou",
    "encode_sunsynk_tou",
    "simple_offpeak_programme",
    "hm_to_minutes",
    "minutes_to_hm",
    # Cloud
    "Deye",
    "Solis",
    "Solarman",
    "Growatt",
    "Sungrow",
    "Huawei",
    "GoodWe",
    # Local
    "EybondLocalAdapter",
    "GoodWeLocalAdapter",
    "ModbusTcpPoller",
    "SolarmanV5Poller",
    "SunsynkLocalAdapter",
    # Daemon
    "LocalAgentDaemon",
    "LocalDeviceConfig",
    "PollResult",
    "PollFailure",
]
