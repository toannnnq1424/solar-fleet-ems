"""EVN Time-of-Use Tariff, Power Factor Penalty, and Peak Shaving Engine.

Implements the official Vietnamese EVN electricity tariff system (Decision 2699/QĐ-BCT,
Decision 14/2023/QĐ-TTg, and Circular 15/2014/TT-BCT on reactive power surcharge).
Provides TOU tier classification (Peak, Normal, Off-peak), bill simulation,
power factor (cos phi) penalty calculation, and battery peak-shaving dispatch advice.
References: sem-community tariff provider patterns (MIT referenced, independent implementation).
"""

from __future__ import annotations

import math
from datetime import datetime, time, timedelta
from typing import Any, Literal
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException, Request
from pydantic import BaseModel, Field

from .domain import utcnow

# ============================================================================
# EVN ELECTRICITY TARIFF RATES (VND / kWh, before 8% or 10% VAT)
# Source: EVN Retail Electricity Tariff Schedule (Decision 2699/QĐ-BCT)
# ============================================================================

EVN_TARIFF_TABLES: dict[str, dict[str, dict[str, float]]] = {
    "MANUFACTURING": {
        "HIGH_VOLTAGE_110KV": {
            "off_peak": 1044.0,
            "normal": 1658.0,
            "peak": 2973.0,
        },
        "MEDIUM_VOLTAGE_22_110KV": {
            "off_peak": 1092.0,
            "normal": 1707.0,
            "peak": 3072.0,
        },
        "LOW_VOLTAGE_UNDER_22KV": {
            "off_peak": 1152.0,
            "normal": 1822.0,
            "peak": 3254.0,
        },
    },
    "COMMERCIAL_BUSINESS": {
        "HIGH_VOLTAGE_110KV": {
            "off_peak": 1478.0,
            "normal": 2623.0,
            "peak": 4545.0,
        },
        "MEDIUM_VOLTAGE_22_110KV": {
            "off_peak": 1640.0,
            "normal": 2777.0,
            "peak": 4707.0,
        },
        "LOW_VOLTAGE_UNDER_22KV": {
            "off_peak": 1770.0,
            "normal": 2866.0,
            "peak": 4926.0,
        },
    },
    "ADMINISTRATIVE": {
        "MEDIUM_VOLTAGE": {
            "off_peak": 1806.0,
            "normal": 1806.0,
            "peak": 1806.0,
        },
        "LOW_VOLTAGE": {
            "off_peak": 1903.0,
            "normal": 1903.0,
            "peak": 1903.0,
        },
    },
}


class TariffTierSchedule:
    """EVN Standard Time-of-Use schedule definition."""

    @staticmethod
    def classify_hour(local_dt: datetime) -> Literal["PEAK", "NORMAL", "OFF_PEAK"]:
        """Classify a given local datetime into EVN TOU tariff period.
        
        - Off-peak (Giờ thấp điểm): 22:00 to 04:00 (Every day Monday through Sunday).
        - Peak (Giờ cao điểm):
            Monday through Saturday:
              Morning peak: 09:30 - 11:30
              Evening peak: 17:00 - 20:00
            Sunday: No peak hours (Sunday has only Normal and Off-peak).
        - Normal (Giờ bình thường): All other hours.
        """
        weekday = local_dt.weekday()  # 0=Monday, 6=Sunday
        t = local_dt.time()

        # 1. Off-peak: 22:00 to 04:00
        if t >= time(22, 0) or t < time(4, 0):
            return "OFF_PEAK"

        # 2. Sunday has no peak hours -> always Normal outside off-peak
        if weekday == 6:
            return "NORMAL"

        # 3. Monday through Saturday Peak windows
        # Morning peak: 09:30 - 11:30
        if time(9, 30) <= t < time(11, 30):
            return "PEAK"
        # Evening peak: 17:00 - 20:00
        if time(17, 0) <= t < time(20, 0):
            return "PEAK"

        # 4. Otherwise: Normal hours
        return "NORMAL"


