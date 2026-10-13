"""SAM regions constrain geometry without becoming point correspondences."""
from copy import deepcopy

import numpy as np
from PIL import Image

from tools import sam_supported_leaf_patches as tool
from tools.leaf_light import common
from tools.manual_leaf_preview import project
from tools.tests.test_visible_leaf_patch import case
from tools.visible_leaf_patch import make_patch


def test_candidate_selection_prefers_saved_observations_over_score():
    def candidate(box, score, index):
        a,b,c,d=box
        return dict(rings=[dict(points_px=[[a,b],[c,b],[c,d],[a,d]],is_hole=False)],score=score,candidate_index=index)
    result=tool.choose_candidate([candidate([0,0,10,10],.99,0),candidate([20,20,60,60],.5,1)],
                                  np.array([[30,30],[40,40]]),(100,100))
    assert result['candidate_index']==1 and result['observed_points_inside']==2
    assert result['human_review']=='pending'


def test_holes_remove_surface_instead_of_creating_correspondences(case):
    capture,rows,region=case
    square=np.array([[-30,-30,0],[30,-30,0],[30,30,0],[-30,30,0]],float)
    hole=np.array([[-10,-10,0],[10,-10,0],[10,10,0],[-10,10,0]],float)
    for obs,frame in zip(region['observations'],capture['frames']):
        outer=project(square,frame,capture['intrinsics']).tolist()
        obs.update(boundary_xy_px=outer,rings=[dict(points_px=outer,is_hole=False),
            dict(points_px=project(hole,frame,capture['intrinsics']).tolist(),is_hole=True)])
    model=make_patch(capture,rows,region,4,0)
    xyz=np.array(model['vertices_mm'])
    centers=np.array([xyz[f].mean(axis=0) for f in model['faces']])
    assert not np.any((np.abs(centers[:,0])<10)&(np.abs(centers[:,1])<10))
    assert len(model['physical_landmarks'])==4


def test_batch_uses_existing_depths_and_reports_missing_geometry(case,tmp_path,monkeypatch):
    capture,depths,region=case
    monkeypatch.setattr(common,'BUILD',tmp_path/'build')
    source=tmp_path/'source';source.mkdir()
    for frame in capture['frames']:
        path=source/frame['image_file'];Image.new('RGB',(128,128)).save(path)
        frame.update(image_path=str(path),sha256=common.file_hash(path))
        for row in depths:
            if row['image_file']==frame['image_file']:
                row['image_sha256']=frame['sha256']
                xy=project(np.array([[row[k] for k in ('x_board_mm','y_board_mm','z_board_mm')]]),frame,capture['intrinsics'])[0]
                row.update(x_px=xy[0],y_px=xy[1])
    missing=deepcopy(depths[0]);missing.update(organ_id='missing',z_board_mm='unavailable')
    depths.append(missing)
    common.write_json(source/'capture.json',capture)
    common.write_rows(source/'editor_point_depths.csv',depths,tuple(depths[0]))
    class Model:
        def info(self):return dict(is_mock=True)
    monkeypatch.setattr(tool,'load_segmenter',lambda *args:Model())
    ring=dict(points_px=[[1,1],[126,1],[126,126],[1,126]],is_hole=False)
    monkeypatch.setattr(tool,'propose',lambda *args:dict(candidates=[dict(rings=[ring],score=.5,candidate_index=0)]))
    before=common.file_hash(source/'editor_point_depths.csv')
    report=tool.build(source,tmp_path/'unused.json',tmp_path/'build/result')
    assert report['records'][0]['status']=='diagnostic_partial_patch'
    assert report['records'][1]['status']=='unavailable'
    assert common.file_hash(source/'editor_point_depths.csv')==before
    assert not report['existing_labels_modified'] and not report['suitable_for_ppfd']
