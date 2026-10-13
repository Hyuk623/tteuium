"""P1.3 - observation ingest: real captures, human boxes/masks, flagged detector proposals, synthetic GT.

Real board-free captures (``data/raw/<plant_id>/<session>/generator_capture.csv``) become
``captures.csv`` rows that reference the raw photo by path + sha256 (never copied). Per photo:

* ``capture_time`` = the CSV's ``captured_at`` (device clock; UTC offset not recorded, stated in
  ``note``); ``time_since_lights_on_min`` and ``photoperiod_phase`` are ``unavailable`` because the
  lights-on clock time is null (``env_light_20261010.json``) and may not be derived from the clock;
* ``scale_status = unavailable``: the ruler scale is pending (Addendum I.4) and the pot-rim inner
  diameter is unmeasured; ``rotation_status = unavailable``: no pot orientation mark is recorded
  (azimuths are ``capture_order_assumed``);
* the sha256 is recomputed from the file and compared with the CSV value; a mismatch is a hard
  error, not a warning.

Observations: human COCO polygons/boxes (``provenance = human``), detector proposals
(``provenance = detector_proposal``, ``review_state = unreviewed``, never tracked) and synthetic GT
(``provenance = synthetic_gt``, fixtures only). No detector and no human labels -> the capture's
observation status is ``unavailable`` with the reason, never an empty list pretending success.
"""

from __future__ import annotations

import csv
import hashlib
import json
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.io.schemas import UNAVAILABLE
from tomato3d.state import schema as s

DETECTOR_STATUS_C6 = "unvalidated_on_boardfree_top"


class IngestError(ValueError):
    """An input fails its contract (hash mismatch, unknown capture, malformed label file)."""


def sha256_file(path: Path) -> str:
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


@dataclass(frozen=True)
class RawPhoto:
    plant_id: str
    session_id: str
    photo_file: str
    view: str
    path: Path
    captured_at: str
    csv_sha256: str
    azimuth_deg: str
    camera_elevation_deg: str
    scale_reference: str
    notes: str


def discover_raw(raw_dir: Path, plant_glob: str = "dwt_1*") -> list[RawPhoto]:
    photos = []
    for csv_path in sorted(Path(raw_dir).glob(f"{plant_glob}/*/generator_capture.csv")):
        with csv_path.open(encoding="utf-8", newline="") as fh:
            for r in csv.DictReader(fh):
                photos.append(RawPhoto(
                    plant_id=r["plant_id"], session_id=r["session_id"], photo_file=r["photo_file"],
                    view=r["photo_kind"], path=csv_path.parent / r["photo_file"], captured_at=r["captured_at"],
                    csv_sha256=r["sha256"], azimuth_deg=r["azimuth_deg"],
                    camera_elevation_deg=r["camera_elevation_deg_approx"], scale_reference=r["scale_reference"],
                    notes=r["notes"]))
    return photos


def capture_id_of(photo: RawPhoto) -> str:
    return f"{photo.session_id}/{Path(photo.photo_file).stem}"


def real_capture_rows(photos: Sequence[RawPhoto], project_root: Path,
                      capture_tz: str | None = None) -> tuple[list[dict[str, str]], list[str]]:
    """``captures.csv`` rows for real photos + a list of hash/time problems (each fatal to the caller).

    ``capture_tz`` (IANA name, stated by the user) makes the device-clock times timezone-aware with
    ``capture_tz_source = user_stated``; without it the times stay naive and both fields are
    ``unavailable``. Nothing defaults to a zone."""
    if capture_tz is not None:
        s.parse_capture_tz(capture_tz)
    rows, problems = [], []
    for ph in photos:
        if not ph.path.exists():
            problems.append(f"{ph.path}: missing")
            continue
        digest = sha256_file(ph.path)
        if ph.csv_sha256 and digest != ph.csv_sha256:
            problems.append(f"{ph.path}: sha256 {digest} != generator_capture.csv {ph.csv_sha256}")
        naive = ph.captured_at.replace(" ", "T") if ph.captured_at else UNAVAILABLE
        stamp, tz_name, tz_source = naive, UNAVAILABLE, UNAVAILABLE
        if capture_tz is not None and naive != UNAVAILABLE:
            try:
                stamp, tz_name, tz_source = s.localize_capture_time(naive, capture_tz), capture_tz, "user_stated"
            except s.P1SchemaError as exc:
                problems.append(f"{ph.path}: {exc}")
        rows.append(dict(
            capture_id=capture_id_of(ph), plant_instance_id=ph.plant_id, source_plant_id=ph.plant_id,
            evidence="real_photo", view=ph.view,
            capture_time=stamp,
            capture_time__status="measured" if ph.captured_at else UNAVAILABLE,
            capture_tz=tz_name, capture_tz_source=tz_source,
            time_since_lights_on_min=UNAVAILABLE, time_since_lights_on_min__status=UNAVAILABLE,
            photoperiod_phase=UNAVAILABLE, frame="image_px", scale_source=UNAVAILABLE, scale_status=UNAVAILABLE,
            mm_per_px=UNAVAILABLE, mm_per_px_sd=UNAVAILABLE, scale_convention=UNAVAILABLE,
            scale_sources="0", scale_cross_check=UNAVAILABLE, scale_plane=UNAVAILABLE, scale_reference=UNAVAILABLE,
            scale_reference_plane=UNAVAILABLE, scale_reference_plane_offset_mm=UNAVAILABLE, rotation_status=UNAVAILABLE,
            image_path=ph.path.resolve().relative_to(project_root.resolve()).as_posix(), image_sha256=digest,
            session_id=ph.session_id,
            note=(("device clock; timezone " + tz_name + " stated by the user" if tz_name != UNAVAILABLE
                   else "device clock, UTC offset not recorded (no --capture-tz)")
                  + f"; azimuth_deg={ph.azimuth_deg or 'n/a'} "
                  f"(capture_order_assumed); camera_elevation_deg_approx={ph.camera_elevation_deg}; "
                  f"scale_reference={ph.scale_reference} (ruler scale pending I.4)")))
    return rows, problems


