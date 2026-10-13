"""Importing an organized capture: path resolution, integrity refusals, and measured poses.

Uses rendered ChArUco images, so no HEIC encoder or camera is needed.
"""
import csv
import hashlib
import json

import cv2
import numpy as np
from PIL import Image
import pytest

from tomato3d.calib.board import build_charuco_board
from tomato3d.config import get_settings
from tomato3d.io.schemas import BoardSpec
from tools import import_organized_capture as tool
from tools.leaf_light import common

SIZE = (900, 900)


def board_photo(path, visible: bool):
    """A top view of the configured board, or a photo where it is not detectable."""
    spec = BoardSpec.model_validate_json(get_settings().board_spec_path.read_text(encoding='utf-8'))
    canvas = np.full((SIZE[1], SIZE[0], 3), 90, np.uint8)
    if visible:
        board = build_charuco_board(spec).generateImage((700, 500))
        canvas[200:700, 100:800] = cv2.cvtColor(board, cv2.COLOR_GRAY2BGR)
    Image.fromarray(cv2.cvtColor(canvas, cv2.COLOR_BGR2RGB)).save(path, format='PNG')
    return common.file_hash(path)


@pytest.fixture
def organized(tmp_path, monkeypatch):
    monkeypatch.setattr(common, 'BUILD', tmp_path / 'build')
    monkeypatch.setattr(tool, 'output_dir', lambda path: common.output_dir(path))
    source = tmp_path / 'organized' / '260920'
    folder = source / 'dwt_09' / '260920'
    folder.mkdir(parents=True)
    rows = []
    for code, visible in (('01', True), ('11', False), ('21', True)):
        name = f'dwt_09_260920_{code}.png'
        digest = board_photo(folder / name, visible)
        rows.append(dict(plant_id='dwt_09', capture_date='2026-09-20', view_code=code,
                         organized_path=f'dwt_09\\260920\\{name}', sha256=digest))
    mapping = tmp_path / 'organized' / 'filename_mapping.csv'
    with mapping.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    intrinsics = dict(schema_version='1.0', camera_id='test_camera', image_width_px=SIZE[0], image_height_px=SIZE[1],
                      camera_matrix=[[1200., 0., SIZE[0]/2], [0., 1200., SIZE[1]/2], [0., 0., 1.]],
                      dist_coeffs=[0., 0., 0., 0., 0.], rms_reprojection_error_px=0.4, n_calibration_images=20)
    intrinsics_path = tmp_path / 'intrinsics.json'
    common.write_json(intrinsics_path, intrinsics)
    return source, mapping, intrinsics_path, tmp_path / 'build' / 'imported'


def test_import_resolves_the_date_directory_and_keeps_failed_poses_explicit(organized):
    source, mapping, intrinsics_path, out = organized
    before = {p.name: common.file_hash(p) for p in source.rglob('*.png')}
    report = tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out)
    assert report['photo_count'] == 3 and report['solved_pose_count'] == 2
    assert report['pose_by_view_group'] == dict(top=dict(total=1, solved=1), side=dict(total=1, solved=0),
                                                oblique=dict(total=1, solved=1))
    assert report['sources_modified'] is False and report['validated_metric'] is False
    capture = common.read_json(out / 'capture.json')
    assert capture['schema_version'] == 'diagnostic-preview-capture-1' and capture['plant_id'] == 'dwt_09'
    assert capture['board_variant_id'] == common.read_json(get_settings().board_spec_path)['variant_id']
    assert capture['board_variant_evidence']['confirmed_by_user'] is False
    assert capture['camera_profile']['same_camera_confirmed_by_user'] is False
    assert capture['quality']['min_pose_corners'] == 6 and capture['quality']['max_pose_error_px'] == 1.0
    side = next(f for f in capture['frames'] if f['view_code'] == '11')
    top = next(f for f in capture['frames'] if f['view_code'] == '01')
    assert side['pose_status'] == 'too_few_corners' and side['rvec_rad'] is None
    assert 'ChArUco corners' in side['failure_reason'] and side['passes_pose_gate'] is False
    assert top['pose_status'] == 'solved' and top['reprojection_error_px'] < 1.0 and top['passes_pose_gate'] is True
    assert top['board_evidence']['source_image_sha256'] == top['sha256']
    # The stored pose must be in the pipeline's board frame: evidence residuals are computed by
    # reprojecting board-frame corners with it, so a sheet-frame pose would blow this up.
    assert top['board_evidence']['existing_pose_charuco_rms_px'] < 1.0
    assert capture['coordinate_frame'].startswith('board')
    assert top['observed_view_group'] == 'top' and top['nominal_polar_deg'] == 0.0
    # Working copies are real decodes of the sources, and the sources are untouched.
    for frame in capture['frames']:
        working = out / frame['image_path']
        assert common.file_hash(working) == frame['sha256']
        with Image.open(working) as image:
            assert image.size == SIZE
    assert {p.name: common.file_hash(p) for p in source.rglob('*.png')} == before
    rows = common.rows(out / 'import_table.csv')
    assert [r['view_code'] for r in rows] == ['01', '11', '21']
    assert '측면' in (out / 'index.html').read_text(encoding='utf-8')


