"""Explicit chart/raster integration against known holes and folded tissue."""
from copy import deepcopy

import cv2
import numpy as np
import pytest
from PIL import Image, ImageDraw

from tools import leaf_surface_compare as sc
from tools.leaf_light import common
from tools.leaf_light.annotations import POINT_COLUMNS
from tools.leaf_light.reconstruction import project
from tools.tests.test_leaf_surface_compare import fixture
from tomato3d.light.geometry import triangle_areas_mm2


def make_study(folder, kind='hole'):
    folder.mkdir(parents=True,exist_ok=True)
    capture,_,_,base_patch,study=fixture()
    capture['coordinate_frame']='board'
    if kind=='hole':
        xyz=np.array([[-20,-20,500],[20,-20,500],[20,20,500],[-20,20,500],
                      [-5,-5,500],[5,-5,500],[5,5,500],[-5,5,500]],float)
        charts=[dict(point_ids=[f'p{i}' for i in range(8)],boundary_point_ids=['p0','p1','p2','p3'],
                     hole_point_ids=[['p4','p5','p6','p7']])]
    elif kind=='fold':
        xyz=np.array([[-20,-10,500],[0,-10,500],[0,10,500],[-20,10,500],
                      [20,-10,510],[20,10,510]],float)
        charts=[dict(point_ids=ring,boundary_point_ids=ring,hole_point_ids=[])
                for ring in [['p0','p1','p2','p3'],['p1','p4','p5','p2']]]
    else:
        xyz=np.array([[-40,-10,500],[-20,-10,500],[-20,10,500],[-40,10,500],
                      [20,-10,500],[40,-10,500],[40,10,500],[20,10,500]],float)
        charts=[dict(point_ids=ring,boundary_point_ids=ring,hole_point_ids=[])
                for ring in [['p0','p1','p2','p3'],['p4','p5','p6','p7']]]
    patches=[dict(base_patch,tissue_patch_id=f'chart_{i}',local_chart=chart,visible_support=[]) for i,chart in enumerate(charts)]
    points=[]
    for frame in capture['frames']:
        xy=project(xyz,frame,capture['intrinsics'])
        im=folder/f"frame_{frame['image_file']}.png"
        picture=Image.new('RGB',(600,600),(230,235,230));draw=ImageDraw.Draw(picture)
        for chart in charts:
            draw.polygon([tuple(xy[int(p[1:])]) for p in chart['boundary_point_ids']],fill=(70,150,95))
            for ring in chart['hole_point_ids']:
                draw.polygon([tuple(xy[int(p[1:])]) for p in ring],fill=(230,235,230))
        draw.text((20,20),'SYNTHETIC '+kind,fill='black');picture.save(im)
        frame.update(image_path=im.name,sha256=common.file_hash(im))
        for i,uv in enumerate(xy):
            points.append(dict(image_file=frame['image_file'],organ_id='L1',leaflet_id='l1',point_id=f'p{i}',
                               x_px=uv[0],y_px=uv[1],boundary_index=-1,boundary_count=0))
        if frame['image_file'] not in study['fit_images']:
            continue
        for patch in patches:
            # Independently rasterized known polygon; retain its boundary pixels.
            chart=patch['local_chart'];mask=np.zeros((600,600),np.uint8)
            boundary=np.rint(xy[[int(p[1:]) for p in chart['boundary_point_ids']]]).astype(np.int32)
            cv2.fillPoly(mask,[boundary],255)
            for ring in chart['hole_point_ids']:
                hole=np.zeros_like(mask)
                uv=np.rint(xy[[int(p[1:]) for p in ring]]).astype(np.int32)
                cv2.fillPoly(hole,[uv],255);cv2.polylines(hole,[uv],True,0,1)
                mask[hole!=0]=0
            path=folder/f"{patch['tissue_patch_id']}_{frame['image_file']}_mask.png"
            Image.fromarray(mask).save(path)
            patch['visible_support'].append(dict(image_file=frame['image_file'],visibility='visible',
                review_source='synthetic analytic polygon',mask=path.name,mask_sha256=common.file_hash(path)))
    study.update(schema='leaf-surface-comparison-1',capture='capture.json',points='points.csv',
                 evidence_kind='synthetic',patches=patches)
    common.write_json(folder/'capture.json',capture)
    common.write_rows(folder/'points.csv',points,POINT_COLUMNS)
    common.write_json(folder/'study.json',study)
    return folder/'study.json'


