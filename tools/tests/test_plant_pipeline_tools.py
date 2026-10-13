"""Pipeline stage tools on synthetic inputs: line fits, carving, region naming, hierarchy helpers, stage status."""
import json

import cv2
import numpy as np
import pytest

from tools import plant_structure as ps
from tools import plant_hierarchy as ph
from tools import plant_pipeline as pp


def synthetic_cams():
    K = [[1500.0, 0, 1000], [0, 1500.0, 1000], [0, 0, 1]]
    frames = []
    for n, az in enumerate((0, 70, 150)):
        a = np.radians(az)
        C = np.array([400 * np.cos(a), 400 * np.sin(a), 250.0])
        z = -C / np.linalg.norm(C)
        x = np.cross(z, [0, 0, 1.0]); x /= np.linalg.norm(x)
        y = np.cross(z, x)
        R = np.stack([x, y, z])
        r, _ = cv2.Rodrigues(R)
        frames.append(dict(image_file=f'p_{n}.png', pose_status='solved', rvec_rad=r.ravel().tolist(), tvec_mm=(-R @ C).tolist()))
    return ps.Cameras(dict(intrinsics=dict(camera_matrix=K, dist_coeffs=[0, 0, 0, 0, 0], image_width_px=2000, image_height_px=2000), frames=frames))


def test_line_fit_recovers_a_known_stem_from_three_cameras():
    cams = synthetic_cams()
    A, B = np.array([5.0, -3.0, 20.0]), np.array([8.0, -1.0, 110.0])
    rays = []
    for key in cams.frames:
        for s in np.linspace(0.05, 0.95, 12):
            xy = cams.project(key, (A + s * (B - A))[None])[0]
            rays.append((key,) + cams.ray(key, tuple(xy)))
    P, u, r = ps.fit_line(rays, np.array([0, 0, 50.0]), np.array([0, 0, 1.0]))
    true_u = (B - A) / np.linalg.norm(B - A)
    assert abs(abs(u @ true_u) - 1) < 1e-6 and np.median(r) < 1e-3
    iv, two, anyv = ps.consensus(rays, P, u if u[2] > 0 else -u)
    assert two is not None and two[1] - two[0] > 70


def test_carving_keeps_the_object_and_drops_empty_space():
    cams = synthetic_cams()
    ball = np.array([[x, y, z] for x in range(-15, 16, 3) for y in range(-15, 16, 3) for z in range(40, 71, 3)
                     if x * x + y * y + (z - 55) ** 2 <= 15 ** 2], float)
    masks = {}
    for key in cams.frames:
        m = np.zeros((2000, 2000), bool)
        p = np.round(cams.project(key, ball)).astype(int)
        m[p[:, 1], p[:, 0]] = True
        masks[key] = cv2.dilate(m.astype(np.uint8), np.ones((9, 9), np.uint8)).astype(bool)
    old = ps.DILATION_PX
    ps.DILATION_PX = 2
    try:
        H = ps.carve(cams, list(cams.frames), masks)
    finally:
        ps.DILATION_PX = old
    centre = H.mean(0)
    assert np.linalg.norm(centre - [0, 0, 55]) < 3
    assert not np.any(np.linalg.norm(H - [0, 0, 55], axis=1) > 45)


def region(k, voxels, z):
    return dict(region=k, photos=2, boxes=[]), voxels, z


@pytest.mark.parametrize('sizes, n_record, expect', [
    # bottom up: region 2 (lowest) is L01
    ([(3000, 120), (2500, 100), (2000, 90)], 3, {0: 'L03', 1: 'L02', 2: 'L01'}),
    ([(3000, 120), (2500, 100), (2000, 90), (800, 125)], 3, {0: 'L03', 1: 'L02', 2: 'L01', 3: 'growing_leaf'}),
    ([(3000, 120), (2500, 100), (2000, 90), (1, 40)], 3, {0: 'L03', 1: 'L02', 2: 'L01', 3: None}),
    ([(3000, 120), (2500, 100)], 3, {0: None, 1: None}),
])
def test_region_names_follow_height_with_growing_leaf_and_fragments(sizes, n_record, expect):
    H, lab, info = [], [], []
    for k, (n, z) in enumerate(sizes):
        H += [[0, 0, z]] * n
        lab += [k] * n
        info.append(dict(region=k, photos=2, boxes=[]))
    growth = dict(compound_leaves=[dict(compound_leaf_id=f'L0{i + 1}') for i in range(n_record)])
    regions, note = ps.name_regions(np.array(H, float), np.array(lab), info, growth)
    assert {r['region']: r['proposed_name'] for r in regions} == expect


