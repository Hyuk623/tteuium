"""Independent bookkeeping arithmetic and science/native refusal boundaries."""
from copy import deepcopy
import csv
import json
from pathlib import Path
import subprocess
import sys
import uuid

import pytest

from tools.vtc_growth_io import ROOT, ContractError, digest, sha, read_json
from tools.nutrient_reservoir import (SCHEMA, EC_UNIT, EQ_UNIT, replay, estimate, trays,
    modelled_split, feedback_gate, response_diagnostic, validate_registry, Missing)
from tools.nutrient_reservoir_records import audit_records, records_estimate
from tools.nutrient_reservoir_transaction import begin, finalize, BINDINGS

START, END = '2026-10-13T10:00:00+09:00', '2026-10-13T11:00:00+09:00'
EV = dict(source_kind='fixture_declared', source_ref='synthetic software fixture; not crop evidence')


def q(v, unit, error=0):
    return dict(value=v, unit=unit, abs_error=error, uncertainty_evidence=EV, **EV)


def tray(tid='T', plants=('p1', 'p2')):
    return dict(tray_id=tid, plant_ids=list(plants), has_plants=bool(plants),
                inner_length_mm=q(100, 'mm'), inner_width_mm=q(100, 'mm'),
                medium_volume_L=q(1, 'L'), medium_mix='fixture_1:1')


def base():
    return dict(schema_version=SCHEMA, scenario_id='fixture', interval_start=START, interval_end=END)


def pool(water=1, solute=2):
    return dict(water_L=q(water, 'L'), ec_equivalent=q(solute, EQ_UNIT))


def event(eid, kind, **kw):
    return dict(event_id=eid, kind=kind, at=END, tray_id='T', **EV, **kw)


def fixture():
    return dict(**base(), trays=[tray()], mixing_model='well_mixed_each_solution', mixing_evidence=EV,
        schedule_evidence=EV, initial={'T':dict(reservoir=pool(), medium=pool(), stored_ec_equivalent=q(.5, EQ_UNIT))},
        events=[event('in', 'supply', pool='reservoir', water_L=q(.5, 'L'), ec_ms_cm=q(2, EC_UNIT)),
                event('to_medium', 'transfer', pool='reservoir', to_pool='medium', water_L=q(.25, 'L')),
                event('a', 'adsorb', ec_equivalent=q(.3, EQ_UNIT)),
                event('r', 'release', ec_equivalent=q(.2, EQ_UNIT)),
                event('e', 'evaporate', pool='reservoir', water_L=q(.1, 'L')),
                event('t', 'plant_water', pool='medium', water_L=q(.2, 'L')),
                event('u', 'uptake', ec_equivalent=q(.4, EQ_UNIT)),
                event('out', 'remove', pool='medium', water_L=q(.1, 'L'))])


def observation(depth=100, ec=2, medium_ec=2):
    return dict(pool_depth_mm=q(depth, 'mm'), pool_ec_ms_cm=q(ec, EC_UNIT),
                medium_water_L=q(1, 'L'), medium_ec_ms_cm=q(medium_ec, EC_UNIT))


def interval_record(tid, end_ec):
    return dict(tray_id=tid, interval_start=START, interval_end=END, **EV,
        start=observation(), end=observation(90, end_ec), supplied_water_L=q(0, 'L'),
        removed_water_L=q(0, 'L'), supplied_ec_equivalent=q(0, EQ_UNIT), removed_ec_equivalent=q(0, EQ_UNIT))


def estimate_fixture():
    # Blank loses .1 L water and .2 EQ to net storage. Plant loses .5 EQ;
    # same medium volume => .3 EQ inferred plant uptake. Reservoir and medium separate.
    return dict(**base(), trays=[tray(), tray('B', ())], blank_tray_id='B',
        uncertainty_mode='absolute_bounds', observations={'T':interval_record('T', 5/3), 'B':interval_record('B', 2)},
        comparisons={'T':dict(blank_tray_id='B', same_medium_and_supply=True,
            exchange_scaling='medium_volume_ratio', evaporation_scale=q(1, 'dimensionless'),
            blank_evaporation_is_upper_bound=True, exchange_discrepancy_bound=q(0, EQ_UNIT),
            evaporation_discrepancy_bound=q(0, 'L'), **EV)})


