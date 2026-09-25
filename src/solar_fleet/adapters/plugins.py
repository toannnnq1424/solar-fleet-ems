"""Built-in integration composition. Vendor names and transport dialects belong here."""

import hashlib

from ..domain import SafetyError
from ..integration import (
    DeviceObservation,
    IntegrationPlugin,
    IntegrationRegistry,
    MeasurementObservation,
    PlantObservation,
)
from ..providers import provider
from .dessmonitor import Dessmonitor
from .deye import CONTRACTS, Deye, source_time
from .deye_control import compile_deye
from .goodwe import GoodWe
from .growatt import Growatt
from .huawei import Huawei
from .solarman import Solarman
from .solis import Solis
from .sungrow import Sungrow


def plant(raw):
    id = raw.get("id")
    if type(id) not in (str, int) or not str(id).strip():
        raise SafetyError("station_identity_invalid")
    return PlantObservation(id, str(raw.get("name") or id), raw.get("regionTimezone"))


def device_decoder(online_states):
    def decode(raw):
        serial = raw.get("deviceSn")
        if not isinstance(serial, str) or not serial.strip():
            raise SafetyError("device_identity_invalid")
        return DeviceObservation(
            serial,
            str(raw.get("deviceType") or "UNKNOWN"),
            raw.get("model"),
            type(raw.get("connectStatus")) is int and raw["connectStatus"] in online_states,
            source_time(raw.get("collectionTime")),
            raw.get("productId"),
        )

    return decode


def measurement_decoder(online_states):
    def decode(raw):
        points, serial = raw.get("dataList"), raw.get("deviceSn")
        if not isinstance(serial, str) or not serial:
            raise SafetyError("device_identity_invalid")
        if not isinstance(points, list) or any(not isinstance(p, dict) for p in points):
            raise SafetyError("vendor_invalid_measurements")
        return MeasurementObservation(
            serial,
            type(raw.get("deviceState")) is int and raw["deviceState"] in online_states,
            source_time(raw.get("collectionTime")),
            points,
        )

    return decode


GROUPS = (
    ("basic", "Cơ bản", "Basic", ("SET_WORK_MODE",)),
    (
        "battery",
        "Pin / BMS",
        "Battery / BMS",
        ("SET_RESERVE_SOC", "SET_MAX_CHARGE_CURRENT", "SET_MAX_DISCHARGE_CURRENT"),
    ),
    ("tou", "Lịch / TOU", "Schedule / TOU", ("SET_TOU", "ENABLE_TOU", "DISABLE_TOU")),
    ("meter", "Meter / CT", "Meter / CT", ()),
    ("export", "Phát lưới", "Export", ("SET_ZERO_EXPORT", "SET_EXPORT_LIMIT")),
    ("generator", "Máy phát", "Generator", ()),
    ("grid", "Lưới điện", "Grid", ("ENABLE_GRID_CHARGE", "DISABLE_GRID_CHARGE")),
    ("advanced", "Nâng cao", "Advanced", ()),
    ("native", "Theo hãng / OEM", "Vendor / OEM native", ()),
)


def research_catalog():
    return [
        dict(
            row,
            enabled=False,
            reason=(
                "Endpoint chưa có profile phần cứng và readback đã nghiệm thu."
                if row["mode"] == "CONTROL"
                else "Đọc qua adapter có xác thực."
            ),
        )
        for row in CONTRACTS.values()
    ]


def credential_contract(spec, *, organization=False, brands=()):
    def prepare(values, options):
        if options["region"] not in spec["regions"]:
            raise SafetyError("unsupported_data_center")
        if set(values) != set(spec["fields"]) or any(not v or len(v) > 4096 for v in values.values()):
            raise SafetyError("credentials_incomplete")
        if options.get("org_id") is not None and not organization:
            raise SafetyError("organization_not_supported_for_connector")
        if options.get("equipment_brand") and options["equipment_brand"] not in brands:
            raise SafetyError("equipment_brand_transport_mismatch")
        credentials = dict(values)
        if spec["identity"]:
            credentials["password_sha256"] = hashlib.sha256(credentials.pop("password").encode()).hexdigest()
            credentials["identity_field"] = options["identity_field"]
        if organization:
            credentials["org_id"] = options.get("org_id")
        return credentials

    return prepare


