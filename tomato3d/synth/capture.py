"""Addendum A generator capture (revisions A.3/A.4): validation and derived measurements.

Per plant session ``data/raw/<plant_id>/<plant_id>_gen_<YYYYMMDD>/``: ``top``,
``side_000/090/180/270`` (camera 20-30 deg down) and ``level_000/090/180/270`` (level), plus the
human-written ``generator_capture.csv``. Everything under ``data/`` is read-only: nothing is
written, renamed or repaired there. Malformed rows are reported and skipped.

Height rule (A.2/A.3): per ``level_*`` photo, ruler reading at the plant top minus the
reading at the pot rim in the same photo; ``height_above_rim_cm`` = median of the four,
spread = max - min, ``height_inconsistent`` when spread exceeds the configured limit.
"""

from __future__ import annotations

import csv
import hashlib
import re
from pathlib import Path
from typing import Any, Iterable

import numpy as np

PHOTO_KINDS = frozenset({"top", "side", "level"})
AZIMUTHS = ("0", "90", "180", "270")
EXPECTED_STEMS = ("top",) + tuple(f"side_{int(a):03d}" for a in AZIMUTHS) + tuple(f"level_{int(a):03d}" for a in AZIMUTHS)
SESSION_RE = re.compile(r"^(?P<plant>.+)_gen_(?P<date>\d{8})$")
REQUIRED_COLUMNS = ("plant_id", "session_id", "photo_file", "photo_kind", "azimuth_deg")


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def discover_sessions(raw_dir: Path) -> list[Path]:
    """Every ``<plant>/<plant>_gen_<date>`` folder under the raw-data root (sorted)."""
    out = []
    raw_dir = Path(raw_dir)
    if not raw_dir.is_dir():
        return out
    for plant_dir in sorted(p for p in raw_dir.iterdir() if p.is_dir()):
        for s in sorted(p for p in plant_dir.iterdir() if p.is_dir()):
            m = SESSION_RE.match(s.name)
            if m and m.group("plant") == plant_dir.name:
                out.append(s)
    return out


def parse_notes(notes: str) -> dict[str, str]:
    """``key=value; key=value; free text`` -> keys (free-text items under ``tags``)."""
    out: dict[str, str] = {}
    tags = []
    for item in (notes or "").split(";"):
        item = item.strip()
        if not item:
            continue
        if "=" in item:
            k, v = item.split("=", 1)
            out[k.strip()] = v.strip()
        else:
            tags.append(item)
    if tags:
        out["tags"] = "; ".join(tags)
    return out


def validate_session(session_dir: Path) -> dict[str, Any]:
    """Validate one session against its files. Never raises for content problems."""
    session_dir = Path(session_dir)
    problems: list[dict[str, Any]] = []
    rows_ok: list[dict[str, Any]] = []
    csv_path = session_dir / "generator_capture.csv"
    result: dict[str, Any] = dict(session_dir=str(session_dir), session_id=session_dir.name,
                                  plant_id=session_dir.parent.name, rows=rows_ok, problems=problems)
    if not csv_path.is_file():
        problems.append(dict(row=None, problem="missing_generator_capture_csv"))
        result.update(status="invalid", csv_sha256=None)
        return result
    result["csv_sha256"] = _sha256(csv_path)
    with csv_path.open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        missing_cols = [c for c in REQUIRED_COLUMNS if c not in (reader.fieldnames or [])]
        rows = list(reader)
    if missing_cols:
        problems.append(dict(row=None, problem="missing_columns", columns=missing_cols))
        result.update(status="invalid")
        return result
    seen_files: set[str] = set()
    seen_slots: set[tuple[str, str]] = set()
    for i, r in enumerate(rows, start=2):
        kind = (r.get("photo_kind") or "").strip()
        name = (r.get("photo_file") or "").strip()
        az = (r.get("azimuth_deg") or "").strip()
        issue = None
        if kind not in PHOTO_KINDS:
            issue = dict(problem="unknown_photo_kind", value=kind)
        elif name in seen_files:
            issue = dict(problem="duplicate_photo_file", value=name)
        elif kind != "top" and az not in AZIMUTHS:
            issue = dict(problem="invalid_azimuth", value=az)
        elif (kind, az) in seen_slots:
            issue = dict(problem="duplicate_slot", value=f"{kind}/{az}")
        elif not (session_dir / name).is_file():
            issue = dict(problem="missing_file", value=name)
        if issue is None:
            sha = _sha256(session_dir / name)
            declared = (r.get("sha256") or "").strip().lower()
            if declared and declared != sha:
                issue = dict(problem="sha256_mismatch", value=name)
        if issue is not None:
            problems.append(dict(row=i, **issue))
            continue
        seen_files.add(name)
        seen_slots.add((kind, az))
        rows_ok.append(dict(r, row=i, sha256_actual=sha, stem=Path(name).stem))
    stems = {r["stem"] for r in rows_ok}
    missing = [s for s in EXPECTED_STEMS if s not in stems]
    if missing:
        problems.append(dict(row=None, problem="incomplete", missing=missing))
    result["status"] = "ok" if not problems else ("incomplete" if missing and len(problems) == 1 else "issues")
    top = next((r for r in rows_ok if r["photo_kind"] == "top"), None)
    result["notes"] = parse_notes(top.get("notes", "")) if top else {}
    result["azimuth_basis"] = sorted({(r.get("azimuth_basis") or "").strip() for r in rows_ok} - {""})
    return result


def capture_status(sessions: list[dict[str, Any]]) -> str:
    """``pending`` (nothing usable), ``integrated`` (all sessions ok) or ``partial``."""
    usable = [s for s in sessions if s["status"] == "ok"]
    if not usable:
        return "pending"
    return "integrated" if len(usable) == len(sessions) else "partial"


def height_from_readings(readings: Iterable[dict[str, Any]], max_spread_cm: float) -> dict[str, Any]:
    """Aggregate per-``level_*`` readings ``{azimuth_deg, rim_cm, top_cm}`` (A.3 rule)."""
    per = []
    for r in readings:
        if r.get("rim_cm") in (None, "") or r.get("top_cm") in (None, ""):
            continue
        per.append(dict(azimuth_deg=str(r["azimuth_deg"]),
                        height_above_rim_cm=float(r["top_cm"]) - float(r["rim_cm"])))
    if not per:
        return dict(height_above_rim_cm=None, spread_cm=None, n=0, flags=["no_readings"], per_photo=per)
    h = np.array([p["height_above_rim_cm"] for p in per])
    spread = float(h.max() - h.min())
    flags = ["height_inconsistent"] if spread > max_spread_cm else []
    if len(per) < len(AZIMUTHS):
        flags.append("fewer_than_four_level_photos")
    return dict(height_above_rim_cm=float(np.median(h)), spread_cm=spread, n=len(per), flags=flags, per_photo=per)


def resolve_compounds(support: dict[str, list[str]]) -> dict[str, str]:
    """Compound id -> ``resolved`` when at least one photo supports it, else ``unresolved``."""
    return {cid: ("resolved" if photos else "unresolved") for cid, photos in support.items()}


def read_heic_rgb(path: Path) -> np.ndarray:
    """Decode a HEIC original (never re-encoded in place) to an RGB uint8 array."""
    import pillow_heif  # lazy: tomato_synth env only

    heif = pillow_heif.open_heif(str(path), convert_hdr_to_8bit=True)
    image = heif.to_pillow()
    from PIL import ImageOps

    return np.asarray(ImageOps.exif_transpose(image).convert("RGB"))
