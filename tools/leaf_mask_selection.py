"""Read reviewed exclusions without changing original leaf annotations or masks."""
from __future__ import annotations

from pathlib import Path

from tools.leaf_light.common import StudyError, file_hash, read_json


def load_selection(path: Path | None, batch, capture: dict, track) -> dict:
    """Bind each exclusion to its original batch item, photograph and review evidence."""
    if path is None:
        return dict(policy_hash='all_ready_not_rejected', excluded={})
    path = Path(path).resolve()
    policy = read_json(track(path))
    if policy.get('schema') != 'observed-leaf-selection-1':
        raise StudyError('Unsupported observed leaf selection')
    if (policy.get('plant_id') != batch.manifest['plant_id'] or
            policy.get('session_id') != capture.get('session_id')):
        raise StudyError('Leaf selection plant/session mismatch')
    if policy.get('origin') != 'observed_annotation_review':
        raise StudyError('Leaf selection requires observed annotation review')
    evidence = policy.get('evidence', {})
    if not evidence.get('path') or not evidence.get('sha256'):
        raise StudyError('Hashed review evidence required')
    source = Path(evidence['path'])
    track(source if source.is_absolute() else path.parent/source, evidence['sha256'])
    entries = policy.get('excluded_items')
    if not isinstance(entries, list):
        raise StudyError('Explicit excluded item list required')
    excluded = {}
    for entry in entries:
        key = entry.get('item_id')
        if key not in batch.manifest['ids'] or key in excluded:
            raise StudyError('Unknown or duplicate excluded leaf item')
        if not entry.get('reason') or not entry.get('item_sha256'):
            raise StudyError('Exclusion reason and item hash required')
        item_path = batch.root/'items'/f'{key}.json'
        item = read_json(track(item_path, entry['item_sha256']))
        if (entry.get('image_file') != item['image_file'] or
                not entry.get('image_sha256') or entry['image_sha256'] != item['image_sha256']):
            raise StudyError('Leaf exclusion image identity mismatch')
        image = (batch.session/item['image_path']).resolve()
        if not image.is_relative_to(batch.session.resolve()):
            raise StudyError('Excluded image outside original session')
        track(image, entry['image_sha256'])
        excluded[key] = entry['reason']
    return dict(policy_hash=file_hash(path), excluded=excluded)
