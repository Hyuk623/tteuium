"""Photo-only automatic run: one folder of 18 photographs in, the S0-S8 pipeline (and optionally XL) out (2026-09-28).

    python -X utf8 -m tools.plant_auto --photos <folder> --plant dwt_05 [--growth <growth.json>] [--xl]

The user's decisions (2026-09-28) this tool implements:

* view codes come from the fixed shooting order: the photographs are sorted by their EXIF capture time and take the
  protocol codes 01, 03, 11-18, 21-28 in that order (all four existing plants follow it exactly);
* model outputs go through without a person: organ boxes from the detector ensemble (stem and petiole outlines from
  its instance masks), leaflet masks from SAM, every mask accepted automatically. Everything they produce is marked
  'auto' (labels schema plant-auto-labels-1, batch label_source='auto', review_source='auto'); a person's later
  review replaces it through the normal editors and review pages;
* the growth record is optional. With it, compound-leaf names and counts are checked against it; without it, names
  are a height-order proposal only. Both can be produced from one set of labels and masks (--growth with --both).

* 2026-10-01: marker-corner poses are added right after S0 (tools.marker_pose_rescue) and S8 writes the whole-plant
  traits (tools.plant_traits). Many plants at once: tools.plant_batch.

Nothing here claims metric accuracy: poses come from the board only (ChArUco or its marker corners), 1 px gate unmet.
Outputs go to a fresh folder (default build/auto_<plant>_<date>/); sources are only read.
"""
from __future__ import annotations

import argparse
import csv
import json
import shutil
import sys
from datetime import datetime
from pathlib import Path

from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
MAIN_CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
#: The capture protocol's order (docs/파일럿_촬영_프로토콜 and filename_mapping.csv of dwt_01..04).
PROTOCOL = ['01', '03', '11', '12', '13', '14', '15', '16', '17', '18', '21', '22', '23', '24', '25', '26', '27', '28']
VIEW_TYPE = {'0': 'top_view', '1': 'middle_view', '2': 'side_view'}
IMAGE_EXT = {'.heic', '.heif', '.jpg', '.jpeg', '.png'}
#: v4 (2026-09-29): whole-photo model for all classes + 2x2-tile model for growth shoots and petioles (organ_prelabel
#: scale plan); held-out mean AP50 0.55 vs v3 0.44. The whole-photo model was trained on whole photos: crop=False.
DEFAULT_MODELS = ['build/organ_detector_v4_20260929/kout_full/full_final_all.pt']
DEFAULT_TILE_MODELS = ['build/organ_detector_v4_20260929/kout_tiles/tiles_final_all.pt']
DEFAULT_CROP = False
#: Learned from the person's 1,281 mask reviews (tools.decision_learning, 2026-09-29): accepts ~64 % of masks at 95 %
#: precision on held-out plants and never rejects; the rest stays a human review task.
DEFAULT_MASK_MODEL = 'build/decision_models_20260930/mask_review.joblib'  # 10-01: features from SAM v5 held-out drafts, no human-choice leak (LOPO 59 % auto at 96.3 % precision)
DEFAULT_SAM = 'build/leaflets5_20260929/sam2_config_v5_4plants.json'  # v5 (09-29): 1,163 masks, held-out IoU median 0.898-0.913 (v4 0.890-0.907)
HEIF_RUNTIME = ROOT / 'build' / 'leaf_light_image_runtime'
#: prelabel class -> the Roboflow class names the editor and S3 use
CLASS_MAP = {'compound_leaf': 'compoundleaves', 'leaflet': 'leaflet', 'sub_stem': 'sub-stem', 'main_stem': 'main-stem',
             'growth_shoot': 'growth-shoot'}
LABELS_SCHEMA = 'plant-auto-labels-1'


def _heif():
    try:
        import pillow_heif  # noqa: F401
    except ImportError:
        sys.path.insert(0, str(HEIF_RUNTIME))
        import pillow_heif
    pillow_heif.register_heif_opener()


def capture_time(path: Path) -> str:
    """EXIF DateTimeOriginal (or DateTime); '' when absent, which fails the ordering check later."""
    with Image.open(path) as im:
        ex = im.getexif()
        return str(ex.get_ifd(0x8769).get(36867) or ex.get(306) or '')


