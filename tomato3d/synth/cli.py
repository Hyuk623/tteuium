"""``python -X utf8 -m tomato3d.synth.cli <command> --out build/synthetic_dwarf_tomato_<date>_NN``

Commands (run in order): ``init`` -> ``contours`` -> ``capture`` -> ``contract`` -> ``generate``
-> ``realism`` -> ``preview``. Run inside the ``tomato_synth`` environment (L-Py, PlantGL, bpy,
pillow-heif). ``contract`` must exist before ``generate`` renders anything, and is never
overwritten.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import json
import logging
import shutil
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.synth import GENERATOR_VERSION, ORIGIN

logger = logging.getLogger(__name__)

#: Read-only real inputs (project-relative). Rig poses: one capture.json per rig, as decided
#: with the user on 2026-10-05.
DEFAULT_INPUTS: dict[str, Any] = {
    "capture_json": [
        "build/plants_dwt_test_20261002/plants/dwt_t1/pose_session/edit_session/capture.json",
        "build/plants_dwt_test_20261002/plants/dwt_t2/pose_session/edit_session/capture.json",
        "build/plants_dwt_test_20261002/plants/dwt_t3/pose_session_merged/edit_session/capture.json",
        "build/plants_e2e_20261002/plants/autodwt01/pose_session/edit_session/capture.json",
    ],
    "traits_csv": [
        "build/pipeline_20261001_s8/traits.csv",
        "build/plants_dwt_test_20261002/traits/traits.csv",
        "build/plants_e2e_20261002/traits/traits.csv",
    ],
    "colour_observations_csv": "build/rgb_ratio_batch_20260929/observations.csv",
    "mask_sources_json": "build/rgb_ratio_batch_20260929/separability.json",
    "visibility_decisions_glob": "~/Downloads/cross_view_decisions_dwt_*.json",
    "p3_engine": ["tools/probabilistic_compound_growth.py", "tools/compound_growth.py"],
}
HEIGHT_SPREAD_MAX_CM = "height_spread_max_cm"


def _sha256(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _write_json(path: Path, value: Any) -> None:
    from tomato3d.synth.pipeline import write_json

    write_json(path, value)


def _board_spec():
    from tomato3d.config import get_settings
    from tomato3d.io.schemas import BoardSpec, load_json_model

    return load_json_model(get_settings().board_spec_path, BoardSpec)


def _manifest_add(out: Path, group: str, paths: list[Path], note: str | None = None) -> None:
    path = out / "inputs_manifest.json"
    data = _read_json(path) if path.exists() else dict(origin=ORIGIN, generator_version=GENERATOR_VERSION, groups={})
    data["groups"][group] = dict(recorded_at=_now(), note=note,
                                 files={Path(p).as_posix(): _sha256(p) for p in paths})
    _write_json(path, data)


def _mask_sources(inputs: dict[str, Any]) -> dict[str, Path]:
    sources = _read_json(Path(inputs["mask_sources_json"]))["sources"]
    return {k: Path(v["export"].replace("\\", "/")) for k, v in sources.items()}


def _decision_files(inputs: dict[str, Any]) -> list[Path]:
    pattern = Path(inputs["visibility_decisions_glob"]).expanduser()
    return sorted(pattern.parent.glob(pattern.name))


# --------------------------------------------------------------------------- init
def cmd_init(args) -> None:
    from tomato3d.calib.board import build_charuco_board
    from tomato3d.synth.camera import load_rig_views
    from tomato3d.synth.config import apply_measured_range, load_generator_config, write_generator_config, constant
    from tomato3d.synth.images import imwrite
    from tomato3d.synth.scene import pot_center_board_mm

    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    inputs = dict(DEFAULT_INPUTS)
    _write_json(out / "inputs.json", inputs)
    cfg = load_generator_config()
    cfg["generator_version"] = GENERATOR_VERSION
    diam = []
    for p in inputs["traits_csv"]:
        with Path(p).open(encoding="utf-8-sig", newline="") as f:
            diam += [float(r["stem_diameter_mm"]) for r in csv.DictReader(f) if r.get("stem_diameter_mm")]
    cfg = apply_measured_range(cfg, "stem_radius_mm", min(diam) / 2, max(diam) / 2,
                               {p: _sha256(Path(p)) for p in inputs["traits_csv"]},
                               "S8 stem_diameter_mm min-max over listed traits.csv files, halved")
    import pandas as pd

    obs = pd.read_csv(inputs["colour_observations_csv"])
    leaf = obs[(obs["cls"] == "leaflet") & (obs["variant"] == "original")]
    ref = {inputs["colour_observations_csv"]: _sha256(Path(inputs["colour_observations_csv"]))}
    for ch in ("r", "g"):
        lo, hi = np.percentile(leaf[f"{ch}_med"], [10, 90])
        cfg = apply_measured_range(cfg, f"leaf_chroma_{ch}", lo, hi, ref,
                                   f"p10-p90 of leaflet {ch}_med chromaticity (cls=leaflet, variant=original, "
                                   f"n={len(leaf)}), rig photos")
    write_generator_config(cfg, out / "generator_config.json")
    spec = _board_spec()
    board = build_charuco_board(spec)
    ppm = constant(cfg, "board_texture_px_per_mm")
    tex = board.generateImage((int(spec.board_width_mm * ppm), int(spec.board_height_mm * ppm)), marginSize=0,
                              borderBits=1)
    imwrite(out / "board_texture.png", tex)
    pot = pot_center_board_mm(spec)
    look = np.array([pot[0], pot[1], 0.0])
    views = []
    for c in inputs["capture_json"]:
        views += [v.__dict__ for v in load_rig_views(Path(c), constant(cfg, "max_pose_reprojection_px"), look)]
    _write_json(out / "views.json", dict(look_at_board_mm=look.tolist(), views=views))
    from tomato3d.config import get_settings

    _manifest_add(out, "rig_capture_json", [Path(p) for p in inputs["capture_json"]], "camera intrinsics + solved poses")
    _manifest_add(out, "traits_csv", [Path(p) for p in inputs["traits_csv"]], "S8 trait ranges (stem, gate)")
    _manifest_add(out, "colour", [Path(inputs["colour_observations_csv"])], "leaflet chromaticity")
    _manifest_add(out, "board_spec", [get_settings().board_spec_path], "board geometry/texture")
    _manifest_add(out, "p3_engine", [Path(p) for p in inputs["p3_engine"]], "imported read-only")
    _manifest_add(out, "generator_template", [Path(__file__).with_name("generator_config_template.json"),
                                              Path(__file__).with_name("compound_leaf.lpy")], "generator code data")
    n_top = sum(1 for v in views if v["elevation_deg"] >= constant(cfg, "top_view_min_elevation_deg"))
    print(json.dumps(dict(status="init", out=str(out), views=len(views), top_views=n_top)))


# --------------------------------------------------------------------------- contours
def cmd_contours(args) -> None:
    from tomato3d.synth.config import constant, load_generator_config
    from tomato3d.synth.contours import build_library, preview_sheet

    out = Path(args.out)
    cfg = load_generator_config(out / "generator_config.json")
    inputs = _read_json(out / "inputs.json")
    sources = _mask_sources(inputs)
    decisions = _decision_files(inputs)
    excluded = list(args.exclude_plants or [])
    opt = lambda k, d: cfg.get("constants", {}).get(k, {}).get("value", d)     # absent = pre-G.2 behaviour
    lib, audit = build_library(sources, decisions, n_points=int(constant(cfg, "contour_points")),
                               max_contact=constant(cfg, "contour_max_contact"),
                               min_solidity=constant(cfg, "contour_min_solidity"),
                               min_dominant=constant(cfg, "contour_min_dominant_fraction"),
                               downscale=int(constant(cfg, "contour_mask_downscale")), exclude_plants=excluded,
                               use_human_visibility=bool(opt("contour_use_human_visibility", True)),
                               exclude_border=bool(opt("contour_exclude_border", True)))
    _write_json(out / "leaflet_contours.json", dict(
        origin="real_masks_normalised", created_at=_now(), sources={k: str(v) for k, v in sources.items()},
        decision_files=[str(d) for d in decisions], excluded_plants=excluded,
        counts=dict(total=len(lib), human_full=sum(r["visibility_source"] == "human_full" for r in lib),
                    geometric_proxy=sum(r["visibility_source"] == "geometric_proxy" for r in lib),
                    geometric_only=sum(r["visibility_source"] == "geometric_only" for r in lib)),
        capture_contours="pending: Addendum A top/side photos need leaflet segmentation (SAM2 not installed "
                         "locally); 18-view reviewed masks are the only source in this run",
        contours=lib))
    with (out / "contour_audit.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(audit[0]))
        w.writeheader()
        w.writerows(audit)
    preview_sheet(lib, out / "contours_preview.png")
    _manifest_add(out, "mask_exports", [p / "accepted.json" for p in sources.values()], "reviewed leaflet masks")
    _manifest_add(out, "visibility_decisions", decisions, "human cross-view visibility answers")
    print(json.dumps(dict(status="contours", total=len(lib), audit=len(audit))))


# --------------------------------------------------------------------------- capture
def cmd_capture(args) -> None:
    from tomato3d.config import get_settings
    from tomato3d.synth.capture import capture_status, discover_sessions, height_from_readings, read_heic_rgb, validate_session
    from tomato3d.synth.config import constant, load_generator_config, write_generator_config
    from tomato3d.synth.images import imwrite
    import cv2

    out = Path(args.out)
    cfg = load_generator_config(out / "generator_config.json")
    raw = get_settings().raw_dir
    sessions = [validate_session(s) for s in discover_sessions(raw)]
    status = capture_status(sessions)
    test_plants = sorted(args.test_plants or [])
    summary = []
    photos = []
    prev_dir = out / "capture_previews"
    for s in sessions:
        use = "test_set" if s["plant_id"] in test_plants else "train_priors"
        summary.append(dict(plant_id=s["plant_id"], session_id=s["session_id"], status=s["status"], use=use,
                            n_rows_ok=len(s["rows"]), problems=s["problems"], notes=s["notes"],
                            azimuth_basis=s["azimuth_basis"]))
        for r in s["rows"]:
            p = Path(s["session_dir"]) / r["photo_file"]
            photos.append(p)
            if args.previews:
                target = prev_dir / s["plant_id"] / f"{r['stem']}.jpg"
                if not target.exists():
                    target.parent.mkdir(parents=True, exist_ok=True)
                    rgb = read_heic_rgb(p)
                    scale = args.preview_px / float(max(rgb.shape[:2]))
                    small = cv2.resize(rgb, None, fx=scale, fy=scale, interpolation=cv2.INTER_AREA)
                    imwrite(target, cv2.cvtColor(small, cv2.COLOR_RGB2BGR))
    heights = []
    if args.height_readings:
        with Path(args.height_readings).open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        for plant in sorted({r["plant_id"] for r in rows}):
            h = height_from_readings([r for r in rows if r["plant_id"] == plant], constant(cfg, HEIGHT_SPREAD_MAX_CM))
            sess = next((s for s in summary if s["plant_id"] == plant), {})
            soil = sess.get("notes", {}).get("soil_depth_below_rim_cm")
            heights.append(dict(plant_id=plant, use=sess.get("use"), method=rows[0].get("method", ""), **h,
                                soil_depth_below_rim_cm=float(soil) if soil else None,
                                height_above_soil_cm=(h["height_above_rim_cm"] + float(soil))
                                if soil and h["height_above_rim_cm"] is not None else None))
        _manifest_add(out, "capture_height_readings", [Path(args.height_readings)], "ruler readings from level_* photos")
    _write_json(out / "capture_sessions.json", dict(status=status, raw_dir=str(raw), test_plants=test_plants,
                                                    sessions=summary, heights=heights, validated_at=_now()))
    if cfg["compound_capture_status"] != status:
        cfg.setdefault("history", []).append(dict(changed_at=_now(), name="compound_capture_status",
                                                  old=cfg["compound_capture_status"], new=status,
                                                  reason=f"{len(sessions)} generator capture sessions validated"))
        cfg["compound_capture_status"] = status
        write_generator_config(cfg, out / "generator_config.json")
    if photos:
        _manifest_add(out, "generator_capture_photos", photos + [Path(s["session_dir"]) / "generator_capture.csv"
                                                                 for s in sessions], "Addendum A originals (read-only)")
    print(json.dumps(dict(status=status, sessions=len(sessions), photos=len(photos), heights=len(heights))))


# --------------------------------------------------------------------------- contract
def _pins(out: Path, cfg: dict) -> dict:
    """Addendum G.2 A4: hashes of the contour pool and texture bank a contract renders from."""
    pins = dict(pins_required=True, leaflet_contours_sha256=_sha256(out / "leaflet_contours.json"))
    from tomato3d.synth.config import input_path

    bank = cfg.get("constants", {}).get("leaf_texture_bank")
    if bank:
        pins["texture_bank_sha256"] = _sha256(input_path(bank["value"]))
    return pins


def cmd_contract(args) -> None:
    from tomato3d.synth.config import config_hash, load_generator_config
    from tomato3d.synth.realism import real_reference

    out = Path(args.out)
    path = out / "stage1_contract.json"
    if path.exists():
        raise SystemExit(f"{path} exists; contract criteria may not be changed")
    cfg = load_generator_config(out / "generator_config.json")
    inputs = _read_json(out / "inputs.json")
    real = real_reference([Path(p) for p in inputs["traits_csv"]], _mask_sources(inputs), args.size, 3024)
    caps = _read_json(out / "capture_sessions.json") if (out / "capture_sessions.json").exists() else {}
    criteria = [
        dict(id="C1_height", kind="gate", synthetic_statistic="median_height_mm", low=real["height_mm"]["min"],
             high=real["height_mm"]["max"], unit="mm", rule="synthetic median plant height above soil inside real min-max",
             real_source="S8 hull_height_mm"),
        dict(id="C2_envelope", kind="gate", synthetic_statistic="median_envelope_area_cm2",
             low=real["envelope_area_cm2"]["min"], high=real["envelope_area_cm2"]["max"], unit="cm2",
             rule="synthetic median convex top envelope inside real hull_footprint min-max (definitions differ: "
                  "convex envelope vs occupancy footprint)", real_source="S8 hull_footprint_cm2"),
        dict(id="C3_leaflets_per_photo", kind="gate", synthetic_statistic="median_leaflets_per_photo",
             low=real["leaflets_per_photo"]["min"], high=real["leaflets_per_photo"]["max"], unit="count",
             rule=f"visible leaflets with >= {args.min_visible_px} px per view, median inside real min-max",
             real_source="accepted reviewed leaflet masks per photo"),
        dict(id="C4_visible_leaflet_area", kind="gate", synthetic_statistic="median_visible_leaflet_area_px",
             low=real["visible_leaflet_area_px"]["p10"], high=real["visible_leaflet_area_px"]["p90"],
             unit=f"px at {args.size}", rule="median visible leaflet area inside real p10-p90",
             real_source="accepted mask areas rescaled"),
        dict(id="C5_occlusion", kind="report_only", synthetic_statistic="median_occlusion_fraction", low=None,
             high=None, unit="fraction", rule="reported only: real photos have no amodal ground truth"),
        dict(id="C6_detector_ap50", kind="gate", synthetic_statistic="detector_leaflet_ap50", low=0.59, high=0.92,
             unit="AP50", rule="existing detector on synthetic photos within +-0.15 of the real plant-held-out "
                               "0.74-0.77 (handoff Stage 1 section 5)", real_source="handoff value"),
        dict(id="C7_sam_iou", kind="gate", synthetic_statistic="sam_leaflet_iou", low=0.72, high=0.96, unit="IoU",
             rule="existing SAM on synthetic photos within +-0.10 of the real 0.82-0.86 (handoff Stage 1 section 5)",
             real_source="handoff value"),
        dict(id="C8_top_view_layout", kind="report_only", synthetic_statistic="median_envelope_area_cm2",
             low=None, high=None, unit="cm2", rule="Addendum A: compared with generator-capture top views; does not "
                                                   "change the gate"),
    ]
    contract = dict(
        schema="synth-stage1-contract-1", declared_at=_now(), declared_before_rendering=True, origin=ORIGIN,
        generator_version=GENERATOR_VERSION, generator_config_sha256=_sha256(out / "generator_config.json"),
        generator_config_hash=config_hash(cfg), scenes=args.scenes, pilot_scenes=args.pilot, seed_base=args.seed_base,
        views_per_scene=dict(top=args.views_top, ring=args.views_ring), resolution_px=args.size,
        cycles_samples=args.samples, min_visible_px=args.min_visible_px,
        **(dict(scene_seeds={f"scene_{args.pilot + k:04d}": args.fresh_seed_base + k for k in range(args.fresh_scenes)},
                fresh_seed_base=args.fresh_seed_base) if args.fresh_scenes else {}),
        test_plants=caps.get("test_plants", []), compound_capture_status=cfg["compound_capture_status"],
        real_reference=real, criteria=criteria, **_pins(out, cfg),
        pass_rule="gate passes when every 'gate' criterion passes; pending criteria (C6/C7 need detector/SAM "
                  "inference) keep the gate pending, never passed")
    _write_json(path, contract)
    print(json.dumps(dict(status="contract", path=str(path))))


# --------------------------------------------------------------------------- amend
def cmd_amend(args) -> None:
    """Append a pre-declared step rule (Addendum B) to contract_amendments.json; never edits the contract."""
    out = Path(args.out)
    if not (out / "stage1_contract.json").exists():
        raise SystemExit("declare stage1_contract.json first")
    content = _read_json(Path(args.file))
    path = out / "contract_amendments.json"
    data = _read_json(path) if path.exists() else dict(contract_sha256=_sha256(out / "stage1_contract.json"),
                                                        amendments=[])
    if any(a["step"] == args.step for a in data["amendments"]):
        raise SystemExit(f"step {args.step} already declared; declarations are not changed")
    blob = json.dumps(content, sort_keys=True).encode("utf-8")
    data["amendments"].append(dict(step=args.step, declared_at=_now(), content=content,
                                   content_sha256=hashlib.sha256(blob).hexdigest()))
    _write_json(path, data)
    print(json.dumps(dict(status="amended", step=args.step)))


# --------------------------------------------------------------------------- generate
def _load_views(out: Path):
    from tomato3d.synth.camera import RigView

    data = _read_json(out / "views.json")
    return [RigView(**{k: (tuple(map(tuple, v)) if k == "camera_matrix" else tuple(v) if isinstance(v, list) else v)
                       for k, v in d.items()}) for d in data["views"]]


def cmd_generate(args) -> None:
    import cv2

    from tomato3d.synth import pipeline as pl
    from tomato3d.synth import render_blender as rb
    from tomato3d.synth.config import constant, load_generator_config, make_rng
    from tomato3d.synth.contours import load_library
    from tomato3d.synth.images import imwrite
    from tomato3d.synth.scene import pot_center_board_mm

    out = Path(args.out)
    contract_path = out / "stage1_contract.json"
    if not contract_path.exists():
        raise SystemExit("stage1_contract.json must be declared before rendering (run 'contract')")
    contract = _read_json(contract_path)
    cfg = load_generator_config(out / "generator_config.json")
    if _sha256(out / "generator_config.json") != contract["generator_config_sha256"] and not args.allow_config_change:
        raise SystemExit("generator_config.json changed after the contract was declared")
    # Addendum G.2 A4: what the contract pins must be what is rendered
    pins = dict(leaflet_contours_sha256=out / "leaflet_contours.json")
    bank_entry = cfg.get("constants", {}).get("leaf_texture_bank")
    if bank_entry:
        from tomato3d.synth.config import input_path

        pins["texture_bank_sha256"] = input_path(bank_entry["value"])
    for key, path in pins.items():
        if key in contract and _sha256(path) != contract[key]:
            raise SystemExit(f"{path} differs from the {key} declared in the contract")
        if contract.get("pins_required") and key not in contract:
            raise SystemExit(f"contract declares pins_required but has no {key}")
    contours, contour_records = load_library(out / "leaflet_contours.json")
    contour_ids = [r.get("mask_id") for r in contour_records]
    scene_seeds = contract.get("scene_seeds", {})
    spec = _board_spec()
    views = _load_views(out)
    gc = pl.GeometryCache(cfg, contract["resolution_px"])
    pot = pot_center_board_mm(spec)
    manifest = out / "manifest.jsonl"
    params_csv = out / "scene_params.csv"
    look = {k: cfg["constants"][k]["value"] for k in ("key_light_size_m", "bump_strength", "bump_distance_m",
                                                      "leaf_specular", "leaf_roughness")
            if k in cfg.get("constants", {})}
    timing = out / "timing.jsonl"
    for i in range(args.start, args.start + args.count):
        scene_id = f"scene_{i:04d}"
        seed = int(scene_seeds.get(scene_id, contract["seed_base"] + i))
        scene_dir = out / "scenes" / scene_id
        if (scene_dir / "DONE").exists():
            continue
        t0 = time.time()
        try:
            scene = pl.build_scene(cfg, seed, scene_id, contours, spec, scene_dir, contour_ids)
        except pl.SceneRejected as exc:
            with (out / "rejected_scenes.jsonl").open("a", encoding="utf-8") as f:
                f.write(json.dumps(dict(scene_id=scene_id, seed=seed, rejections=exc.rejections)) + "\n")
            continue
        shutil.rmtree(scene_dir / "work", ignore_errors=True)
        sel = pl.select_views(views, cfg, seed, contract["views_per_scene"]["top"], contract["views_per_scene"]["ring"])
        n_top = contract["views_per_scene"]["top"]
        if args.rgb == "local":
            rb.build_scene(scene["parts"], scene["scene_params"], (out / "board_texture.png").resolve(),
                           samples=contract["cycles_samples"],
                           backdrop_distance_mm=constant(cfg, "backdrop_distance_mm"), pot_center_mm=pot, look=look)
        rows, t_raster, t_render, job_views = [], 0.0, 0.0, []
        for k, view in enumerate(sel):
            geom = gc.get(view)
            t1 = time.time()
            vdir, layers = pl.write_view_layers(scene, view, k, geom)
            t_raster += time.time() - t1
            if args.rgb == "export":
                job_views.append(dict(name=vdir.name, K_render=geom.K_render, size=geom.render_size_px,
                                      R=view.rotation, t=view.translation))
            if args.rgb == "local":
                t1 = time.time()
                canvas = vdir / "render_canvas.png"
                img = rb.render_view(geom.K_render, geom.render_size_px, view.rotation, view.translation, canvas)
                rgb = geom.warp(img, nearest=False, fill=0)
                rgb = rb.post_process(rgb, scene["scene_params"], make_rng(seed, "post", k))
                imwrite(vdir / "rgb.png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
                canvas.unlink(missing_ok=True)
                t_render += time.time() - t1
            row = pl.manifest_row(scene, view, vdir, out, view_kind="top" if k < n_top else "ring",
                                  rgb_written=args.rgb != "none")
            row["rgb_status"] = dict(local="rendered_local", export="pending_remote", none="not_rendered")[args.rgb]
            rows.append(row)
        if args.rgb == "export":
            from tomato3d.synth.render_remote import export_job

            export_job(scene, job_views, samples=contract["cycles_samples"],
                       backdrop_distance_mm=constant(cfg, "backdrop_distance_mm"), pot_center_mm=pot,
                       board_texture=out / "board_texture.png", look=look)
        with manifest.open("a", encoding="utf-8") as f:
            for r in rows:
                f.write(json.dumps(r) + "\n")
        new = not params_csv.exists()
        flat = dict(scene_id=scene_id, seed=seed, parameter_hash=scene["parameter_hash"], origin=ORIGIN,
                    n_compounds=len(scene["graph"]["compounds"]), n_leaflets=len(scene["index"]),
                    n_rejections=len(scene["rejections"]),
                    **{f"plant.{k}": v for k, v in scene["graph"]["params"].items()},
                    **{f"scene.{k}": v for k, v in scene["scene_params"].items()})
        with params_csv.open("a", encoding="utf-8", newline="") as f:
            w = csv.DictWriter(f, fieldnames=list(flat))
            if new:
                w.writeheader()
            w.writerow(flat)
        dt = time.time() - t0
        with timing.open("a", encoding="utf-8") as f:
            f.write(json.dumps(dict(scene_id=scene_id, seconds=round(dt, 1), raster_s=round(t_raster, 1),
                                    render_s=round(t_render, 1), views=len(sel))) + "\n")
        (scene_dir / "DONE").write_text(_now(), encoding="utf-8")
        logger.info("%s done in %.1f s (raster %.1f, render %.1f)", scene_id, dt, t_raster, t_render)
        print(json.dumps(dict(scene=scene_id, seconds=round(dt, 1))), flush=True)


# --------------------------------------------------------------------------- finalize
def cmd_finalize(args) -> None:
    """Warp remotely rendered canvases with the mask map, post-process, mark manifest rows."""
    import cv2

    from tomato3d.synth import pipeline as pl
    from tomato3d.synth import render_blender as rb
    from tomato3d.synth.config import load_generator_config, make_rng
    from tomato3d.synth.images import imread, imwrite

    out, renders = Path(args.out), Path(args.renders)
    cfg = load_generator_config(out / "generator_config.json")
    contract = _read_json(out / "stage1_contract.json")
    views = {v.view_id: v for v in _load_views(out)}
    gc = pl.GeometryCache(cfg, contract["resolution_px"])
    path = out / "manifest.jsonl"
    rows = [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]
    done = missing = 0
    for r in rows:
        if r.get("rgb_status") != "pending_remote":
            continue
        vdir = out / Path(r["visible_mask"]).parent
        canvas = renders / r["scene_id"] / f"{vdir.name}.png"
        if not canvas.exists():
            missing += 1
            continue
        sp = _read_json(out / "scenes" / r["scene_id"] / "scene_params.json")
        geom = gc.get(views[r["view_id"]])
        img = cv2.cvtColor(imread(canvas, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
        if (img.shape[1], img.shape[0]) != tuple(geom.render_size_px):
            raise SystemExit(f"{canvas}: canvas size {img.shape[:2]} != render size {geom.render_size_px}")
        rgb = rb.post_process(geom.warp(img, nearest=False, fill=0), sp, make_rng(r["seed"], "post", int(vdir.name[:2])))
        imwrite(vdir / "rgb.png", cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR))
        r["rgb_status"] = "rendered_remote"
        r["rgb_canvas_sha256"] = _sha256(canvas)
        done += 1
    path.write_text("".join(json.dumps(r) + "\n" for r in rows), encoding="utf-8")
    print(json.dumps(dict(finalized=done, missing=missing)))


# --------------------------------------------------------------------------- realism
def cmd_realism(args) -> None:
    from tomato3d.synth.realism import evaluate_gate, plant_stats, view_stats

    out = Path(args.out)
    contract = _read_json(out / "stage1_contract.json")
    rows = [json.loads(l) for l in (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    scenes = sorted({r["scene_id"] for r in rows})
    if args.scenes:
        scenes = [s for s in scenes if s in set(args.scenes)]
    plants, views = [], []
    for s in scenes:
        sdir = out / "scenes" / s
        g = _read_json(sdir / "plant_graph.json")
        plants.append(dict(scene_id=s, **plant_stats(g, obj_path=sdir / "meshes.obj")))
        for r in rows:
            if r["scene_id"] == s:
                vs = view_stats(out / Path(r["visible_mask"]).parent, contract["min_visible_px"])
                views.append(dict(scene_id=s, view_id=r["view_id"], view_kind=r["view_kind"], **vs))
    areas = [a for v in views for a in v["visible_leaflet_area_px"]]
    occl = [o for v in views for o in v["occlusion_fraction"]]
    synthetic = dict(
        n_scenes=len(plants), n_views=len(views),
        median_height_mm=float(np.median([p["height_mm"] for p in plants])) if plants else None,
        median_envelope_area_cm2=float(np.median([p["envelope_area_cm2"] for p in plants])) if plants else None,
        median_leaflets_per_photo=float(np.median([v["leaflets_per_photo"] for v in views])) if views else None,
        median_visible_leaflet_area_px=float(np.median(areas)) if areas else None,
        median_occlusion_fraction=float(np.median(occl)) if occl else None,
        fully_hidden_leaflet_views=int(sum(v["fully_hidden"] for v in views)),
        detector_leaflet_ap50=None, sam_leaflet_iou=None)
    ev_path = out / (args.evaluation or "evaluation.json")
    if ev_path.exists():
        ev = _read_json(ev_path)
        if set(ev["scenes"]) == set(scenes):
            synthetic.update(detector_leaflet_ap50=ev["detector"]["ap50"], sam_leaflet_iou=ev["sam"]["median"],
                             evaluation_file=ev_path.name)
        else:
            synthetic["evaluation_note"] = f"{ev_path.name} covers other scenes; C6/C7 left pending"
    gate = evaluate_gate(contract, synthetic)
    caps = _read_json(out / "capture_sessions.json") if (out / "capture_sessions.json").exists() else {}
    report = dict(origin=ORIGIN, evaluated_at=_now(), scenes=scenes, synthetic=synthetic, gate=gate,
                  addendum_capture_heights=caps.get("heights", []),
                  per_plant=plants)
    name = args.name or "realism_report"
    _write_json(out / f"{name}.json", report)
    with (out / f"{name}.csv").open("w", encoding="utf-8", newline="") as f:
        w = csv.writer(f)
        w.writerow(["criterion", "kind", "statistic", "value", "low", "high", "status"])
        for c in gate["criteria"]:
            w.writerow([c["id"], c["kind"], c["synthetic_statistic"], c["value"], c["low"], c["high"], c["status"]])
    print(json.dumps(dict(overall=gate["overall"], **{c["id"]: c["status"] for c in gate["criteria"]})))


# --------------------------------------------------------------------------- preview
def cmd_preview(args) -> None:
    import cv2

    from tomato3d.synth.images import imread, imwrite

    out = Path(args.out)
    rows = [json.loads(l) for l in (out / "manifest.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    pal = np.random.default_rng(0).integers(40, 255, (65536, 3)).astype(np.uint8)
    pal[0] = 0
    tiles = []
    for s in args.scenes:
        srows = [r for r in rows if r["scene_id"] == s][: args.views]
        for r in srows:
            vdir = out / Path(r["visible_mask"]).parent
            rgb = imread(out / r["rgb"], cv2.IMREAD_COLOR) if r.get("rgb") else np.zeros((512, 512, 3), np.uint8)
            vis = imread(vdir / "visible_mask.png")
            vis_c = pal[vis]
            amodal = np.zeros_like(rgb)
            best, best_occ = None, -1.0
            for f in sorted((vdir / "amodal").glob("*.png")):
                m = imread(f) > 0
                occ = 1 - (m & (vis > 0)).sum() / max(1, m.sum())
                if 0.2 < occ < 0.95 and occ > best_occ:
                    best, best_occ = m, occ
            amodal[:] = (rgb * 0.35).astype(np.uint8)
            if best is not None:
                amodal[best] = (0, 0, 255)
                edge = cv2.Canny((vis > 0).astype(np.uint8) * 255, 50, 150) > 0
                amodal[edge] = (255, 255, 255)
            row = np.hstack([rgb, vis_c, amodal])
            cv2.putText(row, f"{s} {r['view_id']} {r['view_kind']}", (6, 18), cv2.FONT_HERSHEY_SIMPLEX, 0.5,
                        (255, 255, 255), 1, cv2.LINE_AA)
            tiles.append(cv2.resize(row, None, fx=args.scale, fy=args.scale, interpolation=cv2.INTER_AREA))
    imwrite(out / f"{args.name}.jpg", np.vstack(tiles))
    print(json.dumps(dict(preview=str(out / f"{args.name}.jpg"), tiles=len(tiles))))


def main(argv: list[str] | None = None) -> None:
    from tomato3d.logging_setup import configure_logging

    configure_logging("INFO")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    p = sub.add_parser("init"); p.add_argument("--out", required=True)
    p = sub.add_parser("contours"); p.add_argument("--out", required=True)
    p.add_argument("--exclude-plants", nargs="*", default=[])
    p = sub.add_parser("capture"); p.add_argument("--out", required=True)
    p.add_argument("--test-plants", nargs="*", default=[]); p.add_argument("--height-readings")
    p.add_argument("--previews", action="store_true"); p.add_argument("--preview-px", type=int, default=1600)
    p = sub.add_parser("contract"); p.add_argument("--out", required=True)
    p.add_argument("--scenes", type=int, required=True); p.add_argument("--pilot", type=int, required=True)
    p.add_argument("--seed-base", type=int, required=True); p.add_argument("--views-top", type=int, required=True)
    p.add_argument("--fresh-seed-base", type=int, help="seed base for extra scenes after the pilot (Addendum G.2: 10 fresh seeds)")
    p.add_argument("--fresh-scenes", type=int, default=0)
    p.add_argument("--views-ring", type=int, required=True); p.add_argument("--size", type=int, required=True)
    p.add_argument("--samples", type=int, required=True); p.add_argument("--min-visible-px", type=int, required=True)
    p = sub.add_parser("amend"); p.add_argument("--out", required=True); p.add_argument("--step", required=True)
    p.add_argument("--file", required=True)
    p = sub.add_parser("generate"); p.add_argument("--out", required=True)
    p.add_argument("--start", type=int, default=0); p.add_argument("--count", type=int, required=True)
    p.add_argument("--rgb", choices=("local", "export", "none"), default="local",
                   help="local: Blender here; export: write render_job/ for a GPU host; none: masks only")
    p.add_argument("--allow-config-change", action="store_true")
    p = sub.add_parser("finalize"); p.add_argument("--out", required=True); p.add_argument("--renders", required=True)
    p = sub.add_parser("realism"); p.add_argument("--out", required=True)
    p.add_argument("--scenes", nargs="*"); p.add_argument("--name"); p.add_argument("--evaluation")
    p = sub.add_parser("preview"); p.add_argument("--out", required=True); p.add_argument("--scenes", nargs="+")
    p.add_argument("--views", type=int, default=4); p.add_argument("--scale", type=float, default=0.5)
    p.add_argument("--name", default="preview")
    args = parser.parse_args(argv)
    dict(init=cmd_init, contours=cmd_contours, capture=cmd_capture, contract=cmd_contract, generate=cmd_generate,
         finalize=cmd_finalize, amend=cmd_amend, realism=cmd_realism, preview=cmd_preview)[args.command](args)


if __name__ == "__main__":
    main()
