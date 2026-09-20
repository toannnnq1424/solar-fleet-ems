from __future__ import annotations

import json
from importlib.resources import files

from .domain import Capability, Device
from .providers import provider


def data(name: str):
    return json.loads(files("solar_fleet").joinpath("data", name).read_text(encoding="utf-8"))


INTENTS = data("intents.json")


def capabilities(device: Device) -> list[Capability]:
    # No commissioned hardware profile has been supplied. Adding one requires reviewed code + acceptance record.
    # Neither an environment variable nor the existence of a vendor endpoint can promote UNKNOWN to VERIFIED.
    spec = provider(device.identity.vendor)
    return [
        Capability(
            intent=intent,
            identity=device.identity,
            semantic_match="requires_manual_configuration",
            transport=device.identity.vendor.lower() + "_cloud"
            if spec and spec["implemented"]
            else "UNKNOWN",
            evidence_ids=spec["evidence"] if spec else [],
            evidence_grade="A" if spec and spec["implemented"] else "F",
            reason="Chưa xác minh model, logger, firmware, quyền, giới hạn và readback trên thiết bị thực.",
        )
        for intent in INTENTS
    ]


def native_catalog() -> list[dict]:
    from .adapters.plugins import research_catalog

    return research_catalog()
