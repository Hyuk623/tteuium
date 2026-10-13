import json
from pathlib import Path

import numpy as np
import pytest

from tools.tests.test_vein_landmarks import workflow, body
from tools.vein_boundary import boundary_candidates, check_boundary_polygon
from tools.leaf_surface_review import run_surface, surface_results
from tools import vein_surface_bridge


def surface_body(w, a='s0', b='s1'):
    v=body(w,a,b)
    for i,xy in enumerate([[-20,-20],[20,-20],[20,20],[-20,20]]):
        point=np.array([*xy,0.])
        pixels=[w.cams.project(w.lab.samples[s]['image_file'],[point])[0].tolist() for s in (a,b)]
        v['points'].append(dict(point_id='B'+str(i),xy=pixels,state='confirmed',kind='boundary',
            boundary_index=i,boundary_reviewed=True))
    v['points'][0]['xy']=[w.cams.project(w.lab.samples[s]['image_file'],[[0.,0.,0.]])[0].tolist() for s in (a,b)]
    return v


def test_boundary_candidates_keep_components_and_exclude_holes():
    mask=np.zeros((100,100),bool);mask[5:40,5:40]=True;mask[60:90,60:90]=True;mask[15:30,15:30]=False
    nodes=boundary_candidates(mask,[100,200])
    assert len({n['component'] for n in nodes})==2
    assert all(mask[n['xy_original_px'][1]-200,n['xy_original_px'][0]-100] for n in nodes)
    assert all(n['review']=='unreviewed' for n in nodes)
    assert not any(115<=n['xy_original_px'][0]<=130 and 215<=n['xy_original_px'][1]<=230 for n in nodes)


def test_surface_requires_human_points_and_never_fabricates_them(workflow):
    r=run_surface(workflow,'L1','diagnostic','synthetic audit')
    assert r['reason']=='no_human_confirmed_points' and r['triangles']==[] and r['reviewed_by'] is None
    assert workflow.latest_reviews()==[]


def test_surface_build_reprojection_and_stale_edit(workflow,monkeypatch):
    monkeypatch.setattr(vein_surface_bridge,'assert_build',lambda p:p)
    w=workflow;v=surface_body(w);w.save(v)
    r=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert r['status']=='interpolated_partial_surface',r
    assert len(r['triangles'])==4 and len(r['projections'])==2
    assert not r['suitable_for_ppfd']
    assert not surface_results(w)['results'][0]['stale']
    v['points'][0]['xy']=[[201,200],[151,200]];w.save(v)
    assert surface_results(w)['results'][0]['stale']
    newer=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert newer['path']!=r['path']
    assert newer['points'][0]['xyz_mm']!=r['points'][0]['xyz_mm']
    assert (w.lab.root/r['path']/'result.json').is_file()


@pytest.mark.parametrize('change,message',[
    ('unreviewed','actual visible leaf boundary'),('duplicate','Duplicate boundary order'),
    ('interior_index','Interior point'),('fractional','integer')])
def test_invalid_boundary_rows_rejected(workflow,change,message):
    v=surface_body(workflow)
    if change=='unreviewed':v['points'][1]['boundary_reviewed']=False
    elif change=='duplicate':v['points'][2]['boundary_index']=0
    elif change=='interior_index':v['points'][0]['boundary_index']=1
    else:v['points'][1]['boundary_index']=.5
    with pytest.raises(ValueError,match=message):workflow.save(v)


def test_cross_view_role_conflict(workflow):
    w=workflow;w.save(surface_body(w))
    other=surface_body(w,'s0','s2');other['points']=[other['points'][0],other['points'][2]]
    other['points'][1]['kind']='interior';other['points'][1]['boundary_index']=-1
    with pytest.raises(ValueError,match='kind/order'):w.save(other)


def test_heldout_third_view_is_not_silently_used(workflow,monkeypatch):
    monkeypatch.setattr(vein_surface_bridge,'assert_build',lambda p:p)
    w=workflow;w.context['membership']['m2']='L1'
    # This synthetic in-memory context change affects only the fixture's identity map.
    w.save(surface_body(w));r=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert len(r['projections'])==3
    third=next(v for v in r['projections'] if v['image_file']=='2.png')
    assert not third['used_for_fit'] and all(p['observed_xy'] is None for p in third['points'])


