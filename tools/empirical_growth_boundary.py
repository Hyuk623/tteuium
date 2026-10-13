"""Export conditional empirical light by frozen interval, scenario and physical leaf surface."""
from __future__ import annotations

import argparse
from datetime import datetime
from pathlib import Path

import numpy as np

from tools.empirical_canopy import intercept
from tools.empirical_light_field import evaluate, finite, load_field, code_hashes as field_code_hashes
from tools.leaf_light.common import StudyError, digest, file_hash, output_dir, read_json, write_json, write_rows
from tools.tomato_fsp_canopy import rigid, triangle_area

SCHEMA = 'empirical-growth-boundary-1'
REQUEST = 'empirical-growth-request-1'
FACE = 'both_geometric_faces_single_lamina_area'
RULE = 'local_horizontal_environment_before_one_canopy_attenuation'


def require(ok: bool, reason: str) -> None:
    if not ok:
        raise StudyError(reason)


def timestamp(value: str) -> datetime:
    try:
        result = datetime.fromisoformat(value)
    except (ValueError, TypeError) as exc:
        raise StudyError('invalid_interval_timestamp') from exc
    require(result.utcoffset() is not None, 'timezone_required')
    return result


def source(ref: dict, hashes: dict) -> Path:
    require(isinstance(ref, dict) and bool(ref.get('path')) and bool(ref.get('sha256')), 'hashed_source_ref_required')
    path = Path(ref['path']).resolve()
    require(file_hash(path) == ref['sha256'], 'source_hash_mismatch:'+str(path))
    hashes[str(path)] = ref['sha256']
    return path


def code_hashes() -> dict:
    paths = [Path(__file__), Path(__file__).with_name('empirical_growth_consumer.py'),
             Path(__file__).with_name('tomato_fsp_canopy.py')]
    return dict(field_code_hashes(), **{str(p.resolve()): file_hash(p) for p in paths})


def geometry(snapshot: dict, registration: dict, field: dict) -> tuple[dict, list[dict]]:
    """Consume actual assemble_canopy output; never reconstruct a leaf from area/outline proxies."""
    require(snapshot.get('frame') == 'canopy_m' and snapshot.get('length_unit') == 'm', 'canopy_frame_m_required')
    surfaces = snapshot['surfaces']
    require(bool(surfaces), 'empty_canopy')
    canonical = [{k: s[k] for k in ('surface_id', 'triangles_m')} for s in surfaces]
    require(snapshot.get('geometry_hash') == digest(canonical), 'geometry_hash_mismatch')
    require(registration.get('from_frame') == 'canopy_m' and registration.get('to_frame') == 'grow_mm', 'registration_frame_mismatch')
    require(registration.get('source_kind') in ('fixture_truth', 'reviewed') and registration.get('source_ref'), 'registration_evidence_required')
    rotation, translation_mm = rigid(registration['rotation'], registration['translation_mm'])
    require(len({s['surface_id'] for s in surfaces}) == len(surfaces), 'duplicate_surface_namespace')
    require(len({s['organ_id'] for s in surfaces}) == len(surfaces), 'one_surface_per_leaf_organ_required_v1')
    identities = snapshot['identity_map']
    expected = [{k: s[k] for k in ('surface_id', 'plant_instance_id', 'source_plant_id', 'organ_id', 'producer_vertex_id')} for s in surfaces]
    require(identities == expected, 'identity_map_mismatch')
    triangles = []; receivers = []; metadata = []
    for s in surfaces:
        pid = s['plant_instance_id']; oid = s['organ_id']; sid = s['surface_id']
        require(isinstance(pid, str) and bool(pid) and '|' not in pid and oid == pid+'|'+s['producer_vertex_id'], 'plant_organ_namespace_mismatch')
        require(bool(sid) and s.get('geometry_source') in ('synthetic_truth', 'reviewed_optical_surface'), 'physical_optical_surface_required')
        require(s.get('face_convention') == 'triangle_winding_geometric_normal', 'explicit_geometric_face_convention_required')
        local_m = np.asarray(s['triangles_m'], dtype=float)
        require(local_m.ndim == 3 and local_m.shape[1:] == (3,3) and len(local_m) > 0 and np.isfinite(local_m).all(), 'invalid_optical_triangles')
        area_m2 = sum(triangle_area(t) for t in local_m)
        require(area_m2 > 0 and np.isclose(area_m2, finite(s['area_m2']), atol=1e-14, rtol=1e-10), 'one_sided_area_mismatch')
        require(np.isclose(area_m2, finite(snapshot['one_sided_areas_m2'][sid]), atol=1e-14, rtol=1e-10), 'area_inventory_mismatch')
        transformed_mm = local_m*1000@rotation.T+translation_mm
        for t in transformed_mm:
            # Vertices as well as the quadrature point must be supported. No partial-leaf scaling.
            for point_mm in t:
                evaluate(field, point_mm.tolist())
            vector = np.cross(t[1]-t[0], t[2]-t[0]); norm = np.linalg.norm(vector)
            require(norm > 0, 'degenerate_triangle')
            index = len(triangles)
            triangles.append(dict(role='leaf', surface_id=sid, vertices_mm=t.tolist()))
            receivers.append(dict(receiver_id=f'triangle-{index}', leaf_id=sid,
                position_mm=t.mean(axis=0).tolist(), normal=(vector/norm).tolist(),
                supported_one_sided_area_m2=float(norm*.5e-6), own_triangle=index))
        metadata.append(dict(plant_instance_id=pid, source_plant_id=s['source_plant_id'], organ_id=oid,
            surface_id=sid, one_sided_area_m2=area_m2, geometry_source=s['geometry_source']))
    return dict(triangles=triangles, receivers=receivers), metadata


