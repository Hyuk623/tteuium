"""Generate unreviewed venation evidence using the existing fixed-mask web algorithm.

python -m tools.leaf_vein_batch --run build/RUN --sigma 2
"""
from __future__ import annotations

import argparse
import csv
import html
import time
from pathlib import Path

import numpy as np
from PIL import Image

from tools.leaf_preprocess_lab import Lab, sha, write_json
from tools.midrib_review import propose, parse_options


def generate(run: Path, sigma: float = 2.0) -> dict:
    app = Lab(run)
    cfg = parse_options(dict(sigma_px=sigma, channel='original_l', polarity='bright'))
    out = app.root / 'veins'
    out.mkdir(exist_ok=False)
    started = time.perf_counter()
    changed = [p for p, digest in app.doc['sources'].items() if sha(Path(p)) != digest]
    if changed:
        raise ValueError(f'Frozen sources changed: {changed}')
    rows, cards = [], []
    for sid, obs in app.samples.items():
        tick = time.perf_counter()
        row = dict(sample_id=sid, annotation_id=obs['source_annotation_id'], plant_id=obs['plant_id'],
                   image_file=obs['image_file'], status='failed', usable_percent=None, reason='')
        try:
            rgb, mask = app.load(sid)
            result = propose(rgb, mask, rgb, [], obs['crop_xyxy_px'], cfg)
            valid, evidence = result.pop('valid'), result.pop('evidence')
            status = ('unavailable' if not valid.any() or result['ridge_normalization_scale'] <= 1e-8
                      else 'candidate_evidence')
            reason = ('no_valid_interior' if not valid.any() else 'no_ridge_response') if status == 'unavailable' else ''
            overlay = rgb.copy()
            overlay[mask & ~valid] = np.rint(.6*overlay[mask & ~valid]+.4*np.array([110,70,160])).astype(np.uint8)
            alpha = evidence[..., None]*.7
            overlay = np.rint(overlay*(1-alpha)+np.array([255,120,0])*alpha).astype(np.uint8)
            panel = np.concatenate([rgb, overlay], axis=1)
            Image.fromarray(panel).save(out/f'{sid}.png')
            # Continuous responses, no invented segmentation threshold or vein graph.
            np.savez_compressed(out/f'{sid}.npz', evidence=evidence, valid=valid)
            write_json(out/f'{sid}.json', dict(schema='leaf-vein-evidence-1', observation=obs, options=cfg,
                       status=status, reason=reason, review='unreviewed', anchors_original_px=[],
                       coordinate_frame='crop pixel grid; add observation.crop_xyxy_px[:2] for original pixels',
                       usable_percent=result['usable_percent'], support_radius_px=result['support_radius_px'],
                       ridge_normalization_scale=result['ridge_normalization_scale'],
                       main_vein_identified=False, validated_metric=False, suitable_for_ppfd=False))
            row.update(status=status, usable_percent=result['usable_percent'], reason=reason)
            image = f'<img loading="lazy" src="/veins/{html.escape(sid)}.png" alt="원본과 잎맥 후보">'
        except (ValueError, OSError, KeyError) as exc:
            row['reason'] = str(exc)
            image = '<p>생성 실패 — 원인 기록을 확인하세요.</p>'
        row['seconds'] = time.perf_counter()-tick
        rows.append(row)
        title = html.escape(f"라벨 {row['annotation_id']} · {row['image_file']}")
        cards.append(f'<article><h2>{title}</h2>{image}<p>{html.escape(row["status"])} · '
                     f'유효 영역 {row["usable_percent"] if row["usable_percent"] is not None else "미산출"}%</p>'
                     f'<a href="/?annotation={row["annotation_id"]}">이 잎을 비교 화면에서 열기</a></article>')
    with (out/'summary.csv').open('w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=list(rows[0]))
        writer.writeheader(); writer.writerows(rows)
    changed = [p for p, digest in app.doc['sources'].items() if sha(Path(p)) != digest]
    manifest = dict(schema='leaf-vein-batch-1', options=cfg, observations=len(rows),
                    counts={s: sum(r['status']==s for r in rows) for s in ('candidate_evidence','unavailable','failed')},
                    seconds=time.perf_counter()-started, dataset_sha256=app.dataset_hash,
                    source_hashes_checked=len(app.doc['sources']), changed_sources=changed,
                    source_verification_passed=not changed,
                    tool_sha256=sha(Path(__file__)), helper_sha256=sha(Path(__file__).with_name('midrib_review.py')),
                    ridge_helper_sha256=sha(Path(__file__).with_name('midrib_flow.py')),
                    inference_run=False, training_run=False, main_vein_identified=False,
                    independent_vein_accuracy=None, validated_metric=False, suitable_for_ppfd=False)
    write_json(out/'manifest.json', manifest)
    (out/'index.html').write_text('<!doctype html><html lang="ko"><meta charset="utf-8"><title>소엽 잎맥 후보</title>'
        '<style>body{font-family:sans-serif;background:#eef3f1;color:#18342a;margin:24px}article{background:white;'
        'padding:18px;margin:18px 0;border-radius:12px}img{max-width:100%;height:auto}h2{font-size:17px}</style>'
        f'<h1>잎맥 후보 · {len(rows)}개 사진별 라벨</h1><p>왼쪽: 원본 · 오른쪽: 주황색 선 후보, 보라색 분석 제외 영역</p>'
        f'<p>Gaussian σ={cfg["sigma_px"]} px · 원본 밝기 · 주변보다 밝은 선. 주름·반사광이 섞일 수 있습니다. '
        '주맥 판정이나 3D 복원 결과가 아닙니다. 모든 항목은 미검토입니다.</p>'+''.join(cards)+'</html>', encoding='utf-8')
    if changed:
        raise ValueError('Sources changed during batch; outputs are not verified')
    return manifest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run', type=Path, required=True)
    parser.add_argument('--sigma', type=float, default=2)
    args = parser.parse_args()
    import json
    print(json.dumps(generate(args.run, args.sigma)))


if __name__ == '__main__':
    main()
