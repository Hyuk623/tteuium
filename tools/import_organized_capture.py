"""Import one organized capture session (HEIC) into a diagnostic capture with measured poses.

python -m tools.import_organized_capture --source tomato_photos_organized_/260920
  --mapping tomato_photos_organized_/filename_mapping.csv --plant dwt_01
  --intrinsics build/photo_audit_board_20260919/intrinsics.board_only.trial.json
  --out build/new_captures_20260920/dwt_01

Sources are read only: originals, the mapping CSV and growth records are never written.
Mapping rows are resolved against the outer date directory, every SHA-256 is re-checked, and
HEIC is really decoded (renaming an extension is not decoding). Poses come from measured
ChArUco detections with the configured board; the existing gates are applied unchanged and
failures stay explicit. Nothing here is validated metric geometry or PPFD input.
"""
from __future__ import annotations

import argparse
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_DOWN
from html import escape
import json
from pathlib import Path
import re
import sys

import cv2
import numpy as np

from tomato3d.config import get_settings
from tomato3d.io.schemas import BoardSpec
from tomato3d.calib.board import build_charuco_board, sheet_to_board_mm
from tools.charuco_capture_evidence import detect_evidence
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json, write_rows

VIEW_GROUPS = {'top': ('01', '03'), 'side': tuple(f'1{i}' for i in range(1, 9)),
               'oblique': tuple(f'2{i}' for i in range(1, 9))}
NOMINAL_POLAR_DEG = {'top': 0.0, 'side': 90.0, 'oblique': 45.0}
MAPPING_COLUMNS = ('plant_id', 'view_code', 'organized_path', 'sha256')
PNP_MINIMUM_CORNERS = 4  # solvePnP cannot run with fewer, whatever the configuration says
IMPORT_COLUMNS = ('plant_id', 'view_code', 'view_group', 'image_file', 'source_path', 'source_sha256',
                  'working_png_sha256', 'source_orientation', 'orientation_applied', 'image_width_px',
                  'image_height_px', 'n_markers_detected', 'n_corners_detected', 'pose_status',
                  'reprojection_error_px', 'passes_pose_gate', 'failure_reason')


def view_group(code: str) -> str:
    for name, codes in VIEW_GROUPS.items():
        if code in codes:
            return name
    raise StudyError(f'Unknown view code {code}; the capture protocol defines 01/03, 11-18, 21-28')


def mapping_rows(mapping: Path, plant_id: str) -> list[dict]:
    with mapping.open(encoding='utf-8-sig', newline='') as stream:
        import csv
        rows = [row for row in csv.DictReader(stream) if (row.get('plant_id') or '').strip() == plant_id]
    if not rows:
        raise StudyError(f'No mapping rows for plant {plant_id}')
    for row in rows:
        missing = [c for c in MAPPING_COLUMNS if not (row.get(c) or '').strip()]
        if missing:
            raise StudyError(f'Mapping row for {plant_id} is missing {missing}')
    codes = Counter(r['view_code'].strip() for r in rows)
    paths = Counter(r['organized_path'].strip() for r in rows)
    duplicates = [code for code, count in codes.items() if count > 1] + [p for p, count in paths.items() if count > 1]
    if duplicates:
        raise StudyError(f'Duplicate mapping entries, refusing to guess: {sorted(set(duplicates))}')
    return sorted(rows, key=lambda r: r['view_code'])


def resolve(source: Path, organized_path: str, plant_id: str) -> Path:
    """The user keeps an outer date directory; resolve against it without rewriting the CSV."""
    parts = [p for p in re.split(r'[\\/]+', organized_path.strip()) if p]
    if not parts or parts[0] != plant_id:
        raise StudyError(f'Mapping path does not start with its plant directory: {organized_path}')
    candidate = source.joinpath(*parts)
    if not candidate.is_file():
        raise StudyError(f'Mapped photograph not found under {source}: {organized_path}')
    return candidate


def load_decoder(runtime: Path | None) -> None:
    try:
        import pillow_heif  # noqa: F401
        return
    except ImportError:
        pass
    if runtime is not None and runtime.is_dir():
        sys.path.insert(0, str(runtime.resolve()))
    try:
        import pillow_heif  # noqa: F401
    except ImportError as exc:
        raise StudyError('HEIC decoding needs pillow-heif; pass --heif-runtime with the vendored runtime '
                         'or export original-size JPEGs. Renaming the extension is not decoding.') from exc


