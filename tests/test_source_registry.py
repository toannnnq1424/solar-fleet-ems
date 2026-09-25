"""Evidence provenance must be unambiguous in both source and shipped package."""

import json
from pathlib import Path


def test_packaged_registry_matches_reviewed_registry_and_has_unique_ids():
    root = Path(__file__).resolve().parents[1]
    reviewed = json.loads((root / "docs/evidence/source-registry.json").read_text(encoding="utf-8"))
    packaged = json.loads((root / "src/solar_fleet/data/source-registry.json").read_text(encoding="utf-8"))
    assert reviewed == packaged
    ids = [r["id"] for r in reviewed]
    assert len(ids) == len(set(ids))
    for row in reviewed:
        if "withdrawn" in row["access_status"]:
            assert row["evidence_grade"] == "F"
            assert row["sha256"] == "UNKNOWN"
