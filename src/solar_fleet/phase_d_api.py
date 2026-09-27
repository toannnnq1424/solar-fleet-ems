"""API endpoints for Phase D integration modules.

Installs routes for:
- MPC Controller dispatch optimization
- Microgrid controller status and simulation
- Anomaly detection monitoring
- Solar PV model estimation
- Modbus protocol register map queries
- Inverter model simulation
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Any, Dict, Literal

from fastapi import Depends, HTTPException, Query
from pydantic import AwareDatetime, BaseModel, ConfigDict, Field, model_validator

from .calculation_inputs import (
    BlackStartCalculation,
    GeneratorCalculation,
    GridCalculation,
    HeatPumpCalculation,
    MicrogridCalculation,
    PredbatCalculation,
    SGCalculation,
)

# ---------------------------------------------------------------------------
# Request / Response models
# ---------------------------------------------------------------------------

class ExplicitCalculationRequest(BaseModel):
    model_config = ConfigDict(extra="forbid", allow_inf_nan=False)


class CatalogueBillRequest(ExplicitCalculationRequest):
    tariff_key: str = Field(min_length=1)
    import_kwh_hourly: list[Annotated[float, Field(ge=0)]] = Field(min_length=24, max_length=24)
    export_kwh_hourly: list[Annotated[float, Field(ge=0)]] = Field(min_length=24, max_length=24)
    peak_demand_kw: float = Field(ge=0)


class PhaseMeasurementRequest(ExplicitCalculationRequest):
    v_l1: float = Field(gt=0)
    v_l2: float = Field(gt=0)
    v_l3: float = Field(gt=0)
    i_l1: float = Field(ge=0)
    i_l2: float = Field(ge=0)
    i_l3: float = Field(ge=0)
    p_l1: float
    p_l2: float
    p_l3: float
    q_l1: float
    q_l2: float
    q_l3: float


class PhaseLimitsRequest(ExplicitCalculationRequest):
    max_total_kw: float = Field(gt=0)
    max_phase_kw: float = Field(gt=0)
    max_phase_kvar: float = Field(ge=0)
    battery_max_charge_kw: float = Field(ge=0)
    battery_max_discharge_kw: float = Field(ge=0)
    allows_independent_phases: bool = Field(strict=True)


class PhaseDispatchRequest(ExplicitCalculationRequest):
    measurement: PhaseMeasurementRequest
    limits: PhaseLimitsRequest


class BuildingParametersRequest(ExplicitCalculationRequest):
    indoor_temp_c: float = Field(gt=-273.15)
    wall_temp_c: float = Field(gt=-273.15)
    air_heat_capacity_kwh_k: float = Field(gt=0)
    wall_heat_capacity_kwh_k: float = Field(gt=0)
    r_indoor_wall_k_kw: float = Field(gt=0)
    r_wall_outdoor_k_kw: float = Field(gt=0)
    solar_aperture_m2: float = Field(ge=0)
    internal_gain_base_kw: float = Field(ge=0)


class BuildingSimulationRequest(ExplicitCalculationRequest):
    building: BuildingParametersRequest
    outdoor_temps_hourly: list[float] = Field(min_length=1, max_length=168)
    solar_ghi_hourly: list[float] = Field(min_length=1, max_length=168)
    heating_thermal_kw: float

    @model_validator(mode="after")
    def validate_series(self):
        if len(self.outdoor_temps_hourly) != len(self.solar_ghi_hourly):
            raise ValueError("aligned_weather_series_required")
        if any(t <= -273.15 for t in self.outdoor_temps_hourly) or any(g < 0 for g in self.solar_ghi_hourly):
            raise ValueError("invalid_weather_series")
        b = self.building
        # One-hour forward Euler steps must not overshoot the thermal time constants.
        if (b.air_heat_capacity_kwh_k * b.r_indoor_wall_k_kw < 1
                or b.wall_heat_capacity_kwh_k < 1 / b.r_indoor_wall_k_kw + 1 / b.r_wall_outdoor_k_kw):
            raise ValueError("thermal_time_constants_require_smaller_integration_step")
        return self


class EVLoadpointRequest(ExplicitCalculationRequest):
    observed_at: AwareDatetime | None = None
    id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    vehicle_id: str | None
    soc_pct: float | None = Field(ge=0, le=100)
    target_soc_pct: float = Field(ge=0, le=100)
    mode: Literal["off", "now", "min_pv", "pv"]
    priority: int = Field(ge=1, le=5)
    min_current_amps: float = Field(gt=0, le=1000)
    max_current_amps: float = Field(gt=0, le=1000)
    voltage_per_phase_v: float = Field(gt=0, le=1000)
    phases: Literal[1, 3]

    @model_validator(mode="after")
    def validate_limits(self):
        if self.min_current_amps > self.max_current_amps:
            raise ValueError("min_current_exceeds_max_current")
        if self.vehicle_id is not None and (not self.vehicle_id.strip() or self.soc_pct is None):
            raise ValueError("connected_vehicle_requires_identity_and_soc")
        return self


class EVFleetRequest(ExplicitCalculationRequest):
    observed_at: AwareDatetime | None = None
    site_breaker_limit_kw: float = Field(gt=0, le=100000)
    available_solar_surplus_kw: float = Field(ge=0, le=100000)
    building_base_load_kw: float = Field(ge=0, le=100000)
    chargers: list[EVLoadpointRequest] = Field(min_length=1, max_length=100)

    @model_validator(mode="after")
    def unique_chargers(self):
        ids = [charger.id for charger in self.chargers]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_charger_id")
        return self


class MarketBidRequest(ExplicitCalculationRequest):
    id: str = Field(min_length=1)
    market: Literal["day_ahead", "intraday"]
    direction: Literal["buy_charge", "sell_discharge"]
    delivery_hour: int = Field(ge=0, le=23)
    quantity_mw: float = Field(ge=0.01, le=100000)
    price_eur_per_mwh: float


class MarketCalculationRequest(ExplicitCalculationRequest):
    fleet_capacity_mw: float = Field(gt=0, le=100000)
    bids: list[MarketBidRequest] = Field(min_length=1, max_length=1000)
    clearing_prices: dict[int, float]

    @model_validator(mode="after")
    def validate_bids(self):
        ids = [bid.id for bid in self.bids]
        if len(ids) != len(set(ids)):
            raise ValueError("duplicate_bid_id")
        quantities = {}
        for bid in self.bids:
            if bid.delivery_hour not in self.clearing_prices:
                raise ValueError("delivery_hour_price_required")
            quantities[bid.delivery_hour] = quantities.get(bid.delivery_hour, 0) + bid.quantity_mw
        if any(value > self.fleet_capacity_mw for value in quantities.values()):
            raise ValueError("hourly_bids_exceed_fleet_capacity")
        if any(hour < 0 or hour > 23 for hour in self.clearing_prices):
            raise ValueError("invalid_clearing_hour")
        return self


class MPCDispatchRequest(BaseModel):
    """Request for MPC dispatch optimization."""

    soc_init: float = Field(ge=0.0, le=1.0)
    pv_forecast_kw: list[float] = Field(min_length=1, max_length=168)
    load_forecast_kw: list[float] = Field(min_length=1, max_length=168)
    price_forecast: list[float] = Field(min_length=1, max_length=168)
    horizon_steps: int = Field(ge=1, le=168, default=24)
    battery_capacity_kwh: float = Field(ge=0.1, le=10000)
    max_charge_kw: float = Field(ge=0.1, le=10000)
    max_discharge_kw: float = Field(ge=0.1, le=10000)


class SolarEstimateRequest(ExplicitCalculationRequest):
    """Request for solar PV energy estimation."""

    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)
    peak_power_kwp: float = Field(ge=0.1, le=100000)
    date: str = Field(pattern=r"^\d{4}-\d{2}-\d{2}$")
    altitude_m: float = Field(ge=0, le=9000)
    tilt_deg: float = Field(ge=0, le=90)
    azimuth_deg: float = Field(ge=0, le=360)
    system_loss: float = Field(ge=0, lt=1)
    inverter_efficiency: float = Field(gt=0, le=1)
    hourly_temperature: list[float] = Field(min_length=24, max_length=24)
    hourly_wind: list[float] = Field(min_length=24, max_length=24)

    @model_validator(mode="after")
    def weather_bounds(self):
        datetime.strptime(self.date, "%Y-%m-%d")
        if any(t <= -273.15 for t in self.hourly_temperature) or any(w < 0 for w in self.hourly_wind):
            raise ValueError("invalid_weather_inputs")
        return self


class AnomalyCheckRequest(BaseModel):
    """Request for anomaly detection check."""

    device_id: str = Field(min_length=1)
    metrics: dict[str, float] = Field(default_factory=dict)
    rated_power_kw: float = Field(ge=0.1, le=100000, default=10.0)


class OptimizePollingRequest(BaseModel):
    """Request for Modbus block polling packing optimization."""

    model_id: str = Field(min_length=1)
    requested_field_ids: list[str] | None = None
    enable_gap_tolerance: bool = True


class DecodeTelemetryRequest(BaseModel):
    """Request for decoding raw Modbus registers into engineering telemetry."""

    model_id: str = Field(min_length=1)
    registers: dict[int, int] = Field(default_factory=dict)


class DecodeAlarmsRequest(BaseModel):
    """Request for decoding multi-word alarm bitfields into structured incidents."""

    model_id: str = Field(min_length=1)
    registers: dict[int, int] = Field(default_factory=dict)


class SolisDiscoveryRequest(BaseModel):
    """Request for compiling Home Assistant MQTT discovery topics and payloads."""

    device_name: str = "solis_inverter"
    device_model: str = "Ginlong Solis String"
    base_topic: str = "solis2mqtt"
    discovery_prefix: str = "homeassistant"


class SolisDecodeTelemetryRequest(BaseModel):
    """Request for decoding raw Solis Modbus registers into engineering telemetry."""

    registers: dict[int, int] = Field(default_factory=dict)
    base_topic: str = "solis2mqtt"


class SolisOfflineSanitizeRequest(BaseModel):
    """Request for simulating offline / night-time telemetry sanitization."""

    last_known_metrics: dict[str, Any] = Field(default_factory=dict)
    base_topic: str = "solis2mqtt"


class SolisCompileControlRequest(BaseModel):
    """Request for compiling FC06 Modbus write command with safety gating."""

    metric: str = Field(min_length=1)
    value: Any
    slave_address: int = 1
    bypass_safety: bool = False


class GoodWeLoginRequest(BaseModel):
    """Request for GoodWe SEMS Portal authentication / credential verification."""

    account: str = Field(default="")
    password: str = Field(default="")


class GoodWeStationDetailRequest(BaseModel):
    """Request for fetching or parsing GoodWe SEMS station monitoring details."""

    station_id: str = Field(default="goodwe_station_1")
    simulated_raw_data: dict[str, Any] | None = None


class GoodWeMonthlyReportRequest(BaseModel):
    """Request for fetching or parsing GoodWe SEMS monthly generation report."""

    station_id: str = Field(default="goodwe_station_1")
    year_month: str = Field(default="2026-09")
    simulated_raw_data: dict[str, Any] | None = None


class GrowattDecodeBMSRequest(BaseModel):
    """Request for decoding Growatt SPH BMS pack gauge registers."""

    registers: dict[int, int] = Field(default_factory=dict)


class GrowattDecodeCellsRequest(BaseModel):
    """Request for decoding Growatt SPH 12-cell voltage registers."""

    registers: dict[int, int] = Field(default_factory=dict)


class GrowattDecodeSlotsRequest(BaseModel):
    """Request for decoding Growatt SPH 12-slot TOU holding registers."""

    holding_registers: dict[int, int] = Field(default_factory=dict)


class GrowattCompileModeRequest(BaseModel):
    """Request for compiling Growatt SPH priority mode command frames."""

    mode: str = Field(default="battery_first")  # 'load_first', 'battery_first', 'grid_first'
    slot_number: int = 1
    start_time: str = "00:00"
    end_time: str = "04:00"
    rate_pct: int = 100
    stop_soc_pct: int = 100
    slave_id: int = 1
    bypass_safety: bool = False


class SolisDecodeStorageModeRequest(BaseModel):
    """Request for decoding Solis Hybrid register 43110 storage control mode."""

    value: int = Field(default=0x0001, description="Register 43110 raw uint16 value")


class SolisCompileGridChargeRequest(BaseModel):
    """Request for compiling Solis Hybrid grid charging toggle command."""

    current_mode_value: int = Field(default=0x0001, description="Current register 43110 value")
    enable_grid_charge: bool = Field(default=True, description="True to allow grid to charge battery (BIT05)")


class SolisCompileTouSlotRequest(BaseModel):
    """Request for compiling Solis Hybrid 7-register TOU schedule slot."""

    slot_type: str = Field(default="charge", description="'charge' or 'discharge'")
    slot_index: int = Field(default=0, ge=0, le=5, description="Slot index (0..5)")
    target_soc: int = Field(default=100, ge=0, le=100, description="Target SOC %")
    current_a: float = Field(default=50.0, ge=0.0, le=100.0, description="Charge/discharge current in Amps")
    start_hour: int = Field(default=0, ge=0, le=23)
    start_minute: int = Field(default=0, ge=0, le=59)
    end_hour: int = Field(default=4, ge=0, le=23)
    end_minute: int = Field(default=0, ge=0, le=59)
    field2: int = Field(default=490, description="Internal slot control field (preserved or default 490)")


class SolisCompileDispatchRequest(BaseModel):
    """Request for compiling Solis Hybrid GreenGrid uniform dynamic dispatch."""

    mode: str = Field(default="auto", description="'auto', 'charge', or 'discharge'")
    power_w: float | None = Field(default=None, description="Target power in Watts")
    ttl_seconds: int = Field(default=1200, ge=60, le=86400, description="Software watchdog TTL in seconds")
    battery_voltage: float | None = Field(default=51.2, description="Battery DC voltage in Volts")
    current_storage_mode: int = Field(default=0x0001, description="Current register 43110 value")
    target_soc: int | None = Field(default=None, description="Optional target SOC % override")


class SolisDecodeTouSlotsRequest(BaseModel):
    """Request for decoding raw holding registers into Solis Hybrid TOU slots."""

    registers: dict[int, int] = Field(default_factory=dict, description="Map of holding register address to raw value")


class DeyeDecodeTelemetryRequest(BaseModel):
    """Request for decoding Deye Hybrid inverter holding registers."""

    registers: dict[int, int] = Field(default_factory=dict, description="Map of holding register address to raw value")


class DeyeDecodeTouRequest(BaseModel):
    """Request for decoding Deye 6-slot TOU schedule registers."""

    registers: dict[int, int] = Field(default_factory=dict, description="Map of holding register address to raw value")


class DeyeCompileWorkModeRequest(BaseModel):
    """Request for compiling Deye Work Mode and Solar Sell commands."""

    mode: int = Field(default=0, ge=0, le=2, description="0: Selling First, 1: Zero Export to Load, 2: Zero Export to CT")
    solar_sell: bool | None = Field(default=None, description="Enable or disable solar export")
    max_sell_power_w: int | None = Field(default=None, ge=0, le=16000, description="Max export power in Watts")


class DeyeCompileGridChargeRequest(BaseModel):
    """Request for compiling Deye Grid Charge command."""

    enable: bool = Field(default=True, description="Enable or disable AC grid charging")
    charge_current_a: int | None = Field(default=None, ge=0, le=120, description="Grid charge current limit in Amps")


class DeyeCompileTouSlotRequest(BaseModel):
    """Request for compiling Deye single TOU schedule slot."""

    slot_number: int = Field(default=1, ge=1, le=6, description="Slot index (1..6)")
    time_str: str = Field(default="01:00", description="Time string in 'HH:MM' format")
    power_w: int = Field(default=5000, ge=0, le=16000, description="Power limit in Watts")
    target_soc: int = Field(default=100, ge=0, le=100, description="Target or floor SOC %")
    charge_source: int = Field(default=1, ge=0, le=3, description="0: Off, 1: Grid, 2: Generator, 3: Both")


class SolarmanV5EncodeRequest(BaseModel):
    """Request for encoding Modbus RTU payload into Solarman V5 TCP frame."""

    modbus_rtu_hex: str = Field(default="", description="Hex-encoded Modbus RTU frame")
    logger_serial: int = Field(default=2312345678, description="Datalogger serial number (uint32)")
    sequence_number: int = Field(default=1, ge=0, le=65535, description="Client frame sequence number")


class SolarmanV5DecodeRequest(BaseModel):
    """Request for decoding and validating a Solarman V5 TCP response frame."""

    v5_frame_hex: str = Field(default="", description="Hex-encoded Solarman V5 frame")


class SolarmanV5CompileRequest(BaseModel):
    """Request for compiling high-level Modbus action into encapsulated Solarman V5 frame."""

    logger_serial: int = Field(default=2312345678, description="Datalogger serial number (uint32)")
    modbus_slave_id: int = Field(default=1, ge=1, le=254)
    function_code: int = Field(default=3, description="Modbus Function Code (3, 4, 6, 16)")
    start_address: int = Field(default=500, ge=0, le=65535)
    quantity_or_value: int = Field(default=1, ge=0, le=65535)
    values: list[int] | None = Field(default=None, description="List of values for FC16 write")
    sequence_number: int = Field(default=1, ge=0, le=65535)


class SolarmanV5DiscoveryRequest(BaseModel):
    """Request for parsing Solarman UDP discovery broadcast reply."""

    payload: str = Field(default="", description="Raw UDP reply string from port 48899")


class SmartEssPollRequest(BaseModel):
    """Request for polling SmartESS / Eybond datalogger telemetry."""

    collector_pn: str = Field(default="EYBOND-COLLECTOR-01", description="Eybond datalogger PN / Serial Number")
    devaddr: int = Field(default=1, ge=1, le=247, description="Inverter RS485 slave address (1..247)")


class SmartEssCommandRequest(BaseModel):
    """Request for safely executing inverter configuration command."""

    collector_pn: str = Field(default="EYBOND-COLLECTOR-01", description="Eybond datalogger PN / Serial Number")
    devaddr: int = Field(default=1, ge=1, le=247, description="Inverter RS485 slave address")
    command_type: str = Field(..., description="output_priority, charger_priority, max_charge_current, max_ac_charge_current, battery_cutoff_voltage, battery_bulk_float")
    params: dict[str, Any] = Field(default_factory=dict, description="Parameters dictionary for the command")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class SmartEssParseFrameRequest(BaseModel):
    """Request for parsing raw Eybond binary frame hex string."""

    raw_frame_hex: str = Field(..., description="Hex string of raw Eybond Modbus binary frame")


class GrowattMultiphaseDecodeTelemetryRequest(BaseModel):
    """Request for decoding Growatt 1-phase or 3-phase SPH registers."""

    input_registers: dict[int, int] = Field(default_factory=dict, description="Map of input register address to raw value")
    holding_registers: dict[int, int] = Field(default_factory=dict, description="Map of holding register address to raw value")


class GrowattCompileExportLimitRequest(BaseModel):
    """Request for compiling Growatt export limitation (zero feed-in) registers 122 & 123."""

    enable: bool = Field(default=True, description="Enable or disable export limitation")
    limit_rate_percent: float = Field(default=100.0, ge=0.0, le=100.0, description="Export limit rate in % (0.1% resolution)")


class GrowattCompileWindowRequest(BaseModel):
    """Request for compiling Growatt Grid First or Battery First time window."""

    window_type: str = Field(default="battery_first", description="'grid_first' or 'battery_first'")
    window_index: int = Field(default=1, ge=1, le=3, description="Window index (1..3)")
    start_time: str = Field(default="02:00", description="Start time 'HH:MM'")
    stop_time: str = Field(default="06:00", description="Stop time 'HH:MM'")
    enable: bool = Field(default=True, description="Enable or disable this time window")
    rate_percent: int = Field(default=100, ge=0, le=100, description="Charge or discharge rate in %")
    stop_soc_percent: int = Field(default=100, ge=0, le=100, description="Target stop SOC in %")
    ac_charge_enable: bool = Field(default=True, description="Enable AC grid charging (Battery First only)")


class GrowattDecodeFaultsRequest(BaseModel):
    """Request for decoding Growatt 112-bit fault registers 1001..1007."""

    fault_registers: dict[int, int] = Field(default_factory=dict, description="Map of fault input register addresses to raw words")


class GrowattCloudPlantsRequest(BaseModel):
    """Request for Growatt Cloud plant listing."""

    token: str = Field(default="DEMO-GROWATT-TOKEN-001", description="Growatt OpenAPI V1 token")
    region: str = Field(default="global", description="Growatt cloud region: 'global', 'cn', 'us'")


class GrowattCloudDevicesRequest(BaseModel):
    """Request for Growatt Cloud devices in plant."""

    token: str = Field(default="DEMO-GROWATT-TOKEN-001", description="Growatt OpenAPI V1 token")
    region: str = Field(default="global", description="Growatt cloud region: 'global', 'cn', 'us'")
    plant_id: str = Field(default="PLANT-GW-8801", description="Target plant ID")


class GrowattCloudSphDetailRequest(BaseModel):
    """Request for Growatt Cloud SPH telemetry detail."""

    token: str = Field(default="DEMO-GROWATT-TOKEN-001", description="Growatt OpenAPI V1 token")
    region: str = Field(default="global", description="Growatt cloud region: 'global', 'cn', 'us'")
    device_sn: str = Field(default="SPH460001", description="Target SPH device serial number")


class GrowattCloudCommandRequest(BaseModel):
    """Request for Growatt Cloud remote parameter write command."""

    token: str = Field(default="DEMO-GROWATT-TOKEN-001", description="Growatt OpenAPI V1 token")
    region: str = Field(default="global", description="Growatt cloud region: 'global', 'cn', 'us'")
    command_type: str = Field(..., description="Command type: 'sph_priority', 'sph_ac_charge', 'sph_power_limits', 'min_time_segment'")
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class EybondCollectorDiscoverRequest(BaseModel):
    """Request for Eybond UDP discovery packet handling."""

    raw_udp_text: str = Field(default="set>server=192.168.1.100:8899;", description="Raw UDP discovery string")


class EybondCollectorAtRequest(BaseModel):
    """Request for Eybond AT command parsing and execution."""

    at_line: str = Field(default="AT+DTUPN?", description="AT command line")
    profile_pn: str = Field(default="V00123456789012345", description="Collector synthetic PN")
    firmware_ver: str = Field(default="0.1.10", description="Bridge firmware version")
    uart_cfg: str = Field(default="2400,8,1,NONE", description="UART baud and parity string")


class EybondCollectorDecodePigsRequest(BaseModel):
    """Request for decoding Voltronic QPIGS and QPIWS telemetry strings."""

    raw_qpigs: str = Field(
        default="239.5 49.9 239.5 49.9 0927 0924 015 396 53.20 000 100 0028 002.2 315.9 00.00 00000 00010000 00 00 00665 000",
        description="Raw QPIGS response string without CRC or parentheses",
    )
    mode_char: str = Field(default="L", description="Voltronic operating mode char ('P', 'S', 'L', 'B', 'F', 'H')")
    qpiws_flags: str = Field(default="00000000000000000000000000000000", description="32-character QPIWS warning flags")
    collector_pn: str = Field(default="V00123456789012345", description="Collector PN")
    inverter_sn: str = Field(default="553555355535552", description="Inverter serial number")


class EybondCollectorCommandRequest(BaseModel):
    """Request for compiling Voltronic inverter control command."""

    command_type: str = Field(..., description="Command type: 'output_priority', 'charger_priority', 'charge_current', 'battery_voltages'")
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class GoodWeLocalTelemetryRequest(BaseModel):
    """Request for polling GoodWe local inverter telemetry."""

    host: str = Field(default="192.168.1.180", description="Inverter IP address on local network")
    port: int = Field(default=8899, description="Inverter local UDP/TCP port")
    comm_addr: int = Field(default=247, description="Modbus slave communication address (default 247/0xF7 or 127/0x7F)")
    model_family: str = Field(default="ET", description="Inverter series family: 'ET', 'ES', 'DT'")


class GoodWeLocalCommandRequest(BaseModel):
    """Request for executing GoodWe local configuration command."""

    host: str = Field(default="192.168.1.180", description="Inverter IP address on local network")
    port: int = Field(default=8899, description="Inverter local UDP/TCP port")
    comm_addr: int = Field(default=247, description="Modbus slave communication address")
    command_type: str = Field(..., description="Command type: 'operation_mode', 'export_limit', 'battery_cutoff_soc', 'eco_mode_window'")
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class HuaweiSun2000TelemetryRequest(BaseModel):
    """Request for polling Huawei SUN2000 & LUNA2000 telemetry."""

    host: str = Field(default="192.168.200.1", description="Inverter IP address on local network / SDongle / AP")
    port: int = Field(default=502, description="Modbus TCP port (default 502)")
    slave_unit_id: int = Field(default=1, description="Modbus slave unit ID (1..16)")


class HuaweiSun2000CommandRequest(BaseModel):
    """Request for executing Huawei SUN2000 & LUNA2000 configuration command."""

    host: str = Field(default="192.168.200.1", description="Inverter IP address on local network")
    port: int = Field(default=502, description="Modbus TCP port")
    slave_unit_id: int = Field(default=1, description="Modbus slave unit ID")
    command_type: str = Field(..., description="Command type: 'active_power_derating', 'storage_mode', 'export_limit', 'cutoff_soc', 'charge_from_grid', 'luna_tou_period'")
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class SolarmanProfileTelemetryRequest(BaseModel):
    """Request for polling multi-vendor inverter telemetry via Solarman profile."""

    profile_id: str = Field(default="deye_hybrid", description="Profile ID: 'deye_hybrid', 'sofar_g3hyd', 'solis_hybrid'")
    host: str = Field(default="192.168.1.150", description="Data logger IP address on local network")
    port: int = Field(default=8899, description="Solarman port (default 8899)")
    slave_id: int = Field(default=1, description="Modbus slave address")


class SolarmanProfileCommandRequest(BaseModel):
    """Request for compiling and verifying Solarman profile parameter write."""

    profile_id: str = Field(default="deye_hybrid", description="Profile ID: 'deye_hybrid', 'sofar_g3hyd', 'solis_hybrid'")
    host: str = Field(default="192.168.1.150", description="Data logger IP address")
    port: int = Field(default=8899, description="Solarman port")
    slave_id: int = Field(default=1, description="Modbus slave address")
    parameter_name: str = Field(..., description="Parameter name defined in profile, e.g. 'Solar Export Power', 'Work Mode', 'Battery Min SOC'")
    value: Any = Field(..., description="Value to write")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class SungrowShxTelemetryRequest(BaseModel):
    """Request for polling Sungrow SHx/SG inverter & SBR battery telemetry."""

    host: str = Field(default="192.168.1.100", description="Sungrow inverter / WiNet-S LAN IP address")
    port: int = Field(default=502, description="Modbus TCP port (default 502)")
    slave_unit_id: int = Field(default=1, description="Modbus slave unit ID (default 1)")


class SungrowShxCommandRequest(BaseModel):
    """Request for compiling and executing Sungrow SHx configuration command."""

    host: str = Field(default="192.168.1.100", description="Sungrow inverter IP address")
    port: int = Field(default=502, description="Modbus TCP port")
    slave_unit_id: int = Field(default=1, description="Modbus slave unit ID")
    command_type: str = Field(
        ...,
        description="Command type: 'ems_mode', 'forced_charge_discharge', 'soc_limits', 'export_limit', 'active_power_limitation', 'power_switch', 'scene'",
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class DeyeMqttTelemetryRequest(BaseModel):
    """Request for polling and decoding Deye multi-family telemetry."""

    family: str = Field(default="deye_sg04lp3", description="Deye family: 'deye_sg01hp3', 'deye_sg04lp3', 'deye_sg02lp1', 'deye_string', 'deye_micro', 'igen_dtsd422', 'deye_hybrid'")
    logger_sn: str = Field(default="1234567890", description="Deye logger serial number")
    topic_prefix: str = Field(default="deye", description="MQTT base topic prefix")


class DeyeMqttCommandRequest(BaseModel):
    """Request for compiling and executing Deye MQTT configuration command."""

    family: str = Field(default="deye_sg04lp3", description="Deye family")
    logger_sn: str = Field(default="1234567890", description="Deye logger serial number")
    command_type: str = Field(
        ...,
        description="Command type: 'workmode', 'solar_sell', 'solar_sell_max_power', 'active_power_regulation', 'battery_settings', 'timeofuse', 'at_command'",
    )
    params: dict[str, Any] = Field(default_factory=dict, description="Command parameters")
    unlocked: bool = Field(default=False, description="Explicit unlock flag; default False enforces read-only safety gate")


class DeyeMqttAggregateRequest(BaseModel):
    """Request for computing multi-inverter parallel cluster aggregated telemetry."""

    inverters: list[dict[str, Any]] = Field(
        default_factory=list,
        description="List of inverter telemetry items with keys: logger_id, ac_power_w, day_energy_kwh, total_energy_kwh, battery_power_w",
    )


# ---------------------------------------------------------------------------
# Install function
# ---------------------------------------------------------------------------

def install_phase_d_apis(app, controller, user, admin=None):
    """Install Phase D integration API endpoints."""

    # -----------------------------------------------------------------------
    # MPC Controller
    # -----------------------------------------------------------------------

    @app.post("/api/mpc/dispatch")
    async def mpc_dispatch(body: MPCDispatchRequest, principal=Depends(user)):
        """Run MPC dispatch optimization."""
        from .mpc_controller import MPCConfig, MPCController, MPCStep

        config = MPCConfig(
            horizon_steps=body.horizon_steps,
            battery_capacity_kwh=body.battery_capacity_kwh,
            max_charge_kw=body.max_charge_kw,
            max_discharge_kw=body.max_discharge_kw,
        )
        ctrl = MPCController(config)

        step = MPCStep(
            timestamp=datetime.now(timezone.utc),
            soc_init=body.soc_init,
            pv_forecast_kw=body.pv_forecast_kw,
            load_forecast_kw=body.load_forecast_kw,
            price_forecast=body.price_forecast,
        )

        decision = ctrl.step(step)
        return {
            "decision": {
                "p_charge_kw": decision.p_charge_kw,
                "p_discharge_kw": decision.p_discharge_kw,
                "is_charging": decision.is_charging,
                "expected_cost": decision.expected_cost,
                "solve_time_ms": decision.solve_time_ms,
                "fallback_used": decision.fallback_used,
                "soc_next": decision.soc_next,
            },
            "full_plan": decision.full_horizon_plan,
        }

    @app.get("/api/mpc/status")
    async def mpc_status(principal=Depends(user)):
        """Get MPC controller status summary."""
        return {
            "available": True,
            "description": "Model Predictive Control receding-horizon battery dispatch optimizer",
            "features": [
                "Deterministic cost-minimization dispatch",
                "Rule-based fallback on solver failure",
                "Warm-start hint from previous solution",
                "Fleet multi-battery coordination",
                "Feeder import/export constraints",
            ],
        }

    # -----------------------------------------------------------------------
    # Solar PV Model
    # -----------------------------------------------------------------------

    @app.post("/api/solar/estimate")
    async def solar_estimate(body: SolarEstimateRequest, principal=Depends(user)):
        """Estimate daily PV energy production under clear-sky."""
        from .solar_model import PVArrayConfig, estimate_daily_energy

        date_str = body.date
        try:
            date = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(400, "invalid date format, use YYYY-MM-DD")

        array = PVArrayConfig(
            peak_power_kwp=body.peak_power_kwp,
            tilt_deg=body.tilt_deg,
            azimuth_deg=body.azimuth_deg,
            system_loss=body.system_loss,
            inverter_efficiency=body.inverter_efficiency,
        )

        result = estimate_daily_energy(
            array, body.latitude, body.longitude, date,
            altitude_m=body.altitude_m,
            hourly_temperature=body.hourly_temperature,
            hourly_wind=body.hourly_wind,
        )
        return {**result, "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
                "provenance": "CLEAR_SKY_SIMULATION", "weather_forecast_verified": False}

    @app.get("/api/solar/clearsky")
    async def solar_clearsky(
        lat: float = Query(ge=-90, le=90, allow_inf_nan=False),
        lon: float = Query(ge=-180, le=180, allow_inf_nan=False),
        date: str = Query(pattern=r"^\d{4}-\d{2}-\d{2}$"),
        altitude_m: float = Query(ge=0, le=9000, allow_inf_nan=False),
        principal=Depends(user),
    ):
        """Get 24-hour clear-sky GHI profile."""
        from .solar_model import clear_sky_profile_24h

        date_str = date
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        except ValueError:
            raise HTTPException(400, "invalid date format")

        profile = clear_sky_profile_24h(lat, lon, dt, altitude_m)
        return {"profile": profile, "latitude": lat, "longitude": lon, "date": date_str,
                "altitude_m": altitude_m, "provenance": "CLEAR_SKY_SIMULATION",
                "input_source": "USER_SUPPLIED", "dispatch_enabled": False,
                "weather_forecast_verified": False}

    # -----------------------------------------------------------------------
    # Anomaly Detection
    # -----------------------------------------------------------------------

    @app.post("/api/anomaly/check")
    async def anomaly_check(body: AnomalyCheckRequest, principal=Depends(user)):
        """Check telemetry for anomalies."""
        from .anomaly_detection import FleetAnomalyMonitor

        monitor = FleetAnomalyMonitor()
        monitor.register_device(body.device_id, body.rated_power_kw)

        events = monitor.process_telemetry(
            body.device_id,
            datetime.now(timezone.utc),
            body.metrics,
        )

        return {
            "device_id": body.device_id,
            "anomaly_count": len(events),
            "anomalies": [e.to_dict() for e in events],
        }

    @app.get("/api/anomaly/detectors")
    async def anomaly_detectors(principal=Depends(user)):
        """List available anomaly detection methods."""
        return {
            "detectors": [
                {"name": "Z-Score", "type": "statistical",
                 "description": "Flags points >N sigma from mean"},
                {"name": "IQR", "type": "statistical",
                 "description": "Interquartile range outlier detection"},
                {"name": "Moving Average", "type": "statistical",
                 "description": "Rolling mean deviation detector"},
                {"name": "EWMA", "type": "statistical",
                 "description": "EWMA control chart"},
                {"name": "Solar Production", "type": "domain",
                 "description": "PV performance ratio and clipping"},
                {"name": "String Mismatch", "type": "domain",
                 "description": "PV string current imbalance"},
                {"name": "Battery Anomaly", "type": "domain",
                 "description": "Battery V/T/SOC anomaly"},
            ],
        }

    # -----------------------------------------------------------------------
    # Microgrid Controller
    # -----------------------------------------------------------------------

    @app.post("/api/microgrid/simulate")
    async def microgrid_simulate(body: MicrogridCalculation, principal=Depends(user)):
        """Run one microgrid controller simulation step."""
        from .microgrid_controller import (
            InverterMode,
            InverterState,
            LoadPriority,
            MicrogridController,
        )

        ctrl = MicrogridController(**body.parameters.model_dump())
        for inverter in body.inverters:
            values = inverter.model_dump()
            values["mode"] = InverterMode(inverter.mode)
            ctrl.register_inverter(InverterState(**values))
        for load in body.loads:
            ctrl.register_load(LoadPriority(**load.model_dump()))

        result = ctrl.update(
            body.grid_voltage_pu,
            body.grid_frequency_hz,
            body.grid_phase_deg,
            body.dt_seconds,
        )
        return {
            "simulation": result,
            "controller_status": ctrl.status(),
            "dispatch_enabled": False,
            "input_source": "USER_SUPPLIED",
            "provenance": "ADVISORY_SIMULATION",
            "initial_state": "grid_connected",
            "scope": "ONE_STEP_FROM_GRID_CONNECTED",
            "hardware_acknowledgements_verified": False,
        }

    @app.get("/api/microgrid/states")
    async def microgrid_states(principal=Depends(user)):
        """List microgrid operating states."""
        from .microgrid_controller import MicrogridState
        return {
            "states": [
                {"name": s.value, "description": s.value.replace("_", " ").title()}
                for s in MicrogridState
            ],
        }

    # -----------------------------------------------------------------------
    # Modbus Protocol
    # -----------------------------------------------------------------------

    @app.get("/api/modbus/maps")
    async def modbus_maps(principal=Depends(user)):
        """List available Modbus register maps."""
        from .modbus_protocol import get_available_maps
        return {"maps": get_available_maps()}

    @app.get("/api/modbus/maps/{map_key}")
    async def modbus_map_detail(map_key: str, principal=Depends(user)):
        """Get detailed register map for a device profile."""
        from .modbus_protocol import REGISTER_MAP_REGISTRY
        reg_map = REGISTER_MAP_REGISTRY.get(map_key)
        if reg_map is None:
            raise HTTPException(404, f"Register map '{map_key}' not found")

        return {
            "map": reg_map.to_dict(),
            "registers": {
                str(addr): reg.to_dict()
                for addr, reg in sorted(reg_map.registers.items())
            },
        }

    @app.get("/api/modbus/faults/growatt/{code}")
    async def modbus_growatt_fault(code: int, principal=Depends(user)):
        """Decode a Growatt fault code."""
        from .modbus_protocol import decode_growatt_fault
        return decode_growatt_fault(code)

    # -----------------------------------------------------------------------
    # Inverter Models
    # -----------------------------------------------------------------------

    @app.get("/api/inverter/models")
    async def inverter_models_list(principal=Depends(user)):
        """List available inverter simulation models."""
        return {
            "models": [
                {
                    "type": "GridFollowingInverter",
                    "description": "Current-source inverter tracking grid voltage/frequency",
                    "use_case": "Standard PV and battery inverters in grid-connected mode",
                },
                {
                    "type": "GridFormingInverter",
                    "description": "Voltage-source inverter with droop control and virtual inertia",
                    "use_case": "Island mode reference source, microgrid operation",
                },
                {
                    "type": "BatteryInverter",
                    "description": "Bidirectional battery inverter with SOC management",
                    "use_case": "Battery energy storage systems",
                },
            ],
        }

    @app.get("/api/inverter/efficiency-curve")
    async def inverter_efficiency_curve(
        rated_power_kw: float = 10.0,
        peak_efficiency: float = 0.98,
        principal=Depends(user),
    ):
        """Generate inverter efficiency curve data."""
        from .inverter_models import InverterEfficiencyCurve

        curve = InverterEfficiencyCurve(
            rated_power_kw=rated_power_kw,
            peak_efficiency=peak_efficiency,
        )
        return {
            "rated_power_kw": rated_power_kw,
            "peak_efficiency": peak_efficiency,
            "curve": curve.curve_points(20),
        }

    # -----------------------------------------------------------------------
    # Weather Forecast
    # -----------------------------------------------------------------------

    @app.get("/api/weather/forecast")
    async def weather_forecast_api(
        lat: float,
        lon: float,
        days: int = 7,
        principal=Depends(user),
    ):
        """Fetch weather forecast from Open-Meteo."""
        from .weather_forecast import OpenMeteoClient, WeatherFetchError

        client = OpenMeteoClient(timeout_seconds=15)
        try:
            forecast = client.fetch_forecast(lat, lon, days)
            return forecast.to_dict()
        except WeatherFetchError as e:
            raise HTTPException(502, str(e))

    @app.get("/api/weather/pv-forecast")
    async def pv_forecast_api(
        lat: float,
        lon: float,
        peak_kwp: float = 10.0,
        tilt: float = 15.0,
        azimuth: float = 180.0,
        principal=Depends(user),
    ):
        """Get PV production forecast from weather."""
        from .weather_forecast import (
            OpenMeteoClient,
            PVProductionForecaster,
            WeatherFetchError,
        )

        client = OpenMeteoClient(timeout_seconds=15)
        try:
            forecast = client.fetch_forecast(lat, lon, 3)
        except WeatherFetchError as e:
            raise HTTPException(502, str(e))

        pv = PVProductionForecaster(
            peak_power_kwp=peak_kwp,
            tilt_deg=tilt, azimuth_deg=azimuth,
        )
        hourly = pv.forecast_from_weather(forecast)
        summary = pv.daily_summary(hourly)
        return {
            "summary": summary,
            "hourly": hourly[:72],  # 3 days max
        }

    # -----------------------------------------------------------------------
    # Battery Degradation
    # -----------------------------------------------------------------------

    @app.get("/api/battery/degradation")
    async def battery_degradation_api(
        capacity_kwh: float = 10.0,
        chemistry: str = "lfp",
        cycles: int = 500,
        avg_dod: float = 0.6,
        temperature_c: float = 25.0,
        principal=Depends(user),
    ):
        """Estimate battery degradation."""
        from .degradation_models import BatteryHealthEstimator

        estimator = BatteryHealthEstimator(
            capacity_kwh, chemistry,
        )

        soc_trace = []
        for _ in range(cycles):
            lo = 0.5 - avg_dod / 2
            hi = 0.5 + avg_dod / 2
            soc_trace.extend([lo, hi])

        result = estimator.assess(
            soc_trace, dt_hours=1.0,
            temperature_c=temperature_c,
        )
        return result.to_dict()

    # -----------------------------------------------------------------------
    # EV Charger
    # -----------------------------------------------------------------------

    @app.get("/api/ev/charger-modes")
    async def ev_charger_modes(principal=Depends(user)):
        """List available EV charge modes."""
        from .ev_charger import ChargeMode
        return {
            "modes": [
                {"value": m.value, "name": m.name}
                for m in ChargeMode
            ],
        }

    # -----------------------------------------------------------------------
    # VPP Aggregator
    # -----------------------------------------------------------------------

    @app.get("/api/vpp/services")
    async def vpp_services(principal=Depends(user)):
        """List available VPP grid services."""
        from .vpp_aggregator import GridService
        return {
            "services": [
                {"value": s.value, "name": s.name}
                for s in GridService
            ],
        }

    # -----------------------------------------------------------------------
    # Energy Optimizer
    # -----------------------------------------------------------------------

    @app.get("/api/optimizer/modes")
    async def optimizer_modes(principal=Depends(user)):
        """List energy optimization modes."""
        from .energy_optimizer import OptimizationMode
        return {
            "modes": [
                {"value": m.value, "name": m.name}
                for m in OptimizationMode
            ],
        }

    # -----------------------------------------------------------------------
    # Power Quality
    # -----------------------------------------------------------------------

    @app.get("/api/power-quality/event-types")
    async def pq_event_types(principal=Depends(user)):
        """List power quality event types."""
        from .power_quality import PQEventType
        return {
            "event_types": [
                {"value": t.value, "name": t.name}
                for t in PQEventType
            ],
        }

    # -----------------------------------------------------------------------
    # Component Scheduler
    # -----------------------------------------------------------------------

    @app.get("/api/scheduler/component-types")
    async def scheduler_component_types(principal=Depends(user)):
        """List available component types."""
        return {
            "types": [
                {"type": "meter", "description": "Grid meter"},
                {"type": "inverter", "description": "PV inverter"},
                {"type": "battery", "description": "Battery storage"},
                {"type": "controller",
                 "description": "Energy controller"},
            ],
        }

    # -----------------------------------------------------------------------
    # Load Predictor
    # -----------------------------------------------------------------------

    @app.get("/api/load-predictor/models")
    async def load_predictor_models(principal=Depends(user)):
        """List available load prediction model architectures."""
        return {
            "models": [
                {"name": "persistence", "description": "Yesterday repeats today baseline"},
                {"name": "similar_day", "description": "K-nearest historical similar days averaging"},
                {"name": "profile_cluster", "description": "K-means Euclidean load profile clustering"},
                {"name": "ensemble", "description": "Weighted ensemble of multiple predictors"},
                {"name": "temperature_adjusted", "description": "HDD/CDD temperature-adjusted load scaling"},
            ],
        }

    @app.post("/api/load-predictor/predict")
    async def load_predictor_predict(
        payload: Dict[str, Any],
        principal=Depends(user),
    ):
        """Generate 24-hour load prediction."""
        from .load_predictor import (
            EnsemblePredictor,
            LoadProfile,
            PersistencePredictor,
            ProfileClusterPredictor,
            SimilarDayPredictor,
            TemperatureAdjustedPredictor,
        )

        model_type = payload.get("model", "ensemble")
        day_type = payload.get("day_type", "weekday")
        history_raw = payload.get("history", [])
        if not history_raw or any(not h.get("values") for h in history_raw):
            raise HTTPException(422, "observed_load_history_required")

        if model_type == "persistence":
            predictor = PersistencePredictor()
        elif model_type == "similar_day":
            predictor = SimilarDayPredictor(n_similar=int(payload.get("n_similar", 3)))
        elif model_type == "profile_cluster":
            predictor = ProfileClusterPredictor(n_clusters=int(payload.get("n_clusters", 3)))
        elif model_type == "temperature_adjusted":
            predictor = TemperatureAdjustedPredictor()
        else:
            predictor = EnsemblePredictor()

        for h in history_raw:
            vals = h["values"]
            predictor.add_history(LoadProfile(values=vals, day_type=h.get("day_type", "weekday")))

        predictor.train()
        predicted = predictor.predict(day_type=day_type)

        temp_forecast = payload.get("temperature_forecast")
        if temp_forecast and isinstance(predictor, TemperatureAdjustedPredictor):
            predicted = predictor.predict_with_temperature(temp_forecast, day_type=day_type)

        return {
            "model": model_type,
            "day_type": day_type,
            "predicted_hourly_kw": [round(v, 3) for v in predicted],
            "total_predicted_kwh": round(sum(predicted), 2),
            "peak_predicted_kw": round(max(predicted) if predicted else 0, 2),
        }

    # -----------------------------------------------------------------------
    # Tariff Catalogue & Bill Calculation
    # -----------------------------------------------------------------------

    @app.get("/api/tariffs/catalogue")
    async def tariffs_catalogue(principal=Depends(user)):
        """Get pre-built tariff catalogue across multiple countries."""
        from .tariff_catalogue import TARIFF_CATALOGUE
        return {
            "tariffs": {
                k: plan.to_dict()
                for k, plan in TARIFF_CATALOGUE.items()
            }
        }

    @app.post("/api/tariffs/calculate-bill")
    async def calculate_bill(
        payload: CatalogueBillRequest,
        principal=Depends(user),
    ):
        """Calculate bill for given import/export profile and tariff plan."""
        from .tariff_catalogue import TARIFF_CATALOGUE, BillCalculator

        tariff_key = payload.tariff_key
        plan = TARIFF_CATALOGUE.get(tariff_key)
        if not plan:
            raise HTTPException(404, f"Tariff '{tariff_key}' not found in catalogue")

        calc = BillCalculator(plan)
        bill = calc.calculate_daily(payload.import_kwh_hourly, payload.export_kwh_hourly,
                                    peak_demand_kw=payload.peak_demand_kw)
        return {**bill, "status": "ADVISORY_CATALOGUE_ESTIMATE", "tariff_key": tariff_key,
                "effective_version_verified": False, "billing_ready": False,
                "input_source": "USER_SUPPLIED", "dispatch_enabled": False}

    # -----------------------------------------------------------------------
    # Thermal Load Manager
    # -----------------------------------------------------------------------

    @app.post("/api/thermal/heat-pump-cop")
    async def heat_pump_cop(
        payload: HeatPumpCalculation,
        principal=Depends(user),
    ):
        """Calculate Carnot heat pump COP and electrical draw."""
        from .thermal_load_manager import HeatPumpModel

        hp = HeatPumpModel(carnot_efficiency=payload.carnot_efficiency,
                           min_electric_kw=payload.min_electric_kw, max_electric_kw=payload.max_electric_kw)
        power = hp.calculate_power(payload.required_thermal_kw, payload.ambient_temp_c, payload.supply_temp_c)
        return {**power, "status": "ESTIMATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
                "assumptions": ["Carnot approximation", "COP bounded to 1.5–6.5"]}

    @app.post("/api/thermal/sg-ready-evaluate")
    async def sg_ready_evaluate(
        payload: SGCalculation,
        principal=Depends(user),
    ):
        """Evaluate SG-Ready 4-state heat pump state based on PV surplus."""
        from .thermal_load_manager import SGReadyController, ThermalStorageTank

        ctrl = SGReadyController(
            surplus_threshold_kw=payload.surplus_threshold_kw,
            forced_surplus_kw=payload.forced_surplus_kw,
        )
        tank = ThermalStorageTank(
            current_temp_c=payload.tank_temp_c, min_temp_c=payload.min_temp_c,
            normal_setpoint_c=payload.normal_setpoint_c, boost_setpoint_c=payload.boost_setpoint_c,
        )
        res = ctrl.evaluate(payload.pv_surplus_kw, payload.grid_price, tank,
                            is_grid_peak_lock=payload.is_grid_peak_lock)
        return {**res, "status": "ESTIMATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
                "assumptions": ["stateless recommendation; no anti-cycling or relay execution"]}

    # -----------------------------------------------------------------------
    # Phase Balancer
    # -----------------------------------------------------------------------

    @app.post("/api/phase-balancer/dispatch")
    async def phase_balancer_dispatch(
        payload: PhaseDispatchRequest,
        principal=Depends(user),
    ):
        """Compute independent per-phase active and reactive power dispatch setpoints."""
        from .phase_balancer import (
            AsymmetricPhaseBalancer,
            InverterPhaseLimits,
            PhaseMeasurement,
            PhaseUnbalanceEvaluator,
        )

        meas = PhaseMeasurement(**payload.measurement.model_dump())
        unbalance = PhaseUnbalanceEvaluator.evaluate(meas)

        limits = InverterPhaseLimits(**payload.limits.model_dump())
        balancer = AsymmetricPhaseBalancer(limits)
        dispatch = balancer.calculate_dispatch(meas)

        return {
            "status": "ESTIMATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
            "assumptions": ["120_degree_phase_displacement", "not_a_compliance_assessment"],
            "unbalance_metrics": unbalance,
            "dispatch_setpoints": dispatch,
        }

    # -----------------------------------------------------------------------
    # Predbat Dispatch Planner
    # -----------------------------------------------------------------------

    @app.post("/api/predbat/plan")
    async def predbat_plan(
        payload: PredbatCalculation,
        principal=Depends(user),
    ):
        """Generate 24-48h predictive battery dispatch schedule."""
        from .predbat_planner import BatterySpecs, PredbatPlanner

        specs = BatterySpecs(**{key: getattr(payload, key) for key in BatterySpecs.__dataclass_fields__})
        planner = PredbatPlanner(specs)

        solar = payload.solar_forecast_hourly
        load = payload.load_forecast_hourly
        imp_tariffs = payload.import_tariffs_hourly
        exp_tariffs = payload.export_tariffs_hourly
        soc = payload.current_soc_pct

        plan = planner.plan_horizon(
            solar_forecast_hourly=solar,
            load_forecast_hourly=load,
            import_tariffs_hourly=imp_tariffs,
            export_tariffs_hourly=exp_tariffs,
            current_soc_pct=soc,
            enable_arbitrage=payload.enable_arbitrage,
        )
        return {**plan, "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
                "provenance": "ADVISORY_SIMULATION", "currency": payload.currency,
                "tariff_source": payload.tariff_source}

    # -----------------------------------------------------------------------
    # Vendor Device Translator
    # -----------------------------------------------------------------------

    @app.post("/api/vendor-translator/translate-command")
    async def vendor_translate_command(
        payload: Dict[str, Any],
        principal=Depends(user),
    ):
        """Translate high-level EMS dispatch command to vendor-specific Modbus registers."""
        from .vendor_device_translator import StandardWorkMode, VendorDeviceTranslator

        vendor = payload.get("vendor", "sungrow")
        slave_id = int(payload.get("slave_id", 1))
        mode_str = payload.get("work_mode", "self_consumption")
        power_w = payload.get("power_w")
        export_limit_w = payload.get("export_limit_w")

        try:
            mode = StandardWorkMode(mode_str)
        except ValueError:
            raise HTTPException(400, f"Invalid work mode: {mode_str}")

        try:
            requests = VendorDeviceTranslator.translate_command(
                vendor=vendor,
                slave_id=slave_id,
                work_mode=mode,
                power_w=power_w,
                export_limit_w=export_limit_w,
            )
            return {
                "vendor": vendor,
                "slave_id": slave_id,
                "modbus_requests": [r.to_dict() for r in requests],
            }
        except ValueError as e:
            raise HTTPException(400, str(e))

    # -----------------------------------------------------------------------
    # Grid Code Regulator
    # -----------------------------------------------------------------------

    @app.post("/api/grid-code/evaluate")
    async def grid_code_evaluate(
        payload: GridCalculation,
        principal=Depends(user),
    ):
        """Evaluate grid-code compliance (Volt-Watt, Volt-Var, Freq-Watt, Anti-Islanding)."""
        from .grid_code_regulator import (
            FreqWattDroop,
            GridCodeRegulator,
            ProtectionRelayLimits,
            VoltVarCurve,
            VoltWattCurve,
        )

        regulator = GridCodeRegulator(
            VoltWattCurve(**payload.volt_watt.model_dump()), VoltVarCurve(**payload.volt_var.model_dump()),
            FreqWattDroop(**payload.freq_watt.model_dump()), ProtectionRelayLimits(**payload.protection.model_dump()))
        res = regulator.evaluate(payload.voltage_v, payload.frequency_hz, payload.current_power_kw)
        return {**res, "status": "ESTIMATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
                "compliance_verified": False, "anti_islanding_verified": False}

    # -----------------------------------------------------------------------
    # Smart Meter Driver
    # -----------------------------------------------------------------------

    @app.get("/api/meters/supported-models")
    async def meter_supported_models(principal=Depends(user)):
        """List supported industrial 3-phase meter models."""
        from .smart_meter_driver import MeterModel
        return {
            "models": [
                {"name": m.name, "value": m.value}
                for m in MeterModel
            ]
        }

    @app.post("/api/meters/decode-registers")
    async def meter_decode_registers(
        payload: Dict[str, Any],
        principal=Depends(user),
    ):
        """Decode raw 3-phase smart meter register dictionary."""
        from .smart_meter_driver import MeterModel, SmartMeterDriver

        model_str = payload.get("model", "eastron_sdm630")
        slave_id = int(payload.get("slave_id", 1))
        reg_raw = payload.get("registers", {})
        # Convert string keys to int addresses
        registers = {int(k): int(v) for k, v in reg_raw.items()}

        try:
            model = MeterModel(model_str)
        except ValueError:
            raise HTTPException(400, f"Unsupported meter model: {model_str}")

        telemetry = SmartMeterDriver.decode(model, slave_id, registers)
        return telemetry.to_dict()

    # -----------------------------------------------------------------------
    # EV Fleet Coordinator (Dynamic Load Management)
    # -----------------------------------------------------------------------

    @app.post("/api/ev-fleet/optimize-dlm")
    async def ev_fleet_optimize_dlm(
        payload: EVFleetRequest,
        principal=Depends(user),
    ):
        """Optimize dynamic load management across fleet of EV chargers."""
        from .ev_fleet_coordinator import ChargePhaseMode, ChargingMode, EVFleetCoordinator, Loadpoint

        # Advisory input check only: timestamps are user declarations, not
        # authenticated telemetry or a commissioned control freshness policy.
        now = datetime.now(timezone.utc)
        observations = {"site": payload.observed_at}
        observations.update({f"charger:{ch.id}": ch.observed_at for ch in payload.chargers})
        ages = {}
        for key, observed_at in observations.items():
            if observed_at is None:
                ages[key] = None
                continue
            age = (now - observed_at).total_seconds()
            if age < 0 or age > 300:
                raise HTTPException(422, f"ev_observation_outside_advisory_window:{key}")
            ages[key] = round(age, 3)

        coord = EVFleetCoordinator(site_breaker_limit_kw=payload.site_breaker_limit_kw,
                                   enable_1p3p_switching=False)

        chargers_data = payload.chargers
        for ch in chargers_data:
            lp = Loadpoint(
                charger_id=ch.id, name=ch.name, connected_vehicle_id=ch.vehicle_id,
                vehicle_soc_pct=ch.soc_pct, target_soc_pct=ch.target_soc_pct,
                mode=ChargingMode(ch.mode), priority=ch.priority,
                min_current_amps=ch.min_current_amps, max_current_amps=ch.max_current_amps,
                voltage_per_phase_v=ch.voltage_per_phase_v, allocated_phases=ChargePhaseMode(ch.phases),
            )
            coord.add_loadpoint(lp)

        surplus = payload.available_solar_surplus_kw
        base_load = payload.building_base_load_kw

        allocation = coord.update(surplus, base_load)
        return {**allocation, "status": "ESTIMATED", "dispatch_enabled": False,
                "input_source": "USER_SUPPLIED", "phase_switching_enabled": False,
                "freshness": {"status": "UNKNOWN" if None in ages.values() else "USER_REPORTED_RECENT",
                              "age_seconds": ages, "max_age_seconds": 300,
                              "evaluated_at": now.isoformat(), "telemetry_verified": False}}

    # -----------------------------------------------------------------------
    # Wholesale Market Trader & FCR
    # -----------------------------------------------------------------------

    @app.post("/api/market-trader/submit-and-clear")
    async def market_submit_and_clear(
        payload: MarketCalculationRequest,
        principal=Depends(user),
    ):
        """Submit wholesale energy market bids and simulate auction clearing."""
        from .market_trader import MarketTrader, MarketType, OrderDirection

        trader = MarketTrader(fleet_capacity_mw=payload.fleet_capacity_mw)
        bids_data = payload.bids

        for b in bids_data:
            trader.submit_bid(
                bid_id=b.id, market=MarketType(b.market), direction=OrderDirection(b.direction),
                delivery_hour=b.delivery_hour, quantity_mw=b.quantity_mw,
                price_eur_per_mwh=b.price_eur_per_mwh,
            )

        clearing_prices = payload.clearing_prices

        result = trader.simulate_auction_clearing(clearing_prices)
        return {**result, "status": "ESTIMATED", "submitted_to_market": False,
                "input_source": "USER_SUPPLIED"}

    @app.get("/api/market-trader/fcr-response")
    async def market_fcr_response(
        frequency_hz: float = 50.05,
        committed_mw: float = 2.0,
        principal=Depends(user),
    ):
        """Compute Frequency Containment Reserve (FCR) primary regulation response."""
        from .market_trader import FCRController, FCRSpecification

        spec = FCRSpecification(committed_capacity_mw=committed_mw)
        ctrl = FCRController(spec)
        res = ctrl.calculate_response(frequency_hz)
        return res

    # -----------------------------------------------------------------------
    # Genset Emergency Dispatch & Black-Start Sequence
    # -----------------------------------------------------------------------

    @app.post("/api/genset/evaluate-dispatch")
    async def genset_evaluate_dispatch(
        payload: GeneratorCalculation,
        principal=Depends(user),
    ):
        """Evaluate diesel/gas genset dispatch, loading sweet-spot, and fuel burn."""
        from .genset_controller import GeneratorController, GeneratorSpecs, GeneratorState

        specs = GeneratorSpecs(**payload.specs.model_dump())
        ctrl = GeneratorController(specs)
        ctrl._transition_to(GeneratorState(payload.initial_state))
        ctrl._elapsed_in_state_seconds = payload.elapsed_in_state_seconds
        ctrl._cumulative_run_seconds = payload.cumulative_run_seconds

        result = ctrl.step(
            dt_seconds=payload.dt_seconds,
            microgrid_load_kw=payload.microgrid_load_kw,
            battery_soc_pct=payload.battery_soc_pct,
            battery_max_charge_kw=payload.battery_max_charge_kw,
            battery_max_discharge_kw=payload.battery_max_discharge_kw,
            is_grid_available=payload.is_grid_available,
        )
        return {
            "status": "ESTIMATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
            "fuel_accounting": "current_calculation_only",
            "genset_specs": {
                "rated_power_kw": specs.rated_power_kw,
                "min_power_kw": specs.min_power_kw,
                "optimal_power_kw": specs.optimal_power_kw,
                "max_power_kw": specs.max_power_kw,
            },
            "dispatch": result,
        }

    @app.post("/api/genset/black-start-sequence")
    async def genset_black_start_sequence(
        payload: BlackStartCalculation,
        principal=Depends(user),
    ):
        """Step through multi-stage black-start microgrid restoration sequence."""
        from .genset_controller import BlackStartOrchestrator, GeneratorController, GeneratorSpecs

        specs = GeneratorSpecs(**payload.specs.model_dump())
        ctrl = GeneratorController(specs)
        orchestrator = BlackStartOrchestrator(ctrl)

        res = {}
        for observation in payload.observations:
            res = orchestrator.execute_next_stage(**observation.model_dump())

        return {**res, "status": "SIMULATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
                "assumptions": ["scenario starts idle", "start/synchronization acknowledgements are not verified"]}

    # -----------------------------------------------------------------------
    # Thermal Building Envelope Simulation (2R2C Model)
    # -----------------------------------------------------------------------

    @app.post("/api/thermal/building-simulation")
    async def thermal_building_simulation(
        payload: BuildingSimulationRequest,
        principal=Depends(user),
    ):
        """Simulate building 2R2C lumped envelope thermal response."""
        from .thermal_load_manager import BuildingThermalModel

        indoor_init = payload.building.indoor_temp_c
        wall_init = payload.building.wall_temp_c
        model = BuildingThermalModel(**payload.building.model_dump())

        outdoor_temps = payload.outdoor_temps_hourly
        heating_kw = payload.heating_thermal_kw
        solar_ghi = payload.solar_ghi_hourly

        sim_hours = []
        for i, out_t in enumerate(outdoor_temps):
            ghi = solar_ghi[i]
            step = model.simulate_hour(
                heating_cooling_thermal_kw=heating_kw,
                outdoor_temp_c=out_t,
                solar_irradiance_w_m2=ghi,
            )
            step["hour"] = i
            sim_hours.append(step)

        return {
            "status": "ESTIMATED", "dispatch_enabled": False, "input_source": "USER_SUPPLIED",
            "initial_state": {"indoor_temp_c": indoor_init, "wall_temp_c": wall_init},
            "hourly_simulation": sim_hours,
            "final_state": {
                "indoor_temp_c": model.indoor_temp_c,
                "wall_temp_c": model.wall_temp_c,
            },
        }

    # -----------------------------------------------------------------------
    # Supported Brands for Modbus Command Translation
    # -----------------------------------------------------------------------

    @app.get("/api/vendor-translator/supported-brands")
    async def vendor_translator_supported_brands(principal=Depends(user)):
        """List all 30 supported inverter and battery brands for Modbus packet translation."""
        from .vendor_device_translator import StandardWorkMode

        brands = [
            {"id": "goodwe", "name": "GoodWe", "protocol": "Modbus RTU/TCP", "registers": "FC06/FC16", "native_modes": ["General", "Backup", "Off-grid", "Peak shaving"]},
            {"id": "sungrow", "name": "Sungrow", "protocol": "Modbus TCP/RTU", "registers": "FC16 holding", "native_modes": ["Self-consumption", "Forced charge", "Backup"]},
            {"id": "deye", "name": "Deye", "protocol": "Modbus RTU", "registers": "FC16 holding", "native_modes": ["Selling first", "Zero export to load", "Batt first"]},
            {"id": "huawei", "name": "Huawei FusionSolar", "protocol": "Modbus TCP", "registers": "FC06/FC16", "native_modes": ["Maximise self-consumption", "TOU", "Feed-in priority"]},
            {"id": "solis", "name": "Solis", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["Self use", "Feed in priority", "Off grid"]},
            {"id": "growatt", "name": "Growatt", "protocol": "Modbus RTU/TCP", "registers": "FC06 holding", "native_modes": ["Load first", "Battery first", "Grid first"]},
            {"id": "victron", "name": "Victron Energy", "protocol": "Modbus TCP", "registers": "FC06/FC16", "native_modes": ["ESS Optimized", "Keep charged", "External control"]},
            {"id": "fronius", "name": "Fronius", "protocol": "SunSpec Modbus TCP", "registers": "FC16 holding", "native_modes": ["Dynamic power reduction", "WMaxLimPct"]},
            {"id": "solaredge", "name": "SolarEdge", "protocol": "SunSpec Modbus TCP", "registers": "FC16 holding", "native_modes": ["Maximize self-consumption", "Backup only"]},
            {"id": "sma", "name": "SMA Solar", "protocol": "Modbus TCP Speedwire", "registers": "FC16 holding", "native_modes": ["Active power limitation", "Zero export"]},
            {"id": "sofar", "name": "Sofar Solar", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["Self-use", "Time of use", "Timing mode"]},
            {"id": "solax", "name": "SolaX Power", "protocol": "Modbus RTU/TCP", "registers": "FC06 holding", "native_modes": ["Self use", "Feedin priority", "Backup mode"]},
            {"id": "alphaess", "name": "AlphaESS", "protocol": "Modbus RTU/TCP", "registers": "FC06 holding", "native_modes": ["Economic", "UPS", "Self-consumption"]},
            {"id": "enphase", "name": "Enphase IQ Gateway", "protocol": "REST API / Envoy", "registers": "Production limit", "native_modes": ["Self-consumption", "Savings", "Full backup"]},
            {"id": "foxess", "name": "FoxESS", "protocol": "Modbus RTU/TCP", "registers": "FC06 holding", "native_modes": ["Self-use", "Feed-in", "Back-up"]},
            {"id": "givenergy", "name": "GivEnergy", "protocol": "Modbus TCP", "registers": "FC06/FC16", "native_modes": ["Eco", "Timed charge", "Timed discharge"]},
            {"id": "hoymiles", "name": "Hoymiles", "protocol": "Modbus RTU (DTU-Pro)", "registers": "FC06/FC16", "native_modes": ["Power limit percent", "Zero export"]},
            {"id": "sigenergy", "name": "Sigenergy (SigenStor)", "protocol": "Modbus TCP", "registers": "FC16 holding", "native_modes": ["AI Mode", "Self-consumption", "TOU"]},
            {"id": "pylontech", "name": "Pylontech", "protocol": "CAN / RS485 Modbus", "registers": "FC03/FC06", "native_modes": ["BMS charge/discharge voltage & current limits"]},
            {"id": "byd", "name": "BYD Battery-Box", "protocol": "CAN / Modbus TCP", "registers": "FC03/FC16", "native_modes": ["BMS communication, SOC, cell temp"]},
            {"id": "kaco", "name": "Kaco new energy", "protocol": "SunSpec Modbus TCP", "registers": "FC16 holding", "native_modes": ["Active power curtailment"]},
            {"id": "kostal", "name": "Kostal Solar", "protocol": "SunSpec / Modbus TCP", "registers": "FC16 holding", "native_modes": ["Dynamic export limitation"]},
            {"id": "srne", "name": "SRNE Solar", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["Solar first", "Utility first", "Battery first"]},
            {"id": "must", "name": "Must Solar", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["SOL", "UTI", "SBU priority"]},
            {"id": "smg", "name": "Anenji / SMG", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["SOL priority", "Utility priority"]},
            {"id": "afore", "name": "Afore New Energy", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["Self-consumption", "Zero export"]},
            {"id": "kstar", "name": "Kstar New Energy", "protocol": "Modbus RTU/TCP", "registers": "FC06 holding", "native_modes": ["Self consumption", "Peak shaving"]},
            {"id": "tsun", "name": "TSUN ESS", "protocol": "Modbus RTU", "registers": "FC06 holding", "native_modes": ["Power limit %"]},
            {"id": "megarevo", "name": "Megarevo", "protocol": "Modbus RTU", "registers": "FC16 holding", "native_modes": ["Peak shaving", "Self consumption", "Off-grid"]},
            {"id": "tesla", "name": "Tesla Powerwall", "protocol": "SunSpec / Modbus TCP", "registers": "FC06 holding", "native_modes": ["Self-consumption", "Peak-shaving", "Backup-only"]},
        ]
        return {
            "total_brands": len(brands),
            "brands": brands,
            "supported_modes": [m.value for m in StandardWorkMode],
        }

    # -----------------------------------------------------------------------
    # Community Inverter Modbus Register Maps & Polling Optimizer
    # Provenance: solar-inverter-modbus-registers-main (MIT, Daniel Szlaski)
    # -----------------------------------------------------------------------

    @app.get("/api/community-inverters/profiles")
    async def community_inverters_list_profiles(principal=Depends(user)):
        """List all 10 verified community inverter profiles with register counts and polling specs."""
        from .community_registers_engine import CommunityRegistersEngine

        profiles = CommunityRegistersEngine.list_profiles()
        return {
            "total_profiles": len(profiles),
            "source": "solar-inverter-modbus-registers (MIT, Daniel Szlaski)",
            "profiles": profiles,
        }

    @app.get("/api/community-inverters/profile/{model_id}")
    async def community_inverters_get_profile(model_id: str, principal=Depends(user)):
        """Get complete register map, polling config, and alarm bitmask for a model."""
        from .community_registers_engine import CommunityRegistersEngine

        profile = CommunityRegistersEngine.get_profile(model_id)
        if not profile:
            raise HTTPException(status_code=404, detail=f"Profile not found: {model_id}")
        return {
            "model_id": model_id,
            "source": "solar-inverter-modbus-registers (MIT, Daniel Szlaski)",
            "profile": profile,
        }

    @app.post("/api/community-inverters/optimize-polling")
    async def community_inverters_optimize_polling(req: OptimizePollingRequest, principal=Depends(user)):
        """Calculate optimal batched Modbus read blocks with gap tolerance."""
        from .community_registers_engine import CommunityRegistersEngine

        result = CommunityRegistersEngine.optimize_polling_blocks(
            model_id=req.model_id,
            requested_field_ids=req.requested_field_ids,
            enable_gap_tolerance=req.enable_gap_tolerance,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message", "Optimization failed"))
        return result

    @app.post("/api/community-inverters/decode-telemetry")
    async def community_inverters_decode_telemetry(req: DecodeTelemetryRequest, principal=Depends(user)):
        """Decode raw 16-bit registers into scaled engineering metrics."""
        from .community_registers_engine import CommunityRegistersEngine

        result = CommunityRegistersEngine.decode_telemetry(
            model_id=req.model_id,
            registers=req.registers,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message", "Decode failed"))
        return result

    @app.post("/api/community-inverters/decode-alarms")
    async def community_inverters_decode_alarms(req: DecodeAlarmsRequest, principal=Depends(user)):
        """Decode multi-word alarm bitfields into structured alarms and actionable SOPs."""
        from .community_registers_engine import CommunityRegistersEngine

        result = CommunityRegistersEngine.decode_alarm_bitfield(
            model_id=req.model_id,
            registers=req.registers,
        )
        if result.get("status") == "error":
            raise HTTPException(status_code=404, detail=result.get("message", "Alarm decode failed"))
        return result

    # -----------------------------------------------------------------------
    # Solis Modbus-to-MQTT Bridge & Home Assistant Auto-Discovery
    # Provenance: solis2mqtt-main (GPL-3.0, incub77)
    # -----------------------------------------------------------------------

    @app.get("/api/solis-mqtt/registers")
    async def solis_mqtt_list_registers(principal=Depends(user)):
        """List all Ginlong Solis Modbus registers and Home Assistant entity specifications."""
        from .solis_mqtt_bridge import SolisMqttBridgeEngine

        registers = SolisMqttBridgeEngine.list_registers()
        return {
            "source": "solis2mqtt-main (independent clean-room implementation)",
            "total_registers": len(registers),
            "registers": registers,
        }

    @app.post("/api/solis-mqtt/discovery-topics")
    async def solis_mqtt_generate_discovery(req: SolisDiscoveryRequest, principal=Depends(user)):
        """Generate Home Assistant MQTT Auto-Discovery topics and JSON configs."""
        from .solis_mqtt_bridge import SolisMqttBridgeEngine

        topics = SolisMqttBridgeEngine.get_discovery_configs(
            device_name=req.device_name,
            device_model=req.device_model,
            base_topic=req.base_topic,
            discovery_prefix=req.discovery_prefix,
        )
        return {
            "total_entities": len(topics),
            "discovery_prefix": req.discovery_prefix,
            "base_topic": req.base_topic,
            "discovery_configs": topics,
        }

    @app.post("/api/solis-mqtt/decode-telemetry")
    async def solis_mqtt_decode_telemetry(req: SolisDecodeTelemetryRequest, principal=Depends(user)):
        """Decode raw Modbus registers into engineering telemetry and MQTT messages."""
        from .solis_mqtt_bridge import SolisMqttBridgeEngine

        # Keys in json might come as strings e.g. "3004" -> cast to int
        parsed_regs = {int(k): int(v) for k, v in req.registers.items()}
        return SolisMqttBridgeEngine.decode_telemetry(
            registers_map=parsed_regs,
            base_topic=req.base_topic,
        )

    @app.post("/api/solis-mqtt/simulate-offline")
    async def solis_mqtt_simulate_offline(req: SolisOfflineSanitizeRequest, principal=Depends(user)):
        """Simulate night-time offline sanitization (measurement zeroing + energy retention)."""
        from .solis_mqtt_bridge import SolisMqttBridgeEngine

        return SolisMqttBridgeEngine.simulate_offline(
            last_known_metrics=req.last_known_metrics,
            base_topic=req.base_topic,
        )

    @app.post("/api/solis-mqtt/compile-control")
    async def solis_mqtt_compile_control(req: SolisCompileControlRequest, principal=Depends(user)):
        """Compile FC06 Modbus write frame with Solar Fleet safety gating."""
        from .solis_mqtt_bridge import SolisMqttBridgeEngine

        try:
            return SolisMqttBridgeEngine.compile_control(
                metric=req.metric,
                value=req.value,
                slave_address=req.slave_address,
                bypass_safety=req.bypass_safety,
            )
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # -----------------------------------------------------------------------
    # GoodWe SEMS Portal Cloud Integration
    # Provenance: pygoodwe-main (MIT, James Hodgkinson)
    # -----------------------------------------------------------------------

    @app.post("/api/goodwe-sems/login")
    async def goodwe_sems_login(req: GoodWeLoginRequest, principal=Depends(user)):
        raise HTTPException(409, "use_registered_account_authentication; no_standalone_session")

    @app.post("/api/goodwe-sems/station-detail")
    async def goodwe_sems_station_detail(req: GoodWeStationDetailRequest, principal=Depends(user)):
        """Parse or simulate GoodWe SEMS station real-time monitoring details."""
        from .goodwe_sems_client import GoodWeSEMSClient

        if not req.simulated_raw_data:
            raise HTTPException(422, "provider_payload_required; use_registered_account_sync")
        raw_data = req.simulated_raw_data

        parsed = GoodWeSEMSClient.parse_station_detail(raw_data, system_id=req.station_id)
        normalized = GoodWeSEMSClient.normalize_to_fleet_telemetry(parsed)

        return {
            "source": "pygoodwe-main (MIT, James Hodgkinson)",
            "station_detail": parsed.to_dict(),
            "normalized_fleet_telemetry": normalized,
        }

    @app.post("/api/goodwe-sems/monthly-report")
    async def goodwe_sems_monthly_report(req: GoodWeMonthlyReportRequest, principal=Depends(user)):
        """Parse or simulate GoodWe SEMS monthly generation report."""
        from .goodwe_sems_client import GoodWeSEMSClient

        if not req.simulated_raw_data:
            raise HTTPException(422, "provider_payload_required; use_registered_account_sync")
        raw_data = req.simulated_raw_data

        return GoodWeSEMSClient.parse_monthly_report(raw_data)

    # -----------------------------------------------------------------------
    # Growatt SPH Hybrid Modbus & TOU Scheduling
    # Provenance: growatt_modbus-main (GPL-3.0)
    # -----------------------------------------------------------------------

    @app.post("/api/growatt-sph/decode-bms")
    async def growatt_sph_decode_bms(req: GrowattDecodeBMSRequest, principal=Depends(user)):
        """Decode Growatt SPH BMS pack gauge registers (1083..1097)."""
        from .growatt_sph_modbus import GrowattSPHEngine

        parsed_regs = {int(k): int(v) for k, v in req.registers.items()}
        gauge = GrowattSPHEngine.decode_bms_gauge(parsed_regs)
        if not gauge:
            raise HTTPException(status_code=400, detail="Registers 1087 or 1088 missing from payload")
        return {
            "source": "growatt_modbus-main (GPL-3.0 clean-room independent)",
            "bms_gauge": gauge.to_dict(),
        }

    @app.post("/api/growatt-sph/decode-cells")
    async def growatt_sph_decode_cells(req: GrowattDecodeCellsRequest, principal=Depends(user)):
        """Decode Growatt SPH 12-cell individual voltages & cell envelope (1108..1123)."""
        from .growatt_sph_modbus import GrowattSPHEngine

        parsed_regs = {int(k): int(v) for k, v in req.registers.items()}
        telemetry = GrowattSPHEngine.decode_cell_telemetry(parsed_regs)
        if not telemetry:
            raise HTTPException(status_code=400, detail="Registers 1108 or 1109 missing from payload")
        return {
            "source": "growatt_modbus-main (GPL-3.0 clean-room independent)",
            "cell_telemetry": telemetry.to_dict(),
        }

    @app.post("/api/growatt-sph/decode-tou-slots")
    async def growatt_sph_decode_tou_slots(req: GrowattDecodeSlotsRequest, principal=Depends(user)):
        """Decode all 12 Time-Of-Use slots (6 Battery First + 6 Grid First)."""
        from .growatt_sph_modbus import GrowattSPHEngine

        parsed_regs = {int(k): int(v) for k, v in req.holding_registers.items()}
        return GrowattSPHEngine.decode_tou_slots(parsed_regs)

    @app.post("/api/growatt-sph/compile-mode-command")
    async def growatt_sph_compile_mode_command(req: GrowattCompileModeRequest, principal=Depends(user)):
        """Compile Modbus FC06 or FC16 frames for Growatt SPH priority mode switching."""
        from .growatt_sph_modbus import GrowattSPHEngine

        mode_clean = req.mode.lower().strip()
        try:
            if mode_clean in ("load_first", "self_consumption"):
                cmds = GrowattSPHEngine.compile_load_first_mode(
                    slave_id=req.slave_id,
                    bypass_safety=req.bypass_safety,
                )
            elif mode_clean in ("battery_first", "ac_charge"):
                cmds = GrowattSPHEngine.compile_battery_first_slot(
                    slot_number=req.slot_number,
                    start_time=req.start_time,
                    end_time=req.end_time,
                    charge_rate_pct=req.rate_pct,
                    stop_soc_pct=req.stop_soc_pct,
                    slave_id=req.slave_id,
                    bypass_safety=req.bypass_safety,
                )
            elif mode_clean in ("grid_first", "forced_export"):
                cmds = GrowattSPHEngine.compile_grid_first_slot(
                    slot_number=req.slot_number,
                    start_time=req.start_time,
                    end_time=req.end_time,
                    discharge_rate_pct=req.rate_pct,
                    stop_soc_floor_pct=req.stop_soc_pct,
                    slave_id=req.slave_id,
                    bypass_safety=req.bypass_safety,
                )
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported mode '{req.mode}'. Expected 'load_first', 'battery_first', or 'grid_first'")

            return {
                "mode": mode_clean,
                "total_commands": len(cmds),
                "commands": [c.to_dict() for c in cmds],
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # -----------------------------------------------------------------------
    # Solis Hybrid S6 / RHI Storage & TOU Scheduling
    # Provenance: solis-modbus-ha-main (MIT)
    # -----------------------------------------------------------------------

    @app.post("/api/solis-hybrid/decode-storage-mode")
    async def solis_hybrid_decode_storage_mode(req: SolisDecodeStorageModeRequest, principal=Depends(user)):
        """Decode Solis Hybrid storage control mode register (43110)."""
        from .solis_hybrid_controller import decode_storage_mode

        return {
            "source": "solis-modbus-ha-main (MIT clean-room independent)",
            "storage_mode": decode_storage_mode(req.value),
        }

    @app.post("/api/solis-hybrid/compile-grid-charge")
    async def solis_hybrid_compile_grid_charge(req: SolisCompileGridChargeRequest, principal=Depends(user)):
        """Compile Modbus FC06 frame to toggle Grid Charge Allowed (BIT05 of 43110)."""
        from .solis_hybrid_controller import SolisHybridDispatchEngine

        engine = SolisHybridDispatchEngine()
        cmd = engine.compile_grid_charge_toggle(req.current_mode_value, req.enable_grid_charge)
        return {
            "source": "solis-modbus-ha-main (MIT clean-room independent)",
            "command": cmd.to_dict(),
        }

    @app.post("/api/solis-hybrid/compile-tou-slot")
    async def solis_hybrid_compile_tou_slot(req: SolisCompileTouSlotRequest, principal=Depends(user)):
        """Compile Modbus FC16 frame to program a 7-register TOU schedule slot."""
        from .solis_hybrid_controller import SolisHybridDispatchEngine

        engine = SolisHybridDispatchEngine()
        cmd = engine.compile_tou_slot_update(
            slot_type=req.slot_type,
            slot_index=req.slot_index,
            target_soc=req.target_soc,
            current_a=req.current_a,
            start_hour=req.start_hour,
            start_minute=req.start_minute,
            end_hour=req.end_hour,
            end_minute=req.end_minute,
            field2=req.field2,
        )
        return {
            "source": "solis-modbus-ha-main (MIT clean-room independent)",
            "command": cmd.to_dict(),
        }

    @app.post("/api/solis-hybrid/compile-dispatch")
    async def solis_hybrid_compile_dispatch(req: SolisCompileDispatchRequest, principal=Depends(user)):
        """Compile uniform GreenGrid/EMS dynamic dispatch with software watchdog TTL."""
        from .solis_hybrid_controller import SolisHybridDispatchEngine

        engine = SolisHybridDispatchEngine()
        cmd = engine.compile_dispatch(
            mode=req.mode,
            power_w=req.power_w,
            ttl_seconds=req.ttl_seconds,
            battery_voltage=req.battery_voltage,
            current_storage_mode=req.current_storage_mode,
            target_soc=req.target_soc,
        )
        return {
            "source": "solis-modbus-ha-main (MIT clean-room independent)",
            "command": cmd.to_dict(),
        }

    @app.post("/api/solis-hybrid/decode-tou-slots")
    async def solis_hybrid_decode_tou_slots(req: SolisDecodeTouSlotsRequest, principal=Depends(user)):
        """Decode raw holding registers into all 12 Solis Hybrid TOU slots."""
        from dataclasses import asdict

        from .solis_hybrid_controller import (
            REG_CHARGE_SLOT_BASE,
            REG_DISCHARGE_SLOT_BASE,
            TOU_SLOT_LENGTH,
            decode_tou_slot,
        )

        parsed_regs = {int(k): int(v) for k, v in req.registers.items()}
        charge_slots = []
        discharge_slots = []

        for i in range(6):
            base_ch = REG_CHARGE_SLOT_BASE + (i * TOU_SLOT_LENGTH)
            regs_ch = [parsed_regs.get(base_ch + j, 0) for j in range(TOU_SLOT_LENGTH)]
            slot_ch = decode_tou_slot(regs_ch, "charge", i)
            charge_slots.append(asdict(slot_ch))

            base_dis = REG_DISCHARGE_SLOT_BASE + (i * TOU_SLOT_LENGTH)
            regs_dis = [parsed_regs.get(base_dis + j, 0) for j in range(TOU_SLOT_LENGTH)]
            slot_dis = decode_tou_slot(regs_dis, "discharge", i)
            discharge_slots.append(asdict(slot_dis))

        return {
            "source": "solis-modbus-ha-main (MIT clean-room independent)",
            "charge_slots": charge_slots,
            "discharge_slots": discharge_slots,
        }

    # -----------------------------------------------------------------------
    # Deye Three-Phase Low-Voltage Hybrid Modbus & TOU Scheduling
    # Provenance: deye-modbus-ha-main (MIT)
    # -----------------------------------------------------------------------

    @app.post("/api/deye-hybrid/decode-telemetry")
    async def deye_hybrid_decode_telemetry(req: DeyeDecodeTelemetryRequest, principal=Depends(user)):
        """Decode Deye 3-phase hybrid inverter holding registers into normalized telemetry."""
        from .deye_hybrid_modbus import DeyeHybridEngine

        parsed_regs = {int(k): int(v) for k, v in req.registers.items()}
        telemetry = DeyeHybridEngine.decode_telemetry(parsed_regs)
        return {
            "source": "deye-modbus-ha-main (MIT clean-room independent)",
            "telemetry": telemetry,
        }

    @app.post("/api/deye-hybrid/decode-tou-schedule")
    async def deye_hybrid_decode_tou_schedule(req: DeyeDecodeTouRequest, principal=Depends(user)):
        """Decode Deye 6-slot TOU schedule registers."""
        from .deye_hybrid_modbus import DeyeHybridEngine

        parsed_regs = {int(k): int(v) for k, v in req.registers.items()}
        slots = DeyeHybridEngine.decode_tou_schedule(parsed_regs)
        return {
            "source": "deye-modbus-ha-main (MIT clean-room independent)",
            "slots": slots,
        }

    @app.post("/api/deye-hybrid/compile-work-mode")
    async def deye_hybrid_compile_work_mode(req: DeyeCompileWorkModeRequest, principal=Depends(user)):
        """Compile Modbus FC06 write frames for Deye Work Mode and Solar Sell."""
        from .deye_hybrid_modbus import DeyeHybridEngine

        try:
            cmd = DeyeHybridEngine.compile_work_mode(
                mode=req.mode,
                solar_sell=req.solar_sell,
                max_sell_power_w=req.max_sell_power_w,
            )
            return {
                "source": "deye-modbus-ha-main (MIT clean-room independent)",
                "command": cmd.to_dict(),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/deye-hybrid/compile-grid-charge")
    async def deye_hybrid_compile_grid_charge(req: DeyeCompileGridChargeRequest, principal=Depends(user)):
        """Compile Modbus FC06 write frames for Deye Grid Charge switch and current."""
        from .deye_hybrid_modbus import DeyeHybridEngine

        cmd = DeyeHybridEngine.compile_grid_charge(
            enable=req.enable,
            charge_current_a=req.charge_current_a,
        )
        return {
            "source": "deye-modbus-ha-main (MIT clean-room independent)",
            "command": cmd.to_dict(),
        }

    @app.post("/api/deye-hybrid/compile-tou-slot")
    async def deye_hybrid_compile_tou_slot(req: DeyeCompileTouSlotRequest, principal=Depends(user)):
        """Compile Modbus FC06 write frames for a single Deye TOU slot."""
        from .deye_hybrid_modbus import DeyeHybridEngine

        try:
            cmd = DeyeHybridEngine.compile_tou_slot(
                slot_number=req.slot_number,
                time_str=req.time_str,
                power_w=req.power_w,
                target_soc=req.target_soc,
                charge_source=req.charge_source,
            )
            return {
                "source": "deye-modbus-ha-main (MIT clean-room independent)",
                "command": cmd.to_dict(),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    # -----------------------------------------------------------------------
    # Solarman V5 Datalogger Frame Protocol (Port 8899)
    # Provenance: pysolarmanv5 (MIT)
    # -----------------------------------------------------------------------

    @app.post("/api/solarman-v5/encode-frame")
    async def solarman_v5_encode_frame(req: SolarmanV5EncodeRequest, principal=Depends(user)):
        """Encapsulate raw Modbus RTU bytes into Solarman V5 datalogger frame."""
        from .solarman_v5_protocol import SolarmanV5Engine

        try:
            rtu_bytes = bytes.fromhex(req.modbus_rtu_hex.replace(" ", ""))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex string in modbus_rtu_hex")

        v5_bytes = SolarmanV5Engine.encode_frame(
            modbus_rtu_frame=rtu_bytes,
            logger_serial=req.logger_serial,
            sequence_number=req.sequence_number,
        )

        return {
            "source": "pysolarmanv5 (MIT clean-room independent)",
            "logger_serial": req.logger_serial,
            "sequence_number": req.sequence_number,
            "modbus_rtu_hex": rtu_bytes.hex().upper(),
            "v5_frame_hex": v5_bytes.hex().upper(),
            "v5_frame_length": len(v5_bytes),
        }

    @app.post("/api/solarman-v5/decode-frame")
    async def solarman_v5_decode_frame(req: SolarmanV5DecodeRequest, principal=Depends(user)):
        """Decode and validate a Solarman V5 datalogger response frame."""
        from .solarman_v5_protocol import SolarmanV5Engine

        try:
            v5_bytes = bytes.fromhex(req.v5_frame_hex.replace(" ", ""))
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid hex string in v5_frame_hex")

        decoded = SolarmanV5Engine.decode_frame(v5_bytes)
        return {
            "source": "pysolarmanv5 (MIT clean-room independent)",
            "decoded": decoded.to_dict(),
        }

    @app.post("/api/solarman-v5/compile-request")
    async def solarman_v5_compile_request(req: SolarmanV5CompileRequest, principal=Depends(user)):
        """Compile high-level Modbus action (FC03, FC04, FC06, FC16) into Solarman V5 packet."""
        from .solarman_v5_protocol import SolarmanV5Engine

        try:
            if req.function_code in (3, 4):
                compiled = SolarmanV5Engine.compile_read_holding_registers(
                    logger_serial=req.logger_serial,
                    slave_id=req.modbus_slave_id,
                    start_address=req.start_address,
                    quantity=req.quantity_or_value,
                    sequence_number=req.sequence_number,
                )
            elif req.function_code == 6:
                compiled = SolarmanV5Engine.compile_write_single_register(
                    logger_serial=req.logger_serial,
                    slave_id=req.modbus_slave_id,
                    register_address=req.start_address,
                    value=req.quantity_or_value,
                    sequence_number=req.sequence_number,
                )
            elif req.function_code == 16:
                vals = req.values or [req.quantity_or_value]
                compiled = SolarmanV5Engine.compile_write_multiple_registers(
                    logger_serial=req.logger_serial,
                    slave_id=req.modbus_slave_id,
                    start_address=req.start_address,
                    values=vals,
                    sequence_number=req.sequence_number,
                )
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported function code {req.function_code}. Expected 3, 4, 6, or 16")

            return {
                "source": "pysolarmanv5 (MIT clean-room independent)",
                "compiled": compiled.to_dict(),
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/solarman-v5/parse-discovery")
    async def solarman_v5_parse_discovery(req: SolarmanV5DiscoveryRequest, principal=Depends(user)):
        """Parse Solarman UDP discovery broadcast response."""
        from .solarman_v5_protocol import parse_solarman_discovery_reply

        result = parse_solarman_discovery_reply(req.payload)
        if not result:
            raise HTTPException(status_code=400, detail="Could not parse discovery payload")
        return {
            "source": "pysolarmanv5 (MIT clean-room independent)",
            "discovery": result,
        }

    # -----------------------------------------------------------------------
    # SmartESS / Eybond Local Inverter Endpoints (Project #8)
    # -----------------------------------------------------------------------

    @app.post("/api/smartess/poll")
    async def smartess_poll(req: SmartEssPollRequest, principal=Depends(user)):
        """Poll telemetry from SmartESS / Eybond datalogger and return normalized EMS payload."""
        raise HTTPException(409, "local_transport_unavailable; use_registered_eybond_account_sync")

    @app.post("/api/smartess/command")
    async def smartess_command(req: SmartEssCommandRequest, principal=Depends(user)):
        """Safely execute inverter configuration command with readback verification."""
        from .smartess_local_client import SmartEssLocalClient

        client = SmartEssLocalClient(collector_pn=req.collector_pn, simulated=False)
        try:
            result = client.execute_command_safely(
                command_type=req.command_type,
                params=req.params,
                unlocked=req.unlocked,
            )
            return {
                "source": "ha-smartess-local (MIT clean-room independent)",
                "result": result,
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/smartess/parse-frame")
    async def smartess_parse_frame(req: SmartEssParseFrameRequest, principal=Depends(user)):
        """Parse raw Eybond binary frame hex string into header, FC, and payload."""
        from .smartess_local_client import (
            FC_FORWARD2DEVICE,
            FC_HEARTBEAT,
            decode_eybond_header,
            parse_forward2device_response,
            parse_heartbeat_response,
            parse_inverter_response,
        )

        try:
            frame_bytes = bytes.fromhex(req.raw_frame_hex.replace(" ", ""))
            hdr = decode_eybond_header(frame_bytes)
            res: dict[str, Any] = {
                "tid": hdr.tid,
                "devcode": hex(hdr.devcode),
                "total_len": hdr.total_len,
                "devaddr": hdr.devaddr,
                "fc": hdr.fc,
            }
            if hdr.fc == FC_HEARTBEAT:
                _, pn = parse_heartbeat_response(frame_bytes)
                res["collector_pn"] = pn
            elif hdr.fc == FC_FORWARD2DEVICE:
                _, p17_payload = parse_forward2device_response(frame_bytes)
                res["p17_raw_hex"] = p17_payload.hex()
                try:
                    cmd_type, text = parse_inverter_response(p17_payload)
                    res["p17_type"] = cmd_type
                    res["p17_text"] = text
                except Exception as inner_e:
                    res["p17_parse_error"] = str(inner_e)
            return {
                "source": "ha-smartess-local (MIT clean-room independent)",
                "frame": res,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Failed to parse frame: {exc}")

    # -----------------------------------------------------------------------
    # Growatt Multi-Phase & Export Limitation Endpoints (Project #9)
    # -----------------------------------------------------------------------

    @app.post("/api/growatt-multiphase/decode-telemetry")
    async def growatt_multiphase_decode_telemetry(req: GrowattMultiphaseDecodeTelemetryRequest, principal=Depends(user)):
        """Decode Growatt 1-phase or 3-phase SPH telemetry, DTC, and normalized EMS payload."""
        from .growatt_multiphase_modbus import decode_growatt_multiphase_telemetry

        try:
            in_regs = {int(k): int(v) for k, v in req.input_registers.items()}
            hold_regs = {int(k): int(v) for k, v in req.holding_registers.items()}
            tel = decode_growatt_multiphase_telemetry(in_regs, hold_regs)
            return {
                "source": "ha-growatt-modbus (MIT clean-room independent)",
                "telemetry": tel,
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Telemetry decode failed: {exc}")

    @app.post("/api/growatt-multiphase/compile-export-limit")
    async def growatt_multiphase_compile_export_limit(req: GrowattCompileExportLimitRequest, principal=Depends(user)):
        """Compile Growatt export limitation / zero feed-in registers 122 & 123."""
        from .growatt_multiphase_modbus import compile_export_limitation_command

        try:
            res = compile_export_limitation_command(enable=req.enable, limit_rate_pct=req.limit_rate_percent)
            return {
                "source": "ha-growatt-modbus (MIT clean-room independent)",
                "command": res,
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/growatt-multiphase/compile-window")
    async def growatt_multiphase_compile_window(req: GrowattCompileWindowRequest, principal=Depends(user)):
        """Compile Growatt Grid First or Battery First time window registers."""
        from .growatt_multiphase_modbus import (
            compile_battery_first_window_command,
            compile_grid_first_window_command,
        )

        try:
            if req.window_type == "grid_first":
                res = compile_grid_first_window_command(
                    window_index=req.window_index,
                    start_time=req.start_time,
                    stop_time=req.stop_time,
                    enable=req.enable,
                    discharge_rate_pct=req.rate_percent,
                    stop_soc_pct=req.stop_soc_percent,
                )
            elif req.window_type == "battery_first":
                res = compile_battery_first_window_command(
                    window_index=req.window_index,
                    start_time=req.start_time,
                    stop_time=req.stop_time,
                    enable=req.enable,
                    ac_charge_enable=req.ac_charge_enable,
                    charge_rate_pct=req.rate_percent,
                    stop_soc_pct=req.stop_soc_percent,
                )
            else:
                raise HTTPException(status_code=400, detail=f"Unsupported window type '{req.window_type}'. Expected 'grid_first' or 'battery_first'")

            return {
                "source": "ha-growatt-modbus (MIT clean-room independent)",
                "command": res,
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/growatt-multiphase/decode-faults")
    async def growatt_multiphase_decode_faults(req: GrowattDecodeFaultsRequest, principal=Depends(user)):
        """Decode Growatt 112-bit fault and warning registers 1001..1007."""
        from .growatt_multiphase_modbus import decode_fault_registers

        try:
            f_regs = {int(k): int(v) for k, v in req.fault_registers.items()}
            alarms = decode_fault_registers(f_regs)
            return {
                "source": "ha-growatt-modbus (MIT clean-room independent)",
                "alarms": [
                    {"register": a.register, "bit": a.bit, "code": a.code, "severity": a.severity}
                    for a in alarms
                ],
            }
        except Exception as exc:
            raise HTTPException(status_code=400, detail=f"Fault decode failed: {exc}")

    # -----------------------------------------------------------------------
    # Growatt Cloud OpenAPI V1 & ShineServer Endpoints (Project #10)
    # -----------------------------------------------------------------------

    @app.post("/api/growatt-cloud/plants")
    async def growatt_cloud_plants(req: GrowattCloudPlantsRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/growatt-cloud/devices")
    async def growatt_cloud_devices(req: GrowattCloudDevicesRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/growatt-cloud/sph-detail")
    async def growatt_cloud_sph_detail(req: GrowattCloudSphDetailRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/growatt-cloud/command")
    async def growatt_cloud_command(req: GrowattCloudCommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.post("/api/eybond-collector/discover")
    async def eybond_collector_discover(req: EybondCollectorDiscoverRequest, principal=Depends(user)):
        """Handle Eybond UDP discovery packet and return reverse-TCP handshake response."""
        from .eybond_collector_engine import build_udp_discovery_reply, parse_udp_discovery_redirect

        res = parse_udp_discovery_redirect(req.raw_udp_text.encode("utf-8"))
        if not res:
            raise HTTPException(status_code=400, detail="Invalid UDP discovery payload. Expected 'set>server=IP:PORT;'")
        host, port = res
        reply = build_udp_discovery_reply()
        return {
            "source": "esp-eybond-collector (MPL-2.0 clean-room independent)",
            "server_host": host,
            "server_port": port,
            "udp_reply": reply.decode("ascii"),
        }

    @app.post("/api/eybond-collector/parse-at")
    async def eybond_collector_parse_at(req: EybondCollectorAtRequest, principal=Depends(user)):
        """Parse Eybond AT command line and generate standard collector response."""
        from .eybond_collector_engine import handle_at_command, parse_at_command

        parsed = parse_at_command(req.at_line)
        if not parsed:
            raise HTTPException(status_code=400, detail="Invalid AT command line. Expected 'AT+<CMD>?' or 'AT+<CMD>=<VAL>'")
        cmd, is_write, val = parsed
        reply = handle_at_command(
            cmd=cmd,
            is_write=is_write,
            val=val,
            profile_pn=req.profile_pn,
            firmware_ver=req.firmware_ver,
            uart_cfg=req.uart_cfg,
        )
        return {
            "source": "esp-eybond-collector (MPL-2.0 clean-room independent)",
            "command": cmd,
            "is_write": is_write,
            "value": val,
            "response": reply.strip(),
        }

    @app.post("/api/eybond-collector/decode-pigs")
    async def eybond_collector_decode_pigs(req: EybondCollectorDecodePigsRequest, principal=Depends(user)):
        """Decode Voltronic QPIGS and QPIWS telemetry into Solar Fleet EMS schema."""
        from .eybond_collector_engine import normalize_eybond_pi30_telemetry, parse_qpigs_response

        try:
            qpigs = parse_qpigs_response(req.raw_qpigs)
            tel = normalize_eybond_pi30_telemetry(
                collector_pn=req.collector_pn,
                inverter_sn=req.inverter_sn,
                qpigs=qpigs,
                mode_char=req.mode_char,
                qpiws_flags=req.qpiws_flags,
            )
            return {
                "source": "esp-eybond-collector (MPL-2.0 clean-room independent)",
                "telemetry": tel,
            }
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc))

    @app.post("/api/eybond-collector/command")
    async def eybond_collector_command(req: EybondCollectorCommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.post("/api/goodwe-local/telemetry")
    async def goodwe_local_telemetry(req: GoodWeLocalTelemetryRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/goodwe-local/command")
    async def goodwe_local_command(req: GoodWeLocalCommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.post("/api/huawei-sun2000/telemetry")
    async def huawei_sun2000_telemetry(req: HuaweiSun2000TelemetryRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/huawei-sun2000/command")
    async def huawei_sun2000_command(req: HuaweiSun2000CommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.get("/api/solarman-profile/profiles")
    async def solarman_profile_list(principal=Depends(user)):
        """List all available Solarman multi-vendor inverter profiles."""
        from .solarman_profile_engine import PROFILE_REGISTRY

        profiles = [
            {
                "profile_id": pid,
                "vendor": p.vendor,
                "family_name": p.family_name,
                "default_slave_id": p.default_slave_id,
                "request_ranges_count": len(p.requests),
                "parameters_count": len(p.parameters),
            }
            for pid, p in PROFILE_REGISTRY.items()
        ]
        return {
            "source": "home_assistant_solarman-main (Apache-2.0 clean-room independent)",
            "profiles": profiles,
        }

    @app.post("/api/solarman-profile/telemetry")
    async def solarman_profile_telemetry(req: SolarmanProfileTelemetryRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/solarman-profile/command")
    async def solarman_profile_command(req: SolarmanProfileCommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.get("/api/sungrow-shx/info")
    async def sungrow_shx_info(principal=Depends(user)):
        """Retrieve Sungrow supported models, running states, and EMS scenes."""
        from .sungrow_shx_client import (
            SUNGROW_DEVICE_TYPES,
            SUNGROW_EMS_MODES,
            SUNGROW_FORCED_CMDS,
            SUNGROW_RUNNING_STATES,
        )

        return {
            "source": "Sungrow-SHx-Inverter-Modbus-Home-Assistant (MIT clean-room independent)",
            "supported_models": [
                {"code_hex": f"0x{code:04X}", "model": name}
                for code, name in sorted(SUNGROW_DEVICE_TYPES.items())
            ],
            "ems_modes": [
                {"key": k, "code": v[0], "name": v[1]}
                for k, v in SUNGROW_EMS_MODES.items()
            ],
            "forced_commands": [
                {"key": k, "code_hex": f"0x{v[0]:02X}", "name": v[1]}
                for k, v in SUNGROW_FORCED_CMDS.items()
            ],
            "running_states_sample": [
                {"code_hex": f"0x{code:04X}", "state": name}
                for code, name in sorted(SUNGROW_RUNNING_STATES.items())[:10]
            ],
            "scenes": [
                "self_consumption",
                "zero_export",
                "max_export",
                "battery_bypass",
                "forced_charge",
                "forced_discharge",
            ],
        }

    @app.post("/api/sungrow-shx/telemetry")
    async def sungrow_shx_telemetry(req: SungrowShxTelemetryRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/sungrow-shx/command")
    async def sungrow_shx_command(req: SungrowShxCommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.get("/api/deye-mqtt/families")
    async def deye_mqtt_families(principal=Depends(user)):
        """Enumerate supported Deye and SunSynk device families and command schemas."""
        from .deye_mqtt_bridge import DEYE_FAMILY_CATALOG, DeyeDeviceFamily

        descriptions = {
            DeyeDeviceFamily.SG01HP3: "High-Voltage 3-Phase Hybrid (6..50kW) (stack 150..800V, BMS stack regs 210..250)",
            DeyeDeviceFamily.SG04LP3: "Low-Voltage 3-Phase Hybrid (5..12kW) (48V battery, regs 142..177, 500..653)",
            DeyeDeviceFamily.SG02LP1: "Low-Voltage 1-Phase Hybrid (3.6..8kW) (regs 3..114, 150..279, BMS 312..319)",
            DeyeDeviceFamily.SG03LP1: "Low-Voltage 1-Phase Hybrid (extended models)",
            DeyeDeviceFamily.STRING: "Grid-Tied String Inverter (PV1..PV4, 3-Phase Grid AC, regs 60..116, 198..210)",
            DeyeDeviceFamily.MICRO: "Microinverters (SUN300..SUN2000G3, individual DC inputs, AC grid output)",
            DeyeDeviceFamily.IGEN_DTSD422: "IGEN DTSD-422-D3 Smart Power Meter (CT1..CT3 power, bidirectional energy)",
            DeyeDeviceFamily.HYBRID: "Classic Hybrid Inverter",
            DeyeDeviceFamily.AGGREGATED: "Multi-Inverter Cluster Data Aggregation (summed active power & daily energy)",
        }

        families_data = []
        for fam in DeyeDeviceFamily:
            sensors = DEYE_FAMILY_CATALOG.get(fam, [])
            sample_topics = [s.mqtt_topic_suffix for s in sensors[:5]]
            families_data.append({
                "family": fam.value,
                "name": fam.name,
                "description": descriptions.get(fam, fam.value),
                "sensor_count": len(sensors),
                "sample_topics": sample_topics,
            })

        return {
            "source": "deye-inverter-mqtt (Apache-2.0 clean-room independent)",
            "supported_families": families_data,
            "supported_commands": [
                "workmode",
                "solar_sell",
                "solar_sell_max_power",
                "active_power_regulation",
                "battery_settings",
                "timeofuse",
                "at_command",
            ],
            "at_commands_supported": ["AT+WNTYPE", "AT+WSKEY", "AT+MID", "AT+VER", "AT+Z", "AT+H"],
        }

    @app.post("/api/deye-mqtt/telemetry")
    async def deye_mqtt_telemetry(req: DeyeMqttTelemetryRequest, principal=Depends(user)):
        raise HTTPException(503, detail="LIVE_TRANSPORT_UNAVAILABLE: configure a scoped integration binding; simulator data is not operational telemetry.")

    @app.post("/api/deye-mqtt/command")
    async def deye_mqtt_command(req: DeyeMqttCommandRequest, principal=Depends(user)):
        raise HTTPException(409, detail="UNCOMMISSIONED_CONTROL: use the shared command engine; request flags cannot authorize hardware writes.")

    @app.post("/api/deye-mqtt/aggregate")
    async def deye_mqtt_aggregate(req: DeyeMqttAggregateRequest, principal=Depends(user)):
        """Aggregate telemetry from multiple inverters in a parallel cluster."""
        from .deye_mqtt_bridge import DeyeMultiInverterAggregator

        aggregator = DeyeMultiInverterAggregator()
        inverters = req.inverters or [
            {"logger_id": "inv_master", "ac_power_w": 5200.0, "day_energy_kwh": 26.5, "total_energy_kwh": 8200.0, "battery_power_w": 2000.0},
            {"logger_id": "inv_slave_1", "ac_power_w": 4800.0, "day_energy_kwh": 24.2, "total_energy_kwh": 7650.0, "battery_power_w": 1800.0},
            {"logger_id": "inv_slave_2", "ac_power_w": 4950.0, "day_energy_kwh": 25.1, "total_energy_kwh": 7900.0, "battery_power_w": 1900.0},
        ]

        for inv in inverters:
            aggregator.record_inverter_metrics(
                logger_id=str(inv.get("logger_id", "inv")),
                ac_active_power_w=float(inv.get("ac_power_w", 0.0)),
                daily_energy_kwh=float(inv.get("day_energy_kwh", 0.0)),
                total_energy_kwh=float(inv.get("total_energy_kwh", 0.0)),
                battery_power_w=float(inv.get("battery_power_w", 0.0)),
            )

        cluster_summary = aggregator.get_aggregated_cluster_metrics()
        return {
            "source": "deye-inverter-mqtt (Apache-2.0 clean-room independent)",
            "aggregated": cluster_summary,
        }
