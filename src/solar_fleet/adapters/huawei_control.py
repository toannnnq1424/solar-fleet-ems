"""Stub control mappings for Huawei FusionSolar.

Huawei FusionSolar Northbound API is primarily READ-ONLY for monitoring.
Control operations (battery modes, TOU schedules, power curtailment)
require either:
1. FusionSolar App / Portal (manual operation)
2. Local Modbus TCP connection to SUN2000 inverter / SmartLogger

This file provides candidate intent mappings for documentation purposes.
All intents are permanently locked with LOCKED_PENDING_HARDWARE_ACCEPTANCE
and additionally flagged as requiring local Modbus TCP transport.

Source references:
- HUAWEI_NB_001: Northbound API does not expose public write endpoints
- HUAWEI_MODBUS_001: SUN2000 Modbus TCP register map (requires local network access)
Evidence grade: C — Northbound read-only; control is Modbus TCP local only.
"""

from __future__ import annotations

from ..domain import Device, SafetyError, VendorCall


def compile_huawei(device: Device, intent: str, parameters: dict) -> tuple[list[VendorCall], dict]:
    """Huawei control intents are NOT available via Northbound cloud API.

    This compiler exists to document the intent→register mapping for future
    local Modbus TCP transport implementation. All calls will be rejected
    by the capability gate because no cloud write endpoint exists.
    """
    # Huawei Northbound API does not expose write endpoints.
    # Control requires local Modbus TCP to SUN2000/SmartLogger.
    raise SafetyError(
        "huawei_northbound_read_only: "
        "FusionSolar Northbound API does not expose public write endpoints. "
        "Control requires local Modbus TCP connection to SUN2000 inverter "
        "or SmartLogger. Intent: " + intent
    )
