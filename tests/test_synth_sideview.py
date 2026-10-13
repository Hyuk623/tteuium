"""Side-view direction labels (Prompt R): bins, boundary exclusion, the clockwise quadrant converter,
the image-right sign convention against the renderer's projection, and label extraction on a toy scene.

Needs only numpy/OpenCV (project environment).
"""

from __future__ import annotations

import json
import math
from pathlib import Path

import numpy as np
import pytest

from tomato3d.synth import sideview as sv
from tomato3d.synth.camera import build_render_geometry, project_render

PROJECT_ROOT = Path(__file__).resolve().parents[1]
O_CELL = PROJECT_ROOT / "build/synthetic_dwarf_tomato_20261008_07/O-mature"
K512 = np.array([[800.0, 0.0, 255.5], [0.0, 800.0, 255.5], [0.0, 0.0, 1.0]])
ZERO_DIST = np.zeros(5)


def _geom(view):
    return build_render_geometry(view, 512, tolerance_px=0.5, iterations=100, max_canvas_scale=1.6)


def test_wrap_and_bins():
    assert sv.wrap_deg(180.0) == 180.0 and sv.wrap_deg(-180.0) == 180.0 and sv.wrap_deg(540.0) == 180.0
    assert sv.wrap_deg(-190.0) == 170.0 and sv.wrap_deg(10.0) == 10.0
    expect = {0: "cl_toward", 44.9: "cl_toward", 45: "cl_toward", 46: "cl_right", 90: "cl_right", 134: "cl_right",
              135: "cl_away", 180: "cl_away", -135: "cl_away", -134: "cl_left", -90: "cl_left", -46: "cl_left",
              -45: "cl_toward", 270: "cl_left", 225: "cl_away"}
    for d, cls in expect.items():
        assert sv.camera_relative_class(d) == cls, d
    assert sv.boundary_distance_deg(0) == 45.0 and sv.boundary_distance_deg(90) == 45.0
    assert sv.boundary_distance_deg(44) == 1.0 and sv.boundary_distance_deg(-136) == 1.0
    assert sv.camera_relative_bin(35.0)["excluded_boundary"] is True        # distance 10 -> excluded (<=)
    assert sv.camera_relative_bin(36.0)["excluded_boundary"] is True
    assert sv.camera_relative_bin(34.0, exclusion_deg=10.0)["excluded_boundary"] is False
    assert sv.camera_relative_bin(125.0)["excluded_boundary"] is True
    assert sv.camera_relative_bin(100.0)["excluded_boundary"] is False


def test_quadrant_faces_the_view_k_camera():
    phi0 = 270.0                                   # view-0 camera south of the plant
    for k in range(4):
        theta = sv.wrap_deg(phi0 - 90 * k)         # pointing straight at the view-k camera position
        assert sv.quadrant_from_direction(theta, phi0) == k + 1
        assert sv.quadrant_from_direction(theta + 44.9, phi0) == k + 1
        assert sv.quadrant_from_direction(theta - 44.9, phi0) == k + 1
    assert sv.camera_relative_to_quadrant("cl_toward", 0) == 1
    assert sv.camera_relative_to_quadrant("cl_toward", 90) == 2
    assert sv.camera_relative_to_quadrant("cl_left", 0) == 2
    assert sv.camera_relative_to_quadrant("cl_right", 0) == 4
    assert sv.camera_relative_to_quadrant("cl_away", 0) == 3
    assert sv.camera_relative_to_quadrant("cl_right", 90) == 1
    with pytest.raises(ValueError):
        sv.camera_relative_to_quadrant("compound_unclear", 0)
    with pytest.raises(ValueError):
        sv.camera_relative_to_quadrant("cl_toward", 45)


