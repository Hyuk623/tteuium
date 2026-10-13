"""One detector label class set + JSON label files for the synthetic sets (2026-10-12).

Spec: ``handoff/CLAUDE_CODE_CLI_PROMPT_LABEL_SCHEMA_JSON_2026-10-12.md``; human-facing summary:
``handoff/LABEL_CLASS_SCHEMA_2026-10-12.md``.

The class set is the user's decision of 2026-10-12 and is normative, spelling included
(``compond_leaf``). Everything else about an instance is an ATTRIBUTE, never an extra class:
``axis`` (``M``/``S1``...), ``rank``, ``compound_id``, leaflet ``tag`` (``T``/``P1L``/``I1``/``S1``),
``direction`` (side views only) and ``vis_frac``.

Three entry points:

* :func:`export_top` - top-view JSON from an existing Stage-1 run (no re-render). Leaflet instances
  come from the stored ``visible_mask.png`` + ``amodal/`` layers and the generator's own tag (never a
  geometry heuristic). Compound and shoot instances need masks the run never stored (a compound is
  its leaflets + rachis + petiolules, the shoot is the ``apex`` part), so the view's MASK layers are
  rasterised once more from ``render_job/parts.npz`` with the run's own camera geometry - the same
  rasteriser that wrote the stored layers. RGB is never touched. The stored leaflet layer is
  recomputed in the same pass and compared pixel for pixel; the agreement goes into the header.
* :func:`verify_side` - checks the already-written side-view file against its source COCO and the
  R.2 summary. It never rewrites the side file.
* :func:`load_label_file` / :func:`validate_labels` - loader + schema checks shared by both views.

``tag`` and ``axis`` are different fields that share spellings: ``tag = "S1"`` is a second-order
leaflet (MTG ``SecondaryLeaflet``), ``axis = "S1"`` is side shoot 1 (MTG Amendment A4).
"""

from __future__ import annotations

import collections
import datetime as dt
import hashlib
import json
from pathlib import Path
from typing import Any

import numpy as np

SCHEMA = "tomato-synth-labels-1"

# (id, name, Korean name) - user decision 2026-10-12, normative. Do not "fix" compond_leaf.
CLASS_SET: tuple[tuple[int, str, str], ...] = (
    (0, "compond_leaf", "복엽"),
    (1, "leaf", "소엽(측소엽)"),
    (2, "leaf2", "소소엽"),
    (3, "shoot", "신엽 묶음"),
    (4, "terminal_leaf", "정소엽"),
    (5, "truss", "화방"),
)
CLASS_ID: dict[str, int] = {name: i for i, name, _ in CLASS_SET}

# Generator leaflet ``kind`` -> class. Taken from the generator's own record, never from geometry.
# ``secondary`` is listed for completeness: synth-stage1-0.2.0 never produces one (see TRUSS/S1 notes).
LEAFLET_KIND_CLASS: dict[str, str] = {
    "terminal": "terminal_leaf",
    "pair": "leaf",
    "intercalary": "leaf2",
    "secondary": "leaf2",
}

TRUSS_ABSENT_REASON = (
    "tomato3d/synth contains no truss / inflorescence / flower code (verified 2026-10-12), so no synthetic "
    "image contains a truss. 'truss' in tomato3d/io/schemas.py and tomato3d/state/* is the state layer, not "
    "the generator. A truss detector can only be trained from real photos.")
S1_ABSENT_REASON = (
    "the generator (synth-stage1-0.2.0, compound_leaf.py) produces no second-order leaflets, so class leaf2 "
    "holds intercalary leaflets (tag I1) only in this file")

# Per-annotation attribute types. ``None`` is allowed where listed.
_COMMON_ATTRS: dict[str, tuple[type, ...]] = {
    "id": (int,), "image_id": (int,), "class": (str,), "class_id": (int,), "bbox_xywh": (list,),
    "compound_id": (str, type(None)), "vis_frac": (float, int), "visible_px": (int,),
}
_VIEW_ATTRS: dict[str, dict[str, tuple[type, ...]]] = {
    "top": {"object_id": (str,), "axis": (str,), "rank": (int, type(None)), "tag": (str, type(None)),
            "amodal_px": (int,), "amodal_bbox_xywh": (list,)},
    "side": {"direction": (str, type(None)), "direction_status": (str,), "quadrant_gt": (int,),
             "delta_deg": (float, int), "boundary_excluded": (bool,)},
}
DIRECTION_VALUES = ("cl_toward", "cl_right", "cl_away", "cl_left")
DIRECTION_STATUS_VALUES = ("clear", "unclear_boundary_band")


