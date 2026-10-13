"""Human confirmation of the proposed top-view instances (X4 of
``handoff/CLAUDE_CODE_CLI_PROMPT_TOPVIEW_REAL_LINK_2026-10-12.md``), in the style of ``tomato3d.cli.rim_points_tool``.

    python -X utf8 -m tomato3d.topview.confirm_tool build --run build/topview_<date>_<nn>/real_top --out build/topview_confirm_<date>_<nn>
    python -X utf8 -m tomato3d.topview.confirm_tool check --run ... --csv <saved confirmations.csv>

``build`` writes a self-contained ``index.html`` (photos + mask overlays embedded) and ``confirmations_template.csv``
(every instance ``decision = proposed``). A person accepts, rejects or fixes each compound / leaflet (class, compound
membership, own-pot attribution, mask good or not) and saves ``confirmations.csv``. The file is HUMAN-OWNED and stays
under ``build/`` - it is never written into ``data/records/`` by this tool. ``check`` validates a saved file against
the run (instance ids, raw photo sha256, allowed values) and reports what is confirmed, rejected and still proposed.

Rules: a row stays ``proposed`` until a person decides; ``accept`` keeps every proposed value; ``fix`` must change
at least one value (or say the mask is bad); ``reject`` = not a real organ of this plant or not this class at all.
Detector boxes and SAM masks remain suggestions (DETECTOR_POLICY).

Exit codes: 0 written / valid; 2 input error (missing run files, existing output folder, invalid confirmations).
"""

from __future__ import annotations

import argparse
import base64
import csv
import json
import sys
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.topview import instances as inst

HERE = Path(__file__).resolve().parent
EXIT_OK, EXIT_INPUT = 0, 2
CONFIRM_COLUMNS = ("plant_id", "image_sha256", "instance_id", "kind", "proposed_class", "proposed_compound_id",
                   "proposed_attribution", "decision", "class", "compound_id", "attribution", "mask_ok", "annotator",
                   "note")
DECISIONS = ("proposed", "accept", "reject", "fix")
LEAFLET_CLASSES = ("leaf", "terminal_leaf", "leaf2")
COMPOUND_CLASS = "compond_leaf"
NO_COMPOUND = "none"
DISPLAY_SCALE = 0.5          # the embedded photo is shown at half resolution; decisions are per instance, not px


class ConfirmError(ValueError):
    """A confirmations file breaks its rules; reported, never repaired."""


def _photo_dirs(run: Path) -> list[Path]:
    dirs = sorted(p.parent for p in Path(run).glob("*/measure2d.json"))
    if not dirs:
        raise ConfirmError(f"{run}: no */measure2d.json")
    return dirs


