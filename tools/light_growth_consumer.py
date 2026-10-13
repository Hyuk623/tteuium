"""Independent read-only CSV consumer and consistency checker for light-growth-1.

This module intentionally does not import the exporter or its aggregation code.
"""
from __future__ import annotations

from collections import defaultdict
import csv
from datetime import datetime, timedelta, timezone
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np
from tomato3d.io.schemas import ScheduleSegment
from tools.compound_growth import MATH_TOL as OBSERVED_AXIS_NUMERIC_TOL

from tools.leaf_light.common import DLI_UNIT, StudyError, digest, file_hash, read_json

_SECOND = ('xx', 'xy', 'xz', 'yy', 'yz', 'zz')
_IJ = ((0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2))
_RAW = ('arrival_flux_umol_s', *(f'arrival_M_{a}_umol_s' for a in 'xyz'),
        *(f'arrival_B_{a}_umol_s' for a in _SECOND))
_NORMALIZED = (*(f'{stem}_{a}' for stem in ('mean_arrival', 'dominant_arrival') for a in 'xyz'),
               'directionality', *(f'angular_second_{a}' for a in _SECOND))


def _matrix(values: list) -> np.ndarray:
    result = np.zeros((3, 3))
    for value, (i, j) in zip(values, _IJ): result[i, j] = result[j, i] = value
    return result


def _check_moment_bounds(row: dict, close: Any, atol: float) -> None:
    values = [row[k] for k in _RAW]
    if any(v is None for v in values):
        if any(v is not None for v in values): raise StudyError('partial_unknown_angular_moments')
        return
    f = values[0]; m = np.array(values[1:4]); b = _matrix(values[4:])
    if f < 0 or not close(np.trace(b), f) or np.linalg.eigvalsh(b).min() < -atol:
        raise StudyError('invalid_angular_second_moment')
    if (np.linalg.norm(m) > f and not close(np.linalg.norm(m), f)) or (f == 0 and np.any(np.array(values[1:]) != 0)):
        raise StudyError('invalid_angular_first_moment')
    if f > 0 and np.linalg.eigvalsh(b - np.outer(m, m) / f).min() < -atol * max(1., f):
        raise StudyError('inconsistent_angular_moment_covariance')


def _check_angular_feature(samples: list[dict], row: dict, rotation: np.ndarray,
                           close: Any, atol: float, dtol: float) -> None:
    """Independent sums/rotation/normalization; no exporter arithmetic imported."""
    if any(any(s[k] is None for k in _RAW) for s in samples):
        if any(row[k] is not None for k in (*_RAW, *_NORMALIZED)):
            raise StudyError('unknown_angular_sample_promoted_to_feature')
        return
    raw = [math.fsum(s[k] for s in samples) for k in _RAW]
    f = raw[0]; m = rotation @ np.array(raw[1:4]); b = rotation @ _matrix(raw[4:]) @ rotation.T
    wanted = dict(zip(_RAW, [f, *m, *(b[i, j] for i, j in _IJ)]))
    norm = float(np.linalg.norm(m))
    for stem, value in (('mean_arrival', m / f if f else None),
                        ('dominant_arrival', m / norm if f and norm > dtol * f else None)):
        wanted.update({f'{stem}_{a}': float(value[i]) if value is not None else None for i, a in enumerate('xyz')})
    wanted['directionality'] = norm / f if f else None
    wanted.update({f'angular_second_{a}': float(b[i, j] / f) if f else None for a, (i, j) in zip(_SECOND, _IJ)})
    if any(not close(row[k], value) for k, value in wanted.items()):
        raise StudyError('angular_feature_sum_frame_or_normalization_mismatch')
    _check_moment_bounds(row, close, atol)


