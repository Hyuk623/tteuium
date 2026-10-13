"""P1.6 - side-view compound geometry from P0..Pm points (MTG A1.5 / A2).

Inputs are 2-D points on one side image per compound: ``P0`` (petiole insertion on the stem),
``N1..Nm`` (lateral-pair nodes, base to tip), ``END`` (rachis end = terminal leaflet base) and
``STEM_UP`` (a point on the main stem above the node). On real photos a person clicks them
(``side_points.csv``, none exist yet -> unavailable); on R.1 fixtures they are the generator's
truth points projected through the scene's own render camera.

Quantities, all measured in the image plane (x right, y up): ``compound_insertion_angle_deg``,
``rachis_bend_alpha_<i>_deg``, ``rachis_curvature_deg``, ``rachis_bend_theta_deg`` (excludes the
last alpha by construction), ``chord_to_path_ratio``. A single side view projects 3-D angles, so the
value is biased by foreshortening; :func:`validate_scene` measures that bias against 3-D truth per
view as a function of the view angle. Nothing is classified flat/bent (MTG 8.4 on hold).

Blade-azimuth quadrant: from the camera-relative direction class (human or label) and the
recorded protocol view azimuth, through ``tomato3d.synth.sideview.camera_relative_to_quadrant``
(the single production converter); a side view alone gives no azimuth in degrees.

Fixture-only note: projecting truth needs the synthetic scene's own placement
(``plant_graph.json`` ``placement``) to move plant-local points into the render camera's frame.
That transform is part of the synthetic scene; it is never applied to real data, where no
board <-> plant-local transform exists.
"""

from __future__ import annotations

import json
import math
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import fixture_truth as ft
from tomato3d.state import geometry as g
from tomato3d.state import schema as s

STEM_UP_OFFSET_MM = 10.0  # fixture: STEM_UP = P0 + 10 mm along the stem above the node (declared)
POINTS_SOURCE_FIXTURE = "projected_synthetic_truth_render_canvas"
POINTS_SOURCE_HUMAN = "human_clicked"


@dataclass(frozen=True)
class SidePoints:
    p0: np.ndarray
    nodes: list[np.ndarray]
    end: np.ndarray
    stem_up: np.ndarray


def image_to_up(points_px: np.ndarray) -> np.ndarray:
    """Image (u right, v down) -> (x right, y up)."""
    p = np.asarray(points_px, float)
    return np.stack([p[..., 0], -p[..., 1]], axis=-1)


def measure(points: SidePoints) -> dict[str, float | None]:
    """A2 quantities from 2-D points already in (x right, y up)."""
    alphas = g.bend_alphas_deg(points.p0, points.nodes, points.end)
    return {
        "compound_insertion_angle_deg": (g.insertion_angle_deg(points.stem_up - points.p0, points.p0, points.nodes[0])
                                         if points.nodes else None),
        "alphas": alphas,  # type: ignore[dict-item]
        "rachis_curvature_deg": sum(alphas) if alphas else None,
        "rachis_bend_theta_deg": g.theta_deg(points.p0, points.nodes),
        "chord_to_path_ratio": g.chord_to_path_ratio(points.p0, points.nodes),
    }


#: View-selection rule for joining side values to the MTG (measured on 50 R.1 scenes, 348 compounds:
#: insertion-angle |error| median 7.0 / p90 15.6 deg with this rule vs 14.6 / 49.5 for the first view).
SIDE_ON_CLASSES = ("cl_left", "cl_right")
#: Version tag of the rule, written into every side row (MTG convention section 14, Amendment A3).
VIEW_SELECTION_RULE = "MTG_A3_v1:first_view_by_view_id_with_direction_class_cl_left_or_cl_right"


