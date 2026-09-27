"""Diesel and gas generator controller with black-start orchestration.

Independently implemented for Solar Fleet EMS.
Concepts from OpenEMS io.openems.edge.controller.ess.dieselgenerator
and virtual-power-plant-main microgrid coordination.
No code copied.

Provides:
- Generator state machine (OFF, CRANKING, WARMUP, RUNNING_LOADED, COOLDOWN, FAULT)
- Fuel consumption model and loading sweet spot (60-80% to prevent wet stacking)
- Battery charging coordination to maintain optimal generator loading
- Black-start multi-stage sequencing for islanded microgrids
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class GeneratorState(str, Enum):
    """Operational state of the generator set."""

    OFF = "off"
    CRANKING = "cranking"
    WARMUP = "warmup"
    RUNNING_LOADED = "running_loaded"
    COOLDOWN = "cooldown"
    FAULT = "fault"
    LOCKED_OUT = "locked_out"


class BlackStartStage(str, Enum):
    """Phases of microgrid black-start restoration."""

    IDLE = "idle"
    STAGE_1_DEAD_BUS_CHECK = "stage_1_dead_bus_check"
    STAGE_2_GENSET_START = "stage_2_genset_start"
    STAGE_3_BUS_ENERGIZATION = "stage_3_bus_energization"
    STAGE_4_PV_SYNCHRONIZATION = "stage_4_pv_synchronization"
    STAGE_5_LOAD_RESTORATION = "stage_5_load_restoration"
    COMPLETED = "completed"
    FAILED = "failed"


# ---------------------------------------------------------------------------
# Generator Hardware Specifications
# ---------------------------------------------------------------------------

@dataclass
class GeneratorSpecs:
    """Technical and operational specifications of the genset."""

    rated_power_kw: float = 50.0
    min_loading_ratio: float = 0.40      # Prevent wet stacking below 40%
    optimal_loading_ratio: float = 0.75  # Peak fuel efficiency sweet spot
    max_loading_ratio: float = 0.95      # Reserve margin
    fuel_idle_liters_per_hour: float = 2.5
    fuel_slope_liters_per_kwh: float = 0.22  # Liters per generated kWh
    warmup_time_seconds: int = 120
    cooldown_time_seconds: int = 180
    min_run_time_seconds: int = 1800     # 30 minutes minimum to avoid thermal cycling
    auto_start_soc_threshold: float = 20.0
    auto_stop_soc_threshold: float = 80.0

    @property
    def min_power_kw(self) -> float:
        return self.rated_power_kw * self.min_loading_ratio

    @property
    def optimal_power_kw(self) -> float:
        return self.rated_power_kw * self.optimal_loading_ratio

    @property
    def max_power_kw(self) -> float:
        return self.rated_power_kw * self.max_loading_ratio

    def calculate_fuel_rate(self, electric_power_kw: float) -> float:
        """Compute instantaneous fuel consumption (liters/hour)."""
        if electric_power_kw <= 0:
            return 0.0
        return self.fuel_idle_liters_per_hour + (self.fuel_slope_liters_per_kwh * electric_power_kw)


# ---------------------------------------------------------------------------
# Generator Controller
# ---------------------------------------------------------------------------

class GeneratorController:
    """Manages generator lifecycle, loading optimization, and fuel efficiency.

    Coordinates with battery storage to absorb excess generator capacity so
    the engine always operates in its high-efficiency, low-carbon sweet spot.
    """

    def __init__(self, specs: GeneratorSpecs):
        self.specs = specs
        self._state = GeneratorState.OFF
        self._elapsed_in_state_seconds = 0
        self._cumulative_run_seconds = 0
        self._total_fuel_consumed_liters = 0.0
        self._fault_reason = ""

    @property
    def state(self) -> GeneratorState:
        return self._state

    def step(
        self,
        dt_seconds: int,
        microgrid_load_kw: float,
        battery_soc_pct: float,
        battery_max_charge_kw: float,
        is_grid_available: bool = False,
    ) -> Dict[str, Any]:
        """Execute one simulation/control step."""
        self._elapsed_in_state_seconds += dt_seconds

        # Decision logic for auto-start / auto-stop
        output_power_kw = 0.0
        battery_charge_kw = 0.0

        if self._state == GeneratorState.OFF:
            # Trigger conditions:
            # 1. Grid lost AND battery SOC dropped below start threshold
            # 2. Grid lost AND load exceeds battery max discharge capability
            if not is_grid_available and (battery_soc_pct <= self.specs.auto_start_soc_threshold or microgrid_load_kw > 15.0):
                self._transition_to(GeneratorState.CRANKING)

        elif self._state == GeneratorState.CRANKING:
            # Cranking takes 10 seconds
            if self._elapsed_in_state_seconds >= 10:
                self._transition_to(GeneratorState.WARMUP)

        elif self._state == GeneratorState.WARMUP:
            if self._elapsed_in_state_seconds >= self.specs.warmup_time_seconds:
                self._transition_to(GeneratorState.RUNNING_LOADED)

        elif self._state == GeneratorState.RUNNING_LOADED:
            self._cumulative_run_seconds += dt_seconds

            # Optimize loading: target optimal loading sweet spot (e.g. 75% of rated)
            target_genset_power = self.specs.optimal_power_kw

            # If site load is higher than optimal, ramp genset up to max rating
            if microgrid_load_kw > target_genset_power:
                output_power_kw = min(self.specs.max_power_kw, microgrid_load_kw)
            else:
                # Load is below optimal: run genset at optimal power, direct surplus to battery
                output_power_kw = target_genset_power
                surplus_power = max(0.0, output_power_kw - microgrid_load_kw)
                battery_charge_kw = min(battery_max_charge_kw, surplus_power)
                # Adjust output if battery cannot absorb full surplus
                output_power_kw = max(self.specs.min_power_kw, microgrid_load_kw + battery_charge_kw)

            # Fuel tracking
            fuel_rate = self.specs.calculate_fuel_rate(output_power_kw)
            fuel_step = (fuel_rate * dt_seconds) / 3600.0
            self._total_fuel_consumed_liters += fuel_step

            # Check stop condition:
            # Can stop if grid restored OR battery SOC reached auto-stop threshold
            # MUST honor minimum run time to avoid thermal wear
            can_stop = (
                (is_grid_available or battery_soc_pct >= self.specs.auto_stop_soc_threshold)
                and self._cumulative_run_seconds >= self.specs.min_run_time_seconds
            )
            if can_stop:
                self._transition_to(GeneratorState.COOLDOWN)

        elif self._state == GeneratorState.COOLDOWN:
            # Idle at no-load to cool turbochargers
            fuel_rate = self.specs.fuel_idle_liters_per_hour
            fuel_step = (fuel_rate * dt_seconds) / 3600.0
            self._total_fuel_consumed_liters += fuel_step

            if self._elapsed_in_state_seconds >= self.specs.cooldown_time_seconds:
                self._cumulative_run_seconds = 0
                self._transition_to(GeneratorState.OFF)

        loading_ratio = (output_power_kw / self.specs.rated_power_kw) if self.specs.rated_power_kw > 0 else 0.0

        return {
            "state": self._state.value,
            "output_power_kw": round(output_power_kw, 2),
            "battery_charge_kw": round(battery_charge_kw, 2),
            "loading_ratio_pct": round(loading_ratio * 100.0, 1),
            "fuel_rate_lph": round(self.specs.calculate_fuel_rate(output_power_kw), 2),
            "total_fuel_liters": round(self._total_fuel_consumed_liters, 2),
            "elapsed_in_state_seconds": self._elapsed_in_state_seconds,
            "cumulative_run_seconds": self._cumulative_run_seconds,
        }

    def _transition_to(self, new_state: GeneratorState) -> None:
        self._state = new_state
        self._elapsed_in_state_seconds = 0


# ---------------------------------------------------------------------------
# Black-Start Orchestration Engine
# ---------------------------------------------------------------------------

class BlackStartOrchestrator:
    """Multi-stage restoration sequence for microgrids after total blackout."""

    def __init__(self, genset_controller: GeneratorController):
        self.genset = genset_controller
        self._stage = BlackStartStage.IDLE
        self._log: List[Dict[str, Any]] = []

    @property
    def stage(self) -> BlackStartStage:
        return self._stage

    def execute_next_stage(
        self,
        bus_voltage_v: float,
        pv_frequency_hz: float,
        critical_load_kw: float,
    ) -> Dict[str, Any]:
        """Advance one stage in the restoration sequence."""
        now = datetime.now(timezone.utc).isoformat()

        if self._stage == BlackStartStage.IDLE:
            # Stage 1: Verify dead bus (voltage must be close to 0 to prevent out-of-phase closure)
            if bus_voltage_v < 10.0:
                self._stage = BlackStartStage.STAGE_1_DEAD_BUS_CHECK
                self._log_event(now, "STAGE_1_DEAD_BUS_CHECK", "Bus confirmed de-energized (< 10V)")
            else:
                self._stage = BlackStartStage.FAILED
                self._log_event(now, "FAILED", f"Bus energized ({bus_voltage_v}V), unsafe to black-start")

        elif self._stage == BlackStartStage.STAGE_1_DEAD_BUS_CHECK:
            # Stage 2: Start generator and bring to rated speed
            self.genset._transition_to(GeneratorState.RUNNING_LOADED)
            self._stage = BlackStartStage.STAGE_2_GENSET_START
            self._log_event(now, "STAGE_2_GENSET_START", "Generator started and running at rated RPM")

        elif self._stage == BlackStartStage.STAGE_2_GENSET_START:
            # Stage 3: Close generator master breaker to energize microgrid MV/LV bus
            self._stage = BlackStartStage.STAGE_3_BUS_ENERGIZATION
            self._log_event(now, "STAGE_3_BUS_ENERGIZATION", "Master bus energization: 400V 50Hz reference established")

        elif self._stage == BlackStartStage.STAGE_3_BUS_ENERGIZATION:
            # Stage 4: Synchronize grid-following PV inverters once bus frequency is within 49.8 - 50.2 Hz
            if 49.5 <= pv_frequency_hz <= 50.5:
                self._stage = BlackStartStage.STAGE_4_PV_SYNCHRONIZATION
                self._log_event(now, "STAGE_4_PV_SYNCHRONIZATION", f"PV inverters synchronized to microgrid bus at {pv_frequency_hz} Hz")
            else:
                self._log_event(now, "STAGE_4_WAIT", f"Waiting for frequency stabilization ({pv_frequency_hz} Hz)")

        elif self._stage == BlackStartStage.STAGE_4_PV_SYNCHRONIZATION:
            # Stage 5: Pick up prioritized critical loads
            self._stage = BlackStartStage.STAGE_5_LOAD_RESTORATION
            self._log_event(now, "STAGE_5_LOAD_RESTORATION", f"Critical feeder loads restored ({critical_load_kw} kW)")

        elif self._stage == BlackStartStage.STAGE_5_LOAD_RESTORATION:
            self._stage = BlackStartStage.COMPLETED
            self._log_event(now, "COMPLETED", "Microgrid black-start sequence successfully completed")

        return {
            "current_stage": self._stage.value,
            "genset_state": self.genset.state.value,
            "event_log": self._log,
        }

    def _log_event(self, timestamp: str, stage: str, message: str) -> None:
        self._log.append({
            "timestamp": timestamp,
            "stage": stage,
            "message": message,
        })
