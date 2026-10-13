"""P1 trusses and segments (MTG Amendment A5): registry, segment_index derivation, validators, fixture package."""

from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

import pytest

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import axes as ax
from tomato3d.state import canopy as cn
from tomato3d.state import ingest
from tomato3d.state import package as pk
from tomato3d.state import schema as s
from tomato3d.state import trusses as tr

SCENES = "tests/fixtures/p1/O-mature/scenes"
KST = timezone(timedelta(hours=9))
OLD_SIDESHOOT_PACKAGE = pk.PROJECT_ROOT / "build/p1_state_20261012_03"


def _registry(tmp_path: Path, rows: list[list[str]], name: str = "truss_registry.csv") -> Path:
    path = tmp_path / name
    with path.open("w", encoding="utf-8", newline="") as fh:
        w = csv.writer(fh, lineterminator="\n")
        w.writerow(tr.REGISTRY_COLUMNS)
        w.writerows(rows)
    return path


def _entry(axis: str, above: int | None, serial: int, day: str = "2026-10-10", plant: str = "p") -> tr.TrussEntry:
    return tr.TrussEntry(plant, axis, above, date.fromisoformat(day), serial, f"reg#line{serial + 1}")


# ---------------------------------------------------------------- T3 registry

def test_registry_reads_and_numbers_by_row_order(tmp_path) -> None:
    path = _registry(tmp_path, [["p", "M", "4", "2026-10-09", ""], ["p", "S1", "3", "2026-10-13", ""],
                                ["q", "M", "", "2026-10-01", "position unknown"]])
    entries = tr.read_registry(path)
    assert [(e.plant_id, e.axis, e.above_rank, e.serial) for e in entries] == [
        ("p", "M", 4, 1), ("p", "S1", 3, 2), ("q", "M", None, 1)]
    assert entries[0].vertex_id() == "p/F0001", "creation-order serial, never a rank"


@pytest.mark.parametrize("rows, match", [
    ([["p", "S1.1", "2", "2026-10-09", ""]], "S1.1"),
    ([["p", "X1", "2", "2026-10-09", ""]], "M or S<k>"),
    ([["p", "M", "4", "2026-10-09", ""], ["p", "M", "4", "2026-10-10", ""]], "second truss"),
    ([["p", "M", "4", "2026-10-10", ""], ["p", "M", "6", "2026-10-09", ""]], "observation order"),
    ([["p", "M", "four", "2026-10-09", ""]], "not an integer"),
    ([["p", "M", "4", "10/09/2026", ""]], "ISO date"),
    ([["p", "S1", "4", "2026-10-09", "shoot′"]], "prime"),
])
def test_registry_rejects(tmp_path, rows, match) -> None:
    with pytest.raises((tr.TrussRegistryError, s.P1SchemaError), match=match):
        tr.read_registry(_registry(tmp_path, rows))


def test_registry_header_and_template(tmp_path) -> None:
    bad = tmp_path / "bad.csv"
    bad.write_text("plant_id,axis,above_rank,first_observed,note,segment_index\n", encoding="utf-8")
    with pytest.raises(tr.TrussRegistryError, match="header"):
        tr.read_registry(bad)
    path = tr.write_template(tmp_path / "tpl")
    entries = tr.read_registry(path)
    assert len(entries) == 1 and "EXAMPLE" in path.read_text(encoding="utf-8")
    assert "segment_index" not in path.read_text(encoding="utf-8").splitlines()[0], "never hand-entered"
    assert (tmp_path / "tpl" / "README.md").exists()


def test_side_axis_truss_needs_its_registration() -> None:
    side = [ax.RegistryEntry("p", "S1", 2, date(2026, 10, 10), ((date(2026, 10, 10), "axis_shoot"),), ("r",))]
    tr.check_against_axes([_entry("S1", 3, 1, "2026-10-12")], side)
    with pytest.raises(tr.TrussRegistryError, match="no side-shoot registry entry"):
        tr.check_against_axes([_entry("S2", 3, 1)], side)
    with pytest.raises(tr.TrussRegistryError, match="before its axis"):
        tr.check_against_axes([_entry("S1", 3, 1, "2026-10-09")], side)


# ---------------------------------------------------------------- derivation

