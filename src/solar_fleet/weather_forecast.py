"""Weather forecast integration for solar fleet operations.

Independently implemented for Solar Fleet EMS.
Provides weather data retrieval from Open-Meteo API (free, no API key)
and local forecast models for PV production estimation.

Concepts informed by emhass-master (MIT license) weather retrieval
and batpred-main (personal-use license) solar forecast concepts.
No code copied from either project.
"""

from __future__ import annotations

import json
import logging
import math
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib.error import URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class HourlyWeather:
    """Single hourly weather data point."""

    timestamp_utc: str
    temperature_c: float
    humidity_pct: float
    wind_speed_ms: float
    wind_direction_deg: float
    cloud_cover_pct: float
    precipitation_mm: float
    ghi_wm2: float
    dni_wm2: float
    dhi_wm2: float
    pressure_hpa: float

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp_utc": self.timestamp_utc,
            "temperature_c": round(self.temperature_c, 1),
            "humidity_pct": round(self.humidity_pct, 0),
            "wind_speed_ms": round(self.wind_speed_ms, 1),
            "wind_direction_deg": round(self.wind_direction_deg, 0),
            "cloud_cover_pct": round(self.cloud_cover_pct, 0),
            "precipitation_mm": round(self.precipitation_mm, 1),
            "ghi_wm2": round(self.ghi_wm2, 1),
            "dni_wm2": round(self.dni_wm2, 1),
            "dhi_wm2": round(self.dhi_wm2, 1),
            "pressure_hpa": round(self.pressure_hpa, 1),
        }


@dataclass
class WeatherForecast:
    """Complete weather forecast for a site."""

    latitude: float
    longitude: float
    timezone_str: str
    elevation_m: float
    fetched_at_utc: str
    hourly: List[HourlyWeather] = field(default_factory=list)
    source: str = "open-meteo"

    def to_dict(self) -> dict[str, Any]:
        return {
            "latitude": self.latitude,
            "longitude": self.longitude,
            "timezone": self.timezone_str,
            "elevation_m": self.elevation_m,
            "fetched_at_utc": self.fetched_at_utc,
            "source": self.source,
            "hours": len(self.hourly),
            "hourly": [h.to_dict() for h in self.hourly],
        }

    @property
    def ghi_profile(self) -> List[float]:
        """Extract GHI values as list."""
        return [h.ghi_wm2 for h in self.hourly]

    @property
    def temperature_profile(self) -> List[float]:
        """Extract temperature values as list."""
        return [h.temperature_c for h in self.hourly]

    @property
    def wind_profile(self) -> List[float]:
        """Extract wind speed values as list."""
        return [h.wind_speed_ms for h in self.hourly]


# ---------------------------------------------------------------------------
# Open-Meteo client
# ---------------------------------------------------------------------------

class OpenMeteoClient:
    """Client for Open-Meteo free weather API.

    Uses the forecast API for hourly weather data including
    solar radiation (GHI, DNI, DHI).

    API docs: https://open-meteo.com/en/docs
    """

    BASE_URL = "https://api.open-meteo.com/v1/forecast"

    HOURLY_PARAMS = [
        "temperature_2m",
        "relative_humidity_2m",
        "wind_speed_10m",
        "wind_direction_10m",
        "cloud_cover",
        "precipitation",
        "shortwave_radiation",
        "direct_normal_irradiance",
        "diffuse_radiation",
        "surface_pressure",
    ]

    def __init__(self, timeout_seconds: int = 10) -> None:
        self.timeout = timeout_seconds

    def fetch_forecast(
        self,
        latitude: float,
        longitude: float,
        forecast_days: int = 7,
    ) -> WeatherForecast:
        """Fetch weather forecast from Open-Meteo.

        Parameters
        ----------
        latitude, longitude : float
            Site coordinates.
        forecast_days : int
            Number of forecast days (1-16).

        Returns
        -------
        WeatherForecast
            Parsed forecast data.

        Raises
        ------
        WeatherFetchError
            On network or parse failure.
        """
        params = "&".join([
            f"latitude={latitude}",
            f"longitude={longitude}",
            f"hourly={','.join(self.HOURLY_PARAMS)}",
            f"forecast_days={min(forecast_days, 16)}",
            "timezone=UTC",
        ])
        url = f"{self.BASE_URL}?{params}"

        try:
            req = Request(url, headers={"User-Agent": "SolarFleetEMS/0.2"})
            with urlopen(req, timeout=self.timeout) as resp:
                data = json.loads(resp.read().decode("utf-8"))
        except (URLError, OSError, json.JSONDecodeError) as e:
            raise WeatherFetchError(
                f"Failed to fetch weather from Open-Meteo: {e}"
            ) from e

        return self._parse_response(data, latitude, longitude)

    def _parse_response(
        self, data: dict, lat: float, lon: float,
    ) -> WeatherForecast:
        """Parse Open-Meteo JSON response."""
        hourly_data = data.get("hourly", {})
        times = hourly_data.get("time", [])

        hourly: List[HourlyWeather] = []
        for i, ts in enumerate(times):
            hourly.append(HourlyWeather(
                timestamp_utc=ts,
                temperature_c=_safe_get(hourly_data, "temperature_2m", i),
                humidity_pct=_safe_get(hourly_data, "relative_humidity_2m", i),
                wind_speed_ms=_safe_get(hourly_data, "wind_speed_10m", i),
                wind_direction_deg=_safe_get(
                    hourly_data, "wind_direction_10m", i,
                ),
                cloud_cover_pct=_safe_get(hourly_data, "cloud_cover", i),
                precipitation_mm=_safe_get(
                    hourly_data, "precipitation", i,
                ),
                ghi_wm2=_safe_get(
                    hourly_data, "shortwave_radiation", i,
                ),
                dni_wm2=_safe_get(
                    hourly_data, "direct_normal_irradiance", i,
                ),
                dhi_wm2=_safe_get(hourly_data, "diffuse_radiation", i),
                pressure_hpa=_safe_get(
                    hourly_data, "surface_pressure", i,
                ),
            ))

        return WeatherForecast(
            latitude=data.get("latitude", lat),
            longitude=data.get("longitude", lon),
            timezone_str=data.get("timezone", "UTC"),
            elevation_m=data.get("elevation", 0.0),
            fetched_at_utc=datetime.now(timezone.utc).isoformat(),
            hourly=hourly,
            source="open-meteo",
        )


