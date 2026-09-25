"""GIS spatial engine, Haversine distance, and map clustering for fleet visualization."""

from __future__ import annotations

import math
from typing import Any


def haversine_distance_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Calculate the great-circle distance between two points on the Earth's surface."""
    r = 6371.0  # Earth radius in kilometers

    d_lat = math.radians(lat2 - lat1)
    d_lon = math.radians(lon2 - lon1)
    a = (
        math.sin(d_lat / 2.0) ** 2
        + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(d_lon / 2.0) ** 2
    )
    a = min(1.0, max(0.0, a))
    c = 2.0 * math.atan2(math.sqrt(a), math.sqrt(1.0 - a))
    return r * c


def cluster_plants(
    plants: list[dict[str, Any]],
    distance_threshold_km: float = 25.0,
) -> list[dict[str, Any]]:
    """Cluster plants based on spatial proximity.

    :param plants: list of plant dicts containing 'latitude', 'longitude', 'id', 'name', 'capacity_kwp'.
    :param distance_threshold_km: max distance to group plants into the same cluster.
    :return: list of cluster dicts (or single-plant items) with center coordinates and stats.
    """
    valid_plants = [
        p
        for p in plants
        if isinstance(p.get("latitude"), (int, float))
        and isinstance(p.get("longitude"), (int, float))
        and math.isfinite(p["latitude"])
        and math.isfinite(p["longitude"])
        and -90 <= p["latitude"] <= 90
        and -180 <= p["longitude"] <= 180
    ]

    clusters: list[list[dict[str, Any]]] = []
    for plant in valid_plants:
        lat = plant["latitude"]
        lon = plant["longitude"]
        assigned = False

        for cluster in clusters:
            center_lat = sum(p["latitude"] for p in cluster) / len(cluster)
            center_lon = sum(p["longitude"] for p in cluster) / len(cluster)
            dist = haversine_distance_km(lat, lon, center_lat, center_lon)

            if dist <= distance_threshold_km:
                cluster.append(plant)
                assigned = True
                break

        if not assigned:
            clusters.append([plant])

    # Convert clusters into structured markers
    results = []
    for idx, group in enumerate(clusters):
        count = len(group)
        center_lat = sum(p["latitude"] for p in group) / count
        center_lon = sum(p["longitude"] for p in group) / count
        total_kwp = sum(float(p.get("capacity_kwp") or 0.0) for p in group)

        if count == 1:
            # Single plant marker
            single = group[0]
            results.append(
                {
                    "type": "PLANT",
                    "id": single["id"],
                    "name": single.get("name") or single["id"],
                    "latitude": single["latitude"],
                    "longitude": single["longitude"],
                    "capacity_kwp": total_kwp,
                    "status": single.get("status", "UNKNOWN"),
                }
            )
        else:
            # Aggregated cluster
            results.append(
                {
                    "type": "CLUSTER",
                    "cluster_id": f"cluster_{idx + 1}",
                    "count": count,
                    "latitude": round(center_lat, 6),
                    "longitude": round(center_lon, 6),
                    "total_capacity_kwp": round(total_kwp, 1),
                    "plant_ids": [p["id"] for p in group],
                    "plants": [{"id": p["id"], "name": p.get("name") or p["id"]} for p in group],
                }
            )

    return results


def filter_viewport(
    plants: list[dict[str, Any]],
    min_lat: float,
    max_lat: float,
    min_lng: float,
    max_lng: float,
) -> list[dict[str, Any]]:
    """Filter plants within a geographic bounding box."""
    return [
        p
        for p in plants
        if isinstance(p.get("latitude"), (int, float))
        and isinstance(p.get("longitude"), (int, float))
        and min_lat <= p["latitude"] <= max_lat
        and min_lng <= p.get("longitude", -999) <= max_lng
    ]
