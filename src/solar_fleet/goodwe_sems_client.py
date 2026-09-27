"""GoodWe SEMS Portal Cloud API Client & Telemetry Normalizer.

Independently implemented for Solar Fleet EMS.
Researched and derived from upstream open-source project:
pygoodwe-main (MIT License, Copyright (c) 2017 James Hodgkinson).

Provides:
- GoodWe SEMS Portal CrossLogin authentication with automatic token handling and regional base URL discovery
- Real-time station monitoring ingestion (v2/PowerStation/GetMonitorDetailByPowerstationId)
- Multiphase inverter electrical telemetry (vac1..3, iac1..3, fac, vpv1..2, ipv1..2, temp)
- Battery state-of-charge (SOC) and bidirectional powerflow parser (-1 Importing, 1 Using Battery)
- Monthly station energy and yield report parser (v1/ReportData/GetPowerStationPowerReportByMonth)
- High-fidelity telemetry normalization into unified Solar Fleet EMS telemetry schema
"""

from __future__ import annotations

import json
import logging
import re
from dataclasses import asdict, dataclass, field
from datetime import datetime
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DEFAULT_SEMS_UA = "PVMaster/2.0.4 (iPhone; iOS 11.4.1; Scale/2.00)"
DEFAULT_SEMS_GLOBAL_URL = "https://semsportal.com/api/"
DEFAULT_INIT_TOKEN = '{"version":"v2.0.4","client":"ios","language":"en"}'
SUCCESS_MSG_KEYWORDS = ("success", "successful", "ok")


# ---------------------------------------------------------------------------
# Data Models
# ---------------------------------------------------------------------------

@dataclass
class GoodWeStationInfo:
    """Station metadata from GoodWe SEMS Portal."""

    station_id: str
    station_name: str
    capacity_kw: float
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address: Optional[str] = None
    status: int = 1
    battery_capacity_kwh: Optional[float] = None
    time_str: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GoodWePowerflow:
    """Bidirectional power flow state."""

    pv_power_w: float = 0.0
    load_power_w: float = 0.0
    load_status: int = -1  # -1 = Importing from Grid, 1 = Using Battery / Exporting
    load_direction: str = "Importing"
    battery_power_w: float = 0.0
    grid_power_w: float = 0.0
    soc_pct: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GoodWeInverterTelemetry:
    """Electrical telemetry for a single GoodWe inverter."""

    serial_number: str
    name: str
    model_type: str
    status: int
    temperature_c: float
    pac_w: float
    vac1: float
    vac2: float = 0.0
    vac3: float = 0.0
    iac1: float = 0.0
    iac2: float = 0.0
    iac3: float = 0.0
    fac1_hz: float = 50.0
    vpv1: float = 0.0
    vpv2: float = 0.0
    ipv1: float = 0.0
    ipv2: float = 0.0
    soc_pct: Optional[float] = None
    pmeter_w: Optional[float] = None

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class GoodWeStationDetail:
    """Full station monitoring detail bundle."""

    station_info: GoodWeStationInfo
    kpi: Dict[str, float]
    powerflow: GoodWePowerflow
    inverters: List[GoodWeInverterTelemetry] = field(default_factory=list)
    raw_response: Optional[Dict[str, Any]] = None

    def to_dict(self) -> Dict[str, Any]:
        return {
            "station_info": self.station_info.to_dict(),
            "kpi": self.kpi,
            "powerflow": self.powerflow.to_dict(),
            "inverters": [inv.to_dict() for inv in self.inverters],
        }


# ---------------------------------------------------------------------------
# Value Parsers
# ---------------------------------------------------------------------------

def parse_goodwe_numeric(val: Any, unit_strip: str = "(W)") -> float:
    """Parse numeric strings from GoodWe SEMS which often contain unit suffixes like '2678.67(W)'."""
    if val is None:
        return 0.0
    if isinstance(val, (int, float)):
        return float(val)
    if isinstance(val, str):
        cleaned = val.strip()
        if unit_strip and cleaned.endswith(unit_strip):
            cleaned = cleaned[:-len(unit_strip)].strip()
        # Remove any other common unit suffixes if present
        cleaned = re.sub(r"\s*\([A-Za-z%]+\)$", "", cleaned)
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    return 0.0


# ---------------------------------------------------------------------------
# GoodWe SEMS Portal Client
# ---------------------------------------------------------------------------

