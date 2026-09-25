"""Reproducible handwritten source inventory. This script does not run tests or import the app."""

from __future__ import annotations

import argparse
import json
from datetime import UTC, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
START = "<!-- actual-code-inventory:start -->"
END = "<!-- actual-code-inventory:end -->"
GROUPS = (
    ("backend", "Backend Python", "src/solar_fleet", {".py"}),
    ("frontend_js", "Frontend JavaScript", "src/solar_fleet/static", {".js"}),
    ("frontend_style", "Frontend CSS / HTML", "src/solar_fleet/static", {".css", ".html"}),
    ("backend_tests", "Test BE / simulator / fixture", "tests", {".py"}),
    ("browser_tests", "Test UI / browser fixture", "ui_tests", {".py"}),
    ("scripts", "Scripts tự viết", "scripts", {".py", ".js", ".cjs", ".mjs", ".ps1"}),
)


def inventory():
    groups = []
    for key, label, directory, suffixes in GROUPS:
        entries = []
        for path in sorted((ROOT / directory).rglob("*")):
            if not path.is_file() or path.suffix not in suffixes or "__pycache__" in path.parts:
                continue
            lines = path.read_text(encoding="utf-8-sig").splitlines()
            entries.append(
                {
                    "path": path.relative_to(ROOT).as_posix(),
                    "lines": len(lines),
                    "nonblank": sum(bool(line.strip()) for line in lines),
                }
            )
        groups.append(
            {
                "key": key,
                "label": label,
                "files": len(entries),
                "lines": sum(row["lines"] for row in entries),
                "nonblank": sum(row["nonblank"] for row in entries),
                "entries": entries,
            }
        )
    return {
        "measured_at_utc": datetime.now(UTC).isoformat(),
        "scope": "working_tree_including_uncommitted",
        "method": "physical_lines_and_nonblank_lines_not_semantic_sloc",
        "groups": groups,
    }


def markdown(data):
    def total(keys, field):
        return sum(group[field] for group in data["groups"] if group["key"] in keys)

    lines = [
        START,
        "## Số dòng thực tế có thể đo lại",
        "",
        f"Đo lúc **{data['measured_at_utc']}** trên working tree, gồm code chưa commit.",
        "",
        "| Nhóm | Số file | Dòng vật lý | Dòng không trống |",
        "|---|---:|---:|---:|",
    ]
    for group in data["groups"]:
        lines.append(
            f"| {group['label']} | {group['files']:,} | {group['lines']:,} | {group['nonblank']:,} |"
        )
    for label, keys in (
        ("Tổng FE (JS + CSS/HTML)", {"frontend_js", "frontend_style"}),
        ("Tổng code ứng dụng BE + FE", {"backend", "frontend_js", "frontend_style"}),
        ("Tổng test / simulator / fixture", {"backend_tests", "browser_tests"}),
        ("Tổng code ứng dụng + test + scripts", {row["key"] for row in data["groups"]}),
    ):
        lines.append(
            f"| **{label}** | **{total(keys, 'files'):,}** | **{total(keys, 'lines'):,}** | **{total(keys, 'nonblank'):,}** |"
        )
    lines += [
        "",
        "Phương pháp: đếm dòng vật lý (gồm comment và dòng trống), đồng thời công bố số dòng không trống. Không phải semantic SLOC. Không tính dependency, môi trường ảo, lock, generated, assets/ảnh, JSON hợp đồng, tài liệu, build output hoặc cache. Nhóm simulator/fixture không được tính vào production. Không cộng các dòng tổng lần nữa.",
        "",
        "Đo lại bằng `python scripts/measure_code.py --update-doc`; lệnh chỉ đọc source và cập nhật báo cáo, không chạy test, build, QA hoặc gọi thiết bị.",
        "",
        "Danh sách từng file và số dòng nằm trong [code-inventory.json](evidence/code-inventory.json). LOC phản ánh kích thước mã, không chứng minh workflow đúng, hoàn thiện UI hoặc nghiệm thu phần cứng.",
        END,
    ]
    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--update-doc", action="store_true")
    args = parser.parse_args()
    data = inventory()
    if args.update_doc:
        path = ROOT / "docs/mockup-coverage.md"
        text = path.read_text(encoding="utf-8")
        section = markdown(data)
        if START in text:
            before, rest = text.split(START, 1)
            _, after = rest.split(END, 1)
            text = before + section + after
        else:
            text += "\n\n" + section + "\n"
        path.write_text(text, encoding="utf-8")
        (ROOT / "docs/evidence/code-inventory.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
        )
    print(
        json.dumps(
            {
                "measured_at_utc": data["measured_at_utc"],
                "groups": [{k: v for k, v in group.items() if k != "entries"} for group in data["groups"]],
            },
            ensure_ascii=True,
        )
    )


if __name__ == "__main__":
    main()
