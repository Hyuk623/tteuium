"""The bridge links existing contracts without promoting diagnostic data."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools import plant_light_bridge as bridge
from tools import ppfd_validation as pv
from tools.leaf_light.common import StudyError, file_hash, read_json, rows, write_json, write_rows
from tools.tests.test_canopy_light import inputs
from tools.tests.test_groimp_structure_export import fixture_snapshot
from tools.tests.test_ppfd_validation import point, reading, study_folder


def fixture(folder: Path) -> tuple[Path, Path]:
    run = fixture_snapshot(folder / 'source')
    backup = folder / 'source/backup.json'
    data = read_json(backup)
    data['capture'].update(capture_date='2026-10-01', plant_id='DT-001', coordinate_frame='board_mm')
    write_json(backup, data)
    hpath = run / 'DT-001/hierarchy/hierarchy.json'
    h = read_json(hpath); h['inputs']['backup_sha256'] = file_hash(backup); write_json(hpath, h)
    study = study_folder(folder / 'study', points=[point(300, 130, 0, case_id='plant', stage='plant', plant_id='DT-001')])
    inputs(folder / 'study')
    scene = read_json(study.parent / 'scene.json')
    scene['scenarios'] = []
    scene['fixtures'][0]['distribution']['half_intensity_half_angle_deg']['value'] = 45
    write_json(study.parent / 'scene.json', scene)
    geom = study.parent / 'geometry.csv'
    from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS
    surfaces = rows(geom)
    for r in surfaces:
        r['normal_convention'] = 'adaxial_ccw'
    write_rows(geom, surfaces, LEAF_SURFACES_CSV_COLUMNS)
    write_json(study.parent / 'review.json', dict(geometry_sha256=file_hash(geom), geometry_variant_id='v25',
        snapshot_date='2026-10-01', surface_kind='leaf_triangles', review_state='accepted', reviewer='synthetic tester',
        reviewed_at='2026-10-01T00:00:00+09:00', geometry_completeness='partial',
        validated_metric=False, suitable_for_ppfd=False))
    plan = read_json(study)
    plan['cases'] = [dict(case_id='plant', stage='plant', plant_id='DT-001', session_id='synthetic',
                         geometry_snapshot_date='2026-10-01', geometry='geometry.csv', geometry_variant_id='v25',
                         surface_review='review.json', data_kind='synthetic')]
    plan['sensitivity'] = {}
    write_json(study, plan)
    return run, study


def connect_fixture(folder: Path, **kwargs) -> tuple[Path, dict]:
    run, study = fixture(folder)
    out = folder / 'result'
    result = bridge.connect(run, 'DT-001', 'synthetic', study, out, **kwargs)
    return out, result


def test_preparation_uses_existing_gate_and_preserves_sources(tmp_path):
    out, result = connect_fixture(tmp_path)
    assert result['status'] == 'prepared'
    assert not result['validated_metric'] and result['source_files_unchanged']
    assert not (out / 'light/execution').exists()
    assert bridge.stale(out)['stale'] is False
    audit = read_json(out / 'input_audit.json')
    assert audit['geometry_counts'] == {'axis': 1, 'position': 2}
    assert audit['optical_triangle_count'] == 4
    assert audit['geometry_completeness'] == 'partial'
    assert read_json(out / 'light_summary.json')['absorbed_umol_s'] is None
    jobs = read_json(out / 'light/prepared/jobs.json')
    plant = next(c for c in jobs['cases'] if c['case_id'] == 'plant')
    assert plant['n_leaf_triangles'] == 4
    assert 'AreaLight' in (out / 'light/prepared/plant/leaves/Model.rgg').read_text()
    assert rows(out / 'surfaces.csv')[0]['source_photos'] == '["v1.png", "v2.png"]'
    for path, expected in result['source_hashes'].items():
        assert file_hash(Path(path)) == expected


def test_placement_uses_shared_transform_once(tmp_path):
    out, _ = connect_fixture(tmp_path)
    text = (out / 'report.html').read_text(encoding='utf-8')
    import json, re
    data = json.loads(re.search(r'const D = (.*);\n', text).group(1))
    # Board [-40,-40,100] plus fixture placement [300,200,0], yaw 0.
    assert data['vertices_grow_mm'][0][0] == [260, 160, 100]
    rgg = (out / 'light/prepared/plant/leaves/Model.rgg').read_text()
    assert '0.26' in rgg and '0.16' in rgg and '0.1' in rgg


@pytest.mark.parametrize('key,value', [('session_id', 'different'), ('plant_id', 'different'),
                                     ('geometry_snapshot_date', '2026-10-02')])
def test_case_identity_and_date_conflicts_fail(tmp_path, key, value):
    run, study = fixture(tmp_path)
    data = read_json(study); data['cases'][0][key] = value; write_json(study, data)
    with pytest.raises(StudyError, match='mismatch'):
        bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'result', case_id='plant')
    assert not (tmp_path / 'result').exists()


def test_missing_date_not_guessed_from_session_or_case(tmp_path):
    run, study = fixture(tmp_path)
    backup = tmp_path / 'source/backup.json'; b = read_json(backup); del b['capture']['capture_date']; write_json(backup, b)
    hp = run / 'DT-001/hierarchy/hierarchy.json'; h = read_json(hp); h['inputs']['backup_sha256'] = file_hash(backup); write_json(hp, h)
    out = tmp_path / 'result'
    result = bridge.connect(run, 'DT-001', 'synthetic', study, out)
    assert result['capture_date'] is None and result['status'] == 'blocked'
    assert 'capture_date_unavailable' in result['blockers']
    assert not (out / 'light').exists()


def test_missing_surface_and_light_export_blocker_report(tmp_path):
    run, study = fixture(tmp_path)
    data = read_json(study); data['scene'] = None; data['cases'][0]['geometry'] = 'missing.csv'; write_json(study, data)
    result = bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'result')
    assert result['status'] == 'blocked'
    summary = read_json(tmp_path / 'result/light_summary.json')
    assert summary['covered_area_mm2'] is None and summary['photosynthesis'] is None
    assert rows(tmp_path / 'result/surface_light_links.csv') == []


@pytest.mark.parametrize('change', ['foreign', 'duplicate', 'hash', 'review_date', 'unreviewed', 'normal'])
def test_bad_surface_tables_do_not_enter_transport(tmp_path, change):
    run, study = fixture(tmp_path)
    geom, review_path = study.parent / 'geometry.csv', study.parent / 'review.json'
    data, review = rows(geom), read_json(review_path)
    if change == 'foreign': data[0]['plant_id'] = 'OTHER'
    if change == 'duplicate': data.append(deepcopy(data[0]))
    if change == 'normal': data[0]['normal_convention'] = 'unknown'
    write_rows(geom, data, tuple(data[0]))
    review['geometry_sha256'] = 'bad' if change == 'hash' else file_hash(geom)
    if change == 'review_date': review['snapshot_date'] = '2026-10-02'
    if change == 'unreviewed': review['review_state'] = 'pending'
    write_json(review_path, review)
    if change in ('foreign', 'duplicate', 'hash', 'review_date'):
        with pytest.raises(ValueError): bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'result')
    else:
        result = bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'result')
        assert result['status'] == 'blocked' and not (tmp_path / 'result/light').exists()


def test_reading_date_mismatch_and_duplicate_cases_rejected(tmp_path):
    run, study = fixture(tmp_path)
    write_rows(study.parent / 'ppfd_readings.csv', [reading('plant', 'p', 1, 0, 'validation', stage='plant',
        plant_id='DT-001', session_id='synthetic', geometry_snapshot_date='2026-09-01')], pv.READING_COLUMNS)
    with pytest.raises(StudyError, match='Reading session/date'):
        bridge.audit(run, 'DT-001', 'synthetic', study)
    data = read_json(study); data['cases'].append(deepcopy(data['cases'][0])); write_json(study, data)
    with pytest.raises(StudyError, match='Duplicate'):
        bridge.audit(run, 'DT-001', 'synthetic', study)


def test_fresh_outputs_and_stale_geometry_and_review(tmp_path):
    out, _ = connect_fixture(tmp_path)
    run, study = tmp_path / 'source/run', tmp_path / 'study/study.json'
    with pytest.raises(StudyError, match='already exists'):
        bridge.connect(run, 'DT-001', 'synthetic', study, out)
    for path in [study.parent / 'geometry.csv', study.parent / 'review.json', out / 'light/prepared/plant/leaves/Model.rgg']:
        old = path.read_bytes(); path.write_bytes(old + b'\n')
        assert bridge.stale(out)['stale']
        path.write_bytes(old)
    assert not bridge.stale(out)['stale']
    with pytest.raises(StudyError, match='build'):
        bridge.connect(run, 'DT-001', 'synthetic', study, Path('C:/unrelated_bridge_output'))


def test_capture_hash_conflict_fails_before_output(tmp_path):
    run, study = fixture(tmp_path)
    structure = tmp_path / 'source/structure/structure.json'
    write_json(structure, dict(plant_id='DT-001', inputs=dict(capture=str(tmp_path / 'source/backup.json'), capture_sha256='bad')))
    with pytest.raises(StudyError, match='hash mismatch'):
        bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'out')
    assert not (tmp_path / 'out').exists()


def test_elevation_not_photo_numbers_and_no_default_centre():
    cap = dict(frames=[dict(image_file='27.png', rvec_rad=[0, 0, 0], tvec_mm=[0, 0, -100]),
                       dict(image_file='01.png', rvec_rad=[0, 0, 0], tvec_mm=[-100, 0, -30])])
    assert all(r['group'] is None for r in bridge.measured_views(cap, None))
    result = bridge.measured_views(cap, dict(centre_board_mm=[0, 0, 0], top_elevation_gt_deg=70, source='synthetic'))
    assert [r['group'] for r in result] == ['top', 'ring']
    assert result[0]['elevation_deg'] == 90


def test_movement_groups_are_preserved_and_unaligned_group_blocks(tmp_path):
    run, study = fixture(tmp_path)
    metadata = tmp_path / 'metadata.json'
    groups = [dict(group_id='A', alignment_status='reference', included_in_optical_scene=True),
              dict(group_id='B2', alignment_status='failed', included_in_optical_scene=True)]
    write_json(metadata, dict(plant_id='DT-001', session_id='synthetic', movement=dict(groups=groups)))
    result = bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'out', metadata=metadata)
    assert 'unaligned_movement_group' in result['blockers']
    assert read_json(tmp_path / 'out/input_audit.json')['movement']['groups'] == groups


def test_area_weighted_flux_invariant_to_mesh_subdivision():
    a = dict(area_mm2=100, received_both_faces_umol_s=.02, absorbed_umol_s=.01)
    b = dict(area_mm2=300, received_both_faces_umol_s=.12, absorbed_umol_s=.06)
    one = bridge.aggregate_light([a, b], 3600, 'partial')
    split = [{k: v / 10 for k, v in b.items()} for _ in range(10)]
    many = bridge.aggregate_light([a, *split], 3600, 'partial')
    assert one['received_both_faces_area_weighted_umol_m2_s'] == pytest.approx(350)
    assert many['received_both_faces_area_weighted_umol_m2_s'] == pytest.approx(350)
    assert one['absorbed_mmol_d'] == pytest.approx(.252)
    assert one['whole_plant_absorbed_umol_s'] is None
    assert bridge.aggregate_light([a], None, 'partial')['received_both_faces_dli_mol_m2_d'] is None


def test_schedule_missing_dimmed_or_different_stays_unavailable(tmp_path):
    _, study = fixture(tmp_path)
    path = study.parent / 'scene.json'; scene = read_json(path)
    assert bridge.constant_light_seconds(path) > 0
    scene['fixtures'][0]['schedule'] = []; write_json(path, scene)
    assert bridge.constant_light_seconds(path) is None
    scene['fixtures'][0]['schedule'] = [dict(start_hhmm='08:00', end_hhmm='20:00', output_fraction=.5)]
    write_json(path, scene)
    assert bridge.constant_light_seconds(path) is None


def test_result_table_identity_and_missing_flux_are_not_guessed(tmp_path):
    out, _ = connect_fixture(tmp_path)
    audit = read_json(out / 'input_audit.json')
    values = []
    for s in audit['surfaces']:
        values.append(dict(case_id='plant', **{k:s[k] for k in ('surface_id','plant_id','session_id','organ_id','leaflet_id','triangle_id','area_mm2')},
                           received_both_faces_umol_s=.01, absorbed_umol_s=.005,
                           received_both_faces_per_one_sided_area_umol_m2_s=3.125, absorbed_per_one_sided_area_umol_m2_s=1.5625))
    path = out / 'light/leaf_triangle_light.csv'
    write_rows(path, values, tuple(values[0]))
    summary, linked = bridge.result_tables(audit, out / 'light', out)
    assert len(linked) == 4 and summary['absorbed_umol_s'] == .02
    assert not summary['validated_metric'] and summary['whole_plant_absorbed_umol_s'] is None
    values[0]['session_id'] = 'foreign'; write_rows(path, values, tuple(values[0]))
    with pytest.raises(StudyError, match='identity mismatch'):
        bridge.result_tables(audit, out / 'light', out)


def test_report_escapes_source_strings(tmp_path):
    out, _ = connect_fixture(tmp_path)
    a = read_json(out / 'input_audit.json'); a['blockers'] = ['</script><script>alert(1)</script>']
    bridge.report(out, a, 'blocked', {}, [])
    text = (out / 'report.html').read_text(encoding='utf-8')
    assert '</script><script>alert(1)' not in text
    assert '\\u003c/script\\u003e' in text
    assert 'textContent' in text


def test_existing_site_link_requires_matching_fresh_result(tmp_path):
    from tools.plant_site import light_panel
    out, _ = connect_fixture(tmp_path)
    run = tmp_path / 'source/run'
    panel = light_panel(run, out, tmp_path / 'linked.html')
    assert 'result/report.html' in panel
    with pytest.raises(StudyError, match='another'):
        light_panel(tmp_path / 'other', out, tmp_path / 'linked.html')
    (out / 'surfaces.csv').write_text('changed')
    with pytest.raises(StudyError, match='stale'):
        light_panel(run, out, tmp_path / 'linked.html')


def test_fixed_seed_preparation_is_reproducible_without_execution(tmp_path):
    out, _ = connect_fixture(tmp_path)
    second = tmp_path / 'second'
    bridge.connect(tmp_path / 'source/run', 'DT-001', 'synthetic', tmp_path / 'study/study.json', second)
    for p in (out / 'light/prepared').rglob('Model.rgg'):
        assert p.read_bytes() == (second / 'light/prepared' / p.relative_to(out / 'light/prepared')).read_bytes()


def test_execution_budget_is_enforced_without_running_native_jobs(tmp_path, monkeypatch):
    run, study = fixture(tmp_path)
    called = []
    monkeypatch.setattr(pv, 'density_execute', lambda *args: called.append(args))
    with pytest.raises(StudyError, match='exceeds declared limit'):
        bridge.connect(run, 'DT-001', 'synthetic', study, tmp_path / 'out', execute=True)
    assert not called


def test_foreign_plant_cases_are_not_executed_or_joined(tmp_path):
    run, study = fixture(tmp_path)
    plan = read_json(study); other = deepcopy(plan['cases'][0]); other.update(case_id='other', plant_id='OTHER', session_id='other')
    plan['cases'].append(other); write_json(study, plan)
    out = tmp_path / 'out'; result = bridge.connect(run, 'DT-001', 'synthetic', study, out)
    assert result['status'] == 'prepared'
    assert [c['case_id'] for c in read_json(out / 'inputs/scoped_study.json')['cases']] == ['plant']


def test_date_mapping_needs_verified_evidence(tmp_path):
    run, study = fixture(tmp_path)
    meta = tmp_path / 'meta.json'
    write_json(meta, dict(plant_id='DT-001', session_id='synthetic', capture_date='2026-10-01'))
    with pytest.raises(StudyError, match='source_hashes'):
        bridge.audit(run, 'DT-001', 'synthetic', study, metadata_path=meta)
    data = read_json(meta); data['source_hashes'] = {str(study): file_hash(study)}; write_json(meta, data)
    assert bridge.audit(run, 'DT-001', 'synthetic', study, metadata_path=meta)['capture_date'] == '2026-10-01'


def test_duplicate_sensor_records_are_rejected(tmp_path):
    run, study = fixture(tmp_path)
    path = study.parent / 'sensors.csv'; records = rows(path)
    write_rows(path, records * 2, pv.SENSOR_COLUMNS)
    with pytest.raises(StudyError, match='Duplicate sensor'):
        bridge.audit(run, 'DT-001', 'synthetic', study)


def test_existing_collector_and_comparison_are_connected_with_fixture_logs(tmp_path, monkeypatch):
    """Exercise the execute branch without Java or simulated physical claims."""
    run, study = fixture(tmp_path)
    plan = read_json(study); plan['solver']['max_local_native_jobs'] = 3; write_json(study, plan)

    def fixture_execute(prepared, execution, *_):
        execution.mkdir(); jobs = read_json(prepared / 'jobs.json'); records = []
        for case in jobs['cases']:
            specs = read_json(prepared / case['case_id'] / 'job_specs.json')
            for job in specs['specs']:
                target = execution / case['case_id'] / job['job']; target.mkdir(parents=True)
                lines = []
                if job['job'] == 'leaves':
                    lines = [f'LEAF\t{r["surface_id"]}\t0.01\t0.005' for r in rows(prepared / case['case_id'] / 'triangles.csv')]
                for probe in job['probes']:
                    lines.append(f'PROBE\t{probe["point_id"]}:0\t0.01')
                log = target / 'groimp.log'; log.write_text('\n'.join(lines + ['SANITY_DONE']))
                records.append(dict(case_id=case['case_id'], job=job['job'], status='completed', log_sha256=file_hash(log)))
        write_json(execution / 'execution.json', dict(jobs_sha256=file_hash(prepared / 'jobs.json'), runs=records))

    monkeypatch.setattr(pv, 'density_execute', fixture_execute)
    out = tmp_path / 'out'
    result = bridge.connect(run, 'DT-001', 'synthetic', study, out, execute=True)
    assert result['status'] == 'native_completed_physical_validation_pending'
    assert len(rows(out / 'surface_light_links.csv')) == 4
    sensors = rows(out / 'sensor_light_links.csv')
    assert len(sensors) == 1 and sensors[0]['session_id'] == 'synthetic'
    assert sensors[0]['solver_jobs_sha256'] == file_hash(out / 'light/prepared/jobs.json')
    assert sensors[0]['predicted_ppfd_umol_m2_s'] == 'unavailable'  # assumed lamp values
    assert read_json(out / 'light/comparison.json')['status'] == 'unavailable'
    assert bridge.stale(out)['stale'] is False


def test_explicit_linked_growth_capture_date_and_conflicts(tmp_path):
    run, study = fixture(tmp_path)
    growth = tmp_path / 'source/growth.json'
    write_json(growth, dict(plant_id='DT-001', capture_date='2026-10-01'))
    structure = tmp_path / 'source/structure/structure.json'
    write_json(structure, dict(plant_id='DT-001', inputs=dict(growth=str(growth))))
    result = bridge.audit(run, 'DT-001', 'synthetic', study)
    assert result['capture_date_evidence'] == [dict(source=str(growth), capture_date='2026-10-01')]
    write_json(growth, dict(plant_id='DT-001', capture_date='2026-10-02'))
    with pytest.raises(StudyError, match='Conflicting capture dates'):
        bridge.audit(run, 'DT-001', 'synthetic', study)


def test_source_photo_hashes_and_no_copying_large_media(tmp_path):
    run, study = fixture(tmp_path)
    backup = tmp_path / 'source/backup.json'; data = read_json(backup)
    photo = tmp_path / 'source/photo.png'; photo.write_bytes(b'test photo bytes')
    data['capture']['frames'] = [dict(image_file='photo.png', image_path=str(photo), sha256=file_hash(photo))]
    write_json(backup, data)
    hierarchy = run / 'DT-001/hierarchy/hierarchy.json'; h = read_json(hierarchy)
    h['inputs']['backup_sha256'] = file_hash(backup); write_json(hierarchy, h)
    out = tmp_path / 'out'; result = bridge.connect(run, 'DT-001', 'synthetic', study, out)
    assert str(photo) in result['media_hashes'] and str(photo) not in result['frozen_inputs']
    photo.write_bytes(b'changed')
    assert bridge.stale(out)['stale']
    with pytest.raises(StudyError, match='image hash mismatch'):
        bridge.audit(run, 'DT-001', 'synthetic', study)