CALIBRATION_PROFILE_KEYS = ('exif_make', 'exif_model', 'exif_lens_model', 'exif_focal_length_mm',
                            'exif_digital_zoom_ratio')
EXPECTATION_KEYS = {'make': 'exif_make', 'model': 'exif_model', 'lens_model': 'exif_lens_model',
                    'focal_length_mm': 'exif_focal_length_mm', 'digital_zoom_ratio': 'exif_digital_zoom_ratio'}


def truncated_focal_length_mm(value: object) -> str | None:
    """Comparison only: discard digits after hundredths; keep stored EXIF unchanged."""
    if value is None:
        return None
    try:
        number = Decimal(str(value).strip())
        if not number.is_finite() or number <= 0:
            raise ValueError('focal length must be finite and positive')
        return str(number.quantize(Decimal('0.01'), rounding=ROUND_DOWN))
    except (InvalidOperation, ValueError) as exc:
        raise StudyError(f'Invalid focal length in mm: {value!r}') from exc


def camera_field_matches(key: str, observed: object, expected: object) -> bool:
    if key == 'exif_focal_length_mm':
        return truncated_focal_length_mm(observed) == truncated_focal_length_mm(expected)
    return str(observed).strip().casefold() == str(expected).strip().casefold()


def calibration_profile(intrinsics: dict) -> dict:
    """The EXIF profile a calibration file declares, if it declares one at all."""
    declared = intrinsics.get('camera_profile') if isinstance(intrinsics.get('camera_profile'), dict) else intrinsics
    return {key: declared.get(key) for key in CALIBRATION_PROFILE_KEYS if declared.get(key) is not None}


def camera_profile(records: list[dict], intrinsics: dict, expected: dict | None = None) -> dict:
    """One physical camera/lens/mode per session, with calibration compatibility stated explicitly.

    Equal image dimensions do NOT prove calibration compatibility. A comparison happens only
    against a profile the calibration file actually declares, or against an explicit
    ``--expect-camera-*`` contract; otherwise compatibility is reported as unverified.
    """
    keys = ('make', 'model', 'lens_model', 'focal_length_mm', 'digital_zoom_ratio')
    unique = {key: sorted({json.dumps(truncated_focal_length_mm(r['metadata'].get(key))
                                    if key == 'focal_length_mm' else r['metadata'].get(key))
                           for r in records}) for key in keys}
    mixed = {key: values for key, values in unique.items() if len(values) > 1}
    if mixed:
        raise StudyError(f'Photographs were not taken with one camera/lens/mode: {mixed}')
    sizes = {(r['metadata']['image_width_px'], r['metadata']['image_height_px']) for r in records}
    if len(sizes) != 1:
        raise StudyError(f'Mixed image sizes in one session: {sorted(sizes)}')
    size = sizes.pop()
    if size != (intrinsics['image_width_px'], intrinsics['image_height_px']):
        raise StudyError(f'Photographs are {size}, calibration is '
                         f"{(intrinsics['image_width_px'], intrinsics['image_height_px'])}; do not rescale annotations")
    observed = {target: records[0]['metadata'].get(source) for source, target in EXPECTATION_KEYS.items()}
    declared = calibration_profile(intrinsics)
    contract = {EXPECTATION_KEYS[key]: value for key, value in (expected or {}).items() if value is not None}
    mismatches = {key: dict(photographs=observed.get(key), expected=value)
                  for key, value in {**declared, **contract}.items()
                  if not camera_field_matches(key, observed.get(key), value)}
    if mismatches:
        raise StudyError('Photographs do not match the expected calibration camera profile: '
                         f'{mismatches}. Import with the matching calibration, or state a different contract.')
    compared = sorted(set(declared) | set(contract))
    if compared:
        status = 'verified_against_declared_profile' if declared else 'verified_against_explicit_contract'
        note = ('Camera/lens fields compared and equal for: ' + ', '.join(compared) +
                '. Zoom/crop/focus/processing settings are still not proven identical to the calibration session.')
    else:
        status = 'unverified_no_camera_profile_available'
        note = ('The calibration file declares no EXIF camera profile and no --expect-camera-* contract was '
                'given, so only image dimensions could be compared. Equal dimensions are NOT calibration '
                'compatibility. The user states one lens is used, which reduces lens-switching risk but is an '
                'operational statement, not a measurement.')
    return dict(**observed, image_size_px=list(size), intrinsics_camera_id=intrinsics.get('camera_id'),
                intrinsics_rms_reprojection_error_px=intrinsics.get('rms_reprojection_error_px'),
                calibration_declared_profile=declared or None, explicit_expectation=contract or None,
                compared_fields=compared, calibration_compatibility=status,
                focal_length_comparison='truncate to 2 decimal places in mm; raw values preserved',
                image_size_matches_calibration=True, same_camera_confirmed_by_user=False,
                one_lens_operation_stated_by_user=True, note=note)


