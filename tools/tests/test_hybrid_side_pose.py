"""Diagnostic side poses inferred from reconstructed leaflet landmarks.

The baseline stays ChArUco-only. These tests check that the solver recovers a known
camera, refuses the cases where it must not answer, keeps held-out points out of the
fit, and that the rebuild attaches the result as a separate hybrid branch which never
overwrites a measured pose or the baseline table.
"""
from copy import deepcopy

import cv2
import numpy as np
import pytest

from tools import editor_point_review as review_tool
from tools import rebuild_leaf_edit_session as tool
from tools import side_pose_candidate as side
from tools.leaf_light import common
from tools.leaf_light.reconstruction import project
from tools.leaf_light.synthetic import camera_frame
from tools.tests.test_manual_leaf_preview_fragments import fragment_case  # noqa: F401  (fixture)
from tools.tests.test_rebuild_leaf_edit_session import prepared  # noqa: F401  (fixture)

INTRINSICS = dict(camera_matrix=[[1200., 0., 800.], [0., 1200., 600.], [0., 0., 1.]],
                  dist_coeffs=[-0.21, 0.09, 0.001, -0.002, 0.01],
                  image_width_px=1600, image_height_px=1200)
SIDE_CENTRE = np.array([-190., -25., 120.])


def landmarks(count: int = 12, planar: bool = False, collinear: bool = False) -> np.ndarray:
    """Landmark-like points: a spread of vein/tip positions on and around one leaflet."""
    generator = np.random.default_rng(7)
    if collinear:
        return np.stack([np.linspace(-60., 60., count), np.zeros(count), np.full(count, 100.)], axis=1)
    points = np.column_stack([generator.uniform(-70., 70., count), generator.uniform(-50., 50., count),
                              np.full(count, 100.) if planar else generator.uniform(85., 130., count)])
    return points


def reference_document(points_mm: np.ndarray) -> dict:
    return dict(schema_version=side.REFERENCE_SCHEMA, reference_id='reference_test', plant_id='P', session_id='S',
                intrinsics=INTRINSICS, intrinsics_sha256='intr', depth_csv_sha256='depth', capture_sha256='capture',
                coordinate_frame='board; millimetres',
                reference_points=[dict(viewer_leaflet_id='L3D', point_id=f'b{i}', organ_id='O3D', leaflet_id='L3D',
                                       xyz_board_mm=list(map(float, xyz)))
                                  for i, xyz in enumerate(points_mm)])


def pose_of(centre: np.ndarray, target=(0., 0., 100.)) -> tuple[np.ndarray, np.ndarray]:
    frame = camera_frame('side.png', np.asarray(centre, float), np.asarray(target, float), 'side')
    return np.asarray(frame['rvec_rad'], float).reshape(3, 1), np.asarray(frame['tvec_mm'], float).reshape(3, 1)


def pixels_of(points_mm: np.ndarray, rvec, tvec) -> np.ndarray:
    return cv2.projectPoints(points_mm, rvec, tvec, np.asarray(INTRINSICS['camera_matrix'], float),
                             np.asarray(INTRINSICS['dist_coeffs'], float))[0].reshape(-1, 2)


def observations_of(points_mm: np.ndarray, rvec, tvec) -> list[dict]:
    return [dict(viewer_leaflet_id='L3D', point_id=f'b{i}', x_px=float(px[0]), y_px=float(px[1]))
            for i, px in enumerate(pixels_of(points_mm, rvec, tvec))]


def centre_of(candidate: dict) -> np.ndarray:
    rotation = cv2.Rodrigues(np.asarray(candidate['rvec_rad'], float))[0]
    return -rotation.T @ np.asarray(candidate['tvec_mm'], float)