def area(method):
    faces=np.array([[[r[f'v{i}_{a}_mm'] for a in 'xyz'] for i in range(3)] for r in method['faces']])
    return triangle_areas_mm2(faces).sum()/100


@pytest.mark.parametrize('kind,expected', [('hole',15.),('disconnected',8.),('fold',(400+20*np.sqrt(500))/100)])
def test_known_chart_topology_and_global_area(tmp_path,monkeypatch,kind,expected):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    study=make_study(tmp_path/'inputs',kind)
    report=sc.run(study,tmp_path/'out')
    assert report['source_hashes_verified']
    assert not report['physical_validation'] and not report['suitable_for_ppfd']
    for name,audit in report['global_surface_audits'].items():
        methods=[next(m for m in p['methods'] if m['method']==name) for p in report['patches']]
        assert sum(area(m) for m in methods)==pytest.approx(expected,abs=1e-8)
        assert audit['compounds'][0]['supported_area_cm2']==pytest.approx(expected,abs=1e-8)
        assert not audit['intersecting_pairs'] and not audit['duplicate_pairs']
        assert all(m['heldout']['rms_px']<1e-8 for m in methods)
    assert len(report['patches'])==(1 if kind=='hole' else 2)
    assert all(p['leaflet_id']=='l1' for p in report['patches'])
    # Multiple charts of the same labelled leaf must be aggregated before division.
    assert len(report['relative_leaf_areas'])==2  # one leaf, two estimators
    assert all(r['relative_area']==1 and r['area_cm2']==pytest.approx(expected,abs=1e-8)
               and r['area_scope']=='supported_partial_surface' for r in report['relative_leaf_areas'])
    if kind=='hole':
        assert all('mask.png' in p for p in report['source_hashes'] if 'mask' in p)


def test_mask_hash_and_coordinate_guard(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    path=make_study(tmp_path/'inputs')
    study=common.read_json(path);v=study['patches'][0]['visible_support'][0]
    mask=path.parent/v['mask'];Image.new('L',(100,100),255).save(mask)
    with pytest.raises(common.StudyError,match='hash mismatch'):sc.run(path,tmp_path/'bad_hash')
    v['mask_sha256']=common.file_hash(mask);common.write_json(path,study)
    with pytest.raises(common.StudyError,match='original calibrated'):sc.run(path,tmp_path/'bad_size')


def test_occluded_mask_is_not_negative_and_support_stays_unavailable(tmp_path,monkeypatch):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    path=make_study(tmp_path/'inputs');study=common.read_json(path)
    study['patches'][0]['visible_support'][1]=dict(image_file='1',visibility='occluded',review_source='synthetic')
    common.write_json(path,study);report=sc.run(path,tmp_path/'out')
    for method in report['patches'][0]['methods']:
        assert method['audit']['compounds'][0]['supported_area_cm2'] is None
        assert all('insufficient_visible_support' in f['reasons'] for f in method['audit']['faces'])
        assert all('face_outside_visible_tissue' not in f['reasons'] for f in method['audit']['faces'])


@pytest.mark.parametrize('damage',['missing_point','duplicate_point','missing_mask','heldout_mask','repeated_patch'])
def test_unsupported_chart_contract_cannot_silently_pass(tmp_path,monkeypatch,damage):
    monkeypatch.setattr(common,'BUILD',tmp_path)
    path=make_study(tmp_path/'inputs');study=common.read_json(path);patch=study['patches'][0]
    if damage=='missing_point':patch['local_chart']['boundary_point_ids'][0]='foreign'
    if damage=='duplicate_point':patch['local_chart']['point_ids'].append('p0')
    if damage=='missing_mask':del patch['visible_support']
    if damage=='heldout_mask':patch['visible_support'][1]['image_file']='2'
    if damage=='repeated_patch':study['patches'].append(deepcopy(patch))
    common.write_json(path,study)
    with pytest.raises(common.StudyError):sc.run(path,tmp_path/'out')
