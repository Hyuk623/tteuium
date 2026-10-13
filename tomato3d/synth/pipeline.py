"""One synthetic scene: plant (P3 + L-Py, with rejection/resampling), views, layers, RGB.

Output layout under ``<out>/scenes/<scene_id>/``::

    plant_graph.json   scene_params.json   leaflet_index.json   meshes.obj   rejections.json
    views/<k>_<session>_<code>/
        rgb.png  visible_mask.png  organ_mask.png  valid_mask.png  depth_mm.npy
        amodal/<compound>_<tag>.png
"""

from __future__ import annotations

import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth.images import imread, imwrite

from tomato3d.synth import GENERATOR_VERSION, ORIGIN
from tomato3d.synth.camera import RenderGeometry, RigView, build_render_geometry
from tomato3d.synth.compound_leaf import CompoundRejected, build_compound
from tomato3d.synth.config import config_hash, constant, make_rng, sample_range
from tomato3d.synth.raster import rasterize
from tomato3d.synth.scene import pot_center_board_mm, scene_parts
from tomato3d.synth.structure import StructureRejected, generate_structure

SCENE_RANGES = ("pot_radius_mm", "pot_height_mm", "soil_depth_below_rim_mm", "plant_rotation_deg",
                "stem_radius_mm", "rachis_radius_mm", "leaf_chroma_r", "leaf_chroma_g", "leaf_srgb_mean",
                "leaf_translucency", "leaf_roughness", "key_light_power_w", "key_light_elevation_deg",
                "key_light_azimuth_deg", "world_light_strength", "image_noise_sigma", "backdrop_gray")


class SceneRejected(RuntimeError):
    def __init__(self, scene_id: str, rejections: list[dict[str, Any]]):
        super().__init__(f"{scene_id}: no valid plant within the attempt budget")
        self.rejections = rejections


def sample_scene_params(cfg: dict[str, Any], seed: int) -> dict[str, float]:
    rng = make_rng(seed, "scene")
    sp = {name: sample_range(rng, cfg, name) for name in SCENE_RANGES}
    sp["wb_gain_r"] = sample_range(rng, cfg, "white_balance_gain")
    sp["wb_gain_b"] = sample_range(rng, cfg, "white_balance_gain")
    return sp


def generate_plant(cfg: dict[str, Any], seed: int, scene_id: str, contours: list[np.ndarray],
                   work_dir: Path) -> tuple[dict[str, Any], dict[str, Any], list[dict[str, Any]]]:
    """Return (plant graph, interiors by compound id, rejection log)."""
    rejections: list[dict[str, Any]] = []
    for attempt in range(int(constant(cfg, "max_scene_attempts"))):
        try:
            graph = generate_structure(cfg, seed, Path(work_dir) / f"p3_attempt_{attempt}", scene_id, attempt)
        except StructureRejected as exc:
            rejections.append(dict(stage="structure", attempt=attempt, reason=str(exc)))
            continue
        interiors: dict[str, Any] = {}
        try:
            for comp in graph["compounds"]:
                interior, rej = build_compound(cfg, comp, contours, seed * 1000 + attempt, scene_id)
                rejections += [dict(stage="compound_contract", scene_attempt=attempt, **r) for r in rej]
                interiors[comp["compound_id"]] = interior
        except CompoundRejected as exc:
            rejections += [dict(stage="compound_contract", scene_attempt=attempt, **r) for r in exc.rejections]
            rejections.append(dict(stage="scene", attempt=attempt, reason=f"compound_budget_exhausted:{exc.compound_id}"))
            continue
        return graph, interiors, rejections
    raise SceneRejected(scene_id, rejections)


def select_views(views: list[RigView], cfg: dict[str, Any], seed: int, n_top: int, n_ring: int) -> list[RigView]:
    """``n_top`` views with elevation >= the top threshold and ``n_ring`` others, without replacement."""
    rng = make_rng(seed, "views")
    top_min = constant(cfg, "top_view_min_elevation_deg")
    top = [v for v in views if v.elevation_deg >= top_min]
    ring = [v for v in views if v.elevation_deg < top_min]
    pick_top = [top[i] for i in rng.choice(len(top), size=min(n_top, len(top)), replace=False)]
    pick_ring = [ring[i] for i in rng.choice(len(ring), size=min(n_ring, len(ring)), replace=False)]
    return pick_top + pick_ring


def write_obj(parts: list[dict[str, Any]], path: Path) -> None:
    lines, offset = ["# synthetic dwarf tomato scene, board frame mm, origin=synthetic"], 1
    for part in parts:
        lines.append(f"o {part['name'].replace('/', '__')}")
        lines += [f"v {x:.4f} {y:.4f} {z:.4f}" for x, y, z in part["vertices"]]
        lines += [f"f {a + offset} {b + offset} {c + offset}" for a, b, c in part["faces"]]
        offset += len(part["vertices"])
    Path(path).write_text("\n".join(lines) + "\n", encoding="utf-8")


def _json_default(o):
    if isinstance(o, np.ndarray):
        return o.tolist()
    if isinstance(o, (np.floating, np.integer)):
        return o.item()
    raise TypeError(type(o))


