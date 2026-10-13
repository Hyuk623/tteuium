"""Fixed-camera comparison must not flatten observed curvature into accuracy."""
from copy import deepcopy

import numpy as np
import pytest

from tools import leaf_surface_compare as sc
from tools.leaf_light.common import StudyError
from tools.leaf_light.reconstruction import project


def fixture(curved=False):
    capture=dict(plant_id='p',session_id='s',intrinsics=dict(camera_matrix=[[600.,0,300.],[0,600.,300.],[0,0,1]],
        dist_coeffs=[0.]*5,image_width_px=600,image_height_px=600),
        frames=[dict(image_file=str(i),pose_status='solved',rvec_rad=[0.,0.,0.],tvec_mm=[t,0.,0.]) for i,t in enumerate([-60.,60.,100.])])
    xyz=np.array([[-20.,-10.,500.],[20.,-10.,500.],[20.,10.,500.],[-20.,10.,500.],[0.,0.,508. if curved else 500.]])
    points=[]; contours=[]
    for f in capture['frames']:
        xy=project(xyz,f,capture['intrinsics'])
        for j,uv in enumerate(xy):
            points.append(dict(image_file=f['image_file'],organ_id='L1',leaflet_id='l1',point_id=f'p{j}',
                               x_px=uv[0],y_px=uv[1],boundary_index=j if j<4 else -1,boundary_count=4))
        for j,uv in enumerate(xy[:4]):
            contours.append(dict(image_file=f['image_file'],organ_id='L1',leaflet_id='l1',vertex_index=j,x_px=uv[0],y_px=uv[1]))
    patch=dict(organ_id='L1',leaflet_id='l1',tissue_patch_id='l1',identity_status='confirmed',point_review_status='confirmed',
               review_source='synthetic fixture',topology_review='accepted')
    study=dict(fit_images=['0','1'],heldout_images=['2'],minimum_abs_ray_plane_cosine=.01,
               quality=dict(min_ray_angle_deg=2.,max_point_error_px=2.,contour_tolerance_px=3.),
               surface_policy=dict(coordinate_tolerance_mm=1e-7,minimum_face_area_mm2=0.,minimum_supported_views=2,maximum_pair_checks=1000))
    return capture,points,contours,patch,study


def test_known_plane_area_and_independent_third_view():
    args=fixture(); original=deepcopy(args)
    result=sc.compare_patch(*args)
    assert len(result['methods'])==2
    for method in result['methods']:
        assert method['heldout']['observations']==5 and method['heldout']['rms_px']<1e-8
        assert method['audit']['compounds'][0]['supported_area_cm2']==pytest.approx(8.)
        assert not method['physical_validation']
    assert args==original
    assert result['curved_candidate']['status']=='unavailable'


def test_planar_fit_does_not_claim_to_recover_real_curvature():
    result=sc.compare_patch(*fixture(curved=True))
    baseline,plane=result['methods']
    assert baseline['heldout']['rms_px']<1e-8
    assert plane['heldout']['rms_px']>baseline['heldout']['rms_px']+0.1
    assert plane['detail']['triangulated_point_plane_rms_mm']>0
    assert result['total_tissue_area_cm2'] is None


def test_no_independent_view_is_explicit():
    args=list(fixture()); args[-1]['heldout_images']=[]
    result=sc.compare_patch(*args)
    assert all(m['heldout']['rms_px'] is None for m in result['methods'])


def test_unreviewed_identities_never_become_geometry():
    args=list(fixture()); args[-2]['identity_status']='proposed'
    result=sc.compare_patch(*args)
    assert result['methods']==[] and result['status']=='reviewed_physical_correspondences_missing'


def test_fit_and_evaluation_cannot_share_views():
    args=list(fixture()); args[-1]['heldout_images']=['0']
    with pytest.raises(StudyError,match='disjoint'): sc.compare_patch(*args)


def test_conditioning_and_collinear_plane_rejected():
    with pytest.raises(StudyError,match='Collinear'): sc.fit_plane(np.array([[0,0,0],[1,0,0],[2,0,0]],float))
    with pytest.raises(StudyError,match='parallel'):
        sc.intersect_plane(np.zeros(3),np.array([1.,0,0]),np.array([0.,0,10.]),np.array([0.,0,1.]),.01)
    with pytest.raises(StudyError,match='behind'):
        sc.intersect_plane(np.zeros(3),np.array([0.,0,-1.]),np.array([0.,0,10.]),np.array([0.,0,1.]),.01)


