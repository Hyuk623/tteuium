"""Read-only boundary validation. No native transport, carbon calculation or state advance."""
from __future__ import annotations

import argparse
import math
from pathlib import Path

from tools.empirical_growth_boundary import (SCHEMA, FACE, RULE, absorption, code_hashes, geometry,
                                            require, schedule, source, timestamp)
from tools.empirical_light_field import finite, load_field, verify_hashes
from tools.leaf_light.common import StudyError, digest, file_hash, read_json, rows

ABS_TOL = 1e-10
REL_TOL = 1e-10


def same(actual: object, expected: object, reason: str) -> None:
    if expected is None:
        require(actual is None, reason)
    elif isinstance(expected, (int, float)) and not isinstance(expected, bool):
        require(math.isclose(finite(actual), expected, abs_tol=ABS_TOL, rel_tol=REL_TOL), reason)
    else:
        require(actual == expected, reason)


def check_csv(path: Path, expected: list[dict]) -> None:
    data = rows(path)
    require(len(data) == len(expected), 'csv_row_count_mismatch')
    for a, b in zip(data, expected):
        require(set(a) == set(b), 'csv_columns_mismatch')
        for key, value in b.items():
            require(a[key] == ('unavailable' if value is None else str(value)), 'csv_value_mismatch:'+key)


