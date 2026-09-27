"""Grid inverter models — grid-forming and grid-following.

Independently implemented for Solar Fleet EMS.
Physical models based on published power systems engineering.
Concepts inspired by virtual-power-plant-main (MIT license)
grid/inverter.py.

Grid-forming inverters establish voltage and frequency (droop control,
virtual synchronous machine). Grid-following inverters track the grid
and inject/absorb power based on a setpoint.
"""

from __future__ import annotations

import math
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any, Dict, List, Optional

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class InverterOperatingPoint:
    """Instantaneous inverter operating point."""

    real_power_kw: float = 0.0
    reactive_power_kvar: float = 0.0
    voltage_pu: float = 1.0
    frequency_hz: float = 50.0
    current_a: float = 0.0
    power_factor: float = 1.0
    efficiency: float = 0.97
    is_online: bool = True

    def to_dict(self) -> dict[str, Any]:
        return {
            "real_power_kw": round(self.real_power_kw, 3),
            "reactive_power_kvar": round(self.reactive_power_kvar, 3),
            "voltage_pu": round(self.voltage_pu, 4),
            "frequency_hz": round(self.frequency_hz, 3),
            "power_factor": round(self.power_factor, 3),
            "efficiency": round(self.efficiency, 4),
            "is_online": self.is_online,
        }

    @property
    def apparent_power_kva(self) -> float:
        """Apparent power magnitude."""
        return math.sqrt(self.real_power_kw ** 2 + self.reactive_power_kvar ** 2)


# ---------------------------------------------------------------------------
# Efficiency curve model
# ---------------------------------------------------------------------------

class InverterEfficiencyCurve:
    """Inverter efficiency as a function of loading.

    Uses a 3-parameter model: η = P_out / (P_out + P_self + k * P_out²)
    where P_self is standby loss and k is resistive loss coefficient.
    """

    def __init__(
        self,
        rated_power_kw: float,
        peak_efficiency: float = 0.98,
        standby_loss_kw: float = 0.01,
        euro_efficiency: Optional[float] = None,
    ) -> None:
        self.rated_power_kw = rated_power_kw
        self.peak_efficiency = peak_efficiency
        self.standby_loss_kw = standby_loss_kw

        # Derive resistive loss coefficient from peak efficiency
        # At peak: η = P / (P + P_self + k*P²) => k = (1/η - 1)*1/P - P_self/P²
        p_peak = rated_power_kw * 0.3  # Peak efficiency typically at 30% loading
        if p_peak > 0 and peak_efficiency > 0:
            self._k = max(0, (1 / peak_efficiency - 1) / p_peak - standby_loss_kw / p_peak ** 2)
        else:
            self._k = 0.001

    def efficiency(self, power_kw: float) -> float:
        """Calculate efficiency at given power level."""
        p = abs(power_kw)
        if p < 0.001:
            return 0.0

        losses = self.standby_loss_kw + self._k * p ** 2
        eff = p / (p + losses)
        return max(0.0, min(1.0, eff))

    def losses(self, power_kw: float) -> float:
        """Calculate power losses at given power level."""
        p = abs(power_kw)
        return self.standby_loss_kw + self._k * p ** 2

    def curve_points(self, steps: int = 20) -> List[Dict[str, float]]:
        """Generate efficiency curve data points."""
        points = []
        for i in range(1, steps + 1):
            p_frac = i / steps
            p = p_frac * self.rated_power_kw
            eff = self.efficiency(p)
            points.append({
                "loading_pct": round(p_frac * 100, 1),
                "power_kw": round(p, 2),
                "efficiency_pct": round(eff * 100, 2),
                "losses_kw": round(self.losses(p), 3),
            })
        return points


# ---------------------------------------------------------------------------
# Abstract inverter model
# ---------------------------------------------------------------------------

