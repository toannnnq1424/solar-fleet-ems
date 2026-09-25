"""Timeseries processing, LTTB downsampling, and solar energy/financial analytics.

Includes:
- LTTB (Largest-Triangle-Three-Buckets) downsampling algorithm for high-density charts.
- Trapezoidal numerical energy integration from instantaneous power telemetry.
- 3-tier TOU tariff financial calculator (EVN Industrial / Commercial schedules).
- Standard Performance Ratio (PR) and avoided CO2 emissions calculator.
"""

from __future__ import annotations

import math
from typing import Sequence

# Vietnam national grid average emission factor (kg CO2 per kWh)
VIETNAM_GRID_EMISSION_FACTOR = 0.7221

# Standard EVN Industrial Tariff (VND / kWh, excluding VAT)
EVN_INDUSTRIAL_TARIFF = {
    "peak": 3171,  # Giờ cao điểm (09:30-11:30, 17:00-20:00)
    "normal": 1738,  # Giờ bình thường (04:00-09:30, 11:30-17:00, 20:00-22:00)
    "off_peak": 1100,  # Giờ thấp điểm (22:00-04:00 hôm sau)
}


def lttb_downsample(data: Sequence[tuple[float, float]], threshold: int) -> list[tuple[float, float]]:
    """Downsample a timeseries using the Largest-Triangle-Three-Buckets (LTTB) algorithm.

    Preserves peaks, troughs, and visual trend while reducing point count.
    :param data: list of (timestamp_or_x, value_or_y) tuples, sorted by x.
    :param threshold: desired number of output points (must be >= 3).
    :return: downsampled list of (x, y) tuples.
    """
    data_len = len(data)
    if threshold >= data_len or threshold <= 2:
        return list(data)

    sampled = []
    # Bucket size: leave room for the start and end data points
    every = (data_len - 2) / (threshold - 2)

    a = 0  # Initial point
    sampled.append(data[a])

    for i in range(threshold - 2):
        # Calculate point average for next bucket (bucket c)
        avg_x = 0.0
        avg_y = 0.0
        avg_range_start = int(math.floor((i + 1) * every) + 1)
        avg_range_end = int(math.floor((i + 2) * every) + 1)
        avg_range_end = min(avg_range_end, data_len)

        avg_range_len = avg_range_end - avg_range_start
        if avg_range_len > 0:
            for j in range(avg_range_start, avg_range_end):
                avg_x += data[j][0]
                avg_y += data[j][1]
            avg_x /= avg_range_len
            avg_y /= avg_range_len
        else:
            avg_x = data[avg_range_start][0] if avg_range_start < data_len else data[-1][0]
            avg_y = data[avg_range_start][1] if avg_range_start < data_len else data[-1][1]

        # Get the range for this bucket (bucket b)
        range_offs = int(math.floor(i * every) + 1)
        range_to = int(math.floor((i + 1) * every) + 1)

        # Point a
        point_a_x = data[a][0]
        point_a_y = data[a][1]

        max_area = -1.0
        next_a = range_offs

        for j in range(range_offs, range_to):
            # Calculate triangle area over points a, point_b, and average_c
            area = (
                abs(
                    (point_a_x - avg_x) * (data[j][1] - point_a_y)
                    - (point_a_x - data[j][0]) * (avg_y - point_a_y)
                )
                * 0.5
            )
            if area > max_area:
                max_area = area
                next_a = j

        sampled.append(data[next_a])
        a = next_a

    # Always add the last point
    sampled.append(data[-1])
    return sampled


def integrate_power_to_energy(points: Sequence[tuple[float, float]]) -> float:
    """Calculate accumulated energy in kWh from instantaneous power points in W using trapezoidal rule.

    :param points: list of (timestamp_seconds, power_watts).
    :return: energy in kilowatt-hours (kWh).
    """
    if len(points) < 2:
        return 0.0

    energy_watt_seconds = 0.0
    for i in range(1, len(points)):
        dt = points[i][0] - points[i - 1][0]
        if 0 < dt <= 3600:  # Ignore gaps larger than 1 hour
            avg_power = (points[i][1] + points[i - 1][1]) * 0.5
            energy_watt_seconds += avg_power * dt

    return energy_watt_seconds / 3_600_000.0


def calculate_performance_ratio(
    actual_energy_kwh: float,
    capacity_kwp: float,
    poa_irradiance_kwh_m2: float,
    reference_irradiance: float = 1.0,
) -> float:
    """Calculate the Performance Ratio (PR) according to IEC 61724-1.

    PR = (Actual Energy / Nominal Capacity) / (Plane-of-Array Irradiance / Reference Irradiance)
    :return: PR percentage between 0.0 and 100.0 (or 0.0 if irradiance is zero).
    """
    if capacity_kwp <= 0 or poa_irradiance_kwh_m2 <= 0:
        return 0.0

    specific_yield = actual_energy_kwh / capacity_kwp
    reference_yield = poa_irradiance_kwh_m2 / reference_irradiance
    if reference_yield <= 0:
        return 0.0

    pr = (specific_yield / reference_yield) * 100.0
    return min(100.0, max(0.0, pr))


def calculate_financial_savings(
    pv_energy_kwh: float,
    self_consumption_pct: float,
    tariff: dict[str, int] | None = None,
) -> dict[str, float]:
    """Calculate estimated cost savings and carbon footprint avoided.

    :param pv_energy_kwh: total energy generated by solar.
    :param self_consumption_pct: percentage (0..100) used locally.
    :param tariff: dict with peak, normal, off_peak rates.
    :return: dict with self_consumed_kwh, exported_kwh, savings_vnd, avoided_co2_kg.
    """
    rates = tariff or EVN_INDUSTRIAL_TARIFF
    # Blended average daytime tariff rate (VND / kWh)
    blended_daytime_rate = (rates["peak"] * 0.35) + (rates["normal"] * 0.65)

    self_consumed_kwh = pv_energy_kwh * (self_consumption_pct / 100.0)
    exported_kwh = pv_energy_kwh - self_consumed_kwh

    # Savings = self-consumed solar electricity * blended tariff avoided
    savings_vnd = self_consumed_kwh * blended_daytime_rate
    avoided_co2_kg = pv_energy_kwh * VIETNAM_GRID_EMISSION_FACTOR

    return {
        "self_consumed_kwh": round(self_consumed_kwh, 2),
        "exported_kwh": round(exported_kwh, 2),
        "savings_vnd": round(savings_vnd, 0),
        "avoided_co2_kg": round(avoided_co2_kg, 2),
        "avoided_co2_tons": round(avoided_co2_kg / 1000.0, 3),
    }
