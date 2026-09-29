"""Actual detections, single-source board coordinates and immutable pose provenance."""
from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tomato3d.calib.board import build_charuco_board, sheet_to_board_mm
from tomato3d.io.schemas import BoardSpec
from tools import charuco_capture_evidence as evidence_tool
from tools.leaf_light import common
from tools.leaf_light.reconstruction import project


@pytest.fixture
def fixture_capture(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, BoardSpec]:
    board_path = evidence_tool.get_settings().board_spec_path
    spec = BoardSpec.model_validate_json(board_path.read_text(encoding="utf-8"))
    board = build_charuco_board(spec)
    image = np.pad(board.generateImage((798, 570)), 30, constant_values=255)
    image_path = tmp_path / "board.png"
    cv2.imencode(".png", image)[1].tofile(image_path)
    blank_path = tmp_path / "blank.png"
    cv2.imencode(".png", np.full_like(image, 255))[1].tofile(blank_path)
    unreadable_path = tmp_path / "unreadable.png"
    unreadable_path.write_bytes(b"")
    intrinsics = dict(camera_matrix=[[1200., 0., image.shape[1] / 2], [0., 1200., image.shape[0] / 2], [0., 0., 1.]],
                      dist_coeffs=[0.] * 5, image_width_px=image.shape[1], image_height_px=image.shape[0])
    calibration_path = tmp_path / "intrinsics.json"
    common.write_json(calibration_path, intrinsics)
    frames = [dict(image_file=path.name, image_path=str(path), sha256=common.file_hash(path),
                   pose_status="solved" if index == 0 else "failed",
                   rvec_rad=[0., 0., 0.] if index == 0 else None,
                   tvec_mm=[0., 0., 500.] if index == 0 else None,
                   reprojection_error_px=999. if index == 0 else None, n_corners_detected=2,
                   passes_pose_gate=False, failure_reason=None if index == 0 else "old_unsolved_pose")
              for index, path in enumerate((image_path, blank_path, unreadable_path))]
    capture = dict(schema_version="diagnostic-preview-capture-1", board_variant_id=spec.variant_id,
                   intrinsics_path=str(calibration_path), intrinsics_sha256=common.file_hash(calibration_path),
                   intrinsics=intrinsics, quality=dict(max_pose_error_px=1.), validated_metric=False, frames=frames)
    capture_path = tmp_path / "capture.json"
    common.write_json(capture_path, capture)
    monkeypatch.setattr(common, "BUILD", tmp_path / "build")
    return capture_path, tmp_path / "build" / "evidence", spec


def test_real_detector_outputs_and_failed_frames_preserve_existing_poses(fixture_capture: tuple[Path, Path, BoardSpec]) -> None:
    capture_path, out, spec = fixture_capture
    original = common.read_json(capture_path)
    source_hash = common.file_hash(capture_path)
    result = evidence_tool.export_evidence(capture_path, out, overlays=True)
    saved = common.read_json(out / "capture.board_evidence.json")
    assert common.file_hash(capture_path) == source_hash
    assert saved["quality"] == original["quality"] and saved["intrinsics"] == original["intrinsics"]
    for source, enriched in zip(original["frames"], saved["frames"]):
        assert {key: enriched[key] for key in source} == source
    actual = saved["frames"][0]["board_evidence"]
    assert actual["detection_status"] == "detected"
    assert actual["n_markers_detected"] == spec.expected_marker_count
    assert actual["n_charuco_corners_detected"] == spec.expected_inner_corner_count
    assert set(actual["detected_marker_ids"]) == set(spec.marker_ids)
    assert actual["existing_pose_charuco_rms_px"] > 1.
    assert saved["frames"][0]["reprojection_error_px"] == 999.
    assert not saved["frames"][0]["passes_pose_gate"]
    origin = next(corner for corner in actual["corners"] if corner["corner_id"] == 0)
    np.testing.assert_allclose(origin["board_xyz_mm"], [0., 0., 0.])
    assert all(corner["board_xyz_mm"][2] == 0. for corner in actual["corners"])
    blank, unreadable = [frame["board_evidence"] for frame in saved["frames"][1:]]
    assert blank["detection_status"] == "no_board_detected"
    assert blank["detected_marker_ids"] == [] and blank["existing_pose_charuco_rms_px"] is None
    assert unreadable["detection_status"] == "image_unreadable"
    assert unreadable["detected_corner_ids"] == []
    assert len(common.rows(out / "frames.csv")) == 3
    assert len(common.rows(out / "marker_observations.csv")) == spec.expected_marker_count * 4
    assert len(common.rows(out / "corner_observations.csv")) == spec.expected_inner_corner_count
    assert result["frame_count"] == 3 and not result["pose_reestimated"] and not result["deep_learning_run"]
    assert (out / "board_board_evidence.jpg").exists()