def _check_angular_inventory(folder: Path, tables: dict, package: dict, schema: dict,
                             close: Any, atol: float) -> None:
    diagnostics = read_json(folder / 'angular_diagnostics.json')
    if set(diagnostics) != {s['geometry_snapshot_id'] for s in package['geometry_validity']}:
        raise StudyError('angular_snapshot_inventory_mismatch')
    full = [r for r in tables['light_samples.csv'] if r['time_step_id'] == 'full_output']
    for sid, meta in diagnostics.items():
        rows = [r for r in full if r['geometry_snapshot_id'] == sid]
        if meta.get('status') == 'unavailable_native_angular_channels':
            if rows: raise StudyError('native_angular_snapshot_has_direct_samples')
            continue
        if meta.get('protocol') != schema['angular_protocol'] or meta.get('status') != 'complete_inventory_scalar_and_normal_side_parity_passed':
            raise StudyError('unverified_angular_producer_protocol')
        n = meta['receiver_count']; limit = meta['max_chunk_paths']
        if type(n) is not int or n < 1 or type(limit) is not int or limit < 1 or not 0 <= meta['largest_chunk_paths'] <= limit:
            raise StudyError('invalid_angular_resource_inventory')
        inventory = {r['fixture_id']: r for r in meta['fixtures']}
        if len(inventory) != len(meta['fixtures']) or set(inventory) != set(package['schedule']['fixtures']):
            raise StudyError('angular_fixture_inventory_mismatch')
        receiver_ids = {}; groups = defaultdict(list)
        for row in rows:
            i = row['receiver_index']
            if i is None or int(i) != i or not 0 <= i < n: raise StudyError('invalid_global_angular_receiver_index')
            if i in receiver_ids and receiver_ids[i] != row['sample_id']: raise StudyError('angular_receiver_identity_changed')
            receiver_ids[i] = row['sample_id']; groups[i].append(row)
        if not package.get('split_instance_id') and set(receiver_ids) != set(range(n)):
            raise StudyError('missing_angular_receiver_inventory')
        for f in inventory.values():
            e = f['emitter_count']
            if e is None:
                if not f['unavailable_fixture_event'] or f['expected_path_count'] is not None or f['received_path_count'] is not None:
                    raise StudyError('invalid_unknown_fixture_inventory')
            elif (type(e) is not int or e < 1 or f['expected_path_count'] != n*e or f['received_path_count'] != n*e
                  or f['chunks'] != math.ceil(n*e/limit) or f['unavailable_fixture_event']):
                raise StudyError('incomplete_angular_path_inventory')
        for sample_rows in groups.values():
            by_fixture = {r['fixture_id']: r for r in sample_rows}
            if set(by_fixture) != set(inventory) | {'all'}: raise StudyError('missing_sample_angular_fixture')
            for fid, row in by_fixture.items():
                count = row['arrival_path_unknown_count']
                if count is not None and (count < 0 or int(count) != count): raise StudyError('invalid_unknown_path_count')
                if fid != 'all':
                    e = inventory[fid]['emitter_count']
                    if e is None:
                        if count is not None or row['arrival_flux_umol_s'] is not None: raise StudyError('unknown_fixture_claims_flux')
                    elif count is None or count > e or (count == 0) != (row['arrival_flux_umol_s'] is not None):
                        raise StudyError('angular_missingness_inventory_mismatch')
                else:
                    for k in (*_RAW, 'arrival_path_unknown_count'):
                        values = [by_fixture[f][k] for f in inventory]
                        expected = math.fsum(values) if all(v is not None for v in values) else None
                        if not close(row[k], expected): raise StudyError('angular_fixture_sum_mismatch')
    for row in tables['light_samples.csv']:
        _check_moment_bounds(row, close, atol)
        q = row['received_ppfd_umol_m2_s']
        if not close(row['arrival_flux_umol_s'], q * row['quadrature_area_m2'] if q is not None else None):
            raise StudyError('angular_flux_scalar_parity_mismatch')


def _time(value: str) -> datetime:
    result = datetime.fromisoformat(value)
    if result.tzinfo is None or result.utcoffset() is None:
        raise StudyError('timezone_required')
    return result.astimezone(timezone.utc)


def load_tables(folder: Path) -> dict:
    schema = read_json(folder / 'schema.json'); result = {}
    for name, spec in schema['tables'].items():
        with (folder / name).open(encoding='utf-8-sig', newline='') as stream:
            reader = csv.DictReader(stream)
            if reader.fieldnames != [c['name'] for c in spec['columns']]:
                raise StudyError('column_order_or_header_mismatch:' + name)
            records = []
            for raw in reader:
                row = {}
                if None in raw: raise StudyError('extra_csv_cells')
                for col in spec['columns']:
                    value = raw[col['name']]
                    if value is None or value == '': raise StudyError('empty_csv_cell:' + col['name'])
                    if col['type'] == 'number':
                        value = None if value == schema['csv_missing'] else float(value)
                        if value is None and not col['nullable']: raise StudyError('required_numeric_missing')
                        if value is not None and not math.isfinite(value): raise StudyError('nonfinite_numeric')
                    elif col['type'] == 'boolean':
                        if value not in ('True', 'False'): raise StudyError('invalid_boolean')
                        value = value == 'True'
                    elif col.get('nullable') and value == schema['csv_missing']:
                        value = None
                    if value is not None and col.get('enum') and value not in col['enum']:
                        raise StudyError('invalid_enum:' + col['name'])
                    row[col['name']] = value
                records.append(row)
            result[name] = records
    return result


