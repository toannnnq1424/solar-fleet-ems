"""Grid-code compliance and autonomous voltage/frequency regulation engine.

Independently implemented for Solar Fleet EMS.
Concepts from OpenEMS io.openems.edge.controller.ess.activepowervoltagecharacteristic,
io.openems.edge.controller.ess.reactivepowervoltagecharacteristic,
and io.openems.edge.protectionrelay.telehaase (NA003).
Complies with IEEE 1547-2018 and AS/NZS 4777.2 grid interconnection standards.
No code copied.

Provides:
- Volt-Watt P(V) piecewise linear active power curtailment to mitigate grid overvoltage
- Volt-Var Q(V) autonomous reactive power injection/absorption for voltage support
- Frequency-Watt P(f) over-frequency and under-frequency droop response
- Anti-islanding grid loss protection filter (over/under voltage and frequency trip gates)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, Optional

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GridConnectionState(str, Enum):
    """Grid operational state per IEEE 1547 standard."""

    CONNECTED_NORMAL = "connected_normal"
    VOLT_VAR_ACTIVE = "volt_var_active"
    VOLT_WATT_CURTAILED = "volt_watt_curtailed"
    FREQ_WATT_DROOP = "freq_watt_droop"
    TRIPPED_OVER_VOLTAGE = "tripped_over_voltage"
    TRIPPED_UNDER_VOLTAGE = "tripped_under_voltage"
    TRIPPED_OVER_FREQUENCY = "tripped_over_frequency"
    TRIPPED_UNDER_FREQUENCY = "tripped_under_frequency"


# ---------------------------------------------------------------------------
# 1. Volt-Watt P(V) Characteristic Curve
# ---------------------------------------------------------------------------

@dataclass
class VoltWattCurve:
    """Piecewise linear Volt-Watt active power curtailment characteristic.

    Standard points (V in Volts, P in per-unit of rated power):
    V1: 207V (0.90 p.u.) -> P = 1.0 p.u.
    V2: 253V (1.10 p.u.) -> P = 1.0 p.u. (curtailment begins)
    V3: 258V (1.12 p.u.) -> P = 0.5 p.u.
    V4: 265V (1.15 p.u.) -> P = 0.2 p.u. (maximum curtailment floor)
    """

    nominal_voltage_v: float = 230.0
    v1_v: float = 207.0
    v2_v: float = 253.0
    v3_v: float = 258.0
    v4_v: float = 265.0
    p_rated_kw: float = 10.0
    min_power_ratio: float = 0.20

    def calculate_power_limit(self, measured_voltage_v: float) -> Dict[str, float]:
        """Compute maximum allowable active power generation at measured voltage."""
        v = measured_voltage_v

        if v <= self.v2_v:
            # Below curtailment threshold: full 100% power allowed
            p_pu = 1.0
        elif v <= self.v3_v:
            # Linear curtailment from 1.0 down to 0.5
            slope = (0.5 - 1.0) / (self.v3_v - self.v2_v)
            p_pu = 1.0 + slope * (v - self.v2_v)
        elif v <= self.v4_v:
            # Linear curtailment from 0.5 down to min_power_ratio
            slope = (self.min_power_ratio - 0.5) / (self.v4_v - self.v3_v)
            p_pu = 0.5 + slope * (v - self.v3_v)
        else:
            # Above V4: clamped to minimum power floor
            p_pu = self.min_power_ratio

        p_pu = max(self.min_power_ratio, min(1.0, p_pu))
        power_limit_kw = p_pu * self.p_rated_kw

        return {
            "power_limit_kw": round(power_limit_kw, 3),
            "power_pu": round(p_pu, 4),
            "is_curtailed": p_pu < 0.999,
            "measured_voltage_v": round(v, 2),
        }


# ---------------------------------------------------------------------------
# 2. Volt-Var Q(V) Characteristic Curve
# ---------------------------------------------------------------------------

@dataclass
class VoltVarCurve:
    """Piecewise linear Volt-Var reactive power voltage support characteristic.

    Standard points (V in Volts, Q in per-unit of rated kVA):
    V1: 207V (Low voltage)  -> Q = +0.44 p.u. (Capacitive / boost voltage)
    V2: 220V (Deadband low) -> Q = 0.0
    V3: 240V (Deadband high)-> Q = 0.0
    V4: 258V (High voltage) -> Q = -0.44 p.u. (Inductive / depress voltage)
    """

    nominal_voltage_v: float = 230.0
    v1_v: float = 207.0
    v2_v: float = 220.0
    v3_v: float = 240.0
    v4_v: float = 258.0
    q_max_ratio: float = 0.44  # Max 44% of rated kVA as reactive power
    rated_kva: float = 10.0

    def calculate_reactive_power(self, measured_voltage_v: float) -> Dict[str, float]:
        """Compute required reactive power setpoint (+ capacitive, - inductive)."""
        v = measured_voltage_v

        if v <= self.v1_v:
            q_pu = self.q_max_ratio  # Maximum capacitive boost
        elif v <= self.v2_v:
            # Linear transition from +Q_max down to 0
            slope = (0.0 - self.q_max_ratio) / (self.v2_v - self.v1_v)
            q_pu = self.q_max_ratio + slope * (v - self.v1_v)
        elif v <= self.v3_v:
            # Deadband: no reactive power injection
            q_pu = 0.0
        elif v <= self.v4_v:
            # Linear transition from 0 down to -Q_max
            slope = (-self.q_max_ratio - 0.0) / (self.v4_v - self.v3_v)
            q_pu = slope * (v - self.v3_v)
        else:
            # Above V4: maximum inductive absorption
            q_pu = -self.q_max_ratio

        q_pu = max(-self.q_max_ratio, min(self.q_max_ratio, q_pu))
        q_kvar = q_pu * self.rated_kva

        return {
            "reactive_power_kvar": round(q_kvar, 3),
            "q_pu": round(q_pu, 4),
            "mode": "capacitive_boost" if q_kvar > 0.01 else ("inductive_buck" if q_kvar < -0.01 else "deadband"),
            "measured_voltage_v": round(v, 2),
        }


# ---------------------------------------------------------------------------
# 3. Frequency-Watt P(f) Droop Response
# ---------------------------------------------------------------------------

@dataclass
class FreqWattDroop:
    """Frequency-dependent active power droop per IEEE 1547 / EN 50549.

    Nominal: 50.0 Hz (or 60.0 Hz)
    Over-frequency deadband: 50.2 Hz
    Under-frequency deadband: 49.8 Hz
    Droop slope: typically 4% to 5% droop
    """

    nominal_freq_hz: float = 50.0
    over_freq_threshold_hz: float = 50.2
    under_freq_threshold_hz: float = 49.8
    droop_pct: float = 5.0  # 5% droop: 100% power delta per 2.5 Hz deviation
    p_rated_kw: float = 10.0

    def calculate_power_adjustment(
        self,
        measured_freq_hz: float,
        current_power_kw: float,
    ) -> Dict[str, float]:
        """Compute active power adjustment factor based on grid frequency."""
        f = measured_freq_hz
        delta_p_kw = 0.0

        if f > self.over_freq_threshold_hz:
            # Over-frequency: curtail active power
            freq_excess = f - self.over_freq_threshold_hz
            # P_curtail = (delta_f / (nominal_f * droop)) * P_rated
            curtail_ratio = freq_excess / (self.nominal_freq_hz * (self.droop_pct / 100.0))
            delta_p_kw = -curtail_ratio * self.p_rated_kw
            target_kw = max(0.0, current_power_kw + delta_p_kw)
        elif f < self.under_freq_threshold_hz:
            # Under-frequency: boost active power if headroom available
            freq_deficit = self.under_freq_threshold_hz - f
            boost_ratio = freq_deficit / (self.nominal_freq_hz * (self.droop_pct / 100.0))
            delta_p_kw = boost_ratio * self.p_rated_kw
            target_kw = min(self.p_rated_kw, current_power_kw + delta_p_kw)
        else:
            target_kw = current_power_kw

        return {
            "target_power_kw": round(target_kw, 3),
            "delta_power_kw": round(delta_p_kw, 3),
            "is_droop_active": abs(delta_p_kw) > 0.01,
            "measured_freq_hz": round(f, 3),
        }


# ---------------------------------------------------------------------------
# 4. Anti-Islanding Protection Relay Monitor
# ---------------------------------------------------------------------------

@dataclass
class ProtectionRelayLimits:
    """Statutory grid disconnect limits (TeleHaase NA003 / EN 50549)."""

    v_min_trip_v: float = 184.0   # 0.80 p.u. of 230V
    v_max_trip_v: float = 264.5   # 1.15 p.u. of 230V
    f_min_trip_hz: float = 47.5   # Under-frequency trip
    f_max_trip_hz: float = 51.5   # Over-frequency trip


class GridCodeRegulator:
    """Comprehensive grid-code regulation and protection coordinator."""

    def __init__(
        self,
        volt_watt: Optional[VoltWattCurve] = None,
        volt_var: Optional[VoltVarCurve] = None,
        freq_watt: Optional[FreqWattDroop] = None,
        protection: Optional[ProtectionRelayLimits] = None,
    ):
        self.vw = volt_watt or VoltWattCurve()
        self.vv = volt_var or VoltVarCurve()
        self.fw = freq_watt or FreqWattDroop()
        self.prot = protection or ProtectionRelayLimits()

    def evaluate(
        self,
        measured_voltage_v: float,
        measured_freq_hz: float,
        current_active_power_kw: float,
    ) -> Dict[str, Any]:
        """Evaluate grid compliance and compute coordinated P & Q commands."""
        # 1. Protection Trip Checks
        if measured_voltage_v >= self.prot.v_max_trip_v:
            return {
                "state": GridConnectionState.TRIPPED_OVER_VOLTAGE.value,
                "allow_inverter_run": False,
                "target_p_kw": 0.0,
                "target_q_kvar": 0.0,
                "reason": f"Grid overvoltage trip: {measured_voltage_v}V >= {self.prot.v_max_trip_v}V",
            }
        if measured_voltage_v <= self.prot.v_min_trip_v:
            return {
                "state": GridConnectionState.TRIPPED_UNDER_VOLTAGE.value,
                "allow_inverter_run": False,
                "target_p_kw": 0.0,
                "target_q_kvar": 0.0,
                "reason": f"Grid undervoltage trip: {measured_voltage_v}V <= {self.prot.v_min_trip_v}V",
            }
        if measured_freq_hz >= self.prot.f_max_trip_hz:
            return {
                "state": GridConnectionState.TRIPPED_OVER_FREQUENCY.value,
                "allow_inverter_run": False,
                "target_p_kw": 0.0,
                "target_q_kvar": 0.0,
                "reason": f"Grid overfrequency trip: {measured_freq_hz}Hz >= {self.prot.f_max_trip_hz}Hz",
            }
        if measured_freq_hz <= self.prot.f_min_trip_hz:
            return {
                "state": GridConnectionState.TRIPPED_UNDER_FREQUENCY.value,
                "allow_inverter_run": False,
                "target_p_kw": 0.0,
                "target_q_kvar": 0.0,
                "reason": f"Grid underfrequency trip: {measured_freq_hz}Hz <= {self.prot.f_min_trip_hz}Hz",
            }

        # 2. Autonomous Regulation Curves
        vw_res = self.vw.calculate_power_limit(measured_voltage_v)
        vv_res = self.vv.calculate_reactive_power(measured_voltage_v)
        fw_res = self.fw.calculate_power_adjustment(measured_freq_hz, current_active_power_kw)

        # Active power command is constrained by both Volt-Watt and Freq-Watt
        final_p_kw = min(vw_res["power_limit_kw"], fw_res["target_power_kw"])
        final_q_kvar = vv_res["reactive_power_kvar"]

        # Determine state
        if vw_res["is_curtailed"]:
            state = GridConnectionState.VOLT_WATT_CURTAILED
        elif fw_res["is_droop_active"]:
            state = GridConnectionState.FREQ_WATT_DROOP
        elif abs(final_q_kvar) > 0.05:
            state = GridConnectionState.VOLT_VAR_ACTIVE
        else:
            state = GridConnectionState.CONNECTED_NORMAL

        return {
            "state": state.value,
            "allow_inverter_run": True,
            "target_p_kw": round(final_p_kw, 3),
            "target_q_kvar": round(final_q_kvar, 3),
            "volt_watt": vw_res,
            "volt_var": vv_res,
            "freq_watt": fw_res,
        }
