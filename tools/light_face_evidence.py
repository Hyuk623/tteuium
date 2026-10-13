"""Expose actual two-side transport using separately reviewed biological identity."""
from __future__ import annotations

import math
from pathlib import Path

from tools.leaf_light.common import StudyError, file_hash

FACE_KEY = ('geometry_snapshot_id', 'plant_instance_id', 'session_id', 'organ_id', 'leaflet_id', 'triangle_id')
FACE_FIELDS = ('normal_biological_face', 'illuminated_faces', 'face_mapping_id', 'face_source_ref')


def classify_face(row: dict) -> None:
    """Classification only: never clip, divide, relabel or correct photon quantities."""
    normal = row.get('normal_biological_face')
    reasons = row.setdefault('_reasons', {})
    row['illuminated_faces'] = None
    if row.get('backend') != 'direct': reason = 'native_face_exposure_unavailable'
    elif normal not in ('adaxial', 'abaxial'): reason = 'biological_face_mapping_unavailable'
    elif any(row.get(k) is None for k in ('normal_side_ppfd_umol_m2_s', 'opposite_side_ppfd_umol_m2_s')):
        reason = 'face_exposure_unavailable'
    else:
        a, b = row['normal_side_ppfd_umol_m2_s'], row['opposite_side_ppfd_umol_m2_s']
        if any(not math.isfinite(v) or v < 0 for v in (a, b)): raise StudyError('invalid_face_photon_contribution')
        if a > 0 and b > 0: row['illuminated_faces'] = 'both'
        elif a > 0: row['illuminated_faces'] = normal+'_only'
        elif b > 0: row['illuminated_faces'] = ('abaxial' if normal == 'adaxial' else 'adaxial')+'_only'
        reason = 'no_positive_face_exposure' if row['illuminated_faces'] is None else None
    if reason: reasons['illuminated_faces'] = reason
    else: reasons.pop('illuminated_faces', None)
    for field in ('normal_biological_face', 'face_mapping_id', 'face_source_ref'):
        if row.get(field) is None:
            row[field] = None; reasons[field] = 'biological_face_mapping_unavailable'
        else: reasons.pop(field, None)


def bind_face_mappings(raw: list[dict], base: Path, rows: list[dict], geometry_hashes: dict,
                       sources: dict) -> dict:
    """One reviewed mapping per original triangle/instance/snapshot, never by lamp."""
    actual = {tuple(r[k] for k in FACE_KEY) for r in rows if r['backend'] == 'direct'}
    lookup = {}; records = {}; ids = set()
    for item in raw:
        key = tuple(item[k] for k in FACE_KEY)
        mid = item.get('mapping_id')
        if not isinstance(mid, str) or not mid or '#' in mid or mid in ids or key in lookup:
            raise StudyError('duplicate_or_invalid_face_mapping')
        if key not in actual: raise StudyError('unknown_face_mapping_surface')
        if item.get('review_status') != 'reviewed' or not item.get('reviewer'):
            raise StudyError('reviewed_biological_face_mapping_required')
        if item.get('normal_biological_face') not in ('adaxial', 'abaxial'):
            raise StudyError('invalid_normal_biological_face')
        if item.get('geometry_sha256') != geometry_hashes.get(key[0]):
            raise StudyError('stale_face_mapping_geometry')
        path = (base/item['evidence_path']).resolve()
        sha = file_hash(path)
        if sha != item.get('evidence_sha256'): raise StudyError('stale_face_mapping_evidence')
        sources[str(path)] = sha
        normalized = dict(item, evidence_path=str(path))
        ids.add(mid); records[mid] = normalized; lookup[key] = normalized
    for row in rows:
        item = lookup.get(tuple(row[k] for k in FACE_KEY)) if row['backend'] == 'direct' else None
        if item:
            row.update(normal_biological_face=item['normal_biological_face'], face_mapping_id=item['mapping_id'],
                       face_source_ref='face_mappings.json#'+item['mapping_id'])
        classify_face(row)
    return dict(schema_version='biological-face-evidence-1', mappings=records,
                missing_mapping='unavailable', transport='unaltered_normal_and_opposite_side_photons')
