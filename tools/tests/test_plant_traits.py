"""S8 traits: union area with per-mask depth, calibration through the origin, light and the person's measurement files."""
import csv
import copy
import json

import numpy as np
import pytest

from tools import plant_traits as pt


class FlatCameras:
    """A camera looking straight down the z axis: pixel = f * (x, y) / z + c, depth = z."""
    def __init__(self, f=100.0, size=(200, 200)):
        self.K = np.array([[f, 0, 100], [0, f, 100], [0, 0, 1]], float)
        self.size = size

    def project(self, key, X):
        X = np.asarray(X, float)
        return np.c_[self.K[0, 0] * X[:, 0] / X[:, 2] + 100, self.K[1, 1] * X[:, 1] / X[:, 2] + 100]

    def depth(self, key, X):
        return np.asarray(X, float)[:, 2]


def _hull(z, half=20.0, n=21):  # projects to pixels 90..110
    g = np.linspace(-half, half, n)
    return np.array([(x, y, z) for x in g for y in g])


def test_union_area_counts_overlaps_once_and_scales_with_depth():
    cams = FlatCameras()
    hull = _hull(z=200.0)
    m = np.ones((20, 20), bool)
    one = pt.photo_area(cams, 'k', hull, [((90, 90, 110, 110), m, True)])
    two = pt.photo_area(cams, 'k', hull, [((90, 90, 110, 110), m, True), ((90, 90, 110, 110), m, False)])
    assert one['union_px'] == two['union_px'] == 400
    assert abs(one['leaf_area_cm2'] - 400 * (200 / 100) ** 2 / 100) < 1e-6  # 16 cm2: (Z/f)^2 mm2 per pixel
    assert two['leaf_area_cm2'] == one['leaf_area_cm2'] and two['accepted_leaf_area_cm2'] == one['leaf_area_cm2']


def test_mask_without_hull_behind_it_is_not_counted():
    cams = FlatCameras()
    r = pt.photo_area(cams, 'k', _hull(z=200.0), [((0, 0, 20, 20), np.ones((20, 20), bool), True)])
    assert r['masks_without_depth'] == 1 and r['leaf_area_cm2'] == 0


def test_only_accepted_masks_enter_the_accepted_area():
    cams = FlatCameras()
    m = np.ones((10, 20), bool)
    r = pt.photo_area(cams, 'k', _hull(z=200.0), [((90, 90, 110, 100), m, True), ((90, 100, 110, 110), m, False)])
    assert abs(r['accepted_leaf_area_cm2'] * 2 - r['leaf_area_cm2']) < 1e-6


def test_calibration_through_origin_and_leave_one_out():
    traits = [dict(plant_id=f'p{i}', leaf_area_proxy_cm2=x) for i, x in enumerate([10.0, 20.0, 30.0, 40.0])]
    measured = {'p0': 30.0, 'p1': 60.0, 'p2': 90.0}
    c = pt.calibrate(traits, measured)
    assert c['status'] == 'fitted' and c['plants'] == 3 and abs(c['k'] - 3.0) < 1e-9 and c['loo_mean_abs_rel_error_pct'] == 0
    assert pt.calibrate(traits, {})['status'] == 'no_measurements'
    assert 'loo_mean_abs_rel_error_pct' not in pt.calibrate(traits, {'p0': 30.0})


def _write(path, fields, rows):
    with open(path, 'w', newline='', encoding='utf-8') as fh:
        w = csv.DictWriter(fh, fieldnames=fields)
        w.writeheader()
        w.writerows(rows)


