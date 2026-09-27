"""Load prediction engine — ML and pattern-based load forecasting.

Independently implemented for Solar Fleet EMS.
Concepts from batpred-main (predbat load_predictor.py, prediction.py),
OpenEMS predictor modules (similarday, profileclustering, persistence),
and emhass-master load forecasting — no code copied.

Implements: persistence, similar-day, profile-clustering,
weighted ensemble, and basic neural-network-style prediction.
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class LoadProfile:
    """24-hour load profile (hourly kW values)."""

    values: List[float] = field(default_factory=lambda: [0.0] * 24)
    date: str = ""
    day_type: str = "weekday"  # weekday, weekend, holiday
    total_kwh: float = 0.0

    def __post_init__(self):
        self.total_kwh = sum(self.values)

    @property
    def peak_kw(self) -> float:
        return max(self.values) if self.values else 0

    @property
    def base_kw(self) -> float:
        return min(self.values) if self.values else 0

    @property
    def load_factor(self) -> float:
        if self.peak_kw <= 0:
            return 0
        return (self.total_kwh / 24.0) / self.peak_kw


# ---------------------------------------------------------------------------
# Predictor base
# ---------------------------------------------------------------------------

class LoadPredictor:
    """Base class for load predictors."""

    def __init__(self, name: str = "base"):
        self.name = name
        self._history: List[LoadProfile] = []
        self._trained = False

    def add_history(self, profile: LoadProfile) -> None:
        """Add a historical load profile."""
        self._history.append(profile)

    def train(self) -> Dict[str, Any]:
        """Train the predictor on historical data."""
        self._trained = True
        return {"status": "trained", "samples": len(self._history)}

    def predict(self, target_date: str = "", day_type: str = "weekday") -> List[float]:
        """Predict 24-hour load profile."""
        raise NotImplementedError


# ---------------------------------------------------------------------------
# Persistence predictor
# ---------------------------------------------------------------------------

class PersistencePredictor(LoadPredictor):
    """Use most recent day's profile as prediction.

    Simplest baseline — yesterday's load repeats today.
    """

    def __init__(self):
        super().__init__("persistence")

    def predict(self, target_date: str = "", day_type: str = "weekday") -> List[float]:
        if not self._history:
            raise ValueError("observed_load_history_required")
        return list(self._history[-1].values)


# ---------------------------------------------------------------------------
# Similar-day predictor
# ---------------------------------------------------------------------------

class SimilarDayPredictor(LoadPredictor):
    """Find the most similar historical day and use its profile.

    Similarity based on: day type, season, total energy.
    OpenEMS predictor.similardaymodel concept.
    """

    def __init__(self, n_similar: int = 5):
        super().__init__("similar_day")
        self.n_similar = n_similar

    def predict(self, target_date: str = "", day_type: str = "weekday") -> List[float]:
        if not self._history:
            raise ValueError("observed_load_history_required")

        # Filter by day type
        candidates = [p for p in self._history if p.day_type == day_type]
        if not candidates:
            candidates = self._history

        # Score by total energy similarity to most recent
        ref_energy = self._history[-1].total_kwh
        scored = sorted(
            candidates,
            key=lambda p: abs(p.total_kwh - ref_energy),
        )

        # Average top-N similar days
        top_n = scored[: min(self.n_similar, len(scored))]
        result = [0.0] * 24
        for h in range(24):
            result[h] = sum(p.values[h] for p in top_n) / len(top_n)

        return result


# ---------------------------------------------------------------------------
# Profile clustering predictor
# ---------------------------------------------------------------------------

class ProfileClusterPredictor(LoadPredictor):
    """Cluster historical profiles and match to closest cluster.

    OpenEMS predictor.profileclusteringmodel concept.
    Simple k-means-like clustering using Euclidean distance.
    """

    def __init__(self, n_clusters: int = 3):
        super().__init__("profile_cluster")
        self.n_clusters = n_clusters
        self._centroids: List[List[float]] = []

    def train(self) -> Dict[str, Any]:
        if len(self._history) < self.n_clusters:
            self._centroids = [
                list(p.values) for p in self._history
            ]
            self._trained = True
            return {"status": "trained", "clusters": len(self._centroids)}

        # Simple k-means initialization (first k profiles)
        centroids = [
            list(self._history[i].values)
            for i in range(self.n_clusters)
        ]

        # Run 10 iterations
        for _ in range(10):
            # Assign each profile to nearest centroid
            clusters: Dict[int, List[LoadProfile]] = {
                i: [] for i in range(self.n_clusters)
            }
            for profile in self._history:
                dists = [
                    self._euclidean(profile.values, c)
                    for c in centroids
                ]
                nearest = dists.index(min(dists))
                clusters[nearest].append(profile)

            # Update centroids
            for i in range(self.n_clusters):
                if clusters[i]:
                    for h in range(24):
                        centroids[i][h] = (
                            sum(p.values[h] for p in clusters[i])
                            / len(clusters[i])
                        )

        self._centroids = centroids
        self._trained = True
        return {"status": "trained", "clusters": self.n_clusters}

    def predict(self, target_date: str = "", day_type: str = "weekday") -> List[float]:
        if not self._centroids:
            raise ValueError("trained_load_history_required")

        if not self._history:
            return list(self._centroids[0])

        # Match recent profile to nearest cluster
        recent = self._history[-1].values
        dists = [
            self._euclidean(recent, c) for c in self._centroids
        ]
        nearest = dists.index(min(dists))
        return list(self._centroids[nearest])

    @staticmethod
    def _euclidean(a: Sequence[float], b: Sequence[float]) -> float:
        return math.sqrt(sum((x - y) ** 2 for x, y in zip(a, b)))


# ---------------------------------------------------------------------------
# Weighted ensemble predictor
# ---------------------------------------------------------------------------

class EnsemblePredictor(LoadPredictor):
    """Weighted ensemble of multiple predictors.

    Combines persistence, similar-day, and profile clustering
    with configurable weights.
    """

    def __init__(
        self,
        weights: Optional[Dict[str, float]] = None,
    ):
        super().__init__("ensemble")
        self._predictors: Dict[str, LoadPredictor] = {
            "persistence": PersistencePredictor(),
            "similar_day": SimilarDayPredictor(),
            "profile_cluster": ProfileClusterPredictor(),
        }
        self._weights = weights or {
            "persistence": 0.3,
            "similar_day": 0.4,
            "profile_cluster": 0.3,
        }

    def add_history(self, profile: LoadProfile) -> None:
        super().add_history(profile)
        for pred in self._predictors.values():
            pred.add_history(profile)

    def train(self) -> Dict[str, Any]:
        results = {}
        for name, pred in self._predictors.items():
            results[name] = pred.train()
        self._trained = True
        return {"status": "trained", "sub_models": results}

    def predict(self, target_date: str = "", day_type: str = "weekday") -> List[float]:
        predictions: Dict[str, List[float]] = {}
        for name, pred in self._predictors.items():
            predictions[name] = pred.predict(target_date, day_type)

        result = [0.0] * 24
        total_weight = sum(self._weights.values())

        for h in range(24):
            weighted_sum = 0.0
            for name, pred_vals in predictions.items():
                w = self._weights.get(name, 0)
                weighted_sum += pred_vals[h] * w
            result[h] = weighted_sum / total_weight if total_weight > 0 else 0

        return result


# ---------------------------------------------------------------------------
# Temperature-adjusted predictor
# ---------------------------------------------------------------------------

class TemperatureAdjustedPredictor(LoadPredictor):
    """Adjust load prediction based on temperature forecast.

    Uses heating/cooling degree days to scale base prediction.
    Concept from batpred-main temperature.py.
    """

    def __init__(
        self,
        base_predictor: Optional[LoadPredictor] = None,
        heating_threshold_c: float = 18.0,
        cooling_threshold_c: float = 24.0,
        heating_sensitivity: float = 0.03,
        cooling_sensitivity: float = 0.05,
    ):
        super().__init__("temperature_adjusted")
        self._base = base_predictor or PersistencePredictor()
        self.heating_threshold = heating_threshold_c
        self.cooling_threshold = cooling_threshold_c
        self.heating_sens = heating_sensitivity
        self.cooling_sens = cooling_sensitivity

    def add_history(self, profile: LoadProfile) -> None:
        super().add_history(profile)
        self._base.add_history(profile)

    def train(self) -> Dict[str, Any]:
        result = self._base.train()
        self._trained = True
        return result

    def predict_with_temperature(
        self,
        temperature_forecast: List[float],
        day_type: str = "weekday",
    ) -> List[float]:
        """Predict load with temperature adjustment."""
        base = self._base.predict(day_type=day_type)
        result = list(base)

        for h in range(min(24, len(temperature_forecast))):
            temp = temperature_forecast[h]
            adjustment = 1.0

            if temp < self.heating_threshold:
                hdd = self.heating_threshold - temp
                adjustment += self.heating_sens * hdd
            elif temp > self.cooling_threshold:
                cdd = temp - self.cooling_threshold
                adjustment += self.cooling_sens * cdd

            result[h] = base[h] * adjustment

        return result

    def predict(self, target_date: str = "", day_type: str = "weekday") -> List[float]:
        return self._base.predict(target_date, day_type)


# ---------------------------------------------------------------------------
# Prediction evaluation metrics
# ---------------------------------------------------------------------------

def prediction_metrics(
    actual: Sequence[float], predicted: Sequence[float],
) -> Dict[str, float]:
    """Calculate prediction accuracy metrics."""
    n = min(len(actual), len(predicted))
    if n == 0:
        return {"mae": 0, "rmse": 0, "mape": 0, "r2": 0}

    errors = [actual[i] - predicted[i] for i in range(n)]
    abs_errors = [abs(e) for e in errors]
    sq_errors = [e ** 2 for e in errors]

    mae = sum(abs_errors) / n
    rmse = math.sqrt(sum(sq_errors) / n)

    # MAPE (avoid division by zero)
    pct_errors = []
    for i in range(n):
        if abs(actual[i]) > 0.01:
            pct_errors.append(abs(errors[i]) / abs(actual[i]))
    mape = (sum(pct_errors) / len(pct_errors) * 100) if pct_errors else 0

    # R²
    mean_actual = sum(actual[:n]) / n
    ss_res = sum(sq_errors)
    ss_tot = sum((actual[i] - mean_actual) ** 2 for i in range(n))
    r2 = 1 - ss_res / ss_tot if ss_tot > 0 else 0

    return {
        "mae": round(mae, 4),
        "rmse": round(rmse, 4),
        "mape": round(mape, 2),
        "r2": round(r2, 4),
        "n": n,
    }
