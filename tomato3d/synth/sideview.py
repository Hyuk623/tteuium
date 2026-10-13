"""Synthetic side-view set with terminal-leaflet direction labels (Prompt R, 2026-10-09).

Side-view photos are labelled at COMPOUND level (policy: ``handoff/DETECTOR_POLICY_2026-10-09.md``,
"Side-view labeling policy"). The training label for direction is CAMERA-RELATIVE; the stored
value is the ABSOLUTE clockwise quadrant, derived by :func:`camera_relative_to_quadrant`.

Conventions fixed by this module (and copied into ``R_contract.json``):

* Board frame, ``+Z`` up. Every horizontal azimuth is ``atan2(y, x)`` in degrees, i.e. measured
  COUNTER-CLOCKWISE from ``+X`` when the plant is seen from above, wrapped to ``(-180, 180]``.
* Compound direction ``theta``: azimuth of the terminal leaflet heading (``interiors[cid]
  .leaflets[tag == "T"].heading``) after the scene's ``plant_rotation_deg``; the compound's
  ``direction_unit`` (rachis axis) is the fallback when no terminal leaflet exists.
* Camera azimuth ``phi``: azimuth of ``camera_centre - look_at_target``.
* ``delta = wrap(theta - phi)``. Bins: ``cl_toward`` |delta| <= 45, ``cl_right`` 45 < delta < 135,
  ``cl_away`` |delta| >= 135, ``cl_left`` -135 < delta < -45. ``delta = +90`` means the terminal
  leaflet points to the camera's IMAGE-RIGHT (``tests/test_synth_sideview.py`` proves this against
  :func:`tomato3d.synth.camera.project_render`, so the sign is pinned by the renderer, not by prose).
* Boundary exclusion: a sample whose |distance to the nearest bin boundary| <= ``exclusion_deg``
  (10) is excluded from direction training (``excluded_boundary``), never silently dropped.
* Protocol view azimuth ``a`` in {0, 90, 180, 270}: the camera POSITION angle measured CLOCKWISE
  (seen from above) from the view-0 camera position. The synthetic camera for view ``k`` therefore
  sits at ``phi_k = phi_0 - a_k + jitter``.
* Clockwise quadrant ``q`` in {1, 2, 3, 4}: ``psi = (phi_0 - theta) mod 360`` is the clockwise angle
  from the view-0 camera direction to the compound direction and ``q = 1 + floor(((psi + 45) mod
  360) / 90)``. Hence ``q == k + 1`` exactly when the terminal leaflet points toward the view-``k``
  camera (+-45 deg): quadrant 1 faces the view-0 camera, quadrant 2 the view-90 camera, ...
* Converter (production, real photos): ``q = 1 + (((a + OFFSET[cls]) mod 360) // 90)`` with
  ``OFFSET = {cl_toward: 0, cl_left: 90, cl_away: 180, cl_right: 270}``. With azimuth jitter
  <= exclusion band this is exact on every non-excluded sample (tested).

Real-photo caveat: ``generator_capture.csv`` records ``azimuth_basis = capture_order_assumed`` -
the 0 deg mark and the walking direction were not written down. The converter assumes the
protocol order (clockwise from above); the human must confirm that bit per session before any
quadrant is reported for real plants.

Nothing here touches the Stage 1 outputs: all files go under a ``sideprop_*`` run folder.
"""

from __future__ import annotations

import csv
import hashlib
import json
import math
from pathlib import Path
from typing import Any

import cv2
import numpy as np

from tomato3d.synth import GENERATOR_VERSION, ORIGIN
from tomato3d.synth.camera import RenderGeometry, RigView
from tomato3d.synth.config import make_rng
from tomato3d.synth.images import imwrite
from tomato3d.synth.raster import ORGAN_CLASSES, rasterize

DIRECTION_CLASSES = ("cl_toward", "cl_right", "cl_away", "cl_left")
BIN_BOUNDARIES_DEG = (-135.0, -45.0, 45.0, 135.0)
QUADRANT_OFFSET_DEG = {"cl_toward": 0, "cl_left": 90, "cl_away": 180, "cl_right": 270}
PROTOCOL_AZIMUTHS_DEG = (0, 90, 180, 270)
# YOLO class ids. ``compound_unclear`` holds boundary-excluded compounds so that they are neither
# direction-supervised nor taught as background (mirrors the human ``unclear`` option).
YOLO_CLASSES = ("cl_toward", "cl_right", "cl_away", "cl_left", "main_stem", "growth_shoot", "compound_unclear")
LABEL_SCHEMA = "synth-sideview-labels-1"


# --------------------------------------------------------------------------- angles
def wrap_deg(a: float) -> float:
    """Wrap to ``(-180, 180]``."""
    a = float(a) % 360.0
    return a - 360.0 if a > 180.0 else a


def azimuth_deg(xy: np.ndarray) -> float:
    """Counter-clockwise-from-+X azimuth of a horizontal vector (board frame, seen from above)."""
    v = np.asarray(xy, float).ravel()
    return math.degrees(math.atan2(v[1], v[0]))


def boundary_distance_deg(delta_deg: float) -> float:
    """Angular distance from ``delta`` to the nearest bin boundary (+-45, +-135)."""
    d = wrap_deg(delta_deg)
    return min(abs(wrap_deg(d - b)) for b in BIN_BOUNDARIES_DEG)


def camera_relative_class(delta_deg: float) -> str:
    """4-way camera-relative class of ``delta = wrap(theta_compound - phi_camera)``."""
    d = wrap_deg(delta_deg)
    if abs(d) <= 45.0:
        return "cl_toward"
    if abs(d) >= 135.0:
        return "cl_away"
    return "cl_right" if d > 0 else "cl_left"


