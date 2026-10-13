"""Explicit, evidence-gated calibration of the proposed compound growth laws.

python -X utf8 -m tools.growth_calibration --help
No fitting occurs during forecast. All writers create a fresh build directory.
"""
from __future__ import annotations

import argparse
import csv
from copy import deepcopy
from datetime import datetime, timezone
import json
import math
from pathlib import Path
import platform
import re
import sys
from typing import Any

import numpy as np
import scipy
from scipy.optimize import minimize, brentq
from scipy.special import i0e, logsumexp
from scipy.stats import norm, lognorm, vonmises

from tools.compound_growth import aware_time
from tools.growth_observation_evidence import load_evidence, attach_evidence, calibration_reasons, CONTINUITY
from tools.leaf_light.common import StudyError, digest, file_hash, number, output_dir, read_json, rows, write_json

SCHEMA = 'growth-calibration-1'
KINDS = {'measured', 'user_assumed', 'literature_informed', 'fitted', 'unidentified'}
FAMILIES = {'anchored_expansion', 'azimuth_rotation', 'lognormal_wait'}
COLUMNS = ('record_id', 'plant_id', 'organ_id', 'target_id', 'unit_id', 'observed_at',
           'origin_at', 'elapsed_days', 'value', 'initial_value', 'unit', 'frame_id',
           'identity_status', 'coverage_basis', 'age_basis', 'measurement_sd',
           'lower_day', 'upper_day', 'censoring', 'visibility_status', 'split',
           'capture_phase', 'exposure_kind')
NUMERIC = {'elapsed_days', 'value', 'initial_value', 'measurement_sd', 'lower_day', 'upper_day'}
FAMILY_UNITS = {
    'anchored_expansion': {'k': '1/calendar_day'},
    'azimuth_rotation': {'D': 'rad', 'k': '1/calendar_day'},
    'lognormal_wait': {'mu': 'log(calendar_day/reference_day)', 'sigma': 'dimensionless', 'stop': 'probability'},
}
#: Meaning of a fitted role (source) and of a calculator coordinate (destination). A binding is
#: accepted only when the meanings are equal; equal units alone are not enough (e.g. a fitted
#: increment in mm must not become the absolute side-extent target in mm). A conversion between
#: different meanings needs a separately reviewed contract and measured anchor; none is implemented.
ROLE_MEANING = {
    ('anchored_expansion', 'D'): 'remaining_increment',
    ('anchored_expansion', 'k'): 'rate',
    ('azimuth_rotation', 'D'): 'angular_amplitude',
    ('azimuth_rotation', 'k'): 'rate',
    ('lognormal_wait', 'mu'): 'log_positive_wait_location',
    ('lognormal_wait', 'sigma'): 'log_positive_wait_scale',
    ('lognormal_wait', 'stop'): 'stop_probability',
}
COORDINATE_MEANING = {
    'D_length_mm': 'remaining_increment', 'D_segment_mm': 'remaining_increment', 'D_area_cm2': 'remaining_increment',
    'k_length': 'rate', 'k_width': 'rate', 'k_rotation': 'rate',
    'k_area': 'rate', 'k_segment': 'rate',
    'left_target_mm': 'absolute_extent_target_at_reference_DLI', 'right_target_mm': 'absolute_extent_target_at_reference_DLI',
    'birth_axis_length_mm': 'birth_value', 'birth_left_extent_mm': 'birth_value',
    'birth_right_extent_mm': 'birth_value', 'birth_area_cm2': 'birth_value',
    'azimuth_rad': 'angular_offset', 'elevation_rad': 'angular_offset',
    'rotation_x_rad': 'angular_amplitude', 'rotation_y_rad': 'angular_amplitude', 'rotation_z_rad': 'angular_amplitude',
    'wait_dev_days': 'positive_wait',
}
for _trait, _unit_name in {'length':'mm','left':'mm','right':'mm','segment':'mm','area':'cm2'}.items():
    COORDINATE_MEANING.update({f'{_trait}_x_max_{_unit_name}':'absolute_potential_maximum',
        f'{_trait}_a_m_dev_days':'beta_timing',f'{_trait}_a_e_dev_days':'beta_timing',
        f'{_trait}_a_m_over_a_e':'dimensionless_ratio'})


def _contains_l02(value: Any) -> bool:
    if isinstance(value,dict): return any(_contains_l02(x) for x in value.values())
    if isinstance(value,(list,tuple)): return any(_contains_l02(x) for x in value)
    if not isinstance(value,str): return False
    return bool(re.search(r'(?<![A-Za-z0-9])L02(?![A-Za-z0-9])',value,re.IGNORECASE)) or value in {
        'directional_light_moment','normalized_first_moment','M_over_norm_M','dominant_light_direction'}


def _check_binding_meaning(target: dict, role: str, coordinate: str, provenance: Any = None) -> None:
    source = ROLE_MEANING.get((target['family'], role))
    destination = COORDINATE_MEANING.get(coordinate)
    if (destination in ('angular_offset','angular_amplitude') or coordinate=='k_rotation') and _contains_l02([target,provenance]):
        raise StudyError('L02 directional light descriptors cannot bind P3 direction coordinates without an adopted response law')
    if source is None or destination is None:
        raise StudyError(f'Binding meaning undeclared for {target["family"]}.{role} -> {coordinate}; refusing')
    if source != destination:
        raise StudyError(f'Binding meaning mismatch: {target["family"]}.{role} is {source} but {coordinate} is '
                         f'{destination}; cross-meaning conversion is undeclared and is not implemented')


def _object(value: Any) -> dict:
    return deepcopy(value) if isinstance(value, dict) else read_json(Path(value))


def _issue(component: str, reason: str, source: Any = None) -> dict:
    return dict(component=component, reason_code=reason, source=source)


def _finite(value: Any, label: str) -> float:
    if isinstance(value, bool):
        raise StudyError(label + ': boolean is not numeric')
    return number(value, label)


def _csv(path: Path, records: list[dict], columns: list | tuple) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns)
        writer.writeheader()
        writer.writerows({k: '' if r.get(k) is None else r.get(k) for k in columns} for r in records)


def validate_evidence_registry(registry: dict | str | Path) -> tuple[list[dict], list[dict]]:
    """Validate dimensional/source semantics; never assign scientific acceptance."""
    reg = _object(registry)
    if reg.get('schema_version') != SCHEMA:
        raise StudyError('Unsupported evidence schema')
    result, issues, seen = [], [], set()
    for r in reg.get('records', []):
        if not r.get('id') or r['id'] in seen:
            raise StudyError('Duplicate/missing evidence ID')
        seen.add(r['id'])
        if r.get('source_kind') not in KINDS:
            raise StudyError('Unknown evidence kind')
        if r.get('value') is not None:
            _finite(r['value'], 'evidence value')
            if not r.get('unit'):
                raise StudyError('Evidence value requires unit')
        if r.get('source_kind') == 'unidentified' and r.get('value') is not None:
            raise StudyError('Unidentified evidence cannot contain a value')
        for k in ('source_ref', 'locator', 'source_version', 'applicability', 'review_status'):
            if not r.get(k):
                issues.append(_issue(r['id'], 'missing_' + k))
        if r.get('source_kind') == 'literature_informed':
            for k in ('cultivar', 'conditions', 'organ', 'stage', 'evidence_role', 'experimental_unit'):
                if not r.get(k):
                    issues.append(_issue(r['id'], 'unknown_' + k, r.get('source_ref')))
            if r.get('evidence_role') == 'borrowed' and not r.get('original_source_ref'):
                issues.append(_issue(r['id'], 'borrowed_source_not_traced'))
        if r.get('unit') in ('rad', 'deg') and not r.get('angle_reference'):
            issues.append(_issue(r['id'], 'angle_reference_missing'))
        uncertainty = r.get('uncertainty')
        if uncertainty and uncertainty.get('value') is not None:
            if uncertainty.get('kind') not in ('SD', 'SE', 'CI'):
                raise StudyError('Uncertainty must distinguish SD, SE and CI')
            if uncertainty['kind'] == 'CI':
                a, b = uncertainty['value']
                if _finite(a, 'CI') > _finite(b, 'CI') or not 0 < uncertainty.get('level', 0) < 1:
                    raise StudyError('Invalid confidence interval')
            elif _finite(uncertainty['value'], 'uncertainty') < 0:
                raise StudyError('Negative uncertainty')
        result.append(r)
    return result, issues