def test_known_camera_is_recovered_through_distortion_and_stays_diagnostic():
    points = landmarks()
    rvec, tvec = pose_of(SIDE_CENTRE)
    candidate = side.solve_side_pose(reference_document(points), 'photo_side.png', observations_of(points, rvec, tvec))
    assert candidate['calculation_status'] == 'solved' and candidate['quality_status'] == 'meets_diagnostic_policy'
    assert candidate['validation'] == 'available' and candidate['diagnostic_inclusion'] == 'eligible'
    np.testing.assert_allclose(centre_of(candidate), SIDE_CENTRE, atol=1e-4)
    assert candidate['fit_rms_px'] < 1e-4 and candidate['holdout_rms_px'] < 1e-4
    # The recovery above is exact because the coefficients are applied to the raw pixels: at the true pose the
    # residual is zero with them and pixels wide without them.
    pixels = pixels_of(points, rvec, tvec)
    assert side._residuals(points, pixels, rvec, tvec, INTRINSICS).max() < 1e-9
    assert side._residuals(points, pixels, rvec, tvec, dict(INTRINSICS, dist_coeffs=[0.] * 5)).max() > 1.0
    # Undistorting the observations before handing them over undistorts twice and moves the camera again.
    undistorted = cv2.undistortPoints(pixels_of(points, rvec, tvec).reshape(-1, 1, 2),
                                      np.asarray(INTRINSICS['camera_matrix'], float),
                                      np.asarray(INTRINSICS['dist_coeffs'], float),
                                      P=np.asarray(INTRINSICS['camera_matrix'], float)).reshape(-1, 2)
    twice = side.solve_side_pose(reference_document(points), 'photo_side.png',
                                 [dict(viewer_leaflet_id='L3D', point_id=f'b{i}', x_px=float(p[0]), y_px=float(p[1]))
                                  for i, p in enumerate(undistorted)])
    assert np.linalg.norm(centre_of(twice) - SIDE_CENTRE) > 0.5
    # A solved pose is never presented as a measurement.
    assert candidate['pose_source'] == 'leaflet_landmark_pnp' and candidate['pose_source_is_measured_board'] is False
    assert candidate['validated_metric'] is False and candidate['suitable_for_ppfd'] is False


def test_wrong_matches_become_outliers_and_do_not_move_the_camera():
    points = landmarks(14)
    rvec, tvec = pose_of(SIDE_CENTRE)
    observations = observations_of(points, rvec, tvec)
    clean = side.solve_side_pose(reference_document(points), 'photo_side.png', deepcopy(observations))
    swapped = deepcopy(observations)
    fit_ids = [key[1] for key in map(tuple, clean['fit_point_ids'])]
    a, b = (next(o for o in swapped if o['point_id'] == pid) for pid in fit_ids[:2])
    a['x_px'], a['y_px'], b['x_px'], b['y_px'] = b['x_px'], b['y_px'], a['x_px'], a['y_px']
    candidate = side.solve_side_pose(reference_document(points), 'photo_side.png', swapped)
    assert candidate['calculation_status'] == 'solved'
    assert sorted(k[1] for k in candidate['outlier_point_ids']) == sorted(fit_ids[:2])
    np.testing.assert_allclose(centre_of(candidate), SIDE_CENTRE, atol=1e-3)


def test_refusals_are_explicit_for_each_unusable_case():
    points = landmarks()
    rvec, tvec = pose_of(SIDE_CENTRE)
    observations = observations_of(points, rvec, tvec)
    thin = side.solve_side_pose(reference_document(points[:4]), 'photo_side.png', observations[:4])
    assert thin['calculation_status'] == 'insufficient_points' and thin['rvec_rad'] is None
    assert '4 usable correspondences' in thin['inclusion_reason']
    line = landmarks(10, collinear=True)
    collinear = side.solve_side_pose(reference_document(line), 'photo_side.png',
                                     observations_of(line, *pose_of(np.array([-420., -200., 150.]))))
    assert collinear['calculation_status'] == 'degenerate_point_distribution'
    assert collinear['geometry']['degeneracy_reasons'] == ['near_collinear_points']
    still = np.repeat(np.array([[0., 0., 100.]]), 8, axis=0) + np.linspace(0, 1, 8)[:, None] * 0.1
    tiny = side.solve_side_pose(reference_document(still), 'photo_side.png',
                                observations_of(still, *pose_of(np.array([-420., -200., 150.]))))
    assert 'insufficient_spatial_extent' in tiny['geometry']['degeneracy_reasons']
    unmatched = side.solve_side_pose(reference_document(points), 'photo_side.png',
                                     [dict(viewer_leaflet_id='LX', point_id='zz', x_px=10., y_px=10.)] + observations[:3])
    assert unmatched['calculation_status'] == 'insufficient_points'
    assert unmatched['unmatched'][0]['reason'] == 'no frozen reference point'
    outside = deepcopy(observations)
    outside[0]['x_px'] = 9999.
    assert side.solve_side_pose(reference_document(points), 'photo_side.png', outside)['unmatched'][0]['reason'] \
        == 'pixel outside the calibrated image'
    with pytest.raises(common.StudyError, match='Duplicate observation'):
        side.solve_side_pose(reference_document(points), 'photo_side.png', observations + observations[:1])


