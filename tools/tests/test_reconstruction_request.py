"""JSON references for the three-route calculator: resolution, findings, counts and unique observations.

The reference layer must consult human and capture records without changing them, report every
unusable reference before anything is calculated, count an observation once however many routes
reach it, and leave the geometry identical whatever route the reviewer navigated.
"""
import json

import pytest

from tools import rebuild_leaf_edit_session as tool
from tools import reconstruction_request as ref
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)

GROWTH = dict(plant_id='P', capture_date='2026-09-20', compound_leaf_count=3,
              compound_leaves=[dict(compound_leaf_id='L01', leaflet_count=8, is_unfolding=False),
                               dict(compound_leaf_id='L02', leaflet_count=2, is_unfolding=False),
                               dict(compound_leaf_id='L03', leaflet_count=None, is_unfolding=None)],
              growth_shoot_count=3, truss_count=0)


def capture_with(codes):
    return dict(plant_id='P', session_id='S', frames=[
        dict(image_file=f'p_{code}.png', view_code=code,
             observed_view_group='top' if code in ('01', '03') else 'oblique' if code[0] == '2' else 'side',
             pose_status='solved' if code in posed else 'failed',
             passes_pose_gate=False)
        for code, posed in [(c, p) for c, p in codes]])


CODES = [('01', ('01', '03', '21')), ('03', ('01', '03', '21')), ('21', ('01', '03', '21')),
         ('11', ('01', '03', '21')), ('22', ('01', '03', '21')), ('12', ('01', '03', '21'))]
CAPTURE = capture_with(CODES)


def observation(leaflet, point_id, image, x=100., y=200., **extra):
    row = dict(plant_id='P', session_id='S', organ_id='L01', leaflet_id=leaflet, viewer_leaflet_id=leaflet,
               point_id=point_id, image_file=image, x_px=x, y_px=y, point_kind='boundary',
               point_semantic_name=None, view_visibility='full', identity_review='confirmed')
    row.update(extra)
    return row


# ----------------------------------------------------------------------------------------------
# The request manifest
# ----------------------------------------------------------------------------------------------

@pytest.fixture
def manifest(tmp_path, monkeypatch):
    """A request written beside the inputs it names, as the CLI writes one."""
    monkeypatch.setattr(common, 'BUILD', tmp_path / 'build')
    session = tmp_path / 'inputs' / 'edit_session'
    session.mkdir(parents=True)
    common.write_json(session / 'capture.json', CAPTURE)
    common.write_json(session / 'intrinsics.json', dict(camera_id='test'))
    common.write_json(session / 'seed.backup.json', dict(plant_id='P'))
    common.write_json(tmp_path / 'inputs' / 'growth.json', GROWTH)
    common.write_json(tmp_path / 'inputs' / 'backup.json', dict(plant_id='P', variants={}))
    common.write_json(tmp_path / 'inputs' / 'annotations.json', dict(leaflets=[]))
    out = tmp_path / 'requests' / 'request.json'
    ref.write_request(out, 'P', 'S', tmp_path / 'inputs' / 'growth.json', session,
                      tmp_path / 'inputs' / 'backup.json', tmp_path / 'inputs' / 'annotations.json',
                      tmp_path / 'build' / 'result', capture_date='2026-09-20')
    return out, tmp_path


def test_paths_resolve_against_the_manifest_not_the_shell_and_nothing_is_modified(manifest, monkeypatch):
    path, root = manifest
    stored = json.loads(path.read_text(encoding='utf-8'))
    assert stored['references']['growth_record']['path'] == '../inputs/growth.json'
    assert stored['references']['capture']['path'] == '../inputs/edit_session/capture.json'
    before = {p: common.file_hash(p) for p in (root / 'inputs').rglob('*.json')}
    monkeypatch.chdir(root.parent)  # a different working directory must not change resolution
    loaded = ref.load_request(path)
    assert loaded['status'] == 'ready' and loaded['findings'] == []
    assert loaded['documents']['growth_record']['plant_id'] == 'P'
    assert loaded['documents']['capture']['session_id'] == 'S'
    assert {p: common.file_hash(p) for p in (root / 'inputs').rglob('*.json')} == before
    assert ref.require_ready(loaded) is loaded