class InverterModel(ABC):
    """Abstract base for all inverter models."""

    def __init__(
        self,
        inverter_id: str,
        rated_power_kw: float,
        rated_voltage_v: float = 400.0,
        nominal_frequency_hz: float = 50.0,
        max_dc_voltage_v: float = 1000.0,
        mppt_channels: int = 2,
    ) -> None:
        self.inverter_id = inverter_id
        self.rated_power_kw = rated_power_kw
        self.rated_voltage_v = rated_voltage_v
        self.nominal_frequency_hz = nominal_frequency_hz
        self.max_dc_voltage_v = max_dc_voltage_v
        self.mppt_channels = mppt_channels
        self.state = InverterOperatingPoint(frequency_hz=nominal_frequency_hz)
        self._efficiency_curve = InverterEfficiencyCurve(rated_power_kw)
        self._total_energy_kwh: float = 0.0
        self._operating_hours: float = 0.0

    @abstractmethod
    def update(
        self,
        dt_seconds: float,
        grid_voltage_pu: float,
        grid_frequency_hz: float,
    ) -> InverterOperatingPoint:
        """Update inverter state for one time step."""

    @abstractmethod
    def set_power_reference(
        self,
        p_kw: float,
        q_kvar: float = 0.0,
    ) -> None:
        """Set active/reactive power reference."""

    def to_dict(self) -> dict[str, Any]:
        return {
            "inverter_id": self.inverter_id,
            "type": type(self).__name__,
            "rated_power_kw": self.rated_power_kw,
            "rated_voltage_v": self.rated_voltage_v,
            "mppt_channels": self.mppt_channels,
            "total_energy_kwh": round(self._total_energy_kwh, 2),
            "operating_hours": round(self._operating_hours, 1),
            "state": self.state.to_dict(),
        }


# ---------------------------------------------------------------------------
# Grid-following inverter
# ---------------------------------------------------------------------------

class GridFollowingInverter(InverterModel):
    """Grid-following (current-source) inverter.

    Tracks the grid voltage and frequency; injects power at the commanded
    setpoint. Used for standard PV inverters and battery inverters in
    grid-connected mode.
    """

    def __init__(
        self,
        inverter_id: str,
        rated_power_kw: float,
        rated_voltage_v: float = 400.0,
        nominal_frequency_hz: float = 50.0,
        ramp_rate_kw_per_s: float = 100.0,
        max_dc_voltage_v: float = 1000.0,
        mppt_channels: int = 2,
    ) -> None:
        super().__init__(
            inverter_id, rated_power_kw, rated_voltage_v,
            nominal_frequency_hz, max_dc_voltage_v, mppt_channels,
        )
        self.ramp_rate_kw_per_s = ramp_rate_kw_per_s
        self._p_ref: float = 0.0
        self._q_ref: float = 0.0

    def set_power_reference(self, p_kw: float, q_kvar: float = 0.0) -> None:
        """Set active/reactive power reference.

        Power is clamped to rated capacity.
        """
        self._p_ref = max(-self.rated_power_kw, min(self.rated_power_kw, p_kw))
        apparent_limit = self.rated_power_kw  # Assuming unity rated VA/W ratio
        q_max = math.sqrt(max(0, apparent_limit ** 2 - self._p_ref ** 2))
        self._q_ref = max(-q_max, min(q_max, q_kvar))

    def update(
        self,
        dt_seconds: float,
        grid_voltage_pu: float,
        grid_frequency_hz: float,
    ) -> InverterOperatingPoint:
        """Update inverter state, ramping toward reference."""

        if not self.state.is_online:
            return self.state

        # Ramp toward reference
        dp_max = self.ramp_rate_kw_per_s * dt_seconds
        dp = self._p_ref - self.state.real_power_kw
        dp = max(-dp_max, min(dp_max, dp))
        self.state.real_power_kw += dp

        dq_max = dp_max  # same ramp rate for reactive
        dq = self._q_ref - self.state.reactive_power_kvar
        dq = max(-dq_max, min(dq_max, dq))
        self.state.reactive_power_kvar += dq

        # Follow grid
        self.state.voltage_pu = grid_voltage_pu
        self.state.frequency_hz = grid_frequency_hz

        # Update efficiency
        self.state.efficiency = self._efficiency_curve.efficiency(self.state.real_power_kw)

        # Power factor
        s = self.state.apparent_power_kva
        if s > 0.001:
            self.state.power_factor = abs(self.state.real_power_kw) / s
        else:
            self.state.power_factor = 1.0

        # Current
        v = grid_voltage_pu * self.rated_voltage_v
        if v > 0:
            self.state.current_a = s * 1000 / (v * math.sqrt(3))

        # Accumulate energy and hours
        if abs(self.state.real_power_kw) > 0.01:
            self._total_energy_kwh += abs(self.state.real_power_kw) * dt_seconds / 3600.0
            self._operating_hours += dt_seconds / 3600.0

        return self.state


