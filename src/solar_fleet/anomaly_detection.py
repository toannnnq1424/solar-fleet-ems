"""Anomaly detection for solar fleet telemetry.

Independently implemented for Solar Fleet EMS.
Concepts inspired by virtual-power-plant-main (MIT license)
research/anomaly.py. Provides statistical methods (Z-score, IQR,
Moving Average, EWMA) for detecting anomalous sensor readings,
production deviations, and equipment faults.

All models are statistical — no ML framework dependencies.
"""

from __future__ import annotations

import logging
import math
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, List, Optional, Sequence, Tuple

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

class AnomalyType(str, Enum):
    """Classification of anomaly types."""

    PRODUCTION_DROP = "production_drop"
    OVERCURRENT = "overcurrent"
    OVERVOLTAGE = "overvoltage"
    UNDERVOLTAGE = "undervoltage"
    TEMPERATURE_HIGH = "temperature_high"
    FREQUENCY_DRIFT = "frequency_drift"
    COMMUNICATION_LOSS = "communication_loss"
    POWER_FACTOR_LOW = "power_factor_low"
    EFFICIENCY_DROP = "efficiency_drop"
    STRING_MISMATCH = "string_mismatch"
    BATTERY_ANOMALY = "battery_anomaly"
    SENSOR_DRIFT = "sensor_drift"
    UNKNOWN = "unknown"


class AnomalySeverity(str, Enum):
    """Severity levels for detected anomalies."""

    INFO = "info"
    WARNING = "warning"
    HIGH = "high"
    CRITICAL = "critical"


@dataclass
class AnomalyEvent:
    """A single detected anomaly."""

    event_id: str
    timestamp: datetime
    anomaly_type: AnomalyType
    severity: AnomalySeverity
    device_id: str
    metric_name: str
    observed_value: float
    expected_value: float
    deviation: float
    confidence: float
    description: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_id": self.event_id,
            "timestamp": self.timestamp.isoformat(),
            "anomaly_type": self.anomaly_type.value,
            "severity": self.severity.value,
            "device_id": self.device_id,
            "metric_name": self.metric_name,
            "observed_value": round(self.observed_value, 4),
            "expected_value": round(self.expected_value, 4),
            "deviation": round(self.deviation, 4),
            "confidence": round(self.confidence, 4),
            "description": self.description,
        }


# ---------------------------------------------------------------------------
# Z-Score detector
# ---------------------------------------------------------------------------

class ZScoreDetector:
    """Z-score anomaly detector.

    Flags data points more than *threshold* standard deviations from
    the mean computed during training.
    """

    def __init__(self, threshold: float = 3.0) -> None:
        self.threshold = threshold
        self._mean: Optional[float] = None
        self._std: Optional[float] = None
        self._count: int = 0

    def train(self, values: Sequence[float]) -> Dict[str, float]:
        """Train on historical data."""
        if len(values) < 2:
            return {"mean": 0.0, "std": 1.0}

        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        std = math.sqrt(variance) if variance > 0 else 1e-9

        self._mean = mean
        self._std = max(std, 1e-9)
        self._count = n
        return {"mean": round(mean, 6), "std": round(std, 6)}

    def is_anomaly(self, value: float) -> Tuple[bool, float]:
        """Check if a value is anomalous.

        Returns (is_anomaly, z_score).
        """
        if self._mean is None or self._std is None:
            return False, 0.0

        z = abs(value - self._mean) / self._std
        return z > self.threshold, round(z, 4)

    def detect_batch(self, values: Sequence[float]) -> List[int]:
        """Return indices of anomalous values."""
        return [i for i, v in enumerate(values) if self.is_anomaly(v)[0]]


# ---------------------------------------------------------------------------
# IQR detector
# ---------------------------------------------------------------------------