def test_every_unusable_reference_is_reported_before_any_calculation(manifest):
    path, root = manifest
    stored = json.loads(path.read_text(encoding='utf-8'))

    def reloaded(change):
        document = json.loads(json.dumps(stored))
        change(document)
        common.write_json(path, document)
        return ref.load_request(path)

    def codes(loaded, reference):
        return sorted(f['code'] for f in loaded['findings'] if f['reference'] == reference)

    (root / 'inputs' / 'growth.json').unlink()
    missing = ref.load_request(path)
    assert codes(missing, 'growth_record') == ['reference_file_missing'] and missing['status'] == 'blocked'
    with pytest.raises(common.StudyError, match='growth_record: reference_file_missing'):
        ref.require_ready(missing)
    common.write_json(root / 'inputs' / 'growth.json', GROWTH)

    (root / 'inputs' / 'annotations.json').write_text('{not json', encoding='utf-8')
    assert 'reference_not_readable_json' in codes(ref.load_request(path), 'annotation_context')
    common.write_json(root / 'inputs' / 'annotations.json', dict(leaflets=[]))

    changed = json.loads(json.dumps(GROWTH))
    changed['compound_leaves'][0]['leaflet_count'] = 4
    common.write_json(root / 'inputs' / 'growth.json', changed)
    stale = ref.load_request(path)
    assert codes(stale, 'growth_record') == ['reference_hash_changed_since_snapshot']
    finding = next(f for f in stale['findings'] if f['code'] == 'reference_hash_changed_since_snapshot')
    assert finding['recorded'] != finding['current'] and 'refresh the snapshot' in finding['detail']
    common.write_json(root / 'inputs' / 'growth.json', GROWTH)

    assert codes(reloaded(lambda d: d['references']['capture'].update(sha256=None)), 'capture') == \
        ['reference_hash_not_recorded']
    assert 'plant_identity_mismatch' in codes(reloaded(lambda d: d.update(plant_id='OTHER')), 'capture')
    assert 'session_identity_mismatch' in codes(reloaded(lambda d: d.update(session_id='OTHER')), 'capture')
    assert 'capture_date_mismatch' in codes(reloaded(lambda d: d.update(capture_date='2026-01-01')),
                                            'growth_record')
    assert codes(reloaded(lambda d: d['references'].pop('annotation_snapshot')), 'annotation_snapshot') == \
        ['reference_missing_from_request']
    unknown = reloaded(lambda d: d.update(schema_version='reconstruction-request-99'))
    assert unknown['status'] == 'blocked' and unknown['findings'][0]['code'] == 'unknown_request_schema'
    with pytest.raises(common.StudyError, match='not found'):
        ref.load_request(root / 'requests' / 'absent.json')
    path.write_text('{oops', encoding='utf-8')
    with pytest.raises(common.StudyError, match='not readable JSON'):
        ref.load_request(path)


# ----------------------------------------------------------------------------------------------
# Growth record review
# ----------------------------------------------------------------------------------------------

