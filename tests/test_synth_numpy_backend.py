"""Generator: numpy derive/interpret backend and the narrow ``fixed=`` whitelist (P1 fixes A4/A5)."""

from __future__ import annotations

import json
from pathlib import Path

import numpy as np
import pytest

from tomato3d.synth import compound_leaf as cl
from tomato3d.synth.config import load_generator_config

ROOT = Path(__file__).resolve().parents[1]
O_CELL = ROOT / "build/synthetic_dwarf_tomato_20261008_07/O-mature"
COMPOUND = dict(compound_id="L01", attachment_mm=[0.0, 0.0, 20.0], direction_unit=[0.6, 0.2, 0.77],
                rachis_arc_length_mm=55.0, left_extent_mm=40.0, right_extent_mm=40.0)


@pytest.fixture(scope="module")
def cfg() -> dict:
    return load_generator_config()


def test_fixed_none_is_bit_identical_and_pins_only_whitelisted(cfg) -> None:
    a = cl.sample_interior(cfg, COMPOUND, 50, 7, 0)
    b = cl.sample_interior(cfg, COMPOUND, 50, 7, 0, None)
    assert a == b
    pinned = cl.sample_interior(cfg, COMPOUND, 50, 7, 0, {"terminal_rel_length": 0.61, "contour_index.T": 4,
                                                          "width_scale.T": 1.33})
    assert pinned["terminal_rel_length"] == 0.61
    assert pinned["leaflets"]["T"]["contour_index"] == 4 and pinned["leaflets"]["T"]["width_scale"] == 1.33
    # the RNG stream is untouched: every other draw is identical
    for key in a:
        if key not in ("terminal_rel_length", "leaflets"):
            assert pinned[key] == a[key], key
    for tag, leaf in a["leaflets"].items():
        other = pinned["leaflets"][tag]
        for k, v in leaf.items():
            if not (tag == "T" and k in ("contour_index", "width_scale")):
                assert other[k] == v, (tag, k)


def test_fixed_rejects_unknown_keys_and_out_of_pool_contours(cfg) -> None:
    with pytest.raises(ValueError, match="whitelist"):
        cl.sample_interior(cfg, COMPOUND, 50, 7, 0, {"leaflet_pairs": 3})
    with pytest.raises(ValueError, match="outside the contour pool"):
        cl.sample_interior(cfg, COMPOUND, 50, 7, 0, {"contour_index.T": 50})


def test_derive_modules_follows_the_grammar() -> None:
    events = [(0, "P1L", "L", 5.0, 0.3, 40.0), (0, "P1R", "R", 4.0, 0.3, 40.0), (2, "I1", "L", 2.0, 0.0, 40.0)]
    mods = cl.derive_modules(events, 3.0, 2.0, 3, 20.0)
    assert [m[0] for m in mods] == ["I", "LP", "LP", "I", "I", "LP", "T"]
    assert cl.derive_modules([], 0.0, 0.0, 1, 9.0) == [("I", 0.0, 0.0), ("T", 9.0)]


def test_numpy_turtle_conventions() -> None:
    t = cl._Turtle(np.zeros(3), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]))
    assert np.allclose(t.left_axis, [0, 1, 0])
    t.down(90)
    assert np.allclose(t.h, [0, 0, -1]) and np.allclose(t.u, [1, 0, 0])
    t2 = cl._Turtle(np.zeros(3), np.array([1.0, 0, 0]), np.array([0, 0, 1.0]))
    t2.left(90)
    assert np.allclose(t2.h, [0, 1, 0])
    t2.push(); t2.f(2.0); t2.pop()
    assert np.allclose(t2.p, 0)


def test_unknown_backend_rejected(cfg) -> None:
    with pytest.raises(ValueError, match="backend"):
        cl.build_compound(cfg, COMPOUND, [np.zeros((4, 2))], 1, "p", backend="opengl")


@pytest.mark.skipif(not (O_CELL / "scenes/scene_0000/plant_graph.json").exists(), reason="O-mature run not on disk")
def test_numpy_backend_reproduces_stored_lpy_plantgl_interiors() -> None:
    from tomato3d.synth.contours import load_library

    cfg_o = json.loads((O_CELL / "generator_config.json").read_text(encoding="utf-8"))
    contours, _ = load_library(O_CELL / "leaflet_contours.json")
    worst = 0.0
    for scene in ("scene_0000", "scene_0007"):
        g = json.loads((O_CELL / "scenes" / scene / "plant_graph.json").read_text(encoding="utf-8"))
        for comp in g["compounds"]:
            stored = g["interiors"][comp["compound_id"]]
            got, _ = cl.build_compound(cfg_o, comp, contours, g["seed"] * 1000 + g["attempt"], g["plant_id"],
                                       backend="numpy")
            assert got["attempt"] == stored["attempt"]
            worst = max(worst, float(np.abs(np.array(got["rachis_points_mm"]) - np.array(stored["rachis_points_mm"])).max()))
            for a, b in zip(got["leaflets"], stored["leaflets"]):
                assert a["tag"] == b["tag"] and a["contour_index"] == b["contour_index"]
                for k in ("base_mm", "heading", "up", "left"):
                    worst = max(worst, float(np.abs(np.array(a[k]) - np.array(b[k])).max()))
    assert worst < 1e-8
