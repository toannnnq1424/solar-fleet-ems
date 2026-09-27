"""Explicit parameters for non-executing engineering calculations."""

from typing import Literal

from pydantic import Field, model_validator

from .planning_configuration import BatteryParameters, ExplicitModel


class MicrogridParameters(ExplicitModel):
    nominal_frequency_hz: float = Field(gt=0, le=100)
    nominal_voltage_pu: float = Field(gt=0, le=2)
    frequency_threshold_hz: float = Field(gt=0)
    voltage_threshold_pu: float = Field(gt=0)
    resync_frequency_tolerance_hz: float = Field(gt=0)
    resync_voltage_tolerance_pu: float = Field(gt=0)
    resync_phase_tolerance_deg: float = Field(gt=0, le=180)

    @model_validator(mode="after")
    def thresholds(self):
        if (self.frequency_threshold_hz >= self.nominal_frequency_hz
                or self.voltage_threshold_pu >= self.nominal_voltage_pu
                or self.resync_frequency_tolerance_hz > self.frequency_threshold_hz
                or self.resync_voltage_tolerance_pu > self.voltage_threshold_pu):
            raise ValueError("invalid_microgrid_thresholds")
        return self


class MicrogridInverter(ExplicitModel):
    inverter_id: str = Field(min_length=1)
    mode: Literal["grid_following", "grid_forming", "standby", "fault"]
    real_power_kw: float
    reactive_power_kvar: float
    voltage_pu: float = Field(ge=0, le=2)
    frequency_hz: float = Field(ge=0, le=100)
    power_factor: float = Field(ge=-1, le=1)
    rated_power_kw: float = Field(gt=0)
    is_online: bool

    @model_validator(mode="after")
    def rating(self):
        if abs(self.real_power_kw) > self.rated_power_kw:
            raise ValueError("power_exceeds_rating")
        return self


class MicrogridLoad(ExplicitModel):
    load_id: str = Field(min_length=1)
    name: str = Field(min_length=1)
    power_kw: float = Field(ge=0)
    priority: int = Field(ge=1, le=10)
    is_shed: bool
    is_critical: bool


class MicrogridCalculation(ExplicitModel):
    parameters: MicrogridParameters
    inverters: list[MicrogridInverter] = Field(max_length=1000)
    loads: list[MicrogridLoad] = Field(max_length=1000)
    grid_voltage_pu: float = Field(ge=0, le=2)
    grid_frequency_hz: float = Field(ge=0, le=100)
    grid_phase_deg: float = Field(ge=-180, le=180)
    dt_seconds: float = Field(gt=0, le=60)

    @model_validator(mode="after")
    def unique_ids(self):
        if (len({i.inverter_id for i in self.inverters}) != len(self.inverters)
                or len({load.load_id for load in self.loads}) != len(self.loads)):
            raise ValueError("duplicate_equipment_ids")
        return self


class PredbatCalculation(BatteryParameters):
    solar_forecast_hourly: list[float] = Field(min_length=24, max_length=48)
    load_forecast_hourly: list[float] = Field(min_length=24, max_length=48)
    import_tariffs_hourly: list[float] = Field(min_length=24, max_length=48)
    export_tariffs_hourly: list[float] = Field(min_length=24, max_length=48)
    current_soc_pct: float = Field(ge=0, le=100)
    enable_arbitrage: bool
    currency: Literal["USD"]
    tariff_source: str = Field(min_length=1)

    @model_validator(mode="after")
    def aligned_forecasts(self):
        series = (self.solar_forecast_hourly, self.load_forecast_hourly,
                  self.import_tariffs_hourly, self.export_tariffs_hourly)
        if len({len(values) for values in series}) != 1:
            raise ValueError("equal_hourly_horizons_required")
        if any(value < 0 for values in series[:2] for value in values):
            raise ValueError("negative_generation_or_load")
        if not self.min_soc_pct <= self.current_soc_pct <= self.max_soc_pct:
            raise ValueError("soc_outside_battery_limits")
        if not self.tariff_source.strip():
            raise ValueError("tariff_source_required")
        return self


class GeneratorParameters(ExplicitModel):
    rated_power_kw: float = Field(gt=0)
    min_loading_ratio: float = Field(ge=0, le=1)
    optimal_loading_ratio: float = Field(gt=0, le=1)
    max_loading_ratio: float = Field(gt=0, le=1)
    fuel_idle_liters_per_hour: float = Field(ge=0)
    fuel_slope_liters_per_kwh: float = Field(ge=0)
    warmup_time_seconds: int = Field(ge=0)
    crank_time_seconds: int = Field(ge=0)
    cooldown_time_seconds: int = Field(ge=0)
    min_run_time_seconds: int = Field(ge=0)
    auto_start_soc_threshold: float = Field(ge=0, le=100)
    auto_stop_soc_threshold: float = Field(ge=0, le=100)

    @model_validator(mode="after")
    def ordered(self):
        if not self.min_loading_ratio <= self.optimal_loading_ratio <= self.max_loading_ratio:
            raise ValueError("invalid_generator_loading_limits")
        if self.auto_start_soc_threshold >= self.auto_stop_soc_threshold:
            raise ValueError("invalid_generator_soc_thresholds")
        return self


