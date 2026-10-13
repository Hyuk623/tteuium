"""Accepted Science contracts; explicit synthetic assumptions, no biological claims."""
from copy import deepcopy
import math

import numpy as np
import pytest

from tools import probabilistic_compound_growth as p
from tools import growth_calibration as g
from tools.leaf_light.common import StudyError, digest, file_hash, read_json, rows
from tools.tests.test_p3_growth_decisions import (
    fixture, fitted, beta_config, budget_config, light_response, clock, event_history,
)
from tools.tests.test_probabilistic_compound_growth import later_observation


def test_sub_base_pause_and_no_extrapolation():
    kwargs = dict(t_base_c=10,t_ref_c=20,m_max=2,upper_knot_c=40,
        intervals=[dict(start_day=0,end_day=30,input_value=7)],source_kind='user_assumed',
        source_ref='SYNTHETIC ONLY',applicability='synthetic')
    c = dict(clock=p.normalized_temperature_clock(**kwargs,lower_knot_c=5))
    assert p._clock(c,30) == 0
    c['clock']['intervals'][0]['input_value'] = 20
    assert p._clock(c,30) == 30
    for value in (4,41):
        c['clock']['intervals'][0]['input_value'] = value
        with pytest.raises(StudyError,match='outside supplied domain'): p._clock(c,30)
    with pytest.raises(StudyError,match='outside supplied domain'): p.normalized_temperature_clock(**kwargs)
    with pytest.raises(StudyError,match='below T_base'): p.normalized_temperature_clock(**kwargs,lower_knot_c=10)


@pytest.mark.parametrize('case',[
    'absorbed','tissue_config','tissue_origin','missing_reference','missing_day',
    'partial_day','midday','bad_normal','below_domain','above_domain',
    'shared_identity','wrong_role','missing_curve','legacy_coefficient',
])
def test_reference_contract_refusals(fixture,case):
    o,c = beta_config(fixture); light = c['light_response'] = light_response()
    if case == 'absorbed': light['light_basis']='absorbed'
    elif case == 'tissue_config': c['provenance']={'tissue_area_basis_ids':[light['basis_id']]}
    elif case == 'tissue_origin': o['provenance']={'area_basis_id':light['basis_id']}
    elif case == 'missing_reference': light.pop('reference')
    elif case == 'missing_day': light.pop('local_day')
    elif case == 'partial_day': light['local_day']['coverage']='partial'
    elif case == 'midday': light['local_day']['start_at']='2026-10-03T01:00:00+09:00'
    elif case == 'bad_normal': light['reference']['normal_unit_xyz']=[0,0,2]
    elif case == 'below_domain': light['applicability_interval']['min']=21
    elif case == 'above_domain': light['applicability_interval']['max']=19
    elif case == 'shared_identity': light['coefficients']['determinate_beta']['coefficient_id']=light['coefficients']['exponential']['coefficient_id']
    elif case == 'wrong_role': light['coefficients']['exponential']['role']='absolute_potential_maximum'
    elif case == 'missing_curve': light['coefficients'].pop('determinate_beta')
    elif case == 'legacy_coefficient': light['c_DLI']=.5
    if case in ('bad_normal','shared_identity','legacy_coefficient'):
        with pytest.raises(StudyError): p.sample_forecast(o,c)
    else:
        assert p.sample_forecast(o,c)['status']=='unavailable'


def test_distinct_equal_coefficients_and_complete_dst_day(fixture):
    o,c=beta_config(fixture); light=c['light_response']=light_response()
    light['local_day'].update(start_at='2026-03-08T00:00:00-05:00',end_at='2026-03-09T00:00:00-04:00',timezone='America/New_York')
    light['applicability_interval'].update(min=20,max=20)
    bank=p.sample_forecast(o,c)
    assert all(t['valid'] for t in bank['trajectories'])
    paths=bank['p3_environment_paths']
    assert {x['growth_curve'] for x in paths if 'growth_curve' in x}=={'exponential','determinate_beta'}
    values={'D_length_mm':4,'length_x_max_mm':8}
    assert p._size_response(values,c)['D_length_mm']==8
    assert p._size_response(values,c)['length_x_max_mm']==8
    beta=p._size_response(dict(values,growth_curve='determinate_beta'),c)
    assert beta['D_length_mm']==4 and beta['length_x_max_mm']==16


