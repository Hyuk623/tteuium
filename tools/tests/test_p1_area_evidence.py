"""Synthetic contract fixtures only; no test establishes physical leaf accuracy."""
from copy import deepcopy
from pathlib import Path

import cv2
import numpy as np
import pytest

from tools import compound_surface as cs
from tools.leaf_light.common import StudyError, digest, file_hash, read_json, rows, write_json, write_rows
from tools.tests.test_compound_surface import POLICY, row


def fixture(tmp_path):
    geometry = [row(np.array([[0, 0, 0], [10, 0, 0], [0, 10, 0]], float))]
    face = {**{k: geometry[0][k] for k in cs.KEY}, 'tissue_patch_id': 'patch',
            'identity_status': 'confirmed', 'support_kind': 'observed_supported',
            'topology_review': 'accepted', 'review_source': 'fixture_review'}
    intr = dict(camera_matrix=[[10, 0, 40], [0, 10, 40], [0, 0, 1]],
                dist_coeffs=[0, 0, 0, 0, 0], image_width_px=100, image_height_px=100)
    views = {'patch': [(dict(image_file=f'v{i}', rvec_rad=[0, 0, 0], tvec_mm=[i, 0, 10],
                            pose_status='solved', passes_pose_gate=True, reprojection_error_px=0.2),
                       intr, np.ones((100, 100), bool)) for i in range(2)]}
    sources = {}
    for name in ('partition', 'identity', 'scale', 'pose', 'capture', 'schedule', 'area'):
        p = tmp_path/('capture_evidence.json' if name == 'capture' else name+'.json')
        write_json(p, {'fixture_only': True, 'evidence_group': name})
        sources[name] = dict(path=p.name, sha256=file_hash(p))
    patch = {**{k: geometry[0][k] for k in cs.KEY[:5]}, 'tissue_patch_id': 'patch',
             'area_basis_id': 'fixture_patch_one_sided',
             'identity': dict(partition_sha256=sources['partition']['sha256'], reviewer='fixture reviewer', source_ref='identity'),
             'scale': dict(square_size_mm=10, calibration_residual_mm=0.01, source_ref='scale'),
             'pose': dict(max_reprojection_error_px=1, source_ref='pose'),
             'capture': dict(captured_at='2026-10-04T08:00:00+09:00', capture_phase='early_photoperiod',
                             source_ref='capture', schedule_source_ref='schedule'),
             'area': dict(quantity='one_sided_physical_tissue', coverage_fraction=0.5,
                          occlusion_statement='Fixture covers only the reviewed visible patch', source_ref='area')}
    context = dict(schema='p1-area-evidence-1', data_kind='observed', geometry_digest=digest(geometry),
                   partition_source_ref='partition', sources=sources, patches=[patch])
    return geometry, [face], views, context


def audit(tmp_path, data):
    geometry, evidence, views, context = data
    return cs.audit_surface(geometry, evidence, POLICY, views, area_evidence=context, evidence_base=tmp_path)


def claim(result):
    return result['area_evidence']['patches'][0]


def test_complete_evidence_gates_area_without_face_or_optical_claim(tmp_path):
    data = fixture(tmp_path)
    frozen = deepcopy((data[0], data[1], data[3]))
    result = audit(tmp_path, data)
    assert claim(result)['status'] == 'evidence_complete'
    assert claim(result)['downstream_supported_area_cm2'] == pytest.approx(0.5)
    assert result['faces'][0]['eligible_real_area']
    assert not result['validated_metric'] and not result['suitable_for_ppfd']
    assert result['area_evidence']['biological_face_status'] == 'unavailable'
    assert result['area_evidence']['illuminated_faces'] is None
    assert (data[0], data[1], data[3]) == frozen