def test_count_mismatches_are_findings_and_never_change_a_label():
    labels = [dict(organ_id='L01', leaflet_id=f'A{i}', identity_review='confirmed') for i in range(9)]
    labels += [dict(organ_id='L02', leaflet_id='B1', identity_review='confirmed'),
               dict(organ_id='L02', leaflet_id='B2', identity_review='unconfirmed'),
               dict(organ_id='L09', leaflet_id='C1', identity_review='confirmed')]
    review = ref.review_counts(GROWTH, labels)
    entries = {e['compound_leaf_id']: e for e in review['compound_leaves']}
    assert entries['L01']['finding'] == 'more_reviewed_leaflets_than_recorded'
    assert entries['L01']['reviewed_leaflet_count'] == 9 and entries['L01']['recorded_leaflet_count'] == 8
    # An unconfirmed identity is listed but never counted as a reviewed leaflet.
    assert entries['L02']['finding'] == 'fewer_reviewed_leaflets_than_recorded'
    assert entries['L02']['reviewed_leaflet_count'] == 1 and entries['L02']['unconfirmed_leaflet_ids'] == ['B2']
    assert entries['L03']['finding'] == 'growth_leaflet_count_not_recorded'
    assert {f['code'] for f in review['findings']} >= {'parent_not_in_growth_record'}
    # The growth-shoot count is never folded into a leaflet count, and nothing is edited.
    assert review['growth_shoot_count'] == 3
    assert review['labels_changed'] is False and review['geometry_changed'] is False
    assert len(labels) == 12 and labels[0]['leaflet_id'] == 'A0'


def test_a_matching_count_produces_no_finding():
    labels = [dict(organ_id='L02', leaflet_id=f'B{i}', identity_review='confirmed') for i in range(2)]
    entries = {e['compound_leaf_id']: e for e in ref.review_counts(GROWTH, labels)['compound_leaves']}
    assert entries['L02']['finding'] is None


MEMBERSHIP = dict(schema_version='compound-leaf-membership-1', candidates={
    'c1': dict(leaf_key='leaf_007|unavailable', state='ambiguous',
               candidate_parents=[dict(parent_id='L01'), dict(parent_id='L02')]),
    'c2': dict(leaf_key='leaf_008|unavailable', state='kept_unresolved', candidate_parents=[dict(parent_id='L02')]),
    'c3': dict(leaf_key='leaf_009|unavailable', state='rejected', candidate_parents=[dict(parent_id='L01')]),
    'c4': dict(leaf_key='L01|leaf_004', state='accepted', candidate_parents=[dict(parent_id='L01')])})


def test_open_membership_candidates_are_listed_per_parent_and_never_counted():
    labels = [dict(organ_id='L01', leaflet_id='leaf_004', identity_review='confirmed', membership_state='confirmed'),
              dict(organ_id='L01', leaflet_id='A1', identity_review='confirmed'),  # legacy: no membership decision
              dict(organ_id='leaf_007', leaflet_id='unavailable', identity_review='confirmed', membership_state=None)]
    review = ref.review_counts(GROWTH, labels, MEMBERSHIP)
    entries = {e['compound_leaf_id']: e for e in review['compound_leaves']}
    # The counting rule is unchanged: two identity-confirmed leaflets carry L01, open candidates add nothing.
    assert entries['L01']['reviewed_leaflet_count'] == 2
    assert entries['L01']['membership_confirmed_ids'] == ['leaf_004']
    assert entries['L01']['membership_unreviewed_ids'] == ['A1']
    # Only open candidates are unresolved; one ambiguous leaflet is listed under both parents it names.
    assert entries['L01']['unresolved_candidate_leaflets'] == ['leaf_007|unavailable']
    assert entries['L02']['unresolved_candidate_leaflets'] == ['leaf_007|unavailable', 'leaf_008|unavailable']
    assert entries['L01']['exact_total_claimed'] is False and entries['L03']['exact_total_claimed'] is True
    codes = [(f['code'], f.get('compound_leaf_id')) for f in review['findings']]
    assert ('leaflet_membership_unresolved', 'L01') in codes and ('leaflet_membership_unresolved', 'L02') in codes
    assert ('leaflet_membership_not_reviewed', 'L01') in codes
    assert review['open_membership_candidates'] == 2
    assert not any(f['code'] in ref.BLOCKING_FINDINGS for f in review['findings'])
    assert review['labels_changed'] is False and review['growth_shoot_count'] == 3


