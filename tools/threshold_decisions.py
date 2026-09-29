"""Collect human review decisions with the rule scores they were made against (threshold-decision-log-1).

Thresholds for later automation are fitted to these rows, never guessed. Every row is one human
decision: which rule flagged or scored the object, that rule's version and score at decision time,
what the person decided, and where the object lives. Nothing here changes a label or a threshold.

Sources
  --review-dir   JSON documents exported from a review page's database (one file per decision)
  --backup       editor backups; reads membership.decision_log
  --mask-batch   a leaflet mask batch folder (read-only); final review states are turned into
                 decisions, and the default-versus-final mask agreement is recomputed from the
                 cached model scores

  python -m tools.threshold_decisions --review-dir build/threshold_decisions_20260922/review_page_db/decisions \\
      --backup <editor backup.json> --mask-batch build/leaflet_mask_batch_20260922/dwt_02 \\
      --out build/threshold_decisions_20260922/collected
"""
from __future__ import annotations

import argparse
import csv
import json
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np
from scipy import ndimage

from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json

SCHEMA = 'threshold-decision-log-1'
COLUMNS = ('decision_id', 'source', 'rule_id', 'rule_version', 'score_name', 'score_value', 'decision', 'plant_id',
           'session_id', 'image_file', 'object_id', 'reviewer', 'decided_at', 'scores_json', 'decision_detail_json',
           'record_ref')
#: Below this many decisions of every kind a rule stays fully human-reviewed (no automatic band).
MIN_DECISIONS_PER_CLASS = 30
#: Final states of the mask batch; 'edited' and 'unreviewed' are still open and are not decisions.
FINAL_MASK_STATES = ('accepted', 'rejected', 'deferred')
MASK_RULE_VERSION = 1


def _row(entry: dict, record_ref: str) -> dict:
    if entry.get('schema_version') != SCHEMA:
        raise StudyError(f'Not a {SCHEMA} record: {record_ref}')
    for key in ('rule_id', 'decision'):
        if not entry.get(key):
            raise StudyError(f'Decision record without {key}: {record_ref}')
    return dict(decision_id=entry.get('decision_id') or entry.get('object_id'), source=entry.get('source'),
                rule_id=entry['rule_id'], rule_version=entry.get('rule_version'), score_name=entry.get('score_name'),
                score_value=entry.get('score_value'), decision=entry['decision'], plant_id=entry.get('plant_id'),
                session_id=entry.get('session_id'), image_file=entry.get('image_file'), object_id=entry.get('object_id'),
                reviewer=entry.get('reviewer'), decided_at=entry.get('decided_at') or entry.get('at'),
                scores_json=json.dumps(entry.get('scores') or {}, ensure_ascii=False, sort_keys=True),
                decision_detail_json=json.dumps(entry.get('decision_detail') or {}, ensure_ascii=False, sort_keys=True),
                record_ref=record_ref)


def from_review_dir(folder: Path) -> list[dict]:
    rows = []
    for path in sorted(Path(folder).glob('*.json')):
        doc = read_json(path)
        rows.append(_row(doc, f'{path.name}#sha256={file_hash(path)[:12]}'))
    return rows


def from_backup(path: Path) -> list[dict]:
    backup = read_json(path)
    rows = []
    for variant, state in (backup.get('variants') or {}).items():
        for i, entry in enumerate(((state.get('membership') or {}).get('decision_log') or [])):
            rows.append(_row(entry, f'{Path(path).name}:{variant}:decision_log[{i}]'))
    return rows


def _mask_shape(mask: np.ndarray) -> dict:
    labels, pieces = ndimage.label(mask)
    filled = ndimage.binary_fill_holes(mask)
    return dict(area_px=int(mask.sum()), pieces=int(pieces), hole_px=int((filled & ~mask).sum()))