class PowerFactorAnalysis(BaseModel):
    """Evaluation of power factor and Circular 15/2014/TT-BCT penalty."""

    cos_phi: float = Field(ge=0.0, le=1.0)
    tan_phi: float
    penalty_ratio: float = Field(ge=0.0, description="k surcharge multiplier on active energy")
    penalty_percent: float = Field(ge=0.0, description="k percentage surcharge")
    is_compliant: bool = Field(description="True if cos phi >= 0.90")
    estimated_penalty_vnd: float
    reactive_compensation_needed_kvar: float
    advice: str


def calculate_power_factor_penalty(
    active_energy_kwh: float,
    reactive_energy_kvarh: float,
    active_bill_vnd: float,
) -> PowerFactorAnalysis:
    """Calculate reactive power purchase surcharge per Circular 15/2014/TT-BCT.
    
    Formula:
      cos(phi) = P / sqrt(P^2 + Q^2)
      If cos(phi) < 0.90:
        k = (0.90 / cos(phi) - 1.0) * 100%
        Surcharge = Active Bill * k
    """
    p = max(0.0, active_energy_kwh)
    q = max(0.0, reactive_energy_kvarh)
    apparent = math.sqrt(p * p + q * q)

    if apparent <= 0 or p <= 0:
        cos_phi = 1.0
        tan_phi = 0.0
    else:
        cos_phi = round(p / apparent, 4)
        tan_phi = round(q / p, 4)

    if cos_phi >= 0.90:
        penalty_ratio = 0.0
        penalty_pct = 0.0
        is_compliant = True
        penalty_vnd = 0.0
        comp_needed = 0.0
        advice = "Hệ số công suất đạt chuẩn quy định EVN (cos φ ≥ 0.90). Không phát sinh tiền mua công suất phản kháng."
    else:
        # k = (0.90 / cos phi) - 1.0
        penalty_ratio = round((0.90 / cos_phi) - 1.0, 4)
        penalty_pct = round(penalty_ratio * 100.0, 2)
        is_compliant = False
        penalty_vnd = round(active_bill_vnd * penalty_ratio, 0)
        # Q_target to reach cos phi = 0.90: tan(acos(0.90)) = 0.4843
        target_q = p * 0.4843
        comp_needed = round(max(0.0, q - target_q), 1)
        advice = (
            f"Hệ số công suất cos φ = {cos_phi:.2f} < 0.90 vi phạm Thông tư 15/2014/TT-BCT. "
            f"Tỷ lệ phạt k = {penalty_pct}%, tương đương phụ thu ước tính {penalty_vnd:,.0f} VNĐ. "
            f"Cần bù thêm tối thiểu {comp_needed:.1f} kvar công suất phản kháng hoặc điều chỉnh góc kích biến tần PV."
        )

    return PowerFactorAnalysis(
        cos_phi=cos_phi,
        tan_phi=tan_phi,
        penalty_ratio=penalty_ratio,
        penalty_percent=penalty_pct,
        is_compliant=is_compliant,
        estimated_penalty_vnd=penalty_vnd,
        reactive_compensation_needed_kvar=comp_needed,
        advice=advice,
    )


class TariffAnalysisResult(BaseModel):
    """Full site tariff and cost analysis."""

    site_id: str
    customer_class: str
    voltage_tier: str
    analysis_period_days: int
    energy_consumption_kwh: dict[str, float]
    energy_cost_vnd: dict[str, float]
    total_active_energy_kwh: float
    total_active_bill_vnd: float
    effective_rate_vnd_per_kwh: float
    solar_savings_vnd: float
    power_factor_analysis: PowerFactorAnalysis
    peak_shaving_opportunity: dict[str, Any]