def test_backups_without_membership_keep_their_previous_findings():
    labels = [dict(organ_id='L02', leaflet_id=f'B{i}', identity_review='confirmed') for i in range(2)]
    review = ref.review_counts(GROWTH, labels)
    assert not any(f['code'].startswith('leaflet_membership') for f in review['findings'])
    assert review['open_membership_candidates'] == 0 and review['membership_schema'] is None


def test_rebuild_passes_membership_decisions_from_the_editor_backup():
    backup = dict(variants={'__all__': dict(leaflets={
        'L01|leaf_003': dict(organ_id='L01', leaflet_id='leaf_003', membership_review=dict(state='confirmed', parent_id='L01')),
        'leaf_001|A1': dict(organ_id='leaf_001', leaflet_id='A1')}, membership=MEMBERSHIP)})
    leaflets = {r['leaf_key']: r for r in tool.reviewed_leaflets(backup, [], [])}
    assert leaflets['L01|leaf_003']['membership_state'] == 'confirmed'
    assert leaflets['leaf_001|A1']['membership_state'] is None


def test_rebuild_reference_review_carries_the_backup_membership(tmp_path):
    request = tmp_path / 'request.json'
    common.write_json(request, dict(schema_version=ref.REQUEST_SCHEMA))
    loaded = dict(documents=dict(growth_record=GROWTH), request=dict(plant_id='P', session_id='S'),
                  request_path=str(request), findings=[], resolved={}, status='ready')
    backup = dict(variants={'__all__': dict(leaflets={}, membership=MEMBERSHIP)})
    review = tool.attach_references(loaded, CAPTURE, [], backup, [])
    entries = {e['compound_leaf_id']: e for e in review['growth_review']['compound_leaves']}
    assert entries['L02']['unresolved_candidate_leaflets'] == ['leaf_007|unavailable', 'leaf_008|unavailable']
    assert ref.summary(review)['growth_review']['L02']['unresolved'] == 2


# ----------------------------------------------------------------------------------------------
# Routes over one set of observations
# ----------------------------------------------------------------------------------------------

def test_routes_come_from_capture_labels_and_order_the_navigation():
    membership = {m['view_code']: m for m in ref.route_membership(CAPTURE)}
    assert membership['01']['routes'] == ['global', 'vertical']
    assert membership['21']['routes'] == ['global', 'vertical', 'circumferential']
    assert membership['11']['ring'] == 'side_ring' and membership['21']['ring'] == 'oblique_ring'
    assert ref.route_images(CAPTURE, 'vertical') == ['p_01.png', 'p_03.png', 'p_21.png', 'p_11.png',
                                                     'p_22.png', 'p_12.png']
    assert ref.route_images(CAPTURE, 'circumferential') == ['p_11.png', 'p_12.png', 'p_21.png', 'p_22.png']
    assert len(ref.route_images(CAPTURE, 'global')) == 6
    with pytest.raises(common.StudyError, match='Unknown review route'):
        ref.route_images(CAPTURE, 'spiral')


def test_one_observation_reached_by_several_routes_is_counted_once():
    rows = [observation('A1', 'b0', 'p_01.png'), observation('A1', 'b0', 'p_21.png'),
            observation('A1', 'b0', 'p_11.png')]
    collected = ref.collect_observations(rows, CAPTURE)
    point = collected['points'][0]
    assert point['unique_observation_count'] == 3 and collected['unique_observations'] == 3
    reached = {o['image_file']: o['routes_reached'] for o in point['observations']}
    assert reached['p_21.png'] == ['global', 'vertical', 'circumferential']
    assert point['routes_reached'] == ['circumferential', 'global', 'vertical']
    # Being reachable through three routes does not make it three observations.
    assert sum(len(o['routes_reached']) for o in point['observations']) == 8
    assert collected['duplicate_observations_collapsed'] == 0


