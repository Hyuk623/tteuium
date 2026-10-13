"""Depth definitions, unavailable observations, provenance and gate regressions."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import numpy as np
import pytest

from tools import leaf_depth_records as depth
from tools.leaf_light import common
from tools.leaf_light.reconstruction import project


def fixture_records() -> tuple[dict, dict, list[dict]]:
    intrinsics = dict(camera_matrix=[[100, 0, 200], [0, 100, 200], [0, 0, 1]], dist_coeffs=[0] * 5,
                      image_width_px=400, image_height_px=400, rms_reprojection_error_px=9.)
    frames = [dict(image_file="a.png", image_path="a.png", sha256="a", pose_status="solved",
                   rvec_rad=[0., 0., 0.], tvec_mm=[10., 0., 20.], passes_pose_gate=False,
                   reprojection_error_px=9., n_corners_detected=8),
              dict(image_file="b.png", image_path="b.png", sha256="b", pose_status="solved",
                   rvec_rad=[0., np.pi / 2, 0.], tvec_mm=[0., 0., 30.], passes_pose_gate=False,
                   reprojection_error_px=8., n_corners_detected=6),
              dict(image_file="c.png", image_path="c.png", sha256="c", pose_status="failed",
                   rvec_rad=None, tvec_mm=None, passes_pose_gate=False, reprojection_error_px=None,
                   n_corners_detected=4, failure_reason="insufficient corners")]
    xyz_mm = np.array([[3., 4., 5.], [4., 4., 5.], [3., 5., 6.]])
    capture = dict(schema_version="diagnostic-preview-capture-1", plant_id="p", session_id="s",
                   board_variant_id="board-a", intrinsics=intrinsics, frames=frames,
                   quality=dict(max_point_error_px=2.))
    preview = dict(schema_version="manual-leaf-preview-result-1",
                   geometry_source="manual_multiview_landmark_interpolation", diagnostics=[],
                   geometry=[dict(leaflet_id="L1", organ_id="O1", vertices_mm=xyz_mm.tolist(),
                                  source_images=["a.png", "b.png"], review_status="candidate_unreviewed")])
    point_rows = []
    for frame in frames[:2]:
        for index, xy_px in enumerate(project(xyz_mm, frame, intrinsics)):
            point_rows.append(dict(image_file=frame["image_file"], organ_id="O1", leaflet_id="L1",
                                   point_id=f"b{index}", boundary_index=str(index),
                                   x_px=str(xy_px[0]), y_px=str(xy_px[1])))
    return capture, preview, point_rows


def test_axis_depth_range_rotation_and_height_are_distinct() -> None:
    capture, preview, points = fixture_records()
    result = depth.compile_records(capture, preview, points, {})
    first, rotated = result["observations"][0], result["observations"][3]
    assert first["z_board_mm"] == 5.
    assert first["camera_axis_z_mm"] == 25.
    assert first["camera_range_mm"] == pytest.approx(np.linalg.norm([13., 4., 25.]))
    assert rotated["camera_axis_z_mm"] == pytest.approx(27.)
    assert rotated["camera_range_mm"] == pytest.approx(np.linalg.norm([5., 4., 27.]))
    assert first["passes_point_gate"] and not first["passes_all_source_pose_gates"]
    assert not first["validated_metric"] and not first["suitable_for_ppfd"]
    assert result["leaves"][0]["min_vertex_board_height_mm"] == 5.
    assert result["leaves"][0]["max_vertex_board_height_mm"] == 6.


def test_reprojection_is_never_counted_as_observed_label() -> None:
    capture, preview, points = fixture_records()
    points.append(dict(points[0], image_file="c.png", observation_kind="projection"))
    result = depth.compile_records(capture, preview, points, {})
    assert len(result["observations"]) == 6 and result["excluded_nonmanual_rows"] == 1
    assert len(result["frames"]) == 3
    frame = result["frames"][2]
    assert frame["manual_observation_count"] == 0 and frame["labeling_status"] == "no_manual_labels"
    assert frame["camera_depth_status"] == "unavailable" and frame["pose_failure_reason"] == "insufficient corners"
    assert frame["detected_marker_ids"] is None and frame["detected_corner_ids"] is None


def test_unsolved_manually_labeled_photo_keeps_unavailable_depth() -> None:
    capture, preview, points = fixture_records()
    preview["geometry"][0]["source_images"].append("c.png")
    points.append(dict(points[0], image_file="c.png"))
    result = depth.compile_records(capture, preview, points, {})
    last = result["observations"][-1]
    assert last["depth_status"] == "camera_pose_unavailable"
    assert last["camera_axis_z_mm"] is None and last["camera_range_mm"] is None
    assert last["z_board_mm"] == 5. and last["observed_x_px"] is not None
    assert last["passes_point_gate"] is None and not last["residuals_complete"]


def test_gate_failure_and_inactive_gate_remain_honest() -> None:
    capture, preview, points = fixture_records()
    points[3]["x_px"] = str(float(points[3]["x_px"]) + 20.)
    result = depth.compile_records(capture, preview, points, {})
    assert result["landmarks"][0]["point_max_reprojection_error_px"] == pytest.approx(20.)
    assert result["landmarks"][0]["passes_point_gate"] is False
    capture["quality"]["max_point_error_px"] = None
    result = depth.compile_records(capture, preview, points, {})
    assert result["landmarks"][0]["passes_point_gate"] is None
    assert result["landmarks"][0]["point_gate_active"] is False
    assert result["landmarks"][0]["validated_metric"] is False


def test_board_evidence_is_bound_to_photograph_and_observed_ids() -> None:
    capture, preview, points = fixture_records()
    frame = capture['frames'][0]
    frame['board_evidence'] = dict(source_image_sha256=frame['sha256'], detection_status='detected',
        detected_marker_ids=[2, 7], detected_corner_ids=[5], existing_pose_charuco_rms_px=9.,
        markers=[{'marker_id':2}, {'marker_id':7}], corners=[{'corner_id':5}])
    result = depth.compile_records(capture, preview, points, {})
    assert result['observations'][0]['detected_marker_ids'] == '2;7'
    assert result['observations'][0]['detected_corner_ids'] == '5'
    assert result['frames'][0]['existing_pose_charuco_rms_px'] == 9.
    assert result['frames'][1]['detected_marker_ids'] is None
    assert not result['observations'][0]['passes_pose_gate']
    frame['board_evidence']['detected_marker_ids'].append(9)
    with pytest.raises(common.StudyError, match='ID summary'):
        depth.compile_records(capture, preview, points, {})
    frame['board_evidence']['source_image_sha256'] = 'different'
    with pytest.raises(common.StudyError, match='different photograph'):
        depth.compile_records(capture, preview, points, {})


def test_observed_empty_board_is_distinct_from_missing_evidence() -> None:
    capture, preview, points = fixture_records()
    frame = capture['frames'][2]
    frame['board_evidence'] = dict(source_image_sha256=frame['sha256'], detection_status='no_board_detected',
        detected_marker_ids=[], detected_corner_ids=[], markers=[], corners=[])
    result = depth.compile_records(capture, preview, points, {})
    assert result['frames'][2]['detected_marker_ids'] == 'none_detected'
    assert result['frames'][2]['camera_depth_status'] == 'unavailable'
    frame['board_evidence']['detection_status'] = 'detector_error'
    result = depth.compile_records(capture, preview, points, {})
    assert result['frames'][2]['detected_marker_ids'] is None


@pytest.mark.parametrize("mutation,error", [
    ("duplicate", "Duplicate manual"), ("wrong_source", "source observations"),
    ("reindex", "index changes"), ("invalid_pixel", "outside original"),
])
def test_ambiguous_or_misaligned_manual_rows_rejected(mutation: str, error: str) -> None:
    capture, preview, points = fixture_records()
    if mutation == "duplicate":
        points.append(dict(points[0]))
    elif mutation == "wrong_source":
        points[0]["image_file"] = "c.png"
    elif mutation == "reindex":
        points[3]["boundary_index"] = "1"
    else:
        points[0]["x_px"] = "-1"
    with pytest.raises(common.StudyError, match=error):
        depth.compile_records(capture, preview, points, {})


def export_fixture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path, Path]:
    capture, preview, points = fixture_records()
    calibration_path = tmp_path / "intrinsics.json"
    common.write_json(calibration_path, capture["intrinsics"])
    capture.update(intrinsics_path=str(calibration_path), intrinsics_sha256=common.file_hash(calibration_path))
    for frame in capture["frames"]:
        image_path = tmp_path / frame["image_file"]
        image_path.write_bytes(frame["image_file"].encode())
        frame.update(image_path=str(image_path), sha256=common.file_hash(image_path))
    capture_path, preview_path, points_path = (tmp_path / name for name in ("capture.json", "preview.json", "points.csv"))
    common.write_json(capture_path, capture)
    preview["capture_sha256"] = common.file_hash(capture_path)
    common.write_json(preview_path, preview)
    common.write_rows(points_path, points, depth.POINT_COLUMNS)
    board_path = tmp_path / "board.json"
    common.write_json(board_path, dict(variant_id="board-a", square_size_mm=38., physical_print_verified=False))
    monkeypatch.setattr(depth, "get_settings", lambda: SimpleNamespace(board_spec_path=board_path))
    monkeypatch.setattr(common, "BUILD", tmp_path / "build")
    return capture_path, preview_path, points_path, tmp_path / "build" / "export"


def test_export_has_verified_lineage_and_unavailable_csv(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    capture_path, preview_path, points_path, out = export_fixture(tmp_path, monkeypatch)
    before = {p: common.file_hash(p) for p in (capture_path, preview_path, points_path)}
    metadata = depth.export_records(capture_path, preview_path, points_path, out)
    assert metadata["counts"] == dict(observations=6, landmarks=3, frames=3, leaves=1)
    assert metadata["calibration_sha256"] == common.file_hash(tmp_path / "intrinsics.json")
    assert not metadata["validated_metric"] and not metadata["deep_learning_run"]
    unavailable = common.rows(out / "frames.csv")[-1]
    assert unavailable["pose_reprojection_error_px"] == "unavailable"
    assert unavailable["detected_marker_ids"] == "unavailable"
    assert all(common.file_hash(p) == digest for p, digest in before.items())
    with pytest.raises(common.StudyError, match="already exists"):
        depth.export_records(capture_path, preview_path, points_path, out)


@pytest.mark.parametrize("corrupt", ["photo", "calibration", "capture", "board"])
def test_rejects_changed_provenance_before_output(tmp_path: Path, monkeypatch: pytest.MonkeyPatch, corrupt: str) -> None:
    capture_path, preview_path, points_path, out = export_fixture(tmp_path, monkeypatch)
    if corrupt == "photo":
        (tmp_path / "a.png").write_bytes(b"changed")
    elif corrupt == "calibration":
        (tmp_path / "intrinsics.json").write_text("{}", encoding="utf-8")
    elif corrupt == "capture":
        capture_path.write_text(capture_path.read_text(encoding="utf-8") + " ", encoding="utf-8")
    else:
        common.write_json(tmp_path / "board.json", dict(variant_id="board-b"))
    with pytest.raises(common.StudyError):
        depth.export_records(capture_path, preview_path, points_path, out)
    assert not out.exists()
