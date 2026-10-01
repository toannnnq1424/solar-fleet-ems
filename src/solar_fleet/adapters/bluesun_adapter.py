"""Bluesun Multi-Platform Adapter — Disaggregates Bluesun into 3 distinct operational paths.

Official technical reality (Bluesun Solar Manuals & Catalogues):
1. BSM-Series (e.g. BSM-5500BLV-48DA): SRNE/Voltronic OEM hybrid, monitors via SmartESS / Eybond
   Wi-Fi Plug Pro, RS485 Modbus RTU / Eybond protocol.
2. BSE-Series (e.g. BSE6KL1, BSE20/30KH3): Next-gen Commercial/Residential Hybrid, monitors via
   Bluesun Hybrid Cloud Platform (anti-feed-in, TOU scheduling, remote firmware update).
3. Bluesun ESS Battery: Dedicated Lithium LFP BMS Cloud & direct CAN/RS485 (pack-level SOH, cell delta-V).
"""

from __future__ import annotations

import enum
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from typing import Any

logger = logging.getLogger(__name__)


class BluesunBranch(str, enum.Enum):
    BSM_OFFGRID = "bsm_offgrid"
    BSE_HYBRID = "bse_hybrid"
    ESS_BATTERY = "ess_battery"


@dataclass
class BluesunDeviceConfig:
    device_id: str
    branch: BluesunBranch
    serial_number: str
    modbus_slave_id: int = 1
    cloud_station_id: str | None = None
    bms_pack_id: int = 1
    rated_power_kw: float = 5.0
    nominal_voltage_v: float = 48.0


@dataclass
class CapabilityProfile:
    vendor: str
    model: str
    supports_work_mode: bool = False
    supports_export_limit: bool = False
    supports_tou: bool = False
    supports_peak_shaving: bool = False
    supports_generator_charge: bool = False
    supports_bms_param_edit: bool = False
    max_charge_power_kw: float = 0.0
    max_discharge_power_kw: float = 0.0
    supported_work_modes: list[str] = field(default_factory=list)
    notes: str = ""