def select_views(rows: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Apply MTG A3: per (plant instance, capture, compound) mark the first view (by ``view_id``)
    whose ``direction_class`` is cl_left / cl_right and that has an insertion angle as
    ``selected_for_mtg = true``; every other row ``false``. A compound with no such view has no
    selected row, so its MTG side values stay unavailable. Each row records the rule version."""
    out = [dict(r) for r in rows]
    chosen: set[tuple[str, str, str]] = set()
    for r in sorted(out, key=lambda r: (r["plant_instance_id"], r["capture_id"], r["compound_id"], r["view_id"])):
        key = (r["plant_instance_id"], r["capture_id"], r["compound_id"])
        ok = (r["direction_class"] in SIDE_ON_CLASSES and r["compound_insertion_angle_deg"] != UNAVAILABLE
              and key not in chosen)
        if ok:
            chosen.add(key)
        r["selected_for_mtg"] = "true" if ok else "false"
        r["view_selection_rule"] = VIEW_SELECTION_RULE
    return out


def side_row(plant_instance_id: str, capture_id: str, view_id: str, compound_id: str, values: Mapping[str, Any],
             points_source: str, evidence: str, status: str, quadrant: int | None,
             quadrant_status: str, direction_class: str = UNAVAILABLE) -> dict[str, str]:
    row = {c: UNAVAILABLE for c in s.SIDE_GEOMETRY_COLUMNS}
    row.update(plant_instance_id=plant_instance_id, capture_id=capture_id, view_id=view_id, compound_id=compound_id,
               points_source=points_source, direction_class=direction_class, selected_for_mtg="false",
               view_selection_rule=VIEW_SELECTION_RULE, evidence=evidence, frame="image_px")

    def put(attr: str, value: float | None) -> None:
        if value is not None and math.isfinite(value):
            row[attr], row[f"{attr}__status"] = s.fmt(value, 3), status

    put("compound_insertion_angle_deg", values.get("compound_insertion_angle_deg"))
    alphas = values.get("alphas") or []
    if len(alphas) > s.MAX_BEND_NODES:
        raise s.P1SchemaError(f"{compound_id}: {len(alphas)} bend nodes > {s.MAX_BEND_NODES}")
    row["n_bend_nodes"] = str(len(alphas)) if alphas else UNAVAILABLE
    for i, a in enumerate(alphas, start=1):
        put(f"rachis_bend_alpha_{i}_deg", a)
    put("rachis_curvature_deg", values.get("rachis_curvature_deg"))
    put("rachis_bend_theta_deg", values.get("rachis_bend_theta_deg"))
    put("chord_to_path_ratio", values.get("chord_to_path_ratio"))
    if quadrant is not None:
        row["blade_azimuth_quadrant"], row["blade_azimuth_quadrant__status"] = str(quadrant), quadrant_status
    return row


# --------------------------------------------------------------------------------------
# Fixture: R.1 scenes
# --------------------------------------------------------------------------------------


@dataclass(frozen=True)
class RenderCamera:
    name: str
    k: np.ndarray
    r: np.ndarray
    t: np.ndarray

    def project(self, xyz_board_mm: np.ndarray) -> np.ndarray:
        cam = np.asarray(xyz_board_mm, float) @ self.r.T + self.t
        uvw = cam @ self.k.T
        return uvw[..., :2] / uvw[..., 2:3]

    @property
    def view_dir_board(self) -> np.ndarray:
        """Optical axis (+Z_cam) in the board frame."""
        return self.r.T @ np.array([0.0, 0.0, 1.0])


def load_cameras(scene_dir: Path) -> list[RenderCamera]:
    job = json.loads((Path(scene_dir) / "render_job" / "job.json").read_text(encoding="utf-8"))
    return [RenderCamera(v["name"], np.asarray(v["K_render"], float), np.asarray(v["R"], float),
                         np.asarray(v["t"], float)) for v in job["views"]]


def _placement(scene_dir: Path):
    from tomato3d.synth.scene import plant_to_board

    graph = json.loads((Path(scene_dir) / "plant_graph.json").read_text(encoding="utf-8"))
    pl = graph["placement"]
    base = np.array([pl["pot_center_board_mm"][0], pl["pot_center_board_mm"][1], pl["soil_z_board_mm"]], float)
    rot = float(pl["plant_rotation_deg"])
    return lambda pts: plant_to_board(np.atleast_2d(pts), rot, base)


def truth_values(points: ft.CompoundPoints) -> dict[str, Any]:
    alphas = g.bend_alphas_deg(points.p0, points.nodes, points.rachis_end)
    return {
        "compound_insertion_angle_deg": (g.insertion_angle_deg(points.stem_above_dir, points.p0, points.nodes[0])
                                         if points.nodes else None),
        "alphas": alphas,
        "rachis_curvature_deg": sum(alphas) if alphas else None,
        "rachis_bend_theta_deg": g.theta_deg(points.p0, points.nodes),
        "chord_to_path_ratio": g.chord_to_path_ratio(points.p0, points.nodes),
    }


def _insertion_plane_view_angle(points: ft.CompoundPoints, to_board, camera: RenderCamera) -> float | None:
    """Angle between the camera axis and the normal of the plane (stem-above, petiole): 0 = the
    plane faces the camera (no foreshortening of the insertion angle), 90 = seen edge-on."""
    if not points.nodes:
        return None
    a = to_board(points.p0 + points.stem_above_dir)[0] - to_board(points.p0)[0]
    b = to_board(points.nodes[0])[0] - to_board(points.p0)[0]
    n = np.cross(a, b)
    if np.linalg.norm(n) < 1e-9:
        return None
    ang = g.angle_between_deg(n, camera.view_dir_board)
    return None if ang is None else min(ang, 180.0 - ang)


def validate_scene(scene_dir: Path, source_plant_id: str, view_filter: Sequence[str] | None = None,
                   capture_id: str | None = None) -> tuple[list[dict[str, str]], list[dict[str, str]]]:
    """Side rows (2-D measured from projected truth) + per (view, compound, quantity) errors vs 3-D truth.

    The views of one R.1 scene are one side capture session: every row carries ``capture_id`` (default:
    the scene folder name) and its own ``view_id``, so :func:`select_views` picks one view per compound."""
    capture = capture_id or Path(scene_dir).name
    from tomato3d.synth.sideview import camera_relative_to_quadrant

    plant = ft.load_plant(scene_dir, source_plant_id)
    to_board = _placement(scene_dir)
    cams = load_cameras(scene_dir)
    gen_to_vertex = {c.gen_compound_id: plant.compound_vertex_id(c) for c in plant.compounds}
    rows: list[dict[str, str]] = []
    errors: list[dict[str, str]] = []
    for cam in cams:
        if view_filter is not None and cam.name not in view_filter:
            continue
        labels_path = Path(scene_dir) / "views" / cam.name / "labels.json"
        labels = json.loads(labels_path.read_text(encoding="utf-8")) if labels_path.exists() else None
        label_by = {c["compound_id"]: c for c in (labels or {}).get("compounds", [])}
        protocol = labels["protocol_azimuth_deg"] if labels else None
        for comp in plant.compounds:
            pts = ft.compound_points(plant, comp)
            if not pts.nodes:
                continue
            proj = lambda p: image_to_up(cam.project(to_board(p))[0])  # noqa: E731
            sp = SidePoints(p0=proj(pts.p0), nodes=[proj(n) for n in pts.nodes], end=proj(pts.rachis_end),
                            stem_up=proj(pts.p0 + STEM_UP_OFFSET_MM * pts.stem_above_dir
                                         / np.linalg.norm(pts.stem_above_dir)))
            measured = measure(sp)
            lab = label_by.get(comp.gen_compound_id)
            quadrant = None
            direction = UNAVAILABLE
            if lab is not None:
                direction = "unclear" if lab.get("excluded_boundary") or lab.get("excluded_occluded") else lab["cls"]
            if direction not in (UNAVAILABLE, "unclear"):
                quadrant = camera_relative_to_quadrant(direction, protocol)
            cid = gen_to_vertex[comp.gen_compound_id]
            rows.append(side_row(source_plant_id, capture, cam.name, cid, measured, POINTS_SOURCE_FIXTURE,
                                 "synthetic_fixture", "derived", quadrant, "derived" if quadrant else UNAVAILABLE,
                                 direction))
            truth = truth_values(pts)
            view_angle = _insertion_plane_view_angle(pts, to_board, cam)
            pairs = [("compound_insertion_angle_deg", measured["compound_insertion_angle_deg"],
                      truth["compound_insertion_angle_deg"]),
                     ("rachis_curvature_deg", measured["rachis_curvature_deg"], truth["rachis_curvature_deg"]),
                     ("rachis_bend_theta_deg", measured["rachis_bend_theta_deg"], truth["rachis_bend_theta_deg"]),
                     ("chord_to_path_ratio", measured["chord_to_path_ratio"], truth["chord_to_path_ratio"])]
            for i, (ma, ta) in enumerate(zip(measured["alphas"] or [], truth["alphas"] or []), start=1):
                pairs.append((f"rachis_bend_alpha_{i}_deg", ma, ta))
            for qty, m, t in pairs:
                if m is None or t is None:
                    continue
                errors.append(dict(scene=Path(scene_dir).name, view_id=cam.name, compound_id=cid,
                                   direction_class=direction, quantity=qty,
                                   measured_2d=s.fmt(m, 3), truth_3d=s.fmt(t, 3), error=s.fmt(m - t, 3),
                                   insertion_plane_view_angle_deg=s.fmt(view_angle, 2),
                                   quadrant_label=str(quadrant) if quadrant else UNAVAILABLE,
                                   quadrant_gt=str(lab["quadrant_gt"]) if lab else UNAVAILABLE))
    return rows, errors


SIDE_ERROR_COLUMNS = ("scene", "view_id", "compound_id", "direction_class", "quantity", "measured_2d", "truth_3d", "error",
                      "insertion_plane_view_angle_deg", "quadrant_label", "quadrant_gt")


def summarize_errors(errors: Sequence[Mapping[str, str]], bins_deg: Sequence[float]) -> list[dict[str, str]]:
    """Median / p90 absolute error per quantity and view-angle bin (bins are reporting edges)."""
    out = []
    quantities = sorted({e["quantity"] for e in errors})
    for qty in quantities:
        sel = [e for e in errors if e["quantity"] == qty]
        for lo, hi in zip(bins_deg[:-1], bins_deg[1:]):
            vals = [abs(float(e["error"])) for e in sel
                    if e["insertion_plane_view_angle_deg"] != UNAVAILABLE
                    and lo <= float(e["insertion_plane_view_angle_deg"]) < hi]
            out.append(dict(quantity=qty, view_angle_bin_deg=f"[{lo:g},{hi:g})", n=str(len(vals)),
                            median_abs_error=s.fmt(float(np.median(vals)), 3) if vals else UNAVAILABLE,
                            p90_abs_error=s.fmt(float(np.percentile(vals, 90)), 3) if vals else UNAVAILABLE))
    for qty in quantities:
        for cls in ("cl_left", "cl_right", "cl_toward", "cl_away", "unclear"):
            vals = [abs(float(e["error"])) for e in errors if e["quantity"] == qty and e["direction_class"] == cls]
            out.append(dict(quantity=qty, view_angle_bin_deg=f"class:{cls}", n=str(len(vals)),
                            median_abs_error=s.fmt(float(np.median(vals)), 3) if vals else UNAVAILABLE,
                            p90_abs_error=s.fmt(float(np.percentile(vals, 90)), 3) if vals else UNAVAILABLE))
    quad = [e for e in errors if e["quantity"] == "compound_insertion_angle_deg"
            and e["quadrant_label"] != UNAVAILABLE and e["quadrant_gt"] != UNAVAILABLE]
    exact = sum(e["quadrant_label"] == e["quadrant_gt"] for e in quad)
    out.append(dict(quantity="blade_azimuth_quadrant", view_angle_bin_deg="all", n=str(len(quad)),
                    median_abs_error=UNAVAILABLE, p90_abs_error=f"exact {exact}/{len(quad)}"))
    return out


SIDE_SUMMARY_COLUMNS = ("quantity", "view_angle_bin_deg", "n", "median_abs_error", "p90_abs_error")
RULE_SUMMARY_COLUMNS = ("quantity", "selection", "n_compounds", "median_abs_error", "p90_abs_error",
                        "compounds_without_side_on_view")


def rule_summary(errors: Sequence[Mapping[str, str]]) -> list[dict[str, str]]:
    """Per compound: |error| of the MTG A3 view (first cl_left/cl_right view by view_id) vs the first view."""
    out = []
    for qty in sorted({e["quantity"] for e in errors}):
        by: dict[tuple[str, str], list[Mapping[str, str]]] = {}
        for e in errors:
            if e["quantity"] == qty:
                by.setdefault((e["scene"], e["compound_id"]), []).append(e)
        first, rule, missing = [], [], 0
        for es in by.values():
            es = sorted(es, key=lambda e: e["view_id"])
            first.append(abs(float(es[0]["error"])))
            side_on = [e for e in es if e["direction_class"] in SIDE_ON_CLASSES]
            if side_on:
                rule.append(abs(float(side_on[0]["error"])))
            else:
                missing += 1
        for name, vals in (("first_view", first), ("mtg_a3_side_on", rule)):
            out.append(dict(quantity=qty, selection=name, n_compounds=str(len(vals)),
                            median_abs_error=s.fmt(float(np.median(vals)), 3) if vals else UNAVAILABLE,
                            p90_abs_error=s.fmt(float(np.percentile(vals, 90)), 3) if vals else UNAVAILABLE,
                            compounds_without_side_on_view=str(missing) if name == "mtg_a3_side_on" else "0"))
    return out

HUMAN_POINT_COLUMNS = ("plant_instance_id", "capture_id", "view_id", "compound_id", "point", "u_px", "v_px",
                       "labeled_by")


def from_human_points(rows: Sequence[Mapping[str, str]], evidence: str = "real_photo",
                      direction_class_of: Mapping[tuple[str, str, str], str] | None = None) -> list[dict[str, str]]:
    """Real path: human-clicked points (``side_points.csv``) -> side rows (status ``photo_estimate``).
    ``direction_class_of`` maps (capture_id, view_id, compound_id) to the human direction label."""
    groups: dict[tuple[str, str, str, str], dict[str, np.ndarray]] = {}
    for r in rows:
        key = (r["plant_instance_id"], r["capture_id"], r["view_id"], r["compound_id"])
        groups.setdefault(key, {})[r["point"]] = image_to_up(np.array([float(r["u_px"]), float(r["v_px"])]))
    out = []
    for (pid, cap, view, cid), pts in sorted(groups.items()):
        nodes = [pts[k] for k in sorted((k for k in pts if k.startswith("N")), key=lambda k: int(k[1:]))]
        if "P0" not in pts or "END" not in pts or "STEM_UP" not in pts or not nodes:
            continue
        values = measure(SidePoints(pts["P0"], nodes, pts["END"], pts["STEM_UP"]))
        direction = (direction_class_of or {}).get((cap, view, cid), UNAVAILABLE)
        out.append(side_row(pid, cap, view, cid, values, POINTS_SOURCE_HUMAN, evidence, "photo_estimate", None,
                            UNAVAILABLE, direction))
    return out
