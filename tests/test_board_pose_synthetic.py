"""Pose recovery from synthetic ChArUco views."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tomato3d.calib.board import (
    board_frame_origin_sheet_mm,
    board_rectangle_board_mm,
    board_to_sheet_mm,
    detect_board_corners,
    sheet_pose_to_board_pose,
    sheet_to_board_mm,
)
from tomato3d.calib.pose import (
    estimate_turntable_axis,
    measured_angle_deg,
    solve_pose,
)
from tomato3d.io.schemas import BoardDetection, BoardSpec, Intrinsics

MIN_CORNERS_FOR_POSE = 6

#: The brief's accuracy bar for a recovered pose.
MAX_REPROJECTION_ERROR_PX = 0.5


def _reprojection_error_px(
    pose, spec: BoardSpec, intrinsics: Intrinsics, detection: BoardDetection, board
) -> float:
    """RMS error of the *board-frame* pose against the detected corners.

    Projecting through the board frame is what proves the frame conversion, not just the
    solver.
    """
    object_points_sheet_mm, image_points_px = board.matchImagePoints(
        detection.corners.reshape(-1, 1, 2), detection.ids.reshape(-1, 1)
    )
    object_points_board_mm = sheet_to_board_mm(
        np.asarray(object_points_sheet_mm, dtype=np.float64).reshape(-1, 3), spec
    )
    reprojected_px, _ = cv2.projectPoints(
        object_points_board_mm,
        np.asarray(pose.rvec_rad).reshape(3, 1),
        np.asarray(pose.tvec_mm).reshape(3, 1),
        intrinsics.camera_matrix_array,
        intrinsics.dist_coeffs_array,
    )
    residuals_px = np.linalg.norm(
        reprojected_px.reshape(-1, 2) - image_points_px.reshape(-1, 2), axis=1
    )
    return float(np.sqrt(np.mean(np.square(residuals_px))))


def test_board_frame_origin_is_the_first_inner_corner(board_spec, charuco_board) -> None:
    assert board_frame_origin_sheet_mm(charuco_board) == pytest.approx(
        [*board_spec.first_inner_corner_sheet_mm, 0.0]
    )
    assert sheet_to_board_mm(
        np.array([[*board_spec.first_inner_corner_sheet_mm, 0.0]]), board_spec
    )[0] == pytest.approx([0.0, 0.0, 0.0])


def test_board_frame_z_points_away_from_the_board(board_spec) -> None:
    """A point 10 mm above the board surface has board-frame z = +10."""
    above_sheet_mm = np.array([[135.0, 135.0, -10.0]])
    assert sheet_to_board_mm(above_sheet_mm, board_spec)[0][2] == pytest.approx(10.0)


def test_board_frame_roundtrip(board_spec) -> None:
    points_sheet_mm = np.array([[0.0, 0.0, 0.0], [270.0, 90.0, -47.9], [112.5, 112.5, 0.0]])
    recovered = board_to_sheet_mm(sheet_to_board_mm(points_sheet_mm, board_spec), board_spec)
    assert recovered == pytest.approx(points_sheet_mm)


def test_board_rectangle_spans_the_printed_sheet(board_spec) -> None:
    rectangle_mm = board_rectangle_board_mm(board_spec)
    assert rectangle_mm.shape == (4, 3)
    assert np.allclose(rectangle_mm[:, 2], 0.0)
    assert rectangle_mm[:, 0].min() == pytest.approx(-board_spec.square_size_mm)
    assert rectangle_mm[:, 0].max() == pytest.approx(
        board_spec.board_width_mm - board_spec.square_size_mm
    )


def test_board_pose_synthetic(
    board_spec, charuco_board, synthetic_intrinsics, render_view
) -> None:
    """A known synthetic pose is recovered to within 0.5 px reprojection."""
    view = render_view(angle_deg=25.0)
    detection = detect_board_corners(view.image, charuco_board)
    assert detection.n_corners_detected == (board_spec.squares_x - 1) * (
        board_spec.squares_y - 1
    )

    pose = solve_pose(
        detection, synthetic_intrinsics, charuco_board, MIN_CORNERS_FOR_POSE
    )
    assert pose.is_solved
    assert pose.reprojection_error_px < MAX_REPROJECTION_ERROR_PX
    assert (
        _reprojection_error_px(
            pose, board_spec, synthetic_intrinsics, detection, charuco_board
        )
        < MAX_REPROJECTION_ERROR_PX
    )

    expected_rvec_rad, expected_tvec_mm = sheet_pose_to_board_pose(
        view.rvec_sheet_rad, view.tvec_sheet_mm, board_spec
    )
    assert pose.rvec_rad == pytest.approx(expected_rvec_rad, abs=5e-3)
    assert pose.tvec_mm == pytest.approx(expected_tvec_mm, abs=2.0)


def test_pose_partial_occlusion(
    charuco_board, synthetic_intrinsics, render_view
) -> None:
    """With 70 percent of the board covered, the pose still solves."""
    unoccluded = detect_board_corners(render_view(angle_deg=25.0).image, charuco_board)
    view = render_view(angle_deg=25.0, occlusion_fraction=0.7)
    detection = detect_board_corners(view.image, charuco_board)

    assert detection.n_corners_detected < unoccluded.n_corners_detected
    assert detection.n_corners_detected >= MIN_CORNERS_FOR_POSE

    pose = solve_pose(
        detection, synthetic_intrinsics, charuco_board, MIN_CORNERS_FOR_POSE
    )
    assert pose.is_solved
    assert pose.reprojection_error_px < MAX_REPROJECTION_ERROR_PX


def test_pose_below_min_corners(charuco_board, synthetic_intrinsics) -> None:
    """Fewer corners than the minimum yields pose_status='failed', with no exception."""
    detection = BoardDetection(
        corners=np.array([[100.0, 100.0], [200.0, 100.0], [200.0, 200.0]], np.float32),
        ids=np.array([0, 1, 5], np.int32),
        n_corners_detected=3,
    )
    pose = solve_pose(
        detection, synthetic_intrinsics, charuco_board, MIN_CORNERS_FOR_POSE
    )
    assert pose.pose_status == "failed"
    assert pose.rvec_rad is None and pose.tvec_mm is None
    assert "3 corners" in (pose.failure_reason or "")


def test_pose_on_an_empty_detection(charuco_board, synthetic_intrinsics) -> None:
    pose = solve_pose(
        BoardDetection.empty(), synthetic_intrinsics, charuco_board, MIN_CORNERS_FOR_POSE
    )
    assert pose.pose_status == "failed"


def test_detect_on_a_blank_image(charuco_board) -> None:
    blank = np.full((480, 640, 3), 128, np.uint8)
    detection = detect_board_corners(blank, charuco_board)
    assert detection.n_corners_detected == 0
    assert detection.corners.shape == (0, 2)


def test_turntable_axis_and_measured_angle(
    board_spec, charuco_board, synthetic_intrinsics, render_view
) -> None:
    """The fitted axis recovers the capture radius and the commanded angle steps."""
    nominal_angles_deg = [float(index * 30) for index in range(12)]
    poses = []
    for angle_deg in nominal_angles_deg:
        detection = detect_board_corners(
            render_view(angle_deg=angle_deg).image, charuco_board
        )
        pose = solve_pose(
            detection, synthetic_intrinsics, charuco_board, MIN_CORNERS_FOR_POSE
        )
        assert pose.is_solved
        poses.append(pose)

    axis = estimate_turntable_axis(poses)
    assert axis.is_solved
    assert axis.n_poses_used == len(poses)
    assert axis.radius_mm == pytest.approx(550.0, abs=2.0)
    assert axis.rms_fit_error_mm < 1.0
    # The axis is the board normal, so it is parallel to board +Z.
    assert abs(float(np.asarray(axis.direction) @ np.array([0.0, 0.0, 1.0]))) == (
        pytest.approx(1.0, abs=1e-3)
    )

    measured_deg = [measured_angle_deg(pose, axis) for pose in poses]
    # The reference view reads zero, never 359.999... from a wrapped -0.
    assert measured_deg[0] == pytest.approx(0.0, abs=1e-9)
    assert all(0.0 <= angle_deg < 360.0 for angle_deg in measured_deg)

    # Angle zero is the first side view, and the sense of rotation follows the right-hand
    # rule about the fitted axis - which may be either sense physically. What must hold
    # is that every commanded 30 degree step measures 30 degrees, in one steady
    # direction.
    steps_deg = np.diff(measured_deg) % 360.0
    signed_steps_deg = np.where(steps_deg > 180.0, steps_deg - 360.0, steps_deg)
    assert np.abs(signed_steps_deg) == pytest.approx(
        np.full(len(poses) - 1, 30.0), abs=0.5
    )
    assert len(set(np.sign(signed_steps_deg))) == 1, "rotation sense must not flip"


def test_measured_angle_requires_a_solved_axis() -> None:
    from tomato3d.io.schemas import Pose, TurntableAxis

    solved_pose = Pose(
        pose_status="solved",
        n_corners_detected=20,
        rvec_rad=np.zeros(3),
        tvec_mm=np.array([0.0, 0.0, 500.0]),
    )
    unfitted = TurntableAxis(status="failed", n_poses_used=1)
    with pytest.raises(ValueError, match="unfitted"):
        measured_angle_deg(solved_pose, unfitted)


def test_turntable_axis_needs_enough_poses() -> None:
    from tomato3d.io.schemas import Pose

    axis = estimate_turntable_axis([Pose(pose_status="failed", n_corners_detected=0)])
    assert not axis.is_solved
    assert axis.n_poses_used == 0


# --------------------------------------------------------------------------------------
# Board construction from the spec: legacy flag, marker ids, scale block box
# --------------------------------------------------------------------------------------


def _even_row_spec(board_spec: BoardSpec) -> BoardSpec:
    """The real spec reshaped to an even row count, with its cross-checks kept valid.

    OpenCV's legacy pattern only changes the layout when ``squares_y`` is even, so the
    operational 7x7 board cannot demonstrate that the flag matters.
    """
    from conftest import derive_board_spec

    squares_x, squares_y = 6, 6
    return derive_board_spec(
        board_spec,
        squares_x=squares_x,
        squares_y=squares_y,
        board_width_mm=squares_x * board_spec.square_size_mm,
        board_height_mm=squares_y * board_spec.square_size_mm,
        expected_marker_count=(squares_x * squares_y) // 2,
        expected_inner_corner_count=(squares_x - 1) * (squares_y - 1),
        marker_ids=list(range((squares_x * squares_y) // 2)),
    )


def _layout(board) -> tuple[np.ndarray, np.ndarray]:
    """Rendered pattern and stacked marker object points of a board."""
    size_px = 60 * max(board.getChessboardSize())
    image = board.generateImage((size_px, size_px), marginSize=0, borderBits=1)
    return image, np.vstack(board.getObjPoints())


@pytest.mark.parametrize("legacy_pattern", [False, True])
def test_build_charuco_board_sets_legacy_flag_from_spec(
    board_spec, legacy_pattern: bool
) -> None:
    """The flag comes from the spec, in both directions - never from the OpenCV default."""
    from conftest import derive_board_spec

    from tomato3d.calib.board import build_charuco_board

    for spec in (board_spec, _even_row_spec(board_spec)):
        derived = derive_board_spec(spec, legacy_pattern=legacy_pattern)
        assert build_charuco_board(derived).getLegacyPattern() is legacy_pattern


def test_legacy_flag_changes_the_layout_on_an_even_row_board(board_spec) -> None:
    """Proves the flag matters, so dropping the explicit call cannot pass silently."""
    from conftest import derive_board_spec

    from tomato3d.calib.board import build_charuco_board

    spec = _even_row_spec(board_spec)
    modern_image, modern_points = _layout(
        build_charuco_board(derive_board_spec(spec, legacy_pattern=False))
    )
    legacy_image, legacy_points = _layout(
        build_charuco_board(derive_board_spec(spec, legacy_pattern=True))
    )
    assert not np.array_equal(modern_image, legacy_image)
    assert not np.allclose(modern_points, legacy_points)


def test_legacy_flag_is_a_no_op_on_the_operational_odd_row_board(board_spec) -> None:
    """Documents the verified OpenCV behaviour for the 7x7 board: both patterns coincide.

    The explicit ``setLegacyPattern`` call is still required - it is what protects any
    even-row board added later.
    """
    from conftest import derive_board_spec

    from tomato3d.calib.board import build_charuco_board

    assert board_spec.squares_y % 2 == 1
    modern_image, modern_points = _layout(
        build_charuco_board(derive_board_spec(board_spec, legacy_pattern=False))
    )
    legacy_image, legacy_points = _layout(
        build_charuco_board(derive_board_spec(board_spec, legacy_pattern=True))
    )
    assert np.array_equal(modern_image, legacy_image)
    assert np.allclose(modern_points, legacy_points)


def test_build_charuco_board_uses_the_spec_marker_ids(board_spec) -> None:
    from conftest import derive_board_spec

    from tomato3d.calib.board import build_charuco_board

    board = build_charuco_board(board_spec)
    assert board.getIds().ravel().tolist() == list(board_spec.marker_ids)

    shifted_ids = [marker_id + 20 for marker_id in board_spec.marker_ids]
    shifted = build_charuco_board(derive_board_spec(board_spec, marker_ids=shifted_ids))
    assert shifted.getIds().ravel().tolist() == shifted_ids


def test_build_charuco_board_rejects_ids_outside_the_dictionary(board_spec) -> None:
    from conftest import derive_board_spec

    from tomato3d.calib.board import BoardError, build_charuco_board

    too_high = [marker_id + 1000 for marker_id in board_spec.marker_ids]
    with pytest.raises(BoardError, match="marker_ids"):
        build_charuco_board(derive_board_spec(board_spec, marker_ids=too_high))


def test_real_board_matches_its_expected_counts(board_spec, charuco_board) -> None:
    assert len(charuco_board.getIds()) == board_spec.expected_marker_count
    assert (
        len(charuco_board.getChessboardCorners())
        == board_spec.expected_inner_corner_count
    )


def test_scale_block_box_refuses_a_null_height(board_spec) -> None:
    from tomato3d.calib.board import BoardError, scale_block_box_board_mm

    assert board_spec.scale_block_nominal_height_mm is None
    with pytest.raises(BoardError, match="scale_block_nominal_height_mm"):
        scale_block_box_board_mm(board_spec)


def test_scale_block_box_footprint(measured_board_spec) -> None:
    """Default footprint is one square; a measured footprint replaces it."""
    from conftest import derive_board_spec

    from tomato3d.calib.board import scale_block_box_board_mm

    def footprint_side_mm(spec: BoardSpec) -> float:
        box_mm = scale_block_box_board_mm(spec)
        return float(np.ptp(box_mm[:4, 0]))

    assert measured_board_spec.scale_block_footprint_mm is None
    assert footprint_side_mm(measured_board_spec) == pytest.approx(
        measured_board_spec.square_size_mm
    )

    wider = derive_board_spec(measured_board_spec, scale_block_footprint_mm=40.0)
    box_mm = scale_block_box_board_mm(wider)
    assert footprint_side_mm(wider) == pytest.approx(40.0)
    assert np.ptp(box_mm[:, 2]) == pytest.approx(wider.scale_block_nominal_height_mm)
    # Centred on the configured sheet-frame position, whatever the footprint.
    center_board_mm = box_mm[:4].mean(axis=0)
    expected_board_mm = sheet_to_board_mm(
        np.array([[*wider.scale_block_position_mm, 0.0]]), wider
    )[0]
    assert center_board_mm == pytest.approx(expected_board_mm)
