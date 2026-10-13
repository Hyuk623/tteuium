"""Run stage 1 over one capture session.

    python -m tomato3d.cli.run_stage1 --session data/raw/DT-001/DT-001_20260915_0900

Writes ``poses.csv``, ``masks/`` and ``quality.json`` under
``<data_root>/derived/<plant_id>/<session_id>/``, then prints a one-screen summary.

A frame whose pose does not solve is recorded with ``pose_status='failed'`` and
``unavailable`` in every numeric column; the run continues.

The three outputs are published together. They are written to a staging folder first
and only swapped into place once every file has been written, so ``masks/`` never holds a
previous run's masks beside this run's ``quality.json``, and a ``quality.json`` that is
present always describes the ``poses.csv`` and ``masks/`` next to it.
"""

from __future__ import annotations

import argparse
import logging
import os
import shutil
import sys
import tempfile
from collections.abc import Sequence
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass, replace
from pathlib import Path

import cv2
import numpy as np

from tomato3d.calib.board import build_charuco_board, detect_board_corners
from tomato3d.calib.pose import estimate_turntable_axis, measured_angle_deg, solve_pose
from tomato3d.config import ConfigError, Settings, get_settings
from tomato3d.io.images import ImageIOError, read_image, write_image
from tomato3d.io.manifest import (
    MASKS_DIRNAME,
    POSES_FILENAME,
    QUALITY_FILENAME,
    ManifestError,
    SessionPaths,
    mask_filename,
    read_manifest,
    resolve_session_paths,
)
from tomato3d.io.quality import (
    REASON_IMAGE_SIZE_MISMATCH,
    REASON_OPERATIONAL_TOP_SILHOUETTE_UNAVAILABLE,
    REASON_SIDE_SILHOUETTE_UNAVAILABLE,
    REASON_UNREADABLE_IMAGE,
    build_quality_record,
    write_quality,
)
from tomato3d.io.schemas import (
    POSE_FAILED,
    UNAVAILABLE,
    BoardSpec,
    ImageEntry,
    Intrinsics,
    MaybeFloat,
    Pose,
    QualityRecord,
    QualityThresholds,
    SchemaError,
    SessionManifest,
    load_json_model,
)
from tomato3d.io.tables import write_poses_csv
from tomato3d.logging_setup import configure_logging
from tomato3d.mask.silhouette import (
    SUPPORTED_VIEW_TYPES,
    MaskError,
    segment_plant_silhouette,
    silhouette_area_cv,
    silhouette_blockers,
    view_supports_silhouette,
)

logger = logging.getLogger(__name__)

_STAGING_PREFIX = ".stage1-staging-"


class BoardVariantMismatchError(SchemaError):
    """The session was captured on a different printed board than the spec describes."""


@dataclass(frozen=True)
class _FrameResult:
    """One image: its pose, its mask, and any validity failure it raised.

    ``issues`` holds validity codes from :mod:`tomato3d.io.quality`; a frame that merely
    failed to solve (too few corners) carries none, because the pose ratio gate covers it.
    """

    entry: ImageEntry
    pose: Pose
    mask: np.ndarray | None
    issues: tuple[str, ...] = ()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tomato3d.cli.run_stage1",
        description=(
            "Solve per-frame board pose and plant silhouettes for one capture session."
        ),
    )
    parser.add_argument(
        "--session",
        type=Path,
        required=True,
        help="Session folder under data/raw/<plant_id>/<session_id>.",
    )
    parser.add_argument(
        "--board",
        type=Path,
        default=None,
        help="board_spec.json (default: <TOMATO3D_CONFIG_DIR>/board_spec.json).",
    )
    parser.add_argument(
        "--thresholds",
        type=Path,
        default=None,
        help="quality_thresholds.json (default: from TOMATO3D_CONFIG_DIR).",
    )
    parser.add_argument(
        "--intrinsics",
        type=Path,
        default=None,
        help=(
            "intrinsics_<camera_id>.json (default: resolved from the manifest's "
            "camera_id under <data_root>/calib)."
        ),
    )
    return parser


def _identify(pose: Pose, entry: ImageEntry, session_id: str) -> Pose:
    return pose.with_identity(
        session_id=session_id,
        image_file=entry.file,
        view_type=entry.view_type,
        top_position=entry.top_position,
    )


def _rejected_frame(
    entry: ImageEntry, session_id: str, reason: str, issue: str
) -> _FrameResult:
    """A frame refused before pose estimation, with its validity code."""
    logger.warning("%s: not processed (%s)", entry.file, reason)
    pose = Pose(pose_status=POSE_FAILED, n_corners_detected=0, failure_reason=reason)
    return _FrameResult(entry, _identify(pose, entry, session_id), None, (issue,))


