"""Session manifest validation and path resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from tomato3d.io.manifest import (
    ManifestError,
    parse_session_id,
    read_manifest,
    resolve_session_paths,
    write_manifest,
)
from tomato3d.io.schemas import SessionManifest, validate_model

REQUIRED_FIELDS = (
    "plant_id",
    "session_id",
    "captured_at",
    "camera_id",
    "board_variant_id",
    "board_spec_ref",
    "intrinsics_ref",
    "rotation_mode",
    "side_view_count",
    "top_view_count",
    "operational_top_view",
    "images",
)


@pytest.mark.parametrize("missing_field", REQUIRED_FIELDS)
def test_manifest_validation(
    tmp_path: Path, make_manifest_payload, missing_field: str
) -> None:
    """A manifest missing a required field is rejected with the field named."""
    import json

    payload = make_manifest_payload([0.0, 10.0], ["T0"])
    del payload[missing_field]
    path = tmp_path / "session_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestError) as raised:
        read_manifest(path)
    assert missing_field in str(raised.value)


def test_manifest_rejects_unknown_field(tmp_path: Path, make_manifest_payload) -> None:
    import json

    payload = make_manifest_payload([0.0], ["T0"])
    payload["turntable_brand"] = "unspecified"
    path = tmp_path / "session_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestError, match="turntable_brand"):
        read_manifest(path)


def test_manifest_rejects_angle_on_a_top_view(make_manifest_payload) -> None:
    payload = make_manifest_payload([0.0], ["T0"])
    top_entry = next(
        entry for entry in payload["images"] if entry["view_type"] == "top"
    )
    top_entry["nominal_angle_deg"] = 0.0

    from tomato3d.io.schemas import SchemaError

    with pytest.raises(SchemaError, match="nominal_angle_deg"):
        validate_model(payload, SessionManifest, source="test")


def test_manifest_rejects_count_mismatch(make_manifest_payload) -> None:
    payload = make_manifest_payload([0.0, 10.0], ["T0"])
    payload["side_view_count"] = 36

    from tomato3d.io.schemas import SchemaError

    with pytest.raises(SchemaError, match="side_view_count"):
        validate_model(payload, SessionManifest, source="test")


def test_parse_session_id() -> None:
    assert parse_session_id("DT-001_20260915_0900") == ("DT-001", "20260915", "0900")
    with pytest.raises(ManifestError, match="does not match"):
        parse_session_id("DT-001-20260915")


def test_manifest_rejects_plant_id_mismatch(
    tmp_path: Path, make_manifest_payload
) -> None:
    import json

    payload = make_manifest_payload([0.0], ["T0"])
    payload["plant_id"] = "DT-999"
    path = tmp_path / "session_manifest.json"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ManifestError, match="prefix"):
        read_manifest(path)


def test_resolve_session_paths(clean_settings, make_manifest_payload) -> None:
    manifest = validate_model(
        make_manifest_payload([0.0], ["T0"]), SessionManifest, source="test"
    )
    session_dir = clean_settings.raw_dir / manifest.plant_id / manifest.session_id
    session_dir.mkdir(parents=True)
    write_manifest(session_dir / "session_manifest.json", manifest)

    paths = resolve_session_paths(session_dir, clean_settings)
    assert paths.plant_id == manifest.plant_id
    assert paths.session_id == manifest.session_id
    assert paths.manifest_path.is_file()
    assert paths.images_dir == session_dir / "images"
    assert paths.derived_dir == (
        clean_settings.derived_dir / manifest.plant_id / manifest.session_id
    )
    assert paths.poses_csv_path.name == "poses.csv"
    assert paths.quality_json_path.name == "quality.json"
    assert paths.mask_path("images/side_003.jpg") == paths.masks_dir / "side_003.png"


def test_resolve_session_paths_without_manifest(clean_settings, tmp_path: Path) -> None:
    with pytest.raises(ManifestError, match="session_manifest.json"):
        resolve_session_paths(tmp_path, clean_settings)


def test_manifest_accepts_an_unmeasured_scale_block(make_manifest_payload) -> None:
    """A session shot before the block is measured records null, not a placeholder."""
    payload = make_manifest_payload([0.0], ["T0"])
    payload["scale_reference_block_mm"] = None
    manifest = validate_model(payload, SessionManifest, source="test")
    assert manifest.scale_reference_block_mm is None

    from tomato3d.io.schemas import SchemaError

    payload["scale_reference_block_mm"] = 0.0
    with pytest.raises(SchemaError, match="scale_reference_block_mm"):
        validate_model(payload, SessionManifest, source="test")
