"""Silhouette masking: the geometric parts must not read pixel colour."""

from __future__ import annotations

import cv2
import numpy as np
import pytest

from tomato3d.calib.board import detect_board_corners
from tomato3d.calib.pose import solve_pose
from tomato3d.mask.silhouette import (
    MaskError,
    board_plane_mask,
    scale_block_mask,
    segment_plant_silhouette,
    silhouette_area_cv,
    silhouette_blockers,
    workspace_prism_mask,
)

MIN_CORNERS_FOR_POSE = 6

GEOMETRIC_MASKS = (board_plane_mask, scale_block_mask, workspace_prism_mask)


@pytest.fixture
def solved_view(charuco_board, synthetic_intrinsics, render_view):
    """A rendered view together with its solved pose."""
    view = render_view(angle_deg=25.0, draw_plant=True)
    detection = detect_board_corners(view.image, charuco_board)
    pose = solve_pose(
        detection, synthetic_intrinsics, charuco_board, MIN_CORNERS_FOR_POSE
    )
    assert pose.is_solved
    return view, pose


@pytest.mark.parametrize("mask_function", GEOMETRIC_MASKS)
def test_mask_geometry_only(
    solved_view, measured_board_spec, synthetic_intrinsics, mask_function
) -> None:
    """Geometric mask output is unchanged when the input image colours are randomised."""
    view, pose = solved_view
    image_shape = view.image.shape[:2]
    spec = measured_board_spec

    from_real_image = mask_function(pose, synthetic_intrinsics, spec, image_shape)

    rng = np.random.default_rng(20260915)
    randomised = rng.integers(0, 256, size=view.image.shape, dtype=np.uint8)
    assert not np.array_equal(randomised, view.image)
    from_random_image = mask_function(
        pose, synthetic_intrinsics, spec, randomised.shape[:2]
    )

    assert np.array_equal(from_real_image, from_random_image)
    assert from_real_image.dtype == np.uint8
    assert set(np.unique(from_real_image)) <= {0, 255}
    assert from_real_image.any(), "the board must be visible in this view"


def test_board_plane_mask_covers_the_board_corners(
    solved_view, board_spec, synthetic_intrinsics
) -> None:
    """The mask contains the projected board corners and excludes a far-away point."""
    from tomato3d.calib.board import board_rectangle_board_mm

    view, pose = solved_view
    image_shape = view.image.shape[:2]
    mask = board_plane_mask(pose, synthetic_intrinsics, board_spec, image_shape)

    projected_px, _ = cv2.projectPoints(
        board_rectangle_board_mm(board_spec),
        np.asarray(pose.rvec_rad).reshape(3, 1),
        np.asarray(pose.tvec_mm).reshape(3, 1),
        synthetic_intrinsics.camera_matrix_array,
        synthetic_intrinsics.dist_coeffs_array,
    )
    centroid_px = projected_px.reshape(-1, 2).mean(axis=0).round().astype(int)
    assert mask[centroid_px[1], centroid_px[0]] == 255
    assert mask[0, 0] == 0


def test_scale_block_mask_sits_inside_the_board_footprint(
    solved_view, measured_board_spec, synthetic_intrinsics
) -> None:
    view, pose = solved_view
    image_shape = view.image.shape[:2]
    spec = measured_board_spec
    board = board_plane_mask(pose, synthetic_intrinsics, spec, image_shape) > 0
    block = scale_block_mask(pose, synthetic_intrinsics, spec, image_shape) > 0

    assert block.any()
    # The block stands on the board, so its base overlaps the board footprint while its
    # top rises above it.
    assert (block & board).any()
    assert (block & ~board).any()


def test_prism_contains_the_board_footprint(
    solved_view, board_spec, synthetic_intrinsics
) -> None:
    view, pose = solved_view
    image_shape = view.image.shape[:2]
    board = board_plane_mask(pose, synthetic_intrinsics, board_spec, image_shape) > 0
    prism = workspace_prism_mask(pose, synthetic_intrinsics, board_spec, image_shape) > 0

    assert prism.sum() > board.sum()
    # Allow the hull rasteriser a one-pixel boundary difference.
    assert (board & ~prism).sum() <= board.sum() * 0.01