def camera_relative_bin(delta_deg: float, exclusion_deg: float = 10.0) -> dict[str, Any]:
    """Class + boundary distance + exclusion flag for one compound/view pair."""
    d = wrap_deg(delta_deg)
    dist = boundary_distance_deg(d)
    return dict(delta_deg=round(d, 3), cls=camera_relative_class(d), boundary_distance_deg=round(dist, 3),
                excluded_boundary=bool(dist <= exclusion_deg))


def quadrant_from_direction(theta_deg: float, phi0_deg: float) -> int:
    """Absolute clockwise quadrant 1-4 of a compound direction, view-0 camera direction as reference."""
    psi = (float(phi0_deg) - float(theta_deg)) % 360.0          # clockwise from the view-0 camera direction
    return 1 + int(((psi + 45.0) % 360.0) // 90.0)


def camera_relative_to_quadrant(cls: str, view_azimuth_deg: float) -> int:
    """Production converter: camera-relative class + protocol view azimuth -> clockwise quadrant 1-4.

    ``view_azimuth_deg`` is the recorded protocol label (0/90/180/270, clockwise camera positions
    from the view-0 position). Raises on any other value so a wrong label cannot pass silently.
    """
    if cls not in QUADRANT_OFFSET_DEG:
        raise ValueError(f"not a direction class: {cls!r}")
    a = float(view_azimuth_deg)
    if a % 90.0 != 0.0:
        raise ValueError(f"view azimuth must be a multiple of 90 deg, got {view_azimuth_deg}")
    return 1 + int(((a + QUADRANT_OFFSET_DEG[cls]) % 360.0) // 90.0)


# --------------------------------------------------------------------------- cameras
def look_at_view(view_id: str, *, center_mm: np.ndarray, target_mm: np.ndarray, camera_matrix: np.ndarray,
                 dist_coeffs: np.ndarray, image_size_px: tuple[int, int], session_id: str = "synside",
                 elevation_deg: float | None = None) -> RigView:
    """OpenCV camera (x right, y down, z forward) at ``center`` looking at ``target``, ``+Z`` up."""
    center, target = np.asarray(center_mm, float), np.asarray(target_mm, float)
    z = target - center
    z /= np.linalg.norm(z)
    x = np.cross(z, [0.0, 0.0, 1.0])
    x /= np.linalg.norm(x)
    y = np.cross(z, x)
    R = np.stack([x, y, z])
    t = -R @ center
    rel = center - target
    elev = math.degrees(math.atan2(rel[2], math.hypot(rel[0], rel[1]))) if elevation_deg is None else elevation_deg
    return RigView(view_id=view_id, session_id=session_id, capture_path="synthetic", image_file=f"{view_id}.png",
                   camera_matrix=tuple(map(tuple, np.asarray(camera_matrix, float).tolist())),
                   dist_coeffs=tuple(np.asarray(dist_coeffs, float).tolist()),
                   image_size_px=(int(image_size_px[0]), int(image_size_px[1])),
                   rvec_rad=tuple(cv2.Rodrigues(R)[0].ravel().tolist()), tvec_mm=tuple(t.tolist()),
                   reprojection_error_px=0.0, camera_center_mm=tuple(center.tolist()), elevation_deg=float(elev),
                   passes_pose_gate=True)


def camera_azimuth_deg(view: RigView, target_mm: np.ndarray) -> float:
    rel = np.asarray(view.camera_center_mm, float) - np.asarray(target_mm, float)
    return azimuth_deg(rel[:2])


def plan_side_cameras(seed: int, geometry: dict[str, Any]) -> list[dict[str, Any]]:
    """Per-scene camera plan: one entry per protocol azimuth, with the declared jitter.

    ``geometry`` keys: ``view0_camera_azimuth_deg`` (phi_0, CCW-from-+X), ``elevation_deg``,
    ``elevation_jitter_deg``, ``azimuth_jitter_deg``, ``distance_mm``, ``protocol_azimuths_deg``.
    """
    plan = []
    for k, a in enumerate(geometry.get("protocol_azimuths_deg", PROTOCOL_AZIMUTHS_DEG)):
        rng = make_rng(seed, "sidecam", k)
        jaz = float(rng.uniform(-geometry["azimuth_jitter_deg"], geometry["azimuth_jitter_deg"]))
        jel = float(rng.uniform(-geometry["elevation_jitter_deg"], geometry["elevation_jitter_deg"]))
        phi = wrap_deg(geometry["view0_camera_azimuth_deg"] - a + jaz)      # clockwise protocol order
        plan.append(dict(k=k, protocol_azimuth_deg=int(a), camera_azimuth_deg=round(phi, 4),
                         azimuth_jitter_deg=round(jaz, 4), elevation_deg=round(geometry["elevation_deg"] + jel, 4),
                         elevation_jitter_deg=round(jel, 4), distance_mm=float(geometry["distance_mm"])))
    return plan


def camera_center_mm(target_mm: np.ndarray, azimuth_deg_: float, elevation_deg: float, distance_mm: float
                     ) -> np.ndarray:
    az, el = math.radians(azimuth_deg_), math.radians(elevation_deg)
    return np.asarray(target_mm, float) + distance_mm * np.array(
        [math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)])


def scene_target_mm(graph: dict[str, Any], target_rule: dict[str, Any]) -> np.ndarray:
    """Look-at point: pot centre XY, z = soil + ``height_fraction`` x apex height (plant frame)."""
    pl = graph["placement"]
    apex_z = float(np.asarray(graph["stem"]["points_mm"], float)[-1, 2])
    z = float(pl["soil_z_board_mm"]) + float(target_rule["height_fraction"]) * apex_z
    return np.array([pl["pot_center_board_mm"][0], pl["pot_center_board_mm"][1], z], float)


# --------------------------------------------------------------------------- directions
def _rotate_z(v: np.ndarray, rotation_deg: float) -> np.ndarray:
    a = math.radians(rotation_deg)
    R = np.array([[math.cos(a), -math.sin(a), 0.0], [math.sin(a), math.cos(a), 0.0], [0.0, 0.0, 1.0]])
    return R @ np.asarray(v, float)


def compound_direction_deg(graph: dict[str, Any], compound_id: str) -> dict[str, Any]:
    """Board-frame azimuth of the compound's terminal-leaflet heading (fallback: rachis axis)."""
    rot = float(graph["placement"]["plant_rotation_deg"])
    interior = graph.get("interiors", {}).get(compound_id, {})
    terminal = [l for l in interior.get("leaflets", []) if l.get("tag") == "T"]
    if terminal:
        v, source = np.asarray(terminal[0]["heading"], float), "terminal_leaflet_heading"
    else:
        comp = next(c for c in graph["compounds"] if c["compound_id"] == compound_id)
        v, source = np.asarray(comp["direction_unit"], float), "compound_direction_unit"
    vb = _rotate_z(v, rot)
    horiz = float(math.hypot(vb[0], vb[1]))
    return dict(theta_deg=round(azimuth_deg(vb[:2]), 4), source=source,
                horizontal_norm=round(horiz, 4), pitch_deg=round(math.degrees(math.atan2(vb[2], horiz)), 3))


# --------------------------------------------------------------------------- parts / labels
def compound_of_part(part: dict[str, Any]) -> str | None:
    """Compound id a scene part belongs to (``rachis_L03``, ``scene_0000/L03/T``, ``petiolule_...``)."""
    name, organ = str(part["name"]), part["organ"]
    if organ == "rachis" and name.startswith("rachis_"):
        return name[len("rachis_"):]
    if organ in ("leaflet", "petiolule"):
        core = name[len("petiolule_"):] if name.startswith("petiolule_") else name
        bits = core.split("/")
        return bits[1] if len(bits) >= 3 else None
    return None


def relabel_parts_by_compound(parts: list[dict[str, Any]], compound_ids: list[str], *, drop_board: bool
                              ) -> tuple[list[dict[str, Any]], dict[str, int]]:
    """Instance = compound index (1..n); stem = n+1; apex (growth shoot) = n+2; the rest 0."""
    ids = {cid: i + 1 for i, cid in enumerate(compound_ids)}
    stem_i, apex_i = len(compound_ids) + 1, len(compound_ids) + 2
    out = []
    for p in parts:
        if drop_board and p["organ"] == "board":
            continue
        q = dict(p)
        cid = compound_of_part(p)
        if cid is not None and cid in ids:
            q["instance"] = ids[cid]
        elif p["organ"] == "stem":
            q["instance"] = stem_i
        elif p["organ"] == "apex":
            q["instance"] = apex_i
        else:
            q["instance"] = 0
        out.append(q)
    return out, dict(**ids, main_stem=stem_i, growth_shoot=apex_i)


def _box_of(mask: np.ndarray) -> list[float] | None:
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    return [float(xs.min()), float(ys.min()), float(xs.max() + 1), float(ys.max() + 1)]


def view_labels(graph: dict[str, Any], parts: list[dict[str, Any]], view: RigView, geom: RenderGeometry, *,
                protocol_azimuth_deg: int, view0_camera_azimuth_deg: float, target_mm: np.ndarray,
                exclusion_deg: float, min_visible_px: int, drop_board: bool = True
                ) -> tuple[dict[str, Any], Any]:
    """Compound / stem / growth-shoot boxes + direction labels for one view. Returns (labels, layers)."""
    cids = [c["compound_id"] for c in graph["compounds"]]
    relabeled, inst = relabel_parts_by_compound(parts, cids, drop_board=drop_board)
    layers = rasterize(relabeled, view.rotation, view.translation, geom)
    phi = camera_azimuth_deg(view, target_mm)
    W, H = geom.out_size_px
    compounds, excluded_boundary, excluded_occluded = [], [], []
    for cid in cids:
        i = inst[cid]
        vis = layers.visible == i
        area = int(vis.sum())
        amodal = layers.amodal.get(i)
        amodal_px = int(amodal.sum()) if amodal is not None else 0
        d = compound_direction_deg(graph, cid)
        b = camera_relative_bin(d["theta_deg"] - phi, exclusion_deg)
        rank = next(c["rank_from_bottom"] for c in graph["compounds"] if c["compound_id"] == cid)
        rec = dict(compound_id=cid, rank_from_bottom=int(rank), instance=i, theta_deg=d["theta_deg"],
                   direction_source=d["source"], pitch_deg=d["pitch_deg"], camera_azimuth_deg=round(phi, 4),
                   quadrant_gt=quadrant_from_direction(d["theta_deg"], view0_camera_azimuth_deg),
                   visible_px=area, amodal_px=amodal_px, vis_frac=round(area / amodal_px, 4) if amodal_px else 0.0,
                   box_xyxy=_box_of(vis), amodal_box_xyxy=_box_of(amodal) if amodal is not None else None, **b)
        if area < min_visible_px:
            rec["excluded_occluded"] = True
            excluded_occluded.append(rec)
            continue
        rec["excluded_occluded"] = False
        compounds.append(rec)
        if rec["excluded_boundary"]:
            excluded_boundary.append(dict(compound_id=cid, delta_deg=rec["delta_deg"],
                                          boundary_distance_deg=rec["boundary_distance_deg"]))
    stem_box = _box_of(layers.visible == inst["main_stem"])
    shoot_box = _box_of(layers.visible == inst["growth_shoot"])
    labels = dict(schema=LABEL_SCHEMA, origin=ORIGIN, scene_id=graph["plant_id"], view_id=view.view_id,
                  protocol_azimuth_deg=int(protocol_azimuth_deg), camera_azimuth_deg=round(phi, 4),
                  view0_camera_azimuth_deg=float(view0_camera_azimuth_deg),
                  camera_elevation_deg=round(view.elevation_deg, 3), image_size_px=[int(W), int(H)],
                  exclusion_deg=float(exclusion_deg), min_visible_px=int(min_visible_px),
                  compounds=compounds, excluded_boundary=excluded_boundary, excluded_occluded=excluded_occluded,
                  main_stem=dict(box_xyxy=stem_box, visible_px=int((layers.visible == inst["main_stem"]).sum())),
                  growth_shoot=dict(box_xyxy=shoot_box,
                                    visible_px=int((layers.visible == inst["growth_shoot"]).sum())),
                  instances=inst)
    return labels, layers


# --------------------------------------------------------------------------- exports
def yolo_lines(labels: dict[str, Any]) -> list[str]:
    """YOLO txt: ``cls cx cy w h`` normalised. Boundary-excluded compounds -> ``compound_unclear``."""
    W, H = labels["image_size_px"]

    def line(cls_id: int, box: list[float]) -> str:
        x0, y0, x1, y1 = box
        return (f"{cls_id} {((x0 + x1) / 2) / W:.6f} {((y0 + y1) / 2) / H:.6f} "
                f"{(x1 - x0) / W:.6f} {(y1 - y0) / H:.6f}")

    out = []
    for c in labels["compounds"]:
        if c["box_xyxy"] is None:
            continue
        cls = "compound_unclear" if c["excluded_boundary"] else c["cls"]
        out.append(line(YOLO_CLASSES.index(cls), c["box_xyxy"]))
    for key in ("main_stem", "growth_shoot"):
        box = labels[key]["box_xyxy"]
        if box is not None:
            out.append(line(YOLO_CLASSES.index(key), box))
    return out


def coco_annotations(labels: dict[str, Any], image_id: int, ann_start: int) -> list[dict[str, Any]]:
    out, k = [], ann_start

    def add(cls: str, box: list[float], extra: dict[str, Any]) -> None:
        nonlocal k
        x0, y0, x1, y1 = box
        out.append(dict(id=k, image_id=image_id, category_id=YOLO_CLASSES.index(cls) + 1,
                        bbox=[x0, y0, x1 - x0, y1 - y0], area=(x1 - x0) * (y1 - y0), iscrowd=0, **extra))
        k += 1

    for c in labels["compounds"]:
        if c["box_xyxy"] is None:
            continue
        cls = "compound_unclear" if c["excluded_boundary"] else c["cls"]
        add(cls, c["box_xyxy"], dict(compound_id=c["compound_id"], delta_deg=c["delta_deg"],
                                     quadrant_gt=c["quadrant_gt"], excluded_boundary=c["excluded_boundary"],
                                     visible_px=c["visible_px"], vis_frac=c["vis_frac"]))
    for key in ("main_stem", "growth_shoot"):
        box = labels[key]["box_xyxy"]
        if box is not None:
            add(key, box, {})
    return out


CAPTURE_ROTATION = "clockwise_assumed_unverified"   # R_DECISIONS 2026-10-10 item 3: visible on every manifest
MANIFEST_COLUMNS = ("scene_id", "view_id", "protocol_azimuth_deg", "camera_azimuth_deg", "camera_elevation_deg",
                    "compound_id", "rank_from_bottom", "theta_deg", "pitch_deg", "direction_source", "delta_deg", "cls",
                    "boundary_distance_deg", "excluded_boundary", "excluded_occluded", "quadrant_gt",
                    "quadrant_from_converter", "capture_rotation", "visible_px", "vis_frac", "box_xyxy", "image")


def manifest_rows(labels: dict[str, Any], image_rel: str) -> list[dict[str, Any]]:
    rows = []
    for c in labels["compounds"] + labels["excluded_occluded"]:
        conv = (camera_relative_to_quadrant(c["cls"], labels["protocol_azimuth_deg"])
                if not c["excluded_boundary"] else "")
        rows.append(dict(scene_id=labels["scene_id"], view_id=labels["view_id"],
                         protocol_azimuth_deg=labels["protocol_azimuth_deg"],
                         camera_azimuth_deg=labels["camera_azimuth_deg"],
                         camera_elevation_deg=labels["camera_elevation_deg"], compound_id=c["compound_id"],
                         rank_from_bottom=c["rank_from_bottom"], theta_deg=c["theta_deg"], pitch_deg=c["pitch_deg"],
                         direction_source=c["direction_source"], delta_deg=c["delta_deg"], cls=c["cls"],
                         boundary_distance_deg=c["boundary_distance_deg"],
                         excluded_boundary=int(c["excluded_boundary"]), excluded_occluded=int(c["excluded_occluded"]),
                         quadrant_gt=c["quadrant_gt"], quadrant_from_converter=conv,
                         capture_rotation=labels.get("capture_rotation", CAPTURE_ROTATION), visible_px=c["visible_px"],
                         vis_frac=c["vis_frac"], box_xyxy=json.dumps(c["box_xyxy"]), image=image_rel))
    return rows


def write_manifest_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    """(Re)write the per-compound manifest; ``collect`` always rebuilds it from the per-scene rows."""
    with Path(path).open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=list(MANIFEST_COLUMNS))
        w.writeheader()
        w.writerows(rows)


