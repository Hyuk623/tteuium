"""Label class schema + JSON label files (handoff/CLAUDE_CODE_CLI_PROMPT_LABEL_SCHEMA_JSON_2026-10-12.md).

Class ids/names exact (user spelling ``compond_leaf`` kept), one class per instance, typed attributes,
leaflet classes from the generator tag only, the truss gap stated rather than faked, and the side-view
verifier catching a tampered box. Toy masks only; the two real files are checked when present.
"""

from __future__ import annotations

import copy
import hashlib
import json
from pathlib import Path

import numpy as np
import pytest

from tomato3d.synth import labels_json as lj

PROJECT_ROOT = Path(__file__).resolve().parents[1]
TOP_FILE = PROJECT_ROOT / "build/labels_json_20261012/top_labels_v1.json"
SIDE_FILE = PROJECT_ROOT / "build/sideprop_20261009_01/labels_json/side_labels_compound_v1.json"
MIN_PX = 4


# --------------------------------------------------------------------------- class set
def test_class_set_is_exactly_the_user_decision():
    assert [(i, n) for i, n, _ in lj.CLASS_SET] == [
        (0, "compond_leaf"), (1, "leaf"), (2, "leaf2"), (3, "shoot"), (4, "terminal_leaf"), (5, "truss")]
    assert lj.CLASS_ID["compond_leaf"] == 0 and "compound_leaf" not in lj.CLASS_ID
    assert [c["name"] for c in lj.class_set_json()] == [n for _, n, _ in lj.CLASS_SET]


def test_leaflet_class_comes_from_the_generator_tag():
    assert lj.leaflet_class(dict(kind="terminal", tag="T")) == "terminal_leaf"
    assert lj.leaflet_class(dict(kind="pair", tag="P1L")) == "leaf"
    assert lj.leaflet_class(dict(kind="intercalary", tag="I1")) == "leaf2"
    assert lj.leaflet_class(dict(kind="secondary", tag="S1")) == "leaf2"
    with pytest.raises(lj.LabelSchemaError):          # terminal leaflet tagged as a lateral: defect, not a choice
        lj.leaflet_class(dict(kind="terminal", tag="P1L"))
    with pytest.raises(lj.LabelSchemaError):
        lj.leaflet_class(dict(kind="bud", tag="B"))


# --------------------------------------------------------------------------- toy top view
def _toy():
    """One compound L01 (T, P1L, I1 + rachis) and the apex, in a 40x40 image."""
    index = {"1": dict(leaflet_id="s/L01/T", compound_id="L01", tag="T", kind="terminal"),
             "2": dict(leaflet_id="s/L01/P1L", compound_id="L01", tag="P1L", kind="pair"),
             "3": dict(leaflet_id="s/L01/I1", compound_id="L01", tag="I1", kind="intercalary")}
    graph = dict(compounds=[dict(compound_id="L01", rank_from_bottom=2)])
    parts = [dict(name="s/L01/T", organ="leaflet"), dict(name="s/L01/P1L", organ="leaflet"),
             dict(name="s/L01/I1", organ="leaflet"), dict(name="rachis_L01", organ="rachis"),
             dict(name="petiolule_s/L01/P1L", organ="petiolule"), dict(name="apex", organ="apex"),
             dict(name="stem", organ="stem"), dict(name="pot", organ="pot")]
    planned, plan = lj.instance_plan(parts, index)
    ids = {p["name"]: p["instance"] for p in planned}
    vis = np.zeros((40, 40), np.uint16)
    vis[2:10, 2:12] = ids["s/L01/T"]
    vis[12:20, 2:10] = ids["s/L01/P1L"]
    vis[22:24, 2:3] = ids["s/L01/I1"]            # 2 px visible < MIN_PX -> excluded, listed
    vis[2:30, 20:22] = ids["rachis_L01"]         # rachis extends the compound box to y = 30, x = 22
    vis[35:38, 35:38] = ids["apex"]
    amodal = {i: vis == i for i in set(np.unique(vis)) - {0}}
    amodal[ids["s/L01/T"]] = amodal[ids["s/L01/T"]].copy()
    amodal[ids["s/L01/T"]][10:12, 2:12] = True   # hidden part of the terminal leaflet
    stored_vis = np.where(np.isin(vis, [1, 2, 3]), vis, 0)
    stored_amodal = {"L01_T": amodal[1], "L01_P1L": amodal[2], "L01_I1": amodal[3]}
    return dict(index=index, graph=graph, plan=plan, ids=ids, raster_visible=vis, raster_amodal=amodal,
                stored_visible=stored_vis, stored_amodal=stored_amodal)


