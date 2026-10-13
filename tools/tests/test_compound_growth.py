"""Directional state and chronological forecast regression tests."""
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json

import numpy as np
import pytest

from tools import compound_growth as cg
from tools.leaf_light.common import StudyError, file_hash, write_json, write_rows


def state(day=0, angle=0, length=10, elevation=0, parent=(0,0,0), plant='p', compound='L1'):
    az,el=np.radians([angle,elevation]);x=np.array([np.cos(az)*np.cos(el),np.sin(az)*np.cos(el),np.sin(el)])
    y=np.array([-np.sin(az),np.cos(az),0.])
    t=(datetime(2026,10,1,tzinfo=timezone.utc)+timedelta(days=day)).isoformat()
    record=dict(plant_id=plant,compound_leaf_id=compound,session_id='s'+str(day),observed_at=t,parent_stem_id='stem',
                identity_status='confirmed',review_source='synthetic_fixture',geometry_status='observed_axis',
                development_state='unfolding',first_observed_at=None,supported_area_cm2=10+day,estimated_total_area_cm2=None,
                area_basis_id='same_patch',**dict(zip(('transverse_x','transverse_y','transverse_z'),y)))
    pts=np.array(parent)+np.array([0,.5,1])[:,None]*x*length
    axis=[dict(station=s,x_mm=p[0],y_mm=p[1],z_mm=p[2]) for s,p in zip([0,.5,1],pts)]
    ext=[dict(station=.5,left_mm=2+day,right_mm=3+day)]
    return cg.extract_compound_state(record,axis,ext,dict(frame_id='fixed_board',coordinate_frame='board_mm',frame_stability='confirmed',frame_evidence='synthetic fixture',data_kind='synthetic',reference_status='synthetic_truth'))


def run(history, model='recent_change', horizon=1):
    return cg.forecast(history,[horizon],None,dict(model=model,max_horizon_days=3,provenance='synthetic_fixture'))['predictions'][0]


def test_signed_angles_and_vertical_azimuth():
    assert state(elevation=30)['elevation_deg']==pytest.approx(30)
    assert state(elevation=-30)['elevation_deg']==pytest.approx(-30)
    assert state(elevation=90)['azimuth_deg'] is None


def test_wraparound_and_unequal_intervals():
    p=run([state(0,angle=179),state(2,angle=-179)])['state']
    assert p['azimuth_deg']==pytest.approx(-178)
    assert p['rachis_arc_length_mm']==pytest.approx(10)


def test_parent_translation_length_width_and_area():
    a=state(0,length=10);b=state(2,length=14,parent=(0,0,4))
    p=run([a,b])['state']
    assert p['attachment_xyz_mm']==pytest.approx([0,0,6])
    assert p['tip_xyz_mm']==pytest.approx([16,0,6])
    assert p['left_extent_mm']==pytest.approx([5])
    assert p['supported_area_cm2']==pytest.approx(13)
    assert not p['eligible_state'] and not p['suitable_for_ppfd']


def test_rigid_rotation_does_not_inflate_area_or_length():
    a=state(0,angle=0);b=state(1,angle=30);b['supported_area_cm2']=a['supported_area_cm2']
    p=run([a,b])['state']
    assert p['azimuth_deg']==pytest.approx(60)
    assert p['rachis_arc_length_mm']==pytest.approx(10)
    assert p['supported_area_cm2']==10


def test_persistence_and_determinism():
    history=[state()];first=run(history,'persistence');second=run(history,'persistence')
    assert first==second
    assert first['state']['rachis_points_mm']==history[-1]['rachis_points_mm']
    assert history[0]['eligible_state']


@pytest.mark.parametrize('horizon',[0,-1,4,float('nan'),float('inf')])
def test_invalid_horizon(horizon):
    with pytest.raises(StudyError): run([state()],horizon=horizon)


def test_one_observation_cannot_invent_rate():
    p=run([state()]);assert p['state'] is None and 'two distinct' in p['reason']


