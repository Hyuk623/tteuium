"""Build diagnostic SAM-clipped patches from existing multi-view point depths.

python -m tools.sam_supported_leaf_patches --result build/.../result
  --segmenter-config build/.../sam2_config.json --out build/.../sam_patches

Runs explicitly requested segmentation inference, never training or pose estimation.
SAM contours constrain existing landmark interpolation; they are not correspondences.
"""
from __future__ import annotations

import argparse
import json
from collections import defaultdict
from html import escape
from pathlib import Path
import time

import numpy as np

from tools.export_leaflet_training import region_mask
from tools.leaflet_segmenter import load_segmenter, propose
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, rows, write_json
from tools.visible_leaf_patch import build_patch


def write_combined(folder: Path, records: list[dict]) -> None:
    """Reuse the patch viewer; retain separate leaves in one measured board frame."""
    patches = [(r, read_json(folder / Path(r['url']).parent / 'patch.json')) for r in records
               if r['status'] == 'diagnostic_partial_patch']
    if not patches:
        return
    combined = dict(leaflet_id='SAM 부분 면 모음', vertices_mm=[], faces=[], physical_landmarks=[],
                    source_images=[], proposed_faces=0, retained_faces=0, components=[],
                    coordinate_frame='board', validated_metric=False, suitable_for_ppfd=False,
                    complete_leaf=False, complete_plant=False, interpolation_vertices_are_observations=False)
    photos = []
    for record, patch in patches:
        offset = len(combined['vertices_mm'])
        combined['components'].append(dict(organ_id=record['organ_id'], leaflet_id=record['leaflet_id'],
            first_face=len(combined['faces']), face_count=len(patch['faces']), source_patch=record['url']))
        combined['vertices_mm'].extend(patch['vertices_mm'])
        combined['faces'].extend([[i+offset for i in face] for face in patch['faces']])
        combined['physical_landmarks'].extend([dict(p, point_id=record['organ_id']+'/'+record['leaflet_id']+'/'+p['point_id'])
                                               for p in patch['physical_landmarks']])
        combined['source_images'].extend(patch['source_images'])
        combined['proposed_faces'] += patch['proposed_faces']
        combined['retained_faces'] += patch['retained_faces']
        photos.append(f'<figure><a href="{record["url"]}">{escape(record["organ_id"]+"/"+record["leaflet_id"])} · 개별 3D와 사진</a></figure>')
    combined['source_images'] = sorted(set(combined['source_images']))
    write_json(folder/'combined_patch.json', combined)
    with (folder/'combined_patch_mm.ply').open('w', encoding='ascii') as stream:
        stream.write(f'ply\nformat ascii 1.0\ncomment unvalidated separate leaf patches in board mm\nelement vertex {len(combined["vertices_mm"])}\nproperty float x\nproperty float y\nproperty float z\nelement face {len(combined["faces"])}\nproperty list uchar int vertex_indices\nend_header\n')
        for point in combined['vertices_mm']:
            stream.write(' '.join(map(str, point))+'\n')
        for face in combined['faces']:
            stream.write('3 '+' '.join(map(str, face))+'\n')
    template = Path(__file__).with_name('visible_leaf_patch.html').read_text(encoding='utf-8')
    page = template.replace('__PATCH__', json.dumps(combined, ensure_ascii=True).replace('<','\\u003c'))
    page = page.replace('__PHOTOS__',''.join(photos)).replace('href="patch.json"','href="combined_patch.json"')
    page = page.replace('href="visible_patch_mm.ply"','href="combined_patch_mm.ply"')
    page = page.replace('확인한 대응점', '기존 미검증 대응점').replace('물리적 대응점', '대응점 후보')
    (folder/'combined.html').write_text(page,encoding='utf-8')


def choose_candidate(candidates: list[dict], xy_px: np.ndarray, size: tuple[int, int]) -> dict:
    """Prefer observation support, then model score; no human acceptance implied."""
    ranked = []
    for candidate in candidates:
        mask = region_mask(candidate['rings'], *size)
        pixel = np.rint(xy_px).astype(int)
        valid = ((pixel >= 0).all(axis=1) & (pixel[:, 0] < size[0]) & (pixel[:, 1] < size[1]))
        count = int(mask[pixel[valid, 1], pixel[valid, 0]].sum())
        ranked.append((count, candidate.get('score') or 0, candidate))
    if not ranked:
        raise StudyError('No segmentation candidates')
    count, _, chosen = max(ranked, key=lambda item: item[:2])
    return dict(chosen, observed_points_inside=count, observed_points_total=len(xy_px),
                selection_method='maximum saved-point containment then model score', human_review='pending')


