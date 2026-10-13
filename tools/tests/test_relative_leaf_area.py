"""First-labelled-leaf normalization retains missingness and comparison scope."""
from copy import deepcopy

import pytest

from tools import relative_leaf_area as ra
from tools.leaf_light import common


def examples():
    return [dict(plant_id='synthetic',session_id='s',capture_date=None,area_method='example',
                 area_scope='measured_leaf_area',view_id=None,label_id=name,area_cm2=area)
            for name,area in [('leaf_10',20.),('leaf_2',30.),('leaf_3',10.)]]


def test_first_supplied_not_lexical_label_and_uniform_scale_invariance():
    data=examples();before=deepcopy(data)
    result=ra.normalize(data)
    assert [r['relative_area'] for r in result]==[1.,1.5,.5]
    assert all(r['reference_label_id']=='leaf_10' for r in result)
    scaled=ra.normalize([dict(r,area_cm2=r['area_cm2']*25) for r in data])
    assert [r['relative_area'] for r in scaled]==[1.,1.5,.5]
    assert data==before


@pytest.mark.parametrize('area,status',[(None,'reference_unavailable'),(0,'reference_zero')])
def test_reference_not_silently_replaced(area,status):
    data=examples();data[0]['area_cm2']=area
    result=ra.normalize(data)
    assert all(r['relative_area'] is None and r['ratio_status']==status for r in result)


def test_missing_leaf_is_not_zero_but_measured_zero_remains_zero():
    data=examples();data[1]['area_cm2']=None;data[2]['area_cm2']=0
    result=ra.normalize(data)
    assert result[1]['relative_area'] is None
    assert result[2]['relative_area']==0


@pytest.mark.parametrize('field,value',[('session_id','other'),('capture_date','2026-10-03'),
    ('area_method','other'),('area_scope','supported_partial_surface'),('plant_id','other')])
def test_reference_not_shared_across_incompatible_groups(field,value):
    data=examples();data[1][field]=value
    result=ra.normalize(data)
    selected=next(r for r in result if r['label_id']=='leaf_2')
    assert selected['reference_label_id']=='leaf_2' and selected['relative_area']==1


def test_projected_ratios_require_same_known_photo():
    data=[dict(r,area_scope='projected_mask_area') for r in examples()]
    with pytest.raises(common.StudyError,match='view_id'):ra.normalize(data)
    data=[dict(r,view_id='photo_1') for r in data];data[1]['view_id']='photo_2'
    result=ra.normalize(data)
    assert next(r for r in result if r['label_id']=='leaf_2')['relative_area']==1


def test_bad_or_duplicate_area_rejected():
    with pytest.raises(common.StudyError,match='Duplicate'):ra.normalize(examples()*2)
    for invalid in [-1,float('nan'),float('inf')]:
        data=examples();data[0]['area_cm2']=invalid
        with pytest.raises(common.StudyError):ra.normalize(data)


def test_csv_round_trip_preserves_source(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    source=tmp_path/'input.csv';common.write_rows(source,examples(),ra.COLUMNS)
    before=common.file_hash(source)
    result=ra.run(source,tmp_path/'out')
    assert result['units']=='dimensionless' and result['rows'][1]['relative_area']==1.5
    assert common.file_hash(source)==before
    assert common.rows(tmp_path/'out/relative_leaf_areas.csv')[0]['reference_label_id']=='leaf_10'