class GeneratorCalculation(ExplicitModel):
    specs: GeneratorParameters
    initial_state: Literal["off", "cranking", "warmup", "running_loaded", "cooldown", "fault", "locked_out"]
    elapsed_in_state_seconds: int = Field(ge=0)
    cumulative_run_seconds: int = Field(ge=0)
    microgrid_load_kw: float = Field(ge=0)
    battery_soc_pct: float = Field(ge=0, le=100)
    is_grid_available: bool
    battery_max_charge_kw: float = Field(ge=0)
    battery_max_discharge_kw: float = Field(ge=0)
    dt_seconds: int = Field(gt=0, le=3600)


class BlackStartObservation(ExplicitModel):
    bus_voltage_v: float = Field(ge=0)
    pv_frequency_hz: float = Field(ge=0, le=100)
    critical_load_kw: float = Field(ge=0)


class BlackStartCalculation(ExplicitModel):
    specs: GeneratorParameters
    observations: list[BlackStartObservation] = Field(min_length=1, max_length=7)


class HeatPumpCalculation(ExplicitModel):
    ambient_temp_c: float = Field(gt=-273.15)
    supply_temp_c: float = Field(gt=-273.15)
    required_thermal_kw: float = Field(ge=0)
    carnot_efficiency: float = Field(gt=0, le=1)
    min_electric_kw: float = Field(ge=0)
    max_electric_kw: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.min_electric_kw > self.max_electric_kw or self.supply_temp_c <= self.ambient_temp_c:
            raise ValueError("invalid_heat_pump_limits_or_temperature_lift")
        return self


class SGCalculation(ExplicitModel):
    pv_surplus_kw: float = Field(ge=0)
    grid_price: float
    is_grid_peak_lock: bool
    surplus_threshold_kw: float = Field(ge=0)
    forced_surplus_kw: float = Field(ge=0)
    tank_temp_c: float = Field(gt=-273.15)
    min_temp_c: float = Field(gt=-273.15)
    normal_setpoint_c: float = Field(gt=-273.15)
    boost_setpoint_c: float = Field(gt=-273.15)

    @model_validator(mode="after")
    def ordered(self):
        if not self.min_temp_c <= self.normal_setpoint_c <= self.boost_setpoint_c:
            raise ValueError("invalid_tank_setpoints")
        if self.surplus_threshold_kw > self.forced_surplus_kw:
            raise ValueError("invalid_surplus_thresholds")
        return self


class VoltWattParameters(ExplicitModel):
    nominal_voltage_v: float = Field(gt=0)
    v1_v: float = Field(gt=0)
    v2_v: float = Field(gt=0)
    v3_v: float = Field(gt=0)
    v4_v: float = Field(gt=0)
    p_rated_kw: float = Field(gt=0)
    min_power_ratio: float = Field(ge=0, le=0.5)

    @model_validator(mode="after")
    def ordered(self):
        if not self.v1_v < self.v2_v < self.v3_v < self.v4_v:
            raise ValueError("ordered_voltage_curve_required")
        return self


class VoltVarParameters(ExplicitModel):
    nominal_voltage_v: float = Field(gt=0)
    v1_v: float = Field(gt=0)
    v2_v: float = Field(gt=0)
    v3_v: float = Field(gt=0)
    v4_v: float = Field(gt=0)
    q_max_ratio: float = Field(ge=0, le=1)
    rated_kva: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if not self.v1_v < self.v2_v < self.v3_v < self.v4_v:
            raise ValueError("ordered_voltage_curve_required")
        return self


class FrequencyParameters(ExplicitModel):
    nominal_freq_hz: float = Field(gt=0)
    over_freq_threshold_hz: float = Field(gt=0)
    under_freq_threshold_hz: float = Field(gt=0)
    droop_pct: float = Field(gt=0, le=100)
    p_rated_kw: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if not self.under_freq_threshold_hz < self.nominal_freq_hz < self.over_freq_threshold_hz:
            raise ValueError("ordered_frequency_thresholds_required")
        return self


class ProtectionParameters(ExplicitModel):
    v_min_trip_v: float = Field(ge=0)
    v_max_trip_v: float = Field(gt=0)
    f_min_trip_hz: float = Field(ge=0)
    f_max_trip_hz: float = Field(gt=0)

    @model_validator(mode="after")
    def ordered(self):
        if self.v_min_trip_v >= self.v_max_trip_v or self.f_min_trip_hz >= self.f_max_trip_hz:
            raise ValueError("ordered_protection_thresholds_required")
        return self


class GridCalculation(ExplicitModel):
    voltage_v: float = Field(ge=0)
    frequency_hz: float = Field(ge=0)
    current_power_kw: float = Field(ge=0)
    volt_watt: VoltWattParameters
    volt_var: VoltVarParameters
    freq_watt: FrequencyParameters
    protection: ProtectionParameters

    @model_validator(mode="after")
    def consistent(self):
        if self.volt_watt.p_rated_kw != self.freq_watt.p_rated_kw:
            raise ValueError("inconsistent_rated_active_power")
        if self.volt_var.rated_kva < self.volt_watt.p_rated_kw:
            raise ValueError("apparent_power_below_rated_active_power")
        if self.current_power_kw > self.volt_watt.p_rated_kw:
            raise ValueError("active_power_exceeds_rating")
        return self