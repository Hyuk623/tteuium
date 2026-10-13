"""Known cameras and boxes: bounded, one-view, same-centre, incompatible and degenerate extents."""
from itertools import product

import numpy as np
import pytest

from tools import leaflet_extent as tool
from tools.leaf_light.reconstruction import project
from tools.leaf_light.synthetic import camera_frame

INTRINSICS = dict(camera_matrix=[[1100, 0, 640], [0, 1100, 480], [0, 0, 1]],
                  dist_coeffs=[-0.12, 0.03, 0.001, -0.0005, 0.0], image_width_px=1280, image_height_px=960)
TARGET = np.array([0., 0., 60.])
LEAF_BOX_MM = np.array(list(product([-20., 20.], [-10., 10.], [50., 70.])))


def cameras(*centres):
    return [camera_frame(str(i), np.asarray(c, dtype=float), TARGET, 'side') for i, c in enumerate(centres)]


def tight_box(frame, points=LEAF_BOX_MM, shift_px=(0., 0.)):
    uv = project(points, frame, INTRINSICS) + 0.5 + np.asarray(shift_px)  # pixel centres -> pixel edges
    return dict(x_min_px=float(uv[:, 0].min()), y_min_px=float(uv[:, 1].min()),
                x_max_px=float(uv[:, 0].max()), y_max_px=float(uv[:, 1].max()))


def test_two_and_three_views_bound_a_region_that_contains_the_true_object():
    views = cameras([420, 0, 320], [0, 420, 300], [-300, -300, 260])
    for count in (2, 3):
        result = tool.feasible_extent([(f, tight_box(f)) for f in views[:count]], INTRINSICS)
        assert result['status'] == tool.ExtentStatus.OK
        low, high = np.array(result['cuboid_min_mm']), np.array(result['cuboid_max_mm'])
        assert np.all(LEAF_BOX_MM >= low - 1e-6) and np.all(LEAF_BOX_MM <= high + 1e-6)
        for corner in LEAF_BOX_MM:
            assert tool.point_relation(corner, result)['inside_feasible_region']
        # The enclosing cuboid is reported separately from the smaller feasible region.
        assert 0 < result['feasible_fraction_of_cuboid'] < 1
        assert result['max_projected_outside_bbox_px'] < 0.5  # distortion approximation check
        assert result['validated_metric'] is False
    two = tool.feasible_extent([(f, tight_box(f)) for f in views[:2]], INTRINSICS)
    three = tool.feasible_extent([(f, tight_box(f)) for f in views], INTRINSICS)
    assert three['feasible_volume_mm3'] <= two['feasible_volume_mm3'] + 1e-6


def test_single_view_and_same_centre_views_stay_unbounded_without_inventing_depth():
    one = cameras([420, 0, 320])[0]
    single = tool.feasible_extent([(one, tight_box(one))], INTRINSICS)
    assert single['status'] == tool.ExtentStatus.SINGLE
    assert single['cuboid_min_mm'] is None and single['cuboid_volume_mm3'] is None
    twin = dict(one, image_file='twin')  # Same camera centre: no parallax, no depth bound.
    same = tool.feasible_extent([(one, tight_box(one)), (twin, tight_box(twin, shift_px=(3, 2)))], INTRINSICS)
    assert same['status'] == tool.ExtentStatus.UNBOUNDED and same['cuboid_min_mm'] is None
    assert tool.feasible_extent([], INTRINSICS)['status'] == tool.ExtentStatus.NONE


def test_incompatible_views_are_reported_not_forced_into_a_box():
    views = cameras([420, 0, 320], [0, 420, 300])
    moved = tight_box(views[1], shift_px=(500, 0))
    result = tool.feasible_extent([(views[0], tight_box(views[0])), (views[1], moved)], INTRINSICS)
    assert result['status'] == tool.ExtentStatus.INCOMPATIBLE
    assert result['cuboid_min_mm'] is None and result['feasible_vertices_mm'] is None


def test_degenerate_region_is_not_displayed_as_a_zero_sized_box(monkeypatch):
    views = cameras([420, 0, 320], [0, 420, 300])
    monkeypatch.setattr(tool, 'MIN_INSCRIBED_RADIUS_MM', 1e6)
    result = tool.feasible_extent([(f, tight_box(f)) for f in views], INTRINSICS)
    assert result['status'] == tool.ExtentStatus.DEGENERATE
    assert result['cuboid_min_mm'] is None and result['cuboid_volume_mm3'] is None


def test_outside_points_are_measured_and_left_in_place():
    views = cameras([420, 0, 320], [0, 420, 300])
    result = tool.feasible_extent([(f, tight_box(f)) for f in views], INTRINSICS)
    far = np.array([0., 0., 400.])
    relation = tool.point_relation(far, result)
    assert relation['inside_bbox_cuboid'] is False and relation['inside_feasible_region'] is False
    assert relation['outside_cuboid_distance_mm'] > 300 and relation['feasible_region_violation_mm'] > 0
    assert relation['z_cuboid_local_mm'] == pytest.approx(far[2] - result['cuboid_min_mm'][2])
    assert far.tolist() == [0., 0., 400.]
    assert set(tool.point_relation(far, dict(status=tool.ExtentStatus.SINGLE)).values()) == {None}


def test_bbox_edges_use_pixel_edge_convention():
    outline = tool.bbox_outline_px(dict(x_min_px=10, y_min_px=20, x_max_px=30, y_max_px=50))
    assert outline[:, 0].min() == pytest.approx(9.5) and outline[:, 1].max() == pytest.approx(49.5)
    assert len(outline) == 4 * tool.EDGE_SAMPLES_PER_SIDE
