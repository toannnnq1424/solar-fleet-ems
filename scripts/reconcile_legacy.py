"""Read-only legacy provenance inspection; no upstream imports or license promotion.

Print JSON to stdout; redirect to an evidence file explicitly. Historical tree
hashes are not compared because the original per-file manifest/algorithm is absent.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    value = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            value.update(block)
    return value.hexdigest()


def reconcile(root, inventory, locks):
    excluded = set(inventory["excluded_directory_names"])
    rows = []
    for project in inventory["projects"]:
        name = project["project"]
        directory = root / name
        licenses = []
        files = []
        if directory.is_dir() and not directory.is_symlink():
            for path in sorted(directory.rglob("*")):
                relative = path.relative_to(directory)
                if any(part in excluded for part in relative.parts) or path.is_symlink():
                    continue
                if not path.is_file() or not path.resolve().is_relative_to(directory.resolve()):
                    continue
                files.append((relative.as_posix(), digest(path)))
                if path.name.lower().startswith(("license", "licence", "copying")):
                    licenses.append({"path": relative.as_posix(), "sha256": files[-1][1]})
        manifest = dict(files)
        selected = []
        for lock in locks:
            if lock["local_directory"] != name:
                continue
            for source in lock["files"]:
                actual = manifest.get(source["path"])
                selected.append({"path": source["path"], "expected_sha256": source["sha256"],
                                 "actual_sha256": actual,
                                 "status": "MATCH" if actual == source["sha256"] else "MISSING" if actual is None else "CHANGED"})
        # This explicit algorithm is portable; never imply equivalence to an undocumented old hash.
        tree = hashlib.sha256("".join(f"{name}\0{sha}\n" for name, sha in files).encode()).hexdigest()
        rows.append({"project": name, "present": directory.is_dir(), "files": len(files),
                     "previous_files": project["files"], "tree_sha256_path_nul_digest_lf": tree,
                     "historical_tree_comparison": "UNVERIFIABLE_WITHOUT_ORIGINAL_ALGORITHM",
                     "license_files": licenses, "locked_files": selected,
                     "disposition": "reference-only; no new import authorized",
                     "blocker": "file/dependency license and feature-owner review required before new reuse"})
    return {"reviewed_at_utc": datetime.now(UTC).isoformat(), "root_label": root.name,
            "method": "sha256 of sorted UTF-8 relative-path NUL file-sha256 LF; excludes symlinks/cache/build",
            "scope": "local presence, license-file hashes and existing selected-source locks; not legal acceptance",
            "projects": rows}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True, type=Path)
    args = parser.parse_args()
    if not args.root.is_dir():
        parser.error("legacy root must be an existing directory")
    inventory = json.loads((ROOT / "docs/evidence/legacy-project-inventory.json").read_text())
    locks = json.loads((ROOT / "src/solar_fleet/data/model-source-lock.json").read_text())
    print(json.dumps(reconcile(args.root, inventory, locks), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()