def board_variant_evidence(spec: BoardSpec, frames: list[dict], observed: dict | None) -> dict:
    """Only measured detections and explicitly sourced observations. Never a canned caption.

    The configured square size is what PnP actually uses; a descriptive string cannot change
    geometry. Writing the same 'observed caption' into every session would falsely suggest the
    printed board was checked for that session, so an unsourced observation stays unavailable.
    """
    detected = [m for f in frames for m in f['board_evidence']['detected_marker_ids']]
    evidence = dict(configured_variant=spec.variant_id, configured_square_size_mm=spec.square_size_mm,
                    configured_marker_id_range=[min(spec.marker_ids), max(spec.marker_ids)],
                    max_detected_marker_id=max(detected) if detected else None,
                    detected_marker_id_count=len(set(detected)),
                    detected_ids_exceeding_configured_board=sorted({m for m in detected if m > max(spec.marker_ids)}),
                    reprojection_cannot_distinguish_scale=True,
                    printed_caption_observed=None, printed_caption_source=None, observed_by=None, observed_at=None,
                    confirmed_by_user=False,
                    note=('Marker IDs and reprojection cannot establish the printed variant: a different print with '
                          'the same dictionary rescales every length. Supply --board-caption with its source, or '
                          'leave it unavailable.'))
    if observed:
        evidence.update(printed_caption_observed=observed.get('caption'),
                        printed_caption_source=observed.get('source'), observed_by=observed.get('observed_by'),
                        observed_at=observed.get('observed_at'),
                        confirmed_by_user=bool(observed.get('confirmed_by_user')))
    return evidence


def solve_pose(board, spec: BoardSpec, corner_ids, corner_pixels, intrinsics: dict, quality: dict) -> dict:
    """Poses are stored in the pipeline's BOARD frame, not OpenCV's sheet frame.

    ``sheet_to_board_mm`` is the project's only sheet->board map (CONVENTIONS section 6), so the
    stored rvec/tvec reproject board-frame points the way every existing viewer and the
    reconstruction expect.
    """
    matrix = np.asarray(intrinsics['camera_matrix'], float)
    distortion = np.asarray(intrinsics['dist_coeffs'], float)
    result = dict(pose_status='too_few_corners', rvec_rad=None, tvec_mm=None, reprojection_error_px=None,
                  passes_pose_gate=False if quality['max_pose_error_px'] is not None else None, failure_reason=None)
    if len(corner_ids) < quality['min_pose_corners']:
        result['failure_reason'] = f'{len(corner_ids)} ChArUco corners; {quality["min_pose_corners"]} required'
        return result
    object_points = sheet_to_board_mm(board.getChessboardCorners(), spec)[np.asarray(corner_ids, dtype=int)]
    image_points = np.asarray(corner_pixels, float).reshape(-1, 2)
    solved, rvec, tvec = cv2.solvePnP(object_points, image_points, matrix, distortion,
                                      flags=cv2.SOLVEPNP_ITERATIVE)
    if not solved:
        return dict(result, pose_status='failed', failure_reason='solvePnP did not converge')
    projected = cv2.projectPoints(object_points, rvec, tvec, matrix, distortion)[0].reshape(-1, 2)
    error = float(np.sqrt(np.mean(np.sum((projected - image_points) ** 2, axis=1))))
    gate = quality['max_pose_error_px']
    return dict(result, pose_status='solved', rvec_rad=rvec.ravel().tolist(), tvec_mm=tvec.ravel().tolist(),
                reprojection_error_px=error,
                passes_pose_gate=None if gate is None else error <= gate,
                failure_reason=None if gate is None or error <= gate else f'reprojection {error:.3f} px exceeds {gate} px')


