"""Optional diffusion experiment boundary; existing reconstruction stays read-only.

python -m tools.multiview_completion audit --request build/request.json --out build/new_audit
python -m tools.multiview_completion prepare --request build/request.json --out build/new_prepared
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import html
import json
from pathlib import Path
import re
import shutil

import numpy as np
from PIL import Image

from tools.leaf_light.common import StudyError, digest, file_hash, output_dir, read_json, write_json, write_rows

SCHEMA = 'multiview-completion-request-1'
SAFE_ID = re.compile(r'^[A-Za-z0-9][A-Za-z0-9_.-]*$')
ROLES = ('condition', 'evaluation')
TARGET_PROVENANCE_KEYS = ('model_pose_polar_azimuth_radius', 'passes_pose_gate')
METRIC_COLUMNS = ('candidate_id', 'image_id', 'split', 'metric', 'value', 'denominator',
                  'excluded_pixels', 'status', 'reason')


def identifier(value: str) -> str:
    if not isinstance(value, str) or not SAFE_ID.fullmatch(value) or '..' in value:
        raise StudyError('Unsafe or missing identifier')
    return value


def resolve(base: Path, value: str) -> Path:
    path = Path(value)
    return (path if path.is_absolute() else base/path).resolve()


def dependency_closure(assets: dict[str, dict], roots: list[str]) -> set[str]:
    result: set[str] = set()
    visiting: set[str] = set()

    def visit(key: str) -> None:
        if key not in assets:
            raise StudyError(f'Unknown dependency: {key}')
        if key in visiting:
            raise StudyError(f'Cyclic dependency: {key}')
        if key in result:
            return
        visiting.add(key)
        for parent in assets[key]['parent_asset_ids']:
            visit(parent)
        visiting.remove(key)
        result.add(key)

    for key in roots:
        visit(key)
    return result


def audit_request(request_path: Path) -> dict:
    request_path = request_path.resolve()
    before = file_hash(request_path)
    request = read_json(request_path)
    if request.get('schema') != SCHEMA:
        raise StudyError('Unsupported completion request')
    for key in ('request_id', 'plant_id', 'session_id'):
        identifier(request.get(key))
    mode = request.get('deployment_mode')
    if mode not in ('top_only', 'multiview'):
        raise StudyError('Invalid deployment mode')
    assets: dict[str, dict] = {}
    hashes = {str(request_path): before}
    for asset in request['assets']:
        key = identifier(asset['asset_id'])
        if key in assets:
            raise StudyError('Duplicate asset')
        if not isinstance(asset.get('parent_asset_ids'), list) or not isinstance(asset.get('source_image_ids'), list):
            raise StudyError('Explicit asset dependency and image lists required')
        path = resolve(request_path.parent, asset['path'])
        actual = file_hash(path)
        if actual != asset['sha256']:
            raise StudyError(f'Asset hash mismatch: {key}')
        assets[key] = dict(asset, resolved_path=str(path))
        hashes[str(path)] = actual
    dependency_closure(assets, list(assets))
    observations = request['observations']
    ids: set[str] = set()
    conditions, evaluation, roots = set(), set(), []
    blockers: list[str] = []
    for view in observations:
        key = identifier(view['image_id'])
        if key in ids or view['role'] not in ROLES:
            raise StudyError('Duplicate image or invalid role')
        ids.add(key)
        image_key = view['image_asset_id']
        if image_key not in assets or assets[image_key]['source_image_ids'] != [key]:
            raise StudyError('Image asset must declare its own source image')
        with Image.open(assets[image_key]['resolved_path']) as picture:
            if list(picture.size) != view['original_size_px'] or picture.getexif().get(274, 1) != 1:
                raise StudyError('Original image size/orientation mismatch')
        # Masks in this interface are full-resolution raster evidence, never model-resized arrays.
        for field in ('mask_asset_id', 'known_region_asset_id'):
            if view.get(field):
                if view[field] not in assets:
                    raise StudyError('Unknown mask asset')
                with Image.open(assets[view[field]]['resolved_path']) as mask:
                    if list(mask.size) != view['original_size_px']:
                        raise StudyError('Original mask shape mismatch')
        if view['role'] == 'condition':
            conditions.add(key)
            roots.extend([image_key, *[view[f] for f in ('mask_asset_id', 'camera_asset_id') if view.get(f)]])
            if mode == 'top_only' and view.get('view_group') != 'top':
                blockers.append('top_only_contains_non_top_condition')
        else:
            evaluation.add(key)
    if not conditions:
        blockers.append('conditioning_images_missing')
    if mode == 'multiview' and len(conditions) < 2:
        blockers.append('multiview_requires_multiple_real_conditions')
    roots.extend(request.get('condition_asset_ids', []))
    closure = dependency_closure(assets, roots)
    for key in sorted(closure):
        asset = assets[key]
        if asset.get('provenance_status') != 'declared':
            blockers.append(f'unknown_dependency_provenance:{key}')
        if not set(asset['source_image_ids']).issubset(conditions):
            blockers.append(f'forbidden_conditioning_dependency:{key}')
        if asset.get('origin') == 'generative':
            blockers.append(f'generated_input_requires_separate_stage:{key}')
    if not request.get('movement_group_id') or not request.get('movement_evidence'):
        blockers.append('rigid_movement_group_unverified')
    if request.get('composition') != 'alternative_hypothesis_only':
        blockers.append('composition_contract_not_implemented')
    if request.get('sample_selection') != 'retain_all_declared_seeds':
        blockers.append('sample_selection_not_supported')
    backend = request.get('backend', {})
    if not backend.get('name'):
        blockers.append('backend_missing')
    if backend.get('model_policy') not in ('user_tuned', 'user_authorized_public_trial') or not backend.get('policy_source'):
        blockers.append('model_policy_evidence_missing')
    if not backend.get('revision') or not backend.get('checkpoint'):
        blockers.append('backend_revision_or_checkpoint_missing')
    budget = request.get('budgets', {})
    for key in ('max_candidates', 'steps', 'max_wall_time_s'):
        if type(budget.get(key)) is not int or budget[key] <= 0:
            blockers.append(f'budget_missing:{key}')
    seeds = budget.get('seeds', [])
    if not seeds or any(type(x) is not int or x < 0 for x in seeds) or len(set(seeds)) != len(seeds):
        blockers.append('explicit_unique_seeds_required')
    if type(budget.get('max_candidates')) is int and len(seeds) > budget['max_candidates']:
        blockers.append('candidate_budget_exceeded')
    if file_hash(request_path) != before:
        raise StudyError('Request changed during audit')
    for name, expected in hashes.items():
        if file_hash(Path(name)) != expected:
            raise StudyError('Source changed during audit')
    return dict(schema='completion-request-audit-1', request=request, request_sha256=before,
                request_path=str(request_path), assets=assets, source_hashes=hashes,
                conditioning_asset_ids=sorted(closure), condition_image_ids=sorted(conditions),
                evaluation_image_ids=sorted(evaluation), blockers=sorted(set(blockers)),
                status='ready_for_backend_preparation' if not blockers else 'blocked',
                backend_executed=False, validated_metric=False, suitable_for_ppfd=False)


def prepare_request(request_path: Path, out: Path) -> dict:
    audit = audit_request(request_path)
    folder = output_dir(out)
    write_json(folder/'audit.json', audit)
    write_json(folder/'request.snapshot.json', audit['request'])
    # Only the explicit backend contract crosses the boundary. In particular,
    # source-run paths, ratio files and evaluator metadata are not copied through.
    keys = ('schema','request_id','plant_id','session_id','capture_date','deployment_mode',
            'observations','condition_asset_ids','movement_group_id','movement_evidence',
            'composition','sample_selection','backend','budgets','targets','geometry_scope','pose_quality_notice')
    package = {k:deepcopy(audit['request'][k]) for k in keys if k in audit['request']}
    package['observations'] = [v for v in package['observations'] if v['role']=='condition']
    allowed = set(audit['conditioning_asset_ids'])
    package['assets'] = []
    (folder/'inputs').mkdir()
    for key in sorted(allowed):
        asset = audit['assets'][key]
        source = Path(asset['resolved_path'])
        target = folder/'inputs'/(key+source.suffix.lower())
        shutil.copyfile(source, target)
        if file_hash(target) != asset['sha256']:
            raise StudyError('Copied asset changed')
        copied = {k:v for k,v in asset.items() if k != 'resolved_path'}
        copied['path'] = str(target.relative_to(folder)).replace('\\', '/')
        package['assets'].append(copied)
    package['source_request_sha256'] = audit['request_sha256']
    package['preparation_blockers'] = audit['blockers']
    package['backend_execution_enabled'] = not audit['blockers']
    write_json(folder/'backend_request.json', package)
    manifest = dict(schema='completion-prepared-1', request_sha256=audit['request_sha256'],
                    package_sha256=file_hash(folder/'backend_request.json'),
                    status='prepared' if not audit['blockers'] else 'prepared_blocked',
                    files={str(p.relative_to(folder)).replace('\\','/'):file_hash(p)
                           for p in sorted(folder.rglob('*')) if p.is_file()},
                    backend_executed=False, validated_metric=False, suitable_for_ppfd=False)
    write_json(folder/'manifest.json', manifest)
    return manifest


def verify_prepared(prepared: Path) -> tuple[dict, dict]:
    manifest = read_json(prepared/'manifest.json')
    for name, sha in manifest['files'].items():
        path = resolve(prepared, name)
        if not path.is_relative_to(prepared.resolve()) or file_hash(path) != sha:
            raise StudyError('Prepared package changed')
    return read_json(prepared/'backend_request.json'), manifest


def import_candidate_bundle(prepared: Path, candidate_path: Path, out: Path) -> dict:
    request, prepared_manifest = verify_prepared(prepared)
    bundle = read_json(candidate_path)
    if bundle.get('complete', True) is not True or '.partial.' in candidate_path.name:
        raise StudyError('Partial candidate bundle cannot be imported')
    if bundle.get('schema') != 'completion-candidates-1':
        raise StudyError('Unsupported candidate bundle')
    if bundle.get('request_sha256') != prepared_manifest['request_sha256']:
        raise StudyError('Candidate/request hash mismatch')
    if bundle.get('conditioning_asset_ids') != sorted(a['asset_id'] for a in request['assets']):
        raise StudyError('Candidate conditioning closure mismatch')
    if bundle.get('backend_executed') is not True:
        raise StudyError('Bundle is not an executed model result')
    if bundle.get('backend') != request['backend']:
        raise StudyError('Candidate backend provenance mismatch')
    candidates = bundle.get('candidates', [])
    if not candidates or len(candidates) > request['budgets']['max_candidates']:
        raise StudyError('Candidate count outside budget')
    if [c['seed'] for c in candidates] != request['budgets']['seeds']:
        raise StudyError('All declared seeds must be retained in order')
    target_contract = {t['target_id']: t for t in request.get('targets', [])}
    seen, paths = set(), {}
    for candidate in candidates:
        key = identifier(candidate['candidate_id'])
        if key in seen:
            raise StudyError('Duplicate candidate')
        seen.add(key)
        if candidate.get('origin') != 'generative' or candidate.get('validated_metric') is not False:
            raise StudyError('Generative origin/validation flag required')
        if candidate.get('suitable_for_ppfd') is not False:
            raise StudyError('Candidate cannot declare optical eligibility')
        if candidate.get('representation') != 'novel_view_rgb':
            raise StudyError('Only RGB hypotheses supported by this backend adapter')
        target_ids = set()
        if not candidate.get('views'):
            raise StudyError('Candidate has no generated views')
        for view in candidate['views']:
            identifier(view['target_id'])
            target = target_contract.get(view['target_id'], {})
            for field in TARGET_PROVENANCE_KEYS:
                if field in target and (field not in view or view[field] != target[field]):
                    raise StudyError(f'Candidate target provenance mismatch: {field}')
            if view['target_id'] in target_ids:
                raise StudyError('Duplicate candidate target')
            target_ids.add(view['target_id'])
            path = resolve(candidate_path.parent, view['path'])
            if not path.is_relative_to(candidate_path.parent.resolve()):
                raise StudyError('Candidate file outside bundle')
            if file_hash(path) != view['sha256']:
                raise StudyError('Candidate image hash mismatch')
            with Image.open(path) as picture:
                if list(picture.size) != view['size_px']:
                    raise StudyError('Candidate image size mismatch')
            paths[(key, view['target_id'])] = path
        expected_targets = {t['target_id'] for t in request.get('targets', [])}
        if expected_targets and target_ids != expected_targets:
            raise StudyError('Candidate must retain every declared target')
    folder = output_dir(out)
    imported = deepcopy(bundle)
    for candidate in imported['candidates']:
        dest = folder/candidate['candidate_id']
        dest.mkdir()
        for view in candidate['views']:
            source = paths[(candidate['candidate_id'], view['target_id'])]
            target = dest/(view['target_id']+source.suffix)
            shutil.copyfile(source, target)
            if file_hash(target) != view['sha256']:
                raise StudyError('Candidate changed during copy')
            view['path'] = str(target.relative_to(folder)).replace('\\','/')
    imported['import_status'] = 'candidate_imported'
    imported['metric_geometry_status'] = 'unavailable_from_novel_view_rgb'
    imported['source_bundle_sha256'] = file_hash(candidate_path)
    write_json(folder/'candidates.json', imported)
    return imported


def silhouette_metric(predicted: np.ndarray, observed: np.ndarray, known: np.ndarray) -> dict:
    if predicted.shape != observed.shape or observed.shape != known.shape:
        raise StudyError('Metric raster shape mismatch')
    if any(x.dtype != np.bool_ for x in (predicted, observed, known)):
        raise StudyError('Boolean raster masks required')
    union = int(((predicted | observed) & known).sum())
    intersection = int((predicted & observed & known).sum())
    return dict(value=intersection/union if union else None, denominator=union,
                excluded_pixels=int((~known).sum()), status='computed' if union else 'unavailable',
                reason=None if union else 'empty_valid_union')


def evaluate_candidates(prepared: Path, imported: Path, out: Path) -> dict:
    """Report evaluability honestly; canonical RGB does not imply real-camera alignment."""
    request, manifest = verify_prepared(prepared)
    bundle = read_json(imported/'candidates.json')
    if bundle['request_sha256'] != manifest['request_sha256']:
        raise StudyError('Evaluation request mismatch')
    snapshot = read_json(prepared/'request.snapshot.json')
    report_rows = []
    for candidate in bundle['candidates']:
        for view in candidate['views']:
            if file_hash(resolve(imported,view['path'])) != view['sha256']:
                raise StudyError('Stale generated image')
        for view in snapshot['observations']:
            report_rows.append(dict(candidate_id=candidate['candidate_id'],image_id=view['image_id'],
                split=view['role'],metric='observed_camera_silhouette_iou',value=None,denominator=None,
                excluded_pixels=None,status='unavailable',reason='canonical_generated_rgb_has_no_validated_original_camera_mapping'))
    folder = output_dir(out)
    write_rows(folder/'view_metrics.csv',report_rows,METRIC_COLUMNS)
    report = dict(schema='completion-evaluation-1',request_sha256=manifest['request_sha256'],
                  candidate_bundle_sha256=file_hash(imported/'candidates.json'),
                  status='evaluation_unavailable',rows=report_rows,
                  metric_geometry_status='unavailable_from_novel_view_rgb',
                  validated_metric=False,suitable_for_ppfd=False,
                  limitation='Generated images can be inspected; no mask, depth, alignment or identity is invented to score them.')
    write_json(folder/'evaluation.json',report)
    return report


def export_review_bundle(imported: Path, out: Path) -> dict:
    """Display the actual saved generated images, preserving candidate provenance."""
    bundle = read_json(imported/'candidates.json')
    folder = output_dir(out)
    cards = []
    for candidate in bundle['candidates']:
        for view in candidate['views']:
            source = resolve(imported, view['path'])
            if file_hash(source) != view['sha256']:
                raise StudyError('Stale candidate image')
            target = folder/(identifier(candidate['candidate_id'])+'_'+identifier(view['target_id'])+source.suffix)
            shutil.copyfile(source, target)
            cards.append(f'<figure><img src="{html.escape(target.name)}"><figcaption>'
                         f'{html.escape(candidate["candidate_id"])} / {html.escape(view["target_id"])}'
                         f' / seed {candidate["seed"]}</figcaption></figure>')
    page = ('<!doctype html><meta charset="utf-8"><title>확산 보완 시험</title>'
            '<style>body{font:16px system-ui;margin:30px;max-width:1100px}main{display:flex;flex-wrap:wrap}'
            'figure{margin:12px}img{max-width:320px}pre{white-space:pre-wrap;overflow-wrap:anywhere}</style>'
            '<h1>확산 보완 시험 결과</h1><p>생성된 시점의 영상 가설입니다. 실측 잎·깊이·면적 또는 광학 입력으로 확정되지 않았습니다.</p>'
            '<main>'+''.join(cards)+'</main><details><summary>출처와 실행 정보</summary><pre>'
            +html.escape(json.dumps(bundle, ensure_ascii=False, indent=2))+'</pre></details>')
    (folder/'viewer.html').write_text(page, encoding='utf-8')
    write_json(folder/'review.json', bundle)
    return dict(status='review_exported', candidates=len(bundle['candidates']), viewer=str(folder/'viewer.html'))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='action', required=True)
    for action in ('audit', 'prepare'):
        command = sub.add_parser(action)
        command.add_argument('--request', type=Path, required=True)
        command.add_argument('--out', type=Path, required=True)
    command = sub.add_parser('import')
    command.add_argument('--prepared', type=Path, required=True)
    command.add_argument('--candidate', type=Path, required=True)
    command.add_argument('--out', type=Path, required=True)
    command = sub.add_parser('review')
    command.add_argument('--imported', type=Path, required=True)
    command.add_argument('--out', type=Path, required=True)
    command = sub.add_parser('evaluate')
    command.add_argument('--prepared', type=Path, required=True)
    command.add_argument('--imported', type=Path, required=True)
    command.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    if args.action == 'audit':
        report = audit_request(args.request)
        write_json(output_dir(args.out)/'audit.json', report)
    elif args.action == 'prepare':
        report = prepare_request(args.request, args.out)
    elif args.action == 'import':
        report = import_candidate_bundle(args.prepared, args.candidate, args.out)
    elif args.action == 'evaluate':
        report = evaluate_candidates(args.prepared, args.imported, args.out)
    else:
        report = export_review_bundle(args.imported, args.out)
    print({k:report[k] for k in ('status','blockers','import_status','backend_executed') if k in report})


if __name__ == '__main__':
    main()