def test_bidirectional_accounting_and_no_input_mutation():
    req=fixture(); original=deepcopy(req); result=replay(req)
    assert req == original and result['status']=='available_prescribed_accounting'
    final=result['final_state']['T']; c=result['closure'][0]
    assert final['stored_ec_equivalent']==pytest.approx(.6)
    assert final['reservoir']['water_L']==pytest.approx(1.15)
    assert final['reservoir']['ec_equivalent']==pytest.approx(2.5)
    assert final['medium']['water_L']==pytest.approx(.95)
    assert final['medium']['ec_equivalent']==pytest.approx(2-2*.1/1.05)
    assert c['water_residual_L']==pytest.approx(0, abs=1e-14)
    assert c['ec_equivalent_residual']==pytest.approx(0, abs=1e-14)
    assert c['prescribed_uptake_ec_equivalent']==.4
    assert result['native_causality'] is False


def test_blank_prescribed_no_uptake_and_declining_adsorption_fixture():
    req=fixture(); req['trays']=[tray('T', ())]
    req['events']=[event('a1','adsorb',ec_equivalent=q(.4,EQ_UNIT)), event('a2','adsorb',ec_equivalent=q(.1,EQ_UNIT)),
                   event('r','release',ec_equivalent=q(.2,EQ_UNIT))]
    result=replay(req)
    assert result['final_state']['T']['stored_ec_equivalent']==pytest.approx(.8)
    assert result['closure'][0]['prescribed_uptake_ec_equivalent']==0
    # A declining prescribed schedule is not an identified saturation law.
    assert result['biological_validation']=='not_established'


@pytest.mark.parametrize('field', ['stored_ec_equivalent','medium','reservoir'])
def test_initial_hidden_states_never_default(field):
    req=fixture(); req['initial']['T'].pop(field)
    result=replay(req); assert result['status']=='unavailable' and result['final_state'] is None


@pytest.mark.parametrize('fault', ['negative','nan','inf','bool','overdraw_solute','overdraw_water','overdraw_store',
    'duplicate_event','late_event','before_start','naive_time','unknown_tray','unknown_pool','self_transfer','dry_pool',
    'zero_dimension','duplicate_plant','cross_tray','blank_plant','no_mix','missing_schedule','no_source','blank_uptake'])
def test_invalid_replay_refused_without_partial_result(fault):
    req=fixture()
    if fault in {'negative','nan','inf','bool'}:
        req['initial']['T']['stored_ec_equivalent']['value']={'negative':-1,'nan':float('nan'),'inf':float('inf'),'bool':True}[fault]
    if fault=='overdraw_solute':req['events']=[event('x','adsorb',ec_equivalent=q(3,EQ_UNIT))]
    if fault=='overdraw_water':req['events']=[event('x','evaporate',pool='medium',water_L=q(3,'L'))]
    if fault=='overdraw_store':req['events']=[event('x','release',ec_equivalent=q(1,EQ_UNIT))]
    if fault=='duplicate_event':req['events'].append(deepcopy(req['events'][-1]))
    if fault=='late_event':req['events'][-1]['at']='2026-10-13T12:00:00+09:00'
    if fault=='before_start':req['events'][0]['at']='2026-10-13T09:00:00+09:00'
    if fault=='naive_time':req['events'][0]['at']='2026-10-13T10:00:00'
    if fault=='unknown_tray':req['events'][0]['tray_id']='other'
    if fault=='unknown_pool':req['events'][0]['pool']='other'
    if fault=='self_transfer':req['events'][1]['to_pool']='reservoir'
    if fault=='dry_pool':req['events']=[event('x','evaporate',pool='medium',water_L=q(1,'L'))]
    if fault=='zero_dimension':req['trays'][0]['inner_length_mm']['value']=0
    if fault=='duplicate_plant':req['trays'][0]['plant_ids']=['p1','p1']
    if fault=='cross_tray':req['trays'].append(tray('X'))
    if fault=='blank_plant':req['trays'][0]['has_plants']=False
    if fault=='no_mix':req['mixing_model']='lumped'
    if fault=='missing_schedule':req.pop('schedule_evidence')
    if fault=='no_source':req['events'][0]['source_ref']=''
    if fault=='blank_uptake':req['trays']=[tray('T',())]
    if fault=='missing_schedule':assert replay(req)['status']=='unavailable'
    else:
        with pytest.raises((ContractError,ValueError)):replay(req)