# ---------------------------------------------------------------------------
# Grid-forming inverter
# ---------------------------------------------------------------------------

class GridFormingInverter(InverterModel):
    """Grid-forming (voltage-source) inverter.

    Establishes voltage and frequency using droop control. Used as the
    reference source in island mode.
    """

    def __init__(
        self,
        inverter_id: str,
        rated_power_kw: float,
        rated_voltage_v: float = 400.0,
        nominal_frequency_hz: float = 50.0,
        droop_kp: float = 0.05,
        droop_kq: float = 0.05,
        inertia_constant_s: float = 5.0,
        ramp_rate_kw_per_s: float = 50.0,
    ) -> None:
        super().__init__(
            inverter_id, rated_power_kw, rated_voltage_v, nominal_frequency_hz,
        )
        self.droop_kp = droop_kp
        self.droop_kq = droop_kq
        self.inertia_constant_s = inertia_constant_s
        self.ramp_rate_kw_per_s = ramp_rate_kw_per_s
        self._p_ref: float = 0.0
        self._q_ref: float = 0.0
        self._omega: float = 2 * math.pi * nominal_frequency_hz

    def set_power_reference(self, p_kw: float, q_kvar: float = 0.0) -> None:
        """Set power reference for droop control."""
        self._p_ref = max(-self.rated_power_kw, min(self.rated_power_kw, p_kw))
        self._q_ref = max(-self.rated_power_kw, min(self.rated_power_kw, q_kvar))

    def update(
        self,
        dt_seconds: float,
        grid_voltage_pu: float,
        grid_frequency_hz: float,
    ) -> InverterOperatingPoint:
        """Update grid-forming inverter state.

        Uses droop characteristic to set frequency and voltage based on
        active/reactive power output.
        """

        if not self.state.is_online:
            return self.state

        # P-f droop
        p_pu = self.state.real_power_kw / self.rated_power_kw if self.rated_power_kw > 0 else 0
        p_ref_pu = self._p_ref / self.rated_power_kw if self.rated_power_kw > 0 else 0
        freq_setpoint = self.nominal_frequency_hz * (1.0 - self.droop_kp * (p_pu - p_ref_pu))

        # Virtual inertia (swing equation integration)
        if self.inertia_constant_s > 0:
            d_omega = (freq_setpoint - self.state.frequency_hz) / self.inertia_constant_s * dt_seconds
            self.state.frequency_hz += d_omega
        else:
            self.state.frequency_hz = freq_setpoint

        # Q-V droop
        q_pu = self.state.reactive_power_kvar / self.rated_power_kw if self.rated_power_kw > 0 else 0
        q_ref_pu = self._q_ref / self.rated_power_kw if self.rated_power_kw > 0 else 0
        self.state.voltage_pu = 1.0 - self.droop_kq * (q_pu - q_ref_pu)
        self.state.voltage_pu = max(0.85, min(1.15, self.state.voltage_pu))

        # Ramp power
        dp_max = self.ramp_rate_kw_per_s * dt_seconds
        dp = self._p_ref - self.state.real_power_kw
        dp = max(-dp_max, min(dp_max, dp))
        self.state.real_power_kw += dp

        dq = self._q_ref - self.state.reactive_power_kvar
        dq = max(-dp_max, min(dp_max, dq))
        self.state.reactive_power_kvar += dq

        # Efficiency and metrics
        self.state.efficiency = self._efficiency_curve.efficiency(self.state.real_power_kw)

        s = self.state.apparent_power_kva
        if s > 0.001:
            self.state.power_factor = abs(self.state.real_power_kw) / s

        if abs(self.state.real_power_kw) > 0.01:
            self._total_energy_kwh += abs(self.state.real_power_kw) * dt_seconds / 3600.0
            self._operating_hours += dt_seconds / 3600.0

        return self.state


