"""Schema round trips, the unavailable sentinel, and null-threshold behaviour."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tomato3d.io.quality import build_quality_record, evaluate_usable_for_training
from tomato3d.io.schemas import (
    POSES_CSV_COLUMNS,
    POSES_CSV_NUMERIC_COLUMNS,
    SCHEMA_VERSION,
    UNAVAILABLE,
    BoardSpec,
    CaptureConfig,
    Intrinsics,
    Pose,
    QualityRecord,
    QualityThresholds,
    SchemaError,
    SessionManifest,
    dump_json_model,
    json_schema,
    load_json_model,
    validate_model,
)
from tomato3d.io.tables import read_poses_csv, read_table, write_poses_csv, write_table

CONFIG_MODELS = (
    ("board_spec.json", BoardSpec),
    ("capture_config.json", CaptureConfig),
    ("quality_thresholds.json", QualityThresholds),
)


@pytest.mark.parametrize("filename,model_cls", CONFIG_MODELS)
def test_shipped_config_validates(project_root: Path, filename, model_cls) -> None:
    load_json_model(project_root / "config" / filename, model_cls)


@pytest.mark.parametrize("filename,model_cls", CONFIG_MODELS)
def test_schema_roundtrip_json(
    project_root: Path, tmp_path: Path, filename, model_cls
) -> None:
    """Every JSON document writes and reads back identically."""
    source = project_root / "config" / filename
    model = load_json_model(source, model_cls)
    destination = tmp_path / filename
    dump_json_model(destination, model)
    assert load_json_model(destination, model_cls) == model
    assert json.loads(destination.read_text(encoding="utf-8")) == json.loads(
        source.read_text(encoding="utf-8")
    )


def test_schema_roundtrip_intrinsics(
    tmp_path: Path, synthetic_intrinsics: Intrinsics
) -> None:
    destination = tmp_path / "intrinsics_cam_synth.json"
    dump_json_model(destination, synthetic_intrinsics)
    assert load_json_model(destination, Intrinsics) == synthetic_intrinsics


def test_schema_roundtrip_manifest(tmp_path: Path, make_manifest_payload) -> None:
    manifest = validate_model(
        make_manifest_payload([0.0, 10.0], ["T0", "T1"]),
        SessionManifest,
        source="test",
    )
    destination = tmp_path / "session_manifest.json"
    dump_json_model(destination, manifest)
    assert load_json_model(destination, SessionManifest) == manifest


def test_schema_roundtrip_poses_csv(tmp_path: Path) -> None:
    """poses.csv writes and reads back identically, column order preserved."""
    solved = Pose(
        pose_status="solved",
        n_corners_detected=21,
        reprojection_error_px=0.4123456789,
        rvec_rad=np.array([0.1234567, -2.3456789, 0.9876543]),
        tvec_mm=np.array([-12.3456, 45.6789, 612.3456]),
        measured_angle_deg=123.456789,
    ).with_identity(
        session_id="DT-001_20260915_0900",
        image_file="images/side_000.jpg",
        view_type="side",
        top_position=None,
    )
    failed = Pose(pose_status="failed", n_corners_detected=2).with_identity(
        session_id="DT-001_20260915_0900",
        image_file="images/side_001.jpg",
        view_type="side",
        top_position=None,
    )

    destination = tmp_path / "poses.csv"
    write_poses_csv(destination, [solved, failed])

    header = destination.read_text(encoding="utf-8").splitlines()[0]
    assert tuple(header.split(",")) == POSES_CSV_COLUMNS

    rows = read_poses_csv(destination)
    assert [row for row in rows] == [solved.to_csv_row(), failed.to_csv_row()]
    assert float(rows[0]["rvec_y"]) == pytest.approx(-2.3456789, abs=0.0)
    assert float(rows[0]["tvec_z_mm"]) == pytest.approx(612.3456, abs=0.0)


def test_table_header_contract_is_enforced(tmp_path: Path) -> None:
    destination = tmp_path / "table.csv"
    write_table(destination, [{"a": "1", "b": "2"}], ("a", "b"))
    with pytest.raises(SchemaError, match="does not match the contract"):
        read_table(destination, ("b", "a"))


def test_unavailable_not_zero(tmp_path: Path) -> None:
    """A failed pose row serialises numeric fields as unavailable, not 0."""
    failed = Pose(
        pose_status="failed", n_corners_detected=3, failure_reason="too few corners"
    ).with_identity(
        session_id="DT-001_20260915_0900",
        image_file="images/side_007.jpg",
        view_type="side",
        top_position=None,
    )
    destination = tmp_path / "poses.csv"
    write_poses_csv(destination, [failed])
    row = read_poses_csv(destination)[0]

    assert row["image_file"] == "images/side_007.jpg"
    assert row["pose_status"] == "failed"
    for column in POSES_CSV_NUMERIC_COLUMNS:
        assert row[column] == UNAVAILABLE, f"{column} must be {UNAVAILABLE!r}"
        assert row[column] != "0"
        assert row[column] != ""

    raw = destination.read_text(encoding="utf-8")
    assert ",0," not in raw and ",,"not in raw


def test_quality_record_omits_later_stage_keys(tmp_path: Path) -> None:
    thresholds = QualityThresholds(
        schema_version=SCHEMA_VERSION,
        min_pose_solved_ratio=0.95,
        max_mean_reprojection_error_px=1.0,
        max_silhouette_area_cv=0.15,
        max_scale_block_height_error_mm=None,
        min_charuco_corners_for_pose=6,
    )
    record = build_quality_record(
        session_id="DT-001_20260915_0900",
        poses=[
            Pose(
                pose_status="solved",
                n_corners_detected=20,
                reprojection_error_px=0.3,
                rvec_rad=np.zeros(3),
                tvec_mm=np.array([0.0, 0.0, 500.0]),
            )
        ],
        silhouette_cv=0.05,
        thresholds=thresholds,
    )
    destination = tmp_path / "quality.json"
    dump_json_model(destination, record)
    payload = json.loads(destination.read_text(encoding="utf-8"))

    assert "scale_block_height_error_mm" not in payload
    assert "hull_voxel_count" not in payload
    assert "depth_scale_fit_rmse_mm" not in payload
    assert load_json_model(destination, QualityRecord) == record


def test_null_threshold_inactive() -> None:
    """A null threshold does not gate usable_for_training."""
    all_null = QualityThresholds(
        schema_version=SCHEMA_VERSION,
        min_pose_solved_ratio=None,
        max_mean_reprojection_error_px=None,
        max_silhouette_area_cv=None,
        max_scale_block_height_error_mm=None,
        min_charuco_corners_for_pose=6,
    )
    assert all_null.active_thresholds == {}

    # Metrics far outside any plausible limit, and one that is not measurable at all.
    usable, reasons = evaluate_usable_for_training(
        solved_ratio=0.1,
        mean_reprojection_error=99.0,
        silhouette_cv=UNAVAILABLE,
        thresholds=all_null,
    )
    assert usable is True
    assert reasons == []

    # The same metrics against an active threshold must fail, otherwise the test above
    # would pass for the wrong reason.
    active = all_null.model_copy(update={"min_pose_solved_ratio": 0.95})
    usable, reasons = evaluate_usable_for_training(
        solved_ratio=0.1,
        mean_reprojection_error=99.0,
        silhouette_cv=UNAVAILABLE,
        thresholds=active,
    )
    assert usable is False
    assert reasons == ["pose_solved_ratio_below_0.95"]


def test_unavailable_metric_cannot_pass_an_active_gate() -> None:
    thresholds = QualityThresholds(
        schema_version=SCHEMA_VERSION,
        min_pose_solved_ratio=0.95,
        max_mean_reprojection_error_px=None,
        max_silhouette_area_cv=None,
        max_scale_block_height_error_mm=None,
        min_charuco_corners_for_pose=6,
    )
    usable, reasons = evaluate_usable_for_training(
        solved_ratio=UNAVAILABLE,
        mean_reprojection_error=UNAVAILABLE,
        silhouette_cv=UNAVAILABLE,
        thresholds=thresholds,
    )
    assert usable is False
    assert reasons == ["pose_solved_ratio_unavailable"]


def test_json_schema_is_exported() -> None:
    for model_cls in (BoardSpec, CaptureConfig, QualityThresholds, Intrinsics,
                      SessionManifest, QualityRecord):
        schema = json_schema(model_cls)
        assert schema["type"] == "object"
        assert "properties" in schema


# --------------------------------------------------------------------------------------
# BoardSpec against the real config/board_spec.json
# --------------------------------------------------------------------------------------

REAL_BOARD_SPEC_PATH = Path(__file__).resolve().parents[1] / "config" / "board_spec.json"


def _real_board_spec_payload() -> dict:
    return json.loads(REAL_BOARD_SPEC_PATH.read_text(encoding="utf-8"))


def test_real_board_spec_validates() -> None:
    """The actual config file - not a fixture copy - satisfies the schema.

    If this fails, the config and the schema have drifted apart again.
    """
    spec = load_json_model(REAL_BOARD_SPEC_PATH, BoardSpec)
    payload = _real_board_spec_payload()

    assert spec.variant_id == payload["variant_id"]
    assert spec.position_frame == "sheet"
    assert spec.expected_marker_count == (spec.squares_x * spec.squares_y) // 2
    assert spec.expected_inner_corner_count == (spec.squares_x - 1) * (spec.squares_y - 1)
    assert len(spec.marker_ids) == spec.expected_marker_count
    # Every top-level key in the file is either a modelled field or a human note.
    note_keys = {key for key in payload if key.startswith("_")}
    assert set(spec.human_notes) == note_keys
    assert set(payload) - note_keys <= set(BoardSpec.model_fields)


def test_real_board_spec_roundtrips_to_the_same_file_content(tmp_path: Path) -> None:
    spec = load_json_model(REAL_BOARD_SPEC_PATH, BoardSpec)
    destination = tmp_path / "board_spec.json"
    dump_json_model(destination, spec)
    assert json.loads(destination.read_text(encoding="utf-8")) == _real_board_spec_payload()
    assert load_json_model(destination, BoardSpec) == spec


@pytest.mark.parametrize(
    "overrides, message",
    [
        ({"expected_marker_count": 25}, "expected_marker_count"),
        ({"expected_inner_corner_count": 49}, "expected_inner_corner_count"),
        ({"marker_ids": list(range(23))}, "marker_ids"),
        ({"marker_ids": "repeat_first_id"}, "duplicate"),
        ({"position_frame": "board"}, "position_frame"),
        ({"scale_block_nominal_height_mm": 0.0}, "scale_block_nominal_height_mm"),
        ({"scale_block_footprint_mm": -1.0}, "scale_block_footprint_mm"),
    ],
)
def test_board_spec_cross_checks_reject_hand_edits(overrides: dict, message: str) -> None:
    payload = _real_board_spec_payload()
    if overrides.get("marker_ids") == "repeat_first_id":
        # Right count, repeated id: only the duplicate check can reject it.
        overrides = {"marker_ids": [0] * payload["expected_marker_count"]}
    with pytest.raises(SchemaError, match=message):
        validate_model({**payload, **overrides}, BoardSpec)


def test_board_spec_null_block_height_is_accepted_and_inactive() -> None:
    spec = validate_model(
        {**_real_board_spec_payload(), "scale_block_nominal_height_mm": None}, BoardSpec
    )
    assert spec.scale_block_nominal_height_mm is None
    assert spec.scale_block_footprint_side_mm == spec.square_size_mm


def test_board_spec_still_forbids_unknown_keys() -> None:
    """Strictness is kept: a typo is an error, only ``_`` notes are free."""
    with pytest.raises(SchemaError, match="sqaures_x"):
        validate_model({**_real_board_spec_payload(), "sqaures_x": 7}, BoardSpec)


def test_board_spec_note_keys() -> None:
    payload = {**_real_board_spec_payload(), "_reviewer_note": "checked on paper"}
    spec = validate_model(payload, BoardSpec)
    assert spec.human_notes["_reviewer_note"] == "checked on paper"
    assert spec.model_dump(mode="json")["_reviewer_note"] == "checked on paper"
    assert "human_notes" not in spec.model_dump(mode="json")

    with pytest.raises(SchemaError, match="_bad_note"):
        validate_model({**payload, "_bad_note": 3}, BoardSpec)
    with pytest.raises(SchemaError, match="human_notes"):
        validate_model({**payload, "human_notes": {}}, BoardSpec)


def test_board_spec_notes_never_affect_behaviour() -> None:
    from tomato3d.calib.board import build_charuco_board, scale_block_box_board_mm

    payload = {**_real_board_spec_payload(), "scale_block_nominal_height_mm": 30.0}
    plain = validate_model(
        {key: value for key, value in payload.items() if not key.startswith("_")}, BoardSpec
    )
    annotated = validate_model({**payload, "_extra_note": "legacy_pattern true"}, BoardSpec)

    plain_board = build_charuco_board(plain)
    annotated_board = build_charuco_board(annotated)
    assert plain_board.getLegacyPattern() == annotated_board.getLegacyPattern()
    assert np.array_equal(
        plain_board.generateImage((700, 700)), annotated_board.generateImage((700, 700))
    )
    assert np.array_equal(scale_block_box_board_mm(plain), scale_block_box_board_mm(annotated))


def test_board_spec_json_schema_describes_note_keys() -> None:
    schema = json_schema(BoardSpec)
    assert "human_notes" not in schema["properties"]
    assert schema["patternProperties"] == {"^_": {"type": "string"}}
    assert schema["additionalProperties"] is False
    for key in _real_board_spec_payload():
        if not key.startswith("_"):
            assert key in schema["properties"], key


# --------------------------------------------------------------------------------------
# Validity failures - not thresholds, never skipped
# --------------------------------------------------------------------------------------


def _all_null_thresholds() -> QualityThresholds:
    return QualityThresholds(
        schema_version=SCHEMA_VERSION,
        min_pose_solved_ratio=None,
        max_mean_reprojection_error_px=None,
        max_silhouette_area_cv=None,
        max_scale_block_height_error_mm=None,
        min_charuco_corners_for_pose=6,
    )


def _solved_pose() -> Pose:
    return Pose(
        pose_status="solved",
        n_corners_detected=36,
        reprojection_error_px=0.2,
        rvec_rad=np.zeros(3),
        tvec_mm=np.array([0.0, 0.0, 500.0]),
    )


def test_validity_failure_gates_even_when_every_threshold_is_null() -> None:
    from tomato3d.io.quality import REASON_OPERATIONAL_TOP_SILHOUETTE_UNAVAILABLE

    record = build_quality_record(
        session_id="DT-001_20260915_0900",
        poses=[_solved_pose()],
        silhouette_cv=0.01,
        thresholds=_all_null_thresholds(),
        validity_failures=[REASON_OPERATIONAL_TOP_SILHOUETTE_UNAVAILABLE],
    )
    assert record.usable_for_training is False
    assert record.failure_reasons == [REASON_OPERATIONAL_TOP_SILHOUETTE_UNAVAILABLE]


def test_validity_failures_follow_threshold_reasons_once_each() -> None:
    from tomato3d.io.quality import (
        REASON_IMAGE_SIZE_MISMATCH,
        REASON_SIDE_SILHOUETTE_UNAVAILABLE,
    )

    thresholds = _all_null_thresholds().model_copy(update={"min_pose_solved_ratio": 0.95})
    record = build_quality_record(
        session_id="DT-001_20260915_0900",
        poses=[_solved_pose(), Pose(pose_status="failed", n_corners_detected=0)],
        silhouette_cv=0.01,
        thresholds=thresholds,
        validity_failures=[
            REASON_IMAGE_SIZE_MISMATCH,
            REASON_SIDE_SILHOUETTE_UNAVAILABLE,
            REASON_IMAGE_SIZE_MISMATCH,
        ],
    )
    assert record.failure_reasons == [
        "pose_solved_ratio_below_0.95",
        REASON_IMAGE_SIZE_MISMATCH,
        REASON_SIDE_SILHOUETTE_UNAVAILABLE,
    ]


def test_no_validity_failures_keeps_the_threshold_decision() -> None:
    record = build_quality_record(
        session_id="DT-001_20260915_0900",
        poses=[_solved_pose()],
        silhouette_cv=0.01,
        thresholds=_all_null_thresholds(),
    )
    assert record.usable_for_training is True
    assert record.failure_reasons == []


def test_unknown_validity_code_is_rejected() -> None:
    with pytest.raises(ValueError, match="unknown validity failure codes"):
        build_quality_record(
            session_id="DT-001_20260915_0900",
            poses=[_solved_pose()],
            silhouette_cv=0.01,
            thresholds=_all_null_thresholds(),
            validity_failures=["looks_fine_to_me"],
        )