def test_missing_reviewed_model_is_explicit():
    p=run([state(0),state(1)],'reviewed_growth');assert p['status']=='unavailable'
    assert 'specification' in p['reason']


def test_ambiguous_identity_and_changed_frame():
    a,b=state(0),state(1);b['frame_id']='moved'
    with pytest.raises(StudyError,match='Frame'):run([a,b])
    b=state(1,compound='L2')
    with pytest.raises(StudyError,match='Mixed'):run([a,b])
    b=state(1);b['eligible_state']=False
    with pytest.raises(StudyError,match='unconfirmed'):run([a,b])


def test_same_timestamp_different_sessions_rejected():
    a,b=state(),state();b['session_id']='other'
    with pytest.raises(StudyError,match='Duplicate'):run([a,b])


def test_missing_and_changed_coverage_do_not_create_area_rate():
    a,b=state(0),state(1);b['area_basis_id']='different'
    p=run([a,b])['state'];assert p['supported_area_cm2'] is None
    a['left_extent_mm']=None
    p=run([a,b])['state'];assert p['left_extent_mm'] is None


def test_collapsed_axis_and_negative_extrapolation():
    with pytest.raises(StudyError,match='Collapsed'):cg.axis_traits([[0,0,0],[0,0,0]])
    p=run([state(0,length=10),state(1,length=2)])
    assert p['status']=='unavailable' and 'collapses' in p['reason']


def test_frame_rotation_equivariance():
    history=[state(0,angle=10),state(1,angle=20)]
    original=run(history)['state']
    rot=cg.Rotation.from_euler('xyz',[15,25,40],degrees=True)
    shift=np.array([4,8,-2]); moved=deepcopy(history)
    for s in moved:
        pts=rot.apply(s['rachis_points_mm'])+shift
        s.update(rachis_points_mm=pts.tolist(),**cg.axis_traits(pts))
        s['transverse_unit_xyz']=rot.apply(s['transverse_unit_xyz']).tolist()
    actual=run(moved)['state']
    np.testing.assert_allclose(actual['rachis_points_mm'],rot.apply(original['rachis_points_mm'])+shift,atol=1e-8)


def plan():
    return dict(train_plant_ids=['train'],test_plant_ids=['p'],split_provenance='frozen_synthetic',
                model_parameters=dict(max_horizon_days=3,provenance='fixture'),
                forecasts=[dict(plant_id='p',compound_leaf_id='L1',forecast_origin=state(1)['observed_at'],target_at=state(2)['observed_at'])])


def test_evaluation_cannot_use_future_target_to_fit():
    states=[state(0,length=10),state(1,length=12),state(2,length=100)]
    result=cg.evaluate_compound_forecasts(states,plan())
    recent=next(r for r in result['metrics'] if r['model']=='recent_change')
    assert recent['tip_error_mm']==pytest.approx(86)
    assert not result['validated_growth']
    changed=plan();changed['train_plant_ids']=['p']
    with pytest.raises(StudyError,match='disjoint'):cg.evaluate_compound_forecasts(states,changed)


def test_missing_target_is_in_coverage_denominator():
    result=cg.evaluate_compound_forecasts([state(0),state(1)],plan())
    assert all(s['coverage']==0 and s['requested']==1 for s in result['summary'])


