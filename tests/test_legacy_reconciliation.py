"""Small synthetic provenance trees; never copy or execute upstream code."""

import hashlib
import importlib.util
from pathlib import Path

SPEC = importlib.util.spec_from_file_location(
    "reconcile_legacy", Path(__file__).resolve().parents[1] / "scripts/reconcile_legacy.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


def test_presence_hash_lock_mismatch_and_exclusions(tmp_path):
    project = tmp_path / "synthetic"
    project.mkdir()
    (project / "LICENSE").write_text("synthetic fixture only")
    (project / "source.py").write_text("never executed")
    (project / ".git").mkdir()
    (project / ".git" / "config").write_text("excluded")
    inventory = {"excluded_directory_names": [".git"], "projects": [
        {"project": "synthetic", "files": 2}, {"project": "missing", "files": 1}]}
    locks = [{"local_directory": "synthetic", "files": [
        {"path": "source.py", "sha256": hashlib.sha256(b"never executed").hexdigest()},
        {"path": "LICENSE", "sha256": "old"}, {"path": "absent", "sha256": "old"}]}]
    result = MODULE.reconcile(tmp_path, inventory, locks)
    row, absent = result["projects"]
    assert row["files"] == 2
    assert [f["status"] for f in row["locked_files"]] == ["MATCH", "CHANGED", "MISSING"]
    assert len(row["license_files"]) == 1
    assert not absent["present"]
    assert absent["files"] == 0
    assert MODULE.reconcile(tmp_path, inventory, locks)["projects"] == result["projects"]