def schedule(interval: dict, fixture_ids: list[str]) -> list[dict]:
    begin = timestamp(interval['start_at']); end = timestamp(interval['end_at'])
    require(end > begin, 'nonpositive_interval')
    cursor = begin; result = []
    require(bool(interval.get('segments')), 'explicit_schedule_required')
    for i, s in enumerate(interval['segments']):
        a = timestamp(s['start_at']); b = timestamp(s['end_at'])
        require(a == cursor and b > a and b <= end, 'schedule_gap_overlap_or_outside_interval')
        fractions = s.get('fixture_fractions', {})
        require(set(fractions) == set(fixture_ids), 'fixture_schedule_membership_mismatch')
        values = [finite(fractions[f]) for f in fixture_ids]
        require(len(set(values)) == 1 and values[0] in (0., 1.), 'aggregate_field_requires_common_full_or_off_schedule')
        require(s.get('source_kind') in ('user_stated','user_assumed','fixture_truth') and s.get('source_ref'), 'schedule_provenance_required')
        result.append(dict(segment_index=i, start_at=s['start_at'], end_at=s['end_at'],
            duration_s=(b-a).total_seconds(), output_fraction=values[0]))
        cursor = b
    require(cursor == end, 'schedule_incomplete')
    return result


def absorption(value: dict | None) -> tuple[float | None, float | None]:
    if value is None:
        return None, None
    require(value.get('source_kind') in ('user_assumed','fixture_truth','measured') and value.get('source_ref'), 'absorptance_provenance_required')
    a, b = finite(value['normal']), finite(value['opposite'])
    require(0 <= a <= 1 and 0 <= b <= 1, 'invalid_absorptance')
    return a, b