def _load(observation_refs: dict | str | Path | None) -> tuple[list[dict], dict]:
    if observation_refs is None:
        return [], dict(data_kind='unavailable', source_hashes={})
    ref = _object(observation_refs)
    if ref.get('schema_version') != SCHEMA or ref.get('data_kind') not in ('synthetic', 'observed'):
        raise StudyError('Invalid calibration observation manifest')
    base = Path(observation_refs).resolve().parent if not isinstance(observation_refs, dict) else Path(ref.get('base_dir', '.')).resolve()
    hashes = dict(ref.get('source_hashes', {}))
    if not isinstance(observation_refs, dict):
        hashes[str(Path(observation_refs).resolve())] = file_hash(Path(observation_refs))
    if not ref.get('observations'):
        return [], dict(ref, source_hashes=hashes)
    entry = ref['observations']; path = (base / entry['path']).resolve()
    if file_hash(path) != entry.get('sha256'):
        raise StudyError('Observation hash mismatch')
    hashes[str(path)] = entry['sha256']
    records = rows(path, COLUMNS)
    for i, record in enumerate(records, 2):
        record['source_row'] = dict(table_sha256=entry['sha256'],csv_line=i)
    evidence = load_evidence(ref, base, hashes)
    attach_evidence(records, evidence, calibration=True)
    records.sort(key=lambda r: r['record_id'])
    ids = set()
    for r in records:
        if not r['record_id'] or r['record_id'] in ids:
            raise StudyError('Duplicate/missing record_id')
        ids.add(r['record_id'])
        for k in NUMERIC:
            r[k] = number(r.get(k), k, missing=True)
    _unchanged(hashes)
    return records, dict(ref, source_hashes=hashes)


def _unchanged(hashes: dict) -> None:
    for path, sha in hashes.items():
        if file_hash(Path(path)) != sha:
            raise StudyError('Immutable source changed: ' + path)


def blank_plan() -> dict:
    return dict(schema_version=SCHEMA, model_version='stochastic-grammar-proposal-1',
                plan_id=None, review={'status': 'unreviewed', 'reviewer': None, 'source_ref': None},
                time_basis='calendar_day', applicability=None, targets=[], parameters={},
                split={'train_plants': [], 'validation_plants': [], 'train_units': [], 'validation_units': []},
                dependence=None, uncertainty=None, optimizer=None, engine_bindings=[],
                selection_frozen_at=None)


def _plan(plan: Any) -> tuple[dict, list[dict]]:
    p = _object(plan)
    if p.get('schema_version') != SCHEMA:
        raise StudyError('Unsupported fit plan')
    if p.get('model_version') != 'stochastic-grammar-proposal-1':
        raise StudyError('Unsupported equation/model version')
    missing = []
    for k in ('plan_id', 'applicability', 'targets', 'parameters', 'dependence', 'uncertainty', 'optimizer', 'selection_frozen_at'):
        if not p.get(k):
            missing.append(_issue('fit_plan', 'missing_' + k))
    if p.get('time_basis') != 'calendar_day':
        raise StudyError('Only explicit calendar-day fitting is implemented')
    split = p.get('split') or {}
    for kind in ('plants', 'units'):
        a, b = split.get('train_' + kind, []), split.get('validation_' + kind, [])
        if len(set(a)) != len(a) or len(set(b)) != len(b) or set(a) & set(b):
            raise StudyError('Split leakage/duplicates: ' + kind)
        if not a: missing.append(_issue('split', 'missing_train_' + kind))
    if p.get('selection_frozen_at'):
        aware_time(p['selection_frozen_at'])
    if missing:
        return p, missing
    if p['dependence'].get('kind') != 'assignment_unit_bootstrap' or not p['dependence'].get('source_ref'):
        raise StudyError('Declare assignment-unit dependence and its source')
    u = p['uncertainty']
    if u.get('method') != 'stratified_cluster_bootstrap' or type(u.get('replicates')) is not int or u['replicates'] < 2:
        raise StudyError('Declare >=2 whole-unit bootstrap replicates')
    if type(u.get('seed')) is not int or u['seed'] < 0 or u.get('stratify_by') != 'treatment_id':
        raise StudyError('Invalid bootstrap seed/stratum')
    if type(u.get('min_units_per_treatment')) is not int or u['min_units_per_treatment'] < 2:
        raise StudyError('At least two assignment units per treatment required for resampling')
    if not 0 < _finite(u['min_success_fraction'], 'bootstrap success') <= 1:
        raise StudyError('Invalid bootstrap success fraction')
    opt = p['optimizer']
    for key in ('ftol', 'gtol', 'finite_difference_step', 'hessian_relative_tolerance', 'bound_margin'):
        if _finite(opt[key], key) <= 0:
            raise StudyError('Positive numerical controls required')
    if type(opt.get('maxiter')) is not int or opt['maxiter'] <= 0:
        raise StudyError('Positive maxiter required')
    for name, spec in p['parameters'].items():
        if spec.get('status') not in ('fit', 'fixed') or not spec.get('unit') or not spec.get('source_ref'):
            raise StudyError('Incomplete parameter: ' + name)
        if spec.get('transform') not in ('identity', 'log'):
            raise StudyError('Unknown parameter transform')
        if spec['status'] == 'fit':
            lo, hi = map(float, spec['bounds']); initial = _finite(spec['initial'], name)
            if not math.isfinite(lo + hi) or not lo < initial < hi or not spec.get('bounds_source'):
                raise StudyError('Finite sourced bounds and interior initial value required')
            if spec['transform'] == 'log' and lo <= 0:
                raise StudyError('Log parameter requires positive bounds')
        else:
            if spec['transform'] == 'log' and _finite(spec['value'], name) <= 0:
                raise StudyError('Log parameter must be positive')
            _finite(spec['value'], name)
    names = set()
    for t in p['targets']:
        tid = t['id']
        if tid in names or t.get('family') not in FAMILIES:
            raise StudyError('Duplicate target or unsupported family')
        names.add(tid)
        if not t.get('equation_ref') or not t.get('unit'):
            raise StudyError('Target equation/unit required')
        if t.get('effect_interpretation') not in ('observational_association', 'experimental_contrast', 'synthetic_assumption'):
            raise StudyError('Declare association versus experimental effect interpretation')
        needed = ('mu', 'sigma', 'stop') if t['family'] == 'lognormal_wait' else ('D', 'k')
        if set(t['parameters']) != set(needed):
            raise StudyError('Target parameter roles differ from declared equation')
        for role in needed:
            name = t['parameters'][role]
            if name not in p['parameters']:
                raise StudyError('Unknown target parameter')
            expected = FAMILY_UNITS[t['family']].get(role, t['unit'])
            if p['parameters'][name]['unit'] != expected:
                raise StudyError('Parameter unit mismatch: ' + name)
        if t['family'] == 'azimuth_rotation' and (t['unit'] != 'rad' or not t.get('angle_reference')):
            raise StudyError('Angular target requires radians and reference')
        if t['family'] == 'lognormal_wait':
            if t['unit'] != 'calendar_day' or _finite(t['reference_day'], 'reference_day') <= 0 or t.get('event_endpoint') not in ('residual_wait', 'inter_event_wait'):
                raise StudyError('Event endpoint/time reference required')
        else:
            e = t.get('observation_error') or {}
            expected = 'von_mises' if t['family'] == 'azimuth_rotation' else 'gaussian'
            if e.get('kind') != expected or not e.get('source_ref'):
                raise StudyError('Explicit compatible observation-error model required')
            if expected == 'von_mises' and _finite(e['kappa'], 'kappa') <= 0:
                raise StudyError('Positive von Mises concentration required')
            if expected == 'gaussian' and not 0 <= _finite(e['within_series_rho'], 'rho') < 1:
                raise StudyError('Gaussian series correlation must be in [0,1)')
        feats = t.get('features', [])
        if len({f['column'] for f in feats}) != len(feats):
            raise StudyError('Duplicate response feature')
        for f in feats:
            if f['role'] not in needed or f.get('link') not in ('identity', 'log'):
                raise StudyError('Invalid response role/link')
            if f['coefficient'] not in p['parameters'] or not f.get('unit') or not f.get('source_ref'):
                raise StudyError('Incomplete response evidence')
            if _finite(f['scale'], 'feature scale') <= 0:
                raise StudyError('Positive feature scale required')
            _finite(f['center'], 'feature center')
            lo, hi = f['domain']
            if _finite(lo, 'feature lower') >= _finite(hi, 'feature upper'):
                raise StudyError('Invalid feature domain')
            unit = 'dimensionless' if f['link'] == 'log' else p['parameters'][t['parameters'][f['role']]]['unit']
            if p['parameters'][f['coefficient']]['unit'] != unit:
                raise StudyError('Response coefficient unit mismatch')
    return p, []