# ---------------------------------------------------------------------------
# Battery inverter (bidirectional)
# ---------------------------------------------------------------------------

class BatteryInverter(GridFollowingInverter):
    """Bidirectional battery inverter.

    Extends grid-following with battery SOC management, charge/discharge
    limits, and BMS integration points.
    """

    def __init__(
        self,
        inverter_id: str,
        rated_power_kw: float,
        battery_capacity_kwh: float,
        soc_init: float = 0.5,
        soc_min: float = 0.05,
        soc_max: float = 0.95,
        charge_efficiency: float = 0.95,
        discharge_efficiency: float = 0.95,
        **kwargs: Any,
    ) -> None:
        super().__init__(inverter_id, rated_power_kw, **kwargs)
        self.battery_capacity_kwh = battery_capacity_kwh
        self.soc = soc_init
        self.soc_min = soc_min
        self.soc_max = soc_max
        self.charge_efficiency = charge_efficiency
        self.discharge_efficiency = discharge_efficiency
        self._charge_energy_kwh: float = 0.0
        self._discharge_energy_kwh: float = 0.0
        self._cycle_count: float = 0.0

    def update(
        self,
        dt_seconds: float,
        grid_voltage_pu: float,
        grid_frequency_hz: float,
    ) -> InverterOperatingPoint:
        """Update battery inverter with SOC tracking."""

        # Apply SOC limits to power reference
        dt_hours = dt_seconds / 3600.0
        soc_kwh = self.soc * self.battery_capacity_kwh

        if self._p_ref > 0:  # Charging
            available_capacity = (self.soc_max * self.battery_capacity_kwh) - soc_kwh
            max_charge_power = available_capacity / (dt_hours * self.charge_efficiency) if dt_hours > 0 else 0
            self._p_ref = min(self._p_ref, max_charge_power)
        elif self._p_ref < 0:  # Discharging
            available_energy = soc_kwh - (self.soc_min * self.battery_capacity_kwh)
            max_discharge_power = available_energy * self.discharge_efficiency / dt_hours if dt_hours > 0 else 0
            self._p_ref = max(self._p_ref, -max_discharge_power)

        # Run base update
        result = super().update(dt_seconds, grid_voltage_pu, grid_frequency_hz)

        # Update SOC
        if result.real_power_kw > 0:  # Charging
            energy_in = result.real_power_kw * dt_hours * self.charge_efficiency
            soc_kwh += energy_in
            self._charge_energy_kwh += energy_in
        elif result.real_power_kw < 0:  # Discharging
            energy_out = abs(result.real_power_kw) * dt_hours / self.discharge_efficiency
            soc_kwh -= energy_out
            self._discharge_energy_kwh += energy_out

        soc_kwh = max(
            self.soc_min * self.battery_capacity_kwh,
            min(self.soc_max * self.battery_capacity_kwh, soc_kwh),
        )
        self.soc = soc_kwh / self.battery_capacity_kwh

        # Update cycle count (throughput-based)
        total_throughput = self._charge_energy_kwh + self._discharge_energy_kwh
        self._cycle_count = total_throughput / (2 * self.battery_capacity_kwh)

        return result

    def to_dict(self) -> dict[str, Any]:
        base = super().to_dict()
        base.update({
            "battery_capacity_kwh": self.battery_capacity_kwh,
            "soc": round(self.soc, 4),
            "soc_min": self.soc_min,
            "soc_max": self.soc_max,
            "cycle_count": round(self._cycle_count, 2),
            "charge_energy_kwh": round(self._charge_energy_kwh, 2),
            "discharge_energy_kwh": round(self._discharge_energy_kwh, 2),
        })
        return base