def build(result: Path, segmenter_config: Path, out: Path) -> dict:
    result = result.resolve()
    capture = read_json(result / 'capture.json')
    depths = rows(result / 'editor_point_depths.csv')
    frames = {f['image_file']: f for f in capture['frames']}
    for frame in frames.values():
        source = Path(frame['image_path'])
        if not source.is_absolute():
            source = result / source
        frame['image_path'] = str(source.resolve())
        if file_hash(source) != frame['sha256']:
            raise StudyError('Source photograph changed')
    folder = output_dir(out)
    write_json(folder / 'capture.json', capture)
    model = load_segmenter('sam2', segmenter_config)
    grouped = defaultdict(list)
    for row in depths:
        grouped[(row['organ_id'], row['leaflet_id'])].append(row)
    records = []
    for index, ((organ, leaflet), observations) in enumerate(grouped.items()):
        record = dict(organ_id=organ, leaflet_id=leaflet, status='unavailable', views=[],
                      validated_metric=False, suitable_for_ppfd=False, human_review='pending')
        records.append(record)
        eligible = defaultdict(list)
        for row in observations:
            try:
                xyz = np.array([float(row[f'{axis}_board_mm']) for axis in 'xyz'])
                xy = np.array([float(row['x_px']), float(row['y_px'])])
            except (ValueError, TypeError):
                continue
            if np.isfinite(xyz).all() and np.isfinite(xy).all() and frames[row['image_file']]['pose_status'] == 'solved':
                eligible[row['image_file']].append(row)
        eligible = {name: obs for name, obs in eligible.items() if len({r['point_id'] for r in obs}) >= 3}
        if len(eligible) < 2:
            record['reason'] = 'fewer_than_two_posed_views_with_three_existing_landmarks'
            continue
        selected_views = []
        for view_index, (name, obs) in enumerate(eligible.items()):
            frame = frames[name]
            xy = np.array([[float(r['x_px']), float(r['y_px'])] for r in obs])
            size = (capture['intrinsics']['image_width_px'], capture['intrinsics']['image_height_px'])
            # Existing sparse landmarks define a prompt only, never a new leaf identity.
            low, high = np.maximum(xy.min(axis=0)-1, 0), np.minimum(xy.max(axis=0)+2, size)
            prompt = dict(box_px=[*low, *high], positive_px=[], negative_px=[])
            start = time.perf_counter()
            try:
                proposal = propose(model, Path(frame['image_path']), frame['sha256'], prompt)
                chosen = choose_candidate(proposal['candidates'], xy, size)
                write_json(folder / f'proposal_{index}_{view_index}.json', dict(
                    **proposal, selected_candidate=chosen, image_file=name, image_sha256=frame['sha256']))
                outer = [r for r in chosen['rings'] if not r.get('is_hole')]
                selected_views.append(dict(image_file=name, label_image_size_px=list(size),
                    boundary_xy_px=outer[0]['points_px'], rings=chosen['rings'],
                    source='sam2_unreviewed', selected_candidate_index=chosen['candidate_index']))
                record['views'].append(dict(image_file=name, elapsed_seconds=time.perf_counter()-start,
                    candidate_index=chosen['candidate_index'], inside_points=chosen['observed_points_inside'],
                    total_points=len(xy)))
            except Exception as exc:
                record['views'].append(dict(image_file=name, error=str(exc)))
        annotation = dict(two_d_only_candidates=[dict(organ_id=organ, leaflet_id=leaflet,
            observations=selected_views, human_review='pending', source='sam2_unreviewed')])
        annotation_path = folder / f'regions_{index}.json'
        write_json(annotation_path, annotation)
        try:
            patch = build_patch(folder / 'capture.json', result / 'editor_point_depths.csv',
                                annotation_path, leaflet, folder / f'leaf_{index}')
            record.update(status='diagnostic_partial_patch', url=f'leaf_{index}/index.html',
                          faces=patch['retained_faces'], complete_leaf=False)
        except (StudyError, ValueError) as exc:
            record['reason'] = str(exc)
        write_json(folder / 'progress.json', dict(records=records))
        print(f'{organ}/{leaflet}: {record["status"]}', flush=True)
    report = dict(records=records, model=model.info(), source_result=str(result),
        depth_sha256=file_hash(result / 'editor_point_depths.csv'), inference_run=True, training_run=False,
        existing_labels_modified=False, validated_metric=False, suitable_for_ppfd=False,
        note='Existing triangulated landmark interpolation clipped to SAM draft masks. Not full-leaf reconstruction.')
    write_json(folder / 'report.json', report)
    write_combined(folder, records)
    links = []
    for record in records:
        label = escape(record['organ_id'] + '/' + record['leaflet_id'])
        if record['status'] == 'diagnostic_partial_patch':
            links.append(f'<li><a href="{record["url"]}">{label} · 부분 3D 보기</a> · 삼각형 {record["faces"]}개</li>')
        else:
            links.append(f'<li>{label} · 미복원: {escape(record.get("reason", "unavailable"))}</li>')
    (folder / 'index.html').write_text('<!doctype html><meta charset="utf-8"><title>SAM 기반 부분 3D</title>'
        '<style>body{background:#14241d;color:#eef5f0;font:18px system-ui;padding:28px}a{color:#8ee7ca}li{margin:18px}</style>'
        '<h1>SAM 윤곽으로 제한한 부분 3D</h1><p><a href="combined.html">복원된 부분 면을 한 3D 화면에서 보기</a></p><p>기존 대응점의 3D 위치를 보간하고 SAM 윤곽 안의 면만 남겼습니다. '
        '윤곽 꼭짓점끼리 대응시킨 결과가 아닙니다. 모든 결과는 미검증이며 전체 잎·PPFD용 모델이 아닙니다.</p>'
        '<p>사진: 초록 = 부분 면 재투영 / 분홍 = SAM 윤곽 / 노랑 = 기존 대응점</p><ul>'+''.join(links)+'</ul>', encoding='utf-8')
    return report


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('result', 'segmenter-config', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args()
    build(args.result, args.segmenter_config, args.out)


if __name__ == '__main__':
    main()