def compute(request_path: Path) -> tuple[dict, list[dict], list[dict], list[dict]]:
    req = read_json(request_path); hashes = {str(request_path.resolve()): file_hash(request_path)}
    require(req.get('schema_version') == REQUEST and bool(req.get('run_id')), 'invalid_boundary_request')
    contract = req.get('transport_contract', {})
    require(contract.get('interpretation') == RULE and contract.get('source_ref') and
        contract.get('source_kind') in ('user_assumed','fixture_truth','reviewed'), 'explicit_scientific_transport_contract_required')
    require(contract.get('field_light_basis') == 'incident' and contract.get('already_canopy_shaded') is False and
        contract.get('canopy_shading_passes') == 1 and contract.get('quadrature') == 'triangle_centroid_area_weighted', 'double_shading_or_unsupported_input_basis')
    require(contract.get('local_field_approximation_acknowledged') is True, 'local_field_transport_assumption_not_acknowledged')
    require(contract.get('canopy_scattering') == 'not_modelled_transmission_only', 'explicit_canopy_scattering_limit_required')
    require(req.get('off_period_ambient') == 'excluded_unmeasured', 'ambient_not_supported_by_empirical_lamp_field')
    field_path = source(req['field_ref'], hashes); config_path = source(req['configuration_ref'], hashes)
    field = load_field(field_path, config_path)
    fixture_ids = req.get('fixture_ids', [])
    require(bool(fixture_ids) and len(set(fixture_ids)) == len(fixture_ids), 'invalid_fixture_inventory')
    bars = field['configuration']['empirical_contract'].get('direction_bars') or []
    require({b.get('fixture_id') for b in bars} == set(fixture_ids), 'field_direction_fixture_membership_mismatch')
    intervals = req.get('intervals', [])
    require(bool(intervals) and len({i['interval_id'] for i in intervals}) == len(intervals), 'invalid_interval_inventory')
    rows = []; audit = []; bindings = []; previous_end = None
    for interval in intervals:
        require(previous_end is None or timestamp(interval['start_at']) == previous_end, 'interval_gap_or_overlap')
        previous_end = timestamp(interval['end_at'])
        segments = schedule(interval, fixture_ids)
        snapshot_path = source(interval['snapshot_ref'], hashes)
        registration_path = source(interval['registration_ref'], hashes)
        snapshot = read_json(snapshot_path); registration = read_json(registration_path)
        if registration.get('source_kind') == 'reviewed': source(registration['source_ref'], hashes)
        require(interval['expected_geometry_hash'] == snapshot.get('geometry_hash'), 'expected_geometry_mismatch')
        mesh, identities = geometry(snapshot, registration, field)
        fixture = all(s['geometry_source'] == 'synthetic_truth' for s in identities)
        require(fixture or all(s['geometry_source'] == 'reviewed_optical_surface' for s in identities), 'mixed_geometry_provenance')
        if not fixture: source(interval['surface_review_ref'], hashes)
        scene = dict(schema_version='empirical-canopy-1', coordinate_frame='grow',
            source_kind='fixture_truth' if fixture else 'reviewed_optical_surface',
            source_ref=str(snapshot_path) if fixture else interval['surface_review_ref'],
            configuration_sha256=field['configuration_sha256'], direction_source_kind='user_assumed',
            diffuse_fractions=req['diffuse_fractions'], quadrature=req['quadrature'],
            leaf_transmittance=req['leaf_transmittance'], leaf_transmittance_source_ref=req.get('leaf_transmittance_source_ref'), **mesh)
        result = intercept(field, scene)
        optics = interval.get('absorptance_by_surface', {})
        require(set(optics) == {s['surface_id'] for s in identities}, 'absorptance_inventory_mismatch')
        binding = dict(interval_id=interval['interval_id'], start_at=interval['start_at'], end_at=interval['end_at'],
            geometry_hash=snapshot['geometry_hash'], geometry_hash_scheme='fsp_canopy_surface_triangles_m_v1',
            snapshot_sha256=file_hash(snapshot_path), registration_sha256=file_hash(registration_path),
            placement_hash=snapshot['placement_hash'], configuration_sha256=field['configuration_sha256'],
            namespace_hash=digest(snapshot['identity_map']), orientation_variant=field['configuration']['empirical_contract']['coordinate_variant'])
        bindings.append(binding)
        for ident in identities:
            sid = ident['surface_id']; alpha_normal, alpha_opposite = absorption(optics[sid])
            tau = req['leaf_transmittance']
            if tau is not None and alpha_normal is not None:
                require(max(alpha_normal, alpha_opposite)+finite(tau) <= 1+1e-12, 'absorptance_transmittance_exceed_one')
            for fraction in req['diffuse_fractions']:
                samples = [r for r in result['receivers'] if r['leaf_id'] == sid and r['diffuse_fraction'] == fraction]
                valid = all(r['status'] != 'unavailable' for r in samples)
                upper = sum(r['supported_one_sided_area_m2']*r['upper_ppfd_umol_m2_s'] for r in samples) if valid else None
                lower = sum(r['supported_one_sided_area_m2']*r['lower_ppfd_umol_m2_s'] for r in samples) if valid else None
                area = sum(r['supported_one_sided_area_m2'] for r in samples)
                require(np.isclose(area, ident['one_sided_area_m2'], rtol=1e-10, atol=1e-14), 'incomplete_area_support')
                evidence_id = f"{interval['interval_id']}:{sid}:{fraction}"
                audit.append(dict(evidence_id=evidence_id, samples=samples, absorption=optics[sid]))
                for segment in segments:
                    scale = segment['output_fraction']; seconds = segment['duration_s']
                    # Off is explicitly observed/declarative schedule zero, never missing schedule.
                    a = upper*scale if valid else (0. if scale == 0 else None)
                    b = lower*scale if valid else (0. if scale == 0 else None)
                    incident = a+b if a is not None else None
                    absorbed = (a*alpha_normal+b*alpha_opposite) if incident is not None and alpha_normal is not None else None
                    available = incident is not None
                    rows.append(dict(binding | ident | segment, diffuse_fraction=fraction,
                        evidence_id=evidence_id, face_convention=FACE, normal_side='triangle_winding_not_botanical_upper',
                        source_kind='derived', method='empirical_light_field', direction_source_kind='user_assumed',
                        shading_passes=1, incident_normal_umol_s=a, incident_opposite_umol_s=b,
                        incident_umol_s=incident, incident_ppfd_umol_m2_s=incident/area if available else None,
                        incident_dose_umol=incident*seconds if available else None,
                        incident_dose_mol_m2=incident*seconds/area/1e6 if available else None,
                        absorbed_umol_s=absorbed, absorbed_ppfd_umol_m2_s=absorbed/area if absorbed is not None else None,
                        absorbed_dose_umol=absorbed*seconds if absorbed is not None else None,
                        absorbed_dose_mol_m2=absorbed*seconds/area/1e6 if absorbed is not None else None,
                        light_basis='incident_with_separate_absorbed' if alpha_normal is not None else 'incident_only',
                        status='conditional' if available else 'unavailable',
                        absorbed_status='conditional' if absorbed is not None else 'unavailable',
                        missing_reason=None if available else 'leaf_transmittance_unavailable',
                        absorbed_missing_reason=None if absorbed is not None else ('absorptance_unavailable' if alpha_normal is None else 'incident_light_unavailable')))
    manifest = dict(schema_version=SCHEMA, run_id=req['run_id'], method='empirical_light_field', source_kind='derived',
        status='conditional_export_only', native_consumption='unverified_hook_required',
        physical_accuracy='unvalidated', coordinate_frame='grow_mm', face_convention=FACE,
        configuration_sha256=field['configuration_sha256'], transport_contract=contract,
        intervals=bindings, diffuse_fractions=req['diffuse_fractions'], rows=rows,
        source_hashes=hashes, code_hashes=code_hashes(), request_path=str(request_path.resolve()),
        schedule_semantics='explicit_segments_no_clock_or_off_state_imputation',
        disclosures=['local_environment_model_not_conservative_room_radiance', 'no_native_reshading_or_second_absorptance',
            'no_reference_dli_scaling', 'no_growth_or_physiology_computation', 'no_below_canopy_bounce_solution',
            'geometric_faces_are_not_botanical_faces', 'triangle_centroid_quadrature_requires_spatial_refinement_check'])
    return manifest, rows, audit, bindings