def test_mixed_unavailable_curves_keep_original_mass_and_exports(fixture):
    root,_,_=fixture; o,c=beta_config(fixture); c['light_response']=light_response()
    c['light_response']['coefficients']['determinate_beta']['c_DLI']=math.log(.1)
    low=c['parameter_particles'][0]; low['weight']=.5
    high=deepcopy(low); high.update(id='high_target',weight=.5)
    for name in ('residual','interval'):
        high['families'][name]['constants']['length_x_max_mm']['value']=80
    c['parameter_particles'].append(high)
    bank=p.sample_forecast(o,c); original=deepcopy(bank)
    assert all(t['valid'] and t['weight']==1/32 for t in bank['trajectories'])
    assert len({len(t['events']) for t in bank['trajectories']})==1
    available=sum(t['weight'] for t in bank['trajectories'] if t['blocks'][1]['growth']['length_x_max_mm']>2)
    assert 0<available<1
    summary=p.summarize_forecast(bank,dict(output_days=[11],quantiles=[.5]))
    key='/'.join(bank['trajectories'][0]['blocks'][1]['block_id'].split('/')[1:])
    row=next(r for r in summary if r['target_id']==key and r['quantity']=='rachis_arc_length_mm')
    assert row['value']==pytest.approx(8)
    assert row['available_weight']==available and row['ensemble_weight']==1
    assert row['available_fraction_of_ensemble']==available
    assert row['unavailable_reasons']==[dict(reason_code='dli_target_below_birth',weight=1-available,probability_of_ensemble=1-available)]
    assert next(r for r in summary if r['target_id']==key and r['quantity']=='occurrence')['value']==1
    for tr in bank['trajectories']:
        b=tr['blocks'][1]
        assert p._decode_block(tr,b,b['birth_day'])['rachis_arc_length_mm']==2
        if b['growth']['length_x_max_mm']<2:
            assert p._decode_block(tr,b,11)['rachis_arc_length_mm'] is None
    assert bank==original
    bank['summaries']=summary
    out=p.export_run(bank,root/'science_mixed_export')
    manifest=read_json(out/'manifest.json')
    assert all(file_hash(out/name)==sha for name,sha in manifest['output_hashes'].items())
    assert any('dli_target_below_birth' in r['growth_unavailable'] and r['axis_length_mm']=='' for r in rows(out/'block_states.csv'))
    assert any('dli_target_below_birth' in r['unavailable_reasons'] for r in rows(out/'summary.csv'))
    assert manifest['cross_organ_measurement_correlation']=='not_modeled'


def test_narrowing_exact_threshold_and_asymptote(fixture):
    state={'left_extent_mm':[2,4]}
    p._check_narrowing({'left_target_mm':3},state,None)
    p._check_narrowing({'left_target_mm':2},state,None)
    with pytest.raises(StudyError,match='scientific_evidence_missing'):
        p._check_narrowing({'left_target_mm':1.9},state,None)
    evidence=dict(source_kind='user_assumed',source_ref='SYNTHETIC narrowing')
    p._check_narrowing({'left_target_mm':1.9},state,evidence)
    _,o,c=fixture; c=deepcopy(c); c['light_response']=light_response()
    c['parameter_particles'][0]['families']['existing']['constants']['k_width']['value']=10
    tr=p.sample_forecast(o,c)['trajectories'][0]; b=tr['blocks'][0]
    result=p._decode_block(tr,b,30)
    target=b['growth']['left_target_mm']
    assert result['left_extent_mm']==pytest.approx([w+2*(target-w) for w in b['state']['left_extent_mm']])


def test_negative_width_unavailable_not_zero_growth(fixture):
    _,o,c=fixture; c=deepcopy(c); c['light_response']=light_response()
    c['light_response']['coefficients']['exponential']['c_DLI']=math.log(4)
    f=c['parameter_particles'][0]['families']['existing']
    f['constants']['left_target_mm']['value']=1
    assert p.sample_forecast(o,c)['status']=='unavailable'
    f['narrowing_assumption']=dict(source_kind='user_assumed',source_ref='SYNTHETIC narrowing')
    bank=p.sample_forecast(o,c)
    assert all(t['valid'] for t in bank['trajectories'])
    tr=bank['trajectories'][0]; b=tr['blocks'][0]
    assert p._decode_block(tr,b,0)['left_extent_mm']==b['state']['left_extent_mm']
    s=p._decode_block(tr,b,7)
    assert s['left_extent_mm'] is None and s['right_extent_mm'] is not None
    assert s['rachis_arc_length_mm'] is not None
    assert s['growth_unavailable']['left_extent_mm']=='dli_negative_width_target'


def test_unscaled_invalid_beta_still_fails(fixture):
    o,c=beta_config(fixture); c['light_response']=light_response()
    c['parameter_particles'][0]['families']['residual']['constants']['length_x_max_mm']['value']=1
    bank=p.sample_forecast(o,c)
    assert all(not t['valid'] for t in bank['trajectories'])
    assert all('x_max < x_birth' in t['status_reason'] for t in bank['trajectories'])


def test_existing_segments_hard_refuse_beta(fixture):
    o,c=beta_config(fixture)
    c['parameter_particles'][0]['axes']['stem']['segment_families']['p0:p1']='residual'
    with pytest.raises(StudyError,match='Existing segments'): p.sample_forecast(o,c)


def test_complete_semantic_taxonomy_and_l02():
    assert set(p.UNITS)<=set(g.COORDINATE_MEANING)
    for coordinate in ('azimuth_rad','elevation_rad','rotation_x_rad','k_rotation'):
        for source in ('L02','L02_output','normalized_first_moment'):
            with pytest.raises(StudyError,match='L02'):
                g._check_binding_meaning({'family':'azimuth_rotation'},'D',coordinate,{'equation_source':source})
    for coordinate in ('left_target_mm','birth_axis_length_mm','length_x_max_mm','wait_dev_days','length_a_e_dev_days','length_a_m_over_a_e'):
        with pytest.raises(StudyError,match='meaning mismatch'):
            g._check_binding_meaning({'family':'anchored_expansion'},'D',coordinate)


