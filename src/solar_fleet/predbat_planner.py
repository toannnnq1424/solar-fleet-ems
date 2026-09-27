"""Predbat-style predictive battery dispatch planner and dynamic tariff arbitrage engine.

Independently implemented for Solar Fleet EMS.
Concepts from batpred-main (predbat.py, prediction.py, futurerate.py).
No code copied.

Provides:
- 24-hour to 48-hour forward battery state-of-charge simulation
- Battery cycle degradation-aware arbitrage ($2 * LCOE_deg hurdle rate)
- Dynamic tariff slot optimization (cheapest import charging vs. peak export discharge)
- Actionable inverter work-mode and time-of-use schedule generation
- Comparative cost assessment: baseline self-consumption vs. predictive optimization
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Enums and Config
# ---------------------------------------------------------------------------

class InverterDispatchMode(str, Enum):
    """Actionable hybrid inverter operational dispatch mode."""

    SELF_CONSUMPTION = "self_consumption"
    FORCE_CHARGE_GRID = "force_charge_grid"
    FORCE_DISCHARGE_EXPORT = "force_discharge_export"
    HOLD_SOC = "hold_soc"
    STANDBY = "standby"


@dataclass
class BatterySpecs:
    """Technical and financial specifications of the energy storage system."""

    capacity_kwh: float = 10.0
    usable_kwh: float = 9.0
    max_charge_kw: float = 5.0
    max_discharge_kw: float = 5.0
    charge_efficiency: float = 0.95
    discharge_efficiency: float = 0.95
    min_soc_pct: float = 10.0
    max_soc_pct: float = 100.0
    reserve_soc_pct: float = 20.0
    replacement_cost_usd: float = 3000.0
    rated_cycle_life: int = 6000

    @property
    def round_trip_efficiency(self) -> float:
        return self.charge_efficiency * self.discharge_efficiency

    @property
    def degradation_cost_per_kwh(self) -> float:
        """Levelized cycle degradation cost per kWh throughput.

        Total lifetime throughput = capacity * cycle_life * DOD (approx 80%)
        """
        lifetime_throughput_kwh = self.capacity_kwh * self.rated_cycle_life * 0.80
        if lifetime_throughput_kwh <= 0:
            return 0.05
        return self.replacement_cost_usd / lifetime_throughput_kwh


@dataclass
class SimulationSlot:
    """Results of a single discrete simulation time slot."""

    hour: int
    solar_generation_kw: float
    building_load_kw: float
    import_tariff: float
    export_tariff: float
    dispatch_mode: InverterDispatchMode
    battery_charge_kw: float = 0.0
    battery_discharge_kw: float = 0.0
    grid_import_kw: float = 0.0
    grid_export_kw: float = 0.0
    battery_soc_pct: float = 0.0
    slot_cost_usd: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "hour": self.hour,
            "solar_kw": round(self.solar_generation_kw, 3),
            "load_kw": round(self.building_load_kw, 3),
            "import_tariff": round(self.import_tariff, 4),
            "export_tariff": round(self.export_tariff, 4),
            "dispatch_mode": self.dispatch_mode.value,
            "battery_charge_kw": round(self.battery_charge_kw, 3),
            "battery_discharge_kw": round(self.battery_discharge_kw, 3),
            "grid_import_kw": round(self.grid_import_kw, 3),
            "grid_export_kw": round(self.grid_export_kw, 3),
            "battery_soc_pct": round(self.battery_soc_pct, 1),
            "slot_cost_usd": round(self.slot_cost_usd, 4),
        }


# ---------------------------------------------------------------------------
# Predbat Predictive Planner
# ---------------------------------------------------------------------------

class PredbatPlanner:
    """Predictive forward-planning engine for battery storage systems.

    Simulates hourly energy flows across the prediction horizon, identifies
    optimal grid-charge and export windows based on price spreads vs. cell degradation,
    and constructs executable inverter schedules.
    """

    def __init__(self, battery: BatterySpecs):
        self.battery = battery

    def plan_horizon(
        self,
        solar_forecast_hourly: List[float],
        load_forecast_hourly: List[float],
        import_tariffs_hourly: List[float],
        export_tariffs_hourly: List[float],
        current_soc_pct: float = 50.0,
        enable_arbitrage: bool = True,
    ) -> Dict[str, Any]:
        """Compute the optimal 24-48 hour forward dispatch plan."""
        n_hours = min(
            len(solar_forecast_hourly),
            len(load_forecast_hourly),
            len(import_tariffs_hourly),
            len(export_tariffs_hourly),
        )
        if n_hours == 0:
            return {"status": "error", "message": "empty forecast inputs"}

        # 1. Calculate net solar deficit over the horizon
        # Check if daytime solar covers the daytime load
        total_solar_kwh = sum(solar_forecast_hourly[:n_hours])
        total_load_kwh = sum(load_forecast_hourly[:n_hours])
        expected_deficit_kwh = max(0.0, total_load_kwh - total_solar_kwh)

        # 2. Determine degradation hurdle rate
        # Arbitrage is only economical if Price_export - Price_import > 2 * degradation_cost
        deg_cost = self.battery.degradation_cost_per_kwh
        hurdle_spread = 2.0 * deg_cost

        # 3. Identify cheapest import hours for pre-charging
        ranked_import_hours = sorted(
            range(n_hours),
            key=lambda h: import_tariffs_hourly[h],
        )

        # Determine how many cheap hours we need to charge if there's a deficit
        usable_battery_kwh = self.battery.usable_kwh
        hours_to_charge = min(4, int(math.ceil(usable_battery_kwh / self.battery.max_charge_kw)))
        cheapest_charge_hours = set(ranked_import_hours[:hours_to_charge])

        # 4. Identify peak export hours
        ranked_export_hours = sorted(
            range(n_hours),
            key=lambda h: export_tariffs_hourly[h],
            reverse=True,
        )

        # High export hours that clear the hurdle spread compared to average import
        min_import_price = min(import_tariffs_hourly[:n_hours])
        profitable_export_hours = set()
        if enable_arbitrage:
            for h in ranked_export_hours:
                if (export_tariffs_hourly[h] * self.battery.discharge_efficiency) - (min_import_price / self.battery.charge_efficiency) > hurdle_spread:
                    profitable_export_hours.add(h)

        # 5. Forward Simulation Loop
        current_soc = current_soc_pct
        current_energy_kwh = (current_soc / 100.0) * self.battery.capacity_kwh
        slots: List[SimulationSlot] = []

        total_import_cost = 0.0
        total_export_revenue = 0.0

        for h in range(n_hours):
            p_solar = solar_forecast_hourly[h]
            p_load = load_forecast_hourly[h]
            t_import = import_tariffs_hourly[h]
            t_export = export_tariffs_hourly[h]

            net_solar = p_solar - p_load  # > 0 means surplus, < 0 means deficit

            mode = InverterDispatchMode.SELF_CONSUMPTION
            p_charge = 0.0
            p_discharge = 0.0
            p_grid_import = 0.0
            p_grid_export = 0.0

            # Decision: Force Charge from Grid?
            # If this is one of the designated cheapest hours and battery is below max SOC
            if h in cheapest_charge_hours and current_soc < 95.0 and expected_deficit_kwh > 0:
                mode = InverterDispatchMode.FORCE_CHARGE_GRID
                charge_space_kwh = (self.battery.max_soc_pct - current_soc) / 100.0 * self.battery.capacity_kwh
                p_charge = min(self.battery.max_charge_kw, charge_space_kwh)
                # Grid import must cover both load and battery charge minus any solar
                p_grid_import = max(0.0, p_load + p_charge - p_solar)
                current_energy_kwh += p_charge * self.battery.charge_efficiency
                current_soc = min(self.battery.max_soc_pct, (current_energy_kwh / self.battery.capacity_kwh) * 100.0)

            # Decision: Force Discharge to Grid for Arbitrage?
            elif enable_arbitrage and h in profitable_export_hours and current_soc > self.battery.reserve_soc_pct:
                mode = InverterDispatchMode.FORCE_DISCHARGE_EXPORT
                avail_energy_kwh = max(0.0, (current_soc - self.battery.reserve_soc_pct) / 100.0 * self.battery.capacity_kwh)
                p_discharge = min(self.battery.max_discharge_kw, avail_energy_kwh)
                # Inverter outputs discharge + solar to cover load, excess exported to grid
                total_supply = p_discharge * self.battery.discharge_efficiency + p_solar
                if total_supply >= p_load:
                    p_grid_export = total_supply - p_load
                else:
                    p_grid_import = p_load - total_supply
                current_energy_kwh -= p_discharge
                current_soc = max(self.battery.min_soc_pct, (current_energy_kwh / self.battery.capacity_kwh) * 100.0)

            # Standard Self-Consumption Mode
            else:
                mode = InverterDispatchMode.SELF_CONSUMPTION
                if net_solar >= 0:
                    # Surplus solar: charge battery first
                    charge_space_kwh = (self.battery.max_soc_pct - current_soc) / 100.0 * self.battery.capacity_kwh
                    p_charge = min(self.battery.max_charge_kw, net_solar, charge_space_kwh)
                    current_energy_kwh += p_charge * self.battery.charge_efficiency
                    current_soc = min(self.battery.max_soc_pct, (current_energy_kwh / self.battery.capacity_kwh) * 100.0)
                    # Remaining surplus exported to grid
                    p_grid_export = max(0.0, net_solar - p_charge)
                else:
                    # Solar deficit: discharge battery to cover load
                    deficit_kw = -net_solar
                    avail_energy_kwh = max(0.0, (current_soc - self.battery.min_soc_pct) / 100.0 * self.battery.capacity_kwh)
                    p_discharge = min(self.battery.max_discharge_kw, deficit_kw, avail_energy_kwh)
                    current_energy_kwh -= p_discharge / self.battery.discharge_efficiency
                    current_soc = max(self.battery.min_soc_pct, (current_energy_kwh / self.battery.capacity_kwh) * 100.0)
                    # Remaining deficit imported from grid
                    p_grid_import = max(0.0, deficit_kw - p_discharge)

            # Financial calculation for this hour
            cost = p_grid_import * t_import
            revenue = p_grid_export * t_export
            slot_net_cost = cost - revenue

            total_import_cost += cost
            total_export_revenue += revenue

            slots.append(
                SimulationSlot(
                    hour=h,
                    solar_generation_kw=p_solar,
                    building_load_kw=p_load,
                    import_tariff=t_import,
                    export_tariff=t_export,
                    dispatch_mode=mode,
                    battery_charge_kw=p_charge,
                    battery_discharge_kw=p_discharge,
                    grid_import_kw=p_grid_import,
                    grid_export_kw=p_grid_export,
                    battery_soc_pct=current_soc,
                    slot_cost_usd=slot_net_cost,
                )
            )

        # Baseline comparison: No battery management (pure grid import/export without storage)
        baseline_cost = sum(
            max(0.0, load_forecast_hourly[h] - solar_forecast_hourly[h]) * import_tariffs_hourly[h]
            - max(0.0, solar_forecast_hourly[h] - load_forecast_hourly[h]) * export_tariffs_hourly[h]
            for h in range(n_hours)
        )

        plan_cost = total_import_cost - total_export_revenue
        total_savings = baseline_cost - plan_cost

        # Extract actionable inverter schedule windows
        inverter_schedule = self._build_inverter_schedule(slots)

        return {
            "status": "success",
            "horizon_hours": n_hours,
            "baseline_cost_usd": round(baseline_cost, 2),
            "plan_cost_usd": round(plan_cost, 2),
            "estimated_savings_usd": round(total_savings, 2),
            "total_import_cost_usd": round(total_import_cost, 2),
            "total_export_revenue_usd": round(total_export_revenue, 2),
            "degradation_cost_per_kwh": round(deg_cost, 4),
            "arbitrage_hurdle_spread": round(hurdle_spread, 4),
            "inverter_schedule": inverter_schedule,
            "slots": [s.to_dict() for s in slots],
        }

    @staticmethod
    def _build_inverter_schedule(slots: List[SimulationSlot]) -> List[Dict[str, Any]]:
        """Group consecutive hours into actionable time-of-use inverter commands."""
        if not slots:
            return []

        schedule = []
        current_mode = slots[0].dispatch_mode
        start_hour = slots[0].hour
        target_soc = slots[0].battery_soc_pct
        max_rate = max(slots[0].battery_charge_kw, slots[0].battery_discharge_kw)

        for s in slots[1:]:
            if s.dispatch_mode != current_mode:
                schedule.append({
                    "start_hour": start_hour,
                    "end_hour": s.hour,
                    "mode": current_mode.value,
                    "target_soc_pct": round(target_soc, 1),
                    "max_rate_kw": round(max_rate, 2),
                })
                current_mode = s.dispatch_mode
                start_hour = s.hour
                target_soc = s.battery_soc_pct
                max_rate = max(s.battery_charge_kw, s.battery_discharge_kw)
            else:
                target_soc = s.battery_soc_pct
                max_rate = max(max_rate, s.battery_charge_kw, s.battery_discharge_kw)

        # Append final segment
        schedule.append({
            "start_hour": start_hour,
            "end_hour": slots[-1].hour + 1,
            "mode": current_mode.value,
            "target_soc_pct": round(target_soc, 1),
            "max_rate_kw": round(max_rate, 2),
        })

        return schedule