def white_sheet_texture(path: Path, size_hw: tuple[int, int] = (1520, 2128), gray: int = 230) -> Path:
    """Board plane kept as a plain white sheet: no ChArUco pattern in the side set ("no board")."""
    imwrite(Path(path), np.full((size_hw[0], size_hw[1]), gray, np.uint8))
    return Path(path)


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


# --------------------------------------------------------------------------- contract
def effective_contract(raw: dict[str, Any]) -> dict[str, Any]:
    """The declared contract with every amendment's ``overrides`` (dotted keys) applied in order.

    Amendments never delete the declared text; an override must name an existing key.
    """
    c = json.loads(json.dumps(raw))
    for am in raw.get("amendments", []):
        for dotted, value in (am.get("overrides") or {}).items():
            node, keys = c, dotted.split(".")
            for k in keys[:-1]:
                node = node[k]
            if keys[-1] not in node:
                raise KeyError(f"amendment {am.get('id')} overrides unknown key {dotted}")
            node[keys[-1]] = value
    return c


def load_contract(out: Path) -> dict[str, Any]:
    return effective_contract(json.loads((Path(out) / "R_contract.json").read_text(encoding="utf-8")))


def _check_inputs(out: Path, c: dict[str, Any]) -> tuple[dict[str, Any], dict[str, Any]]:
    """Refuse to run when an input differs from what R_contract.json pins."""
    from tomato3d.synth.config import input_path, load_generator_config

    gen = c["generator"]
    for name, key in (("generator_config.json", "generator_config_sha256"),
                      ("leaflet_contours.json", "leaflet_contours_sha256")):
        if sha256_file(out / name) != gen[key]:
            raise SystemExit(f"{name} differs from {key} pinned in R_contract.json")
    cfg = load_generator_config(out / "generator_config.json")
    bank = cfg.get("constants", {}).get("leaf_texture_bank")
    if bank and sha256_file(input_path(bank["value"])) != gen["texture_bank_sha256"]:
        raise SystemExit("texture bank differs from texture_bank_sha256 pinned in R_contract.json")
    if not (out / "board_texture.png").exists():
        raise SystemExit("board_texture.png (uniform sheet) is missing")
    intr = json.loads((out / "views_intrinsics.json").read_text(encoding="utf-8"))
    return cfg, intr