def test_converter_exact_on_non_excluded_samples():
    rng = np.random.default_rng(20261009)
    n, excluded, mismatches_if_wider = 0, 0, 0
    for _ in range(20000):
        theta, phi0 = rng.uniform(-180, 180), rng.uniform(-180, 180)
        a = int(rng.choice(sv.PROTOCOL_AZIMUTHS_DEG))
        jitter = rng.uniform(-10, 10)
        phi = sv.wrap_deg(phi0 - a + jitter)
        b = sv.camera_relative_bin(theta - phi, exclusion_deg=10.0)
        gt = sv.quadrant_from_direction(theta, phi0)
        if b["excluded_boundary"]:
            excluded += 1
            continue
        n += 1
        assert sv.camera_relative_to_quadrant(b["cls"], a) == gt
        # with a narrower band than the jitter the converter would not be exact: the band is load-bearing
        if sv.camera_relative_bin(theta - phi, exclusion_deg=0.0)["cls"] != b["cls"]:
            mismatches_if_wider += 1
    assert n > 10000 and excluded > 0
    # a sample at the raw boundary with jitter can flip class; verify the exclusion band actually removes such
    flips = 0
    for _ in range(20000):
        theta, phi0 = rng.uniform(-180, 180), rng.uniform(-180, 180)
        a = int(rng.choice(sv.PROTOCOL_AZIMUTHS_DEG))
        phi = sv.wrap_deg(phi0 - a + rng.uniform(-10, 10))
        cls = sv.camera_relative_class(theta - phi)
        if sv.camera_relative_to_quadrant(cls, a) != sv.quadrant_from_direction(theta, phi0):
            flips += 1
    assert flips > 0                                 # without exclusion the converter is NOT exact


def test_image_right_sign_against_projection():
    target = np.zeros(3)
    phi = 270.0                                          # camera south (-Y), looking +Y
    center = sv.camera_center_mm(target, phi, 25.0, 300.0)
    view = sv.look_at_view("t/0", center_mm=center, target_mm=target, camera_matrix=K512, dist_coeffs=ZERO_DIST,
                           image_size_px=(512, 512))
    assert abs(sv.camera_azimuth_deg(view, target) - (-90.0)) < 1e-9
    assert abs(view.elevation_deg - 25.0) < 1e-9
    R, t = view.rotation, view.translation
    right = np.array([[50.0, 0.0, 0.0]])                 # theta = 0 = phi + 90 -> cl_right
    left = np.array([[-50.0, 0.0, 0.0]])
    (pr, _), (pl_, _) = project_render(right, R, t, K512), project_render(left, R, t, K512)
    assert pr[0, 0] > K512[0, 2] > pl_[0, 0]
    assert sv.camera_relative_class(0.0 - sv.camera_azimuth_deg(view, target)) == "cl_right"
    assert sv.camera_relative_class(180.0 - sv.camera_azimuth_deg(view, target)) == "cl_left"
    up = np.array([[0.0, 0.0, 50.0]])
    (pu, _) = project_render(up, R, t, K512)
    assert pu[0, 1] < K512[1, 2]                         # +Z is image-up (y down)


def test_plan_side_cameras_is_clockwise_and_jittered():
    geometry = dict(view0_camera_azimuth_deg=270.0, elevation_deg=25.0, elevation_jitter_deg=5.0,
                    azimuth_jitter_deg=10.0, distance_mm=331.0)
    plan = sv.plan_side_cameras(7, geometry)
    assert [p["protocol_azimuth_deg"] for p in plan] == [0, 90, 180, 270]
    for p in plan:
        nominal = sv.wrap_deg(270.0 - p["protocol_azimuth_deg"])
        assert abs(sv.wrap_deg(p["camera_azimuth_deg"] - nominal)) <= 10.0
        assert abs(p["elevation_deg"] - 25.0) <= 5.0
    assert plan == sv.plan_side_cameras(7, geometry)                     # reproducible
    assert plan != sv.plan_side_cameras(8, geometry)
    # view 90 sits clockwise (seen from above) of view 0: azimuth decreases by 90 in the CCW convention
    assert abs(sv.wrap_deg(sv.wrap_deg(270.0 - 90.0) - 180.0)) < 1e-9


def _quad(x0, x1, y0, y1, z0, z1, name, organ, const_axis):
    if const_axis == "y":
        v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y0, z1], [x0, y0, z1]], float)
    elif const_axis == "x":
        v = np.array([[x0, y0, z0], [x0, y1, z0], [x0, y1, z1], [x0, y0, z1]], float)
    else:
        v = np.array([[x0, y0, z0], [x1, y0, z0], [x1, y1, z0], [x0, y1, z0]], float)
    return dict(name=name, organ=organ, instance=0, vertices=v, faces=np.array([(0, 1, 2), (0, 2, 3)]))


