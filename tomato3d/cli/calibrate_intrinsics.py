"""Calibrate one camera from a folder of ChArUco shots.

    python -m tomato3d.cli.calibrate_intrinsics --images data/calib/intrinsics_shots/ \\
                                                --board config/board_spec.json \\
                                                --camera-id cam_a
"""

from __future__ import annotations

import argparse
import logging
import sys
from pathlib import Path

from tomato3d.calib.intrinsics import CalibrationError, calibrate_intrinsics
from tomato3d.config import get_settings
from tomato3d.io.schemas import BoardSpec, SchemaError, dump_json_model, load_json_model
from tomato3d.logging_setup import configure_logging

logger = logging.getLogger(__name__)

#: Extensions accepted as calibration shots.
IMAGE_SUFFIXES = (".jpg", ".jpeg", ".png", ".tif", ".tiff")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python -m tomato3d.cli.calibrate_intrinsics",
        description="Calibrate camera intrinsics from ChArUco board shots.",
    )
    parser.add_argument(
        "--images",
        type=Path,
        required=True,
        help="Folder of calibration shots of the ChArUco board.",
    )
    parser.add_argument(
        "--board",
        type=Path,
        default=None,
        help="board_spec.json (default: <TOMATO3D_CONFIG_DIR>/board_spec.json).",
    )
    parser.add_argument(
        "--camera-id",
        default=None,
        help="Camera id (default: TOMATO3D_CAMERA_ID).",
    )
    parser.add_argument(
        "--out",
        type=Path,
        default=None,
        help="Output JSON (default: <data_root>/calib/intrinsics_<camera_id>.json).",
    )
    return parser


def collect_image_paths(images_dir: Path) -> list[Path]:
    """Every calibration shot in ``images_dir``, in a stable order."""
    return sorted(
        path
        for path in images_dir.iterdir()
        if path.is_file() and path.suffix.lower() in IMAGE_SUFFIXES
    )


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    settings = get_settings()
    configure_logging(settings.log_level)

    camera_id = args.camera_id or settings.camera_id
    board_spec_path = args.board or settings.board_spec_path
    output_path = args.out or settings.intrinsics_path(camera_id)

    if not args.images.is_dir():
        logger.error("not a directory: %s", args.images)
        return 2
    try:
        spec = load_json_model(board_spec_path, BoardSpec)
    except SchemaError as exc:
        logger.error("%s", exc)
        return 2

    image_paths = collect_image_paths(args.images)
    if not image_paths:
        logger.error("no calibration images in %s", args.images)
        return 2

    try:
        intrinsics = calibrate_intrinsics(image_paths, spec, camera_id)
    except CalibrationError as exc:
        logger.error("%s", exc)
        return 1

    dump_json_model(output_path, intrinsics)

    print(f"camera_id                  {intrinsics.camera_id}")
    print(
        f"image size                 {intrinsics.image_width_px} x "
        f"{intrinsics.image_height_px} px"
    )
    print(f"calibration images used    {intrinsics.n_calibration_images}")
    print(f"RMS reprojection error     {intrinsics.rms_reprojection_error_px:.4f} px")
    print(f"written                    {output_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
