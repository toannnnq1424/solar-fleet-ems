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

# Cloud adapters
from .deye import Deye

# Local adapters
from .eybond_local import EybondLocalAdapter
from .goodwe import GoodWe
from .goodwe_local import GoodWeLocalAdapter
from .growatt import Growatt
from .huawei import Huawei
from .interfaces import (
    METRIC_ACTIVE_POWER,
    METRIC_BATTERY_CHARGE,
    METRIC_BATTERY_CURRENT,
    METRIC_BATTERY_DISCHARGE,
    METRIC_BATTERY_POWER,
    METRIC_BATTERY_SOC,
    METRIC_BATTERY_SOH,
    METRIC_BATTERY_TEMP,
    METRIC_BATTERY_VOLTAGE,
    METRIC_ENERGY_TODAY,
    METRIC_ENERGY_TOTAL,
    METRIC_EXPORT_TODAY,
    METRIC_EXPORT_TOTAL,
    METRIC_GRID_EXPORT,
    METRIC_GRID_FREQUENCY,
    METRIC_GRID_IMPORT,
    METRIC_GRID_POWER,
    METRIC_IMPORT_TODAY,
    METRIC_IMPORT_TOTAL,
    METRIC_INVERTER_STATUS,
    METRIC_INVERTER_TEMP,
    METRIC_LOAD_POWER,
    # Canonical metric names
    METRIC_PV_POWER,
    METRIC_WORK_MODE,
    InverterControlMixin,
    LocalReadAdapterProtocol,
    ReadAdapterProtocol,
    TelemetrySnapshot,
    TouSlot,
    UnifiedCloudAdapter,
    UnifiedInverterAdapter,
    UnifiedLocalAdapter,
    WorkMode,
    WriteAdapterProtocol,
    adapter_capabilities,
    create_unified_adapter,
    normalize_points,
)

# Daemon
from .local_daemon import LocalAgentDaemon, LocalDeviceConfig, PollFailure, PollResult
from .modbus_local import ModbusTcpPoller
from .solarman import Solarman
from .solarman_local import SolarmanV5Poller
from .solis import Solis
from .sungrow import Sungrow
from .sunsynk_local import SunsynkLocalAdapter
from .tou_builder import (
    TouSlotProgramme,
    build_tou_programme,
    encode_deye_tou,
    encode_sunsynk_tou,
    hm_to_minutes,
    minutes_to_hm,
    simple_offpeak_programme,
)

__all__ = [
    # Canonical metric names
    "METRIC_ACTIVE_POWER",


    "METRIC_BATTERY_CHARGE",
    "METRIC_BATTERY_CURRENT",
    "METRIC_BATTERY_DISCHARGE",
    "METRIC_BATTERY_POWER",
    "METRIC_BATTERY_SOC",
    "METRIC_BATTERY_SOH",
    "METRIC_BATTERY_TEMP",
    "METRIC_BATTERY_VOLTAGE",
    "METRIC_ENERGY_TODAY",
    "METRIC_ENERGY_TOTAL",
    "METRIC_EXPORT_TODAY",
    "METRIC_EXPORT_TOTAL",
    "METRIC_GRID_EXPORT",
    "METRIC_GRID_FREQUENCY",
    "METRIC_GRID_IMPORT",
    "METRIC_GRID_POWER",
    "METRIC_IMPORT_TODAY",
    "METRIC_IMPORT_TOTAL",
    "METRIC_INVERTER_STATUS",
    "METRIC_INVERTER_TEMP",
    "METRIC_LOAD_POWER",
    "METRIC_PV_POWER",
    "METRIC_WORK_MODE",
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
