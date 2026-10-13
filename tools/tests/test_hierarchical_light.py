"""Hierarchy accounting and transport tests with explicit artificial optical geometry."""
from copy import deepcopy
from pathlib import Path

import numpy as np
import pytest

from tools import hierarchical_light as h
from tools.hierarchical_light_demo import synthetic_inputs
from tools.leaf_light.common import StudyError, file_hash, read_json, rows, write_json, write_rows


def run_case(folder, groups=('A', 'B', 'C'), tau=.1, subdivisions=2):
    source = synthetic_inputs(folder / 'inputs', groups, tau, subdivisions)
    manifest = h.prepare_subset_cases(source, folder / 'prepared')
    assert manifest['status'] == 'prepared', manifest['audit']
    result = h.calculate_direct(folder / 'prepared', folder / 'results')
    return source, manifest, result


def target_row(result, quantity='received'):
    return next(r for r in result['tables']['leaflet_interactions']
                if r['leaflet_id'] == 'target' and r['fixture_id'] == 'all' and r['quantity'] == quantity)


def rewrite_geometry(source, records):
    path = source.parent / 'leaf_surfaces.csv'
    write_rows(path, records, tuple(records[0]))
    rp = source.parent / 'review.json'; review = read_json(rp)
    review['geometry_sha256'] = file_hash(path); write_json(rp, review)


def test_empty_other_tissue(tmp_path):
    _, manifest, result = run_case(tmp_path, ())
    r = target_row(result)
    assert r['full_umol_s'] > 0
    assert r['total_loss_umol_s'] == 0
    assert all(r[f'shapley_{g}_umol_s'] == 0 for g in h.BITS)
    assert len(result['tables']['interaction_cases']) == 16
    assert h.stale(tmp_path / 'results')['stale'] is False


@pytest.mark.parametrize('group', ['A', 'B', 'C'])
def test_only_one_category(tmp_path, group):
    _, _, result = run_case(tmp_path, (group,))
    r = target_row(result)
    assert r['full_umol_s'] / r['baseline_umol_s'] == pytest.approx(.1)
    for g in h.BITS:
        assert r[f'shapley_{g}_umol_s'] == pytest.approx(r['total_loss_umol_s'] if g == group else 0, abs=1e-14)


def test_layers_and_weighted_accounting(tmp_path):
    _, _, result = run_case(tmp_path)
    r = target_row(result)
    assert r['full_umol_s'] / r['baseline_umol_s'] == pytest.approx(.001)
    assert sum(r[f'shapley_{g}_umol_s'] for g in h.BITS) == pytest.approx(r['total_loss_umol_s'])
    assert sum(r[f'overlap_{s}_umol_s'] for s in h.SUBSETS[1:]) == pytest.approx(r['total_loss_umol_s'])
    absorbed = target_row(result, 'absorbed')
    assert absorbed['full_umol_s'] == pytest.approx(.9 * r['full_umol_s'])
    plants = [r for r in result['tables']['plant_interactions'] if r['quantity'] == 'received' and r['fixture_id'] == 'all']
    leaf = [r for r in result['tables']['leaflet_interactions'] if r['quantity'] == 'received' and r['fixture_id'] == 'all']
    for p in plants:
        same = [r for r in leaf if r['plant_instance_id'] == p['plant_instance_id']]
        assert p['full_umol_m2_s'] == pytest.approx(sum(r['full_umol_s'] for r in same) / sum(r['area_m2'] for r in same))
        assert p['loss_fraction'] == pytest.approx(sum(r['total_loss_umol_s'] for r in same) / sum(r['baseline_umol_s'] for r in same))


def test_redundant_opaque_shadows(tmp_path):
    _, _, result = run_case(tmp_path, ('A', 'B'), 0.)
    r = target_row(result)
    assert r['standalone_A_umol_s'] + r['standalone_B_umol_s'] == pytest.approx(2 * r['total_loss_umol_s'])
    assert r['overlap_AB_umol_s'] == pytest.approx(-r['total_loss_umol_s'])
    assert r['shapley_A_umol_s'] == pytest.approx(r['total_loss_umol_s'] / 2)
    assert r['shapley_B_umol_s'] == pytest.approx(r['shapley_A_umol_s'])
    assert r['marginal_A_umol_s'] == 0


