"""Cell O (2026-10-08): determinate cap on compounds per plant through the P3 engine's node_budget."""

from __future__ import annotations

import copy
import json

from tomato3d.synth.config import load_generator_config
from tomato3d.synth.structure import CAP_RANGE, generate_structure, sample_plant_params


def _capped(cfg, lo, hi, age=30):
    c = copy.deepcopy(cfg)
    c["ranges"][CAP_RANGE] = dict(min=lo, max=hi, integer=True, unit="count", source_kind="user_assumed",
                                  source_ref="test")
    if age is not None:
        c["ranges"]["plant_age_days"] = dict(c["ranges"]["plant_age_days"], min=age, max=age)
    return c


def test_cap_draw_leaves_the_other_plant_draws_identical():
    cfg = load_generator_config()
    a = sample_plant_params(cfg, 20264001)
    b = sample_plant_params(_capped(cfg, 4, 6, age=None), 20264001)
    assert CAP_RANGE not in a and 4 <= b[CAP_RANGE] <= 6
    assert {k: v for k, v in b.items() if k != CAP_RANGE} == a


def test_cap_bounds_the_compound_count_and_keeps_growth(tmp_path):
    cfg = load_generator_config()
    free = generate_structure(_capped(cfg, 60, 60), 20264001, tmp_path / "free", "p_free")
    capped = generate_structure(_capped(cfg, 4, 4), 20264001, tmp_path / "cap", "p_cap")
    assert len(free["compounds"]) > 4 and len(capped["compounds"]) == 4
    assert capped["params"][CAP_RANGE] == 4
    model = json.loads((tmp_path / "cap" / "model.json").read_text(encoding="utf-8"))
    stem = model["parameter_particles"][0]["axes"]["stem"]
    assert stem["node_budget"]["pmf"] == [dict(n=4, p=1.0)] and "stop_probability" not in stem
    # the first compounds are the same leaves (same births) and keep growing after the stem stopped
    for f, c in zip(free["compounds"][:4], capped["compounds"]):
        assert f["p3_block_id"] == c["p3_block_id"] and abs(f["age_days"] - c["age_days"]) < 1e-9
        assert abs(f["rachis_arc_length_mm"] - c["rachis_arc_length_mm"]) < 1e-6