def test_instance_plan_keeps_leaflet_ids_and_groups_parts_by_compound():
    t = _toy()
    assert [t["ids"][n] for n in ("s/L01/T", "s/L01/P1L", "s/L01/I1")] == [1, 2, 3]
    assert sorted(t["plan"]["compounds"]["L01"]) == sorted([1, 2, 3, t["ids"]["rachis_L01"],
                                                            t["ids"]["petiolule_s/L01/P1L"]])
    assert t["plan"]["apex"] == [t["ids"]["apex"]]
    assert t["ids"]["stem"] == 0 and t["ids"]["pot"] == 0
    with pytest.raises(lj.LabelSchemaError):
        lj.instance_plan([dict(name="s/L09/T", organ="leaflet")], t["index"])


def test_view_annotations_one_class_per_instance_and_typed_attributes():
    t = _toy()
    va = lj.view_annotations(scene_id="s", graph=t["graph"], index=t["index"], stored_visible=t["stored_visible"],
                             stored_amodal=t["stored_amodal"], raster_visible=t["raster_visible"],
                             raster_amodal=t["raster_amodal"], plan=t["plan"], min_visible_px=MIN_PX)
    by = {a["object_id"]: a for a in va["annotations"]}
    assert by["s/L01/T"]["class"] == "terminal_leaf" and by["s/L01/T"]["tag"] == "T"
    assert by["s/L01/P1L"]["class"] == "leaf"
    assert by["s/L01"]["class"] == "compond_leaf" and by["s/L01"]["tag"] is None
    assert by["s/L01"]["bbox_xywh"] == [2.0, 2.0, 20.0, 28.0]          # rachis is part of the compound
    assert by["s/M/shoot"]["class"] == "shoot" and by["s/M/shoot"]["rank"] is None
    assert by["s/L01/T"]["vis_frac"] == round(80 / 100, 4)
    assert all(a["axis"] == "M" for a in va["annotations"])
    assert by["s/L01/P1L"]["rank"] == 2
    assert va["excluded_occluded"] == [{"object_id": "s/L01/I1", "class": "leaf2", "visible_px": 2}]
    assert len(by) == len(va["annotations"])                          # no object twice
    agree = lj.leaflet_layer_agreement(t["stored_visible"], t["raster_visible"], t["plan"])
    assert agree["differing_px"] == 0


def _doc(view_type="top"):
    t = _toy()
    va = lj.view_annotations(scene_id="s", graph=t["graph"], index=t["index"], stored_visible=t["stored_visible"],
                             stored_amodal=t["stored_amodal"], raster_visible=t["raster_visible"],
                             raster_amodal=t["raster_amodal"], plan=t["plan"], min_visible_px=MIN_PX)
    anns = [dict(id=k + 1, image_id=1, **a) for k, a in enumerate(va["annotations"])]
    return dict(schema=lj.SCHEMA, view_type=view_type, class_set=lj.class_set_json(),
                classes_present=sorted({a["class"] for a in anns}),
                classes_absent=[dict(name="truss", id=5, reason=lj.TRUSS_ABSENT_REASON)],
                evidence="synthetic ground truth", counts_as_real_annotation=False,
                images=[dict(id=1, file_name="x.png", width=40, height=40)], annotations=anns)


