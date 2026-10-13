"""Bounded GroIMP adapter for retained-target hierarchy cases; no automatic execution."""
from __future__ import annotations

from pathlib import Path
import numpy as np

from tools.groimp_density import execute, parse_log, verify_prepared
from tools.groimp_light_sanity import CORE
from tools.leaf_light.common import StudyError, file_hash, read_json, write_json
from tools.ppfd_validation import lamp_adapter, make_job_rgg


def prepare_native(folder: Path, manifest: dict, context: object) -> None:
    spec = manifest['plan'].get('native', {})
    blockers = []
    for field in ('rays', 'max_depth', 'max_jobs', 'max_total_rays'):
        if type(spec.get(field)) is not int or spec[field] < 1:
            blockers.append(f'explicit_positive_native_limit_required:{field}')
    seeds = spec.get('seeds', [])
    if not seeds or len(seeds) != len(set(seeds)) or any(type(s) is not int or s < 0 or s > 2147483647 for s in seeds):
        blockers.append('unique_nonnegative_32bit_seed_list_required')
    scene = context.resolved.scene.model_copy(update={'fixtures': [f.fixture for f in context.resolved.fixtures]})
    adapter = lamp_adapter(folder / 'scene.json', scene)
    write_json(folder / 'native_lamp_adapter.json', adapter)
    blockers.extend(f'unsupported_fixture:{f["fixture_id"]}:{f["reason"]}' for f in adapter['unsupported_fixtures'])
    optics = tuple(getattr(scene.leaf_optics, n).value for n in ('absorptance', 'reflectance', 'transmittance'))
    if any(x is None for x in optics):
        blockers.append('native_requires_complete_leaf_optics')
    elif not np.isclose(sum(optics), 1., atol=1e-6):
        blockers.append('native_requires_A_plus_R_plus_T_equal_one')
    job_count = len(manifest['cases']) * len(seeds)
    if not blockers:
        if job_count > spec['max_jobs'] or job_count * spec['rays'] > spec['max_total_rays']:
            blockers.append('native_budget_exceeded')
    manifest['native_cost'] = dict(jobs=job_count, rays_per_job=spec.get('rays'),
        total_rays=job_count * spec['rays'] if spec.get('rays') else None, max_depth=spec.get('max_depth'), seeds=seeds)
    manifest['native_blockers'] = blockers
    if blockers:
        manifest['status'] = 'blocked'
        return
    jobs = dict(schema_version='groimp-density-jobs-1', cases=[], source_hashes=manifest['source_hashes'],
                solver=spec, validated_metric=False, suitable_for_ppfd=False,
                transport='GroIMP CPU diffuse reflection and transmission', artifact_hashes={})
    for case in manifest['cases']:
        native_case = dict(case_id=case['case_id'], status='prepared', blockers=[], jobs=[], model_hashes={})
        leaves = [(dict(surface_id=f't{i:07d}'), context.vertices[i]) for i in case['retained']]
        for index, seed in enumerate(seeds):
            name = f'replicate_{index:04d}'
            job = folder / case['case_id'] / name
            job.mkdir(parents=True)
            rgg = make_job_rgg(adapter['initialization_rgg'], spec['rays'], spec['max_depth'], seed,
                               rig=context.background, leaves=leaves, leaf_optics=optics)
            (job / 'Model.rgg').write_text(rgg, encoding='utf-8')
            native_case['jobs'].append(name)
            native_case['model_hashes'][name] = file_hash(job / 'Model.rgg')
            jobs['artifact_hashes'][str((job / 'Model.rgg').relative_to(folder))] = file_hash(job / 'Model.rgg')
        jobs['cases'].append(native_case)
    write_json(folder / 'jobs.json', jobs)
    manifest['artifact_hashes'] = dict(jobs['artifact_hashes'])


def execute_native(prepared: Path, out: Path, execute_flag: bool, java: str, core: Path | None) -> dict:
    from tools.hierarchical_light import require_fresh
    manifest = require_fresh(prepared)
    if manifest['backend'] != 'native' or manifest['status'] != 'prepared':
        raise StudyError('prepared_native_run_required')
    if not execute_flag:
        return dict(status='not_executed', cost=manifest['native_cost'])
    # Existing executor retains failures and verifies RGG hashes before every job.
    return execute(prepared, out, core or CORE, java)


def collect_native(prepared: Path, execution: Path, out: Path) -> dict:
    from tools.hierarchical_light import require_fresh, write_report
    manifest = require_fresh(prepared)
    if manifest['backend'] != 'native' or manifest['status'] != 'prepared':
        raise StudyError('prepared_native_run_required')
    jobs = read_json(prepared / 'jobs.json'); verify_prepared(prepared, jobs)
    execution_manifest = read_json(execution / 'execution.json')
    if execution_manifest['jobs_sha256'] != file_hash(prepared / 'jobs.json'):
        raise StudyError('native_execution_manifest_stale')
    if Path(execution_manifest['prepared']).resolve() != prepared.resolve():
        raise StudyError('native_execution_prepared_mismatch')
    done = {(r['case_id'], r['job']): r for r in execution_manifest['runs']}
    if len(done) != len(execution_manifest['runs']):
        raise StudyError('duplicate_native_execution_record')
    runs, failures = [], []
    for index, seed in enumerate(manifest['plan']['native']['seeds']):
        name = f'replicate_{index:04d}'
        run = dict(replicate=name, seed=seed, values={})
        for case in manifest['cases']:
            cid = case['case_id']
            rec = done.get((cid, name), {})
            if rec.get('status') != 'completed':
                failures.append(dict(case_id=cid, replicate=name, reason=rec.get('reason', 'not_executed')))
                continue
            log = execution / cid / name / 'groimp.log'
            if not log.is_file() or file_hash(log) != rec.get('log_sha256'):
                raise StudyError('native_log_changed_or_missing')
            leaves, probes = parse_log(log)
            if probes or set(leaves) != {f't{i:07d}' for i in case['retained']}:
                raise StudyError('native_leaf_output_identity_mismatch')
            result = {}
            for tid, target in manifest['targets'].items():
                if not set(target['triangles']).issubset(case['retained']):
                    continue
                flux = np.sum([leaves[f't{i:07d}'] for i in target['triangles']], axis=0)
                result[tid] = {'all': dict(received=float(flux[0]), absorbed=float(flux[1]))}
            run['values'][cid] = result
        runs.append(run)
    manifest['native_failures'] = failures
    manifest['source_hashes'][str((prepared / 'manifest.json').resolve())] = file_hash(prepared / 'manifest.json')
    manifest['native_execution_hashes'] = {str((execution / 'execution.json').resolve()): file_hash(execution / 'execution.json')}
    for case_id, job in done:
        p = execution / case_id / job / 'groimp.log'
        if p.is_file():
            manifest['native_execution_hashes'][str(p.resolve())] = file_hash(p)
    manifest['source_hashes'].update(manifest['native_execution_hashes'])
    return write_report(manifest, runs, out)
