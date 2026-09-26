"""Offline, deterministic import of explicitly licensed legacy model definitions.

Usage: python scripts/import_model_library.py --root D:/Downloads/before_project
Requires the profile-import extra. Does not import/execute any upstream Python,
read secrets.yaml, load arbitrary YAML tags or contact hardware/cloud services.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
from pathlib import Path

import yaml

from solar_fleet.model_library import DecodeSpec, ModelProfile, profile_hash

DEST = Path(__file__).resolve().parents[1] / "src/solar_fleet/data"


def slug(value):
    return re.sub(r"[^a-z0-9]+", "_", str(value).lower()).strip("_")[:54] or "field"


def metadata(path, project, prefix, name, manufacturer, models, url, transport):
    locked = next(
        row
        for row in json.loads((DEST / "model-source-lock.json").read_text("utf-8"))
        if row["local_directory"] == project.name
    )
    relative = path.relative_to(project).as_posix()
    expected = next(row["sha256"] for row in locked["files"] if row["path"] == relative)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != expected or not locked["all_selected_files_match"]:
        raise ValueError(f"Source changed: review and update the provenance lock for {relative}")
    revision = locked["upstream_commit_checked"]
    return {
        "id": prefix + "-" + slug(path.stem).replace("_", "-"),
        "name": name,
        "manufacturer": manufacturer,
        "models": [str(m) for m in models],
        "source_id": prefix,
        "source_path": path.relative_to(project).as_posix(),
        "source_sha256": digest,
        "source_revision": revision,
        "source_url": url + "/blob/" + revision + "/" + relative,
        "license": "MIT",
        "transport_hint": transport,
        "unit_id_hint": None,
        "max_block_size": 60,
        "fields": [],
        "limitations": [
            "Community definition; not accepted against this installation's model/logger/firmware.",
            "Read-only native measurements. No commissioned controls or automatic canonical mapping.",
            "Conditional, derived and unsupported definitions remain visible with a blocking reason.",
        ],
    }


def add_field(profile, name, native, group, unit, spec=None, reason=None):
    base = slug(name)
    ids = {f["id"] for f in profile["fields"]}
    key = base
    index = 2
    while key in ids:
        key = f"{base}_{index}"
        index += 1
    if spec is not None:
        try:
            spec = DecodeSpec.model_validate(spec).model_dump(mode="json")
        except ValueError:
            spec, reason = None, "Invalid or unsupported numeric/register definition; review source."
    profile["fields"].append(
        {
            "id": key,
            "name": name,
            "unit": unit,
            "group": group,
            "decode": spec,
            "blocked_reason": reason,
            "native": native,
        }
    )


def ha_spec(item):
    rule = item.get("rule")
    # Conservatively gate stateful validation, dynamic topology and computations.
    for key in (
        "sensors",
        "lookup",
        "validation",
        "enabled_lookup",
        "name_lookup",
        "mppt",
        "pack",
        "disabled",
        "ensure_increasing",
        "bitmask",
        "uint",
        "l",
    ):
        if key in item:
            return None, f"Requires upstream {key} semantics or explicit device variant; not compiled."
    registers = item.get("registers")
    if not registers or not all(type(r) is int for r in registers):
        return None, "Missing, derived or variant-specific register addresses."
    if rule not in (1, 2, 3, 4, 5):
        return None, "Unsupported decoder rule; retained for research."
    code = item.get("code", 3)
    code = code.get("read") if isinstance(code, dict) else code
    if code not in (3, 4):
        return None, "No FC03/FC04 read operation."
    for key in ("scale", "offset", "divide"):
        if key in item and type(item[key]) not in (int, float):
            return None, f"Variant-specific {key}; select and review the exact variant."
    raw_range = item.get("range") or {}
    if set(raw_range) - {"min", "max"}:
        return None, "Range includes a synthetic fallback or unknown semantics."
    signed = rule in (2, 4)
    spec = {
        "function": code,
        "registers": registers,
        "word_order": "little",
        "encoding": "ascii"
        if rule == 5
        else "magnitude"
        if signed and item.get("magnitude")
        else "signed"
        if signed
        else "unsigned",
        "scale": item.get("scale", 1),
        "offset": -item.get("offset", 0),
        "floor_divisor": item.get("divide"),
        "negate": bool(signed and item.get("inverted")),
        "mask": item.get("mask") if not signed else None,
        "bit": item.get("bit") if not signed else None,
        "raw_min": raw_range.get("min"),
        "raw_max": raw_range.get("max"),
    }
    return spec, None


def import_solarman(root):
    project = root / "ha-solarman-main"
    result = []
    for path in sorted((project / "custom_components/solarman/inverter_definitions").glob("*.yaml")):
        data = yaml.safe_load(path.read_text("utf-8"))
        info = data.get("info") or {}
        models = info.get("model", path.stem)
        models = models if isinstance(models, list) else [models]
        profile = metadata(
            path,
            project,
            "ha-solarman-models",
            path.stem.replace("_", " "),
            str(info.get("manufacturer", "See source definition")),
            models,
            "https://github.com/davidrapan/ha-solarman",
            "SOLARMAN V5; verify logger support",
        )
        default = data.get("default") or {}
        max_size = default.get("max_size", 60)
        profile["max_block_size"] = max(1, min(125, max_size))
        for group in data.get("parameters", []):
            inherited = {k: v for k, v in group.items() if k != "items"}
            for item in group.get("items", []):
                merged = inherited | item
                if "code" not in merged:
                    code = default.get("code", 3)
                    regs = merged.get("registers")
                    if regs and all(type(r) is int for r in regs) and not data.get("requests_fine_control"):
                        for request in data.get("requests", []):
                            if request["start"] <= min(regs) <= request["end"]:
                                code = request.get("code", 3)
                    merged["code"] = code
                spec, reason = ha_spec(merged)
                if "requests_fine_control" in data:
                    spec, reason = None, "Requires exact upstream fine-control request sequence."
                add_field(
                    profile,
                    str(item.get("name", "Unnamed")),
                    merged,
                    str(group.get("group", "Measurements")),
                    merged.get("uom"),
                    spec,
                    reason,
                )
        result.append(profile)
    return result


def import_glance(root):
    project = root / "solar-inverter-modbus-registers-main"
    path = project / "supported_inverters.json"
    result = []
    for source in json.loads(path.read_text("utf-8"))["profiles"]:
        profile = metadata(
            path,
            project,
            "glance-modbus-models",
            source["modelName"],
            source["brandName"],
            [source["modelName"]],
            "https://github.com/szlaskidaniel/solar-inverter-modbus-registers",
            "Modbus TCP; verify model interface",
        )
        profile["id"] = f"glance-{source['brandId']}-{source['modelId']}"
        profile["unit_id_hint"] = source["unitId"]
        profile["max_block_size"] = source.get("polling", {}).get("maxBlockSize", 60)
        offset = source.get("addressOffset", 0)
        for name, native in source["fields"].items():
            if "presence" in native:
                add_field(
                    profile,
                    name,
                    native,
                    "Measurements",
                    None,
                    reason=f"Upstream presence: {native['presence']}",
                )
                continue
            start = native["addr"] + offset
            unit = (
                "kWh"
                if "kwh" in name.lower() or name == "monthEnergy"
                else "kW"
                if "kw" in name.lower()
                else "%"
                if name == "batteryPercent"
                else None
            )
            add_field(
                profile,
                name,
                native | {"addressOffset": offset},
                "Measurements",
                unit,
                {
                    "function": native["fc"],
                    "registers": list(range(start, start + native["count"])),
                    "encoding": "signed" if native.get("signed") else "unsigned",
                    "word_order": "big",
                    "scale": native.get("scale", 1),
                    "minimum": native.get("min"),
                    "maximum": native.get("max"),
                },
            )
        # Preserve every alarm code and bit definition, but do not promote it to
        # fleet incidents without an accepted model/profile and severity mapping.
        for index, alarm in enumerate(source.get("alarms", [])):
            add_field(
                profile,
                f"Alarm bitfield {index + 1}",
                alarm,
                "Alarms",
                None,
                reason="Native alarm bitfield: requires reviewed incident/severity mapping.",
            )
        result.append(profile)
    return result


class HaYamlLoader(yaml.SafeLoader):
    pass


# Retain the NAME of an HA secret as inert metadata. Never resolve secrets.yaml.
HaYamlLoader.add_constructor(
    "!secret", lambda loader, node: {"ha_secret_name": loader.construct_scalar(node)}
)


def import_sungrow(root):
    project = root / "Sungrow-SHx-Inverter-Modbus-Home-Assistant-main"
    path = project / "modbus_sungrow.yaml"
    data = yaml.load(path.read_text("utf-8"), Loader=HaYamlLoader)
    profile = metadata(
        path,
        project,
        "sungrow-ha-models",
        "Sungrow SHx (2026 HA definition)",
        "Sungrow",
        ["SHx RT/RS: check model and firmware limitations"],
        "https://github.com/mkaiser/Sungrow-SHx-Inverter-Modbus-Home-Assistant",
        "Modbus TCP; internal LAN/WiNet have different availability",
    )
    for hub in data["modbus"]:
        for item in hub["sensors"]:
            dtype = item.get("data_type", "int16")
            encoding = "ascii" if dtype == "string" else "signed" if dtype.startswith("int") else "unsigned"
            count = item.get("count", 2 if "32" in dtype else 1)
            spec = {
                "function": 4 if item.get("input_type", "holding") == "input" else 3,
                "registers": list(range(item["address"], item["address"] + count)),
                "encoding": encoding,
                "word_order": "little" if item.get("swap") == "word" else "big",
                "scale": item.get("scale", 1),
                "post_offset": item.get("offset", 0),
            }
            reason = None
            if dtype not in ("string", "int16", "uint16", "int32", "uint32") or item.get("swap") not in (
                None,
                "word",
            ):
                spec, reason = None, "Unsupported HA data_type/swap; review source."
            if any(
                key in item
                for key in ("nan_value", "zero_suppress", "structure", "slave_count", "virtual_count")
            ):
                spec, reason = (
                    None,
                    "HA sentinel/custom decoding requires additional source-specific handling.",
                )
            add_field(
                profile, item["name"], item, "Measurements", item.get("unit_of_measurement"), spec, reason
            )
    return [profile]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", type=Path, required=True)
    args = parser.parse_args()
    result = import_solarman(args.root) + import_glance(args.root) + import_sungrow(args.root)
    for profile in result:
        profile["profile_digest"] = profile_hash(profile)
        ModelProfile.model_validate(profile)
    DEST.mkdir(parents=True, exist_ok=True)
    (DEST / "model-library.json").write_text(
        json.dumps(
            {"schema_version": 1, "importer_version": 1, "profiles": result}, ensure_ascii=False, indent=2
        )
        + "\n",
        encoding="utf-8",
    )
    license_dir = DEST / "licenses"
    license_dir.mkdir(exist_ok=True)
    for directory, filename, target in [
        ("ha-solarman-main", "license", "ha-solarman-MIT.txt"),
        ("solar-inverter-modbus-registers-main", "LICENSE", "glance-registers-MIT.txt"),
        ("Sungrow-SHx-Inverter-Modbus-Home-Assistant-main", "LICENSE", "sungrow-ha-MIT.txt"),
    ]:
        (license_dir / target).write_bytes((args.root / directory / filename).read_bytes())
    print(
        json.dumps(
            {
                "profiles": len(result),
                "fields": sum(len(p["fields"]) for p in result),
                "readable": sum(bool(f["decode"]) for p in result for f in p["fields"]),
            }
        )
    )


if __name__ == "__main__":
    main()