def test_integrity_and_camera_refusals_write_nothing(organized, tmp_path):
    source, mapping, intrinsics_path, out = organized
    photo = source / 'dwt_09' / '260920' / 'dwt_09_260920_01.png'
    original = photo.read_bytes()
    photo.write_bytes(original[:-4] + b'\x00\x00\x00\x00')  # same name, different bytes
    with pytest.raises(common.StudyError, match='SHA-256 changed'):
        tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out)
    assert not out.exists()
    photo.write_bytes(original)
    rows = list(csv.DictReader(mapping.open(encoding='utf-8-sig')))
    duplicated = tmp_path / 'duplicate.csv'
    with duplicated.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows + [rows[0]])
    with pytest.raises(common.StudyError, match='Duplicate mapping'):
        tool.import_capture(source, duplicated, 'dwt_09', intrinsics_path, out)
    missing = tmp_path / 'missing.csv'
    rows[1]['organized_path'] = 'dwt_09\\260920\\absent.png'
    with missing.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with pytest.raises(common.StudyError, match='not found'):
        tool.import_capture(source, missing, 'dwt_09', intrinsics_path, out)
    with pytest.raises(common.StudyError, match='No mapping rows'):
        tool.import_capture(source, mapping, 'dwt_99', intrinsics_path, out)
    wrong_size = common.read_json(intrinsics_path)
    wrong_size['image_width_px'] = 1234
    other = tmp_path / 'other_intrinsics.json'
    common.write_json(other, wrong_size)
    with pytest.raises(common.StudyError, match='do not rescale'):
        tool.import_capture(source, mapping, 'dwt_09', other, out)
    assert not out.exists()


def test_mixed_cameras_and_unknown_view_codes_are_refused(organized, monkeypatch, tmp_path):
    source, mapping, intrinsics_path, out = organized
    from tools.leaf_light import phone
    real = phone.read_phone_image
    calls = {'n': 0}

    def mixed(path):
        image, metadata = real(path)
        calls['n'] += 1
        metadata['model'] = 'iPhone 16' if calls['n'] % 2 else 'Other Phone'
        return image, metadata
    monkeypatch.setattr(phone, 'read_phone_image', mixed)
    with pytest.raises(common.StudyError, match='one camera/lens/mode'):
        tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out)
    assert not out.exists()
    monkeypatch.setattr(phone, 'read_phone_image', real)
    rows = list(csv.DictReader(mapping.open(encoding='utf-8-sig')))
    rows[0]['view_code'] = '99'
    bad = tmp_path / 'bad_code.csv'
    with bad.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with pytest.raises(common.StudyError, match='Unknown view code'):
        tool.import_capture(source, bad, 'dwt_09', intrinsics_path, out)


def test_heic_name_must_be_a_real_container(organized, tmp_path):
    source, mapping, intrinsics_path, out = organized
    photo = source / 'dwt_09' / '260920' / 'dwt_09_260920_01.png'
    renamed = photo.with_suffix('.heic')
    photo.rename(renamed)  # a PNG merely renamed to .heic
    rows = list(csv.DictReader(mapping.open(encoding='utf-8-sig')))
    rows[0]['organized_path'] = 'dwt_09\\260920\\' + renamed.name
    rows[0]['sha256'] = common.file_hash(renamed)
    renamed_csv = tmp_path / 'renamed.csv'
    with renamed_csv.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    with pytest.raises(common.StudyError, match='ISO container'):
        tool.import_capture(source, renamed_csv, 'dwt_09', intrinsics_path, out)
    assert not out.exists()


