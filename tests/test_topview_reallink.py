"""Real-photo link, rim-plane mm, persisted masks, compound membership, own-pot attribution, confirmation file, and
the measured synthetic top camera (handoff/CLAUDE_CODE_CLI_PROMPT_TOPVIEW_REAL_LINK_2026-10-12.md). Toy inputs only:
no network, no SAM checkpoint (a fake predictor stands in), no HEIC decoder (hand-built HEIC boxes)."""

from __future__ import annotations

import csv
import hashlib
import json
import math
import struct
from pathlib import Path

import cv2
import numpy as np
import pytest
from PIL import Image

from tomato3d.synth import pairs
from tomato3d.topview import confirm_tool as ct
from tomato3d.topview import instances as inst
from tomato3d.topview import measure2d as m2
from tomato3d.topview import reallink as rl

SIZE = 400


# --------------------------------------------------------------------------- helpers
def _box(typ: bytes, body: bytes) -> bytes:
    return struct.pack(">I4s", 8 + len(body), typ) + body


def _fake_heic(path: Path, w: int, h: int, irot: int | None = None) -> Path:
    props = _box(b"ispe", b"\0\0\0\0" + struct.pack(">II", w, h))
    if irot is not None:
        props += _box(b"irot", bytes([irot]))
    path.write_bytes(_box(b"ftyp", b"heic\0\0\0\0") + _box(b"meta", b"\0\0\0\0" + _box(b"iprp", _box(b"ipco", props))))
    return path


def _sha(p: Path) -> str:
    return hashlib.sha256(Path(p).read_bytes()).hexdigest()


def _capture(tmp: Path, *, heic_wh=(SIZE, SIZE), jpg_wh=(SIZE, SIZE), irot=None, exif_orient=None):
    (tmp / "data/raw/dwt_101").mkdir(parents=True, exist_ok=True)
    raw = _fake_heic(tmp / "data/raw/dwt_101/top.heic", *heic_wh, irot=irot)
    imgs = tmp / "imgs"
    imgs.mkdir(exist_ok=True)
    im = Image.new("RGB", jpg_wh, (240, 240, 240))
    kw = {}
    if exif_orient:
        ex = Image.Exif()
        ex[0x0112] = exif_orient
        kw["exif"] = ex
    im.save(imgs / "dwt_101_top.jpg", quality=95, **kw)
    cap = dict(capture_id="dwt_101_s/top", source_plant_id="dwt_101", image_path="data/raw/dwt_101/top.heic",
               image_sha256=_sha(raw), view="top", evidence="real_photo")
    return cap, imgs


# --------------------------------------------------------------------------- X1 link / grid refusals
def test_link_accepts_identical_grid(tmp_path):
    cap, imgs = _capture(tmp_path)
    link = rl.link_top_capture(cap, tmp_path, Path("imgs"))
    assert link["plant_id"] == "dwt_101" and link["image_sha256"] == cap["image_sha256"]
    assert link["image_file_sha256"] == _sha(imgs / "dwt_101_top.jpg") and link["size_px"] == [SIZE, SIZE]


@pytest.mark.parametrize("kw, match", [
    (dict(jpg_wh=(SIZE, SIZE - 1)), "different pixel grids"),
    (dict(irot=1), "rotation present"),
    (dict(exif_orient=6), "rotation present"),
])
def test_link_refuses_when_the_grid_cannot_be_shown_identical(tmp_path, kw, match):
    cap, _ = _capture(tmp_path, **kw)
    with pytest.raises(rl.GridRefusal, match=match):
        rl.link_top_capture(cap, tmp_path, Path("imgs"))


def test_link_refuses_a_changed_raw_photo_and_an_unrelated_download(tmp_path):
    cap, imgs = _capture(tmp_path)
    with pytest.raises(rl.GridRefusal, match="sha256"):
        rl.link_top_capture(dict(cap, image_sha256="0" * 64), tmp_path, Path("imgs"))
    other = tmp_path / "IMG_8419.jpg"                       # e.g. a Roboflow download: same size, other bytes
    Image.new("RGB", (SIZE, SIZE), (241, 240, 240)).save(other, quality=90)
    err = rl.refuse_unlinked(other, [cap], tmp_path, Path("imgs"))
    assert "no plant_id and no mm" in str(err)