def _read_csv(path: Path) -> list[dict[str, str]]:
    with Path(path).open(encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def proposals(run: Path) -> list[dict[str, str]]:
    """Template rows (all ``proposed``) for every compound and leaflet of every photo in a measure2d run."""
    rows = []
    for d in _photo_dirs(run):
        head = json.loads((d / "measure2d.json").read_text(encoding="utf-8"))
        if head.get("plant_id") in (None, "unavailable"):
            raise ConfirmError(f"{d}: photo not linked to a capture (no plant_id) - nothing to confirm against")
        for r in _read_csv(d / "compounds_2d.csv"):
            rows.append(dict(plant_id=r["plant_id"], image_sha256=r["image_sha256"], instance_id=r["compound_id"],
                             kind="compound", proposed_class=r["class"], proposed_compound_id=NO_COMPOUND,
                             proposed_attribution=r["attribution"]))
        for r in _read_csv(d / "leaflets_2d.csv"):
            cid = r["compound_id"] if r["membership_status"] == "member" else NO_COMPOUND
            rows.append(dict(plant_id=r["plant_id"], image_sha256=r["image_sha256"], instance_id=r["leaflet_id"],
                             kind="leaflet", proposed_class=r["class"], proposed_compound_id=cid,
                             proposed_attribution=r["attribution"]))
    for r in rows:
        r.update(decision="proposed", **{"class": r["proposed_class"]}, compound_id=r["proposed_compound_id"],
                 attribution=r["proposed_attribution"], mask_ok="", annotator="", note="")
    return rows


def write_csv(path: Path, rows: list[dict[str, str]]) -> None:
    with Path(path).open("w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=CONFIRM_COLUMNS, lineterminator="\n")
        w.writeheader()
        w.writerows(rows)


def check(run: Path, path: Path) -> dict[str, Any]:
    """Validate a saved confirmations file against the run; returns final values and counts per status."""
    expected = {r["instance_id"]: r for r in proposals(run)}
    with Path(path).open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        if tuple(reader.fieldnames or ()) != CONFIRM_COLUMNS:
            raise ConfirmError(f"{Path(path).name}: header {reader.fieldnames} != {CONFIRM_COLUMNS}")
        got = list(reader)
    compounds = {(e["plant_id"], i) for i, e in expected.items() if e["kind"] == "compound"}
    seen, final, problems = set(), {}, []
    for n, r in enumerate(got, start=2):
        where = f"line {n} ({r.get('instance_id')})"
        e = expected.get(r["instance_id"])
        if e is None:
            problems.append(f"{where}: instance not in the run")
            continue
        if r["instance_id"] in seen:
            problems.append(f"{where}: duplicate row")
        seen.add(r["instance_id"])
        for k in ("plant_id", "image_sha256", "kind", "proposed_class", "proposed_compound_id",
                  "proposed_attribution"):
            if r[k] != e[k]:
                problems.append(f"{where}: {k} {r[k]!r} != run {e[k]!r} (proposal columns are read-only)")
        if r["decision"] not in DECISIONS:
            problems.append(f"{where}: decision {r['decision']!r} not in {DECISIONS}")
            continue
        classes = (COMPOUND_CLASS,) if e["kind"] == "compound" else LEAFLET_CLASSES
        if r["class"] not in classes:
            problems.append(f"{where}: class {r['class']!r} not in {classes}")
        if r["attribution"] not in inst.ATTRIBUTIONS:
            problems.append(f"{where}: attribution {r['attribution']!r} not in {inst.ATTRIBUTIONS}")
        if r["compound_id"] != NO_COMPOUND and (e["kind"] == "compound" or (e["plant_id"], r["compound_id"])
                                                not in compounds):
            problems.append(f"{where}: compound_id {r['compound_id']!r} is not a compound of this photo")
        if r["mask_ok"] not in ("", "yes", "no"):
            problems.append(f"{where}: mask_ok {r['mask_ok']!r} not in ('', 'yes', 'no')")
        changed = any(r[k] != r["proposed_" + k] for k in ("class", "compound_id", "attribution"))
        if r["decision"] == "proposed" and (changed or r["mask_ok"]):
            problems.append(f"{where}: values changed but decision is still 'proposed' - choose accept/fix/reject")
        if r["decision"] == "accept" and (changed or r["mask_ok"] == "no"):
            problems.append(f"{where}: 'accept' keeps every proposed value and a good mask; use 'fix'")
        if r["decision"] == "fix" and not (changed or r["mask_ok"] == "no"):
            problems.append(f"{where}: 'fix' changes nothing")
        if r["decision"] != "proposed" and not r["annotator"].strip():
            problems.append(f"{where}: a decision needs the annotator")
        status = dict(proposed="proposed", accept="confirmed", fix="confirmed", reject="rejected")[r["decision"]]
        final[r["instance_id"]] = dict(status=status, **{k: r[k] for k in ("class", "compound_id", "attribution",
                                                                           "mask_ok", "annotator", "note")})
    missing = sorted(set(expected) - seen)
    if missing:
        problems.append(f"{len(missing)} run instances have no row (e.g. {missing[0]})")
    if problems:
        raise ConfirmError("; ".join(problems[:20]) + (f" (+{len(problems) - 20} more)" if len(problems) > 20 else ""))
    counts = {s: sum(v["status"] == s for v in final.values()) for s in ("confirmed", "rejected", "proposed")}
    return dict(counts=counts, instances=final)


# --------------------------------------------------------------------------- page
def _rgba_png(mask_crop: np.ndarray) -> str:
    rgba = np.zeros(mask_crop.shape + (4,), np.uint8)
    rgba[mask_crop] = (255, 255, 255, 255)
    ok, buf = cv2.imencode(".png", rgba)
    if not ok:
        raise ConfirmError("PNG encode failed")
    return "data:image/png;base64," + base64.b64encode(buf.tobytes()).decode("ascii")


def page_data(run: Path, project_root: Path) -> dict[str, Any]:
    from tomato3d.synth.images import imread

    photos = []
    rows = proposals(run)
    for d in _photo_dirs(run):
        head = json.loads((d / "measure2d.json").read_text(encoding="utf-8"))
        man = json.loads((d / "masks_manifest.json").read_text(encoding="utf-8"))
        img_path = Path(project_root) / head["image"] if not Path(head["image"]).is_absolute() else Path(head["image"])
        bgr = imread(img_path, cv2.IMREAD_COLOR)
        if bgr is None:
            raise ConfirmError(f"cannot read {img_path}")
        small = cv2.resize(bgr, None, fx=DISPLAY_SCALE, fy=DISPLAY_SCALE, interpolation=cv2.INTER_AREA)
        ok, jpg = cv2.imencode(".jpg", small, [cv2.IMWRITE_JPEG_QUALITY, 88])
        masks = {}
        for e in man["masks"]:
            if e["png"] is None:
                continue
            full = inst.load_mask(e, d)
            x0, y0 = e["offset_px"]
            w, h = e["crop_size_px"]
            masks[e["instance_id"]] = dict(png=_rgba_png(full[y0:y0 + h, x0:x0 + w]), x=x0, y=y0, w=w, h=h)
        attr = head["attribution"]["own_rim_polygon_px"]
        photos.append(dict(plant_id=head["plant_id"], capture_id=head["capture_id"], image_sha256=head["image_sha256"],
                           size_px=head["image_size_px"], jpg="data:image/jpeg;base64," +
                           base64.b64encode(jpg.tobytes()).decode("ascii"), display_scale=DISPLAY_SCALE,
                           rim_polygon_px=attr if isinstance(attr, list) else None, masks=masks,
                           v4_split=head["detector"].get("v4_split", "unavailable")))
    return dict(schema="topview-confirm-tool-1", run=Path(run).as_posix(), columns=list(CONFIRM_COLUMNS),
                leaflet_classes=list(LEAFLET_CLASSES), compound_class=COMPOUND_CLASS,
                attributions=list(inst.ATTRIBUTIONS), rows=rows, photos=photos)


def build(run: Path, out: Path, project_root: Path = Path(".")) -> Path:
    out = Path(out)
    if out.exists():
        raise ConfirmError(f"{out} exists; outputs are never overwritten")
    if "records" in out.resolve().parts and "data" in out.resolve().parts:
        raise ConfirmError("the confirmation tool never writes under data/records/")
    doc = page_data(run, project_root)
    page = (HERE / "confirm_tool.html").read_text(encoding="utf-8")
    out.mkdir(parents=True)
    (out / "index.html").write_text(page.replace("__DATA__", json.dumps(doc, ensure_ascii=False).replace("</", "<\\/")),
                                    encoding="utf-8")
    write_csv(out / "confirmations_template.csv", doc["rows"])
    (out / "README.md").write_text(
        "# 위 사진 인스턴스 사람 확인 (X4)\n\n"
        "`index.html`을 Chrome/Edge로 엽니다. 복엽·소엽마다 수락 / 거부 / 수정을 고르고 `confirmations.csv`로 "
        "저장합니다. 이 파일은 사람이 소유하며 `build/` 아래에 둡니다(`data/records/`에 넣지 않음).\n\n"
        "- 수락: 제안된 클래스·복엽 소속·화분 귀속·마스크를 그대로 인정\n"
        "- 수정: 하나 이상 바꾸거나 마스크가 나쁘다고 표시\n"
        "- 거부: 이 식물의 기관이 아니거나 검출 자체가 틀림\n"
        "- 고르지 않은 행은 `proposed`로 남고 관측으로 쓰이지 않습니다.\n\n"
        f"검사: `python -X utf8 -m tomato3d.topview.confirm_tool check --run {Path(run).as_posix()} --csv <저장한 파일>`\n",
        encoding="utf-8")
    return out / "index.html"


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    sub = ap.add_subparsers(dest="cmd", required=True)
    b = sub.add_parser("build")
    b.add_argument("--run", required=True)
    b.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("--run", required=True)
    c.add_argument("--csv", required=True)
    args = ap.parse_args(argv)
    try:
        if args.cmd == "build":
            print(build(Path(args.run), Path(args.out)).as_posix())
        else:
            print(json.dumps(check(Path(args.run), Path(args.csv))["counts"]))
    except ConfirmError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return EXIT_INPUT
    return EXIT_OK


if __name__ == "__main__":
    raise SystemExit(main())