def _toy_scene():
    heading_x, heading_my = [1.0, 0.0, 0.0], [0.0, -1.0, 0.0]
    graph = dict(plant_id="toy", stem=dict(points_mm=[[0, 0, 0], [0, 0, 40]]),
                 compounds=[dict(compound_id="L01", rank_from_bottom=1, direction_unit=heading_x),
                            dict(compound_id="L02", rank_from_bottom=2, direction_unit=heading_my)],
                 interiors=dict(L01=dict(leaflets=[dict(tag="T", heading=heading_x)]),
                                L02=dict(leaflets=[dict(tag="T", heading=heading_my)])),
                 placement=dict(pot_center_board_mm=[0.0, 0.0, 0.0], soil_z_board_mm=0.0, plant_rotation_deg=0.0))
    parts = [
        _quad(-2, 2, 0, 0, 0, 40, "stem", "stem", "y"),                      # vertical strip in the x-z plane
        _quad(-2, 2, 0, 0, 40, 44, "apex", "apex", "y"),
        _quad(5, 20, 0, 0, 29, 31, "rachis_L01", "rachis", "y"),
        _quad(20, 45, -8, 8, 30, 30, "toy/L01/T", "leaflet", "z"),           # flat leaflet pointing +X
        _quad(0, 0, -20, -5, 19, 21, "rachis_L02", "rachis", "x"),
        _quad(-8, 8, -45, -20, 20, 20, "toy/L02/T", "leaflet", "z"),         # flat leaflet pointing -Y
        _quad(-100, 100, -100, 100, -1, -1, "board", "board", "z"),
    ]
    return graph, parts


def test_view_labels_toy_scene_and_exports():
    graph, parts = _toy_scene()
    target = np.array([0.0, 0.0, 20.0])
    phi0 = 270.0
    center = sv.camera_center_mm(target, phi0, 25.0, 300.0)
    view = sv.look_at_view("synside/toy/000", center_mm=center, target_mm=target, camera_matrix=K512,
                           dist_coeffs=ZERO_DIST, image_size_px=(512, 512))
    labels, layers = sv.view_labels(graph, parts, view, _geom(view), protocol_azimuth_deg=0,
                                    view0_camera_azimuth_deg=phi0, target_mm=target, exclusion_deg=10.0,
                                    min_visible_px=20)
    by_id = {c["compound_id"]: c for c in labels["compounds"]}
    assert set(by_id) == {"L01", "L02"} and not labels["excluded_occluded"]
    assert by_id["L02"]["cls"] == "cl_toward" and by_id["L02"]["quadrant_gt"] == 1
    assert by_id["L01"]["cls"] == "cl_right" and by_id["L01"]["quadrant_gt"] == 4
    assert by_id["L01"]["direction_source"] == "terminal_leaflet_heading"
    for c in labels["compounds"]:
        assert sv.camera_relative_to_quadrant(c["cls"], 0) == c["quadrant_gt"]
        assert c["box_xyxy"] is not None and c["visible_px"] > 0 and 0 < c["vis_frac"] <= 1.0
    x0, _, x1, _ = by_id["L01"]["box_xyxy"]
    assert (x0 + x1) / 2 > 256                                    # the +X leaflet lies on the image right
    assert by_id["L01"]["box_xyxy"][0] > by_id["L02"]["box_xyxy"][0]
    # the rachis pixels belong to the compound instance, the stem and the apex to their own instances
    inst = labels["instances"]
    assert (layers.visible == inst["L01"]).sum() == by_id["L01"]["visible_px"]
    assert labels["main_stem"]["box_xyxy"] is not None and labels["growth_shoot"]["box_xyxy"] is not None
    assert labels["growth_shoot"]["box_xyxy"][1] < labels["main_stem"]["box_xyxy"][1]   # shoot above the stem top
    assert (layers.organ == 8).sum() == 0                           # board dropped from the label raster
    lines = sv.yolo_lines(labels)
    assert len(lines) == 4 and {int(l.split()[0]) for l in lines} == {0, 1, 4, 5}
    for l in lines:
        vals = [float(x) for x in l.split()[1:]]
        assert all(0.0 <= v <= 1.0 for v in vals)
    anns = sv.coco_annotations(labels, 1, 1)
    assert [a["id"] for a in anns] == [1, 2, 3, 4] and all(a["area"] > 0 for a in anns)
    rows = sv.manifest_rows(labels, "x/rgb.png")
    assert len(rows) == 2 and all(r["quadrant_from_converter"] == r["quadrant_gt"] for r in rows)
    assert set(rows[0]) == set(sv.MANIFEST_COLUMNS)