def audit_calibration_data(observation_refs: Any, treatment_manifest: Any, fit_plan: Any) -> dict:
    p, issues = _plan(fit_plan)
    data, context = _load(observation_refs)
    tr = _object(treatment_manifest) if treatment_manifest is not None else {'units': []}
    units = {u['unit_id']: u for u in tr.get('units', [])}
    if len(units) != len(tr.get('units', [])):
        raise StudyError('Duplicate assignment units')
    for u in units.values():
        if any(not u.get(k) for k in ('treatment_id', 'run_id', 'source_ref')):
            raise StudyError('Incomplete assignment-unit evidence')
    hashes = dict(context['source_hashes'])
    for obj in (treatment_manifest, fit_plan):
        if isinstance(obj, (str, Path)):
            hashes[str(Path(obj).resolve())] = file_hash(Path(obj))
    if not data: issues.append(_issue('observations', 'no_observations_supplied'))
    review = p.get('review') or {}
    allowed = ('reviewed', 'synthetic_assumption') if context['data_kind'] == 'synthetic' else ('reviewed',)
    if review.get('status') not in allowed or not review.get('reviewer') or not review.get('source_ref'):
        issues.append(_issue('fit_plan', 'scientific_review_missing'))
    if issues:
        return dict(status='unavailable', eligible_targets=[], missing_evidence=issues,
                    identifiability_flags=[], source_hashes=hashes, data_kind=context['data_kind'],
                    record_count=len(data), targets=[], plan_hash=digest(p), treatment_hash=digest(tr))
    split = p['split']; targets = {t['id']: t for t in p['targets']}
    target_issues = {tid: [] for tid in targets}
    for tid, target in targets.items():
        ri = target_issues[tid]
        if context['data_kind'] == 'observed' and target['effect_interpretation'] == 'synthetic_assumption':
            ri.append(_issue(tid, 'synthetic_interpretation_on_real_data'))
        if target['effect_interpretation'] == 'experimental_contrast':
            for key in ('randomization_ref', 'blocking_ref', 'controlled_conditions_ref'):
                if not tr.get('design', {}).get(key): ri.append(_issue(tid, 'missing_' + key))
        if target['family'] == 'azimuth_rotation' and context.get('target_metadata', {}).get(tid, {}).get('angle_reference') != target['angle_reference']:
            ri.append(_issue(tid, 'angle_reference_mismatch'))
        for feature in target.get('features', []):
            if context.get('feature_units', {}).get(feature['column']) != feature['unit']:
                ri.append(_issue(tid, 'feature_unit_missing_or_mismatched', feature['column']))
            if feature.get('kind') in ('spectral', 'directional') and not context.get('feature_provenance', {}).get(feature['column']):
                ri.append(_issue(tid, 'spectrum_or_direction_evidence_missing', feature['column']))
    plant_units, series, event_keys = {}, {}, set()
    for r in data:
        if r['target_id'] not in targets:
            raise StudyError('Unknown observation target')
        tid = r['target_id']; t = targets[tid]; ri = target_issues[tid]
        ri.extend(_issue(tid, reason, r['record_id']) for reason in calibration_reasons(r, t, context))
        for key in ('plant_id', 'organ_id', 'frame_id', 'age_basis', 'capture_phase'):
            if not r.get(key): ri.append(_issue(tid, 'missing_' + key, r['record_id']))
        if r['identity_status'] != 'confirmed': ri.append(_issue(tid, 'unconfirmed_identity', r['record_id']))
        if r['unit'] != t['unit']: raise StudyError('Observation unit mismatch: ' + tid)
        if r['unit_id'] not in units: ri.append(_issue(tid, 'assignment_unit_missing', r['record_id']))
        if r['plant_id'] in plant_units and plant_units[r['plant_id']] != r['unit_id']:
            raise StudyError('Plant appears in multiple assignment units')
        plant_units[r['plant_id']] = r['unit_id']
        if r['split'] not in ('train', 'validation'):
            raise StudyError('Explicit train/validation split required')
        if r['plant_id'] not in split[r['split'] + '_plants'] or r['unit_id'] not in split[r['split'] + '_units']:
            raise StudyError('Record violates frozen plant/unit split')
        if not r['observed_at'] or not r['origin_at']:
            ri.append(_issue(tid, 'timestamp_missing', r['record_id'])); continue
        elapsed = (aware_time(r['observed_at']) - aware_time(r['origin_at'])).total_seconds() / 86400
        if elapsed < 0 or r['elapsed_days'] is None or not math.isclose(elapsed, r['elapsed_days'], abs_tol=1e-8):
            raise StudyError('Timestamp/elapsed-time mismatch')
        if r['age_basis'] != t.get('age_basis'):
            ri.append(_issue(tid, 'age_endpoint_mismatch', r['record_id']))
        if t.get('coverage_basis') and r['coverage_basis'] != t['coverage_basis']:
            ri.append(_issue(tid, 'incomparable_coverage', r['record_id']))
        if t['family'] == 'lognormal_wait':
            event_key = (r['plant_id'], r['organ_id'], tid, r['origin_at'])
            if event_key in event_keys:
                raise StudyError('Duplicate event endpoint: do not count successive censoring records as independent events')
            event_keys.add(event_key)
            if r['visibility_status'] != 'confirmed': ri.append(_issue(tid, 'event_visibility_unconfirmed', r['record_id']))
            l, u = r['lower_day'], r['upper_day']
            if r['censoring'] not in ('interval', 'right') or l is None or l < 0:
                raise StudyError('Event must retain a valid interval/right censoring')
            if r['censoring'] == 'interval' and (u is None or u <= l or u > elapsed):
                raise StudyError('Invalid appearance interval')
            if r['censoring'] == 'right' and (u is not None or l > elapsed):
                raise StudyError('Invalid right censoring')
        else:
            if r['value'] is None or r['initial_value'] is None:
                ri.append(_issue(tid, 'state_or_anchor_missing', r['record_id']))
            if t['family'] == 'anchored_expansion' and (r['measurement_sd'] is None or r['measurement_sd'] <= 0):
                ri.append(_issue(tid, 'measurement_error_missing', r['record_id']))
            key = (r['plant_id'], r['organ_id'], tid, r['origin_at'])
            group = series.setdefault(key, [])
            if any(old['elapsed_days'] == r['elapsed_days'] for old in group):
                raise StudyError('Duplicate series time; provide a replicate measurement model')
            if group and any(r[k] != group[0][k] for k in ('initial_value', 'frame_id', 'coverage_basis')):
                raise StudyError('Series anchor/frame/coverage changed')
            trait = 'area' if t['unit'] == 'cm2' else 'direction' if t['family'] == 'azimuth_rotation' else None
            if group and trait:
                old = group[0].get('observation_evidence', {}).get(trait, {})
                new = r.get('observation_evidence', {}).get(trait, {})
                if any(old.get(k) != new.get(k) for k in CONTINUITY):
                    ri.append(_issue(tid, trait + '_method_or_support_changed', r['record_id']))
            group.append(r)
        for f in t.get('features', []):
            val = number(r.get(f['column']), f['column'], missing=True)
            if val is None:
                ri.append(_issue(tid, 'response_input_missing', r['record_id']))
            elif not f['domain'][0] <= val <= f['domain'][1]:
                ri.append(_issue(tid, 'response_outside_domain', r['record_id']))
            if r['split'] == 'train' and r['exposure_kind'] != 'observed_history':
                ri.append(_issue(tid, 'training_exposure_not_observed', r['record_id']))
            if f.get('basis') not in ('constant_exposure',):
                ri.append(_issue(tid, 'response_history_basis_not_supported', f['column']))
    summaries, flags = [], []
    for tid, t in targets.items():
        train = [r for r in data if r['target_id'] == tid and r['split'] == 'train']
        ri = target_issues[tid]
        if not train: ri.append(_issue(tid, 'no_training_targets'))
        count_by_treatment = {}
        for uid in {r['unit_id'] for r in train}:
            if uid in units: count_by_treatment.setdefault(units[uid]['treatment_id'], set()).add(uid)
        if any(len(v) < p['uncertainty']['min_units_per_treatment'] for v in count_by_treatment.values()):
            ri.append(_issue(tid, 'insufficient_independent_treatment_units'))
        if t['family'] != 'lognormal_wait':
            groups = [g for key, g in series.items() if key[2] == tid and g[0]['split'] == 'train']
            if not groups or any(len({r['elapsed_days'] for r in g if r['elapsed_days'] > 0}) < 2 for g in groups):
                ri.append(_issue(tid, 'endpoint_only_cannot_identify_dynamics'))
            for g in groups:
                for f in t.get('features', []):
                    if len({r.get(f['column']) for r in g}) > 1:
                        ri.append(_issue(tid, 'nonconstant_history_requires_integrated_response', f['column']))
        feature_columns = list(dict.fromkeys(f['column'] for f in t.get('features', [])))
        if train and feature_columns and not any(x['reason_code'] == 'response_input_missing' for x in ri):
            X = np.asarray([[1] + [float(r[k]) for k in feature_columns] for r in train])
            scales = np.std(X[:, 1:], axis=0)
            if np.any(scales == 0):
                ri.append(_issue(tid, 'constant_input_cannot_identify_response'))
            else:
                X[:, 1:] = (X[:, 1:] - X[:, 1:].mean(axis=0)) / scales
                if np.linalg.matrix_rank(X) < X.shape[1]:
                    ri.append(_issue(tid, 'collinear_response_terms'))
        flags.extend(x for x in ri if any(w in x['reason_code'] for w in ('identify', 'collinear', 'endpoint', 'independent')))
        summaries.append(dict(target_id=tid, eligible=not ri, training_rows=len(train),
                              training_units=len({r['unit_id'] for r in train}), issues=ri))
    all_issues = [x for s in summaries for x in s['issues']]
    eligible = [s['target_id'] for s in summaries if s['eligible']]
    _unchanged(hashes)
    return dict(status='eligible' if not all_issues else 'partially_available' if eligible else 'unavailable',
                eligible_targets=eligible, missing_evidence=all_issues, identifiability_flags=flags,
                source_hashes=hashes, data_kind=context['data_kind'], record_count=len(data),
                targets=summaries, plan_hash=digest(p), treatment_hash=digest(tr),
                observation_evidence={r['record_id']:r['observation_evidence'] for r in data if r.get('observation_evidence')})


