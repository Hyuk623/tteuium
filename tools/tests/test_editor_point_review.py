"""Sparse observed pixels remain visible; predictions never masquerade as labels."""
from PIL import Image
import pytest

from tools import editor_point_review as tool
from tools.leaf_light import common
from tools.tests.test_manual_leaf_preview_fragments import fragment_case


def test_observation_colors_original_resolution_and_escaped_ids(fragment_case):
    capture_path, _, out = fragment_case
    out.mkdir(parents=True)
    capture = common.read_json(capture_path)
    rows = [dict(image_file='photo_0.png', organ_id='<script>bad()</script>', leaflet_id='L', point_id='b0',
                 point_kind='boundary', x_px=500., y_px=400., depth_status='fewer_than_two_solved_views'),
            dict(image_file='photo_0.png', organ_id='O', leaflet_id='L', point_id='i0', point_kind='interior',
                 x_px=800., y_px=400., z_board_mm=100., camera_axis_z_mm=350.)]
    tool.write_point_review(capture, rows, out)
    assert len(list((out / 'labels').glob('photo_*.jpg'))) == 3
    with Image.open(out / 'labels/photo_0000.jpg') as im:
        assert im.size == (1600, 1200)
        red, green, blue = im.getpixel((500, 400))
        assert red > green > blue  # Filled orange saved boundary point.
        red, green, blue = im.getpixel((800, 396))
        assert red > green + 30 and blue > green + 30  # Magenta interior ring.
    html = (out / 'labels/index.html').read_text(encoding='utf-8')
    assert '&lt;script&gt;bad()&lt;/script&gt;' in html and '<script>bad()</script>' not in html
    assert 'photo_2.png' in html and '대응 사진 부족' in html


def test_projected_and_unavailable_observed_coordinates_are_not_drawn(fragment_case):
    capture_path, _, out = fragment_case
    out.mkdir(parents=True)
    capture = common.read_json(capture_path)
    rows = [dict(image_file='photo_0.png', point_id='b0', observation_kind='projected', x_px=500, y_px=400),
            dict(image_file='photo_0.png', point_id='b1', observed_x_px=None, observed_y_px=None, x_px=800, y_px=400)]
    tool.write_point_review(capture, rows, out)
    with Image.open(out / 'labels/photo_0000.jpg') as im:
        for point in ((500, 400), (800, 400)):
            assert max(abs(a-b) for a, b in zip(im.getpixel(point), (30, 40, 50))) < 5
    assert '표시한 관찰점 0개 / 저장된 행 2개' in (out / 'labels/index.html').read_text(encoding='utf-8')


def test_accepted_outline_is_visible_without_inventing_points_or_filling_holes(fragment_case):
    capture_path, _, out = fragment_case
    out.mkdir(parents=True)
    region = dict(image_file='photo_0.png', leaflet_id='L', rings=[
        dict(points_px=[[100, 100], [300, 100], [300, 300], [100, 300]]),
        dict(is_hole=True, points_px=[[180, 180], [220, 180], [220, 220], [180, 220]])])
    tool.write_point_review(common.read_json(capture_path), [], out, accepted_regions=[region])
    with Image.open(out / 'labels/photo_0000.jpg') as im:
        for point in ((200, 100), (200, 180)):
            red, green, blue = im.getpixel(point)
            assert green > red + 70 and blue > red + 70
        assert max(abs(a-b) for a,b in zip(im.getpixel((200, 200)), (30,40,50))) < 5
    html = (out / 'labels/index.html').read_text(encoding='utf-8')
    assert '수락한 2D 윤곽 1개' in html and '표시한 관찰점 0개' in html


def test_empty_rows_keep_all_photos_and_output_must_stay_in_build(fragment_case):
    capture_path, _, out = fragment_case
    out.mkdir(parents=True)
    capture = common.read_json(capture_path)
    tool.write_point_review(capture, [], out)
    assert len(list((out / 'labels').glob('photo_*.jpg'))) == 3
    with pytest.raises(ValueError, match='inside build'):
        tool.write_point_review(capture, [], capture_path.parent)


def test_point_scene_keeps_sparse_ids_and_observations_without_inventing_depth():
    capture = dict(frames=[dict(image_file='a.png'), dict(image_file='b.png')])
    def row(pid, image, xyz):
        return dict(organ_id='O', leaflet_id='B1', point_id=pid, image_file=image,
                    x_px=20, y_px=30, **dict(zip(('x_board_mm', 'y_board_mm', 'z_board_mm'), xyz)))
    rows = [row(pid, image, [0, 20, 100]) for pid in ('b0', 'b2', 'b5') for image in ('a.png', 'b.png')]
    rows += [row('b1', 'a.png', [None, None, None]), row('b3', 'a.png', [1, 2, 3]),
             row('b3', 'b.png', [1, 2, 4]), row('b4', 'a.png', [1, 2, float('nan')])]
    points = tool.point_scene_payload(capture, rows)
    assert [p['point_id'] for p in points] == ['b0', 'b2', 'b5']
    assert all(p['photo_indices'] == [0, 1] and p['xyz_mm'] == (0, 20, 100) for p in points)
    assert all(p['validated_metric'] is False and 'faces' not in p for p in points)