def analyze_site_tariff(
    site_id: str,
    customer_class: str = "MANUFACTURING",
    voltage_tier: str = "MEDIUM_VOLTAGE_22_110KV",
    hourly_grid_import_kwh: list[tuple[datetime, float]] | None = None,
    hourly_solar_kwh: list[tuple[datetime, float]] | None = None,
    total_reactive_kvarh: float = 0.0,
    timezone: str = "Asia/Ho_Chi_Minh",
) -> TariffAnalysisResult:
    """Analyze electricity cost under EVN TOU structure and peak-shaving potential."""
    rates = EVN_TARIFF_TABLES.get(customer_class, EVN_TARIFF_TABLES["MANUFACTURING"]).get(
        voltage_tier, EVN_TARIFF_TABLES["MANUFACTURING"]["MEDIUM_VOLTAGE_22_110KV"]
    )
    zone = ZoneInfo(timezone)

    consumption = {"PEAK": 0.0, "NORMAL": 0.0, "OFF_PEAK": 0.0}
    solar_by_tier = {"PEAK": 0.0, "NORMAL": 0.0, "OFF_PEAK": 0.0}
    peak_demand_kw = 0.0
    peak_hours_demand: list[float] = []

    if hourly_grid_import_kwh:
        for dt, kwh in hourly_grid_import_kwh:
            local = dt.astimezone(zone)
            tier = TariffTierSchedule.classify_hour(local)
            consumption[tier] += max(0.0, kwh)
            power_kw = kwh  # 1 hour interval -> kW = kWh
            if power_kw > peak_demand_kw:
                peak_demand_kw = power_kw
            if tier == "PEAK":
                peak_hours_demand.append(power_kw)

    if hourly_solar_kwh:
        for dt, kwh in hourly_solar_kwh:
            local = dt.astimezone(zone)
            tier = TariffTierSchedule.classify_hour(local)
            solar_by_tier[tier] += max(0.0, kwh)

    total_kwh = sum(consumption.values())
    cost_peak = consumption["PEAK"] * rates["peak"]
    cost_normal = consumption["NORMAL"] * rates["normal"]
    cost_off_peak = consumption["OFF_PEAK"] * rates["off_peak"]
    total_bill = cost_peak + cost_normal + cost_off_peak

    effective_rate = total_bill / total_kwh if total_kwh > 0 else rates["normal"]

    # Solar savings: solar energy produced during peak/normal replaces expensive grid import
    solar_savings = (
        solar_by_tier["PEAK"] * rates["peak"]
        + solar_by_tier["NORMAL"] * rates["normal"]
        + solar_by_tier["OFF_PEAK"] * rates["off_peak"]
    )

    # Power Factor Evaluation
    pf_analysis = calculate_power_factor_penalty(
        active_energy_kwh=total_kwh,
        reactive_energy_kvarh=total_reactive_kvarh,
        active_bill_vnd=total_bill,
    )

    # Peak Shaving Opportunity Analysis
    avg_peak_demand = sum(peak_hours_demand) / len(peak_hours_demand) if peak_hours_demand else 0.0
    shavable_peak_kw = max(0.0, peak_demand_kw - avg_peak_demand)
    arbitrage_spread_vnd = rates["peak"] - rates["off_peak"]

    peak_shaving = {
        "max_demand_peak_kw": round(peak_demand_kw, 1),
        "average_peak_period_kw": round(avg_peak_demand, 1),
        "recommended_battery_discharge_kw": round(shavable_peak_kw, 1),
        "price_spread_vnd_per_kwh": round(arbitrage_spread_vnd, 0),
        "estimated_monthly_arbitrage_vnd": round(shavable_peak_kw * 4.0 * arbitrage_spread_vnd * 26.0 * 0.85, 0),
        "peak_hours_definition": "Mon-Sat 09:30-11:30 & 17:00-20:00 (EVN Giờ cao điểm)",
    }

    return TariffAnalysisResult(
        site_id=site_id,
        customer_class=customer_class,
        voltage_tier=voltage_tier,
        analysis_period_days=30,
        energy_consumption_kwh={
            "peak_kwh": round(consumption["PEAK"], 1),
            "normal_kwh": round(consumption["NORMAL"], 1),
            "off_peak_kwh": round(consumption["OFF_PEAK"], 1),
        },
        energy_cost_vnd={
            "peak_vnd": round(cost_peak, 0),
            "normal_vnd": round(cost_normal, 0),
            "off_peak_vnd": round(cost_off_peak, 0),
        },
        total_active_energy_kwh=round(total_kwh, 1),
        total_active_bill_vnd=round(total_bill, 0),
        effective_rate_vnd_per_kwh=round(effective_rate, 1),
        solar_savings_vnd=round(solar_savings, 0),
        power_factor_analysis=pf_analysis,
        peak_shaving_opportunity=peak_shaving,
    )


