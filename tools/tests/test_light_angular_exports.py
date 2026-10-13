"""Actual producer -> bridge -> serialized independent consumer checks."""
from copy import deepcopy

import numpy as np
import pytest

from tools import hierarchical_light as hierarchy
from tools import light_growth_bridge as bridge
from tools.hierarchical_light_demo import synthetic_inputs
from tools.light_growth_consumer import load_tables
from tools.leaf_light.common import StudyError, read_json, write_json, file_hash, write_rows
from test_light_growth_bridge import timing, schedule, add_observations


def actual_request(root, mode='known'):
    source = synthetic_inputs(root/'inputs', groups=() if mode=='opposing' else ('A','B','C'))
    scene = read_json(source.parent/'scene.json')
    fx = scene['fixtures'][0]
    fx['emitting_length_mm']['value'] = 600.
    fx['emitter_grid'] = [3, 1]
    second = deepcopy(fx); second['fixture_id'] = 'side'
    second['emitting_center_grow_mm']['value'] = [350., 120., 900.]
    if mode=='opposing':
        second['emitting_center_grow_mm']['value'] = [0., 0., -1000.]
        second['aim_tilt_deg']['value'] = 180.
    scene['fixtures'].append(second)
    scene['simulation']['max_ray_triangle_pairs_per_chunk'] = 7
    if mode == 'unknown_tau':
        scene['leaf_optics']['transmittance'].update(value=None, status='unavailable')
    if mode == 'unknown_fixture': fx['photon_flux_umol_s'].update(value=None, status='unavailable')
    if mode == 'zero':
        for lamp in scene['fixtures']: lamp['photon_flux_umol_s']['value'] = 0.
    if mode == 'background':
        from tools.ppfd_validation import RIG_SURFACE_COLUMNS
        background = {key:'' for key in RIG_SURFACE_COLUMNS}
        background.update(surface_id='fixed_plate',kind='shelf',role='physical_occluder',
            center_x_mm=0,center_y_mm=0,center_z_mm=800,normal_x=0,normal_y=0,normal_z=1,
            width_axis_x=1,width_axis_y=0,width_axis_z=0,width_mm=2000,height_mm=2000,
            reflectance=0,transmittance=0,geometry_status='assumed',geometry_source='synthetic plate',
            optics_status='assumed',optics_source='synthetic opaque')
        write_rows(source.parent/'background.csv',[background],RIG_SURFACE_COLUMNS)
        plan = read_json(source); plan['background_csv']='background.csv'; write_json(source,plan)
    write_json(source.parent/'scene.json', scene)
    hierarchy.prepare_subset_cases(source, root/'prepared')
    hierarchy.calculate_direct(root/'prepared', root/'legacy')
    t = timing(); snap = t['snapshots'][0]
    snap.update(prepared_run='prepared', full_scene_results='legacy', observed_at=t['start_at'],
                board_frame_ids={'P1':'board_P1','P2':'board_P2'})
    sched = schedule(); sched['fixtures'] = {
        'synthetic_LED':[dict(start_hhmm='00:00',end_hhmm='12:00',output_fraction=1.)],
        'side':[dict(start_hhmm='00:00',end_hhmm='06:00',output_fraction=.25)]}
    if mode == 'unknown_schedule': sched['fixtures']['side'] = None
    request = dict(schema_version='light-growth-1',run_id='actual_angular_test', snapshots=[snap],
        interval={k:t[k] for k in ('start_at','end_at')}, schedule=sched,
        limits=dict(max_transport_calls=1,max_receiver_emitter_pairs=100000,max_schedule_minutes=4000))
    write_json(root/'request.json', request)
    return root/'request.json'


def test_actual_opposing_export_preserves_second_moment_and_cancellation(tmp_path):
    request = actual_request(tmp_path,'opposing')
    data = read_json(request); data['snapshots'][0]['board_frame_ids'] = {'P1':'board_P1'}
    write_json(request,data)
    bridge.build_package(request,tmp_path/'package')
    check = bridge.validate_growth_light_package(tmp_path/'package'); assert check['valid'], check
    records = load_tables(tmp_path/'package')['compound_light_features.csv']
    row = next(r for r in records if r['level']=='canopy' and r['time_step_id']=='full_output' and r['fixture_id']=='all')
    assert row['arrival_flux_umol_s'] > 0
    assert row['directionality'] < 1e-9
    assert row['dominant_arrival_z'] is None
    assert row['angular_second_zz'] > .9
    # Unequal fixture schedules break the symmetry in the actual exported interval.
    assert any(r['dominant_arrival_z'] is not None for r in records if r['level']=='canopy' and r['time_step_id']!='full_output' and r['fixture_id']=='all')