def test_estimate_signs_blank_release_and_evaporation_bias():
    req=estimate_fixture(); result=estimate(req); plant=result['rows'][0]
    assert plant['uptake_ec_equivalent']==pytest.approx(.3)
    assert plant['water_uptake_lower_estimate']['value']==pytest.approx(0)
    assert result['rows'][1]['net_adsorption_minus_release']['value']==pytest.approx(.2)
    req['observations']['B']['end']['pool_ec_ms_cm']['value']=2.5  # blank release .25
    plant=estimate(req)['rows'][0]
    assert plant['blank_net_adsorption_minus_release']['value']==pytest.approx(-.25)
    assert plant['uptake_ec_equivalent']==pytest.approx(.75)
    req['observations']['T']['end']['pool_depth_mm']['value']=80
    assert estimate(req)['rows'][0]['water_uptake_lower_estimate']['value']==pytest.approx(.1)
    req['comparisons']['T']['evaporation_scale']['value']=.5
    assert estimate(req)['rows'][0]['water_uptake_lower_estimate']['value']==pytest.approx(.15)


def test_negative_residual_is_never_clipped_or_called_uptake():
    req=estimate_fixture(); req['observations']['T']['end']['pool_ec_ms_cm']['value']=3
    row=estimate(req)['rows'][0]
    assert row['signed_uptake_residual']['value'] < 0 and row['uptake_ec_equivalent'] is None


@pytest.mark.parametrize('fault',['blank','volume','ec','medium','uncertainty','uncertainty_evidence','comparability','discrepancy'])
def test_missing_evidence_uptake_unavailable(fault):
    req=estimate_fixture()
    if fault=='blank':req.pop('blank_tray_id')
    if fault=='volume':req['observations']['T']['start'].pop('pool_depth_mm')
    if fault=='ec':req['observations']['T']['end'].pop('pool_ec_ms_cm')
    if fault=='medium':req['observations']['T']['start'].pop('medium_water_L')
    if fault=='uncertainty':req['observations']['B']['end']['pool_ec_ms_cm'].pop('abs_error')
    if fault=='uncertainty_evidence':req['observations']['B']['end']['pool_ec_ms_cm'].pop('uncertainty_evidence')
    if fault=='comparability':req['comparisons']={}
    if fault=='discrepancy':req['comparisons']['T'].pop('exchange_discrepancy_bound')
    result=estimate(req)
    assert result['status']=='unavailable' and result['uptake_ec_equivalent'] is None


def test_bound_propagation_includes_ec_depth_and_blank_mismatch():
    req=estimate_fixture()
    req['observations']['T']['end']['pool_ec_ms_cm']['abs_error']=.1
    req['observations']['T']['end']['pool_depth_mm']['abs_error']=1
    req['comparisons']['T']['exchange_discrepancy_bound']['value']=.05
    row=estimate(req)['rows'][0]['signed_uptake_residual']
    assert row['lower']==pytest.approx(.3-(.9*.1+.01*5/3+.01*.1)-.05)
    assert row['upper']==pytest.approx(.3+(.9*.1+.01*5/3-.01*.1)+.05)
    assert 'not_probability' in row['uncertainty_kind']


def demand():
    return dict(scenario_id='fixture', interval_start=START, interval_end=END, unit='gC', values={'p1':1,'p2':3}, **EV)


def test_split_is_modelled_and_sums_to_tray_total():
    row=estimate(estimate_fixture())['rows'][0]
    result=modelled_split(tray(), row, demand())
    assert [r['uptake_ec_equivalent'] for r in result['rows']]==pytest.approx([.075,.225])
    assert all(r['allocation_kind']=='modelled_split' and not r['element_resolved'] for r in result['rows'])
    d=demand();d['values']={'p1':0,'p2':0}
    assert modelled_split(tray(),row,d)['status']=='unavailable'
    row['uptake_ec_equivalent']=None
    assert modelled_split(tray(),row,d)['status']=='unavailable'


