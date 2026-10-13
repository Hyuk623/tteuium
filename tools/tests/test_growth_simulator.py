"""Scaffold contracts, not biological accuracy tests."""
from dataclasses import asdict, replace
import json

import numpy as np
import pytest

from tools.growth_simulator import Environment, demo_parameters, export_result, simulate


def env(**changes):
    return replace(Environment(1,250,16,24,65,2,6),**changes)


def test_time_series_has_growing_surfaces_trusses_and_stable_parents():
    result=simulate([env() for _ in range(30)],demo_parameters())
    previous=set(); sizes=[]
    for frame in result['frames']:
        organs=frame['organs'];ids={o['organ_id'] for o in organs}
        assert len(ids)==len(organs) and previous <= ids
        assert all(o['parent_id'] is None or o['parent_id'] in ids for o in organs)
        assert all(np.isfinite(o['points_mm']).all() and np.isfinite(o['triangles_mm']).all() for o in organs)
        previous=ids
        first=next((o for o in organs if o['organ_id'].endswith('L001/F01')),None)
        if first and first['triangles_mm']:
            vertices=np.array(first['triangles_mm']).reshape(-1,3)
            sizes.append(np.linalg.norm(vertices.max(axis=0)-vertices.min(axis=0)))
            assert all(np.linalg.norm(np.cross(np.array(t)[1]-t[0],np.array(t)[2]-t[0]))>0 for t in first['triangles_mm'])
    assert len(set(round(s,6) for s in sizes))>1
    assert min(np.diff(sizes))>=-1e-10
    assert {'Leaflet','Truss','Flower','GrowthShoot','SubStem'} <= {o['organ_type'] for o in result['frames'][-1]['organs']}
    assert result['validated_growth'] is False and result['suitable_for_ppfd'] is False


@pytest.mark.parametrize('changes',[dict(ppfd_umol_m2_s=0),dict(photoperiod_h=0),dict(temperature_c=12),dict(relative_humidity_pct=25),dict(solution_ec_ms_cm=0),dict(solution_ph=3),dict(water_available=False)])
def test_each_environment_driver_reaches_development(changes):
    p=demo_parameters()
    baseline=simulate([env(dt_days=20)],p)
    altered=simulate([env(dt_days=20,**changes)],p)
    assert altered['frames'][-1]['development_days']<baseline['frames'][-1]['development_days']


def test_temporal_intervals_and_callback_preserve_inputs_and_snapshots():
    steps=[env(dt_days=3,nutrients_mg_l={'N':100}),env(dt_days=2,nutrients_mg_l={'N':50})]
    before=[asdict(e) for e in steps]
    received=[]
    def model(e,p):
        received.append(e.nutrients_mg_l['N']);e.nutrients_mg_l['N']=0
        return {'custom':.5}
    result=simulate(steps,demo_parameters(),response_model=model)
    assert received==[100,50] and [asdict(e) for e in steps]==before
    assert [f['day'] for f in result['frames']]==[0,3,5]
    assert result['frames'][-1]['development_days']==2.5
    assert result['frames'][1]['environment']['nutrients_mg_l']['N']==100
    assert len(result['frames'][0]['organs'])==3


@pytest.mark.parametrize('changes',[dict(ppfd_umol_m2_s=float('nan')),dict(dt_days=0),dict(relative_humidity_pct=101),dict(solution_ph=None),dict(nutrients_mg_l={'N':-1}),dict(water_available='yes')])
def test_invalid_environment_is_not_imputed(changes):
    with pytest.raises(ValueError):simulate([env(**changes)],demo_parameters())


def test_invalid_response_parameters_and_empty_schedule():
    for response in [lambda e,p:{},lambda e,p:{'x':float('inf')},lambda e,p:{'x':-1}]:
        with pytest.raises(ValueError):simulate([env()],demo_parameters(),response_model=response)
    with pytest.raises(ValueError):simulate([],demo_parameters())
    with pytest.raises(ValueError):simulate([env()],replace(demo_parameters(),node_interval_dev_days=0))


def test_step_partition_deterministic_and_dormant_demo():
    p=demo_parameters()
    a=simulate([env(dt_days=15)],p)
    b=simulate([env() for _ in range(15)],p)
    assert a['frames'][-1]['organs']==b['frames'][-1]['organs']
    stopped=simulate([env(dt_days=15,ppfd_umol_m2_s=0)],p)
    assert stopped['frames'][0]['organs']==stopped['frames'][-1]['organs']


def test_export_roundtrip_units_and_no_overwrite(tmp_path,monkeypatch):
    monkeypatch.chdir(tmp_path)
    payload={'plant_id':'test','parameters':asdict(demo_parameters()),'environment_steps':[asdict(env(dt_days=15))]}
    result=simulate([env(dt_days=15)],demo_parameters(),plant_id='test')
    out=tmp_path/'build/demo';export_result(result,out,payload)
    assert json.loads((out/'simulation.json').read_text(encoding='utf-8'))==result
    vertices=[list(map(float,s.split()[1:])) for s in (out/'display_only_m.obj').read_text().splitlines() if s.startswith('v ')]
    expected=[]
    for organ in result['frames'][-1]['organs']:
        expected.extend([p for tri in organ['triangles_mm'] for p in tri]);expected.extend(organ['points_mm'])
    assert np.allclose(np.array(vertices)*1000,expected,atol=1e-8)
    manifest=json.loads((out/'manifest.json').read_text())
    assert manifest['groimp_import_verified'] is False
    assert '__SIMULATION_JSON__' not in (out/'viewer.html').read_text(encoding='utf-8')
    with pytest.raises(FileExistsError):export_result(result,out,payload)
    with pytest.raises(ValueError):export_result(result,tmp_path/'not-build',payload)