def _done_scenes(out: Path) -> list[Path]:
    return sorted(p.parent for p in Path(out).glob("scenes/scene_*/DONE"))


# --------------------------------------------------------------------------- R.1 / R.2 generation
def generate_side_set(out: Path, *, start: int, count: int, rgb: str = "export") -> None:
    """Plants, label layers, labels and render jobs for scenes ``start .. start+count-1``.

    Needs the ``tomato_synth`` env (L-Py/PlantGL). Resumable: a scene with ``DONE`` or ``REJECTED`` is
    skipped; a scene killed half-way is rebuilt from its seed. Per scene it writes
    ``views/<k>_synside_<az>/{visible_compound_mask,organ_mask,valid_mask}.png``, ``amodal/``,
    ``labels.json``, ``labels/<stem>.txt`` (YOLO), ``render_job/`` and ``side_rows.json``; ``collect``
    assembles the set-level files from those, so a re-run can never duplicate manifest rows.
    """
    import shutil
    import time

    from tomato3d.synth import pipeline as pl
    from tomato3d.synth.cli import _board_spec
    from tomato3d.synth.config import constant
    from tomato3d.synth.contours import load_library
    from tomato3d.synth.render_remote import export_job
    from tomato3d.synth.scene import pot_center_board_mm

    out = Path(out)
    c = load_contract(out)
    cfg, intr = _check_inputs(out, c)
    geometry, dl, sc = c["camera_geometry"], c["direction_labels"], c["scenes"]
    K = np.asarray(intr["camera_matrix"], float)
    dist = np.asarray(intr["dist_coeffs"], float)
    size = tuple(int(x) for x in intr["image_size_px"])
    contours, contour_records = load_library(out / "leaflet_contours.json")
    contour_ids = [r.get("mask_id") for r in contour_records]
    spec = _board_spec()
    gc = pl.GeometryCache(cfg, int(sc["resolution_px"]))
    pot = pot_center_board_mm(spec)
    sheet = out / "board_texture.png"
    look = {k: cfg["constants"][k]["value"] for k in ("key_light_size_m", "bump_strength", "bump_distance_m",
                                                      "leaf_specular", "leaf_roughness")
            if k in cfg.get("constants", {})}
    (out / "labels").mkdir(exist_ok=True)
    for i in range(start, start + count):
        scene_id = f"scene_{i:04d}"
        seed = int(c["seeds"]["seed_base"]) + i
        scene_dir = out / "scenes" / scene_id
        if (scene_dir / "DONE").exists() or (scene_dir / "REJECTED").exists():
            continue
        t0 = time.time()
        try:
            scene = pl.build_scene(cfg, seed, scene_id, contours, spec, scene_dir, contour_ids)
        except pl.SceneRejected as exc:
            scene_dir.mkdir(parents=True, exist_ok=True)
            (scene_dir / "REJECTED").write_text(json.dumps(dict(scene_id=scene_id, seed=seed,
                                                                rejections=exc.rejections), default=str, indent=1),
                                                encoding="utf-8")
            print(json.dumps(dict(scene=scene_id, rejected=True)), flush=True)
            continue
        shutil.rmtree(scene_dir / "work", ignore_errors=True)
        graph = scene["graph"]
        target = scene_target_mm(graph, geometry["look_at_target"])
        job_views, view_rows, label_rows = [], [], []
        for cam in plan_side_cameras(seed, geometry):
            k, a = cam["k"], cam["protocol_azimuth_deg"]
            center = camera_center_mm(target, cam["camera_azimuth_deg"], cam["elevation_deg"], cam["distance_mm"])
            view = look_at_view(f"synside/{scene_id}/{a:03d}", center_mm=center, target_mm=target, camera_matrix=K,
                                dist_coeffs=dist, image_size_px=size)
            geom = gc.get(view)
            labels, layers = view_labels(graph, scene["parts"], view, geom, protocol_azimuth_deg=a,
                                         view0_camera_azimuth_deg=float(geometry["view0_camera_azimuth_deg"]),
                                         target_mm=target, exclusion_deg=float(dl["exclusion_deg"]),
                                         min_visible_px=int(dl["min_visible_px_compound"]))
            vdir = scene_dir / "views" / f"{k:02d}_synside_{a:03d}"
            (vdir / "amodal").mkdir(parents=True, exist_ok=True)
            imwrite(vdir / "visible_compound_mask.png", layers.visible)
            imwrite(vdir / "organ_mask.png", layers.organ)
            imwrite(vdir / "valid_mask.png", layers.valid.astype(np.uint8) * 255)
            names = {v: n for n, v in labels["instances"].items()}
            for inst_i, m in layers.amodal.items():
                if m.any():
                    imwrite(vdir / "amodal" / f"{names[inst_i]}.png", m.astype(np.uint8) * 255)
            labels.update(camera_plan=cam, target_mm=target.tolist(), seed=seed,
                          parameter_hash=scene["parameter_hash"], generator_version=GENERATOR_VERSION,
                          capture_rotation=CAPTURE_ROTATION, view_dir=vdir.name)
            (vdir / "labels.json").write_text(json.dumps(labels, indent=1), encoding="utf-8")
            stem = f"{scene_id}_{vdir.name}"
            image_rel = f"scenes/{scene_id}/views/{vdir.name}/rgb.png"
            (out / "labels" / f"{stem}.txt").write_text("".join(l + "\n" for l in yolo_lines(labels)), encoding="utf-8")
            label_rows += manifest_rows(labels, image_rel)
            job_views.append(dict(name=vdir.name, K_render=geom.K_render, size=geom.render_size_px, R=view.rotation,
                                  t=view.translation))
            view_rows.append(dict(scene_id=scene_id, view_id=view.view_id, view_dir=vdir.name, stem=stem, rgb=image_rel,
                                  labels=f"scenes/{scene_id}/views/{vdir.name}/labels.json", yolo=f"labels/{stem}.txt",
                                  seed=seed, parameter_hash=scene["parameter_hash"], origin=ORIGIN,
                                  generator_version=GENERATOR_VERSION, view_kind="side", protocol_azimuth_deg=a,
                                  camera_azimuth_deg=cam["camera_azimuth_deg"],
                                  camera_elevation_deg=cam["elevation_deg"], distance_mm=cam["distance_mm"],
                                  capture_rotation=CAPTURE_ROTATION,
                                  rgb_status="pending_remote" if rgb == "export" else "not_rendered",
                                  n_compounds=len(labels["compounds"]),
                                  n_excluded_boundary=len(labels["excluded_boundary"]),
                                  n_excluded_occluded=len(labels["excluded_occluded"])))
        if rgb == "export":       # the board plane stays as geometry and renders with the uniform sheet texture
            export_job(scene, job_views, samples=int(sc["cycles_samples"]),
                       backdrop_distance_mm=constant(cfg, "backdrop_distance_mm"), pot_center_mm=pot,
                       board_texture=sheet, look=look)
        dt = round(time.time() - t0, 1)
        (scene_dir / "side_rows.json").write_text(json.dumps(dict(view_rows=view_rows, label_rows=label_rows,
                                                                  seconds=dt), indent=1), encoding="utf-8")
        (scene_dir / "DONE").write_text(scene_id, encoding="utf-8")
        print(json.dumps(dict(scene=scene_id, seconds=dt, compounds=len(graph["compounds"]),
                              boxes=sum(r["n_compounds"] for r in view_rows))), flush=True)