def test_segment_plant_silhouette_finds_the_plant(
    solved_view, measured_board_spec, synthetic_intrinsics
) -> None:
    view, pose = solved_view
    board_spec = measured_board_spec
    mask = segment_plant_silhouette(view.image, pose, synthetic_intrinsics, board_spec)

    assert mask.dtype == np.uint8
    assert mask.shape == view.image.shape[:2]
    assert set(np.unique(mask)) <= {0, 255}
    assert mask.any(), "the synthetic plant must be found"

    board = board_plane_mask(
        pose, synthetic_intrinsics, board_spec, view.image.shape[:2]
    )
    assert not np.any((mask > 0) & (board > 0)), "the board region must be excluded"

    # The mask must actually sit on the green blob, not on random background.
    blue, green, red = cv2.split(view.image.astype(np.float32))
    greenness = 2.0 * green - red - blue
    assert greenness[mask > 0].mean() > greenness[mask == 0].mean()


def test_segment_plant_silhouette_requires_a_solved_pose(
    solved_view, board_spec, synthetic_intrinsics
) -> None:
    from tomato3d.io.schemas import Pose

    view, _ = solved_view
    failed = Pose(pose_status="failed", n_corners_detected=0)
    with pytest.raises(MaskError, match="solved pose"):
        segment_plant_silhouette(view.image, failed, synthetic_intrinsics, board_spec)


def test_unmeasured_scale_block_blocks_silhouettes(
    solved_view, board_spec, synthetic_intrinsics
) -> None:
    """With the real config's null block height, masking refuses and names the field."""
    assert board_spec.scale_block_nominal_height_mm is None
    blockers = silhouette_blockers(board_spec)
    assert len(blockers) == 1
    assert "scale_block_nominal_height_mm" in blockers[0]

    view, pose = solved_view
    with pytest.raises(MaskError, match="scale_block_nominal_height_mm"):
        scale_block_mask(pose, synthetic_intrinsics, board_spec, view.image.shape[:2])
    with pytest.raises(MaskError, match="scale_block_nominal_height_mm"):
        segment_plant_silhouette(view.image, pose, synthetic_intrinsics, board_spec)


def test_measured_scale_block_has_no_blockers(measured_board_spec) -> None:
    assert silhouette_blockers(measured_board_spec) == []


def test_silhouette_area_cv() -> None:
    def disc(radius_px: int) -> np.ndarray:
        mask = np.zeros((200, 200), np.uint8)
        cv2.circle(mask, (100, 100), radius_px, 255, cv2.FILLED)
        return mask

    identical = [disc(40), disc(40), disc(40)]
    assert silhouette_area_cv(identical) == pytest.approx(0.0, abs=1e-9)

    varying = [disc(30), disc(40), disc(50)]
    assert silhouette_area_cv(varying) > 0.1

    with pytest.raises(ValueError, match="at least 2 masks"):
        silhouette_area_cv([disc(40)])

    empty = np.zeros((200, 200), np.uint8)
    with pytest.raises(ValueError, match="undefined"):
        silhouette_area_cv([empty, empty])


def test_top_view_is_unsupported_because_board_rejection_removes_the_plant(
    board_spec, measured_board_spec, charuco_board, synthetic_intrinsics
) -> None:
    """Why ``SUPPORTED_VIEW_TYPES`` excludes top views, measured rather than asserted.

    Seen straight down, the plant projects inside the board quad, so the segmenter keeps
    almost none of it. If segmentation improves and this starts failing, re-enable top
    views deliberately - together with the quality gate that depends on them.
    """
    from conftest import look_at_pose_sheet, render_charuco_view

    from tomato3d.mask.silhouette import SUPPORTED_VIEW_TYPES, view_supports_silhouette

    assert "top" not in SUPPORTED_VIEW_TYPES
    assert not view_supports_silhouette("top")
    assert view_supports_silhouette("side")

    center_x_mm, center_y_mm = board_spec.board_center_sheet_mm
    rvec_sheet_rad, tvec_sheet_mm = look_at_pose_sheet(
        np.array([center_x_mm, center_y_mm, -550.0]),
        np.array([center_x_mm, center_y_mm, 0.0]),
    )
    view = render_charuco_view(
        board_spec,
        charuco_board,
        synthetic_intrinsics,
        rvec_sheet_rad,
        tvec_sheet_mm,
        draw_plant=True,
    )
    pose = solve_pose(
        detect_board_corners(view.image, charuco_board),
        synthetic_intrinsics,
        charuco_board,
        MIN_CORNERS_FOR_POSE,
    )
    assert pose.is_solved

    mask = segment_plant_silhouette(
        view.image, pose, synthetic_intrinsics, measured_board_spec
    )
    blue, green, red = cv2.split(view.image.astype(np.float32))
    plant = (2.0 * green - red - blue) > 100.0
    assert plant.sum() > 10_000, "the synthetic plant must be visible from above"
    retained_fraction = float((plant & (mask > 0)).sum()) / float(plant.sum())
    assert retained_fraction < 0.05