def _check_feature_frames_regions(tables: dict, grouped: dict, transforms: dict, mapping: dict,
                                 capabilities: dict, close: Any, atol: float, dtol: float) -> None:
    """Independently verify frame-invariant scalars and measured local partitions."""
    features=tables['compound_light_features.csv']
    context_keys=('run_id','scenario_id','geometry_snapshot_id','time_step_id','backend','replicate','fixture_id')
    def key(row: dict) -> tuple:
        return (tuple(row[k] for k in context_keys),row['level'],row['entity_id'])
    observations={tuple(r[k] for k in ('geometry_snapshot_id','plant_instance_id','session_id','compound_id')):r
                  for r in mapping['observed_states']}
    whole={}; regional=defaultdict(dict)
    for row in features:
        if row['quantity_frame'] not in ('grow','board','compound_local'):
            raise StudyError('unknown_feature_coordinate_frame')
        if row['region_id']=='whole_supported': whole[(key(row),row['quantity_frame'])]=row
        else:
            if row['region_id'] in regional[key(row)]: raise StudyError('duplicate_region_across_frames')
            regional[key(row)][row['region_id']]=row
        angular=[v for k,v in row.items() if k.startswith(('arrival_','mean_arrival_','dominant_arrival_','angular_second_')) or k=='directionality']
        if capabilities[row['backend']]['directional']!='implemented' and any(v is not None for v in angular):
            raise StudyError('unsupported_directional_channel_claim')
        if row['backend']=='native':
            fields=('normal_side_ppfd_umol_m2_s','opposite_side_ppfd_umol_m2_s',
                    'received_p10_umol_m2_s','received_p50_umol_m2_s','received_p90_umol_m2_s')
            if row['region_id']!='whole_supported' or any(row[k] is not None for k in fields):
                raise StudyError('unsupported_native_spatial_or_side_claim')
    if set(regional)-set(grouped): raise StudyError('orphan_supported_region')
    scalar_fields=('supported_area_m2','supported_area_cm2','estimated_total_area_m2','coverage_fraction',
        'received_umol_s','absorbed_umol_s','received_supported_subtotal_umol_s','absorbed_supported_subtotal_umol_s',
        'normal_side_ppfd_umol_m2_s','opposite_side_ppfd_umol_m2_s','received_ppfd_umol_m2_s','absorbed_ppfd_umol_m2_s',
        'received_p10_umol_m2_s','received_p50_umol_m2_s','received_p90_umol_m2_s')
    for (identity,frame),row in whole.items():
        reference=whole.get((identity,'grow'))
        if reference is None: raise StudyError('missing_grow_frame_reference')
        if any(not close(row[k],reference[k]) for k in scalar_fields):
            raise StudyError('frame_scalar_invariance_mismatch')
        for k in ('plant_instance_id','source_plant_id','session_id','compound_id','compound_leaf_id',
                  'observed_at','area_basis_id','transform_id','coverage_status','frame_id'):
            if row[k]!=reference[k]: raise StudyError('frame_identity_or_area_basis_mismatch')
        observation_key=tuple(row[k] for k in ('geometry_snapshot_id','plant_instance_id','session_id','compound_id'))
        state=observations.get(observation_key) if row['level']=='compound' else None
        direction=state['direction_unit_xyz'] if state else None
        local_available=direction is not None and state['transverse_unit_xyz'] is not None
        required={'grow'} if row['level']=='canopy' else {'grow','board'}
        if local_available: required.add('compound_local')
        if frame not in required or any((identity,f) not in whole for f in required):
            raise StudyError('missing_or_unsupported_feature_frame')
        if row['backend'] == 'direct' and capabilities['direct']['directional'] == 'implemented':
            rotation = np.eye(3) if frame == 'grow' else np.asarray(transforms[row['transform_id']]['T_grow_to_board'])[:3, :3]
            if frame == 'compound_local':
                x = np.asarray(direction); y = np.asarray(state['transverse_unit_xyz'])
                rotation = np.column_stack((x, y, np.cross(x, y))).T @ rotation
            _check_angular_feature(grouped[identity], row, rotation, close, atol, dtol)
        expected=None
        if direction is not None:
            expected=np.asarray(direction,dtype=float)
            if frame=='grow': expected=np.asarray(transforms[row['transform_id']]['T_board_to_grow'])[:3,:3]@expected
            elif frame=='compound_local': expected=np.array([1.,0.,0.])
        actual=[row[f'observed_rachis_{a}'] for a in 'xyz']
        if expected is None:
            if any(v is not None for v in actual) or row['observed_azimuth_deg'] is not None or row['observed_elevation_deg'] is not None:
                raise StudyError('unavailable_observed_axis_fabricated')
        else:
            if any(v is None for v in actual) or not close(actual,expected): raise StudyError('observed_axis_frame_rotation_mismatch')
            xy=math.hypot(expected[0],expected[1])
            azimuth=None if xy<=OBSERVED_AXIS_NUMERIC_TOL else math.degrees(math.atan2(expected[1],expected[0]))
            elevation=math.degrees(math.atan2(expected[2],xy))
            if not close(row['observed_azimuth_deg'],azimuth) or not close(row['observed_elevation_deg'],elevation):
                raise StudyError('observed_axis_signed_angles_mismatch')
        if frame!='grow': continue
        partition=state.get('region_partition') if local_available and row['backend']=='direct' else None
        regions=regional.get(identity,{})
        if not partition:
            if regions: raise StudyError('regions_without_measured_partition')
            continue
        names=('left','right','lateral_unassigned','proximal','distal','longitudinal_unassigned')
        if set(regions)!=set(names): raise StudyError('missing_or_unknown_supported_regions')
        x=np.asarray(direction); y=np.asarray(state['transverse_unit_xyz']); basis=np.column_stack((x,y,np.cross(x,y)))
        origin=np.asarray(state['attachment_xyz_mm']); boundary=partition['proximal_distal_boundary_mm']
        bins={name:[] for name in names}
        for sample in grouped[identity]:
            point=np.array([sample[f'position_board_{a}_mm'] for a in 'xyz'])
            local=basis.T@(point-origin)
            lateral='lateral_unassigned' if abs(local[1])<=atol else 'left' if local[1]<0 else 'right'
            longitudinal='longitudinal_unassigned' if abs(local[0]-boundary)<=atol else 'proximal' if local[0]<boundary else 'distal'
            bins[lateral].append(sample); bins[longitudinal].append(sample)
        for name,region in regions.items():
            if region['quantity_frame']!='compound_local': raise StudyError('region_frame_mismatch')
            for field in ('plant_instance_id','session_id','compound_id','compound_leaf_id','frame_id','area_basis_id'):
                if region[field]!=row[field]: raise StudyError('region_identity_or_area_basis_mismatch')
            subset=bins[name]; area=math.fsum(s['quadrature_area_m2'] for s in subset)
            if capabilities['direct']['directional'] == 'implemented':
                rotation = basis.T @ np.asarray(transforms[row['transform_id']]['T_grow_to_board'])[:3, :3]
                _check_angular_feature(subset, region, rotation, close, atol, dtol)
            if not close(area,region['supported_area_m2']) or not close(area*10000,region['supported_area_cm2']):
                raise StudyError('region_supported_area_mismatch')
            if region['estimated_total_area_m2'] is not None or region['coverage_fraction'] is not None:
                raise StudyError('regional_completeness_without_evidence')
            for field in ('received_ppfd_umol_m2_s','absorbed_ppfd_umol_m2_s','normal_side_ppfd_umol_m2_s','opposite_side_ppfd_umol_m2_s'):
                values=[s[field] for s in subset]
                flux=math.fsum(v*s['quadrature_area_m2'] for v,s in zip(values,subset)) if all(v is not None for v in values) else None
                mean=flux/area if flux is not None and area>0 else None
                if not close(mean,region[field]): raise StudyError('region_weighted_mean_mismatch')
                prefix=field.split('_')[0]
                if prefix in ('received','absorbed'):
                    if not close(flux,region[prefix+'_umol_s']): raise StudyError('region_flux_mismatch')
                    known=[v*s['quadrature_area_m2'] for v,s in zip(values,subset) if v is not None]
                    subtotal=math.fsum(known) if known or not subset else None
                    if not close(subtotal,region[prefix+'_supported_subtotal_umol_s']): raise StudyError('region_subtotal_mismatch')
            values=[s['received_ppfd_umol_m2_s'] for s in subset]
            for percentile,fraction in (('p10',.1),('p50',.5),('p90',.9)):
                value=None
                if subset and all(v is not None for v in values):
                    cumulative=0.
                    for v,w in sorted((v,s['quadrature_area_m2']) for v,s in zip(values,subset)):
                        cumulative+=w
                        if cumulative>=area*fraction: value=v; break
                if not close(value,region[f'received_{percentile}_umol_m2_s']): raise StudyError('region_weighted_quantile_mismatch')
        local_whole=whole[(identity,'compound_local')]
        for prefix,a,b in (('left_right','left','right'),('proximal_distal','proximal','distal')):
            f1,f2=regions[a]['received_umol_s'],regions[b]['received_umol_s']
            q1,q2=regions[a]['received_ppfd_umol_m2_s'],regions[b]['received_ppfd_umol_m2_s']
            difference=f1-f2 if f1 is not None and f2 is not None else None
            contrast=(q1-q2)/(q1+q2) if q1 is not None and q2 is not None and q1+q2>0 else None
            if not close(difference,local_whole[prefix+'_flux_difference_umol_s']) or not close(contrast,local_whole[prefix+'_mean_contrast']):
                raise StudyError('region_signed_contrast_mismatch')


