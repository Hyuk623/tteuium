"""Visible-only outlines stay separate from physical correspondences and meshes."""
from __future__ import annotations

from pathlib import Path

import numpy as np
from PIL import Image
import pytest

from tools import manual_leaf_preview as preview_tool
from tools.leaf_light import common
from tools.leaf_light.reconstruction import project
from tools.tests.test_manual_leaf_preview import inputs


@pytest.fixture
def fragment_case(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    _, observations, intrinsics, quality = inputs()
    quality["contour_tolerance_px"] = 3.
    frames = [entry[0] for entry in observations]
    frames.append(dict(image_file="unsolved.png", pose_status="failed", passes_pose_gate=False,
                       rvec_rad=None, tvec_mm=None, n_corners_detected=4, failure_reason="too_few_corners"))
    for index, frame in enumerate(frames):
        frame["image_file"] = f"photo_{index}.png"
        path = tmp_path / frame["image_file"]
        Image.new("RGB", (intrinsics["image_width_px"], intrinsics["image_height_px"]), (30, 40, 50)).save(path)
        frame.update(image_path=str(path), sha256=common.file_hash(path))
    board_path = preview_tool.get_settings().board_spec_path
    capture = dict(schema_version="diagnostic-preview-capture-1", intrinsics=intrinsics, frames=frames,
                   quality=quality, board_variant_id=common.read_json(board_path)["variant_id"])
    xyz_mm = np.array([[-15., 0., 100.], [15., 0., 100.], [0., 15., 100.]])
    annotation = dict(schema_version="manual-leaf-preview-1", leaflets=[
        dict(leaflet_id="L3D", organ_id="O3D", description="Known synthetic triangle for branch regression",
             review_status="synthetic_test_only", observations=[
                 dict(image_file=frame["image_file"], label_image_size_px=[1600, 1200],
                      boundary_xy_px=project(xyz_mm, frame, intrinsics).tolist()) for frame in frames[:2]
             ])], two_d_only_candidates=[
        dict(leaflet_id="F2D", organ_id="O2D", description="Visible fragment without established identity",
             review_status="candidate_unreviewed", image_file="photo_2.png", label_image_size_px=[800, 600],
             boundary_xy_px=[[250., 150.], [300., 150.], [300., 180.], [250., 180.]])])
    capture_path, annotation_path = tmp_path / "capture.json", tmp_path / "annotations.json"
    common.write_json(capture_path, capture)
    common.write_json(annotation_path, annotation)
    monkeypatch.setattr(common, "BUILD", tmp_path / "build")
    return capture_path, annotation_path, tmp_path / "build" / "preview"


def test_fragment_exports_visible_pixels_without_3d_or_correspondence(fragment_case: tuple[Path, Path, Path]) -> None:
    capture_path, annotation_path, out = fragment_case
    result = preview_tool.build(capture_path, annotation_path, out)
    fragments = common.rows(out / "visible_fragments.candidate.csv")
    assert len(fragments) == 4 and {r["leaflet_id"] for r in fragments} == {"F2D"}
    assert float(fragments[0]["x_px"]) == 500. and float(fragments[0]["y_px"]) == 300.
    assert {r["geometry_status"] for r in fragments} == {"2d_only"}
    assert {r["depth_status"] for r in fragments} == {"unavailable"}
    assert {r["correspondence_status"] for r in fragments} == {"not_a_landmark"}
    assert {r["surface_extent"] for r in fragments} == {"visible_fragment_only"}
    for filename in ("points.candidate.csv", "contours.candidate.csv", "landmark_fit.csv"):
        records = common.rows(out / filename)
        assert records and {r["leaflet_id"] for r in records} == {"L3D"}
    saved = common.read_json(out / "preview.json")
    assert [leaf["leaflet_id"] for leaf in saved["geometry"]] == ["L3D"]
    assert saved["modeled_leaflets"] == 1 and saved["annotated_photos"] == 3
    fragment = saved["two_d_only_candidates"][0]
    assert fragment["source_images"] == ["photo_2.png"] and fragment["cross_view_identity"] == "unconfirmed"
    assert fragment["depth_status"] == "unavailable" and "vertices_mm" not in fragment
    assert not result["validated_metric"] and not result["deep_learning_run"]
    ply_text = (out / "leaf_preview_mm.ply").read_text(encoding="ascii")
    assert "element vertex 3\n" in ply_text
    with Image.open(out / "photo_2_review.jpg") as overlay:
        # The unsolved photo still receives a visible magenta outline at its rescaled original-pixel location.
        red, green, blue = overlay.convert("RGB").getpixel((400, 225))
        assert red > green + 30 and blue > green + 30
    html = (out / "index.html").read_text(encoding="utf-8")
    assert '"leaflet_id": "F2D"' in html and '"geometry_status": "2d_only"' in html


def test_two_labeled_views_do_not_make_fragment_vertices_physical_correspondences(fragment_case):
    capture_path, annotation_path, out = fragment_case
    annotation = common.read_json(annotation_path)
    fragment = annotation['two_d_only_candidates'][0]
    entry = {key:fragment.pop(key) for key in ('image_file','label_image_size_px','boundary_xy_px')}
    fragment['observations'] = [entry, dict(entry,image_file='photo_0.png',
        boundary_xy_px=[[250,150],[300,150],[310,165],[300,180],[250,180]])]
    common.write_json(annotation_path, annotation)
    result = preview_tool.build(capture_path, annotation_path, out)
    assert result['two_d_only_candidates'][0]['source_images']==['photo_2.png','photo_0.png']
    assert len(common.rows(out/'visible_fragments.candidate.csv')) == 9
    assert {r['leaflet_id'] for r in common.rows(out/'leaf_depth_observations.csv')} == {'L3D'}
    assert [g['leaflet_id'] for g in common.read_json(out/'preview.json')['geometry']] == ['L3D']


@pytest.mark.parametrize("mutation,message", [
    ("unknown_image", "unknown fragment image"),
    ("duplicate_fragment", "Duplicate leaflet ID"),
    ("collision_with_3d", "Duplicate leaflet ID"),
    ("negative_pixel", "outside_original_image"),
    ("edge_pixel", "outside_original_image"),
    ("nonfinite_pixel", "Invalid annotation polygon"),
])
def test_invalid_fragment_rejected(fragment_case: tuple[Path, Path, Path], mutation: str, message: str) -> None:
    capture_path, annotation_path, out = fragment_case
    annotation = common.read_json(annotation_path)
    fragment = annotation["two_d_only_candidates"][0]
    if mutation == "unknown_image":
        fragment["image_file"] = "not_captured.png"
    elif mutation == "duplicate_fragment":
        annotation["two_d_only_candidates"].append(dict(fragment))
    elif mutation == "collision_with_3d":
        fragment["leaflet_id"] = "L3D"
    elif mutation == "negative_pixel":
        fragment["boundary_xy_px"][0][0] = -1.
    elif mutation == "edge_pixel":
        fragment["boundary_xy_px"][0][0] = 800.
    else:
        # A parseable non-finite coordinate is rejected before geometry or drawing.
        fragment["boundary_xy_px"][0][0] = "nan"
    common.write_json(annotation_path, annotation)
    with pytest.raises(common.StudyError, match=message):
        preview_tool.build(capture_path, annotation_path, out)
    assert not (out / "preview.json").exists()
    assert not (out / "leaf_preview_mm.ply").exists()