def _process_frame(
    entry: ImageEntry,
    image_path: Path,
    board: cv2.aruco.CharucoBoard,
    intrinsics: Intrinsics,
    spec: BoardSpec,
    min_corners: int,
    session_id: str,
    *,
    masking_enabled: bool,
) -> _FrameResult:
    """Detect, solve and mask one frame. Never raises for a bad frame."""
    image = read_image(image_path)
    if image is None:
        return _rejected_frame(
            entry, session_id, f"unreadable image {image_path}", REASON_UNREADABLE_IMAGE
        )

    height_px, width_px = image.shape[:2]
    if (height_px, width_px) != intrinsics.image_shape:
        # A resized or cropped frame solved with the unscaled camera matrix gives a wrong
        # pose with a small residual, so no reprojection gate would catch it.
        return _rejected_frame(
            entry,
            session_id,
            f"image is {width_px}x{height_px} px but {intrinsics.camera_id} was "
            f"calibrated at {intrinsics.image_width_px}x{intrinsics.image_height_px} px",
            REASON_IMAGE_SIZE_MISMATCH,
        )

    detection = detect_board_corners(image, board)
    pose = _identify(
        solve_pose(detection, intrinsics, board, min_corners), entry, session_id
    )
    if not pose.is_solved:
        logger.warning(
            "%s: pose failed (%s)", entry.file, pose.failure_reason or "unknown reason"
        )
        return _FrameResult(entry, pose, None)
    if not masking_enabled or not view_supports_silhouette(entry.view_type):
        return _FrameResult(entry, pose, None)

    try:
        mask = segment_plant_silhouette(image, pose, intrinsics, spec)
    except MaskError as exc:
        logger.warning("%s: masking failed (%s)", entry.file, exc)
        return _FrameResult(entry, pose, None)
    if not np.any(mask):
        logger.warning("%s: silhouette is empty and is not published", entry.file)
        return _FrameResult(entry, pose, None)
    return _FrameResult(entry, pose, mask)


def _fill_measured_angles(results: list[_FrameResult]) -> list[_FrameResult]:
    """Fit the turntable axis from the side views and stamp each side pose with its angle.

    Top views get no measured angle: they are shot from a jig, not from the turntable.
    """
    side_poses = [result.pose for result in results if result.entry.view_type == "side"]
    axis = estimate_turntable_axis(side_poses)
    if not axis.is_solved:
        logger.warning(
            "turntable axis not fitted (%s); measured_angle_deg stays unavailable",
            axis.failure_reason,
        )
        return results

    stamped: list[_FrameResult] = []
    for result in results:
        if result.entry.view_type != "side" or not result.pose.is_solved:
            stamped.append(result)
            continue
        try:
            angle_deg = measured_angle_deg(result.pose, axis)
        except ValueError as exc:
            logger.warning("%s: %s", result.entry.file, exc)
            stamped.append(result)
            continue
        stamped.append(
            replace(result, pose=result.pose.with_measured_angle_deg(angle_deg))
        )
    return stamped


def _silhouette_cv(results: list[_FrameResult]) -> MaybeFloat:
    side_masks = [
        result.mask
        for result in results
        if result.entry.view_type == "side" and result.mask is not None
    ]
    try:
        return silhouette_area_cv(side_masks)
    except ValueError as exc:
        logger.warning("silhouette_area_cv unavailable: %s", exc)
        return UNAVAILABLE


def _validity_failures(
    results: Sequence[_FrameResult], operational_top_view: str
) -> list[str]:
    """Every validity code this run raised, frame issues first, in a stable order."""
    failures: list[str] = [issue for result in results for issue in result.issues]

    operational_top = [
        result
        for result in results
        if result.entry.view_type == "top"
        and result.entry.top_position == operational_top_view
    ]
    if not any(result.mask is not None for result in operational_top):
        failures.append(REASON_OPERATIONAL_TOP_SILHOUETTE_UNAVAILABLE)

    if any(
        result.entry.view_type == "side" and result.pose.is_solved and result.mask is None
        for result in results
    ):
        failures.append(REASON_SIDE_SILHOUETTE_UNAVAILABLE)

    return list(dict.fromkeys(failures))


def _publish_outputs(
    session_paths: SessionPaths,
    poses: Sequence[Pose],
    masks: dict[str, np.ndarray],
    record: QualityRecord,
) -> None:
    """Write this run's outputs as one coherent set, replacing the previous run's.

    Everything is written into a staging folder first; a write failure leaves the
    previous outputs untouched. The swap removes ``quality.json`` first and puts it back
    last, so if the swap itself is interrupted no ``quality.json`` describes a mixed set.
    Only Stage 1's own artifacts are replaced; other files in the folder are left alone.

    Raises:
        ImageIOError: a mask could not be encoded or written.
    """
    derived_dir = session_paths.derived_dir
    derived_dir.mkdir(parents=True, exist_ok=True)
    staging_dir = Path(tempfile.mkdtemp(prefix=_STAGING_PREFIX, dir=derived_dir))
    try:
        staged_masks_dir = staging_dir / MASKS_DIRNAME
        staged_masks_dir.mkdir()
        for image_file, mask in masks.items():
            write_image(staged_masks_dir / mask_filename(image_file), mask)
        write_poses_csv(staging_dir / POSES_FILENAME, poses)
        write_quality(staging_dir / QUALITY_FILENAME, record)

        session_paths.quality_json_path.unlink(missing_ok=True)
        if session_paths.masks_dir.exists():
            shutil.rmtree(session_paths.masks_dir)
        os.replace(staged_masks_dir, session_paths.masks_dir)
        os.replace(staging_dir / POSES_FILENAME, session_paths.poses_csv_path)
        os.replace(staging_dir / QUALITY_FILENAME, session_paths.quality_json_path)
    finally:
        shutil.rmtree(staging_dir, ignore_errors=True)