def test_summary_asks_only_for_measurements_and_uses_them(tmp_path):
    traits = [dict(plant_id='a', leaf_area_proxy_cm2=10.0, top_leaf_area_cm2=None, hull_footprint_cm2=50.0),
              dict(plant_id='b', leaf_area_proxy_cm2=20.0, top_leaf_area_cm2=40.0, hull_footprint_cm2=80.0)]
    empty = tmp_path / 'none'
    d = pt.summarize(traits, tmp_path / 'out1', empty)
    assert len(d['human_tasks']) == 2 and d['validated_metric'] is False
    m = tmp_path / 'm'
    m.mkdir()
    _write(m / 'leaf_area.csv', pt.LEAF_AREA_FIELDS, [dict(plant_id='a', leaf_area_cm2=25)])
    _write(m / 'light.csv', pt.LIGHT_FIELDS, [dict(plant_id='*', ppfd_umol_m2_s=200, photoperiod_h=16)])
    d = pt.summarize(traits, tmp_path / 'out2', m)
    rows = {r['plant_id']: r for r in d['rows']}
    assert rows['b']['estimated_leaf_area_cm2'] == 50.0 and rows['a']['measured_leaf_area_cm2'] == 25.0
    assert rows['a']['dli_mol_m2_d'] == 11.52  # 200 x 16 h x 3600 / 1e6
    assert rows['a']['canopy_source'] == 'hull footprint' and rows['b']['canopy_source'] == 'top photo leaves'
    assert abs(rows['b']['intercepted_mmol_d'] - 11.52 * 40 / 1e4 * 1000) < 0.1
    assert (tmp_path / 'out2' / 'traits.csv').exists() and len(d['human_tasks']) == 1  # fewer than 3 calibration plants


def test_repeated_plant_dates_join_independently_without_mutation(tmp_path):
    traits = [dict(plant_id='a', capture_date=d, session_id=s, leaf_area_proxy_cm2=x,
                   top_leaf_area_cm2=x) for d, s, x in [('2026-10-01','s1',10.),('2026-10-02','s2',20.)]]
    original = copy.deepcopy(traits)
    m = tmp_path / 'measurements'; m.mkdir()
    _write(m/'leaf_area.csv', pt.LEAF_AREA_FIELDS,
           [dict(plant_id='a', date=t['capture_date'], leaf_area_cm2=3*t['leaf_area_proxy_cm2']) for t in traits])
    _write(m/'light.csv', pt.LIGHT_FIELDS,
           [dict(plant_id='a', date=t['capture_date'], ppfd_umol_m2_s=v, photoperiod_h=16)
            for t, v in zip(traits,[100,200])])
    before = {p.name:p.read_bytes() for p in m.iterdir()}
    d = pt.summarize(traits,tmp_path/'out',m)
    assert [r['measured_leaf_area_cm2'] for r in d['rows']] == [30,60]
    assert [r['dli_mol_m2_d'] for r in d['rows']] == [5.76,11.52]
    assert d['plants'] == 1 and d['observations'] == 2
    assert d['calibration']['plants'] == 1 and 'loo_mean_abs_rel_error_pct' not in d['calibration']
    assert traits == original and before == {p.name:p.read_bytes() for p in m.iterdir()}


def test_dates_do_not_fall_back_to_undated_or_wrong_day(tmp_path):
    t = dict(plant_id='a',capture_date='2026-10-02',leaf_area_proxy_cm2=10.)
    m=tmp_path/'m';m.mkdir()
    _write(m/'leaf_area.csv',pt.LEAF_AREA_FIELDS,[dict(plant_id='a',date='2026-10-01',leaf_area_cm2=30)])
    _write(m/'light.csv',pt.LIGHT_FIELDS,[dict(plant_id='*',ppfd_umol_m2_s=200,photoperiod_h=16)])
    r=pt.summarize([t],tmp_path/'o',m)['rows'][0]
    assert r['measured_leaf_area_cm2'] is None and 'dli_mol_m2_d' not in r
    assert r['area_join_status'] == r['light_join_status'] == 'no_matching_date_or_session'


def test_sessions_need_explicit_disambiguation():
    traits=[dict(plant_id='a',date='2026-10-01',session_id=s) for s in ['morning','evening']]
    with pytest.raises(pt.StudyError,match='session_id'):
        pt.match_record(traits[0],[dict(plant_id='a',date='2026-10-01')],traits)
    rows=[dict(t,leaf_area_cm2=x) for t,x in zip(traits,[10,20])]
    assert pt.match_record(traits[1],rows,traits)[0]['leaf_area_cm2']==20
    with pytest.raises(pt.StudyError,match='Ambiguous'):
        pt.match_record(traits[0],[rows[0],rows[0]],traits)