def test_surface_topology_review_required_even_for_perfect_fit():
    args=list(fixture()); args[-2]['topology_review']='pending'
    result=sc.compare_patch(*args)
    assert all(m['audit']['compounds'][0]['supported_area_cm2'] is None for m in result['methods'])


def test_failed_poses_cannot_be_used_as_fit_or_independent_evidence():
    args = list(fixture())
    args[0]['frames'][2]['pose_status'] = 'failed'
    result = sc.compare_patch(*args)
    assert all(m['heldout']['rms_px'] is None and m['heldout']['failed_pose_observations']==5 for m in result['methods'])
    args[0]['frames'][0]['pose_status'] = 'failed'
    assert sc.compare_patch(*args)['status'] == 'fit_pose_unavailable'


def test_observed_tilted_plane_recovers_physical_not_projected_area():
    capture, points, contours, patch, study = fixture()
    # A rigid rotation preserves the independently known 40 x 20 mm rectangle.
    theta = np.deg2rad(60.)
    xyz = np.array([[-20.,-10.,0.],[20.,-10.,0.],[20.,10.,0.],[-20.,10.,0.],[0.,0.,0.]])
    rotation = np.array([[np.cos(theta),0,np.sin(theta)],[0,1,0],[-np.sin(theta),0,np.cos(theta)]])
    xyz = xyz @ rotation.T + [0,0,500.]
    for frame in capture['frames']:
        xy = project(xyz,frame,capture['intrinsics'])
        for j, row in enumerate(r for r in points if r['image_file']==frame['image_file']):
            row.update(x_px=xy[j,0],y_px=xy[j,1])
        for j, row in enumerate(r for r in contours if r['image_file']==frame['image_file']):
            row.update(x_px=xy[j,0],y_px=xy[j,1])
    result = sc.compare_patch(capture,points,contours,patch,study)
    plane = result['methods'][1]
    assert plane['audit']['compounds'][0]['supported_area_cm2'] == pytest.approx(8.,abs=1e-8)
    assert abs(plane['detail']['unsigned_normal'][2]) == pytest.approx(.5)
    assert plane['heldout']['rms_px'] < 1e-8


def test_run_audits_coincident_tissue_across_different_patches(tmp_path, monkeypatch):
    from PIL import Image
    from tools.leaf_light import common
    from tools.leaf_light.annotations import POINT_COLUMNS, CONTOUR_COLUMNS
    monkeypatch.setattr(common, 'BUILD', tmp_path)
    capture, points, contours, patch, study = fixture()
    capture['coordinate_frame'] = 'board'
    for frame in capture['frames']:
        path = tmp_path / (frame['image_file'] + '.png')
        Image.new('RGB',(600,600)).save(path)
        frame.update(image_path=str(path),sha256=common.file_hash(path))
    # Two claimed identities at the exact same location require review, even
    # though each individual patch has perfect reprojection and accepted flags.
    points += [dict(r,leaflet_id='l2') for r in list(points)]
    contours += [dict(r,leaflet_id='l2') for r in list(contours)]
    study.update(schema='leaf-surface-comparison-1',evidence_kind='synthetic',
                 capture='capture.json',points='points.csv',contours='contours.csv',
                 patches=[patch,dict(patch,leaflet_id='l2',tissue_patch_id='l2')])
    common.write_json(tmp_path/'capture.json',capture)
    common.write_json(tmp_path/'study.json',study)
    common.write_rows(tmp_path/'points.csv',points,POINT_COLUMNS)
    common.write_rows(tmp_path/'contours.csv',contours,CONTOUR_COLUMNS)
    report = sc.run(tmp_path/'study.json',tmp_path/'out')
    for audit in report['global_surface_audits'].values():
        assert all(r['supported_area_cm2'] is None for r in audit['compounds'])
        assert all('ambiguous_coincident_tissue' in f['reasons'] for f in audit['faces'])
    assert not report['suitable_for_ppfd']
