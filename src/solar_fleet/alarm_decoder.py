"""Unmapped native events. Reviewed per-model decoding lives in incident profiles."""

from dataclasses import dataclass


@dataclass(frozen=True)
class DecodedAlarm:
    """A vendor alarm translated into unified format."""

    vendor: str
    fault_code: str | int
    name_en: str
    severity: str  # CRITICAL, MAJOR, WARNING, INFO
    description_vi: str
    description_en: str
    category: str  # grid, pv, battery, inverter, communication, system
    sop_reference: str | None = None


def decode_alarm(vendor: str, fault_code: int | str) -> list[DecodedAlarm]:
    return [
        DecodedAlarm(
            vendor=vendor,
            fault_code=fault_code,
            name_en="Unmapped vendor event",
            severity="UNKNOWN",
            description_vi="Chưa có bảng mã theo model/firmware đã xác thực.",
            description_en="Exact model/firmware alarm mapping has not been verified.",
            category="unknown",
        )
    ]


def supported_vendors() -> list[str]:
    return []


def alarm_summary() -> dict[str, int]:
    return {}