# --------------------------------------------------------------------------- X2 rim mm, pose
EDGE_MM, LO, HI = 60.0, 100.0, 300.0                       # rim square 200 px -> 0.3 mm/px


def _records(root: Path, sha: str, plant: str = "dwt_101", lo: float = LO, hi: float = HI) -> None:
    pots = root / "records/pots"
    pots.mkdir(parents=True, exist_ok=True)
    spec = pots / "pot_spec.csv"
    if not spec.exists():
        spec.write_text("pot_type,shape,plant_ids,pot_rim_outer_edge_mm,pot_rim_inner_diameter_mm,pot_depth_mm,"
                        "source_kind,method,measured_date,note\ncell,square,dwt_1*,60,,70,measured,caliper,2026-10-12,\n",
                        encoding="utf-8")
    pts = pots / "rim_points.csv"
    new = not pts.exists()
    with pts.open("a", encoding="utf-8", newline="") as f:
        w = csv.writer(f, lineterminator="\n")
        if new:
            w.writerow(("plant_id", "image_sha256", "kind", "side", "x_px", "y_px", "click_uncertainty_px",
                        "ruler_reading_mm", "annotator", "note"))
        mid = (lo + hi) / 2
        for side, xy in ((1, [(lo + 20, lo), (mid, lo), (hi - 20, lo)]), (2, [(hi, lo + 20), (hi, mid), (hi, hi - 20)]),
                         (3, [(hi - 20, hi), (mid, hi), (lo + 20, hi)]), (4, [(lo, hi - 20), (lo, mid), (lo, lo + 20)])):
            for x, y in xy:
                w.writerow((plant, sha, "rim_edge", side, x, y, 1, "", "t", ""))


class _FakePredictor:
    """Box prompt -> filled ellipse inscribed in the box (a stand-in for SAM)."""

    def set_image(self, rgb):
        self.shape = rgb.shape[:2]

    def predict(self, box, multimask_output):
        m = np.zeros(self.shape, np.uint8)
        x0, y0, x1, y1 = box
        cv2.ellipse(m, (int((x0 + x1) / 2), int((y0 + y1) / 2)), (int((x1 - x0) / 2) - 1, int((y1 - y0) / 2) - 1),
                    0, 0, 360, 1, -1)
        return np.stack([m.astype(bool)] * 3), np.array([0.5, 0.9, 0.7]), None


class _FakeSeg:
    predictor = _FakePredictor()
    config = dict(model_name="fake", checkpoint_sha256="0" * 64)


def _pred(items):
    return dict(image=dict(width=SIZE, height=SIZE), predictions=[
        dict(x=(b[0] + b[2]) / 2, y=(b[1] + b[3]) / 2, width=b[2] - b[0], height=b[3] - b[1], confidence=0.9,
             **{"class": c}) for c, b in items])


#: compound C01 reaches into the rim square; C02 lies wholly outside it (bottom-left), like IMG_8419's neighbour.
DETS = [("compond_leaf", (150, 150, 290, 260)), ("compond_leaf", (5, 330, 90, 395)),
        ("leaf", (160, 160, 210, 200)), ("terminal_leaf", (230, 200, 285, 255)), ("leaf", (10, 340, 45, 390)),
        ("leaf", (305, 20, 350, 60))]


def _run(tmp: Path, linked: bool) -> tuple[Path, dict]:
    img = tmp / "photo.jpg"
    if not img.exists():
        Image.new("RGB", (SIZE, SIZE), (200, 200, 200)).save(img, quality=95)
    out = tmp / ("linked" if linked else "unlinked") / "dwt_101"
    out.mkdir(parents=True)
    (out / "detections.json").write_text(json.dumps(_pred(DETS)), encoding="utf-8")
    raw_sha = "ab" * 32
    data = tmp / "data"
    if not (data / "records/pots/rim_points.csv").exists():
        _records(data, raw_sha)
    link = dict(plant_id="dwt_101", capture_id="dwt_101_s/top", image_sha256=raw_sha,
                image_file_sha256=_sha(img), size_px=[SIZE, SIZE]) if linked else None
    r = m2.measure_photo(img, out, seg=_FakeSeg(), link=link, data_root=data)
    return out, r