def bundle(folder):
    folder.mkdir(parents=True)
    observations=[];axes=[];extents=[]
    for day in range(4):
        s=state(day,angle=day*10,length=10+day*2)
        obs={k:s.get(k) for k in cg.OBS_COLUMNS}
        obs.update(dict(zip(('transverse_x','transverse_y','transverse_z'),s['transverse_unit_xyz'])))
        observations.append(obs)
        key={k:s[k] for k in cg.SESSION}
        axes.extend({**key,'station':u,**dict(zip(('x_mm','y_mm','z_mm'),p))} for u,p in zip(s['axis_stations'],s['rachis_points_mm']))
        extents.append({**key,'station':.5,'left_mm':s['left_extent_mm'][0],'right_mm':s['right_extent_mm'][0]})
    tables={}
    for name,data,columns in [('observations',observations,cg.OBS_COLUMNS),('axes',axes,cg.AXIS_COLUMNS),('extents',extents,cg.EXTENT_COLUMNS)]:
        p=folder/(name+'.csv');write_rows(p,data,columns);tables[name]=dict(path=p.name,sha256=file_hash(p))
    p=folder/'input.json';write_json(p,dict(schema='compound-observations-1',coordinate_frame='board_mm',frame_id='board',
                                        frame_stability='confirmed',frame_evidence='synthetic',data_kind='synthetic',reference_status='synthetic_truth',tables=tables))
    return p


def test_bundle_integrity_and_roundtrip(tmp_path,monkeypatch):
    p=bundle(tmp_path/'input');states,context=cg.load_history(p)
    assert len(states)==4 and all(s['eligible_state'] for s in states)
    # Only tests override the shared build guard; production uses the real guard.
    import tools.leaf_light.common as common
    monkeypatch.setattr(common,'BUILD',tmp_path)
    r=cg.forecast(states[:2],[1,2],None,dict(model='recent_change',max_horizon_days=2,provenance='fixture'))
    out=cg.export_run(tmp_path/'out',states,context,r)
    assert (out/'viewer.html').is_file() and '__COMPOUND_JSON__' not in (out/'viewer.html').read_text()
    assert (out/'forecast_axes.csv').is_file()
    with (tmp_path/'input/axes.csv').open('a') as f:f.write('\n')
    with pytest.raises(StudyError,match='hash mismatch'):cg.load_history(p)


def test_legacy_does_not_promote_petiole_or_guess_date(tmp_path):
    capture=tmp_path/'capture.json';write_json(capture,dict(plant_id='p',session_id='20261001'))
    structure=tmp_path/'structure.json';write_json(structure,dict(plant_id='p',session_id='20261001',
        inputs=dict(capture=str(capture),capture_sha256=file_hash(capture)),
        compound_regions=[dict(region=1,proposed_name='L1')],
        petioles=[dict(region=1,status='fitted',near_end=[0,0,5],far_end=[10,0,0],views=['a','b'])]))
    result=cg.audit_legacy_structure(structure);c=result['candidates'][0]
    assert c['petiole_signed_elevation_deg']<0 and c['observed_at'] is None
    assert c['compound_leaf_id'] is None and not c['eligible_state']


def test_prepare_light_delegates_existing_bridge(tmp_path,monkeypatch):
    from tools import plant_light_bridge
    seen={}
    def connect(*args,**kwargs):seen.update(kwargs)
    monkeypatch.setattr(plant_light_bridge,'connect',connect)
    import sys
    monkeypatch.setattr(sys,'argv',['compound_growth','prepare-light','--run','run','--plant','p','--session','s','--study','study.json','--out',str(tmp_path/'out')])
    cg.main();assert seen['execute'] is False


def test_model_generated_target_cannot_validate():
    states=[state(0),state(1),state(2)];states[-1]['reference_status']='model_generated'
    result=cg.evaluate_compound_forecasts(states,plan())
    assert all(r['status']=='unavailable' for r in result['metrics'])


def test_missing_sentinels_do_not_establish_identity_or_frame(tmp_path):
    p=bundle(tmp_path/'input');manifest=json.loads(p.read_text());manifest['frame_evidence']='unavailable'
    write_json(p,manifest);states,_=cg.load_history(p)
    assert not any(s['eligible_state'] for s in states)


def test_low_level_forecast_rejects_nonpositive_duration():
    with pytest.raises(StudyError):cg.forecast_persistence([state()],0)
    with pytest.raises(StudyError):cg.forecast_recent_change([state(0),state(1)],-1)