def test_near_planar_landmarks_are_reported_as_ambiguous_but_still_solved():
    points = landmarks(12, planar=True)
    candidate = side.solve_side_pose(reference_document(points), 'photo_side.png',
                                     observations_of(points, *pose_of(SIDE_CENTRE)))
    assert candidate['calculation_status'] == 'solved'
    assert candidate['geometry_warnings'] == ['near_planar_points_ambiguous_pnp']
    assert candidate['alternative_solutions'] or candidate['geometry']['planarity_ratio'] < 0.02


def test_inactive_threshold_never_becomes_a_silent_default():
    points = landmarks()
    candidate = side.solve_side_pose(reference_document(points), 'photo_side.png',
                                     observations_of(points, *pose_of(SIDE_CENTRE)),
                                     policy=dict(max_holdout_error_px=None))
    assert candidate['policy_checks']['holdout_error'] is None
    assert candidate['quality_status'] == 'unavailable' and candidate['diagnostic_inclusion'] == 'excluded'
    overridden = side.solve_side_pose(reference_document(points), 'photo_side.png',
                                      observations_of(points, *pose_of(SIDE_CENTRE)),
                                      policy=dict(max_holdout_error_px=None), diagnostic_override=True)
    assert overridden['diagnostic_inclusion'] == 'included_by_explicit_override'
    assert 'override' in overridden['inclusion_reason']


def test_held_out_points_never_influence_the_fit_and_the_partition_is_seeded():
    points = landmarks()
    rvec, tvec = pose_of(SIDE_CENTRE)
    observations = observations_of(points, rvec, tvec)
    candidate = side.solve_side_pose(reference_document(points), 'photo_side.png', deepcopy(observations))
    held = [tuple(k) for k in candidate['holdout_point_ids']]
    assert held and not set(held) & {tuple(k) for k in candidate['fit_point_ids']}
    spoiled = deepcopy(observations)
    for entry in spoiled:
        if ('L3D', entry['point_id']) in held:
            entry['x_px'] += 25.
    moved = side.solve_side_pose(reference_document(points), 'photo_side.png', spoiled)
    assert moved['rvec_rad'] == candidate['rvec_rad'] and moved['tvec_mm'] == candidate['tvec_mm']
    assert moved['holdout_rms_px'] > candidate['holdout_rms_px'] and moved['fit_rms_px'] == candidate['fit_rms_px']
    assert moved['quality_status'] == 'fails_diagnostic_policy' and moved['diagnostic_inclusion'] == 'excluded'
    # The partition itself is reproducible and recorded with its seed.
    identities = [('L3D', f'b{i}') for i in range(12)]
    assert side.partition(identities, side.DEFAULT_POLICY) == side.partition(identities, side.DEFAULT_POLICY)
    assert side.partition(identities, dict(side.DEFAULT_POLICY, holdout_seed=1)) != \
        side.partition(identities, side.DEFAULT_POLICY)
    assert candidate['policy']['holdout_seed'] == side.DEFAULT_POLICY['holdout_seed']


def test_a_camera_that_would_put_landmarks_behind_itself_is_refused(monkeypatch):
    points = landmarks()
    rvec, tvec = pose_of(SIDE_CENTRE)
    observations = observations_of(points, rvec, tvec)
    accepted = side.solve_side_pose(reference_document(points), 'photo_side.png', deepcopy(observations))
    # Every solved candidate keeps its fit points in front of the camera.
    rotation = cv2.Rodrigues(np.asarray(accepted['rvec_rad'], float))[0]
    assert np.all((points @ rotation.T + np.asarray(accepted['tvec_mm'], float))[:, 2] > 0)
    # A refinement that flips the camera through the scene is rejected rather than reported as a pose.
    flip = cv2.Rodrigues(np.array([np.pi, 0., 0.]))[0]

    def flipped(*args, **kwargs):
        return (cv2.Rodrigues(flip @ rotation)[0],
                (flip @ np.asarray(accepted['tvec_mm'], float)).reshape(3, 1))

    monkeypatch.setattr(side.cv2, 'solvePnPRefineLM', flipped)
    candidate = side.solve_side_pose(reference_document(points), 'photo_side.png', observations)
    assert candidate['calculation_status'] == 'points_behind_camera' and candidate['rvec_rad'] is None
    assert candidate['diagnostic_inclusion'] == 'excluded'


