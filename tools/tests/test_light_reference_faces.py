"""Actual direct transport -> reviewed faces/reference attachment -> independent consumer."""
from copy import deepcopy
from pathlib import Path

import pytest

from tools import hierarchical_light as hierarchy
from tools import light_growth_bridge as bridge
from tools.hierarchical_light_demo import synthetic_inputs
from tools.leaf_light.common import StudyError, file_hash, read_json, rows, write_json, write_rows
from tools.light_growth_consumer import load_tables
from tools.reference_dli_demo import create_inputs, write_readings
from tools.reference_dli import prepare_record, save_result


def request_fixture(folder: Path, opposite=True, mapped=True, second_fraction=1., zero=False) -> Path:
    source = synthetic_inputs(folder/'optical_inputs', groups=())
    scene = read_json(source.parent/'scene.json')
    other = deepcopy(scene['fixtures'][0]); other['fixture_id'] = 'LED_other'
    other['emitting_center_grow_mm']['value'] = [0., 0., -1000. if opposite else 1000.]
    other['aim_tilt_deg']['value'] = 180. if opposite else 0.
    if zero:
        scene['fixtures'][0]['photon_flux_umol_s']['value'] = 0.
        other['photon_flux_umol_s']['value'] = 0.
    scene['fixtures'].append(other); write_json(source.parent/'scene.json', scene)
    hierarchy.prepare_subset_cases(source, folder/'prepared')
    hierarchy.calculate_direct(folder/'prepared', folder/'legacy')
    schedule = dict(timezone='Asia/Seoul', provenance={'source':'synthetic'}, fixed_optics_beam_spectrum=True,
        fixtures={fid: [dict(start_hhmm='00:00', end_hhmm='24:00', output_fraction=fraction)] if fraction is not None else None
                  for fid, fraction in [('synthetic_LED',1.),('LED_other',second_fraction)]})
    start='2026-10-04T00:00:00+09:00'; end='2026-10-05T00:00:00+09:00'
    request = dict(schema_version='light-growth-1', run_id='synthetic_face_test', schedule=schedule,
        interval=dict(start_at=start, end_at=end), limits=dict(max_transport_calls=2,max_receiver_emitter_pairs=100000,max_schedule_minutes=4000),
        snapshots=[dict(geometry_snapshot_id='g', prepared_run='prepared', full_scene_results='legacy',
            board_frame_ids={'P1':'board_P1'}, valid_from=start,valid_until=end,geometry_mode='held_current_geometry_scenario')])
    if mapped:
        evidence = folder/'face_review.json'
        write_json(evidence, dict(source_kind='synthetic_test_only', note='Explicit artificial normal/adaxial review; not observed leaves'))
        request['face_mappings'] = [dict(mapping_id='face_'+r['triangle_id'], geometry_snapshot_id='g',
            plant_instance_id=r['plant_id'], session_id=r['session_id'], organ_id=r['organ_id'],leaflet_id=r['leaflet_id'],triangle_id=r['triangle_id'],
            geometry_sha256=file_hash(folder/'prepared/leaf_surfaces.csv'), normal_biological_face='adaxial',
            review_status='reviewed', reviewer='synthetic_fixture', evidence_path=evidence.name,evidence_sha256=file_hash(evidence))
            for r in rows(folder/'prepared/leaf_surfaces.csv')]
    path=folder/'request.json'; write_json(path, request); return path


def add_reference(folder: Path, request: Path, monkeypatch, mode='available') -> Path:
    import tools.leaf_light.common as common
    monkeypatch.setattr(common,'BUILD',folder)
    source=folder/'reference_inputs'; fixture=create_inputs(source)
    p=fixture['position']; p['plant_association']['plant_instance_ids']=['P1']
    if mode=='out_of_domain':
        write_readings(source/'reference_readings.csv',[dict(r,ppfd_umol_m2_s=1000.) for r in fixture['readings']])
    if mode=='unavailable': p['levelled']=False
    write_json(source/'reference_position.json',p)
    record,audit=prepare_record(source/'reference_position.json', source/'schedule.json',route='spot_schedule',
        readings_path=source/'reference_readings.csv',survey_path=source/'spot_survey.csv')
    save_result(record,audit,folder/'reference_result')
    result=folder/'reference_result/reference_dli.json'
    data=read_json(request);data['reference_dli']=dict(path=str(result),sha256=file_hash(result));write_json(request,data)
    return result


@pytest.mark.parametrize('opposite,expected',[(True,'both'),(False,'adaxial_only')])
def test_actual_two_fixture_faces_and_p4_metadata_gate(tmp_path,opposite,expected):
    request=request_fixture(tmp_path,opposite=opposite)
    folder=tmp_path/'package';bridge.build_package(request,folder)
    check=bridge.validate_growth_light_package(folder);assert check['valid'],check
    samples=load_tables(folder)['light_samples.csv']
    total=next(r for r in samples if r['fixture_id']=='all' and r['time_step_id']!='full_output')
    assert total['illuminated_faces']==expected
    contributions=[r for r in samples if r['sample_id']==total['sample_id'] and r['time_step_id']==total['time_step_id'] and r['fixture_id']!='all']
    assert total['received_ppfd_umol_m2_s']==pytest.approx(sum(r['received_ppfd_umol_m2_s'] for r in contributions),rel=1e-9,abs=1e-10)
    from tools import fsp_carbon_diagnostic as p4
    if opposite:
        with pytest.raises(p4.MissingEvidence) as exc:p4._combined_face({},contributions)
        assert exc.value.code=='two_sided_exchange_unavailable'
    else:
        assert p4._combined_face({},contributions)=='adaxial_only'
    bridge.split_canopy_results(folder,'P1',tmp_path/'split')
    assert bridge.validate_growth_light_package(tmp_path/'split')['valid']