def test_surface_strict_failure_and_gapped_boundary_order(workflow):
    w=workflow;w.save(surface_body(w))
    r=run_surface(w,'L1','strict','synthetic reviewer')
    assert r['status']=='unavailable' and not r['triangles']
    v=surface_body(w);v['points'][-1]['boundary_index']=7;w.save(v)
    assert run_surface(w,'L1','diagnostic','synthetic reviewer')['reason']=='boundary_order_incomplete_or_failed_points'


def test_crossed_and_repeated_boundary_order():
    p=np.array([[0,0,0],[2,2,0],[0,2,0],[2,0,0]],float)
    with pytest.raises(ValueError,match='self_intersecting'):check_boundary_polygon(p)
    with pytest.raises(ValueError,match='repeated|intersecting'):check_boundary_polygon(np.array([[0,0,0],[0,0,0],[2,2,0]]))


def test_hole_is_not_filled(workflow,monkeypatch):
    monkeypatch.setattr(vein_surface_bridge,'assert_build',lambda p:p)
    w=workflow;original=w.lab.load
    def load(s):
        rgb,mask=original(s)
        # Hole within the top triangle, away from every annotated vertex.
        mask[85:90,(85 if s=='s0' else 35):(90 if s=='s0' else 40)]=False
        return rgb,mask
    w.lab.load=load;w.save(surface_body(w));r=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert len(r['triangles'])<4
    assert r['bridge']['removed']


def test_source_change_marks_saved_surface_stale_without_repair(workflow):
    w=workflow;run_surface(w,'L1','diagnostic','synthetic audit')
    w.lab.dataset_path.write_text('{}')
    result=surface_results(w)['results'][0]
    assert result['stale'] and result['freshness_error']
    assert w.lab.dataset_path.read_text()=='{}'
    with pytest.raises(ValueError):run_surface(w,'L1','diagnostic','synthetic audit')


def test_third_view_addition_preserves_two_view_run(workflow,monkeypatch):
    monkeypatch.setattr(vein_surface_bridge,'assert_build',lambda p:p)
    w=workflow;w.context['membership']['m2']='L1'
    w.save(surface_body(w));old=run_surface(w,'L1','diagnostic','synthetic reviewer')
    extra=surface_body(w,'s0','s2');extra['points']=[extra['points'][0],extra['points'][2]]
    w.save(extra);new=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert new['path']!=old['path']
    assert not next(v for v in old['projections'] if v['image_file']=='2.png')['used_for_fit']
    assert next(v for v in new['projections'] if v['image_file']=='2.png')['used_for_fit']
    assert surface_results(w)['results'][0]['stale']
    assert json.loads((w.lab.root/old['path']/'result.json').read_text(encoding='utf-8'))['path']==old['path']


def test_collinear_boundary_cannot_generate_surface(workflow,monkeypatch):
    monkeypatch.setattr(vein_surface_bridge,'assert_build',lambda p:p)
    w=workflow;v=surface_body(w)
    v['points']=v['points'][:4]
    for row,xyz in zip(v['points'],[[0,10,0],[-20,0,0],[0,0,0],[20,0,0]]):
        row['xy']=[w.cams.project(w.lab.samples[s]['image_file'],[xyz])[0].tolist() for s in ('s0','s1')]
    w.save(v);r=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert r['status']=='points_only' and not r['triangles']
    assert r['reason']=='collinear_boundary_points'


def test_disconnected_masks_not_joined_by_surface(workflow,monkeypatch):
    monkeypatch.setattr(vein_surface_bridge,'assert_build',lambda p:p)
    w=workflow;original=w.lab.load
    def split_mask(s):
        rgb,mask=original(s)
        mask[85:95,:]=False
        return rgb,mask
    w.lab.load=split_mask
    w.save(surface_body(w));r=run_surface(w,'L1','diagnostic','synthetic reviewer')
    assert r['status']=='points_only' and not r['triangles']
    assert r['reason'].startswith('boundary_crosses_disconnected_visible_components')
