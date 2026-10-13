"""Frozen dataset manifest for the mask-learning -> multiview experiment (user prompt 2026-09-30).

    python -X utf8 -m tools.split_experiment --out build/split_exp_<date>

Roles are declared here, in an isolated experiment manifest; tools/plant_pipeline_plants.json and the instance
workflow's dwt_01 development / dwt_02 frozen evaluation roles are not rewritten:

    train       dwt_03, dwt_04   (every photo, date, view and crop of these plants)
    development dwt_01           (thresholds and method choices only)
    evaluation  dwt_02           (never trained on: no supervised, pseudo-label, normalisation or matching fit)

The manifest freezes, per plant: the newest accepted export (path + sha256 of accepted.json and of every mask PNG),
the Roboflow organ labels (sha256), every photo (sha256, size), the per-class / per-visibility counts, the rejected
drafts with reasons (error evidence, never corrected masks), and the cross-view answers. It also records the lineage of
the existing checkpoints, so a reused model is never scored on data it was trained on without saying so.
"""
from __future__ import annotations

import argparse
import glob
from collections import Counter
from pathlib import Path

from PIL import Image

from tools.leaf_light.common import StudyError, file_hash, read_json, write_json

ROOT = Path(__file__).resolve().parents[1]
CONFIG = Path(__file__).with_name('plant_pipeline_plants.json')
ROLES = {'dwt_03': 'train', 'dwt_04': 'train', 'dwt_01': 'development', 'dwt_02': 'evaluation'}
CLASSES = ('compoundleaves', 'leaflet', 'main-stem', 'sub-stem', 'growth-shoot')

#: What each existing checkpoint was trained on (from its kernel code and results files). A model whose training set
#: contains an experiment's development or evaluation plant is NOT a valid baseline for this split.
LINEAGE = {
    'organ_v4 full/tiles final_all': dict(trained_on=['dwt_01', 'dwt_02', 'dwt_03', 'dwt_04'],
                                          files=['build/organ_detector_v4_20260929/kout_full/full_final_all.pt',
                                                 'build/organ_detector_v4_20260929/kout_tiles/tiles_final_all.pt']),
    'organ_v4 lopo_dwt_02': dict(trained_on=['dwt_01', 'dwt_03', 'dwt_04'],
                                 files=['build/organ_detector_v4_20260929/kout_full/full_lopo_dwt_02.pt']),
    'sam_v5 4plants / heldout_*': dict(trained_on='all four (final) or three of four (held-out folds)',
                                       files=['build/leaflets5_20260929/kout_sam/']),
    'obb_v5 4plants / heldout_*': dict(trained_on='all four (final) or three of four (held-out folds)',
                                       files=['build/leaflets5_20260929/kout_obb/']),
    'decision models 20260929': dict(trained_on=['dwt_01', 'dwt_02', 'dwt_03', 'dwt_04'],
                                     files=['build/decision_models_20260929/']),
    'SAM 2.1 hiera tiny (public, unchanged)': dict(trained_on=[], note='SA-V / SA-1B (Meta); no tomato data',
                                                  files=['build/sam_trial_20260919/checkpoints/sam2.1_hiera_tiny.pt']),
    'YOLO11s-seg (public COCO, start point)': dict(trained_on=[], note='COCO; no tomato classes, so no unchanged-detector baseline exists',
                                                   files=['yolo11s-seg.pt (ultralytics release)']),
}
DISCLOSURE = ('dwt_02 is not an untouched test plant: its masks, rejections and cross-view answers were inspected '
              'while earlier methods were chosen (09-22..09-30: decision-learning LOPO reports, conflict review, '
              'organ/SAM/OBB LOPO folds). Results on it are a held-out-plant check, not a final untouched test; '
              'that claim needs a new plant cohort.')


def valid_for_split(trained_on) -> bool:
    return isinstance(trained_on, list) and not ({'dwt_01', 'dwt_02'} & set(trained_on))