def test_boundary_excluded_compound_goes_to_unclear_class():
    graph, parts = _toy_scene()
    target = np.array([0.0, 0.0, 20.0])
    phi0 = 270.0 + 40.0          # view-0 camera rotated so that L02 (theta -90) sits 40 deg off -> delta = -40
    center = sv.camera_center_mm(target, phi0, 25.0, 300.0)
    view = sv.look_at_view("synside/toy/000", center_mm=center, target_mm=target, camera_matrix=K512,
                           dist_coeffs=ZERO_DIST, image_size_px=(512, 512))
    labels, _ = sv.view_labels(graph, parts, view, _geom(view), protocol_azimuth_deg=0,
                               view0_camera_azimuth_deg=phi0, target_mm=target, exclusion_deg=10.0,
                               min_visible_px=20)
    by_id = {c["compound_id"]: c for c in labels["compounds"]}
    assert by_id["L02"]["excluded_boundary"] is True and abs(by_id["L02"]["delta_deg"] - (-40.0)) < 1e-6
    # L01 (theta 0) sits at delta +50, 5 deg from the 45 boundary: excluded as well
    assert sorted(e["compound_id"] for e in labels["excluded_boundary"]) == ["L01", "L02"]
    classes = {int(l.split()[0]) for l in sv.yolo_lines(labels)}
    assert classes == {sv.YOLO_CLASSES.index("compound_unclear"), 4, 5}
    rows = {r["compound_id"]: r for r in sv.manifest_rows(labels, "x")}
    assert rows["L02"]["quadrant_from_converter"] == "" and rows["L02"]["excluded_boundary"] == 1


@pytest.mark.skipif(not (O_CELL / "scenes").exists(), reason="O-mature cell not on this machine")
def test_converter_exact_on_O_mature_plant_graphs():
    """R.3 dry run on real generator GT (plant graphs only, nothing rendered): every non-excluded
    compound/view pair converts to the GT quadrant under the declared camera plan."""
    geometry = dict(view0_camera_azimuth_deg=270.0, elevation_deg=25.0, elevation_jitter_deg=5.0,
                    azimuth_jitter_deg=10.0, distance_mm=331.0)
    checked, excluded, sources = 0, 0, set()
    for gp in sorted(O_CELL.glob("scenes/scene_*/plant_graph.json")):
        graph = json.loads(gp.read_text(encoding="utf-8"))
        seed = int(graph["seed"])
        for cam in sv.plan_side_cameras(seed, geometry):
            for comp in graph["compounds"]:
                d = sv.compound_direction_deg(graph, comp["compound_id"])
                sources.add(d["source"])
                b = sv.camera_relative_bin(d["theta_deg"] - cam["camera_azimuth_deg"], 10.0)
                gt = sv.quadrant_from_direction(d["theta_deg"], geometry["view0_camera_azimuth_deg"])
                if b["excluded_boundary"]:
                    excluded += 1
                    continue
                assert sv.camera_relative_to_quadrant(b["cls"], cam["protocol_azimuth_deg"]) == gt
                checked += 1
    assert checked > 100 and sources == {"terminal_leaflet_heading"}
    assert 0.15 < excluded / (checked + excluded) < 0.35          # 4 bands x 20 deg of 360 = 22 % expected


def test_effective_contract_applies_overrides_in_order():
    raw = dict(camera_geometry=dict(distance_mm=270.0, look_at_target=dict(height_fraction=0.85)),
               amendments=[dict(id="A1", overrides={}),
                           dict(id="A2", overrides={"camera_geometry.look_at_target.height_fraction": 0.9}),
                           dict(id="A3", overrides={"camera_geometry.look_at_target.height_fraction": 0.8})])
    c = sv.effective_contract(raw)
    assert c["camera_geometry"]["look_at_target"]["height_fraction"] == 0.8
    assert raw["camera_geometry"]["look_at_target"]["height_fraction"] == 0.85        # declared text untouched
    with pytest.raises(KeyError):
        sv.effective_contract(dict(camera_geometry={}, amendments=[dict(id="X", overrides={"camera_geometry.nope": 1})]))