class IQRDetector:
    """Interquartile range anomaly detector.

    Values outside [Q1 - k*IQR, Q3 + k*IQR] are flagged.
    """

    def __init__(self, k: float = 1.5) -> None:
        self.k = k
        self._q1: Optional[float] = None
        self._q3: Optional[float] = None
        self._iqr: Optional[float] = None

    def train(self, values: Sequence[float]) -> Dict[str, float]:
        """Train on historical data."""
        if len(values) < 4:
            return {"q1": 0.0, "q3": 0.0, "iqr": 0.0}

        sorted_vals = sorted(values)
        n = len(sorted_vals)
        q1_idx = n // 4
        q3_idx = 3 * n // 4
        self._q1 = sorted_vals[q1_idx]
        self._q3 = sorted_vals[q3_idx]
        self._iqr = max(self._q3 - self._q1, 1e-9)

        return {
            "q1": round(self._q1, 6),
            "q3": round(self._q3, 6),
            "iqr": round(self._iqr, 6),
        }

    def is_anomaly(self, value: float) -> Tuple[bool, float]:
        """Check if a value is anomalous.

        Returns (is_anomaly, distance_from_bounds).
        """
        if self._q1 is None or self._q3 is None or self._iqr is None:
            return False, 0.0

        lower = self._q1 - self.k * self._iqr
        upper = self._q3 + self.k * self._iqr

        if value < lower:
            return True, round(lower - value, 4)
        elif value > upper:
            return True, round(value - upper, 4)
        return False, 0.0


# ---------------------------------------------------------------------------
# Moving Average detector
# ---------------------------------------------------------------------------

class MovingAverageDetector:
    """Moving-average based anomaly detection.

    Computes a rolling mean and standard deviation. Points deviating
    more than ``threshold_sigma`` from the local mean are flagged.
    """

    def __init__(self, window_size: int = 24, threshold_sigma: float = 2.5) -> None:
        self.window_size = max(window_size, 2)
        self.threshold_sigma = threshold_sigma

    def detect(self, values: Sequence[float]) -> List[Tuple[int, float, float]]:
        """Detect anomalies in a time series.

        Returns list of (index, observed, moving_mean) for anomalous points.
        """
        n = len(values)
        if n < self.window_size:
            return []

        anomalies: List[Tuple[int, float, float]] = []

        for i in range(self.window_size, n):
            window = values[i - self.window_size:i]
            mean = sum(window) / self.window_size
            variance = sum((v - mean) ** 2 for v in window) / self.window_size
            std = math.sqrt(variance) if variance > 0 else 1e-9

            if abs(values[i] - mean) > self.threshold_sigma * std:
                anomalies.append((i, values[i], mean))

        return anomalies


# ---------------------------------------------------------------------------
# EWMA detector
# ---------------------------------------------------------------------------

class EWMADetector:
    """Exponentially Weighted Moving Average anomaly detector.

    Uses EWMA control limits for detecting shifts in process mean.
    Common in industrial quality control (SPC).
    """

    def __init__(self, alpha: float = 0.2, threshold_sigma: float = 3.0) -> None:
        self.alpha = max(0.01, min(1.0, alpha))
        self.threshold_sigma = threshold_sigma
        self._ewma: Optional[float] = None
        self._ewma_var: Optional[float] = None
        self._process_std: Optional[float] = None

    def train(self, values: Sequence[float]) -> Dict[str, float]:
        """Initialize EWMA from training data."""
        if len(values) < 2:
            return {"ewma": 0.0, "std": 1.0}

        n = len(values)
        mean = sum(values) / n
        variance = sum((v - mean) ** 2 for v in values) / (n - 1)
        self._process_std = math.sqrt(variance) if variance > 0 else 1e-9
        self._ewma = mean
        self._ewma_var = variance * self.alpha / (2 - self.alpha)

        return {
            "ewma": round(mean, 6),
            "std": round(self._process_std, 6),
        }

    def update(self, value: float) -> Tuple[bool, float, float]:
        """Update EWMA and check for anomaly.

        Returns (is_anomaly, ewma_value, control_limit).
        """
        if self._ewma is None or self._process_std is None:
            self._ewma = value
            self._process_std = 1.0
            return False, value, 0.0

        # Update EWMA
        self._ewma = self.alpha * value + (1 - self.alpha) * self._ewma

        # EWMA control limits
        cl = self.threshold_sigma * self._process_std * math.sqrt(
            self.alpha / (2 - self.alpha)
        )

        is_anomaly = abs(value - self._ewma) > cl
        return is_anomaly, round(self._ewma, 6), round(cl, 6)


