"""Battery Health and Degradation Modeling Engine.

Provides State of Health (SOH) estimation, equivalent full cycle (EFC) counting,
depth of discharge (DoD) stress binning, Arrhenius temperature aging acceleration,
and warranty compliance verification for energy storage systems (BESS).
References: vpplib-dev battery degradation model patterns (GPL-3.0 referenced,
independent clean-room implementation) and standard LFP/NMC degradation curves.
"""

from __future__ import annotations

import math
from datetime import timedelta
from typing import Literal

from fastapi import Depends, HTTPException
from pydantic import BaseModel, Field

from .domain import utcnow


class BatterySpecification(BaseModel):
    """Specification of an energy storage battery pack."""

    nominal_capacity_kwh: float = Field(default=10.0, gt=0, description="Nameplate energy capacity in kWh")
    chemistry: Literal["LFP", "NMC", "LTO", "LEAD_ACID"] = "LFP"
    nominal_voltage: float = Field(default=51.2, gt=0, description="Nominal battery pack voltage (V)")
    warranty_cycles: int = Field(default=6000, ge=100, description="Rated warranty full cycles at 80% DOD")
    warranty_years: int = Field(default=10, ge=1, description="Rated warranty calendar duration in years")
    eol_soh_percent: float = Field(default=70.0, ge=50.0, le=80.0, description="End-of-life SOH threshold")
    rated_temp_c: float = Field(default=25.0, ge=10.0, le=45.0, description="Reference operating temperature in °C")


class BatteryHealthState(BaseModel):
    """Comprehensive battery degradation and health evaluation."""

    device_id: str
    nominal_capacity_kwh: float
    chemistry: str
    soh_percent: float = Field(ge=0.0, le=100.0)
    reported_bms_soh: float | None = None
    equivalent_full_cycles: float
    total_energy_throughput_kwh: float
    calendar_age_days: int
    operating_temp_c: float
    temperature_stress_factor: float
    cycle_count_by_dod: dict[str, int]
    degradation_breakdown: dict[str, float]
    estimated_remaining_cycles: int
    estimated_remaining_years: float
    warranty_status: Literal["WITHIN_WARRANTY", "EXCEEDED_CYCLES", "EXCEEDED_CALENDAR", "EXPIRED"]
    warranty_remaining_cycles: int
    warranty_remaining_days: int
    recommendations: list[str]


def calculate_temperature_stress(temp_c: float, ref_temp_c: float = 25.0) -> float:
    """Calculate Arrhenius thermal degradation acceleration factor.
    
    For Li-ion (especially LFP/NMC), operating above 25°C accelerates SEI layer growth
    and electrolyte consumption. Rate approximately doubles every 10°C rise above 25°C.
    Operating below 15°C under heavy charge can also induce lithium plating.
    """
    if temp_c <= ref_temp_c:
        # At or below reference temperature: baseline or mild cold stress under charging
        if temp_c < 10.0:
            return 1.15  # cold-induced kinetic resistance & plating risk
        return 1.0
    # Arrhenius doubling model: 2^((T - T_ref) / 10)
    delta = temp_c - ref_temp_c
    stress = math.pow(2.0, delta / 10.0)
    return round(min(stress, 5.0), 3)


def calculate_dod_stress_factor(dod_percent: float) -> float:
    """Calculate cycle aging penalty as a function of Depth of Discharge (DoD).
    
    Cycling at 100% DOD causes substantially more mechanical strain on active particles
    than shallow cycling (e.g. 50% DOD). Normalized to 80% DOD = 1.0.
    """
    clamped_dod = max(5.0, min(100.0, dod_percent))
    # Empirical power law for LFP: Stress ~ (DOD / 80)^1.4
    return round(math.pow(clamped_dod / 80.0, 1.4), 3)