def export(request_path: Path, out: Path) -> dict:
    manifest, records, audit, _ = compute(request_path)
    folder = output_dir(out)
    write_rows(folder/'leaf_segments.csv', records, list(records[0]))
    write_json(folder/'transport_evidence.json', audit)
    totals = []
    for key in dict.fromkeys((r['interval_id'], r['surface_id'], r['diffuse_fraction']) for r in records):
        group = [r for r in records if (r['interval_id'], r['surface_id'], r['diffuse_fraction']) == key]
        first = group[0]
        total = {k: first[k] for k in ('interval_id','plant_instance_id','organ_id','surface_id','diffuse_fraction',
            'geometry_hash','registration_sha256','namespace_hash','one_sided_area_m2','start_at')}
        total.update(start_at=group[0]['start_at'], end_at=group[-1]['end_at'],
                     duration_s=sum(r['duration_s'] for r in group), on_duration_s=sum(r['duration_s']*r['output_fraction'] for r in group))
        for name in ('incident_dose_umol','absorbed_dose_umol','incident_dose_mol_m2','absorbed_dose_mol_m2'):
            total[name] = sum(r[name] for r in group) if all(r[name] is not None for r in group) else None
        totals.append(total)
    manifest['interval_totals'] = totals
    write_rows(folder/'leaf_intervals.csv', totals, list(totals[0]))
    manifest['artifact_hashes'] = {name: file_hash(folder/name) for name in ('leaf_segments.csv', 'leaf_intervals.csv', 'transport_evidence.json')}
    write_json(folder/'boundary.json', manifest)
    return manifest


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--request', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = export(args.request, args.out)
        print(dict(status=result['status'], rows=len(result['rows']), native_consumption=result['native_consumption']))
        return 0
    except (StudyError, ValueError, KeyError, OSError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
