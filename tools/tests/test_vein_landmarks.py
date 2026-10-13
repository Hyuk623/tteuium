"""Vein proposals are not identity labels; test geometry and review invariants."""
import json
from pathlib import Path
from types import SimpleNamespace

import cv2
import numpy as np
import pytest

from tools.vein_landmarks import graph, skeletonize, propose_matches
from tools.vein_correspondence import Workflow, digest, settings
from tools.leaf_preprocess_lab import sha, write_json


def y_image():
    a=np.zeros((101,101),np.uint8)
    for p in [(18,15),(82,15),(50,88)]: cv2.line(a,(50,50),p,255,5)
    return a


def test_y_representative_on_skeleton_original_coordinates_and_topology():
    a=y_image(); g=graph(a/255,np.ones(a.shape,bool),np.repeat(a[...,None],3,axis=2),[100,200,201,301])
    junctions=[n for n in g['nodes'] if n['kind']=='junction']
    assert len(junctions)==1
    n=junctions[0]; x,y=n['xy_original_px']
    assert g['skeleton'][y-200,x-100] and n['degree']==3
    assert len(n['ordered_neighbours'])==3
    assert len(g['edges'])==3
    assert sum(n['kind']=='endpoint' for n in g['nodes'])==3


def test_occlusion_gap_is_not_bridged_and_blank_stays_unavailable():
    a=y_image(); valid=np.ones(a.shape,bool); valid[58:67]=False
    g=graph(a/255,valid,np.repeat(a[...,None],3,axis=2),[0,0,101,101])
    assert not g['skeleton'][58:67].any()
    for e in g['edges']:
        assert not any(58<=y<67 for x,y in e['xy_original_px'])
    empty=graph(np.zeros(a.shape),valid,np.zeros((*a.shape,3),np.uint8),[0,0,101,101])
    assert empty['status']=='no_evidence' and empty['nodes']==[]