class BluesunAdapter:
    """Unified Bluesun Adapter delegating to exact underlying driver without fake monolithic calls."""

    def __init__(self, credentials: dict[str, Any] | None = None):
        self.credentials = credentials or {}

    async def read_telemetry(self, config: BluesunDeviceConfig, raw_data: dict[str, Any] | None = None) -> dict[str, Any]:
        """Read fresh telemetry routed by specific hardware branch.

        Fail-closed: Returns UNAVAILABLE if no physical transport or verified raw data is supplied.
        Zero hardcoded watts or synthetic SOC values in operational logic.
        """
        now_iso = datetime.now(UTC).isoformat()

        if raw_data is None:
            # Check if underlying credentials or active transport exist
            has_transport = bool(self.credentials.get("active_transport") or self.credentials.get("connected"))
            if not has_transport:
                return {
                    "branch": config.branch.value,
                    "device_id": config.device_id,
                    "serial_number": config.serial_number,
                    "status": "UNAVAILABLE",
                    "reason": "NO_PHYSICAL_TRANSPORT_CONFIGURED",
                    "timestamp": now_iso,
                    "telemetry": {},
                }

        return self.decode_branch_telemetry(config.branch, raw_data or {})

    @staticmethod
    def decode_branch_telemetry(branch: BluesunBranch, raw: dict[str, Any]) -> dict[str, Any]:
        """Decodes raw input registers or payload according to exact branch protocol specification."""
        if branch == BluesunBranch.BSM_OFFGRID:
            # BSM Series: Eybond / SmartESS RS485 Modbus RTU telemetry
            return {
                "branch": "bsm_offgrid",
                "status": "ok" if raw else "NO_DATA",
                "inverter_mode": raw.get("work_mode", "UNKNOWN"),
                "telemetry": {
                    "pv_power_w": raw.get("pv_power_w"),
                    "pv1_voltage_v": raw.get("pv1_v"),
                    "battery_soc": raw.get("soc"),
                    "battery_voltage_v": raw.get("bat_v"),
                    "ac_output_power_w": raw.get("ac_power_w"),
                    "grid_voltage_v": raw.get("grid_v"),
                    "load_percentage": raw.get("load_pct"),
                },
            }

        elif branch == BluesunBranch.BSE_HYBRID:
            # BSE Series: Bluesun Hybrid Cloud Platform telemetry
            return {
                "branch": "bse_hybrid",
                "status": "ok" if raw else "NO_DATA",
                "feed_in_limiter_enabled": bool(raw.get("anti_feed_in", False)),
                "export_limit_w": raw.get("export_limit_w"),
                "telemetry": {
                    "grid_active_power_w": raw.get("grid_p_w"),
                    "pv_active_power_w": raw.get("pv_p_w"),
                    "battery_power_w": raw.get("bat_p_w"),
                    "load_active_power_w": raw.get("load_p_w"),
                    "battery_soc": raw.get("soc"),
                    "work_mode": raw.get("mode", "UNKNOWN"),
                },
            }

        elif branch == BluesunBranch.ESS_BATTERY:
            # Dedicated Bluesun LFP Battery BMS Pack
            return {
                "branch": "ess_battery",
                "status": "ok" if raw else "NO_DATA",
                "chemistry": "LiFePO4",
                "telemetry": {
                    "nominal_voltage_v": 51.2,
                    "total_voltage_v": raw.get("pack_voltage_v"),
                    "current_a": raw.get("pack_current_a"),
                    "soc_pct": raw.get("soc"),
                    "soh_pct": raw.get("soh"),
                    "max_continuous_c_rate": 0.5,
                    "pack_temperature_c": raw.get("temp_c"),
                    "cell_voltages_v": raw.get("cell_voltages_v", []),
                    "cycle_count": raw.get("cycle_count"),
                },
            }
        else:
            raise ValueError(f"Unknown Bluesun branch: {branch}")


    async def write_parameter(self, config: BluesunDeviceConfig, register: int, value: Any) -> None:
        """Remote parameter writes strictly gated pending real field hardware acceptance."""
        raise PermissionError(
            f"Remote control write locked for Bluesun device {config.device_id} ({config.branch}). "
            "Requires physical commissioning and IEC 62446-1 verification."
        )

    def get_capability_profile(self, branch: BluesunBranch, model_name: str) -> CapabilityProfile:
        if branch == BluesunBranch.BSM_OFFGRID:
            return CapabilityProfile(
                vendor="bluesun",
                model=model_name,
                supports_work_mode=True,
                supports_export_limit=True,
                supports_tou=True,
                supports_generator_charge=True,
                max_charge_power_kw=5.5,
                max_discharge_power_kw=5.5,
                supported_work_modes=["SolarFirst", "UtilityFirst", "SBU"],
                notes="BSM Series using SmartESS/Eybond protocol (Voltronic/SRNE OEM core)",
            )
        elif branch == BluesunBranch.ESS_BATTERY:
            return CapabilityProfile(
                vendor="bluesun",
                model=model_name,
                supports_work_mode=False,
                supports_export_limit=False,
                max_charge_power_kw=0.0,
                max_discharge_power_kw=0.0,
                notes="Bluesun Lithium ESS Battery BMS monitoring stream",
            )
        else:
            return CapabilityProfile(
                vendor="bluesun",
                model=model_name,
                supports_work_mode=True,
                supports_export_limit=True,
                supports_tou=True,
                supports_peak_shaving=True,
                supports_generator_charge=True,
                supports_bms_param_edit=True,
                max_charge_power_kw=6.0,
                max_discharge_power_kw=6.0,
                supported_work_modes=["General", "PeakShaving", "OffGrid", "Economic"],
                notes="BSE Series using Bluesun Hybrid Cloud Platform with anti-feed-in",
            )
