from datetime import date, timedelta

import numpy as np
import pytest

from tools.first_flowering import (events, feature_table, fit_aft, log_probability,
    plot_summary, predict_aft, compare_models, templates, analyse)
from tools.leaf_light.common import StudyError, read_json, write_json


def plant(pid='p1',plot='a',split='development'):
    return dict(plant_id=pid,plot_id=plot,density_id='dense',start_date='2026-09-01',end_date='2026-09-30',split=split)


def visit(day,state,pid='p1',confirmed='true',photo='flower.jpg'):
    return dict(plant_id=pid,date=f'2026-09-{day:02d}',state=state,human_confirmed=confirmed,evidence_photo=photo)


def test_intervals_and_right_censoring_not_end_date(tmp_path):
    (tmp_path/'flower.jpg').write_bytes(b'evidence placeholder for test only')
    records=events([plant(),plant('p2','b')],
        [visit(1,'not_open'),visit(5,'bud_only'),visit(6,'missed'),visit(9,'first_open'),
         visit(1,'not_open','p2'),visit(12,'not_open','p2'),visit(30,'missed','p2')],tmp_path)
    assert records[0]['event_status']=='interval_censored'
    assert (records[0]['lower_day'],records[0]['upper_day'])==(4,8)
    assert records[1]['event_status']=='right_censored'
    assert records[1]['lower_day']==11 and records[1]['upper_day'] is None
    assert sum(r['n_confirmed_open'] for r in plot_summary(records))==1


def test_entry_flower_unknown_baseline_and_unverified_not_promoted(tmp_path):
    (tmp_path/'flower.jpg').write_bytes(b'test')
    result=events([plant(),plant('p2','b'),plant('p3','c')],
        [visit(1,'first_open'),visit(5,'first_open','p2'),visit(5,'first_open','p3','false')],tmp_path)
    assert [r['event_status'] for r in result]==['already_flowered_at_entry','baseline_unknown','no_confirmed_observation']


def test_photo_and_group_leakage_and_reversion(tmp_path):
    with pytest.raises(StudyError,match='evidence photo'):
        events([plant()],[visit(2,'first_open')],tmp_path)
    with pytest.raises(StudyError,match='One plot'):
        events([plant(),plant('p2','a','evaluation')],[],tmp_path)
    (tmp_path/'flower.jpg').write_bytes(b'test')
    with pytest.raises(StudyError,match='revert'):
        events([plant()],[visit(2,'first_open'),visit(4,'not_open')],tmp_path)


def test_future_feature_and_geometry_leakage(tmp_path):
    e=events([plant()],[visit(10,'not_open')],tmp_path)
    growth=[dict(plant_id='p1',date=d,height_mm=h,leaf_count=4,reviewed_leaf_area_mm2=100) for d,h in [('2026-09-01',12),('2026-09-15',999)]]
    light=[dict(plant_id='p1',date='2026-09-01',geometry_date='2026-09-01',lower_ppfd_umol_m2_s=20,upper_ppfd_umol_m2_s=50,leaf_ppfd_cv=.2,source_run='actual-run',review_state='reviewed')]
    f,excluded=feature_table(e,growth,light,0)
    assert not excluded and f[0]['height_mm']==12
    light[0]['geometry_date']='2026-09-02'
    with pytest.raises(StudyError,match='later'):
        feature_table(e,growth,light,0)


def test_aft_censoring_likelihood_and_plot_disjoint_comparison():
    p=log_probability(np.array([0.,10.,20.]),np.array([10.,20.,np.inf]),np.full(3,np.log(15)),.5)
    assert np.exp(p).sum()==pytest.approx(1)
    rng=np.random.default_rng(45); records=[]
    for i in range(90):
        x=float(rng.normal()); t=float(np.exp(3+.25*x+rng.normal(0,.3)))
        censored=i%4==0
        records.append(dict(plant_id=f'p{i}',plot_id=f'g{i//3}',split='development' if i<60 else 'evaluation',
            lower_day=12. if censored else max(0,t-1),upper_day=None if censored else t+1,
            landmark_day=0,height_mm=100+x,leaf_count=5,reviewed_leaf_area_mm2=500,
            lower_ppfd_umol_m2_s=100+10*x,upper_ppfd_umol_m2_s=200,leaf_ppfd_cv=.2,light_exclusion=None))
    settings=dict(ridge=1.,max_iterations=2000,min_development_plots=4,min_development_events=10,min_evaluation_plots=3)
    result=compare_models(records,settings)
    assert result['status']=='evaluated_exploratory'
    assert result['models']['baseline']['n_plots']==20
    assert all(r['predicted_total_day_median']>0 for r in result['models']['baseline']['predictions'])
    settings['min_development_plots']=None
    assert compare_models(records,settings)['status']=='unavailable'
    records[-1]['plot_id']='g0'
    with pytest.raises(StudyError,match='leakage'):
        compare_models(records,settings)


def test_empty_templates_can_analyse_without_manufactured_outcomes(tmp_path):
    templates(tmp_path/'input')
    result=analyse(tmp_path/'input',tmp_path/'out',tmp_path/'input/analysis_settings.json')
    assert result['n_plants']==0 and result['prediction_status']=='unavailable'
    assert result['photosynthesis']=='unavailable'