# Advertised features must match the shared controller contract.
_VENDOR_CONFIG = (
    {
        "id": "Eybond / SmartESS",
        "factory": Dessmonitor,
        "states": (),
        "auth": "SIGNED_SESSION",
        "features": {"discovery", "latest"},
        "namespace": "eybond",
        "brands": ("Bluesun",),
        "compile_intent": None,
    },
    {
        "id": "Deye",
        "factory": Deye,
        "states": (1,),
        "auth": "TOKEN",
        "features": {"discovery", "latest", "history", "configuration", "alarms"},
        "compile_intent": compile_deye,
    },
    {
        "id": "Solis",
        "factory": Solis,
        "states": (1,),
        "auth": "API_KEY",
        "features": {"discovery", "latest"},
        "compile_intent": None,
    },
    {
        "id": "SOLARMAN",
        "factory": Solarman,
        "states": (1, 2),
        "auth": "TOKEN",
        "features": {"discovery", "latest"},
        "compile_intent": None,  # Transport-only; OEM identification required
    },
    {
        "id": "GoodWe",
        "factory": GoodWe,
        "states": (1,),
        "auth": "TOKEN",
        "features": {"discovery", "latest"},
        "compile_intent": None,
    },
    {
        "id": "Sungrow",
        "factory": Sungrow,
        "states": (1,),
        "auth": "TOKEN",
        "features": {"discovery", "latest"},
        "compile_intent": None,
    },
    {
        "id": "Huawei",
        "factory": Huawei,
        "states": (1,),
        "auth": "TOKEN",
        "features": {"discovery", "latest"},
        "compile_intent": None,  # No accepted cloud or local write mapping is packaged.
    },
    {
        "id": "Growatt",
        "factory": Growatt,
        "states": (1,),
        "auth": "TOKEN",
        "features": {"discovery", "latest"},
        "compile_intent": None,
    },
)


def builtins() -> IntegrationRegistry:
    registry = IntegrationRegistry()
    for cfg in _VENDOR_CONFIG:
        id = cfg["id"]
        factory = cfg["factory"]
        spec = provider(id)
        groups = tuple(
            {
                "id": key,
                "label": {"vi": vi, "en": en},
                "intents": list(intents),
                "state": "UNKNOWN",
                "native_fields": [],
                "reason": "model_firmware_protocol_acceptance_required",
            }
            for key, vi, en, intents in GROUPS
        )
        plugin_kwargs = {}
        if cfg.get("compile_intent") is not None:
            plugin_kwargs["compile_intent"] = cfg["compile_intent"]
        registry.register(
            IntegrationPlugin(
                id=id,
                version=factory.version,
                factory=factory,
                plant=plant,
                device=device_decoder(cfg["states"]),
                measurement=measurement_decoder(cfg["states"]),
                namespace=cfg.get("namespace", id.lower()),
                evidence_ids=tuple(spec["evidence"]),
                authentication=cfg["auth"],
                features=frozenset(cfg["features"]),
                native_groups=groups,
                registration=dict(
                    spec,
                    organization=id == "SOLARMAN",
                    equipment_brands=list(cfg.get("brands", ("Bluesun",) if id == "SOLARMAN" else ())),
                ),
                prepare_credentials=credential_contract(
                    spec,
                    organization=id == "SOLARMAN",
                    brands=cfg.get("brands", ("Bluesun",) if id == "SOLARMAN" else ()),
                ),
                documentation=({"title": id + " developer documentation", "url": spec["url"]},),
                **plugin_kwargs,
            )
        )
    return registry
