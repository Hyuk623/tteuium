"""Versioned empirical per-position dose; deliberately not a whole-plant P3 input."""
from __future__ import annotations

import math
from pathlib import Path

from tools.empirical_light_field import (code_hashes, evaluate, finite, grids, load_field, verify_hashes)
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, rows, write_json, write_rows

SCHEMA = 'reference-dli-empirical-result-1'
COLUMNS = ('position_id', 'x_mm', 'y_mm', 'z_mm', 'ppfd_umol_m2_s', 'dli_mol_m2_day',
           'status', 'reason', 'method', 'source_kind')
ABS_TOL = 1e-12
REL_TOL = 1e-12


def operation_hours(operation: dict) -> float:
    hours = finite(operation.get('daily_on_hours'))
    if not 0 < hours <= 24:
        raise StudyError('invalid_daily_on_hours')
    if (operation.get('output_fraction') != 1 or operation.get('measurement_output_fraction') != 1 or
            operation.get('constant_during_on') is not True or operation.get('source_kind') != 'user_stated' or
            not operation.get('source_ref')):
        raise StudyError('only_declared_constant_observed_full_output_supported')
    return hours


def positions(path: Path) -> list[dict]:
    result = rows(path, ('position_id', 'x_mm', 'y_mm', 'z_mm'))
    if not result or len({r['position_id'] for r in result}) != len(result) or any(not r['position_id'] for r in result):
        raise StudyError('invalid_position_ids')
    return result


def run(field_path: Path, configuration_path: Path, positions_path: Path, operation_path: Path, out: Path) -> dict:
    field = load_field(field_path, configuration_path)
    operation = read_json(operation_path); hours = operation_hours(operation)
    results = []; audits = []
    for row in positions(positions_path):
        xyz = [finite(row[key]) for key in ('x_mm', 'y_mm', 'z_mm')]
        try:
            value = evaluate(field, xyz)
            q = value['ppfd_umol_m2_s']; reason = None
            audits.append(dict(position_id=row['position_id'], weights=value['interpolation_weights']))
        except StudyError as exc:
            if str(exc) not in ('outside_tray_block', 'outside_sample_centre_support'):
                raise
            q = None; reason = str(exc)
            audits.append(dict(position_id=row['position_id'], weights=None))
        results.append(dict(position_id=row['position_id'], x_mm=xyz[0], y_mm=xyz[1], z_mm=xyz[2],
            ppfd_umol_m2_s=q, dli_mol_m2_day=q*hours*3600/1e6 if q is not None else None,
            status='conditional' if q is not None else 'unavailable', reason=reason,
            method='empirical_light_field', source_kind='derived'))
    folder = output_dir(out)
    write_rows(folder/'reference_dli.csv', results, COLUMNS)
    write_json(folder/'integration_evidence.json', audits)
    record = dict(schema_version=SCHEMA, method='empirical_light_field', source_kind='derived',
        quantity='incident', unit='mol/m2/day', time_basis='declared_daily_on_duration',
        model_scope='per_position_horizontal_reference', status='conditional', value=None,
        coordinate_frame='grow', height_basis='shelf_floor', sensor_normal=[0, 0, 1],
        configuration_sha256=field['configuration_sha256'], operation=operation, positions=results,
        source_hashes={str(p.resolve()): file_hash(p) for p in (field_path, configuration_path, positions_path, operation_path)},
        code_hashes=code_hashes(), inputs=dict(field=str(field_path.resolve()), configuration=str(configuration_path.resolve()),
            positions=str(positions_path.resolve()), operation=str(operation_path.resolve())),
        artifact_hashes={name: file_hash(folder/name) for name in ('reference_dli.csv', 'integration_evidence.json')},
        disclosures=['conditional_constant_output_on_period_dose_not_a_logged_24h_integral',
            'off_period_ambient_unmeasured', 'clock_times_unconfirmed', 'not_a_whole_plant_growth_input',
            'sensor_calibration_unknown', 'spatial_interpolation_accuracy_unvalidated'])
    write_json(folder/'reference_dli.json', record)
    return record


def independent_ppfd(field: dict, xyz: list[float]) -> float | None:
    """Consumer's direct tensor-product evaluation; never calls producer evaluate/bracket."""
    x, y, z = xyz
    a, b, c, d = field['configuration']['empirical_contract']['tray_bounds_xy_mm']
    if not (a <= x <= b and c <= y <= d and 70 <= z <= 150):
        return None
    total = 0.
    for height, (xs, ys, cells) in grids(field['samples']).items():
        vertical = (150-z)/80 if height == 70 else (z-70)/80
        if vertical == 0:
            continue
        if not xs[0] <= x <= xs[-1] or not ys[0] <= y <= ys[-1]:
            return None
        i = next(i for i in range(len(xs)-1) if xs[i] <= x <= xs[i+1])
        j = next(j for j in range(len(ys)-1) if ys[j] <= y <= ys[j+1])
        u = (x-xs[i])/(xs[i+1]-xs[i]); v = (y-ys[j])/(ys[j+1]-ys[j])
        total += vertical*((1-u)*(1-v)*cells[xs[i], ys[j]]['ppfd_umol_m2_s']+
            u*(1-v)*cells[xs[i+1], ys[j]]['ppfd_umol_m2_s']+
            (1-u)*v*cells[xs[i], ys[j+1]]['ppfd_umol_m2_s']+
            u*v*cells[xs[i+1], ys[j+1]]['ppfd_umol_m2_s'])
    return total