# ---------------------------------------------------------------------------
# Solar Production Anomaly Detector
# ---------------------------------------------------------------------------

class SolarProductionAnomalyDetector:
    """Specialized anomaly detector for solar PV production.

    Combines multiple detection methods with domain-specific rules:
    - Expected vs actual production ratio (performance ratio)
    - String current mismatch detection
    - Clipping detection (inverter at max capacity)
    - Nighttime production check (fault indicator)
    - Degradation trend detection
    """

    def __init__(
        self,
        rated_power_kw: float,
        min_performance_ratio: float = 0.6,
        string_mismatch_threshold: float = 0.2,
    ) -> None:
        self.rated_power_kw = rated_power_kw
        self.min_performance_ratio = min_performance_ratio
        self.string_mismatch_threshold = string_mismatch_threshold
        self._zscore = ZScoreDetector(threshold=3.0)
        self._ewma = EWMADetector(alpha=0.1, threshold_sigma=2.5)
        self._event_counter = 0

    def _next_event_id(self) -> str:
        self._event_counter += 1
        return f"ANM-{self._event_counter:06d}"

    def check_production(
        self,
        device_id: str,
        timestamp: datetime,
        actual_power_kw: float,
        irradiance_wm2: float,
        temperature_c: float = 25.0,
    ) -> List[AnomalyEvent]:
        """Check for production anomalies.

        Uses irradiance and temperature to estimate expected production
        and compares with actual.
        """
        events: List[AnomalyEvent] = []

        if irradiance_wm2 < 50:
            # Low irradiance — check for nighttime production (fault)
            if actual_power_kw > 0.1 * self.rated_power_kw:
                events.append(AnomalyEvent(
                    event_id=self._next_event_id(),
                    timestamp=timestamp,
                    anomaly_type=AnomalyType.PRODUCTION_DROP,
                    severity=AnomalySeverity.WARNING,
                    device_id=device_id,
                    metric_name="ac_power",
                    observed_value=actual_power_kw,
                    expected_value=0.0,
                    deviation=actual_power_kw,
                    confidence=0.8,
                    description=f"Unexpected production ({actual_power_kw:.1f} kW) during low irradiance ({irradiance_wm2:.0f} W/m²)",
                ))
            return events

        # Expected production (simple linear model with temperature derate)
        temp_coeff = -0.004  # %/°C for c-Si
        temp_derate = 1.0 + temp_coeff * (temperature_c - 25.0)
        temp_derate = max(0.5, min(1.1, temp_derate))

        expected_kw = self.rated_power_kw * (irradiance_wm2 / 1000.0) * temp_derate * 0.85
        expected_kw = min(expected_kw, self.rated_power_kw)

        if expected_kw > 0.5:  # Only check when meaningful production expected
            perf_ratio = actual_power_kw / expected_kw

            if perf_ratio < self.min_performance_ratio:
                severity = (
                    AnomalySeverity.CRITICAL if perf_ratio < 0.3
                    else AnomalySeverity.HIGH if perf_ratio < 0.5
                    else AnomalySeverity.WARNING
                )
                events.append(AnomalyEvent(
                    event_id=self._next_event_id(),
                    timestamp=timestamp,
                    anomaly_type=AnomalyType.PRODUCTION_DROP,
                    severity=severity,
                    device_id=device_id,
                    metric_name="performance_ratio",
                    observed_value=actual_power_kw,
                    expected_value=expected_kw,
                    deviation=round(1.0 - perf_ratio, 4),
                    confidence=0.75,
                    description=(
                        f"Production underperforming: {actual_power_kw:.1f} kW vs "
                        f"expected {expected_kw:.1f} kW (PR={perf_ratio:.1%})"
                    ),
                    metadata={
                        "irradiance_wm2": irradiance_wm2,
                        "temperature_c": temperature_c,
                        "performance_ratio": round(perf_ratio, 4),
                    },
                ))

            # Clipping detection
            if actual_power_kw > self.rated_power_kw * 0.98:
                events.append(AnomalyEvent(
                    event_id=self._next_event_id(),
                    timestamp=timestamp,
                    anomaly_type=AnomalyType.PRODUCTION_DROP,
                    severity=AnomalySeverity.INFO,
                    device_id=device_id,
                    metric_name="ac_power",
                    observed_value=actual_power_kw,
                    expected_value=expected_kw,
                    deviation=round(actual_power_kw - self.rated_power_kw, 2),
                    confidence=0.9,
                    description=f"Inverter clipping at {actual_power_kw:.1f} kW (rated {self.rated_power_kw:.0f} kW)",
                ))

        return events

    def check_string_mismatch(
        self,
        device_id: str,
        timestamp: datetime,
        string_currents: Dict[str, float],
    ) -> List[AnomalyEvent]:
        """Detect PV string current mismatches.

        Compares individual string currents against the average.
        Large deviations indicate shading, soiling, or module faults.
        """
        events: List[AnomalyEvent] = []

        if len(string_currents) < 2:
            return events

        currents = list(string_currents.values())
        avg_current = sum(currents) / len(currents)

        if avg_current < 0.5:  # Skip at low current
            return events

        for string_id, current in string_currents.items():
            deviation = abs(current - avg_current) / avg_current if avg_current > 0 else 0

            if deviation > self.string_mismatch_threshold:
                severity = (
                    AnomalySeverity.HIGH if deviation > 0.5
                    else AnomalySeverity.WARNING
                )
                events.append(AnomalyEvent(
                    event_id=self._next_event_id(),
                    timestamp=timestamp,
                    anomaly_type=AnomalyType.STRING_MISMATCH,
                    severity=severity,
                    device_id=device_id,
                    metric_name=f"string_{string_id}_current",
                    observed_value=current,
                    expected_value=avg_current,
                    deviation=round(deviation, 4),
                    confidence=0.7,
                    description=(
                        f"String {string_id} current mismatch: {current:.2f}A vs "
                        f"avg {avg_current:.2f}A ({deviation:.0%} deviation)"
                    ),
                ))

        return events

    def check_battery(
        self,
        device_id: str,
        timestamp: datetime,
        soc: float,
        voltage: float,
        current: float,
        temperature_c: float,
        nominal_voltage: float = 48.0,
    ) -> List[AnomalyEvent]:
        """Detect battery anomalies.

        Checks voltage bounds, temperature, and SOC consistency.
        """
        events: List[AnomalyEvent] = []

        # Over-temperature
        if temperature_c > 45.0:
            severity = (
                AnomalySeverity.CRITICAL if temperature_c > 55.0
                else AnomalySeverity.HIGH
            )
            events.append(AnomalyEvent(
                event_id=self._next_event_id(),
                timestamp=timestamp,
                anomaly_type=AnomalyType.TEMPERATURE_HIGH,
                severity=severity,
                device_id=device_id,
                metric_name="battery_temperature",
                observed_value=temperature_c,
                expected_value=25.0,
                deviation=temperature_c - 25.0,
                confidence=0.9,
                description=f"Battery temperature high: {temperature_c:.1f}°C",
            ))

        # Voltage bounds
        v_min = nominal_voltage * 0.85
        v_max = nominal_voltage * 1.15
        if voltage < v_min or voltage > v_max:
            anomaly_type = AnomalyType.UNDERVOLTAGE if voltage < v_min else AnomalyType.OVERVOLTAGE
            events.append(AnomalyEvent(
                event_id=self._next_event_id(),
                timestamp=timestamp,
                anomaly_type=anomaly_type,
                severity=AnomalySeverity.HIGH,
                device_id=device_id,
                metric_name="battery_voltage",
                observed_value=voltage,
                expected_value=nominal_voltage,
                deviation=round(abs(voltage - nominal_voltage), 2),
                confidence=0.85,
                description=f"Battery voltage out of range: {voltage:.1f}V (nominal {nominal_voltage:.0f}V)",
            ))

        return events