def freeze(out: Path, config: Path = CONFIG) -> dict:
    out = Path(out)
    if out.exists():
        raise StudyError(f'Output exists: {out}')
    cfg = read_json(config)
    plants = {}
    for plant, role in ROLES.items():
        pc = cfg['plants'][plant]
        session = ROOT / pc['capture'] / 'edit_session'
        frames = read_json(session / 'capture.json')['frames']
        photos = {}
        for f in frames:
            p = session / f['image_path']
            with Image.open(p) as im:
                photos[f['image_file']] = dict(sha256=file_hash(p), size=list(im.size), pose_status=f.get('pose_status'))
        exp = sorted((ROOT / pc['batch'] / 'exports').glob('accepted_*'))[-1]
        acc = read_json(exp / 'accepted.json')
        obs = [o for o in acc['observations'] if o['review'] == 'accepted_by_user']
        sizes = {tuple(o['image_size_px']) for o in obs}
        wrong = [o['id'] for o in obs if list(o['image_size_px']) != photos.get(o['image_file'], {}).get('size')]
        if wrong:
            raise StudyError(f'{plant}: mask size differs from its photo for {wrong[:5]}')
        items = [read_json(f) for f in sorted((ROOT / pc['batch'] / 'items').glob('*.json'))]
        labels = ROOT / pc['labels'] / 'seed_with_imports.backup.json'
        dets = read_json(labels)['variants']['__all__']['membership']['detections']
        decisions = [str(ROOT / d) for d in pc.get('decisions', [])] + sorted(glob.glob(str(Path(cfg['downloads']) / f'cross_view_decisions_{plant}_*.json')))
        plants[plant] = dict(
            role=role, capture=pc['capture'], photos=photos,
            accepted_export=dict(path=str(exp.relative_to(ROOT)).replace('\\', '/'), accepted_sha256=file_hash(exp / 'accepted.json'),
                                 masks={o['id']: dict(file=o['mask_file'], sha256=file_hash(exp / o['mask_file']), image_file=o['image_file'],
                                                      edited=bool(o.get('changed')), visibility=o.get('visibility') or 'unspecified')
                                        for o in obs},
                                 image_sizes=sorted(list(s) for s in sizes)),
            counts=dict(accepted=len(obs), edited=sum(bool(o.get('changed')) for o in obs),
                        visibility=dict(Counter(o.get('visibility') or 'unspecified' for o in obs)),
                        organ_labels=dict(Counter(x['class_name'] for v in dets.values() for x in v))),
            rejected=[dict(id=i['id'], image_file=i['image_file'], reason=i.get('reject_reason')) for i in items if i['review'] == 'rejected'],
            organ_labels=dict(path=str(labels.relative_to(ROOT)).replace('\\', '/'), sha256=file_hash(labels),
                              note='compoundleaves and leaflet entries are boxes (bbox annotations, not boundaries); '
                                   'main-stem/sub-stem/growth-shoot entries are drawn outlines of the visible part'),
            decisions=[dict(path=d, sha256=file_hash(Path(d))) for d in decisions if Path(d).is_file()] +
                      [dict(path=d, kind='folder') for d in decisions if Path(d).is_dir()])
    doc = dict(schema='split-experiment-1', roles=ROLES, classes=list(CLASSES), plants=plants,
               lineage={k: dict(v, valid_baseline_for_this_split=valid_for_split(v['trained_on'])) for k, v in LINEAGE.items()},
               disclosure=DISCLOSURE, human_rules=[
                   'accepted_by_user masks are the leaflet references; review history is kept as exported',
                   'review_source auto / auto_model answers are never references or targets',
                   'rejected drafts are error evidence, not corrected masks; a missed box does not make its region background',
                   'unlabelled or uncertain regions are not negatives for the matching model',
                   'dwt_02 is excluded from every fit, including pseudo-labels, normalisation and matching'],
               unlabeled_photos=dict(available=0, note='all 72 photos (4 plants x 18) carry human labels; the semi-supervised '
                                                        'experiment stays prepared-but-pending until eligible unlabeled training photos exist'),
               validated_metric=False, suitable_for_ppfd=False)
    out.mkdir(parents=True)
    write_json(out / 'manifest.json', doc)
    return doc


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--out', required=True, type=Path)
    d = freeze(ap.parse_args().out)
    for p, v in d['plants'].items():
        print(p, v['role'], v['counts'], 'rejected', len(v['rejected']), 'decision sources', len(v['decisions']))
    print({k: v['valid_baseline_for_this_split'] for k, v in d['lineage'].items()})


if __name__ == '__main__':
    main()
