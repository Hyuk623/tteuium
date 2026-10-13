"""Area/topology regressions, using geometry independent of the estimator."""
from copy import deepcopy

import numpy as np
import pytest

from tools import compound_surface as cs
from tools.leaf_light.common import StudyError

POLICY=dict(coordinate_tolerance_mm=1e-7,minimum_face_area_mm2=0,minimum_supported_views=2,maximum_pair_checks=10000)


def row(tri, tid='t0', leaflet='leaf'):
    return dict(plant_id='p',session_id='s',geometry_variant_id='v',organ_id='L1',leaflet_id=leaflet,triangle_id=tid,
                geometry_source='reconstructed',organ_class='leaf',normal_convention='unknown',
                **{f'v{i}_{a}_mm':float(tri[i][j]) for i in range(3) for j,a in enumerate('xyz')})


def audit(tris,patches=None,views=None,policy=None):
    rr=[row(t,'t'+str(i)) for i,t in enumerate(tris)]
    ev=[{**{k:r[k] for k in cs.KEY},'tissue_patch_id':patches[i] if patches else 'patch',
         'identity_status':'confirmed','support_kind':'landmark_interpolated','topology_review':'accepted','review_source':'fixture'} for i,r in enumerate(rr)]
    if views is None:
        intr=dict(camera_matrix=[[10,0,40],[0,10,40],[0,0,1]],dist_coeffs=[0,0,0,0,0],image_width_px=100,image_height_px=100)
        views={p:[(dict(image_file=f'v{i}',rvec_rad=[0,0,0],tvec_mm=[i,0,10]),intr,np.ones((100,100),bool)) for i in range(2)] for p in (patches or ['patch'])}
    return cs.audit_surface(rr,ev,policy or POLICY,views)


def test_planar_area_units_duplicates_and_reversed_faces():
    a=np.array([[0,0,0],[10,0,0],[10,10,0]],float)
    b=np.array([[0,0,0],[10,10,0],[0,10,0]],float)
    result=audit([a,b,a[::-1]])
    assert result['compounds'][0]['supported_area_cm2']==pytest.approx(1)
    assert 'duplicate_physical_face' in result['faces'][2]['reasons']
    assert not result['suitable_for_ppfd'] and result['compounds'][0]['total_area_cm2'] is None


def test_ambiguous_duplicate_tissue_not_merged():
    a=np.array([[0,0,0],[10,0,0],[0,10,0]],float)
    r=audit([a,a],['one','two'])
    assert r['compounds'][0]['supported_area_cm2'] is None
    assert all('ambiguous_coincident_tissue' in f['reasons'] for f in r['faces'])


def test_adjacent_fold_not_intersection():
    a=np.array([[0,0,0],[10,0,0],[0,10,0]],float)
    b=np.array([[0,0,0],[10,0,0],[0,0,10]],float)
    assert not cs.intersecting_faces(a,b,1e-7)
    r=audit([a,b]);assert r['compounds'][0]['supported_area_cm2']==pytest.approx(1)


def test_crossing_faces_flagged():
    a=np.array([[0,0,0],[10,0,0],[0,10,0]],float)
    b=np.array([[2,2,-5],[2,2,5],[8,2,0]],float)
    r=audit([a,b])
    assert r['intersecting_pairs']==[[0,1]]
    assert r['compounds'][0]['supported_area_cm2'] is None


def test_coplanar_overlap_flagged():
    a=np.array([[0,0,0],[10,0,0],[0,10,0]],float)
    assert cs.intersecting_faces(a,a+[1,1,0],1e-7)


def test_full_face_mask_hole_not_only_vertices():
    tri=np.array([[0,0,0],[10,0,0],[0,10,0]],float)
    intr=dict(camera_matrix=[[10,0,40],[0,10,40],[0,0,1]],dist_coeffs=[0,0,0,0,0],image_width_px=100,image_height_px=100)
    mask=np.ones((100,100),bool);mask[42:44,42:44]=False
    views={'patch':[(dict(image_file=str(i),rvec_rad=[0,0,0],tvec_mm=[0,0,10]),intr,mask) for i in range(2)]}
    r=audit([tri],views=views)
    assert 'face_outside_visible_tissue' in r['faces'][0]['reasons']


def test_missing_support_and_null_policy_do_not_pass():
    tri=np.array([[0,0,0],[10,0,0],[0,10,0]],float)
    assert not audit([tri],views={})['faces'][0]['eligible_supported_area']
    with pytest.raises(StudyError):audit([tri],policy={**POLICY,'coordinate_tolerance_mm':None})


def test_local_charts_preserve_hole_and_disconnected_gap():
    pts=np.array([[0,0,0],[10,0,0],[10,10,0],[0,10,0],[4,4,0],[6,4,0],[6,6,0],[4,6,0]],float)
    tris=cs.local_patch_faces(pts,[0,1,2,3],[[4,5,6,7]])
    assert cs.triangle_areas_mm2(tris).sum()==pytest.approx(96)
    other=tris+[20,0,0]
    assert cs.triangle_areas_mm2(np.concatenate((tris,other))).sum()==pytest.approx(192)


def test_curved_surface_convergence_and_rigid_invariance():
    # Half cylinder of radius 10 and length 20 has analytic area pi*10*20.
    def cylinder(n):
        t=np.linspace(0,np.pi,n+1);lower=np.c_[10*np.cos(t),10*np.sin(t),np.zeros(n+1)]
        upper=lower+[0,0,20]
        return np.array([tri for i in range(n) for tri in [[lower[i],upper[i],upper[i+1]],[lower[i],upper[i+1],lower[i+1]]]])
    coarse,fine=cylinder(8),cylinder(64)
    truth=np.pi*10*20
    assert abs(cs.triangle_areas_mm2(fine).sum()-truth)<abs(cs.triangle_areas_mm2(coarse).sum()-truth)
    from scipy.spatial.transform import Rotation
    moved=Rotation.from_euler('xyz',[20,40,70],degrees=True).apply(fine.reshape(-1,3)).reshape(fine.shape)+[10,20,30]
    np.testing.assert_allclose(cs.triangle_areas_mm2(moved),cs.triangle_areas_mm2(fine))


def test_pair_budget_cannot_silently_approve():
    a=np.array([[0,0,0],[1,0,0],[0,1,0]],float)
    r=audit([a,a+[2,0,0],a+[4,0,0]],policy={**POLICY,'maximum_pair_checks':1})
    assert not r['audit_complete'] and r['compounds'][0]['supported_area_cm2'] is None


def test_degenerate_face_excluded():
    r=audit([np.array([[0,0,0],[1,0,0],[2,0,0]],float)])
    assert 'degenerate_or_below_area_policy' in r['faces'][0]['reasons']