def from_mask_batch(folder: Path) -> list[dict]:
    """Final mask reviews as decisions; scores describe the DEFAULT mask the reviewer was shown."""
    from tools import leaflet_mask_batch as batch_tool
    folder = Path(folder)
    batch = batch_tool.Batch(folder)
    manifest = batch.manifest
    rows = []
    for identity in manifest['ids']:
        item = batch.item(identity)
        if item['review'] not in FINAL_MASK_STATES or item['generation'] != 'ready':
            continue
        meta = read_json(folder / 'cache' / item['cache_key'] / 'result.json')
        default_sensitivity = float(meta.get('sensitivity', batch_tool.DEFAULT_SENSITIVITY))
        default = batch.mask(dict(item, manual_rings=None), meta['default_candidate'], default_sensitivity)[0]
        final = batch.mask(item)[0]
        union = int((default | final).sum())
        box = item['source_bbox_xywh_px']
        shape = _mask_shape(default)
        iou = float((default & final).sum() / union) if union else None
        decision = item['review'] if item['review'] != 'accepted' else ('accepted_unchanged' if not item['changed'] else 'accepted_edited')
        scores = dict(default_fill_ratio=shape['area_px'] / (box[2] * box[3]), default_pieces=shape['pieces'],
                      default_hole_px=shape['hole_px'], default_candidate=meta['default_candidate'],
                      default_sensitivity=default_sensitivity, candidate_scores=meta.get('scores'),
                      final_candidate=item['selected_candidate'], final_sensitivity=item['sensitivity'],
                      manual_contour=item['manual_rings'] is not None, iou_default_vs_final=iou,
                      risk=meta.get('risk'), review_seconds=item.get('review_seconds'), edit_seconds=item.get('edit_seconds'))
        last = next((h for h in reversed(item.get('history') or []) if h.get('action') in ('accept', 'reject', 'defer')), {})
        rows.append(_row(dict(schema_version=SCHEMA, decision_id=f'{identity}@r{item["revision"]}',
                              source='leaflet_mask_batch', rule_id='mask_default_threshold', rule_version=MASK_RULE_VERSION,
                              score_name='default_fill_ratio', score_value=scores['default_fill_ratio'], scores=scores,
                              decision=decision, decision_detail=dict(history=item.get('history')), plant_id=item['plant_id'],
                              session_id=Path(manifest['session']).parent.name, image_file=item['image_file'],
                              object_id=identity, reviewer=None, decided_at=last.get('at')),
                         f'{folder.name}/items/{identity}.json#revision={item["revision"]}'))
    return rows


def summarise(rows: list[dict]) -> dict:
    by_rule = defaultdict(list)
    for row in rows:
        by_rule[(row['rule_id'], row['rule_version'])].append(row)
    rules = []
    for (rule, version), group in sorted(by_rule.items(), key=lambda kv: (kv[0][0], str(kv[0][1]))):
        counts = Counter(r['decision'] for r in group)
        plants = Counter(r['plant_id'] for r in group)
        short = {k: v for k, v in counts.items() if v < MIN_DECISIONS_PER_CLASS}
        rules.append(dict(rule_id=rule, rule_version=version, decisions=len(group), by_decision=dict(counts),
                          by_plant=dict(plants), ready_to_fit=not short and len(counts) >= 2 and len(plants) >= 2,
                          not_ready_because=(['fewer than %d decisions of: %s' % (MIN_DECISIONS_PER_CLASS, ', '.join(sorted(short)))] if short else []) +
                                            (['only one decision kind'] if len(counts) < 2 else []) +
                                            (['decisions from one plant only (thresholds must be checked on another plant)'] if len(plants) < 2 else [])))
    return dict(schema_version='threshold-decision-summary-1', total=len(rows), rules=rules,
                min_decisions_per_class=MIN_DECISIONS_PER_CLASS,
                notice='Counts only. No threshold is fitted or changed here; a rule without enough decisions stays fully human-reviewed.')


def collect(out: Path, review_dirs=(), backups=(), mask_batches=()) -> dict:
    rows = []
    for folder in review_dirs:
        rows += from_review_dir(folder)
    for path in backups:
        rows += from_backup(path)
    for folder in mask_batches:
        rows += from_mask_batch(folder)
    ids = Counter(r['decision_id'] for r in rows)
    duplicated = [k for k, n in ids.items() if n > 1]
    if duplicated:
        raise StudyError(f'Duplicate decision ids across sources: {duplicated[:5]}')
    folder = output_dir(out)
    with open(folder / 'decisions.csv', 'w', newline='', encoding='utf-8') as handle:
        writer = csv.DictWriter(handle, fieldnames=COLUMNS)
        writer.writeheader(); writer.writerows(rows)
    summary = summarise(rows)
    summary['sources'] = dict(review_dirs=[str(p) for p in review_dirs], backups=[str(p) for p in backups],
                              mask_batches=[str(p) for p in mask_batches])
    write_json(folder / 'summary.json', summary)
    return summary


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument('--review-dir', type=Path, action='append', default=[])
    parser.add_argument('--backup', type=Path, action='append', default=[])
    parser.add_argument('--mask-batch', type=Path, action='append', default=[])
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    summary = collect(args.out, args.review_dir, args.backup, args.mask_batch)
    print(json.dumps({k: summary[k] for k in ('total', 'rules')}, ensure_ascii=False))


if __name__ == '__main__':
    main()
