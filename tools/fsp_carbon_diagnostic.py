"""Evidence-gated, read-only P4 carbon diagnostics. No P3 or light execution.

Run ``python -X utf8 -m tools.fsp_carbon_diagnostic --help``.
Biological numbers must be supplied with evidence or explicit hypothetical labels.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
from copy import deepcopy
from datetime import datetime
from functools import wraps
import json
from importlib.metadata import version
import math
from pathlib import Path
import re
import sys
from typing import Any

from tools.leaf_light.common import DLI_UNIT, StudyError, digest, file_hash, output_dir, write_json

SCHEMA = 'p4-carbon-diagnostic-2'
# Molecular/unit identities, not plant parameters.
GC_PER_UMOL_CO2 = 12.011e-6
GC_PER_G_CH2O = 12.011 / 30.026
SECONDS_PER_DAY = 86400
CM2_TO_M2 = 1e-4
IDENTITY = ('run_id', 'scenario_id', 'plant_instance_id', 'source_plant_id',
            'trajectory_id', 'trajectory_weight', 't_start', 't_end', 'frame_id',
            'geometry_hash_start', 'geometry_hash_end', 'area_basis_id')
CORE = ('available_growth_carbon_gC', 'required_growth_carbon_gC', 'sufficiency_ratio',
        'maintenance_deficit_gC', 'growth_deficit_gC')
ENVIRONMENT = {'temperature_c', 'leaf_temperature_c', 'air_temperature_c', 'co2_ppm',
               'pressure_pa', 'relative_humidity_pct', 'vpd_kpa', 'ec_ms_cm', 'ph',
               'dli_mol_m2_day', 'ppfd_umol_m2_s', 'photoperiod_h'}
EVIDENCE_KINDS = {'measured', 'fitted', 'borrowed', 'assumed', 'unidentified'}
P3_STRUCTURAL_FEATURES = {'axis_length_mm', 'left_extent_mm', 'right_extent_mm',
                          'spacing_mm', 'azimuth_sin', 'azimuth_cos', 'order_index'}


class MissingEvidence(Exception):
    """A valid representation lacks evidence for a specific computation."""

    def __init__(self, code: str, reason: str):
        super().__init__(reason)
        self.code, self.reason = code, reason


def _missing(code: str, reason: str) -> None:
    raise MissingEvidence(code, reason)


def _strict_api(function: Any) -> Any:
    @wraps(function)
    def checked(*args: Any, **kwargs: Any) -> Any:
        try:
            return function(*args, **kwargs)
        except (KeyError, IndexError, TypeError, AttributeError, OverflowError, ZeroDivisionError) as exc:
            raise StudyError(function.__name__ + ': malformed or numerically invalid input: ' + str(exc)) from exc
    return checked


def _finite(value: Any, label: str, minimum: float | None = None) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
        raise StudyError(label + ': finite JSON number required')
    if minimum is not None and value < minimum:
        raise StudyError(label + ': below minimum')
    return float(value)


def _number(value: Any, label: str, minimum: float | None = None) -> float:
    if value is None:
        _missing(label + '_missing', label + ' is unavailable')
    return _finite(value, label, minimum)


def _positive(value: Any, label: str) -> float:
    result = _number(value, label, 0)
    if result == 0:
        raise StudyError(label + ': must be positive')
    return result


def _text(value: Any, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise StudyError(label + ': nonempty string required')
    return value


def _sha(value: Any, label: str) -> str:
    if not isinstance(value, str) or re.fullmatch('[0-9a-f]{64}', value) is None:
        raise StudyError(label + ': SHA256 required')
    return value


def _json_finite(value: Any) -> None:
    try:
        json.dumps(value, allow_nan=False)
    except (ValueError, TypeError) as exc:
        raise StudyError('Inputs must be finite JSON values') from exc


def _time(value: Any) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise StudyError('ISO8601 timestamp required') from exc
    if result.utcoffset() is None:
        raise StudyError('Timezone-aware timestamp required')
    return result


def _interval(obj: dict) -> tuple[datetime, datetime]:
    start, end = _time(obj.get('t_start')), _time(obj.get('t_end'))
    if end <= start:
        raise StudyError('Interval must have positive elapsed duration')
    return start, end


def _index(records: list[dict], key: str) -> dict[str, dict]:
    if not isinstance(records, list):
        raise StudyError(key + ': list required')
    result = {}
    for row in records:
        identifier = _text(row.get(key), key)
        if identifier in result:
            raise StudyError('Duplicate ' + key + ': ' + identifier)
        result[identifier] = row
    return result


def _sealed(value: dict | None, label: str) -> dict:
    if value is None:
        _missing(label + '_missing', 'Missing hashed ' + label)
    if not isinstance(value, dict) or set(value) != {'payload', 'sha256'}:
        raise StudyError(label + ': expected external {payload, sha256} envelope')
    _json_finite(value)
    if _sha(value['sha256'], label) != digest(value['payload']):
        raise StudyError(label + ': content hash mismatch')
    if not isinstance(value['payload'], dict):
        raise StudyError(label + ': object payload required')
    return value['payload']


def _evidence(record: dict, label: str, pack: dict) -> None:
    if record.get('evidence_kind') not in EVIDENCE_KINDS:
        _missing('evidence_missing', label + ': evidence kind required')
    if record['evidence_kind'] == 'unidentified':
        _missing('unidentified_parameter', label + ' is unidentified')
    for key in ('source_id', 'locator', 'applicability'):
        if not record.get(key):
            _missing('evidence_missing', label + ': ' + key + ' required')
    if 'uncertainty' not in record or 'conditions' not in record or 'cultivar' not in record:
        _missing('evidence_missing', label + ': uncertainty/conditions/cultivar must be explicit, even if null')
    if pack.get('review_status') == 'reviewed' and record.get('review_state') != 'reviewed':
        _missing('parameter_review_missing', label + ': parameter review required')


def _pack(envelope: dict | None) -> dict:
    pack = _sealed(envelope, 'parameter_pack')
    if pack.get('schema_version') != SCHEMA:
        raise StudyError('Unsupported parameter-pack schema')
    _text(pack.get('pack_id'), 'pack_id')
    if pack.get('review_status') not in {'hypothetical', 'reviewed'}:
        _missing('physiological_review_missing', 'Pack must be reviewed or explicitly hypothetical')
    if pack['review_status'] == 'hypothetical' and not pack.get('assumptions'):
        _missing('hypothetical_assumptions_missing', 'Hypothetical pack needs explicit assumptions')
    if pack['review_status'] == 'reviewed' and not pack.get('review_ref'):
        _missing('physiological_review_missing', 'Recorded review reference required')
    if pack.get('response_multipliers'):
        raise StudyError('Uncontracted environment/stress multipliers are forbidden')
    numerics = pack.get('numerics', {})
    for key in ('carbon_abs_tol_gC', 'carbon_rel_tol', 'mass_abs_tol_gDM', 'area_abs_tol_m2'):
        _number(numerics.get(key), key, 0)
    if not isinstance(pack.get('parameters'), dict):
        _missing('parameters_missing', 'Parameter records required')
    return pack


def _parameter(pack: dict, parameter_id: str | None, unit: str, minimum: float | None = None) -> float:
    record = pack.get('parameters', {}).get(parameter_id)
    if record is None:
        _missing('parameter_missing', str(parameter_id) + ': ' + unit + ' parameter required')
    _evidence(record, str(parameter_id), pack)
    if record.get('unit') != unit:
        # Preserve the strict unit check: paper m2/mg is not m2/g structural blade DM.
        if unit == 'm2/g_structural_blade_DM':
            _missing('sla_unit_incompatible', str(parameter_id) + ': expected ' + unit + '; no automatic mass-unit conversion')
        raise StudyError(str(parameter_id) + ': expected unit ' + unit)
    return _number(record.get('value'), str(parameter_id), minimum)


def _source_family(pack: dict, record: dict | None = None) -> str:
    """Use explicit provenance classification, never source-ID substring matching."""
    family = (record or {}).get('source_family', pack.get('source_family'))
    if family is None:
        _missing('source_family_undeclared', 'Declare source_family on the pack or parameter evidence')
    if family not in {'butturini_dwarf', 'non_dwarf', 'hypothetical'}:
        raise StudyError('Unsupported source_family')
    return family


def _saturation_id(pack: dict) -> str | None:
    photo = pack.get('photosynthesis', {})
    if photo.get('Pmax') and photo.get('P_sat') and photo['Pmax'] != photo['P_sat']:
        raise StudyError('Pmax and P_sat must reference the same saturation parameter')
    return photo.get('Pmax') or photo.get('P_sat')


def _photo_evidence_issues(pack: dict) -> list[dict]:
    photo = pack.get('photosynthesis', {})
    families = [_source_family(pack)]
    issues = []
    for role, parameter_id in [('alpha', photo.get('alpha')), ('Pmax', _saturation_id(pack)), ('theta', photo.get('theta'))]:
        record = pack.get('parameters', {}).get(parameter_id)
        if record is None:
            _missing('parameter_missing', role + ': missing coefficient evidence')
        _evidence(record, str(parameter_id), pack)
        families.append(_source_family(pack, record))
        basis = record.get('measured_light_basis')
        if basis is None:
            _missing('measured_light_basis_missing', str(parameter_id) + ': measured_light_basis required')
        if basis not in {'incident', 'absorbed'}:
            raise StudyError('Unsupported measured_light_basis: ' + str(parameter_id))
        if basis != pack['light_basis']:
            issues.append(dict(code='alpha_calibration_basis_conflict', reason='Coefficient measurement basis differs from adopted model input; no hidden conversion',
                               parameter_id=parameter_id, parameter_role=role, measured_light_basis=basis,
                               pack_light_basis=pack['light_basis'], parameter_source_id=record['source_id']))
    if 'butturini_dwarf' in families and pack['light_basis'] != 'absorbed':
        _missing('dwarf_source_requires_absorbed_light', 'D15 adopts absorbed model input for dwarf-source coefficients')
    return issues


def _net_leaf_evidence(pack: dict) -> None:
    """Both phase Rd records need evidence from an explicitly non-dwarf source."""
    try:
        if _source_family(pack) == 'butturini_dwarf':
            _missing('net_leaf_requires_rd_bearing_source', 'D16 dwarf-source convention is before_mito')
        photo = pack.get('photosynthesis', {})
        for role in ('alpha', 'Pmax', 'theta'):
            record = pack.get('parameters', {}).get(_saturation_id(pack) if role == 'Pmax' else photo.get(role), {})
            if _source_family(pack, record) == 'butturini_dwarf':
                _missing('net_leaf_requires_rd_bearing_source', 'Dwarf NRH evidence cannot be relabelled net_leaf')
        for role in ('Rd_day', 'Rd_night'):
            parameter_id = photo.get(role)
            record = pack.get('parameters', {}).get(parameter_id)
            if record is None or _source_family(pack, record) != 'non_dwarf':
                _missing('net_leaf_requires_rd_bearing_source', role + ': non-dwarf source evidence required')
            _parameter(pack, parameter_id, 'umolCO2/m2/s', 0)
    except MissingEvidence as exc:
        _missing('net_leaf_requires_rd_bearing_source', exc.reason)


def _face(row: dict) -> str:
    face = row.get('illuminated_faces')
    if face is None:
        _missing('illuminated_faces_undeclared', 'Biological illuminated face is undeclared')
    if face not in {'adaxial_only', 'abaxial_only', 'both'}:
        raise StudyError('Unsupported illuminated_faces')
    if face == 'both':
        _missing('two_sided_exchange_unavailable', 'Two-sided exchange is not modelled')
    if not row.get('face_source_ref'):
        _missing('illuminated_faces_evidence_missing', 'Biological face mapping requires face_source_ref')
    return face


def _combined_face(patch: dict, contributions: list[dict]) -> str:
    faces = []
    for row in contributions:
        # A single fixture can use the explicit patch declaration. Multiple
        # fixtures require their own evidence so opposite faces cannot be hidden.
        faces.append(_face(row if len(contributions) > 1 or 'illuminated_faces' in row else patch))
    if len(set(faces)) > 1:
        _missing('two_sided_exchange_unavailable', 'Opposite-face fixtures require a two-sided physiological model')
    if faces[0] == 'abaxial_only':
        _missing('abaxial_exchange_unavailable', 'Adopted exchange model supports evidenced adaxial_only only')
    return faces[0]


def _component(status: str, value: float | None = None, rows: list | None = None,
               issues: list | None = None, **extra: Any) -> dict:
    return dict(status=status, value_gC=value, rows=rows or [], issues=issues or [], **extra)


def _unavailable(exc: MissingEvidence) -> dict:
    return _component('unavailable', issues=[dict(code=exc.code, reason=exc.reason)])


def _context(p3: dict) -> dict:
    if not isinstance(p3, dict) or p3.get('schema_version') != SCHEMA:
        raise StudyError('P4 interval request schema required; use an explicit adapter for P3 exports')
    for key in IDENTITY:
        if key == 'trajectory_weight':
            _finite(p3.get(key), key, 0)
        elif key.startswith('geometry_hash'):
            _sha(p3.get(key), key)
        else:
            _text(p3.get(key), key)
    _interval(p3)
    for side in ('start', 'end'):
        records = p3.get('organ_states_' + side)
        _index(records, 'organ_id')
        if digest(records) != p3['geometry_hash_' + side]:
            raise StudyError('Interval geometry hash does not match complete preserved organ states: ' + side)
    _index(p3.get('events', []), 'event_id')
    return {key: p3[key] for key in IDENTITY}


def _owner_paths(config: dict) -> list[dict]:
    """Read the pinned P3 audit vocabulary; never import or run the producer."""
    paths = []
    def add(path: str, metric: str, target: str) -> None:
        paths.append(dict(path=path, metric=metric, target=target))
    clock = config.get('clock') or {}
    if clock.get('kind') == 'piecewise_linear_response':
        add('clock.input_metric', clock['input_metric'], 'clock')
    for i, particle in enumerate(config.get('parameter_particles') or []):
        for name, family in particle.get('families', {}).items():
            for j, feature in enumerate(family.get('features', [])):
                metric = feature.removesuffix('_missing')
                if metric not in ENVIRONMENT | P3_STRUCTURAL_FEATURES:
                    raise StudyError('Unknown P3 family feature/alias cannot prove environment independence: ' + feature)
                if metric in ENVIRONMENT and any(row[j] != 0 for row in family['coefficients']):
                    add(f'parameter_particles[{i}].families.{name}.features[{j}]', metric, 'family')
        for axis, policy in particle.get('axes', {}).items():
            for key, coefficient in (policy.get('stop_logit') or {}).get('coefficients', {}).items():
                if key in ENVIRONMENT and coefficient != 0:
                    add(f'parameter_particles[{i}].axes.{axis}.stop_logit.coefficients.{key}', key, 'stop')
    if config.get('light_response'):
        add('light_response', 'dli_mol_m2_day', 'size_target')
    calibration = config.get('calibration') or {}
    for i, feature in enumerate(calibration.get('applied_features', [])):
        add(f'calibration.applied_features[{i}]', feature['column'], feature['role'])
    if calibration and 'applied_features' not in calibration:
        add('calibration', 'unknown', 'provenance_unavailable')
    return paths


@_strict_api
def inspect_p3_coupling(p3_manifest: dict | None, frozen_config: dict | None,
                        calibration_provenance: dict | None) -> dict:
    """Return full producer audit and a conservative D9 assessment, without feedback."""
    try:
        manifest = _sealed(p3_manifest, 'p3_manifest')
        config = _sealed(frozen_config, 'frozen_config')
        if manifest.get('config_hash') != frozen_config['sha256']:
            raise StudyError('P3 manifest and frozen config hashes disagree')
        if manifest.get('schema_version') != 'probabilistic-compound-1':
            _missing('p3_schema_unsupported', 'Producer schema is not pinned by this diagnostic')
        required = ('p3_light_coupling', 'p3_environment_paths', 'environment_audit_status')
        if any(key not in manifest for key in required):
            _missing('p3_environment_audit_missing', 'Legacy clock-only flags are insufficient')
        declared = manifest['p3_environment_paths']
        normalized = [{key: row[key] for key in ('path', 'metric', 'target')} for row in declared]
        observed = _owner_paths(config)
        if sorted(normalized, key=digest) != sorted(observed, key=digest):
            raise StudyError('P3 full-config environment audit disagrees with manifest')
        light = config.get('light_response')
        if manifest['p3_light_coupling'] != ('size_target_dli' if light else 'none'):
            raise StudyError('p3_light_coupling disagrees with frozen config')
        issues = []
        provenance = None
        if config.get('calibration'):
            if not calibration_provenance:
                issues.append(dict(code='embedded_response_provenance_missing', reason='Frozen calibration provenance is absent'))
            else:
                provenance = _sealed(calibration_provenance, 'calibration_provenance')
                if provenance.get('applied_features') != config['calibration'].get('applied_features'):
                    raise StudyError('Embedded fitted effects disagree with calibration provenance')
                for field in ('parameter_set_id', 'fit_plan_hash', 'parameter_set_hash', 'calibration_clock_reference'):
                    if field in config['calibration'] and provenance.get(field) != config['calibration'][field]:
                        raise StudyError('Frozen calibration provenance mismatch: ' + field)
                if not provenance.get('parameter_set_id') or not provenance.get('fit_plan_hash'):
                    issues.append(dict(code='embedded_response_provenance_missing', reason='Parameter-set ID and fit-plan hash required'))
                else:
                    _sha(provenance['fit_plan_hash'], 'fit_plan_hash')
        if manifest['environment_audit_status'] != 'complete' or any(p['metric'] == 'unknown' for p in observed):
            issues.append(dict(code='p3_environment_audit_missing', reason='Producer audit is incomplete'))
        allowed = {('temperature_c', 'clock'), ('dli_mol_m2_day', 'size_target')}
        violations = [row for row in observed if (row['metric'], row['target']) not in allowed and row['metric'] != 'unknown']
        clock = config.get('clock') or {}
        if clock.get('kind') not in {'calendar', 'piecewise_linear_response'}:
            violations.append(dict(path='clock', metric='unsupported_clock', target='clock'))
        elif clock.get('kind') == 'piecewise_linear_response':
            if clock.get('input_metric') != 'temperature_c' or clock.get('input_unit') != 'deg C':
                violations.append(dict(path='clock.input_unit', metric='incompatible_clock_units', target='clock'))
            normalization = clock.get('normalization')
            if not normalization:
                issues.append(dict(code='calibration_clock_mapping_unverified', reason='Missing normalized temperature-clock evidence'))
            else:
                base, ref, cap, upper = (_finite(normalization[k], k) for k in ('t_base_c', 't_ref_c', 'm_max', 'upper_knot_c'))
                if not base < ref <= upper or cap < 1:
                    raise StudyError('Invalid normalized clock declaration')
                values = sorted({base, ref, upper, *([base + cap * (ref - base)] if base + cap * (ref - base) < upper else [])})
                if normalization.get('lower_knot_c') is not None:
                    lower = _finite(normalization['lower_knot_c'], 'lower_knot_c')
                    if lower >= base:
                        raise StudyError('Declared lower temperature knot must be below T_base')
                    values.insert(0, lower)
                knots = [dict(value=x, multiplier=max(0., min((x-base)/(ref-base), cap))) for x in values]
                if clock.get('knots') != knots:
                    violations.append(dict(path='clock.knots', metric='normalization_mismatch', target='clock'))
                if config.get('calibration'):
                    binding = (provenance or {}).get('calibration_clock_reference') or {}
                    if binding.get('kind') != 'fixed_setpoint' or binding.get('time_basis') != 'calendar_day' or not binding.get('source_ref') or binding.get('temperature_c') != ref:
                        issues.append(dict(code='calibration_clock_mapping_unverified', reason='Frozen fixed-setpoint calibration evidence is missing/incompatible'))
        for particle in config.get('parameter_particles', []):
            for name, family in particle.get('families', {}).items():
                if any(key.removesuffix('_missing') in ENVIRONMENT for key in family.get('features', [])):
                    violations.append(dict(path='families.' + name, metric='forbidden_feature', target='family'))
        if light:
            for path, value in [('light_response.unit', light.get('unit')),
                                ('light_response.applicability_interval.unit', (light.get('applicability_interval') or {}).get('unit'))]:
                if value == 'mol/m2/d':
                    issues.append(dict(code='legacy_dli_unit_spelling', reason='Frozen DLI spelling is obsolete; regenerate explicitly without numerical conversion',
                                       field=path, actual=value, expected=DLI_UNIT))
                    violations.append(dict(path=path, metric='legacy_dli_unit_spelling', target='size_target'))
        if light and (light.get('fixed_over_horizon') is not True or light.get('unit') != DLI_UNIT or light.get('kind') != 'size_target_dli'):
            violations.append(dict(path='light_response', metric='invalid_contract', target='size_target'))
        if violations:
            issues.append(dict(code='p3_d9_policy_incompatible', reason='D9 forbids one or more active response paths'))
        unknown = bool([i for i in issues if i['code'] != 'p3_d9_policy_incompatible'])
        compatibility = 'incompatible' if violations else ('unavailable' if unknown or config.get('environment_profile') != 'd9' else 'compatible')
        return dict(status='unavailable' if unknown else ('incompatible' if violations else 'complete'),
                    d9_compatibility=compatibility, paths=deepcopy(declared), issues=issues,
                    p3_light_coupling=manifest['p3_light_coupling'], feedback_action='none')
    except MissingEvidence as exc:
        return dict(status='unavailable', d9_compatibility='unavailable', paths=None,
                    issues=[dict(code=exc.code, reason=exc.reason)], feedback_action='none')
    except (KeyError, IndexError, TypeError) as exc:
        raise StudyError('Malformed producer audit/config representation') from exc


def _cover(records: list[dict], start: datetime, end: datetime, label: str) -> list[dict]:
    ordered = sorted(records, key=lambda row: _interval(row)[0])
    cursor = start
    for row in ordered:
        a, b = _interval(row)
        if a < cursor or b > end:
            raise StudyError(label + ': overlapping or out-of-range intervals')
        if a > cursor:
            _missing('time_coverage_missing', label + ': interval gap')
        cursor = b
    if cursor != end:
        _missing('time_coverage_missing', label + ': incomplete interval')
    return ordered


def _at(records: list[dict], instant: datetime) -> dict:
    return next(row for row in records if _interval(row)[0] <= instant < _interval(row)[1])


def _env(environment: dict, context: dict, pack: dict) -> list[dict]:
    if not environment or not environment.get('records'):
        _missing('environment_missing', 'Explicit measured or assumed environment intervals required')
    start, end = _interval(context)
    for row in environment['records']:
        if row.get('plant_instance_id') != context['plant_instance_id']:
            raise StudyError('Environment plant instance mismatch')
        if row.get('environment_kind') not in {'measured', 'assumed', 'forecast'} or not row.get('source_ref'):
            _missing('environment_provenance_missing', 'Environment origin and source required')
    return _cover(environment['records'], start, end, 'environment')


def _area_evidence(row: dict, context: dict, value: float, unit: str, hypothetical: bool) -> dict:
    """Validate declared physical support; a declaration is not biological validation."""
    evidence = row.get('area_evidence')
    if evidence is None:
        if hypothetical:
            return dict(status='hypothetical', quantity='hypothetical_one_sided_lamina',
                        unit=unit, value=value, source_ref='legacy_explicit_hypothetical_input')
        _missing('physical_area_evidence_missing', 'Supported one-sided lamina evidence is required')
    if not isinstance(evidence, dict):
        raise StudyError('area_evidence must be an object')
    if evidence.get('schema_version') != 'p4-area-evidence-1':
        _missing('physical_area_evidence_missing', 'Declare the versioned area evidence contract')
    if evidence.get('quantity') != 'physical_one_sided_lamina' or evidence.get('status') != 'supported':
        _missing('physical_area_unsupported', 'Projection, hull, unvalidated A1/A2 and double-face estimates are not supported lamina area')
    if evidence.get('area_method') in {'area_review_A1', 'ring_projection_A1', 'projected_proxy', 'hull_surface', 'hull_envelope', 'two_face_mesh'} or evidence.get('estimator_status') in {'proposed', 'unvalidated'}:
        _missing('physical_area_unsupported', 'An estimator proposal or whole-plant projection cannot qualify spatial lamina support')
    expected_support = 'located_tissue_partition' if 'patch_id' in row else 'organ_lamina'
    if evidence.get('spatial_support') != expected_support:
        _missing('physical_area_evidence_missing', 'Area support must explicitly identify ' + expected_support)
    if evidence.get('unit') != unit:
        _missing('area_unit_incompatible', 'Area evidence unit must match the named input field: ' + unit)
    if evidence.get('value') != value:
        raise StudyError('Area evidence value differs from its input')
    expected = dict(plant_instance_id=context['plant_instance_id'], organ_id=row['organ_id'], area_basis_id=context['area_basis_id'])
    if 'patch_id' in row:
        expected.update(patch_id=row['patch_id'], geometry_hash=context['geometry_hash'])
    else:
        expected['geometry_hash'] = context['geometry_hash']
    if any(evidence.get(key) != val for key, val in expected.items()):
        _missing('area_identity_mismatch', 'Area evidence must identify the exact plant, organ, patch, basis and geometry')
    for key in ('source_ref', 'source_row_id', 'support_source_ref'):
        if not evidence.get(key):
            _missing('physical_area_evidence_missing', 'Area evidence requires ' + key)
    if not evidence.get('source_sha256'):
        _missing('physical_area_evidence_missing', 'Area source hash is missing')
    _sha(evidence['source_sha256'], 'area source hash')
    if 'patch_id' in row:
        for key in ('tissue_partition_id', 'partition_source_ref', 'partition_sha256'):
            if not evidence.get(key):
                _missing('tissue_partition_evidence_missing', 'Disjoint tissue partition evidence requires ' + key)
        _sha(evidence['partition_sha256'], 'partition source hash')
    return deepcopy(evidence)


def _physical_light_support(light: dict, pack: dict) -> dict:
    """One plant slice; retain whole-canopy provenance without pooling biology."""
    context = light['context']; areas = {}; seen = set(); source_rows = set()
    canopy = light.get('canopy_provenance')
    if light.get('light_scope', 'plant') not in {'plant', 'canopy'}:
        raise StudyError('Unknown light_scope')
    canopy_tagged = context.get('canopy_id') or any(r.get('canopy_id') or r.get('canopy_geometry_hash') for r in light['samples'])
    if light.get('light_scope') == 'canopy' or canopy is not None or canopy_tagged:
        if not isinstance(canopy, dict) or light.get('light_scope') != 'canopy':
            _missing('canopy_provenance_missing', 'Canopy illumination requires explicit scope and provenance')
        members = canopy.get('plant_instance_ids', [])
        if not members or len(set(members)) != len(members) or context['plant_instance_id'] not in members:
            _missing('canopy_identity_mismatch', 'Selected plant must occur exactly once in the canopy membership')
        for key in ('canopy_id', 'source_ref', 'source_sha256', 'geometry_hash'):
            if not canopy.get(key):
                _missing('canopy_provenance_missing', 'Full-canopy provenance requires ' + key)
        _sha(canopy['source_sha256'], 'canopy source hash'); _sha(canopy['geometry_hash'], 'canopy geometry hash')
        for sample in light['samples']:
            if sample.get('canopy_id') != canopy['canopy_id'] or sample.get('canopy_geometry_hash') != canopy['geometry_hash']:
                _missing('canopy_identity_mismatch', 'Every sample must retain the full-canopy source geometry association')
    for patch in light['patches']:
        for key in ('plant_instance_id', 'area_basis_id', 'geometry_hash'):
            if key in patch and patch[key] != context[key]:
                raise StudyError('Patch context mismatch: ' + key)
        if 'area_weight_cm2' in patch or patch.get('area_unit', 'm2') != 'm2':
            _missing('area_unit_incompatible', 'Supply weights accept area_weight_m2 only')
        if patch.get('area_weight_m2') is None:
            _missing('physical_area_evidence_missing', 'Supply area_weight_m2 is missing')
        hypothetical = patch.get('geometry_kind') == 'hypothetical_tissue' and pack['review_status'] == 'hypothetical'
        area = _area_evidence(patch, context, patch['area_weight_m2'], 'm2', hypothetical)
        partition = area.get('tissue_partition_id', patch.get('tissue_partition_id', patch['patch_id']))
        if partition in seen:
            _missing('duplicate_tissue_partition', 'One physical tissue partition may contribute only once, independent of patch ID')
        seen.add(partition)
        if area.get('source_sha256'):
            source_row = (area['source_sha256'], area['source_row_id'])
            if source_row in source_rows:
                _missing('duplicate_tissue_partition', 'The same area source row cannot be counted as another tissue partition')
            source_rows.add(source_row)
        face = patch.get('biological_face_evidence')
        if face is not None or not hypothetical:
            if not isinstance(face, dict) or face.get('kind') not in {'observed_anatomical_mapping', 'reviewed_anatomical_mapping'} or face.get('face') != 'adaxial':
                _missing('illuminated_faces_evidence_missing', 'Normals, winding and top projection do not establish biological adaxial identity')
            if any(face.get(k) != v for k,v in dict(plant_instance_id=context['plant_instance_id'], organ_id=patch['organ_id'], source_ref=patch.get('face_source_ref')).items()) or not face.get('source_sha256'):
                _missing('illuminated_faces_evidence_missing', 'Biological face evidence must identify the tissue and its source')
            _sha(face['source_sha256'], 'biological face source hash')
        areas[patch['patch_id']] = dict(area_evidence=area, tissue_partition_id=partition,
                                        biological_face_evidence=deepcopy(face), hypothetical=hypothetical)
    return dict(patches=areas, canopy_provenance=deepcopy(canopy))


def _area_disclosures(supply: dict, light: dict) -> dict:
    supports = {r['patch_id']: r['area_support'] for r in supply['rows']}
    status = ('unavailable' if supply['status'] != 'available' else
              'hypothetical' if any(s['hypothetical'] for s in supports.values()) else 'supported_declaration')
    return dict(area_evidence_contract='p4-area-evidence-1', area_evidence_status=status,
                physical_area_validated=False, area_support_json=json.dumps(supports, sort_keys=True),
                canopy_provenance_json=json.dumps(light.get('canopy_provenance'), sort_keys=True))


def _scope_supply(state: dict, light: dict, pack: dict) -> None:
    """Completeness is a separate dependency from calculable partial leaf exchange."""
    masses = _mass_scope(state, pack)
    patches = _index(light.get('patches', []), 'patch_id')
    leaves = {key for key in state['included_organ_ids'] if masses[key].get('organ_kind') == 'leaf'}
    if {row.get('organ_id') for row in patches.values()} != leaves:
        _missing('leaf_coverage_missing', 'Light inventory must cover exactly the scoped leaf compartments')
    for organ in leaves:
        area = _number(masses[organ].get('supported_area_m2'), 'metric_area_m2', 0)
        total = math.fsum(p['area_weight_m2'] for p in patches.values() if p['organ_id'] == organ)
        if abs(area - total) > pack['numerics']['area_abs_tol_m2']:
            _missing('leaf_coverage_missing', 'Quadrature weights do not cover scoped tissue area')
    if state['scope'] == 'whole_plant' and not state.get('nonfoliar_assimilation_assumption'):
        _missing('nonfoliar_assimilation_unresolved', 'Declare treatment of nonfoliar assimilation')


def _domain(pack: dict, row: dict) -> None:
    domain = pack.get('applicable_domain')
    if not isinstance(domain, dict) or not domain:
        if pack['review_status'] == 'hypothetical' and pack.get('domain_assumptions'):
            return
        _missing('photosynthesis_domain_unavailable', 'No explicit applicability domain')
    for key, bounds in domain.items():
        if row.get(key) is None:
            _missing('photosynthesis_domain_unavailable', 'Required domain input missing: ' + key)
        value = _finite(row[key], key)
        low, high = (_finite(x, 'domain bound') for x in bounds)
        if low > high:
            raise StudyError('Reversed domain bounds')
        if not low <= value <= high:
            _missing('photosynthesis_domain_unavailable', key + ': outside declared domain')


def _ownership(pack: dict) -> dict[str, dict]:
    if pack.get('respiration_accounting') not in {'before_mito', 'net_leaf'}:
        _missing('respiration_overlap_unresolved', 'Declare exclusive exchange/respiration ownership')
    if pack['respiration_accounting'] == 'net_leaf':
        _net_leaf_evidence(pack)
    ledger = _index(pack.get('respiration_ownership', []), 'organ_id')
    if not ledger:
        _missing('respiration_overlap_unresolved', 'Explicit per-organ respiration ledger required')
    for row in ledger.values():
        if row.get('growth') != 'demand':
            _missing('respiration_overlap_unresolved', 'ASR charges growth cost; net supply cannot charge it again')
        if row.get('maintenance') not in {'downstream', 'leaf_exchange'}:
            _missing('respiration_overlap_unresolved', 'Maintenance owner unresolved')
        if pack['respiration_accounting'] == 'before_mito' and row['maintenance'] != 'downstream':
            _missing('respiration_overlap_unresolved', 'Before-mito supply excludes all mitochondrial costs')
    return ledger


@_strict_api
def compute_leaf_exchange(leaf_samples: dict, environment: dict, parameters: dict | None) -> dict:
    """Integrate explicit piecewise-constant samples; sum fixtures before NRH."""
    issues = []
    try:
        pack = _pack(parameters)
        if pack.get('model_id') != 'nrh':
            _missing('photosynthesis_model_unavailable', 'Only the contracted conditional NRH is implemented')
        if pack.get('light_basis') not in {'incident', 'absorbed'}:
            _missing('photosynthesis_basis_unresolved', 'Declare compatible incident or absorbed basis')
        issues = _photo_evidence_issues(pack)
        ledger = _ownership(pack)
        if not leaf_samples or not leaf_samples.get('samples'):
            _missing('light_samples_missing', 'Time-resolved physical light samples required')
        context = leaf_samples['context']; start, end = _interval(context)
        for field in ('plant_instance_id', 'area_basis_id', 'backend', 'replicate'):
            _text(context.get(field), field)
        _sha(context.get('geometry_hash'), 'light geometry hash')
        env = _env(environment, context, pack)
        if leaf_samples.get('geometry_policy') != 'fixed_snapshot' or not leaf_samples.get('geometry_assumption'):
            _missing('geometry_time_basis_missing', 'Declare the fixed supported-geometry interval assumption')
        inventory = _index(leaf_samples.get('patches', []), 'patch_id')
        fixtures = leaf_samples.get('fixture_ids')
        if not inventory or not fixtures or len(set(fixtures)) != len(fixtures):
            raise StudyError('Unique explicit patch and fixture inventories required')
        support = _physical_light_support(leaf_samples, pack)
        for patch in inventory.values():
            if _face(patch) == 'abaxial_only':
                _missing('abaxial_exchange_unavailable', 'Adopted model does not support abaxial-only exchange')
            if patch.get('optical_eligible') is not True:
                _missing('optical_geometry_ineligible', 'P3 future envelopes cannot supply optical tissue')
            if patch.get('geometry_kind') not in {'measured_tissue', 'hypothetical_tissue'}:
                _missing('optical_geometry_ineligible', 'Declare supported physical tissue, never an envelope or pixel ratio')
            if patch['geometry_kind'] == 'hypothetical_tissue' and pack['review_status'] != 'hypothetical':
                _missing('hypothetical_geometry', 'Hypothetical tissue cannot be presented as reviewed real input')
            if patch.get('organ_id') not in ledger:
                _missing('respiration_overlap_unresolved', 'Leaf organ missing from respiration ledger')
            _positive(patch.get('area_weight_m2'), 'area_weight_m2')
        samples: dict[tuple[str, str], list[dict]] = {(patch, fixture): [] for patch in inventory for fixture in fixtures}
        for row in leaf_samples['samples']:
            key = (row.get('patch_id'), row.get('fixture_id'))
            if key not in samples:
                raise StudyError('Unknown patch/fixture in light samples')
            patch = inventory[key[0]]
            if 'area_weight_cm2' in row or row.get('area_unit', 'm2') != 'm2':
                _missing('area_unit_incompatible', 'Supply sample weights accept m2 only')
            for field in ('plant_instance_id', 'geometry_hash', 'area_basis_id', 'backend', 'replicate'):
                if row.get(field) != context.get(field):
                    raise StudyError('Light sample context mismatch: ' + field)
            if row.get('organ_id') != patch['organ_id'] or row.get('area_weight_m2') != patch['area_weight_m2']:
                raise StudyError('Patch identity/area differs across fixtures/time')
            if row.get('one_sided_area_basis') is not True or row.get('light_basis') != pack['light_basis']:
                raise StudyError('Incompatible area/light basis; never convert by hidden absorptance')
            if row.get('status') != 'available' or row.get('ppfd_umol_m2_s') is None:
                _missing('light_samples_missing', 'Unknown light is not zero light')
            if not row.get('source_ref'):
                _missing('light_provenance_missing', 'Light sample source required')
            _finite(row['ppfd_umol_m2_s'], 'PPFD', 0)
            samples[key].append(row)
        for key in samples:
            samples[key] = _cover(samples[key], start, end, 'light ' + str(key))
        photo = pack.get('photosynthesis', {})
        alpha = _parameter(pack, photo.get('alpha'), 'umolCO2/umol_photon', 0)
        pmax = _parameter(pack, _saturation_id(pack), 'umolCO2/m2/s', 0)
        theta = _parameter(pack, photo.get('theta'), 'dimensionless', 0)
        if alpha == 0 or pmax == 0 or not 0 < theta <= 1:
            raise StudyError('Invalid NRH parameter domain')
        boundaries = {start, end}
        for rows in [env, *samples.values()]:
            for row in rows:
                boundaries.update(_interval(row))
        ordered = sorted(boundaries); fluxes = []
        for a, b in zip(ordered, ordered[1:]):
            erow = _at(env, a); _domain(pack, erow)
            duration_s = (b - a).total_seconds()
            for key, patch in inventory.items():
                contributions = [_at(samples[(key, fixture)], a) for fixture in fixtures]
                illuminated_faces = _combined_face(patch, contributions)
                irradiance = math.fsum(row['ppfd_umol_m2_s'] for row in contributions)
                ai = alpha * irradiance
                # Sum of nonnegative terms avoids catastrophic cancellation.
                root = math.sqrt((ai - pmax) ** 2 + 4 * (1 - theta) * ai * pmax)
                gross = 0.0 if irradiance == 0 else 2 * ai * pmax / (ai + pmax + root)
                rd = 0.0
                if pack['respiration_accounting'] == 'net_leaf':
                    if ledger[patch['organ_id']]['maintenance'] != 'leaf_exchange':
                        _missing('respiration_overlap_unresolved', 'Net leaf Rd requires matching leaf-exchange maintenance ownership')
                    phase = erow.get('phase')
                    if phase not in {'day', 'night'}:
                        _missing('respiration_phase_missing', 'Net leaf exchange needs explicit day/night phase')
                    rd = _parameter(pack, photo.get('Rd_' + phase), 'umolCO2/m2/s', 0)
                exchange = (gross - rd) * patch['area_weight_m2'] * duration_s * GC_PER_UMOL_CO2
                fluxes.append(dict(component='supply', organ_id=patch['organ_id'], patch_id=key,
                                   plant_instance_id=context['plant_instance_id'], geometry_hash=context['geometry_hash'],
                                   area_basis_id=context['area_basis_id'], area_unit='m2',
                                   area_support=deepcopy(support['patches'][key]),
                                   tissue_partition_id=support['patches'][key]['tissue_partition_id'],
                                   canopy_provenance=deepcopy(support['canopy_provenance']),
                                   light_sources=[dict(fixture_id=r['fixture_id'], source_ref=r['source_ref'],
                                                       sample_sha256=digest(r)) for r in contributions],
                                   t_start=a.isoformat(), t_end=b.isoformat(), value_gC=exchange,
                                   illuminated_faces=illuminated_faces, face_source_ref=patch['face_source_ref'],
                                   issues=deepcopy(issues), issue_codes='|'.join(sorted({issue['code'] for issue in issues})),
                                   ppfd_umol_m2_s=irradiance, area_weight_m2=patch['area_weight_m2'],
                                   exchange_umol_m2_s=gross - rd))
        total = math.fsum(row['value_gC'] for row in fluxes)
        _finite(total, 'integrated_supply_gC')
        return _component('available', total, fluxes, issues=issues)
    except MissingEvidence as exc:
        result = _unavailable(exc)
        result['issues'] = issues + result['issues']
        return result


@_strict_api
def compute_respiration(organ_states: dict, environment: dict, accounting_policy: dict | None,
                        dt_s: float) -> dict:
    """Integrate maintenance once using explicit masses and activity histories."""
    try:
        pack = _pack(accounting_policy); ledger = _ownership(pack)
        context = organ_states['context']; start, end = _interval(context)
        if _finite(dt_s, 'dt_s', 0) != (end - start).total_seconds():
            raise StudyError('dt_s is elapsed seconds, not development time')
        env = _env(environment, context, pack)
        masses = _mass_scope(organ_states, pack)
        _rgr5_consistency(organ_states, pack)
        included = organ_states.get('included_organ_ids', [])
        if not included:
            _missing('initial_mass_missing', 'No scoped organ masses')
        rows = []
        for organ in included:
            if organ not in masses or organ not in ledger:
                _missing('initial_mass_missing', 'Missing organ mass/respiration ownership: ' + organ)
            mass = masses[organ]
            if ledger[organ]['maintenance'] == 'leaf_exchange':
                if mass.get('organ_kind') != 'leaf':
                    _missing('respiration_overlap_unresolved', 'Non-leaf maintenance cannot be hidden in leaf Rd')
                rows.append(dict(component='maintenance_excluded', organ_id=organ, value_gC=0.0,
                                 t_start=context['t_start'], t_end=context['t_end']))
                continue
            spec = pack.get('organ_parameter_map', {}).get(organ, {})
            temperature_metric = spec.get('temperature_metric')
            if temperature_metric not in {'leaf_temperature_c', 'air_temperature_c', 'root_temperature_c', 'organ_temperature_c'}:
                _missing('temperature_basis_missing', 'Declare the temperature input for each organ')
            if temperature_metric != 'leaf_temperature_c' or mass.get('organ_kind') != 'leaf':
                if not spec.get('temperature_assumption'):
                    _missing('temperature_basis_missing', 'Non-leaf or surrogate organ temperature needs evidence/assumption')
            rate = _parameter(pack, spec.get('maintenance_rate'), 'gCH2O/g_structural_DM/day', 0)
            q10 = _parameter(pack, spec.get('Q10'), 'dimensionless', 0)
            tref = _parameter(pack, spec.get('Tref'), 'degC')
            rate_record = pack['parameters'].get(spec.get('maintenance_rate'), {})
            tref_record = pack['parameters'].get(spec.get('Tref'), {})
            if 'butturini_dwarf' in {_source_family(pack), _source_family(pack, rate_record), _source_family(pack, tref_record)} and tref != 25:
                _missing('dwarf_maintenance_tref_conflict', 'D17 dwarf-source maintenance uses evidenced Tref=25 C; no global default is supplied')
            if q10 == 0:
                raise StudyError('Q10 must be positive')
            history = mass.get('maintenance_history')
            if history is None:
                if not organ_states.get('maintenance_start_mass_assumption'):
                    _missing('maintenance_history_missing', 'Declare mass history or start-state approximation')
                history = [dict(t_start=context['t_start'], t_end=context['t_end'],
                                structural_dm_g=mass.get('structural_dm_g'))]
            history = _cover(history, start, end, 'maintenance mass')
            plant_history = []
            activity_kind = spec.get('activity_kind')
            if activity_kind == 'constant':
                constant_activity = _parameter(pack, spec.get('activity'), 'dimensionless', 0)
                if constant_activity > 1:
                    raise StudyError('Activity must lie in [0,1]')
            elif activity_kind == 'RGR5':
                if spec.get('rgr5_scope') != 'plant':
                    _missing('RGR5_scope_missing', 'RGR5 requires rgr5_scope=plant')
                plant_history = organ_states.get('plant_rgr5_history') or []
                if not plant_history:
                    _missing('RGR5_history_missing', 'Whole-plant evidence required; organ histories are not substitutes')
                plant_history = _cover(plant_history, start, end, 'plant RGR5')
            else:
                _missing('activity_missing', 'Explicit constant activity or supported RGR5 required')
            boundaries = sorted({start, end, *(t for row in env + history + plant_history for t in _interval(row))})
            for a, b in zip(boundaries, boundaries[1:]):
                erow, hrow = _at(env, a), _at(history, a)
                temperature = erow.get(temperature_metric)
                if temperature is None:
                    if temperature_metric != 'leaf_temperature_c' or not organ_states.get('air_temperature_substitution_assumption'):
                        _missing('leaf_temperature_missing', 'Leaf temperature or labelled air substitution required')
                    temperature = erow.get('air_temperature_c')
                temperature = _number(temperature, 'maintenance_temperature_c')
                weight = _number(hrow.get('structural_dm_g'), 'structural_dm_g', 0)
                if activity_kind == 'RGR5':
                    f_days = _parameter(pack, spec.get('activity_f'), 'day', 0)
                    rgr = _at(plant_history, a)
                    if (rgr.get('rgr5_scope') != 'plant' or rgr.get('plant_instance_id') != context['plant_instance_id']
                            or rgr.get('mass_basis') != 'structural_dm_excluding_reserve'
                            or rgr.get('whole_plant_coverage_complete') is not True or not rgr.get('coverage_statement')
                            or rgr.get('history_complete') is not True or rgr.get('window_days') != 5 or not rgr.get('source_ref')):
                        _missing('RGR5_history_missing', 'Complete independently supported five-day structural mass history required')
                    if not rgr.get('mass_at_now') or not rgr.get('mass_at_5days_ago'):
                        _missing('RGR5_history_missing', 'Dated whole-plant endpoint evidence required')
                    if (_time(rgr['mass_at_now']) != _time(rgr['t_start'])
                            or (_time(rgr['mass_at_now']) - _time(rgr['mass_at_5days_ago'])).total_seconds() != 5 * SECONDS_PER_DAY):
                        _missing('RGR5_history_missing', 'Mass endpoints must span five elapsed days ending at activity record start')
                    w0 = _positive(rgr.get('structural_dm_5days_ago_g'), 'RGR5 initial mass')
                    w1 = _positive(rgr.get('structural_dm_now_g'), 'RGR5 current mass')
                    if w1 < w0:
                        _missing('negative_RGR5_unsupported', 'Negative-growth activity needs a reviewed model')
                    activity = -math.expm1(-f_days * (math.log(w1) - math.log(w0)) / 5)
                    if not 0 <= activity < 1:
                        _missing('RGR5_activity_out_of_domain', 'RGR5 activity must be in [0,1); floating saturation is not clipped')
                else:
                    activity = constant_activity
                value = GC_PER_G_CH2O * rate * weight * q10 ** ((temperature - tref) / 10) * activity * (b - a).total_seconds() / SECONDS_PER_DAY
                _finite(value, 'maintenance_gC', 0)
                rows.append(dict(component='maintenance', organ_id=organ, t_start=a.isoformat(),
                                 t_end=b.isoformat(), value_gC=value, structural_dm_g=weight,
                                 activity=activity, activity_kind=activity_kind,
                                 rgr5_scope='plant' if activity_kind == 'RGR5' else None,
                                 maintenance_activity_zero=activity == 0))
        return _component('available', math.fsum(row['value_gC'] for row in rows), rows)
    except MissingEvidence as exc:
        return _unavailable(exc)


def _rgr5_consistency(state: dict, pack: dict) -> None:
    """Legacy organ-local declarations must agree with the single plant history."""
    specs = pack.get('organ_parameter_map', {})
    if not any(specs.get(o, {}).get('activity_kind') == 'RGR5' for o in state.get('included_organ_ids', [])):
        return
    canonical = state.get('plant_rgr5_history') or []
    if not canonical:
        return  # The existing RGR5 path reports missing canonical evidence.
    start, end = _interval(state['context'])
    canonical = _cover(canonical, start, end, 'plant RGR5')
    fields = ('rgr5_scope', 'plant_instance_id', 'mass_basis', 'whole_plant_coverage_complete',
              'coverage_statement', 'history_complete', 'window_days', 'source_ref', 'source_id',
              'evidence_kind', 'structural_dm_5days_ago_g', 'structural_dm_now_g',
              'mass_at_now', 'mass_at_5days_ago', 'lineage_id', 'sha256')

    def payload(row: dict) -> dict:
        return {key: _time(row[key]).isoformat() if key in {'mass_at_now', 'mass_at_5days_ago'} and row.get(key)
                else row.get(key) for key in fields}

    for mass in state.get('organ_masses', []):
        organ = mass['organ_id']
        if organ not in state['included_organ_ids']:
            continue
        declarations = []
        for holder in (mass, specs.get(organ, {})):
            if holder.get('rgr5') is not None:
                declarations.append((start, end, holder['rgr5']))
        for row in mass.get('maintenance_history') or []:
            if row.get('rgr5') is not None:
                declarations.append((*_interval(row), row['rgr5']))
        for a, b, declaration in declarations:
            for row in canonical:
                c, d = _interval(row)
                if max(a, c) < min(b, d) and payload(declaration) != payload(row):
                    _missing('rgr5_scope_inconsistent', 'Retained organ RGR5 payload/provenance differs from canonical plant history: ' + organ)


def _reserve_boundary(state: dict) -> dict:
    return dict(plant_instance_id=state.get('context', {}).get('plant_instance_id'), scope=state.get('scope'),
                included=sorted(state.get('included_organ_ids', [])) if state.get('scope') != 'whole_plant' else None,
                excluded=sorted(state.get('excluded_organ_ids', [])) if state.get('scope') != 'whole_plant' else None,
                boundary_policy=state.get('boundary_policy'))


def _reserve_provenance(state: dict) -> dict:
    evidence = state.get('reserve_evidence')
    if state.get('reserve_gC') is None:
        _missing('reserve_stock_missing', 'Initial reserve carbon is not supplied')
    if not evidence or not evidence.get('source_ref'):
        _missing('reserve_source_missing', 'reserve_gC requires reserve_evidence.source_ref')
    if not evidence.get('lineage_id'):
        _missing('reserve_lineage_missing', 'Declare the supplied reserve evidence lineage; no per-run ID is inferred')
    _text(evidence['source_ref'], 'reserve source_ref')
    _text(evidence['lineage_id'], 'reserve lineage_id')
    boundary = _reserve_boundary(state)
    chain = digest(dict(lineage_id=evidence['lineage_id'], accounting_boundary=boundary))
    evidence_hash = digest(dict(evidence=evidence, boundary=boundary, stock_at=state.get('stock_at'), reserve_gC=state['reserve_gC']))
    return dict(reserve_provenance_chain_id=chain, reserve_evidence_hash=evidence_hash,
                reserve_source_ref=evidence['source_ref'], reserve_provenance_status='declared')


def _disclosures(state: dict, envelope: dict | None) -> dict:
    """Reporting statuses never become substituted model-input defaults."""
    pack = _sealed(envelope, 'parameter_pack') if envelope else {}
    specs = pack.get('organ_parameter_map', {})
    active = [specs.get(o, {}) for o in state.get('included_organ_ids', [])]
    rgr = [s for s in active if s.get('activity_kind') == 'RGR5']
    scopes = {s.get('rgr5_scope') for s in rgr}
    scope = ('undeclared' if None in scopes else 'plant' if scopes == {'plant'} else 'inconsistent' if len(scopes) > 1 else 'unsupported') if rgr else (
        'not_applicable' if active and all(s.get('activity_kind') == 'constant' for s in active) else 'undeclared')
    fields = dict(respiration_accounting=pack.get('respiration_accounting') or 'undeclared',
                  light_basis=pack.get('light_basis') or 'undeclared', rgr5_scope=scope,
                  source_buffer_feedback='not_modelled', nonfoliar_assimilation='not_modelled',
                  maintenance_temperature_integration='sub_daily', diagnostic_interpretation='cross_cultivar_consistency_check',
                  nrh_fit_preprocessing='unresolved', two_sided_exchange='not_modelled', sympodial_continuation='not_modelled',
                  light_to_orientation_response='not_modelled', fvcb='not_modelled',
                  rgr5_mass_basis_deviation_from_source='not_applicable', total_dm_substitute_caveat='not_applicable',
                  nrh_interpretation_note='Conditional source-model interpretation only: if the origin-passing three-parameter curve was fitted to net data without correction, alpha/saturation and supply may be underestimated and leaf respiration counted again. Under that conservative-bias interpretation ratio >= 1 is credible, while ratio < 1 alone is not evidence of shortage. This is not a target adequacy guarantee; light, domain, mass, reserve and omitted-process uncertainty remain.',
                  disclosure_reasons=[])
    for key in ('respiration_accounting', 'light_basis', 'rgr5_scope'):
        if fields[key] in {'undeclared', 'not_applicable', 'inconsistent', 'unsupported'}:
            fields['disclosure_reasons'].append(dict(field=key, status=fields[key], reason='Not declared or not applicable to the supplied activity/model configuration'))
            if key == 'rgr5_scope':
                fields['disclosure_reasons'][-1]['declared_scopes'] = sorted(str(s) for s in scopes)
    if rgr:
        families = [(pack.get('parameters', {}).get(s.get('activity_f')) or {}).get('source_family', pack.get('source_family')) for s in rgr]
        if 'butturini_dwarf' in families:
            fields['rgr5_mass_basis_deviation_from_source'] = 'source_total_dm_with_roots_and_buffer_vs_p4_structural_dm_excluding_reserve'
        elif any(f is None for f in families):
            fields['rgr5_mass_basis_deviation_from_source'] = 'source_basis_undeclared'
    if state.get('total_dm_substitute') or any(m.get('total_dm_substitute') for m in state.get('organ_masses', [])):
        fields['total_dm_substitute_caveat'] = 'Explicit substitution assumption: source static branch assumes 90 percent structural mass (approximately 10 percent buffer). Not a target conversion; P4 does not multiply mass by 0.9 and unsupported mass bases remain unavailable.'
    try:
        fields.update(_reserve_provenance(state))
    except MissingEvidence as exc:
        fields.update(reserve_provenance_chain_id='unavailable', reserve_evidence_hash='unavailable', reserve_source_ref='undeclared', reserve_provenance_status='unavailable')
        fields['disclosure_reasons'].append(dict(field='reserve_provenance_chain_id', status='unavailable', reason=exc.reason, code=exc.code))
    return fields


def _mass_scope(state: dict, pack: dict) -> dict[str, dict]:
    included = state.get('included_organ_ids', [])
    excluded = state.get('excluded_organ_ids', [])
    if len(set(included)) != len(included) or set(included) & set(excluded):
        raise StudyError('Carbon compartments must be disjoint')
    if state.get('scope') not in {'whole_plant', 'supported_leaf_subset'}:
        raise StudyError('Unknown carbon scope')
    if pack.get('scope') != state['scope']:
        _missing('parameter_scope_mismatch', 'Parameter pack must explicitly cover the requested carbon scope')
    masses = _index(state.get('organ_masses', []), 'organ_id')
    if not included or any(organ not in masses for organ in included):
        _missing('initial_mass_missing', 'Every included organ needs an explicit mass compartment')
    for organ in included:
        mass = masses[organ]
        if mass.get('mass_basis') != 'structural_dm_excluding_reserve':
            _missing('maintenance_mass_basis_unresolved', 'Mass must exclude reserves and use structural DM')
        if set(mass.get('child_organ_ids', [])) & set(included):
            raise StudyError('Parent and child mass compartments overlap')
        _number(mass.get('structural_dm_g'), 'structural_dm_g', 0)
        if not mass.get('source_ref') or mass.get('evidence_kind') not in EVIDENCE_KINDS - {'unidentified'}:
            _missing('mass_provenance_missing', 'Scoped structural mass requires evidence/assumption')
    if state['scope'] == 'whole_plant':
        if excluded:
            _missing('whole_plant_scope_incomplete', 'Excluded living compartments cannot be called a whole-plant budget')
        if not any(masses[o].get('organ_kind') == 'root' for o in included):
            _missing('root_scope_missing', 'Whole-plant accounting requires root mass and demand')
        reproduction = state.get('reproductive_scope')
        if not isinstance(reproduction, dict) or reproduction.get('status') not in {'not_present', 'accounted'} or not reproduction.get('source_ref') or not state.get('coverage_statement'):
            _missing('organ_scope_missing', 'Explicit reproductive and whole-plant coverage statements required')
        reproductive_ids = set(reproduction.get('organ_ids', []))
        if reproduction['status'] == 'accounted' and (not reproductive_ids or not reproductive_ids <= set(included)):
            _missing('reproductive_demand_missing', 'Accounted reproduction requires included organ compartments')
        if reproduction['status'] == 'not_present' and reproductive_ids:
            raise StudyError('Absent reproduction cannot have reproductive compartments')
    elif any(masses[o].get('organ_kind') != 'leaf' for o in included):
        raise StudyError('supported_leaf_subset cannot include non-leaf compartments')
    return masses


@_strict_api
def infer_structural_demand(p3_interval: dict, mass_state: dict,
                            mass_form_parameters: dict | None) -> dict:
    """Infer required carbon from immutable increments; never allocate/realize growth."""
    try:
        pack = _pack(mass_form_parameters)
        masses = _mass_scope(mass_state, pack)
        start = _index(p3_interval['organ_states_start'], 'organ_id')
        end = _index(p3_interval['organ_states_end'], 'organ_id')
        direct = _index(mass_state.get('mass_increments', []), 'organ_id')
        included = mass_state['included_organ_ids']
        if mass_state['scope'] == 'whole_plant' and p3_interval.get('post_termination_scope') == 'unavailable':
            _missing('sympodial_continuation_not_modeled', 'Whole-plant post-terminal demand unavailable')
        for event in p3_interval.get('events', []):
            if event.get('event_kind') in {'truss', 'terminal'} and any(event.get(k) is not None for k in ('geometry', 'supported_area_cm2')):
                raise StudyError('Truss/terminal events cannot supply leaf geometry')
            if mass_state['scope'] == 'whole_plant' and event.get('event_kind') == 'truss' and not event.get('material_source_ref'):
                _missing('reproductive_demand_missing', 'Truss event is not a reproductive mass observation')
        if any(row.get('retention_assumption_exceeded') for row in end.values() if row['organ_id'] in included):
            _missing('retention_assumption_exceeded', 'No death/remobilization model is adopted')
        missing_organs = set(end) - set(included) - set(mass_state.get('excluded_organ_ids', []))
        if missing_organs:
            _missing('organ_scope_missing', 'Unaccounted endpoint organs: ' + ','.join(sorted(missing_organs)))
        demands = []
        tolerance = pack['numerics']['mass_abs_tol_gDM']
        for organ in included:
            mass = masses[organ]; initial = mass['structural_dm_g']
            area_support = []
            spec = pack.get('organ_parameter_map', {}).get(organ, {})
            if organ in direct:
                record = direct[organ]
                if record.get('unit') != 'g_structural_DM':
                    raise StudyError('Direct mass increments require g_structural_DM')
                if not record.get('source_ref') or record.get('evidence_kind') not in EVIDENCE_KINDS - {'unidentified'}:
                    _missing('mass_increment_evidence_missing', 'Direct mass increment needs explicit evidence/assumption')
                if _number(record.get('structural_dm_start_g'), 'start mass', 0) != initial:
                    raise StudyError('Mass-increment anchor disagrees with initial mass')
                target = _number(record.get('structural_dm_end_g'), 'end mass', 0)
            else:
                if organ not in start or organ not in end:
                    _missing('mass_form_mapping_missing', 'No supported endpoint mass mapping for ' + organ)
                mapping = pack.get('mass_form_mapping', {}).get(organ)
                if not mapping or not mapping.get('source_ref'):
                    _missing('mass_form_mapping_missing', 'Independent mass/form evidence required for ' + organ)
                candidates = []
                inverses = mapping.get('inverses', [])
                inverse_ids = [inverse.get('inverse_id', inverse['kind']) for inverse in inverses]
                if len(inverses) > 1 and (not mapping.get('primary_inverse') or any(not inverse.get('inverse_id') for inverse in inverses)):
                    _missing('primary_inverse_missing', 'Multiple inverses require unique inverse_id and explicit primary_inverse')
                for inverse_id in inverse_ids:
                    _text(inverse_id, 'inverse_id')
                if mapping.get('primary_inverse') is not None:
                    _text(mapping['primary_inverse'], 'primary_inverse')
                if len(set(inverse_ids)) != len(inverse_ids):
                    raise StudyError('Mass-form inverse IDs must be unique')
                primary = mapping.get('primary_inverse', inverse_ids[0] if inverse_ids else None)
                if inverses and primary not in inverse_ids:
                    raise StudyError('primary_inverse must name a supplied inverse_id')
                for inverse in inverses:
                    if inverse['kind'] == 'area':
                        a0, a1 = start[organ].get('supported_area_cm2'), end[organ].get('supported_area_cm2')
                        for side, endpoint, value in [('start', start[organ], a0), ('end', end[organ], a1)]:
                            if 'supported_area_m2' in endpoint or endpoint.get('area_unit', 'cm2') != 'cm2':
                                _missing('area_unit_incompatible', 'Area inverse accepts supported_area_cm2 only')
                            if value is None:
                                _missing('physical_area_evidence_missing', 'Area inverse requires supported endpoint area')
                            evidence_row = dict(endpoint, area_evidence=p3_interval.get('area_evidence_' + side, {}).get(organ))
                            area_support.append(dict(endpoint=side, evidence=_area_evidence(evidence_row, dict(plant_instance_id=p3_interval['plant_instance_id'],
                                area_basis_id=p3_interval['area_basis_id'], geometry_hash=p3_interval['geometry_hash_' + side]),
                                value, 'cm2', pack['review_status'] == 'hypothetical' and endpoint.get('geometry_kind', 'hypothetical_tissue') == 'hypothetical_tissue')))
                        if start[organ].get('area_basis_id') != p3_interval['area_basis_id'] or end[organ].get('area_basis_id') != p3_interval['area_basis_id']:
                            raise StudyError('Area inversion has inconsistent support/basis')
                        s0 = _parameter(pack, inverse.get('sla_start'), 'm2/g_structural_blade_DM', 0)
                        s1 = _parameter(pack, inverse.get('sla_end'), 'm2/g_structural_blade_DM', 0)
                        if s0 == 0 or s1 == 0 or mass.get('mass_compartment') != 'blade':
                            _missing('mass_form_mapping_missing', 'Positive blade SLA and matching compartment required')
                        candidates.append((_number(a1, 'area_end', 0) * CM2_TO_M2 - _number(a0, 'area_start', 0) * CM2_TO_M2 + s0 * initial) / s1)
                    elif inverse['kind'] == 'dimension':
                        field = inverse.get('field')
                        if field not in {'rachis_arc_length_mm', 'left_extent_mm', 'right_extent_mm', 'segment_length_mm'}:
                            raise StudyError('Unsupported metric dimension field')
                        lam = _parameter(pack, inverse.get('lambda'), 'mm/mg^gamma', 0)
                        gamma = _parameter(pack, inverse.get('gamma'), 'dimensionless', 0)
                        if lam == 0 or gamma == 0:
                            raise StudyError('Positive allometric lambda/gamma required')
                        base = (_number(end[organ].get(field), field, 0) - _number(start[organ].get(field), field, 0) + lam * (1000 * initial) ** gamma) / lam
                        if base < 0:
                            _missing('negative_mass_change_unsupported', 'Allometric inverse has a negative base')
                        candidates.append(base ** (1 / gamma) / 1000)
                    else:
                        raise StudyError('Unsupported mass-form inverse')
                if not candidates:
                    _missing('mass_form_mapping_missing', 'No inverse supplied')
                target = candidates[inverse_ids.index(primary)]
                if any(abs(value - target) > tolerance for value in candidates):
                    _missing('inconsistent_mass_form', 'Independent inverses disagree; no averaging')
            increment = target - initial
            if increment < 0:
                _missing('negative_mass_change_unsupported', 'Negative mass is not a remobilization credit')
            if organ in end and organ not in start and not mass.get('birth_mass_accounted'):
                _missing('birth_mass_unfunded_or_unknown', 'New-organ initial material must be explicitly accounted')
            if organ in end and organ not in start and initial != 0:
                _missing('birth_transfer_unresolved', 'Pre-existing bud transfers require a separate stock ledger; new growth starts at zero mass')
            q = _parameter(pack, spec.get('ASR'), 'gCH2O/g_structural_DM', 0)
            carbon = _parameter(pack, spec.get('carbon_fraction'), 'gC/g_structural_DM', 0)
            if q == 0 or not 0 < carbon <= min(1, GC_PER_G_CH2O * q):
                raise StudyError('Require 0 < carbon fraction <= min(1, chi*ASR)')
            demand = GC_PER_G_CH2O * q * increment
            demands.append(dict(component='demand', organ_id=organ, value_gC=demand,
                                area_support=area_support,
                                structural_increment_gDM=increment, structural_increment_gC=carbon * increment,
                                growth_respiration_required_gC=demand - carbon * increment,
                                primary_inverse='direct_mass_increment' if organ in direct else primary))
        return _component('available', math.fsum(row['value_gC'] for row in demands), demands)
    except MissingEvidence as exc:
        return _unavailable(exc)


@_strict_api
def audit_carbon_balance(diagnostic_ledger: dict, originating_diagnostic: dict | None = None) -> dict:
    """Audit only a funded hypothetical ledger. Does not return a new plant state."""
    try:
        fields = ('reserve_start_gC', 'reserve_end_gC', 'supply_gC', 'maintenance_gC',
                  'growth_respiration_gC', 'structural_increment_gC', 'external_import_gC', 'external_export_gC')
        values = {k: _number(diagnostic_ledger.get(k), k, None if k == 'supply_gC' else 0) for k in fields}
        if diagnostic_ledger.get('funded') is not True or diagnostic_ledger.get('hypothetical') is not True:
            _missing('ledger_not_funded', 'Only explicitly hypothetical funded accounting can be audited')
        if originating_diagnostic is None:
            _missing('originating_diagnostic_missing', 'Supply the originating C04 diagnostic, not just an echoed pack ID')
        _verify_originating_diagnostic(originating_diagnostic)
        origin = originating_diagnostic
        pack_id = origin['diagnostic']['pack_id']
        if not diagnostic_ledger.get('pack_id') or diagnostic_ledger['pack_id'] != pack_id:
            _missing('ledger_pack_mismatch', 'Ledger pack_id must match the verified originating diagnostic')
        comps, state = origin['components'], origin['inputs']['carbon_state']
        if any(comps[key]['status'] != 'available' for key in ('supply', 'maintenance', 'demand', 'budget')):
            _missing('originating_diagnostic_unavailable', 'Originating accounting components must be available')
        expected = dict(reserve_start_gC=state['reserve_gC'], supply_gC=comps['supply']['value_gC'],
                        maintenance_gC=comps['maintenance']['value_gC'], external_import_gC=state['external_import_gC'],
                        external_export_gC=state['external_export_gC'],
                        growth_respiration_gC=math.fsum(r['growth_respiration_required_gC'] for r in comps['demand']['rows']),
                        structural_increment_gC=math.fsum(r['structural_increment_gC'] for r in comps['demand']['rows']))
        numerics = _pack(origin['inputs']['parameter_pack'])['numerics']
        for key, value in expected.items():
            if not math.isclose(values[key], value, abs_tol=numerics['carbon_abs_tol_gC'], rel_tol=numerics['carbon_rel_tol']):
                _missing('ledger_origin_value_mismatch', 'Ledger differs from originating diagnostic: ' + key)
        lhs = values['reserve_end_gC'] - values['reserve_start_gC'] + values['structural_increment_gC']
        rhs = values['supply_gC'] - values['maintenance_gC'] - values['growth_respiration_gC'] + values['external_import_gC'] - values['external_export_gC']
        tolerance = _number(diagnostic_ledger.get('abs_tol_gC'), 'abs_tol_gC', 0) + _number(diagnostic_ledger.get('rel_tol'), 'rel_tol', 0) * max(abs(lhs), abs(rhs))
        return dict(status='balanced' if abs(lhs - rhs) <= tolerance else 'imbalance', residual_gC=lhs - rhs, tolerance_gC=tolerance,
                    pack_id=pack_id, originating_diagnostic_sha256=digest(origin), association_verified=True)
    except MissingEvidence as exc:
        return dict(status='unavailable', residual_gC=None, reason=exc.reason, code=exc.code, association_verified=False)


def _budget(state: dict, supply: dict, maintenance: dict, pack: dict | None, light: dict) -> dict:
    try:
        if pack is None:
            _missing('parameter_pack_missing', 'Compatible parameter pack required')
        _reserve_provenance(state)
        _mass_scope(state, pack)
        _scope_supply(state, light, pack)
        if supply['status'] != 'available' or maintenance['status'] != 'available':
            _missing('budget_components_missing', 'Supply and maintenance must both be available')
        if state['scope'] == 'supported_leaf_subset' and not state.get('boundary_policy'):
            _missing('partial_boundary_budget_missing', 'Subset reserve allocation and transfers require an explicit policy')
        for key in ('reserve_gC', 'minimum_reserve_gC', 'external_import_gC', 'external_export_gC'):
            _number(state.get(key), key, 0)
        u = state['reserve_gC'] + supply['value_gC'] + state['external_import_gC'] - state['external_export_gC'] - maintenance['value_gC']
        v = max(u - state['minimum_reserve_gC'], 0) if u >= 0 else None
        return _component('available', v, unprotected_budget_gC=u, maintenance_deficit_gC=max(-u, 0))
    except MissingEvidence as exc:
        return _unavailable(exc)


@_strict_api
def compute_carbon_sufficiency(p3_interval: dict, carbon_state: dict, light_series: dict,
                               environment: dict, parameter_pack: dict | None) -> dict:
    """Pure single plant/trajectory/draw/interval diagnostic; return no growth state."""
    inputs = [p3_interval, carbon_state, light_series, environment, parameter_pack]
    _json_finite(inputs); before = digest(inputs)
    context = _context(p3_interval)
    for field in ('plant_instance_id', 't_start', 't_end'):
        if carbon_state.get('context', {}).get(field) != context[field]:
            raise StudyError('Carbon-state identity/interval mismatch: ' + field)
    if _time(carbon_state.get('stock_at')) != _time(context['t_start']):
        raise StudyError('Reserve stock must be at interval start')
    if light_series:
        for field in ('plant_instance_id', 't_start', 't_end', 'area_basis_id'):
            if light_series.get('context', {}).get(field) != context[field]:
                raise StudyError('Light-series identity/interval mismatch: ' + field)
        if light_series['context'].get('geometry_hash') != context['geometry_hash_start']:
            raise StudyError('Fixed optical snapshot is not the declared interval geometry')
    try:
        pack = _pack(parameter_pack)
    except MissingEvidence as exc:
        pack = None
    coupling = inspect_p3_coupling(p3_interval.get('p3_manifest_ref'), p3_interval.get('frozen_config_ref'), p3_interval.get('calibration_provenance'))
    supply = compute_leaf_exchange(light_series, environment, parameter_pack)
    starting_organs = {row['organ_id'] for row in p3_interval['organ_states_start']}
    if light_series and any(patch['organ_id'] not in starting_organs for patch in light_series.get('patches', [])):
        supply = _unavailable(MissingEvidence('optical_geometry_ineligible', 'Fixed optical snapshot includes an organ absent from the initial geometry'))
    maintenance = compute_respiration(carbon_state, environment, parameter_pack, (_time(context['t_end']) - _time(context['t_start'])).total_seconds())
    demand = infer_structural_demand(p3_interval, carbon_state, parameter_pack)
    budget = _budget(carbon_state, supply, maintenance, pack, light_series)
    components = dict(supply=supply, maintenance=maintenance, demand=demand, budget=budget)
    reasons = []
    for name, result in [*components.items(), ('coupling', coupling)]:
        for reason in result['issues']:
            reasons.append(dict(component=name, **reason,
                                **{k: context[k] for k in ('plant_instance_id', 'trajectory_id', 't_start', 't_end')}, source_ref=None))
    output = dict(context, **{key: None for key in CORE}, schema_version=SCHEMA,
                  diagnostic_scope=carbon_state.get('scope'), evidence_status='conditional_reviewed' if pack and pack['review_status'] == 'reviewed' else 'hypothetical',
                  light_basis=pack['light_basis'] if pack and pack.get('light_basis') in {'incident', 'absorbed'} else 'unavailable', status='unavailable',
                  component_status={key: value['status'] for key, value in components.items()},
                  coupling_audit_status=coupling['status'], d9_compatibility=coupling['d9_compatibility'],
                  feedback_action='none', accepted_for_domain=False, numerical_tolerance_applied=False,
                  reserve_propagation='none', interval_independence='independent_single_interval',
                  reserve_reuse_assumption=carbon_state.get('reserve_reuse_assumption'),
                  pack_id=pack['pack_id'] if pack else None,
                  maintenance_activity_zero=any(r.get('maintenance_activity_zero', False) for r in maintenance['rows']),
                  p4_parameter_draw_id=pack.get('draw_id', pack['pack_id']) if pack else 'unavailable',
                  limiting_inputs=reasons, assumptions=deepcopy(pack.get('assumptions', [])) if pack else [],
                  source_hashes={name: digest(value) for name, value in zip(('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack'), inputs)})
    for key in ('maintenance_start_mass_assumption', 'air_temperature_substitution_assumption', 'boundary_policy', 'nonfoliar_assimilation_assumption', 'coverage_statement', 'reproductive_scope'):
        if carbon_state.get(key):
            output['assumptions'].append(str(carbon_state[key]))
    if light_series.get('geometry_assumption'):
        output['assumptions'].append(light_series['geometry_assumption'])
    if pack:
        output['assumptions'].extend(str(row['temperature_assumption']) for row in pack.get('organ_parameter_map', {}).values() if row.get('temperature_assumption'))
    output.update(_disclosures(carbon_state, parameter_pack))
    output.update(_area_disclosures(supply, light_series))
    if demand['status'] == 'available':
        output['required_growth_carbon_gC'] = demand['value_gC']
    if budget['status'] == 'available':
        output['available_growth_carbon_gC'] = budget['value_gC']
        output['maintenance_deficit_gC'] = budget['maintenance_deficit_gC']
    if all(result['status'] == 'available' for result in components.values()):
        u, v, d = budget['unprotected_budget_gC'], budget['value_gC'], demand['value_gC']
        if u < 0:
            output['status'] = 'maintenance_deficit'
            code, why = 'maintenance_budget_negative', 'Supply and reserves do not fund maintenance/transfers'
        elif d == 0:
            output.update(status='no_growth_demand', growth_deficit_gC=0.0)
            code, why = 'zero_growth_demand', 'Ratio undefined for zero structural growth demand'
        else:
            tol = pack['numerics']['carbon_abs_tol_gC'] + pack['numerics']['carbon_rel_tol'] * max(abs(v), abs(d))
            output.update(status='sufficient' if v + tol >= d else 'growth_deficit',
                          sufficiency_ratio=v / d, growth_deficit_gC=max(d - v, 0),
                          numerical_tolerance_applied=bool(v < d <= v + tol))
            code = None
        if code:
            output['limiting_inputs'].append(dict(component='budget' if u < 0 else 'demand', code=code, reason=why,
                **{k: context[k] for k in ('plant_instance_id', 'trajectory_id', 't_start', 't_end')}, source_ref=None))
    if digest(inputs) != before:
        raise AssertionError('Diagnostic mutated an input')
    output['issue_codes'] = '|'.join(sorted({issue['code'] for issue in output['limiting_inputs']}))
    output['calibration_basis_issues_json'] = json.dumps([issue for issue in supply['issues'] if issue['code'] == 'alpha_calibration_basis_conflict'], sort_keys=True)
    _json_finite(output)
    return dict(diagnostic=output, components=components, coupling_audit=coupling,
                input_hash_before=before, input_hash_after=digest(inputs), inputs=deepcopy(dict(zip(('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack'), inputs))))


@_strict_api
def audit_diagnostic_inputs(request: dict, parameter_pack: dict | None) -> dict:
    """Read-only audit. Blank templates produce actionable missing-input records."""
    _json_finite(request)
    missing = [name for name in ('p3_interval', 'carbon_state', 'light_series', 'environment') if not request.get(name)]
    if parameter_pack is None:
        missing.append('parameter_pack')
    if missing:
        return dict(status='unavailable', components={}, issues=[dict(component=name, code=name + '_missing', reason='Required input group missing') for name in missing], source_hashes={'request': digest(request)}, coupling_audit_status='unavailable')
    result = compute_carbon_sufficiency(request['p3_interval'], request['carbon_state'], request['light_series'], request['environment'], parameter_pack)
    row = result['diagnostic']
    return dict(status='available' if row['status'] != 'unavailable' else 'unavailable', components=row['component_status'], issues=row['limiting_inputs'], source_hashes=row['source_hashes'], coupling_audit_status=row['coupling_audit_status'])


def _csv(path: Path, records: list[dict], columns: list[str]) -> None:
    with path.open('w', encoding='utf-8', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=columns); writer.writeheader()
        for row in records:
            writer.writerow({key: '' if row.get(key) is None else json.dumps(row[key], sort_keys=True) if isinstance(row[key], (dict, list)) else row[key] for key in columns})


def _validate_result_semantics(result: dict) -> None:
    _json_finite(result)
    inputs = result['inputs']
    order = ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack')
    actual_hash = digest([inputs[key] for key in order])
    if result['input_hash_before'] != actual_hash or result['input_hash_after'] != actual_hash:
        raise StudyError('Export source objects do not match immutability hashes')
    row, components = result['diagnostic'], result['components']
    for key, value in _area_disclosures(components['supply'], inputs['light_series']).items():
        if row.get(key) != value:
            raise StudyError('Export area disclosure mismatch: ' + key)
    if components['supply']['status'] == 'available':
        support = _physical_light_support(inputs['light_series'], _pack(inputs['parameter_pack']))
        context = inputs['light_series']['context']
        for flux in components['supply']['rows']:
            if flux.get('area_support') != support['patches'].get(flux['patch_id']) or flux.get('canopy_provenance') != support['canopy_provenance']:
                raise StudyError('Export physical support provenance mismatch')
            if any(flux.get(k) != context[k] for k in ('plant_instance_id', 'area_basis_id', 'geometry_hash')):
                raise StudyError('Export supply tissue identity mismatch')
    for key, value in _disclosures(inputs['carbon_state'], inputs['parameter_pack']).items():
        if row.get(key) != value:
            raise StudyError('Export disclosure/provenance mismatch: ' + key)
    if row.get('issue_codes') != '|'.join(sorted({issue['code'] for issue in row['limiting_inputs']})):
        raise StudyError('Export issue codes mismatch')
    if row.get('calibration_basis_issues_json') != json.dumps([issue for issue in components['supply']['issues'] if issue['code'] == 'alpha_calibration_basis_conflict'], sort_keys=True):
        raise StudyError('Export coefficient-basis issues mismatch')
    try:
        pack = _pack(inputs['parameter_pack']) if inputs['parameter_pack'] else None
    except MissingEvidence:
        pack = None
    if row.get('pack_id') != (pack['pack_id'] if pack else None):
        raise StudyError('Export pack association mismatch')
    if row.get('reserve_propagation') != 'none' or row.get('interval_independence') != 'independent_single_interval':
        raise StudyError('Diagnostics cannot propagate reserve stocks')
    assumption = inputs['carbon_state'].get('reserve_reuse_assumption')
    if assumption is not None:
        _text(assumption, 'reserve_reuse_assumption')
    if row.get('reserve_reuse_assumption') != assumption:
        raise StudyError('Reserve reuse assumption was changed')
    if row.get('maintenance_activity_zero') != any(r.get('maintenance_activity_zero', False) for r in components['maintenance']['rows']):
        raise StudyError('Maintenance zero-activity flag mismatch')

    if row['source_hashes'] != {key: digest(inputs[key]) for key in order}:
        raise StudyError('Export provenance mismatch')
    if any(row[key] != inputs['p3_interval'][key] for key in IDENTITY):
        raise StudyError('Export identity/weight/interval changed')
    for reason in row['limiting_inputs']:
        if any(reason[key] != row[key] for key in ('plant_instance_id', 'trajectory_id', 't_start', 't_end')):
            raise StudyError('Reason identity/interval differs from diagnostic')
    for name in ('supply', 'maintenance', 'demand'):
        comp = components[name]
        if comp['status'] == 'available' and not math.isclose(math.fsum(r['value_gC'] for r in comp['rows']), comp['value_gC'], rel_tol=0, abs_tol=0):
            raise StudyError('Export component sum mismatch')
    complete = all(components[name]['status'] == 'available' for name in ('supply', 'maintenance', 'demand', 'budget'))
    if complete:
        u = components['budget']['unprotected_budget_gC']
        v, d = components['budget']['value_gC'], components['demand']['value_gC']
        if row['available_growth_carbon_gC'] != v or row['required_growth_carbon_gC'] != d:
            raise StudyError('Diagnostic carbon quantities differ from components')
        if u < 0:
            expected = 'maintenance_deficit'
        elif d == 0:
            expected = 'no_growth_demand'
        else:
            numerics = _pack(inputs['parameter_pack'])['numerics']
            tol = numerics['carbon_abs_tol_gC'] + numerics['carbon_rel_tol'] * max(abs(v), abs(d))
            expected = 'sufficient' if v + tol >= d else 'growth_deficit'
            if row['sufficiency_ratio'] != v / d or row['growth_deficit_gC'] != max(d-v, 0):
                raise StudyError('Export ratio/deficit arithmetic mismatch')
        if row['status'] != expected:
            raise StudyError('Export status is inconsistent with accounting')
    elif row['status'] != 'unavailable':
        raise StudyError('Incomplete components cannot produce a sufficient/deficit result')


def _verify_originating_diagnostic(result: dict) -> None:
    """Recompute retained inputs; a caller-supplied ID alone cannot prove association."""
    _validate_result_semantics(result)
    order = ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack')
    actual = compute_carbon_sufficiency(*(result['inputs'][key] for key in order))
    if any(digest(result[key]) != digest(value) for key, value in actual.items()):
        raise StudyError('Originating diagnostic does not match recomputed C04 inputs')


@_strict_api
def validate_diagnostic_table(results: list[dict]) -> dict:
    """Compare supplied intervals only; no hidden history or reserve propagation."""
    if not isinstance(results, list) or not results:
        raise StudyError('A nonempty list of diagnostic results is required')
    groups: dict[str, list] = {}
    for index, result in enumerate(results):
        _verify_originating_diagnostic(result)
        row, inputs = result['diagnostic'], result['inputs']
        state = inputs['carbon_state']
        key = digest(dict(identity={k: row[k] for k in ('plant_instance_id', 'trajectory_id', 'p4_parameter_draw_id', 'pack_id')},
                          scope=state['scope'],
                          included=sorted(state['included_organ_ids']) if state['scope'] != 'whole_plant' else None,
                          excluded=sorted(state.get('excluded_organ_ids', [])) if state['scope'] != 'whole_plant' else None,
                          boundary_policy=state.get('boundary_policy')))
        groups.setdefault(key, []).append((index, result))
    comparisons = []
    for group in groups.values():
        ending: dict[datetime, list] = {}
        for index, result in group:
            ending.setdefault(_time(result['diagnostic']['t_end']), []).append((index, result))
        for index, result in group:
            row = result['diagnostic']; state = result['inputs']['carbon_state']
            for previous_index, previous in ending.get(_time(row['t_start']), []):
                reserve = state.get('reserve_gC')
                reused = reserve is not None and reserve == previous['inputs']['carbon_state'].get('reserve_gC')
                assumption = row['reserve_reuse_assumption']
                if reused and not assumption:
                    raise StudyError(f'Contiguous rows {previous_index}/{index} reuse identical reserves without reserve_reuse_assumption')
                comparisons.append(dict(previous_row=previous_index, current_row=index, identical_reserve=reused,
                                        same_reserve_lineage=row['reserve_provenance_chain_id'] != 'unavailable' and row['reserve_provenance_chain_id'] == previous['diagnostic']['reserve_provenance_chain_id'],
                                        previous_reserve_provenance_chain_id=previous['diagnostic']['reserve_provenance_chain_id'],
                                        current_reserve_provenance_chain_id=row['reserve_provenance_chain_id'],
                                        reserve_reuse_assumption=assumption))
    return dict(status='valid', row_count=len(results), contiguous_comparisons=comparisons,
                validation_scope='supplied_rows_only', reserve_propagation='none',
                interval_independence='independent_single_interval')


@_strict_api
def export_diagnostic_table(results: list[dict], output_path: str | Path) -> dict:
    """Validate intervals before exporting a combined table and source snapshots."""
    validation = validate_diagnostic_table(results)
    folder = output_dir(Path(output_path))
    for index, result in enumerate(results):
        export_diagnostic(result, folder / f'row_{index:04d}')
    rows = []
    for index, result in enumerate(results):
        row = {k: v for k, v in result['diagnostic'].items() if not isinstance(v, (dict, list))}
        row['metadata_ref'] = f'row_{index:04d}/availability.json'
        rows.append(row)
    _csv(folder / 'diagnostics.csv', rows, list(rows[0]))
    write_json(folder / 'validation.json', validation)
    write_json(folder / 'manifest.json', dict(schema_version=SCHEMA, validation=validation,
        artifact_hashes={p.relative_to(folder).as_posix(): file_hash(p) for p in folder.rglob('*') if p.is_file()}))
    return validation


@_strict_api
def export_diagnostic(result: dict, output_path: str | Path) -> dict:
    """Export immutable source objects and normalized CSV/JSON metadata to fresh build/."""
    from jsonschema import Draft202012Validator, FormatChecker
    schema_path = Path(__file__).with_name('fsp_carbon_diagnostic_schema.json')
    schema = json.loads(schema_path.read_text(encoding='utf-8'))
    errors = list(Draft202012Validator(schema['$defs']['result'], format_checker=FormatChecker()).iter_errors(result['diagnostic']))
    if errors:
        raise StudyError('Output schema: ' + errors[0].message)
    _validate_result_semantics(result)
    folder = output_dir(Path(output_path))
    write_json(folder / 'inputs.json', result['inputs'])
    write_json(folder / 'result.json', result)
    row = result['diagnostic']
    scalar = {key: value for key, value in row.items() if not isinstance(value, (list, dict))}
    scalar['metadata_ref'] = 'availability.json'
    _csv(folder / 'diagnostics.csv', [scalar], list(scalar))
    fluxes = [dict({'plant_instance_id': row['plant_instance_id'], 'trajectory_id': row['trajectory_id'], 'p4_parameter_draw_id': row['p4_parameter_draw_id']}, **record) for comp in result['components'].values() for record in comp['rows']]
    columns = list(dict.fromkeys(['plant_instance_id', 'trajectory_id', 'p4_parameter_draw_id', 'component', 'organ_id', 't_start', 't_end', 'value_gC'] + [key for record in fluxes for key in record]))
    _csv(folder / 'component_fluxes.csv', fluxes, columns)
    write_json(folder / 'availability.json', row)
    write_json(folder / 'coupling_audit.json', result['coupling_audit'])
    manifest = dict(schema_version=SCHEMA, code_hashes={Path(__file__).name: file_hash(Path(__file__)), schema_path.name: file_hash(schema_path), 'leaf_light/common.py': file_hash(Path(__file__).parent/'leaf_light/common.py')},
                    input_hash_before=result['input_hash_before'], input_hash_after=result['input_hash_after'],
                    source_hashes=row['source_hashes'], feedback_action='none', accepted_for_domain=False,
                    artifact_hashes={p.name: file_hash(p) for p in folder.iterdir() if p.is_file()}, command=sys.argv)
    manifest['file_source_hashes'] = result.get('file_source_hashes', {})
    manifest['runtime'] = dict(python=sys.version, jsonschema=version('jsonschema'))
    write_json(folder / 'manifest.json', manifest)
    return manifest


def _load_request(path: Path) -> tuple[dict, dict]:
    """Materialize explicitly hashed local CSV/JSON references at the CLI boundary."""
    raw_request = path.read_bytes()
    request = json.loads(raw_request.decode('utf-8-sig'))
    sources = {str(path.resolve()): hashlib.sha256(raw_request).hexdigest()}

    def referenced(ref: dict) -> tuple[Path, bytes]:
        if set(ref) != {'path', 'sha256'}:
            raise StudyError('File reference requires only path and SHA256')
        target = (path.parent / ref['path']).resolve()
        raw = target.read_bytes() if target.is_file() else None
        if raw is None or hashlib.sha256(raw).hexdigest() != _sha(ref['sha256'], 'file reference'):
            raise StudyError('Missing or changed input file: ' + str(target))
        sources[str(target)] = ref['sha256']
        return target, raw

    for name in ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack'):
        value = request.get(name)
        if isinstance(value, dict) and set(value) == {'path', 'sha256'}:
            _, raw = referenced(value)
            request[name] = json.loads(raw.decode('utf-8-sig'))
    numeric = {'area_weight_m2', 'ppfd_umol_m2_s', 'leaf_temperature_c', 'air_temperature_c',
               'root_temperature_c', 'organ_temperature_c', 'co2_ppm', 'pressure_pa', 'relative_humidity_pct',
               'vpd_kpa', 'ec_ms_cm', 'ph', 'structural_dm_g', 'structural_dm_start_g',
               'structural_dm_end_g', 'supported_area_m2'}
    booleans = {'one_sided_area_basis', 'birth_mass_accounted'}
    for group, column, ref_key in [('light_series', 'samples', 'samples_csv'), ('environment', 'records', 'records_csv'),
                                   ('carbon_state', 'organ_masses', 'organ_masses_csv'), ('carbon_state', 'mass_increments', 'mass_increments_csv')]:
        obj = request.get(group) or {}
        if ref_key not in obj:
            continue
        if column in obj:
            raise StudyError('Supply inline records or CSV reference, not both')
        _, raw = referenced(obj[ref_key])
        with io.StringIO(raw.decode('utf-8-sig'), newline='') as stream:
            reader = csv.DictReader(stream)
            if not reader.fieldnames or len(set(reader.fieldnames)) != len(reader.fieldnames):
                raise StudyError('CSV requires unique named columns')
            records = list(reader)
        for row in records:
            if None in row or any(value is None for value in row.values()):
                raise StudyError('Malformed CSV row')
            for key, value in row.items():
                if value == '': row[key] = None
                elif key in numeric: row[key] = _finite(float(value), key)
                elif key in booleans:
                    if value.lower() not in {'true', 'false'}:
                        raise StudyError('Boolean CSV cells must be true/false')
                    row[key] = value.lower() == 'true'
        obj[column] = records
    return request, sources


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='operation', required=True)
    for operation in ('templates', 'audit', 'diagnose', 'validate-table'):
        cmd = sub.add_parser(operation); cmd.add_argument('--out', type=Path, required=True)
        if operation != 'templates':
            cmd.add_argument('--input', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.operation == 'templates':
            folder = output_dir(args.out)
            write_json(folder / 'request.json', dict(schema_version=SCHEMA, p3_interval=None, carbon_state=None, light_series=None, environment=None, parameter_pack=None))
            write_json(folder / 'parameter_pack.json', dict(payload=dict(schema_version=SCHEMA, pack_id=None, review_status=None, source_family=None, model_id='nrh', parameters={}, organ_parameter_map={}, mass_form_mapping={}, respiration_ownership=[], applicable_domain={}, numerics={}, assumptions=[]), sha256=None))
            print(json.dumps(dict(status='blank_templates', out=str(folder))))
            return 0
        if args.operation == 'validate-table':
            table = json.loads(args.input.read_text(encoding='utf-8-sig'))
            if table.get('schema_version') != SCHEMA:
                raise StudyError('Unsupported table schema')
            results = []
            for ref in table['results']:
                if set(ref) != {'path', 'sha256'}:
                    raise StudyError('Table result reference requires path and SHA256')
                raw = (args.input.parent / ref['path']).read_bytes()
                if hashlib.sha256(raw).hexdigest() != _sha(ref['sha256'], 'table result'):
                    raise StudyError('Table result hash mismatch')
                results.append(json.loads(raw.decode('utf-8-sig')))
            validation = export_diagnostic_table(results, args.out)
            print(json.dumps(validation))
            return 0
        request, file_sources = _load_request(args.input)
        if request.get('schema_version') != SCHEMA:
            raise StudyError('Unsupported request schema')
        from jsonschema import Draft202012Validator
        input_schema = json.loads(Path(__file__).with_name('fsp_carbon_diagnostic_schema.json').read_text(encoding='utf-8'))
        errors = list(Draft202012Validator(input_schema).iter_errors(request))
        if errors:
            raise StudyError('Request schema: ' + errors[0].message)
        if args.operation == 'audit':
            result = audit_diagnostic_inputs(request, request.get('parameter_pack'))
            result['file_source_hashes'] = file_sources
            folder = output_dir(args.out); write_json(folder / 'audit.json', result)
        else:
            result = compute_carbon_sufficiency(*(request.get(key) for key in ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack')))
            result['file_source_hashes'] = file_sources
            export_diagnostic(result, args.out)
        print(json.dumps(dict(status=result.get('status', result.get('diagnostic', {}).get('status')), out=str(args.out))))
        return 0
    except (StudyError, MissingEvidence, KeyError, TypeError, ValueError, OverflowError) as exc:
        parser.exit(2, 'Diagnostic input error: ' + str(exc) + '\n')


if __name__ == '__main__':
    raise SystemExit(main())
