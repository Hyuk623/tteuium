"""Visible-region clipping preserves concavities without inventing correspondences."""
from copy import deepcopy

import numpy as np
import pytest
from PIL import Image

from tools.visible_leaf_patch import make_patch, inside_mask, build_patch
from tools.manual_leaf_preview import project
from tools.leaf_light.common import StudyError
from tools.leaf_light import common


@pytest.fixture
def case():
    capture = dict(intrinsics=dict(image_width_px=128, image_height_px=128,
        camera_matrix=[[100,0,64],[0,100,64],[0,0,1]], dist_coeffs=[0,0,0,0,0]),
        frames=[dict(image_file=f'p{i}.png', rvec_rad=[0.,0.,0.], tvec_mm=[float(i*10),0.,100.],
                     pose_status='solved', passes_pose_gate=False, sha256=f'h{i}') for i in range(2)])
    xyz=np.array([[-30,-30,0],[30,-30,0],[30,30,0],[-30,30,0]],dtype=float)
    # Deep concavity has no matching polygon-vertex IDs; only the four corners have depth.
    outline=np.array([[-30,-30,0],[30,-30,0],[30,30,0],[5,30,0],[5,0,0],[-5,0,0],[-5,30,0],[-30,30,0]],dtype=float)
    region=dict(organ_id='O',leaflet_id='L',observations=[])
    rows=[]
    for f in capture['frames']:
        region['observations'].append(dict(image_file=f['image_file'], label_image_size_px=[128,128],
            boundary_xy_px=project(outline,f,capture['intrinsics']).tolist()))
        for i,point in enumerate(xyz):
            rows.append(dict(organ_id='O',leaflet_id='L',point_id=f'b{i}',image_file=f['image_file'],
                coordinate_frame='board',image_sha256=f['sha256'],
                **dict(zip(('x_board_mm','y_board_mm','z_board_mm'),point))))
    return capture,rows,region


def test_observed_notch_is_not_filled_and_vertices_are_interpolated(case):
    capture,rows,region=case
    model=make_patch(capture,rows,region,4,1)
    assert 0 < model['retained_faces'] < model['proposed_faces']
    xyz=np.array(model['vertices_mm']); assert np.all(xyz[:,2]==0)
    centers=np.array([xyz[f].mean(axis=0) for f in model['faces']])
    assert not np.any((np.abs(centers[:,0])<5)&(centers[:,1]>0))
    assert model['interpolated_patch_area_mm2'] < 3600-300
    assert len(model['physical_landmarks'])==4 and len(xyz)>4
    assert not model['interpolation_vertices_are_observations']
    assert not model['validated_metric'] and not model['suitable_for_ppfd']


def test_one_region_and_two_landmarks_cannot_make_surface(case):
    capture,rows,region=case
    partial=deepcopy(region);partial['observations']=partial['observations'][:1]
    with pytest.raises(StudyError,match='two independently'):
        make_patch(capture,rows,partial,3,0)
    with pytest.raises(StudyError,match='three finite'):
        make_patch(capture,[r for r in rows if r['point_id'] in ('b0','b1')],region,3,0)


def test_conflicting_coordinates_or_photo_hash_are_rejected(case):
    capture,rows,region=case
    changed=deepcopy(rows);changed[-1]['z_board_mm']=1
    with pytest.raises(StudyError,match='Conflicting'):
        make_patch(capture,changed,region,2,0)
    changed=deepcopy(rows);changed[0]['image_sha256']='other'
    with pytest.raises(StudyError,match='source image'):
        make_patch(capture,changed,region,2,0)


def test_behind_camera_and_image_boundary_are_excluded(case):
    capture,_,_=case;frame=capture['frames'][0];mask=np.ones((128,128),np.uint8)
    assert not inside_mask(np.array([[0,0,-101],[1,0,-101],[0,1,-101.]]),frame,capture['intrinsics'],mask)
    assert not inside_mask(np.array([[63.9,0,0],[63.8,0,0],[63.9,1,0]]),frame,capture['intrinsics'],mask)


def test_artifact_links_source_photos_and_rejects_changed_image_before_output(case,tmp_path,monkeypatch):
    capture,rows,region=case
    monkeypatch.setattr(common,'BUILD',tmp_path/'build')
    for frame in capture['frames']:
        path=tmp_path/frame['image_file'];Image.new('RGB',(128,128),(20,40,25)).save(path)
        frame.update(image_path=str(path),sha256=common.file_hash(path))
        for row in rows:
            if row['image_file']!=frame['image_file']: continue
            row['image_sha256']=frame['sha256']
            xy=project(np.array([[row[k] for k in ('x_board_mm','y_board_mm','z_board_mm')]]),frame,capture['intrinsics'])[0]
            row.update(x_px=xy[0],y_px=xy[1])
    paths=[tmp_path/'capture.json',tmp_path/'depth.csv',tmp_path/'annotation.json']
    common.write_json(paths[0],capture);common.write_rows(paths[1],rows,tuple(rows[0]))
    common.write_json(paths[2],dict(two_d_only_candidates=[region]))
    out=tmp_path/'build/result'
    result=build_patch(*paths,'L',out,levels=3,margin_px=1)
    assert len(result['photo_reviews'])==2
    assert (out/'visible_patch_mm.ply').is_file()
    assert '__PHOTOS__' not in (out/'index.html').read_text(encoding='utf-8')
    for review in result['photo_reviews']:
        assert (out/review['overlay_file']).is_file()
    (tmp_path/'p0.png').write_bytes(b'changed')
    with pytest.raises(StudyError,match='photograph hash'):
        build_patch(*paths,'L',tmp_path/'build/rejected',levels=3,margin_px=1)
    assert not (tmp_path/'build/rejected').exists()
