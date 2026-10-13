"""Document 06 only: read-only cached comparisons and diagnostic mask evidence.

python -m tools.instance_workflow --operation sensitivity_sweep --session ...
  --backup ... --context ... --batch ... --out build/new_run [--reference reviewed.json]
No model inference or training is performed. Missing human evidence stays missing.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from copy import deepcopy
from datetime import datetime, timezone
import json
import hashlib
from pathlib import Path
import time

import numpy as np
from PIL import Image

from tools.leaf_light import common as io
from tools.leaflet_mask_batch import Batch, render_rings, threshold
from tools.rebuild_leaf_edit_session import checked_inputs, current_state
from tools.instance_evidence import fuse, mask_metrics

DEFAULTS = Path(__file__).with_name('instance_workflow_defaults.json')
OPERATIONS = ('sensitivity_sweep', 'instance_fusion')
FUSION_PLANTS = ('dwt_01', 'dwt_02', 'dwt_03', 'dwt_04')


def check_operation_scope(operation: str, plant: str) -> None:
    allowed = FUSION_PLANTS if operation == 'instance_fusion' else ('dwt_01', 'dwt_02')
    if plant not in allowed:
        raise io.StudyError(f'{operation} scope is {", ".join(allowed)}; evaluation protocol is unchanged')


def checked_import_sources(batch: Batch, capture: dict) -> tuple[dict, dict]:
    """Refresh only a declared review reference in a new run; never rewrite an import.

    Growth counts are not used by fusion. The original import's explicit role and
    matching seed/COCO linkage distinguish them from arbitrary changed JSON files.
    """
    recorded = batch.manifest.get('input_hashes', {})
    resolved = {Path(p).resolve(): sha for p, sha in recorded.items()}
    coco = Path(batch.manifest['source_coco']).resolve()
    seed_path = coco.parent/'seed_with_imports.backup.json'
    audit = dict(schema_version='instance-import-freshness-1', refreshed_references=[],
                 policy='declared growth reference only; never a geometry input')
    growth_path = None
    provenance_hashes = {}
    if seed_path.is_file():
        raw = seed_path.read_bytes()
        imported = json.loads(raw.decode('utf-8-sig'))
        derivation = imported.get('seed_derivation') or {}
        if derivation.get('tool') == 'tools.roboflow_session_import' and derivation.get('growth_reference'):
            base_seed = (batch.session/'seed.backup.json').resolve()
            if (imported.get('plant_id') != capture['plant_id'] or
                imported.get('session_id') != capture['session_id'] or
                Path(derivation.get('coco', '')).resolve() != coco or
                derivation.get('coco_sha256') != batch.manifest['source_coco_sha256'] or
                Path(derivation.get('base_seed', '')).resolve() != base_seed or
                derivation.get('base_seed_sha256') != resolved.get(base_seed)):
                raise io.StudyError('Growth reference import linkage mismatch; review the imported seed')
            growth_path = Path(derivation['growth_reference']).resolve()
            if growth_path not in resolved or growth_path == coco or growth_path == base_seed:
                raise io.StudyError('Growth reference is not a separately recorded import input')
            provenance_hashes[str(seed_path)] = hashlib.sha256(raw).hexdigest()
    current = {}
    blocked = []
    for name, expected in recorded.items():
        path = Path(name).resolve()
        if not path.is_file():
            blocked.append(f'missing input: {path}')
            continue
        if path == growth_path:
            raw = path.read_bytes()
            actual = hashlib.sha256(raw).hexdigest()
            try:
                growth = json.loads(raw.decode('utf-8-sig'))
                date = datetime.strptime(growth['capture_date'], '%Y-%m-%d').strftime('%Y%m%d')
                valid = (growth['plant_id'] == capture['plant_id'] and
                         capture['session_id'] == f"{capture['plant_id']}_{date}" and
                         isinstance(growth.get('compound_leaves'), list))
            except (KeyError, TypeError, ValueError, UnicodeError):
                valid = False
            if not valid:
                raise io.StudyError(f'Growth reference plant/date or record structure mismatch: {path}')
            # Snapshot current metadata separately; the editor backup remains untouched.
            audit['growth_reference'] = dict(path=str(path), import_sha256=expected,
                current_sha256=actual, record=growth, used_for_geometry=False)
            if actual != expected:
                audit['refreshed_references'].append(dict(path=str(path), old_sha256=expected,
                    new_sha256=actual, reason='review_only_growth_metadata_changed'))
        else:
            actual = io.file_hash(path)
            if actual != expected:
                blocked.append(f'protected import input changed: {path}')
        current[str(path)] = actual
    if blocked:
        raise io.StudyError('Prepared import validation failed; revalidate affected inputs before reimport: ' + '; '.join(blocked))
    current.update(provenance_hashes)
    return current, audit


def verify_snapshot_sources(hashes: dict) -> None:
    changed = [p for p, sha in hashes.items() if not Path(p).is_file() or io.file_hash(Path(p)) != sha]
    if changed:
        raise io.StudyError('Inputs changed during snapshot: ' + '; '.join(changed))


def backup_digest(backup: dict) -> str:
    return io.digest({k: backup.get(k) for k in ('plant_id', 'session_id', 'capture', 'variants')})


def check_research_path(path: Path) -> None:
    # Neither of the old UI fixture directories, nor any future fixture, is research data.
    if any('fixture' in part.lower() for part in path.resolve().parts):
        raise io.StudyError('UI fixtures are excluded from research runs')


def identity_for(item: dict, backup: dict) -> dict:
    """Join using source observation identity, not box overlap or compound counts."""
    state, photo = current_state(backup), Path(item['image_file']).name.lower()
    candidates = []
    for key, leaf in state.get('leaflets', {}).items():
        for image_key, box in leaf.get('bboxes', {}).items():
            if Path(image_key).name.lower() != photo:
                continue
            source = box.get('source_detection') or {}
            if str(source.get('source_annotation_id')) != str(item['source_annotation_id']):
                continue
            status = leaf.get('view_status', {}).get(image_key, {})
            candidates.append(dict(leaf_key=key, leaflet_id=key, editor_leaflet_id_raw=leaf.get('leaflet_id'),
                identity_namespace='existing_editor_leaf_key',
                compound_leaf_id=leaf.get('organ_id') if leaf.get('membership_review', {}).get('state') == 'confirmed' else None,
                identity_review=status.get('identity_review', 'unconfirmed'),
                visibility=status.get('visibility', 'unknown'), annotation_box=box))
    if len(candidates) == 1:
        return candidates[0]
    return dict(leaf_key=None, leaflet_id=None, compound_leaf_id=None,
                identity_review='unconfirmed', visibility='unknown',
                identity_conflict=len(candidates) > 1, candidate_leaf_keys=[c['leaf_key'] for c in candidates])


def input_signature(batch: Batch, backup: dict, ids: list[str]) -> dict:
    return dict(backup=backup_digest(backup), manifest=io.file_hash(batch.root/'manifest.json'),
                items={i: io.file_hash(batch.root/'items'/f'{i}.json') for i in ids})


def stale_reasons(run: Path, batch: Batch, backup: dict) -> list[str]:
    manifest = io.read_json(run/'manifest.json')
    before = manifest['input_signature']
    after = input_signature(batch, backup, list(before['items']))
    reasons = [k for k in before if before[k] != after[k]]
    for path, expected in manifest.get('source_hashes', {}).items():
        if not Path(path).is_file() or io.file_hash(Path(path)) != expected:
            reasons.append('source_changed:'+Path(path).name)
    return reasons


def table(out: Path, name: str, rows: list[dict], fallback: tuple = ('status',)) -> None:
    columns = sorted({k for r in rows for k in r}) or list(fallback)
    values = [{k: (json.dumps(r.get(k), ensure_ascii=False) if isinstance(r.get(k), (dict, list)) else r.get(k))
               for k in columns} for r in rows]
    io.write_rows(out/name, values, columns)


def reference_template(capture: dict, observations: list[dict]) -> dict:
    photos = sorted({o['image_file'] for o in observations})
    return dict(schema_version='instance-visible-reference-1', version='', reviewer='',
                independent_manual_review=False, plant_id=capture['plant_id'], session_id=capture['session_id'],
                note='Draw/review visible masks independently; neither rectangles nor predictions become ground truth automatically.',
                photos=[dict(image_file=p, image_sha256=next(o['image_sha256'] for o in observations if o['image_file'] == p),
                    coverage='unreviewed', ignore_rings=[], instances=[]) for p in photos],
                instance_example=dict(reference_id='unique_in_photo', visibility='full_or_partial',
                    origin='independent_manual', rings=[dict(is_hole=False, points_px=[]) ]))


def validate_reference(reference: dict | None, capture: dict) -> dict:
    if reference is None:
        return {}
    if (reference.get('schema_version') != 'instance-visible-reference-1' or
        reference.get('plant_id') != capture['plant_id'] or reference.get('session_id') != capture['session_id'] or
        not reference.get('version') or not reference.get('reviewer') or reference.get('independent_manual_review') is not True):
        raise io.StudyError('Reference requires a version, reviewer and independent manual review for this plant/session')
    frames = {f['image_file']: f for f in capture['frames']}
    result = {}
    for photo in reference.get('photos', []):
        name = photo.get('image_file')
        if name not in frames or name in result or photo.get('image_sha256') != frames[name]['sha256']:
            raise io.StudyError('Reference photo identity/hash mismatch or duplicate')
        if photo.get('coverage') not in ('complete_visible', 'incomplete', 'unreviewed'):
            raise io.StudyError('Reference coverage is required')
        ids = set()
        for instance in photo.get('instances', []):
            if (instance.get('origin') != 'independent_manual' or not instance.get('reference_id') or
                instance['reference_id'] in ids or instance.get('visibility') not in ('full', 'partial')):
                raise io.StudyError('Reference instance provenance, visibility or ID is invalid')
            ids.add(instance['reference_id'])
        result[name] = photo
    return result


def freeze_parameters(development_run: Path, destination: Path) -> dict:
    manifest = io.read_json(development_run/'manifest.json')
    result = io.read_json(development_run/'result.json')
    if manifest['plant_id'] != 'dwt_01' or result.get('operation') != 'sensitivity_sweep':
        raise io.StudyError('Freeze requires a completed dwt_01 sensitivity development run')
    if destination.exists():
        raise io.StudyError('Freeze destination already exists; write a new version')
    frozen = dict(schema_version='instance-parameters-frozen-1', development_plant='dwt_01', evaluation_plant='dwt_02',
                  frozen_at=datetime.now(timezone.utc).isoformat(), settings=manifest['settings'],
                  settings_sha256=io.digest(manifest['settings']), development_run_sha256=io.file_hash(development_run/'manifest.json'),
                  validation='exploratory_unvalidated' if not result.get('evaluated_photos') else 'development_comparison_only')
    destination = destination.resolve()
    if not destination.is_relative_to(io.BUILD.resolve()) or destination.parent == io.BUILD.resolve():
        raise io.StudyError('Freeze must stay in a dedicated build directory')
    destination.parent.mkdir(parents=True, exist_ok=True)
    io.write_json(destination, frozen)
    return frozen


def snapshot(batch: Batch, backup: dict, capture: dict, out: Path, operation: str, scope: str,
             settings: dict) -> tuple[list[dict], dict[str, np.ndarray], dict, dict]:
    frames = {f['image_file']: f for f in capture['frames']}
    observations, masks, hashes = [], {}, {}
    (out/'masks').mkdir(); (out/'scores').mkdir()
    # A lease excludes writes by both this service and another process during the snapshot.
    with batch.lock, batch.writer():
        if batch.job['running']:
            raise io.StudyError('Stop mask generation before taking a snapshot')
        selected = [batch.item(i) for i in batch.manifest['ids']]
        if scope == 'pilot':
            views = settings['pilot_views'].get(capture['plant_id'])
            if views is not None:
                selected = [i for i in selected if str(frames[i['image_file']]['view_code']).zfill(2) in views]
            else:
                pilot = batch.manifest.get('pilot_photos', [])
                if not pilot or any(name not in frames for name in pilot):
                    raise io.StudyError('No valid recorded pilot photos; use --scope all')
                selected = [i for i in selected if i['image_file'] in pilot]
        signature = input_signature(batch, backup, [i['id'] for i in selected])
        for item in selected:
            batch._validate_source(item)
            frame = frames[item['image_file']]
            obs = {k: deepcopy(item.get(k)) for k in ('id', 'plant_id', 'source_annotation_id', 'image_file', 'image_path',
                'image_sha256', 'image_size_px', 'source_bbox_xywh_px', 'transform', 'image_provenance', 'prompts',
                'review', 'generation', 'revision', 'selected_candidate', 'sensitivity', 'cache_key', 'history',
                'generation_seconds', 'review_seconds', 'edit_seconds')}
            obs.update(identity_for(item, backup), session_id=capture['session_id'], view_code=frame['view_code'],
                view_group=frame.get('observed_view_group'), pose_reference=frame['image_file'],
                pose_status=frame['pose_status'], passes_pose_gate=frame.get('passes_pose_gate'),
                reprojection_error_px=frame.get('reprojection_error_px'), marker_evidence=frame.get('board_evidence'),
                mask_file=None, crop_px=None, snapshot_exclusion=None)
            hashes[str((batch.session/item['image_path']).resolve())] = item['image_sha256']
            if item['generation'] == 'ready':
                raw = batch.preview_logits(item['id'])  # validates all cached scores and checksum
                n, h, w, revision = np.frombuffer(raw[:16], dtype='<u4')
                scores = np.frombuffer(raw[16:], dtype='<f4').reshape(int(n), int(h), int(w))
                mask, meta = batch.mask(item)
                obs.update(crop_px=meta['crop_px'], model=meta.get('model'), model_scores=meta['scores'],
                           mask_file=f"masks/{item['id']}.png", scores_sha256=meta['logits_sha256'])
                Image.fromarray(mask.astype(np.uint8)*255).save(out/obs['mask_file'])
                masks[item['id']] = mask
                if operation == 'sensitivity_sweep':
                    np.savez_compressed(out/'scores'/f"{item['id']}.npz", logits=scores[item['selected_candidate']])
                hashes[str(batch.root/'cache'/item['cache_key']/'logits.npz')] = meta['logits_sha256']
            else:
                obs['snapshot_exclusion'] = 'cached_scores_unavailable'
            observations.append(obs)
        if signature != input_signature(batch, backup, [i['id'] for i in selected]):
            raise io.StudyError('Inputs changed during snapshot')
    hashes[str(Path(batch.manifest['source_coco']))] = batch.manifest['source_coco_sha256']
    return observations, masks, signature, hashes


def sensitivity_sweep(out: Path, observations: list[dict], references: dict, settings: dict,
                      evaluation_allowed: bool) -> dict:
    values = sorted(set(settings['sensitivity_values']) | {o['sensitivity'] for o in observations})
    groups = defaultdict(list)
    for obs in observations:
        groups[obs['image_file']].append(obs)
    summaries, areas, visibility_rows = [], [], []
    evaluated = set()
    for photo, items in groups.items():
        ready = [o for o in items if o['mask_file']]
        arrays = {}
        for o in ready:
            with np.load(out/'scores'/f"{o['id']}.npz", allow_pickle=False) as archive:
                arrays[o['id']] = archive['logits']
        ref = references.get(photo)
        reason = ('parameters_not_frozen_for_dwt_02' if not evaluation_allowed else
                  'independent_visible_reference_unavailable' if ref is None else
                  'incomplete_reference_coverage' if ref['coverage'] != 'complete_visible' else
                  'some_observations_have_no_cached_scores' if len(ready) != len(items) else None)
        width, height = items[0]['image_size_px']
        gt, ignore = [], None
        if reason is None:
            gt = [render_rings(i['rings'], (height, width), [0, 0, width, height]) for i in ref['instances']]
            ignore = render_rings(ref.get('ignore_rings', []), (height, width), [0, 0, width, height])
            evaluated.add(photo)
        for sensitivity in values:
            started = time.perf_counter()
            predicted = []
            for obs in ready:
                # np.float32 comparison matches Batch.mask and the browser; no inference or cleanup.
                mask = arrays[obs['id']] > threshold(float(sensitivity))
                areas.append(dict(observation_id=obs['id'], image_file=photo, candidate=obs['selected_candidate'],
                    sensitivity=sensitivity, area_px=int(mask.sum()), saved_sensitivity=obs['sensitivity'],
                    candidate_held_fixed=True, manual_edits_applied=False))
                if reason is None:
                    x0, y0, x1, y1 = obs['crop_px']
                    full = np.zeros((height, width), bool); full[y0:y1, x0:x1] = mask
                    predicted.append(full)
            row = dict(plant_id=items[0]['plant_id'], image_file=photo, view_code=items[0]['view_code'],
                       sensitivity=sensitivity, observations=len(items), cached_observations=len(ready),
                       evaluated=reason is None, unavailable_reason=reason, reference_instances=len(gt) if reason is None else None,
                       tp=None, fp=None, fn=None, precision=None, recall=None, mean_iou_all_reference=None,
                       mean_dice_all_reference=None, merged_instance_count=None, split_instance_count=None)
            if reason is None:
                metrics = mask_metrics(predicted, gt, settings, ignore)
                metrics.pop('matches')
                matches = metrics.pop('segmentation_matches')
                row['merge_observation_ids'] = [ready[i]['id'] for i in metrics.pop('merge_prediction_indices')]
                row['split_reference_ids'] = [ref['instances'][i]['reference_id'] for i in metrics.pop('split_reference_indices')]
                row.update(metrics)
                by_ref = {m['reference_index']: m for m in matches}
                for index, reference in enumerate(ref['instances']):
                    match = by_ref.get(index, {})
                    visibility_rows.append(dict(plant_id=items[0]['plant_id'], image_file=photo,
                        sensitivity=sensitivity, reference_id=reference['reference_id'], visibility=reference['visibility'],
                        matched=match.get('detected', False), iou=match.get('iou', 0), dice=match.get('dice', 0)))
            row['runtime_seconds'] = time.perf_counter()-started
            summaries.append(row)
    table(out, 'sensitivity_comparison.csv', summaries)
    table(out, 'observation_sensitivity.csv', areas)
    table(out, 'visibility_comparison.csv', visibility_rows)
    return dict(status='complete', metric_status='available_for_reported_coverage' if evaluated else 'unavailable_no_evaluable_reference',
                evaluated_photos=len(evaluated), total_photos=len(groups), sensitivity_values=values,
                comparison=summaries, evaluation_label='bbox-assisted segmentation performance',
                missing_references_are_not_zero_accuracy=True, candidate_changes='not compared; fixed per observation',
                role='development' if observations and observations[0]['plant_id'] == 'dwt_01' else 'held_out_engineering_comparison',
                generalization_claim=False)


def run(operation: str, session: Path, backup_path: Path, context: Path, batch_root: Path, out: Path,
        *, scope: str = 'pilot', mode: str = 'strict', reference: dict | None = None, frozen: dict | None = None) -> dict:
    if operation not in OPERATIONS or scope not in ('pilot', 'all'):
        raise io.StudyError('Document 06 supports sensitivity_sweep and instance_fusion only')
    for p in (session, batch_root, out): check_research_path(p)
    if out.exists(): raise io.StudyError('Output exists; every run requires a new directory')
    settings = io.read_json(DEFAULTS)
    settings = {k: v for k, v in settings.items() if not k.startswith(('dbscan', 'display_eps', 'display_min', 'pca_', 'max_clustering'))}
    capture, _, backup, _ = checked_inputs(session, backup_path, context)
    check_operation_scope(operation, capture['plant_id'])
    evaluation_allowed = capture['plant_id'] == 'dwt_01'
    if frozen is not None:
        if (frozen.get('schema_version') != 'instance-parameters-frozen-1' or frozen.get('development_plant') != 'dwt_01' or
            frozen.get('evaluation_plant') != 'dwt_02' or frozen.get('settings_sha256') != io.digest(settings) or frozen.get('settings') != settings):
            raise io.StudyError('Frozen development settings do not match this implementation')
        if datetime.fromisoformat(frozen['frozen_at']) >= datetime.now(timezone.utc):
            raise io.StudyError('Freeze must predate evaluation')
        evaluation_allowed = capture['plant_id'] in ('dwt_01', 'dwt_02')
    references = validate_reference(reference, capture)
    batch = Batch(batch_root)
    if (batch.session.resolve() != session.resolve() or batch.manifest.get('organ_class', 'leaflet') != 'leaflet'
        or batch.manifest.get('plant_id') != capture['plant_id']):
        raise io.StudyError('Expected matching leaflet batch')
    import_hashes, import_audit = checked_import_sources(batch, capture)
    out = io.output_dir(out)
    started = time.perf_counter()
    observations, masks, signature, hashes = snapshot(batch, backup, capture, out, operation, scope, settings)
    hashes.update(import_hashes)
    verify_snapshot_sources(hashes)
    for p in (session/'capture.json', session/'session_report.json', context, Path(capture['intrinsics_path']), Path(capture['board_spec_path'])):
        hashes[str(p.resolve())] = io.file_hash(p)
    manifest = dict(schema_version='instance-evidence-run-1', operation=operation, plant_id=capture['plant_id'],
        session_id=capture['session_id'], created_at=datetime.now(timezone.utc).isoformat(), scope=scope, mode=mode,
        settings=settings, input_signature=signature, source_hashes=hashes, observations=observations,
        reference=reference, frozen_parameters=frozen, import_freshness=import_audit,
        validated_metric=False, suitable_for_ppfd=False,
        source_code_sha256={p.name: io.file_hash(p) for p in (Path(__file__), Path(__file__).with_name('instance_evidence.py'))})
    io.write_json(out/'manifest.json', manifest)
    io.write_json(out/'import_freshness.json', import_audit)
    io.write_json(out/'editor.backup.json', backup)
    io.write_json(out/'capture.json', capture)
    io.write_json(out/'reference_template.json', reference_template(capture, observations))
    table(out, 'observations.csv', observations)
    if operation == 'sensitivity_sweep':
        result = sensitivity_sweep(out, observations, references, settings, evaluation_allowed)
    else:
        result = fuse(capture, observations, masks, settings, mode)
        table(out, 'voxels.csv', result.get('voxels', []), ('voxel_id','leaf_key','x_mm','y_mm','z_mm',
              'support_ids','contradiction_ids','unknown_ids','support_views','state','exclusion_reason','ambiguous'))
        table(out, 'extents.csv', result.get('extents', []), ('leaf_key','status'))
        table(out, 'exclusions.csv', result.get('exclusions', []), ('observation_id','reason'))
        io.write_json(out/'evidence.json', result)
        voxels = result.pop('voxels', [])
        stride = max(1, int(np.ceil(len(voxels)/settings['display_point_limit'])))
        result.update(voxel_count=len(voxels), supported_voxels=sum(v['state'] == 'supported' for v in voxels),
                      display_voxels=voxels[::stride], display_stride=stride,
                      display_subsampling_only=True, full_evidence_file='evidence.json')
    result.update(operation=operation, runtime_seconds=time.perf_counter()-started,
        review_seconds=sum(o.get('review_seconds') or 0 for o in observations),
        edit_seconds=sum(o.get('edit_seconds') or 0 for o in observations),
        review_states=dict(Counter(o['review'] for o in observations)),
        human_identity_confirmed=sum(o['identity_review'] == 'confirmed' for o in observations),
        validated_metric=False, suitable_for_ppfd=False, inference_calls=0, clustering='deferred_by_user',
        files=sorted(p.name for p in out.iterdir() if p.is_file())+['result.json'])
    io.write_json(out/'result.json', result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--operation', choices=(*OPERATIONS, 'freeze_parameters'), required=True)
    for arg in ('session', 'backup', 'context', 'batch', 'out', 'reference', 'frozen', 'development-run'):
        parser.add_argument('--'+arg, type=Path)
    parser.add_argument('--scope', choices=('pilot', 'all'), default='pilot')
    parser.add_argument('--mode', choices=('strict', 'diagnostic'), default='strict')
    args = parser.parse_args()
    if args.operation == 'freeze_parameters':
        result = freeze_parameters(args.development_run, args.out)
    else:
        result = run(args.operation, args.session, args.backup, args.context, args.batch, args.out,
                     scope=args.scope, mode=args.mode, reference=io.read_json(args.reference) if args.reference else None,
                     frozen=io.read_json(args.frozen) if args.frozen else None)
    print(json.dumps({k: v for k, v in result.items() if k not in ('display_voxels', 'comparison', 'extents', 'exclusions')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