def validate(path: Path, current_configuration: Path, expected_context: dict,
             required_basis: str | None = None) -> dict:
    """Expected context must come from the consuming state, not be copied from the export."""
    m = read_json(path)
    for key, value in dict(schema_version=SCHEMA, method='empirical_light_field', source_kind='derived',
            status='conditional_export_only', native_consumption='unverified_hook_required',
            physical_accuracy='unvalidated', coordinate_frame='grow_mm', face_convention=FACE).items():
        same(m.get(key), value, 'boundary_contract_mismatch:'+key)
    require(required_basis in (None, 'incident', 'absorbed'), 'unsupported_P4_light_basis')
    require(expected_context.get('schema_version') == 'empirical-native-context-1' and
            expected_context.get('run_id') == m['run_id'], 'consumer_run_namespace_mismatch')
    verify_hashes(m['source_hashes']); verify_hashes(m['code_hashes'])
    require(set(m['code_hashes']) == set(code_hashes()), 'incomplete_code_coverage')
    require(m['request_path'] in m['source_hashes'], 'request_not_hash_bound')
    req = read_json(Path(m['request_path'])); hashes = {}
    field_path = source(req['field_ref'], hashes)
    source(req['configuration_ref'], hashes)
    field = load_field(field_path, current_configuration)
    require(m['configuration_sha256'] == field['configuration_sha256'], 'field_configuration_mismatch')
    require(expected_context.get('configuration_sha256') == m['configuration_sha256'], 'consumer_configuration_mismatch')
    contract = m['transport_contract']
    require(contract == req['transport_contract'] and contract.get('interpretation') == RULE and
            contract.get('field_light_basis') == 'incident' and contract.get('already_canopy_shaded') is False and
            contract.get('canopy_shading_passes') == 1 and contract.get('local_field_approximation_acknowledged') is True,
            'second_shading_or_basis_mismatch')
    require(contract.get('canopy_scattering') == 'not_modelled_transmission_only','canopy_scattering_contract_mismatch')
    require(m['diffuse_fractions'] == req['diffuse_fractions'], 'direction_scenario_mismatch')
    artifacts = {'leaf_segments.csv', 'leaf_intervals.csv', 'transport_evidence.json'}
    require(set(m['artifact_hashes']) == artifacts, 'boundary_artifacts_missing')
    for name in artifacts:
        require(file_hash(path.parent/name) == m['artifact_hashes'][name], 'artifact_hash_mismatch')
    check_csv(path.parent/'leaf_segments.csv', m['rows'])
    check_csv(path.parent/'leaf_intervals.csv', m['interval_totals'])
    raw_audit = read_json(path.parent/'transport_evidence.json')
    evidence = {r['evidence_id']: r for r in raw_audit}
    require(len(evidence) == len(raw_audit), 'duplicate_transport_evidence')
    keys = [(r['interval_id'],r['segment_index'],r['surface_id'],r['diffuse_fraction']) for r in m['rows']]
    require(len(set(keys)) == len(keys), 'duplicate_leaf_segment')
    totals_keys = [(r['interval_id'],r['surface_id'],r['diffuse_fraction']) for r in m['interval_totals']]
    require(len(set(totals_keys)) == len(totals_keys), 'duplicate_leaf_interval')
    require(set(totals_keys) == {(a,c,d) for a,b,c,d in keys}, 'interval_total_inventory_mismatch')
    expected_keys = set(); expected_evidence = set(); missing_absorbed = 0; previous_end = None
    require(len(m['intervals']) == len(req['intervals']) == len(expected_context.get('intervals', [])), 'interval_coverage_mismatch')
    for interval, binding, target in zip(req['intervals'], m['intervals'], expected_context['intervals']):
        require(previous_end is None or previous_end == timestamp(interval['start_at']), 'interval_time_gap')
        previous_end = timestamp(interval['end_at'])
        snapshot_path = source(interval['snapshot_ref'], hashes)
        registration_path = source(interval['registration_ref'], hashes)
        snapshot = read_json(snapshot_path); registration = read_json(registration_path)
        mesh, identities = geometry(snapshot, registration, field)
        segments = schedule(interval, req['fixture_ids'])
        expected_binding = dict(interval_id=interval['interval_id'], start_at=interval['start_at'], end_at=interval['end_at'],
            geometry_hash=snapshot['geometry_hash'], geometry_hash_scheme='fsp_canopy_surface_triangles_m_v1',
            snapshot_sha256=file_hash(snapshot_path), registration_sha256=file_hash(registration_path),
            placement_hash=snapshot['placement_hash'], configuration_sha256=field['configuration_sha256'],
            namespace_hash=digest(snapshot['identity_map']), orientation_variant=field['configuration']['empirical_contract']['coordinate_variant'])
        require(binding == expected_binding, 'export_geometry_or_interval_binding_mismatch')
        for k in ('interval_id','start_at','end_at','geometry_hash','namespace_hash','registration_sha256'):
            require(target.get(k) == binding[k], 'native_consumer_context_mismatch:'+k)
        for ident in identities:
            sid = ident['surface_id']; area = ident['one_sided_area_m2']
            for fraction in req['diffuse_fractions']:
                eid = f"{interval['interval_id']}:{sid}:{fraction}"; expected_evidence.add(eid)
                require(eid in evidence, 'transport_evidence_missing')
                samples = evidence[eid]['samples']
                declared = [r for r in mesh['receivers'] if r['leaf_id'] == sid]
                require(len(samples) == len(declared), 'partial_surface_coverage')
                for sample, receiver in zip(samples, declared):
                    require(sample['receiver_id'] == receiver['receiver_id'] and sample['leaf_id'] == sid and sample['diffuse_fraction'] == fraction,
                            'transport_namespace_or_scenario_mismatch')
                    same(sample['supported_one_sided_area_m2'], receiver['supported_one_sided_area_m2'], 'sample_area_mismatch')
                    require(sample['source_kind'] == 'derived' and sample['direction_source_kind'] == 'user_assumed', 'transport_provenance_mismatch')
                    for k in ('upper_ppfd_umol_m2_s','lower_ppfd_umol_m2_s'):
                        require(sample[k] is None or finite(sample[k]) >= 0, 'invalid_face_flux')
                valid = all(s['upper_ppfd_umol_m2_s'] is not None and s['lower_ppfd_umol_m2_s'] is not None for s in samples)
                upper = math.fsum(s['supported_one_sided_area_m2']*s['upper_ppfd_umol_m2_s'] for s in samples) if valid else None
                lower = math.fsum(s['supported_one_sided_area_m2']*s['lower_ppfd_umol_m2_s'] for s in samples) if valid else None
                same(math.fsum(s['supported_one_sided_area_m2'] for s in samples), area, 'surface_area_incomplete')
                optics = interval['absorptance_by_surface'][sid]
                require(evidence[eid]['absorption'] == optics, 'absorption_provenance_mismatch')
                alpha, beta = absorption(optics)
                for segment in segments:
                    key = (interval['interval_id'],segment['segment_index'],sid,fraction); expected_keys.add(key)
                    require(key in keys, 'leaf_segment_missing')
                    row = m['rows'][keys.index(key)]
                    for k,v in (binding | ident | segment).items(): same(row.get(k),v,'leaf_binding_mismatch:'+k)
                    require(row['shading_passes'] == 1 and row['source_kind'] == 'derived' and row['direction_source_kind'] == 'user_assumed' and row['face_convention'] == FACE,
                            'double_shading_or_source_basis_mismatch')
                    f = segment['output_fraction']; duration = segment['duration_s']
                    a = upper*f if valid else (0. if f == 0 else None)
                    b = lower*f if valid else (0. if f == 0 else None)
                    q = a+b if a is not None else None
                    absorbed = a*alpha+b*beta if q is not None and alpha is not None else None
                    for k,v in dict(incident_normal_umol_s=a, incident_opposite_umol_s=b,
                        incident_umol_s=q, absorbed_umol_s=absorbed,
                        light_basis='incident_only' if alpha is None else 'incident_with_separate_absorbed',
                        status='conditional' if q is not None else 'unavailable',
                        absorbed_status='conditional' if absorbed is not None else 'unavailable').items(): same(row[k],v,'light_basis_or_flux_mismatch:'+k)
                    for basis, flux in (('incident',q),('absorbed',absorbed)):
                        for suffix,v in (('_ppfd_umol_m2_s',flux/area if flux is not None else None),
                            ('_dose_umol',flux*duration if flux is not None else None),
                            ('_dose_mol_m2',flux*duration/(1e6*area) if flux is not None else None)):
                            same(row[basis+suffix],v,'independent_area_or_schedule_integral_mismatch')
                    if absorbed is None: missing_absorbed += 1
                    if required_basis is not None:
                        require((absorbed if required_basis == 'absorbed' else q) is not None, 'P4_'+required_basis+'_input_unavailable')
    require(set(keys) == expected_keys and set(evidence) == expected_evidence, 'unexpected_export_rows_or_evidence')
    for total, key in zip(m['interval_totals'], totals_keys):
        group = [r for r in m['rows'] if (r['interval_id'],r['surface_id'],r['diffuse_fraction']) == key]
        first = group[0]
        same(total['start_at'],first['start_at'],'total_start_mismatch')
        same(total['end_at'],group[-1]['end_at'],'total_end_mismatch')
        for k in ('plant_instance_id','organ_id','geometry_hash','namespace_hash','registration_sha256','one_sided_area_m2'):
            same(total[k],first[k],'total_binding_mismatch')
        same(total['duration_s'],math.fsum(r['duration_s'] for r in group),'interval_duration_mismatch')
        same(total['on_duration_s'],math.fsum(r['duration_s']*r['output_fraction'] for r in group),'on_duration_mismatch')
        for k in ('incident_dose_umol','absorbed_dose_umol','incident_dose_mol_m2','absorbed_dose_mol_m2'):
            value=math.fsum(r[k] for r in group) if all(r[k] is not None for r in group) else None
            same(total[k],value,'interval_integral_mismatch')
    for p,h in hashes.items(): require(m['source_hashes'].get(p) == h,'source_reference_coverage_mismatch')
    return dict(valid=True, rows=len(keys), intervals=len(m['intervals']), missing_absorbed_rows=missing_absorbed,
        required_basis=required_basis, native_consumption='unverified_hook_required',
        absolute_tolerance=ABS_TOL,relative_tolerance=REL_TOL,
        arithmetic='independent_sample_area_aggregation_and_schedule_integration')


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    p.add_argument('boundary',type=Path)
    p.add_argument('--configuration',type=Path,required=True)
    p.add_argument('--context',type=Path,required=True)
    p.add_argument('--required-basis',choices=('incident','absorbed'))
    a=p.parse_args(argv)
    try:
        print(validate(a.boundary,a.configuration,read_json(a.context),a.required_basis)); return 0
    except (StudyError,ValueError,KeyError,OSError) as exc:
        p.exit(2,str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
