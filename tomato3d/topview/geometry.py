"""T3 (baseline) - projected 2-D -> leaflet tilt, true length and true one-sided area.

This is the ANALYTIC baseline the learned top-mask -> 3D model (prompt T3) must beat; the learned model needs the
calibrated paired dataset (T2), which the T0 gate holds back. The baseline uses one measured fact: a leaflet's true
length/width ratio lies in 1.4-1.7 (topview_config.json). For a planar leaflet tilted about its WIDTH axis
("pure pitch") the projected ratio is r_true * cos(e), so

    e = arccos(r_projected / r_true),   true_length = L' / cos e,   true_area = A' / cos e.

Pure pitch is the SMALLEST tilt that explains a projected ratio below r_true; any roll about the midrib needs more
tilt, so e(pure pitch, r_true = 1.4) is a lower bound and the area/length estimates are lower-bound-leaning.
A projected ratio above 1.7 cannot come from pitch alone (roll, curl, or a bad mask) and is flagged.

Sign: a top projection cannot tell up-tilt from down-tilt. The flow resolves it with the generator's bending prior,
which is not calibrated (T0 gate closed), so the sign is ``unavailable`` here - never ``measured``.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.topview.calibration import load_config

UNAVAILABLE = "unavailable"
STATUS = "inferred_aspect_prior_pure_pitch"


def _acos_deg(x: float) -> float:
    return math.degrees(math.acos(max(-1.0, min(1.0, x))))


def estimate_leaflet(length: float, width: float, area: float, aspect_range: tuple[float, float]) -> dict[str, Any]:
    """Tilt / true length / true area from projected length, width and area (any consistent unit).

    Returns point estimates at the mid prior ratio and the interval over the prior range, both under pure pitch.
    """
    r_lo, r_hi = aspect_range
    if width <= 0 or length <= 0 or area <= 0:
        return dict(status=UNAVAILABLE, reason="empty projection")
    rp = length / width
    r_mid = 0.5 * (r_lo + r_hi)
    e_mid, e_lo, e_hi = _acos_deg(rp / r_mid), _acos_deg(rp / r_lo), _acos_deg(rp / r_hi)
    cos = lambda e: math.cos(math.radians(e))  # noqa: E731
    out = dict(status=STATUS, projected_aspect=round(rp, 4),
               tilt_deg=round(e_mid, 2), tilt_deg_interval=[round(e_lo, 2), round(e_hi, 2)],
               tilt_sign=UNAVAILABLE, tilt_sign_reason="top projection is sign-blind; generator bending prior "
                                                       "not calibrated (T0)",
               true_length=round(length / cos(e_mid), 4),
               true_length_interval=[round(length / cos(e_lo), 4), round(length / cos(e_hi), 4)],
               true_area=round(area / cos(e_mid), 4),
               true_area_interval=[round(area / cos(e_lo), 4), round(area / cos(e_hi), 4)])
    if rp > r_hi:
        out["flag"] = "aspect_above_prior: pitch alone cannot explain it (roll, curl or mask error); tilt set 0"
    return out


# --------------------------------------------------------------------------- synthetic validation
def _mesh_truth(verts_cam: np.ndarray, faces: np.ndarray) -> tuple[float, float]:
    """(true one-sided area, area projected along the camera axis) in mm^2."""
    a, b, c = (verts_cam[faces[:, k]] for k in range(3))
    cr = np.cross(b - a, c - a)
    true = 0.5 * float(np.linalg.norm(cr, axis=1).sum())
    proj = 0.5 * float(np.abs(cr[:, 2]).sum())
    return true, proj


def evaluate_on_synthetic(run: Path, labels_json: Path, out: Path) -> dict[str, Any]:
    """Score the baseline against the generator's 3D truth on the exported top views.

    Per leaflet: projected measures from the stored AMODAL mask (upper bound) and the VISIBLE mask (what a real
    photo gives), mm/px from the depth map at that leaflet (stands in for the rim scale), truth from the mesh in
    ``render_job/parts.npz`` and ``leaflet_index.length_mm``. Three estimators: none (projected = true), the
    measured prior 1.4-1.7, and an ORACLE ratio (the generator's own L/W per leaflet) that isolates the method's
    error from the prior's.
    """
    from tomato3d.synth.camera import RigView
    from tomato3d.synth.config import load_generator_config
    from tomato3d.synth.images import imread
    from tomato3d.synth.pipeline import GeometryCache
    from tomato3d.synth.contours import load_library
    from tomato3d.synth.render_remote import load_parts
    from tomato3d.topview.measure2d import measure_mask

    cfg = load_config()
    prior = (cfg["leaflet_true_aspect_range"]["min"], cfg["leaflet_true_aspect_range"]["max"])
    run, labels = Path(run), json.loads(Path(labels_json).read_text(encoding="utf-8"))
    contract = json.loads((run / "stage1_contract.json").read_text(encoding="utf-8"))
    gc = GeometryCache(load_generator_config(run / "generator_config.json"), int(contract["resolution_px"]))
    views = {d["view_id"]: RigView(**{k: (tuple(map(tuple, v)) if k == "camera_matrix" else
                                          tuple(v) if isinstance(v, list) else v) for k, v in d.items()})
             for d in json.loads((run / "views.json").read_text(encoding="utf-8"))["views"]}
    contours, _ = load_library(run / "leaflet_contours.json")
    rows = []
    cache: dict[str, Any] = {}
    for im in labels["images"]:
        sid = im["scene_id"]
        if sid not in cache:
            sdir = run / "scenes" / sid
            job = json.loads((sdir / "render_job" / "job.json").read_text(encoding="utf-8"))
            parts = {p["name"]: p for p in load_parts(sdir / "render_job", job) if p["organ"] == "leaflet"}
            graph = json.loads((sdir / "plant_graph.json").read_text(encoding="utf-8"))
            leaf3d = {l["leaflet_id"]: l for it in graph["interiors"].values() for l in it["leaflets"]}
            cache = {sid: dict(index=json.loads((sdir / "leaflet_index.json").read_text(encoding="utf-8")),
                               parts=parts, leaf3d=leaf3d)}
        sc = cache[sid]
        vdir = run / Path(im["file_name"]).parent
        view = views[im["view_id"]]
        geom = gc.get(view)
        fx = 0.5 * (geom.K_out[0, 0] + geom.K_out[1, 1])
        vis_all = imread(vdir / "visible_mask.png")
        depth = np.load(vdir / "depth_mm.npy")
        R, t = view.rotation, view.translation
        for a in labels["annotations"]:
            if a["image_id"] != im["id"] or a["class"] not in cfg["leaflet_classes"]:
                continue
            key = next(k for k, v in sc["index"].items() if v["compound_id"] == a["compound_id"] and v["tag"] == a["tag"])
            info = sc["index"][key]
            vis = vis_all == int(key)
            amodal = imread(vdir / "amodal" / f"{a['compound_id']}_{a['tag']}.png") > 0
            z = depth[vis & (depth > 0)]
            if len(z) == 0:
                continue
            mm_px = float(np.median(z)) / fx
            part = sc["parts"][info["leaflet_id"]]
            true_area, proj_area = _mesh_truth(part["vertices"] @ R.T + t, np.asarray(part["faces"]))
            l3 = sc["leaf3d"][info["leaflet_id"]]
            c = np.asarray(contours[l3["contour_index"]], float)
            oracle = (c[:, 0].max() - c[:, 0].min()) / (c[:, 1].max() - c[:, 1].min()) / float(l3["width_scale"])
            row = dict(image_id=im["id"], leaflet=info["leaflet_id"], cls=a["class"], vis_frac=a["vis_frac"],
                       true_area_mm2=true_area, true_length_mm=float(l3["length_mm"]),
                       true_cos=proj_area / true_area, oracle_aspect=oracle)
            for src, m in (("amodal", amodal), ("visible", vis)):
                mm = measure_mask(m)
                if mm is None:
                    continue
                L, W, A = mm["length_px"] * mm_px, mm["width_px"] * mm_px, mm["area_px"] * mm_px ** 2
                row[f"{src}_proj_area_mm2"], row[f"{src}_proj_length_mm"] = A, L
                for name, rng in (("prior", prior), ("oracle", (oracle, oracle))):
                    e = estimate_leaflet(L, W, A, rng)
                    row[f"{src}_{name}_area_mm2"] = e.get("true_area")
                    row[f"{src}_{name}_length_mm"] = e.get("true_length")
                    row[f"{src}_{name}_cos"] = math.cos(math.radians(e["tilt_deg"])) if "tilt_deg" in e else None
            rows.append(row)

    def rel(est, truth):
        v = np.array([(r[est] - r[truth]) / r[truth] for r in sel if r.get(est) is not None])
        return dict(n=int(len(v)), median_rel_err=round(float(np.median(v)), 4) if len(v) else None,
                    median_abs_rel_err=round(float(np.median(np.abs(v))), 4) if len(v) else None)

    bins = {"vis_frac>=0.9": lambda r: r["vis_frac"] >= 0.9, "0.5<=vis_frac<0.9": lambda r: 0.5 <= r["vis_frac"] < 0.9,
            "vis_frac<0.5": lambda r: r["vis_frac"] < 0.5, "all": lambda r: True}
    summary = {}
    for bname, f in bins.items():
        sel = [r for r in rows if f(r)]
        summary[bname] = {
            "n": len(sel),
            **{f"area_{src}_{est}": rel(k, "true_area_mm2") for src in ("amodal", "visible")
               for est, k in (("none", f"{src}_proj_area_mm2"), ("prior", f"{src}_prior_area_mm2"),
                              ("oracle", f"{src}_oracle_area_mm2"))},
            **{f"length_{src}_{est}": rel(k, "true_length_mm") for src in ("amodal", "visible")
               for est, k in (("none", f"{src}_proj_length_mm"), ("prior", f"{src}_prior_length_mm"),
                              ("oracle", f"{src}_oracle_length_mm"))},
        }
    tc = np.array([r["true_cos"] for r in rows])
    oa = np.array([r["oracle_aspect"] for r in rows])
    result = dict(schema="topview-geometry-eval-1", run=run.as_posix(), labels=Path(labels_json).as_posix(),
                  n_leaflets=len(rows), prior_aspect_range=list(prior),
                  generator_true_aspect_p10_p50_p90=[round(float(x), 3) for x in np.percentile(oa, [10, 50, 90])],
                  true_projection_cos_p10_p50_p90=[round(float(x), 3) for x in np.percentile(tc, [10, 50, 90])],
                  scale_note="mm/px from the depth map at each leaflet (stands in for the rim scale)",
                  truth_note="true area = one-sided mesh area; true length = generator midrib length_mm",
                  summary=summary)
    Path(out).parent.mkdir(parents=True, exist_ok=True)
    Path(out).write_text(json.dumps(result, indent=1), encoding="utf-8")
    import csv

    with Path(out).with_suffix(".csv").open("w", encoding="utf-8", newline="") as f:
        keys = sorted({k for r in rows for k in r})
        w = csv.DictWriter(f, fieldnames=keys)
        w.writeheader()
        w.writerows(rows)
    return result


def estimate_photo(measure_csv: Path, out: Path) -> dict[str, Any]:
    """Apply the baseline to a T1 output (px, or mm when the rim scale is solved)."""
    import csv

    cfg = load_config()
    prior = (cfg["leaflet_true_aspect_range"]["min"], cfg["leaflet_true_aspect_range"]["max"])
    rows = list(csv.DictReader(Path(measure_csv).open(encoding="utf-8")))
    out_rows = []
    for r in rows:
        unit = "mm" if r["scale_status"] == "solved" else "px"
        keys = ("length_mm", "width_mm", "area_mm2") if unit == "mm" else ("length_px", "width_px", "area_px")
        if any(r[k] == UNAVAILABLE for k in keys):
            out_rows.append(dict(leaflet_id=r["leaflet_id"], status=UNAVAILABLE))
            continue
        e = estimate_leaflet(*(float(r[k]) for k in keys), prior)
        out_rows.append(dict(leaflet_id=r["leaflet_id"], cls=r["class"], unit=unit, **e))
    doc = dict(schema="topview-geometry-1", source=Path(measure_csv).as_posix(), method=STATUS,
               prior_aspect_range=list(prior), prior_source=cfg["leaflet_true_aspect_range"]["source_ref"],
               caveats=["pure pitch = minimum tilt; roll/curl need more tilt -> lengths and areas lean low",
                        "sign unavailable (prior not calibrated)", "rim-plane scale OVERestimates leaves above the rim (they are nearer the camera; factor Z_rim / Z_leaf > 1); no correction applied",
                        "a learned model (T3 proper) is blocked until the T0 calibration opens T2"],
               leaflets=out_rows)
    Path(out).write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="T3 baseline: aspect-prior tilt / true size")
    sub = ap.add_subparsers(dest="cmd", required=True)
    e = sub.add_parser("eval-synthetic")
    e.add_argument("--run", required=True)
    e.add_argument("--labels", required=True)
    e.add_argument("--out", required=True)
    p = sub.add_parser("photo")
    p.add_argument("--measure-csv", required=True)
    p.add_argument("--out", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "eval-synthetic":
        r = evaluate_on_synthetic(Path(args.run), Path(args.labels), Path(args.out))
        print(json.dumps({k: r[k] for k in ("n_leaflets", "generator_true_aspect_p10_p50_p90",
                                            "true_projection_cos_p10_p50_p90")}))
        for b, s in r["summary"].items():
            print(b, s["n"], {k: v["median_rel_err"] for k, v in s.items() if isinstance(v, dict)})
    else:
        d = estimate_photo(Path(args.measure_csv), Path(args.out))
        print(len(d["leaflets"]), "leaflets")


if __name__ == "__main__":
    main()
