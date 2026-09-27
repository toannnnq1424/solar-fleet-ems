"""Power quality monitoring and analysis.

Independently implemented for Solar Fleet EMS.
Based on IEEE 1159-2019 power quality standards
and IEC 61000-4-30 measurement methods.
"""

from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List


class PQEventType(str, Enum):
    """Power quality event type per IEEE 1159."""

    NORMAL = "normal"
    SAG = "sag"             # 0.1 - 0.9 pu, 0.5 cycles to 1 min
    SWELL = "swell"         # 1.1 - 1.8 pu, 0.5 cycles to 1 min
    INTERRUPTION = "interruption"  # < 0.1 pu
    OVERVOLTAGE = "overvoltage"    # > 1.1 pu sustained
    UNDERVOLTAGE = "undervoltage"  # < 0.9 pu sustained
    HARMONIC = "harmonic"          # THD > limits
    FLICKER = "flicker"
    FREQUENCY_DEV = "frequency_deviation"
    UNBALANCE = "unbalance"
    TRANSIENT = "transient"


class PQSeverity(str, Enum):
    INFO = "info"
    WARNING = "warning"
    ALARM = "alarm"
    CRITICAL = "critical"


@dataclass
class PQEvent:
    """A power quality event."""

    event_type: PQEventType
    severity: PQSeverity
    timestamp: str
    duration_ms: float = 0.0
    magnitude_pu: float = 1.0
    phase: str = "all"
    description: str = ""
    measured_value: float = 0.0
    limit_value: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "event_type": self.event_type.value,
            "severity": self.severity.value,
            "timestamp": self.timestamp,
            "duration_ms": round(self.duration_ms, 1),
            "magnitude_pu": round(self.magnitude_pu, 4),
            "phase": self.phase,
            "description": self.description,
            "measured_value": round(self.measured_value, 3),
            "limit_value": round(self.limit_value, 3),
        }


@dataclass
class PQMeasurement:
    """Instantaneous power quality measurement."""

    timestamp: str = ""
    voltage_l1_v: float = 230.0
    voltage_l2_v: float = 230.0
    voltage_l3_v: float = 230.0
    current_l1_a: float = 0.0
    current_l2_a: float = 0.0
    current_l3_a: float = 0.0
    frequency_hz: float = 50.0
    thd_voltage_pct: float = 0.0
    thd_current_pct: float = 0.0
    power_factor: float = 1.0
    voltage_unbalance_pct: float = 0.0
    flicker_pst: float = 0.0

    @property
    def voltage_avg_v(self) -> float:
        return (
            self.voltage_l1_v + self.voltage_l2_v + self.voltage_l3_v
        ) / 3

    @property
    def voltage_avg_pu(self) -> float:
        return self.voltage_avg_v / 230.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "timestamp": self.timestamp,
            "voltage_l1_v": round(self.voltage_l1_v, 1),
            "voltage_l2_v": round(self.voltage_l2_v, 1),
            "voltage_l3_v": round(self.voltage_l3_v, 1),
            "frequency_hz": round(self.frequency_hz, 3),
            "thd_voltage_pct": round(self.thd_voltage_pct, 2),
            "thd_current_pct": round(self.thd_current_pct, 2),
            "power_factor": round(self.power_factor, 3),
            "voltage_unbalance_pct": round(
                self.voltage_unbalance_pct, 2,
            ),
            "flicker_pst": round(self.flicker_pst, 2),
        }


# ---------------------------------------------------------------------------
# Power Quality Monitor
# ---------------------------------------------------------------------------