@pytest.mark.parametrize('angle',[0,90,180,270])
def test_rotated_bright_y_keeps_candidate_not_automatic_truth(angle):
    a=np.rot90(y_image(),angle//90)
    rgb=np.repeat((a*.5+40).astype(np.uint8)[...,None],3,axis=2)
    g=graph(a/255,np.ones(a.shape,bool),rgb,[0,0,101,101])
    m=propose_matches(g,g)
    assert len(m)==1 and m[0]['status']=='unreviewed'
    assert m[0]['score']==pytest.approx(0)


def test_reflection_and_repeated_pattern_conflict_top_three():
    rng=np.random.default_rng(3); patch=rng.normal(size=(9,9))
    def node(i,p): return dict(id=i,kind='junction',degree=3,neighbour_degrees=[1,1,3],descriptor=p.ravel().tolist())
    left=dict(nodes=[node('a',patch),node('b',patch)])
    right=dict(nodes=[node(str(i),patch[:,::-1]) for i in range(5)])
    m=propose_matches(left,right)
    assert len(m)==6 and all(r['ambiguous_target'] and r['reflected_patch'] for r in m)
    assert all(r['score']==pytest.approx(0) for r in m)


@pytest.fixture
def workflow(tmp_path):
    root=tmp_path/'run'; root.mkdir(); (root/'landmarks').mkdir()
    rgb=np.full((200,200,3),80,np.uint8); mask=np.ones((200,200),bool)
    cv2.line(rgb,(100,100),(40,30),(180,190,170),5)
    cv2.line(rgb,(100,100),(160,30),(180,190,170),5)
    cv2.line(rgb,(100,100),(100,175),(180,190,170),5)
    samples={f's{i}':dict(id=f's{i}',plant_id='test',session_id='session',image_file=f'{i}.png',
        observation_id=f'm{i}',source_annotation_id=i,crop_xyxy_px=[100,100,300,300]) for i in range(3)}
    dataset=root/'dataset.json'; write_json(dataset,dict(samples=list(samples.values())))
    frames=[dict(image_file=f'{i}.png',pose_status='solved',rvec_rad=[0,0,0],tvec_mm=[-50*i,0,1000],passes_pose_gate=False) for i in range(3)]
    capture=dict(plant_id='test',session_id='session',coordinate_frame='board',frames=frames,
        intrinsics=dict(camera_matrix=[[1000,0,200],[0,1000,200],[0,0,1]],dist_coeffs=[0,0,0,0,0],image_width_px=400,image_height_px=400),
        quality=dict(min_ray_angle_deg=2,max_point_error_px=2,contour_tolerance_px=1))
    context=dict(capture=capture,membership={'m0':'L1','m1':'L1'},different=[],excluded=[],sources={},
        discovery=dict(roots=[],downloads=str(tmp_path/'absent'),pattern='*.json'),discovered=[],dataset_sha256=sha(dataset))
    write_json(root/'landmarks/context.json',context)
    lab=SimpleNamespace(root=root,samples=samples,dataset_path=dataset,load=lambda sid:(rgb.copy(),mask.copy()))
    return Workflow(lab)


def body(w,a='s0',b='s1',pid='J1',xy=None,state='confirmed'):
    pair=w.pair(a,b,{})
    return dict(a=a,b=b,graph_settings={},signature=pair['signature'],identity='same',leaflet_id='L1',
        points=[dict(point_id=pid,xy=xy or [[200,200],[150,200]],state=state)],review_seconds=1)


def test_only_human_confirmed_points_pass_to_existing_triangulation(workflow):
    w=workflow; b=body(w); b['points'].append(dict(point_id='unreviewed',xy=[[210,210],[160,210]],state='pending'))
    w.save(b)
    strict=w.export('strict'); assert strict['points'][0]['reason']=='fewer_than_two_eligible_poses'
    diag=w.export('diagnostic'); assert len(diag['points'])==1
    assert diag['points'][0]['xyz_mm']==pytest.approx([0,0,0],abs=1e-8)
    assert len(diag['points'][0]['reprojections'])==2
    assert not diag['validated_metric'] and not diag['suitable_for_ppfd']
    b['identity']='unresolved'; w.save(b); assert not w.export('diagnostic')['points']


def test_original_coordinate_mask_validation_and_many_to_one(workflow):
    w=workflow; b=body(w)
    b['points'].append(dict(point_id='J2',state='confirmed',xy=[[201,200],[150,200]]))
    with pytest.raises(ValueError,match='Many-to-one'): w.save(b)
    b=body(w,xy=[[99,99],[150,200]])
    with pytest.raises(ValueError,match='outside'): w.save(b)


def test_changes_make_old_exports_stale_and_recalculation_new(workflow):
    w=workflow; b=body(w); w.save(b); old=w.export('diagnostic')
    assert not w.status()['exports'][0]['stale']
    b['points'][0]['xy']=[[201,200],[151,200]]; w.save(b)
    assert w.status()['exports'][0]['stale']
    new=w.export('diagnostic'); assert old['path']!=new['path']
    assert new['points'][0]['xyz_mm'][0]==pytest.approx(1,abs=1e-8)
    w.pair('s0','s1',dict(sigma_px=3))
    assert all(x['stale'] for x in w.status()['exports'])
    assert w.export('diagnostic')['excluded'][0]['reason']=='stale_settings'


def test_negative_identity_and_source_change(workflow):
    w=workflow
    w.context['different']=[['m0','m2']]
    assert w.relation('s1','s2')=='different'
    with pytest.raises(ValueError,match='Blocked'): w.pair('s1','s2',{})
    w.lab.dataset_path.write_text('{}')
    with pytest.raises(ValueError,match='stale'): w.verify()


def test_global_conflicting_point_ids_are_blocked(workflow):
    w=workflow; w.save(body(w))
    w.save(body(w,'s0','s2','J2',[[200,200],[100,200]]))
    with pytest.raises(ValueError,match='Cross-pair'): w.export('diagnostic')


def test_pose_absence_still_allows_review_but_not_geometry(workflow):
    w=workflow
    w.context['capture']['frames'][1]['pose_status']='failed'
    b=body(w); w.save(b)
    assert w.epiline('s0','s1',[200,200])==[]
    assert w.export('diagnostic')['points'][0]['status']=='unavailable'


def test_ray_and_reprojection_gates_remain_active(workflow):
    w=workflow; b=body(w,xy=[[200,200],[150,230]]); w.save(b)
    w.context['capture']['quality']['min_ray_angle_deg']=0
    assert w.export('diagnostic')['points'][0]['reason']=='reprojection_error'
    w.context['capture']['quality']['min_ray_angle_deg']=2
    b=body(w,xy=[[200,200],[199,200]]); w.save(b)
    assert w.export('diagnostic')['points'][0]['reason']=='insufficient_parallax'


def test_epiline_and_settings_validation(workflow):
    line=np.array(workflow.epiline('s0','s1',[200,200]))
    assert len(line)==100 and np.allclose(line[:,1],200)
    for cfg in [{'sigma_px':4},{'threshold':float('nan')},{'threshold':True}]:
        with pytest.raises(ValueError): settings(cfg)


def test_saved_different_link_cannot_be_bypassed_through_third_view(workflow):
    w=workflow
    b=body(w); b['identity']='different';w.save(b)
    w.save(body(w,'s0','s2','J1',[[200,200],[100,200]]))
    w.save(body(w,'s1','s2','J1',[[150,200],[100,200]]))
    with pytest.raises(ValueError,match='Human different'):w.export('diagnostic')


def test_rejected_triple_does_not_break_confirmed_pair(workflow):
    w=workflow;w.context['different_sets']=[dict(decision='ext1',masks=['m0','m1','m2'])]
    assert w.relation('s0','s1')=='same'
    w.save(body(w)); assert w.export('diagnostic')['points'][0]['xyz_mm'] is not None
    p=w.pair('s0','s2',{})
    assert p['known_points'][0]['point_id']=='J1'
    w.save(body(w,'s0','s2','J1',[[200,200],[100,200]]))
    with pytest.raises(ValueError,match='Rejected multi-view group'):w.export('diagnostic')


def test_unobserved_point_is_saved_pending_not_filled(workflow):
    b=body(workflow,state='pending');b['points'][0]['xy'][1]=None
    r=workflow.save(b)
    assert r['record']['points'][0]['visibility']==['observed','unobserved']
    assert not workflow.export('diagnostic')['points']
    b['points'][0]['state']='confirmed'
    with pytest.raises(ValueError,match='both views'):workflow.save(b)


def test_http_vein_routes_token_and_no_nested_lock(workflow):
    import threading
    import urllib.request
    import urllib.error
    from http.server import ThreadingHTTPServer
    from tools.leaf_preprocess_lab import handler
    app=workflow.lab; app.vein_workflow=workflow; app.token='fixture-only'; app.lock=threading.Lock()
    server=ThreadingHTTPServer(('127.0.0.1',0),handler(app))
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    url=f'http://127.0.0.1:{server.server_port}/api/vein/pair'
    data=json.dumps(dict(a='s0',b='s1',graph_settings={})).encode()
    try:
        with pytest.raises(urllib.error.HTTPError) as e:urllib.request.urlopen(urllib.request.Request(url,data=data),timeout=5)
        assert e.value.code==403
        req=urllib.request.Request(url,data=data,headers={'X-Lab-Token':app.token,'Content-Type':'application/json'})
        result=json.load(urllib.request.urlopen(req,timeout=5))
        assert result['relation']=='same' and result['left']['nodes']
        def post(action,payload):
            req=urllib.request.Request(url.removesuffix('pair')+action,data=json.dumps(payload).encode(),
                headers={'X-Lab-Token':app.token,'Content-Type':'application/json'})
            return json.load(urllib.request.urlopen(req,timeout=5))
        assert len(post('view-guide',{'a':'s0'})['photos'])==3
        assert all(r['image_file']=='1.png' for r in post('candidates',{'a':'s0','image_file':'1.png'})['candidates'])
        review=dict(a='s0',b='s1',graph_settings={},signature=result['signature'],identity='same',leaflet_id='L1',
                    points=[dict(point_id='http_point',xy=[[200,200],[150,200]],state='confirmed')])
        assert post('save',review)['record']['points'][0]['state']=='confirmed'
        assert post('export',{'mode':'diagnostic'})['points'][0]['xyz_mm']==pytest.approx([0,0,0],abs=1e-8)
        review['points'][0]['xy']=[[201,200],[151,200]]
        post('save',review)
        assert post('status',{})['exports'][0]['stale']
        surface=post('surface',{'leaflet_id':'L1','mode':'diagnostic','reviewed_by':'synthetic fixture'})
        assert surface['status']=='points_only' and not surface['triangles']
        assert not post('surface-results',{})['results'][0]['stale']
    finally:server.shutdown();server.server_close();thread.join()


def test_view_guide_uses_measured_pose_not_capture_angles(workflow):
    from tools.vein_view_guide import view_guide
    w=workflow
    w.cams.frames['1.png']['tvec_mm']=[-1000,0,1000]
    w.cams.frames['1.png']['azimuth_deg']=170
    w.cams.frames['2.png']['pose_status']='too_few_corners'
    w.cams.frames['2.png']['azimuth_deg']=45
    before=digest(w.context)
    result=view_guide(w,'s0');rows={r['image_file']:r for r in result['photos']}
    assert rows['1.png']['board_origin_view_angle_deg']==pytest.approx(45)
    assert not rows['1.png']['poses_pass_gate']
    assert rows['2.png']['board_origin_view_angle_deg'] is None
    assert digest(w.context)==before and not result['suitable_for_ppfd']


def test_view_guide_only_hash_matched_markers_and_missing_labels(workflow):
    from tools.vein_view_guide import view_guide
    w=workflow
    for sid in ['s0','s1']:
        w.lab.samples[sid]['source_image_sha256']='expected'
        w.cams.frames[w.lab.samples[sid]['image_file']]['board_evidence']={
            'source_image_sha256':'expected','detected_marker_ids':[2,4,4]}
    w.context['capture']['frames'].append({'image_file':'22.png','pose_status':'unavailable','view_code':'22'})
    rows={r['image_file']:r for r in view_guide(w,'s0')['photos']}
    assert rows['1.png']['shared_marker_ids']==[2,4]
    assert rows['22.png']['sample_ids']==[]
    w.cams.frames['1.png']['board_evidence']['source_image_sha256']='wrong'
    assert next(r for r in view_guide(w,'s0')['photos'] if r['image_file']=='1.png')['marker_ids']==[]


def test_photo_preview_preserves_original_and_rejects_changed_photo(workflow,tmp_path):
    from PIL import Image
    from tools.vein_view_guide import photo_preview
    w=workflow;p=tmp_path/'photo.png'
    Image.fromarray(np.full((400,400,3),80,np.uint8)).save(p)
    obs=w.lab.samples['s0'];obs.update(source_image=str(p),source_image_sha256=sha(p))
    original=sha(p);before=digest(w.lab.samples)
    result=photo_preview(w,'s0')
    assert result['original_size_px']==[400,400] and result['scale']==1
    assert result['image'].startswith('data:image/png;base64,')
    assert sha(p)==original and digest(w.lab.samples)==before
    p.write_bytes(b'changed')
    with pytest.raises(ValueError,match='photograph changed'):photo_preview(w,'s0')


def test_partial_surface_bridge_uses_actual_boundary_and_preserves_inputs(workflow,tmp_path,monkeypatch):
    from tools import vein_surface_bridge as bridge
    from tools.leaf_light.annotations import POINT_COLUMNS,CONTOUR_COLUMNS
    import csv
    w=workflow;w.save(body(w));result=w.export('diagnostic')
    boundaries=[];contours=[]
    corners=[[-20,-20,0],[20,-20,0],[20,20,0],[-20,20,0]]
    for image in ['0.png','1.png']:
        pixels=w.cams.project(image,np.array(corners,float))
        for i,(x,y) in enumerate(pixels):
            common=dict(image_file=image,organ_id='compound1',leaflet_id='L1',x_px=x,y_px=y)
            boundaries.append(dict(common,point_id=f'B{i}',boundary_index=i,boundary_count=4))
            contours.append(dict(common,vertex_index=i))
    paths=[]
    for name,rows,cols in [('boundary',boundaries,POINT_COLUMNS),('contour',contours,CONTOUR_COLUMNS)]:
        path=tmp_path/(name+'.csv');paths.append(path)
        with path.open('w',newline='') as f:
            writer=csv.DictWriter(f,fieldnames=cols);writer.writeheader();writer.writerows(rows)
    before=[sha(p) for p in paths]
    monkeypatch.setattr(bridge,'assert_build',lambda p:p)
    surface=bridge.run(w,w.lab.root/result['path'],*paths,tmp_path/'surface','synthetic fixture reviewer')
    assert surface['faces']==4 and not surface['suitable_for_ppfd']
    assert [sha(p) for p in paths]==before
    with pytest.raises(ValueError,match='No reviewed boundary'):
        bridge.merge_points([],read_json_rows(w.lab.root/result['path']/'points.interior.csv'))


def read_json_rows(path):
    import csv
    with path.open() as f:return list(csv.DictReader(f))


def test_new_leaflet_id_and_point_id_reused_without_confirming_new_pair(workflow):
    w=workflow;w.context['membership']={}
    first=w.pair('s0','s1',{})
    b=body(w);b['leaflet_id']=first['leaflet_id'];w.save(b)
    second=w.pair('s0','s2',{})
    assert second['leaflet_id']==first['leaflet_id']
    assert second['relation']=='unknown'  # an ID suggestion is not a confirmation
    assert second['known_points'][0]['point_id']=='J1'
    wrong=body(w,'s0','s2',xy=[[200,200],[100,200]])
    wrong['leaflet_id']='another_leaf'
    with pytest.raises(ValueError,match='Reuse'):w.save(wrong)
    changed=w.pair('s0','s1',dict(sigma_px=3))
    assert changed['leaflet_id']==first['leaflet_id']
    assert changed['known_points']==[]  # stale point candidates excluded, identity preserved


def test_summary_separates_identity_points_and_manual_time(workflow):
    w=workflow;b=body(w);b['points'].append(dict(point_id='J2',xy=[[205,205],None],state='pending'))
    b['review_seconds']=1000;w.save(b)
    s=w.status()['review_summary']
    assert s['leaflet_pair_verdicts']==dict(same=1,different=0,unresolved=0)
    assert s['point_pair_verdicts']==dict(confirmed=1,rejected=0,pending=1)
    assert s['correction_seconds'] is None and s['point_correspondence_accuracy'] is None
    b['correction_seconds']=12;w.save(b)
    assert w.status()['review_summary']['correction_seconds']==12
    b['correction_seconds']=-1
    with pytest.raises(ValueError,match='correction time'):w.save(b)
    w.pair('s0','s1',dict(sigma_px=1))
    assert w.status()['review_summary']['stale_pairs']==1
