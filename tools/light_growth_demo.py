"""Reproducible synthetic direct example, including two instances of one source.

All geometry, optics, reviews and associations here are artificial software fixtures.
No native jobs or biological growth are executed.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path

from tools import hierarchical_light as hierarchy
from tools import light_growth_bridge as bridge
from tools.compound_growth import OBS_COLUMNS, AXIS_COLUMNS, EXTENT_COLUMNS
from tools.hierarchical_light_demo import synthetic_inputs
from tools.leaf_light.common import file_hash, output_dir, read_json, rows, write_json, write_rows


def demo(out: Path) -> dict:
    folder=output_dir(out); source=synthetic_inputs(folder/'inputs')
    plan=read_json(source); scene=read_json(source.parent/'scene.json')
    # Artificial extended emitters exercise actual path directions, not lamp centers.
    scene['fixtures'][0]['emitting_length_mm']['value']=400.
    scene['fixtures'][0]['emitter_grid']=[4,1]
    scene['simulation']['max_ray_triangle_pairs_per_chunk']=127
    fixture=deepcopy(scene['fixtures'][0]); fixture['fixture_id']='synthetic_LED_side'
    fixture['emitting_center_grow_mm']['value']=[400.,100.,1000.]
    scene['fixtures'].append(fixture); write_json(source.parent/'scene.json',scene)
    instance=deepcopy(plan['case']['instances'][0]); instance['plant_id']='P1_COPY'
    instance['placement']=deepcopy(scene['plants'][0]); instance['placement']['plant_id']='P1_COPY'
    instance['placement']['board_origin_grow_mm']['value']=[500.,0.,600.]
    instance['placement']['board_yaw_deg']['value']=35.
    plan['case']['instances'].append(instance); write_json(source,plan)
    membership=rows(source.parent/'membership.csv')
    membership += [dict(row,plant_instance_id='P1_COPY') for row in membership if row['plant_instance_id']=='P1']
    write_rows(source.parent/'membership.csv',membership,hierarchy.MEMBERSHIP)
    hierarchy.prepare_subset_cases(source,folder/'prepared')
    hierarchy.calculate_direct(folder/'prepared',folder/'hierarchy_results')
    start='2026-10-03T00:00:00+09:00'; end='2026-10-04T00:00:00+09:00'
    observation=dict(plant_id='P1',compound_leaf_id='synthetic_observed_C1',session_id='synthetic_session',
        observed_at=start,parent_stem_id='synthetic_stem',identity_status='confirmed',review_source='synthetic_test_only',
        geometry_status='observed_axis',development_state='expanded',first_observed_at=start,supported_area_cm2=1604.,
        area_basis_id='synthetic_reviewed_supported_area',estimated_total_area_cm2=None,transverse_x=0.,transverse_y=1.,transverse_z=0.)
    write_rows(folder/'observations.csv',[observation],OBS_COLUMNS)
    axes=[dict(plant_id='P1',compound_leaf_id='synthetic_observed_C1',session_id='synthetic_session',station=s,
               x_mm=x,y_mm=0.,z_mm=0.) for s,x in ((0,-200.),(1,200.))]
    write_rows(folder/'axes.csv',axes,AXIS_COLUMNS); write_rows(folder/'extents.csv',[],EXTENT_COLUMNS)
    write_json(folder/'history.json',dict(schema='compound-observations-1',data_kind='synthetic',reference_status='synthetic',
        frame_id='source_board_P1',coordinate_frame='board_mm',frame_stability='confirmed',frame_evidence='synthetic_test_only',
        tables={name:dict(path=name+'.csv',sha256=file_hash(folder/(name+'.csv'))) for name in ('observations','axes','extents')}))
    write_json(folder/'review_evidence.json',dict(data_kind='synthetic',note='Artificial source/compound/area/frame associations; not human observations.'))
    associations=[dict(geometry_snapshot_id='synthetic_geometry_1',plant_instance_id=pid,session_id='synthetic_session',
        compound_id='compound_1',compound_leaf_id='synthetic_observed_C1',review_status='reviewed',evidence_path='review_evidence.json',
        evidence_sha256=file_hash(folder/'review_evidence.json'),geometry_sha256=file_hash(folder/'prepared'/'leaf_surfaces.csv'),
        area_basis_id='synthetic_reviewed_supported_area',supported_area_m2=.1604,
        region_partition=dict(proximal_distal_boundary_mm=200.)) for pid in ('P1','P1_COPY')]
    request=dict(schema_version='light-growth-1',run_id='synthetic_light_growth_canopy',compound_history='history.json',associations=associations,
        interval=dict(start_at=start,end_at=end),
        snapshots=[dict(geometry_snapshot_id='synthetic_geometry_1',prepared_run='prepared',full_scene_results='hierarchy_results',
            observed_at=start,valid_from=start,valid_until=end,geometry_mode='held_current_geometry_scenario',
            board_frame_ids={'P1':'source_board_P1','P1_COPY':'source_board_P1','P2':'source_board_P2'})],
        schedule=dict(timezone='Asia/Seoul',provenance=dict(kind='synthetic_test_only',source='light_growth_demo'),fixed_optics_beam_spectrum=True,
            fixtures={'synthetic_LED':[dict(start_hhmm='06:00',end_hhmm='18:00',output_fraction=1.)],
                'synthetic_LED_side':[dict(start_hhmm='22:00',end_hhmm='02:00',output_fraction=.5),dict(start_hhmm='12:00',end_hhmm='16:00',output_fraction=.25)]}),
        limits=dict(max_transport_calls=1,max_receiver_emitter_pairs=1000000,max_schedule_minutes=2000))
    write_json(folder/'request.json',request)
    bridge.build_package(folder/'request.json',folder/'package')
    bridge.split_canopy_results(folder/'package','P1',folder/'P1_in_canopy')
    bridge.split_canopy_results(folder/'package','P1_COPY',folder/'P1_COPY_in_canopy')
    checks={name:bridge.validate_growth_light_package(folder/name) for name in ('package','P1_in_canopy','P1_COPY_in_canopy')}
    write_json(folder/'consumer_checks.json',checks)
    from tools.light_growth_consumer import load_tables
    original=load_tables(folder/'P1_in_canopy')['light_samples.csv']
    copied=load_tables(folder/'P1_COPY_in_canopy')['light_samples.csv']
    def coordinates(table: list[dict]) -> list:
        return sorted((r['organ_id'],r['leaflet_id'],r['triangle_id'],*(round(r[f'position_board_{a}_mm'],9) for a in 'xyz'))
            for r in table if r['time_step_id']=='full_output' and r['fixture_id']=='all')
    copy_check=dict(source_board_coordinates_equal=coordinates(original)==coordinates(copied),
        distinct_instance_ids=sorted({r['plant_instance_id'] for r in original+copied}),
        context_preserved=read_json(folder/'P1_in_canopy'/'package.json')['context_geometry_hashes']==read_json(folder/'P1_COPY_in_canopy'/'package.json')['context_geometry_hashes'])
    write_json(folder/'copy_roundtrip.json',copy_check)
    if not all(c['valid'] for c in checks.values()) or not copy_check['source_board_coordinates_equal']:
        raise ValueError('synthetic_consumer_verification_failed')
    return dict(output=str(folder),consumer_checks=checks,copy_check=copy_check,native_executed=False,physical_validation=False)


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); result=demo(args.out)
    print('Synthetic package and two canopy-preserving splits verified:',result['output'])


if __name__=='__main__':
    main()