def test_validate_accepts_a_good_file_and_reports_no_gaps():
    assert lj.validate_labels(_doc()) == []


@pytest.mark.parametrize("mutate, match", [
    (lambda d: d["annotations"][0].update(class_id=1), "class_id"),
    (lambda d: d["annotations"][0].update({"class": "compound_leaf"}), "not in the class set"),
    (lambda d: d["annotations"].append(dict(d["annotations"][0], id=99, **{"class": "leaf", "class_id": 1})),
     "labelled twice"),
    (lambda d: d["annotations"][0].update(rank="2"), "rank"),
    (lambda d: d["annotations"][0].update(visible_px=True), "bool"),
    (lambda d: d["annotations"][0].update(vis_frac=1.5), "vis_frac"),
    (lambda d: d["annotations"][0].update(image_id=7), "image_id"),
    (lambda d: d["annotations"][0].pop("axis"), "missing attribute"),
    (lambda d: d["class_set"][0].update(name="compound_leaf"), "class_set"),
    (lambda d: d.update(class_set=d["class_set"][::-1]), "class_set"),
    (lambda d: d.update(counts_as_real_annotation=True), "counts_as_real"),
    (lambda d: d.update(classes_absent=[dict(name="leaf", id=1, reason="x")]), "listed as absent"),
    (lambda d: d.update(classes_absent=[dict(name="truss", id=5, reason="")]), "no reason"),
    (lambda d: d.update(view_type="ring"), "view_type"),
])
def test_validate_rejects(mutate, match):
    d = copy.deepcopy(_doc())
    mutate(d)
    with pytest.raises(lj.LabelSchemaError, match=match):
        lj.validate_labels(d)


def test_older_header_is_a_gap_not_an_error():
    d = _doc()
    del d["classes_absent"], d["counts_as_real_annotation"]
    gaps = lj.validate_labels(d)
    assert len(gaps) == 2


# --------------------------------------------------------------------------- side verifier
def _side_triple(tmp_path: Path):
    cats = [dict(id=1, name="cl_toward"), dict(id=2, name="cl_right"), dict(id=3, name="cl_away"),
            dict(id=4, name="cl_left"), dict(id=5, name="main_stem"), dict(id=6, name="growth_shoot"),
            dict(id=7, name="compound_unclear")]
    images = [dict(id=1, file_name="a.png", width=512, height=512, scene_id="scene_0000", protocol_azimuth_deg=90,
                   camera_azimuth_deg=0.0)]
    coco_anns = [
        dict(id=1, image_id=1, category_id=2, bbox=[1.0, 2.0, 3.0, 4.0], compound_id="L01", delta_deg=100.0,
             quadrant_gt=1, excluded_boundary=False, visible_px=50, vis_frac=0.5),   # cl_right @90 -> q1
        dict(id=2, image_id=1, category_id=7, bbox=[5.0, 6.0, 7.0, 8.0], compound_id="L02", delta_deg=44.0,
             quadrant_gt=2, excluded_boundary=True, visible_px=60, vis_frac=0.9),
        dict(id=3, image_id=1, category_id=5, bbox=[0.0, 0.0, 2.0, 9.0]),
    ]
    coco = dict(categories=cats, images=images, annotations=coco_anns)
    cp = tmp_path / "coco.json"
    cp.write_text(json.dumps(coco), encoding="utf-8")
    side_anns = [
        dict(id=1, image_id=1, **{"class": "compond_leaf"}, class_id=0, bbox_xywh=[1.0, 2.0, 3.0, 4.0],
             compound_id="L01", direction="cl_right", direction_status="clear", quadrant_gt=1, delta_deg=100.0,
             boundary_excluded=False, vis_frac=0.5, visible_px=50),
        dict(id=2, image_id=1, **{"class": "compond_leaf"}, class_id=0, bbox_xywh=[5.0, 6.0, 7.0, 8.0],
             compound_id="L02", direction=None, direction_status="unclear_boundary_band", quadrant_gt=2,
             delta_deg=44.0, boundary_excluded=True, vis_frac=0.9, visible_px=60),
    ]
    side = dict(schema=lj.SCHEMA, view_type="side", class_set=lj.class_set_json(), classes_present=["compond_leaf"],
                evidence="synthetic ground truth (generator)", images=images, annotations=side_anns,
                dropped_from_source={"main_stem": 1},
                source_sha256=hashlib.sha256(cp.read_bytes()).hexdigest())
    summ = dict(views=1, boxed_compounds=2, scenes_done=1, excluded_boundary_among_boxed=1,
                direction_class_counts={"cl_right": 1},
                quadrant_check=dict(checked=2, mismatches=0))   # all-pairs population may be larger
    sp, mp = tmp_path / "side.json", tmp_path / "summary.json"
    sp.write_text(json.dumps(side), encoding="utf-8")
    mp.write_text(json.dumps(summ), encoding="utf-8")
    return sp, cp, mp


