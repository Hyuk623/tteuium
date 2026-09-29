"""Shared fixtures.

Every test runs on a synthetically rendered ChArUco view. No test requires a real
photograph, so the suite is runnable before the pilot capture exists.

The renderer works in the *sheet* frame (OpenCV's ChArUco object-point frame) because
that is the frame the ground-truth pose is easiest to construct in. Tests that check
pose recovery convert the ground truth into the board frame with
:func:`tomato3d.calib.board.sheet_pose_to_board_pose`, which is the same conversion the
pipeline uses.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import cv2
import numpy as np
import pytest

from tomato3d.io.schemas import (
    SCHEMA_VERSION,
    BoardSpec,
    Intrinsics,
    SessionManifest,
    load_json_model,
)

PROJECT_ROOT = Path(__file__).resolve().parents[1]

#: Name of the scratch data root. Deliberately non-ASCII, like the real project folder:
#: on Windows ``cv2.imread``/``cv2.imwrite`` silently fail on such paths, and an ASCII
#: temp path is exactly what hid that defect from the suite before.
NON_ASCII_DATA_DIRNAME = "데이터_한글 경로"
CONFIG_DIR = PROJECT_ROOT / "config"

#: Texture resolution of the rendered board, in pixels per millimetre. High enough that
#: the warped markers stay crisp at the test image size.
_TEXTURE_PX_PER_MM = 4.0

#: Mid grey background, so neither Otsu class is degenerate in the mask tests.
_BACKGROUND_VALUE = 110

_SESSION_CAPTURED_AT = datetime(2026, 9, 15, 9, 0, tzinfo=timezone(timedelta(hours=9)))


@dataclass(frozen=True)
class SyntheticView:
    """A rendered board view with its ground-truth pose in the sheet frame."""

    image: np.ndarray
    rvec_sheet_rad: np.ndarray
    tvec_sheet_mm: np.ndarray


@pytest.fixture(scope="session")
def project_root() -> Path:
    return PROJECT_ROOT


#: Test-only scale block height. The real block is unmeasured, so ``config/board_spec.json``
#: carries null; tests that need to exercise the block exclusion geometry use this instead.
#: It never reaches the real config.
SYNTHETIC_SCALE_BLOCK_HEIGHT_MM = 30.0


@pytest.fixture(scope="session")
def board_spec() -> BoardSpec:
    """The real ``config/board_spec.json``, exactly as the human wrote it."""
    return load_json_model(CONFIG_DIR / "board_spec.json", BoardSpec)


def derive_board_spec(spec: BoardSpec, **overrides: object) -> BoardSpec:
    """A re-validated copy of ``spec`` with ``overrides`` applied.

    Goes through full validation, unlike ``model_copy``, so a derived spec obeys the same
    cross-checks as the real one.
    """
    from tomato3d.io.schemas import validate_model

    return validate_model(
        {**spec.model_dump(mode="json"), **overrides}, BoardSpec, source="derived spec"
    )


@pytest.fixture(scope="session")
def measured_board_spec(board_spec: BoardSpec) -> BoardSpec:
    """The real spec with a synthetic scale block height filled in."""
    return derive_board_spec(
        board_spec, scale_block_nominal_height_mm=SYNTHETIC_SCALE_BLOCK_HEIGHT_MM
    )


@pytest.fixture
def measured_config_dir(tmp_path: Path, measured_board_spec: BoardSpec) -> Path:
    """A config directory identical to the real one except for the block height."""
    import shutil

    from tomato3d.io.schemas import dump_json_model

    config_dir = tmp_path / "config_measured"
    config_dir.mkdir()
    for name in ("capture_config.json", "quality_thresholds.json"):
        shutil.copyfile(CONFIG_DIR / name, config_dir / name)
    dump_json_model(config_dir / "board_spec.json", measured_board_spec)
    return config_dir


@pytest.fixture(scope="session")
def charuco_board(board_spec: BoardSpec) -> cv2.aruco.CharucoBoard:
    from tomato3d.calib.board import build_charuco_board

    return build_charuco_board(board_spec)


@pytest.fixture(scope="session")
def synthetic_intrinsics() -> Intrinsics:
    """A distortion-free pinhole camera, so render and solve share one model exactly."""
    width_px, height_px = 1600, 1200
    focal_px = 1500.0
    return Intrinsics(
        schema_version=SCHEMA_VERSION,
        camera_id="cam_synth",
        image_width_px=width_px,
        image_height_px=height_px,
        camera_matrix=(
            (focal_px, 0.0, width_px / 2.0),
            (0.0, focal_px, height_px / 2.0),
            (0.0, 0.0, 1.0),
        ),
        dist_coeffs=(0.0, 0.0, 0.0, 0.0, 0.0),
        rms_reprojection_error_px=0.0,
        n_calibration_images=20,
        calibrated_at=_SESSION_CAPTURED_AT,
        distortion_model="opencv_pinhole",
    )


def look_at_pose_sheet(
    camera_position_sheet_mm: np.ndarray, target_sheet_mm: np.ndarray
) -> tuple[np.ndarray, np.ndarray]:
    """Build a sheet-frame camera pose looking from one point at another.

    Returns:
        ``(rvec_sheet_rad, tvec_sheet_mm)``, each shaped ``(3, 1)``.
    """
    camera_position_sheet_mm = np.asarray(camera_position_sheet_mm, dtype=np.float64)
    forward = np.asarray(target_sheet_mm, dtype=np.float64) - camera_position_sheet_mm
    forward /= np.linalg.norm(forward)

    # Board "up" is sheet -Z. Straight-down views need a different hint.
    up_hint = np.array([0.0, 0.0, -1.0])
    if np.linalg.norm(np.cross(forward, up_hint)) < 1e-6:
        up_hint = np.array([0.0, 1.0, 0.0])
    right = np.cross(forward, up_hint)
    right /= np.linalg.norm(right)
    down = np.cross(forward, right)

    rotation = np.vstack([right, down, forward])
    translation_mm = -rotation @ camera_position_sheet_mm
    rvec_rad, _ = cv2.Rodrigues(rotation)
    return rvec_rad.reshape(3, 1), translation_mm.reshape(3, 1)


def side_camera_position_sheet_mm(
    spec: BoardSpec, angle_deg: float, radius_mm: float = 550.0, height_mm: float = 300.0
) -> np.ndarray:
    """A side camera on the capture circle, at ``angle_deg`` about the board centre."""
    center_x_mm, center_y_mm = spec.board_center_sheet_mm
    angle_rad = np.radians(angle_deg)
    return np.array(
        [
            center_x_mm + radius_mm * np.cos(angle_rad),
            center_y_mm + radius_mm * np.sin(angle_rad),
            -height_mm,
        ],
        dtype=np.float64,
    )


def _row_covering_board_area(
    projected_px: np.ndarray, image_shape: tuple[int, int], fraction: float
) -> int:
    """Topmost image row of a bottom band that covers ``fraction`` of the board's area.

    Measured on the board's *projected area*, not on its bounding box: under perspective
    the near edge is much larger, so a band covering 70 percent of the bounding box
    height hides far more than 70 percent of the board.
    """
    board_mask = np.zeros(image_shape, dtype=np.uint8)
    cv2.fillConvexPoly(board_mask, np.round(projected_px).astype(np.int32), 1)
    rows_px = board_mask.sum(axis=1)
    total_px = int(rows_px.sum())
    if total_px == 0:
        return 0
    from_bottom_px = np.cumsum(rows_px[::-1])
    band_rows = int(np.searchsorted(from_bottom_px, fraction * total_px)) + 1
    return max(0, image_shape[0] - band_rows)


def render_charuco_view(
    spec: BoardSpec,
    board: cv2.aruco.CharucoBoard,
    intrinsics: Intrinsics,
    rvec_sheet_rad: np.ndarray,
    tvec_sheet_mm: np.ndarray,
    *,
    occlusion_fraction: float = 0.0,
    draw_plant: bool = False,
) -> SyntheticView:
    """Render the board as seen from a known sheet-frame pose.

    The board texture is warped into the view with the homography between its four sheet
    corners and their projections, which is exact for a plane under a pinhole camera.

    Args:
        occlusion_fraction: Fraction of the board's image bounding box, measured from the
            bottom, to cover with an opaque patch - the plant standing on the board.
        draw_plant: Draw a green blob above the board, so that silhouette segmentation
            has something to find.
    """
    texture_width_px = int(round(spec.board_width_mm * _TEXTURE_PX_PER_MM))
    texture_height_px = int(round(spec.board_height_mm * _TEXTURE_PX_PER_MM))
    texture = board.generateImage(
        (texture_width_px, texture_height_px), marginSize=0, borderBits=1
    )

    sheet_corners_mm = np.array(
        [
            [0.0, 0.0, 0.0],
            [spec.board_width_mm, 0.0, 0.0],
            [spec.board_width_mm, spec.board_height_mm, 0.0],
            [0.0, spec.board_height_mm, 0.0],
        ],
        dtype=np.float64,
    )
    projected_px, _ = cv2.projectPoints(
        sheet_corners_mm,
        rvec_sheet_rad,
        tvec_sheet_mm,
        intrinsics.camera_matrix_array,
        intrinsics.dist_coeffs_array,
    )
    projected_px = projected_px.reshape(-1, 2).astype(np.float32)

    texture_corners_px = np.array(
        [
            [0.0, 0.0],
            [texture_width_px, 0.0],
            [texture_width_px, texture_height_px],
            [0.0, texture_height_px],
        ],
        dtype=np.float32,
    )
    homography = cv2.getPerspectiveTransform(texture_corners_px, projected_px)

    height_px, width_px = intrinsics.image_shape
    canvas = np.full((height_px, width_px), _BACKGROUND_VALUE, dtype=np.uint8)
    canvas = cv2.warpPerspective(
        texture,
        homography,
        (width_px, height_px),
        dst=canvas,
        flags=cv2.INTER_LINEAR,
        borderMode=cv2.BORDER_TRANSPARENT,
    )
    image = cv2.cvtColor(canvas, cv2.COLOR_GRAY2BGR)

    if occlusion_fraction > 0.0:
        cover_top_px = _row_covering_board_area(
            projected_px, (height_px, width_px), occlusion_fraction
        )
        x_min = float(projected_px[:, 0].min())
        x_max = float(projected_px[:, 0].max())
        cv2.rectangle(
            image,
            (int(np.floor(x_min)), int(cover_top_px)),
            (int(np.ceil(x_max)), height_px),
            (40, 90, 40),
            thickness=cv2.FILLED,
        )

    if draw_plant:
        center_x_mm, center_y_mm = spec.board_center_sheet_mm
        canopy_sheet_mm = np.array(
            [[center_x_mm, center_y_mm, -150.0]], dtype=np.float64
        )
        canopy_px, _ = cv2.projectPoints(
            canopy_sheet_mm,
            rvec_sheet_rad,
            tvec_sheet_mm,
            intrinsics.camera_matrix_array,
            intrinsics.dist_coeffs_array,
        )
        center_px = tuple(int(round(value)) for value in canopy_px.reshape(2))
        cv2.ellipse(
            image,
            center_px,
            (int(width_px * 0.09), int(height_px * 0.11)),
            0,
            0,
            360,
            (35, 150, 45),
            thickness=cv2.FILLED,
        )

    return SyntheticView(
        image=image,
        rvec_sheet_rad=np.asarray(rvec_sheet_rad, dtype=np.float64).reshape(3),
        tvec_sheet_mm=np.asarray(tvec_sheet_mm, dtype=np.float64).reshape(3),
    )


@pytest.fixture
def render_view(board_spec: BoardSpec, charuco_board, synthetic_intrinsics):
    """Factory: ``render_view(angle_deg, occlusion_fraction=..., draw_plant=...)``."""

    def _render(
        angle_deg: float = 25.0,
        *,
        occlusion_fraction: float = 0.0,
        draw_plant: bool = False,
    ) -> SyntheticView:
        rvec_sheet_rad, tvec_sheet_mm = look_at_pose_sheet(
            side_camera_position_sheet_mm(board_spec, angle_deg),
            np.array([*board_spec.board_center_sheet_mm, -110.0]),
        )
        return render_charuco_view(
            board_spec,
            charuco_board,
            synthetic_intrinsics,
            rvec_sheet_rad,
            tvec_sheet_mm,
            occlusion_fraction=occlusion_fraction,
            draw_plant=draw_plant,
        )

    return _render


@pytest.fixture
def clean_settings(monkeypatch, tmp_path: Path):
    """A :class:`Settings` built from a scratch data root, with the cache cleared."""
    from tomato3d.config import get_settings

    monkeypatch.setenv("TOMATO3D_DATA_ROOT", str(tmp_path / NON_ASCII_DATA_DIRNAME))
    monkeypatch.setenv("TOMATO3D_CONFIG_DIR", str(CONFIG_DIR))
    monkeypatch.setenv("TOMATO3D_CAMERA_ID", "cam_synth")
    monkeypatch.setenv("TOMATO3D_LOG_LEVEL", "WARNING")
    monkeypatch.setenv("TOMATO3D_MAX_WORKERS", "2")
    get_settings.cache_clear()
    settings = get_settings()
    yield settings
    get_settings.cache_clear()


def manifest_payload(
    spec: BoardSpec, side_angles_deg: list[float], top_positions: list[str]
) -> dict:
    """A valid ``session_manifest.json`` payload for a synthetic session."""
    images = [
        {
            "file": f"images/side_{index:03d}.jpg",
            "view_type": "side",
            "top_position": None,
            "nominal_angle_deg": angle_deg,
        }
        for index, angle_deg in enumerate(side_angles_deg)
    ]
    images += [
        {
            "file": f"images/top_{position}.jpg",
            "view_type": "top",
            "top_position": position,
            "nominal_angle_deg": None,
        }
        for position in top_positions
    ]
    capture_config = json.loads(
        (CONFIG_DIR / "capture_config.json").read_text(encoding="utf-8")
    )
    return {
        "schema_version": SCHEMA_VERSION,
        "plant_id": "DT-001",
        "session_id": "DT-001_20260915_0900",
        "captured_at": _SESSION_CAPTURED_AT.isoformat(),
        "camera_id": "cam_synth",
        "board_variant_id": spec.variant_id,
        "board_spec_ref": "config/board_spec.json",
        "intrinsics_ref": "calib/intrinsics_cam_synth.json",
        "rotation_mode": "board_with_plant",
        "side_view_count": len(side_angles_deg),
        "side_view_step_deg": capture_config["side_view_step_deg"],
        "top_view_count": len(top_positions),
        "top_view_method": "camera_moved_to_overhead_jig",
        "top_view_positions_mm": capture_config["top_view_positions_mm"],
        "operational_top_view": capture_config["operational_top_view"],
        "side_camera_radius_mm": capture_config["side_camera_radius_mm"],
        "side_camera_height_mm": capture_config["side_camera_height_mm"],
        "color_chart_in_frame": True,
        "scale_reference_block_mm": spec.scale_block_nominal_height_mm,
        "environment_log_ref": None,
        "images": images,
        "notes": "synthetic session",
    }


@pytest.fixture
def make_manifest_payload(board_spec: BoardSpec):
    """Factory: ``make_manifest_payload(side_angles_deg, top_positions)``."""

    def _make(side_angles_deg: list[float], top_positions: list[str]) -> dict:
        return manifest_payload(board_spec, side_angles_deg, top_positions)

    return _make


@pytest.fixture
def synthetic_session(
    clean_settings,
    board_spec: BoardSpec,
    charuco_board,
    synthetic_intrinsics: Intrinsics,
    tmp_path: Path,
):
    """A complete synthetic session on disk: images, manifest and intrinsics."""
    from tomato3d.io.images import write_image
    from tomato3d.io.schemas import dump_json_model, validate_model

    side_angles_deg = [float(index * 45) for index in range(8)]
    payload = manifest_payload(board_spec, side_angles_deg, ["T0"])
    manifest = validate_model(payload, SessionManifest, source="synthetic")

    session_dir = (
        clean_settings.raw_dir / manifest.plant_id / manifest.session_id
    )
    (session_dir / "images").mkdir(parents=True, exist_ok=True)

    for index, angle_deg in enumerate(side_angles_deg):
        rvec_sheet_rad, tvec_sheet_mm = look_at_pose_sheet(
            side_camera_position_sheet_mm(board_spec, angle_deg),
            np.array([*board_spec.board_center_sheet_mm, -110.0]),
        )
        view = render_charuco_view(
            board_spec,
            charuco_board,
            synthetic_intrinsics,
            rvec_sheet_rad,
            tvec_sheet_mm,
            draw_plant=True,
        )
        write_image(session_dir / f"images/side_{index:03d}.jpg", view.image)

    top_rvec_rad, top_tvec_mm = look_at_pose_sheet(
        np.array([*board_spec.board_center_sheet_mm, -550.0]),
        np.array([*board_spec.board_center_sheet_mm, 0.0]),
    )
    top_view = render_charuco_view(
        board_spec,
        charuco_board,
        synthetic_intrinsics,
        top_rvec_rad,
        top_tvec_mm,
        draw_plant=True,
    )
    write_image(session_dir / "images/top_T0.jpg", top_view.image)

    dump_json_model(session_dir / "session_manifest.json", manifest)
    dump_json_model(
        clean_settings.intrinsics_path("cam_synth"), synthetic_intrinsics
    )
    return session_dir


# --------------------------------------------------------------------------------------
# Leaf light-use
# --------------------------------------------------------------------------------------

#: Example light inputs. Every physical value in them is a placeholder, and the readings
#: are synthetic; they exercise the flow and double as the template a person copies.
LIGHT_FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures" / "light"


def light_input(value: object, status: str = "assumed") -> dict:
    """A ``ScalarInput`` / ``VectorInput`` payload."""
    source = "unavailable in test" if value is None else "test value"
    return {"value": value, "status": status, "source": source}


def point_fixture_payload(
    fixture_id: str = "L1",
    *,
    center_mm: tuple[float, float, float] = (0.0, 0.0, 1000.0),
    photon_flux_umol_s: float | None = 100.0,
    half_angle_deg: float = 60.0,
    cutoff_deg: float = 90.0,
    aim_tilt_deg: float = 0.0,
    aim_azimuth_deg: float = 0.0,
    length_mm: float = 0.0,
    emitter_grid: tuple[int, int] = (1, 1),
    electrical_input_w: float | None = 40.0,
    schedule: list[dict] | None = None,
) -> dict:
    """A downward point lamp, Lambertian by default, lit 06:00-22:00 at full output."""
    return {
        "fixture_id": fixture_id,
        "model_name": "test lamp",
        "emitting_center_grow_mm": light_input(list(center_mm)),
        "aim_tilt_deg": light_input(aim_tilt_deg),
        "aim_azimuth_deg": light_input(aim_azimuth_deg),
        "long_axis_azimuth_deg": light_input(0.0),
        "emitting_length_mm": light_input(length_mm),
        "emitting_width_mm": light_input(0.0),
        "emitter_grid": list(emitter_grid),
        "photon_flux_umol_s": light_input(
            photon_flux_umol_s, "assumed" if photon_flux_umol_s is not None else "unavailable"
        ),
        "photon_band": "PAR_400_700nm",
        "distribution": {
            "kind": "cosine_power",
            "half_intensity_half_angle_deg": light_input(half_angle_deg),
            "cutoff_half_angle_deg": cutoff_deg,
        },
        "electrical_input_w": light_input(
            electrical_input_w, "assumed" if electrical_input_w is not None else "unavailable"
        ),
        "electrical_boundary": "wall_plug_including_driver",
        "schedule": schedule
        if schedule is not None
        else [{"start_hhmm": "06:00", "end_hhmm": "22:00", "output_fraction": 1.0}],
    }


def light_scene_payload(
    fixtures: list[dict] | None = None,
    plants: list[str] = (),
    *,
    transmittance: float | None = 0.1,
    absorptance: float | None = 0.85,
    subdivisions: int = 1,
) -> dict:
    """A valid ``LightScene`` payload; plants sit with the board origin at the grow origin."""
    return {
        "schema_version": "1.0",
        "setup_id": "test_setup",
        "grow_frame_description": "test frame",
        "ambient_light": "excluded_dark_room",
        "reflections": "not_modelled",
        "fixtures": fixtures if fixtures is not None else [point_fixture_payload()],
        "plants": [
            {
                "plant_id": plant_id,
                "board_origin_grow_mm": light_input([0.0, 0.0, 0.0], "measured"),
                "board_yaw_deg": light_input(0.0, "measured"),
                "posture_since_capture": "unchanged_checked",
            }
            for plant_id in plants
        ],
        "leaf_optics": {
            "photon_band": "PAR_400_700nm",
            "absorptance": light_input(
                absorptance, "assumed" if absorptance is not None else "unavailable"
            ),
            "transmittance": light_input(
                transmittance, "assumed" if transmittance is not None else "unavailable"
            ),
            "reflectance": light_input(0.05),
        },
        "simulation": {
            "triangle_subdivisions": subdivisions,
            "ray_offset_mm": 0.01,
            "max_ray_triangle_pairs_per_chunk": 100000,
        },
        "validation": {"ppfd_bin_edges_umol_m2_s": None},
        "scenarios": [],
    }