@pytest.mark.parametrize('group,reason', [
    ('scale', 'physical_scale_evidence_unavailable'),
    ('pose', 'pose_evidence_unavailable'),
    ('capture', 'capture_time_phase_evidence_unavailable'),
    ('area', 'one_sided_area_evidence_unavailable'),
    ('identity', 'partition_identity_review_unavailable'),
])
def test_each_missing_evidence_group_refuses_real_claim(tmp_path, group, reason):
    data = fixture(tmp_path)
    del data[3]['patches'][0][group]
    result = audit(tmp_path, data)
    assert reason in claim(result)['reasons']
    assert claim(result)['area_basis_id'] is None
    assert claim(result)['downstream_supported_area_cm2'] is None
    assert not result['faces'][0]['eligible_real_area']
    assert result['compounds'][0]['supported_area_cm2'] == pytest.approx(0.5)  # diagnostic unchanged


@pytest.mark.parametrize('field,value,reason', [
    ('captured_at', '2026-10-04T08:00:00', 'capture_time_phase_evidence_unavailable'),
    ('capture_phase', 'unknown', 'capture_time_phase_evidence_unavailable'),
    ('schedule_source_ref', None, 'capture_time_phase_evidence_unavailable'),
])
def test_time_phase_needs_actual_evidence(tmp_path, field, value, reason):
    data = fixture(tmp_path); data[3]['patches'][0]['capture'][field] = value
    assert reason in claim(audit(tmp_path, data))['reasons']


@pytest.mark.parametrize('value', [None, -1, 0, 1.1, float('nan'), True])
def test_invalid_coverage_cannot_issue_basis(tmp_path, value):
    data = fixture(tmp_path); data[3]['patches'][0]['area']['coverage_fraction'] = value
    assert 'one_sided_area_evidence_unavailable' in claim(audit(tmp_path, data))['reasons']


def test_stale_partition_and_geometry_bindings_refused(tmp_path):
    data = fixture(tmp_path)
    data[3]['patches'][0]['identity']['partition_sha256'] = '0'*64
    data[0][0]['v1_x_mm'] = 12
    why = claim(audit(tmp_path, data))['reasons']
    assert 'partition_identity_review_unavailable' in why
    assert 'area_geometry_binding_unavailable' in why


@pytest.mark.parametrize('key,value,reason', [
    ('reprojection_error_px', None, 'pose_evidence_unavailable'),
    ('reprojection_error_px', 2, 'pose_evidence_rejected'),
    ('passes_pose_gate', False, 'pose_evidence_rejected'),
])
def test_every_support_frame_must_pass_pose_policy(tmp_path, key, value, reason):
    data = fixture(tmp_path); data[2]['patch'][1][0][key] = value
    assert reason in claim(audit(tmp_path, data))['reasons']


def test_source_missing_is_unavailable_but_tampered_hash_is_integrity_error(tmp_path):
    data = fixture(tmp_path)
    data[3]['sources']['scale']['path'] = 'absent.json'
    assert 'physical_scale_evidence_unavailable' in claim(audit(tmp_path, data))['reasons']
    data[3]['sources']['scale']['path'] = 'scale.json'
    (tmp_path/'scale.json').write_text('changed', encoding='utf-8')
    with pytest.raises(StudyError, match='source hash mismatch'): audit(tmp_path, data)


def test_explicit_synthetic_ids_never_become_real_claim(tmp_path):
    data = fixture(tmp_path); data[3]['data_kind'] = 'synthetic'
    result = audit(tmp_path, data)
    assert claim(result)['data_kind'] == 'synthetic'
    assert claim(result)['declared_area_basis_id'] == 'fixture_patch_one_sided'
    assert claim(result)['area_basis_id'] is None
    assert 'synthetic_not_real_area' in claim(result)['reasons']


@pytest.mark.parametrize('quantity', ['projected_mask_area', 'relative_area', 'estimated_total_area',
                                     'hull_footprint', 'hull_surface_area', 'area_review_A2_fit'])