def test_remote_masks_reproduce_the_local_run(tmp_path):
    """Masks made remotely (npz in the kernel's layout) give the same rows as running the predictor here."""
    out, local = _run(tmp_path, linked=True)
    cfg = m2.load_config()
    boxes = m2.photo_boxes(_pred(DETS), cfg, (SIZE, SIZE))
    fp = _FakePredictor()
    fp.set_image(np.zeros((SIZE, SIZE, 3), np.uint8))
    packed, best = [], []
    for b in boxes:
        m, s, _ = fp.predict(np.asarray(b["box"], np.float32), True)
        packed.append(np.packbits(m[int(np.argmax(s))].ravel()))
        best.append(float(s.max()))
    np.savez_compressed(tmp_path / "dwt_101.npz", box_keys=np.array([m2.box_key(b["box"]) for b in boxes]),
                        masks_packed=np.stack(packed), best_score=np.array(best), image_hw=np.array([SIZE, SIZE]))
    seg = m2.PrecomputedSeg(tmp_path / "dwt_101.npz", dict(model_name="fake", checkpoint_sha256="0" * 64,
                                                            device="cuda (test)", torch_version="x"))
    out2 = tmp_path / "remote" / "dwt_101"
    out2.mkdir(parents=True)
    (out2 / "detections.json").write_text(json.dumps(_pred(DETS)), encoding="utf-8")
    link = dict(plant_id="dwt_101", capture_id="dwt_101_s/top", image_sha256="ab" * 32,
                image_file_sha256=_sha(tmp_path / "photo.jpg"), size_px=[SIZE, SIZE])
    remote = m2.measure_photo(tmp_path / "photo.jpg", out2, seg=seg, link=link, data_root=tmp_path / "data")
    keys = ("area_px", "length_mm", "compound_id", "attribution")
    assert [[r[k] for k in keys] for r in remote["rows"]] == [[r[k] for k in keys] for r in local["rows"]]
    assert remote["header"]["segmenter"]["device"] == "cuda (test)"
    bad = m2.PrecomputedSeg(tmp_path / "dwt_101.npz", dict(model_name="f", checkpoint_sha256="0", device="d",
                                                            torch_version="x"))
    bad.predictor.masks.pop(m2.box_key(boxes[0]["box"]))
    with pytest.raises(SystemExit, match="no precomputed mask"):
        m2.sam_masks(bad, np.zeros((SIZE, SIZE, 3), np.uint8), boxes)


def test_no_mm_without_plant_id_and_original_hash(tmp_path):
    _, r = _run(tmp_path, linked=False)
    assert all(x["area_mm2"] == "unavailable" and x["plant_id"] == "unavailable" for x in r["rows"])
    assert "not linked" in r["header"]["scale"]["reason"]
    for args in ((None, "dwt_101"), ("ab" * 32, None)):
        assert m2.pot_scale(*args, tmp_path).status == "unavailable"


def test_linked_photo_gets_rim_mm_with_sd_and_overestimate_note(tmp_path):
    out, r = _run(tmp_path, linked=True)
    assert r["header"]["scale"]["status"] == "solved"
    assert r["header"]["scale"]["mm_per_px_centre"] == pytest.approx(0.3, rel=1e-3)
    assert "overestimates" in r["header"]["scale"]["plane_note"]
    leaf = r["rows"][0]
    assert leaf["plant_id"] == "dwt_101" and leaf["image_sha256"] == "ab" * 32
    assert leaf["plane_bias"] == "overestimates_above_rim" and leaf["scale_plane"] == "rim_plane"
    assert leaf["length_mm"] == pytest.approx(leaf["length_px"] * 0.3, rel=0.02)
    assert leaf["length_mm_sd"] > 0 and leaf["area_mm2_sd"] == pytest.approx(
        2 * leaf["area_mm2"] * leaf["length_mm_sd"] / leaf["length_mm"], rel=0.02)
    assert all(x["review_status"] == "proposed" for x in r["rows"] + r["compounds"])