# --------------------------------------------------------------------------------------------
# Rebuild integration
# --------------------------------------------------------------------------------------------

def side_candidate(image_file: str, rvec, tvec, depth_sha: str, capture: dict, **overrides) -> dict:
    """A candidate document as tools.side_pose_candidate writes one, for attachment tests."""
    document = dict(schema_version=side.CANDIDATE_SCHEMA, candidate_id='side_testcandidate', version=1,
                    pose_source=side.POSE_SOURCE, image_file=image_file,
                    rvec_rad=list(map(float, np.asarray(rvec).reshape(3))),
                    tvec_mm=list(map(float, np.asarray(tvec).reshape(3))),
                    reference_id='reference_test', reference_depth_csv_sha256=depth_sha,
                    intrinsics_sha256=capture.get('intrinsics_sha256'),
                    calculation_status='solved', quality_status='meets_diagnostic_policy',
                    validation='available', diagnostic_inclusion='eligible',
                    fit_rms_px=0.02, holdout_rms_px=0.05, holdout_point_ids=[['L3D', 'b2']],
                    pose_source_is_measured_board=False, validated_metric=False, suitable_for_ppfd=False)
    document.update(overrides)
    return document


@pytest.fixture
def hybrid_case(prepared):
    """The prepared session plus one landmark that only a side view can complete."""
    session, path, context, out, _, backup, capture = prepared
    frames = {f['image_file']: f for f in capture['frames']}
    unposed = next(f for f in capture['frames'] if f['pose_status'] != 'solved')
    assert unposed['image_file'] == 'photo_2.png'
    new_xyz = np.array([[-8., -6., 104.]])
    rvec, tvec = pose_of(np.array([-380., -120., 220.]))
    side_frame = dict(unposed, rvec_rad=np.asarray(rvec).reshape(3).tolist(),
                      tvec_mm=np.asarray(tvec).reshape(3).tolist(), pose_status='solved')
    leaf = backup['variants']['__all__']['leaflets']['O3D|L3D']
    leaf['pts']['i1'] = {
        'photo_1.png': project(new_xyz, frames['photo_1.png'], capture['intrinsics'])[0].tolist(),
        'photo_2.png': project(new_xyz, side_frame, capture['intrinsics'])[0].tolist()}
    common.write_json(path, backup)
    return session, path, context, out, capture, (rvec, tvec), new_xyz[0]


