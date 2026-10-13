"""Independent area references and fail-closed estimator/version behavior."""
from copy import deepcopy

import numpy as np
import pytest

from tools.leaf_area_geometry import (IntegrationPolicy, METHOD, normalized_pixel_areas,
                                      photo_area_v2, view_geometry, calibration_identity)
from tools.leaf_light.common import StudyError
from tools.plant_structure import Cameras
from tools import plant_traits as pt

POLICY = dict(chunk_pixels=1024, inverse_iterations=60, inverse_tolerance_px=1e-7,
              relative_area_tolerance=1e-7, absolute_area_tolerance_normalized=1e-14,
              max_edge_subdivisions=16)
K = np.array([[100., 0, 100.], [0, 80., 100.], [0, 0, 1.]])
D = np.zeros(5)


def camera() -> Cameras:
    return Cameras(dict(intrinsics=dict(camera_matrix=K.tolist(), dist_coeffs=D.tolist(), image_width_px=200, image_height_px=200),
                        frames=[dict(image_file='one', pose_status='solved', rvec_rad=[0., 0., 0.], tvec_mm=[0., 0., 0.])]))


def hull() -> np.ndarray:
    return np.array([[x, y, 200.] for x in np.linspace(-20, 20, 21) for y in np.linspace(-20, 20, 21)])


def test_exact_anisotropic_focal_length_and_explicit_resampling():
    p = IntegrationPolicy.parse(POLICY)
    a, diag = normalized_pixel_areas(np.array([[100., 100.], [150., 70.]]), K, D, (200, 200), p)
    assert np.all(a == 1 / 8000)
    scaled, _ = normalized_pixel_areas(np.array([[100.5, 100.5]]), K, D, (200, 200), p, (2., 2.))
    assert scaled[0] == pytest.approx(4 / 8000)
    assert not diag['unconverged_pixels']


def test_distorted_disk_has_independently_known_area():
    # Radial mapping preserves a centered circle: rd=r*(1+k*r^2).
    # Boundary rasterization error is bounded by its one-pixel perimeter band.
    k = K.copy(); k[0, 0] = k[1, 1] = 200.; k[:2, 2] = 150.
    distortion = np.array([.35, 0., 0., 0., 0.])
    radius = .4
    rd_px = 200 * radius * (1 + .35 * radius**2)
    y, x = np.mgrid[0:300, 0:300]
    mask = (x-150)**2 + (y-150)**2 <= rd_px**2
    xy = np.c_[x[mask], y[mask]]
    area, diag = normalized_pixel_areas(xy, k, distortion, (300, 300), IntegrationPolicy.parse(POLICY))
    assert np.isfinite(area).all()
    assert abs(area.sum() - np.pi * radius**2) / (np.pi * radius**2) < .01
    assert not diag['inverse_failed_pixels']


def test_off_axis_tangential_distortion_converges_and_is_chunk_invariant():
    xy = np.array([[150., 160.], [40., 30.], [95., 88.]])
    d = np.array([.1, -.01, .015, -.02, .001])
    a, _ = normalized_pixel_areas(xy, K, d, (200, 200), IntegrationPolicy.parse(POLICY))
    b, _ = normalized_pixel_areas(xy, K, d, (200, 200), IntegrationPolicy.parse({**POLICY, 'chunk_pixels': 1}))
    np.testing.assert_allclose(a, b, rtol=1e-12)
    assert np.isfinite(a).all() and not np.allclose(a, 1/8000, rtol=.001)


def test_off_axis_distorted_area_against_independent_jacobian_quadrature():
    # Independent implementation: solve Brown-Conrady coordinates with SciPy,
    # then integrate the inverse analytic Jacobian, not pixel boundary polygons.
    from scipy.optimize import root
    k1,k2,p1,p2,k3 = .1,-.01,.015,-.02,.001
    def forward_jacobian(uv):
        x,y=uv; r2=x*x+y*y
        radial=1+k1*r2+k2*r2*r2+k3*r2**3
        dr=2*(k1+2*k2*r2+3*k3*r2*r2)
        mapped=np.array([x*radial+2*p1*x*y+p2*(r2+2*x*x),
                         y*radial+p1*(r2+2*y*y)+2*p2*x*y])
        jac=np.array([[radial+x*x*dr+2*p1*y+6*p2*x,x*y*dr+2*p1*x+2*p2*y],
                      [x*y*dr+2*p1*x+2*p2*y,radial+y*y*dr+6*p1*y+2*p2*x]])
        return mapped,jac
    xy=np.array([[150.,160.],[40.,30.]])
    d=np.array([k1,k2,p1,p2,k3])
    actual,_=normalized_pixel_areas(xy,K,d,(200,200),IntegrationPolicy.parse(POLICY))
    nodes,weights=np.polynomial.legendre.leggauss(5)
    references=[]
    for centre in xy:
        integral=0.
        for i,u in enumerate(nodes):
            for j,v in enumerate(nodes):
                target=(centre+.5*np.array([u,v])-K[:2,2])/np.diag(K)[:2]
                solution=root(lambda q:forward_jacobian(q)[0]-target,target,
                              jac=lambda q:forward_jacobian(q)[1],tol=1e-11)
                assert np.linalg.norm(forward_jacobian(solution.x)[0]-target)<1e-12
                integral+=weights[i]*weights[j]/(4*K[0,0]*K[1,1]*np.linalg.det(forward_jacobian(solution.x)[1]))
        references.append(integral)
    # Integrator's requested relative tolerance is 1e-7; permit two tolerances.
    np.testing.assert_allclose(actual,references,rtol=2e-7,atol=1e-14)


