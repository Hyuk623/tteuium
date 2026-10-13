"""P1.10 / P1.11 - package build, validation, failure handling, P2 dry-read, replay, CLI exits.

Runs under a Korean path (the project's own path class; image IO must survive it).
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path

import pytest

from tomato3d.cli import run_p1
from tomato3d.io.tables import read_table, write_table
from tomato3d.state import canopy as cn
from tomato3d.state import package as pk
from tomato3d.state import schema as s

FIX = "tests/fixtures/p1/O-mature/scenes"
pytestmark = pytest.mark.skipif(not (pk.PROJECT_ROOT / cn.SLOT_TABLE).exists(), reason="slot table absent")


def small_request() -> dict:
    return dict(
        mode="fixture",
        source_plants=[dict(source_plant_id="fx_a", scene_dir=f"{FIX}/scene_0000")],
        donor_scene=f"{FIX}/scene_0001",
        completion_pool_scenes=[f"{FIX}/scene_0001"],
        sequences={"fx_a": [dict(capture_id="c0", time_h=0, phase="am", yaw_deg=0),
                            dict(capture_id="c1", time_h=12, phase="pm", yaw_deg=30, occlude=[2]),
                            dict(capture_id="c2", time_h=24, phase="am", yaw_deg=-10, remove=[1], add=[[3, 200.0]])]},
        instances=[dict(plant_instance_id="fx_a", slot_id="T2-row2-L", yaw_deg=0.0, variety="micro_tom"),
                   dict(plant_instance_id="fx_a#2", slot_id="T2-row2-R", yaw_deg=45.0, variety="micro_tom"),
                   dict(plant_instance_id="fx_o", slot_id="T2-row4-R", yaw_deg=0.0, variety="other")],
        decisions=None)


@pytest.fixture(scope="module")
def built(tmp_path_factory) -> Path:
    target = tmp_path_factory.mktemp("p1") / "한글 경로" / "p1_state_test_01"
    return pk.build_fixture(target, small_request())


def test_package_validates_and_has_every_file(built) -> None:
    assert pk.validate(built) == []
    for name in ("captures.csv", "identity_manifest.csv", "mtg_vertices.csv", "areas.csv",
                 "optical_surface_manifest.csv", "canopy_placement.json", "p1_manifest.json", "viewer/index.html",
                 "observations/observations.csv", "truth/truth_mtg_vertices.csv", "compare_observation.csv"):
        assert (built / name).exists(), name
    man = json.loads((built / "p1_manifest.json").read_text(encoding="utf-8"))
    assert man["schema_version"] == s.P1_SCHEMA_VERSION and man["evidence"] == "synthetic_fixture"
    assert man["counts_as_photo_reconstruction"] is False and man["overall_status"] == "fixture_only"
    assert man["input_snapshot"] and man["p2_field_map"]
    assert man["tracking_identity_scores"]["fx_a"]["wrong_links"] == 0


def test_duplicate_instance_and_other_variety(built) -> None:
    doc = json.loads((built / "canopy_placement.json").read_text(encoding="utf-8"))
    inst = {i["plant_instance_id"]: i for i in doc["instances"]}
    assert inst["fx_a"]["duplicate_of_source"] and inst["fx_a#2"]["source_plant_id"] == "fx_a"
    assert inst["fx_o"]["in_optical_scene"] is False
    optical = read_table(built / "optical_surface_manifest.csv", s.OPTICAL_MANIFEST_COLUMNS)
    owners = {s.split_external_id(r["external_leaflet_id"])[0] for r in optical}
    assert owners == {"fx_a", "fx_a#2"}
    check = json.loads((built / "canopy_merge_check.json").read_text(encoding="utf-8"))
    assert check["round_trip_ok"] and check["duplicate_instances_distinct"]
    ident = read_table(built / "identity_manifest.csv", s.IDENTITY_COLUMNS)
    a = [(r["capture_id"], r["organ_id"], r["track_state"]) for r in ident if r["plant_instance_id"] == "fx_a"]
    b = [(r["capture_id"], r["organ_id"], r["track_state"]) for r in ident if r["plant_instance_id"] == "fx_a#2"]
    assert a == b and a


def test_p2_dry_read(built) -> None:
    dry = pk.p2_dry_read(built)
    assert dry["ok"] and {r["plant_instance_id"] for r in dry["plants_csv_rows"]} == {"fx_a", "fx_a#2"}
    assert set(dry["plants_csv_rows"][0]) >= {"tx_mm", "ty_mm", "tz_mm", "yaw_deg", "transform_source"}
    assert dry["v3_stage2_boundary"]["rows_with_metric_3d_observed_or_model_estimated"] == 0


def test_tampering_and_mislabelled_evidence_fail(built, tmp_path) -> None:
    copy = tmp_path / "copy"
    shutil.copytree(built, copy)
    rows = read_table(copy / "mtg_vertices.csv", s.MTG_VERTICES_COLUMNS)
    rows[0]["evidence"] = "real_photo"
    write_table(copy / "mtg_vertices.csv", rows, s.MTG_VERTICES_COLUMNS)
    problems = pk.validate(copy)
    assert any("changed since publish" in p for p in problems)
    assert any("real_photo" in p or "labels a row" in p for p in problems)


def test_stale_code_is_detected(built, monkeypatch) -> None:
    real = pk.code_hashes()
    monkeypatch.setattr(pk, "code_hashes", lambda root=pk.PROJECT_ROOT: dict(real, **{"tomato3d/state/schema.py": "x"}))
    assert any(p.startswith("stale") for p in pk.validate(built))


def test_failed_build_publishes_nothing(tmp_path, monkeypatch) -> None:
    def boom(*a, **k):
        raise RuntimeError("engine failure mid-run")

    monkeypatch.setattr(pk.cn, "place", boom)
    target = tmp_path / "p1_state_fail"
    with pytest.raises(RuntimeError):
        pk.build_fixture(target, small_request())
    assert not target.exists()
    assert not list(tmp_path.glob(".p1_state_fail.staging-*"))


def test_existing_package_is_never_overwritten(built) -> None:
    with pytest.raises(pk.PackageError, match="already holds"):
        pk.build_fixture(built, small_request())


def test_replay_is_deterministic(built) -> None:
    result = pk.replay(built)
    assert result["ok"], result


def test_cli_prepare_run_collect_and_exit_codes(tmp_path) -> None:
    req = tmp_path / "req.json"
    req.write_text(json.dumps(small_request()), encoding="utf-8")
    out = tmp_path / "프로젝트" / "p1_state_cli_01"
    assert run_p1.main(["prepare", "--mode", "fixture", "--out", str(out), "--request", str(req)]) == 0
    assert run_p1.main(["prepare", "--mode", "fixture", "--out", str(out), "--request", str(req)]) == 2
    assert run_p1.main(["prepare", "--mode", "real", "--out", str(tmp_path / "x"), "--request", str(req)]) == 2
    assert run_p1.main(["run", "--package", str(out)]) == 0
    assert (out / "p1_request.json").exists() and (out / "p1_manifest.json").exists()
    assert run_p1.main(["collect", "--package", str(out)]) == 0
    assert run_p1.main(["compare-observation", "--package", str(out), "--out", str(tmp_path / "cmp.csv")]) == 0
    man = json.loads((out / "p1_manifest.json").read_text(encoding="utf-8"))
    man["overall_status"] = "partial"
    (out / "p1_manifest.json").write_text(json.dumps(man), encoding="utf-8")
    assert run_p1.main(["collect", "--package", str(out)]) == 3, "a partial package is never success"
    (out / "areas.csv").write_text("broken\n", encoding="utf-8")
    assert run_p1.main(["collect", "--package", str(out)]) == 1
    assert run_p1.main(["run", "--package", str(tmp_path / "missing")]) == 2