def test_plant_frame_stats_matches_the_real_photo_statistic():
    organ = np.zeros((100, 100), np.uint8)
    organ[40:60, 20:80] = sv.ORGAN_CLASSES["leaflet"]
    organ[60:90, 48:52] = sv.ORGAN_CLASSES["stem"]
    organ[90:100, :] = sv.ORGAN_CLASSES["pot"]                     # pot/soil are not plant
    s = sv.plant_frame_stats(organ)
    assert s["plant_frac"] == round((20 * 60 + 30 * 4) / 1e4, 4)
    assert 0.40 <= s["cy"] <= 0.70 and 0.40 <= s["bbox_h"] <= 0.50 and 0.55 <= s["bbox_w"] <= 0.60
    assert math.isnan(sv.plant_frame_stats(np.zeros((50, 50), np.uint8))["cy"])


def test_collect_rebuilds_set_files_and_checks_quadrants(tmp_path):
    graph, parts = _toy_scene()
    target = np.array([0.0, 0.0, 20.0])
    geometry = dict(view0_camera_azimuth_deg=270.0, elevation_deg=25.0, elevation_jitter_deg=5.0,
                    azimuth_jitter_deg=10.0, distance_mm=300.0)
    for s in range(2):
        sdir = tmp_path / "scenes" / f"scene_{s:04d}"
        view_rows, label_rows = [], []
        for cam in sv.plan_side_cameras(100 + s, geometry):
            center = sv.camera_center_mm(target, cam["camera_azimuth_deg"], cam["elevation_deg"], cam["distance_mm"])
            view = sv.look_at_view(f"synside/toy/{cam['protocol_azimuth_deg']:03d}", center_mm=center, target_mm=target,
                                   camera_matrix=K512, dist_coeffs=ZERO_DIST, image_size_px=(512, 512))
            labels, _ = sv.view_labels(dict(graph, plant_id=sdir.name), parts, view, _geom(view),
                                       protocol_azimuth_deg=cam["protocol_azimuth_deg"], view0_camera_azimuth_deg=270.0,
                                       target_mm=target, exclusion_deg=10.0, min_visible_px=20)
            vname = f"{cam['k']:02d}_synside_{cam['protocol_azimuth_deg']:03d}"
            labels.update(capture_rotation=sv.CAPTURE_ROTATION, view_dir=vname)
            (sdir / "views" / vname).mkdir(parents=True)
            (sdir / "views" / vname / "labels.json").write_text(json.dumps(labels), encoding="utf-8")
            label_rows += sv.manifest_rows(labels, f"scenes/{sdir.name}/views/{vname}/rgb.png")
            view_rows.append(dict(scene_id=sdir.name, view_dir=vname, n_compounds=len(labels["compounds"]),
                                  n_excluded_boundary=len(labels["excluded_boundary"]), rgb_status="pending_remote",
                                  protocol_azimuth_deg=cam["protocol_azimuth_deg"]))
        (sdir / "side_rows.json").write_text(json.dumps(dict(view_rows=view_rows, label_rows=label_rows)),
                                             encoding="utf-8")
        (sdir / "DONE").write_text("x", encoding="utf-8")
    half = tmp_path / "scenes" / "scene_0002" / "views" / "00_synside_000"      # killed mid-scene: no DONE
    half.mkdir(parents=True)
    (half / "labels.json").write_text("{}", encoding="utf-8")
    s1 = sv.collect(tmp_path)
    s2 = sv.collect(tmp_path)                                                    # idempotent: no duplicate rows
    assert s1 == s2 and s1["scenes_done"] == 2 and s1["views"] == 8 and s1["views_complete"]
    assert s1["quadrant_check"]["exact"] and s1["quadrant_check"]["checked"] > 0
    assert s1["compounds_per_plant"] == {2: 2} and s1["capture_rotation"] == "clockwise_assumed_unverified"
    lines = (tmp_path / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
    assert len(lines) == 8
    import csv as _csv
    with (tmp_path / "labels_manifest.csv").open(encoding="utf-8", newline="") as f:
        rows = list(_csv.DictReader(f))
    assert len(rows) == 16 and {r["capture_rotation"] for r in rows} == {"clockwise_assumed_unverified"}
    coco = json.loads((tmp_path / "synside_coco.json").read_text(encoding="utf-8"))
    assert len(coco["images"]) == 8 and [c["name"] for c in coco["categories"]] == list(sv.YOLO_CLASSES)
