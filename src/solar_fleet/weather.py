"""Weather and solar irradiance service using Open-Meteo public API.

Open-Meteo (https://open-meteo.com) is free, requires no API key,
provides hourly weather and solar radiation data worldwide.

This module:
 - Fetches current weather + 48h forecast for a GPS coordinate
 - Returns temperature, cloud cover, GHI (W/m²), DNI, DHI
 - Caches results for 15 minutes to avoid excessive calls
 - Degrades gracefully when offline (returns cached or None)
"""

from __future__ import annotations

import math
import time
from datetime import datetime, timezone
from typing import Any

import httpx

# Cache: key = (lat_rounded, lon_rounded), value = (timestamp, data)
_cache: dict[tuple[float, float], tuple[float, dict]] = {}
_CACHE_TTL = 900  # 15 minutes


def _round_coord(lat: float, lon: float) -> tuple[float, float]:
    """Round to 2 decimals (~1km precision) for cache grouping."""
    return round(lat, 2), round(lon, 2)


async def fetch_weather(
    latitude: float,
    longitude: float,
    *,
    timeout: float = 10.0,
) -> dict[str, Any] | None:
    """Fetch current weather and solar irradiance from Open-Meteo.

    Returns dict with keys:
      current: {temperature_c, humidity_pct, cloud_cover_pct, wind_speed_ms,
                ghi_wm2, dni_wm2, dhi_wm2, weather_code, description}
      hourly_forecast: [{hour, temperature_c, ghi_wm2, cloud_cover_pct}, ...]
      meta: {latitude, longitude, timezone, fetched_at}

    Returns None on error (network, timeout, invalid coords).
    """
    if (
        not all(math.isfinite(v) for v in (latitude, longitude))
        or not -90 <= latitude <= 90
        or not -180 <= longitude <= 180
    ):
        return None
    key = _round_coord(latitude, longitude)

    # Check cache
    if key in _cache:
        cached_time, cached_data = _cache[key]
        if time.monotonic() - cached_time < _CACHE_TTL:
            return cached_data

    url = "https://api.open-meteo.com/v1/forecast"
    params = {
        "latitude": latitude,
        "longitude": longitude,
        "current": "temperature_2m,relative_humidity_2m,cloud_cover,wind_speed_10m,weather_code",
        "hourly": "temperature_2m,cloud_cover,shortwave_radiation,direct_normal_irradiance,diffuse_radiation",
        "forecast_days": 2,
        "timezone": "UTC",
        "wind_speed_unit": "ms",
    }

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.get(url, params=params)
            resp.raise_for_status()
            raw = resp.json()
    except Exception:
        # Return stale cache if available
        if key in _cache:
            return {**_cache[key][1], "meta": {**_cache[key][1]["meta"], "stale": True}}
        return None

    current = raw.get("current", {})
    hourly = raw.get("hourly", {})

    # Parse current conditions
    weather_codes = {
        0: "Trời quang / Clear sky",
        1: "Ít mây / Mainly clear",
        2: "Mây rải rác / Partly cloudy",
        3: "Nhiều mây / Overcast",
        45: "Sương mù / Fog",
        48: "Sương mù đọng / Depositing rime fog",
        51: "Mưa phùn nhẹ / Light drizzle",
        53: "Mưa phùn / Moderate drizzle",
        55: "Mưa phùn dày / Dense drizzle",
        61: "Mưa nhẹ / Slight rain",
        63: "Mưa vừa / Moderate rain",
        65: "Mưa to / Heavy rain",
        80: "Mưa rào nhẹ / Slight rain showers",
        81: "Mưa rào vừa / Moderate rain showers",
        82: "Mưa rào to / Violent rain showers",
        95: "Giông / Thunderstorm",
        96: "Giông kèm mưa đá nhẹ / Thunderstorm with slight hail",
        99: "Giông kèm mưa đá lớn / Thunderstorm with heavy hail",
    }
    code = current.get("weather_code", -1)

    result = {
        "current": {
            "temperature_c": current.get("temperature_2m"),
            "humidity_pct": current.get("relative_humidity_2m"),
            "cloud_cover_pct": current.get("cloud_cover"),
            "wind_speed_ms": current.get("wind_speed_10m"),
            "weather_code": code,
            "description": weather_codes.get(code, f"Code {code}"),
            # GHI from nearest hourly value
            "ghi_wm2": None,
            "dni_wm2": None,
            "dhi_wm2": None,
        },
        "hourly_forecast": [],
        "meta": {
            "latitude": raw.get("latitude", latitude),
            "longitude": raw.get("longitude", longitude),
            "timezone": raw.get("timezone", "UTC"),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
            "source": "Open-Meteo (open-meteo.com)",
            "stale": False,
            "license": "CC BY 4.0",
        },
    }

    # Extract hourly data
    times = hourly.get("time", [])
    temps = hourly.get("temperature_2m", [])
    clouds = hourly.get("cloud_cover", [])
    ghis = hourly.get("shortwave_radiation", [])
    dnis = hourly.get("direct_normal_irradiance", [])
    dhis = hourly.get("diffuse_radiation", [])

    # Find current hour index for GHI
    now_str = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:00")
    for i, t_str in enumerate(times):
        entry = {
            "hour": t_str,
            "temperature_c": temps[i] if i < len(temps) else None,
            "cloud_cover_pct": clouds[i] if i < len(clouds) else None,
            "ghi_wm2": ghis[i] if i < len(ghis) else None,
            "dni_wm2": dnis[i] if i < len(dnis) else None,
            "dhi_wm2": dhis[i] if i < len(dhis) else None,
        }
        result["hourly_forecast"].append(entry)

        # Populate current GHI from the nearest hour
        if t_str and now_str and t_str[:13] == now_str[:13]:
            result["current"]["ghi_wm2"] = entry["ghi_wm2"]
            result["current"]["dni_wm2"] = entry["dni_wm2"]
            result["current"]["dhi_wm2"] = entry["dhi_wm2"]

    if len(_cache) >= 256:
        _cache.pop(next(iter(_cache)))
    _cache[key] = (time.monotonic(), result)
    return result


def clear_cache() -> None:
    """Clear the weather cache (for testing)."""
    _cache.clear()