# --------------------------------------------------------------------------- pre-render check
PRECHECK_CY_BAND = (0.42, 0.58)            # R_contract camera_geometry.look_at_target.pre_render_check
PLANT_ORGANS = ("leaflet", "stem", "rachis", "petiolule", "apex")


def plant_frame_stats(organ: np.ndarray) -> dict[str, float]:
    """Plant-pixel fraction and 1-99 percentile plant box (frame fractions), as measured on the real photos."""
    plant = np.isin(organ, [ORGAN_CLASSES[o] for o in PLANT_ORGANS])
    H, W = plant.shape
    ys, xs = np.nonzero(plant)
    if len(ys) <= 50:
        return dict(plant_frac=round(float(plant.mean()), 4), bbox_h=float("nan"), bbox_w=float("nan"),
                    cy=float("nan"))
    y0, y1 = np.percentile(ys, [1, 99])
    x0, x1 = np.percentile(xs, [1, 99])
    return dict(plant_frac=round(float(plant.mean()), 4), bbox_h=round(float((y1 - y0) / H), 4),
                bbox_w=round(float((x1 - x0) / W), 4), cy=round(float((y0 + y1) / 2 / H), 4))


def precheck(out: Path, n_scenes: int = 5) -> dict[str, Any]:
    """Declared pre-render check on the first generated scenes (masks only); writes ``R1_precheck.json``."""
    from tomato3d.synth.images import imread

    out = Path(out)
    c = load_contract(out)
    scenes = _done_scenes(out)[:n_scenes]
    rows = []
    for sdir in scenes:
        for vdir in sorted((sdir / "views").iterdir()):
            rows.append(dict(scene=sdir.name, view=vdir.name, **plant_frame_stats(imread(vdir / "organ_mask.png"))))

    def p50(key: str) -> float:
        return round(float(np.nanmedian([r[key] for r in rows])), 4) if rows else float("nan")

    real_path = out / "real_eval" / "real_side_green_stats_512.json"
    real = json.loads(real_path.read_text(encoding="utf-8")) if real_path.exists() else []
    real_p50 = {k: round(float(np.median([r[k] for r in real])), 4) for k in ("green_frac", "bbox_h", "bbox_w", "cy")
                } if real else {}
    cy = p50("cy")
    report = dict(schema="sideview-R1-precheck-1", declared_rule=c["camera_geometry"]["look_at_target"],
                  cy_band=list(PRECHECK_CY_BAND), scenes=[s.name for s in scenes], n_views=len(rows),
                  synthetic_p50=dict(plant_frac=p50("plant_frac"), bbox_h=p50("bbox_h"), bbox_w=p50("bbox_w"), cy=cy),
                  real_p50=real_p50, passed=bool(len(scenes) == n_scenes and PRECHECK_CY_BAND[0] <= cy <= PRECHECK_CY_BAND[1]),
                  rows=rows)
    (out / "R1_precheck.json").write_text(json.dumps(report, indent=1), encoding="utf-8")
    return report