def _check_reference_channel(folder: Path, tables: dict, package: dict) -> None:
    from tools.light_reference_channel import CAPABILITY, check_attachment
    capabilities = read_json(folder/'capabilities.json')
    if capabilities.get('reference_dli') != CAPABILITY:
        raise StudyError('unsupported_reference_dli_capability')
    tissue = {r['area_basis_id'] for rows in tables.values() for r in rows if 'area_basis_id' in r}
    check_attachment(folder, read_json(folder/'reference_channel.json'),
        read_json(folder/'consumer_mapping.json')['growth']['reference_dli'], tissue, package)


def _check_biological_faces(folder: Path, tables: dict, package: dict) -> None:
    """Independent side classification, bound to the original reviewed request."""
    fields = ('geometry_snapshot_id', 'plant_instance_id', 'session_id', 'organ_id', 'leaflet_id', 'triangle_id')
    proof = package['request_source_ref']
    if package['source_hashes'].get(proof['path']) != proof['sha256']:
        raise StudyError('face_mapping_request_source_missing')
    request = read_json(Path(proof['path']))
    expected = {}
    for raw in request.get('face_mappings', []):
        mid = raw['mapping_id']
        if mid in expected: raise StudyError('duplicate_face_mapping_id')
        expected[mid] = dict(raw, evidence_path=str((Path(proof['path']).parent/raw['evidence_path']).resolve()))
    document = read_json(folder/'face_mappings.json')
    if document.get('schema_version') != 'biological-face-evidence-1' or document.get('mappings') != expected:
        raise StudyError('face_mapping_request_mismatch')
    lookup = {}
    for mid, item in expected.items():
        key = tuple(item[k] for k in fields)
        if key in lookup: raise StudyError('duplicate_face_mapping_surface')
        if item['review_status'] != 'reviewed' or not item.get('reviewer'):
            raise StudyError('unreviewed_face_mapping')
        if item['geometry_sha256'] != package['context_geometry_hashes'][item['geometry_snapshot_id']]:
            raise StudyError('face_mapping_geometry_mismatch')
        if package['source_hashes'].get(item['evidence_path']) != item['evidence_sha256']:
            raise StudyError('face_mapping_evidence_source_missing')
        if item['normal_biological_face'] not in ('adaxial', 'abaxial'):
            raise StudyError('invalid_normal_biological_face')
        lookup[key] = item
    availability = read_json(folder/'availability.json')
    for row in tables['light_samples.csv']:
        mapping = lookup.get(tuple(row[k] for k in fields))
        normal = mapping['normal_biological_face'] if mapping else None
        wanted = dict(normal_biological_face=normal, face_mapping_id=mapping['mapping_id'] if mapping else None,
                      face_source_ref='face_mappings.json#'+mapping['mapping_id'] if mapping else None)
        a, b = row['normal_side_ppfd_umol_m2_s'], row['opposite_side_ppfd_umol_m2_s']
        face = None
        reason = 'biological_face_mapping_unavailable'
        if mapping:
            if a is None or b is None: reason = 'face_exposure_unavailable'
            elif a < 0 or b < 0: raise StudyError('negative_face_exposure')
            elif a > 0 and b > 0: face = 'both'
            elif a > 0: face = normal+'_only'
            elif b > 0: face = ('abaxial' if normal == 'adaxial' else 'adaxial')+'_only'
            else: reason = 'no_positive_face_exposure'
        wanted['illuminated_faces'] = face
        if any(row[k] != v for k, v in wanted.items()): raise StudyError('biological_face_exposure_mismatch')
        if face is None and availability[row['availability_id']].get('illuminated_faces') != reason:
            raise StudyError('face_unavailability_reason_mismatch')


