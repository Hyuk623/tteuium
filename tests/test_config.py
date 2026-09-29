"""Settings resolution and derived paths."""

from __future__ import annotations

from pathlib import Path

from tomato3d.config import (
    CONFIG_FILE_PROPERTIES,
    DATA_DIR_PROPERTIES,
    Settings,
    get_settings,
)


def test_config_paths(clean_settings: Settings) -> None:
    """Every derived data path property resolves under TOMATO3D_DATA_ROOT."""
    data_root = clean_settings.data_root.resolve()
    assert DATA_DIR_PROPERTIES, "the data path contract must not be empty"
    for property_name in DATA_DIR_PROPERTIES:
        resolved = Path(getattr(clean_settings, property_name)).resolve()
        assert resolved.is_relative_to(data_root), (
            f"{property_name} resolved to {resolved}, outside {data_root}"
        )
    assert clean_settings.intrinsics_path("cam_a").resolve().is_relative_to(data_root)


def test_config_file_paths_live_under_config_dir(clean_settings: Settings) -> None:
    config_dir = clean_settings.config_dir.resolve()
    for property_name in CONFIG_FILE_PROPERTIES:
        resolved = Path(getattr(clean_settings, property_name)).resolve()
        assert resolved.parent == config_dir
        assert resolved.is_file(), f"{property_name} points at a missing file"


def test_settings_cached(clean_settings: Settings) -> None:
    """get_settings() returns the same object twice."""
    assert get_settings() is get_settings()
    assert get_settings() is clean_settings


def test_settings_are_frozen(clean_settings: Settings) -> None:
    import dataclasses

    import pytest

    with pytest.raises(dataclasses.FrozenInstanceError):
        clean_settings.camera_id = "other"  # type: ignore[misc]