@pytest.mark.parametrize('mode', ['known','zero','background','unknown_tau','unknown_fixture','unknown_schedule'])
def test_actual_unknown_zero_schedule_and_moment_exports(tmp_path, mode):
    request = actual_request(tmp_path, mode)
    add_observations(tmp_path, request)
    bridge.build_package(request, tmp_path/'package')
    result = bridge.validate_growth_light_package(tmp_path/'package')
    assert result['valid'], result
    tables = load_tables(tmp_path/'package')
    samples = tables['light_samples.csv']
    for row in samples:
        q = row['received_ppfd_umol_m2_s']; f = row['arrival_flux_umol_s']
        assert (q is None) == (f is None)
        if q is not None: assert f == pytest.approx(q*row['quadrature_area_m2'], abs=1e-10, rel=1e-9)
    features = tables['compound_light_features.csv']
    if mode in ('zero','background'):
        assert all(r['arrival_flux_umol_s'] == 0 and r['dominant_arrival_x'] is None and r['directionality'] is None for r in features)
    elif mode in ('unknown_tau','unknown_fixture'):
        unknown = [r for r in samples if r['time_step_id']=='full_output' and r['arrival_flux_umol_s'] is None]
        assert unknown
        assert all(r['arrival_path_unknown_count'] is None or r['arrival_path_unknown_count'] > 0 for r in unknown)
    elif mode == 'unknown_schedule':
        assert any(r['arrival_flux_umol_s'] is not None for r in samples if r['fixture_id']=='side' and r['time_step_id']=='full_output')
        assert all(r['arrival_flux_umol_s'] is None for r in samples if r['fixture_id']=='side' and r['time_step_id']!='full_output')
    else:
        full = {r['sample_id']:r for r in samples if r['fixture_id']=='side' and r['time_step_id']=='full_output'}
        for row in samples:
            if row['fixture_id']=='side' and row['time_step_id']!='full_output':
                ratio = row['arrival_flux_umol_s']/full[row['sample_id']]['arrival_flux_umol_s']
                assert min(abs(ratio), abs(ratio-.25)) < 1e-10
                for key in bridge.ARRIVAL:
                    assert row[key] == pytest.approx(full[row['sample_id']][key]*ratio, abs=1e-10, rel=1e-9)
        assert any(r['quantity_frame']=='compound_local' and r['arrival_flux_umol_s'] is not None for r in features)


@pytest.mark.parametrize('mutation', ['sample_flux','sample_M','sample_B','time_M','board_M','local_B','region_M',
                                    'path_count','fixture_missing','receiver_index','unknown_count'])
def test_independent_angular_consumer_rejects_rehashed_wrong_producer_output(tmp_path, mutation):
    request = actual_request(tmp_path); add_observations(tmp_path,request)
    folder = tmp_path/'package'; bridge.build_package(request,folder)
    assert bridge.validate_growth_light_package(folder)['valid']
    if mutation in ('path_count','fixture_missing'):
        path = folder/'angular_diagnostics.json'; data = read_json(path)
        if mutation == 'path_count': data['g']['fixtures'][0]['received_path_count'] -= 1
        else: data['g']['fixtures'].pop()
        write_json(path,data)
    else:
        tables = load_tables(folder)
        table = 'compound_light_features.csv' if mutation.startswith(('board_','local_','region_')) else 'light_samples.csv'
        records = tables[table]
        if table == 'light_samples.csv':
            row = next(r for r in records if (r['time_step_id']!='full_output') == (mutation=='time_M') and r['fixture_id']=='side')
        else:
            frame = 'board' if mutation=='board_M' else 'compound_local'
            row = next(r for r in records if r['quantity_frame']==frame and (r['region_id']!='whole_supported') == (mutation=='region_M'))
        key = {'sample_flux':'arrival_flux_umol_s','sample_M':'arrival_M_x_umol_s','sample_B':'arrival_B_xx_umol_s',
               'time_M':'arrival_M_y_umol_s','board_M':'arrival_M_x_umol_s','local_B':'arrival_B_xy_umol_s',
               'region_M':'arrival_M_z_umol_s','receiver_index':'receiver_index','unknown_count':'arrival_path_unknown_count'}[mutation]
        row[key] += 1
        path = folder/table; write_rows(path,records,[c['name'] for c in bridge.SCHEMA['tables'][table]['columns']])
    package = read_json(folder/'package.json'); package['artifact_hashes'][path.name] = file_hash(path)
    write_json(folder/'package.json',package)
    check = bridge.validate_growth_light_package(folder)
    assert not check['valid'], mutation


@pytest.mark.parametrize('mutation', ['drop_first','drop_last','duplicate'])
def test_actual_producer_chunk_loss_and_duplication_stop_export(tmp_path, monkeypatch, mutation):
    request = actual_request(tmp_path)
    original = hierarchy.direct_light
    def intercepted(*args, **kwargs):
        callback = kwargs['diagnostic_callback']
        def receive(event):
            first = event['path_start']==0
            last = event['path_stop']==event['expected_path_count']
            if (mutation=='drop_first' and first) or (mutation=='drop_last' and last): return
            callback(event)
            if mutation=='duplicate' and first: callback(event)
        kwargs['diagnostic_callback'] = receive
        return original(*args, **kwargs)
    monkeypatch.setattr(hierarchy,'direct_light',intercepted)
    with pytest.raises(StudyError, match='duplicate_missing_or_unordered|missing_direction_paths_or_fixture'):
        bridge.build_package(request,tmp_path/'rejected')


def test_actual_producer_arrays_reused_immediately_after_callback(tmp_path, monkeypatch):
    request = actual_request(tmp_path)
    original = hierarchy.direct_light
    buffers = {}
    def intercepted(*args, **kwargs):
        callback = kwargs['diagnostic_callback']
        def receive(event):
            borrowed = dict(event)
            for k,v in event.items():
                if isinstance(v,np.ndarray):
                    key = (k,v.shape)
                    if key not in buffers: buffers[key] = np.empty_like(v)
                    np.copyto(buffers[key],v); borrowed[k] = buffers[key].view()
                    borrowed[k].flags.writeable = False
            callback(borrowed)
            for v in buffers.values(): v.fill(0)
        kwargs['diagnostic_callback'] = receive
        return original(*args, **kwargs)
    monkeypatch.setattr(hierarchy,'direct_light',intercepted)
    bridge.build_package(request,tmp_path/'package')
    result = bridge.validate_growth_light_package(tmp_path/'package')
    assert result['valid'],result