def validate_package(folder: Path) -> dict:
    report: dict[str, Any] = dict(valid=False, errors=[], checks=[], software_scope_complete=False, physical_validation=False)
    try:
        package = read_json(folder / 'package.json'); schema = read_json(folder / 'schema.json')
        authoritative = read_json(Path(__file__).with_name('light_growth_schema.json'))
        if schema != authoritative or package['schema_version'] != 'light-growth-1':
            raise StudyError('schema_contract_mismatch')
        for field in ('source_hashes', 'code_hashes', 'artifact_hashes'):
            for name, expected in package[field].items():
                path = folder / name if field == 'artifact_hashes' else Path(name)
                if field == 'artifact_hashes' and not path.resolve().is_relative_to(folder.resolve()):
                    raise StudyError('artifact_path_escape')
                if not path.is_file() or file_hash(path) != expected:
                    raise StudyError('stale_' + field + ':' + name)
        required = set(schema['required_json']) - {'package.json'} | set(schema['tables'])
        if not required.issubset(package['artifact_hashes']): raise StudyError('unhashed_required_artifact')
        report['checks'].append('source_code_artifact_freshness')
        from tools.light_geometry_evidence import check_package_evidence
        check_package_evidence(folder, package)
        report['checks'].append('geometric_computability_separate_from_physical_eligibility')
        tables = load_tables(folder); availability = read_json(folder / 'availability.json')
        _check_reference_channel(folder, tables, package)
        report['checks'].append('reference_channel_evidence_and_tissue_basis_separation')
        for name, rows in tables.items():
            spec = schema['tables'][name]; keys = set()
            for row in rows:
                key = tuple(row[k] for k in spec['primary_key'])
                if key in keys: raise StudyError('duplicate_primary_key:' + name)
                keys.add(key)
                reasons = availability.get(row['availability_id'])
                if reasons is None: raise StudyError('unknown_availability_id')
                for col in spec['columns']:
                    if (col['type'] == 'number' or col.get('nullable')) and row[col['name']] is None and not reasons.get(col['name']):
                        raise StudyError('missing_field_reason:' + col['name'])
                if row['run_id'] != package['run_id']: raise StudyError('foreign_run_id')
        report['checks'].append('exact_schema_keys_units_missingness')
        _check_biological_faces(folder, tables, package)
        report['checks'].append('reviewed_biological_faces_and_actual_side_exposure')
        policy = schema['numerical_policy']; atol = policy['absolute_tolerance']; rtol = policy['relative_tolerance']
        def close(a: Any, b: Any) -> bool:
            if a is None or b is None: return a is None and b is None
            return bool(np.allclose(a,b,atol=atol,rtol=rtol))
        transforms = read_json(folder / 'transforms.json')
        instances = {(r['geometry_snapshot_id'],r['plant_instance_id'],r['session_id'],r['compound_id']): r for r in tables['instance_map.csv']}
        validity = {r['geometry_snapshot_id']:r for r in package['geometry_validity']}
        for instance in instances.values():
            t = transforms[instance['transform_id']]
            forward=np.asarray(t['T_board_to_grow']); inverse=np.asarray(t['T_grow_to_board'])
            if forward.shape != (4,4) or inverse.shape != (4,4) or not close(forward @ inverse,np.eye(4)):
                raise StudyError('invalid_rigid_inverse')
            r=forward[:3,:3]
            if not close(r.T@r,np.eye(3)) or not close(np.linalg.det(r),1): raise StudyError('nonrigid_rotation')
            if instance['geometry_sha256'] != package['context_geometry_hashes'][instance['geometry_snapshot_id']]:
                raise StudyError('instance_geometry_hash_mismatch')
        intervals = {}; fractions = {}
        schedule=package['schedule']; zone=ZoneInfo(schedule['timezone'])
        def scheduled(fixture: str, moment: datetime) -> float | None:
            raw=schedule['fixtures'][fixture]
            if raw is None: return None
            if not raw: raise StudyError('empty_schedule_is_unknown')
            local=moment.astimezone(zone); minute=local.hour*60+local.minute
            for segment in raw:
                parsed=ScheduleSegment.model_validate(segment)
                if any(a<=minute<b for a,b in parsed.day_intervals_minutes()): return parsed.output_fraction
            return 0.
        for row in tables['light_intervals.csv']:
            a,b=_time(row['start_at']),_time(row['end_at'])
            if b<=a or not close((b-a).total_seconds(),row['duration_s']): raise StudyError('invalid_interval_duration')
            snapshot=validity[row['geometry_snapshot_id']]
            if a<_time(snapshot['valid_from']) or b>_time(snapshot['valid_until']): raise StudyError('outside_geometry_validity')
            interval_key=(row['geometry_snapshot_id'],row['time_step_id'],row['backend'],row['replicate'])
            if interval_key in intervals and (intervals[interval_key]['start_at'],intervals[interval_key]['end_at']) != (row['start_at'],row['end_at']):
                raise StudyError('inconsistent_fixture_interval')
            intervals[interval_key]=row
            expected=scheduled(row['fixture_id'],a+(b-a)/2) if row['fixture_id']!='all' else None
            if row['fixture_id']=='all':
                values=[scheduled(f,a+(b-a)/2) for f in schedule['fixtures']]
                if values and all(v is not None and v==values[0] for v in values): expected=values[0]
            if not close(expected,row['output_fraction']): raise StudyError('interval_schedule_fraction_mismatch')
            fractions[(*interval_key,row['fixture_id'])]=row['output_fraction']
        report['checks'].append('rigid_transform_geometry_validity')
        samples=tables['light_samples.csv']; full={}; by_time=defaultdict(list); grouped=defaultdict(list)
        for row in samples:
            if row['backend']!='direct': raise StudyError('unsupported_native_sample_claim')
            if row['quadrature_area_m2'] is None or row['quadrature_area_m2']<=0: raise StudyError('metric_sample_area_required')
            ikey=tuple(row[k] for k in ('geometry_snapshot_id','plant_instance_id','session_id','compound_id'))
            instance=instances.get(ikey)
            if instance is None: raise StudyError('orphan_sample_identity')
            for k in ('source_plant_id','frame_id','transform_id','compound_leaf_id','observed_at'):
                if row[k]!=instance[k]: raise StudyError('sample_instance_'+k+'_mismatch')
            forward=np.asarray(transforms[row['transform_id']]['T_board_to_grow'])
            p=np.array([row[f'position_board_{a}_mm'] for a in 'xyz'])
            g=np.array([row[f'position_grow_{a}_mm'] for a in 'xyz'])
            n=np.array([row[f'normal_board_{a}'] for a in 'xyz'])
            ng=np.array([row[f'normal_grow_{a}'] for a in 'xyz'])
            if not close(forward[:3,:3]@p+forward[:3,3],g) or not close(forward[:3,:3]@n,ng) or not close(np.linalg.norm(n),1):
                raise StudyError('sample_frame_roundtrip_mismatch')
            q,normal,opposite,absorbed=[row[k] for k in ('received_ppfd_umol_m2_s','normal_side_ppfd_umol_m2_s','opposite_side_ppfd_umol_m2_s','absorbed_ppfd_umol_m2_s')]
            if any(v is not None and v<0 for v in (q,normal,opposite,absorbed)): raise StudyError('negative_photon_quantity')
            if q is not None and normal is not None and opposite is not None and not close(normal+opposite,q):
                raise StudyError('side_budget_mismatch')
            if absorbed is not None and q is not None and absorbed>q+atol+rtol*q: raise StudyError('absorption_exceeds_incident')
            sample_key=(row['geometry_snapshot_id'],row['sample_id'],row['fixture_id'],row['replicate'])
            if row['time_step_id']=='full_output': full[sample_key]=row
            else:
                interval_key=(row['geometry_snapshot_id'],row['time_step_id'],row['backend'],row['replicate'])
                if interval_key not in intervals: raise StudyError('orphan_sample_time')
                by_time[interval_key].append(row)
            common=tuple(row[k] for k in ('run_id','scenario_id','geometry_snapshot_id','time_step_id','backend','replicate','fixture_id'))
            for level,parts in (('leaflet',(row['plant_instance_id'],row['session_id'],row['organ_id'],row['leaflet_id'])),
                                ('compound',(row['plant_instance_id'],row['session_id'],row['compound_id'])),
                                ('plant',(row['plant_instance_id'],)),('canopy',('__all__',))):
                if level=='compound' and row['compound_id']=='__unassigned__': continue
                if level=='canopy' and package.get('split_instance_id'): continue
                grouped[(common,level,digest([level,parts])[:24])].append(row)
        for key,rows in by_time.items():
            expected={k for k in full if k[0]==key[0] and k[3]==key[3]}
            actual={(r['geometry_snapshot_id'],r['sample_id'],r['fixture_id'],r['replicate']) for r in rows}
            if actual!=expected: raise StudyError('missing_or_extra_time_samples')
            for row in rows:
                reference=full[(row['geometry_snapshot_id'],row['sample_id'],row['fixture_id'],row['replicate'])]
                if row['receiver_index'] != reference['receiver_index'] or row['arrival_path_unknown_count'] != reference['arrival_path_unknown_count']:
                    raise StudyError('time_angular_inventory_changed')
                if not close(reference['quadrature_area_m2'],row['quadrature_area_m2']) or reference['area_basis_id']!=row['area_basis_id']:
                    raise StudyError('time_sample_area_basis_changed_without_snapshot')
                for field in ('received_ppfd_umol_m2_s','absorbed_ppfd_umol_m2_s','normal_side_ppfd_umol_m2_s','opposite_side_ppfd_umol_m2_s', *_RAW):
                    terms=[]
                    for fixture in schedule['fixtures'] if row['fixture_id']=='all' else [row['fixture_id']]:
                        original=full[(row['geometry_snapshot_id'],row['sample_id'],fixture,row['replicate'])][field]
                        factor=fractions[(*key,fixture)]
                        terms.append(original*factor if original is not None and factor is not None else None)
                    expected_value=math.fsum(terms) if all(v is not None for v in terms) else None
                    if not close(expected_value,row[field]): raise StudyError('scheduled_sample_value_mismatch')
        # Native scalar references stay leaflet aggregates. They are not exported as samples.
        for source in package.get('native_sources',[]):
            legacy=read_json(Path(source['results'])/'results.json'); manifest=legacy['manifest']
            if manifest['backend']!='native': raise StudyError('native_reference_backend_mismatch')
            previous={(r['target_id'],r['replicate']):r for r in legacy['tables']['interaction_cases'] if r['subset']=='ABC' and r['fixture_id']=='all'}
            replicates={r['replicate'] for r in legacy['tables']['interaction_cases']}
            for target in manifest['targets'].values():
                pid=target['plant_instance_id']
                if package.get('split_instance_id') and pid!=package['split_instance_id']: continue
                for replicate in replicates:
                    raw=previous.get((target['target_id'],replicate),{})
                    steps=[('full_output',1.)]+[(r['time_step_id'],r['output_fraction']) for r in tables['light_intervals.csv']
                        if r['geometry_snapshot_id']==source['geometry_snapshot_id'] and r['replicate']==replicate and r['backend']=='native' and r['fixture_id']=='all']
                    for step,fraction in steps:
                        row=dict(quadrature_area_m2=target['area_m2'])
                        for quantity in ('received','absorbed'):
                            flux=raw.get(quantity+'_umol_s')
                            row[quantity+'_ppfd_umol_m2_s']=flux/target['area_m2']*fraction if flux is not None and fraction is not None else None
                        common=(package['run_id'],manifest['plan']['scenario_id'],source['geometry_snapshot_id'],step,'native',replicate,'all')
                        for level,parts in (('leaflet',(pid,target['session_id'],target['organ_id'],target['leaflet_id'])),
                            ('compound',(pid,target['session_id'],target['compound_id'])),('plant',(pid,)),('canopy',('__all__',))):
                            if level=='compound' and not target['hierarchy_ready']: continue
                            if level=='canopy' and package.get('split_instance_id'): continue
                            grouped[(common,level,digest([level,parts])[:24])].append(row)
        features=tables['compound_light_features.csv']; checked=set()
        for row in features:
            if row['region_id']!='whole_supported' or row['quantity_frame']!='grow': continue
            common=tuple(row[k] for k in ('run_id','scenario_id','geometry_snapshot_id','time_step_id','backend','replicate','fixture_id'))
            key=(common,row['level'],row['entity_id']); group=grouped.get(key)
            if not group: raise StudyError('orphan_scalar_feature')
            checked.add(key); area=math.fsum(r['quadrature_area_m2'] for r in group)
            if not close(area,row['supported_area_m2']) or not close(area*10000,row['supported_area_cm2']):
                raise StudyError('aggregate_area_unit_mismatch')
            for name in ('received','absorbed'):
                values=[r[name+'_ppfd_umol_m2_s'] for r in group]
                flux=math.fsum(v*r['quadrature_area_m2'] for v,r in zip(values,group)) if all(v is not None for v in values) else None
                if not close(flux,row[name+'_umol_s']) or not close(None if flux is None else flux/area,row[name+'_ppfd_umol_m2_s']):
                    raise StudyError('sample_scalar_aggregate_mismatch')
        if checked!=set(grouped): raise StudyError('missing_scalar_aggregates')
        report['checks'].append('samples_sides_frames_missingness_quadrature_aggregates')
        dose_groups=defaultdict(list)
        dose_keys=('run_id','scenario_id','plant_instance_id','session_id','compound_id','backend','replicate','level','entity_id','fixture_id')
        for row in features:
            if row['time_step_id']=='full_output' or row['region_id']!='whole_supported' or row['quantity_frame']!='grow': continue
            dose_groups[tuple(row[k] for k in dose_keys)].append(row)
        checked_doses=set()
        for row in tables['light_dose.csv']:
            key=tuple(row[k] for k in dose_keys); group=dose_groups.get(key)
            if not group: raise StudyError('orphan_dose')
            checked_doses.add(key)
            start,end=_time(row['start_at']),_time(row['end_at']); requested=(end-start).total_seconds()
            if start!=_time(package['requested_interval']['start_at']) or end!=_time(package['requested_interval']['end_at']) or not close(requested,row['requested_seconds']):
                raise StudyError('dose_requested_interval_mismatch')
            periods=[]
            for item in group:
                interval=intervals[(item['geometry_snapshot_id'],item['time_step_id'],item['backend'],item['replicate'])]
                periods.append((_time(interval['start_at']),_time(interval['end_at']),item,interval['duration_s']))
            periods.sort(key=lambda p:p[0])
            if any(a[1]>b[0] for a,b in zip(periods,periods[1:])): raise StudyError('overlapping_dose_periods')
            for quantity,label,coverage in (('received','incident','covered_seconds'),('absorbed','absorbed','absorbed_covered_seconds')):
                valid=[p for p in periods if p[2][quantity+'_ppfd_umol_m2_s'] is not None and p[2][quantity+'_umol_s'] is not None]
                covered=math.fsum(p[3] for p in valid)
                subtotal=math.fsum(p[2][quantity+'_ppfd_umol_m2_s']*p[3] for p in valid)*1e-6 if valid else None
                photons=math.fsum(p[2][quantity+'_umol_s']*p[3] for p in valid)*1e-6 if valid else None
                complete=close(covered,requested)
                expected_values={coverage:covered,label+'_supported_dose_mol_m2':subtotal,
                    label+'_dose_mol_m2':subtotal if complete else None,label+'_photons_mol':photons if complete else None}
                if any(not close(value,row[field]) for field,value in expected_values.items()): raise StudyError('dose_integration_mismatch')
            local_start,local_end=start.astimezone(zone),end.astimezone(zone)
            daily=local_start.time().isoformat()==local_end.time().isoformat()=='00:00:00' and local_end.date()==local_start.date()+timedelta(days=1)
            daily=daily and close(row['covered_seconds'],requested)
            if row['complete_local_day']!=daily or not close(row['dli_mol_m2_day'],row['incident_dose_mol_m2'] if daily else None):
                raise StudyError('invalid_daily_light_label')
        if checked_doses!=set(dose_groups): raise StudyError('missing_dose_records')
        report['checks'].append('schedule_scaling_time_integrated_flux_and_dose')
        mapping=read_json(folder/'consumer_mapping.json')
        for observed in mapping['observed_states']:
            key=tuple(observed[k] for k in ('geometry_snapshot_id','plant_instance_id','session_id','compound_id'))
            if key not in instances:
                if package.get('split_instance_id') and observed['plant_instance_id']!=package['split_instance_id']: continue
                raise StudyError('orphan_growth_mapping')
            instance=instances[key]
            if instance['compound_leaf_id']!=observed['compound_leaf_id'] or instance['frame_id']!=observed['frame_id'] or _time(instance['observed_at'])!=_time(observed['observed_at']):
                raise StudyError('growth_identity_frame_time_mismatch')
            rows=[r for r in features if tuple(r[k] for k in ('geometry_snapshot_id','plant_instance_id','session_id','compound_id'))==key and r['level']=='compound' and r['quantity_frame']=='board' and r['region_id']=='whole_supported']
            if not rows: raise StudyError('missing_board_compound_features')
            for row in rows:
                if row['area_basis_id']!=observed['area_basis_id']: raise StudyError('growth_area_basis_mismatch')
                actual=[row[f'observed_rachis_{a}'] for a in 'xyz']
                actual=None if all(v is None for v in actual) else actual
                if not close(actual,observed['direction_unit_xyz']):
                    raise StudyError('growth_observed_direction_changed')
        report['checks'].append('reviewed_growth_identity_frame_time_area_direction')
        _check_angular_inventory(folder, tables, package, schema, close, atol)
        _check_feature_frames_regions(tables,grouped,transforms,mapping,read_json(folder/'capabilities.json'),close,atol,
                                      policy['direction_degeneracy_tolerance'])
        report['checks'].append('actual_path_inventory_moment_flux_fixture_time_frame_region_consistency')
        report['checks'].append('frame_scalar_invariance_observed_rotations_supported_regions_capabilities')
        if package.get('split_instance_id'):
            parent=read_json(Path(package['parent_package'])/'package.json')
            if parent['canopy_run_id']!=package['canopy_run_id'] or parent['context_geometry_hashes']!=package['context_geometry_hashes']:
                raise StudyError('split_lost_canopy_context')
        report.update(valid=True, software_scope_complete=package['software_scope_complete'],
            counts={name:len(rows) for name,rows in tables.items()},
            limitations=['native_angular_channels_unavailable','no_independent_physical_validation'])
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report['errors'].append(str(exc))
    return report