def estimate_battery_health(
    device_id: str,
    spec: BatterySpecification,
    total_discharge_kwh: float,
    calendar_days: int,
    avg_temp_c: float = 28.0,
    reported_bms_soh: float | None = None,
    dod_distribution: dict[str, int] | None = None,
) -> BatteryHealthState:
    """Compute SOH, degradation breakdown, and remaining life estimation.
    
    Combines:
    1. Cyclic degradation based on Equivalent Full Cycles (EFC) and DoD distribution.
    2. Calendar degradation based on square root of time (diffusion-limited SEI growth).
    3. Temperature acceleration via Arrhenius factor.
    4. Harmonization with reported BMS internal SOH reading when available.
    """
    # 1. Equivalent Full Cycles (EFC)
    efc = total_discharge_kwh / spec.nominal_capacity_kwh if spec.nominal_capacity_kwh > 0 else 0.0
    efc = round(efc, 1)

    # 2. Temperature Stress
    temp_stress = calculate_temperature_stress(avg_temp_c, spec.rated_temp_c)

    # 3. Default DOD distribution if not provided
    if not dod_distribution:
        # Typical residential/commercial solar self-consumption profile
        dod_distribution = {
            "0-20%": max(0, int(efc * 0.15)),
            "20-50%": max(0, int(efc * 0.25)),
            "50-80%": max(0, int(efc * 0.40)),
            "80-100%": max(0, int(efc * 0.20)),
        }

    # 4. Cycle Degradation Calculation
    # Rated cycles to EOL (e.g. 6000 cycles to 70% SOH = 30% total fade, or ~0.005% per cycle at 80% DOD)
    total_allowable_fade = 100.0 - spec.eol_soh_percent
    fade_per_rated_cycle = total_allowable_fade / spec.warranty_cycles
    cycle_fade = efc * fade_per_rated_cycle * temp_stress

    # 5. Calendar Degradation Calculation
    # Square root of time model: Calendar fade ~ k_cal * sqrt(days) * temp_stress
    # Typically 1.5% - 2.0% per year at 25°C
    k_cal = 0.08  # ~1.5% after 365 days
    calendar_fade = k_cal * math.sqrt(max(0, calendar_days)) * (temp_stress * 0.7 + 0.3)

    # Combined physical model fade
    total_model_fade = cycle_fade + calendar_fade
    model_soh = max(spec.eol_soh_percent - 10.0, min(100.0, 100.0 - total_model_fade))

    # 6. Harmonize with reported BMS SOH if present
    if reported_bms_soh is not None and 50.0 <= reported_bms_soh <= 100.0:
        # Weighted fusion: 60% reported BMS Coulomb counting, 40% physical degradation model
        final_soh = round(0.6 * reported_bms_soh + 0.4 * model_soh, 1)
    else:
        final_soh = round(model_soh, 1)

    # 7. Remaining Useful Life (RUL)
    current_fade = 100.0 - final_soh
    remaining_fade = max(0.0, total_allowable_fade - current_fade)
    daily_efc = efc / max(1, calendar_days) if calendar_days > 0 else 1.0
    effective_daily_efc = max(0.1, min(3.0, daily_efc))

    if fade_per_rated_cycle > 0:
        remaining_cycles = int(remaining_fade / (fade_per_rated_cycle * temp_stress))
    else:
        remaining_cycles = spec.warranty_cycles

    remaining_years = round(remaining_cycles / (effective_daily_efc * 365.25), 1)

    # 8. Warranty Compliance
    warranty_total_days = spec.warranty_years * 365
    remaining_warranty_days = max(0, warranty_total_days - calendar_days)
    remaining_warranty_cycles = max(0, spec.warranty_cycles - int(efc))

    if calendar_days > warranty_total_days and efc > spec.warranty_cycles:
        warranty_status = "EXPIRED"
    elif calendar_days > warranty_total_days:
        warranty_status = "EXCEEDED_CALENDAR"
    elif efc > spec.warranty_cycles:
        warranty_status = "EXCEEDED_CYCLES"
    else:
        warranty_status = "WITHIN_WARRANTY"

    # 9. Engineering Action Recommendations
    recommendations: list[str] = []
    if avg_temp_c > 32.0:
        recommendations.append(
            f"Nhiệt độ vận hành trung bình ({avg_temp_c:.1f}°C) cao hơn mức thiết kế 25°C. "
            f"Hệ số lão hóa nhiệt tăng {temp_stress:.2f}x. Khuyến nghị bổ sung thông gió hoặc điều hòa phòng pin."
        )
    if final_soh < spec.eol_soh_percent + 5.0:
        recommendations.append(
            f"Dung lượng khả dụng SOH ({final_soh:.1f}%) đang tiến gần ngưỡng hết hạn sử dụng (EOL {spec.eol_soh_percent}%). "
            "Cần lập kế hoạch ngân sách thay thế hoặc tái điều chỉnh công suất xả."
        )
    if dod_distribution.get("80-100%", 0) / max(1, efc) > 0.5:
        recommendations.append(
            "Hơn 50% chu kỳ vận hành ở độ xả sâu >80% (DOD cao). Cài đặt DOD tối đa ở mức 80% có thể kéo dài tuổi thọ thêm 30%."
        )
    if not recommendations:
        recommendations.append("Pin đang vận hành trong điều kiện tối ưu theo tiêu chuẩn bảo hành nhà sản xuất.")

    return BatteryHealthState(
        device_id=device_id,
        nominal_capacity_kwh=spec.nominal_capacity_kwh,
        chemistry=spec.chemistry,
        soh_percent=final_soh,
        reported_bms_soh=reported_bms_soh,
        equivalent_full_cycles=efc,
        total_energy_throughput_kwh=round(total_discharge_kwh, 1),
        calendar_age_days=calendar_days,
        operating_temp_c=avg_temp_c,
        temperature_stress_factor=temp_stress,
        cycle_count_by_dod=dod_distribution,
        degradation_breakdown={
            "cycle_fade_percent": round(cycle_fade, 2),
            "calendar_fade_percent": round(calendar_fade, 2),
            "total_fade_percent": round(current_fade, 2),
        },
        estimated_remaining_cycles=max(0, remaining_cycles),
        estimated_remaining_years=max(0.0, remaining_years),
        warranty_status=warranty_status,
        warranty_remaining_cycles=remaining_warranty_cycles,
        warranty_remaining_days=remaining_warranty_days,
        recommendations=recommendations,
    )