def _roles(target: dict, values: dict, row: dict) -> dict:
    v = {role: values[name] for role, name in target['parameters'].items()}
    grouped = {}
    for f in target.get('features', []):
        raw = _finite(row.get(f['column']), f['column'])
        if not f['domain'][0] <= raw <= f['domain'][1]:
            raise StudyError('Response input outside declared domain')
        key = (f['role'], f['link'])
        grouped[key] = grouped.get(key, 0) + values[f['coefficient']] * (raw - f['center']) / f['scale']
    if len({role for role, link in grouped}) != len(grouped):
        raise StudyError('Mixed links for the same role are ambiguous')
    for (role, link), delta in grouped.items():
        v[role] = v[role] * math.exp(delta) if link == 'log' else v[role] + delta
    if target['family'] == 'lognormal_wait':
        if v['sigma'] <= 0 or not 0 <= v['stop'] <= 1: raise StudyError('Invalid event parameter support')
    elif v['k'] < 0:
        raise StudyError('Negative growth rate')
    if target['family'] == 'anchored_expansion' and not target.get('allow_negative_increment', False) and v['D'] < 0:
        raise StudyError('Negative remaining growth')
    return v


def _prediction(t: dict, values: dict, row: dict) -> float:
    v = _roles(t, values, row)
    value = row['initial_value'] + v['D'] * -math.expm1(-v['k'] * row['elapsed_days'])
    return math.atan2(math.sin(value), math.cos(value)) if t['family'] == 'azimuth_rotation' else value


def _event_log_probability(t: dict, values: dict, r: dict) -> float:
    v = _roles(t, values, r)
    scale = t['reference_day'] * math.exp(v['mu'])
    log_survival = lognorm.logsf(r['lower_day'], s=v['sigma'], scale=scale)
    log_grow = math.log1p(-v['stop']) if v['stop'] < 1 else -math.inf
    if r['censoring'] == 'right':
        log_stop = math.log(v['stop']) if v['stop'] else -math.inf
        return float(np.logaddexp(log_stop, log_grow + log_survival))
    upper_survival = lognorm.logsf(r['upper_day'], s=v['sigma'], scale=scale)
    if not math.isfinite(log_survival) or upper_survival >= log_survival:
        return -math.inf
    return log_grow + float(log_survival + np.log(-np.expm1(upper_survival - log_survival)))


def _loss(values: dict, data: list[dict], targets: dict) -> float:
    total = 0.0; gaussian = {}
    try:
        for r in data:
            t = targets[r['target_id']]
            if t['family'] == 'lognormal_wait':
                total -= _event_log_probability(t, values, r)
            elif t['family'] == 'azimuth_rotation':
                kappa = t['observation_error']['kappa']
                delta = _prediction(t, values, r) - r['value']
                total += kappa * (1 - math.cos(delta)) + math.log(2 * math.pi * i0e(kappa))
            else:
                key = (r.get('_bootstrap_copy', 0), r['unit_id'], r['plant_id'], r['organ_id'], r['target_id'], r['origin_at'])
                gaussian.setdefault(key, []).append(r)
        for group in gaussian.values():
            t = targets[group[0]['target_id']]; rho = t['observation_error']['within_series_rho']
            residual = np.asarray([(_prediction(t, values, r) - r['value']) / r['measurement_sd'] for r in group])
            # Explicit exchangeable measurement covariance, not independent plants.
            n = len(group)
            quadratic = (np.dot(residual, residual) - rho * residual.sum() ** 2 / (1 + (n - 1) * rho)) / (1 - rho)
            total += float(quadratic / 2)
    except (StudyError, OverflowError, ValueError, FloatingPointError):
        return math.inf
    return total if math.isfinite(total) else math.inf


def _fit_once(data: list[dict], p: dict, target_ids: list[str]) -> tuple[dict | None, dict]:
    targets = {t['id']: t for t in p['targets'] if t['id'] in target_ids}
    used = {name for t in targets.values() for name in t['parameters'].values()}
    used |= {f['coefficient'] for t in targets.values() for f in t.get('features', [])}
    names = sorted(n for n in used if p['parameters'][n]['status'] == 'fit')
    fixed = {n: p['parameters'][n]['value'] for n in used if p['parameters'][n]['status'] == 'fixed'}
    if not names:
        return fixed, dict(status='fixed_assumptions', loss=_loss(fixed, data, targets), names=[], eigenvalues=[])
    specs = [p['parameters'][n] for n in names]
    bounds = np.asarray([[math.log(v) if s['transform'] == 'log' else v for v in s['bounds']] for s in specs])
    initial = np.asarray([math.log(s['initial']) if s['transform'] == 'log' else s['initial'] for s in specs])
    span = bounds[:, 1] - bounds[:, 0]
    def unpack(z: np.ndarray) -> dict:
        physical = bounds[:, 0] + span * z
        return dict(fixed, **{n: math.exp(x) if s['transform'] == 'log' else float(x) for n, s, x in zip(names, specs, physical)})
    def objective(z: np.ndarray) -> float:
        return _loss(unpack(z), data, targets)
    opt = p['optimizer']
    solution = minimize(objective, (initial - bounds[:, 0]) / span, method='L-BFGS-B',
                        bounds=[(0., 1.)] * len(names),
                        options={k: opt[k] for k in ('maxiter', 'ftol', 'gtol')})
    diagnostic = dict(status='failed', message=str(solution.message), loss=float(solution.fun) if math.isfinite(solution.fun) else None,
                      names=names, iterations=int(solution.nit), eigenvalues=[])
    if not solution.success or not math.isfinite(solution.fun):
        return None, diagnostic
    z = solution.x
    if np.any(z <= opt['bound_margin']) or np.any(z >= 1 - opt['bound_margin']):
        diagnostic['status'] = 'boundary_constrained'; return None, diagnostic
    step = opt['finite_difference_step']; n = len(names); hessian = np.zeros((n, n))
    for i in range(n):
        ei = np.eye(n)[i] * step
        hessian[i, i] = (objective(z + ei) - 2 * objective(z) + objective(z - ei)) / step ** 2
        for j in range(i):
            ej = np.eye(n)[j] * step
            hessian[i, j] = hessian[j, i] = (objective(z + ei + ej) - objective(z + ei - ej) - objective(z - ei + ej) + objective(z - ei - ej)) / (4 * step ** 2)
    if not np.isfinite(hessian).all():
        diagnostic['status'] = 'nonfinite_curvature'; return None, diagnostic
    eigen = np.linalg.eigvalsh(hessian); diagnostic['eigenvalues'] = eigen.tolist()
    if eigen[-1] <= 0 or eigen[0] <= opt['hessian_relative_tolerance'] * eigen[-1]:
        diagnostic['status'] = 'nonidentifiable'; return None, diagnostic
    diagnostic['status'] = 'converged'
    return unpack(z), diagnostic