def test_pose_from_rim_recovers_a_known_camera():
    f, d, tilt = 3000.0, 250.0, math.radians(12.0)
    R = np.array([[1, 0, 0], [0, math.cos(tilt), -math.sin(tilt)], [0, math.sin(tilt), math.cos(tilt)]])
    t = np.array([5.0, -3.0, d])
    K = np.array([[f, 0, 1500], [0, f, 1500], [0, 0, 1.0]])
    g = K @ np.c_[R[:, 0], R[:, 1], t]                       # rim-plane mm -> image px
    p = rl.pose_from_rim(np.linalg.inv(g), f, (1500, 1500))
    assert p["pot_centre_depth_mm"] == pytest.approx(d, rel=1e-6)
    assert p["tilt_from_vertical_deg"] == pytest.approx(12.0, abs=1e-6)
    assert p["axis_ratio_self_check"] == pytest.approx(1.0, abs=1e-9)
    assert rl.bias_factor(230.0, 1.0, 20.0) == pytest.approx(230 / 210)  # overestimate: factor > 1
    b = rl.focal_px_bases(52, 4032, 3024)
    assert b["frame_width"] == pytest.approx(5824.0) and b["frame_diagonal"] == pytest.approx(6057.3, abs=0.1)


# --------------------------------------------------------------------------- X4 masks + membership
def test_mask_persistence_round_trip_and_tamper(tmp_path):
    rng = np.random.default_rng(0)
    masks = {"p#C01": rng.random((50, 60)) > 0.7, "p#L001": np.zeros((50, 60), bool)}
    masks["p#L001"][10:20, 30:41] = True
    entries = inst.save_masks(masks, tmp_path / "masks", rel_to=tmp_path)
    for e in entries:
        assert np.array_equal(inst.load_mask(e, tmp_path), masks[e["instance_id"]])
    empty = inst.save_masks({"p#L002": np.zeros((5, 5), bool)}, tmp_path / "masks", rel_to=tmp_path)[0]
    assert empty["png"] is None and not inst.load_mask(empty, tmp_path).any()
    (tmp_path / entries[1]["png"]).write_bytes((tmp_path / entries[0]["png"]).read_bytes())
    with pytest.raises(ValueError, match="sha256"):
        inst.load_mask(entries[1], tmp_path)


def test_persisted_run_masks_reload(tmp_path):
    out, r = _run(tmp_path, linked=True)
    man = json.loads((out / "masks_manifest.json").read_text(encoding="utf-8"))
    assert len(man["masks"]) == len(r["rows"]) + len(r["compounds"]) and man["review_status"] == "proposed"
    assert all(inst.load_mask(e, out).sum() == e["area_px"] for e in man["masks"])


def test_compound_leaflet_membership():
    def m(box):
        a = np.zeros((100, 100), bool)
        a[box[1]:box[3], box[0]:box[2]] = True
        return a
    comps = [dict(id="C1", box=[0, 0, 60, 60], mask=m([0, 0, 60, 60])),
             dict(id="C2", box=[40, 0, 100, 60], mask=m([60, 0, 100, 60]))]
    leaves = [dict(id="L1", box=[5, 5, 20, 20], mask=m([5, 5, 20, 20])),        # only C1
              dict(id="L2", box=[42, 5, 58, 20], mask=m([42, 5, 58, 20])),      # both boxes; mask in C1 only
              dict(id="L3", box=[45, 30, 55, 40], mask=None),                   # both boxes; no mask -> ambiguous
              dict(id="L4", box=[70, 70, 90, 90], mask=m([70, 70, 90, 90]))]    # none
    res = {x["leaflet_id"]: x for x in inst.membership(leaves, comps, 0.5)}
    assert (res["L1"]["status"], res["L1"]["compound_id"]) == ("member", "C1")
    assert (res["L2"]["status"], res["L2"]["compound_id"], res["L2"]["basis"]) == (
        "member", "C1", "box_majority_then_mask_majority")
    assert res["L3"]["status"] == "ambiguous" and sorted(res["L3"]["candidates"]) == ["C1", "C2"]
    assert res["L4"]["status"] == "unassigned"
    conflicts = inst.terminal_conflicts(list(res.values()), dict(L1="terminal_leaf", L2="terminal_leaf"))
    assert conflicts == {"C1": ["L1", "L2"]}


