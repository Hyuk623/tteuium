"""Preview retains errors while still rejecting impossible/duplicate rays."""
import numpy as np
import pytest
from tools.manual_leaf_preview import diagnostic_point
from tools.manual_leaf_preview import supported_faces
from tools.leaf_light.synthetic import camera_frame
from tools.leaf_light.reconstruction import project


def inputs():
    intr=dict(camera_matrix=[[1200,0,800],[0,1200,600],[0,0,1]],dist_coeffs=[0]*5,image_width_px=1600,image_height_px=1200)
    target=np.array([0.,0.,100.])
    frames=[camera_frame(str(i),np.array(c,dtype=float),target,'side') for i,c in enumerate([[400,0,300],[0,400,300]])]
    for f in frames: f['passes_pose_gate']=False
    obs=[(f,project(target[None],f,intr)[0]) for f in frames]
    return target,obs,intr,dict(min_ray_angle_deg=2.,max_point_error_px=2.)


def test_exact_correspondences_keep_failed_camera_quality():
    target,obs,intr,quality=inputs();xyz,diag=diagnostic_point(obs,intr,quality)
    np.testing.assert_allclose(xyz,target,atol=1e-7)
    assert diag['passes_point_gate']
    assert not diag['passes_all_pose_gates'] and not diag['validated_metric']


def test_bad_fit_remains_visible_and_does_not_change_thresholds():
    _,obs,intr,quality=inputs();obs[1][1][1]+=40
    _,diag=diagnostic_point(obs,intr,quality)
    assert diag['max_error_px']>2 and not diag['passes_point_gate']
    assert quality['max_point_error_px']==2.


def test_unknown_pose_duplicate_view_and_invalid_pixel_rejected():
    _,obs,intr,quality=inputs()
    with pytest.raises(ValueError,match='duplicate'): diagnostic_point([obs[0],obs[0]],intr,quality)
    obs[0][0]['pose_status']='failed'
    with pytest.raises(ValueError,match='no_measured_pose'): diagnostic_point(obs,intr,quality)
    obs[0][0]['pose_status']='solved';obs[0][1][0]=-1
    with pytest.raises(ValueError,match='outside'): diagnostic_point(obs,intr,quality)


def test_repeated_or_collinear_landmarks_do_not_make_a_surface():
    for points in (np.ones((3,3)), np.array([[0.,0.,0.],[1.,0.,0.],[2.,0.,0.]])):
        with pytest.raises(ValueError, match='degenerate_leaf_patch'):
            supported_faces(points, [], {}, 3.)