def fit_growth_parameters(observation_refs: Any, evidence_registry: Any, fit_plan: Any,
                          treatment_manifest: Any = None) -> dict:
    """Fit only eligible targets; treatment_manifest may be embedded in fit_plan."""
    p = _object(fit_plan)
    tr = treatment_manifest if treatment_manifest is not None else p.get('treatment_manifest')
    audit = audit_calibration_data(observation_refs, tr, fit_plan)
    evidence, evidence_issues = validate_evidence_registry(evidence_registry)
    evidence_ids = {r['id']: r for r in evidence}
    eligible = list(audit['eligible_targets'])
    for t in p.get('targets', []):
        if t['id'] not in eligible: continue
        for name in set(t['parameters'].values()) | {f['coefficient'] for f in t.get('features', [])}:
            ev = evidence_ids.get(p['parameters'][name]['source_ref'])
            if ev is None:
                audit['missing_evidence'].append(_issue(t['id'], 'parameter_evidence_missing', name))
                if t['id'] in eligible: eligible.remove(t['id'])
            elif ev.get('unit') not in (None, p['parameters'][name]['unit']):
                raise StudyError('Evidence/parameter unit mismatch')
            elif ev.get('evidence_role') == 'endpoint' and p['parameters'][name]['unit'] == '1/calendar_day':
                raise StudyError('Endpoint evidence cannot supply a dynamic rate')
            elif any(x['component'] == ev['id'] and x['reason_code'].startswith('missing_') for x in evidence_issues):
                audit['missing_evidence'].append(_issue(t['id'], 'incomplete_parameter_evidence', name))
                if t['id'] in eligible: eligible.remove(t['id'])
    result = dict(schema_version=SCHEMA, status='unavailable', data_audit=audit,
                  evidence_registry=_object(evidence_registry), evidence_issues=evidence_issues,
                  fit_plan=p, parameter_set=None, diagnostics=[], validation=[])
    audit['eligible_targets'] = eligible
    if audit['missing_evidence']:
        audit['status'] = 'partially_available' if eligible else 'unavailable'
    if not eligible: return result
    data, context = _load(observation_refs)
    train = [r for r in data if r['split'] == 'train' and r['target_id'] in eligible]
    values, diagnostic = _fit_once(train, p, eligible)
    result['diagnostics'].append(dict(replicate='point', **diagnostic))
    if values is None:
        result['status'] = 'fit_failed'; return result
    if diagnostic['status'] == 'fixed_assumptions':
        result['status'] = 'assumption_only_no_fitted_parameters'; return result
    tm = _object(tr); units = {u['unit_id']: u for u in tm['units']}
    strata = {}
    for uid in sorted({r['unit_id'] for r in train}):
        strata.setdefault(units[uid]['treatment_id'], []).append(uid)
    rng = np.random.Generator(np.random.PCG64(p['uncertainty']['seed']))
    particles = []
    for b in range(p['uncertainty']['replicates']):
        selected = [uid for key in sorted(strata) for uid in rng.choice(strata[key], len(strata[key]), replace=True)]
        sample = [dict(r, _bootstrap_copy=i) for i, uid in enumerate(selected) for r in train if r['unit_id'] == uid]
        draw, diag = _fit_once(sample, p, eligible)
        result['diagnostics'].append(dict(replicate=b, **diag))
        if draw is not None: particles.append(dict(id='bootstrap-' + str(b), values=draw, sampled_units=selected))
    fraction = len(particles) / p['uncertainty']['replicates']
    if fraction < p['uncertainty']['min_success_fraction'] or len(particles) < 2:
        result['status'] = 'uncertainty_failed'; return result
    for particle in particles: particle['weight'] = 1 / len(particles)
    order = sorted(values)
    covariance = np.atleast_2d(np.cov([[d['values'][n] for n in order] for d in particles], rowvar=False, ddof=1)).tolist()
    residuals = []
    for r in train:
        t = next(t for t in p['targets'] if t['id'] == r['target_id'])
        pred = None if t['family'] == 'lognormal_wait' else _prediction(t, values, r)
        err = None if pred is None else pred - r['value']
        if err is not None and t['family'] == 'azimuth_rotation': err = math.atan2(math.sin(err), math.cos(err))
        residuals.append(dict(record_id=r['record_id'], target_id=t['id'], predicted=pred, residual=err, unit=t['unit']))
    parameter_set = dict(schema_version=SCHEMA, parameter_set_id=digest([p, values, particles]),
                         evidence_kind='fitted', data_kind=context['data_kind'], validation_status='unevaluated',
                         accepted_for_domain=False, applicable_domain=p['applicability'],
                         values=values, units={n: p['parameters'][n]['unit'] for n in order},
                         parameter_order=order, covariance=covariance, particles=particles,
                         uncertainty_kind='assignment_unit_bootstrap_parameter_uncertainty',
                         predictive_process_uncertainty='not_estimated', plan_hash=digest(p),
                         evidence_hash=digest(_object(evidence_registry)), source_hashes=audit['source_hashes'],
                         training_record_ids=[r['record_id'] for r in train],
                         training_plants=sorted({r['plant_id'] for r in train}),
                         training_units=sorted({r['unit_id'] for r in train}), eligible_targets=eligible,
                         training_observed_until=max((aware_time(r['observed_at']) for r in train)).isoformat(),
                         fit_plan=p, residuals=residuals)
    result.update(status='synthetic_fitted' if context['data_kind'] == 'synthetic' else 'fitted_unevaluated', parameter_set=parameter_set)
    _unchanged(audit['source_hashes'])
    return result


def _parameter_set(value: Any) -> dict:
    s = _object(value)
    if s.get('schema_version') != SCHEMA or not s.get('particles') or not s.get('values'):
        raise StudyError('An eligible fitted parameter set is required')
    if s.get('accepted_for_domain'):
        raise StudyError('Automatic parameter promotion is not supported')
    p, missing = _plan(s['fit_plan'])
    if missing or digest(p) != s['plan_hash'] or s['parameter_set_id'] != digest([p, s['values'], s['particles']]):
        raise StudyError('Parameter set/fit plan mismatch')
    names = set(s['values'])
    weights = []
    for particle in s['particles']:
        if set(particle['values']) != names:
            raise StudyError('Joint particle parameter mismatch')
        for v in particle['values'].values(): _finite(v, 'particle')
        weights.append(_finite(particle['weight'], 'weight'))
    if min(weights) < 0 or not math.isclose(sum(weights), 1, abs_tol=1e-10):
        raise StudyError('Particle weights must be normalized')
    return s


def _weighted_quantile(values: list, weights: list, probability: float) -> float:
    order = np.argsort(values); v = np.asarray(values)[order]; w = np.asarray(weights)[order]
    return float(v[min(np.searchsorted(np.cumsum(w), probability, side='left'), len(v) - 1)])