def test_algebra_negative_gain_missing_and_zero_baseline():
    q = {s: 10. + mask for mask, s in enumerate(h.SUBSETS)}
    r = h.attribution(q)
    assert r['total_loss_umol_s'] == -7
    assert [r[f'shapley_{g}_umol_s'] for g in h.BITS] == pytest.approx([-1, -2, -4])
    assert h.attribution({s: 0. for s in h.SUBSETS})['loss_fraction'] is None
    q['AB'] = None
    r = h.attribution(q)
    assert r['total_loss_umol_s'] == -7 and r['shapley_A_umol_s'] is None


def test_receiver_remapping_and_full_scene_equivalence(tmp_path):
    from tomato3d.light.raytrace import direct_light
    _, manifest, result = run_case(tmp_path)
    context = h.load_context(tmp_path / 'prepared', manifest)
    target = next(t for t in context.targets.values() if t['leaflet_id'] == 'target')
    assert min(target['triangles']) > 0
    receivers, occluders, active = h.filtered_transport(context, target['triangles'])
    assert set(receivers.own_triangle) == {0, 1}
    assert len(occluders.vertices_grow_mm) == 2
    raw = direct_light(context.receivers, context.resolved.fixtures, context.occluders,
                       context.resolved.scene.leaf_optics.transmittance.value, context.resolved.scene.simulation)
    select = np.isin(context.receivers.own_triangle, target['triangles'])
    flux = np.sum(raw.ppfd_umol_m2_s[0, select] * context.weights_m2[select])
    assert target_row(result)['full_umol_s'] == pytest.approx(flux)


def test_shared_edge_counts_one_leaf_and_separate_leaves_count_twice():
    from tomato3d.light.raytrace import Occluders, count_crossings
    tris = np.array([[[-1,-1,1],[1,-1,1],[1,1,1]],[[-1,-1,1],[1,1,1],[-1,1,1]]], float)
    o = Occluders(tris, np.array([True,True]), np.array([0,0]), np.array([0,0]))
    rays = np.array([[0,0,2.]], float)
    count, blocked = count_crossings(np.array([[0,0,0.]]), rays, np.array([-1]), o, 2)
    assert count.tolist() == [1] and not blocked.any()
    two = Occluders(np.concatenate([tris, tris + [0,0,.5]]), np.ones(4, bool), np.array([0,0,1,1]), np.zeros(4, int))
    count, _ = count_crossings(np.array([[0,0,0.]]), rays, np.array([-1]), two, 2)
    assert count.tolist() == [2]