def validate_result(path: Path, current_configuration: Path | None) -> dict:
    if current_configuration is None:
        raise StudyError('empirical_consumer_requires_current_configuration')
    record = read_json(path)
    for key, expected in dict(schema_version=SCHEMA, method='empirical_light_field', source_kind='derived',
        quantity='incident', unit='mol/m2/day', time_basis='declared_daily_on_duration',
        model_scope='per_position_horizontal_reference', status='conditional', value=None,
        coordinate_frame='grow', height_basis='shelf_floor', sensor_normal=[0, 0, 1]).items():
        if record.get(key) != expected:
            raise StudyError('empirical_result_contract_mismatch:'+key)
    verify_hashes(record['source_hashes']); verify_hashes(record['code_hashes'])
    inputs = record['inputs']
    if set(inputs) != {'field', 'configuration', 'positions', 'operation'} or any(p not in record['source_hashes'] for p in inputs.values()):
        raise StudyError('empirical_result_inputs_unbound')
    field = load_field(Path(inputs['field']), current_configuration)
    if record['configuration_sha256'] != field['configuration_sha256']:
        raise StudyError('empirical_configuration_mismatch')
    operation = read_json(Path(inputs['operation'])); hours = operation_hours(operation)
    if record['operation'] != operation:
        raise StudyError('operation_mismatch')
    names = {'reference_dli.csv', 'integration_evidence.json'}
    if set(record['artifact_hashes']) != names:
        raise StudyError('empirical_artifacts_missing')
    for name in names:
        if file_hash(path.parent/name) != record['artifact_hashes'][name]:
            raise StudyError('empirical_artifact_hash_mismatch')
    source_positions = positions(Path(inputs['positions']))
    csv_values = rows(path.parent/'reference_dli.csv', COLUMNS)
    audits = read_json(path.parent/'integration_evidence.json')
    if len(record['positions']) != len(source_positions) or len(csv_values) != len(source_positions) or len(audits) != len(source_positions):
        raise StudyError('empirical_position_count_mismatch')
    samples = {r['sample_id']: r for r in field['samples']}
    for source, row, csv_row, audit in zip(source_positions, record['positions'], csv_values, audits):
        for key in COLUMNS:
            expected_text = 'unavailable' if row[key] is None else str(row[key])
            if csv_row[key] != expected_text:
                raise StudyError('empirical_csv_mismatch')
        if row['position_id'] != source['position_id'] or audit['position_id'] != source['position_id']:
            raise StudyError('empirical_position_id_mismatch')
        xyz = [finite(source[key]) for key in ('x_mm', 'y_mm', 'z_mm')]
        if xyz != [row[key] for key in ('x_mm', 'y_mm', 'z_mm')]:
            raise StudyError('empirical_position_mismatch')
        expected_q = independent_ppfd(field, xyz)
        if row['source_kind'] != 'derived' or row['method'] != 'empirical_light_field':
            raise StudyError('empirical_provenance_mismatch')
        if expected_q is None:
            if row['status'] != 'unavailable' or row['ppfd_umol_m2_s'] is not None or row['dli_mol_m2_day'] is not None or audit['weights'] is not None:
                raise StudyError('empirical_extrapolation_claim')
        else:
            if row['status'] != 'conditional' or row['reason'] is not None:
                raise StudyError('empirical_status_mismatch')
            for key, expected in (('ppfd_umol_m2_s', expected_q), ('dli_mol_m2_day', expected_q*hours*.0036)):
                if not math.isclose(finite(row[key]), expected, abs_tol=ABS_TOL, rel_tol=REL_TOL):
                    raise StudyError('independent_empirical_arithmetic_mismatch')
            weights = audit['weights']
            if not weights or len({w['sample_id'] for w in weights}) != len(weights):
                raise StudyError('invalid_interpolation_evidence')
            for w in weights:
                if w['sample_id'] not in samples or not 0 <= finite(w['weight']) <= 1 or w['ppfd_umol_m2_s'] != samples[w['sample_id']]['ppfd_umol_m2_s']:
                    raise StudyError('invalid_interpolation_evidence')
            # Check partition of unity, point reconstruction, and dose independently.
            for actual, expected in [(sum(w['weight'] for w in weights), 1.),
                (sum(w['weight']*w['ppfd_umol_m2_s'] for w in weights), expected_q)]+[
                (sum(w['weight']*samples[w['sample_id']][key] for w in weights), value)
                for key, value in zip(('x_mm', 'y_mm', 'z_mm'), xyz)]:
                if not math.isclose(actual, expected, abs_tol=ABS_TOL, rel_tol=REL_TOL):
                    raise StudyError('interpolation_evidence_mismatch')
    return dict(valid=True, status='conditional', value=None, positions=len(source_positions),
        arithmetic='independent_tensor_product_and_duration_integration', absolute_tolerance=ABS_TOL,
        relative_tolerance=REL_TOL, physical_accuracy='unvalidated')