def import_capture(source: Path, mapping: Path, plant_id: str, intrinsics_path: Path, out: Path,
                   session_id: str | None = None, heif_runtime: Path | None = None,
                   expected_camera: dict | None = None, session_evidence: dict | None = None,
                   exclude_views: dict[str, str] | None = None) -> dict:
    """exclude_views: {view_code: reason}. An excluded photo is still hash-checked but never decoded, posed or
    written; it is listed in the report. Use it for a photo the calibration cannot describe (e.g. a portrait
    frame among square ones) instead of cropping or rescaling it."""
    exclude_views = {str(k): str(v) for k, v in (exclude_views or {}).items()}
    if any(not reason.strip() for reason in exclude_views.values()):
        raise StudyError('Every excluded view needs a written reason')
    source, mapping, intrinsics_path = (p.resolve() for p in (source, mapping, intrinsics_path))
    intrinsics = read_json(intrinsics_path)
    settings = get_settings()
    spec = BoardSpec.model_validate_json(settings.board_spec_path.read_text(encoding='utf-8'))
    board = build_charuco_board(spec)
    detector = cv2.aruco.CharucoDetector(board)
    thresholds = read_json(settings.config_dir / 'quality_thresholds.json')
    # CONVENTIONS section 3: a null threshold is loaded but INACTIVE. Never substitute a default.
    corner_minimum = thresholds['min_charuco_corners_for_pose']
    pose_error_gate = thresholds['max_mean_reprojection_error_px']
    quality = dict(min_pose_corners=PNP_MINIMUM_CORNERS if corner_minimum is None else int(corner_minimum),
                   min_pose_corners_source=('config' if corner_minimum is not None else
                                            'algorithmic PnP minimum; config value is null (inactive)'),
                   max_pose_error_px=None if pose_error_gate is None else float(pose_error_gate),
                   pose_gate_active=pose_error_gate is not None,
                   max_point_error_px=2.0, min_ray_angle_deg=2.0, contour_tolerance_px=3.0)
    rows = mapping_rows(mapping, plant_id)
    # Integrity first: resolve every mapped file and check bytes before anything is decoded or written.
    sources = []
    for row in rows:
        path = resolve(source, row['organized_path'], plant_id)
        actual = file_hash(path)
        if actual != row['sha256'].strip():
            raise StudyError(f'SHA-256 changed since the mapping was written: {path.name}')
        # A .heic name must really be an ISO container: renaming an extension is not decoding.
        if path.suffix.lower() in {'.heic', '.heif'}:
            with path.open('rb') as stream:
                if stream.read(12)[4:8] != b'ftyp':
                    raise StudyError(f'Not an ISO container despite its name: {path.name}')
        view_group(row['view_code'].strip())
        if row['view_code'].strip() in exclude_views:
            continue
        sources.append((row, path, actual))
    unknown = set(exclude_views) - {r['view_code'].strip() for r in rows}
    if unknown:
        raise StudyError(f'Excluded view codes are not in the mapping: {sorted(unknown)}')
    if any(path.suffix.lower() in {'.heic', '.heif'} for _, path, _ in sources):
        load_decoder(heif_runtime)
    from tools.leaf_light.phone import read_phone_image
    records = []
    for row, path, actual in sources:
        image, metadata = read_phone_image(path)
        records.append(dict(row=row, path=path, source_sha256=actual, image=image, metadata=metadata))
    profile = camera_profile(records, intrinsics, expected_camera)
    folder = output_dir(out)
    (folder / 'images').mkdir()
    frames, table = [], []
    for record in records:
        code = record['row']['view_code'].strip()
        group = view_group(code)
        name = f'{plant_id}_{record["row"].get("capture_date", "").strip().replace("-", "")}_{code}.png'.replace('__', '_')
        working = folder / 'images' / name
        record['image'].save(working, format='PNG', optimize=False)
        working_hash = file_hash(working)
        pixels = cv2.cvtColor(np.array(record['image']), cv2.COLOR_RGB2BGR)
        corner_pixels, corner_ids, _, _ = detector.detectBoard(cv2.cvtColor(pixels, cv2.COLOR_BGR2GRAY))
        ids = [] if corner_ids is None else [int(i) for i in np.asarray(corner_ids).reshape(-1)]
        pose = solve_pose(board, spec, ids, corner_pixels if ids else [], intrinsics, quality)
        frame = dict(image_file=name, view_code=code, observed_view_group=group,
                     nominal_polar_deg=NOMINAL_POLAR_DEG[group], azimuth_deg=None,
                     capture_protocol_note='View codes are capture labels from the input order, not measured angles.',
                     image_path=f'images/{name}', sha256=working_hash,
                     source_path=str(record['path']), source_sha256=record['source_sha256'],
                     source_orientation=record['metadata']['source_orientation'],
                     orientation_applied=record['metadata']['source_orientation'] != 1,
                     n_corners_detected=len(ids), **pose)
        frame['board_evidence'] = detect_evidence(pixels, frame, intrinsics, detector, board, spec)
        frame['n_markers_detected'] = frame['board_evidence']['n_markers_detected']
        frames.append(frame)
        table.append(dict(plant_id=plant_id, view_code=code, view_group=group, image_file=name,
                          source_path=str(record['path']), source_sha256=record['source_sha256'],
                          working_png_sha256=working_hash, source_orientation=frame['source_orientation'],
                          orientation_applied=frame['orientation_applied'],
                          image_width_px=record['metadata']['image_width_px'],
                          image_height_px=record['metadata']['image_height_px'],
                          n_markers_detected=frame['n_markers_detected'], n_corners_detected=len(ids),
                          pose_status=frame['pose_status'], reprojection_error_px=frame['reprojection_error_px'],
                          passes_pose_gate=frame['passes_pose_gate'], failure_reason=frame['failure_reason']))
        record['image'].close()
    session = session_id or f'{plant_id}_{rows[0].get("capture_date", "").strip().replace("-", "")}'
    capture = dict(schema_version='diagnostic-preview-capture-1', validated_metric=False,
                   plant_id=plant_id, session_id=session, intrinsics=intrinsics,
                   intrinsics_path=str(intrinsics_path), intrinsics_sha256=file_hash(intrinsics_path),
                   quality=quality, board_variant_id=spec.variant_id,
                   board_spec_path=str(settings.board_spec_path), board_spec_sha256=file_hash(settings.board_spec_path),
                   board_variant_evidence=board_variant_evidence(spec, frames, session_evidence),
                   camera_profile=profile,
                   board_evidence_provenance='Detected with the configured board from the decoded working PNGs.',
                   coordinate_frame='board; origin inner corner 0; +Z away from the board surface; millimetres',
                   notice=('Diagnostic capture from measured ChArUco detections with reused unvalidated trial '
                           'intrinsics. Poses that fail the gate are kept and flagged; no dimension is validated.'))
    capture['frames'] = frames
    write_json(folder / 'capture.json', capture)
    write_rows(folder / 'import_table.csv', table, IMPORT_COLUMNS)
    solved = [f for f in frames if f['pose_status'] == 'solved']
    report = dict(schema_version='organized-capture-import-1', plant_id=plant_id, session_id=session,
                  excluded_views=[dict(view_code=c, reason=r) for c, r in sorted(exclude_views.items())],
                  source=str(source), mapping=str(mapping), mapping_sha256=file_hash(mapping),
                  photo_count=len(frames), solved_pose_count=len(solved),
                  # With an inactive gate, 'accepted' is not measurable: report unavailable, never 0-as-fact.
                  accepted_pose_count=(sum(f['passes_pose_gate'] is True for f in frames)
                                       if quality['pose_gate_active'] else None),
                  pose_by_view_group={group: dict(total=sum(f['observed_view_group'] == group for f in frames),
                                                  solved=sum(f['observed_view_group'] == group and f['pose_status'] == 'solved' for f in frames))
                                      for group in VIEW_GROUPS},
                  reprojection_error_px=dict(
                      min=min([f['reprojection_error_px'] for f in solved], default=None),
                      max=max([f['reprojection_error_px'] for f in solved], default=None)),
                  quality=quality, camera_profile=profile,
                  board_variant_id=spec.variant_id, intrinsics_sha256=capture['intrinsics_sha256'],
                  sources_modified=False, validated_metric=False, suitable_for_ppfd=False, deep_learning_run=False,
                  decoded_with='pillow-heif (vendored runtime allowed via --heif-runtime)',
                  note='Side views are expected to fail while the board is out of focus or nearly edge-on; '
                       'that is a capture limitation, not a threshold to relax.')
    write_json(folder / 'import_report.json', report)
    write_summary(folder, report, table)
    return report