def test_decoder_requirement_is_reported_not_guessed(monkeypatch, tmp_path):
    import builtins
    real_import = builtins.__import__

    def without_pillow_heif(name, *args, **kwargs):
        if name == 'pillow_heif':
            raise ImportError('missing for this test')
        return real_import(name, *args, **kwargs)
    monkeypatch.setattr(builtins, '__import__', without_pillow_heif)
    with pytest.raises(common.StudyError, match='pillow-heif'):
        tool.load_decoder(tmp_path / 'no_runtime_here')


def test_foreign_but_uniform_camera_is_not_claimed_compatible(organized, monkeypatch):
    """R1: equal image dimensions are not calibration compatibility."""
    source, mapping, intrinsics_path, out = organized
    from tools.leaf_light import phone
    real = phone.read_phone_image

    def foreign(path):
        image, metadata = real(path)
        metadata.update(make='OtherBrand', model='OtherCam 1', lens_model='OtherCam 2mm f/2.8',
                        focal_length_mm=2.0, digital_zoom_ratio=2.0)
        return image, metadata
    monkeypatch.setattr(phone, 'read_phone_image', foreign)
    # The calibration declares no camera profile, so the import must say so instead of claiming a match.
    report = tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out)
    profile = report['camera_profile']
    assert profile['calibration_compatibility'] == 'unverified_no_camera_profile_available'
    assert profile['compared_fields'] == [] and profile['calibration_declared_profile'] is None
    assert 'NOT calibration compatibility' in profile['note']
    assert profile['exif_model'] == 'OtherCam 1' and profile['same_camera_confirmed_by_user'] is False
    # With an explicit contract, the same foreign set is refused before anything is written.
    with pytest.raises(common.StudyError, match='expected calibration camera profile'):
        tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out.with_name('contract'),
                            expected_camera=dict(model='Apple iPhone 16'))
    assert not out.with_name('contract').exists()


def test_calibration_declared_profile_is_compared_and_enforced(organized, tmp_path, monkeypatch):
    source, mapping, intrinsics_path, out = organized
    declared = common.read_json(intrinsics_path)
    declared['camera_profile'] = dict(exif_model='Apple iPhone 16', exif_lens_model='iPhone 16 back camera 5.96mm f/1.6')
    profiled = tmp_path / 'profiled_intrinsics.json'
    common.write_json(profiled, declared)
    from tools.leaf_light import phone
    real = phone.read_phone_image

    def matching(path):
        image, metadata = real(path)
        metadata.update(model='Apple iPhone 16', lens_model='iPhone 16 back camera 5.96mm f/1.6')
        return image, metadata
    monkeypatch.setattr(phone, 'read_phone_image', matching)
    report = tool.import_capture(source, mapping, 'dwt_09', profiled, out)
    profile = report['camera_profile']
    assert profile['calibration_compatibility'] == 'verified_against_declared_profile'
    assert profile['compared_fields'] == ['exif_lens_model', 'exif_model']
    assert 'still not proven identical' in profile['note']

    def different_lens(path):
        image, metadata = matching(path)
        metadata['lens_model'] = 'iPhone 16 back camera 13mm f/2.4'
        return image, metadata
    monkeypatch.setattr(phone, 'read_phone_image', different_lens)
    with pytest.raises(common.StudyError, match='expected calibration camera profile'):
        tool.import_capture(source, mapping, 'dwt_09', profiled, out.with_name('mismatch'))
    assert not out.with_name('mismatch').exists()


def test_board_caption_is_sourced_per_session_or_unavailable(organized):
    """R3: no canned 'observed caption' for sessions nobody looked at."""
    source, mapping, intrinsics_path, out = organized
    tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out)
    evidence = common.read_json(out / 'capture.json')['board_variant_evidence']
    assert evidence['printed_caption_observed'] is None and evidence['printed_caption_source'] is None
    assert evidence['confirmed_by_user'] is False
    assert evidence['configured_square_size_mm'] > 0
    assert evidence['detected_ids_exceeding_configured_board'] == []
    assert evidence['reprojection_cannot_distinguish_scale'] is True
    supplied = tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out.with_name('sourced'),
                                   session_evidence=dict(caption='7 x 5 squares, 38 mm', source='top view 01',
                                                         observed_by='tester', observed_at='2026-09-20'))
    sourced = common.read_json(out.with_name('sourced') / 'capture.json')['board_variant_evidence']
    assert sourced['printed_caption_observed'] == '7 x 5 squares, 38 mm'
    assert sourced['printed_caption_source'] == 'top view 01' and sourced['observed_by'] == 'tester'
    assert sourced['confirmed_by_user'] is False and supplied['plant_id'] == 'dwt_09'


