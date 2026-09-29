"""End-to-end CLI behaviour on a synthetic session.

Not one of the unit contracts, but the wiring between manifest, pose, mask and quality is
where a stage-1 run actually fails, so it is exercised here. Every session in this file
lives under a non-ASCII data root (see ``conftest.NON_ASCII_DATA_DIRNAME``).
"""

from __future__ import annotations

import json
from pathlib import Path

import cv2
import numpy as np
import pytest

from conftest import (
    NON_ASCII_DATA_DIRNAME,
    look_at_pose_sheet,
    render_charuco_view,
    side_camera_position_sheet_mm,
)
from tomato3d.cli import calibrate_intrinsics as calibrate_cli
from tomato3d.cli import run_stage1
from tomato3d.io.images import ImageIOError, read_image, write_image
from tomato3d.io.schemas import (
    POSES_CSV_COLUMNS,
    UNAVAILABLE,
    Intrinsics,
    dump_json_model,
    load_json_model,
)
from tomato3d.io.tables import read_poses_csv

N_SIDE_VIEWS = 8
SIDE_MASK_NAMES = [f"side_{index:03d}.png" for index in range(N_SIDE_VIEWS)]


@pytest.fixture
def use_measured_config(monkeypatch, measured_config_dir: Path):
    """Point the run at a config whose scale block height is filled in (test-only)."""
    from tomato3d.config import get_settings

    monkeypatch.setenv("TOMATO3D_CONFIG_DIR", str(measured_config_dir))
    get_settings.cache_clear()
    yield measured_config_dir
    get_settings.cache_clear()


def _use_real_config(monkeypatch) -> None:
    from conftest import CONFIG_DIR

    from tomato3d.config import get_settings

    monkeypatch.setenv("TOMATO3D_CONFIG_DIR", str(CONFIG_DIR))
    get_settings.cache_clear()


def _derived_dir(settings) -> Path:
    return settings.derived_dir / "DT-001" / "DT-001_20260915_0900"


def _quality(settings) -> dict:
    return json.loads((_derived_dir(settings) / "quality.json").read_text(encoding="utf-8"))


def _mask_names(settings) -> list[str]:
    return sorted(path.name for path in (_derived_dir(settings) / "masks").glob("*.png"))


def _green_pixels(image: np.ndarray) -> np.ndarray:
    """The synthetic plant: strongly green pixels, independent of the pipeline's split."""
    blue, green, red = cv2.split(image.astype(np.float32))
    return (2.0 * green - red - blue) > 100.0


def _no_staging_left(settings) -> bool:
    return not list(_derived_dir(settings).glob(".stage1-staging-*"))


def test_run_stage1_help_works() -> None:
    with pytest.raises(SystemExit) as raised:
        run_stage1.build_parser().parse_args(["--help"])
    assert raised.value.code == 0


def test_calibrate_intrinsics_help_works() -> None:
    with pytest.raises(SystemExit) as raised:
        calibrate_cli.build_parser().parse_args(["--help"])
    assert raised.value.code == 0


def test_run_stage1_on_a_synthetic_session(
    clean_settings, synthetic_session: Path, use_measured_config, capsys
) -> None:
    exit_code = run_stage1.main(["--session", str(synthetic_session)])
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err

    derived_dir = _derived_dir(clean_settings)
    rows = read_poses_csv(derived_dir / "poses.csv")
    assert len(rows) == N_SIDE_VIEWS + 1
    assert tuple(rows[0]) == POSES_CSV_COLUMNS
    assert all(row["pose_status"] == "solved" for row in rows)

    side_rows = [row for row in rows if row["view_type"] == "side"]
    top_rows = [row for row in rows if row["view_type"] == "top"]
    assert len(side_rows) == N_SIDE_VIEWS and len(top_rows) == 1
    assert top_rows[0]["top_position"] == "T0"
    # Top views come from a jig, not from the turntable, so they carry no angle.
    assert top_rows[0]["measured_angle_deg"] == UNAVAILABLE
    assert all(row["measured_angle_deg"] != UNAVAILABLE for row in side_rows)

    quality = _quality(clean_settings)
    assert quality["n_images_total"] == N_SIDE_VIEWS + 1
    assert quality["n_images_solved"] == N_SIDE_VIEWS + 1
    assert quality["pose_solved_ratio"] == 1.0
    assert quality["mean_reprojection_error_px"] < 1.0
    assert quality["silhouette_area_cv"] != UNAVAILABLE
    assert "hull_voxel_count" not in quality
    # Side silhouettes exist, but the operational top view has none, so the session is
    # not training-usable (R2).
    assert _mask_names(clean_settings) == SIDE_MASK_NAMES
    assert quality["usable_for_training"] is False
    assert quality["failure_reasons"] == ["operational_top_view_silhouette_unavailable"]

    assert "masks written              8" in captured.out
    assert "usable_for_training" in captured.out
    assert _no_staging_left(clean_settings)


