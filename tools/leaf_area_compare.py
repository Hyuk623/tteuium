"""Compare saved leaf masks with versioned projected-area geometry, without inference.

python -m tools.leaf_area_compare --study build/study.json --out build/fresh_result
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path
from time import perf_counter

import numpy as np
from PIL import Image

from tools.leaf_area_geometry import IntegrationPolicy, METHOD, LEGACY, view_geometry, calibration_identity
from tools.leaf_light.common import StudyError, digest, file_hash, output_dir, read_json, write_json, write_rows
from tools.leaflet_mask_batch import Batch
from tools.plant_structure import Cameras
from tools import plant_traits as pt
from tools.leaf_mask_selection import load_selection


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return (base / path).resolve() if not path.is_absolute() else path.resolve()


class Inputs:
    """Hash consumed files and verify both declared identity and concurrent changes."""
    def __init__(self) -> None:
        self.hashes: dict[str, str] = {}

    def add(self, path: Path, expected: str | None = None) -> Path:
        path = path.resolve()
        value = file_hash(path)
        if (expected and value != expected) or (str(path) in self.hashes and self.hashes[str(path)] != value):
            raise StudyError(f'Source hash mismatch: {path}')
        self.hashes[str(path)] = value
        return path

    def verify(self) -> None:
        for name, expected in self.hashes.items():
            if file_hash(Path(name)) != expected:
                raise StudyError(f'Source changed during comparison: {name}')


def preview(image_path: Path, masks: list, out: Path, max_px: int) -> None:
    """Render existing evidence only; never generate or change a mask."""
    with Image.open(image_path) as source:
        im = source.convert('RGB')
    union = np.zeros((im.height, im.width), bool)
    for (x0, y0, x1, y1), mask, _ in masks:
        if mask.shape != (y1-y0, x1-x0) or not (0 <= x0 < x1 <= im.width and 0 <= y0 < y1 <= im.height):
            raise StudyError('Preview mask/crop mismatch')
        union[y0:y1, x0:x1] |= mask
    im.thumbnail((max_px, max_px))
    im.save(out.with_suffix('.jpg'))
    overlay = Image.fromarray((union * 100).astype(np.uint8)).resize(im.size, Image.Resampling.NEAREST)
    green = Image.new('RGB', im.size, (30, 230, 100))
    Image.composite(green, im, overlay).save(out.with_name(out.name + '_mask').with_suffix('.jpg'))


def compare_case(case: dict, base: Path, folder: Path, policy: dict, inputs: Inputs, max_px: int) -> dict:
    start = perf_counter()
    capture_path = inputs.add(resolve(base, case['capture']))
    structure_path = inputs.add(resolve(base, case['structure']))
    capture, structure = read_json(capture_path), read_json(structure_path)
    for document in (capture, structure):
        if document.get('plant_id') != case['plant_id'] or document.get('session_id') != case['session_id']:
            raise StudyError('Case plant/session does not match capture and structure')
    dependencies = structure.get('inputs', {})
    if not dependencies.get('capture') or not dependencies.get('capture_sha256'):
        raise StudyError('Structure must identify and hash its capture poses')
    declared_capture = inputs.add(resolve(structure_path.parent, dependencies['capture']), dependencies['capture_sha256'])
    if inputs.hashes[str(declared_capture)] != inputs.hashes[str(capture_path)]:
        raise StudyError('Hull and selected camera poses have different provenance')
    for name in ('backup', 'growth', 'name_decisions'):
        if dependencies.get(name):
            inputs.add(resolve(structure_path.parent, dependencies[name]), dependencies.get(name+'_sha256'))
    dates = {pt.record_date(capture)} - {''}
    if dependencies.get('growth'):
        growth = read_json(resolve(structure_path.parent, dependencies['growth']))
        if growth.get('plant_id') and growth['plant_id'] != case['plant_id']:
            raise StudyError('Foreign growth record')
        dates |= {pt.record_date(growth)} - {''}
    if len(dates) > 1:
        raise StudyError('Conflicting capture dates in supplied source records')
    if capture.get('coordinate_frame') not in ('board', 'board_mm',
            'board; origin inner corner 0; +Z away from the board surface; millimetres'):
        raise StudyError('Explicit supported board coordinate frame required')
    if not case.get('capture_style'):
        raise StudyError('Explicit capture_style required')
    for path_key, hash_key in [('intrinsics_path', 'intrinsics_sha256'), ('board_spec_path', 'board_spec_sha256')]:
        if capture.get(path_key):
            inputs.add(resolve(capture_path.parent, capture[path_key]), capture.get(hash_key))
    batch_path = resolve(base, case['batch'])
    inputs.add(batch_path / 'manifest.json')
    batch = Batch(batch_path)
    if batch.manifest.get('plant_id') != case['plant_id'] or batch.manifest.get('organ_class') != 'leaflet':
        raise StudyError('Foreign plant or non-leaflet mask batch')
    original_capture_path = inputs.add(batch.session / 'capture.json')
    original_capture = read_json(original_capture_path)
    if original_capture.get('plant_id') != case['plant_id'] or original_capture.get('session_id') != case['session_id']:
        raise StudyError('Mask batch capture identity mismatch')
    selection = load_selection(resolve(base, case['mask_selection']) if case.get('mask_selection') else None,
                               batch, original_capture, inputs.add)
    original_frames = {f['image_file'].lower(): f for f in original_capture['frames']}
    for name, expected in batch.manifest.get('input_hashes', {}).items():
        inputs.add(resolve(batch_path, name), expected)
    cams = Cameras(capture)
    hull_path = inputs.add(structure_path.parent / 'hull_voxels.csv')
    hull_mm = np.loadtxt(hull_path, delimiter=',', skiprows=1, usecols=(0, 1, 2), ndmin=2)
    masks: dict[str, list] = defaultdict(list)
    decisions: list[dict] = []
    for identity in batch.manifest['ids']:
        inputs.add(batch_path / 'items' / f'{identity}.json')
        item = batch.item(identity)
        key = item['image_file'].lower()
        if key not in original_frames:
            raise StudyError('Mask references unknown source image')
        decisions.append({k: item.get(k) for k in ('id', 'image_file', 'generation', 'review', 'revision')})
        decisions[-1]['exclusion_reason'] = selection['excluded'].get(identity)
        if identity in selection['excluded']:
            continue
        if item['generation'] != 'ready' or item['review'] == 'rejected':
            continue
        cache = batch_path / 'cache' / item['cache_key']
        metadata = read_json(inputs.add(cache / 'result.json'))
        if metadata.get('image_sha256') != original_frames[key].get('sha256'):
            raise StudyError('Mask cache belongs to a different image')
        inputs.add(cache / 'logits.npz', metadata.get('logits_sha256'))
        mask, metadata = batch.mask(item)
        masks[key].append((metadata['crop_px'], mask, item['review'] in ('accepted', 'accepted_by_user')))
    folder.mkdir()
    write_json(folder / 'capture.snapshot.json', capture)
    write_json(folder / 'structure.snapshot.json', structure)
    write_json(folder / 'case.snapshot.json', case)
    write_rows(folder / 'mask_decisions.csv', decisions, ('id', 'image_file', 'generation', 'review', 'revision', 'exclusion_reason'))
    photos = []
    excluded = {r['photo'].lower():r['reason'] for r in structure.get('views_skipped',[])}
    for index, (key, frame) in enumerate(cams.frames.items()):
        row = dict(image_file=key, view_code=frame.get('view_code'), pose_status=frame.get('pose_status'),
                   passes_pose_gate=frame.get('passes_pose_gate'), reprojection_error_px=frame.get('reprojection_error_px'),
                   **view_geometry(cams, key, case.get('view_grouping')))
        row.update(hull_view_used=key in [v.lower() for v in structure.get('views_used',[])],
                   hull_exclusion_reason=excluded.get(key))
        source_frame = original_frames.get(key)
        if source_frame is None or frame.get('sha256') != source_frame.get('sha256'):
            raise StudyError('Posed image differs from mask source image')
        image_path = inputs.add(resolve(capture_path.parent, frame['image_path']), frame.get('sha256'))
        with Image.open(image_path) as im:
            if im.size != cams.size:
                raise StudyError('Actual image dimensions differ from camera calibration')
        row['source_image'] = os.path.relpath(image_path, folder).replace('\\', '/')
        if not cams.posed(key):
            row['status'] = 'pose_unavailable'
        elif key in excluded:
            row['status'] = 'excluded_by_structure'
        elif not masks.get(key):
            row['status'] = 'no_masks'
        else:
            result = pt.photo_area(cams, key, hull_mm, masks[key], area_policy=policy)
            row.update(status=result['area_v2']['status'], legacy_projected_area_cm2=result['leaf_area_cm2'],
                       legacy_accepted_area_cm2=result['accepted_leaf_area_cm2'], **{k: v for k, v in result['area_v2'].items() if k != 'status'})
        name = f'photo_{index:03d}'
        preview(image_path, masks.get(key, []), folder / name, max_px)
        row.update(preview=name+'.jpg', mask_preview=name+'_mask.jpg')
        photos.append(row)
    groups = []
    for group in sorted({p['group'] for p in photos}):
        rr = [p for p in photos if p['group'] == group]
        complete = all(p.get('projected_area_cm2') is not None for p in rr)
        old = [p.get('legacy_projected_area_cm2') for p in rr]
        groups.append(dict(group=group, photos=len(rr), complete_photos=sum(p.get('projected_area_cm2') is not None for p in rr),
                           legacy_mean_cm2=float(np.mean(old)) if all(v is not None for v in old) else None,
                           corrected_mean_cm2=float(np.mean([p['projected_area_cm2'] for p in rr])) if complete and group != 'unavailable' else None))
    result = dict(schema='leaf-area-comparison-case-1', case_id=case['case_id'], plant_id=case['plant_id'], session_id=case['session_id'],
                  mask_selection=selection, mask_selection_hash=selection['policy_hash'],
                  capture_date=next(iter(dates),None), capture_style=case['capture_style'],
                  area_method=METHOD, baseline_method=LEGACY, photos=photos, groups=groups,
                  calibration_hash=calibration_identity(cams.K,cams.D,cams.size),
                  integration_policy_hash=digest(policy),grouping_policy_hash=digest(case.get('view_grouping')),
                  movement=case.get('movement', {'status': 'unavailable'}),
                  new_motion_detection_performed=False, registration_performed=False,
                  total_tissue_area_cm2=None, supported_surface_area_cm2=None,
                  calibrated_whole_plant_area_cm2=None, physical_validation=False,
                  capture_quality=capture.get('quality'), board_evidence=capture.get('board_variant_evidence'),
                  surface_status='no_reviewed_surface_input', elapsed_seconds=perf_counter()-start)
    write_json(folder / 'comparison.json', result)
    fields = ('image_file', 'view_code', 'group', 'elevation_deg', 'status', 'pose_status', 'passes_pose_gate',
              'legacy_projected_area_cm2', 'projected_area_cm2', 'supported_projected_area_cm2', 'original_union_px', 'used_union_px', 'missing_union_px')
    write_rows(folder / 'photos.csv', [{k:r.get(k) for k in fields} for r in photos], fields)
    write_rows(folder / 'groups.csv', groups, tuple(groups[0]) if groups else ('group',))
    return result


def summarize_cases(cases: list[dict], folder: Path, measurements: Path, inputs: Inputs) -> list[dict]:
    """Refit only compatible corrected proxies; never import a historical k."""
    for name in ('leaf_area.csv','light.csv'):
        if (measurements/name).exists():
            inputs.add(measurements/name)
    grouped: dict[str,list] = defaultdict(list)
    for case in cases:
        by_group={r['group']:r for r in case['groups']}
        ring,top=by_group.get('ring',{}),by_group.get('top',{})
        trait={k:case[k] for k in ('plant_id','session_id','capture_date','area_method','capture_style',
                                 'calibration_hash','grouping_policy_hash','integration_policy_hash','mask_selection_hash')}
        trait.update(leaf_area_proxy_cm2=ring.get('corrected_mean_cm2'),leaf_area_proxy_photos=ring.get('photos',0),
                     top_leaf_area_cm2=top.get('corrected_mean_cm2'))
        grouped[digest(pt.area_calibration_contract(trait))].append((case,trait))
    summaries=[]
    for index,(contract,items) in enumerate(grouped.items()):
        summary=pt.summarize([t for _,t in items],folder/f'calibration_{index:03d}',measurements)
        by_key={pt.observation_key(r):r for r in summary['rows']}
        for case,trait in items:
            row=by_key[pt.observation_key(trait)]
            case['calibrated_whole_plant_area_cm2']=row['estimated_leaf_area_cm2']
            case['calibration_status']=summary['calibration']['status']
            case['calibration_contract_hash']=contract
            write_json(folder/case['case_id']/'comparison.json',case)
            write_json(folder/case['case_id']/'corrected_traits.json',trait)
        summaries.append(summary)
    return summaries


def run(study_path: Path, out: Path) -> dict:
    inputs = Inputs()
    for name in ('leaf_area_compare.py', 'leaf_area_compare.html', 'leaf_area_geometry.py', 'plant_traits.py',
                 'plant_structure.py', 'leaflet_mask_batch.py', 'leaf_mask_selection.py'):
        inputs.add(Path(__file__).with_name(name))
    study = read_json(inputs.add(study_path))
    if study.get('schema') != 'leaf-area-comparison-1':
        raise StudyError('Unsupported comparison study')
    IntegrationPolicy.parse(study['integration'])
    max_px = study.get('preview_max_px')
    if type(max_px) is not int or max_px <= 0:
        raise StudyError('Explicit positive preview_max_px required')
    ids = [c['case_id'] for c in study['cases']]
    if not ids or len(set(ids)) != len(ids) or any(not isinstance(i, str) or not i or not all(c.isalnum() or c in '_-' for c in i) for i in ids):
        raise StudyError('Unique safe case IDs required')
    folder = output_dir(out)
    write_json(folder / 'study.snapshot.json', study)
    cases = []
    for case in study['cases']:
        cases.append(compare_case(case, study_path.resolve().parent, folder / case['case_id'], study['integration'], inputs, max_px))
        print(json.dumps(dict(case=case['case_id'], photos=len(cases[-1]['photos']), seconds=cases[-1]['elapsed_seconds'])), flush=True)
    measurements=resolve(study_path.resolve().parent,study['measurements']) if study.get('measurements') else pt.ROOT/pt.MEASUREMENTS
    summaries=summarize_cases(cases,folder,measurements,inputs)
    inputs.verify()
    report = dict(schema='leaf-area-comparison-1', status='comparison_complete', physical_validation=False,
                  cases=cases, calibration_summaries=summaries, source_hashes=inputs.hashes, source_hashes_verified=True,
                  integration=study['integration'], integration_policy_hash=digest(study['integration']))
    write_json(folder / 'audit.json', report)
    template = Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    payload = json.dumps(report, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c')
    (folder / 'viewer.html').write_text(template.replace('__AREA_DATA__', payload), encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = run(args.study, args.out)
    print(json.dumps(dict(status=result['status'], cases=len(result['cases']), physical_validation=False)))


if __name__ == '__main__':
    main()
