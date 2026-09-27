"""Explainable hourly baseline adapted from SEM's MIT HourlyProfile algorithm.

Copyright (c) 2025 belinea4071; see data/licenses/sem-community-MIT.txt.
Source: traktore-org/sem-community, analytics/consumption_predictor.py.
Changes: train from bounded verified history, actual dates/UTC buckets, explicit
missing values, sampling coverage and source isolation. This is not an optimizer
or a forecast-accuracy estimate, and never proposes or sends device commands.
"""

from __future__ import annotations

import math
from collections import defaultdict
from datetime import UTC, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from fastapi import Depends, HTTPException

from .domain import utcnow


class HourlyProfile:
    """SEM's exponentially weighted weekday/hour bins and same-hour fallback."""

    def __init__(self, alpha=0.3):
        if not 0 < alpha <= 1:
            raise ValueError("alpha must be in (0, 1]")
        self.alpha = alpha
        self.bins = {}
        self.counts = defaultdict(int)

    def update(self, dow, hour, value):
        if not 0 <= dow <= 6 or not 0 <= hour <= 23 or not math.isfinite(value) or value < 0:
            raise ValueError("invalid hourly observation")
        key = (dow, hour)
        self.bins[key] = (
            value if key not in self.bins else self.alpha * value + (1 - self.alpha) * self.bins[key]
        )
        self.counts[key] += 1

    def predict(self, dow, hour):
        key = (dow, hour)
        if key in self.bins:
            return self.bins[key], "WEEKDAY_HOUR", self.counts[key]
        values = [value for (_, h), value in self.bins.items() if h == hour]
        if values:
            return (
                sum(values) / len(values),
                "SAME_HOUR_FALLBACK",
                sum(count for (_, h), count in self.counts.items() if h == hour),
            )
        return None, "NO_OBSERVATIONS", 0