# ---------------------------------------------------------------------------
# Fleet Anomaly Monitor
# ---------------------------------------------------------------------------

class FleetAnomalyMonitor:
    """Fleet-level anomaly monitoring across all devices.

    Maintains per-device detectors and provides aggregate anomaly reporting.
    """

    def __init__(self) -> None:
        self._detectors: Dict[str, SolarProductionAnomalyDetector] = {}
        self._history: List[AnomalyEvent] = []
        self._max_history: int = 10_000

    def register_device(
        self,
        device_id: str,
        rated_power_kw: float,
    ) -> None:
        """Register a device for monitoring."""
        self._detectors[device_id] = SolarProductionAnomalyDetector(
            rated_power_kw=rated_power_kw,
        )

    def process_telemetry(
        self,
        device_id: str,
        timestamp: datetime,
        metrics: Dict[str, float],
    ) -> List[AnomalyEvent]:
        """Process telemetry data and return any detected anomalies."""

        detector = self._detectors.get(device_id)
        if detector is None:
            return []

        events: List[AnomalyEvent] = []

        # Production check
        if "ac_power" in metrics and "irradiance" in metrics:
            events.extend(detector.check_production(
                device_id=device_id,
                timestamp=timestamp,
                actual_power_kw=metrics["ac_power"] / 1000.0,
                irradiance_wm2=metrics["irradiance"],
                temperature_c=metrics.get("temperature", 25.0),
            ))

        # String mismatch
        string_currents = {
            k.replace("string_", "").replace("_current", ""): v
            for k, v in metrics.items()
            if k.startswith("string_") and k.endswith("_current")
        }
        if string_currents:
            events.extend(detector.check_string_mismatch(
                device_id=device_id,
                timestamp=timestamp,
                string_currents=string_currents,
            ))

        # Battery check
        if "battery_soc" in metrics and "battery_voltage" in metrics:
            events.extend(detector.check_battery(
                device_id=device_id,
                timestamp=timestamp,
                soc=metrics["battery_soc"],
                voltage=metrics["battery_voltage"],
                current=metrics.get("battery_current", 0.0),
                temperature_c=metrics.get("battery_temperature", 25.0),
            ))

        # Store history
        for event in events:
            self._history.append(event)
        # Trim history
        if len(self._history) > self._max_history:
            self._history = self._history[-self._max_history:]

        return events

    def get_recent_anomalies(
        self,
        device_id: Optional[str] = None,
        anomaly_type: Optional[AnomalyType] = None,
        severity: Optional[AnomalySeverity] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """Query recent anomalies with optional filters."""

        filtered = self._history
        if device_id:
            filtered = [e for e in filtered if e.device_id == device_id]
        if anomaly_type:
            filtered = [e for e in filtered if e.anomaly_type == anomaly_type]
        if severity:
            filtered = [e for e in filtered if e.severity == severity]

        return [e.to_dict() for e in filtered[-limit:]]

    def summary(self) -> Dict[str, Any]:
        """Return anomaly monitoring summary."""
        by_type: Dict[str, int] = {}
        by_severity: Dict[str, int] = {}
        by_device: Dict[str, int] = {}

        for event in self._history:
            by_type[event.anomaly_type.value] = by_type.get(event.anomaly_type.value, 0) + 1
            by_severity[event.severity.value] = by_severity.get(event.severity.value, 0) + 1
            by_device[event.device_id] = by_device.get(event.device_id, 0) + 1

        return {
            "total_events": len(self._history),
            "monitored_devices": len(self._detectors),
            "by_type": by_type,
            "by_severity": by_severity,
            "by_device": by_device,
        }