def _safe_get(data: dict, key: str, idx: int) -> float:
    """Safely get a value from hourly data arrays."""
    arr = data.get(key, [])
    if idx < len(arr) and arr[idx] is not None:
        return float(arr[idx])
    return 0.0


class WeatherFetchError(Exception):
    """Raised when weather data fetch fails."""


# ---------------------------------------------------------------------------
# Cloud-cover to GHI estimator (when API unavailable)
# ---------------------------------------------------------------------------

class CloudCoverGHIEstimator:
    """Estimate GHI from cloud cover percentage.

    Uses a simple linear model:
        GHI_actual = GHI_clear * (1 - k * cloud_cover / 100)

    where k is the cloud transmittance reduction factor.
    """

    def __init__(self, k: float = 0.75) -> None:
        self.k = max(0.0, min(1.0, k))

    def estimate_ghi(
        self, ghi_clear_sky: float, cloud_cover_pct: float,
    ) -> float:
        """Estimate actual GHI from clear-sky GHI and cloud cover."""
        factor = 1.0 - self.k * (cloud_cover_pct / 100.0)
        return max(0.0, ghi_clear_sky * factor)

    def estimate_profile(
        self,
        clear_sky_profile: List[float],
        cloud_cover_profile: List[float],
    ) -> List[float]:
        """Estimate actual GHI profile from clear-sky and clouds."""
        n = min(len(clear_sky_profile), len(cloud_cover_profile))
        return [
            self.estimate_ghi(clear_sky_profile[i], cloud_cover_profile[i])
            for i in range(n)
        ]


# ---------------------------------------------------------------------------
# PV production forecast
# ---------------------------------------------------------------------------

class PVProductionForecaster:
    """Forecast PV production from weather data.

    Combines weather forecast with PV array configuration to estimate
    hourly AC power output.
    """

    def __init__(
        self,
        peak_power_kwp: float,
        tilt_deg: float = 15.0,
        azimuth_deg: float = 180.0,
        system_loss: float = 0.14,
        inverter_efficiency: float = 0.97,
    ) -> None:
        self.peak_power_kwp = peak_power_kwp
        self.tilt_deg = tilt_deg
        self.azimuth_deg = azimuth_deg
        self.system_loss = system_loss
        self.inverter_efficiency = inverter_efficiency

    def forecast_from_weather(
        self, weather: WeatherForecast,
    ) -> List[Dict[str, Any]]:
        """Generate hourly PV production forecast from weather."""

        results: List[Dict[str, Any]] = []

        for h in weather.hourly:
            # Temperature derate
            temp_coeff = -0.004  # %/°C for c-Si
            temp_derate = 1.0 + temp_coeff * (h.temperature_c - 25.0)
            temp_derate = max(0.5, min(1.1, temp_derate))

            # Cloud-adjusted GHI
            ghi = h.ghi_wm2

            # Simplified POA from GHI
            tilt_rad = math.radians(self.tilt_deg)
            poa_ratio = 1.0 + 0.033 * math.cos(tilt_rad)
            poa = ghi * poa_ratio

            # DC power
            if poa > 0:
                dc = (
                    self.peak_power_kwp
                    * (poa / 1000.0)
                    * temp_derate
                    * (1 - self.system_loss)
                )
            else:
                dc = 0.0

            # AC power
            ac = max(0, dc * self.inverter_efficiency)

            results.append({
                "timestamp_utc": h.timestamp_utc,
                "ghi_wm2": round(ghi, 1),
                "poa_wm2": round(poa, 1),
                "temperature_c": round(h.temperature_c, 1),
                "temp_derate": round(temp_derate, 4),
                "dc_power_kw": round(dc, 3),
                "ac_power_kw": round(ac, 3),
                "cloud_cover_pct": round(h.cloud_cover_pct, 0),
            })

        return results

    def daily_summary(
        self, hourly_forecast: List[Dict[str, Any]],
    ) -> Dict[str, Any]:
        """Summarize hourly forecast into daily totals."""
        if not hourly_forecast:
            return {"total_energy_kwh": 0, "peak_power_kw": 0}

        total_energy = sum(h["ac_power_kw"] for h in hourly_forecast)
        peak_power = max(h["ac_power_kw"] for h in hourly_forecast)
        avg_ghi = (
            sum(h["ghi_wm2"] for h in hourly_forecast)
            / len(hourly_forecast)
        )
        sunshine_hours = sum(
            1 for h in hourly_forecast if h["ghi_wm2"] > 50
        )

        return {
            "total_energy_kwh": round(total_energy, 2),
            "peak_power_kw": round(peak_power, 3),
            "average_ghi_wm2": round(avg_ghi, 1),
            "sunshine_hours": sunshine_hours,
            "capacity_factor": round(
                total_energy / (self.peak_power_kwp * 24)
                if self.peak_power_kwp > 0 else 0, 4,
            ),
        }