def test_unknown_membership_preserves_total(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs')
    mp = source.parent / 'membership.csv'; records = rows(mp)
    records[0]['identity_status'] = 'pending'; write_rows(mp, records, h.MEMBERSHIP)
    audit = h.audit_inputs(source)
    assert audit['transport_ready'] and not audit['hierarchy_ready']
    h.prepare_subset_cases(source, tmp_path / 'prepared')
    result = h.calculate_direct(tmp_path / 'prepared', tmp_path / 'results')
    r = target_row(result)
    assert r['total_loss_umol_s'] > 0 and r['shapley_A_umol_s'] is None


@pytest.mark.parametrize('change', ['identity_hash', 'duplicate_member', 'foreign_session', 'foreign_plant', 'duplicate_face', 'unreviewed', 'mixed_date', 'copied_observed'])
def test_conflicting_inputs_block(tmp_path, change):
    source = synthetic_inputs(tmp_path / 'inputs'); plan = read_json(source)
    mp = source.parent / 'membership.csv'; members = rows(mp)
    if change == 'identity_hash': members[0]['evidence_sha256'] = 'bad'
    if change == 'duplicate_member': members.append(deepcopy(members[0]))
    if change == 'foreign_session': members[0]['session_id'] = 'other'
    if change == 'foreign_plant': plan['case']['instances'] = plan['case']['instances'][:1]
    if change == 'duplicate_face':
        geometry = rows(source.parent / 'leaf_surfaces.csv'); extra = deepcopy(geometry[0]); extra['triangle_id'] = 'different'; geometry.append(extra); rewrite_geometry(source, geometry)
    if change == 'unreviewed':
        rp = source.parent / 'review.json'; review = read_json(rp); review['review_state'] = 'pending'; write_json(rp, review)
    if change in ('mixed_date', 'copied_observed'):
        plan['case']['data_kind'] = 'observed_geometry'
        if change == 'mixed_date': plan['case']['instances'][1]['capture_date'] = '2026-10-02'
        else: plan['case']['instances'][0]['plant_id'] = 'COPY'
    write_rows(mp, members, h.MEMBERSHIP); write_json(source, plan)
    assert not h.audit_inputs(source)['transport_ready']


@pytest.mark.parametrize('name', ['membership.csv', 'leaf_surfaces.csv', 'scene.json', 'identity_evidence.json'])
def test_stale_source(tmp_path, name):
    source, _, _ = run_case(tmp_path)
    p = source.parent / name; p.write_bytes(p.read_bytes() + b'\n')
    assert h.stale(tmp_path / 'prepared')['stale']
    with pytest.raises(StudyError, match='stale'):
        h.calculate_direct(tmp_path / 'prepared', tmp_path / 'new_results')


@pytest.mark.parametrize('parameter', ['transmittance', 'absorptance', 'photon_flux_umol_s'])
def test_missing_optics_and_fixture(tmp_path, parameter):
    source = synthetic_inputs(tmp_path / 'inputs')
    sp = source.parent / 'scene.json'; scene = read_json(sp)
    obj = scene['fixtures'][0] if parameter == 'photon_flux_umol_s' else scene['leaf_optics']
    obj[parameter] = dict(value=None, status='unavailable', source='not measured')
    write_json(sp, scene)
    h.prepare_subset_cases(source, tmp_path / 'prepared')
    result = h.calculate_direct(tmp_path / 'prepared', tmp_path / 'results')
    r = target_row(result)
    if parameter == 'transmittance':
        assert r['baseline_umol_s'] is not None and r['full_umol_s'] is None
    elif parameter == 'absorptance':
        assert r['full_umol_s'] is not None and target_row(result, 'absorbed')['full_umol_s'] is None
    else:
        assert r['baseline_umol_s'] is None


def test_directed_nonadditive_matrix(tmp_path):
    _, _, result = run_case(tmp_path, ('A','B'), 0.)
    matrix = [r for r in result['tables']['source_target_interactions'] if r['level'] == 'leaflet' and r['quantity'] == 'received']
    to_target = [r for r in matrix if r['target_label'].endswith('/target') and r['source_id'] != r['target_id']]
    assert sum(r['effect_umol_s'] for r in to_target) == 0
    assert target_row(result)['total_loss_umol_s'] > 0
    assert all(not r['additive'] for r in matrix)
    assert all(r['effect_umol_s'] is None for r in matrix if r['source_id'] == r['target_id'])
    assert any(r['effect_umol_s'] > 0 for r in matrix if r['effect_umol_s'] is not None)


def test_native_preparation_and_opt_in(tmp_path):
    from tools.hierarchical_light_native import execute_native
    source = synthetic_inputs(tmp_path / 'inputs')
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared', 'native')
    assert manifest['status'] == 'prepared', manifest.get('native_blockers')
    assert not (tmp_path / 'execution').exists()
    result = execute_native(tmp_path / 'prepared', tmp_path / 'execution', False, 'java', None)
    assert result['status'] == 'not_executed'
    jobs = read_json(tmp_path / 'prepared/jobs.json')
    assert sum(len(c['jobs']) for c in jobs['cases']) == manifest['native_cost']['jobs']
    case = next(c for c in manifest['cases'] if len(c['retained']) == 2)
    model = tmp_path / 'prepared' / case['case_id'] / 'replicate_0000/Model.rgg'
    text = model.read_text()
    assert 'AreaLight' in text and text.count('[LeafSurface(') == 2
    assert 'setSeed(3103)' in text or '3103' in text
    model.write_text(text + '\n')
    with pytest.raises(StudyError):
        execute_native(tmp_path / 'prepared', tmp_path / 'execution', True, 'java', None)


def test_native_budgets_and_unsupported_fixture(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs'); p = read_json(source)
    p['native']['max_jobs'] = 1; write_json(source, p)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared', 'native')
    assert manifest['status'] == 'blocked' and 'native_budget_exceeded' in manifest['native_blockers']


def test_prepare_does_not_mutate_sources_and_cost_limit(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs'); before = {p: file_hash(p) for p in source.parent.iterdir()}
    h.prepare_subset_cases(source, tmp_path / 'prepared')
    assert before == {p: file_hash(p) for p in source.parent.iterdir()}
    p = read_json(source); p['limits']['max_transport_calls'] = 1; write_json(source, p)
    with pytest.raises(StudyError, match='budget'):
        h.prepare_subset_cases(source, tmp_path / 'limited')


def test_own_leaf_fold_is_retained_in_baseline(tmp_path):
    from tomato3d.light.raytrace import direct_light
    source = synthetic_inputs(tmp_path / 'inputs', ('A',), 0.)
    geometry = rows(source.parent / 'leaf_surfaces.csv')
    for r in geometry:
        r['organ_id'] = r['leaflet_id'] = 'target'
    rewrite_geometry(source, geometry)
    mp = source.parent / 'membership.csv'; members = [r for r in rows(mp) if r['leaflet_id'] == 'target']
    write_rows(mp, members, h.MEMBERSHIP)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared')
    context = h.load_context(tmp_path / 'prepared', manifest)
    result = h.calculate_direct(tmp_path / 'prepared', tmp_path / 'results')
    r = target_row(result)
    raw = direct_light(context.receivers, context.resolved.fixtures, context.occluders, 0., context.resolved.scene.simulation)
    unshaded = float(np.sum(raw.unoccluded_ppfd_umol_m2_s[0] * context.weights_m2))
    assert r['baseline_umol_s'] < unshaded
    assert r['baseline_umol_s'] == pytest.approx(r['full_umol_s'])
    assert r['total_loss_umol_s'] == 0


def test_partial_shadow_converges_with_area_sampling(tmp_path):
    ratios = []
    for n in (12, 40):
        folder = tmp_path / str(n)
        source = synthetic_inputs(folder / 'inputs', ('A',), 0., n)
        geometry = rows(source.parent / 'leaf_surfaces.csv')
        for r in geometry:
            if r['leaflet_id'] == 'A':
                for vertex in range(3):
                    if float(r[f'v{vertex}_x_mm']) > 0:
                        r[f'v{vertex}_x_mm'] = 2.4
        rewrite_geometry(source, geometry)
        h.prepare_subset_cases(source, folder / 'prepared')
        result = h.calculate_direct(folder / 'prepared', folder / 'results')
        r = target_row(result); ratios.append(r['full_umol_s'] / r['baseline_umol_s'])
    # At z=200 mm the ray footprint is 0.8 times the target x extent.
    # A plate ending at x=2.4 mm covers 65% of the 20 mm target width.
    assert ratios[-1] == pytest.approx(.35, abs=.004)
    assert abs(ratios[-1] - ratios[0]) < .02


def test_group_permutation_preserves_allocations():
    original = {s: float(100 - i*i) for i, s in enumerate(h.SUBSETS)}
    perm = {h.SUBSETS[((i & 1) << 2) | (i & 2) | ((i & 4) >> 2)]: value
            for i, value in enumerate(original.values())}
    first, second = h.attribution(original), h.attribution(perm)
    assert first['shapley_A_umol_s'] == pytest.approx(second['shapley_C_umol_s'])
    assert first['shapley_B_umol_s'] == pytest.approx(second['shapley_B_umol_s'])


def test_cross_plant_reused_leaflet_ids_are_distinct(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs', ('C',))
    geom = rows(source.parent / 'leaf_surfaces.csv')
    for r in geom:
        r['organ_id'] = r['leaflet_id'] = 'shared'
    rewrite_geometry(source, geom)
    mp = source.parent / 'membership.csv'; members = rows(mp)
    for r in members: r['organ_id'] = r['leaflet_id'] = 'shared'
    write_rows(mp, members, h.MEMBERSHIP)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared')
    context = h.load_context(tmp_path / 'prepared', manifest)
    assert len(context.targets) == 2 and len(set(context.occluders.surface_code)) == 2
    result = h.calculate_direct(tmp_path / 'prepared', tmp_path / 'results')
    r = next(r for r in result['tables']['leaflet_interactions'] if r['plant_instance_id'] == 'P1' and r['fixture_id'] == 'all' and r['quantity'] == 'received')
    assert r['full_umol_s'] / r['baseline_umol_s'] == pytest.approx(.1)


def test_copied_hypothetical_instances_keep_identity(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs', ())
    geom = rows(source.parent / 'leaf_surfaces.csv')
    for r in geom: r['geometry_source'] = 'manual'
    rewrite_geometry(source, geom)
    plan = read_json(source); plan['case']['data_kind'] = 'hypothetical_layout'
    instance = deepcopy(plan['case']['instances'][0]); instance['plant_id'] = 'COPY'
    instance['placement'] = deepcopy(read_json(source.parent / 'scene.json')['plants'][0])
    instance['placement']['board_origin_grow_mm']['value'] = [50., 0., 0.]
    plan['case']['instances'].append(instance); write_json(source, plan)
    mp = source.parent / 'membership.csv'; members = rows(mp); members[0]['identity_status'] = 'reviewed'
    copy = deepcopy(members[0]); copy['plant_instance_id'] = 'COPY'; members.append(copy)
    write_rows(mp, members, h.MEMBERSHIP)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared')
    assert manifest['status'] == 'prepared', manifest['audit']
    assert {t['plant_instance_id'] for t in manifest['targets'].values()} == {'P1','COPY'}
    assert {t['source_plant_id'] for t in manifest['targets'].values()} == {'P1'}


def fake_native_execution(prepared, folder, manifest, omit=False):
    folder.mkdir()
    records = []
    for case in manifest['cases']:
        for index, _ in enumerate(manifest['plan']['native']['seeds']):
            name = f'replicate_{index:04d}'
            if omit and case['case_id'] == manifest['full_case'] and index == 1:
                continue
            job = folder / case['case_id'] / name; job.mkdir(parents=True)
            # Synthetic parser fixture with a signed gain when more surfaces are present.
            received = (1 + len(case['retained'])) * (index + 1.)
            text = ''.join(f'LEAF\tt{i:07d}\t{received}\t{received*.5}\n' for i in case['retained']) + 'SANITY_DONE\n'
            log = job / 'groimp.log'; log.write_text(text)
            records.append(dict(case_id=case['case_id'], job=name, status='completed', log_sha256=file_hash(log)))
    write_json(folder / 'execution.json', dict(prepared=str(prepared.resolve()), jobs_sha256=file_hash(prepared / 'jobs.json'), runs=records))


@pytest.mark.parametrize('omit', [False, True])
def test_native_collection_pairing_and_failed_jobs(tmp_path, omit):
    from tools.hierarchical_light_native import collect_native
    source = synthetic_inputs(tmp_path / 'inputs', ('A', 'B'))
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared', 'native')
    fake_native_execution(tmp_path / 'prepared', tmp_path / 'execution', manifest, omit)
    result = collect_native(tmp_path / 'prepared', tmp_path / 'execution', tmp_path / 'results')
    assert target_row(result)['total_loss_umol_s'] < 0
    summary = next(r for r in result['tables']['replicate_summary'] if r['table'] == 'leaflet_interactions' and r.get('leaflet_id') == 'target' and r['quantity'] == 'received' and r['metric'] == 'total_loss_umol_s')
    if omit:
        assert result['manifest']['native_failures'] and summary['mean'] is None
    else:
        r = target_row(result)
        assert summary['mean'] == pytest.approx(r['total_loss_umol_s'] * 1.5)
        assert summary['paired_replicate_standard_error'] == pytest.approx(abs(r['total_loss_umol_s']) / 2)
    assert not h.stale(tmp_path / 'results')['stale']


def test_native_unsupported_optics_and_stale_rgg(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs')
    sp = source.parent / 'scene.json'; scene = read_json(sp)
    scene['fixtures'][0]['distribution']['cutoff_half_angle_deg'] = 70
    write_json(sp, scene)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared', 'native')
    assert manifest['status'] == 'blocked'
    assert any('unsupported_fixture' in b for b in manifest['native_blockers'])


def test_fixed_background_is_present_in_all_counterfactuals(tmp_path):
    from tools.ppfd_validation import RIG_SURFACE_COLUMNS
    source = synthetic_inputs(tmp_path / 'inputs', ())
    background = {key: '' for key in RIG_SURFACE_COLUMNS}
    background.update(surface_id='fixed_plate', kind='shelf', role='physical_occluder',
        center_x_mm=0, center_y_mm=0, center_z_mm=500, normal_x=0, normal_y=0, normal_z=1,
        width_axis_x=1, width_axis_y=0, width_axis_z=0, width_mm=100, height_mm=100,
        reflectance=0, transmittance=0, geometry_status='assumed', geometry_source='synthetic plate',
        optics_status='assumed', optics_source='synthetic opaque')
    write_rows(source.parent / 'background.csv', [background], RIG_SURFACE_COLUMNS)
    plan = read_json(source); plan['background_csv'] = 'background.csv'; write_json(source, plan)
    h.prepare_subset_cases(source, tmp_path / 'prepared')
    result = h.calculate_direct(tmp_path / 'prepared', tmp_path / 'results')
    r = target_row(result)
    assert r['baseline_umol_s'] == r['full_umol_s'] == r['total_loss_umol_s'] == 0
    assert r['loss_fraction'] is None


def test_scene_override_is_audited_and_applied_once(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs', ())
    plan = read_json(source)
    plan['case']['scenarios'] = [dict(scenario_id='moved', description='synthetic placement',
        placement_overrides=[dict(plant_id='P1', board_origin_grow_mm=[40,0,0])])]
    plan['scenario_id'] = 'moved'; write_json(source, plan)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared')
    assert manifest['audit']['resolved_placements']['P1']['board_origin_grow_mm']['value'] == [40,0,0]
    context = h.load_context(tmp_path / 'prepared', manifest)
    assert context.vertices[0,0,0] == 30


def test_missing_alpha_has_explicit_attribution_reason(tmp_path):
    _, _, result = run_case(tmp_path, ())
    raw = deepcopy(result['tables']['interaction_cases'])
    for row in raw: row['absorbed_umol_s'] = None
    records = h.attribute_groups(raw, result['manifest']['targets'])
    assert all(r['reason'] == 'transport_or_optics_unavailable' for r in records if r['quantity'] == 'absorbed')


def test_receiver_and_source_filters_preserve_scene_and_report_selection(tmp_path):
    source = synthetic_inputs(tmp_path / 'inputs')
    plan = read_json(source)
    tid = h.token(('P1', 'synthetic_session', 'target', 'target'))
    source_id = h.token(['plant', ['P2']])
    plan['target_ids'] = [tid]; plan['source_entity_ids'] = [source_id]; write_json(source, plan)
    manifest = h.prepare_subset_cases(source, tmp_path / 'prepared')
    result = h.calculate_direct(tmp_path / 'prepared', tmp_path / 'results')
    assert len(manifest['targets']) == 4 and manifest['selected_targets'] == [tid]
    assert target_row(result)['full_umol_s'] / target_row(result)['baseline_umol_s'] == pytest.approx(.001)
    matrix = result['tables']['source_target_interactions']
    assert {r['source_id'] for r in matrix} == {source_id}
    assert all(r['target_selection'] == 'selected_leaflets_only' and r['n_receiver_leaflets'] == 1 for r in matrix)
