"""T2 - paired synthetic dataset: top-view and side-view MASKS + 3D truth per scene, no Cycles render.

Spec: ``handoff/CLAUDE_CODE_CLI_PROMPT_TOP_TO_3D_2026-10-12.md`` T2. The geometry model is trained on masks, not
RGB, so only the mask layers are rasterised (the label export proved that re-rasterising ``render_job/parts.npz``
reproduces the stored leaflet layer exactly). Every part gets its own raster instance
(:func:`tomato3d.synth.labels_json.instance_plan`), so one pass per view yields leaflet, compound and shoot masks,
and amodal masks give occluded organs a complete target. The same organ keeps the same instance id in every view of
a scene - top/side pairs need no matching.

GATE: training data from an uncalibrated generator teaches the wrong geometry. :func:`export_pairs` refuses unless
the T0 calibration (``tomato3d.topview.calibration``) says ``t2_gate.open``. ``smoke=True`` exists only to test the
code path: its header says ``not_for_training: true`` and nothing downstream may train on it.
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "synth-topside-pairs-1"


def _sha(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def _rotate_z(v: np.ndarray, deg: float) -> np.ndarray:
    a = math.radians(deg)
    R = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    return R @ np.asarray(v, float)


def leaflet_truth(part: dict[str, Any], leaf: dict[str, Any], rotation_deg: float) -> dict[str, Any]:
    """3D truth of one leaflet: one-sided mesh area, generator midrib length, base->tip chord, mean normal.

    Board frame (+Z up). ``chord_elevation_deg`` > 0 means the tip is above the base.
    """
    v, f = np.asarray(part["vertices"], float), np.asarray(part["faces"], int)
    a, b, c = (v[f[:, k]] for k in range(3))
    cr = np.cross(b - a, c - a)
    area = 0.5 * float(np.linalg.norm(cr, axis=1).sum())
    n = cr.sum(axis=0)
    n = n / max(np.linalg.norm(n), 1e-12)
    if n[2] < 0:
        n = -n                                     # two-sided blade: report the upward-facing normal
    heading = _rotate_z(leaf["heading"], rotation_deg)
    rel = v - v.mean(axis=0)
    base = v[np.argmin(rel @ heading)]
    tip = v[np.argmax(rel @ heading)]
    chord = tip - base
    return dict(true_area_mm2=round(area, 4), length_mm=float(leaf["length_mm"]),
                chord_mm=[round(float(x), 4) for x in chord],
                chord_elevation_deg=round(math.degrees(math.atan2(chord[2], math.hypot(chord[0], chord[1]))), 3),
                normal=[round(float(x), 5) for x in n],
                normal_tilt_deg=round(math.degrees(math.acos(min(1.0, abs(float(n[2]))))), 3),
                bend_deg=leaf["bend_deg"], roll_deg=leaf["roll_deg"], twist_deg=leaf["twist_deg"])


def _top_cameras(seed: int, top: dict[str, Any]) -> list[dict[str, Any]]:
    """Top cameras of one scene. ``measured_poses`` (preferred): each view draws one real top pose (distance from
    the rim-plane pot centre, tilt from vertical) - see :func:`measured_top_block`. Otherwise the older single
    elevation +- jitter at one distance (declared assumption)."""
    from tomato3d.synth.config import make_rng

    out = []
    poses = top.get("measured_poses")
    for k in range(int(top["n_views"])):
        rng = make_rng(seed, "topcam", k)
        azimuth = float(rng.uniform(-180.0, 180.0))
        if poses:
            i = int(rng.integers(len(poses)))
            out.append(dict(k=k, camera_azimuth_deg=azimuth, elevation_deg=90.0 - float(poses[i]["tilt_deg"]),
                            distance_mm=float(poses[i]["distance_mm"]), pose_source=poses[i]["source"]))
        else:
            out.append(dict(k=k, camera_azimuth_deg=azimuth,
                            elevation_deg=float(top["elevation_deg"] + rng.uniform(-top["elevation_jitter_deg"],
                                                                                    top["elevation_jitter_deg"])),
                            distance_mm=float(top["distance_mm"])))
    return out


def _top_target(graph: dict[str, Any], params: dict[str, Any], rule: dict[str, Any]) -> np.ndarray:
    """``{"rim_centre": true}`` = the pot centre on the rim plane (what the measured distance refers to)."""
    from tomato3d.synth.sideview import scene_target_mm

    if rule.get("rim_centre"):
        c = graph["placement"]["pot_center_board_mm"]
        return np.array([c[0], c[1], float(params["pot_height_mm"])], float)
    return scene_target_mm(graph, rule)


def measured_top_block(pose_files: list[Path], basis: str, n_views: int) -> dict[str, Any]:
    """Top-camera block from the real top photos' rim poses (``tomato3d.topview.reallink``, status approximate).

    Each pose = (distance camera -> rim-plane pot centre, tilt of the optical axis from vertical) on one focal
    basis. The real camera's look direction is not exactly at the pot centre (the pot is off-centre in the frame);
    the synthetic camera looks at the rim centre - stated, not modelled."""
    poses = []
    for f in pose_files:
        d = json.loads(Path(f).read_text(encoding="utf-8"))
        if d.get("status") == "unavailable":
            continue
        b = d["bases"][basis]
        poses.append(dict(distance_mm=b["pot_centre_distance_mm"], tilt_deg=b["tilt_from_vertical_deg"],
                          axis_ratio_self_check=b["axis_ratio_self_check"], source=Path(f).parent.name))
    if not poses:
        raise SystemExit("no solved top pose - cannot build a measured top camera")
    dist = sorted(p["distance_mm"] for p in poses)
    tilt = sorted(p["tilt_deg"] for p in poses)
    return dict(n_views=int(n_views), measured_poses=poses, look_at_target=dict(rim_centre=True),
                source_kind="measured_approximate", focal_basis=basis,
                source="real top photos: rim homography + EXIF focal (tomato3d.topview.reallink.photo_pose); "
                       "principal point assumed at the image centre; pose status approximate",
                distance_mm_range=[round(dist[0], 1), round(dist[-1], 1)],
                tilt_deg_range=[round(tilt[0], 2), round(tilt[-1], 2)],
                tilt_deg_median=round(float(np.median(tilt)), 2), n_poses=len(poses))


def export_scene(scene_dir: Path, out_dir: Path, geometry: dict[str, Any], gcfg: dict[str, Any],
                 intrinsics: dict[str, Any]) -> dict[str, Any]:
    """Masks + truth of one generated scene (needs ``render_job/parts.npz``)."""
    from tomato3d.synth.labels_json import instance_plan, leaflet_class
    from tomato3d.synth.pipeline import GeometryCache
    from tomato3d.synth.raster import rasterize
    from tomato3d.synth.render_remote import load_parts
    from tomato3d.synth.sideview import camera_center_mm, look_at_view, plan_side_cameras, scene_target_mm

    scene_dir, out_dir = Path(scene_dir), Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)
    job = json.loads((scene_dir / "render_job" / "job.json").read_text(encoding="utf-8"))
    graph = json.loads((scene_dir / "plant_graph.json").read_text(encoding="utf-8"))
    index = json.loads((scene_dir / "leaflet_index.json").read_text(encoding="utf-8"))
    params = json.loads((scene_dir / "scene_params.json").read_text(encoding="utf-8"))
    parts, plan = instance_plan(load_parts(scene_dir / "render_job", job), index)
    rot = float(graph["placement"]["plant_rotation_deg"])
    leaf3d = {l["leaflet_id"]: l for it in graph["interiors"].values() for l in it["leaflets"]}

    instances: dict[str, Any] = {}
    for p in parts:
        i = int(p.get("instance", 0))
        if i == 0:
            continue
        if p["organ"] == "leaflet":
            info = index[str(i)]
            instances[str(i)] = dict(organ="leaflet", leaflet_id=info["leaflet_id"], compound_id=info["compound_id"],
                                     tag=info["tag"], **{"class": leaflet_class(info)},
                                     truth=leaflet_truth(p, leaf3d[info["leaflet_id"]], rot))
        else:
            cid = next((c for c, ids in plan["compounds"].items() if i in ids), None)
            instances[str(i)] = dict(organ=p["organ"], name=p["name"], compound_id=cid)
    compounds = [dict(compound_id=c["compound_id"], rank_from_bottom=c["rank_from_bottom"],
                      instance_ids=sorted(plan["compounds"].get(c["compound_id"], [])),
                      direction_unit_board=[round(float(x), 6) for x in _rotate_z(c["direction_unit"], rot)],
                      rachis_arc_length_mm=c["rachis_arc_length_mm"]) for c in graph["compounds"]]

    K = np.asarray(intrinsics["camera_matrix"], float)
    dist = np.asarray(intrinsics["dist_coeffs"], float)
    size = tuple(int(x) for x in intrinsics["image_size_px"])
    gc = GeometryCache(gcfg, int(geometry["resolution_px"]))
    side_g, top_g = geometry["side"], geometry["top"]
    target_side = scene_target_mm(graph, side_g["look_at_target"])
    target_top = _top_target(graph, params, top_g["look_at_target"])
    seed = int(params["seed"])
    cams = [("top", c, target_top) for c in _top_cameras(seed, top_g)]
    cams += [("side", c, target_side) for c in plan_side_cameras(seed, side_g)]
    views = []
    for kind, c, target in cams:
        name = f"{kind}_{c['k']:02d}"
        centre = camera_center_mm(target, c["camera_azimuth_deg"], c["elevation_deg"], c["distance_mm"])
        view = look_at_view(name, center_mm=centre, target_mm=target, camera_matrix=K, dist_coeffs=dist,
                            image_size_px=size)
        geom = gc.get(view)
        layers = rasterize(parts, view.rotation, view.translation, geom)
        ids = sorted(int(i) for i, m in layers.amodal.items() if m.any())
        np.savez_compressed(out_dir / f"{name}.npz", visible=layers.visible, organ=layers.organ,
                            depth_mm=layers.depth_mm.astype(np.float32), valid=layers.valid,
                            amodal_ids=np.array(ids, np.int32),
                            amodal_packed=np.stack([np.packbits(layers.amodal[i]) for i in ids]) if ids else
                            np.zeros((0, 0), np.uint8))
        views.append(dict(name=name, kind=kind, **{k: v for k, v in c.items() if k != "k"},
                          R=view.rotation.round(9).tolist(), t=view.translation.round(6).tolist(),
                          K_out=np.asarray(geom.K_out).round(6).tolist(), out_size_px=list(geom.out_size_px),
                          visible_instances=int(len(np.unique(layers.visible)) - (0 in layers.visible))))
    truth = dict(scene_id=graph["plant_id"], seed=seed, parameter_hash=params.get("parameter_hash"),
                 plant_rotation_deg=rot, frame="board_mm, +Z up", instances=instances, compounds=compounds,
                 apex_instance_ids=plan["apex"], views=views,
                 npz_layout="visible uint16 instance ids; organ uint8 (raster.ORGAN_CLASSES); depth_mm float32; "
                            "valid bool; amodal_packed[i] = np.packbits(mask of instance amodal_ids[i])")
    (out_dir / "truth.json").write_text(json.dumps(truth, indent=1), encoding="utf-8")
    return dict(scene_id=truth["scene_id"], seed=seed, parameter_hash=truth["parameter_hash"], views=len(views),
                leaflets=sum(v["organ"] == "leaflet" for v in instances.values()))


def export_pairs(scene_dirs: list[Path], out: Path, *, calibration: Path, geometry_path: Path,
                 generator_config: Path, smoke: bool = False) -> dict[str, Any]:
    from tomato3d.synth.config import load_generator_config
    from tomato3d.topview.calibration import calibration_gate

    cal = json.loads(Path(calibration).read_text(encoding="utf-8"))
    is_open, reason = calibration_gate(cal)
    if not is_open and not smoke:
        raise SystemExit(f"T2 gate closed: {reason}. Fill data/records/leaf_bend/ and rerun T0; never invent values.")
    geometry = json.loads(Path(geometry_path).read_text(encoding="utf-8"))
    intr = json.loads(Path(geometry["intrinsics"]).read_text(encoding="utf-8"))
    gcfg = load_generator_config(Path(generator_config))
    out = Path(out)
    scenes = [export_scene(Path(s), out / "scenes" / Path(s).name, geometry, gcfg, intr) for s in scene_dirs]
    header = dict(schema=SCHEMA, not_for_training=not is_open, smoke=bool(smoke),
                  calibration=dict(path=Path(calibration).as_posix(), sha256=_sha(calibration), gate_open=is_open,
                                   gate_reason=reason),
                  geometry=dict(path=Path(geometry_path).as_posix(), sha256=_sha(geometry_path)),
                  generator_config=dict(path=Path(generator_config).as_posix(), sha256=_sha(generator_config)),
                  scene_count=len(scenes), scenes=scenes, rgb="none (masks only)")
    out.mkdir(parents=True, exist_ok=True)
    (out / "dataset.json").write_text(json.dumps(header, indent=1), encoding="utf-8")
    return header


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="T2 paired top/side mask dataset (gated by T0)")
    ap.add_argument("--scenes", nargs="+", required=True, help="generated scene folders with render_job/")
    ap.add_argument("--out", required=True)
    ap.add_argument("--calibration", required=True, help="T0 output JSON")
    ap.add_argument("--geometry", required=True, help="camera geometry JSON (top + side)")
    ap.add_argument("--generator-config", required=True)
    ap.add_argument("--smoke-uncalibrated", action="store_true",
                    help="code-path check only; header says not_for_training")
    args = ap.parse_args(argv)
    h = export_pairs([Path(s) for s in args.scenes], Path(args.out), calibration=Path(args.calibration),
                     geometry_path=Path(args.geometry), generator_config=Path(args.generator_config),
                     smoke=args.smoke_uncalibrated)
    print(json.dumps(dict(scene_count=h["scene_count"], not_for_training=h["not_for_training"],
                          gate=h["calibration"]["gate_reason"])))


if __name__ == "__main__":
    main()