def baseline(rows: list[dict], timezone: str, now: datetime) -> dict:
    if now.tzinfo is None:
        raise ValueError("timezone-aware forecast timestamp required")
    zone = ZoneInfo(timezone)
    start = now.astimezone(UTC).replace(minute=0, second=0, microsecond=0)
    result = {
        "method": "HOURLY_EWMA",
        "timezone": timezone,
        "generated_at": now.isoformat(),
        "horizon_hours": 24,
        "accuracy": None,
        "dispatch_enabled": False,
        "metrics": {},
    }
    for metric in ("pv_w", "load_w"):
        valid = []
        for row in rows:
            if row["metric"] != metric or row["quality"] != "GOOD" or row["unit"] != "W":
                continue
            value = row["value"]
            if value is None or not math.isfinite(value) or value < 0 or not row["source_timestamp"]:
                continue
            stamp = datetime.fromisoformat(row["source_timestamp"])
            if stamp.tzinfo is not None and start - timedelta(days=7) <= stamp < start:
                valid.append((stamp.astimezone(UTC), value, row["binding_id"]))
        series = {"training_days": 0, "training_hours": 0, "points": [], "status": "COLD_START"}
        result["metrics"][metric] = series
        bindings = {binding for _, _, binding in valid}
        if len(bindings) != 1 or None in bindings:
            series["status"] = "SINGLE_VERIFIED_SOURCE_REQUIRED"
            continue
        # Equal weight to quarter-hour bins prevents a noisy high-rate source
        # from dominating an hourly average. A missing quarter stays missing.
        hours = defaultdict(lambda: defaultdict(list))
        seen = {}
        for stamp, value, _ in valid:
            if stamp in seen and seen[stamp] != value:
                series["status"] = "CONFLICTING_OBSERVATIONS"
                break
            seen[stamp] = value
        if series["status"] == "CONFLICTING_OBSERVATIONS":
            continue
        for stamp, value in seen.items():
            hours[stamp.replace(minute=0, second=0, microsecond=0)][stamp.minute // 15].append(value)
        model = HourlyProfile()
        days = set()
        latest = None
        for stamp, quarters in sorted(hours.items()):
            if len(quarters) < 3:
                continue
            local = stamp.astimezone(zone)
            hourly_mean = sum(sum(q) / len(q) for q in quarters.values()) / len(quarters)
            model.update(local.weekday(), local.hour, hourly_mean)
            days.add(local.date())
            series["training_hours"] += 1
            latest = stamp
        series["training_days"] = len(days)
        if len(days) < 3 or series["training_hours"] < 24:
            continue
        if latest is None or start - latest > timedelta(hours=3):
            series["status"] = "STALE_TRAINING_DATA"
            continue
        series["status"] = "BASELINE_ONLY"
        for offset in range(24):
            stamp = start + timedelta(hours=offset)
            local = stamp.astimezone(zone)
            value, method, observations = model.predict(local.weekday(), local.hour)
            series["points"].append(
                {
                    "timestamp": stamp.isoformat(),
                    "local_time": local.isoformat(),
                    "value_w": value,
                    "method": method,
                    "observations": observations,
                }
            )
    return result




# ============================================================================
# CLEAR-SKY SOLAR PV ESTIMATION & ECONOMIC DISPATCH OPTIMIZATION
# ============================================================================


def calculate_clearsky_pv_profile(
    latitude: float,
    longitude: float,
    peak_kwp: float,
    start_dt: datetime,
    hours: int = 24,
    performance_ratio: float = 0.82,
) -> list[dict[str, Any]]:
    """Compute physical clear-sky solar irradiance and PV output profile.
    
    Uses standard solar geometry (declination, equation of time, solar hour angle,
    and zenith angle) with atmospheric attenuation model.
    """
    profile = []
    # Approximate solar day of year
    day_of_year = start_dt.timetuple().tm_yday
    # Solar declination angle (radians)
    declination = math.radians(23.45 * math.sin(math.radians((360.0 / 365.0) * (284 + day_of_year))))
    lat_rad = math.radians(latitude)

    for h in range(hours):
        current = start_dt + timedelta(hours=h)
        # Local solar time approximation: LSTM = 15 * timezone_offset
        # For UTC+7 (Vietnam standard): standard meridian = 105 degrees
        lstm = 105.0
        # Equation of time (minutes)
        b = math.radians((360.0 / 365.0) * (day_of_year - 81))
        eot = 9.87 * math.sin(2 * b) - 7.53 * math.cos(b) - 1.5 * math.sin(b)
        time_offset = 4.0 * (longitude - lstm) + eot
        local_solar_hour = current.hour + (current.minute + time_offset) / 60.0
        # Hour angle (degrees)
        hour_angle = (local_solar_hour - 12.0) * 15.0
        ha_rad = math.radians(hour_angle)

        # Solar zenith angle: cos(theta_z) = sin(lat)*sin(dec) + cos(lat)*cos(dec)*cos(ha)
        cos_zenith = math.sin(lat_rad) * math.sin(declination) + math.cos(lat_rad) * math.cos(declination) * math.cos(ha_rad)

        if cos_zenith > 0.05:
            # Empirical clear sky global horizontal irradiance (W/m2)
            ghi = 1080.0 * math.pow(cos_zenith, 1.15)
            # PV output power: P_dc * (GHI / 1000) * PR
            pv_w = peak_kwp * 1000.0 * (ghi / 1000.0) * performance_ratio
            pv_w = round(max(0.0, pv_w), 1)
        else:
            ghi = 0.0
            pv_w = 0.0

        profile.append({
            "timestamp": current.isoformat(),
            "hour": current.hour,
            "ghi_w_per_m2": round(ghi, 1),
            "pv_power_w": pv_w,
        })

    return profile


def optimize_economic_dispatch(
    pv_profile: list[dict[str, Any]],
    load_profile: list[dict[str, Any]],
    battery_capacity_kwh: float,
    initial_soc_percent: float = 50.0,
    min_soc_percent: float = 20.0,
    max_soc_percent: float = 95.0,
    max_charge_power_w: float = 5000.0,
    max_discharge_power_w: float = 5000.0,
    roundtrip_efficiency: float = 0.92,
    timezone: str = "Asia/Ho_Chi_Minh",
) -> dict[str, Any]:
    """24-Hour Economic Battery Dispatch Optimizer under EVN TOU Tariffs.
    
    Minimizes grid import costs and peak demand surcharges by:
    1. Storing surplus solar generation (self-consumption maximization).
    2. Discharging during high-cost EVN Peak hours (09:30-11:30 & 17:00-20:00).
    3. Selective off-peak pre-charging if morning solar forecast is insufficient.
    """
    from .tariff_engine import EVN_TARIFF_TABLES, TariffTierSchedule
    zone = ZoneInfo(timezone)
    rates = EVN_TARIFF_TABLES["MANUFACTURING"]["MEDIUM_VOLTAGE_22_110KV"]

    soc = initial_soc_percent
    one_way_eff = math.sqrt(roundtrip_efficiency)
    usable_kwh = battery_capacity_kwh * ((max_soc_percent - min_soc_percent) / 100.0)

    points = []
    total_cost_without_ems = 0.0
    total_cost_with_ems = 0.0
    total_pv_kwh = 0.0
    total_load_kwh = 0.0
    total_grid_import_kwh = 0.0
    total_grid_export_kwh = 0.0

    steps = min(len(pv_profile), len(load_profile))
    for i in range(steps):
        pv_item = pv_profile[i]
        load_item = load_profile[i]
        dt = datetime.fromisoformat(pv_item["timestamp"])
        local = dt.astimezone(zone)
        tier = TariffTierSchedule.classify_hour(local)
        rate = rates[tier.lower()]

        pv_w = pv_item.get("pv_power_w", 0.0)
        load_w = load_item.get("value_w", 0.0)
        total_pv_kwh += (pv_w / 1000.0)
        total_load_kwh += (load_w / 1000.0)

        # Baseline without battery: unbuffered grid import
        net_load_w = load_w - pv_w
        unbuffered_import_w = max(0.0, net_load_w)
        cost_unbuffered = (unbuffered_import_w / 1000.0) * rate
        total_cost_without_ems += cost_unbuffered

        # Battery dispatch decision
        battery_w = 0.0  # + charge, - discharge
        available_discharge_kwh = (soc - min_soc_percent) / 100.0 * battery_capacity_kwh
        available_charge_kwh = (max_soc_percent - soc) / 100.0 * battery_capacity_kwh

        if net_load_w < 0:
            # Solar surplus: charge battery first
            surplus_w = abs(net_load_w)
            charge_power = min(surplus_w, max_charge_power_w)
            # Energy limit
            max_energy_w = (available_charge_kwh / one_way_eff) * 1000.0
            charge_power = min(charge_power, max_energy_w)
            battery_w = round(charge_power, 1)
            delta_soc = ((charge_power * one_way_eff) / 1000.0) / battery_capacity_kwh * 100.0
            soc = min(max_soc_percent, soc + delta_soc)
            grid_import_w = 0.0
            grid_export_w = round(surplus_w - charge_power, 1)
        else:
            # Deficit: need power
            grid_export_w = 0.0
            if tier == "PEAK":
                # High cost period: discharge aggressively
                discharge_power = min(net_load_w, max_discharge_power_w)
                max_energy_w = (available_discharge_kwh * one_way_eff) * 1000.0
                discharge_power = min(discharge_power, max_energy_w)
                battery_w = -round(discharge_power, 1)
                delta_soc = ((discharge_power / one_way_eff) / 1000.0) / battery_capacity_kwh * 100.0
                soc = max(min_soc_percent, soc - delta_soc)
                grid_import_w = round(net_load_w - discharge_power, 1)
            elif tier == "NORMAL" and soc > 45.0:
                # Moderate cost period: partial discharge preserving reserve
                discharge_power = min(net_load_w * 0.5, max_discharge_power_w)
                max_energy_w = (available_discharge_kwh * one_way_eff) * 1000.0
                discharge_power = min(discharge_power, max_energy_w)
                battery_w = -round(discharge_power, 1)
                delta_soc = ((discharge_power / one_way_eff) / 1000.0) / battery_capacity_kwh * 100.0
                soc = max(min_soc_percent, soc - delta_soc)
                grid_import_w = round(net_load_w - discharge_power, 1)
            elif tier == "OFF_PEAK" and soc < 35.0:
                # Cheap grid hours: pre-charge battery up to 60% for morning peak
                charge_power = min(max_charge_power_w * 0.5, (available_charge_kwh / one_way_eff) * 1000.0)
                battery_w = round(charge_power, 1)
                delta_soc = ((charge_power * one_way_eff) / 1000.0) / battery_capacity_kwh * 100.0
                soc = min(max_soc_percent, soc + delta_soc)
                grid_import_w = round(net_load_w + charge_power, 1)
            else:
                battery_w = 0.0
                grid_import_w = round(net_load_w, 1)

        total_grid_import_kwh += (grid_import_w / 1000.0)
        total_grid_export_kwh += (grid_export_w / 1000.0)
        cost_ems = (grid_import_w / 1000.0) * rate
        total_cost_with_ems += cost_ems

        points.append({
            "timestamp": dt.isoformat(),
            "local_time": local.isoformat(),
            "hour": local.hour,
            "tariff_tier": tier,
            "tariff_rate_vnd": rate,
            "pv_power_w": pv_w,
            "load_power_w": load_w,
            "battery_power_w": battery_w,
            "battery_soc_percent": round(soc, 1),
            "grid_import_w": grid_import_w,
            "grid_export_w": grid_export_w,
            "cost_without_ems_vnd": round(cost_unbuffered, 0),
            "cost_with_ems_vnd": round(cost_ems, 0),
            "hourly_savings_vnd": round(max(0.0, cost_unbuffered - cost_ems), 0),
        })

    savings_vnd = max(0.0, total_cost_without_ems - total_cost_with_ems)
    savings_pct = (savings_vnd / total_cost_without_ems * 100.0) if total_cost_without_ems > 0 else 0.0

    return {
        "horizon_hours": steps,
        "battery_capacity_kwh": battery_capacity_kwh,
        "usable_capacity_kwh": round(usable_kwh, 1),
        "total_pv_generation_kwh": round(total_pv_kwh, 1),
        "total_load_consumption_kwh": round(total_load_kwh, 1),
        "total_grid_import_kwh": round(total_grid_import_kwh, 1),
        "total_grid_export_kwh": round(total_grid_export_kwh, 1),
        "total_cost_without_ems_vnd": round(total_cost_without_ems, 0),
        "total_cost_with_ems_vnd": round(total_cost_with_ems, 0),
        "total_savings_vnd": round(savings_vnd, 0),
        "savings_percentage": round(savings_pct, 1),
        "dispatch_points": points,
    }


def install_forecast_baseline(app, controller, user):
    @app.get("/api/devices/{device_id}/forecast-baseline")
    def forecast(device_id: str, who=Depends(user)):
        device = controller.store.get("device", device_id)
        if not device or not who.can_access(device["site_id"]):
            raise HTTPException(404, "device_not_found")
        site = controller.store.get("site", device["site_id"])
        now = utcnow()
        rows = []
        for metric in ("pv_w", "load_w"):
            selected = controller.store.report_samples(device_id, now - timedelta(days=7), now, metric, 10001)
            if len(selected) > 10000:
                raise HTTPException(422, "forecast_history_limit; use a reviewed rollup before training")
            rows.extend(selected)
        return baseline(rows, site.get("timezone", "UTC"), now)

    @app.get("/api/sites/{site_id}/dispatch-schedule")
    def site_dispatch_schedule(site_id: str, who=Depends(user)):
        site = controller.store.get("site", site_id)
        if not site or not who.can_access(site_id):
            raise HTTPException(404, "site_not_found")

        from .observed_energy import accepted_points
        from .predbat_planner import BatterySpecs, PredbatPlanner

        # One reviewed measurement boundary avoids summing overlapping meters.
        device_id = site.get("dispatch_device_id")
        device = controller.store.get("device", device_id) if device_id else None
        if not device or device.get("site_id") != site_id:
            raise HTTPException(422, "site_dispatch_device_required")
        trained = forecast(device_id, who)
        profiles = [trained["metrics"][key] for key in ("pv_w", "load_w")]
        if any(len(profile["points"]) != 24 or any(p["value_w"] is None for p in profile["points"]) for profile in profiles):
            raise HTTPException(422, "complete_verified_history_forecast_required")
        config = site.get("dispatch_config") or {}
        required = tuple(BatterySpecs.__dataclass_fields__)
        if any(key not in config for key in required):
            raise HTTPException(422, "reviewed_battery_dispatch_specifications_required")
        if any(isinstance(config[k], bool) or not isinstance(config[k], (int, float))
               or not math.isfinite(config[k]) for k in required):
            raise HTTPException(422, "finite_battery_specifications_required")
        specs = BatterySpecs(**{key: config[key] for key in required})
        if not (0 < specs.usable_kwh <= specs.capacity_kwh and specs.max_charge_kw > 0
                and specs.max_discharge_kw > 0 and 0 < specs.charge_efficiency <= 1
                and 0 < specs.discharge_efficiency <= 1 and specs.rated_cycle_life > 0
                and specs.replacement_cost_usd >= 0
                and 0 <= specs.min_soc_pct <= specs.reserve_soc_pct < specs.max_soc_pct <= 100):
            raise HTTPException(422, "invalid_battery_specifications")
        now = utcnow()
        rows = controller.store.report_samples(device_id, now - timedelta(minutes=15), now, "battery_soc", 10001)
        soc = accepted_points(rows, "battery_soc", "%", now - timedelta(minutes=15), now)
        if not soc or not 0 <= soc[-1][1] <= 100:
            raise HTTPException(422, "fresh_verified_battery_soc_required")
        # Rates must be configured per actual UTC hour, with currency and provenance.
        prices = config.get("hourly_prices", [])
        timestamps = [point["timestamp"] for point in profiles[0]["points"]]
        if (config.get("currency") != "USD" or not config.get("tariff_source")
                or len(prices) != 24 or [p.get("timestamp") for p in prices] != timestamps):
            raise HTTPException(422, "aligned_effective_usd_tariff_required")
        for price in prices:
            for key in ("import_per_kwh", "export_per_kwh"):
                value = price.get(key)
                if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
                    raise HTTPException(422, "finite_tariff_required")
        result = PredbatPlanner(specs).plan_horizon(
            [p["value_w"] / 1000 for p in profiles[0]["points"]],
            [p["value_w"] / 1000 for p in profiles[1]["points"]],
            [p["import_per_kwh"] for p in prices],
            [p["export_per_kwh"] for p in prices],
            current_soc_pct=soc[-1][1],
        )
        result.update(status="ESTIMATED", dispatch_enabled=False, device_id=device_id,
                      forecast_method=trained["method"], source_timestamp=soc[-1][0].isoformat(),
                      tariff_source=config["tariff_source"], currency="USD")
        for slot, timestamp in zip(result["slots"], timestamps):
            slot["timestamp"] = timestamp
        return result