def validate_parameter_set(parameter_set: Any, independent_targets: Any, evaluation_plan: Any) -> dict:
    """Independent prediction scores; returned copy never marks domain acceptance."""
    s = _parameter_set(parameter_set); ep = _object(evaluation_plan)
    if ep.get('schema_version') != SCHEMA or ep.get('plan_hash') != s['plan_hash']:
        raise StudyError('Evaluation must name the frozen fit plan')
    frozen = aware_time(ep['frozen_at'])
    if frozen > aware_time(s['fit_plan']['selection_frozen_at']):
        raise StudyError('Evaluation plan must be fixed by model-selection freeze')
    levels = ep['interval_levels']
    if not levels or any(not 0 < _finite(q, 'coverage level') < 1 for q in levels):
        raise StudyError('Explicit interval levels required')
    if ep.get('future_environment_basis') not in ('known', 'forecast', 'assumed'):
        raise StudyError('Evaluation future-environment basis required')
    data, context = _load(independent_targets)
    p = s['fit_plan']; targets = {t['id']: t for t in p['targets']}
    weights = [d['weight'] for d in s['particles']]
    selected = [r for r in data if r['split'] == 'validation']
    if not selected:
        return dict(status='unavailable', parameter_set=s, validation=[],
                    requirements=[_issue('validation', 'independent_targets_missing')])
    validation, requirements = [], []
    for r in selected:
        if r['record_id'] in s['training_record_ids'] or r['plant_id'] in s['training_plants'] or r['unit_id'] in s['training_units']:
            raise StudyError('Independent validation leaks a training record/plant/unit')
        if r['plant_id'] not in p['split']['validation_plants'] or r['unit_id'] not in p['split']['validation_units']:
            raise StudyError('Validation violates frozen split')
        origin = aware_time(r['origin_at']); observed_at = aware_time(r['observed_at'])
        if frozen > origin or aware_time(s['training_observed_until']) > origin:
            raise StudyError('Forecast origin predates frozen training information')
        elapsed = (observed_at - origin).total_seconds() / 86400
        if elapsed <= 0 or not math.isclose(elapsed, r['elapsed_days'], abs_tol=1e-8):
            raise StudyError('Invalid chronological validation time')
        t = targets.get(r['target_id'])
        base = dict(record_id=r['record_id'], target_id=r['target_id'], plant_id=r['plant_id'],
                    unit_id=r['unit_id'], horizon_days=elapsed, unit=r['unit'],
                    status='available', reason=None, environment_basis=ep['future_environment_basis'])
        if r.get('observation_evidence'):
            base['observation_evidence'] = r['observation_evidence']
        def emit(metric: str, value: Any, **extra: Any) -> None:
            validation.append(dict(base, metric=metric, value=value, **extra))
        reason = None
        if t is None or t['id'] not in s['eligible_targets']: reason = 'unfitted_target'
        elif r['unit'] != t['unit']: raise StudyError('Validation unit mismatch')
        elif r['identity_status'] != 'confirmed': reason = 'identity_unconfirmed'
        elif not r['frame_id'] or r['age_basis'] != t.get('age_basis'): reason = 'frame_or_age_basis_missing'
        elif t.get('coverage_basis') and r['coverage_basis'] != t['coverage_basis']: reason = 'incomparable_coverage'
        elif t['family'] == 'azimuth_rotation' and context.get('target_metadata', {}).get(t['id'], {}).get('angle_reference') != t['angle_reference']: reason = 'angle_reference_mismatch'
        elif t['family'] != 'lognormal_wait' and (r['initial_value'] is None or r['value'] is None): reason = 'observation_missing'
        if not reason and t is not None:
            evidence_reasons = calibration_reasons(r, t, context)
            reason = evidence_reasons[0] if evidence_reasons else None
        if reason:
            base.update(status='unavailable', reason=reason); emit('coverage', None); continue
        if t.get('features') and r['exposure_kind'] != ep['future_environment_basis']:
            raise StudyError('Validation exposure basis differs from evaluation plan')
        if t['family'] == 'lognormal_wait':
            if r['visibility_status'] != 'confirmed':
                base.update(status='unavailable', reason='event_visibility_unconfirmed'); emit('interval_log_loss', None); continue
            if r['lower_day'] is None or r['lower_day'] < 0 or r['lower_day'] > elapsed:
                raise StudyError('Invalid validation censoring lower bound')
            if r['censoring'] == 'interval':
                if r['upper_day'] is None or not r['lower_day'] < r['upper_day'] <= elapsed:
                    raise StudyError('Invalid validation appearance interval')
            elif r['censoring'] != 'right' or r['upper_day'] is not None:
                raise StudyError('Invalid validation right censoring')
            lp = [_event_log_probability(t, d['values'], r) for d in s['particles']]
            logp = float(logsumexp(np.asarray(lp) + np.log(weights)))
            if math.isfinite(logp): emit('interval_log_loss', -logp)
            else:
                base.update(status='failed', reason='zero_probability'); emit('interval_log_loss', None)
            occurred = r['censoring'] == 'interval'
            horizon = r['upper_day'] if occurred else r['lower_day']
            survival = []
            for d in s['particles']:
                v = _roles(t, d['values'], r)
                survival.append(v['stop'] + (1 - v['stop']) * lognorm.sf(horizon, v['sigma'], scale=t['reference_day'] * math.exp(v['mu'])))
            prob = 1 - float(np.dot(weights, survival))
            emit('occurrence_brier', (prob - float(occurred)) ** 2)
            continue
        predictions = [_prediction(t, d['values'], r) for d in s['particles']]
        circular = t['family'] == 'azimuth_rotation'
        if circular:
            z = np.dot(weights, np.exp(1j * np.array(predictions)))
            if abs(z) < ep['direction_resultant_tolerance']:
                base.update(status='unavailable', reason='undefined_circular_center'); emit('angular_error', None); continue
            center = float(np.angle(z))
            error = math.atan2(math.sin(center - r['value']), math.cos(center - r['value']))
            kappa = t['observation_error']['kappa']
            lp = vonmises.logpdf(r['value'], kappa, loc=np.asarray(predictions))
            emit('angular_absolute_error', abs(error)); emit('predictive_log_loss', -float(logsumexp(lp + np.log(weights))))
            radii = [abs(math.atan2(math.sin(v - center), math.cos(v - center))) for v in predictions]
            for level in levels:
                radius = _weighted_quantile(radii, weights, level)
                emit('parameter_angular_coverage', float(abs(error) <= radius), nominal_probability=level, interval_width=2 * radius)
        else:
            center = _weighted_quantile(predictions, weights, .5); error = center - r['value']
            x, w = np.asarray(predictions), np.asarray(weights)
            emit('absolute_error', abs(error))
            # Latent trajectory score and interval: does not include observation/process noise.
            crps = np.dot(w, abs(x - r['value'])) - .5 * np.sum(w[:, None] * w[None, :] * abs(x[:, None] - x[None, :]))
            emit('latent_crps', float(crps))
            for level in levels:
                lo = _weighted_quantile(predictions, weights, (1 - level) / 2)
                hi = _weighted_quantile(predictions, weights, (1 + level) / 2)
                emit('parameter_interval_coverage', float(lo <= r['value'] <= hi), nominal_probability=level, interval_width=hi - lo)
            if r['measurement_sd'] is not None and r['measurement_sd'] > 0:
                sd = r['measurement_sd']
                emit('observation_predictive_log_loss', -float(logsumexp(norm.logpdf(r['value'], x, sd) + np.log(w))))
                for level in levels:
                    bounds = [brentq(lambda v: float(np.dot(w, norm.cdf(v, x, sd))) - q,
                                     float(x.min() - 12 * sd), float(x.max() + 12 * sd)) for q in ((1 - level) / 2, (1 + level) / 2)]
                    emit('observation_predictive_coverage', float(bounds[0] <= r['value'] <= bounds[1]), nominal_probability=level, interval_width=bounds[1] - bounds[0])
            else: requirements.append(_issue(r['record_id'], 'predictive_measurement_error_missing'))
        baseline_error = r['initial_value'] - r['value']
        if circular: baseline_error = math.atan2(math.sin(baseline_error), math.cos(baseline_error))
        emit('persistence_absolute_error', abs(baseline_error))
        # Baseline history is separate and must precede the origin; never use target differences.
        history = ep.get('recent_change', {}).get(r['record_id'])
        if history:
            if aware_time(history['observed_at']) >= origin or history['unit'] != t['unit'] or history['frame_id'] != r['frame_id'] or history['organ_id'] != r['organ_id'] or history['plant_id'] != r['plant_id'] or not history.get('source_ref'):
                raise StudyError('Invalid pre-origin baseline evidence')
            if t['unit']=='cm2' or t['family']=='azimuth_rotation':
                trait = 'area' if t['unit']=='cm2' else 'direction'
                comparison = dict(r, observed_at=r['origin_at'], origin_at=history['observed_at'],
                    observation_evidence={trait:r.get('observation_evidence', {}).get('anchor_'+trait),
                        'anchor_'+trait:history.get('observation_evidence', {}).get(trait)})
                reasons = calibration_reasons(comparison, t, context)
                if reasons:
                    validation.append(dict(base, metric='recent_change_absolute_error', value=None,
                                           status='unavailable', reason=reasons[0]))
                    continue
            delta = r['initial_value'] - history['value']
            if circular: delta = math.atan2(math.sin(delta), math.cos(delta))
            dt = (origin - aware_time(history['observed_at'])).total_seconds() / 86400
            err = r['initial_value'] + delta / dt * elapsed - r['value']
            if circular: err = math.atan2(math.sin(err), math.cos(err))
            emit('recent_change_absolute_error', abs(err))
        else:
            validation.append(dict(base, metric='recent_change_absolute_error', value=None, status='unavailable', reason='pre_origin_history_missing'))
    for day in ep['horizons_days']:
        subset = [r for r in selected if r['elapsed_days'] == day]
        requirements.extend([] if subset else [_issue('validation', 'no_independent_target_at_horizon', day)])
    evaluated = deepcopy(s)
    evaluated['validation_status'] = 'synthetic_evaluated' if context['data_kind'] == 'synthetic' or s['data_kind'] == 'synthetic' else 'evaluated_unaccepted'
    evaluated['validation_record'] = dict(evaluation_plan_hash=digest(ep), source_hashes=context['source_hashes'],
                                         target_count=len(selected), plant_count=len({r['plant_id'] for r in selected}),
                                         assignment_unit_count=len({r['unit_id'] for r in selected}),
                                         accepted_for_domain=False)
    scored_ids = {r['record_id'] for r in validation if r['status'] == 'available' and r['value'] is not None}
    evaluated['validation_record'].update(scored_targets=len(scored_ids), unavailable_targets=len(selected) - len(scored_ids),
                                         failed_metric_rows=sum(r['status'] == 'failed' for r in validation))
    if not scored_ids:
        evaluated['validation_status'] = 'unavailable'
    _unchanged(context['source_hashes'])
    return dict(status=evaluated['validation_status'], parameter_set=evaluated,
                validation=validation, requirements=requirements, evaluation_plan=ep)