def test_nonphysical_area_basis_is_refused(tmp_path, quantity):
    data = fixture(tmp_path); data[3]['patches'][0]['area']['quantity'] = quantity
    assert 'one_sided_area_evidence_unavailable' in claim(audit(tmp_path, data))['reasons']


def test_incomplete_support_does_not_reuse_coverage_id(tmp_path):
    data = fixture(tmp_path); data[1][0]['identity_status'] = 'proposed'
    result = audit(tmp_path, data)
    assert 'patch_geometry_support_incomplete' in claim(result)['reasons']
    assert not result['faces'][0]['eligible_real_area']


def test_generated_or_assumed_geometry_is_not_measured(tmp_path):
    data = fixture(tmp_path); data[0][0]['geometry_source'] = 'assumed'
    data[3]['geometry_digest'] = digest(data[0])
    assert 'physical_tissue_geometry_source_unavailable' in claim(audit(tmp_path, data))['reasons']


def test_legacy_call_keeps_diagnostic_area_and_explicit_real_unavailability(tmp_path):
    geometry, evidence, views, _ = fixture(tmp_path)
    result = cs.audit_surface(geometry, evidence, POLICY, views)
    assert result['compounds'][0]['supported_area_cm2'] == pytest.approx(0.5)
    assert claim(result)['status'] == 'unavailable'
    assert 'area_evidence_undeclared' in claim(result)['reasons']


def write_study(tmp_path, synthetic=False):
    geometry, evidence, views, context = fixture(tmp_path)
    write_rows(tmp_path/'geometry.csv', geometry, cs.LEAF_SURFACES_CSV_COLUMNS)
    # Geometry digest binds the exact loaded table, including CSV string cells.
    context['geometry_digest'] = digest(rows(tmp_path/'geometry.csv'))
    write_rows(tmp_path/'faces.csv', evidence, list(evidence[0]))
    write_json(tmp_path/'area_evidence.json', context)
    capture = dict(plant_id='p', session_id='s', intrinsics=views['patch'][0][1],
                   frames=[v[0] for v in views['patch']])
    write_json(tmp_path/'capture.json', capture)
    cv2.imencode('.png', np.full((100, 100), 255, np.uint8))[1].tofile(tmp_path/'mask.png')
    study = dict(schema='compound-surface-study-1', policy=POLICY, geometry_csv='geometry.csv',
                 geometry_sha256=file_hash(tmp_path/'geometry.csv'), evidence_csv='faces.csv',
                 evidence_sha256=file_hash(tmp_path/'faces.csv'),
                 area_evidence=dict(path='area_evidence.json', sha256=file_hash(tmp_path/'area_evidence.json')),
                 visible_support=[dict(tissue_patch_id='patch', visibility='visible', review_source='fixture',
                    capture='capture.json', capture_sha256=file_hash(tmp_path/'capture.json'),
                    mask='mask.png', mask_sha256=file_hash(tmp_path/'mask.png'), image_file=f'v{i}') for i in range(2)])
    if synthetic: study['data_kind'] = 'synthetic'
    write_json(tmp_path/'study.json', study)
    return tmp_path/'study.json'


@pytest.mark.parametrize('synthetic', [False, True])
def test_cli_boundary_preserves_sources_and_serializes_separate_exports(tmp_path, synthetic):
    study = write_study(tmp_path, synthetic)
    before = {p: file_hash(p) for p in tmp_path.iterdir() if p.is_file()}
    out = tmp_path/'out'
    result = cs.audit_study(study, out)
    assert all(file_hash(p) == h for p, h in before.items())
    assert len(rows(out/'supported_leaf_surfaces.csv')) == 1
    assert len(rows(out/'downstream_leaf_surfaces.csv')) == (0 if synthetic else 1)
    assert rows(out/'area_basis.csv')[0]['status'] == ('unavailable' if synthetic else 'evidence_complete')
    assert read_json(out/'surface_review.json')['review_state'] == 'pending'
    assert claim(result)['data_kind'] == ('synthetic' if synthetic else 'observed')