def test_the_same_saved_observation_offered_twice_collapses_and_conflicts_are_kept():
    rows = [observation('A1', 'b0', 'p_01.png'), observation('A1', 'b0', 'p_01.png')]
    same = ref.collect_observations(rows, CAPTURE)
    assert same['duplicate_observations_collapsed'] == 1 and same['unique_observations'] == 1
    assert same['conflicts'] == [] and same['points'][0]['observations'][0]['eligible'] is True
    rows = [observation('A1', 'b0', 'p_01.png', x=100.), observation('A1', 'b0', 'p_01.png', x=140.)]
    conflicting = ref.collect_observations(rows, CAPTURE)
    observations = conflicting['points'][0]['observations']
    assert len(observations) == 1 and observations[0]['contradictory_coordinates'] == [[140., 200.]]
    assert observations[0]['eligible'] is False
    assert observations[0]['ineligible_reason'] == 'contradictory_coordinates_for_one_observation'
    assert conflicting['conflicts'][0]['kept'] == [100., 200.] and conflicting['conflicts'][0]['also_saved'] == [140., 200.]


def test_identical_local_point_names_on_different_leaflets_stay_separate():
    rows = [observation('A1', 'b1', 'p_01.png'), observation('A2', 'b1', 'p_01.png'),
            observation('A1', 'b1', 'p_03.png')]
    collected = ref.collect_observations(rows, CAPTURE)
    assert collected['unique_physical_points'] == 2
    keys = sorted(p['physical_point_key'] for p in collected['points'])
    assert keys == ['P|S|L01|A1|b1', 'P|S|L01|A2|b1']
    assert {p['point_id'] for p in collected['points']} == {'b1'}
    counts = {p['leaflet_id']: p['unique_observation_count'] for p in collected['points']}
    assert counts == {'A1': 2, 'A2': 1}


def test_point_eligibility_is_decided_per_point_and_unposed_views_supply_no_ray():
    rows = [observation('A1', 'b0', 'p_01.png'), observation('A1', 'b0', 'p_11.png'),
            observation('A1', 'b1', 'p_01.png', view_visibility='partial'),
            observation('A1', 'b1', 'p_03.png', view_visibility='partial')]
    points = {p['point_id']: p for p in ref.collect_observations(rows, CAPTURE)['points']}
    # b0 is seen in one posed and one unposed view: the unposed observation is kept for identity review.
    assert points['b0']['unique_observation_count'] == 2 and points['b0']['eligible_observation_count'] == 1
    assert points['b0']['triangulation_status'] == 'fewer_than_two_solved_views'
    assert points['b0']['ineligible_reasons'] == ['unposed_no_triangulation_ray']
    # A partially occluded leaflet still has assessable visible points.
    assert points['b1']['triangulation_status'] == 'two_or_more_eligible_views'
    assert all(o['view_visibility'] == 'partial' and o['eligible'] for o in points['b1']['observations'])


def test_selecting_a_route_only_narrows_the_photographs_it_walks():
    rows = [observation('A1', 'b0', image) for image in ('p_01.png', 'p_21.png', 'p_11.png')]
    circumferential = ref.collect_observations(rows, CAPTURE, route='circumferential')
    assert circumferential['points'][0]['unique_observation_count'] == 2
    assert 'p_01.png' not in [o['image_file'] for o in circumferential['points'][0]['observations']]
    assert ref.collect_observations(rows, CAPTURE, leaflet='A9')['points'] == []
    assert ref.collect_observations(rows, CAPTURE, leaflet='A1')['unique_physical_points'] == 1


# ----------------------------------------------------------------------------------------------
# Rebuild integration
# ----------------------------------------------------------------------------------------------

def request_for(prepared_case, tmp_path, growth=None, **overrides):
    session, backup_path, context, out, _, backup, capture = prepared_case
    tmp_path.mkdir(parents=True, exist_ok=True)
    growth_path = tmp_path / 'growth.json'
    common.write_json(growth_path, growth or dict(
        plant_id='P', capture_date='2026-09-20', compound_leaf_count=1,
        compound_leaves=[dict(compound_leaf_id='O3D', leaflet_count=2, is_unfolding=False)],
        growth_shoot_count=1, truss_count=0))
    path = tmp_path / 'requests' / 'request.json'
    ref.write_request(path, 'P', 'S', growth_path, session, backup_path, context, out / 'result',
                      capture=session / 'capture.json', calibration=session / 'intrinsics.json',
                      capture_date='2026-09-20', **overrides)
    return path