@pytest.mark.parametrize('fault',['missing','negative','wrong_scenario','wrong_interval'])
def test_bad_split(fault):
    d=demand();row=estimate(estimate_fixture())['rows'][0]
    if fault=='missing':d['values'].pop('p1')
    if fault=='negative':d['values']['p1']=-1
    if fault=='wrong_scenario':d['scenario_id']='x'
    if fault=='wrong_interval':d['interval_end']='2026-10-13T12:00:00+09:00'
    with pytest.raises(ContractError):modelled_split(tray(),row,d)


def registry():
    # Complete arithmetic-only test contract, deliberately not a selected biological law.
    par=lambda v:dict(value=v,unit='dimensionless',uncertainty='fixture_exact',**EV)
    return dict(schema_version='tray-nutrient-response-registry-1', law_id='test_only_triangle', law_version='1',
        ec_input_definition='fixture_instant_pool', ec_unit=EC_UNIT, time_support='fixture_instant',
        temperature_convention='fixture_no_temperature_model', deficiency_equation='f=s*x for x<=1',
        high_ec_equation='f=s*(2-x) for 1<x<=2', breakpoint_definitions='x=EC/1mS_cm, peak=1',
        domain='0<=EC<=2mS/cm; reject outside; arithmetic test only',
        coupling_site='gross_assimilation_once_before_allocation', exchange_contract_ref='prescribed fixture',
        initial_pool_contract_ref='explicit fixture', review=dict(status='fixture_only',**EV),fixture=True,
        scenarios={'none':{'s':par(1)},'moderate':{'s':par(.8)},'strong':{'s':par(.4)}})


def test_injected_declared_low_and_high_ec_scenarios_stay_diagnostic():
    def triangle(value,sid,reg):
        assert 0<=value<=2
        return reg['scenarios'][sid]['s']['value']*(value if value<=1 else 2-value)
    for ec in (.25,1.75):
        obs=dict(**q(ec,EC_UNIT),input_definition='fixture_instant_pool',time_support='fixture_instant',
                 temperature_convention='fixture_no_temperature_model')
        rows=[response_diagnostic(obs,sid,registry(),triangle,('test_only_triangle','1'),True) for sid in ('none','moderate','strong')]
        assert [r['f_nut'] for r in rows]==[None,.2,.1]
        assert all(not r['native_causality'] and not r['growth_feedback_applied'] for r in rows)
        assert len({r['scenario_id'] for r in rows})==3


def test_disabled_feedback_never_calls_evaluator_or_defaults_missing_ec_to_one():
    def bad(*args):raise AssertionError('disabled evaluator called')
    assert response_diagnostic(None,'moderate',None,bad)['engine_action']=='unchanged'
    assert response_diagnostic(None,'moderate',None,bad,evaluate=True)['f_nut'] is None
    assert feedback_gate()==dict(ENABLE_NUTRIENT_FEEDBACK=False,engine_action='unchanged')
    with pytest.raises(ContractError):feedback_gate(True)


@pytest.mark.parametrize('field',['law_id','deficiency_equation','high_ec_equation','breakpoint_definitions','review','scenarios'])
def test_incomplete_registry_refused(field):
    reg=registry();reg.pop(field)
    with pytest.raises(ContractError):validate_registry(reg)


def transaction_fixture():
    req=fixture(); cand=replay(req)
    proposal=dict(schema_version='tray-resource-protocol-fixture-1',fixture=True,proposal_id='P1',run_id='R',
        scenario_id='fixture',tray_membership={'T':['p1','p2']},interval_start=START,interval_end=END,
        issued_at=START,expires_at=END,**{k:digest(k) for k in BINDINGS if k.endswith('_sha256')})
    proposal['reservoir_state_sha256']=cand['initial_sha256']
    native=dict(fixture=True,native_causality=False,predecessor_sha256=proposal['native_state_sha256'],state={'fixture_carbon':.1})
    response=dict(proposal_id='P1',transaction_id=digest(proposal),binding={k:proposal[k] for k in BINDINGS},
        expires_at=END,ENABLE_NUTRIENT_FEEDBACK=False,f_nut=None,native_candidate_sha256=digest(native),
        reservoir_request_sha256=digest(req))
    return proposal,response,native,req