def test_hybrid_adds_the_side_supported_point_without_touching_the_baseline(hybrid_case, tmp_path):
    session, path, context, out, capture, (rvec, tvec), new_xyz = hybrid_case
    baseline = tool.rebuild(session, path, context, out / 'baseline')
    depth_sha = common.file_hash(out / 'baseline' / 'editor_point_depths.csv')
    b3 = [r for r in common.rows(out / 'baseline' / 'editor_point_depths.csv') if r['point_id'] == 'i1']
    assert b3 and {r['z_board_mm'] for r in b3} == {'unavailable'}
    assert {r['depth_status'] for r in b3} == {'fewer_than_two_solved_views'}
    folder = tmp_path / 'side'
    folder.mkdir()
    common.write_json(folder / 'candidate.json', side_candidate('photo_2.png', rvec, tvec, depth_sha, capture))
    report = tool.rebuild(session, path, context, out / 'hybrid', side_poses=folder)

    assert report['side_pose_status'] == 'attached' and report['side_poses_used_in_hybrid'] == 1
    assert report['side_pose_by_status'] == {'solved': 1} and report['side_pose_stale'] == 0
    assert report['hybrid']['points_added'] == 1 and report['hybrid']['images_used'] == ['photo_2.png']
    hybrid_rows = common.rows(out / 'hybrid' / 'hybrid_point_depths.csv')
    solved_b3 = next(r for r in hybrid_rows if r['point_id'] == 'i1' and r['z_board_mm'] != 'unavailable')
    np.testing.assert_allclose([float(solved_b3[f'{a}_board_mm']) for a in 'xyz'], new_xyz, atol=1e-6)
    assert solved_b3['baseline_z_board_mm'] == 'unavailable' and solved_b3['branch'] == 'hybrid'
    assert solved_b3['validated_metric'] == 'False' and solved_b3['suitable_for_ppfd'] == 'False'
    assert solved_b3['uses_inferred_camera'] == 'True'
    # Points the board already supported keep exactly their baseline coordinates.
    b0 = next(r for r in hybrid_rows if r['point_id'] == 'b0' and r['shift_from_baseline_mm'] != '')
    assert float(b0['shift_from_baseline_mm']) < 1e-9

    # The baseline table and capture are byte-identical to a run without the hybrid option.
    plain = tool.rebuild(session, path, context, out / 'plain')
    for name in ('editor_point_depths.csv', 'capture.json'):
        assert common.file_hash(out / 'hybrid' / name) == common.file_hash(out / 'plain' / name)
    assert not (out / 'plain' / 'hybrid_point_depths.csv').exists()
    assert plain['side_pose_status'] == 'not_attached' and plain['hybrid']['points_added'] == 0
    assert baseline['modeled_leaflets'] == plain['modeled_leaflets']

    # capture.json keeps the failed pose; only the separate hybrid capture carries the inferred one.
    assert next(f for f in common.read_json(out / 'hybrid' / 'capture.json')['frames']
                if f['image_file'] == 'photo_2.png')['pose_status'] != 'solved'
    inferred = next(f for f in common.read_json(out / 'hybrid' / 'hybrid_capture.json')['frames']
                    if f['image_file'] == 'photo_2.png')
    assert inferred['pose_source'] == 'leaflet_landmark_pnp' and inferred['pose_is_measured_board'] is False
    assert inferred['passes_pose_gate'] is False
    assert common.read_json(out / 'hybrid' / 'hybrid_capture.json')['contains_inferred_poses'] is True

    html = (out / 'hybrid' / 'labels/index.html').read_text(encoding='utf-8')
    assert '소엽 랜드마크로 추정한 위치 (진단용·측정 아님)' in html and '측정된 ChArUco 보드 위치' in html
    assert 'showHybrid' in html and '"uses_inferred_camera": true' in html
    assert '추정 위치를 쓴 사진에는 보드 검출이 없습니다' in html


def test_edited_reference_points_or_calibration_make_a_candidate_stale(hybrid_case, tmp_path):
    session, path, context, out, capture, (rvec, tvec), _ = hybrid_case
    folder = tmp_path / 'side'
    folder.mkdir()
    common.write_json(folder / 'candidate.json',
                      side_candidate('photo_2.png', rvec, tvec, 'a-hash-from-an-earlier-point-snapshot', capture))
    report = tool.rebuild(session, path, context, out / 'stale', side_poses=folder)
    assert report['side_pose_stale'] == 1 and report['side_poses_used_in_hybrid'] == 0
    assert report['hybrid']['points_added'] == 0
    attached = common.read_json(out / 'stale' / 'side_pose_candidates.json')
    assert attached['candidates'][0]['stale_reasons'] == ['reference_points_changed']
    assert not (out / 'stale' / 'hybrid_point_depths.csv').exists()
    assert '추정 후보 있으나 입력이 바뀜' in (out / 'stale' / 'labels/index.html').read_text(encoding='utf-8')

    depth_sha = common.file_hash(out / 'stale' / 'editor_point_depths.csv')
    common.write_json(folder / 'candidate.json',
                      side_candidate('photo_2.png', rvec, tvec, depth_sha, dict(intrinsics_sha256='other-calibration')))
    assert tool.rebuild(session, path, context, out / 'calibration',
                        side_poses=folder)['side_pose_stale'] == 1
    assert common.read_json(out / 'calibration' / 'side_pose_candidates.json'
                            )['candidates'][0]['stale_reasons'] == ['calibration_changed']