def order_photos(folder: Path) -> list[dict]:
    _heif()
    files = sorted(p for p in Path(folder).iterdir() if p.suffix.lower() in IMAGE_EXT)
    rows = [dict(path=p, time=capture_time(p)) for p in files]
    missing = [r['path'].name for r in rows if not r['time']]
    if missing:
        raise StudyError(f'No EXIF capture time, so the shooting order is unknown: {missing}')
    if len(rows) != len(PROTOCOL):
        raise StudyError(f'{len(rows)} photographs in {folder}; the protocol takes {len(PROTOCOL)} in a fixed order '
                         f'({", ".join(PROTOCOL)}). Remove extras or retake the missing ones.')
    rows.sort(key=lambda r: (r['time'], r['path'].name))
    times = [r['time'] for r in rows]
    if len(set(times)) != len(times):
        raise StudyError('Two photographs share a capture time; the order cannot be decided from EXIF')
    for r, code in zip(rows, PROTOCOL):
        r['view_code'] = code
    return rows


def organise(rows: list[dict], plant: str, date: str, out: Path) -> tuple[Path, Path]:
    """Copy photos under out/photos/<plant>/<yymmdd>/ with protocol names and write the importer's mapping CSV."""
    yymmdd = date[2:].replace('-', '')
    folder = out / 'photos' / plant / yymmdd
    folder.mkdir(parents=True)
    table = []
    for i, r in enumerate(rows, 1):
        name = f'{plant}_{yymmdd}_{r["view_code"]}{r["path"].suffix.lower()}'
        shutil.copy2(r['path'], folder / name)
        table.append(dict(plant_id=plant, capture_date=date, input_index=i, view_code=r['view_code'],
                          view_type=VIEW_TYPE[r['view_code'][0]], source_filename=r['path'].name, source_path=str(r['path']),
                          organized_path=f'{plant}\\{yymmdd}\\{name}', embedded_timestamp=r['time'],
                          sha256=file_hash(folder / name), order_rule='EXIF capture time -> protocol order'))
    mapping = out / 'mapping.csv'
    with open(mapping, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=list(table[0]))
        w.writeheader(); w.writerows(table)
    return out / 'photos', mapping


def wrong_size_views(rows: list[dict], intrinsics: dict) -> dict:
    """Photos whose pixel size differs from the calibration (dwt_04 view 01 was portrait) are excluded with a reason."""
    size = [intrinsics['image_width_px'], intrinsics['image_height_px']]
    bad = {}
    for r in rows:
        with Image.open(r['path']) as im:
            if list(im.size) != size:
                bad[r['view_code']] = f'image size {im.size[0]}x{im.size[1]} differs from calibration {size[0]}x{size[1]}'
    return bad


def labels_from_prelabels(prelabel: dict, capture: dict, session: Path, out: Path, growth: Path | None,
                          seed: bool = True) -> dict:
    """Model drafts (original pixels) -> the labels folder S1/S2/S3 read: original_pixel_labels.coco.json,
    mapping_report.json (schema plant-auto-labels-1), input_hashes.json and seed_with_imports.backup.json.
    seed=False (remote offload, no Node.js there) skips the editor seed; the mask batch does not need it."""
    out.mkdir(parents=True)
    frames = {f['image_file']: f for f in capture['frames']}
    src = read_json(Path(prelabel['out']) / 'prelabels.coco.json')
    names = {c['id']: CLASS_MAP[c['name']] for c in src['categories']}
    cats = {n: i for i, n in enumerate(dict.fromkeys(names.values()), 1)}
    coco = dict(images=[], annotations=[], categories=[dict(id=i, name=n, source='model draft class') for n, i in cats.items()],
                info=dict(description='model drafts in original pixels (tools.plant_auto)', coordinates='original_pixel_edges',
                          labels='MODEL DRAFTS, not human annotations', label_source='auto', prelabel=src['info']))
    photos = []
    for im in src['images']:
        f = frames.get(im['file_name'])
        if f is None:
            raise StudyError(f'Prelabel image {im["file_name"]} is not a prepared frame')
        coco['images'].append(dict(id=im['id'], file_name=im['file_name'], width=im['width'], height=im['height'],
                                   extra=dict(name=im['file_name'], view_group=f.get('observed_view_group'),
                                              transform=dict(type='original_pixels', original_size_px=[im['width'], im['height']]))))
        photos.append(dict(prepared_frame=im['file_name'], view_code=f['view_code'], mapped=True, reason='',
                           labels=sum(a['image_id'] == im['id'] for a in src['annotations']),
                           pose_status=f.get('pose_status'), passes_pose_gate=f.get('passes_pose_gate'),
                           alignment=None, transform='original_pixels'))
    for a in src['annotations']:
        coco['annotations'].append(dict(a, category_id=cats[names[a['category_id']]],
                                        provenance=dict(source='model draft', score=a.get('score'),
                                                        segmentation_source=a.get('segmentation_source'))))
    coco_path = out / 'original_pixel_labels.coco.json'
    write_json(coco_path, coco)
    hashes = {str(session / 'capture.json'): file_hash(session / 'capture.json'), str(coco_path): file_hash(coco_path)}
    write_json(out / 'input_hashes.json', hashes)
    imported = None
    if seed:
        from tools.roboflow_session_import import seed_with_imports
        imported = seed_with_imports(session / 'seed.backup.json', coco_path, capture, growth, out / 'seed_with_imports.backup.json')
    report = dict(schema_version=LABELS_SCHEMA, plant_id=capture['plant_id'], session=str(session),
                  source_annotations=len(coco['annotations']), mapped_annotations=len(coco['annotations']),
                  unmapped_annotations=0, mapped_photos=len(coco['images']), unmapped_photos=0, photos=photos,
                  editor_import=imported, label_source='auto', prelabel=dict(out=prelabel['out'], per_class=prelabel.get('per_class')),
                  validated_metric=False, suitable_for_ppfd=False,
                  notice='Model drafts drawn on the original photographs, not human labels; a person may correct them later.')
    write_json(out / 'mapping_report.json', report)
    return report


