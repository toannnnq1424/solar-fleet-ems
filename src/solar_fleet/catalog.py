from __future__ import annotations

import json
from importlib.resources import files

from .domain import Capability, Device


def data(name: str):
    return json.loads(files("solar_fleet").joinpath("data", name).read_text(encoding="utf-8"))


CONTRACTS = {row["path"]: row for row in data("deye-contract.json")}
INTENTS = data("intents.json")


def capabilities(device: Device) -> list[Capability]:
    # No commissioned hardware profile has been supplied. Adding one requires reviewed code + acceptance record.
    # Neither an environment variable nor the existence of a vendor endpoint can promote UNKNOWN to VERIFIED.
    return [
        Capability(
            intent=intent,
            identity=device.identity,
            semantic_match="requires_manual_configuration",
            transport="deye_cloud" if device.identity.vendor == "Deye" else "UNKNOWN",
            evidence_ids=["DEYE_API_001"] if device.identity.vendor == "Deye" else [],
            evidence_grade="A" if device.identity.vendor == "Deye" else "F",
            reason="Chưa xác minh model, logger, firmware, quyền, giới hạn và readback trên thiết bị thực.",
        )
        for intent in INTENTS
    ]


def native_catalog() -> list[dict]:
    return [
        row
        | {
            "enabled": False,
            "reason": (
                "Endpoint mô tả transport; chưa có profile phần cứng và hợp đồng readback đã nghiệm thu."
                if row["mode"] == "CONTROL"
                else "Gọi đọc qua adapter có xác thực; catalog không gửi request trực tiếp."
            ),
        }
        for row in CONTRACTS.values()
    ]
