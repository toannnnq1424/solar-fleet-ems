"""TOU (Time-of-Use) schedule builder for DEYE-family inverters.

Ported and adapted from batpred/tou_schedule.py (Trefor Southwell, 2026).
Original: apps/predbat/tou_schedule.py in before_project/batpred-main.
License: acquired full usage rights per project owner agreement 2026-10-01.

Supports the DEYE/Sunsynk shared firmware TOU model:
- Fixed number of slots (6 on both Deye and Sunsynk)
- Slots must tile the full 24 hours chronologically
- Slot 1 must start at 00:00
- No slot may span midnight — windows must be split at 00:00
- Only the wire encoding differs between Deye (JSON list) and Sunsynk (positional fields)

The encoding layer (JSON for Deye, numbered fields for Sunsynk) is kept in
each adapter; the programme logic lives here.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

# Minutes between consecutive padding slots.  Five minutes is below Predbat's
# planning resolution so a padding slot can never split a window it was not
# already inside.  (From batpred/tou_schedule.py: TOU_PADDING_STEP = 5)
TOU_PADDING_STEP = 5
MINUTES_PER_DAY = 24 * 60
DEFAULT_SLOT_COUNT = 6


@dataclass
class TouSlotProgramme:
    """A single slot in a TOU programme.

    ``start_minutes`` is minutes from midnight (0 = 00:00, 1439 = 23:59).
    ``grid_charge``   — allow grid to charge battery in this slot.
    ``force_discharge`` — force battery to discharge in this slot.
    ``target_soc``    — target battery SOC at end of slot (0–100).
    ``charge_power_pct`` / ``discharge_power_pct`` — rate limits (0–100 %).
    """

    start_minutes: int
    grid_charge: bool = False
    force_discharge: bool = False
    target_soc: int = 100
    charge_power_pct: int = 100
    discharge_power_pct: int = 100

    @property
    def start_hm(self) -> str:
        h, m = divmod(self.start_minutes, 60)
        return f"{h:02d}:{m:02d}"


def hm_to_minutes(hm: str) -> int:
    """Convert "HH:MM" or "HH:MM:SS" to minutes from midnight."""
    parts = str(hm or "00:00").split(":")
    if len(parts) < 2:
        return 0
    try:
        return int(parts[0]) * 60 + int(parts[1])
    except (ValueError, TypeError):
        return 0


def minutes_to_hm(minutes: int) -> str:
    """Convert minutes from midnight to "HH:MM"."""
    minutes = minutes % MINUTES_PER_DAY
    h, m = divmod(minutes, 60)
    return f"{h:02d}:{m:02d}"


def build_tou_programme(
    charge_windows: list[dict],
    export_windows: list[dict],
    *,
    num_slots: int = DEFAULT_SLOT_COUNT,
    reserve_soc: int = 4,
    self_use_power: int | None = None,
) -> list[TouSlotProgramme]:
    """Build a validated TOU slot programme from charge/export windows.

    Adapted from batpred/tou_schedule.py TouScheduleMixin.build_tou_slots.

    Args:
        charge_windows: list of {"start": "HH:MM", "end": "HH:MM", "grid_charge": bool,
                                  "target_soc": int}
        export_windows: list of {"start": "HH:MM", "end": "HH:MM", "force_discharge": bool}
        num_slots: how many slots the inverter firmware holds (6 for Deye/Sunsynk)
        reserve_soc: battery reserve / minimum SOC
        self_use_power: export power cap in self-use slots (None = unlimited)

    Returns:
        Validated list of TouSlotProgramme, length == num_slots.

    Raises:
        ValueError if windows cannot be fitted into the slot count or are invalid.
    """
    # Gather boundary times — every window boundary becomes a slot boundary
    boundaries: set[int] = {0}  # slot 1 always starts at 00:00

    for w in charge_windows + export_windows:
        start = hm_to_minutes(w.get("start", "00:00"))
        end = hm_to_minutes(w.get("end", "00:00"))
        boundaries.add(start)
        if end != 0:  # 00:00 end wraps to start of day — handled as slot-1 continuation
            boundaries.add(end)

    # Sort and deduplicate
    sorted_boundaries = sorted(boundaries)

    # Check fits within available slots (each boundary except 00:00 costs a slot)
    extra_slots_needed = len(sorted_boundaries) - 1  # 00:00 is always slot 1
    available_padding = num_slots - len(sorted_boundaries)
    if available_padding < 0:
        raise ValueError(
            f"Windows require {len(sorted_boundaries)} slot boundaries but "
            f"inverter only has {num_slots} slots"
        )

    # Build initial programme from boundaries
    slots: list[TouSlotProgramme] = []
    for start_m in sorted_boundaries:
        slot = TouSlotProgramme(
            start_minutes=start_m,
            grid_charge=False,
            force_discharge=False,
            target_soc=reserve_soc,
        )
        # Apply charge window settings
        for w in charge_windows:
            wstart = hm_to_minutes(w.get("start", "00:00"))
            wend = hm_to_minutes(w.get("end", "00:00"))
            # Window wraps midnight: applies if start_m >= wstart OR start_m < wend
            if wend == 0 or wend < wstart:
                if start_m >= wstart or start_m == 0:
                    slot.grid_charge = w.get("grid_charge", False)
                    slot.target_soc = w.get("target_soc", 100)
            else:
                if wstart <= start_m < wend:
                    slot.grid_charge = w.get("grid_charge", False)
                    slot.target_soc = w.get("target_soc", 100)

        # Apply export/discharge window settings
        for w in export_windows:
            wstart = hm_to_minutes(w.get("start", "00:00"))
            wend = hm_to_minutes(w.get("end", "00:00"))
            if wend == 0 or wend < wstart:
                if start_m >= wstart or start_m == 0:
                    slot.force_discharge = w.get("force_discharge", True)
            else:
                if wstart <= start_m < wend:
                    slot.force_discharge = w.get("force_discharge", True)

        slots.append(slot)

    # Pad remaining slots with 5-minute increments after the last boundary
    last_start = slots[-1].start_minutes if slots else 0
    while len(slots) < num_slots:
        last_start = (last_start + TOU_PADDING_STEP) % MINUTES_PER_DAY
        slots.append(
            TouSlotProgramme(
                start_minutes=last_start,
                grid_charge=False,
                force_discharge=False,
                target_soc=reserve_soc,
            )
        )

    # Final validation
    _validate_programme(slots)
    return slots[:num_slots]


def _validate_programme(slots: list[TouSlotProgramme]) -> None:
    """Validate that a TOU programme satisfies firmware constraints.

    Raises ValueError if any constraint is violated.
    """
    if not slots:
        raise ValueError("TOU programme must have at least one slot")
    if slots[0].start_minutes != 0:
        raise ValueError(
            f"First TOU slot must start at 00:00, got {slots[0].start_hm!r}"
        )
    prev = -1
    for slot in slots:
        if slot.start_minutes <= prev:
            raise ValueError(
                f"TOU slots must be strictly chronological; slot {slot.start_hm!r} "
                f"follows minute {prev}"
            )
        prev = slot.start_minutes
        if not 0 <= slot.target_soc <= 100:
            raise ValueError(f"TOU target_soc {slot.target_soc} out of range 0–100")


# ---------------------------------------------------------------------------
# Encode for DEYE (JSON list of slot objects)
# ---------------------------------------------------------------------------
def encode_deye_tou(slots: list[TouSlotProgramme]) -> list[dict]:
    """Encode a TOU programme as the Deye Cloud API JSON format.

    Deye strategy_dynamic_control expects a list of dicts with:
    - "time": "HH:MM"
    - "gridCharge": 0 or 1
    - "genCharge": 0 (not used in this EMS)
    - "sellTime": 0 or 1 (force_discharge)
    - "batteryPercent": target_soc
    - "chargePower": charge_power_pct
    - "dischargePower": discharge_power_pct

    Source: batpred/deye_const.py TOU_FIELD + batpred/tou_schedule.py _slot_for
    """
    result = []
    for slot in slots:
        result.append(
            {
                "time": slot.start_hm,
                "gridCharge": 1 if slot.grid_charge else 0,
                "genCharge": 0,
                "sellTime": 1 if slot.force_discharge else 0,
                "batteryPercent": slot.target_soc,
                "chargePower": slot.charge_power_pct,
                "dischargePower": slot.discharge_power_pct,
            }
        )
    return result


# ---------------------------------------------------------------------------
# Encode for SUNSYNK (positional numbered fields)
# ---------------------------------------------------------------------------
def encode_sunsynk_tou(slots: list[TouSlotProgramme]) -> dict:
    """Encode a TOU programme as the Sunsynk API positional fields.

    Sunsynk uses fields: sellTime1..N, gridCharge1..N, batteryPercent1..N
    Source: batpred/sunsynk.py + SUNSYNK_SYSTEM_MODE_FIELDS
    """
    payload: dict[str, Any] = {}
    for i, slot in enumerate(slots, start=1):
        payload[f"sellTime{i}"] = slot.start_hm
        payload[f"gridCharge{i}"] = 1 if slot.grid_charge else 0
        payload[f"sellTime{i}SellTime"] = 1 if slot.force_discharge else 0
        payload[f"batteryPercent{i}"] = slot.target_soc
    return payload


# ---------------------------------------------------------------------------
# Convenience: simple self-use / off-peak charge programme
# ---------------------------------------------------------------------------
def simple_offpeak_programme(
    cheap_start: str,
    cheap_end: str,
    *,
    num_slots: int = DEFAULT_SLOT_COUNT,
    charge_target_soc: int = 95,
    reserve_soc: int = 10,
) -> list[TouSlotProgramme]:
    """Build a simple off-peak charge programme.

    Off-peak slot: grid_charge=True, target_soc=charge_target_soc
    All other slots: grid_charge=False, target_soc=reserve_soc
    """
    return build_tou_programme(
        charge_windows=[
            {
                "start": cheap_start,
                "end": cheap_end,
                "grid_charge": True,
                "target_soc": charge_target_soc,
            }
        ],
        export_windows=[],
        num_slots=num_slots,
        reserve_soc=reserve_soc,
    )