def test_a_measured_pose_is_never_replaced_and_ineligible_candidates_are_not_used(hybrid_case, tmp_path):
    session, path, context, out, capture, (rvec, tvec), _ = hybrid_case
    first = tool.rebuild(session, path, context, out / 'first')
    depth_sha = common.file_hash(out / 'first' / 'editor_point_depths.csv')
    folder = tmp_path / 'side'
    folder.mkdir()
    common.write_json(folder / 'measured.json', side_candidate('photo_0.png', rvec, tvec, depth_sha, capture))
    common.write_json(folder / 'weak.json', side_candidate('photo_2.png', rvec, tvec, depth_sha, capture,
                                                           candidate_id='side_weak', quality_status='fails_diagnostic_policy',
                                                           diagnostic_inclusion='excluded'))
    report = tool.rebuild(session, path, context, out / 'guarded', side_poses=folder)
    assert report['side_poses_used_in_hybrid'] == 0 and report['hybrid']['points_added'] == 0
    attached = {c['image_file']: c for c in
                common.read_json(out / 'guarded' / 'side_pose_candidates.json')['candidates']}
    assert attached['photo_0.png']['stale_reasons'] == ['measured_charuco_pose_exists_and_is_never_replaced']
    assert attached['photo_2.png']['freshness'] == 'current' and attached['photo_2.png']['used_in_hybrid'] is False
    assert report['side_pose_by_inclusion'] == {'eligible': 1, 'excluded': 1}
    html = (out / 'guarded' / 'labels/index.html').read_text(encoding='utf-8')
    assert '추정 후보 있으나 진단 기준 미달' in html
    assert first['side_pose_status'] == 'not_attached'


def test_pose_source_badge_separates_measurement_inference_and_absence():
    solved = dict(pose_status='solved')
    assert review_tool.pose_source_badge(solved, None)[0] == 'charuco_board_pnp'
    # A measured frame stays measured even when a candidate exists for it.
    assert review_tool.pose_source_badge(solved, dict(freshness='current', used_in_hybrid=True))[0] \
        == 'charuco_board_pnp'
    failed = dict(pose_status='failed')
    assert review_tool.pose_source_badge(failed, None)[0] == 'unavailable'
    assert review_tool.pose_source_badge(failed, dict(freshness='current', used_in_hybrid=True))[0] \
        == 'leaflet_landmark_pnp'
    assert review_tool.pose_source_badge(failed, dict(freshness='current', used_in_hybrid=False))[0] \
        == 'candidate_not_eligible'
    key, text = review_tool.pose_source_badge(failed, dict(freshness='stale', used_in_hybrid=False,
                                                           stale_reasons=['calibration_changed'],
                                                           candidate_id='side_x'))
    assert key == 'stale_candidate' and 'calibration_changed' in text and 'side_x' in text


def test_the_browser_rebuild_route_carries_the_side_pose_option(hybrid_case, tmp_path):
    """The real browser -> server -> rebuild -> viewer route, not just the CLI."""
    from tools import serve_leaf_edit_session as server
    from tools.tests.test_serve_leaf_edit_session import post_backup, running, wait
    session, path, context, out, capture, (rvec, tvec), _ = hybrid_case
    plain = server.EditService(session, context, out.parent / 'runs_plain', path)
    with running(plain) as port:
        job = wait(port, plain, post_backup(port, plain, common.read_json(path))[1]['job_id'])
    assert job['status'] == 'complete' and job['side_pose_status'] == 'not_attached'
    depth_sha = common.file_hash(out.parent / 'runs_plain' / job['job_id'] / 'result' / 'editor_point_depths.csv')
    folder = tmp_path / 'side'
    folder.mkdir()
    common.write_json(folder / 'candidate.json', side_candidate('photo_2.png', rvec, tvec, depth_sha, capture))
    service = server.EditService(session, context, out.parent / 'runs', path, side_poses=folder)
    with running(service) as port:
        job = wait(port, service, post_backup(port, service, common.read_json(path))[1]['job_id'])
    assert job['status'] == 'complete'
    assert job['side_poses_used_in_hybrid'] == 1 and job['hybrid_points_added'] == 1
    assert job['side_pose_stale'] == 0 and 'Baseline ChArUco results are unchanged' in job['hybrid_note']
    result = out.parent / 'runs' / job['job_id'] / 'result'
    assert (result / 'hybrid_point_depths.csv').exists() and (result / 'side_pose_candidates.json').exists()
    assert '소엽 랜드마크로 추정한 위치' in (result / 'labels/index.html').read_text(encoding='utf-8')
