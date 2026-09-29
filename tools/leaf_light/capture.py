"""Read-only capture inspection and per-frame ChArUco calibration adapter."""
from __future__ import annotations

from collections import Counter
from pathlib import Path

from tomato3d.calib.board import build_charuco_board, detect_board_corners
from tomato3d.calib.pose import solve_pose
from tomato3d.config import get_settings
from tomato3d.io.images import read_image
from tomato3d.io.manifest import read_manifest
from tomato3d.io.schemas import BoardSpec, Intrinsics, load_json_model

from .common import StudyError, file_hash, load_protocol, output_dir, variants, write_json


def prepare(manifest_path: Path, intrinsics_path: Path, protocol_path: Path, out: Path,
            phone_profile_path: Path | None = None) -> dict:
    p, protocol_hash = load_protocol(protocol_path)
    manifest = read_manifest(manifest_path)
    spec_path = get_settings().board_spec_path
    spec = load_json_model(spec_path, BoardSpec)
    intrinsics = load_json_model(intrinsics_path, Intrinsics)
    if manifest.board_variant_id != spec.variant_id:
        raise StudyError("Capture board variant disagrees with operational board")
    if manifest.camera_id != intrinsics.camera_id:
        raise StudyError("Capture and intrinsics camera IDs disagree")
    if len({i.file for i in manifest.images}) != len(manifest.images):
        raise StudyError("Duplicate image entries")
    phone_profile = None
    if phone_profile_path:
        from .phone import validate_profile
        phone_profile = validate_profile(phone_profile_path, intrinsics,
                                         [manifest_path.parent / i.file for i in manifest.images])
    board = build_charuco_board(spec)
    frames = []
    for entry in manifest.images:
        path = (manifest_path.parent / entry.file).resolve()
        if not path.is_relative_to(manifest_path.parent.resolve()):
            raise StudyError("Image path leaves the capture directory")
        frame = {"image_file": entry.file, "view_type": entry.view_type,
                 "top_position": entry.top_position, "image_path": str(path),
                 "sha256": file_hash(path) if path.is_file() else None,
                 "pose_status": "failed", "failure_reason": None}
        image = read_image(path)
        if image is None:
            frame["failure_reason"] = "unreadable image"
        elif image.shape[:2] != intrinsics.image_shape:
            frame["failure_reason"] = "image dimensions disagree with calibration"
        else:
            pose = solve_pose(detect_board_corners(image, board), intrinsics, board, p["min_pose_corners"])
            if pose.is_solved and pose.reprojection_error_px <= p["max_pose_error_px"]:
                frame.update(pose_status="solved", rvec_rad=pose.rvec_rad.reshape(3).tolist(),
                             tvec_mm=pose.tvec_mm.reshape(3).tolist(),
                             reprojection_error_px=pose.reprojection_error_px)
            else:
                frame["failure_reason"] = pose.failure_reason or "pose reprojection error too high"
        frames.append(frame)
    selections = variants(p, frames)
    blockers = []
    hashes = Counter(f["sha256"] for f in frames if f["sha256"])
    if any(count > 1 for count in hashes.values()):
        blockers.append("duplicate_image_content")
    if not spec.physical_print_verified:
        blockers.append("physical_print_not_verified")
    if spec.scale_block_nominal_height_mm is None or manifest.scale_reference_block_mm is None:
        blockers.append("scale_reference_not_measured")
    elif abs(spec.scale_block_nominal_height_mm - manifest.scale_reference_block_mm) > 1e-6:
        blockers.append("scale_reference_disagrees")
    bundle = {"protocol_sha256": protocol_hash, "data_kind": "observed",
              "plant_id": manifest.plant_id, "session_id": manifest.session_id,
              "captured_at": manifest.captured_at.isoformat(),
              "manifest_path": str(manifest_path.resolve()), "manifest_sha256": file_hash(manifest_path),
              "board_sha256": file_hash(spec_path), "intrinsics_sha256": file_hash(intrinsics_path),
              "intrinsics": intrinsics.model_dump(mode="json"), "frames": frames,
              "physical_blockers": blockers, "variants": selections,
              "annotation_route": "manual leaf contours; does not claim Stage 1 top-mask repair"}
    bundle["phone_profile"] = phone_profile
    bundle["phone_profile_sha256"] = file_hash(phone_profile_path) if phone_profile_path else None
    folder = output_dir(out)
    write_json(folder / "capture.json", bundle)
    return bundle