def _format_metric(value: MaybeFloat, digits: int) -> str:
    return value if value == UNAVAILABLE else f"{float(value):.{digits}f}"


def check_board_variant(manifest: SessionManifest, spec: BoardSpec) -> None:
    """Refuse a session shot on a different board than the spec describes.

    Marker ids overlap between printed variants, so detection cannot tell the boards
    apart: a 5x5 session processed with the 7x7 spec detects cleanly and is wrong in every
    dimension. The manifest's ``board_variant_id`` is the only evidence of the board.

    Raises:
        BoardVariantMismatchError: the two ids differ. The message names both.
    """
    if manifest.board_variant_id != spec.variant_id:
        raise BoardVariantMismatchError(
            f"session {manifest.session_id} was captured on board "
            f"{manifest.board_variant_id!r} but board_spec.json describes "
            f"{spec.variant_id!r}; refusing to process it"
        )


def run(args: argparse.Namespace, settings: Settings) -> int:
    """Execute stage 1. Returns the process exit code."""
    session_paths = resolve_session_paths(args.session, settings)
    manifest = read_manifest(session_paths.manifest_path)

    spec = load_json_model(args.board or settings.board_spec_path, BoardSpec)
    check_board_variant(manifest, spec)

    mask_blockers = silhouette_blockers(spec)
    for blocker in mask_blockers:
        logger.warning("silhouettes are not produced in this run: %s", blocker)
    if not mask_blockers:
        if not spec.color_chart_on_board:
            logger.warning(
                "color_chart_on_board is false: the colour chart is not excluded "
                "geometrically and may enter the plant silhouettes"
            )
        unsupported_views = sorted(
            {
                entry.view_type
                for entry in manifest.images
                if not view_supports_silhouette(entry.view_type)
            }
        )
        if unsupported_views:
            logger.warning(
                "no silhouettes for %s views: the segmenter supports only %s, because "
                "rejecting the projected board removes a plant seen from above",
                "/".join(unsupported_views),
                "/".join(SUPPORTED_VIEW_TYPES),
            )

    thresholds = load_json_model(
        args.thresholds or settings.quality_thresholds_path, QualityThresholds
    )
    intrinsics_path = args.intrinsics or settings.intrinsics_path(manifest.camera_id)
    intrinsics = load_json_model(intrinsics_path, Intrinsics)
    if intrinsics.camera_id != manifest.camera_id:
        raise SchemaError(
            f"{intrinsics_path.name} is for camera {intrinsics.camera_id!r} but the "
            f"manifest was captured with {manifest.camera_id!r}"
        )

    board = build_charuco_board(spec)
    min_corners = thresholds.min_charuco_corners_for_pose

    def process(entry: ImageEntry) -> _FrameResult:
        return _process_frame(
            entry,
            session_paths.image_path(entry.file),
            board,
            intrinsics,
            spec,
            min_corners,
            manifest.session_id,
            masking_enabled=not mask_blockers,
        )

    with ThreadPoolExecutor(max_workers=settings.max_workers) as executor:
        results = list(executor.map(process, manifest.images))

    results = _fill_measured_angles(results)
    poses = [result.pose for result in results]
    masks = {
        result.entry.file: result.mask for result in results if result.mask is not None
    }

    record = build_quality_record(
        session_id=manifest.session_id,
        poses=poses,
        silhouette_cv=_silhouette_cv(results),
        thresholds=thresholds,
        validity_failures=_validity_failures(results, manifest.operational_top_view),
    )
    _publish_outputs(session_paths, poses, masks, record)

    print(f"session                    {record.session_id}")
    print(f"images total               {record.n_images_total}")
    print(f"poses solved               {record.n_images_solved}")
    print(f"masks written              {len(masks)}")
    print(
        f"pose solved ratio          {_format_metric(record.pose_solved_ratio, 4)}"
    )
    print(
        f"mean reprojection error    "
        f"{_format_metric(record.mean_reprojection_error_px, 4)} px"
    )
    print(f"silhouette area CV         {_format_metric(record.silhouette_area_cv, 4)}")
    print(f"usable_for_training        {record.usable_for_training}")
    if record.failure_reasons:
        print(f"failure reasons            {', '.join(record.failure_reasons)}")
    print(f"written                    {session_paths.derived_dir}")
    return 0


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        settings = get_settings()
    except ConfigError as exc:  # a bad TOMATO3D_* value is an input error (exit 2), not a crash
        logger.error("configuration error: %s", exc)
        return 2
    configure_logging(settings.log_level)
    try:
        return run(args, settings)
    except (ManifestError, SchemaError, ImageIOError) as exc:
        logger.error("%s", exc)
        return 2


if __name__ == "__main__":
    sys.exit(main())