def apply_parameter_set(parameter_set: Any, model_config: Any, scenario: dict) -> dict:
    """Explicit unit-checked bindings into the existing calculator, without fitting.

    Preserve supplied process covariance. Parameter uncertainty is represented by
    the same joint bootstrap particle across every bound family and organ.
    """
    from tools import probabilistic_compound_growth as engine
    s = _parameter_set(parameter_set); c = _object(model_config); plan = s['fit_plan']
    engine.validate_calibration_clock(c, plan.get('calibration_clock_reference'))
    if not plan.get('engine_bindings'):
        raise StudyError('Explicit engine bindings required')
    if not c.get('parameter_particles'):
        raise StudyError('An explicit base model with process assumptions is required')
    if scenario != (c.get('environment_scenario') or {}).get('values', {}):
        raise StudyError('Adapter scenario must match the forecast environment')
    targets = {t['id']: t for t in plan['targets']}
    applied_features = []
    for bind in plan['engine_bindings']:
        for feature in targets[bind['target_id']].get('features', []):
            if feature['role'] == bind['role']:
                applied_features.append(dict(feature,target_id=bind['target_id'],binding=deepcopy(bind),source_ref=s['parameter_set_id']))
    audit_config = deepcopy(c)
    audit_config['calibration'] = dict(applied_features=applied_features)
    try:
        engine._validate_d9(audit_config)
    except engine.ScienceUnavailable as exc:
        return dict(status='unavailable',config=c,parameter_set_id=s['parameter_set_id'],
            unavailable=[dict(reason_code=exc.reason_code,fields=exc.details)],calibration_applied=False)
    particles = []
    for base in c['parameter_particles']:
        for sample in s['particles']:
            p = deepcopy(base); p['id'] = base['id'] + '/' + sample['id']
            p['weight'] = base['weight'] * sample['weight']
            p['calibration_ref'] = s['parameter_set_id']; p['base_evidence'] = {k: base[k] for k in ('source_kind', 'source_ref')}
            p['source_kind'] = 'fitted'; p['source_ref'] = s['parameter_set_id']
            for bind in plan['engine_bindings']:
                target = targets[bind['target_id']]
                if target['id'] not in s['eligible_targets']:
                    raise StudyError('Binding references an unfitted target')
                roles = _roles(target, sample['values'], scenario)
                role = bind['role']; value = roles[role]
                if bind['kind'] == 'axis_stop':
                    if target['family'] != 'lognormal_wait' or role != 'stop': raise StudyError('Invalid stop binding')
                    if p['axes'][bind['axis_id']].get('node_budget'):
                        raise StudyError('Fitted stop probability cannot overwrite node_budget')
                    p['axes'][bind['axis_id']]['stop_probability'] = value
                    continue
                family = p['families'][bind['family']]; coordinate = bind['coordinate']
                if '_x_max_' in coordinate or '_a_m_' in coordinate or '_a_e_' in coordinate or (
                    family.get('growth_curve') == 'determinate_beta' and target['family'] == 'anchored_expansion'):
                    raise StudyError('Beta-coordinate calibration binding is unsupported; exponential parameters cannot bind determinate_beta')
                if coordinate not in engine.UNITS or bind['unit'] != engine.UNITS[coordinate]:
                    raise StudyError('Engine coordinate unit mismatch')
                expected_role_unit = plan['parameters'][target['parameters'][role]]['unit']
                compatible = {'1/calendar_day': '1/development_day', 'calendar_day': 'development_day'}
                if bind['kind'] in ('constant', 'physical_location'):
                    _check_binding_meaning(target, role, coordinate, [bind,plan['parameters'][target['parameters'][role]],
                        s.get('provenance'),s.get('source_provenance')])
                    if compatible.get(expected_role_unit, expected_role_unit) != bind['unit']:
                        raise StudyError('Fitted-to-engine unit mismatch')
                    i = next((i for i, x in enumerate(p['coordinates']) if x['name'] == coordinate), None)
                    if bind['kind'] == 'constant':
                        if i is not None: raise StudyError('Constant binding cannot overwrite a stochastic coordinate')
                        family.setdefault('constants', {})[coordinate] = dict(value=value, unit=bind['unit'], source_ref=s['parameter_set_id'])
                    else:
                        if i is None: raise StudyError('Physical location binding requires a stochastic coordinate')
                        x = p['coordinates'][i]
                        if family['features'] and any(family['coefficients'][i]):
                            raise StudyError('Existing response coefficients would double-count fitted response')
                        if x['transform'] == 'identity': latent = value
                        elif x['transform'] == 'exp':
                            if value <= 0: raise StudyError('Positive physical location required')
                            latent = math.log(value / x['reference'])
                        elif x['transform'] == 'bounded':
                            q = (value - x['lower']) / (x['upper'] - x['lower'])
                            if not 0 < q < 1: raise StudyError('Physical location outside transform bounds')
                            latent = math.log(q / (1 - q))
                        elif x['transform'] == 'elevation':
                            if abs(value) >= math.pi / 2: raise StudyError('Elevation location at/outside pole')
                            latent = math.atanh(value / (math.pi / 2))
                        else: raise StudyError('Unsupported engine transform')
                        family['mean'][i] = latent
                elif bind['kind'] == 'wait_distribution':
                    if target['family'] != 'lognormal_wait' or coordinate != 'wait_dev_days' or role != 'mu':
                        raise StudyError('Invalid event distribution binding')
                    i = next((i for i, x in enumerate(p['coordinates']) if x['name'] == coordinate), None)
                    if i is None or p['coordinates'][i]['transform'] != 'exp':
                        raise StudyError('Lognormal wait requires existing exponential coordinate')
                    if family['features'] or family['rho'] != 0 or any(p['plant_covariance'][i]):
                        raise StudyError('Independent wait fit cannot overwrite conditional/shared/serial dependence')
                    for key in ('initial_covariance', 'innovation_covariance'):
                        if any(x != 0 for j, x in enumerate(family[key][i]) if j != i):
                            raise StudyError('Wait covariance has unfitted cross-trait terms')
                        family[key][i][i] = roles['sigma'] ** 2
                    family['mean'][i] = roles['mu'] + math.log(target['reference_day'] / p['coordinates'][i]['reference'])
                else: raise StudyError('Unsupported engine binding kind')
            particles.append(p)
    c['parameter_particles'] = particles
    c['calibration'] = dict(parameter_set_id=s['parameter_set_id'], validation_status=s['validation_status'],
                            data_kind=s['data_kind'], accepted_for_domain=False,
                            parameter_uncertainty=s['uncertainty_kind'],
                            process_uncertainty='preserved_explicit_base_model', fit_plan_hash=s['plan_hash'],
                            calibration_code_hash=file_hash(Path(__file__)), source_hashes=s['source_hashes'],
                            applied_features=applied_features,
                            calibration_clock_reference=deepcopy(plan.get('calibration_clock_reference')),
                            parameter_set_hash=digest(s))
    return c


def export_calibration(result: dict, output_path: Path) -> Path:
    folder = output_dir(Path(output_path))
    for name, value in (('evidence_registry', result.get('evidence_registry', {'schema_version': SCHEMA, 'records': []})),
                        ('data_audit', result.get('data_audit', {})), ('fit_plan', result.get('fit_plan', {})),
                        ('parameter_set', result.get('parameter_set'))):
        write_json(folder / (name + '.json'), value)
    diagnostics = []
    for d in result.get('diagnostics', []):
        diagnostics.append(dict(replicate=d['replicate'], status=d['status'], loss=d.get('loss'),
                                iterations=d.get('iterations'), message=d.get('message'),
                                min_curvature=min(d['eigenvalues']) if d.get('eigenvalues') else None))
    _csv(folder / 'fit_diagnostics.csv', diagnostics, ('replicate', 'status', 'loss', 'iterations', 'message', 'min_curvature'))
    _csv(folder / 'validation.csv', result.get('validation', []), ('record_id', 'target_id', 'plant_id', 'unit_id',
         'horizon_days', 'unit', 'metric', 'value', 'nominal_probability', 'interval_width', 'status', 'reason', 'environment_basis'))
    evidence = {r['record_id']:r['observation_evidence'] for r in result.get('validation', []) if r.get('observation_evidence')}
    if evidence:
        write_json(folder / 'validation_observation_evidence.json', evidence)
    requirements = list(result.get('data_audit', {}).get('missing_evidence', [])) + list(result.get('requirements', []))
    _csv(folder / 'requirements.csv', [dict(component=x['component'], reason=x['reason_code'], source=x.get('source'),
         provider='scientific_reviewer_or_measurement_provider') for x in requirements], ('component', 'reason', 'source', 'provider'))
    if result.get('evaluation_plan'): write_json(folder / 'evaluation_plan.json', result['evaluation_plan'])
    if result.get('parameter_set'):
        _csv(folder / 'residuals.csv', result['parameter_set'].get('residuals', []), ('record_id', 'target_id', 'predicted', 'residual', 'unit'))
    manifest = dict(schema_version=SCHEMA, status=result['status'], created_at=datetime.now(timezone.utc).isoformat(),
                    code_hashes={str(p.resolve()):file_hash(p) for p in (Path(__file__),Path(__file__).with_name('growth_observation_evidence.py'))},
                    source_hashes=result.get('data_audit', {}).get('source_hashes', {}),
                    artifact_hashes={p.name: file_hash(p) for p in folder.iterdir() if p.is_file()},
                    command=sys.argv, python=platform.python_version(), numpy=np.__version__, scipy=scipy.__version__,
                    seed=(result.get('fit_plan', {}).get('uncertainty') or {}).get('seed'),
                    limitations=['No automatic domain acceptance', 'Data and validation status are recorded in parameter_set.json',
                                 'Proposed growth laws; no photosynthesis/carbon allocation'])
    write_json(folder / 'manifest.json', manifest)
    return folder


def templates(out: Path) -> Path:
    folder = output_dir(out)
    write_json(folder / 'fit_plan.json', blank_plan())
    write_json(folder / 'evidence_registry.json', dict(schema_version=SCHEMA, records=[]))
    write_json(folder / 'treatments.json', dict(schema_version=SCHEMA, units=[]))
    _csv(folder / 'observations.csv', [], COLUMNS)
    write_json(folder / 'observations.json', dict(schema_version=SCHEMA, data_kind='observed',
               observations={'path': 'observations.csv', 'sha256': file_hash(folder / 'observations.csv')}))
    write_json(folder / 'evaluation_plan.json', dict(schema_version=SCHEMA, plan_hash=None, frozen_at=None,
               interval_levels=None, horizons_days=[7, 14, 21, 30], future_environment_basis=None,
               direction_resultant_tolerance=None, recent_change={}))
    write_json(folder / 'literature_candidates.json', read_json(Path(__file__).with_name('growth_calibration_evidence.json')))
    return folder