def test_inactive_null_pose_gate_is_loaded_but_not_applied(organized, tmp_path, monkeypatch):
    """R4: CONVENTIONS section 3 - a null threshold is inactive, not a crash and not a default."""
    source, mapping, intrinsics_path, out = organized
    settings = tool.get_settings()
    thresholds = common.read_json(settings.config_dir / 'quality_thresholds.json')
    thresholds['max_mean_reprojection_error_px'] = None
    thresholds['min_charuco_corners_for_pose'] = None
    config = tmp_path / 'config'
    config.mkdir()
    common.write_json(config / 'quality_thresholds.json', thresholds)

    class Overridden:
        board_spec_path = settings.board_spec_path
        config_dir = config
    monkeypatch.setattr(tool, 'get_settings', lambda: Overridden())
    report = tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out)
    quality = report['quality']
    assert quality['max_pose_error_px'] is None and quality['pose_gate_active'] is False
    assert quality['min_pose_corners'] == tool.PNP_MINIMUM_CORNERS
    assert 'inactive' in quality['min_pose_corners_source']
    capture = common.read_json(out / 'capture.json')
    solved = [f for f in capture['frames'] if f['pose_status'] == 'solved']
    assert solved and all(f['passes_pose_gate'] is None for f in solved), 'an inactive gate cannot pass or fail'
    assert report['accepted_pose_count'] is None, 'an inactive gate cannot report accepted poses'

@pytest.mark.parametrize('observed,expected,match', [
    (5.960000038146973, '5.96', True), (5.969, '5.96', True),
    (5.959, '5.96', False), (5.97, '5.96', False), (None, '5.96', False),
])
def test_focal_comparison_truncates_not_rounds(observed, expected, match):
    assert tool.camera_field_matches('exif_focal_length_mm', observed, expected) is match


@pytest.mark.parametrize('value', ['bad', 'NaN', 'Infinity', -1, 0])
def test_focal_comparison_rejects_invalid_values(value):
    with pytest.raises(common.StudyError, match='Invalid focal length'):
        tool.truncated_focal_length_mm(value)


def test_focal_truncation_applies_within_session_and_preserves_raw_values():
    import copy
    records = [{'metadata': dict(model='Camera', image_width_px=900, image_height_px=900,
                                 focal_length_mm=value)} for value in [5.960000038146973, 5.969]]
    original = copy.deepcopy(records)
    intrinsics = dict(image_width_px=900, image_height_px=900,
                      camera_profile={'exif_focal_length_mm': 5.96})
    result = tool.camera_profile(records, intrinsics, {'focal_length_mm': '5.96'})
    assert result['exif_focal_length_mm'] == 5.960000038146973
    assert records == original and intrinsics['camera_profile']['exif_focal_length_mm'] == 5.96
    assert result['calibration_compatibility'] == 'verified_against_declared_profile'
    records[1]['metadata']['focal_length_mm'] = 5.97
    with pytest.raises(common.StudyError, match='one camera/lens/mode'):
        tool.camera_profile(records, intrinsics)


def test_an_excluded_view_is_hash_checked_listed_and_not_imported(organized, tmp_path):
    source, mapping, intrinsics_path, out = organized
    # view 11 becomes a portrait frame: the whole session would be refused as mixed sizes
    portrait = source / 'dwt_09' / '260920' / 'dwt_09_260920_11.png'
    Image.new('RGB', (SIZE[0], SIZE[1] + 300), (90, 90, 90)).save(portrait, format='PNG')
    rows = list(csv.DictReader(mapping.open(encoding='utf-8-sig')))
    for r in rows:
        if r['view_code'] == '11':
            r['sha256'] = common.file_hash(portrait)
    with mapping.open('w', encoding='utf-8-sig', newline='') as stream:
        writer = csv.DictWriter(stream, fieldnames=list(rows[0])); writer.writeheader(); writer.writerows(rows)
    with pytest.raises(common.StudyError):
        tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, tmp_path / 'build' / 'refused')
    report = tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, out, exclude_views={'11': 'portrait frame'})
    assert report['photo_count'] == 2 and report['excluded_views'] == [dict(view_code='11', reason='portrait frame')]
    assert not any('_11' in p.name for p in (out / 'images').iterdir())
    with pytest.raises(common.StudyError):
        tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, tmp_path / 'build' / 'x', exclude_views={'99': 'nope'})
    with pytest.raises(common.StudyError):
        tool.import_capture(source, mapping, 'dwt_09', intrinsics_path, tmp_path / 'build' / 'y', exclude_views={'11': ' '})
