"""Candidate mappings isolated inside the integration; capability gates remain in core."""

import re

from ..domain import Device, SafetyError, VendorCall


def compile_deye(device: Device, intent: str, parameters: dict) -> tuple[list[VendorCall], dict]:
    """Candidate exact mappings from DEYE_API_001; never callable without a commissioned capability profile."""
    prefix = "/v1.0/order/"
    body = {"deviceSn": device.vendor_id}
    value = parameters.get("value")
    if intent == "SET_WORK_MODE":
        path = "sys/workMode/update"
        body["workMode"] = value
        expected = {"systemWorkMode": value}
    elif intent in ("SET_MAX_CHARGE_CURRENT", "SET_MAX_DISCHARGE_CURRENT"):
        path = "battery/parameter/update"
        body.update(
            paramterType="MAX_CHARGE_CURRENT"
            if intent == "SET_MAX_CHARGE_CURRENT"
            else "MAX_DISCHARGE_CURRENT",
            value=value,
        )
        expected = {
            "maxChargeCurrent" if intent == "SET_MAX_CHARGE_CURRENT" else "maxDischargeCurrent": value
        }
    elif intent in ("ENABLE_GRID_CHARGE", "DISABLE_GRID_CHARGE"):
        path = "battery/modeControl"
        body.update(action="on" if intent == "ENABLE_GRID_CHARGE" else "off", batteryModeType="GRID_CHARGE")
        expected = {"gridChargeAction": body["action"]}
    elif intent == "SET_EXPORT_LIMIT":
        path = "sys/power/update"
        body.update(powerType="MAX_SELL_POWER", value=value)
        expected = {"maxSellPower": value}
    elif intent == "SET_TOU":
        path = "sys/tou/update"
        slots = parameters.get("slots")
        if not isinstance(slots, list) or len(slots) != 6:
            raise SafetyError("tou_requires_six_verified_slots")
        times = [slot.get("time", "") for slot in slots]
        if any(not re.fullmatch(r"(?:[01][0-9]|2[0-3]):[0-5][0-9]", t) for t in times):
            raise SafetyError("tou_time_invalid")
        if times != sorted(set(times)):
            raise SafetyError("tou_times_must_be_unique_and_ordered")
        body["timeUseSettingItems"] = slots
        expected = {"timeUseSettingItems": slots}
    elif intent in ("ENABLE_TOU", "DISABLE_TOU"):
        path = "sys/tou/switch"
        body.update(action="on" if intent == "ENABLE_TOU" else "off")
        if body["action"] == "on":
            body["days"] = parameters["days"]
            # Days have no proven getter in config/tou; a future profile must add that readback field.
            expected = {"touAction": "on", "touDays": body["days"]}
        else:
            expected = {"touAction": "off"}
    else:
        raise SafetyError("intent_mapping_unknown")
    from .deye import Deye

    call = VendorCall(path=prefix + path, body=body)
    Deye.validate(call.path, call.body)
    return [call], expected