def _snapshot(ranks_m: list[int], ranks_s: list[int] = ()) -> list[dict[str, str]]:
    rows = []
    plant = s.blank_mtg_row()
    plant.update(plant_instance_id="p", plant_id="p", capture_id="c", snapshot_capture_id="c", vertex_id="p",
                 scale="1", frame="plant_local_mm", evidence="synthetic_fixture", **{"class": "Plant"})
    rows.append(plant)
    for axis, vid in (("M", "p/A0"), ("S1", "p/S1")):
        a = dict(plant, vertex_id=vid, scale="2", axis=axis, **{"class": "Axis"})
        rows.append(a)
    serial = 0
    for axis, ranks in (("M", ranks_m), ("S1", ranks_s)):
        for r in ranks:
            serial += 1
            c = dict(plant, vertex_id=f"p/C{serial:04d}", scale="3", axis=axis,
                     complex_id="p/A0" if axis == "M" else "p/S1", **{"class": "CompoundLeaf"})
            s.set_value(c, "leaf_unfolded", "true", "user_stated")
            s.set_value(c, "rank", str(r), "user_stated")
            rows.append(c)
            leaf = dict(c, vertex_id=f"p/C{serial:04d}/T", scale="4", complex_id=c["vertex_id"], **{"class": "Leaflet"})
            leaf["rank"], leaf["rank__status"] = UNAVAILABLE, UNAVAILABLE
            leaf["leaf_unfolded"], leaf["leaf_unfolded__status"] = UNAVAILABLE, UNAVAILABLE
            rows.append(leaf)
    return rows


def _with_trusses(rows: list[dict[str, str]], now: list[tr.TrussEntry]) -> list[dict[str, str]]:
    rows += tr.truss_vertex_rows(rows[0], now, {"M": "p/A0", "S1": "p/S1"}, "user_stated")
    tr.apply_segments(rows, now)
    return rows


def _seg(rows, cls=None):
    return {r["vertex_id"]: r["segment_index"] for r in rows if cls is None or r["class"] == cls}


def test_segment_index_counts_trusses_below_and_axis_is_never_split() -> None:
    rows = _with_trusses(_snapshot([1, 2, 3, 4, 5, 6], [1, 2, 3]),
                         [_entry("M", 2, 1), _entry("M", 4, 2), _entry("S1", 3, 3)])
    seg = _seg(rows)
    assert [seg[f"p/C{k:04d}"] for k in range(1, 7)] == ["1", "1", "2", "2", "3", "3"]
    assert seg["p/A0"] == "3" and seg["p/S1"] == "2", "apical segment = 1 + trusses on that axis"
    assert [seg["p/F0001"], seg["p/F0002"], seg["p/F0003"]] == ["1", "2", "1"], "a truss closes its segment"
    assert seg["p/C0005/T"] == "3", "organs repeat their compound's index"
    assert {r["axis"] for r in rows if r["class"] in ("CompoundLeaf", "Truss")} == {"M", "S1"}, "no new axis"
    trusses = [r for r in rows if r["class"] == s.TRUSS_CLASS]
    assert all(r["rank"] == UNAVAILABLE and r["scale"] == "3" for r in trusses)
    s.check_mtg_rows(rows)


def test_no_registry_or_unplaced_truss_leaves_segments_unavailable() -> None:
    rows = _snapshot([1, 2, 3])
    tr.apply_segments(rows, None)
    assert set(_seg(rows).values()) == {UNAVAILABLE}, "absence of a registry is not 'no truss'"
    rows = _with_trusses(_snapshot([1, 2, 3]), [_entry("M", 1, 1), _entry("M", None, 2)])
    seg = _seg(rows)
    assert seg["p/C0001"] == UNAVAILABLE and seg["p/F0001"] == UNAVAILABLE
    assert seg["p/A0"] == "3", "the apical segment needs only the count"
    rows = _with_trusses(_snapshot([1, 2], [1]), [])
    assert _seg(rows, "CompoundLeaf") == {"p/C0001": "1", "p/C0002": "1", "p/C0003": "1"}, "registry, no truss -> 1"
    s.check_mtg_rows(rows)


def test_snapshot_uses_only_trusses_recorded_by_its_capture() -> None:
    clock = [ax.CaptureClock(c, datetime(2026, 10, d, 8, tzinfo=KST)) for c, d in (("c0", 11), ("c1", 12))]
    entries = [_entry("M", 2, 1, "2026-10-12")]
    assert tr.known_at(entries, "p", clock, "c0") == [] and tr.known_at(entries, "p", clock, "c1") == entries
    rows = tr.truss_table_rows("p", "p", clock, entries, {"M": "p/A0"}, "real_photo", "user_stated")
    assert [(r["capture_id"], r["emergence_interval_start"], r["emergence_interval_end"]) for r in rows] == [
        ("c1", "c0", "c1")]
    s.check_trusses(rows)