def install_battery_health(app, controller, user):
    """Register FastAPI endpoints for Battery Health & Degradation Analysis."""

    @app.get("/api/devices/{device_id}/battery-health")
    def get_device_battery_health(device_id: str, who=Depends(user)):
        device = controller.store.get("device", device_id)
        if not device or not who.can_access(device["site_id"]):
            raise HTTPException(404, "device_not_found")

        from .observed_energy import accepted_points, integrate_directional_power

        now = utcnow()
        start = now - timedelta(days=7)
        rows = controller.store.report_samples(device_id, start, now, "battery_discharge_w", 10001)
        if len(rows) > 10000:
            raise HTTPException(422, "health_history_limit; reviewed_rollup_required")
        energy = integrate_directional_power(rows, "battery_discharge_w", start, now)
        measured = {}
        provenance = {}
        for metric, unit, target in (
            ("battery_soh", "%", "soh_percent"),
            ("battery_temp", "°C", "operating_temp_c"),
        ):
            observations = controller.store.report_samples(device_id, now - timedelta(minutes=15), now, metric, 10001)
            points = accepted_points(observations, metric, unit, now - timedelta(minutes=15), now)
            value = points[-1][1] if points else None
            if metric == "battery_soh" and value is not None and not 0 <= value <= 100:
                value = None
            measured[target] = value
            provenance[target] = points[-1][0].isoformat() if value is not None else None
        cap = device.get("battery_capacity_kwh")
        valid_capacity = isinstance(cap, (int, float)) and not isinstance(cap, bool) and math.isfinite(cap) and cap > 0
        throughput = energy["energy_kwh"]
        return {
            "device_id": device_id,
            "status": "MEASURED" if measured["soh_percent"] is not None else "INSUFFICIENT_DATA",
            **measured,
            "reported_bms_soh": measured["soh_percent"],
            "source_timestamps": provenance,
            "nominal_capacity_kwh": cap if valid_capacity else None,
            "equivalent_full_cycles": None,
            "observed_window_equivalent_cycles": throughput / cap if valid_capacity and throughput is not None else None,
            "observed_discharge_kwh": throughput,
            "coverage": energy["coverage"],
            "window_start": start.isoformat(),
            "window_end": now.isoformat(),
            "temperature_stress_factor": None,
            "estimated_remaining_years": None,
            "warranty_status": "UNKNOWN",
            "warranty_remaining_cycles": None,
            "warranty_remaining_days": None,
            "recommendations": ["Lifetime degradation and warranty require reviewed nameplate and lifetime history."],
        }

    @app.get("/api/sites/{site_id}/battery-health")
    def get_site_battery_health(site_id: str, who=Depends(user)):
        site = controller.store.get("site", site_id)
        if not site or not who.can_access(site_id):
            raise HTTPException(404, "site_not_found")
        devices = [d for d in controller.store.list("device") if d.get("site_id") == site_id
                   and (d.get("has_battery") or d.get("type", "").lower() in {"battery", "hybrid", "storage"})]
        results = [get_device_battery_health(d["id"], who) for d in devices]
        values = [r["soh_percent"] for r in results if r["soh_percent"] is not None]
        return {
            "site_id": site_id,
            "batteries_count": len(results),
            "batteries": results,
            "measured_batteries_count": len(values),
            "site_average_soh": sum(values) / len(values) if values and len(values) == len(results) else None,
        }