@pytest.fixture
def build_dir():
    folder=ROOT/'build'/('test_reservoir_'+uuid.uuid4().hex)
    folder.mkdir()
    return folder


def test_interrupted_retried_joint_commit_is_idempotent(build_dir):
    p,r,n,req=transaction_fixture();folder=build_dir/'tx'
    tx=begin(folder,p);assert begin(folder,p)==tx
    assert finalize(folder,r,n,req,END,stage_only=True)['status']=='fixture_staged_not_committed'
    assert not (folder/'committed').exists()
    done=finalize(folder,r,n,req,END)
    assert done==finalize(folder,r,n,req,'2026-10-14T00:00:00+09:00')
    assert len(list(folder.glob('committed/joint_commit.json')))==1
    assert req==fixture() and done['reservoir_candidate']['closure'][0]['prescribed_uptake_ec_equivalent']==.4


@pytest.mark.parametrize('fault',['stale','timeout','response_expiry','wrong_id','changed_candidate','changed_request','feedback',
                                'native_claim','begin_conflict','partial_conflict','commit_conflict'])
def test_transaction_refusals(build_dir,fault):
    p,r,n,req=transaction_fixture();folder=build_dir/'tx';begin(folder,p)
    now=END
    if fault=='partial_conflict':finalize(folder,r,n,req,END,stage_only=True)
    if fault=='commit_conflict':finalize(folder,r,n,req,END)
    if fault=='stale':r['binding']['geometry_sha256']=digest('different')
    if fault=='timeout':now='2026-10-13T12:00:00+09:00'
    if fault=='response_expiry':r['expires_at']='2026-10-13T12:00:00+09:00'
    if fault=='wrong_id':r['proposal_id']='other'
    if fault=='changed_candidate':n['state']['fixture_carbon']=.2
    if fault=='changed_request':req['events']=[]
    if fault=='feedback':r['ENABLE_NUTRIENT_FEEDBACK']=True
    if fault=='native_claim':n['native_causality']=True
    if fault in {'partial_conflict','commit_conflict'}:r['note']='different immutable response'
    if fault=='begin_conflict':
        p['proposal_id']='other'
        with pytest.raises(ContractError):begin(folder,p)
    else:
        with pytest.raises(ContractError):finalize(folder,r,n,req,now)
    if fault!='commit_conflict':assert not (folder/'committed').exists()


def test_real_records_read_only_and_no_identity_or_time_invention():
    path=ROOT/'data/records/env_20261013/nutrient_log_20261013.csv';before=sha(path)
    result=audit_records(path)
    values=[r['value'] for r in result['normalized_rows'] if r['field']=='ec_us_cm']
    assert values==[1.52,None,1.649,1.675,1.691]
    assert result['uptake_ec_equivalent'] is None and sha(path)==before
    assert any(i['reason']=='exact_aware_time_unavailable' for i in result['issues'])
    assert any(i['reason']=='blank_tray_unavailable' for i in result['issues'])


def test_template_is_not_treated_as_zero_or_ready():
    root=ROOT/'build/nutrient_records_template'
    result=audit_records(root/'nutrient_log.csv',root/'tray_spec.csv')
    assert result['issues'] and result['uptake_ec_equivalent'] is None
    assert any(i['reason']=='duplicate_or_placeholder_plant' for i in result['issues'])


def test_cli_actual_replay_and_output_refusal(build_dir):
    source=build_dir/'request.json';source.write_text(json.dumps(fixture()),encoding='utf-8')
    cmd=[sys.executable,'-X','utf8','-m','tools.nutrient_reservoir','replay','--request',str(source),'--out',str(build_dir/'cli')]
    first=subprocess.run(cmd,cwd=ROOT,capture_output=True,text=True)
    assert first.returncode==0,first.stderr
    assert read_json(build_dir/'cli/result.json')['status']=='available_prescribed_accounting'
    assert subprocess.run(cmd,cwd=ROOT,capture_output=True).returncode==2