def write_summary(folder: Path, report: dict, table: list[dict]) -> None:
    rows = ''.join(
        '<tr><td>' + escape(r['view_code']) + '</td><td>' + escape(r['view_group']) + '</td><td>' +
        str(r['n_markers_detected']) + '</td><td>' + str(r['n_corners_detected']) + '</td><td>' +
        escape({'solved': '계산됨', 'too_few_corners': '보드 점 부족', 'failed': '계산 실패'}.get(r['pose_status'], r['pose_status'])) +
        '</td><td>' + ('–' if r['reprojection_error_px'] is None else f"{r['reprojection_error_px']:.2f}") +
        '</td><td>' + ('기준 없음' if r['passes_pose_gate'] is None else '통과' if r['passes_pose_gate'] else '미통과') +
        '</td></tr>' for r in table)
    groups = report['pose_by_view_group']
    (folder / 'index.html').write_text(
        '<!doctype html><meta charset="utf-8"><title>새 촬영 불러오기 결과</title>'
        '<style>body{font:17px sans-serif;max-width:940px;margin:40px auto;padding:20px;background:#10231a;color:#e4f0e8}'
        'td,th{padding:8px;border:1px solid #567}table{border-collapse:collapse}a{color:#91e1b2}</style>'
        f'<h1>{escape(report["plant_id"])} · 사진 {report["photo_count"]}장 불러오기</h1>'
        f'<p>촬영 위치가 계산된 사진: <b>{report["solved_pose_count"]}장</b> · '
        + ('기준 미설정(비활성)' if report['accepted_pose_count'] is None
           else f'{report["quality"]["max_pose_error_px"]}px 기준 통과: {report["accepted_pose_count"]}장') + ' · '
        '모든 값은 미검증 시험값입니다.</p>'
        f'<p>시점별: 상면 {groups["top"]["solved"]}/{groups["top"]["total"]} · '
        f'측면 {groups["side"]["solved"]}/{groups["side"]["total"]} · 사선 {groups["oblique"]["solved"]}/{groups["oblique"]["total"]}</p>'
        '<p>측면 사진은 보드가 초점 밖이거나 거의 수평이어서 대부분 위치를 계산하지 못했습니다. 기준을 낮추지 않았습니다. '
        '측면 각도가 필요하면 보드가 또렷하게 보이도록 다시 촬영해야 합니다.</p>'
        '<p><a href="capture.json">capture.json</a> · <a href="import_table.csv">사진별 표</a> · '
        '<a href="import_report.json">처리 기록</a></p>'
        '<table><tr><th>코드</th><th>시점</th><th>마커</th><th>보드 점</th><th>위치 계산</th><th>재투영 px</th><th>기준</th></tr>'
        + rows + '</table>', encoding='utf-8')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    for name in ('source', 'mapping', 'intrinsics', 'out'):
        parser.add_argument('--' + name, type=Path, required=True)
    parser.add_argument('--plant', required=True)
    parser.add_argument('--session-id')
    parser.add_argument('--heif-runtime', type=Path, help='Directory holding a vendored pillow-heif, if it is not installed')
    parser.add_argument('--expect-camera-model', help='Refuse photographs whose EXIF model differs from this')
    parser.add_argument('--expect-lens-model', help='Refuse photographs whose EXIF lens differs from this')
    parser.add_argument('--expect-focal-length-mm', help='Refuse photographs whose EXIF focal length differs from this')
    parser.add_argument('--board-caption', help='Printed board caption actually read in THIS session\'s photographs')
    parser.add_argument('--board-caption-source', help='Where that caption was read, e.g. "top view 03, read by <name>"')
    parser.add_argument('--board-observed-by', help='Who read it')
    parser.add_argument('--board-observed-at', help='When it was read, ISO date')
    parser.add_argument('--exclude-view', action='append', default=[], metavar='CODE=REASON',
                        help='Leave one mapped photo out (hash-checked, not decoded), with a written reason')
    parser.add_argument('--board-confirmed-by-user', action='store_true',
                        help='Only when the user stated in writing which printed board was used')
    args = parser.parse_args()
    if args.board_caption and not (args.board_caption_source and args.board_observed_by):
        parser.error('--board-caption needs --board-caption-source and --board-observed-by')
    expected = dict(model=args.expect_camera_model, lens_model=args.expect_lens_model,
                    focal_length_mm=args.expect_focal_length_mm)
    evidence = dict(caption=args.board_caption, source=args.board_caption_source, observed_by=args.board_observed_by,
                    observed_at=args.board_observed_at, confirmed_by_user=args.board_confirmed_by_user)
    report = import_capture(args.source, args.mapping, args.plant, args.intrinsics, args.out,
                            args.session_id, args.heif_runtime,
                            {k: v for k, v in expected.items() if v},
                            evidence if (args.board_caption or args.board_confirmed_by_user) else None,
                            dict(item.split('=', 1) for item in args.exclude_view))
    print(json.dumps({k: report[k] for k in ('plant_id', 'photo_count', 'solved_pose_count',
                                             'accepted_pose_count', 'validated_metric')}))


if __name__ == '__main__':
    main()
