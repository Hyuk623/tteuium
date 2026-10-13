"""Partial leaf patches retain depth without masquerading as complete contours."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import numpy as np

from tools import manual_leaf_preview as preview_tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case


def mark_partial(annotation_path: Path) -> dict:
    annotation = common.read_json(annotation_path)
    leaf = annotation["leaflets"][0]
    leaf.update(
        outline_completeness="partial_observed_patch",
        surface_interpretation="Observed right-side patch; hidden margin and whole-leaf area unavailable.",
        review_notes=["The closing edge crosses the blade interior."],
        correspondence_status="candidate_unreviewed",
    )
    common.write_json(annotation_path, annotation)
    return annotation


def test_partial_patch_retains_landmarks_mesh_and_depth_but_not_complete_contour(
    fragment_case: tuple[Path, Path, Path],
) -> None:
    capture_path, annotation_path, out = fragment_case
    annotation = mark_partial(annotation_path)
    preview_tool.build(capture_path, annotation_path, out)

    points = common.rows(out / "points.candidate.csv")
    patches = common.rows(out / "partial_patch_boundaries.candidate.csv")
    assert len(points) == len(patches) == 6
    assert {r["leaflet_id"] for r in points + patches} == {"L3D"}
    assert {r["image_file"] for r in points} == {"photo_0.png", "photo_1.png"}
    assert common.rows(out / "contours.candidate.csv") == []
    for point, patch in zip(points, patches):
        assert point["image_file"] == patch["image_file"]
        assert point["boundary_index"] == patch["vertex_index"]
        assert (point["x_px"], point["y_px"]) == (patch["x_px"], patch["y_px"])

    saved = common.read_json(out / "preview.json")
    assert saved["modeled_leaflets"] == 1
    leaf = saved["geometry"][0]
    assert leaf["leaflet_id"] == "L3D" and len(leaf["faces"]) == 1
    np.testing.assert_allclose(
        leaf["vertices_mm"], [[-15., 0., 100.], [15., 0., 100.], [0., 15., 100.]], atol=1e-7,
    )
    for field in ("outline_completeness", "surface_interpretation", "review_notes", "correspondence_status"):
        assert leaf[field] == annotation["leaflets"][0][field]
    assert not leaf["validated_metric"] and not saved["suitable_for_ppfd"]
    assert "element vertex 3\n" in (out / "leaf_preview_mm.ply").read_text(encoding="ascii")

    depth_rows = common.rows(out / "leaf_depth_observations.csv")
    assert len(depth_rows) == 6
    assert {r["leaflet_id"] for r in depth_rows} == {"L3D"}
    assert {r["image_file"] for r in depth_rows} == {"photo_0.png", "photo_1.png"}
    assert {r["depth_status"] for r in depth_rows} == {"experimental_unvalidated"}
    assert all(float(r["camera_axis_z_mm"]) > 0 and float(r["camera_range_mm"]) > 0 for r in depth_rows)
    assert {r["leaflet_id"] for r in common.rows(out / "visible_fragments.candidate.csv")} == {"F2D"}


def test_partial_patch_with_unknown_pose_keeps_labels_and_reports_unavailable_depth(
    fragment_case: tuple[Path, Path, Path],
) -> None:
    capture_path, annotation_path, out = fragment_case
    annotation = mark_partial(annotation_path)
    unknown = deepcopy(annotation["leaflets"][0]["observations"][0])
    unknown["image_file"] = "photo_2.png"
    annotation["leaflets"][0]["observations"].append(unknown)
    common.write_json(annotation_path, annotation)
    preview_tool.build(capture_path, annotation_path, out)

    saved = common.read_json(out / "preview.json")
    assert saved["geometry"] == [] and saved["modeled_leaflets"] == 0
    assert saved["diagnostics"][0]["reason"] == "no_measured_pose"
    assert len(common.rows(out / "points.candidate.csv")) == 9
    assert len(common.rows(out / "partial_patch_boundaries.candidate.csv")) == 9
    assert common.rows(out / "contours.candidate.csv") == []

    depth_rows = common.rows(out / "leaf_depth_observations.csv")
    assert len(depth_rows) == 9 and {r["leaflet_id"] for r in depth_rows} == {"L3D"}
    unknown_rows = [r for r in depth_rows if r["image_file"] == "photo_2.png"]
    assert len(unknown_rows) == 3
    for row in unknown_rows:
        assert row["pose_status"] == "failed" and row["depth_status"] == "geometry_unavailable"
        for field in ("x_board_mm", "y_board_mm", "z_board_mm", "camera_axis_z_mm", "camera_range_mm",
                      "projected_x_px", "projected_y_px", "reprojection_error_px"):
            assert row[field] == "unavailable"