class GoodWeSEMSClient:
    """Client for the GoodWe SEMS Portal REST API."""

    def __init__(
        self,
        account: str = "",
        password: str = "",
        system_id: str = "",
        global_url: str = DEFAULT_SEMS_GLOBAL_URL,
        user_agent: str = DEFAULT_SEMS_UA,
    ) -> None:
        self.account = account
        self.password = password
        self.system_id = system_id
        self.global_url = global_url if global_url.endswith("/") else global_url + "/"
        self.base_url = self.global_url
        self.user_agent = user_agent
        self.token: str = DEFAULT_INIT_TOKEN
        self.is_authenticated: bool = False

    @property
    def headers(self) -> Dict[str, str]:
        """Headers required by GoodWe SEMS Portal."""
        return {
            "User-Agent": self.user_agent,
            "Token": self.token,
            "Content-Type": "application/json",
            "Accept": "application/json",
        }

    def process_login_response(self, response_data: Dict[str, Any]) -> bool:
        """Process JSON response from /v2/Common/CrossLogin."""
        if not response_data:
            return False

        code = response_data.get("code")
        if code != 0:
            logger.error("GoodWe login failed: %s (code %s)", response_data.get("msg"), code)
            return False

        # Capture dynamic regional endpoint redirection (e.g. eu.semsportal.com or au.semsportal.com)
        api_redirect = response_data.get("api")
        if api_redirect:
            if not api_redirect.endswith("/"):
                api_redirect += "/"
            self.base_url = api_redirect
            logger.info("GoodWe regional endpoint discovered: %s", self.base_url)

        token_data = response_data.get("data")
        if token_data:
            self.token = json.dumps(token_data)
            self.is_authenticated = True
            return True

        return False

    @classmethod
    def parse_station_detail(cls, raw_data: Dict[str, Any], system_id: str = "") -> GoodWeStationDetail:
        """Parse raw JSON from v2/PowerStation/GetMonitorDetailByPowerstationId into structured models."""
        info_raw = raw_data.get("info", {})
        kpi_raw = raw_data.get("kpi", {})
        powerflow_raw = raw_data.get("powerflow", {})
        soc_raw = raw_data.get("soc", {})
        inverters_raw = raw_data.get("inverter", [])

        # 1. Station info
        st_id = str(info_raw.get("powerstation_id") or system_id or "goodwe_station")
        station_info = GoodWeStationInfo(
            station_id=st_id,
            station_name=info_raw.get("stationname", "GoodWe Plant"),
            capacity_kw=parse_goodwe_numeric(info_raw.get("capacity", 0.0)),
            latitude=float(info_raw["latitude"]) if info_raw.get("latitude") is not None else None,
            longitude=float(info_raw["longitude"]) if info_raw.get("longitude") is not None else None,
            address=info_raw.get("address"),
            status=int(info_raw.get("status", 1)),
            battery_capacity_kwh=float(info_raw["battery_capacity"]) if info_raw.get("battery_capacity") is not None else None,
            time_str=info_raw.get("time"),
        )

        # 2. KPI metrics
        kpi = {
            "day_generation_kwh": parse_goodwe_numeric(kpi_raw.get("power", 0.0)),
            "total_generation_kwh": parse_goodwe_numeric(kpi_raw.get("total_power", 0.0)),
            "day_income": parse_goodwe_numeric(kpi_raw.get("day_income", 0.0)),
            "total_income": parse_goodwe_numeric(kpi_raw.get("total_income", 0.0)),
            "pac_w": parse_goodwe_numeric(kpi_raw.get("pac", 0.0)),
        }

        # 3. Powerflow
        pv_val = parse_goodwe_numeric(powerflow_raw.get("pv", "0"))
        load_val = parse_goodwe_numeric(powerflow_raw.get("load", "0"))
        load_status = int(powerflow_raw.get("loadStatus", -1))
        load_dir = "Using Battery" if load_status == 1 else "Importing"
        battery_val = parse_goodwe_numeric(powerflow_raw.get("bettery", "0"))
        grid_val = parse_goodwe_numeric(powerflow_raw.get("grid", "0"))

        # SOC can come from 'soc.power' or inverter.invert_full.soc
        soc_val: Optional[float] = None
        if isinstance(soc_raw, dict) and soc_raw.get("power") is not None:
            soc_val = parse_goodwe_numeric(soc_raw.get("power"))

        powerflow = GoodWePowerflow(
            pv_power_w=pv_val,
            load_power_w=load_val,
            load_status=load_status,
            load_direction=load_dir,
            battery_power_w=battery_val,
            grid_power_w=grid_val,
            soc_pct=soc_val,
        )

        # 4. Inverters
        inverters: List[GoodWeInverterTelemetry] = []
        if isinstance(inverters_raw, list):
            for inv_item in inverters_raw:
                full = inv_item.get("invert_full", {})
                inv_soc = parse_goodwe_numeric(full.get("soc")) if full.get("soc") is not None else soc_val

                inverters.append(
                    GoodWeInverterTelemetry(
                        serial_number=str(inv_item.get("sn", "")),
                        name=str(inv_item.get("name", "Inverter")),
                        model_type=str(inv_item.get("model_type", "GoodWe")),
                        status=int(inv_item.get("status", 1)),
                        temperature_c=parse_goodwe_numeric(inv_item.get("tempperature", full.get("tempperature", 0.0))),
                        pac_w=parse_goodwe_numeric(full.get("pac", 0.0)),
                        vac1=parse_goodwe_numeric(full.get("vac1", 0.0)),
                        vac2=parse_goodwe_numeric(full.get("vac2", 0.0)),
                        vac3=parse_goodwe_numeric(full.get("vac3", 0.0)),
                        iac1=parse_goodwe_numeric(full.get("iac1", 0.0)),
                        iac2=parse_goodwe_numeric(full.get("iac2", 0.0)),
                        iac3=parse_goodwe_numeric(full.get("iac3", 0.0)),
                        fac1_hz=parse_goodwe_numeric(full.get("fac1", 50.0)),
                        vpv1=parse_goodwe_numeric(full.get("vpv1", 0.0)),
                        vpv2=parse_goodwe_numeric(full.get("vpv2", 0.0)),
                        ipv1=parse_goodwe_numeric(full.get("ipv1", 0.0)),
                        ipv2=parse_goodwe_numeric(full.get("ipv2", 0.0)),
                        soc_pct=inv_soc,
                        pmeter_w=parse_goodwe_numeric(full.get("pmeter")) if full.get("pmeter") is not None else None,
                    )
                )

        return GoodWeStationDetail(
            station_info=station_info,
            kpi=kpi,
            powerflow=powerflow,
            inverters=inverters,
            raw_response=raw_data,
        )

    @classmethod
    def parse_monthly_report(cls, raw_data: Dict[str, Any]) -> Dict[str, Any]:
        """Parse monthly generation report from v1/ReportData/GetPowerStationPowerReportByMonth."""
        stations_list = raw_data.get("list", [])
        parsed_stations = []
        for item in stations_list:
            parsed_stations.append({
                "powerstation_id": item.get("pw_id"),
                "station_name": item.get("pw_name"),
                "capacity_kwp": parse_goodwe_numeric(item.get("capacity")),
                "address": item.get("address"),
                "owner_name": item.get("owner_name"),
                "month_generation_kwh": parse_goodwe_numeric(item.get("month_power")),
                "avg_daily_generation_kwh": parse_goodwe_numeric(item.get("avg_day_power")),
                "total_lifetime_generation_kwh": parse_goodwe_numeric(item.get("total_power")),
            })

        return {
            "total_records": raw_data.get("record", len(parsed_stations)),
            "stations": parsed_stations,
        }

    @classmethod
    def normalize_to_fleet_telemetry(cls, detail: GoodWeStationDetail) -> Dict[str, Any]:
        """Normalize GoodWe SEMS telemetry into standard Solar Fleet EMS format."""
        inv = detail.inverters[0] if detail.inverters else None

        active_power_kw = (detail.kpi.get("pac_w", 0.0) or (inv.pac_w if inv else 0.0)) / 1000.0
        pv_power_kw = detail.powerflow.pv_power_w / 1000.0
        load_power_kw = detail.powerflow.load_power_w / 1000.0
        battery_power_kw = detail.powerflow.battery_power_w / 1000.0
        grid_power_kw = detail.powerflow.grid_power_w / 1000.0

        return {
            "source": "GoodWe SEMS Portal (Cloud)",
            "station_id": detail.station_info.station_id,
            "station_name": detail.station_info.station_name,
            "timestamp": detail.station_info.time_str or datetime.utcnow().isoformat(),
            "pv_power_kw": round(pv_power_kw, 3),
            "active_power_kw": round(active_power_kw, 3),
            "load_power_kw": round(load_power_kw, 3),
            "battery_power_kw": round(battery_power_kw, 3),
            "grid_power_kw": round(grid_power_kw, 3),
            "load_direction": detail.powerflow.load_direction,
            "soc_pct": detail.powerflow.soc_pct if detail.powerflow.soc_pct is not None else (inv.soc_pct if inv else None),
            "daily_generation_kwh": round(detail.kpi.get("day_generation_kwh", 0.0), 2),
            "total_generation_kwh": round(detail.kpi.get("total_generation_kwh", 0.0), 2),
            "inverter_temperature_c": inv.temperature_c if inv else None,
            "grid_voltage_v": inv.vac1 if inv else None,
            "grid_frequency_hz": inv.fac1_hz if inv else None,
            "connected_inverters_count": len(detail.inverters),
        }