def record_fixture(folder):
    spec=folder/'tray_spec.csv';log=folder/'nutrient_log.csv'
    specs=[];records=[]
    for tid,ids,end_ec in [('T','p1;p2',5/3),('B','',2)]:
        specs.append(dict(tray_id=tid,has_plants='TRUE' if ids else 'FALSE',plant_ids=ids,
            tray_inner_length_mm=100,tray_inner_width_mm=100,medium_mix_vermiculite_perlite='fixture_1:1',
            medium_volume_per_pot_ml=1000,pot_count=1,source_kind='measured'))
        for at,depth,ec in [(START,100,2),(END,90,end_ec)]:
            records.append(dict(tray_id=tid,event_time=at,event_time__status='measured',event_kind='measure_only',
                supply_volume_ml=0,supply_ec_ms_cm='',supply_ec__status='unavailable',pool_depth_mm_before=depth,
                pool_depth_mm_after=depth,pool_ec_ms_cm=ec,pool_ec__status='measured',removed_volume_ml=0,source_kind='measured'))
    for path,data in [(spec,specs),(log,records)]:
        with path.open('w',newline='',encoding='utf-8') as f:
            writer=csv.DictWriter(f,fieldnames=list(data[0]));writer.writeheader();writer.writerows(data)
    req=estimate_fixture();req.pop('trays');req.pop('observations')
    supplement=dict(record_sha256=sha(log),tray_spec_sha256=sha(spec),request=req,bindings={},bounds={})
    for tid,startline,endline in [('T',2,3),('B',4,5)]:
        supplement['bindings'][tid]=dict(start_line=startline,end_line=endline,event_lines=[endline],
            start_medium_water_L=q(1,'L'),end_medium_water_L=q(1,'L'),
            start_medium_ec_ms_cm=q(2,EC_UNIT),end_medium_ec_ms_cm=q(2,EC_UNIT),complete_event_coverage_evidence=EV)
    audit=audit_records(log,spec)
    for cell in audit['normalized_rows']:
        name=spec.name if cell['source_sha256']==sha(spec) else log.name
        supplement['bounds'][f"{name}:{cell['record_line']}:{cell['field']}"]=dict(abs_error=0,**EV)
    return log,spec,supplement


def test_actual_csv_to_bound_estimate_and_source_preservation(build_dir):
    log,spec,supplement=record_fixture(build_dir);before=(sha(log),sha(spec))
    result=records_estimate(log,spec,supplement)
    assert result['result']['rows'][0]['uptake_ec_equivalent']==pytest.approx(.3)
    assert result['request']['trays'][0]['medium_volume_L']['value']==1
    assert before==(sha(log),sha(spec))
    inp=build_dir/'supplement.json';inp.write_text(json.dumps(supplement),encoding='utf-8')
    run=subprocess.run([sys.executable,'-m','tools.nutrient_reservoir','records-estimate','--request',str(inp),
        '--log',str(log),'--tray-spec',str(spec),'--out',str(build_dir/'records_cli')],cwd=ROOT,capture_output=True,text=True)
    assert run.returncode==0,run.stderr
    assert read_json(build_dir/'records_cli/result.json')['status']=='conditional_residuals'


@pytest.mark.parametrize('fault',['stale','endpoint','coverage','bounds','medium','unavailable_status','contradictory_event'])
def test_csv_binding_refuses_missing_or_changed_evidence(build_dir,fault):
    log,spec,s=record_fixture(build_dir)
    if fault=='stale':s['record_sha256']=digest('stale')
    if fault=='endpoint':s['bindings']['T']['end_line']=5
    if fault=='coverage':s['bindings']['T']['event_lines']=[]
    if fault=='bounds':s['bounds'].pop('nutrient_log.csv:3:pool_ec_ms_cm')
    if fault=='medium':s['bindings']['T']['end_medium_water_L']=None
    if fault in {'unavailable_status','contradictory_event'}:
        data=list(csv.DictReader(log.open(encoding='utf-8')))
        if fault=='unavailable_status':data[1]['pool_ec__status']='unavailable'
        else:data[1]['supply_volume_ml']='1'
        with log.open('w',newline='',encoding='utf-8') as f:
            w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
        s['record_sha256']=sha(log)
    if fault=='medium':
        assert records_estimate(log,spec,s)['result']['status']=='unavailable'
    else:
        with pytest.raises(ContractError):records_estimate(log,spec,s)


