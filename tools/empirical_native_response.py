"""Adapt one validated empirical scenario to the native owner's existing immutable response API."""
from __future__ import annotations

import argparse
from pathlib import Path
import time

import numpy as np

from tools.empirical_growth_boundary import require, source, timestamp
from tools.empirical_growth_consumer import validate
from tools.leaf_light.common import digest, file_hash, read_json, rows, write_json, output_dir, StudyError


def response(boundary_path: Path, configuration: Path, context: dict, working: Path,
             interval_index: int, diffuse_fraction: float, *, light_hours: float,
             nrh_basis: str, fixture: bool, light_only: bool) -> dict:
    """No submission or growth here. Live mesh comparison is independent of export hashes."""
    from tools.tomato_fsp_native_boundary import read_request
    validate(boundary_path, configuration, context, 'absorbed')
    native, leaves = read_request(working, interval_index)
    m = read_json(boundary_path); req = read_json(Path(m['request_path']))
    require(native['run_id'] == m['run_id'], 'native_run_mismatch')
    require(native['configuration_sha256'] == m['configuration_sha256'], 'native_configuration_mismatch')
    require(diffuse_fraction in m['diffuse_fractions'], 'undeclared_direction_scenario')
    chosen = [b for b in m['intervals'] if timestamp(b['start_at']) == timestamp(native['interval_start']) and
              timestamp(b['end_at']) == timestamp(native['interval_end'])]
    require(len(chosen) == 1, 'native_interval_mismatch')
    binding = chosen[0]
    input_interval = next(i for i in req['intervals'] if i['interval_id'] == binding['interval_id'])
    snapshot = read_json(Path(input_interval['snapshot_ref']['path']))
    native_geometry = rows(working/f'boundary_{interval_index}_geometry.csv')
    by = {s['organ_id']:s for s in snapshot['surfaces']}
    require(set(by) == {r['organ_id'] for r in leaves}, 'native_leaf_namespace_mismatch')
    values = []
    for leaf in leaves:
        oid = leaf['organ_id']; s = by[oid]
        require(s['plant_instance_id'] == leaf['plant_instance_id'], 'native_plant_namespace_mismatch')
        coordinates = sorted([r for r in native_geometry if r['organ_id'] == oid], key=lambda r:int(r['vertex']))
        require([int(r['vertex']) for r in coordinates] == list(range(len(coordinates))) and len(coordinates)%3 == 0,
                'native_mesh_vertex_inventory')
        array = np.array([[float(r[k]) for k in ('x_m','y_m','z_m')] for r in coordinates])
        exported = np.asarray(s['triangles_m']).reshape(-1,3)
        require(array.shape == exported.shape and np.array_equal(array,exported), 'not_actual_native_consumed_mesh')
        area = float(leaf['area_m2'])
        require(np.isclose(s['area_m2'],area,rtol=1e-10,atol=1e-12), 'native_mesh_vs_leaf_area_mismatch')
        selected = [r for r in m['rows'] if r['interval_id'] == binding['interval_id'] and
                    r['organ_id'] == oid and r['diffuse_fraction'] == diffuse_fraction]
        require(bool(selected), 'native_leaf_light_missing')
        on = [r for r in selected if r['output_fraction'] == 1]
        require(abs(sum(r['duration_s'] for r in on)-light_hours*3600) <= 1e-8, 'native_light_hours_mismatch')
        fluxes = [r['absorbed_umol_s'] for r in on]
        flux = fluxes[0] if fluxes else 0.
        require(all(v is not None and np.isclose(v,flux,rtol=1e-12,atol=1e-12) for v in fluxes),
                'native_v1_cannot_average_varying_PPFD_before_NRH')
        if not light_only:
            require(fixture and nrh_basis == 'fixture_black_absorbed_equivalence', 'nrh_light_basis_unreviewed')
            optics = input_interval['absorptance_by_surface'][s['surface_id']]
            require(optics is not None and optics['normal'] == optics['opposite'] == 1 and req['leaf_transmittance'] == 0,
                    'fixture_black_equivalence_requires_black_optics')
        else:
            require(nrh_basis == 'disabled_diagnostic', 'diagnostic_nrh_not_disabled')
        values.append(dict(organ_id=oid,plant_instance_id=leaf['plant_instance_id'],area_m2=area,absorbed_umol_s=flux))
    source_files = dict(m['source_hashes'])
    for p in (boundary_path,configuration, working/f'boundary_{interval_index}_request.json',
              working/f'boundary_{interval_index}_geometry.csv',working/f'boundary_{interval_index}_leaves.csv'):
        source_files[str(p.resolve())]=file_hash(p)
    for name in m['artifact_hashes']:
        p=boundary_path.parent/name;source_files[str(p.resolve())]=file_hash(p)
    from tools import tomato_fsp_native_boundary as native_api
    code_files=dict(m['code_hashes'])
    for p in (Path(__file__),Path(native_api.__file__)):
        code_files[str(p.resolve())]=file_hash(p)
    return dict(schema_version='fsp-native-light-response-1',request_sha256=file_hash(working/f'boundary_{interval_index}_request.json'),
        configuration_sha256=m['configuration_sha256'],basis='absorbed_photon_flux',unit='umol/s',transport_count=1,
        source_kind='derived',source_ref=str(boundary_path.resolve()),source_files=source_files,code_files=code_files,
        expires_epoch_ms=native['deadline_epoch_ms'],leaves=values,
        empirical_scenario=dict(diffuse_fraction=diffuse_fraction,orientation_variant=binding['orientation_variant'],
            geometry_sha256=native['geometry_sha256'],registration_sha256=binding['registration_sha256'],
            scope='conditional_fixture_growth' if not light_only else 'light_only_diagnostic'))


def prepare(native_folder: Path, boundary_path: Path, configuration: Path, context_path: Path,
            interval: int, fraction: float, out: Path, submit: bool = False) -> dict:
    from tools.vtc_development import verify_prepared
    from tools.tomato_fsp_native_boundary import read_request, submit_light
    prepared,pkg = verify_prepared(native_folder)
    working=native_folder/'working'; native,_=read_request(working,interval)
    require(native['input_hash']==digest(pkg['source_hashes']) and native['engine_hash']==prepared['binding']['engine_hash'],
            'native_prepared_lineage_mismatch')
    request=pkg['request']; boundary=request['native_boundary']
    result=response(boundary_path,configuration,read_json(context_path),working,interval,fraction,
        light_hours=float(pkg['tables']['environment.csv'][interval]['light_hours']),nrh_basis=boundary['nrh_basis'],
        fixture=request['fixture'],light_only=request.get('light_only',False))
    require(int(time.time()*1000)<result['expires_epoch_ms'],'native_deadline_expired')
    folder=output_dir(out);write_json(folder/'response.json',result)
    if submit:
        receipt=submit_light(working,interval,result);write_json(folder/'submission.json',receipt)
    else: receipt=dict(status='prepared_not_submitted')
    return receipt


def main(argv: list[str] | None = None) -> int:
    p=argparse.ArgumentParser(description=__doc__)
    for name in ('native','boundary','configuration','context','out'):
        p.add_argument('--'+name,type=Path,required=True)
    p.add_argument('--interval',type=int,required=True);p.add_argument('--diffuse-fraction',type=float,required=True)
    p.add_argument('--submit',action='store_true');a=p.parse_args(argv)
    try:
        print(prepare(a.native,a.boundary,a.configuration,a.context,a.interval,a.diffuse_fraction,a.out,a.submit));return 0
    except (StudyError,ValueError,KeyError,OSError) as exc:
        p.exit(2,str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