# --------------------------------------------------------------------------------------
# Human labels (COCO) and detector proposals
# --------------------------------------------------------------------------------------


def _poly_mask(polys: Sequence[Sequence[float]], shape: tuple[int, int]) -> np.ndarray:
    import cv2

    mask = np.zeros(shape, np.uint8)
    for poly in polys:
        pts = np.asarray(poly, float).reshape(-1, 2)
        cv2.fillPoly(mask, [np.round(pts).astype(np.int32)], 1)
    return mask.astype(bool)


COCO_CLASS_MAP = {"compound_leaf": "compound_leaf", "compond_leaf": "compound_leaf", "compound_leaves": "compound_leaf",
                  "leaflet": "leaflet", "terminal_leaflet": "terminal_leaflet", "main_stem": "main_stem",
                  "sub_stem": "sub_stem", "growth_shoot": "growth_shoot", "shoot": "growth_shoot", "truss": "truss"}


def axis_hint_of(label_class: str, attributes: Mapping[str, Any] | None, source: str) -> tuple[str, str]:
    """MTG A4 axis hint of one label: an explicit ``axis`` attribute (human), else ``main_stem`` -> M.
    ``sub_stem`` says "some side axis" but not which, so it gives no hint; nothing is inferred from position."""
    axis = str((attributes or {}).get("axis", "")).strip()
    if axis:
        s.check_axis_code(axis, f"label attribute axis={axis!r}")
        return axis, source
    if label_class == "main_stem":
        return "M", source
    return UNAVAILABLE, UNAVAILABLE


def import_coco(coco_path: Path, capture_of_file: Mapping[str, str], plant_instance_id: str,
                evidence: str = "real_photo") -> tuple[list[dict[str, str]], dict[str, np.ndarray], dict[str, str]]:
    """Human COCO export -> observation rows + masks. ``capture_of_file`` maps image file names to
    capture ids; an image without a capture is an error (labels never float free)."""
    coco = json.loads(Path(coco_path).read_text(encoding="utf-8"))
    cats = {c["id"]: c["name"] for c in coco["categories"]}
    images = {i["id"]: i for i in coco["images"]}
    rows, masks, quality = [], {}, {}
    n = 0
    for ann in coco["annotations"]:
        img = images[ann["image_id"]]
        cap = capture_of_file.get(img["file_name"])
        if cap is None:
            raise IngestError(f"{coco_path}: image {img['file_name']} has no capture")
        cls = COCO_CLASS_MAP.get(cats[ann["category_id"]], "other")
        n += 1
        obs_id = f"h{n:04d}"
        shape = (int(img["height"]), int(img["width"]))
        seg = ann.get("segmentation")
        if isinstance(seg, list) and seg:
            mask = _poly_mask(seg, shape)
            q = "human_polygon"
        else:
            x, y, w, h = ann["bbox"]
            mask = None
            q = "box_only_no_mask"
        quality[cap] = q if quality.get(cap) in (None, q) else "mixed"
        bbox = ann["bbox"]
        hint, hint_src = axis_hint_of(cats[ann["category_id"]], ann.get("attributes"), "human")
        rows.append(dict(
            plant_instance_id=plant_instance_id, capture_id=cap, obs_id=obs_id, obs_class=cls,
            axis_hint=hint, axis_hint_source=hint_src, provenance="human",
            source_id=f"human:{Path(coco_path).name}#ann{ann['id']}", source_score=UNAVAILABLE,
            detector_status="not_applicable", review_state="accepted",
            mask_ref=f"masks.json#{obs_id}" if mask is not None else UNAVAILABLE, mask_quality=q,
            area_px2=str(int(mask.sum())) if mask is not None else UNAVAILABLE,
            bbox_xyxy_px=json.dumps([bbox[0], bbox[1], bbox[0] + bbox[2], bbox[1] + bbox[3]]),
            centroid_xy_px=UNAVAILABLE, touches_other_mask=UNAVAILABLE, touches_image_border=UNAVAILABLE,
            plant_attribution="uncertain", parent_obs_id=UNAVAILABLE, membership_status=UNAVAILABLE,
            frame="image_px", evidence=evidence))
        if mask is not None:
            masks[obs_id] = mask
    return rows, masks, quality