# ---------------------------------------------------------------- T2 validators

def _break(rows, vid, **over):
    return [dict(r, **over) if r["vertex_id"] == vid else r for r in rows]


@pytest.mark.parametrize("vid, over, match", [
    ("p/C0001", dict(segment_index="2"), "1 \\+ trusses below"),           # must start at 1
    ("p/C0004", dict(segment_index="1"), "1 \\+ trusses below"),           # leaf after a truss must increment
    ("p/C0002", dict(segment_index="0"), ">= 1"),
    ("p/F0001", dict(rank="3", rank__status="user_stated"), "no leaf rank"),
    ("p/F0001", dict(scale="4"), "scale-3"),
    ("p/A0", dict(segment_index="1"), "apical"),
    ("p/C0002/T", dict(segment_index="2"), "complex"),
    ("p/C0002", dict(segment_index__status=UNAVAILABLE), "disagree"),
])
def test_segment_validator_rejects(vid, over, match) -> None:
    rows = _with_trusses(_snapshot([1, 2, 3, 4]), [_entry("M", 2, 1)])
    s.check_mtg_rows(rows)
    with pytest.raises(s.P1SchemaError, match=match):
        s.check_mtg_rows(_break(rows, vid, **over))


def test_order_two_is_rejected_naming_the_reserved_spelling(tmp_path) -> None:
    with pytest.raises(s.P1SchemaError, match="S1.1"):
        s.check_axis_code("S1.1", "x")
    row = {c: UNAVAILABLE for c in s.AXES_COLUMNS}
    row.update(plant_instance_id="p", capture_id="c1", axis_id="S1", axis="S1", axis_vertex_id="p/S1", order="2",
               parent_axis_id="M", stage="axis_shoot", axis_state="axis_shoot", registration_ref="r",
               evidence="real_photo")
    with pytest.raises(s.P1SchemaError, match="S1.1"):
        s.check_axes([row])
    with pytest.raises(ax.RegistryError, match="S1.1"):
        path = tmp_path / "side.csv"
        path.write_text(",".join(ax.REGISTRY_COLUMNS) + "\np,S1.1,2,2026-10-10,axis_shoot,2026-10-10,\n",
                        encoding="utf-8")
        ax.read_registry(path)


def test_axes_segment_columns() -> None:
    row = {c: UNAVAILABLE for c in s.AXES_COLUMNS}
    row.update(plant_instance_id="p", capture_id="c1", axis_id="M", axis="M", axis_vertex_id="p/A0", order="0",
               parent_rank="0", parent_rank__status="derived", stage="main", axis_state="main",
               registration_ref="definition:main_axis", evidence="real_photo")
    s.check_axes([row])
    s.check_axes([dict(row, segment_index="2", segment_index__status="derived", truss_count="1")])
    with pytest.raises(s.P1SchemaError, match="truss_count"):
        s.check_axes([dict(row, segment_index="1", segment_index__status="derived", truss_count="1")])
    with pytest.raises(s.P1SchemaError, match="truss_count"):
        s.check_axes([dict(row, segment_index="1", segment_index__status="derived")])


def test_truss_table_rules() -> None:
    clock = [ax.CaptureClock("c0", datetime(2026, 10, 11, 8, tzinfo=KST))]
    row = tr.truss_table_rows("p", "p", clock, [_entry("M", 2, 1)], {"M": "p/A0"}, "real_photo", "user_stated")[0]
    s.check_trusses([row])
    with pytest.raises(s.P1SchemaError, match="registry record"):
        s.check_trusses([dict(row, registry_ref=UNAVAILABLE)])
    with pytest.raises(s.P1SchemaError, match="synthetic"):
        s.check_trusses([dict(row, parent_rank__status="synthetic_truth")])
    with pytest.raises(s.P1SchemaError, match="S1.1"):
        s.check_trusses([dict(row, axis_id="S1.1")])


@pytest.mark.skipif(not (OLD_SIDESHOOT_PACKAGE / "axes.csv").exists(), reason="revision-3 package absent")
def test_revision_three_tables_still_validate() -> None:
    from tomato3d.io.tables import read_table

    s.check_mtg_rows(read_table(OLD_SIDESHOOT_PACKAGE / "mtg_vertices.csv"))
    s.check_identity_rows(read_table(OLD_SIDESHOOT_PACKAGE / "identity_manifest.csv"))
    s.check_axes(read_table(OLD_SIDESHOOT_PACKAGE / "axes.csv"))


