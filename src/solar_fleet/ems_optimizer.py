"""EMS Optimization, Multi-Inverter Fleet Balancing, and EVN TOU Schedule Engine.

Synthesized from:
- batpred (inverter.py, execute.py): multi-inverter SOC balancing & fleet power distribution
- emhass (optimization.py): linear dispatch arbitrage & tariff cost minimization
- tariff_engine.py: EVN 3-tier tariff schedule (Decision 2699/QĐ-BCT)
- tou_builder.py: 6-slot Time-of-Use schedule generation for hardware inverters

Independently implemented for Solar Fleet EMS.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, time
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .adapters.tou_builder import TouSlotProgramme, build_tou_programme
from .tariff_engine import EVN_TARIFF_TABLES, TariffTierSchedule


@dataclass
class InverterFleetMember:
    """State and capability of an individual inverter in a multi-inverter plant."""

    device_id: str
    rated_power_kw: float
    battery_capacity_kwh: float
    current_soc_pct: float
    min_soc_pct: float = 10.0
    max_soc_pct: float = 100.0
    max_charge_kw: float = 5.0
    max_discharge_kw: float = 5.0
    online: bool = True


@dataclass
class FleetBalanceResult:
    """Result of multi-inverter power allocation."""

    total_target_kw: float
    mode: Literal["charge", "discharge", "idle"]
    allocations: dict[str, float]  # {device_id: allocated_power_kw}
    projected_socs: dict[str, float]  # {device_id: estimated_new_soc_after_1h}
    message: str = "ok"


class FleetInverterBalancer:
    """Balances power across multiple parallel inverters to equalize battery wear.

    Derived from batpred/inverter.py:
    - On CHARGE: Inverters with LOWER SOC receive higher charging power to catch up.
    - On DISCHARGE: Inverters with HIGHER SOC deliver higher discharging power.
    - Obeys individual inverter rated power, max charge/discharge rates, and SOC limits.
    """

    @staticmethod
    def balance_fleet(
        members: list[InverterFleetMember],
        target_total_kw: float,
        mode: Literal["charge", "discharge", "idle"],
        duration_hours: float = 1.0,
    ) -> FleetBalanceResult:
        active = [m for m in members if m.online]
        if not active or mode == "idle" or abs(target_total_kw) < 1e-3:
            return FleetBalanceResult(
                total_target_kw=target_total_kw,
                mode="idle",
                allocations={m.device_id: 0.0 for m in members},
                projected_socs={m.device_id: m.current_soc_pct for m in members},
                message="No active members or idle target",
            )

        allocations: dict[str, float] = {m.device_id: 0.0 for m in members}

        if mode == "charge":
            # Weight is proportional to available capacity to 100%: (max_soc - soc) * capacity
            weights = {}
            for m in active:
                headroom = max(0.0, m.max_soc_pct - m.current_soc_pct)
                weights[m.device_id] = headroom * m.battery_capacity_kwh

            total_weight = sum(weights.values())
            if total_weight <= 0:
                # All batteries full
                return FleetBalanceResult(
                    total_target_kw=target_total_kw,
                    mode="charge",
                    allocations=allocations,
                    projected_socs={m.device_id: m.current_soc_pct for m in members},
                    message="All batteries at or above max SOC limit",
                )

            # Proportional distribution with clamping
            for m in active:
                raw_kw = (weights[m.device_id] / total_weight) * target_total_kw
                clamped_kw = min(raw_kw, m.max_charge_kw, m.rated_power_kw)
                allocations[m.device_id] = round(clamped_kw, 2)

        elif mode == "discharge":
            # Weight is proportional to available energy above min_soc: (soc - min_soc) * capacity
            weights = {}
            for m in active:
                avail = max(0.0, m.current_soc_pct - m.min_soc_pct)
                weights[m.device_id] = avail * m.battery_capacity_kwh

            total_weight = sum(weights.values())
            if total_weight <= 0:
                return FleetBalanceResult(
                    total_target_kw=target_total_kw,
                    mode="discharge",
                    allocations=allocations,
                    projected_socs={m.device_id: m.current_soc_pct for m in members},
                    message="All batteries at or below min SOC floor",
                )

            for m in active:
                raw_kw = (weights[m.device_id] / total_weight) * target_total_kw
                clamped_kw = min(raw_kw, m.max_discharge_kw, m.rated_power_kw)
                allocations[m.device_id] = round(clamped_kw, 2)

        # Calculate projected SOCs after 1 hour of running at this allocation
        projected = {}
        for m in members:
            kw = allocations.get(m.device_id, 0.0)
            if mode == "charge":
                delta_soc = (kw * duration_hours / m.battery_capacity_kwh) * 100.0 if m.battery_capacity_kwh > 0 else 0
                new_soc = min(m.max_soc_pct, m.current_soc_pct + delta_soc)
            elif mode == "discharge":
                delta_soc = (kw * duration_hours / m.battery_capacity_kwh) * 100.0 if m.battery_capacity_kwh > 0 else 0
                new_soc = max(m.min_soc_pct, m.current_soc_pct - delta_soc)
            else:
                new_soc = m.current_soc_pct
            projected[m.device_id] = round(new_soc, 1)

        return FleetBalanceResult(
            total_target_kw=sum(allocations.values()),
            mode=mode,
            allocations=allocations,
            projected_socs=projected,
            message="Power balanced across active inverters",
        )


@dataclass
class OptimizationPlanResult:
    """24-hour EVN-aware dispatch plan with cost savings and inverter TOU schedule."""

    site_id: str
    tariff_category: str
    voltage_level: str
    total_baseline_cost_vnd: float
    total_optimized_cost_vnd: float
    net_savings_vnd: float
    savings_pct: float
    slots_24h: list[dict[str, Any]]
    tou_programme: list[TouSlotProgramme]
    battery_degradation_cost_vnd: float = 0.0
    net_profit_vnd: float = 0.0


class EVNTOUOptimizer:
    """Optimizes battery storage schedule for EVN 3-tier Time-of-Use tariffs.

    Rules:
    1. Off-peak (22:00 - 04:00): Lowest tariff (~1.000 - 1.150 VND/kWh).
       -> Force-charge battery from grid up to 95-100% SOC.
    2. Morning Peak (09:30 - 11:30): Highest tariff (~3.000 - 4.900 VND/kWh).
       -> Peak-shaving discharge: battery supplements solar to eliminate grid import.
    3. Normal Day (11:30 - 17:00): Solar typically peak; charge from solar surplus.
    4. Evening Peak (17:00 - 20:00): Highest tariff and no solar.
       -> Maximum discharge to cover building load and reduce peak demand charges.
    5. Normal Night (20:00 - 22:00): Float/self-consumption until off-peak window.
    """

    def __init__(
        self,
        tariff_category: str = "MANUFACTURING",
        voltage_level: str = "LOW_VOLTAGE_UNDER_22KV",
        battery_capacity_kwh: float = 15.0,
        max_charge_kw: float = 6.0,
        max_discharge_kw: float = 6.0,
        battery_deg_cost_vnd_per_kwh: float = 500.0,  # ~0.02 USD/kWh cycle aging
        roundtrip_efficiency: float = 0.92,  # Typical LFP round-trip efficiency
        max_c_rate: float = 0.5,  # Safe continuous C-rate (0.5C)
        weekend_load_factor: float = 0.85,  # Weekend factory consumption factor
        min_soc_pct: float = 10.0,
        max_soc_pct: float = 95.0,
        reserve_soc_pct: float = 20.0,
    ):
        self.tariff_category = tariff_category
        self.voltage_level = voltage_level
        self.battery_capacity_kwh = battery_capacity_kwh
        self.max_charge_kw = max_charge_kw
        self.max_discharge_kw = max_discharge_kw
        self.battery_deg_cost_vnd = battery_deg_cost_vnd_per_kwh
        self.roundtrip_efficiency = roundtrip_efficiency
        self.max_c_rate = max_c_rate
        self.weekend_load_factor = weekend_load_factor
        self.min_soc_pct = min_soc_pct
        self.max_soc_pct = max_soc_pct
        self.reserve_soc_pct = reserve_soc_pct

        # Lookup rates
        cat_table = EVN_TARIFF_TABLES.get(tariff_category, EVN_TARIFF_TABLES["MANUFACTURING"])
        self.rates = cat_table.get(voltage_level, cat_table.get("LOW_VOLTAGE_UNDER_22KV", {
            "off_peak": 1152.0,
            "normal": 1822.0,
            "peak": 3254.0,
        }))

    def get_rate_for_dt(self, dt: datetime) -> float:
        tier = TariffTierSchedule.classify_hour(dt)
        if tier == "PEAK":
            return self.rates["peak"]
        elif tier == "OFF_PEAK":
            return self.rates["off_peak"]
        return self.rates["normal"]

    def optimize_24h(
        self,
        site_id: str,
        solar_kw_24h: list[float],
        load_kw_24h: list[float],
        start_hour: int = 0,
        initial_soc_pct: float = 50.0,
    ) -> OptimizationPlanResult:
        """Compute the 24-hour cost-optimal schedule."""
        tz = ZoneInfo("Asia/Ho_Chi_Minh")
        now_date = datetime.now(tz).date()

        slots: list[dict[str, Any]] = []
        soc = max(self.min_soc_pct, min(100.0, float(initial_soc_pct)))
        energy_kwh = (soc / 100.0) * self.battery_capacity_kwh

        baseline_cost_vnd = 0.0
        optimized_cost_vnd = 0.0

        eff_chg = math.sqrt(self.roundtrip_efficiency)
        eff_dis = math.sqrt(self.roundtrip_efficiency)
        safe_chg_kw = min(self.max_charge_kw, self.battery_capacity_kwh * self.max_c_rate)
        safe_dis_kw = min(self.max_discharge_kw, self.battery_capacity_kwh * self.max_c_rate)

        for h in range(24):
            hour = (start_hour + h) % 24
            slot_dt = datetime.combine(now_date, time(hour, 0), tz)
            rate = self.get_rate_for_dt(slot_dt)
            tier = TariffTierSchedule.classify_hour(slot_dt)

            p_solar = solar_kw_24h[h] if h < len(solar_kw_24h) else 0.0
            base_load = load_kw_24h[h] if h < len(load_kw_24h) else 2.0
            is_weekend = slot_dt.weekday() in (5, 6)
            p_load = base_load * (self.weekend_load_factor if is_weekend else 1.0)

            # Baseline scenario (pure solar without storage)
            net_baseline_import = max(0.0, p_load - p_solar)
            baseline_cost_vnd += net_baseline_import * rate

            # Optimization logic
            dispatch_action = "SELF_CONSUMPTION"
            p_chg = 0.0
            p_dis = 0.0
            p_import = 0.0

            if tier == "OFF_PEAK" and soc < self.max_soc_pct:
                # Force charge during cheap off-peak hours
                dispatch_action = "GRID_CHARGE"
                needed_kwh = (self.max_soc_pct - soc) / 100.0 * self.battery_capacity_kwh
                p_chg = min(safe_chg_kw, needed_kwh)
                p_import = max(0.0, p_load + p_chg - p_solar)
                energy_kwh += p_chg * eff_chg
                soc = min(self.max_soc_pct, (energy_kwh / self.battery_capacity_kwh) * 100.0)

            elif tier == "PEAK" and soc > self.reserve_soc_pct:
                # Peak shaving discharge during high-cost peak hours
                dispatch_action = "PEAK_DISCHARGE"
                avail_kwh = max(0.0, (soc - self.reserve_soc_pct) / 100.0 * self.battery_capacity_kwh)
                deficit = max(0.0, p_load - p_solar)
                p_dis = min(safe_dis_kw, deficit, avail_kwh)
                total_supply = p_solar + p_dis
                if total_supply >= p_load:
                    p_import = 0.0
                else:
                    p_import = p_load - total_supply
                energy_kwh -= p_dis / eff_dis
                soc = max(self.min_soc_pct, (energy_kwh / self.battery_capacity_kwh) * 100.0)

            else:
                # Self-consumption mode during normal hours
                net = p_solar - p_load
                if net > 0:
                    charge_space = max(0.0, (self.max_soc_pct - soc) / 100.0 * self.battery_capacity_kwh)
                    p_chg = min(safe_chg_kw, net, charge_space)
                    energy_kwh += p_chg * eff_chg
                    soc = min(self.max_soc_pct, (energy_kwh / self.battery_capacity_kwh) * 100.0)
                else:
                    deficit = -net
                    floor_soc = max(self.reserve_soc_pct, self.min_soc_pct)
                    avail_kwh = max(0.0, (soc - floor_soc) / 100.0 * self.battery_capacity_kwh)
                    p_dis = min(safe_dis_kw, deficit, avail_kwh)
                    p_import = deficit - p_dis
                    energy_kwh -= p_dis / eff_dis
                    soc = max(self.min_soc_pct, (energy_kwh / self.battery_capacity_kwh) * 100.0)

            # Hour cost
            slot_cost = p_import * rate
            optimized_cost_vnd += slot_cost

            slots.append({
                "hour": hour,
                "tier": tier,
                "rate_vnd": rate,
                "solar_kw": round(p_solar, 2),
                "load_kw": round(p_load, 2),
                "action": dispatch_action,
                "charge_kw": round(p_chg, 2),
                "discharge_kw": round(p_dis, 2),
                "grid_import_kw": round(p_import, 2),
                "battery_soc_pct": round(soc, 1),
                "cost_vnd": round(slot_cost, 0),
            })

        net_savings_vnd = max(0.0, baseline_cost_vnd - optimized_cost_vnd)
        savings_pct = (net_savings_vnd / baseline_cost_vnd * 100.0) if baseline_cost_vnd > 0 else 0.0

        # Construct hardware-ready TOU programme (exactly 6 standard slots for Deye/Sunsynk/Solis)
        charge_windows = [
            {"start": "00:00", "end": "04:00", "grid_charge": True, "target_soc": int(self.max_soc_pct)},
        ]
        export_windows = [
            {"start": "09:30", "end": "11:30", "force_discharge": True, "target_soc": int(self.reserve_soc_pct)},
            {"start": "17:00", "end": "20:00", "force_discharge": True, "target_soc": int(self.reserve_soc_pct)},
        ]
        tou_programme = build_tou_programme(charge_windows, export_windows, num_slots=6, reserve_soc=int(self.reserve_soc_pct))

        total_discharged_kwh = sum(s["discharge_kw"] for s in slots)
        degradation_cost_vnd = round(total_discharged_kwh * self.battery_deg_cost_vnd, 0)
        net_profit_vnd = round(max(0.0, net_savings_vnd - degradation_cost_vnd), 0)

        return OptimizationPlanResult(
            site_id=site_id,
            tariff_category=self.tariff_category,
            voltage_level=self.voltage_level,
            total_baseline_cost_vnd=round(baseline_cost_vnd, 0),
            total_optimized_cost_vnd=round(optimized_cost_vnd, 0),
            net_savings_vnd=round(net_savings_vnd, 0),
            savings_pct=round(savings_pct, 1),
            battery_degradation_cost_vnd=degradation_cost_vnd,
            net_profit_vnd=net_profit_vnd,
            slots_24h=slots,
            tou_programme=tou_programme,
        )

    def optimize_scenarios(
        self,
        site_id: str,
        solar_kw_24h: list[float],
        load_kw_24h: list[float],
        start_hour: int = 0,
        initial_soc_pct: float = 50.0,
    ) -> dict[str, Any]:
        """Compute multi-scenario projections (P10 / Nominal / P90) adapted from batpred/plan.py."""
        nominal = self.optimize_24h(site_id, solar_kw_24h, load_kw_24h, start_hour, initial_soc_pct)
        solar_p10 = [max(0.0, s * 0.45) for s in solar_kw_24h]
        p10 = self.optimize_24h(site_id, solar_p10, load_kw_24h, start_hour, initial_soc_pct)
        solar_p90 = [s * 1.35 for s in solar_kw_24h]
        p90 = self.optimize_24h(site_id, solar_p90, load_kw_24h, start_hour, initial_soc_pct)
        return {
            "nominal": nominal,
            "p10_gloomy": p10,
            "p90_sunny": p90,
            "robust_savings_vnd": min(nominal.net_savings_vnd, p10.net_savings_vnd),
        }


class FleetBalanceRequest(BaseModel):
    target_total_kw: float = Field(..., ge=0, description="Total target charge or discharge power in kW")
    mode: str = Field(default="charge", description="Target mode: charge, discharge, or idle")
    duration_hours: float = Field(default=1.0, ge=0.1, le=24.0)


def install_ems_optimizer(app, controller, user):
    """Register EMS optimization and multi-inverter balancing endpoints."""

    @app.get("/api/sites/{site_id}/ems-optimization")
    async def get_site_ems_optimization(
        site_id: str,
        category: str = "MANUFACTURING",
        voltage: str = "LOW_VOLTAGE_UNDER_22KV",
        battery_kwh: float = 15.0,
        max_charge_kw: float = 6.0,
        max_discharge_kw: float = 6.0,
        who=Depends(user) if user else None,
    ):
        if who and hasattr(who, "can_access") and not who.can_access(site_id):
            raise HTTPException(403, "site_access_denied")

        site = controller.store.get("site", site_id)
        if not site:
            raise HTTPException(404, "site_not_found")

        # Retrieve active inverters and real battery SOC from telemetry store
        devices = [
            d for d in controller.store.list("device")
            if d.get("site_id") == site_id and d.get("type", "").lower() in ("inverter", "hybrid")
        ]
        if not devices:
            raise HTTPException(422, "site_has_no_inverter_devices")

        # Determine primary inverter and extract current SOC
        from .domain import Device
        primary_dev = devices[0]
        dev_obj = Device.model_validate(primary_dev)
        latest = controller.latest(dev_obj) or {}
        samples = {p["metric"]: p["value"] for p in latest.get("samples", []) if p.get("value") is not None}
        current_soc = float(samples.get("battery_soc", 50.0))

        # Build 24h curves from real observations or require inputs
        solar_kw = [0.0] * 24

        load_kw = [0.0] * 24
        
        # Aggregate hourly samples from store
        for dev in devices:
            hist = controller.store.history(dev["id"])
            for s in hist:
                try:
                    ts_str = s.get("source_timestamp") or s.get("received_at")
                    if not ts_str:
                        continue
                    dt = datetime.fromisoformat(ts_str)
                    h = dt.hour
                    metric = s.get("metric")
                    val = float(s.get("value") or 0.0) / 1000.0  # W to kW
                    if metric in ("pv_power", "pv_w", "ppv"):
                        solar_kw[h] = max(solar_kw[h], val)
                    elif metric in ("load_power", "pload"):
                        load_kw[h] = max(load_kw[h], val)
                except (ValueError, TypeError):
                    continue

        # If zero historical data is available across all 24 hours, reject rather than inventing fake curves
        if sum(solar_kw) == 0.0 and sum(load_kw) == 0.0:
            raise HTTPException(
                422,
                "insufficient_measured_telemetry_for_site: verified solar or load observations required"
            )

        optimizer = EVNTOUOptimizer(
            tariff_category=category,
            voltage_level=voltage,
            battery_capacity_kwh=battery_kwh,
            max_charge_kw=max_charge_kw,
            max_discharge_kw=max_discharge_kw,
        )

        scenarios = optimizer.optimize_scenarios(
            site_id=site_id,
            solar_kw_24h=solar_kw,
            load_kw_24h=load_kw,
            initial_soc_pct=current_soc,
        )
        plan = scenarios["nominal"]

        return {
            "site_id": site_id,
            "tariff_category": plan.tariff_category,
            "voltage_level": plan.voltage_level,
            "total_baseline_cost_vnd": plan.total_baseline_cost_vnd,
            "total_optimized_cost_vnd": plan.total_optimized_cost_vnd,
            "net_savings_vnd": plan.net_savings_vnd,
            "savings_pct": plan.savings_pct,
            "battery_degradation_cost_vnd": plan.battery_degradation_cost_vnd,
            "net_profit_after_wear_vnd": plan.net_profit_vnd,
            "scenarios": {
                "nominal_savings_vnd": scenarios["nominal"].net_savings_vnd,
                "p10_gloomy_savings_vnd": scenarios["p10_gloomy"].net_savings_vnd,
                "p90_sunny_savings_vnd": scenarios["p90_sunny"].net_savings_vnd,
                "robust_guaranteed_savings_vnd": scenarios["robust_savings_vnd"],
            },
            "slots_24h": plan.slots_24h,
            "tou_programme": {
                "active_slots": len(plan.tou_programme),
                "slots": [
                    {
                        "index": idx + 1,
                        "time": s.start_hm,
                        "target_soc": s.target_soc,
                        "grid_charge": s.grid_charge,
                        "force_discharge": s.force_discharge,
                    }
                    for idx, s in enumerate(plan.tou_programme)
                ],
            },
        }

    @app.post("/api/sites/{site_id}/fleet-balance")
    async def post_site_fleet_balance(
        site_id: str,
        body: FleetBalanceRequest,
        who=Depends(user) if user else None,
    ):
        if who and hasattr(who, "can_access") and not who.can_access(site_id):
            raise HTTPException(403, "site_access_denied")

        devices = [
            d for d in controller.store.list("device")
            if d.get("site_id") == site_id and d.get("type", "").lower() in ("inverter", "hybrid")
        ]

        from .domain import Device

        members = []
        for d in devices:
            dev_obj = Device.model_validate(d)
            latest = controller.latest(dev_obj) or {}
            metrics = {p["metric"]: p["value"] for p in latest.get("samples", [])}
            soc = metrics.get("battery_soc", 50.0)
            members.append(
                InverterFleetMember(
                    device_id=d["id"],
                    rated_power_kw=float(d.get("rated_power_w", 5000)) / 1000.0,
                    battery_capacity_kwh=float(d.get("battery_capacity_wh", 10000)) / 1000.0,
                    current_soc_pct=soc,
                    max_charge_kw=5.0,
                    max_discharge_kw=5.0,
                    online=d.get("online", True),
                )
            )

        if not members:
            raise HTTPException(422, "no_active_inverters_found_for_site")

        res = FleetInverterBalancer.balance_fleet(
            members=members,
            target_total_kw=body.target_total_kw,
            mode=body.mode,
            duration_hours=body.duration_hours,
        )

        return {
            "site_id": site_id,
            "target_total_kw": res.total_target_kw,
            "mode": res.mode,
            "allocations": res.allocations,
            "projected_socs": res.projected_socs,
            "message": res.message,
        }

