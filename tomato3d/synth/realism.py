"""Realism statistics and the pre-declared Stage 1 gate.

Synthetic statistics come from the written scene outputs; real references from hashed
real-data files. The gate criteria live in ``stage1_contract.json``, written before any
rendering; :func:`evaluate_gate` only reads them.
"""

from __future__ import annotations

import csv
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.synth.images import imread


def _sha256(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def plant_stats(graph: dict[str, Any], mesh_parts: list[dict[str, Any]] | None = None,
                obj_path: Path | None = None) -> dict[str, float]:
    """Plant height above soil and top-projection convex envelope from plant geometry."""
    from scipy.spatial import ConvexHull

    plant_organs = {"leaflet", "stem", "rachis", "petiolule", "apex"}
    if mesh_parts is not None:
        pts = np.vstack([p["vertices"] for p in mesh_parts if p["organ"] in plant_organs])
    else:
        pts = _obj_plant_vertices(Path(obj_path))
    soil_z = graph["placement"]["soil_z_board_mm"]
    hull = ConvexHull(pts[:, :2])
    n_leaflets = sum(len(i["leaflets"]) for i in graph["interiors"].values())
    return dict(height_mm=float(pts[:, 2].max() - soil_z), envelope_area_cm2=float(hull.volume / 100.0),
                n_compounds=len(graph["compounds"]), n_leaflets=n_leaflets)


def _obj_plant_vertices(path: Path) -> np.ndarray:
    keep, pts = False, []
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("o "):
            name = line[2:]
            keep = not any(name.startswith(x) for x in ("pot", "soil", "board"))
        elif keep and line.startswith("v "):
            pts.append([float(x) for x in line.split()[1:4]])
    return np.array(pts)


def view_stats(view_dir: Path, min_visible_px: int) -> dict[str, Any]:
    """Per-view leaflet counts, visible areas and occlusion fractions from written layers."""
    view_dir = Path(view_dir)
    visible = imread(view_dir / "visible_mask.png")
    ids, counts = np.unique(visible[visible > 0], return_counts=True)
    vis_px = dict(zip(ids.tolist(), counts.tolist()))
    index = json.loads((view_dir.parent.parent / "leaflet_index.json").read_text(encoding="utf-8"))
    by_name = {f"{v['compound_id']}_{v['tag']}": int(k) for k, v in index.items()}
    occl = []
    for f in sorted((view_dir / "amodal").glob("*.png")):
        inst = by_name.get(f.stem)
        amodal_px = int((imread(f) > 0).sum())
        if inst is None or amodal_px == 0:
            continue
        occl.append(1.0 - vis_px.get(inst, 0) / amodal_px)
    counted = [c for c in vis_px.values() if c >= min_visible_px]
    return dict(leaflets_per_photo=len(counted), visible_leaflet_area_px=counted, occlusion_fraction=occl,
                fully_hidden=int(sum(1 for o in occl if o >= 1.0)))


def real_reference(traits_csvs: list[Path], accepted_exports: dict[str, Path], out_size_px: int,
                   source_size_px: int) -> dict[str, Any]:
    """Real min/median/max from S8 traits and the human-reviewed leaflet masks."""
    heights, envelopes, refs = [], [], {}
    for p in traits_csvs:
        refs[str(p)] = _sha256(p)
        with Path(p).open(encoding="utf-8-sig", newline="") as f:
            for r in csv.DictReader(f):
                if r.get("hull_height_mm"):
                    heights.append(float(r["hull_height_mm"]))
                if r.get("hull_footprint_cm2"):
                    envelopes.append(float(r["hull_footprint_cm2"]))
    per_photo, areas = [], []
    scale2 = (out_size_px / float(source_size_px)) ** 2
    for plant, export in sorted(accepted_exports.items()):
        acc = Path(export) / "accepted.json"
        refs[str(acc)] = _sha256(acc)
        obs = [o for o in json.loads(acc.read_text(encoding="utf-8"))["observations"] if o["organ_class"] == "leaflet"]
        counts: dict[str, int] = {}
        for o in obs:
            counts[o["image_file"]] = counts.get(o["image_file"], 0) + 1
            areas.append(o["mask_area_px"] * scale2)
        per_photo += list(counts.values())

    def summary(x):
        x = np.asarray(x, float)
        return dict(n=int(len(x)), min=float(x.min()), p10=float(np.percentile(x, 10)), median=float(np.median(x)),
                    p90=float(np.percentile(x, 90)), max=float(x.max()))

    return dict(height_mm=summary(heights), envelope_area_cm2=summary(envelopes),
                leaflets_per_photo=summary(per_photo), visible_leaflet_area_px=summary(areas),
                out_size_px=out_size_px, source_refs=refs,
                notes=dict(height_mm="S8 hull_height_mm (visual-hull z extent)",
                           envelope_area_cm2="S8 hull_footprint_cm2 (occupancy footprint); synthetic uses the "
                                             "convex top envelope - definitions differ, declared in the contract",
                           leaflets_per_photo="accepted human-reviewed leaflet masks per photo (dwt_01-04)",
                           visible_leaflet_area_px="accepted mask areas rescaled to the output size"))


def evaluate_gate(contract: dict[str, Any], synthetic: dict[str, Any]) -> dict[str, Any]:
    """Apply the contract's criteria to synthetic medians; unavailable criteria stay pending."""
    results = []
    for c in contract["criteria"]:
        value = synthetic.get(c["synthetic_statistic"])
        if c["kind"] == "report_only":
            results.append(dict(c, value=value, status="reported"))
            continue
        if value is None:
            results.append(dict(c, value=None, status="pending"))
            continue
        ok = c["low"] <= value <= c["high"]
        results.append(dict(c, value=value, status="pass" if ok else "fail"))
    gated = [r for r in results if r["kind"] == "gate"]
    if any(r["status"] == "fail" for r in gated):
        overall = "fail"
    elif any(r["status"] == "pending" for r in gated):
        overall = "pending"
    else:
        overall = "pass"
    return dict(overall=overall, criteria=results)