def install_tariff_engine(app, controller, user):
    """Register FastAPI endpoints for EVN Tariff Engine and Peak Shaving Advisor."""

    @app.get("/api/tariff/evn-rates")
    def get_evn_rates():
        """Retrieve current EVN official retail electricity tariffs."""
        return {
            "authority": "EVN - Quyết định 2699/QĐ-BCT & 14/2023/QĐ-TTg",
            "effective_date": "2024-10-11",
            "currency": "VND",
            "vat_rate": "8% or 10%",
            "schedules": EVN_TARIFF_TABLES,
            "tou_definitions": {
                "OFF_PEAK": "22:00 - 04:00 (All days)",
                "PEAK": "09:30 - 11:30 & 17:00 - 20:00 (Mon - Sat only, Sunday no peak)",
                "NORMAL": "All other hours",
            },
        }

    @app.get("/api/sites/{site_id}/tariff-analysis")
    def get_site_tariff_analysis(
        site_id: str,
        request: Request,
        customer_class: str = "MANUFACTURING",
        voltage_tier: str = "MEDIUM_VOLTAGE_22_110KV",
        who=Depends(user),
    ):
        from .import_tariffs import price_observations
        from .observed_energy import integrate_directional_power
        from .security import require_session_principal

        now = utcnow()
        start = now - timedelta(days=30)
        # Do not sum overlapping inverter/meter boundaries. The billing meter
        # must be explicitly selected in site configuration.
        with controller.store.transaction():
            require_session_principal(controller.store, request.cookies.get("solar_session"), who)
            site = controller.store.get("site", site_id)
            if not site or not who.can_access(site_id):
                raise HTTPException(404, "site_not_found")
            meter_id = site.get("billing_meter_device_id")
            meter = controller.store.get("device", meter_id) if meter_id else None
            if not meter or meter.get("site_id") != site_id:
                raise HTTPException(422, "site_billing_meter_required")
            rows = controller.store.report_samples(meter_id, start, now, "grid_import_w", 10001)
            revision = controller.store.object_revisions({"site": [site_id]})["site"][site_id]
        if len(rows) > 10000:
            raise HTTPException(422, "tariff_history_limit; reviewed_rollup_required")
        result = integrate_directional_power(rows, "grid_import_w", start, now)
        costs = price_observations(result, site.get("import_tariff_versions", []))
        return {
            **costs,
            "site_revision": revision,
            "method": result["method"],
            "binding_ids": sorted({r["binding_id"] for r in rows if r.get("binding_id")}),
            "priced_coverage": costs["priced_seconds"] / (now - start).total_seconds(),
            "site_id": site_id,
            "status": "PARTIAL_OBSERVATIONS" if result["energy_kwh"] is not None else "INSUFFICIENT_DATA",
            "meter_device_id": meter_id,
            "window_start": start.isoformat(),
            "window_end": now.isoformat(),
            "observed_import_kwh": result["energy_kwh"],
            "coverage": result["coverage"],
            "total_active_bill_vnd": None,
            "solar_savings_vnd": None,
            "power_factor_analysis": None,
            "peak_shaving_opportunity": None,
            "reason": "Observed import cost estimate only; unaligned or unpriced intervals excluded. Not a utility bill.",
        }