def test_truss_observations_are_never_tracked() -> None:
    row = {c: UNAVAILABLE for c in s.OBSERVATIONS_COLUMNS}
    row.update(obs_class="truss", review_state="accepted")
    assert ingest.trackable([row]) == []
    assert ingest.COCO_CLASS_MAP["truss"] == "truss"


# ---------------------------------------------------------------- T5 fixture package

@pytest.fixture(scope="module")
def truss_package(tmp_path_factory):
    if not (pk.PROJECT_ROOT / cn.SLOT_TABLE).exists():
        pytest.skip("slot table absent")
    side = dict(axis="S1", parent_serial=2, leaf_lengths_mm=[30.0, 26.0, 18.0], seed=11, stem_length_mm=14.0,
                stem_elevation_deg=50.0)
    request = dict(
        mode="fixture", source_plants=[dict(source_plant_id="fxs", scene_dir=f"{SCENES}/scene_0000")],
        donor_scene=f"{SCENES}/scene_0001", completion_pool_scenes=[f"{SCENES}/scene_0001"],
        sequences={"fxs": [dict(capture_id="c0", time_h=0, phase="am", side_shoots=[side]),
                           dict(capture_id="c1", time_h=24, phase="am", yaw_deg=20, side_shoots=[side])]},
        side_shoot_registry={"fxs": [dict(axis="S1", parent_serial=2, first_observed="2026-10-09",
                                          states=[["substem", "2026-10-10"]], note="t")]},
        truss_registry={"fxs": [dict(axis="M", above_serial=3, first_observed="2026-10-09", note="t"),
                                dict(axis="S1", above_serial=9, first_observed="2026-10-12", note="t")]},
        fixture_leaf_records=True,
        instances=[dict(plant_instance_id="fxs", slot_id="T3-row1-L", yaw_deg=0.0, variety="micro_tom")],
        decisions=None)
    return pk.build_fixture(tmp_path_factory.mktemp("truss") / "pkg", request)


def _table(pkg: Path, name: str) -> list[dict[str, str]]:
    return list(csv.DictReader((pkg / name).open(encoding="utf-8")))


def test_truss_package_validates_and_matches_truth(truss_package) -> None:
    assert pk.validate(truss_package) == []
    mtg, truth = _table(truss_package, "mtg_vertices.csv"), _table(truss_package, "truth/truth_mtg_vertices.csv")
    seg = {(r["capture_id"], r["vertex_id"]): r["segment_index"] for r in mtg}
    tseg = {(r["capture_id"], r["vertex_id"]): r["segment_index"] for r in truth}
    compounds = [k for k, r in zip(seg, mtg) if r["class"] == "CompoundLeaf"]
    assert compounds and all(seg[k] == tseg[k] for k in compounds), "snapshot segment == truth segment"
    assert max(int(v) for v in seg.values() if v != UNAVAILABLE) == 2, "M continues into segment 2"
    assert {r["axis"] for r in mtg if r["axis"] != UNAVAILABLE} == {"M", "S1"}, "no axis invented, none split"
    axes_rows = {(r["capture_id"], r["axis"]): r for r in _table(truss_package, "axes.csv")}
    assert (axes_rows[("c0", "S1")]["segment_index"], axes_rows[("c1", "S1")]["segment_index"]) == ("1", "2")
    assert axes_rows[("c0", "M")]["truss_count"] == "1"
    trusses = _table(truss_package, "trusses.csv")
    assert {(r["capture_id"], r["axis_id"]) for r in trusses} == {("c0", "M"), ("c1", "M"), ("c1", "S1")}
    s1 = next(r for r in trusses if r["axis_id"] == "S1")
    assert (s1["emergence_interval_start"], s1["emergence_interval_end"]) == ("c0", "c1")
    ident = _table(truss_package, "identity_manifest.csv")
    for r in ident:
        key = (r["capture_id"], r["organ_id"][:-2] if r["organ_id"].endswith("/T") else r["organ_id"])
        if key in seg:
            assert r["segment_index"] == seg[key]
    assert any(r["segment_index"] == "2" for r in ident)


def test_truss_package_p2_dry_read(truss_package) -> None:
    doc = pk.p2_dry_read(truss_package)
    assert doc["ok"], doc["issues"]
    assert doc["axes_and_trusses"]["truss_rows"] == 3 and doc["axes_and_trusses"]["max_segment_index"] == 2