# --------------------------------------------------------------------------- set-level files
def write_coco(out: Path) -> Path:
    """Assemble ``synside_coco.json`` from the ``labels.json`` of every DONE scene."""
    out = Path(out)
    images, anns = [], []
    paths = [lp for sdir in _done_scenes(out) for lp in sorted(sdir.glob("views/*/labels.json"))]
    for i, lp in enumerate(paths):
        lab = json.loads(lp.read_text(encoding="utf-8"))
        W, H = lab["image_size_px"]
        images.append(dict(id=i + 1, file_name=lp.parent.relative_to(out).as_posix() + "/rgb.png", width=W, height=H,
                           scene_id=lab["scene_id"], protocol_azimuth_deg=lab["protocol_azimuth_deg"],
                           camera_azimuth_deg=lab["camera_azimuth_deg"],
                           capture_rotation=lab.get("capture_rotation", CAPTURE_ROTATION)))
        anns += coco_annotations(lab, i + 1, len(anns) + 1)
    coco = dict(info=dict(description="synthetic side-view compound set (Prompt R)", origin=ORIGIN,
                          generator_version=GENERATOR_VERSION, capture_rotation=CAPTURE_ROTATION),
                categories=[dict(id=i + 1, name=n) for i, n in enumerate(YOLO_CLASSES)], images=images,
                annotations=anns)
    path = out / "synside_coco.json"
    path.write_text(json.dumps(coco), encoding="utf-8")
    return path


