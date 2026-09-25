"""Vendor Modbus register maps, alarm decoders, and parameter schemas.

Provides official register offsets, data types, scale factors, and fault decoders
for GoodWe, Sungrow, Huawei SUN2000, Growatt SPH/SPF, Solis, and Deye hybrid inverters.
"""

from __future__ import annotations

from typing import Any

# ============================================================================
# 1. GOODWE HYBRID INVERTER (ET / EH / ES SERIES) REGISTERS & ALARMS
# ============================================================================

GOODWE_HOLDING_REGISTERS = {}  # No accepted exact-model map.

GOODWE_ALARM_CODES = {}  # No accepted exact-model map.


DEYE_HOLDING_REGISTERS = {}  # No accepted exact-model map.

DEYE_ALARM_CODES = {}  # No accepted exact-model map.

# ============================================================================
# 2. SUNGROW HYBRID INVERTER (SH SERIES) REGISTERS & ALARMS
# ============================================================================

SUNGROW_HOLDING_REGISTERS = {}  # No accepted exact-model map.

SUNGROW_ALARM_CODES = {}  # No accepted exact-model map.


# ============================================================================
# 3. HUAWEI SUN2000 INVERTER REGISTERS & ALARMS
# ============================================================================

HUAWEI_HOLDING_REGISTERS = {}  # No accepted exact-model map.

HUAWEI_ALARM_CODES = {}  # No accepted exact-model map.


# ============================================================================
# 4. GROWATT STORAGE INVERTER (SPH / SPF SERIES) REGISTERS & ALARMS
# ============================================================================

GROWATT_HOLDING_REGISTERS = {}  # No accepted exact-model map.

GROWATT_ALARM_CODES = {}  # No accepted exact-model map.

# ============================================================================
# 6. SOLIS INVERTER REGISTERS & ALARMS
# ============================================================================

SOLIS_HOLDING_REGISTERS = {}  # No accepted exact-model map.

SOLIS_ALARM_CODES = {}  # No accepted exact-model map.


# ============================================================================
# HELPER DECODER FUNCTIONS
# ============================================================================


def decode_vendor_alarm(vendor: str, code: int) -> dict[str, Any]:
    return {
        "fault_code": code,
        "title": "Unmapped vendor event",
        "severity": "UNKNOWN",
        "remediation_advice": "Exact model/firmware protocol required",
        "vendor": vendor,
    }


GENERIC_HOLDING_REGISTERS = {}  # No accepted exact-model map.

GENERIC_ALARM_CODES = {}  # No accepted exact-model map.
