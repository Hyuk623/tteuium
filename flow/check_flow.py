"""Check the P1 -> canopy -> P2 -> P4 -> P3 -> relight flow map against the project folder.

Usage (from the project root or anywhere):
    python -X utf8 flow/check_flow.py            # print the table by stage
    python -X utf8 flow/check_flow.py --md       # also write flow/FLOW_STATUS.md

Reads flow/flow_map.csv only. Does not import or run any project code, and never edits anything
outside flow/. A path that no longer exists is reported as MISSING so the map can be corrected.
"""
from __future__ import annotations

import csv
import sys
from datetime import datetime
from pathlib import Path

FLOW_DIR = Path(__file__).resolve().parent
ROOT = FLOW_DIR.parent
MAP = FLOW_DIR / "flow_map.csv"

STATUS_KO = {
    "executed": "실행됨",
    "implemented": "구현됨",
    "partial": "일부",
    "demo_only": "틀·데모만",
    "in_progress": "작업 중",
    "spec_only": "사양만",
    "absent": "없음",
}


def load_rows() -> list[dict]:
    with MAP.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    for r in rows:
        p = r["path"].strip()
        if p.startswith("("):
            r["exists"] = "-"
            r["modified"] = ""
            continue
        full = ROOT / p
        r["exists"] = "OK" if full.exists() else "MISSING"
        r["modified"] = (
            datetime.fromtimestamp(full.stat().st_mtime).strftime("%Y-%m-%d") if full.exists() else ""
        )
    return rows


def render(rows: list[dict]) -> str:
    out = ["# 흐름 상태 (자동 생성: flow/check_flow.py)", ""]
    stages: dict[tuple[int, str], list[dict]] = {}
    for r in rows:
        stages.setdefault((int(r["order"]), r["stage"]), []).append(r)
    for (_, stage), items in sorted(stages.items()):
        out += [f"## {stage}", "", "| 프로그램 | 경로 | 주체 | 상태 | 파일 | 수정일 | 메모 |", "|---|---|---|---|---|---|---|"]
        for r in items:
            out.append(
                f"| {r['program']} | `{r['path']}` | {r['owner']} | {STATUS_KO.get(r['status'], r['status'])} "
                f"| {r['exists']} | {r['modified']} | {r['note']} |"
            )
        out.append("")
    missing = [r for r in rows if r["exists"] == "MISSING"]
    out.append(f"경로 없음: {len(missing)}건" + ("" if not missing else " — " + ", ".join(r["path"] for r in missing)))
    return "\n".join(out) + "\n"


def main(argv: list[str]) -> int:
    rows = load_rows()
    text = render(rows)
    print(text)
    if "--md" in argv:
        (FLOW_DIR / "FLOW_STATUS.md").write_text(text, encoding="utf-8")
    return 1 if any(r["exists"] == "MISSING" for r in rows) else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