def _pct(values: list[float]) -> list[float]:
    return [round(float(x), 3) for x in np.percentile(values, [10, 50, 90])] if values else []


def collect(out: Path) -> dict[str, Any]:
    """Rebuild ``manifest.jsonl``, ``labels_manifest.csv`` and the COCO file from the DONE scenes, and run the
    R.3 converter check against the R.2 quadrant GT (must be exact on every non-excluded sample)."""
    from collections import Counter

    out = Path(out)
    done = _done_scenes(out)
    rejected = sorted(p.parent.name for p in out.glob("scenes/scene_*/REJECTED"))
    view_rows: list[dict[str, Any]] = []
    label_rows: list[dict[str, Any]] = []
    for sdir in done:
        d = json.loads((sdir / "side_rows.json").read_text(encoding="utf-8"))
        view_rows += d["view_rows"]
        label_rows += d["label_rows"]
    (out / "manifest.jsonl").write_text("".join(json.dumps(r) + "\n" for r in view_rows), encoding="utf-8")
    write_manifest_csv(out / "labels_manifest.csv", label_rows)
    coco = write_coco(out)
    checked = [r for r in label_rows if not int(r["excluded_boundary"])]
    mismatches = [r for r in checked if int(r["quadrant_from_converter"]) != int(r["quadrant_gt"])]
    boxed = [r for r in label_rows if not int(r["excluded_occluded"])]
    boxed_clear = [r for r in boxed if not int(r["excluded_boundary"])]
    per_plant = Counter(r["scene_id"] for r in label_rows)
    summary = dict(
        schema="sideview-R2-label-summary-1", capture_rotation=CAPTURE_ROTATION,
        scenes_done=len(done), scenes_rejected=rejected, views=len(view_rows),
        compound_view_pairs=len(label_rows),
        compounds_per_plant=dict(Counter(int(v / 4) for v in per_plant.values())),
        boxed_compounds=len(boxed),
        boxes_per_view_p10_p50_p90=_pct([vr["n_compounds"] for vr in view_rows]),
        excluded_occluded=len(label_rows) - len(boxed),
        excluded_boundary_among_boxed=len(boxed) - len(boxed_clear),
        unclear_share_synthetic=round((len(boxed) - len(boxed_clear)) / max(1, len(boxed)), 4),
        direction_class_counts=dict(Counter(r["cls"] for r in boxed_clear)),
        direction_class_by_view=dict(Counter(f"{r['protocol_azimuth_deg']:03d}:{r['cls']}" for r in boxed_clear)),
        direction_sources=dict(Counter(r["direction_source"] for r in label_rows)),
        pitch_deg_p10_p50_p90=_pct([float(r["pitch_deg"]) for r in label_rows]),
        pitch_abs_gt_60_share=round(float(np.mean([abs(float(r["pitch_deg"])) > 60 for r in label_rows])), 4)
        if label_rows else None,
        quadrant_check=dict(rule="camera_relative_to_quadrant(cls, protocol azimuth) == quadrant_gt on every sample "
                                 "outside the boundary band", checked=len(checked), mismatches=len(mismatches),
                            exact=not mismatches),
        rgb_status=dict(Counter(vr.get("rgb_status") for vr in view_rows)),
        cycles_samples=dict(Counter(str(vr.get("cycles_samples")) for vr in view_rows)),
        files=dict(manifest="manifest.jsonl", labels_manifest="labels_manifest.csv", coco=coco.name, yolo="labels/"),
        views_complete=len(view_rows) == 4 * len(done))
    (out / "R2_label_summary.json").write_text(json.dumps(summary, indent=1), encoding="utf-8")
    if mismatches:
        raise SystemExit(f"R.3 converter check FAILED on {len(mismatches)} samples (see R2_label_summary.json)")
    return summary