def test_rebuild_reports_the_reference_review_without_changing_the_geometry(prepared, tmp_path):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    plain = tool.rebuild(session, path, context, out / 'plain')
    assert plain['reference_status'] == 'no_request_attached'
    request = request_for((session, path, context, out, None, backup, None), tmp_path)
    report = tool.rebuild(session, path, context, out / 'reviewed', request=request)

    assert report['reference_status'] == 'ready'
    # The editor's identity link for this leaflet is still unconfirmed, so it is listed but not counted.
    assert report['growth_review']['O3D'] == dict(recorded=2, reviewed=0, unresolved=0,
                                                  finding='fewer_reviewed_leaflets_than_recorded')
    assert common.read_json(out / 'reviewed' / 'reference_review.json'
                            )['growth_review']['compound_leaves'][0]['unconfirmed_leaflet_ids'] == ['L3D']
    assert report['route_summary']['global']['unique_physical_points'] == 3
    assert report['route_summary']['global']['duplicate_observations_collapsed'] == 0
    review = common.read_json(out / 'reviewed' / 'reference_review.json')
    assert review['status'] == 'ready' and review['validated_metric'] is False
    assert {f['code'] for f in review['findings']} == {'fewer_reviewed_leaflets_than_recorded'}
    table = common.rows(out / 'reviewed' / 'route_observations.csv')
    assert {r['physical_point_key'] for r in table} == {'P|S|O3D|L3D|b0', 'P|S|O3D|L3D|b1', 'P|S|O3D|L3D|b2'}
    assert {r['routes_reached'] for r in table} == {'global'}  # this fixture's photos carry no capture label

    # Consulting JSON changes no coordinate: the geometry outputs are byte-identical.
    for name in ('editor_point_depths.csv', 'capture.json', 'annotations.edited.json'):
        assert common.file_hash(out / 'reviewed' / name) == common.file_hash(out / 'plain' / name)
    html = (out / 'reviewed' / 'labels/index.html').read_text(encoding='utf-8')
    assert 'JSON 참조 검토' in html and '기록보다 검토된 소엽이 적음' in html
    assert 'JSON 참조 검토' not in (out / 'plain' / 'labels/index.html').read_text(encoding='utf-8')


def test_a_count_only_change_refreshes_findings_and_leaves_the_geometry_alone(prepared, tmp_path):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    first = request_for((session, path, context, out, None, backup, None), tmp_path)
    before = tool.rebuild(session, path, context, out / 'before', request=first)
    second = request_for((session, path, context, out, None, backup, None), tmp_path / 'again', growth=dict(
        plant_id='P', capture_date='2026-09-20', compound_leaf_count=1,
        compound_leaves=[dict(compound_leaf_id='O3D', leaflet_count=0, is_unfolding=False)],
        growth_shoot_count=1, truss_count=0))
    after = tool.rebuild(session, path, context, out / 'after', request=second)
    assert before['growth_review']['O3D']['finding'] == 'fewer_reviewed_leaflets_than_recorded'
    assert after['growth_review']['O3D']['finding'] is None
    assert common.file_hash(out / 'after' / 'editor_point_depths.csv') == \
        common.file_hash(out / 'before' / 'editor_point_depths.csv')
    assert after['route_summary'] == before['route_summary']