class LabelSchemaError(ValueError):
    """A label file violates the class schema."""


# --------------------------------------------------------------------------- small helpers
def class_set_json() -> list[dict[str, Any]]:
    return [dict(id=i, name=n, ko=ko) for i, n, ko in CLASS_SET]


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for chunk in iter(lambda: f.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def box_xywh(mask: np.ndarray) -> list[float] | None:
    """Pixel-edge box ``[x, y, w, h]`` of a boolean mask (same edges as ``sideview._box_of``)."""
    ys, xs = np.nonzero(mask)
    if len(ys) == 0:
        return None
    x0, y0 = float(xs.min()), float(ys.min())
    return [x0, y0, float(xs.max() + 1) - x0, float(ys.max() + 1) - y0]


def leaflet_class(info: dict[str, Any]) -> str:
    """Detector class of one generator leaflet record (``leaflet_index.json`` entry)."""
    kind = info.get("kind")
    if kind not in LEAFLET_KIND_CLASS:
        raise LabelSchemaError(f"leaflet {info.get('leaflet_id')!r}: unknown generator kind {kind!r}")
    tag = str(info.get("tag", ""))
    # the tag must agree with the kind; a disagreement is a generator/record defect, not a choice
    expected = {"terminal": tag == "T", "pair": tag.startswith("P"), "intercalary": tag.startswith("I"),
                "secondary": "S" in tag}[kind]
    if not expected:
        raise LabelSchemaError(f"leaflet {info.get('leaflet_id')!r}: kind {kind!r} disagrees with tag {tag!r}")
    return LEAFLET_KIND_CLASS[kind]


# --------------------------------------------------------------------------- top view: per-view instances
def instance_plan(parts: list[dict[str, Any]], index: dict[str, Any]) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Give every part one raster instance so that ONE raster pass yields all three granularities.

    Leaflets keep their generator instance (``leaflet_index.json`` key) so the stored
    ``visible_mask.png`` can be reproduced exactly; rachis / petiolule / apex parts get fresh ids
    above the leaflet range. Returns (parts with ``instance`` set, plan) where ``plan`` maps
    ``compound_id -> [instance ids]``, ``apex -> [ids]`` and ``leaflets -> {instance: index key}``.
    """
    by_leaflet_id = {v["leaflet_id"]: int(k) for k, v in index.items()}
    next_id = max(by_leaflet_id.values(), default=0) + 1
    compounds: dict[str, list[int]] = collections.defaultdict(list)
    apex: list[int] = []
    out = []
    for p in parts:
        q = dict(p)
        name, organ = str(p["name"]), p["organ"]
        if organ == "leaflet":
            if name not in by_leaflet_id:
                raise LabelSchemaError(f"leaflet part {name!r} is not in leaflet_index.json")
            q["instance"] = by_leaflet_id[name]
            compounds[index[str(q["instance"])]["compound_id"]].append(q["instance"])
        elif organ in ("rachis", "petiolule", "apex"):
            q["instance"] = next_id
            if organ == "apex":
                apex.append(next_id)
            else:
                from tomato3d.synth.sideview import compound_of_part

                cid = compound_of_part(p)
                if cid is None:
                    raise LabelSchemaError(f"cannot assign {organ} part {name!r} to a compound")
                compounds[cid].append(next_id)
            next_id += 1
        else:
            q["instance"] = 0
        out.append(q)
    return out, dict(compounds=dict(compounds), apex=apex,
                     leaflets={i: str(i) for i in by_leaflet_id.values()})


def _union(masks: dict[int, np.ndarray], ids: list[int], shape: tuple[int, int]) -> np.ndarray:
    m = np.zeros(shape, bool)
    for i in ids:
        if i in masks:
            m |= masks[i]
    return m


def view_annotations(*, scene_id: str, graph: dict[str, Any], index: dict[str, Any],
                     stored_visible: np.ndarray, stored_amodal: dict[str, np.ndarray],
                     raster_visible: np.ndarray, raster_amodal: dict[int, np.ndarray], plan: dict[str, Any],
                     min_visible_px: int) -> dict[str, Any]:
    """Annotations of one top view. Pure function of the mask layers (testable without a run).

    ``stored_*``: the run's own leaflet layers (``visible_mask.png``; ``amodal/<compound>_<tag>.png``
    keyed ``"<compound>_<tag>"``). ``raster_*``: the one-pass raster of :func:`instance_plan` parts.
    Instances with ``visible_px < min_visible_px`` are listed in ``excluded_occluded``, never dropped
    silently. Every annotation carries exactly one class.
    """
    shape = stored_visible.shape
    rank_of = {c["compound_id"]: int(c["rank_from_bottom"]) for c in graph["compounds"]}
    anns: list[dict[str, Any]] = []
    excluded: list[dict[str, Any]] = []

    def add(cls: str, object_id: str, vis: np.ndarray, amodal: np.ndarray | None, **attrs: Any) -> None:
        visible_px = int(vis.sum())
        amodal_px = int(amodal.sum()) if amodal is not None else 0
        if visible_px < min_visible_px:
            excluded.append(dict(object_id=object_id, **{"class": cls}, visible_px=visible_px))
            return
        if amodal_px < visible_px:  # amodal covers visible by construction; anything else is a broken layer
            raise LabelSchemaError(f"{object_id}: amodal {amodal_px} px < visible {visible_px} px")
        anns.append({"class": cls, "class_id": CLASS_ID[cls], "object_id": object_id,
                     "bbox_xywh": box_xywh(vis), "amodal_bbox_xywh": box_xywh(amodal),
                     "visible_px": visible_px, "amodal_px": amodal_px,
                     "vis_frac": round(visible_px / amodal_px, 4), **attrs})

    # leaflets: stored layers + generator tag
    for key in sorted(index, key=int):
        info = index[key]
        cid, tag = info["compound_id"], info["tag"]
        add(leaflet_class(info), f"{scene_id}/{cid}/{tag}", stored_visible == int(key),
            stored_amodal.get(f"{cid}_{tag}"), axis="M", rank=rank_of[cid], compound_id=cid, tag=tag)
    # compounds: leaflets + rachis + petiolules (the side-view compound definition)
    for comp in graph["compounds"]:
        cid = comp["compound_id"]
        ids = plan["compounds"].get(cid, [])
        add("compond_leaf", f"{scene_id}/{cid}", np.isin(raster_visible, ids),
            _union(raster_amodal, ids, shape), axis="M", rank=rank_of[cid], compound_id=cid, tag=None)
    # shoot: the generator's single apex bud on the main stem (no side shoots in synth-stage1-0.2.0)
    ids = plan["apex"]
    if ids:
        add("shoot", f"{scene_id}/M/shoot", np.isin(raster_visible, ids), _union(raster_amodal, ids, shape),
            axis="M", rank=None, compound_id=None, tag=None)
    return dict(annotations=anns, excluded_occluded=excluded)


def leaflet_layer_agreement(stored_visible: np.ndarray, raster_visible: np.ndarray, plan: dict[str, Any]
                            ) -> dict[str, int]:
    """Pixels where the re-rasterised leaflet layer differs from the stored ``visible_mask.png``."""
    leaflet_ids = np.array(sorted(plan["leaflets"]), dtype=raster_visible.dtype)
    recomputed = np.where(np.isin(raster_visible, leaflet_ids), raster_visible, 0)
    diff = int((recomputed.astype(np.int64) != stored_visible.astype(np.int64)).sum())
    return dict(pixels=int(stored_visible.size), differing_px=diff)


# --------------------------------------------------------------------------- top view: run export
def _read_json(path: Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def export_top(run: Path, out_path: Path, *, min_vis_frac: float, generated: str | None = None,
               view_kind: str = "top") -> dict[str, Any]:
    """Write the top-view label JSON for every ``view_kind == 'top'`` row of ``run/manifest.jsonl``."""
    from tomato3d.synth.camera import RigView
    from tomato3d.synth.config import load_generator_config
    from tomato3d.synth.images import imread
    from tomato3d.synth.pipeline import GeometryCache
    from tomato3d.synth.raster import rasterize
    from tomato3d.synth.render_remote import load_parts

    run = Path(run)
    project_root = Path(__file__).resolve().parents[2]
    contract = _read_json(run / "stage1_contract.json")
    min_visible_px = int(contract["min_visible_px"])
    cfg = load_generator_config(run / "generator_config.json")
    views = {d["view_id"]: RigView(**{k: (tuple(map(tuple, v)) if k == "camera_matrix" else
                                          tuple(v) if isinstance(v, list) else v) for k, v in d.items()})
             for d in _read_json(run / "views.json")["views"]}
    gc = GeometryCache(cfg, int(contract["resolution_px"]))
    rows = [json.loads(line) for line in (run / "manifest.jsonl").read_text(encoding="utf-8").splitlines()
            if line.strip()]
    n_manifest_rows = len(rows)
    rows = [r for r in rows if r["view_kind"] == view_kind]
    if not rows:
        raise SystemExit(f"no view_kind == {view_kind!r} rows in {run / 'manifest.jsonl'}")

    images, annotations, excluded_all, agreement = [], [], [], []
    scene_cache: dict[str, Any] = {}
    for row in rows:
        sid = row["scene_id"]
        if sid not in scene_cache:
            sdir = run / "scenes" / sid
            job = _read_json(sdir / "render_job" / "job.json")
            index = _read_json(sdir / "leaflet_index.json")
            parts, plan = instance_plan(load_parts(sdir / "render_job", job), index)
            scene_cache = {sid: dict(graph=_read_json(sdir / "plant_graph.json"), index=index, parts=parts,
                                     plan=plan)}
        sc = scene_cache[sid]
        vdir = run / Path(row["visible_mask"]).parent
        view = views[row["view_id"]]
        layers = rasterize(sc["parts"], view.rotation, view.translation, gc.get(view))
        stored_visible = imread(vdir / "visible_mask.png")
        stored_amodal = {f.stem: imread(f) > 0 for f in sorted((vdir / "amodal").glob("*.png"))}
        rgb = imread(run / row["rgb"]) if row.get("rgb") else None
        if rgb is None or rgb.shape[:2] != stored_visible.shape:
            raise SystemExit(f"{row['rgb']}: missing or not aligned with its masks")
        image_id = len(images) + 1
        agree = leaflet_layer_agreement(stored_visible, layers.visible, sc["plan"])
        agreement.append(dict(image_id=image_id, **agree))
        va = view_annotations(scene_id=sid, graph=sc["graph"], index=sc["index"], stored_visible=stored_visible,
                              stored_amodal=stored_amodal, raster_visible=layers.visible,
                              raster_amodal=layers.amodal, plan=sc["plan"], min_visible_px=min_visible_px)
        h, w = stored_visible.shape
        images.append(dict(id=image_id, file_name=row["rgb"], width=int(w), height=int(h), scene_id=sid,
                           view_id=row["view_id"], view_kind=row["view_kind"],
                           camera_elevation_deg=row["camera_elevation_deg"],
                           camera_source_session=row["camera_source_session"], rgb_status=row.get("rgb_status")))
        for a in va["annotations"]:
            annotations.append(dict(id=len(annotations) + 1, image_id=image_id, **a))
        excluded_all.extend(dict(image_id=image_id, **e) for e in va["excluded_occluded"])

    counts = collections.Counter(a["class"] for a in annotations)
    tags = collections.Counter(a["tag"] for a in annotations if a["class"] == "leaf2")
    absent = [dict(name="truss", id=CLASS_ID["truss"], reason=TRUSS_ABSENT_REASON)]
    for _, name, _ in CLASS_SET:
        if name != "truss" and counts[name] == 0:
            absent.append(dict(name=name, id=CLASS_ID[name],
                               reason=f"no visible instance (>= {min_visible_px} px) in the exported views"))
    vf = np.array([a["vis_frac"] for a in annotations], float)
    total_diff = sum(a["differing_px"] for a in agreement)
    rel = lambda p: Path(p).resolve().relative_to(project_root).as_posix()  # noqa: E731
    doc = dict(
        schema=SCHEMA, generated=generated or dt.date.today().isoformat(), view_type="top",
        source_run=rel(run),
        source_files={name: dict(path=rel(run / name), sha256=sha256_file(run / name))
                      for name in ("manifest.jsonl", "stage1_contract.json", "generator_config.json", "views.json")},
        generator_version=rows[0].get("generator_version"),
        view_selection=dict(rule=f"manifest.jsonl rows with view_kind == {view_kind!r}",
                            scenes=len({r["scene_id"] for r in rows}), views=len(rows),
                            camera_elevation_deg_min=min(r["camera_elevation_deg"] for r in rows),
                            camera_elevation_deg_max=max(r["camera_elevation_deg"] for r in rows),
                            not_exported=f"{n_manifest_rows - len(rows)} other manifest rows (view_kind != "
                                         f"{view_kind!r}) of the same scenes"),
        class_set=class_set_json(),
        classes_present=[n for _, n, _ in CLASS_SET if counts[n] > 0],
        classes_absent=absent,
        subtypes_absent=[dict(**{"class": "leaf2"}, tag="S1", reason=S1_ABSENT_REASON)] if not tags.get("S1") else [],
        class_counts={n: counts[n] for _, n, _ in CLASS_SET},
        leaf2_tag_counts=dict(tags),
        labeling_rules=dict(
            leaflet_class="from the generator's own leaflet kind/tag in leaflet_index.json (terminal -> terminal_leaf, "
                          "pair -> leaf, intercalary -> leaf2, secondary -> leaf2); never from geometry. A terminal "
                          "leaflet is never also labeled leaf.",
            leaf2="user decision 2026-10-12: leaf2 = second-order leaflets (tag S1) AND intercalary leaflets (tag I1); "
                  "the MTG tag stays in 'tag' so the two can be separated again",
            compond_leaf="all leaflets + rachis + petiolules of one compound (same definition as the side-view set)",
            shoot="the generator's apex bud on the main stem (a sphere of apex_bud_radius_mm with leaf material); "
                  "axis 'M'. The generator has no side shoots, so no shoot' / shoot'' instance exists",
            axis="'M' for every instance: synth-stage1-0.2.0 grows the main stem only",
            rank="compound rank_from_bottom of the generator (rank 1 = lowest compound present); null for shoot",
            object_id="stable per scene: <scene>/<compound>/<tag> leaflet, <scene>/<compound> compound, <scene>/M/shoot",
        ),
        occlusion=dict(
            vis_frac_definition="visible_px / amodal_px in the output image (amodal = every pixel the instance covers "
                                "ignoring occluders, clipped to the image; truncation by the frame is not occlusion)",
            min_visible_px=min_visible_px, min_visible_px_applied=True,
            min_visible_px_source="stage1_contract.json::min_visible_px of the source run",
            excluded_below_min_visible_px=len(excluded_all),
            min_vis_frac=float(min_vis_frac), min_vis_frac_applied=False,
            min_vis_frac_note="recorded, NOT applied: every instance >= min_visible_px is in 'annotations' with its "
                              "vis_frac. No vis_frac rule has been declared for this run (the Addendum B1 GT rule "
                              "declares min_visible_px 49 + solidity 0.434 for C6 only). Filter downstream and record it.",
            n_below_min_vis_frac=int((vf < float(min_vis_frac)).sum()),
            vis_frac_p10_p50_p90=[round(float(x), 4) for x in np.percentile(vf, [10, 50, 90])] if len(vf) else [],
        ),
        mask_reconstruction=dict(
            method="compound and shoot masks: one raster pass of render_job/parts.npz with the run's own camera "
                   "geometry (tomato3d.synth.raster.rasterize, GeometryCache at the contract resolution); RGB untouched",
            leaflet_layer_check="the same pass recomputes visible_mask.png; differing pixels over all exported views",
            differing_px=total_diff, pixels=sum(a["pixels"] for a in agreement),
            per_image_differing_px_max=max(a["differing_px"] for a in agreement),
        ),
        realism_caveat="O-mature did NOT pass realism (rank ratio 1.859, handoff/R_DECISIONS_2026-10-10.md); "
                       "these are labels of synthetic images, not evidence about real plants",
        evidence="synthetic ground truth", counts_as_real_annotation=False,
        bbox_format="bbox_xywh = [x, y, w, h] in pixels, pixel-edge coordinates of the visible mask",
        images=images, annotations=annotations, excluded_occluded=excluded_all,
    )
    validate_labels(doc)
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(doc, ensure_ascii=False, indent=1), encoding="utf-8")
    return doc


# --------------------------------------------------------------------------- loader / validation
def validate_labels(doc: dict[str, Any]) -> list[str]:
    """Raise :class:`LabelSchemaError` on a schema violation; return non-fatal header gaps.

    Fatal: wrong schema / view_type, class set not exactly :data:`CLASS_SET`, an annotation whose
    class and class_id disagree or that names a class outside the set, an instance labelled under
    two classes (same object in one image twice), an attribute of the wrong type, a dangling
    image id, ``counts_as_real_annotation`` true, an annotated class listed as absent.
    Gaps (returned, not raised): header fields this schema expects but an older file lacks.
    """
    if doc.get("schema") != SCHEMA:
        raise LabelSchemaError(f"schema {doc.get('schema')!r} != {SCHEMA!r}")
    view_type = doc.get("view_type")
    if view_type not in _VIEW_ATTRS:
        raise LabelSchemaError(f"view_type {view_type!r} not in {sorted(_VIEW_ATTRS)}")
    got = [(c.get("id"), c.get("name")) for c in doc.get("class_set", [])]
    if got != [(i, n) for i, n, _ in CLASS_SET]:
        raise LabelSchemaError(f"class_set {got} != {[(i, n) for i, n, _ in CLASS_SET]}")
    gaps = []
    if "classes_absent" not in doc:
        gaps.append("header has no classes_absent")
    if "counts_as_real_annotation" not in doc:
        gaps.append("header has no counts_as_real_annotation key (stated only inside 'evidence')")
    elif doc["counts_as_real_annotation"] is not False:
        raise LabelSchemaError("counts_as_real_annotation must be false for synthetic labels")
    if "synthetic ground truth" not in str(doc.get("evidence", "")):
        raise LabelSchemaError("evidence must state 'synthetic ground truth'")
    image_ids = {im["id"] for im in doc.get("images", [])}
    if len(image_ids) != len(doc.get("images", [])):
        raise LabelSchemaError("duplicate image ids")
    attrs = dict(_COMMON_ATTRS, **_VIEW_ATTRS[view_type])
    seen: dict[tuple[int, str], str] = {}
    ann_ids = set()
    for a in doc.get("annotations", []):
        cls = a.get("class")
        if cls not in CLASS_ID:
            raise LabelSchemaError(f"annotation {a.get('id')}: class {cls!r} not in the class set")
        if a.get("class_id") != CLASS_ID[cls]:
            raise LabelSchemaError(f"annotation {a.get('id')}: class_id {a.get('class_id')} != {CLASS_ID[cls]} ({cls})")
        for k, types in attrs.items():
            if k not in a:
                raise LabelSchemaError(f"annotation {a.get('id')}: missing attribute {k!r}")
            v = a[k]
            if isinstance(v, bool) and bool not in types:
                raise LabelSchemaError(f"annotation {a.get('id')}: {k}={v!r} has type bool")
            if not isinstance(v, types):
                raise LabelSchemaError(f"annotation {a.get('id')}: {k}={v!r} is not {[t.__name__ for t in types]}")
        box = a["bbox_xywh"]
        if len(box) != 4 or not all(isinstance(x, (int, float)) for x in box) or box[2] <= 0 or box[3] <= 0:
            raise LabelSchemaError(f"annotation {a.get('id')}: bad bbox_xywh {box}")
        if not 0.0 <= float(a["vis_frac"]) <= 1.0:
            raise LabelSchemaError(f"annotation {a.get('id')}: vis_frac {a['vis_frac']} outside [0, 1]")
        if a["image_id"] not in image_ids:
            raise LabelSchemaError(f"annotation {a.get('id')}: image_id {a['image_id']} not in images")
        if a["id"] in ann_ids:
            raise LabelSchemaError(f"duplicate annotation id {a['id']}")
        ann_ids.add(a["id"])
        if view_type == "side":
            if a["direction"] is not None and a["direction"] not in DIRECTION_VALUES:
                raise LabelSchemaError(f"annotation {a['id']}: direction {a['direction']!r}")
            if a["direction_status"] not in DIRECTION_STATUS_VALUES:
                raise LabelSchemaError(f"annotation {a['id']}: direction_status {a['direction_status']!r}")
            if (a["direction"] is None) != (a["direction_status"] == "unclear_boundary_band"):
                raise LabelSchemaError(f"annotation {a['id']}: direction / direction_status disagree")
        object_key = a.get("object_id") or a.get("compound_id")
        key = (a["image_id"], str(object_key))
        if key in seen:
            raise LabelSchemaError(f"object {object_key!r} in image {a['image_id']} labelled twice "
                                   f"({seen[key]} and {cls})")
        seen[key] = cls
    present = {a["class"] for a in doc.get("annotations", [])}
    for entry in doc.get("classes_absent", []):
        name = entry.get("name") if isinstance(entry, dict) else entry
        if name in present:
            raise LabelSchemaError(f"class {name!r} is listed as absent but has annotations")
        if isinstance(entry, dict) and not entry.get("reason"):
            raise LabelSchemaError(f"classes_absent entry {name!r} has no reason")
    if "classes_present" in doc and sorted(doc["classes_present"]) != sorted(present):
        raise LabelSchemaError(f"classes_present {doc['classes_present']} != annotated {sorted(present)}")
    return gaps


def load_label_file(path: Path) -> dict[str, Any]:
    """Load + validate one label file. Header gaps are attached as ``_gaps`` (never written back)."""
    doc = _read_json(Path(path))
    gaps = validate_labels(doc)
    doc["_gaps"] = gaps
    return doc


# --------------------------------------------------------------------------- side view: verification only
def verify_side(side_path: Path, coco_path: Path, summary_path: Path) -> dict[str, Any]:
    """Compare the side-view JSON with its source COCO and ``R2_label_summary.json``. Read-only."""
    from tomato3d.synth.sideview import camera_relative_class, camera_relative_to_quadrant

    side = _read_json(side_path)
    coco = _read_json(coco_path)
    summ = _read_json(summary_path)
    problems: list[str] = []
    gaps = []
    try:
        gaps = validate_labels(side)
    except LabelSchemaError as exc:
        problems.append(f"schema: {exc}")
    cats = {c["id"]: c["name"] for c in coco["categories"]}
    compound_cats = set(DIRECTION_VALUES) | {"compound_unclear"}
    src = collections.defaultdict(list)
    dropped = collections.Counter()
    for a in coco["annotations"]:
        name = cats[a["category_id"]]
        if name in compound_cats:
            src[(a["image_id"], a["compound_id"])].append(a)
        else:
            dropped[name] += 1

    # counts
    n_src = sum(len(v) for v in src.values())
    checks = dict(
        images=dict(side=len(side["images"]), coco=len(coco["images"]), summary_views=summ["views"]),
        compound_annotations=dict(side=len(side["annotations"]), coco=n_src, summary_boxed=summ["boxed_compounds"]),
        dropped=dict(side_header=side.get("dropped_from_source"), coco=dict(dropped)),
        scenes=dict(side=len({im["scene_id"] for im in side["images"]}), summary=summ["scenes_done"]),
    )
    if not (len(side["images"]) == len(coco["images"]) == summ["views"]):
        problems.append(f"image count {checks['images']}")
    if not (len(side["annotations"]) == n_src == summ["boxed_compounds"]):
        problems.append(f"compound annotation count {checks['compound_annotations']}")
    if dict(side.get("dropped_from_source", {})) != dict(dropped):
        problems.append(f"dropped classes {checks['dropped']}")
    if checks["scenes"]["side"] != summ["scenes_done"]:
        problems.append(f"scene count {checks['scenes']}")
    if sha256_file(coco_path) != side.get("source_sha256"):
        problems.append("source_sha256 does not match synside_coco.json")

    # images identical
    coco_images = {im["id"]: im for im in coco["images"]}
    image_mismatch = 0
    for im in side["images"]:
        c = coco_images.get(im["id"])
        if c is None or any(c.get(k) != im.get(k) for k in ("file_name", "width", "height", "scene_id",
                                                             "protocol_azimuth_deg", "camera_azimuth_deg")):
            image_mismatch += 1
    if image_mismatch:
        problems.append(f"{image_mismatch} images differ from the COCO image records")

    # per-annotation identity + direction + quadrant consistency
    bbox_mismatch = attr_mismatch = missing = duplicate_src = 0
    quad_checked = quad_mismatch = delta_bin_mismatch = 0
    direction_counts = collections.Counter()
    azimuth = {im["id"]: im["protocol_azimuth_deg"] for im in side["images"]}
    seen = set()
    for a in side["annotations"]:
        key = (a["image_id"], a["compound_id"])
        seen.add(key)
        cands = src.get(key, [])
        if len(cands) != 1:
            missing += len(cands) == 0
            duplicate_src += len(cands) > 1
            continue
        c = cands[0]
        if [float(x) for x in c["bbox"]] != [float(x) for x in a["bbox_xywh"]]:
            bbox_mismatch += 1
        name = cats[c["category_id"]]
        expect_dir = None if name == "compound_unclear" else name
        if (a["direction"] != expect_dir or a["boundary_excluded"] != c["excluded_boundary"]
                or a["quadrant_gt"] != c["quadrant_gt"] or a["delta_deg"] != c["delta_deg"]
                or a["vis_frac"] != c["vis_frac"] or a["visible_px"] != c["visible_px"]
                or (a["direction_status"] == "clear") != (not c["excluded_boundary"])):
            attr_mismatch += 1
        if a["direction"] is not None:
            direction_counts[a["direction"]] += 1
            quad_checked += 1
            if camera_relative_to_quadrant(a["direction"], azimuth[a["image_id"]]) != a["quadrant_gt"]:
                quad_mismatch += 1
            if camera_relative_class(a["delta_deg"]) != a["direction"]:
                delta_bin_mismatch += 1
    unmatched_src = sum(1 for k in src if k not in seen)
    checks["annotation_identity"] = dict(bbox_mismatch=bbox_mismatch, attribute_mismatch=attr_mismatch,
                                         side_without_source=missing, ambiguous_source=duplicate_src,
                                         source_without_side=unmatched_src)
    checks["direction_counts"] = dict(side=dict(direction_counts), summary=summ["direction_class_counts"])
    # R2's quadrant_check runs over ALL compound/view pairs outside the band, including the occluded ones that
    # never got a box; the side file holds boxed compounds only, so its population is boxed - boundary-excluded.
    expected_checked = summ["boxed_compounds"] - summ["excluded_boundary_among_boxed"]
    checks["quadrant"] = dict(checked=quad_checked, mismatches=quad_mismatch, expected_boxed_clear=expected_checked,
                              summary_checked_all_pairs=summ["quadrant_check"]["checked"],
                              summary_mismatches=summ["quadrant_check"]["mismatches"],
                              delta_bin_mismatch=delta_bin_mismatch,
                              note="summary_checked_all_pairs includes excluded_occluded pairs that have no box")
    checks["unclear"] = dict(side=sum(1 for a in side["annotations"] if a["direction"] is None),
                             summary_excluded_boundary=summ["excluded_boundary_among_boxed"])
    for k, v in checks["annotation_identity"].items():
        if v:
            problems.append(f"annotation identity: {k} = {v}")
    if dict(direction_counts) != summ["direction_class_counts"]:
        problems.append("direction class counts differ from R2_label_summary")
    if quad_mismatch or quad_checked != expected_checked or summ["quadrant_check"]["mismatches"]:
        problems.append(f"quadrant check {checks['quadrant']}")
    if delta_bin_mismatch:
        problems.append(f"{delta_bin_mismatch} directions disagree with their own delta_deg bin")
    if checks["unclear"]["side"] != summ["excluded_boundary_among_boxed"]:
        problems.append(f"unclear count {checks['unclear']}")
    return dict(schema="tomato-synth-labels-verification-1", verified_file=Path(side_path).as_posix(),
                against=[Path(coco_path).as_posix(), Path(summary_path).as_posix()],
                result="pass" if not problems else "mismatch", problems=problems, header_gaps=gaps, checks=checks)


# --------------------------------------------------------------------------- CLI
def main(argv: list[str] | None = None) -> None:
    import argparse

    ap = argparse.ArgumentParser(description="label class schema + JSON label export (2026-10-12)")
    sub = ap.add_subparsers(dest="cmd", required=True)
    t = sub.add_parser("export-top")
    t.add_argument("--run", required=True, help="Stage-1 run/cell folder with manifest.jsonl")
    t.add_argument("--out", required=True)
    t.add_argument("--min-vis-frac", type=float, required=True,
                   help="recorded in the header, NOT applied (every instance >= min_visible_px is exported)")
    v = sub.add_parser("verify-side")
    v.add_argument("--side", required=True)
    v.add_argument("--coco", required=True)
    v.add_argument("--summary", required=True)
    v.add_argument("--out", required=True)
    c = sub.add_parser("check")
    c.add_argument("files", nargs="+")
    args = ap.parse_args(argv)
    if args.cmd == "export-top":
        doc = export_top(Path(args.run), Path(args.out), min_vis_frac=args.min_vis_frac)
        print(json.dumps(dict(images=len(doc["images"]), annotations=len(doc["annotations"]),
                              class_counts=doc["class_counts"], classes_absent=[a["name"] for a in doc["classes_absent"]],
                              excluded=len(doc["excluded_occluded"]),
                              leaflet_layer_differing_px=doc["mask_reconstruction"]["differing_px"]), ensure_ascii=False))
    elif args.cmd == "verify-side":
        r = verify_side(Path(args.side), Path(args.coco), Path(args.summary))
        Path(args.out).parent.mkdir(parents=True, exist_ok=True)
        Path(args.out).write_text(json.dumps(r, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps(dict(result=r["result"], problems=r["problems"], header_gaps=r["header_gaps"]),
                         ensure_ascii=False))
    else:
        for f in args.files:
            doc = load_label_file(Path(f))
            print(json.dumps(dict(file=f, view_type=doc["view_type"], annotations=len(doc["annotations"]),
                                  gaps=doc["_gaps"]), ensure_ascii=False))


if __name__ == "__main__":
    main()
