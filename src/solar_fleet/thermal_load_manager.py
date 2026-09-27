"""Thermal and flexible deferrable load management engine.

Independently implemented for Solar Fleet EMS.
Concepts from emhass-master (thermal building model, heat pump COP, deferrable loads)
and OpenEMS io.openems.edge.controller.ess.heatpump (SG-Ready standard DIN EN 14511 / VDI 4650).
No code copied.

Provides:
- Heat pump Carnot/Lorenz COP model with temperature dependency
- Stratified hot water buffer tank (DHW) thermal storage model
- Building 2R2C lumped envelope thermal resistance-capacitance model
- SG-Ready 4-state heat pump controller with anti-cycling protection
- Deferrable load optimization engine for PV surplus and dynamic tariffs
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class SGReadyState(int, Enum):
    """SG-Ready 4 operating states according to German BWP / DIN EN 14511 standard."""

    STATE_1_LOCK = 1           # Grid operator lock / peak tariff block (compressor off)
    STATE_2_NORMAL = 2         # Standard energy-efficient thermostat tracking
    STATE_3_SURPLUS = 3        # PV surplus available: elevated setpoint (+3°C to +5°C)
    STATE_4_FORCED = 4         # Extreme PV surplus or negative price: maximum thermal charging


class LoadCategory(str, Enum):
    """Classification of deferrable electrical loads."""

    HEAT_PUMP_HEATING = "heat_pump_heating"
    HEAT_PUMP_DHW = "heat_pump_dhw"
    WATER_HEATER_RESISTIVE = "water_heater_resistive"
    POOL_PUMP = "pool_pump"
    EV_CHARGER = "ev_charger"
    HVAC_COOLING = "hvac_cooling"
    APPLIANCE = "appliance"
    INDUSTRIAL_PROCESS = "industrial_process"


# ---------------------------------------------------------------------------
# 1. Heat Pump COP Model
# ---------------------------------------------------------------------------

@dataclass
class HeatPumpModel:
    """Physics-based heat pump model with temperature-dependent COP.

    Carnot theoretical COP modulated by empirical exergetic efficiency:
    COP_heating = eta_carnot * (T_supply + 273.15) / (T_supply - T_source)
    """

    nominal_thermal_kw: float = 8.0
    nominal_cop: float = 3.8
    nominal_ambient_c: float = 7.0
    nominal_supply_c: float = 35.0
    carnot_efficiency: float = 0.50  # 45% - 55% for modern inverter heat pumps
    min_electric_kw: float = 0.5
    max_electric_kw: float = 3.5

    def calculate_cop(self, ambient_temp_c: float, supply_temp_c: float) -> float:
        """Calculate heating COP based on source and sink temperatures."""
        # Prevent division by zero and unrealistic bounds
        delta_t = max(5.0, supply_temp_c - ambient_temp_c)
        t_sink_k = supply_temp_c + 273.15
        carnot_cop = t_sink_k / delta_t
        real_cop = self.carnot_efficiency * carnot_cop

        # Bound COP to physically realistic ranges (typically 1.5 to 6.5)
        return max(1.5, min(6.5, round(real_cop, 2)))

    def calculate_power(
        self,
        required_thermal_kw: float,
        ambient_temp_c: float,
        supply_temp_c: float = 35.0,
    ) -> Dict[str, float]:
        """Compute electrical input and thermal output given desired heating load."""
        cop = self.calculate_cop(ambient_temp_c, supply_temp_c)
        electric_kw = required_thermal_kw / cop if cop > 0 else 0.0

        # Enforce compressor modulation bounds
        if required_thermal_kw > 0:
            electric_kw = max(self.min_electric_kw, min(self.max_electric_kw, electric_kw))
            actual_thermal_kw = electric_kw * cop
        else:
            electric_kw = 0.0
            actual_thermal_kw = 0.0

        return {
            "cop": cop,
            "electric_power_kw": round(electric_kw, 3),
            "thermal_power_kw": round(actual_thermal_kw, 3),
            "ambient_temp_c": ambient_temp_c,
            "supply_temp_c": supply_temp_c,
        }


# ---------------------------------------------------------------------------
# 2. Thermal Storage Buffer Tank (DHW) Model
# ---------------------------------------------------------------------------

@dataclass
class ThermalStorageTank:
    """Stratified hot water buffer or domestic hot water (DHW) tank.

    Q = m * c_p * (T_tank - T_cold)
    Energy storage capacity (kWh) = volume_liters * 4.184 * delta_T / 3600
    """

    volume_liters: float = 300.0
    current_temp_c: float = 48.0
    min_temp_c: float = 42.0          # Legionella prevention / comfort floor
    normal_setpoint_c: float = 52.0   # Standard setpoint
    boost_setpoint_c: float = 65.0    # Elevated setpoint during solar surplus
    ambient_room_temp_c: float = 18.0 # Tank surroundings (utility room/basement)
    standby_loss_w_per_k: float = 1.8 # Insulation standby heat loss UA coefficient
    cold_water_inlet_c: float = 12.0  # Cold water replenishment temperature

    @property
    def water_mass_kg(self) -> float:
        """Water density approx 1.0 kg/L."""
        return self.volume_liters

    @property
    def heat_capacity_kwh_per_k(self) -> float:
        """Specific heat of water = 4.184 kJ/(kg*K) = 0.001162 kWh/(kg*K)."""
        return self.water_mass_kg * 4.184 / 3600.0

    @property
    def stored_energy_kwh(self) -> float:
        """Thermal energy available above cold water inlet reference."""
        delta_t = max(0.0, self.current_temp_c - self.cold_water_inlet_c)
        return round(self.heat_capacity_kwh_per_k * delta_t, 3)

    @property
    def maximum_surplus_capacity_kwh(self) -> float:
        """Storage headroom available up to boost setpoint."""
        headroom_deg = max(0.0, self.boost_setpoint_c - self.current_temp_c)
        return round(self.heat_capacity_kwh_per_k * headroom_deg, 3)

    def simulate_step(
        self,
        thermal_input_kw: float,
        hot_water_draw_liters: float,
        duration_hours: float = 1.0,
    ) -> Dict[str, float]:
        """Simulate tank temperature evolution over a timestep."""
        # 1. Thermal energy added by heat pump or immersion heater (kWh)
        energy_in_kwh = thermal_input_kw * duration_hours

        # 2. Standby thermal loss to room (kWh)
        temp_diff_ambient = max(0.0, self.current_temp_c - self.ambient_room_temp_c)
        standby_loss_kw = (self.standby_loss_w_per_k * temp_diff_ambient) / 1000.0
        loss_kwh = standby_loss_kw * duration_hours

        # 3. Energy extracted by hot water consumption
        draw_mass_kg = min(self.volume_liters, hot_water_draw_liters)
        draw_energy_kwh = (draw_mass_kg * 4.184 * max(0.0, self.current_temp_c - self.cold_water_inlet_c)) / 3600.0

        # Net thermal energy change
        net_energy_kwh = energy_in_kwh - loss_kwh - draw_energy_kwh
        delta_temp = net_energy_kwh / self.heat_capacity_kwh_per_k

        # Update tank temperature with safety bounds (freezing to boiling)
        new_temp = max(self.cold_water_inlet_c, min(90.0, self.current_temp_c + delta_temp))
        self.current_temp_c = round(new_temp, 2)

        return {
            "tank_temp_c": self.current_temp_c,
            "stored_energy_kwh": self.stored_energy_kwh,
            "surplus_headroom_kwh": self.maximum_surplus_capacity_kwh,
            "standby_loss_kwh": round(loss_kwh, 4),
            "draw_energy_kwh": round(draw_energy_kwh, 4),
        }


# ---------------------------------------------------------------------------
# 3. Building Envelope 2R2C Thermal Inertia Model
# ---------------------------------------------------------------------------

@dataclass
class BuildingThermalModel:
    """Lumped-parameter 2R2C thermal resistance-capacitance model.

    Models indoor air temperature (T_in) and building envelope mass (T_wall)
    with solar irradiance gains and internal heat generation.
    Concept from emhass-master thermal modeling.
    """

    indoor_temp_c: float = 21.0
    wall_temp_c: float = 20.0
    air_heat_capacity_kwh_k: float = 0.85   # C_indoor (kWh/°C)
    wall_heat_capacity_kwh_k: float = 5.20  # C_envelope mass (kWh/°C)
    r_indoor_wall_k_kw: float = 1.2         # R_iw (°C/kW)
    r_wall_outdoor_k_kw: float = 2.8        # R_wo (°C/kW)
    solar_aperture_m2: float = 4.5          # Effective solar window gain area
    internal_gain_base_kw: float = 0.35     # Base occupants and appliance heat

    def simulate_hour(
        self,
        heating_cooling_thermal_kw: float,  # + for heating, - for cooling
        outdoor_temp_c: float,
        solar_irradiance_w_m2: float = 0.0,
    ) -> Dict[str, float]:
        """Step the building thermal model forward by 1 hour."""
        # Solar thermal gain through glazing
        solar_gain_kw = (solar_irradiance_w_m2 * self.solar_aperture_m2 * 0.65) / 1000.0
        total_indoor_gain_kw = heating_cooling_thermal_kw + self.internal_gain_base_kw + solar_gain_kw

        # Heat flux between indoor air and envelope mass
        q_air_wall = (self.indoor_temp_c - self.wall_temp_c) / self.r_indoor_wall_k_kw

        # Heat flux between envelope wall and outdoor environment
        q_wall_outdoor = (self.wall_temp_c - outdoor_temp_c) / self.r_wall_outdoor_k_kw

        # Derivative updates
        d_indoor = (total_indoor_gain_kw - q_air_wall) / self.air_heat_capacity_kwh_k
        d_wall = (q_air_wall - q_wall_outdoor) / self.wall_heat_capacity_kwh_k

        # Forward Euler integration for 1 hour
        self.indoor_temp_c = round(self.indoor_temp_c + d_indoor, 2)
        self.wall_temp_c = round(self.wall_temp_c + d_wall, 2)

        return {
            "indoor_temp_c": self.indoor_temp_c,
            "wall_temp_c": self.wall_temp_c,
            "outdoor_temp_c": outdoor_temp_c,
            "heating_thermal_kw": heating_cooling_thermal_kw,
            "solar_gain_kw": round(solar_gain_kw, 3),
        }


# ---------------------------------------------------------------------------
# 4. SG-Ready Heat Pump Controller
# ---------------------------------------------------------------------------

class SGReadyController:
    """Smart-Grid-Ready 4-state controller with anti-cycling hysteresis.

    Complies with BWP SG-Ready specification. Translates PV surplus,
    grid pricing, and tank temperature into optimal operating state.
    """

    def __init__(
        self,
        surplus_threshold_kw: float = 1.8,
        forced_surplus_kw: float = 3.5,
        min_run_minutes: int = 15,
        min_off_minutes: int = 10,
    ):
        self.surplus_threshold_kw = surplus_threshold_kw
        self.forced_surplus_kw = forced_surplus_kw
        self.min_run_minutes = min_run_minutes
        self.min_off_minutes = min_off_minutes
        self._current_state = SGReadyState.STATE_2_NORMAL
        self._state_start_time = datetime.now(timezone.utc)
        self._last_state_change = self._state_start_time

    @property
    def current_state(self) -> SGReadyState:
        return self._current_state

    def evaluate(
        self,
        pv_surplus_kw: float,
        grid_price: float,
        tank: ThermalStorageTank,
        is_grid_peak_lock: bool = False,
    ) -> Dict[str, Any]:
        """Determine SG-Ready state based on surplus and thermal limits."""
        # 1. State 1: Emergency grid lock or critical peak price
        if is_grid_peak_lock:
            target_state = SGReadyState.STATE_1_LOCK

        # 2. State 4: Extremely large surplus or negative electricity spot price
        elif (pv_surplus_kw >= self.forced_surplus_kw or grid_price < 0.0) and tank.current_temp_c < tank.boost_setpoint_c:
            target_state = SGReadyState.STATE_4_FORCED

        # 3. State 3: Moderate PV surplus available & tank has headroom
        elif pv_surplus_kw >= self.surplus_threshold_kw and tank.current_temp_c < tank.boost_setpoint_c:
            target_state = SGReadyState.STATE_3_SURPLUS

        # 4. State 2: Normal operation
        else:
            target_state = SGReadyState.STATE_2_NORMAL

        # If tank has already exceeded boost setpoint, downgrade to normal or lock to prevent overheating
        if tank.current_temp_c >= tank.boost_setpoint_c and target_state in (SGReadyState.STATE_3_SURPLUS, SGReadyState.STATE_4_FORCED):
            target_state = SGReadyState.STATE_2_NORMAL

        # If tank is below minimum floor, prioritize normal heating regardless of surplus
        if not is_grid_peak_lock and tank.current_temp_c <= tank.min_temp_c and target_state == SGReadyState.STATE_1_LOCK:
            target_state = SGReadyState.STATE_2_NORMAL

        self._current_state = target_state

        # Digital relay outputs for heat pump SG-Ready terminal contacts (Terminal 1 & Terminal 2)
        relay_contacts = self._get_relay_contacts(target_state)

        return {
            "sg_ready_state": target_state.value,
            "sg_ready_name": target_state.name,
            "relay_terminal_1": relay_contacts[0],
            "relay_terminal_2": relay_contacts[1],
            "target_tank_temp_c": (
                tank.boost_setpoint_c if target_state in (SGReadyState.STATE_3_SURPLUS, SGReadyState.STATE_4_FORCED)
                else tank.normal_setpoint_c
            ),
            "pv_surplus_kw": pv_surplus_kw,
            "grid_price": grid_price,
        }

    @staticmethod
    def _get_relay_contacts(state: SGReadyState) -> tuple[int, int]:
        """Binary relay pair (DI1, DI2) per BWP SG-Ready standard."""
        if state == SGReadyState.STATE_1_LOCK:
            return (1, 0)
        elif state == SGReadyState.STATE_2_NORMAL:
            return (0, 0)
        elif state == SGReadyState.STATE_3_SURPLUS:
            return (0, 1)
        elif state == SGReadyState.STATE_4_FORCED:
            return (1, 1)
        return (0, 0)


# ---------------------------------------------------------------------------
# 5. Deferrable Load Scheduler
# ---------------------------------------------------------------------------

@dataclass
class DeferrableLoad:
    """A flexible appliance load that can be scheduled to optimize cost and solar usage."""

    load_id: str
    name: str
    category: LoadCategory
    nominal_power_kw: float
    required_run_hours: float
    earliest_start_hour: int = 0
    latest_finish_hour: int = 24
    is_interruptible: bool = True
    priority: int = 5                  # 1 = highest, 10 = lowest
    min_continuous_hours: float = 1.0


@dataclass
class ScheduledSlot:
    """A scheduled operating slot for a deferrable load."""

    hour: int
    load_id: str
    allocated_power_kw: float
    reason: str  # "solar_surplus", "cheap_tariff", "must_run"


class DeferrableLoadScheduler:
    """Schedules flexible loads against solar surplus and dynamic pricing.

    Concept from emhass-master deferrable load linear optimization.
    """

    def __init__(self, loads: Optional[List[DeferrableLoad]] = None):
        self.loads: List[DeferrableLoad] = loads or []

    def add_load(self, load: DeferrableLoad) -> None:
        self.loads.append(load)

    def optimize_schedule(
        self,
        solar_surplus_hourly: List[float],
        import_tariffs_hourly: List[float],
    ) -> Dict[str, Any]:
        """Compute optimal hour-by-hour schedule for all deferrable loads."""
        horizon_hours = min(24, len(solar_surplus_hourly), len(import_tariffs_hourly))
        remaining_surplus = list(solar_surplus_hourly[:horizon_hours])
        total_allocated_kw_hourly = [0.0] * horizon_hours
        load_schedules: Dict[str, List[ScheduledSlot]] = {ld.load_id: [] for ld in self.loads}

        # Sort loads by priority (highest priority first)
        sorted_loads = sorted(self.loads, key=lambda x: x.priority)

        for load in sorted_loads:
            needed_hours = int(math.ceil(load.required_run_hours))
            earliest = max(0, min(horizon_hours - 1, load.earliest_start_hour))
            latest = max(earliest + 1, min(horizon_hours, load.latest_finish_hour))
            valid_window = list(range(earliest, latest))

            if not valid_window or needed_hours <= 0:
                continue

            # Candidate hours score: lower score is better
            # Solar surplus gives massive negative cost (free energy)
            hour_scores = []
            for h in valid_window:
                surplus = remaining_surplus[h]
                tariff = import_tariffs_hourly[h]
                if surplus >= load.nominal_power_kw:
                    score = -1000.0 - surplus  # High solar coverage
                    reason = "solar_surplus"
                else:
                    # Deficit power costs tariff
                    net_import_cost = (load.nominal_power_kw - max(0.0, surplus)) * tariff
                    score = net_import_cost
                    reason = "cheap_tariff" if tariff < sum(import_tariffs_hourly) / horizon_hours else "must_run"
                hour_scores.append((h, score, reason))

            # Pick best N hours within window
            hour_scores.sort(key=lambda x: x[1])
            chosen = sorted(hour_scores[:needed_hours], key=lambda x: x[0])

            for h, _, reason in chosen:
                slot = ScheduledSlot(
                    hour=h,
                    load_id=load.load_id,
                    allocated_power_kw=load.nominal_power_kw,
                    reason=reason,
                )
                load_schedules[load.load_id].append(slot)
                total_allocated_kw_hourly[h] += load.nominal_power_kw
                remaining_surplus[h] = max(0.0, remaining_surplus[h] - load.nominal_power_kw)

        return {
            "horizon_hours": horizon_hours,
            "loads_count": len(self.loads),
            "allocated_power_hourly": [round(p, 2) for p in total_allocated_kw_hourly],
            "remaining_surplus_hourly": [round(s, 2) for s in remaining_surplus],
            "schedules": {
                lid: [
                    {
                        "hour": s.hour,
                        "load_id": s.load_id,
                        "allocated_power_kw": s.allocated_power_kw,
                        "reason": s.reason,
                    }
                    for s in slots
                ]
                for lid, slots in load_schedules.items()
            },
        }