def test_current_code_and_v2_comparison_different_methods():
    masks = [((90, 92, 110, 108), np.ones((16, 20), bool), True)]
    result = pt.photo_area(camera(), 'one', hull(), masks, area_policy=POLICY)
    assert result['leaf_area_cm2'] == 12.8
    assert result['area_v2']['projected_area_cm2'] == pytest.approx(16.)
    assert result['area_v2']['area_method'] == METHOD
    assert result['area_v2']['accepted_projected_area_cm2'] == pytest.approx(16.)
    assert not result['area_v2']['validated_metric']


def test_duplicate_masks_holes_and_accepted_coverage():
    m = np.ones((16, 20), bool); m[6:10, 8:12] = False
    masks = [((90, 92, 110, 108), m, True), ((90, 92, 110, 108), m, False)]
    r = photo_area_v2(camera(), 'one', hull(), masks, IntegrationPolicy.parse(POLICY), 20, 5)
    assert r['used_union_px'] == 304
    assert r['projected_area_cm2'] == pytest.approx(15.2)
    assert r['accepted_projected_area_cm2'] == pytest.approx(15.2)


def test_missing_depth_empty_mask_and_no_masks_are_distinct():
    m = np.ones((16, 20), bool)
    run = lambda masks: photo_area_v2(camera(), 'one', np.empty((0, 3)), masks, IntegrationPolicy.parse(POLICY), 20, 5)
    missing = run([((90, 92, 110, 108), m, True)])
    assert missing['status'] == 'unavailable' and missing['projected_area_cm2'] is None
    empty = run([((90, 92, 110, 108), ~m, True)])
    assert empty['status'] == 'empty' and empty['projected_area_cm2'] == 0
    assert run([])['status'] == 'no_masks' and run([])['projected_area_cm2'] is None


def test_partial_depth_does_not_silently_become_complete_area():
    masks = [((90, 92, 110, 108), np.ones((16, 20), bool), True),
             ((0, 0, 10, 10), np.ones((10, 10), bool), False)]
    r = photo_area_v2(camera(), 'one', hull(), masks, IntegrationPolicy.parse(POLICY), 20, 5)
    assert r['status'] == 'partial' and r['projected_area_cm2'] is None
    assert r['supported_projected_area_cm2'] == pytest.approx(16.)
    assert r['missing_union_px'] == 100


def test_inverse_failure_is_unavailable():
    # One iteration cannot invert this substantial distortion to tiny tolerance.
    d = np.array([2., 1., .1, .1, .1])
    a, report = normalized_pixel_areas(np.array([[180., 180.]]), K, d, (200, 200),
                       IntegrationPolicy.parse({**POLICY, 'inverse_iterations': 1}))
    assert np.isnan(a[0]) and report['inverse_failed_pixels'] == 1


@pytest.mark.parametrize('field,value', [('chunk_pixels', 0), ('inverse_tolerance_px', None),
                                      ('max_edge_subdivisions', 3), ('relative_area_tolerance', float('nan'))])
def test_invalid_policy_is_not_replaced_by_defaults(field, value):
    with pytest.raises(StudyError):
        IntegrationPolicy.parse({**POLICY, field: value})


def test_bad_crop_calibration_and_original_resolution_rejected():
    p = IntegrationPolicy.parse(POLICY)
    with pytest.raises(StudyError, match='Mask/crop'):
        photo_area_v2(camera(), 'one', hull(), [((90, 92, 110, 108), np.ones((8, 10), bool), True)], p, 20, 5)
    bad = K.copy(); bad[0, 0] = 0
    with pytest.raises(StudyError): normalized_pixel_areas(np.array([[100, 100]]), bad, D, (200, 200), p)
    with pytest.raises(StudyError): normalized_pixel_areas(np.array([[200, 100]]), K, D, (200, 200), p)
    assert calibration_identity(K, D, (200, 200)) != calibration_identity(K, D, (201, 200))


def test_measured_view_group_is_not_photo_order_and_null_threshold_inactive():
    cams = camera(); cams.frames['one']['tvec_mm'] = [0., 0., -500.]
    group = dict(centre_board_mm=[0., 0., 0.], top_elevation_gt_deg=70., source='fixture')
    r = view_geometry(cams, 'one', group)
    assert r['group'] == 'top' and r['elevation_deg'] == 90.
    assert view_geometry(cams, 'one', {**group, 'top_elevation_gt_deg': None})['group'] == 'unavailable'
    assert view_geometry(cams, 'one', None)['elevation_deg'] is None
    cams.frames['one']['pose_status'] = 'failed'
    assert view_geometry(cams, 'one', group)['grouping_source'] == 'pose_unavailable'


def trait(**extra) -> dict:
    return dict(plant_id='p', leaf_area_proxy_cm2=10., area_method=METHOD, calibration_hash='camera',
                capture_style='style', grouping_policy_hash='group', integration_policy_hash='policy', **extra)


@pytest.mark.parametrize('field', ['area_method', 'calibration_hash', 'capture_style', 'grouping_policy_hash', 'integration_policy_hash'])
def test_calibration_cannot_mix_versions_or_capture_contracts(field):
    a, b = trait(), trait()
    b['plant_id'] = 'q'; b[field] = 'different'
    with pytest.raises(StudyError): pt.calibrate([a, b], {'p': 20., 'q': 20.})


def test_calibration_records_compatible_contract_without_mutation():
    t = trait(); old = deepcopy(t)
    result = pt.calibrate([t], {'p': 20.})
    assert result['k'] == 2. and result['area_contract']['area_method'] == METHOD
    assert t == old