def test_clock_guard_precedes_binding(fixture,fitted,monkeypatch):
    _,_,c=fixture; c=deepcopy(c); c['clock']=clock()
    c['clock']['knots'][1]['multiplier']=.5
    def unexpected(*args,**kwargs): raise AssertionError('binding executed before clock check')
    monkeypatch.setattr(g,'_check_binding_meaning',unexpected)
    with pytest.raises(StudyError,match=r'm\(T_ref\)'):
        g.apply_parameter_set(fitted,c,c['environment_scenario']['values'])


@pytest.mark.parametrize('family',['lognormal_wait','azimuth_rotation'])
def test_frozen_adapter_rejects_stop_budget_and_l02(fixture,family):
    from tools.tests.test_growth_calibration import special_fixture
    root,_,_=fixture
    inputs=g.synthetic_fixture(root/('science_fit_'+family),replicates=3)
    obs,plan,treatments,evidence,_=special_fixture(inputs,family)
    if family=='lognormal_wait':
        plan['engine_bindings']=[dict(target_id=plan['targets'][0]['id'],kind='axis_stop',axis_id='stem',role='stop')]
        _,c=budget_config(fixture)
    else:
        plan['engine_bindings']=[dict(target_id=plan['targets'][0]['id'],kind='constant',family='existing',
            coordinate='rotation_z_rad',role='D',unit='rad',source_ref='L02_output')]
        c=deepcopy(fixture[2])
    pack=g.fit_growth_parameters(obs,evidence,plan,treatments)['parameter_set']
    assert pack is not None
    original=deepcopy(pack)
    with pytest.raises(StudyError,match='node_budget' if family=='lognormal_wait' else 'L02'):
        g.apply_parameter_set(pack,c,c['environment_scenario']['values'])
    assert pack==original


def test_joint_ess_stages_without_double_likelihood(fixture):
    o,c=budget_config(fixture); bank=p.sample_forecast(o,c)
    for i,tr in enumerate(bank['trajectories']):
        tr['blocks'][0]['growth']['D_length_mm']+=i/8
    original=deepcopy(bank); folder,assoc=later_observation(fixture,bank,days=7)
    model=dict(source_kind='user_assumed',source_ref='SYNTHETIC',fields=['rachis_arc_length_mm'],
        units={'rachis_arc_length_mm':'mm'},covariance=[[1]],numeric_tolerance=1e-9,
        events=[dict(kind='present',event_kind='truss',truss_observable='visible_bud',node_rank=3,parent_stem_id='stem',visibility='confirmed',through_day=7)])
    anchor=p.decode_trajectory(bank['trajectories'][0],[7])[0]['rachis_arc_length_mm']
    residuals=np.array([p.decode_trajectory(t,[7])[0]['rachis_arc_length_mm']-anchor for t in bank['trajectories']])
    geometry=np.exp(-.5*residuals**2)/32
    joint=geometry*np.array([t['n_max_drawn']['stem']==4 for t in bank['trajectories']])
    expected=joint/joint.sum(); geo=geometry/geometry.sum()
    result=p.update_forecast(bank,folder,assoc,model); d=result['conditioning_diagnostics']
    assert result['status']=='reweighted' and bank==original
    assert d['prior_ess']==pytest.approx(32)
    assert d['after_geometry_ess']==pytest.approx(1/sum(geo**2))
    assert d['after_geometry_then_events_ess']==pytest.approx(1/sum(expected**2))
    assert d['geometry_ess_loss']>0 and d['event_stage_ess_loss']>0
    assert d['conditioning_order']==['geometry','events']
    assert [t['weight'] for t in result['bank']['trajectories']]==pytest.approx(expected)
    assert [t['trajectory_id'] for t in result['bank']['trajectories']]==[t['trajectory_id'] for t in bank['trajectories']]
    assert d['cross_organ_measurement_correlation']=='not_modeled'
    no_model=p.update_forecast(bank,folder,assoc,None)['conditioning_diagnostics']
    assert no_model['after_geometry_ess'] is None and not no_model['final_weights_updated']
    model['events'][0]['node_rank']=99
    impossible=p.update_forecast(bank,folder,assoc,model)
    assert impossible['status']=='update_incompatible'
    assert impossible['conditioning_diagnostics']['after_geometry_then_events_ess']==0


def test_beta_reanchor_retains_remaining_increment_not_absolute_endpoint(fixture):
    o,c=beta_config(fixture); tr=p.sample_forecast(o,c)['trajectories'][0]; b=tr['blocks'][1]
    state=p._decode_block(tr,b,7); state['rachis_arc_length_mm']+=3
    rebased=p._remaining(b,7,state)
    assert p._beta_value(rebased['growth'],'length',state['rachis_arc_length_mm'],4)==pytest.approx(11)