def run(photos: Path, plant: str, out: Path, growth: Path | None = None, both: bool = False, date: str | None = None,
        models: list[str] | None = None, sam_config: str | None = None, xl: bool = False, groimp_core: Path | None = None,
        offload: str = 'local', resume: bool = False, mask_policy: str = 'model', tile_models: list[str] | None = None,
        mask_model: str | None = None, crop: bool | None = None, smoothing: str = 'none') -> dict:
    """tile_models / mask_model / crop override the defaults, e.g. held-out models for a fair validation on a known plant."""
    from tools import import_organized_capture as ioc, prepare_leaf_edit_session as ples, organ_prelabel
    from tools import leaflet_mask_batch as lmb, leaflet_segmenter as seg, plant_pipeline
    out = Path(out).resolve()  # the pipeline writes paths relative to the project root
    main_cfg = read_json(MAIN_CONFIG)
    intrinsics_path = ROOT / main_cfg['intrinsics']
    capture_dir = out / 'capture'
    session = capture_dir / 'edit_session'
    source = out / 'photos'
    if resume:
        # continue an interrupted run with the arguments it started with; finished phases are not redone
        log = read_json(out / 'auto_run.json')
        a = log['args']
        plant, date, both, xl, offload = a['plant'], a['date'], a['both'], a['xl'], a['offload']
        growth, groimp_core = (Path(a['growth']) if a['growth'] else None), (Path(a['groimp_core']) if a['groimp_core'] else None)
        models, sam_config = a['models'], a['sam_config']
        mask_policy = a.get('mask_policy', 'all')
        tile_models, mask_model, crop = a.get('tile_models'), a.get('mask_model'), a.get('crop')
        smoothing = a.get('smoothing', 'none')
        if not (session / 'capture.json').exists():
            raise StudyError('Resume needs a finished S0 (capture/edit_session); start a new run instead')
        log.pop('finished', None)
    else:
        if out.exists():
            raise StudyError(f'Output exists; choose a new folder or use --resume: {out}')
        rows = order_photos(Path(photos))
        date = date or datetime.strptime(rows[0]['time'][:10], '%Y:%m:%d').strftime('%Y-%m-%d')
        out.mkdir(parents=True)
        log = dict(plant=plant, date=date, photos=str(photos), started=datetime.now().isoformat(timespec='seconds'),
                   order=[dict(view_code=r['view_code'], source=r['path'].name, exif_time=r['time']) for r in rows],
                   args=dict(plant=plant, date=date, both=both, xl=xl, offload=offload, growth=str(growth) if growth else None,
                             groimp_core=str(groimp_core) if groimp_core else None, models=models, sam_config=sam_config,
                             mask_policy=mask_policy, tile_models=tile_models, mask_model=mask_model, crop=crop,
                             smoothing=smoothing))
        write_json(out / 'auto_run.json', log)
        # S0: organise, import with measured ChArUco poses, prepare the edit session
        source, mapping = organise(rows, plant, date, out)
        excluded = wrong_size_views(rows, read_json(intrinsics_path))
        ioc.import_capture(source, mapping, plant, intrinsics_path, capture_dir, None, HEIF_RUNTIME, None, None, excluded)
        empty = capture_dir / 'annotations.empty.json'
        write_json(empty, dict(schema_version='manual-leaf-preview-1', human_review='pending',
                               annotation_source='empty starting context for a photo-only auto session', leaflets=[],
                               two_d_only_candidates=[], physical_point_candidates=[], unresolved_observations=[]))
        ples.prepare(capture_dir / 'capture.json', empty, session)
        log['excluded_views'] = excluded
    capture = read_json(session / 'capture.json')
    log['poses_solved'] = [f['view_code'] for f in capture['frames'] if f.get('pose_status') == 'solved']
    # S0b (2026-10-01): extra board poses from ArUco marker corners in a copy of the session (tools.marker_pose_rescue);
    # S1/S2 keep working on the original session, S3 and later use the copy through the config key pose_session
    pose_session = out / 'pose_session' / 'edit_session'
    if not (out / 'pose_session' / 'rescue.json').exists():
        from tools.marker_pose_rescue import rescue_session
        if pose_session.exists():  # an interrupted copy
            shutil.rmtree(pose_session)
        try:
            r = rescue_session(session, pose_session, plant)
            log['pose_rescue'] = {k: r[k] for k in ('posed_before', 'posed_after', 'rescued')}
        except Exception as e:  # never blocks the run; the original poses still work
            log['pose_rescue'] = dict(error=f'{type(e).__name__}: {e}')
            shutil.rmtree(pose_session, ignore_errors=True)
    models_given = bool(models)  # explicitly given (older) models keep the plant-window crop they were run with
    models = [ROOT / m for m in (models or DEFAULT_MODELS)]
    tile_models = tile_models if tile_models is not None else ([] if models_given else None)
    crop = crop if crop is not None else (True if models_given else DEFAULT_CROP)
    mask_model_path = ROOT / (mask_model or DEFAULT_MASK_MODEL)
    sam = ROOT / (sam_config or DEFAULT_SAM)
    labels, batch_dir = out / 'labels', out / 'masks'
    log['offload'] = offload
    if offload in ('kaggle-gpu', 'kaggle-cpu'):
        # S1+S2 on Kaggle (Claude's column); the PC keeps poses, decisions and S3-S7
        from tools import offload_job
        job = out / 'offload_job'
        if not (job / 'job.json').exists():
            offload_job.pack({plant: session}, job, models, sam,
                             tile_detectors=[ROOT / m for m in (tile_models if tile_models is not None else DEFAULT_TILE_MODELS)],
                             crop=crop, smoothing=smoothing)
            result = offload_job.kaggle_run(job, gpu=offload == 'kaggle-gpu')
        else:  # resume: the job was sent; collect its output (again) instead of recomputing
            result = offload_job.kaggle_fetch(job)
        done = batch_dir / 'offload_import.json'
        log['masks'] = dict(offload_import=read_json(done) if done.exists() else offload_job.import_result(
            job, result, plant, session, labels, batch_dir, growth if growth and not both else None,
            mask_model_path if mask_policy == 'model' else None))
        pre = dict(out=str(result / plant / 'prelabel'), per_class=read_json(result / 'result.json')['plants'][plant]['prelabel']['per_class'])
    else:
        # S1: model drafts on every prepared photo
        images = [session / f['image_path'] for f in capture['frames']]
        tiles = [ROOT / m for m in (tile_models if tile_models is not None else DEFAULT_TILE_MODELS)]
        pre = organ_prelabel.run(models, images, out / 'prelabel', crop=crop, smoothing=smoothing,
                                 tile_models=tiles or None)
        labels_from_prelabels(pre, capture, session, labels, growth if growth and not both else None)
    log['prelabel'] = pre
    variants = {'no_growth': labels}
    if growth and both:
        labels_g = out / 'labels_growth'
        if not (labels_g / 'mapping_report.json').exists():
            labels_from_prelabels(pre, capture, session, labels_g, growth)
        variants = {'no_growth': labels, 'growth': labels_g}
    elif growth:
        variants = {'growth': labels}
    # S2: SAM masks for every leaflet box, accepted automatically (already done by the offload import)
    if offload == 'local':
        lmb.prepare(plant, labels, session, batch_dir)
        batch = lmb.Batch(batch_dir, seg.load_segmenter('sam2', sam))
        batch.start(False, False)
        while batch.worker.is_alive():
            batch.worker.join(10)
        if mask_policy == 'model':
            from tools.decision_learning import apply_mask_model
            decided = apply_mask_model(batch_dir, mask_model_path, plant)
        else:
            decided = batch.auto_accept()
        log['masks'] = dict(status=batch.status(), policy=mask_policy, auto_accept=decided)
    # S3-S7 (+XL) through the normal pipeline, once per growth variant
    log['runs'] = {}
    for name, lab in variants.items():
        cfg = {k: v for k, v in main_cfg.items() if k != 'plants'}
        cfg['plants'] = {plant: dict(photo_source=str(source), capture=str(capture_dir), labels=str(lab),
                                     pose_session=str(pose_session) if (pose_session / 'capture.json').exists() else None,
                                     growth=str(growth) if name == 'growth' else None, batch=str(batch_dir), decisions=[],
                                     direction_labels=None, editor_port=None, label_source='auto')}
        cfg['note'] = f'photo-only auto run ({name}); written by tools.plant_auto'
        cfg_path = out / f'plants_{name}.json'
        write_json(cfg_path, cfg)
        args = ['--plant', plant, '--config', str(cfg_path), '--out', str(out / f'pipeline_{name}')]
        if xl:
            args += ['--xl'] + (['--groimp-core', str(groimp_core)] if groimp_core else [])
        plant_pipeline.main(args)
        log['runs'][name] = str(out / f'pipeline_{name}')
    log['finished'] = datetime.now().isoformat(timespec='seconds')
    write_json(out / 'auto_run.json', log)
    return log


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--photos', type=Path, help='folder with the 18 photographs of one plant and date')
    ap.add_argument('--plant')
    ap.add_argument('--resume', type=Path, help='continue an interrupted run in this folder')
    ap.add_argument('--growth', type=Path, help='optional growth record JSON')
    ap.add_argument('--both', action='store_true', help='with --growth, also run without it for comparison')
    ap.add_argument('--date', help='capture date YYYY-MM-DD (default: EXIF date of the first photo)')
    ap.add_argument('--out', type=Path)
    ap.add_argument('--models', nargs='+', help=f'detector weights (default: {", ".join(DEFAULT_MODELS)})')
    ap.add_argument('--sam-config', help=f'segmenter config (default {DEFAULT_SAM})')
    ap.add_argument('--xl', action='store_true')
    ap.add_argument('--groimp-core', type=Path)
    ap.add_argument('--mask-policy', choices=['model', 'all'], default='model',
                    help='model: accept only masks the learned review model is confident about (rest -> person); all: accept every mask')
    ap.add_argument('--offload', choices=['local', 'kaggle-gpu', 'kaggle-cpu'], default='local',
                    help='where the model drafts and SAM masks run (Colab: Codex runs tools/offload_remote.py on the job)')
    ap.add_argument('--tile-models', nargs='*', help=f'tile detector weights (default: {", ".join(DEFAULT_TILE_MODELS)}); empty = none')
    ap.add_argument('--mask-model', help=f'learned mask review model (default {DEFAULT_MASK_MODEL})')
    ap.add_argument('--no-crop', action='store_true', help='run the detectors on the whole photo (v4 full models)')
    ap.add_argument('--detector-smoothing', default='none', help='tools.preprocess_study recipe for the detector input only (e.g. gauss5, mean3)')
    a = ap.parse_args()
    if a.resume:
        out = a.resume
        r = run(None, None, out, resume=True)
    else:
        if not (a.photos and a.plant):
            ap.error('--photos and --plant are required (or --resume <folder>)')
        out = a.out or ROOT / 'build' / f'auto_{a.plant}_{datetime.now().strftime("%Y%m%d_%H%M%S")}'
        r = run(a.photos, a.plant, out, a.growth, a.both, a.date, a.models, a.sam_config, a.xl, a.groimp_core, a.offload,
                mask_policy=a.mask_policy, tile_models=a.tile_models, mask_model=a.mask_model, crop=False if a.no_crop else None,
                smoothing=a.detector_smoothing)
    print(json.dumps(dict(out=str(out), runs=r['runs'], poses_solved=r['poses_solved'], masks=r['masks']),
                     ensure_ascii=False))


if __name__ == '__main__':
    main()