def test_csv_unknown_negative_nan_status_preserves_raw_and_reports(build_dir):
    log,spec,s=record_fixture(build_dir)
    data=list(csv.DictReader(log.open(encoding='utf-8')))
    data[0]['pool_ec_ms_cm']='NaN';data[1]['pool_ec__status']='guessed'
    data[2]['supply_volume_ml']='-1'
    with log.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    before=sha(log);audit=audit_records(log,spec)
    assert any(i['reason']=='invalid_numeric_value' for i in audit['issues'])
    assert any(i['reason']=='unknown_status' for i in audit['issues'])
    assert audit['raw_records'][0]['pool_ec_ms_cm']=='NaN' and sha(log)==before


def test_csv_supply_and_removal_units_totals_and_half_open_interval(build_dir):
    log,spec,s=record_fixture(build_dir)
    old=list(csv.DictReader(log.open(encoding='utf-8')));data=[]
    for idx,tid in [(0,'T'),(2,'B')]:
        # Supply at start belongs to initial stock, so it must not be counted twice.
        start=deepcopy(old[idx]);start.update(event_kind='supply',supply_volume_ml='500',supply_ec_ms_cm='2',supply_ec__status='measured')
        supply=deepcopy(start);supply.update(event_time='2026-10-13T10:20:00+09:00',supply_volume_ml='100')
        remove=deepcopy(start);remove.update(event_time='2026-10-13T10:40:00+09:00',event_kind='remove',supply_volume_ml='0',removed_volume_ml='50')
        lineno=len(data)+2;data.extend([start,supply,remove,old[idx+1]])
        s['bindings'][tid].update(start_line=lineno,end_line=lineno+3,event_lines=[lineno+1,lineno+2,lineno+3],
            removed_ec_by_line={str(lineno+2):q(2,EC_UNIT)})
    with log.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=list(data[0]));w.writeheader();w.writerows(data)
    s['record_sha256']=sha(log)
    for c in audit_records(log,spec)['normalized_rows']:
        name=spec.name if c['source_sha256']==sha(spec) else log.name
        s['bounds'][f"{name}:{c['record_line']}:{c['field']}"]=dict(abs_error=0,**EV)
    result=records_estimate(log,spec,s)
    obs=result['request']['observations']['T']
    assert obs['supplied_water_L']['value']==pytest.approx(.1)
    assert obs['removed_water_L']['value']==pytest.approx(.05)
    assert obs['supplied_ec_equivalent']['value']==pytest.approx(.2)
    assert obs['removed_ec_equivalent']['value']==pytest.approx(.1)
    assert result['result']['rows'][0]['uptake_ec_equivalent']==pytest.approx(.3)


@pytest.mark.parametrize('fault',['law_id','out_of_range','missing_ec','ec_semantics','parameter_null','parameter_source'])
def test_injected_response_boundary_refuses_unsafe_inputs(fault):
    reg=registry();obs=dict(**q(1,EC_UNIT),input_definition=reg['ec_input_definition'],
                          time_support=reg['time_support'],temperature_convention=reg['temperature_convention'])
    law=('test_only_triangle','1');func=lambda *args:.5
    if fault=='law_id':law=('different','1')
    if fault=='out_of_range':func=lambda *args:1.1
    if fault=='missing_ec':obs=None
    if fault=='ec_semantics':obs['input_definition']='medium_mean'
    if fault=='parameter_null':reg['scenarios']['moderate']['s']['value']=None
    if fault=='parameter_source':reg['scenarios']['moderate']['s'].pop('source_ref')
    if fault in {'missing_ec','parameter_null'}:
        assert response_diagnostic(obs,'moderate',reg,func,law,True)['status']=='unavailable'
    else:
        with pytest.raises(ContractError):response_diagnostic(obs,'moderate',reg,func,law,True)


def test_existing_transaction_cannot_bypass_output_boundary(build_dir,monkeypatch):
    import tools.nutrient_reservoir_transaction as tx
    p,r,n,req=transaction_fixture();folder=build_dir/'tx';begin(folder,p)
    monkeypatch.setattr(tx,'ROOT',build_dir)
    with pytest.raises(ContractError,match='below project build'):begin(folder,p)
    with pytest.raises(ContractError,match='below project build'):finalize(folder,r,n,req,END)