def test_grouped_validation_never_implies_metric_accuracy(tmp_path):
    traits=[dict(plant_id=p,date=f'2026-10-0{i}',leaf_area_proxy_cm2=float(i))
            for p in ['a','b','c'] for i in [1,2]]
    m=tmp_path/'m';m.mkdir()
    _write(m/'leaf_area.csv',pt.LEAF_AREA_FIELDS,
           [dict(plant_id=t['plant_id'],date=t['date'],leaf_area_cm2=t['leaf_area_proxy_cm2']*3) for t in traits])
    d=pt.summarize(traits,tmp_path/'o',m)
    assert d['calibration']['loo_mean_abs_rel_error_pct']==0
    assert d['calibration']['plants']==3 and d['calibration']['observations']==6
    assert d['calibration']['loo_unit'].startswith('plant;')
    assert d['validated_metric'] is False
    assert all(r['validated_metric'] is False for r in d['rows'])


def test_calibration_holds_out_all_dates_of_a_plant():
    traits=[dict(plant_id=p,date=d,leaf_area_proxy_cm2=x) for p,d,x in
            [('a','2026-10-01',1.),('a','2026-10-02',2.),('b','2026-10-01',1.),('c','2026-10-01',1.)]]
    measured={pt.observation_key(t):y for t,y in zip(traits,[2.,4.,4.,6.])}
    c=pt.calibrate(traits,measured)
    # A fitted from B+C: k=5; B/C fitted without either date of their held-out plant.
    errors=[1.5,abs((16/6)-4)/4,abs((14/6)-6)/6]
    assert c['loo_mean_abs_rel_error_pct']==round(float(np.mean(errors))*100,1)


@pytest.mark.parametrize('value',['nan','inf','-1','25'])
def test_invalid_light_duration_rejected(tmp_path,value):
    m=tmp_path/'m';m.mkdir()
    _write(m/'light.csv',pt.LIGHT_FIELDS,[dict(plant_id='a',ppfd_umol_m2_s=200,photoperiod_h=value)])
    with pytest.raises(pt.StudyError,match='Invalid'):
        pt.summarize([dict(plant_id='a')],tmp_path/'o',m)


def test_missing_duration_remains_null_and_light_is_not_absorption(tmp_path):
    m=tmp_path/'m';m.mkdir()
    _write(m/'light.csv',pt.LIGHT_FIELDS,[dict(plant_id='a',ppfd_umol_m2_s=200)])
    d=pt.summarize([dict(plant_id='a',top_leaf_area_cm2=10)],tmp_path/'o',m)
    r=d['rows'][0]
    assert r['photoperiod_h'] is None and r['dli_mol_m2_d'] is None
    assert r['intercepted_mmol_d'] is None and r['absorbed_mmol_d'] is None
    assert r['photosynthesis_umol_co2_s'] is None
    json.dumps(d,allow_nan=False)


def test_date_conflicts_and_duplicate_traits_rejected(tmp_path):
    with pytest.raises(pt.StudyError,match='Conflicting'):
        pt.record_date(dict(date='2026-10-01',capture_date='2026-10-02'))
    with pytest.raises(pt.StudyError,match='Duplicate'):
        pt.summarize([dict(plant_id='a')]*2,tmp_path/'o',tmp_path/'m')


def test_zero_top_area_is_not_replaced_by_hull(tmp_path):
    m=tmp_path/'m';m.mkdir()
    _write(m/'light.csv',pt.LIGHT_FIELDS,[dict(plant_id='a',ppfd_umol_m2_s=200,photoperiod_h=16)])
    r=pt.summarize([dict(plant_id='a',top_leaf_area_cm2=0.,hull_footprint_cm2=50.)],tmp_path/'o',m)['rows'][0]
    assert r['intercepted_mmol_d']==0 and r['canopy_source']=='top photo leaves'
