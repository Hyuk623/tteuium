"""Frozen, conditional native lamp calibration; never imports growth or edits observations.

CLI: audit --records DIR --operating JSON --out build/NEW
     freeze --plan JSON --out build/NEW
     run --frozen build/FROZEN --out build/NEW [--java java]
Plans explicitly supply each geometry variant and all numerical/resource controls.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import itertools
import math
import re
from pathlib import Path

import numpy as np

from tomato3d.light.scene import load_scene
from tools import ppfd_validation as pv
from tools.fsp_extensions import photon_factor
from tools.groimp_light_sanity import CORE, run_groimp
from tools.leaf_light.common import StudyError, digest, file_hash, output_dir, read_json, rows, write_json, write_rows

SCHEMA = 'p2-native-lamp-plan-1'
PRED_COLUMNS = ('variant_id', 'point_id', 'split_role', 'x_mm', 'y_mm', 'z_mm',
                'measured_ppfd_umol_m2_s', 'predicted_ppfd_umol_m2_s', 'seed_standard_error_umol_m2_s',
                'black_rig_ppfd_umol_m2_s', 'enclosure_free_ppfd_umol_m2_s',
                'post_reflection_estimate_umol_m2_s', 'post_reflection_standard_error_umol_m2_s',
                'post_reflection_fraction', 'rays', 'source_kind', 'status')


def code_hashes():
    root = Path(__file__).resolve().parents[1]
    names = ('tools/p2_lamp_calibration.py', 'tools/ppfd_validation.py', 'tools/fsp_extensions.py',
             'tools/groimp_light_sanity.py', 'tools/groimp_density.py', 'tools/leaf_light/common.py',
             'tomato3d/light/scene.py', 'tomato3d/light/frames.py', 'tomato3d/io/schemas.py')
    return {str(root/name):file_hash(root/name) for name in names}


def require(ok, reason):
    if not ok:
        raise StudyError(reason)


def finite(value, label, lo=None, hi=None):
    require(type(value) in (int, float) and math.isfinite(value), f'{label}: finite number required')
    require(lo is None or value >= lo, f'{label}: below bound')
    require(hi is None or value <= hi, f'{label}: above bound')
    return float(value)


def audit(records: Path, operating: Path, out: Path) -> dict:
    """Read current human records; retain nested provenance and never invent optical inputs."""
    folder = output_dir(out)
    grid = rows(records/'ppfd_grid_20261013.csv')
    geometry = read_json(records/'shelf_geometry_20261013.json')
    op = read_json(operating)
    hours = finite(op['daily_on_hours'], 'daily_on_hours', 0, 24)
    finite(op['output_fraction'], 'output_fraction', 0, 1)
    require(op.get('source_kind') == 'user_stated' and op.get('source_ref'), 'operating provenance required')
    groups = {}
    # This is a measurement summary, not a fitted spatial field or whole-plant reference.
    for row in grid:
        groups.setdefault(row['plane_id'], []).append(float(row['ppfd_umol_m2_s']))
    summary = {key: dict(n=len(vals), mean_ppfd_umol_m2_s=float(np.mean(vals)),
                        dli_at_declared_hours_mol_m2_day=float(np.mean(vals))*hours*3600/1e6,
                        dli_status='derived_assuming_constant_measured_output') for key, vals in groups.items()}
    blockers = ['emitting_surface_dimensions_and_centres_unconfirmed', 'beam_half_angle_unavailable',
                'wall_extents_and_ceiling_position_unavailable', 'sensor_footprint_and_calibration_unavailable',
                'grid_corner_orientation_variants_need_freezing', 'canopy_plant_geometry_unreconstructed',
                'explicit_fit_bounds_and_native_budget_required']
    report = dict(schema_version='p2-lamp-readiness-1', status='incomplete', numerical_fit_ready=False,
                  summaries=summary, operating=op, geometry=geometry, blockers=blockers,
                  fitted_parameters=None, held_out_error=None, definitive_validation='unavailable',
                  source_hashes={str(p.resolve()): file_hash(p) for p in [*sorted(records.glob('*')),
                                                                       operating] if p.is_file()},
                  notes=['PPF must be fitted from declared flux normalization, not lumens or electrical watts',
                         '50 mm is edge clearance; centre spacing needs confirmed emitting/housing width',
                         'approximately 60% analytic diffuse fraction is not validation truth',
                         'daily duration alone does not establish dated on/off clock intervals'])
    write_json(folder/'readiness.json', report)
    write_json(folder/'plan_template.json', dict(schema_version=SCHEMA, source_kind='real_measurement',
        source_ref=str(records.resolve()), variants=[], bounds=dict(photon_flux_scale=None,
        effective_reflectance_grey=None), reflectance_grid=None, offset_axis=None, offset_grid_mm=None,
        solver=dict(coarse_rays=None, final_rays=4800000, seeds=None, max_depth=None,
                    max_native_jobs=None, timeout_s=None), wavelength_nm=550,
        wavelength_source='declared monochromatic bookkeeping basis, not measured spectrum',
        spectral_fractions=dict(red=.419, green=.416, blue=.165), operating=op,
        note='Each variant: scene path, rig_surfaces path, sensors path, points path, readings path; '
             'fit_surface_ids, enclosure_surface_ids, provenance and conditional_reasons. '
             'Use existing ppfd_validation CSV contracts. No default lamp/rig/sensor geometry.'))
    return report


def _bounds(plan, name, lo, hi=None):
    b = plan['bounds'].get(name)
    require(isinstance(b, list) and len(b) == 2, f'{name} bounds required')
    a, z = [finite(v, name, lo, hi) for v in b]
    require(a < z, f'{name} bounds must increase')
    return a, z


def validate_plan(plan: dict) -> int:
    require(plan.get('schema_version') == SCHEMA, 'unsupported plan schema')
    require(plan.get('source_kind') in ('real_measurement', 'synthetic_test_only') and plan.get('source_ref'),
            'plan provenance required')
    require(set(plan['bounds']) == {'photon_flux_scale', 'effective_reflectance_grey'},
            'only flux and grey reflectance bounds are supported; optional offset uses offset_grid_mm')
    _bounds(plan, 'photon_flux_scale', 0)
    low, high = _bounds(plan, 'effective_reflectance_grey', 0, 1)
    rhos = plan.get('reflectance_grid')
    require(isinstance(rhos, list) and len(set(rhos)) >= 2, 'explicit reflectance grid required')
    require(rhos == sorted(set(rhos)) and rhos[0] == low and rhos[-1] == high,
            'reflectance grid must be unique, sorted, and include bounds')
    for v in rhos: finite(v, 'reflectance grid', low, high)
    offsets = plan.get('offset_grid_mm')
    if offsets is not None:
        require(plan.get('offset_axis') in ('x', 'y', 'z') and isinstance(offsets, list) and len(offsets) >= 2,
                'offset requires one explicit axis and bounded grid')
        require(offsets == sorted(set(offsets)), 'offset grid must be unique and sorted')
        for v in offsets: finite(v, 'offset_mm')
    else:
        require(plan.get('offset_axis') is None, 'offset axis without grid')
        offsets = [0.]
    solver = plan['solver']
    for key in ('coarse_rays', 'final_rays', 'max_depth', 'max_native_jobs', 'timeout_s'):
        require(type(solver.get(key)) is int and solver[key] > 0, f'positive integer solver.{key} required')
    require(solver['final_rays'] >= solver['coarse_rays'] and solver['max_depth'] <= 64, 'invalid ray/depth limits')
    if plan['source_kind'] == 'real_measurement':
        require(solver['final_rays'] == 4800000, 'real final validation requires declared 4.8M rays')
    seeds = solver.get('seeds')
    require(isinstance(seeds, list) and len(seeds) >= 2 and len(set(seeds)) == len(seeds)
            and all(type(s) is int and s >= 0 for s in seeds), 'at least two distinct nonnegative seeds required')
    photon_factor(plan['wavelength_nm'])
    require(plan.get('wavelength_source'), 'wavelength provenance required')
    variants = plan.get('variants')
    require(isinstance(variants, list) and variants, 'explicit variants required')
    require(len({v['variant_id'] for v in variants}) == len(variants), 'duplicate variant')
    jobs = 0
    for variant in variants:
        require(variant.get('provenance') and isinstance(variant.get('conditional_reasons'), list),
                'variant provenance/conditional reasons required')
        pts = variant['points_data']; ids = [p['point_id'] for p in pts]
        require(ids and len(ids) == len(set(ids)), 'unique nonempty point IDs required')
        require(all(p['split_role'] in pv.ROLES for p in pts), 'unknown split role')
        cal = [p for p in pts if p['split_role'] == 'calibration']
        require(len(cal) > (3 if plan.get('offset_grid_mm') else 2) and any(p['split_role'] == 'validation' for p in pts),
                'more calibration points than free parameters and held-out validation required')
        require(all(p['stage'] == 'empty_rig' for p in cal), 'fit only empty-rig calibration points')
        require(not any(p['accessible'] != 'yes' for p in pts), 'inaccessible measurement point')
        read = variant['readings_data']; roles = {p['point_id']:p['split_role'] for p in pts}
        for row in read:
            require(row['point_id'] in roles and row['split_role'] == roles[row['point_id']], 'split mismatch')
            finite(float(row['ppfd_umol_m2_s']), 'observed PPFD', 0)
            require(row['all_fixtures_full_output'] == 'yes' and row['ambient_condition'] == 'excluded_dark',
                    'fit requires declared full output and excluded ambient light')
            require(row['disturbed'] == 'no' and row['sensor_moved_leaves'] == 'no', 'disturbed readings refused')
        require(set(roles) == {r['point_id'] for r in read}, 'missing readings')
        sensors = {s['sensor_id']: s for s in variant['sensors_data']}
        for point in pts:
            require(pv.unit_normal(point).tolist() == [0., 0., 1.], 'horizontal upward probes required')
            pv.sensing_mesh(point, sensors[point['sensor_id']], variant.get('disc_segments'))
        rig = variant['rig_data']; rig_ids = {r['surface_id'] for r in rig}
        require(len(rig_ids) == len(rig), 'duplicate rig surfaces')
        require(variant['fit_surface_ids'] and set(variant['fit_surface_ids']) <= rig_ids, 'fit surface binding missing')
        require(set(variant['enclosure_surface_ids']) <= rig_ids, 'enclosure surface binding missing')
        for surface in rig:
            require(surface['role'] in ('rig', 'physical_occluder'), 'unsupported optical role')
            pv.rig_surface_triangles(surface)
            _, tau = pv.surface_optics(surface)
            require(tau == 0, 'reflection attribution currently requires opaque rig surfaces')
        jobs += len(seeds) * (len(cal)*len(rhos)*len(offsets) + len(pts)*3)
    require(jobs <= solver['max_native_jobs'], f'native job budget exceeded: {jobs} > {solver["max_native_jobs"]}')
    return jobs


def freeze(plan_path: Path, out: Path) -> dict:
    """Freeze ALL variants/splits before fit; no geometry chosen against validation readings."""
    data = read_json(plan_path); base = plan_path.parent
    sources = {str(plan_path.resolve()): file_hash(plan_path)}
    for variant in data['variants']:
        for field, cols in [('rig_surfaces', pv.RIG_SURFACE_COLUMNS), ('sensors', pv.SENSOR_COLUMNS),
                            ('points', pv.POINT_COLUMNS), ('readings', pv.READING_COLUMNS)]:
            p = (base/variant[field]).resolve(); sources[str(p)] = file_hash(p)
            variant[{'rig_surfaces':'rig'}.get(field, field)+'_data'] = rows(p, cols)
        path = (base/variant['scene']).resolve(); sources[str(path)] = file_hash(path)
        scene = load_scene(path); adapter = pv.lamp_adapter(path, scene)
        require(not adapter['unsupported_fixtures'], f'unsupported lamp: {adapter["unsupported_fixtures"]}')
        require(sum(f.photon_flux_umol_s.value for f in scene.fixtures) > 0, 'positive declared flux normalization required')
        variant['scene_data'] = read_json(path)
        variant['absolute_blockers'] = pv.absolute_blockers(scene, {}, variant['rig_data'],
            {s['sensor_id']:s for s in variant['sensors_data']}, variant['points_data'],
            [dict(fixture_id=f.fixture_id, is_full_output='yes') for f in scene.fixtures], False)
    jobs = validate_plan(data)
    data.update(source_hashes=sources, code_hashes=code_hashes(), max_planned_native_jobs=jobs, frozen=True)
    data['plan_sha256'] = digest(data)
    folder = output_dir(out); write_json(folder/'frozen_plan.json', data)
    return dict(status='frozen', planned_native_jobs=jobs, plan_sha256=data['plan_sha256'])


def load_frozen(folder: Path) -> dict:
    p = read_json(folder/'frozen_plan.json')
    require(p.get('frozen') is True and digest({k:v for k,v in p.items() if k != 'plan_sha256'}) == p['plan_sha256'],
            'frozen plan hash mismatch')
    for name, expected in p['source_hashes'].items():
        require(file_hash(Path(name)) == expected, f'source changed since freeze: {name}')
    require(p.get('code_hashes') == code_hashes(), 'code changed since freeze; freeze a new plan')
    validate_plan(p)
    return p


class NativeEvaluator:
    """One probe per run avoids artificial inter-probe shadowing/reflection interception."""
    def __init__(self, plan, out, java='java', core=CORE):
        self.plan, self.out, self.java, self.core = plan, out, java, core
        self.jobs = []

    def __call__(self, variant, points, rho, offset, scale, rays, seed, control='full'):
        factor = photon_factor(self.plan['wavelength_nm'])
        scene = deepcopy(variant['scene_data'])
        for fx in scene['fixtures']:
            # Explicit monochromatic W bookkeeping; convert back once at the receiver.
            fx['photon_flux_umol_s']['value'] *= scale/factor
            if self.plan.get('offset_axis'):
                fx['emitting_center_grow_mm']['value']['xyz'.index(self.plan['offset_axis'])] += offset
        rig = deepcopy(variant['rig_data'])
        for surface in rig:
            if surface['surface_id'] in variant['fit_surface_ids']: surface['reflectance'] = rho
            if control == 'black_rig': surface['reflectance'] = 0.
        if control == 'enclosure_free':
            rig = [s for s in rig if s['surface_id'] not in variant['enclosure_surface_ids']]
        sensors = {s['sensor_id']:s for s in variant['sensors_data']}
        result = []
        for point in points:
            require(len(self.jobs) < self.plan['solver']['max_native_jobs'], 'native runtime job budget exceeded')
            folder = self.out/f'job_{len(self.jobs):05d}'; folder.mkdir()
            write_json(folder/'scene_radiometric_internal.json', scene)
            adapter = pv.lamp_adapter(folder/'scene_radiometric_internal.json')
            adapter['power_convention'] = 'monochromatic_W_from_declared_photon_flux'
            write_json(folder/'adapter.json', adapter)
            tri, area_mm2 = pv.sensing_mesh(point, sensors[point['sensor_id']], variant.get('disc_segments'))
            code = pv.make_job_rgg(adapter['initialization_rgg'], rays, self.plan['solver']['max_depth'], seed,
                                   rig=rig, probes=[('sensor', tri)])
            (folder/'Model.rgg').write_text(code, encoding='utf-8')
            job = dict(folder=str(folder.resolve()), point_id=point['point_id'], control=control,
                       rays=rays, seed=seed, wavelength_nm=self.plan['wavelength_nm'],
                       model_sha256=file_hash(folder/'Model.rgg'), status='started')
            self.jobs.append(job); write_json(self.out/'native_jobs.json', self.jobs)
            run_groimp(folder, self.core, self.java, timeout_s=self.plan['solver']['timeout_s'])
            _, raw = pv.parse_log(folder/'groimp.log')
            raw_lines = re.findall(r'^PROBE\t', (folder/'groimp.log').read_text(encoding='utf-8', errors='replace'), re.M)
            require(len(raw_lines) == len(tri), 'missing/duplicate probe lines')
            require(set(raw) == {f'sensor:{i}' for i in range(len(tri))}, 'missing/duplicate probe output')
            power = sum(raw.values()); finite(power, 'sensor absorbed W', 0)
            q = power*factor/(area_mm2*1e-6)
            job.update(status='completed', log_sha256=file_hash(folder/'groimp.log'),
                       sensor_absorbed_W=power, ppfd_umol_m2_s=q)
            write_json(self.out/'native_jobs.json', self.jobs); result.append(q)
        return np.asarray(result)


def fit_scale(predicted, measured, bounds):
    x, y = np.asarray(predicted), np.asarray(measured)
    require(x.shape == y.shape and np.isfinite(x).all() and (x >= 0).all(), 'invalid model predictions')
    require(float(x@x) > 0, 'zero illumination cannot identify flux')
    return float(np.clip((x@y)/(x@x), *bounds))


def metrics(predicted, measured):
    x, y = np.asarray(predicted), np.asarray(measured); e = x-y
    mean = float(y.mean()); rms = float(np.sqrt(np.mean(e*e)))
    return dict(rmse_umol_m2_s=rms, bias_umol_m2_s=float(e.mean()),
                rms_percent_of_mean=100*rms/mean if mean else None,
                bias_percent_of_mean=100*float(e.mean())/mean if mean else None, n=len(y))


def run(frozen: Path, out: Path, java='java', core=CORE, evaluator_factory=NativeEvaluator):
    plan = load_frozen(frozen); folder = output_dir(out)
    executed_hashes = code_hashes()
    snapshot = folder/'code_snapshot'; snapshot.mkdir()
    for name in executed_hashes:
        target = snapshot/Path(name).relative_to(Path(__file__).resolve().parents[1])
        target.parent.mkdir(parents=True, exist_ok=True); target.write_bytes(Path(name).read_bytes())
    write_json(folder/'frozen_plan.json', plan)
    engine = evaluator_factory(plan, folder, java, core)
    results, predictions = [], []
    solver = plan['solver']; seeds = solver['seeds']
    for variant in plan['variants']:
        points = variant['points_data']; cal = [p for p in points if p['split_role'] == 'calibration']
        measured = {p['point_id']: float(np.mean([float(r['ppfd_umol_m2_s']) for r in variant['readings_data']
                                                 if r['point_id'] == p['point_id']])) for p in points}
        y = np.array([measured[p['point_id']] for p in cal]); candidates = []
        for rho, offset in itertools.product(plan['reflectance_grid'], plan.get('offset_grid_mm') or [0.]):
            q = np.mean([engine(variant, cal, rho, offset, 1., solver['coarse_rays'], seed) for seed in seeds], axis=0)
            scale = fit_scale(q, y, plan['bounds']['photon_flux_scale'])
            candidates.append(dict(effective_reflectance_grey=rho, offset_mm=offset,
                                   photon_flux_scale=scale, **metrics(q*scale, y)))
        best = min(candidates, key=lambda c:c['rmse_umol_m2_s'])
        ensembles = {}
        for control in ('full', 'black_rig', 'enclosure_free'):
            ensembles[control] = np.array([engine(variant, points, best['effective_reflectance_grey'],
                best['offset_mm'], best['photon_flux_scale'], solver['final_rays'], seed, control) for seed in seeds])
        mean = {k:v.mean(axis=0) for k,v in ensembles.items()}
        se = ensembles['full'].std(axis=0, ddof=1)/math.sqrt(len(seeds))
        delta = ensembles['full']-ensembles['black_rig']
        delta_mean = delta.mean(axis=0); delta_se = delta.std(axis=0, ddof=1)/math.sqrt(len(seeds))
        bound_hits = [k for k in ('photon_flux_scale', 'effective_reflectance_grey') if best[k] in plan['bounds'][k]]
        if plan.get('offset_grid_mm') and best['offset_mm'] in (plan['offset_grid_mm'][0], plan['offset_grid_mm'][-1]):
            bound_hits.append('offset_mm')
        result = dict(variant_id=variant['variant_id'], source_kind='fitted', fitted_parameters=best,
            fitted_at_rays=solver['coarse_rays'], evaluated_at_rays=solver['final_rays'], seeds=seeds,
            candidates=candidates, bound_hits=bound_hits, parameter_interval=None,
            parameter_interval_reason='discrete_profile_only_no_identified_statistical_interval',
            conditional_reasons=variant['conditional_reasons'], absolute_blockers=variant.get('absolute_blockers', []),
            definitive_validation='unavailable',
            bounce_method='paired_seed_total_minus_same_geometry_black_opaque_rig',
            bounce_limits='reflection-only opaque static rig; not terminal photon closure; no clipping of negative estimates',
            terminal_escape=None, termination=None, per_band=None)
        for role in pv.ROLES:
            ix = [i for i,p in enumerate(points) if p['split_role'] == role]
            result[role] = metrics(mean['full'][ix], [measured[points[i]['point_id']] for i in ix])
        results.append(result)
        for i,p in enumerate(points):
            predictions.append(dict(variant_id=variant['variant_id'], point_id=p['point_id'], split_role=p['split_role'],
                **{k:p[k] for k in ('x_mm', 'y_mm', 'z_mm')}, measured_ppfd_umol_m2_s=measured[p['point_id']],
                predicted_ppfd_umol_m2_s=float(mean['full'][i]), seed_standard_error_umol_m2_s=float(se[i]),
                black_rig_ppfd_umol_m2_s=float(mean['black_rig'][i]), enclosure_free_ppfd_umol_m2_s=float(mean['enclosure_free'][i]),
                post_reflection_estimate_umol_m2_s=float(delta_mean[i]), post_reflection_standard_error_umol_m2_s=float(delta_se[i]),
                post_reflection_fraction=float(delta_mean[i]/mean['full'][i]) if mean['full'][i] > 0 and 0 <= delta_mean[i] <= mean['full'][i] else None,
                rays=solver['final_rays'], source_kind='fitted', status='conditional'))
    write_rows(folder/'conditional_predictions.csv', predictions, PRED_COLUMNS)
    report = dict(schema_version='p2-native-lamp-fit-1', status='conditional', plan_sha256=plan['plan_sha256'],
                  variants=results, source_hashes=plan['source_hashes'],
                  code_hashes=executed_hashes,
                  definitive_validation='unavailable', physical_accuracy_validated=False,
                  native_runtime=dict(core=str(Path(core).resolve()), core_sha256=file_hash(Path(core)) if Path(core).is_file() else None,
                                      java_command=java),
                  power_convention='umol/s -> monochromatic W -> umol/m2/s, exactly once each',
                  analytic_diffuse_fraction_is_validation_truth=False,
                  artifact_hashes={str(p.relative_to(folder)):file_hash(p) for p in folder.rglob('*') if p.is_file()})
    require(code_hashes() == executed_hashes, 'code changed during native execution; result not finalized')
    for name, sha in plan['source_hashes'].items():
        require(file_hash(Path(name)) == sha, 'source changed during native execution; result not finalized')
    write_json(folder/'fit.json', report)
    return report


def export_reference(fit_path: Path, variant_id: str, contract_path: Path, out: Path):
    """Export a frozen field with explicit frame/time evidence; no inferred spatial transform."""
    from tools.reference_dli_frozen import SCHEMA as FIELD_SCHEMA, COLUMNS
    fit = read_json(fit_path); base = fit_path.parent; contract = read_json(contract_path)
    require(fit.get('schema_version') == 'p2-native-lamp-fit-1', 'unsupported fit schema')
    for name, sha in fit['artifact_hashes'].items():
        require(file_hash(base/name) == sha, 'fit artifact hash mismatch')
    for name, sha in {**fit['source_hashes'], **fit['code_hashes']}.items():
        require(file_hash(Path(name)) == sha, 'fit source/code hash mismatch')
    plan = read_json(base/'frozen_plan.json')
    variant = next((v for v in plan['variants'] if v['variant_id'] == variant_id), None)
    require(variant is not None, 'unknown variant')
    for key in ('frame_id', 'coordinate_frame', 'height_basis', 'time_support'):
        require(contract.get(key), f'reference export requires {key}')
    require(contract['coordinate_frame'] == 'grow_mm_z_up', 'export uses grow frame; explicit external transform required')
    # Preserve the fitted photon scene, not the solver's intermediate radiometric numbers.
    scene = deepcopy(variant['scene_data'])
    fitted = next(v for v in fit['variants'] if v['variant_id'] == variant_id)['fitted_parameters']
    for fx in scene['fixtures']:
        fx['photon_flux_umol_s'].update(value=fx['photon_flux_umol_s']['value']*fitted['photon_flux_scale'],
                                       status='fitted', source=f'fit sha256 {file_hash(fit_path)}')
        if plan.get('offset_axis'):
            centre = fx['emitting_center_grow_mm']; centre['value']['xyz'.index(plan['offset_axis'])] += fitted['offset_mm']
            centre.update(status='fitted', source=f'fit sha256 {file_hash(fit_path)}')
    folder = output_dir(out); write_json(folder/'scene.json', scene)
    table = [dict(point_id=p['point_id'], **{k:p[k] for k in ('x_mm','y_mm','z_mm')},
                  ppfd_umol_m2_s=p['predicted_ppfd_umol_m2_s'],
                  seed_standard_error_umol_m2_s=p['seed_standard_error_umol_m2_s'])
             for p in rows(base/'conditional_predictions.csv') if p['variant_id'] == variant_id]
    write_rows(folder/'predictions.csv', table, COLUMNS)
    hashes = {str(p.resolve()):file_hash(p) for p in (fit_path, base/'frozen_plan.json', contract_path, folder/'scene.json')}
    hashes.update(fit['source_hashes']); hashes.update(fit['code_hashes'])
    support = deepcopy(contract['time_support'])
    if support.get('source_ref'):
        support['source_ref']['path'] = str((contract_path.parent/support['source_ref']['path']).resolve())
    data = dict(schema_version=FIELD_SCHEMA, quantity='incident', unit='umol/m2/s', source_kind='fitted',
        frame_id=contract['frame_id'], coordinate_frame=contract['coordinate_frame'], height_basis=contract['height_basis'],
        sensor_normal=[0,0,1], predictions_csv='predictions.csv', predictions_sha256=file_hash(folder/'predictions.csv'),
        fit_ref=str(fit_path.resolve()), scene_ref='scene.json', source_hashes=hashes,
        fixture_ids=[f['fixture_id'] for f in variant['scene_data']['fixtures']],
        output_basis='all_fixtures_full_photon_output', fixed_optics_beam_spectrum=True, time_support=support,
        conditional_reasons=sorted(set(variant['conditional_reasons']+variant.get('absolute_blockers', [])+
                                       ['physical_accuracy_unvalidated', 'parameter_interval_unidentified'])),
        uncertainty=dict(random_kind='native_seed_standard_error', systematic_status='unavailable'),
        variant_id=variant_id, spectral_fractions=plan.get('spectral_fractions'),
        wavelength_nm=plan['wavelength_nm'], source_plan_sha256=plan['plan_sha256'])
    write_json(folder/'frozen_prediction.json', data)
    return dict(status='conditional', path=str(folder/'frozen_prediction.json'))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__); sub = parser.add_subparsers(dest='command', required=True)
    a = sub.add_parser('audit'); a.add_argument('--records', type=Path, required=True); a.add_argument('--operating', type=Path, required=True)
    f = sub.add_parser('freeze'); f.add_argument('--plan', type=Path, required=True)
    r = sub.add_parser('run'); r.add_argument('--frozen', type=Path, required=True); r.add_argument('--java', default='java'); r.add_argument('--core', type=Path, default=CORE)
    e = sub.add_parser('export-reference'); e.add_argument('--fit', type=Path, required=True)
    e.add_argument('--variant', required=True); e.add_argument('--contract', type=Path, required=True)
    for cmd in (a, f, r, e): cmd.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'audit': result = audit(args.records, args.operating, args.out)
        elif args.command == 'freeze': result = freeze(args.plan, args.out)
        elif args.command == 'run': result = run(args.frozen, args.out, args.java, args.core)
        else: result = export_reference(args.fit, args.variant, args.contract, args.out)
        print(dict(status=result['status'], out=str(args.out)))
        return 0
    except (StudyError, OSError, ValueError, KeyError) as exc: parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