def finalize_side_set(out: Path, renders: Path) -> dict[str, Any]:
    """Warp the remotely rendered canvases with the mask map, post-process (same rule as Stage 1), write
    ``rgb.png`` per view plus the train-ready ``yolo/images`` + ``yolo/labels`` copies, then ``collect``."""
    import shutil

    from tomato3d.synth import pipeline as pl
    from tomato3d.synth import render_blender as rb
    from tomato3d.synth.config import load_generator_config
    from tomato3d.synth.images import imread

    out, renders = Path(out), Path(renders)
    c = load_contract(out)
    cfg = load_generator_config(out / "generator_config.json")
    intr = json.loads((out / "views_intrinsics.json").read_text(encoding="utf-8"))
    probe = look_at_view("probe", center_mm=np.array([0.0, -300.0, 100.0]), target_mm=np.zeros(3),
                         camera_matrix=np.asarray(intr["camera_matrix"], float),
                         dist_coeffs=np.asarray(intr["dist_coeffs"], float),
                         image_size_px=tuple(int(x) for x in intr["image_size_px"]))
    geom = pl.GeometryCache(cfg, int(c["scenes"]["resolution_px"])).get(probe)   # warp depends on intrinsics only
    (out / "yolo" / "images").mkdir(parents=True, exist_ok=True)
    (out / "yolo" / "labels").mkdir(parents=True, exist_ok=True)
    done = missing = 0
    for sdir in _done_scenes(out):
        path = sdir / "side_rows.json"
        d = json.loads(path.read_text(encoding="utf-8"))
        sp = json.loads((sdir / "scene_params.json").read_text(encoding="utf-8"))
        # the job actually sent to the renderer (R_contract R-A3: batch c rendered with fewer Cycles samples)
        samples = json.loads((sdir / "render_job" / "job.json").read_text(encoding="utf-8"))["samples"]
        changed = False
        for vr in d["view_rows"]:
            vdir = sdir / "views" / vr["view_dir"]
            if vr.get("rgb_status") == "rendered_remote" and (vdir / "rgb.png").exists():
                continue
            canvas = renders / sdir.name / f"{vr['view_dir']}.png"
            if not canvas.exists():
                missing += 1
                continue
            img = cv2.cvtColor(imread(canvas, cv2.IMREAD_COLOR), cv2.COLOR_BGR2RGB)
            if (img.shape[1], img.shape[0]) != tuple(geom.render_size_px):
                raise SystemExit(f"{canvas}: canvas size {img.shape[:2]} != render size {geom.render_size_px}")
            k = int(vr["view_dir"][:2])
            rgb = rb.post_process(geom.warp(img, nearest=False, fill=0), sp, make_rng(int(vr["seed"]), "post", k))
            bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
            imwrite(vdir / "rgb.png", bgr)
            imwrite(out / "yolo" / "images" / f"{vr['stem']}.png", bgr)
            shutil.copyfile(out / vr["yolo"], out / "yolo" / "labels" / f"{vr['stem']}.txt")
            vr["rgb_status"] = "rendered_remote"
            vr["rgb_canvas_sha256"] = sha256_file(canvas)
            vr["cycles_samples"] = int(samples)
            done += 1
            changed = True
        if changed:
            path.write_text(json.dumps(d, indent=1), encoding="utf-8")
    (out / "yolo" / "classes.txt").write_text("".join(n + "\n" for n in YOLO_CLASSES), encoding="utf-8")
    summary = collect(out)
    report = dict(finalized=done, missing=missing, rgb_status=summary["rgb_status"])
    print(json.dumps(report), flush=True)
    return report


def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="synthetic side-view set (Prompt R)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("generate")
    g.add_argument("--out", required=True)
    g.add_argument("--start", type=int, default=0)
    g.add_argument("--count", type=int, required=True)
    g.add_argument("--rgb", choices=("export", "none"), default="export")
    p = sub.add_parser("precheck")
    p.add_argument("--out", required=True)
    p.add_argument("--scenes", type=int, default=5)
    c = sub.add_parser("collect")
    c.add_argument("--out", required=True)
    f = sub.add_parser("finalize")
    f.add_argument("--out", required=True)
    f.add_argument("--renders", required=True)
    args = ap.parse_args(argv)
    if args.cmd == "generate":
        generate_side_set(Path(args.out), start=args.start, count=args.count, rgb=args.rgb)
    elif args.cmd == "precheck":
        r = precheck(Path(args.out), args.scenes)
        print(json.dumps({k: r[k] for k in ("scenes", "n_views", "synthetic_p50", "real_p50", "cy_band", "passed")}))
    elif args.cmd == "collect":
        s = collect(Path(args.out))
        print(json.dumps({k: s[k] for k in ("scenes_done", "views", "boxed_compounds", "unclear_share_synthetic",
                                            "direction_class_counts", "quadrant_check")}))
    else:
        finalize_side_set(Path(args.out), Path(args.renders))


if __name__ == "__main__":
    main()