# --------------------------------------------------------------------------------------
# R1 - Unicode paths
# --------------------------------------------------------------------------------------


def test_run_stage1_reads_and_writes_under_a_non_ascii_path(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    """Every input is read and every mask is written and decodes, under a Korean path."""
    assert NON_ASCII_DATA_DIRNAME in str(synthetic_session)
    assert not str(synthetic_session).isascii()

    assert run_stage1.main(["--session", str(synthetic_session)]) == 0

    rows = read_poses_csv(_derived_dir(clean_settings) / "poses.csv")
    assert all(row["pose_status"] == "solved" for row in rows)

    for name in SIDE_MASK_NAMES:
        mask_path = _derived_dir(clean_settings) / "masks" / name
        assert mask_path.is_file(), name
        mask = read_image(mask_path, cv2.IMREAD_UNCHANGED)
        assert mask is not None, f"{name} does not decode"
        assert mask.shape == (1200, 1600)
        assert set(np.unique(mask)) <= {0, 255}


def test_run_stage1_mask_write_failure_is_a_hard_failure(
    clean_settings, synthetic_session: Path, use_measured_config, monkeypatch
) -> None:
    """A mask that cannot be written stops the run before any quality is published."""
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    previous_quality = (_derived_dir(clean_settings) / "quality.json").read_bytes()
    previous_masks = {
        name: (_derived_dir(clean_settings) / "masks" / name).read_bytes()
        for name in SIDE_MASK_NAMES
    }

    def failing_write(path: Path, image: np.ndarray) -> None:
        raise ImageIOError(f"simulated write failure for {path.name}")

    monkeypatch.setattr(run_stage1, "write_image", failing_write)
    assert run_stage1.main(["--session", str(synthetic_session)]) == 2

    assert (_derived_dir(clean_settings) / "quality.json").read_bytes() == previous_quality
    for name, content in previous_masks.items():
        assert (_derived_dir(clean_settings) / "masks" / name).read_bytes() == content
    assert _no_staging_left(clean_settings)


# --------------------------------------------------------------------------------------
# R2 - silhouettes that cannot be trusted are not published and gate training
# --------------------------------------------------------------------------------------


def test_side_masks_keep_the_plant(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    """Content, not existence: each side mask covers most of the plant it was cut from."""
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    for index, name in enumerate(SIDE_MASK_NAMES):
        image = read_image(synthetic_session / "images" / f"side_{index:03d}.jpg")
        mask = read_image(
            _derived_dir(clean_settings) / "masks" / name, cv2.IMREAD_UNCHANGED
        )
        plant = _green_pixels(image)
        retained_fraction = float((plant & (mask > 0)).sum()) / float(plant.sum())
        assert retained_fraction > 0.5, f"{name} keeps only {retained_fraction:.2f}"


def test_top_view_gets_no_mask(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    """No empty or partial T0 mask is ever published."""
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    assert "top_T0.png" not in _mask_names(clean_settings)
    assert "operational_top_view_silhouette_unavailable" in _quality(clean_settings)[
        "failure_reasons"
    ]


def test_empty_side_silhouette_is_not_published(
    clean_settings,
    synthetic_session: Path,
    use_measured_config,
    board_spec,
    charuco_board,
    synthetic_intrinsics,
) -> None:
    """A solved side view with no plant yields no mask file and fails the gate."""
    rvec_sheet_rad, tvec_sheet_mm = look_at_pose_sheet(
        side_camera_position_sheet_mm(board_spec, 90.0),
        np.array([*board_spec.board_center_sheet_mm, -110.0]),
    )
    plant_free = render_charuco_view(
        board_spec, charuco_board, synthetic_intrinsics, rvec_sheet_rad, tvec_sheet_mm
    )
    write_image(synthetic_session / "images" / "side_002.jpg", plant_free.image)

    assert run_stage1.main(["--session", str(synthetic_session)]) == 0

    rows = read_poses_csv(_derived_dir(clean_settings) / "poses.csv")
    side_002 = next(row for row in rows if row["image_file"] == "images/side_002.jpg")
    assert side_002["pose_status"] == "solved"
    assert "side_002.png" not in _mask_names(clean_settings)

    quality = _quality(clean_settings)
    assert quality["usable_for_training"] is False
    assert "side_view_silhouette_unavailable" in quality["failure_reasons"]


# --------------------------------------------------------------------------------------
# R3 - image size must match the calibration
# --------------------------------------------------------------------------------------


def test_run_stage1_rejects_a_resized_frame(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    """Same camera id, half resolution: refused before PnP, never solved with a wrong K."""
    image_path = synthetic_session / "images" / "side_001.jpg"
    image = read_image(image_path)
    write_image(image_path, cv2.resize(image, (800, 600), interpolation=cv2.INTER_AREA))

    assert run_stage1.main(["--session", str(synthetic_session)]) == 0

    rows = read_poses_csv(_derived_dir(clean_settings) / "poses.csv")
    resized = next(row for row in rows if row["image_file"] == "images/side_001.jpg")
    assert resized["pose_status"] == "failed"
    assert resized["tvec_z_mm"] == UNAVAILABLE
    assert sum(row["pose_status"] == "solved" for row in rows) == N_SIDE_VIEWS

    quality = _quality(clean_settings)
    assert quality["usable_for_training"] is False
    assert "image_size_mismatch_with_intrinsics" in quality["failure_reasons"]
    assert "side_001.png" not in _mask_names(clean_settings)


# --------------------------------------------------------------------------------------
# R4 - a rerun replaces the previous run's outputs
# --------------------------------------------------------------------------------------


def test_blocked_rerun_leaves_no_stale_masks(
    clean_settings, synthetic_session: Path, use_measured_config, monkeypatch
) -> None:
    """Measured block first, then the real null-height config: no old mask survives."""
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    assert _mask_names(clean_settings) == SIDE_MASK_NAMES

    _use_real_config(monkeypatch)
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0

    assert _mask_names(clean_settings) == []
    quality = _quality(clean_settings)
    assert quality["silhouette_area_cv"] == UNAVAILABLE
    assert quality["usable_for_training"] is False
    assert _no_staging_left(clean_settings)


def test_rerun_drops_the_mask_of_a_newly_failed_frame(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    assert "side_003.png" in _mask_names(clean_settings)

    blank = np.full((1200, 1600, 3), 128, np.uint8)
    write_image(synthetic_session / "images" / "side_003.jpg", blank)
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0

    assert "side_003.png" not in _mask_names(clean_settings)
    assert len(_mask_names(clean_settings)) == N_SIDE_VIEWS - 1


def test_rerun_keeps_files_stage1_does_not_own(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    """Cleanup is limited to Stage 1's own artifacts."""
    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    later_stage_file = _derived_dir(clean_settings) / "pointcloud.ply"
    later_stage_file.write_text("later stage output", encoding="utf-8")

    assert run_stage1.main(["--session", str(synthetic_session)]) == 0
    assert later_stage_file.read_text(encoding="utf-8") == "later stage output"


# --------------------------------------------------------------------------------------
# Other gating and hard failures
# --------------------------------------------------------------------------------------


def test_run_stage1_records_a_bad_frame_and_keeps_going(
    clean_settings, synthetic_session: Path, use_measured_config
) -> None:
    """A frame with no board is a recorded failure, not a hard failure."""
    blank = np.full((1200, 1600, 3), 128, np.uint8)
    write_image(synthetic_session / "images" / "side_003.jpg", blank)

    assert run_stage1.main(["--session", str(synthetic_session)]) == 0

    rows = read_poses_csv(_derived_dir(clean_settings) / "poses.csv")
    failed = [row for row in rows if row["pose_status"] == "failed"]
    assert [row["image_file"] for row in failed] == ["images/side_003.jpg"]
    assert failed[0]["tvec_z_mm"] == UNAVAILABLE
    assert failed[0]["n_corners_detected"] == UNAVAILABLE

    quality = _quality(clean_settings)
    assert quality["n_images_solved"] == N_SIDE_VIEWS
    assert quality["pose_solved_ratio"] == pytest.approx(N_SIDE_VIEWS / (N_SIDE_VIEWS + 1))
    assert quality["usable_for_training"] is False
    assert quality["failure_reasons"] == [
        "pose_solved_ratio_below_0.95",
        "operational_top_view_silhouette_unavailable",
    ]


def test_run_stage1_with_the_real_config_produces_no_silhouettes(
    clean_settings, synthetic_session: Path, capsys
) -> None:
    """Today's config has an unmeasured scale block: poses solve, masks are unavailable.

    The run is not a hard failure, the reason is logged once rather than per frame, and
    the session is gated out of training.
    """
    exit_code = run_stage1.main(["--session", str(synthetic_session)])
    captured = capsys.readouterr()
    assert exit_code == 0, captured.err

    rows = read_poses_csv(_derived_dir(clean_settings) / "poses.csv")
    assert all(row["pose_status"] == "solved" for row in rows)
    assert _mask_names(clean_settings) == []

    quality = _quality(clean_settings)
    assert quality["silhouette_area_cv"] == UNAVAILABLE
    assert quality["usable_for_training"] is False
    assert quality["failure_reasons"] == [
        "silhouette_area_cv_unavailable",
        "operational_top_view_silhouette_unavailable",
        "side_view_silhouette_unavailable",
    ]
    assert captured.err.count("scale_block_nominal_height_mm") == 1


def test_run_stage1_refuses_a_board_variant_mismatch(
    clean_settings, synthetic_session: Path, capsys
) -> None:
    """A session shot on another board exits non-zero, names both ids, and writes nothing."""
    manifest_path = synthetic_session / "session_manifest.json"
    payload = json.loads(manifest_path.read_text(encoding="utf-8"))
    configured_variant_id = payload["board_variant_id"]
    payload["board_variant_id"] = "charuco_5x5_190mm"
    manifest_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")

    exit_code = run_stage1.main(["--session", str(synthetic_session)])
    captured = capsys.readouterr()

    assert exit_code != 0
    assert "charuco_5x5_190mm" in captured.err
    assert configured_variant_id in captured.err
    assert not _derived_dir(clean_settings).exists(), "no work may happen on a mismatch"


def test_run_stage1_missing_manifest_exits_nonzero(clean_settings, tmp_path: Path) -> None:
    empty_session = tmp_path / "no_such_session"
    empty_session.mkdir()
    assert run_stage1.main(["--session", str(empty_session)]) == 2


def test_run_stage1_rejects_a_mismatched_camera(
    clean_settings, synthetic_session: Path
) -> None:
    """Intrinsics from another camera are a hard failure, not a silent substitution."""
    intrinsics_path = clean_settings.intrinsics_path("cam_synth")
    intrinsics = load_json_model(intrinsics_path, Intrinsics)
    dump_json_model(
        intrinsics_path, intrinsics.model_copy(update={"camera_id": "cam_other"})
    )
    assert run_stage1.main(["--session", str(synthetic_session)]) == 2


def test_calibrate_intrinsics_end_to_end(
    clean_settings,
    board_spec,
    charuco_board,
    synthetic_intrinsics,
    capsys,
) -> None:
    """Twenty shots under a non-ASCII path calibrate; minus six shots they are refused."""
    shots_dir = clean_settings.calib_dir / "intrinsics_shots"
    shots_dir.mkdir(parents=True)
    assert not str(shots_dir).isascii()
    rng = np.random.default_rng(20260915)
    for index in range(20):
        angle_deg = float(index * 17)
        radius_mm = float(rng.uniform(420.0, 640.0))
        height_mm = float(rng.uniform(220.0, 420.0))
        rvec_sheet_rad, tvec_sheet_mm = look_at_pose_sheet(
            side_camera_position_sheet_mm(board_spec, angle_deg, radius_mm, height_mm),
            np.array([*board_spec.board_center_sheet_mm, 0.0]),
        )
        view = render_charuco_view(
            board_spec,
            charuco_board,
            synthetic_intrinsics,
            rvec_sheet_rad,
            tvec_sheet_mm,
        )
        write_image(shots_dir / f"calib_{index:03d}.png", view.image)

    exit_code = calibrate_cli.main(
        ["--images", str(shots_dir), "--camera-id", "cam_synth"]
    )
    assert exit_code == 0, capsys.readouterr().err

    calibrated = load_json_model(clean_settings.intrinsics_path("cam_synth"), Intrinsics)
    assert calibrated.n_calibration_images == 20
    assert calibrated.rms_reprojection_error_px < 1.0
    assert calibrated.camera_matrix[0][0] == pytest.approx(1500.0, rel=0.05)
    assert calibrated.camera_matrix[1][1] == pytest.approx(1500.0, rel=0.05)

    for path in sorted(shots_dir.glob("*.png"))[:6]:
        path.unlink()
    assert (
        calibrate_cli.main(["--images", str(shots_dir), "--camera-id", "cam_synth"]) == 1
    )


def test_calibrate_intrinsics_missing_folder_exits_nonzero(
    clean_settings, tmp_path: Path
) -> None:
    assert calibrate_cli.main(["--images", str(tmp_path / "nope")]) == 2