class PowerQualityMonitor:
    """Monitor and analyze power quality at a site.

    Checks against IEEE 1159 / IEC 61000 limits:
    - Voltage: 0.9 - 1.1 pu (207 - 253 V for 230V nominal)
    - Frequency: ±0.5 Hz from nominal
    - THDv: < 5% (IEEE 519-2022)
    - THDi: < 5% for >1000 kVA
    - Voltage unbalance: < 2%
    - Flicker Pst: < 1.0
    """

    def __init__(
        self,
        nominal_voltage_v: float = 230.0,
        nominal_frequency_hz: float = 50.0,
    ) -> None:
        self.nominal_voltage = nominal_voltage_v
        self.nominal_frequency = nominal_frequency_hz
        self._events: List[PQEvent] = []
        self._measurements: List[PQMeasurement] = []
        self._stats = {
            "sag_count": 0,
            "swell_count": 0,
            "interruption_count": 0,
            "harmonic_violations": 0,
            "frequency_deviations": 0,
        }

        # Configurable limits
        self.voltage_upper_pu = 1.10
        self.voltage_lower_pu = 0.90
        self.voltage_sag_pu = 0.90
        self.voltage_swell_pu = 1.10
        self.voltage_interruption_pu = 0.10
        self.frequency_tolerance_hz = 0.5
        self.thd_voltage_limit_pct = 5.0
        self.thd_current_limit_pct = 5.0
        self.unbalance_limit_pct = 2.0
        self.flicker_pst_limit = 1.0

    def analyze(self, m: PQMeasurement) -> List[PQEvent]:
        """Analyze a single measurement for PQ events."""
        ts = m.timestamp or datetime.now(timezone.utc).isoformat()
        events: List[PQEvent] = []
        self._measurements.append(m)

        # Voltage analysis per phase
        for phase, v in [
            ("L1", m.voltage_l1_v),
            ("L2", m.voltage_l2_v),
            ("L3", m.voltage_l3_v),
        ]:
            v_pu = v / self.nominal_voltage

            if v_pu < self.voltage_interruption_pu:
                events.append(PQEvent(
                    PQEventType.INTERRUPTION, PQSeverity.CRITICAL, ts,
                    magnitude_pu=v_pu, phase=phase,
                    description=f"Voltage interruption on {phase}",
                    measured_value=v, limit_value=self.nominal_voltage * 0.1,
                ))
                self._stats["interruption_count"] += 1
            elif v_pu < self.voltage_sag_pu:
                events.append(PQEvent(
                    PQEventType.SAG, PQSeverity.WARNING, ts,
                    magnitude_pu=v_pu, phase=phase,
                    description=f"Voltage sag on {phase}: {v:.1f}V",
                    measured_value=v,
                    limit_value=self.nominal_voltage * self.voltage_sag_pu,
                ))
                self._stats["sag_count"] += 1
            elif v_pu > self.voltage_swell_pu:
                events.append(PQEvent(
                    PQEventType.SWELL, PQSeverity.WARNING, ts,
                    magnitude_pu=v_pu, phase=phase,
                    description=f"Voltage swell on {phase}: {v:.1f}V",
                    measured_value=v,
                    limit_value=self.nominal_voltage * self.voltage_swell_pu,
                ))
                self._stats["swell_count"] += 1

        # Frequency
        freq_dev = abs(m.frequency_hz - self.nominal_frequency)
        if freq_dev > self.frequency_tolerance_hz:
            sev = (
                PQSeverity.CRITICAL if freq_dev > 1.0
                else PQSeverity.ALARM
            )
            events.append(PQEvent(
                PQEventType.FREQUENCY_DEV, sev, ts,
                magnitude_pu=m.frequency_hz / self.nominal_frequency,
                description=f"Frequency: {m.frequency_hz:.2f} Hz",
                measured_value=m.frequency_hz,
                limit_value=self.nominal_frequency,
            ))
            self._stats["frequency_deviations"] += 1

        # THD voltage
        if m.thd_voltage_pct > self.thd_voltage_limit_pct:
            events.append(PQEvent(
                PQEventType.HARMONIC, PQSeverity.WARNING, ts,
                description=f"THDv: {m.thd_voltage_pct:.1f}%",
                measured_value=m.thd_voltage_pct,
                limit_value=self.thd_voltage_limit_pct,
            ))
            self._stats["harmonic_violations"] += 1

        # THD current
        if m.thd_current_pct > self.thd_current_limit_pct:
            events.append(PQEvent(
                PQEventType.HARMONIC, PQSeverity.WARNING, ts,
                description=f"THDi: {m.thd_current_pct:.1f}%",
                measured_value=m.thd_current_pct,
                limit_value=self.thd_current_limit_pct,
            ))

        # Voltage unbalance
        if m.voltage_unbalance_pct > self.unbalance_limit_pct:
            events.append(PQEvent(
                PQEventType.UNBALANCE, PQSeverity.WARNING, ts,
                description=(
                    f"Unbalance: {m.voltage_unbalance_pct:.1f}%"
                ),
                measured_value=m.voltage_unbalance_pct,
                limit_value=self.unbalance_limit_pct,
            ))

        # Flicker
        if m.flicker_pst > self.flicker_pst_limit:
            events.append(PQEvent(
                PQEventType.FLICKER, PQSeverity.WARNING, ts,
                description=f"Flicker Pst: {m.flicker_pst:.2f}",
                measured_value=m.flicker_pst,
                limit_value=self.flicker_pst_limit,
            ))

        self._events.extend(events)
        return events

    @staticmethod
    def calculate_voltage_unbalance(
        v1: float, v2: float, v3: float,
    ) -> float:
        """Calculate voltage unbalance (NEMA definition).

        Returns percentage unbalance.
        """
        avg = (v1 + v2 + v3) / 3
        if avg <= 0:
            return 0.0
        max_dev = max(abs(v1 - avg), abs(v2 - avg), abs(v3 - avg))
        return (max_dev / avg) * 100

    @staticmethod
    def calculate_thd(
        fundamental: float, harmonics: List[float],
    ) -> float:
        """Calculate Total Harmonic Distortion.

        Parameters
        ----------
        fundamental : float
            Fundamental component magnitude.
        harmonics : list of float
            Harmonic component magnitudes (2nd, 3rd, ...).

        Returns
        -------
        float
            THD percentage.
        """
        if fundamental <= 0:
            return 0.0
        rss = math.sqrt(sum(h ** 2 for h in harmonics))
        return (rss / fundamental) * 100

    def summary(self) -> Dict[str, Any]:
        """Get PQ monitoring summary."""
        n = len(self._measurements)
        if n == 0:
            return {"measurements": 0, "events": 0}

        avg_v = sum(
            m.voltage_avg_v for m in self._measurements
        ) / n
        avg_f = sum(
            m.frequency_hz for m in self._measurements
        ) / n

        return {
            "measurements": n,
            "events": len(self._events),
            "average_voltage_v": round(avg_v, 1),
            "average_frequency_hz": round(avg_f, 3),
            "stats": dict(self._stats),
            "compliance": {
                "voltage_ok": self._stats["sag_count"] == 0
                and self._stats["swell_count"] == 0,
                "frequency_ok": (
                    self._stats["frequency_deviations"] == 0
                ),
                "harmonic_ok": (
                    self._stats["harmonic_violations"] == 0
                ),
            },
        }

    def recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Get recent PQ events."""
        return [e.to_dict() for e in self._events[-limit:]]