@pytest.mark.parametrize('sizes, expect', [
    # the unfolding leaf is listed last and sits at the top
    ([(3000, 120), (2500, 100), (2000, 90), (800, 125)], {0: 'L03', 1: 'L02', 2: 'L01', 3: 'L04'}),
    # no region for the unfolding leaf: only the unfolded ones are named
    ([(3000, 120), (2500, 100), (2000, 90)], {0: 'L03', 1: 'L02', 2: 'L01'}),
])
def test_unfolding_leaf_is_the_top_one(sizes, expect):
    H, lab, info = [], [], []
    for k, (n, z) in enumerate(sizes):
        H += [[0, 0, z]] * n
        lab += [k] * n
        info.append(dict(region=k, photos=2, boxes=[]))
    growth = dict(compound_leaves=[dict(compound_leaf_id=f'L0{i + 1}', is_unfolding=i == 3) for i in range(4)])
    regions, note = ps.name_regions(np.array(H, float), np.array(lab), info, growth)
    assert {r['region']: r['proposed_name'] for r in regions} == expect


def test_name_decisions_apply_only_at_the_height_they_were_made():
    regions = [dict(region=0, median_z_mm=120.0, proposed_name='L01'), dict(region=1, median_z_mm=95.0, proposed_name='L02'),
               dict(region=2, median_z_mm=80.0, proposed_name='L03')]
    decided = {'0': dict(name='L04', median_z_mm=121.0), '1': dict(name='confirm', median_z_mm=95.0),
               '2': dict(name='L01', median_z_mm=60.0)}
    assert ps.apply_name_decisions(regions, decided) == [0, 1]
    assert [r['proposed_name'] for r in regions] == ['L04', 'L02', 'L03']
    assert regions[2]['name_decision']['status'] == 'stale' and 'name_source' not in regions[2]


def test_latest_human_checks_skips_other_files(tmp_path):
    (tmp_path / 'human_checks_1.json').write_text(json.dumps(dict(schema='human-checks-1', names={'dwt_01': {}})), encoding='utf-8')
    (tmp_path / 'human_checks_2.json').write_text('{not json', encoding='utf-8')
    got = pp.latest_human_checks(dict(downloads=str(tmp_path)))
    assert got['schema'] == 'human-checks-1' and got['source'].endswith('human_checks_1.json')


def test_detached_hull_blobs_are_dropped():
    body = np.array([[x, y, z] for x in range(10) for y in range(10) for z in range(10)], float)
    blob = np.array([[100, 100, 0], [101, 100, 0]], float)
    H, removed = ps.main_component(np.vstack([body, blob]))
    assert removed == 2 and len(H) == 1000


def test_trunk_is_traced_through_the_hull_when_one_photo_labels_the_stem():
    """dwt_04 case (2026-09-28): the main-stem polygon of one photo selects the trunk column; a leaf piece behind the
    trunk on the same line of sight and the canopy above must not bend or extend the axis."""
    cams = synthetic_cams()
    A, B = np.array([10.0, -5.0, 20.0]), np.array([14.0, -3.0, 70.0])
    g = np.arange(-40, 41, 1.0)
    X, Y, Z = np.meshgrid(g + 10, g - 5, np.arange(20, 131, 1.0), indexing='ij')
    P = np.stack([X, Y, Z], -1).reshape(-1, 3)
    s = np.clip((P[:, 2] - A[2]) / (B[2] - A[2]), 0, 1)[:, None]
    on_axis = np.linalg.norm((P - (A + s * (B - A)))[:, :2], axis=1)
    trunk = (on_axis <= 3) & (P[:, 2] <= 70)
    canopy = np.linalg.norm(P - [12, -4, 100], axis=1) <= 30
    view0 = next(iter(cams.frames))
    behind = cams.centre(view0)
    d = (np.array([12.0, -4.0, 45.0]) - behind) / np.linalg.norm(np.array([12.0, -4.0, 45.0]) - behind)
    leaf_c = behind + d * (np.linalg.norm(np.array([12.0, -4.0, 45.0]) - behind) + 25)
    leaf = np.linalg.norm(P - leaf_c, axis=1) <= 5
    H = P[trunk | canopy | leaf]
    # like dwt_04 photo 28, the polygon runs on into the canopy, whose viewing column also holds leaf voxels
    lower = cams.project(view0, (A + np.linspace(0, 1.6, 30)[:, None] * (B - A)))
    ring = cv2.convexHull(np.vstack([lower + [-12, 0], lower + [12, 0]]).astype(np.float32)).reshape(-1, 2).tolist()
    dets = {view0: [dict(class_name='main-stem', rings=[ring])]}
    stem, used = ps.stem_from_hull(cams, list(cams.frames), dets, H)
    assert stem['status'] == 'fitted' and stem['method'] == 'hull_trunk'
    ax = np.array(stem['axis'])
    u = (ax[-1] - ax[0]) / np.linalg.norm(ax[-1] - ax[0])
    true_u = (B - A) / np.linalg.norm(B - A)
    assert abs(u @ true_u) > np.cos(np.radians(3))
    assert np.linalg.norm(ax[0][:2] - (A + (ax[0][2] - A[2]) / (B[2] - A[2]) * (B - A))[:2]) < 1.5
    assert ax[-1][2] < 75, 'the trace must stop where the canopy widens the slice'
    assert not (used & np.isin(np.arange(len(H)), np.flatnonzero(leaf[trunk | canopy | leaf]))).any(), \
        'a leaf behind the trunk on the same line of sight is not trunk'