def synthetic_fixture(out: Path, replicates: int = 8) -> tuple[Path, dict, dict, dict, dict]:
    """Explicit software fixture values; never returned as a blank crop model."""
    folder = output_dir(out)
    p = blank_plan()
    p.update(plan_id='synthetic-recovery-1', review=dict(status='synthetic_assumption', reviewer='software_fixture', source_ref='synthetic_fixture'),
             applicability={'cultivar': 'synthetic', 'environment_domain': 'fixture_only'},
             selection_frozen_at='2026-02-01T00:00:00+00:00',
             dependence=dict(kind='assignment_unit_bootstrap', source_ref='synthetic_fixture'),
             uncertainty=dict(method='stratified_cluster_bootstrap', replicates=replicates, seed=203,
                              stratify_by='treatment_id', min_units_per_treatment=2, min_success_fraction=.5),
             optimizer=dict(maxiter=400, ftol=1e-11, gtol=1e-7, finite_difference_step=1e-4,
                            hessian_relative_tolerance=1e-8, bound_margin=1e-5))
    def param(initial: float, bounds: list, unit: str, transform: str = 'identity') -> dict:
        return dict(status='fit', initial=initial, bounds=bounds, unit=unit, transform=transform,
                    source_ref='fixture_' + unit, bounds_source='synthetic_fixture')
    p['parameters'] = {'D': param(15., [1., 60.], 'mm', 'log'), 'k': param(.08, [.005, .8], '1/calendar_day', 'log'),
                       'light_beta': param(.1, [-1., 1.], 'dimensionless')}
    p['targets'] = [dict(id='length', family='anchored_expansion', unit='mm', equation_ref='proposed_spec_5.2',
                         age_basis='remaining_from_measured_origin', coverage_basis='complete_axis', effect_interpretation='synthetic_assumption',
                         parameters={'D': 'D', 'k': 'k'}, observation_error=dict(kind='gaussian', within_series_rho=0., source_ref='fixture_independent_measurement_error'),
                         features=[dict(column='ppfd_umol_m2_s', unit='umol/m2/s', role='D', coefficient='light_beta', link='log',
                                        center=200., scale=100., domain=[100., 300.], source_ref='synthetic_fixture', basis='constant_exposure')])]
    tr = dict(schema_version=SCHEMA, units=[]); records = []
    rng = np.random.Generator(np.random.PCG64(123))
    truth = dict(D=24., k=.12, light_beta=.25)
    for split, n in (('train', 8), ('validation', 4)):
        for i in range(n):
            uid = f'{split}-unit-{i}'; pid = f'{split}-plant-{i}'
            p['split'][split + '_units'].append(uid); p['split'][split + '_plants'].append(pid)
            ppfd = 100. if i % 2 == 0 else 300.
            tr['units'].append(dict(unit_id=uid, treatment_id=str(ppfd), run_id=split, source_ref='synthetic_fixture'))
            origin = '2026-01-01T00:00:00+00:00' if split == 'train' else '2026-02-02T00:00:00+00:00'
            unit_offset = rng.normal(0, .15)
            for day in (3, 7, 14, 21, 30):
                from datetime import timedelta
                observed_at = (aware_time(origin) + timedelta(days=day)).isoformat()
                r = {k: '' for k in COLUMNS}
                r.update(record_id=f'{pid}-{day}', plant_id=pid, organ_id='leaf-1', target_id='length', unit_id=uid,
                         observed_at=observed_at, origin_at=origin, elapsed_days=day, initial_value=10., unit='mm', frame_id='board_fixture',
                         identity_status='confirmed', coverage_basis='complete_axis', age_basis='remaining_from_measured_origin',
                         measurement_sd=.2, split=split, capture_phase='mid_light', exposure_kind='observed_history' if split == 'train' else 'known',
                         ppfd_umol_m2_s=ppfd)
                r['value'] = _prediction(p['targets'][0], truth, r) + unit_offset + rng.normal(0, .1)
                records.append(r)
    _csv(folder / 'observations.csv', records, (*COLUMNS, 'ppfd_umol_m2_s'))
    manifest = dict(schema_version=SCHEMA, data_kind='synthetic', feature_units={'ppfd_umol_m2_s': 'umol/m2/s'},
                    observations={'path': 'observations.csv', 'sha256': file_hash(folder / 'observations.csv')})
    write_json(folder / 'observations.json', manifest)
    registry = dict(schema_version=SCHEMA, records=[dict(id='fixture_' + unit, source_kind='user_assumed', value=None, unit=unit,
                    source_ref='synthetic_fixture', locator='synthetic_fixture', source_version='1', applicability={'domain': 'software_only'},
                    review_status='synthetic_assumption', uncertainty=None) for unit in ('mm', '1/calendar_day', 'dimensionless')])
    ep = dict(schema_version=SCHEMA, plan_hash=digest(p), frozen_at=p['selection_frozen_at'], interval_levels=[.8, .95],
              horizons_days=[7, 14, 21, 30], future_environment_basis='known', direction_resultant_tolerance=1e-8, recent_change={})
    for name, value in (('fit_plan', p), ('treatments', tr), ('evidence_registry', registry), ('evaluation_plan', ep), ('synthetic_truth', truth)):
        write_json(folder / (name + '.json'), value)
    return folder / 'observations.json', p, tr, registry, ep


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    for name in ('templates', 'audit', 'fit', 'validate', 'forecast', 'demo'):
        a = sub.add_parser(name); a.add_argument('--out', type=Path, required=True)
        if name in ('audit', 'fit'):
            a.add_argument('--observations', type=Path); a.add_argument('--treatments', type=Path, required=True)
            a.add_argument('--plan', type=Path, required=True)
        if name == 'fit': a.add_argument('--evidence', type=Path, required=True)
        if name in ('validate', 'forecast'): a.add_argument('--parameters', type=Path, required=True)
        if name == 'validate':
            a.add_argument('--observations', type=Path, required=True); a.add_argument('--plan', type=Path, required=True)
        if name == 'forecast':
            for k in ('history', 'origin', 'model'): a.add_argument('--' + k, type=Path, required=True)
            a.add_argument('--structure', type=Path)
    args = parser.parse_args(argv)
    try:
        if args.command == 'templates': templates(args.out)
        elif args.command == 'audit':
            audit = audit_calibration_data(args.observations, args.treatments, args.plan)
            export_calibration(dict(status=audit['status'], data_audit=audit, fit_plan=read_json(args.plan)), args.out)
        elif args.command == 'fit':
            export_calibration(fit_growth_parameters(args.observations, args.evidence, args.plan, args.treatments), args.out)
        elif args.command == 'validate':
            result = validate_parameter_set(args.parameters, args.observations, args.plan)
            result['fit_plan'] = result['parameter_set']['fit_plan']; export_calibration(result, args.out)
        elif args.command == 'forecast':
            from tools import probabilistic_compound_growth as engine
            config = read_json(args.model)
            config = apply_parameter_set(args.parameters, config, config.get('environment_scenario', {}).get('values', {}))
            if config.get('status')=='unavailable': engine.export_run(config,args.out)
            else:
                origin = engine.prepare_origin(args.history, args.structure, args.origin)
                engine.export_run(engine.sample_forecast(origin, config), args.out)
        else:
            folder = output_dir(args.out)
            obs, p, tr, ev, ep = synthetic_fixture(folder / 'inputs')
            from tools import probabilistic_compound_growth as engine
            origin, config = engine.synthetic_fixture(folder / 'engine_inputs')
            base = config['parameter_particles'][0]
            family = base['existing_blocks']['L1']
            p['engine_bindings'] = [dict(kind='physical_location' if any(x['name'] == coord for x in base['coordinates']) else 'constant',
                target_id='length', role=role, family=family, coordinate=coord, unit=unit)
                for role, coord, unit in [('D', 'D_length_mm', 'mm'), ('k', 'k_length', '1/development_day')]]
            config['environment_scenario']['values'] = {'ppfd_umol_m2_s': 200.}
            ep['plan_hash'] = digest(p)
            write_json(folder / 'inputs' / 'fit_plan.json', p)
            write_json(folder / 'inputs' / 'evaluation_plan.json', ep)
            write_json(folder / 'engine_inputs' / 'model.json', config)
            result = fit_growth_parameters(obs, ev, p, tr)
            if result['parameter_set'] is not None:
                validation = validate_parameter_set(result['parameter_set'], obs, ep)
                result.update({k: v for k, v in validation.items() if k != 'status'})
                bound = apply_parameter_set(result['parameter_set'], config, config['environment_scenario']['values'])
                bank = engine.sample_forecast(origin, bound)
                bank['summaries'] = engine.summarize_forecast(bank, {'quantiles': [.1, .5, .9]})
                engine.export_run(bank, folder / 'forecast')
            export_calibration(result, folder / 'results')
        print(json.dumps(dict(status='written', out=str(args.out), accepted_for_domain=False)))
    except (StudyError, KeyError, ValueError, OSError) as exc:
        parser.exit(2, 'Calibration input/calculation error: ' + str(exc) + '\n')


if __name__ == '__main__':
    main()