def test_verify_side_passes_and_catches_a_moved_box(tmp_path):
    sp, cp, mp = _side_triple(tmp_path)
    r = lj.verify_side(sp, cp, mp)
    assert r["result"] == "pass", r["problems"]
    assert r["checks"]["quadrant"]["checked"] == 1
    side = json.loads(sp.read_text(encoding="utf-8"))
    side["annotations"][0]["bbox_xywh"] = [1.0, 2.0, 3.0, 5.0]
    sp.write_text(json.dumps(side), encoding="utf-8")
    r = lj.verify_side(sp, cp, mp)
    assert r["result"] == "mismatch" and r["checks"]["annotation_identity"]["bbox_mismatch"] == 1


def test_verify_side_catches_a_wrong_quadrant(tmp_path):
    sp, cp, mp = _side_triple(tmp_path)
    side = json.loads(sp.read_text(encoding="utf-8"))
    coco = json.loads(cp.read_text(encoding="utf-8"))
    side["annotations"][0]["quadrant_gt"] = coco["annotations"][0]["quadrant_gt"] = 3
    cp.write_text(json.dumps(coco), encoding="utf-8")
    side["source_sha256"] = hashlib.sha256(cp.read_bytes()).hexdigest()
    sp.write_text(json.dumps(side), encoding="utf-8")
    r = lj.verify_side(sp, cp, mp)
    assert r["result"] == "mismatch" and r["checks"]["quadrant"]["mismatches"] == 1


# --------------------------------------------------------------------------- the real files, when present
@pytest.mark.skipif(not TOP_FILE.exists(), reason="top-view label file not generated")
def test_real_top_file():
    doc = lj.load_label_file(TOP_FILE)
    assert doc["_gaps"] == [] and doc["view_type"] == "top"
    assert [a["name"] for a in doc["classes_absent"]] == ["truss"]
    assert doc["class_counts"]["truss"] == 0
    assert doc["occlusion"]["min_vis_frac_applied"] is False and "min_vis_frac" in doc["occlusion"]
    assert doc["mask_reconstruction"]["differing_px"] == 0
    assert all(a["tag"] in ("I1", "S1") or a["tag"].startswith("I") for a in doc["annotations"]
               if a["class"] == "leaf2")
    assert not any(a["class"] == "leaf" and a["tag"] == "T" for a in doc["annotations"])


@pytest.mark.skipif(not SIDE_FILE.exists(), reason="side-view label file not present")
def test_real_side_file_loads_with_its_known_header_gaps():
    doc = lj.load_label_file(SIDE_FILE)
    assert doc["view_type"] == "side" and doc["classes_present"] == ["compond_leaf"]
    assert len(doc["_gaps"]) == 2
