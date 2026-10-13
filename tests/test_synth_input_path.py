"""TOMATO3D_SYNTH_PATH_MAP: a generator config written on Windows runs unedited on a Linux CPU box.

The config file keeps its recorded absolute paths (its sha256 is pinned by run contracts); only the reader
remaps the recorded prefix. Unset means no remapping at all.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from tomato3d.config import ENV_SYNTH_PATH_MAP, ConfigError, get_settings
from tomato3d.synth.config import input_path

WIN = "C:\\Users\\me\\proj\\build\\run_06\\banks\\current_195\\bank.json"


@pytest.fixture
def path_map(monkeypatch):
    def set_map(value: str | None) -> None:
        if value is None:
            monkeypatch.delenv(ENV_SYNTH_PATH_MAP, raising=False)
        else:
            monkeypatch.setenv(ENV_SYNTH_PATH_MAP, value)
        get_settings.cache_clear()

    yield set_map
    get_settings.cache_clear()


def test_unset_map_is_the_identity(path_map):
    path_map(None)
    assert get_settings().synth_path_map == ()
    assert input_path(WIN) == Path(WIN)
    assert input_path("relative/bank.json") == Path("relative/bank.json")


def test_recorded_windows_prefix_maps_to_the_local_root(path_map, tmp_path):
    path_map(json.dumps({"C:\\Users\\me\\proj\\": str(tmp_path)}))
    assert input_path(WIN) == tmp_path / "build" / "run_06" / "banks" / "current_195" / "bank.json"
    assert input_path("C:/Users/me/proj/x.json") == tmp_path / "x.json"              # forward slashes too
    other = "C:\\Users\\me\\project_other\\a.json"                                     # prefix ends at a separator
    assert input_path(other) == Path(other)


@pytest.mark.parametrize("bad", ["not json", "[1, 2]", '{"a": 3}'])
def test_malformed_map_is_a_config_error(path_map, bad):
    path_map(bad)
    with pytest.raises(ConfigError):
        get_settings()