def test_trunk_trace_reports_unavailable_without_stem_polygons():
    cams = synthetic_cams()
    H = np.array([[0, 0, z] for z in range(20, 60)], float)
    stem, used = ps.stem_from_hull(cams, list(cams.frames), {}, H)
    assert stem['status'] == 'unavailable' and not used.any()


def test_azimuth_around_the_stem():
    stem = dict(status='fitted', axis=[[0, 0, 0], [0, 0, 100]])
    assert ph.azimuth_around(stem, [10, 10, 50]) == (45.0, 14.1)
    assert ph.azimuth_around(dict(status='unavailable'), [1, 1, 1]) is None


def test_missing_inputs_become_human_tasks_not_results(tmp_path):
    cfg = dict(capture='build/x', labels='build/y', growth=None, batch='build/does_not_exist', decisions=[], direction_labels=None)
    p = pp.Plant('dwt_99', cfg, dict(downloads=str(tmp_path)), tmp_path)
    p.s2(); p.s5()
    assert p.stages['S2']['status'] == pp.WAIT and p.stages['S5']['status'] == pp.WAIT
    assert len(p.tasks) == 2 and all(t['priority'] in (1, 3) for t in p.tasks)


def test_points_behind_a_camera_are_never_inside_its_mask():
    cams = synthetic_cams()
    key = next(iter(cams.frames))
    C = cams.centre(key)
    front = np.array([[0, 0, 55.0]])
    behind = (C + (C - front[0]))[None]  # mirror of a visible point through the camera centre
    mask = np.ones((2000, 2000), bool)
    assert ps.inside(cams, key, front, mask)[0] and not ps.inside(cams, key, behind, mask)[0]


def test_feature_poses_join_s4_only_when_they_met_policy(tmp_path):
    from tools import cross_view_candidates as cv

    class Cams:
        frames = {'a.png': dict(pose_status='solved', rvec_rad=[0, 0, 0]), 'b.png': dict(pose_status='failed'),
                  'c.png': dict(pose_status='failed'), 'd.png': dict(pose_status='failed')}

        def posed(self, key):
            return self.frames[key].get('pose_status') == 'solved'

    rep = dict(candidates=[dict(image_file='B.png', status='solved', meets_policy=True, rvec_rad=[1, 0, 0], tvec_mm=[0, 0, 1]),
                           dict(image_file='c.png', status='solved', meets_policy=False, rvec_rad=[1, 0, 0], tvec_mm=[0, 0, 1]),
                           dict(image_file='a.png', status='solved', meets_policy=True, rvec_rad=[9, 9, 9], tvec_mm=[0, 0, 1])],
               second_round=[dict(image_file='d.png', status='no_solution')])
    (tmp_path / 'f.json').write_text(json.dumps(rep), encoding='utf-8')
    cams = Cams()
    assert cv.add_feature_poses(cams, {}, tmp_path / 'f.json') == ['b.png']
    assert cams.frames['b.png']['pose_status'] == 'feature_diagnostic'
    assert cams.frames['a.png']['rvec_rad'] == [0, 0, 0]  # a measured board pose is never replaced
    assert cv.add_feature_poses(cams, {}, None) == []


def test_top_views_are_recognised_by_view_code():
    from tools.plant_structure import _is_top
    assert _is_top('dwt_01_20260920_01.png') and _is_top('autodwt01_20260920_03.png')
    assert not _is_top('dwt_01_20260920_11.png') and not _is_top('dwt_01_20260920_24.png')