def test_an_unusable_or_foreign_request_stops_the_run_before_anything_is_written(prepared, tmp_path):
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    request = request_for((session, path, context, out, None, backup, None), tmp_path)
    stored = json.loads(request.read_text(encoding='utf-8'))
    # A request that is internally consistent but describes another session must not rebuild this one.
    foreign_capture = tmp_path / 'other_capture.json'
    common.write_json(foreign_capture, dict(common.read_json(session / 'capture.json'),
                                            plant_id='OTHER', session_id='OTHER_SESSION'))
    foreign = json.loads(json.dumps(stored))
    foreign.update(plant_id='OTHER', session_id='OTHER_SESSION')
    foreign['references']['capture'] = dict(path='../other_capture.json', role='capture',
                                            sha256=common.file_hash(foreign_capture))
    foreign_growth = tmp_path / 'other_growth.json'
    common.write_json(foreign_growth, dict(common.read_json(tmp_path / 'growth.json'), plant_id='OTHER'))
    foreign['references']['growth_record'] = dict(path='../other_growth.json', role='growth', sha256=None)
    common.write_json(tmp_path / 'requests' / 'foreign.json', foreign)
    loaded = ref.load_request(tmp_path / 'requests' / 'foreign.json')
    assert [f['code'] for f in loaded['findings']] == ['reference_hash_not_recorded']
    foreign['references']['growth_record']['sha256'] = common.file_hash(foreign_growth)
    common.write_json(tmp_path / 'requests' / 'foreign.json', foreign)
    with pytest.raises(common.StudyError, match='not this session'):
        tool.rebuild(session, path, context, out / 'foreign', request=tmp_path / 'requests' / 'foreign.json')
    assert not (out / 'foreign').exists()
    growth = tmp_path / 'growth.json'
    common.write_json(growth, dict(common.read_json(growth), truss_count=2))
    with pytest.raises(common.StudyError, match='reference_hash_changed_since_snapshot'):
        tool.rebuild(session, path, context, out / 'stale', request=request)
    assert not (out / 'stale').exists()


def test_the_browser_rebuild_route_carries_the_request(prepared, tmp_path):
    from tools import serve_leaf_edit_session as server
    from tools.tests.test_serve_leaf_edit_session import post_backup, running, wait
    session, path, context, out, _, backup, _ = prepared
    common.write_json(path, backup)
    request = request_for((session, path, context, out, None, backup, None), tmp_path)
    service = server.EditService(session, context, out.parent / 'runs', path, request=request)
    with running(service) as port:
        job = wait(port, service, post_backup(port, service, common.read_json(path))[1]['job_id'])
    assert job['status'] == 'complete' and job['reference_status'] == 'ready'
    assert job['reference_finding_counts'] == {'fewer_reviewed_leaflets_than_recorded': 1}
    result = out.parent / 'runs' / job['job_id'] / 'result'
    assert (result / 'reference_review.json').exists() and (result / 'route_observations.csv').exists()
    assert 'JSON 참조 검토' in (result / 'labels/index.html').read_text(encoding='utf-8')


def test_imported_labels_are_summarised_per_photo_without_becoming_geometry():
    capture = dict(frames=[dict(image_file='p_01.png', view_code='01', pose_status='solved', passes_pose_gate=False,
                                n_markers_detected=9),
                           dict(image_file='p_11.png', view_code='11', pose_status='too_few_corners', passes_pose_gate=False)])
    detections = {'p_01.png': [dict(class_name='leaflet', adopted_into=dict(leaf_key='leaf_001|unavailable')),
                               dict(class_name='leaflet'), dict(class_name='sub-stem')]}
    backup = dict(variants={'__all__': dict(leaflets={}, membership=dict(detections=detections))})
    summary = tool.imported_label_summary(backup, capture)
    photos = {p['image_file']: p for p in summary['photos']}
    assert photos['p_01.png']['by_class'] == {'leaflet': 2, 'sub-stem': 1}
    assert photos['p_01.png']['adopted_leaflets'] == 1 and photos['p_01.png']['state'] == '2d_labels_only'
    assert photos['p_11.png']['state'] == 'no_imported_labels'
    assert summary['total'] == 3 and summary['confirmed_identities'] == 0