@pytest.mark.parametrize('mapped,zero,fraction,expected',[
    (False,False,1.,None),(True,True,1.,None),(True,False,None,None),(True,False,0.,'adaxial_only')])
def test_mapping_darkness_and_unknown_schedule_do_not_invent_faces(tmp_path,mapped,zero,fraction,expected):
    request=request_fixture(tmp_path,mapped=mapped,zero=zero,second_fraction=fraction)
    folder=tmp_path/'package';bridge.build_package(request,folder)
    check=bridge.validate_growth_light_package(folder);assert check['valid'],check
    totals=[r for r in load_tables(folder)['light_samples.csv'] if r['fixture_id']=='all' and r['time_step_id']!='full_output']
    assert all(r['illuminated_faces']==expected for r in totals)


@pytest.mark.parametrize('mode',['available','out_of_domain','unavailable'])
def test_hashed_reference_attachment_preserved_in_package_and_split(tmp_path,monkeypatch,mode):
    request=request_fixture(tmp_path)
    add_reference(tmp_path,request,monkeypatch,mode)
    folder=tmp_path/'package';bridge.build_package(request,folder)
    check=bridge.validate_growth_light_package(folder);assert check['valid'],check
    mapping=read_json(folder/'consumer_mapping.json')['growth']['reference_dli']
    assert mapping['status']==('available' if mode=='available' else 'unavailable')
    assert mapping['value']==pytest.approx(11.52) if mode=='available' else mapping['value'] is None
    record=read_json(folder/'reference_dli/reference_dli.json')
    if mode=='out_of_domain':assert record['days']['2026-10-04']['dli_mol_m2_day']==pytest.approx(57.6)
    bridge.split_canopy_results(folder,'P1',tmp_path/'split')
    split=bridge.validate_growth_light_package(tmp_path/'split');assert split['valid'],split
    assert file_hash(folder/'reference_dli/reference_dli.json')==file_hash(tmp_path/'split/reference_dli/reference_dli.json')


@pytest.mark.parametrize('mutation',['face','face_evidence','reference_mapping','reference_result','reference_context'])
def test_independent_package_consumer_rejects_rehashed_false_claims(tmp_path,monkeypatch,mutation):
    request=request_fixture(tmp_path)
    add_reference(tmp_path,request,monkeypatch)
    folder=tmp_path/'package';bridge.build_package(request,folder)
    if mutation=='face':
        table=load_tables(folder)['light_samples.csv'];table[0]['illuminated_faces']='abaxial_only'
        write_rows(folder/'light_samples.csv',table,[c['name'] for c in bridge.SCHEMA['tables']['light_samples.csv']['columns']])
    elif mutation=='face_evidence':
        data=read_json(folder/'face_mappings.json');next(iter(data['mappings'].values()))['normal_biological_face']='abaxial'
        write_json(folder/'face_mappings.json',data)
    elif mutation=='reference_mapping':
        data=read_json(folder/'consumer_mapping.json');data['growth']['reference_dli']['value']=12.
        write_json(folder/'consumer_mapping.json',data)
    elif mutation=='reference_result':
        data=read_json(folder/'reference_dli/reference_dli.json');data['value']=12.
        write_json(folder/'reference_dli/reference_dli.json',data)
        envelope=read_json(folder/'reference_channel.json');envelope['result_ref']['sha256']=file_hash(folder/'reference_dli/reference_dli.json')
        write_json(folder/'reference_channel.json',envelope)
    package=read_json(folder/'package.json')
    if mutation=='reference_context':package['reference_context_plant_instance_ids'].append('unverified_plant')
    for name in package['artifact_hashes']:package['artifact_hashes'][name]=file_hash(folder/name)
    write_json(folder/'package.json',package)
    assert not bridge.validate_growth_light_package(folder)['valid']


def test_reviewed_face_annotation_leaves_all_transport_numbers_identical(tmp_path):
    request=request_fixture(tmp_path)
    original=read_json(request); unannotated=deepcopy(original);unannotated.pop('face_mappings')
    other=tmp_path/'unannotated_request.json';write_json(other,unannotated)
    bridge.build_package(other,tmp_path/'unannotated')
    bridge.build_package(request,tmp_path/'annotated')
    left=load_tables(tmp_path/'unannotated');right=load_tables(tmp_path/'annotated')
    for name,spec in bridge.SCHEMA['tables'].items():
        numeric=[c['name'] for c in spec['columns'] if c['type']=='number']
        assert len(left[name])==len(right[name])
        for a,b in zip(left[name],right[name]):
            assert {k:a[k] for k in numeric}=={k:b[k] for k in numeric}


@pytest.mark.parametrize('field,value,reason',[
    ('review_status','pending','reviewed_biological_face_mapping_required'),
    ('geometry_sha256','0'*64,'stale_face_mapping_geometry'),
    ('evidence_sha256','0'*64,'stale_face_mapping_evidence'),
    ('normal_biological_face','upper','invalid_normal_biological_face')])
def test_unsupported_face_review_is_refused(tmp_path,field,value,reason):
    request=request_fixture(tmp_path);data=read_json(request)
    data['face_mappings'][0][field]=value;write_json(request,data)
    with pytest.raises(StudyError,match=reason):bridge.build_package(request,tmp_path/'package')