def run_detector(images: Sequence[Path], weights: Path, imgsz: int, conf: float) -> list[dict[str, Any]]:
    """Run the C6 detector on images -> detection dicts (``{key, rgb_sha256, detector_args, detections}``).
    Requires ``ultralytics`` (project env). The caller labels every box a proposal."""
    from ultralytics import YOLO

    model = YOLO(str(weights))
    out = []
    for img in images:
        res = model.predict(str(img), imgsz=imgsz, conf=conf, verbose=False)[0]
        dets = [dict(cls=res.names[int(c)], box=[round(float(v), 2) for v in b], conf=round(float(p), 4))
                for b, c, p in zip(res.boxes.xyxy.tolist(), res.boxes.cls.tolist(), res.boxes.conf.tolist())]
        out.append(dict(key=Path(img).name, rgb_sha256=sha256_file(img),
                        detector_args=dict(weights=Path(weights).name, weights_sha256=sha256_file(weights),
                                           imgsz=imgsz, conf=conf, image_size_px=list(res.orig_shape[::-1])),
                        detections=dets))
    return out


def proposal_rows(detections: Sequence[Mapping[str, Any]], capture_of_key: Mapping[str, str],
                  plant_of_key: Mapping[str, str], evidence: str = "real_photo") -> list[dict[str, str]]:
    """Detector boxes -> observation rows flagged ``detector_proposal`` / ``unreviewed``."""
    rows = []
    for det in detections:
        cap = capture_of_key[det["key"]]
        for k, d in enumerate(det["detections"], start=1):
            rows.append(dict(
                plant_instance_id=plant_of_key[det["key"]], capture_id=cap, obs_id=f"d{k:04d}",
                obs_class=COCO_CLASS_MAP.get(d["cls"], "other"),
                axis_hint=axis_hint_of(d["cls"], None, "detector_class")[0],
                axis_hint_source=axis_hint_of(d["cls"], None, "detector_class")[1], provenance="detector_proposal",
                source_id=f"{det['detector_args']['weights']}:{det['detector_args']['weights_sha256'][:12]}"
                          f"@imgsz{det['detector_args']['imgsz']}",
                source_score=s.fmt(float(d["conf"]), 4), detector_status=DETECTOR_STATUS_C6,
                review_state="unreviewed", mask_ref=UNAVAILABLE, mask_quality="box_only_no_mask",
                area_px2=UNAVAILABLE, bbox_xyxy_px=json.dumps(d["box"]), centroid_xy_px=UNAVAILABLE,
                touches_other_mask=UNAVAILABLE, touches_image_border=UNAVAILABLE, plant_attribution="uncertain",
                parent_obs_id=UNAVAILABLE, membership_status=UNAVAILABLE, frame="image_px", evidence=evidence))
    return rows


def trackable(rows: Sequence[Mapping[str, str]]) -> list[Mapping[str, str]]:
    """Only accepted/edited, this-plant, non-proposal compound observations with a mask may be tracked."""
    return [r for r in rows if r["obs_class"] == "compound_leaf" and r["review_state"] in ("accepted", "edited")
            and r["provenance"] != "detector_proposal" and r["plant_attribution"] == "this_plant"
            and r["mask_ref"] != UNAVAILABLE]


def pack_masks(masks: Mapping[str, np.ndarray]) -> dict[str, Any]:
    """``{obs_id: {shape, intervals}}`` in the lossless interval format of ``tools.leaflet_mask_batch``."""
    from tools.leaflet_mask_batch import pack_mask

    return {k: pack_mask(np.asarray(v, bool)) for k, v in sorted(masks.items())}


def unpack_masks(doc: Mapping[str, Any]) -> dict[str, np.ndarray]:
    from tools.leaflet_mask_batch import unpack_mask

    return {k: unpack_mask(v, tuple(v["shape"])) for k, v in doc.items()}
