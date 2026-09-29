"""Regressions for handoff/CLAUDE_CODE_REVIEW_2026-09-29.md (bugs B1-B4)."""
from __future__ import annotations

from pathlib import Path

import pytest

from tomato3d.io.schemas import SchemaError, SessionManifest, validate_model
from tomato3d.io.tables import read_table, read_table_columns


# B1: an empty or malformed CSV is a schema error (CLI exit 2), not a pandas traceback
def test_empty_csv_is_a_schema_error(tmp_path: Path) -> None:
    empty = tmp_path / "empty.csv"
    empty.write_text("", encoding="utf-8")
    with pytest.raises(SchemaError, match="cannot read table"):
        read_table(empty)
    with pytest.raises(SchemaError):
        read_table_columns(empty)


def test_malformed_csv_is_a_schema_error(tmp_path: Path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text('a,b\n1,"2\n3,4\n', encoding="utf-8")  # unterminated quote
    with pytest.raises(SchemaError, match="cannot read table"):
        read_table(bad)


def test_run_light_exits_2_on_an_empty_readings_csv(tmp_path: Path, clean_settings) -> None:
    from tomato3d.cli.run_light import main

    empty = tmp_path / "ppfd_readings.csv"
    empty.write_text("", encoding="utf-8")
    scene = Path(__file__).parent / "fixtures" / "light" / "light_scene.example.json"
    assert main(["--scene", str(scene), "--readings", str(empty), "--out", str(tmp_path / "out")]) == 2


# B2: only the implemented origin corner is accepted
def test_origin_corner_other_than_top_left_is_refused(board_spec) -> None:
    from tomato3d.io.schemas import BoardSpec

    payload = {**board_spec.model_dump(mode="json"), "origin_corner": "bottom_left"}
    with pytest.raises(SchemaError, match="origin_corner"):
        validate_model(payload, BoardSpec, source="test")


# B3: two images with one stem would overwrite each other's mask
def test_manifest_refuses_two_images_with_one_stem(make_manifest_payload) -> None:
    payload = make_manifest_payload([0.0], ["T0"])
    top = next(e for e in payload["images"] if e["view_type"] == "top")
    side = next(e for e in payload["images"] if e["view_type"] == "side")
    top["file"] = "images/top/000.jpg"
    side["file"] = "images/side/000.jpg"
    with pytest.raises(SchemaError, match="share the stem"):
        validate_model(payload, SessionManifest, source="test")


# B4: a bad TOMATO3D_* value is an input error (exit 2), not a traceback
@pytest.mark.parametrize("module", ["run_light", "run_stage1", "calibrate_intrinsics"])
def test_cli_exits_2_on_a_bad_environment_value(module: str, monkeypatch, tmp_path: Path) -> None:
    import importlib

    from tomato3d.config import get_settings

    monkeypatch.setenv("TOMATO3D_MAX_WORKERS", "abc")
    get_settings.cache_clear()
    try:
        cli = importlib.import_module(f"tomato3d.cli.{module}")
        argv = {"run_light": ["--out", str(tmp_path / "o")], "run_stage1": ["--session", str(tmp_path)],
                "calibrate_intrinsics": ["--images", str(tmp_path)]}[module]
        assert cli.main(argv) == 2
    finally:
        get_settings.cache_clear()
