"""Synthetic package/reference/face delivery and exact photon-number preservation."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from tools import light_growth_bridge as bridge
from tools.light_growth_demo import demo as tissue_demo
from tools.light_growth_consumer import load_tables
from tools.light_face_evidence import FACE_KEY
from tools.leaf_light.common import DLI_UNIT, file_hash, read_json, write_json
from tools.reference_dli_demo import create_inputs, row, write_readings
from tools.reference_dli import prepare_record, save_result
from tools.reference_dli_intervals import dated_schedule
from tools.reference_dli_p3 import map_single_day


def demo(out: Path) -> dict:
    tissue_demo(out)
    root=out.resolve(); request=read_json(root/'request.json')
    source=root/'reference_inputs'; inputs=create_inputs(source,'logged')
    p=inputs['position']; p.update(dates=['2026-10-03'],representative_date='2026-10-03',
        logger_sample_semantics='interval_mean',gradient_exposure_basis='full_elapsed_day',
        operating_metadata=dict(provenance='synthetic_benchmark_only_not_real_lamp_operation',
            fixture_count=2,actual_synthetic_schedule='same_as_tissue_request'))
    p['plant_association']['plant_instance_ids']=['P1']
    p['applicability_source_ref']['path']=str((source/'synthetic_evidence.json').resolve())
    schedule=deepcopy(request['schedule']); schedule['dates']=p['dates']
    timeline=dated_schedule(p,schedule,p['dates']); observations=[]
    # Predeclared synthetic sensor responses to each full-output fixture. These
    # exercise measured-channel software; they are not fitted or physical PPFD.
    sensor_response={'synthetic_LED':200.,'synthetic_LED_side':100.}
    for i,segment in enumerate(timeline['days']['2026-10-03']['intervals']):
        q=sum(sensor_response[fid]*fraction for fid,fraction in segment['fixture_fractions'].items())
        observations.append(row('interval_'+str(i),segment['end_at'],q,state='on' if q else 'off',
            support_start_at=segment['start_at'],support_end_at=segment['end_at']))
    write_json(source/'reference_position.json',p); write_json(source/'schedule.json',schedule)
    write_readings(source/'reference_readings.csv',observations)
    # Freeze model-owned fields before the producer is evaluated.
    domain=dict(min=0.,max=30.,unit=DLI_UNIT,source_kind='user_assumed',source_ref='PREDECLARED SYNTHETIC DOMAIN',
                applicability_source_ref=deepcopy(p['applicability_source_ref']))
    light=dict(kind='size_target_dli',unit=DLI_UNIT,center=10.,scale=10.,source_kind='user_assumed',
        source_ref='PREDECLARED SYNTHETIC MODEL',applicability_interval=domain,
        coefficients={'exponential':dict(coefficient_id='synthetic_fixed_exp',role='remaining_increment',c_DLI=.1,
            source_kind='user_assumed',source_ref='PREDECLARED SYNTHETIC COEFFICIENT',
            applicability_source_ref=deepcopy(p['applicability_source_ref']))})
    model=dict(environment_profile='d9',clock={'kind':'calendar'},light_response=light,
        parameter_particles=[dict(existing_blocks={'synthetic_block':'existing'},axes={},
                                  families={'existing':dict(growth_curve='exponential',features=[])})])
    write_json(root/'predeclared_p3_validator_config.json',model)
    record,audit=prepare_record(source/'reference_position.json',source/'schedule.json',route='logged',
        readings_path=source/'reference_readings.csv',survey_path=source/'spot_survey.csv')
    save_result(record,audit,root/'reference_result')
    result=root/'reference_result/reference_dli.json'
    request['reference_dli']=dict(path=str(result),sha256=file_hash(result))
    proof=root/'synthetic_face_review.json'
    write_json(proof,dict(source_kind='synthetic_only',note='Artificial reviewed normal/adaxial identity for software tests'))
    baseline=load_tables(root/'package'); geometry=read_json(root/'package/package.json')['context_geometry_hashes']
    surfaces={tuple(r[k] for k in FACE_KEY):r for r in baseline['light_samples.csv']}
    request['face_mappings']=[dict(**dict(zip(FACE_KEY,key)),mapping_id='synthetic_face_'+str(i),
        geometry_sha256=geometry[key[0]],normal_biological_face='adaxial',review_status='reviewed',
        reviewer='synthetic_fixture',evidence_path=proof.name,evidence_sha256=file_hash(proof))
        for i,key in enumerate(sorted(surfaces))]
    write_json(root/'v2_request.json',request)
    bridge.build_package(root/'v2_request.json',root/'v2_package')
    for pid in ('P1','P1_COPY'):bridge.split_canopy_results(root/'v2_package',pid,root/('v2_'+pid+'_in_canopy'))
    checks={name:bridge.validate_growth_light_package(root/name) for name in
            ('v2_package','v2_P1_in_canopy','v2_P1_COPY_in_canopy')}
    current=load_tables(root/'v2_package'); numerical={}
    for name,spec in bridge.SCHEMA['tables'].items():
        numeric=[c['name'] for c in spec['columns'] if c['type']=='number']
        numerical[name]=len(baseline[name])==len(current[name]) and all(
            {k:a[k] for k in numeric}=={k:b[k] for k in numeric} for a,b in zip(baseline[name],current[name]))
    from tools import probabilistic_compound_growth as p3
    config=deepcopy(model);config['light_response']=map_single_day(result,model['light_response'],evidence_kind='user_assumed')
    p3._validate_d9(config,{})
    write_json(root/'p3_validator_input.json',config)
    denied=deepcopy(config);denied['light_response']['value']=31.
    try:p3._validate_d9(denied,{})
    except p3.ScienceUnavailable as exc:out_of_domain=str(exc)
    else:raise AssertionError('P3 accepted out-of-domain DLI')
    report=dict(status='passed' if all(v['valid'] for v in checks.values()) and all(numerical.values()) else 'failed',
        consumers=checks,numeric_fields_exact=numerical,reference_value=record['value'],
        p3_validator=dict(available='passed',out_of_domain=out_of_domain,forecast_executed=False,
                         source_sha256=file_hash(Path(p3.__file__))),
        face_values=sorted({r['illuminated_faces'] for r in current['light_samples.csv'] if r['illuminated_faces']}),
        native_executed=False,physical_validation=False)
    write_json(root/'v2_verification.json',report)
    if report['status']!='passed':raise AssertionError(report)
    return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args();print(demo(args.out))


if __name__=='__main__':main()