# --------------------------------------------------------------------------- X3 attribution
def test_attribution_keeps_ambiguous_and_needs_evidence_for_outside(tmp_path):
    _, r = _run(tmp_path, linked=True)
    a = {x["leaflet_id"].split("#")[1]: x["attribution"] for x in r["rows"]}
    c = {x["compound_id"].split("#")[1]: x["attribution"] for x in r["compounds"]}
    assert c == {"C01": "inside", "C02": "ambiguous"}               # no neighbour record -> never 'outside'
    assert a["L001"] == "inside" and a["L002"] == "inside"          # centroid in rim / member of an inside compound
    assert a["L003"] == "ambiguous"                                 # the bottom-left neighbour-like leaflet
    assert a["L004"] == "ambiguous"                                 # outside the rim, no compound
    poly = inst.rim_polygon_px(np.array([[0.3, 0, -60], [0, 0.3, -60], [0, 0, 1.0]]), 60.0)
    leaves = [dict(id="L", box=[0, 0, 1, 1], centroid=(30.0, 360.0))]
    res = inst.attribute([], leaves, [], poly, {"dwt_102": np.array([[0, 330], [100, 330], [100, 400], [0, 400]],
                                                                     float)})
    assert res["L"]["attribution"] == "outside" and "dwt_102" in res["L"]["reason"]
    assert inst.attribute([], leaves, [], None, {})["L"]["attribution"] == "ambiguous"


# --------------------------------------------------------------------------- X4 confirmation file
def test_confirmations_stay_proposed_until_decided(tmp_path):
    out, _ = _run(tmp_path, linked=True)
    run = out.parent
    rows = ct.proposals(run)
    assert rows and all(r["decision"] == "proposed" for r in rows)
    tpl = tmp_path / "c.csv"
    ct.write_csv(tpl, rows)
    assert ct.check(run, tpl)["counts"] == {"confirmed": 0, "rejected": 0, "proposed": len(rows)}
    leaf = next(r for r in rows if r["kind"] == "leaflet" and r["proposed_attribution"] == "ambiguous")
    bad = [dict(r) for r in rows]
    next(r for r in bad if r["instance_id"] == leaf["instance_id"]).update(decision="accept", attribution="outside",
                                                                          annotator="t")
    ct.write_csv(tpl, bad)
    with pytest.raises(ct.ConfirmError, match="use 'fix'"):
        ct.check(run, tpl)
    good = [dict(r) for r in rows]
    next(r for r in good if r["instance_id"] == leaf["instance_id"]).update(decision="fix", attribution="outside",
                                                                           annotator="t")
    ct.write_csv(tpl, good)
    res = ct.check(run, tpl)
    assert res["counts"]["confirmed"] == 1 and res["instances"][leaf["instance_id"]]["attribution"] == "outside"


def test_confirm_tool_build_never_under_records(tmp_path):
    out, _ = _run(tmp_path, linked=True)
    with pytest.raises(ct.ConfirmError, match="data/records"):
        ct.build(out.parent, tmp_path / "data/records/x", project_root=tmp_path)
    page = ct.build(out.parent, tmp_path / "confirm", project_root=tmp_path)
    assert page.exists() and (page.parent / "confirmations_template.csv").exists()
    assert "__DATA__" not in page.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- X5 measured top camera
def test_top_cameras_draw_from_measured_poses(tmp_path):
    files = []
    for i, (d, t) in enumerate(((193.0, 1.0), (278.0, 31.8))):
        f = tmp_path / f"dwt_10{i}" / "pose.json"
        f.parent.mkdir()
        f.write_text(json.dumps(dict(status="approximate", bases=dict(frame_width=dict(
            pot_centre_distance_mm=d, tilt_from_vertical_deg=t, axis_ratio_self_check=1.0)))), encoding="utf-8")
        files.append(f)
    block = pairs.measured_top_block(files, "frame_width", n_views=4)
    assert block["source_kind"] == "measured_approximate" and block["distance_mm_range"] == [193.0, 278.0]
    cams = pairs._top_cameras(7, block)
    assert len(cams) == 4
    for c in cams:
        assert (c["distance_mm"], round(90.0 - c["elevation_deg"], 6)) in {(193.0, 1.0), (278.0, 31.8)}


# --------------------------------------------------------------------------- X0 wording
def test_no_underestimate_wording_in_topview():
    root = Path(m2.__file__).parent
    for f in list(root.glob("*.py")) + list(root.glob("*.json")) + list(root.glob("*.html")):
        assert "underestimat" not in f.read_text(encoding="utf-8").lower(), f.name
