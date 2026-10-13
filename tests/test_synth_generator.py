"""Synthetic generator end to end (P3 + L-Py + meshes + raster): determinism and the
P3 -> L-Py contract. Skipped where the tomato_synth dependencies are missing."""

from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path

import numpy as np
import pytest

pytest.importorskip("openalea.lpy")
pytest.importorskip("openalea.plantgl.all")

from tomato3d.synth.compound_leaf import CompoundRejected, build_compound, check_contract  # noqa: E402
from tomato3d.synth.config import constant, load_generator_config  # noqa: E402
from tomato3d.synth.leaflet_surface import normalize_contour  # noqa: E402

from tests.test_synth_raster import _geom, _look_at_view  # noqa: E402


def _contours(n=4):
    out = []
    for k in range(n):
        t = np.linspace(0, 2 * np.pi, 120, endpoint=False)
        pts = np.c_[60 * np.cos(t), (25 + 4 * k) * np.sin(t) * (1 + 0.3 * np.cos(t))]
        out.append(normalize_contour(pts, 48)["points"])
    return out


def _compound(**over):
    c = dict(compound_id="L03", rank_from_bottom=3, attachment_mm=[0.0, 0.0, 30.0], direction_unit=[0.8, 0.0, 0.6],
             rachis_arc_length_mm=50.0, left_extent_mm=25.0, right_extent_mm=25.0)
    c.update(over)
    return c


def test_compound_respects_p3_length_and_extents():
    cfg = load_generator_config()
    contours = _contours()
    interior, _ = build_compound(cfg, _compound(), contours, 7, "syn")
    assert check_contract(_compound(), interior, contours, cfg) is None
    rachis = np.array(interior["rachis_points_mm"])
    terminal = next(l for l in interior["leaflets"] if l["tag"] == "T")
    axis = np.linalg.norm(np.diff(rachis, axis=0), axis=1).sum() + terminal["length_mm"]
    assert abs(axis - 50.0) <= constant(cfg, "contract_length_tolerance_rel") * 50.0
    assert all(l["leaflet_id"].startswith("syn/L03/") for l in interior["leaflets"])


def test_contract_violation_rejected_and_resampled_never_clipped():
    cfg = load_generator_config()
    with pytest.raises(CompoundRejected) as exc:
        build_compound(cfg, _compound(left_extent_mm=1.0, right_extent_mm=1.0), _contours(), 7, "syn")
    reasons = {r["reason"] for r in exc.value.rejections}
    assert reasons <= {"left_extent", "right_extent"}
    assert len(exc.value.rejections) == int(constant(cfg, "max_compound_attempts"))


def _hash_tree(root: Path) -> dict[str, str]:
    return {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest()
            for p in sorted(root.rglob("*")) if p.is_file() and "work" not in p.parts}


def test_same_seed_identical_graph_masks_and_manifest(tmp_path):
    from tomato3d.config import get_settings
    from tomato3d.io.schemas import BoardSpec, load_json_model
    from tomato3d.synth import pipeline as pl

    cfg = load_generator_config()
    spec = load_json_model(get_settings().board_spec_path, BoardSpec)
    view = _look_at_view((0.0,) * 5, elevation_deg=50.0, target=(95.0, -57.0, 40.0))
    geom = _geom(view, 256)
    runs = []
    for _ in range(2):
        out = tmp_path / "run"
        if out.exists():
            shutil.rmtree(out)
        scene = pl.build_scene(cfg, 123, "scene_0123", _contours(), spec, out / "scenes" / "scene_0123")
        vdir, layers = pl.write_view_layers(scene, view, 0, geom)
        assert np.all(layers.visible[layers.visible > 0] <= len(scene["index"]))
        row = pl.manifest_row(scene, view, vdir, out, view_kind="ring", rgb_written=False)
        assert row["origin"] == "synthetic"
        runs.append((_hash_tree(out), json.dumps(row, sort_keys=True)))
    assert runs[0] == runs[1]
