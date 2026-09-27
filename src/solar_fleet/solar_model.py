"""Photovoltaic conversion and solar irradiance model.

Independently implemented for Solar Fleet EMS.
Physical models based on published engineering references:
- SAPM/PVWatts cell temperature model (Sandia National Laboratories)
- Clear-sky GHI from solar position (Spencer, Duffie & Beckman)
- Temperature coefficient derate for c-Si modules
- Hourly GTI to period kWh conversion with trapezoidal integration

Inspiration from batpred-main solar_model.py (personal-use license —
concepts only, no code copied) and documented behavior in
the virtual-power-plant-main (MIT) forecasting module.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------

# PVWatts / SAPM cell temperature model constants (glass/glass, open rack)
_SAPM_A = -3.47
_SAPM_B = -0.0594
_SAPM_DELTA_T = 3.0

# c-Si temperature coefficient: -0.4%/°C relative to STC (25°C)
_TEMP_COEFF = 0.004
_STC_TEMP_C = 25.0

# Solar constant (W/m²)
_SOLAR_CONSTANT = 1361.0

# Standard test conditions irradiance
_STC_IRRADIANCE = 1000.0


# ---------------------------------------------------------------------------
# Solar position calculation
# ---------------------------------------------------------------------------

@dataclass
class SolarPosition:
    """Solar position angles."""

    zenith_deg: float
    elevation_deg: float
    azimuth_deg: float
    hour_angle_deg: float
    declination_deg: float
    equation_of_time_min: float

    @property
    def airmass(self) -> float:
        """Simple Kasten-Young airmass model."""
        if self.elevation_deg <= 0:
            return 0.0
        el_rad = math.radians(self.elevation_deg)
        # Kasten-Young formula
        return 1.0 / (math.sin(el_rad) + 0.50572 * (self.elevation_deg + 6.07995) ** (-1.6364))


def solar_position(
    latitude: float,
    longitude: float,
    dt: datetime,
) -> SolarPosition:
    """Calculate solar position for a given location and time.

    Uses Spencer's equation for declination and equation of time.

    Parameters
    ----------
    latitude : float
        Latitude in degrees (positive north).
    longitude : float
        Longitude in degrees (positive east).
    dt : datetime
        UTC datetime.

    Returns
    -------
    SolarPosition
        Solar angles.
    """
    # Day of year
    if dt.tzinfo is not None:
        dt_utc = dt.astimezone(timezone.utc)
    else:
        dt_utc = dt

    doy = dt_utc.timetuple().tm_yday
    hour = dt_utc.hour + dt_utc.minute / 60.0 + dt_utc.second / 3600.0

    # Fractional year (radians)
    gamma = 2.0 * math.pi / 365.0 * (doy - 1 + (hour - 12) / 24.0)

    # Equation of time (minutes)
    eot = 229.18 * (
        0.000075
        + 0.001868 * math.cos(gamma)
        - 0.032077 * math.sin(gamma)
        - 0.014615 * math.cos(2 * gamma)
        - 0.04089 * math.sin(2 * gamma)
    )

    # Solar declination (radians)
    decl = (
        0.006918
        - 0.399912 * math.cos(gamma)
        + 0.070257 * math.sin(gamma)
        - 0.006758 * math.cos(2 * gamma)
        + 0.000907 * math.sin(2 * gamma)
        - 0.002697 * math.cos(3 * gamma)
        + 0.00148 * math.sin(3 * gamma)
    )
    decl_deg = math.degrees(decl)

    # Solar time
    time_offset = eot + 4 * longitude  # minutes
    tst = hour * 60 + time_offset  # true solar time in minutes
    ha = (tst / 4.0) - 180.0  # hour angle in degrees
    ha_rad = math.radians(ha)

    lat_rad = math.radians(latitude)

    # Solar zenith angle
    cos_zenith = (
        math.sin(lat_rad) * math.sin(decl)
        + math.cos(lat_rad) * math.cos(decl) * math.cos(ha_rad)
    )
    cos_zenith = max(-1.0, min(1.0, cos_zenith))
    zenith = math.degrees(math.acos(cos_zenith))
    elevation = 90.0 - zenith

    # Solar azimuth
    if math.cos(math.radians(zenith)) > 0:
        cos_azimuth = (
            (math.sin(decl) - math.sin(lat_rad) * cos_zenith)
            / (math.cos(lat_rad) * math.sin(math.radians(zenith)))
        )
        cos_azimuth = max(-1.0, min(1.0, cos_azimuth))
        azimuth = math.degrees(math.acos(cos_azimuth))
        if ha > 0:
            azimuth = 360 - azimuth
    else:
        azimuth = 180.0

    return SolarPosition(
        zenith_deg=round(zenith, 4),
        elevation_deg=round(elevation, 4),
        azimuth_deg=round(azimuth, 4),
        hour_angle_deg=round(ha, 4),
        declination_deg=round(decl_deg, 4),
        equation_of_time_min=round(eot, 4),
    )


# ---------------------------------------------------------------------------
# Clear-sky irradiance models
# ---------------------------------------------------------------------------

def clear_sky_ghi(
    latitude: float,
    longitude: float,
    dt: datetime,
    altitude_m: float = 0.0,
) -> float:
    """Estimate clear-sky Global Horizontal Irradiance (GHI).

    Uses a simplified Ineichen-Perez model with altitude correction.

    Parameters
    ----------
    latitude : float
        Latitude in degrees.
    longitude : float
        Longitude in degrees.
    dt : datetime
        UTC datetime.
    altitude_m : float
        Site altitude in meters.

    Returns
    -------
    float
        Clear-sky GHI in W/m².
    """
    pos = solar_position(latitude, longitude, dt)

    if pos.elevation_deg <= 0:
        return 0.0

    # Altitude correction for atmospheric pressure
    p_ratio = math.exp(-altitude_m / 8500.0)

    # Optical depth (simplified Linke turbidity = 3.0 for typical conditions)
    linke_turbidity = 3.0

    am = pos.airmass * p_ratio  # pressure-corrected airmass

    # Ineichen clear-sky model (simplified)
    # Direct normal irradiance
    if am > 0:
        cg1 = 5.09e-5 * altitude_m + 0.868
        cg2 = 3.92e-5 * altitude_m + 0.0387
        dni = max(0, _SOLAR_CONSTANT * cg1 * math.exp(-cg2 * am * (linke_turbidity - 0.5)))
    else:
        dni = 0.0

    # Diffuse horizontal irradiance
    sin_el = math.sin(math.radians(pos.elevation_deg))
    dhi = max(0, 130.2 * linke_turbidity * sin_el)

    # GHI = DNI * cos(zenith) + DHI
    cos_z = math.cos(math.radians(pos.zenith_deg))
    ghi = max(0, dni * cos_z + dhi)

    return round(ghi, 2)


def clear_sky_profile_24h(
    latitude: float,
    longitude: float,
    date: datetime,
    altitude_m: float = 0.0,
    interval_minutes: int = 60,
) -> List[Dict[str, Any]]:
    """Generate a 24-hour clear-sky GHI profile.

    Parameters
    ----------
    latitude, longitude : float
        Site coordinates.
    date : datetime
        UTC date (time portion ignored; starts from midnight).
    altitude_m : float
        Site altitude.
    interval_minutes : int
        Time resolution.

    Returns
    -------
    list of dict
        Each with 'hour', 'ghi_wm2', 'elevation_deg'.
    """
    base = datetime(date.year, date.month, date.day, tzinfo=timezone.utc)
    steps = 24 * 60 // interval_minutes
    profile = []

    for i in range(steps):
        dt = base + timedelta(minutes=i * interval_minutes)
        ghi = clear_sky_ghi(latitude, longitude, dt, altitude_m)
        pos = solar_position(latitude, longitude, dt)
        profile.append({
            "hour": i * interval_minutes / 60.0,
            "timestamp_utc": dt.isoformat(),
            "ghi_wm2": ghi,
            "elevation_deg": pos.elevation_deg,
            "azimuth_deg": pos.azimuth_deg,
        })

    return profile


# ---------------------------------------------------------------------------
# PV cell temperature model
# ---------------------------------------------------------------------------

def pvwatts_cell_temperature(
    poa_global_wm2: float,
    temp_air_c: float,
    wind_speed_ms: float = 1.0,
) -> float:
    """Compute PV cell temperature using the SAPM (PVWatts) model.

    Glass/glass module on open rack (most common residential case).

    Formula: T_cell = T_air + GTI*exp(a + b*wind) + (GTI/1000)*deltaT

    Parameters
    ----------
    poa_global_wm2 : float
        Plane-of-array irradiance in W/m².
    temp_air_c : float
        Ambient air temperature in °C.
    wind_speed_ms : float
        Wind speed at module height in m/s.

    Returns
    -------
    float
        Cell temperature in °C.
    """
    return (
        temp_air_c
        + poa_global_wm2 * math.exp(_SAPM_A + _SAPM_B * wind_speed_ms)
        + (poa_global_wm2 / 1000.0) * _SAPM_DELTA_T
    )


def temperature_efficiency(
    poa_global_wm2: float,
    temp_air_c: float,
    wind_speed_ms: float = 1.0,
) -> float:
    """Return temperature efficiency multiplier for a given irradiance sample.

    1.0 = STC performance. Cool cells genuinely produce more (up to 1.1).
    Hot cells derate proportionally.
    """
    t_cell = pvwatts_cell_temperature(poa_global_wm2, temp_air_c, wind_speed_ms)
    return max(0.5, min(1.1, 1.0 - _TEMP_COEFF * (t_cell - _STC_TEMP_C)))


# ---------------------------------------------------------------------------
# PV energy estimation
# ---------------------------------------------------------------------------

@dataclass
class PVArrayConfig:
    """PV array configuration."""

    peak_power_kwp: float
    tilt_deg: float = 15.0  # module tilt from horizontal
    azimuth_deg: float = 180.0  # module facing direction (180 = south)
    system_loss: float = 0.14  # combined cable, mismatch, soiling losses
    inverter_efficiency: float = 0.97


@dataclass
class PVEstimate:
    """PV energy production estimate for one period."""

    timestamp_utc: str
    ghi_wm2: float
    poa_wm2: float
    cell_temp_c: float
    temp_derate: float
    dc_power_kw: float
    ac_power_kw: float
    energy_kwh: float


def estimate_pv_power(
    array: PVArrayConfig,
    ghi_wm2: float,
    temp_air_c: float = 25.0,
    wind_speed_ms: float = 1.0,
) -> Dict[str, float]:
    """Estimate instantaneous PV power output.

    Uses a simplified transposition from GHI to POA and applies
    temperature derate.

    Parameters
    ----------
    array : PVArrayConfig
        Array configuration.
    ghi_wm2 : float
        Global horizontal irradiance.
    temp_air_c : float
        Ambient temperature.
    wind_speed_ms : float
        Wind speed.

    Returns
    -------
    dict
        With keys: poa_wm2, cell_temp_c, temp_derate, dc_power_kw, ac_power_kw.
    """
    if ghi_wm2 <= 0:
        return {
            "poa_wm2": 0.0,
            "cell_temp_c": temp_air_c,
            "temp_derate": 1.0,
            "dc_power_kw": 0.0,
            "ac_power_kw": 0.0,
        }

    # Simplified GHI → POA transposition
    # For tilted surfaces, POA ≈ GHI * (1 + 0.033*cos(tilt))
    # This is a rough approximation; proper transposition needs DNI/DHI
    tilt_rad = math.radians(array.tilt_deg)
    poa_ratio = 1.0 + 0.033 * math.cos(tilt_rad)  # simplified
    poa = ghi_wm2 * poa_ratio

    cell_temp = pvwatts_cell_temperature(poa, temp_air_c, wind_speed_ms)
    temp_derate = max(0.5, min(1.1, 1.0 - _TEMP_COEFF * (cell_temp - _STC_TEMP_C)))

    dc_power = array.peak_power_kwp * (poa / _STC_IRRADIANCE) * temp_derate * (1 - array.system_loss)
    ac_power = dc_power * array.inverter_efficiency

    return {
        "poa_wm2": round(poa, 2),
        "cell_temp_c": round(cell_temp, 2),
        "temp_derate": round(temp_derate, 4),
        "dc_power_kw": round(max(0, dc_power), 3),
        "ac_power_kw": round(max(0, ac_power), 3),
    }


def estimate_daily_energy(
    array: PVArrayConfig,
    latitude: float,
    longitude: float,
    date: datetime,
    hourly_temperature: Optional[List[float]] = None,
    hourly_wind: Optional[List[float]] = None,
    altitude_m: float = 0.0,
) -> Dict[str, Any]:
    """Estimate daily PV energy production under clear-sky conditions.

    Parameters
    ----------
    array : PVArrayConfig
        Array configuration.
    latitude, longitude : float
        Site coordinates.
    date : datetime
        Date for estimation.
    hourly_temperature : list of float, optional
        24-hour temperature profile (°C). Uses 25°C default.
    hourly_wind : list of float, optional
        24-hour wind speed profile (m/s). Uses 1.0 default.
    altitude_m : float
        Site altitude.

    Returns
    -------
    dict
        Daily summary with hourly breakdown.
    """
    profile = clear_sky_profile_24h(latitude, longitude, date, altitude_m)
    temps = hourly_temperature or [25.0] * 24
    winds = hourly_wind or [1.0] * 24

    hourly_estimates: List[Dict[str, Any]] = []
    total_energy = 0.0
    peak_power = 0.0

    for i, step in enumerate(profile):
        hour_idx = min(int(step["hour"]), 23)
        temp = temps[hour_idx] if hour_idx < len(temps) else 25.0
        wind = winds[hour_idx] if hour_idx < len(winds) else 1.0

        pv = estimate_pv_power(array, step["ghi_wm2"], temp, wind)
        energy_kwh = pv["ac_power_kw"]  # 1-hour interval

        hourly_estimates.append({
            "hour": step["hour"],
            "ghi_wm2": step["ghi_wm2"],
            **pv,
            "energy_kwh": round(energy_kwh, 3),
        })

        total_energy += energy_kwh
        peak_power = max(peak_power, pv["ac_power_kw"])

    # Capacity factor
    capacity_factor = total_energy / (array.peak_power_kwp * 24) if array.peak_power_kwp > 0 else 0

    return {
        "date": date.strftime("%Y-%m-%d"),
        "latitude": latitude,
        "longitude": longitude,
        "array_kwp": array.peak_power_kwp,
        "total_energy_kwh": round(total_energy, 2),
        "peak_power_kw": round(peak_power, 3),
        "capacity_factor": round(capacity_factor, 4),
        "sunshine_hours": sum(1 for s in profile if s["ghi_wm2"] > 50),
        "hourly": hourly_estimates,
    }


# ---------------------------------------------------------------------------
# Forecasting models (statistical, no ML dependencies)
# ---------------------------------------------------------------------------

class PersistenceForecaster:
    """Naive persistence forecast: tomorrow = today.

    Independently implements the concept from virtual-power-plant-main (MIT)
    research/forecasting.py PersistenceForecaster.
    """

    def __init__(self) -> None:
        self._last_profile: Optional[List[float]] = None

    def train(self, daily_profiles: List[List[float]]) -> Dict[str, float]:
        """Store the most recent daily profile."""
        if daily_profiles:
            self._last_profile = list(daily_profiles[-1])
        return {"method": "persistence", "profiles_seen": len(daily_profiles)}

    def predict(self, horizon_steps: int = 24) -> List[float]:
        """Predict next period using last known pattern."""
        if self._last_profile is None:
            return [0.0] * horizon_steps

        pattern = self._last_profile
        repeats = (horizon_steps // len(pattern)) + 1
        return (pattern * repeats)[:horizon_steps]


class LinearForecaster:
    """Multivariate linear regression forecaster.

    Uses numpy-free least-squares for simple cases.
    """

    def __init__(self) -> None:
        self._weights: Optional[List[float]] = None
        self._bias: float = 0.0

    def train(self, X: List[List[float]], y: List[float]) -> Dict[str, float]:
        """Train linear model using simple gradient descent.

        X: list of feature vectors, y: target values.
        """
        if not X or not y or len(X) != len(y):
            return {"error": "insufficient_data"}

        n = len(X)
        d = len(X[0]) if X else 0
        if d == 0:
            self._bias = sum(y) / n if n > 0 else 0.0
            return {"bias": self._bias}

        # Initialize weights
        weights = [0.0] * d
        bias = sum(y) / n
        lr = 0.001
        epochs = 100

        for _epoch in range(epochs):
            for i in range(n):
                pred = sum(weights[j] * X[i][j] for j in range(d)) + bias
                error = pred - y[i]

                for j in range(d):
                    weights[j] -= lr * error * X[i][j] / n
                bias -= lr * error / n

        self._weights = weights
        self._bias = bias

        # Training metrics
        predictions = [sum(weights[j] * X[i][j] for j in range(d)) + bias for i in range(n)]
        mae = sum(abs(predictions[i] - y[i]) for i in range(n)) / n
        rmse = math.sqrt(sum((predictions[i] - y[i]) ** 2 for i in range(n)) / n)

        return {"mae": round(mae, 4), "rmse": round(rmse, 4)}

    def predict(self, X: List[List[float]]) -> List[float]:
        """Predict using trained linear model."""
        if self._weights is None:
            return [self._bias] * len(X)

        return [
            sum(self._weights[j] * x[j] for j in range(len(self._weights))) + self._bias
            for x in X
        ]


class ExponentialSmoothingForecaster:
    """Simple exponential smoothing forecaster.

    Independently implements the concept described in VPP forecasting (MIT).
    """

    def __init__(self, alpha: float = 0.3) -> None:
        self.alpha = max(0.01, min(1.0, alpha))
        self._smoothed: Optional[List[float]] = None

    def train(self, profiles: List[List[float]]) -> Dict[str, float]:
        """Train by exponentially smoothing historical profiles."""
        if not profiles:
            return {"error": "no_data"}

        n_steps = len(profiles[0])
        smoothed = list(profiles[0])

        for profile in profiles[1:]:
            for i in range(min(n_steps, len(profile))):
                smoothed[i] = self.alpha * profile[i] + (1 - self.alpha) * smoothed[i]

        self._smoothed = smoothed
        return {"method": "exponential_smoothing", "alpha": self.alpha, "steps": n_steps}

    def predict(self, horizon_steps: int = 24) -> List[float]:
        """Return smoothed forecast."""
        if self._smoothed is None:
            return [0.0] * horizon_steps

        result = list(self._smoothed)
        while len(result) < horizon_steps:
            result.extend(self._smoothed)
        return result[:horizon_steps]