def write_json(path: Path, value: Any) -> None:
    Path(path).write_text(json.dumps(value, indent=1, default=_json_default) + "\n", encoding="utf-8")


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class GeometryCache:
    """Render geometry per (intrinsics, output size)."""

    def __init__(self, cfg: dict[str, Any], out_size_px: int):
        self.cfg, self.size, self.cache = cfg, out_size_px, {}

    def get(self, view: RigView) -> RenderGeometry:
        key = (view.camera_matrix, view.dist_coeffs, view.image_size_px)
        if key not in self.cache:
            self.cache[key] = build_render_geometry(
                view, self.size, tolerance_px=constant(self.cfg, "distortion_inverse_tolerance_px"),
                iterations=int(constant(self.cfg, "distortion_inverse_iterations")),
                max_canvas_scale=constant(self.cfg, "render_canvas_max_scale"))
        return self.cache[key]


def build_scene(cfg: dict[str, Any], seed: int, scene_id: str, contours: list[np.ndarray], spec,
                scene_dir: Path, contour_ids: list[str | None] | None = None) -> dict[str, Any]:
    """Generate the plant and its meshes; write the scene-level files."""
    scene_dir = Path(scene_dir)
    scene_dir.mkdir(parents=True, exist_ok=True)
    graph, interiors, rejections = generate_plant(cfg, seed, scene_id, contours, scene_dir / "work")
    sp = sample_scene_params(cfg, seed)
    parts, index = scene_parts(graph, interiors, contours, cfg, sp, spec, contour_ids)
    soil_z = sp["pot_height_mm"] - sp["soil_depth_below_rim_mm"]
    graph_out = dict(graph, interiors=interiors, placement=dict(
        frame="board_mm", pot_center_board_mm=pot_center_board_mm(spec).tolist(), soil_z_board_mm=soil_z,
        plant_rotation_deg=sp["plant_rotation_deg"]))
    param_hash = hashlib.sha256(json.dumps(dict(scene=sp, plant=graph["params"], config=config_hash(cfg)),
                                           sort_keys=True, default=_json_default).encode()).hexdigest()
    write_json(scene_dir / "plant_graph.json", graph_out)
    write_json(scene_dir / "scene_params.json", dict(origin=ORIGIN, seed=seed, parameter_hash=param_hash, **sp))
    write_json(scene_dir / "leaflet_index.json", index)
    write_json(scene_dir / "rejections.json", rejections)
    write_obj(parts, scene_dir / "meshes.obj")
    return dict(scene_id=scene_id, seed=seed, graph=graph_out, interiors=interiors, parts=parts, index=index,
                scene_params=sp, parameter_hash=param_hash, rejections=rejections, scene_dir=scene_dir)


def write_view_layers(scene: dict[str, Any], view: RigView, k: int, geom: RenderGeometry) -> tuple[Path, Any]:
    """Rasterise one view and write its mask/depth layers; return (view dir, layers)."""
    vdir = scene["scene_dir"] / "views" / f"{k:02d}_{view.session_id}_{view.view_id.split('/')[-1]}"
    (vdir / "amodal").mkdir(parents=True, exist_ok=True)
    layers = rasterize(scene["parts"], view.rotation, view.translation, geom)
    imwrite((vdir / "visible_mask.png"), layers.visible)
    imwrite((vdir / "organ_mask.png"), layers.organ)
    imwrite((vdir / "valid_mask.png"), layers.valid.astype(np.uint8) * 255)
    np.save(vdir / "depth_mm.npy", layers.depth_mm)
    for inst, mask in layers.amodal.items():
        info = scene["index"][str(inst)]
        if mask.any():
            imwrite((vdir / "amodal" / f"{info['compound_id']}_{info['tag']}.png"), mask.astype(np.uint8) * 255)
    return vdir, layers


def manifest_row(scene: dict[str, Any], view: RigView, vdir: Path, out_root: Path, *, view_kind: str,
                 rgb_written: bool) -> dict[str, Any]:
    rel = lambda p: Path(p).resolve().relative_to(Path(out_root).resolve()).as_posix()  # noqa: E731
    return dict(
        scene_id=scene["scene_id"], view_id=view.view_id, camera_source_session=view.session_id,
        rgb=rel(vdir / "rgb.png") if rgb_written else None, visible_mask=rel(vdir / "visible_mask.png"),
        amodal_dir=rel(vdir / "amodal"), depth=rel(vdir / "depth_mm.npy"), organ_mask=rel(vdir / "organ_mask.png"),
        valid_mask=rel(vdir / "valid_mask.png"), plant_graph=rel(scene["scene_dir"] / "plant_graph.json"),
        leaflet_index=rel(scene["scene_dir"] / "leaflet_index.json"), seed=scene["seed"],
        parameter_hash=scene["parameter_hash"], origin=ORIGIN, generator_version=GENERATOR_VERSION,
        view_kind=view_kind, camera_elevation_deg=round(view.elevation_deg, 2),
        pose_reprojection_error_px=view.reprojection_error_px, camera_pose_gate_passed=view.passes_pose_gate,
        depth_units="mm, camera-frame Z (0 = no surface)")