def test_ids_are_detected_not_inferred_and_duplicates_remain_traceable(fixture_capture: tuple[Path, Path, BoardSpec]) -> None:
    capture_path, _, spec = fixture_capture
    capture = common.read_json(capture_path)
    board = build_charuco_board(spec)
    frame = capture["frames"][0]
    origin_mm = sheet_to_board_mm(board.getChessboardCorners()[:1], spec)
    corner_px = project(origin_mm, frame, capture["intrinsics"]).astype(np.float32)[:, None]
    unknown_id = next(value for value in range(50) if value not in spec.marker_ids)
    quad = np.array([[[10., 10.], [20., 10.], [20., 20.], [10., 20.]]], dtype=np.float32)
    detector = SimpleNamespace(detectBoard=lambda image: (corner_px, np.array([[0]], np.int32),
        (quad, quad + 30), np.array([[unknown_id], [unknown_id]], np.int32)))
    image = np.zeros((capture["intrinsics"]["image_height_px"], capture["intrinsics"]["image_width_px"], 3), np.uint8)
    evidence = evidence_tool.detect_evidence(image, frame, capture["intrinsics"], detector, board, spec)
    assert evidence["detected_marker_ids"] == [unknown_id, unknown_id]
    assert [item["detection_index"] for item in evidence["markers"]] == [0, 1]
    assert all(item["board_vertices_mm"] is None for item in evidence["markers"])
    assert all(item["residuals_px"] is None for item in evidence["markers"])
    assert evidence["detected_corner_ids"] == [0]
    assert evidence["existing_pose_charuco_rms_px"] == pytest.approx(0., abs=1e-5)
    assert evidence["existing_pose_marker_rms_px"] is None


def test_resolution_mismatch_keeps_actual_pixels_without_residuals(fixture_capture: tuple[Path, Path, BoardSpec]) -> None:
    capture_path, _, spec = fixture_capture
    capture = common.read_json(capture_path)
    detector = SimpleNamespace(detectBoard=lambda image: (np.array([[[10., 20.]]], np.float32),
                               np.array([[0]], np.int32), (), None))
    evidence = evidence_tool.detect_evidence(np.zeros((20, 30, 3), np.uint8), capture["frames"][0],
                                             capture["intrinsics"], detector, build_charuco_board(spec), spec)
    assert evidence["detection_status"] == "image_resolution_mismatch"
    assert evidence["corners"][0]["pixel_xy_px"] == [10., 20.]
    assert evidence["corners"][0]["projected_xy_px"] is None
    assert evidence["existing_pose_charuco_rms_px"] is None


@pytest.mark.parametrize("changed", ["photo", "calibration", "embedded_calibration", "board_variant", "board_hash"])
def test_changed_sources_rejected_before_output(fixture_capture: tuple[Path, Path, BoardSpec], changed: str) -> None:
    capture_path, out, _ = fixture_capture
    capture = common.read_json(capture_path)
    if changed == "photo":
        Path(capture["frames"][0]["image_path"]).write_bytes(b"changed")
    elif changed == "calibration":
        Path(capture["intrinsics_path"]).write_text("{}", encoding="utf-8")
    elif changed == "embedded_calibration":
        capture["intrinsics"]["camera_matrix"][0][0] = 999.
    elif changed == "board_variant":
        capture["board_variant_id"] = "different_board"
    else:
        capture["board_spec_sha256"] = "incorrect_hash"
    common.write_json(capture_path, capture)
    with pytest.raises(common.StudyError):
        evidence_tool.export_evidence(capture_path, out)
    assert not out.exists()
