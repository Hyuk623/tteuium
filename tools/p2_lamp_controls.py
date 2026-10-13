"""Independent direct-light and reflection-estimator checks on a frozen native fit.

No fitting and no geometry selection. Outputs diagnostics, never absolute validity.
"""
from __future__ import annotations

import argparse
from copy import deepcopy
import math
from pathlib import Path
import numpy as np

from tools import ppfd_validation as pv
from tools.p2_lamp_calibration import require, finite
from tools.leaf_light.common import file_hash, read_json, rows, output_dir, write_json, write_rows
from tomato3d.light.scene import load_scene
from tools.fsp_extensions import photon_factor


def check(fit_path: Path, out: Path, *, emitter_grid: tuple[int,int], sensor_samples: int,
          relative_tolerance: float, absolute_tolerance: float, standard_error_multiplier: float):
    require(len(emitter_grid)==2 and all(type(n) is int and n>0 for n in emitter_grid), 'positive emitter grid required')
    require(type(sensor_samples) is int and sensor_samples>0, 'positive sensor samples required')
    for value in (relative_tolerance, absolute_tolerance, standard_error_multiplier): finite(value,'tolerance',0)
    fit=read_json(fit_path); base=fit_path.parent
    for name,sha in fit['artifact_hashes'].items(): require(file_hash(base/name)==sha,'native artifact changed')
    for name,sha in {**fit['source_hashes'],**fit['code_hashes']}.items():require(file_hash(Path(name))==sha,'native source/code changed')
    plan=read_json(base/'frozen_plan.json'); native=rows(base/'conditional_predictions.csv')
    folder=output_dir(out); records=[]
    for v in plan['variants']:
        parameters=next(r['fitted_parameters'] for r in fit['variants'] if r['variant_id']==v['variant_id'])
        scene=deepcopy(v['scene_data'])
        for fx in scene['fixtures']:
            fx['photon_flux_umol_s']['value']*=parameters['photon_flux_scale']
            if plan.get('offset_axis'):
                fx['emitting_center_grow_mm']['value']['xyz'.index(plan['offset_axis'])]+=parameters['offset_mm']
        path=folder/f'scene_{len(records)}.json';write_json(path,scene)
        states=pv.python_states(load_scene(path),emitter_grid)
        occluders=pv.opaque_occluders([pv.rig_surface_triangles(r) for r in v['rig_data']])
        sensors={s['sensor_id']:s for s in v['sensors_data']}
        for point in v['points_data']:
            prediction=next(p for p in native if p['variant_id']==v['variant_id'] and p['point_id']==point['point_id'])
            direct=pv.python_point_ppfd(states,point,sensors[point['sensor_id']],sensor_samples,occluders)
            # Each point is run alone. job order is frozen: coarse candidates then full/black/enclosure-free.
            jobs=read_json(base/'native_jobs.json')
            # Multiple variants may reuse point IDs: identify the exact native group by frozen execution order.
            variant_index=plan['variants'].index(v); start=0
            for previous in plan['variants'][:variant_index]:
                ncal=sum(p['split_role']=='calibration' for p in previous['points_data'])
                start+=len(plan['solver']['seeds'])*(ncal*len(plan['reflectance_grid'])*len(plan.get('offset_grid_mm') or [0])+3*len(previous['points_data']))
            ncal=sum(p['split_role']=='calibration' for p in v['points_data'])
            coarse=len(plan['solver']['seeds'])*ncal*len(plan['reflectance_grid'])*len(plan.get('offset_grid_mm') or [0])
            n=len(v['points_data'])*len(plan['solver']['seeds'])
            black=jobs[start+coarse+n:start+coarse+2*n]
            samples=[]
            tri,area=pv.sensing_mesh(point,sensors[point['sensor_id']],v.get('disc_segments'))
            for job in black:
                if job['point_id']!=point['point_id']:continue
                require(job['control']=='black_rig' and job['status']=='completed','black control job mismatch')
                log=Path(job['folder'])/'groimp.log'
                require(file_hash(log)==job['log_sha256'],'black control log changed')
                _, powers=pv.parse_log(log)
                require(set(powers)=={f'sensor:{i}' for i in range(len(tri))},'raw black probe incomplete')
                qraw=sum(powers.values())*photon_factor(plan['wavelength_nm'])/(area*1e-6)
                require(math.isclose(qraw,job['ppfd_umol_m2_s'],rel_tol=1e-12,abs_tol=1e-12),'raw power to PPFD mismatch')
                samples.append(qraw)
            require(len(samples)==len(plan['solver']['seeds']),'black control seed completeness')
            se=float(np.std(samples,ddof=1)/math.sqrt(len(samples))); q=float(prediction['black_rig_ppfd_umol_m2_s'])
            require(math.isclose(q,float(np.mean(samples)),rel_tol=1e-12,abs_tol=1e-12),'raw prediction mean mismatch')
            full=jobs[start+coarse:start+coarse+n]
            full_samples=[]
            for job in full:
                if job['point_id']!=point['point_id']:continue
                require(job['control']=='full' and job['status']=='completed','full job mismatch')
                log=Path(job['folder'])/'groimp.log'
                require(file_hash(log)==job['log_sha256'],'full log changed')
                _,powers=pv.parse_log(log)
                require(set(powers)=={f'sensor:{i}' for i in range(len(tri))},'raw full probe incomplete')
                full_samples.append(sum(powers.values())*photon_factor(plan['wavelength_nm'])/(area*1e-6))
            require(len(full_samples)==len(samples),'full control seed completeness')
            require(math.isclose(float(np.mean(full_samples)),float(prediction['predicted_ppfd_umol_m2_s']),
                                 rel_tol=1e-12,abs_tol=1e-12),'raw total prediction mean mismatch')
            differences=np.asarray(full_samples)-np.asarray(samples)
            require(math.isclose(float(np.mean(differences)),float(prediction['post_reflection_estimate_umol_m2_s']),
                                 rel_tol=1e-12,abs_tol=1e-12),'raw reflection difference mismatch')
            require(math.isclose(float(np.std(differences,ddof=1)/math.sqrt(len(samples))),
                                 float(prediction['post_reflection_standard_error_umol_m2_s']),
                                 rel_tol=1e-12,abs_tol=1e-12),'raw reflection uncertainty mismatch')
            tolerance=absolute_tolerance+relative_tolerance*abs(direct)+standard_error_multiplier*se
            reflected=float(prediction['post_reflection_estimate_umol_m2_s'])
            reflected_se=float(prediction['post_reflection_standard_error_umol_m2_s'])
            records.append(dict(variant_id=v['variant_id'],point_id=point['point_id'],
                python_direct_ppfd_umol_m2_s=direct,native_black_rig_ppfd_umol_m2_s=q,
                black_rig_seed_standard_error_umol_m2_s=se,absolute_error=abs(q-direct),allowed_error=tolerance,
                direct_control_pass=abs(q-direct)<=tolerance,post_reflection_estimate_umol_m2_s=reflected,
                reflection_above_seed_noise=reflected>standard_error_multiplier*reflected_se))
    write_rows(folder/'direct_controls.csv',records,tuple(records[0]))
    result=dict(schema_version='p2-native-direct-controls-1',direct_controls_pass=all(r['direct_control_pass'] for r in records),
        transport_raw_to_prediction_pass=True,raw_arithmetic_absolute_tolerance=1e-12,raw_arithmetic_relative_tolerance=1e-12,
        source_fit_sha256=file_hash(fit_path),source_fit=str(fit_path.resolve()),emitter_grid=list(emitter_grid),
        sensor_samples=sensor_samples,absolute_tolerance=absolute_tolerance,relative_tolerance=relative_tolerance,
        standard_error_multiplier=standard_error_multiplier,
        formula='abs(native-python) <= atol + rtol*abs(python) + k*black_control_seed_SE',
        reflection_estimator='total minus same-geometry zero-reflectance opaque rig; preserves direct blocking',
        enclosure_free_is_reflection_only=False,physical_accuracy_validated=False,
        source_hashes={str(Path(__file__).resolve()):file_hash(Path(__file__)),str(fit_path.resolve()):file_hash(fit_path)},
        rows=records)
    write_json(folder/'controls.json',result);return result


def main():
    p=argparse.ArgumentParser(description=__doc__);p.add_argument('--fit',type=Path,required=True);p.add_argument('--out',type=Path,required=True)
    p.add_argument('--emitter-grid',type=int,nargs=2,required=True);p.add_argument('--sensor-samples',type=int,required=True)
    p.add_argument('--atol',type=float,required=True);p.add_argument('--rtol',type=float,required=True);p.add_argument('--se-multiplier',type=float,required=True)
    a=p.parse_args();result=check(a.fit,a.out,emitter_grid=tuple(a.emitter_grid),sensor_samples=a.sensor_samples,
        relative_tolerance=a.rtol,absolute_tolerance=a.atol,standard_error_multiplier=a.se_multiplier)
    print(dict(direct_controls_pass=result['direct_controls_pass']));return 0 if result['direct_controls_pass'] else 1


if __name__=='__main__':raise SystemExit(main())
