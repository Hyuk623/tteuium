"""Light consumer bridge; all transport remains in the existing core solver.

Run ``python -m tools.light_growth_bridge --help``. Direct angular outputs use the
same-call core diagnostic stream; native angular data remain unavailable.
"""
from __future__ import annotations

import argparse
from collections import defaultdict
from copy import deepcopy
from datetime import datetime, timedelta, timezone
import json
import math
import shutil
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from tomato3d.light.frames import board_to_grow_mm
from tools.compound_growth import aware_time, axis_traits
from tools.light_time import _schedules, _fraction, schedule_boundaries, photon_integral
from tools.light_reference_channel import (CAPABILITY as REFERENCE_CAPABILITY, reference_mapping,
                                           load_attachment, copy_attachment)
from tools.light_face_evidence import classify_face, bind_face_mappings
from tools.light_geometry_evidence import VERSION as GEOMETRY_EVIDENCE_VERSION, snapshot_evidence
from tools.leaf_light.common import (DLI_UNIT, StudyError, digest, file_hash, output_dir,
                                     read_json, write_json, write_rows)

SCHEMA_PATH = Path(__file__).with_name('light_growth_schema.json')
SCHEMA = read_json(SCHEMA_PATH)
POLICY = SCHEMA['numerical_policy']
ATOL = POLICY['absolute_tolerance']
RTOL = POLICY['relative_tolerance']
DTOL = POLICY['direction_degeneracy_tolerance']
ALL = '__all__'
UNASSIGNED = '__unassigned__'
PPFD = ('normal_side_ppfd_umol_m2_s', 'opposite_side_ppfd_umol_m2_s',
        'received_ppfd_umol_m2_s', 'absorbed_ppfd_umol_m2_s')
SECOND = ('xx', 'xy', 'xz', 'yy', 'yz', 'zz')
SECOND_INDEX = ((0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2))
ARRIVAL = ('arrival_flux_umol_s', *(f'arrival_M_{a}_umol_s' for a in 'xyz'),
           *(f'arrival_B_{a}_umol_s' for a in SECOND))


def _angular_samples(rows: list[dict], rotation: Any = None) -> dict:
    """Reduce actual unnormalized sample moments, then rotate and normalize once."""
    if any(r.get('backend') != 'direct' or any(r.get(k) is None for k in ARRIVAL) for r in rows):
        return {**{c['name']: None for c in SCHEMA['tables']['compound_light_features.csv']['columns']
                   if c['name'].startswith(('arrival_', 'mean_arrival_', 'dominant_arrival_', 'angular_second_'))
                   or c['name'] == 'directionality'}, 'direction_reason': 'required_angular_contribution_unavailable'}
    raw = [math.fsum(r[k] for r in rows) for k in ARRIVAL]
    b = np.zeros((3, 3))
    for v, (i, j) in zip(raw[4:], SECOND_INDEX): b[i, j] = b[j, i] = v
    return transform_moments(raw[0], raw[1:4], b, np.eye(3) if rotation is None else rotation)


def numeric(value: Any) -> float | None:
    """Missing is explicit; non-finite or malformed numbers are errors."""
    if value is None or value == 'unavailable':
        return None
    if isinstance(value, bool):
        raise StudyError('boolean_is_not_numeric')
    try:
        result = float(value)
    except (ValueError, TypeError) as exc:
        raise StudyError('invalid_numeric_value') from exc
    if not math.isfinite(result):
        raise StudyError('nonfinite_numeric_value')
    return result


def nonnegative(value: Any, label: str) -> float | None:
    result = numeric(value)
    if result is not None and result < 0:
        raise StudyError('negative_' + label)
    return result


def strict_sum(values: list[float | None]) -> float | None:
    return math.fsum(values) if values and all(v is not None for v in values) else None


def _close(a: Any, b: Any) -> bool:
    return bool(np.allclose(a, b, atol=ATOL, rtol=RTOL))


def _observed_at(snapshot: dict, instance_id: str) -> str:
    value = snapshot.get('observed_at_by_instance', {}).get(instance_id, snapshot.get('observed_at'))
    if value is None:
        return UNASSIGNED
    aware_time(value)
    return value


def rigid_transform(placement: dict) -> dict:
    """Derive matrices through the authoritative helper; never accept tilt/scale."""
    if set(placement) - {'plant_id', 'board_origin_grow_mm', 'board_yaw_deg', 'posture_since_capture'}:
        raise StudyError('unsupported_placement_component')
    origin = np.asarray(placement['board_origin_grow_mm']['value'], dtype=float)
    yaw = numeric(placement['board_yaw_deg']['value'])
    if origin.shape != (3,) or not np.isfinite(origin).all() or yaw is None:
        raise StudyError('unavailable_placement')
    transformed = board_to_grow_mm(np.vstack((np.zeros(3), np.eye(3))), origin, math.radians(yaw))
    rotation = (transformed[1:] - transformed[0]).T
    if not _close(rotation.T @ rotation, np.eye(3)) or not _close(np.linalg.det(rotation), 1):
        raise StudyError('nonrigid_transform')
    forward = np.eye(4); forward[:3, :3] = rotation; forward[:3, 3] = transformed[0]
    inverse = np.eye(4); inverse[:3, :3] = rotation.T; inverse[:3, 3] = -rotation.T @ transformed[0]
    if not _close(inverse @ forward, np.eye(4)):
        raise StudyError('transform_roundtrip_failed')
    return dict(transform_id=digest(placement), T_board_to_grow=forward.tolist(),
                T_grow_to_board=inverse.tolist(), coordinate_unit='mm',
                convention='column_vector', placement=deepcopy(placement))


def transform_moments(flux: float, first: Any, second: Any, rotation: Any) -> dict:
    r = np.asarray(rotation, dtype=float)
    m = np.asarray(first, dtype=float); b = np.asarray(second, dtype=float)
    if r.shape != (3, 3) or not _close(r.T @ r, np.eye(3)) or not _close(np.linalg.det(r), 1):
        raise StudyError('invalid_moment_rotation')
    if m.shape != (3,) or b.shape != (3, 3) or not np.isfinite(m).all() or not np.isfinite(b).all():
        raise StudyError('invalid_moments')
    return normalize_moments(flux, r @ m, r @ b @ r.T)


def normalize_moments(flux: float, first: Any, second: Any) -> dict:
    f = nonnegative(flux, 'arrival_flux')
    m = np.asarray(first, dtype=float); b = np.asarray(second, dtype=float)
    if f is None or m.shape != (3,) or b.shape != (3, 3) or not np.isfinite(m).all() or not np.isfinite(b).all():
        raise StudyError('invalid_moments')
    if not _close(b, b.T) or not _close(np.trace(b), f) or np.linalg.eigvalsh(b).min() < -ATOL:
        raise StudyError('invalid_second_moment')
    norm = float(np.linalg.norm(m))
    if f == 0 and (np.any(m != 0) or np.any(b != 0)):
        raise StudyError('zero_flux_requires_zero_unnormalized_moments')
    if norm > f + ATOL + RTOL * f:
        raise StudyError('first_moment_exceeds_flux')
    result = dict(arrival_flux_umol_s=f, **{f'arrival_M_{a}_umol_s': float(m[i]) for i, a in enumerate('xyz')},
                  **{f'arrival_B_{a}_umol_s': float(b[i, j]) for a, (i, j) in zip(SECOND, SECOND_INDEX)})
    mean = m / f if f > 0 else None
    direction = m / norm if f > 0 and norm > DTOL * f else None
    for stem, value in (('mean_arrival', mean), ('dominant_arrival', direction)):
        result.update({f'{stem}_{a}': float(value[i]) if value is not None else None for i, a in enumerate('xyz')})
    result['directionality'] = norm / f if f > 0 else None
    result.update({f'angular_second_{a}': float(b[i, j] / f) if f > 0 else None
                   for a, (i, j) in zip(SECOND, SECOND_INDEX)})
    result['direction_reason'] = 'zero_received_flux' if f == 0 else 'direction_cancellation' if direction is None else None
    return result


def compute_directional_features(sample_contributions: list[dict], memberships: list[dict], frames: dict) -> list[dict]:
    """Aggregate complete explicit paths. This function is NOT a transport backend.

    Membership rows: sample_id, entity_id, quadrature_area_m2, expected_paths
    (list of [fixture_id,path_id]). Contribution rows: sample_id, fixture_id,
    path_id, incident_ppfd_umol_m2_s, arrival_unit_grow_xyz. Frame rotations map
    grow vectors into the named output frame, keyed by entity_id then frame name.
    """
    members = {r['sample_id']: r for r in memberships}
    if len(members) != len(memberships) or not members:
        raise StudyError('duplicate_or_empty_angular_membership')
    expected = set()
    for sid, row in members.items():
        w = nonnegative(row['quadrature_area_m2'], 'quadrature_area')
        if w is None or w == 0:
            raise StudyError('positive_metric_quadrature_required')
        paths = [tuple(p) for p in row['expected_paths']]
        if not paths or len(paths) != len(set(paths)) or any(len(p) != 2 or p[0] == 'all' for p in paths):
            raise StudyError('explicit_unique_angular_paths_required')
        expected.update((sid, *p) for p in paths)
    seen = set(); groups: dict = defaultdict(list)
    for row in sample_contributions:
        key = tuple(row[k] for k in ('sample_id', 'fixture_id', 'path_id'))
        if key in seen or key not in expected:
            raise StudyError('duplicate_or_foreign_angular_path')
        seen.add(key); member = members[key[0]]
        q = nonnegative(row['incident_ppfd_umol_m2_s'], 'incident_ppfd')
        u = row.get('arrival_unit_grow_xyz')
        if q is not None and q > 0:
            u = np.asarray(u, dtype=float)
            if u.shape != (3,) or not np.isfinite(u).all() or not _close(np.linalg.norm(u), 1):
                raise StudyError('arrival_unit_vector_required')
        else:
            u = np.zeros(3)
        weighted = None if q is None else q * float(member['quadrature_area_m2'])
        for fixture in (row['fixture_id'], 'all'):
            groups[(member['entity_id'], fixture)].append((weighted, u))
    if seen != expected:
        raise StudyError('missing_angular_paths')
    result = []
    for (entity, fixture), values in groups.items():
        for name, rotation in frames.get(entity, {'grow': np.eye(3)}).items():
            base = dict(entity_id=entity, fixture_id=fixture, quantity_frame=name)
            if any(w is None for w, _ in values):
                result.append(dict(base, direction_reason='unknown_path_contribution'))
                continue
            f = math.fsum(w for w, _ in values)
            m = np.sum([w * u for w, u in values], axis=0)
            b = np.sum([w * np.outer(u, u) for w, u in values], axis=0)
            result.append(dict(base, **transform_moments(f, m, b, rotation)))
    return result


def aggregate_samples(samples: list[dict]) -> dict:
    """Strict full aggregate and separately named finite supported subtotal."""
    if not samples:
        raise StudyError('empty_sample_group')
    keys = [(r['sample_id'], r.get('fixture_id')) for r in samples]
    if len(keys) != len(set(keys)):
        raise StudyError('duplicate_samples')
    if len({r.get('fixture_id') for r in samples}) != 1:
        raise StudyError('aggregate_one_fixture_scope_at_a_time')
    weights = [nonnegative(r['quadrature_area_m2'], 'quadrature_area') for r in samples]
    if any(w is None or w == 0 for w in weights):
        raise StudyError('positive_metric_quadrature_required')
    area = math.fsum(weights)
    result: dict = dict(supported_area_m2=area, supported_area_cm2=area * 1e4)
    for field in PPFD:
        values = [nonnegative(r.get(field), field) for r in samples]
        flux = strict_sum([q * w if q is not None else None for q, w in zip(values, weights)])
        result[field] = flux / area if flux is not None else None
        if field in PPFD[2:]:
            name = field.split('_')[0]
            result[name + '_umol_s'] = flux
            known = [q * w for q, w in zip(values, weights) if q is not None]
            result[name + '_supported_subtotal_umol_s'] = math.fsum(known) if known else None
    received = [numeric(r.get(PPFD[2])) for r in samples]
    for label, fraction in (('p10', .1), ('p50', .5), ('p90', .9)):
        q = None
        if all(v is not None for v in received):
            ordered = sorted(zip(received, weights)); cumulative = 0.
            for value, w in ordered:
                cumulative += w
                if cumulative >= area * fraction:
                    q = value; break
        result[f'received_{label}_umol_m2_s'] = q
    return result


def integrate_light_schedule(full_output_data: list[dict], schedule: dict, intervals: dict) -> dict:
    """Expand full-output sample rows into explicitly bounded schedule intervals.

    UTC minute scanning exactly covers core HH:MM semantics, including DST folds
    and gaps. The caller must budget scanned minutes; geometry boundaries may be
    sub-minute. Raw samples survive for nonlinear downstream consumers.
    """
    zone, fixtures = _schedules(schedule)
    start, end = aware_time(intervals['start_at']), aware_time(intervals['end_at'])
    if end <= start:
        raise StudyError('invalid_requested_interval')
    cuts = schedule_boundaries(start, end, zone, fixtures, intervals.get('max_schedule_minutes'))
    snapshots = []; ids = set()
    for raw in intervals['snapshots']:
        a, b = aware_time(raw['valid_from']), aware_time(raw['valid_until'])
        if b <= a or raw['geometry_snapshot_id'] in ids:
            raise StudyError('invalid_or_duplicate_geometry_validity')
        if raw['geometry_mode'] not in ('observed', 'held_current_geometry_scenario'):
            raise StudyError('future_envelopes_not_optical_geometry')
        ids.add(raw['geometry_snapshot_id']); snapshots.append((a, b, raw))
        cuts.update(t for t in (a, b) if start < t < end)
    snapshots.sort(key=lambda x: x[0])
    if any(a[1] > b[0] for a, b in zip(snapshots, snapshots[1:])):
        raise StudyError('overlapping_geometry_validity')
    keys = set(); by_snapshot = defaultdict(list)
    for row in full_output_data:
        k = (row['geometry_snapshot_id'], row['sample_id'], row['fixture_id'], row['replicate'])
        if k in keys or row['geometry_snapshot_id'] not in ids:
            raise StudyError('duplicate_or_unknown_time_sample')
        if row['fixture_id'] != 'all' and row['fixture_id'] not in fixtures:
            raise StudyError('missing_fixture_schedule_key')
        if row['backend'] != 'direct' and row['fixture_id'] != 'all':
            raise StudyError('native_per_fixture_response_unavailable')
        keys.add(k); by_snapshot[k[0]].append(row)
    output = []; interval_rows = []; gaps = []
    edges = sorted(cuts)
    for a, b in zip(edges, edges[1:]):
        middle = a + (b - a) / 2
        active = next((raw for left, right, raw in snapshots if left <= middle < right), None)
        step = digest([a.isoformat(), b.isoformat(), active])[:24]
        if active is None or not by_snapshot.get(active['geometry_snapshot_id']):
            gaps.append(dict(start_at=a.isoformat(), end_at=b.isoformat(), reason='geometry_or_response_unavailable'))
            continue
        snapshot = active['geometry_snapshot_id']; rows = by_snapshot[snapshot]
        if len({(r['backend'], r['scenario_id'], r['run_id']) for r in rows}) != 1:
            raise StudyError('mixed_response_context_within_snapshot')
        factors = {f: _fraction(middle, zone, w) for f, w in fixtures.items()}
        native = rows[0]['backend'] != 'direct'
        if native:
            values = list(factors.values())
            factor = values[0] if values and all(v is not None and v == values[0] for v in values) else None
            factors = {'all': factor}
        else:
            rows = [r for r in rows if r['fixture_id'] != 'all']
            if {r['fixture_id'] for r in rows} != set(fixtures):
                raise StudyError('fixture_response_schedule_mismatch')
        base = {k: rows[0][k] for k in SCHEMA['join_key']}
        base.update(plant_instance_id=ALL, session_id=ALL, compound_id=ALL, time_step_id=step)
        duration = (b - a).total_seconds()
        for replicate in sorted({r['replicate'] for r in rows}):
            for fixture, factor in factors.items():
                interval_rows.append(dict(base, replicate=replicate, fixture_id=fixture, start_at=a.isoformat(), end_at=b.isoformat(),
                    duration_s=duration, timezone=schedule['timezone'], geometry_mode=active['geometry_mode'],
                    schedule_evidence_id=digest(schedule['provenance']), output_fraction=factor,
                    _reason='native_unequal_or_missing_schedule' if native and factor is None else 'schedule_unavailable'))
        scaled = []
        for row in rows:
            factor = factors[row['fixture_id']]
            new = dict(row, time_step_id=step, _start_at=a.isoformat(), _end_at=b.isoformat(), _duration_s=duration)
            for field in PPFD:
                value = numeric(row.get(field))
                # Preserve unknown spatial capability, even during known darkness.
                new[field] = value * factor if value is not None and factor is not None else None
            for field in ARRIVAL:
                if field in row:
                    value = numeric(row[field])
                    new[field] = value * factor if value is not None and factor is not None else None
            new['_reason'] = 'schedule_unavailable' if factor is None else row.get('_reason', 'quantity_unavailable')
            if factor is None:
                new['_reasons'] = dict(row.get('_reasons', {}), **{k:'schedule_unavailable' for k in (*PPFD, *ARRIVAL)})
            new['_reasons'] = dict(new.get('_reasons', {}))
            classify_face(new)
            scaled.append(new)
        output.extend(scaled)
        if not native:
            by_sample = defaultdict(list)
            for row in scaled:
                by_sample[(row['sample_id'], row['replicate'])].append(row)
            for sample_rows in by_sample.values():
                if {r['fixture_id'] for r in sample_rows} != set(fixtures):
                    raise StudyError('incomplete_per_sample_fixture_response')
                total = dict(sample_rows[0], fixture_id='all')
                for field in PPFD:
                    total[field] = strict_sum([r[field] for r in sample_rows])
                for field in (*ARRIVAL, 'arrival_path_unknown_count'):
                    if field in sample_rows[0]: total[field] = strict_sum([r.get(field) for r in sample_rows])
                total['_reasons'] = {k: next((r.get('_reasons', {}).get(k, r.get('_reason', 'quantity_unavailable'))
                    for r in sample_rows if r.get(k) is None), 'quantity_unavailable')
                    for k in (*PPFD, *ARRIVAL, 'arrival_path_unknown_count')}
                classify_face(total)
                output.append(total)
    return dict(samples=output, intervals=interval_rows, gaps=gaps,
                start_at=start.isoformat(), end_at=end.isoformat(), timezone=schedule['timezone'])


def _group_samples(samples: list[dict]) -> dict:
    groups = defaultdict(list)
    for row in samples:
        common = tuple(row[k] for k in ('run_id', 'scenario_id', 'geometry_snapshot_id', 'time_step_id', 'backend', 'replicate', 'fixture_id'))
        for level, parts in (
            ('leaflet', (row['plant_instance_id'], row['session_id'], row['organ_id'], row['leaflet_id'])),
            ('compound', (row['plant_instance_id'], row['session_id'], row['compound_id'])),
            ('plant', (row['plant_instance_id'],)), ('canopy', (ALL,))):
            if level == 'compound' and row['compound_id'] == UNASSIGNED:
                continue
            groups[(common, level, digest([level, parts])[:24])].append(row)
    return groups


def export_compound_light_features(spatial: list[dict], directional: list[dict], temporal: dict | None,
                                   compound_states: dict) -> list[dict]:
    """Aggregate observed supported tissue only; no biological response is evaluated."""
    samples = spatial + (temporal['samples'] if temporal else [])
    if directional:
        raise StudyError('use_actual_sample_moments_not_external_directional_records')
    result = []
    for (_, level, entity), rows in _group_samples(samples).items():
        first = rows[0]
        base = {k: first.get(k, UNASSIGNED) for k in SCHEMA['join_key']}
        for key in ('source_plant_id', 'capture_date', 'observed_at', 'geometry_variant_id', 'data_kind',
                    'organ_id', 'leaflet_id', 'compound_leaf_id', 'frame_id', 'transform_id', 'area_basis_id'):
            distinct = {r.get(key, UNASSIGNED) for r in rows}
            base[key] = next(iter(distinct)) if len(distinct) == 1 else ALL
        if level in ('plant', 'canopy'):
            base.update(session_id=ALL, compound_id=ALL, organ_id=ALL, leaflet_id=ALL, compound_leaf_id=ALL)
        elif level == 'compound':
            base.update(organ_id=ALL, leaflet_id=ALL)
        if level == 'canopy':
            base.update(plant_instance_id=ALL, source_plant_id=ALL, transform_id=ALL, frame_id='grow')
        base.update(level=level, entity_id=entity, fixture_id=first['fixture_id'], region_id='whole_supported',
                    quantity_frame='grow', coverage_status='supported_only_total_unknown',
                    estimated_total_area_m2=None, coverage_fraction=None, **aggregate_samples(rows))
        if base['area_basis_id'] == ALL:
            base['area_basis_id'] = digest(sorted({r['area_basis_id'] for r in rows}))
        state = compound_states.get((first['geometry_snapshot_id'], first['plant_instance_id'], first['session_id'], first['compound_id']))
        if level == 'compound' and state:
            base.update(compound_leaf_id=state['compound_leaf_id'], observed_at=state['observed_at'], frame_id=state['frame_id'])
            if state['direction_unit_xyz'] is not None:
                direction = np.asarray(state['direction_unit_xyz'])
                r = np.asarray(state['_rotation_board_to_grow'])
                direction = r @ direction
                base.update({f'observed_rachis_{a}': float(direction[i]) for i, a in enumerate('xyz')})
                trait = axis_traits([[0., 0., 0.], direction.tolist()])
                base.update(observed_azimuth_deg=trait['azimuth_deg'], observed_elevation_deg=trait['elevation_deg'])
            if state.get('_coverage'):
                base.update(state['_coverage'])
        base.update(_angular_samples(rows))
        base['_reason'] = base['direction_reason'] or 'quantity_unavailable'
        base['_reasons'] = {k: 'whole_tissue_coverage_not_supplied' for k in ('estimated_total_area_m2', 'coverage_fraction')}
        for col in SCHEMA['tables']['compound_light_features.csv']['columns']:
            name = col['name']
            if name.startswith('observed_'):
                base['_reasons'][name] = 'reviewed_observed_compound_axis_unavailable_or_not_compound_scope'
            elif name.startswith(('left_right_', 'proximal_distal_')):
                base['_reasons'][name] = 'reviewed_local_partition_unavailable_or_degenerate'
            elif name.startswith(('received_', 'absorbed_', 'normal_side_', 'opposite_side_')):
                base['_reasons'][name] = 'required_sample_contributions_unavailable'
        if first['backend'] != 'direct':
            for percentile in ('p10', 'p50', 'p90'):
                name = f'received_{percentile}_umol_m2_s'
                base[name] = None; base['_reasons'][name] = 'native_spatial_distribution_unavailable'
            for name in PPFD[:2]: base['_reasons'][name] = 'native_side_channels_unavailable'
        result.append(base)
        if level != 'canopy':
            board = dict(base, quantity_frame='board')
            board.update(_angular_samples(rows, first.get('_rotation_grow_to_board')))
            if level == 'compound' and state and state['direction_unit_xyz'] is not None:
                board.update({f'observed_rachis_{a}': float(state['direction_unit_xyz'][i]) for i, a in enumerate('xyz')})
                board.update(observed_azimuth_deg=state['azimuth_deg'], observed_elevation_deg=state['elevation_deg'])
            result.append(board)
        if level == 'compound' and state and state['direction_unit_xyz'] is not None and state.get('transverse_unit_xyz') is not None:
            local = dict(base, quantity_frame='compound_local', observed_rachis_x=1., observed_rachis_y=0., observed_rachis_z=0.,
                         observed_azimuth_deg=0., observed_elevation_deg=0.)
            x = np.asarray(state['direction_unit_xyz']); y = np.asarray(state['transverse_unit_xyz'])
            local_rotation = np.column_stack((x, y, np.cross(x, y))).T @ np.asarray(state['_rotation_board_to_grow']).T
            local.update(_angular_samples(rows, local_rotation))
            result.append(local)
            if state.get('_region_partition') and first['backend'] == 'direct':
                result.extend(_regions(rows, local, state))
    return result


def _regions(samples: list[dict], base: dict, state: dict) -> list[dict]:
    partition = state['_region_partition']
    boundary = numeric(partition['proximal_distal_boundary_mm'])
    if boundary is None:
        raise StudyError('explicit_region_boundary_required')
    x = np.asarray(state['direction_unit_xyz']); y = np.asarray(state['transverse_unit_xyz'])
    basis = np.column_stack((x, y, np.cross(x, y)))
    if not _close(basis.T @ basis, np.eye(3)):
        raise StudyError('reviewed_orthonormal_compound_frame_required')
    origin = np.asarray(state['attachment_xyz_mm']); bins: dict = {name: [] for name in
        ('left', 'right', 'lateral_unassigned', 'proximal', 'distal', 'longitudinal_unassigned')}
    for row in samples:
        point = np.array([row[f'position_board_{a}_mm'] for a in 'xyz'])
        local = basis.T @ (point - origin)
        side = 'lateral_unassigned' if abs(local[1]) <= ATOL else 'left' if local[1] < 0 else 'right'
        longitudinal = 'longitudinal_unassigned' if abs(local[0] - boundary) <= ATOL else 'proximal' if local[0] < boundary else 'distal'
        bins[side].append(row); bins[longitudinal].append(row)
    results = []
    angular_rotation = (basis.T @ np.asarray(state['_rotation_board_to_grow']).T
                        if '_rotation_board_to_grow' in state else None)
    if angular_rotation is None and any(all(r.get(k) is not None for k in ARRIVAL) for r in samples):
        raise StudyError('angular_region_requires_observed_frame_rotation')
    for name, rows in bins.items():
        values = aggregate_samples(rows) if rows else dict(supported_area_m2=0., supported_area_cm2=0.,
            received_umol_s=0., absorbed_umol_s=0., received_supported_subtotal_umol_s=0., absorbed_supported_subtotal_umol_s=0.,
            **{key: None for key in (*PPFD, 'received_p10_umol_m2_s', 'received_p50_umol_m2_s', 'received_p90_umol_m2_s')})
        results.append(dict(base, **values, region_id=name, coverage_status='partial_supported_region',
                            estimated_total_area_m2=None, coverage_fraction=None,
                            **_angular_samples(rows, angular_rotation),
                            _reason='empty_supported_region' if not rows else 'required_angular_contribution_unavailable'))
    by_name = {r['region_id']: r for r in results}
    for prefix, a, b in (('left_right', 'left', 'right'), ('proximal_distal', 'proximal', 'distal')):
        left, right = by_name[a], by_name[b]
        f1, f2 = left['received_umol_s'], right['received_umol_s']
        q1, q2 = left['received_ppfd_umol_m2_s'], right['received_ppfd_umol_m2_s']
        base[prefix + '_flux_difference_umol_s'] = f1 - f2 if f1 is not None and f2 is not None else None
        base[prefix + '_mean_contrast'] = (q1 - q2) / (q1 + q2) if q1 is not None and q2 is not None and q1 + q2 > 0 else None
    return results


def integrate_dose(features: list[dict], temporal: dict) -> list[dict]:
    start, end = aware_time(temporal['start_at']), aware_time(temporal['end_at'])
    requested = (end - start).total_seconds(); zone = ZoneInfo(temporal['timezone'])
    a, b = start.astimezone(zone), end.astimezone(zone)
    daily = a.time().isoformat() == b.time().isoformat() == '00:00:00' and b.date() == a.date() + timedelta(days=1)
    interval_map = {r['time_step_id']: r for r in temporal['intervals']}
    groups = defaultdict(list)
    for row in features:
        if row['time_step_id'] == 'full_output' or row['region_id'] != 'whole_supported' or row['quantity_frame'] != 'grow':
            continue
        key = tuple(row[k] for k in ('run_id', 'scenario_id', 'plant_instance_id', 'session_id', 'compound_id',
                                     'backend', 'replicate', 'level', 'entity_id', 'fixture_id'))
        groups[key].append(row)
    result = []
    for rows in groups.values():
        first = rows[0]; base = {k: first[k] for k in SCHEMA['join_key']}
        for k in ('source_plant_id', 'organ_id', 'leaflet_id', 'level', 'entity_id', 'fixture_id'):
            base[k] = first[k]
        bases = sorted({r['area_basis_id'] for r in rows})
        base.update(geometry_snapshot_id=ALL, time_step_id='integrated', area_basis_id=bases[0] if len(bases) == 1 else 'time_indexed:' + digest(bases),
            start_at=start.isoformat(), end_at=end.isoformat(), timezone=temporal['timezone'], requested_seconds=requested,
            complete_local_day=False, integration_method='piecewise_constant_PPFD_and_time_indexed_flux')
        seen = set()
        for row in rows:
            if row['time_step_id'] in seen:
                raise StudyError('duplicate_dose_interval')
            seen.add(row['time_step_id'])
        for name, dose_name, covered_name in (('received', 'incident', 'covered_seconds'), ('absorbed', 'absorbed', 'absorbed_covered_seconds')):
            valid = [r for r in rows if r[name + '_ppfd_umol_m2_s'] is not None and r[name + '_umol_s'] is not None]
            covered = math.fsum(interval_map[r['time_step_id']]['duration_s'] for r in valid)
            subtotal = photon_integral((r[name + '_ppfd_umol_m2_s'], interval_map[r['time_step_id']]['duration_s']) for r in valid) if valid else None
            photons = photon_integral((r[name + '_umol_s'], interval_map[r['time_step_id']]['duration_s']) for r in valid) if valid else None
            complete = _close(covered, requested)
            base[covered_name] = covered
            base[dose_name + '_supported_dose_mol_m2'] = subtotal
            base[dose_name + '_dose_mol_m2'] = subtotal if complete else None
            base[dose_name + '_photons_mol'] = photons if complete else None
        base['complete_local_day'] = daily and _close(base['covered_seconds'], requested)
        base['dli_mol_m2_day'] = base['incident_dose_mol_m2'] if base['complete_local_day'] else None
        base['_reason'] = 'not_complete_declared_day_or_missing_coverage'
        result.append(base)
    return result


def _source_snapshot(prepared: Path, results: Path) -> tuple[dict, dict, Any]:
    from tools import hierarchical_light as hierarchy
    manifest = hierarchy.require_fresh(prepared)
    result_manifest = hierarchy.require_fresh(results)
    if manifest['status'] != 'prepared' or result_manifest['backend'] != manifest['backend']:
        raise StudyError('incompatible_prepared_results')
    if result_manifest['plan'] != manifest['plan']:
        raise StudyError('results_scenario_or_geometry_mismatch')
    expected = result_manifest['source_hashes'].get(str((prepared / 'manifest.json').resolve()))
    if expected != file_hash(prepared / 'manifest.json'):
        raise StudyError('results_prepared_provenance_mismatch')
    result = read_json(results / 'results.json')
    return manifest, result, hierarchy.load_context(prepared, manifest)


def audit_growth_light_inputs(request_path: Path) -> dict:
    """Read-only audit; known physical blockers are distinct from software inputs."""
    report: dict = dict(schema_version=SCHEMA['schema_version'], input_blockers=[],
        dependencies=[], snapshots=[], optical_geometry=[], source_hashes={},
        physical_validation=False, biological_prediction=False)
    try:
        request_path = request_path.resolve(); request = read_json(request_path)
        report['source_hashes'][str(request_path)] = file_hash(request_path)
        if request['schema_version'] != SCHEMA['schema_version'] or not request['run_id']:
            raise StudyError('invalid_request_schema_or_run_id')
        start, end = aware_time(request['interval']['start_at']), aware_time(request['interval']['end_at'])
        if end <= start:
            raise StudyError('invalid_requested_interval')
        _schedules(request['schedule'])
        limits = request['limits']
        for name in ('max_transport_calls', 'max_receiver_emitter_pairs', 'max_schedule_minutes'):
            if type(limits.get(name)) is not int or limits[name] < 1:
                raise StudyError('explicit_positive_limit_required:' + name)
        ids = set(); calls = 0; pairs = 0; association_contexts = []
        for snapshot in request['snapshots']:
            sid = snapshot['geometry_snapshot_id']
            if sid in ids:
                raise StudyError('duplicate_geometry_snapshot_id')
            ids.add(sid)
            prepared = (request_path.parent / snapshot['prepared_run']).resolve()
            results = (request_path.parent / snapshot['full_scene_results']).resolve()
            manifest, result, context = _source_snapshot(prepared, results)
            if set(request['schedule']['fixtures']) != {f.fixture_id for f in context.resolved.fixtures}:
                raise StudyError('schedule_fixture_identity_mismatch')
            for folder in (prepared, results):
                for name in ('manifest.json', 'results.json'):
                    p = folder / name
                    if p.is_file(): report['source_hashes'][str(p)] = file_hash(p)
            report['source_hashes'].update(manifest['source_hashes'])
            report['source_hashes'].update(manifest['code_hashes'])
            report['source_hashes'].update(result['manifest']['source_hashes'])
            for name in ('scene.json', 'leaf_surfaces.csv'):
                p = prepared / name; report['source_hashes'][str(p)] = file_hash(p)
            if set(snapshot['board_frame_ids']) != {t['plant_instance_id'] for t in context.targets.values()}:
                raise StudyError('explicit_board_frame_ids_required_for_all_instances')
            if not set(snapshot.get('observed_at_by_instance', {})).issubset(snapshot['board_frame_ids']):
                raise StudyError('foreign_observation_clock_instance')
            for pid in snapshot['board_frame_ids']: _observed_at(snapshot, pid)
            if any(not v for v in snapshot['board_frame_ids'].values()):
                raise StudyError('empty_board_frame_id')
            if manifest['backend'] == 'direct':
                calls += 1
                pairs += len(context.weights_m2) * sum(len(f.emitters.positions_grow_mm) for f in context.resolved.fixtures if f.emitters is not None)
            report['snapshots'].append(dict(geometry_snapshot_id=sid, backend=manifest['backend'],
                source_hash=file_hash(prepared / 'leaf_surfaces.csv'), data_kind=manifest['plan']['case']['data_kind'],
                spatial_status='supported' if manifest['backend'] == 'direct' else 'unavailable_native_spatial_channels'))
            geometry_evidence = snapshot_evidence(prepared, snapshot, manifest)
            report['optical_geometry'].append(geometry_evidence)
            if geometry_evidence['geometric_computability'] != 'available':
                raise StudyError(';'.join(geometry_evidence['reasons']))
            if request.get('compound_history') or request.get('associations'):
                # Geometric area ledger for read-only association checks; not light samples.
                geometry_hash=file_hash(prepared/'leaf_surfaces.csv'); ledger=[]; instance_map={}
                transforms={pid:rigid_transform(p.model_dump(mode='json')) for pid,p in context.resolved.placements.items()}
                for target in context.targets.values():
                    pid=target['plant_instance_id']; compound=target['compound_id'] if target['hierarchy_ready'] else UNASSIGNED
                    item=dict(geometry_snapshot_id=sid,plant_instance_id=pid,session_id=target['session_id'],compound_id=compound,
                        source_plant_id=target['source_plant_id'],observed_at=_observed_at(snapshot,pid),
                        frame_id=snapshot['board_frame_ids'][pid],geometry_sha256=geometry_hash)
                    instance_map[(pid,target['session_id'],compound)]=item
                    ledger.append(dict(item,fixture_id='all',replicate='area_audit_only',sample_id=target['target_id'],
                                       quadrature_area_m2=target['area_m2']))
                association_contexts.append(dict(instances=list(instance_map.values()),accounting_rows=ledger,transforms=transforms))
        if not ids or calls > limits['max_transport_calls'] or pairs > limits['max_receiver_emitter_pairs']:
            raise StudyError('full_scene_recalculation_budget_exceeded')
        report['cost'] = dict(transport_calls=calls, receiver_emitter_pairs=pairs)
        # Validate geometry timing and minute budget without running any transport.
        interval = dict(request['interval'], snapshots=request['snapshots'], max_schedule_minutes=limits['max_schedule_minutes'])
        integrate_light_schedule([], request['schedule'], interval)
        audited_states=_join_observations(request,request_path.parent,association_contexts,report['source_hashes'])
        report['reviewed_observation_associations']=len(audited_states)
        if request.get('reference_dli') is not None:
            envelope, _ = load_attachment(request['reference_dli'], request_path.parent, set())
            report['reference_channel_status'] = envelope['status']
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report['input_blockers'].append(str(exc))
    report['input_ready'] = not report['input_blockers']
    return report


def _table(folder: Path, name: str, records: list[dict], availability: dict) -> None:
    spec = SCHEMA['tables'][name]; output = []; seen = set()
    for record in records:
        row = {}; reasons = {}
        for col in spec['columns']:
            key = col['name']
            if key == 'availability_id': continue
            value = record.get(key)
            if col['type'] == 'number':
                value = numeric(value)
                if value is None:
                    reasons[key] = record.get('_reasons', {}).get(key, record.get('_reason', 'input_not_supplied'))
            elif col['type'] == 'boolean':
                if type(value) is not bool: raise StudyError('explicit_boolean_required:' + key)
            elif value is None or value == 'unavailable':
                if col.get('nullable'):
                    value = None
                    reasons[key] = record.get('_reasons', {}).get(key, record.get('_reason', 'input_not_supplied'))
                else: value = UNASSIGNED
            row[key] = value
        key = tuple(row[k] for k in spec['primary_key'])
        if key in seen: raise StudyError('duplicate_table_key:' + name)
        seen.add(key)
        aid = digest(reasons); availability[aid] = reasons; row['availability_id'] = aid
        output.append(row)
    write_rows(folder / name, output, [c['name'] for c in spec['columns']])


def export_spatial_light(prepared_run: Path, full_scene_results: Path, out: Path, *,
                         snapshot: dict, run_id: str, max_receiver_emitter_pairs: int) -> dict:
    """Re-evaluate once using public full-scene direct arrays; check legacy ABC flux."""
    from tools import hierarchical_light as hierarchy
    manifest, legacy, context = _source_snapshot(prepared_run, full_scene_results)
    folder = output_dir(out)
    if manifest['backend'] != 'direct':
        raise StudyError('native_has_no_public_spatial_samples_use_scalar_features')
    pairs = len(context.weights_m2) * sum(len(f.emitters.positions_grow_mm) for f in context.resolved.fixtures if f.emitters is not None)
    if type(max_receiver_emitter_pairs) is not int or pairs > max_receiver_emitter_pairs:
        raise StudyError('spatial_recalculation_budget_exceeded')
    from tools.light_direction_diagnostics import DirectionCollector, PROTOCOL
    inventory = {f.fixture_id: len(f.emitters.positions_grow_mm) if f.emitters is not None else None
                 for f in context.resolved.fixtures}
    chunk_limit = min(max_receiver_emitter_pairs, context.resolved.scene.simulation.max_ray_triangle_pairs_per_chunk)
    collector = DirectionCollector(inventory, context.receivers.unit_normals, context.weights_m2,
        max_paths=max_receiver_emitter_pairs, max_chunk_paths=chunk_limit,
        max_receiver_fixture_pairs=max_receiver_emitter_pairs)
    direct = hierarchy.direct_light(context.receivers, context.resolved.fixtures, context.occluders,
        context.resolved.scene.leaf_optics.transmittance.value, context.resolved.scene.simulation,
        diagnostic_callback=collector, diagnostic_max_paths_per_chunk=chunk_limit)
    moments = collector.finish(direct)
    transforms = {pid: rigid_transform(p.model_dump(mode='json')) for pid, p in context.resolved.placements.items()}
    geometry_hash = file_hash(prepared_run / 'leaf_surfaces.csv')
    base = dict(run_id=run_id, scenario_id=manifest['plan']['scenario_id'], geometry_snapshot_id=snapshot['geometry_snapshot_id'],
                time_step_id='full_output', backend='direct', replicate='deterministic',
                geometry_variant_id=manifest['plan']['case']['geometry_variant_id'], data_kind=manifest['plan']['case']['data_kind'])
    memberships = {(r['plant_instance_id'], r['session_id'], r['organ_id'], r['leaflet_id']): r for r in manifest['audit']['membership']}
    samples = []; instance_rows = {}; counts: dict = defaultdict(int)
    alpha = context.resolved.scene.leaf_optics.absorptance.value
    for i, triangle in enumerate(context.receivers.own_triangle):
        target = context.targets[context.triangle_targets[triangle]]; pid = target['plant_instance_id']
        trans = transforms[pid]; inv = np.asarray(trans['T_grow_to_board'])
        point = context.receivers.points_grow_mm[i]; normal = context.receivers.unit_normals[i]
        board = inv[:3, :3] @ point + inv[:3, 3]; board_normal = inv[:3, :3] @ normal
        triangle_id = context.surfaces.triangle_ids[triangle]
        subindex = counts[(pid, target['session_id'], triangle_id)]; counts[(pid, target['session_id'], triangle_id)] += 1
        compound = target['compound_id'] if target['hierarchy_ready'] else UNASSIGNED
        row = dict(base, **{k: target[k] for k in ('source_plant_id', 'plant_instance_id', 'session_id', 'capture_date', 'organ_id', 'leaflet_id')},
            compound_id=compound, compound_leaf_id=UNASSIGNED, observed_at=_observed_at(snapshot,pid),
            frame_id=snapshot['board_frame_ids'][pid], transform_id=trans['transform_id'],
            area_basis_id=digest([geometry_hash, pid, target['session_id'], compound]), triangle_id=triangle_id,
            sample_id=digest([geometry_hash, pid, target['session_id'], target['organ_id'], target['leaflet_id'], triangle_id, subindex]),
            quadrature_area_m2=float(context.weights_m2[i]), normal_convention='mesh_normal_no_botanical_side_claim',
            receiver_index=i, _rotation_grow_to_board=inv[:3, :3].tolist(),
            _reason='transport_or_optics_unavailable')
        for frame, xyz, n in (('grow', point, normal), ('board', board, board_normal)):
            row.update({f'position_{frame}_{a}_mm': float(xyz[j]) for j, a in enumerate('xyz')})
            row.update({f'normal_{frame}_{a}': float(n[j]) for j, a in enumerate('xyz')})
        fixture_rows = []
        for f, fixture in enumerate(direct.fixture_ids):
            q, upper = hierarchy.finite(direct.ppfd_umol_m2_s[f, i]), hierarchy.finite(direct.upper_side_ppfd_umol_m2_s[f, i])
            opposite = q - upper if q is not None and upper is not None else None
            if opposite is not None and opposite < 0:
                if not _close(opposite, 0): raise StudyError('invalid_side_budget')
                opposite = 0.
            new = dict(row, fixture_id=fixture, received_ppfd_umol_m2_s=q, normal_side_ppfd_umol_m2_s=upper,
                       opposite_side_ppfd_umol_m2_s=opposite, absorbed_ppfd_umol_m2_s=q * alpha if q is not None and alpha is not None else None)
            raw = [moments.flux_umol_s[f, i], *moments.first_umol_s[f, i], *moments.second_umol_s[f, i]]
            new.update({key: hierarchy.finite(value) for key, value in zip(ARRIVAL, raw)})
            count = int(moments.unknown_path_count[f, i])
            new['arrival_path_unknown_count'] = count if count >= 0 else None
            new['_reasons'] = {key: moments.first_missing_reason[f][i] or 'angular_path_unavailable'
                               for key in (*ARRIVAL, 'arrival_path_unknown_count')}
            fixture_rows.append(new)
        total = dict(row, fixture_id='all', **{key: strict_sum([r[key] for r in fixture_rows]) for key in PPFD})
        total.update({key: strict_sum([r[key] for r in fixture_rows]) for key in (*ARRIVAL, 'arrival_path_unknown_count')})
        for sample in fixture_rows + [total]: classify_face(sample)
        samples.extend(fixture_rows + [total])
        ikey = (pid, target['session_id'], compound)
        member = memberships.get((pid, target['session_id'], target['organ_id'], target['leaflet_id']), {})
        instance_rows[ikey] = dict(base, plant_instance_id=pid, source_plant_id=target['source_plant_id'], session_id=target['session_id'],
            compound_id=compound, compound_leaf_id=UNASSIGNED, observed_at=row['observed_at'], frame_id=row['frame_id'],
            transform_id=row['transform_id'], geometry_sha256=geometry_hash, association_status='growth_association_unavailable',
            evidence_sha256=member.get('evidence_sha256', UNASSIGNED))
    parity = []
    sample_groups = defaultdict(list)
    for row in samples:
        target_id = hierarchy.token([row['plant_instance_id'], row['session_id'], row['organ_id'], row['leaflet_id']])
        sample_groups[(target_id, row['fixture_id'])].append(row)
    for old in legacy['tables']['interaction_cases']:
        if old['subset'] != 'ABC': continue
        group = sample_groups[(old['target_id'], old['fixture_id'])]; actual = aggregate_samples(group)
        for field in ('received_umol_s', 'absorbed_umol_s'):
            expected = old[field]; value = actual[field]
            if (expected is None) != (value is None) or (value is not None and not _close(value, expected)):
                raise StudyError('legacy_full_scene_parity_failed:' + field)
        parity.append(dict(target_id=old['target_id'], fixture_id=old['fixture_id'], status='passed'))
    # A selected legacy subset may omit entities; the full spatial package still retains every receiver.
    availability: dict = {}
    _table(folder, 'light_samples.csv', samples, availability)
    _table(folder, 'instance_map.csv', list(instance_rows.values()), availability)
    write_json(folder / 'availability.json', availability)
    write_json(folder / 'transforms.json', transforms)
    metadata = dict(backend='direct', scalar_parity=parity, tolerances=POLICY,
        angular_diagnostics=dict(protocol=PROTOCOL, **collector.summary()),
        geometry_sha256=geometry_hash, source_hashes=manifest['source_hashes'],
        spectral_band=context.resolved.scene.leaf_optics.photon_band,
        numerical_cost=dict(transport_calls=1, receiver_emitter_pairs=pairs))
    write_json(folder / 'spatial_manifest.json', metadata)
    return dict(metadata, samples=samples, accounting_rows=samples, instances=list(instance_rows.values()), transforms=transforms)


def export_native_scalar(prepared: Path, results: Path, snapshot: dict, run_id: str) -> dict:
    """Retain native leaflet scalar responses; never manufacture receiver samples."""
    manifest, legacy, context = _source_snapshot(prepared, results)
    if manifest['backend'] != 'native': raise StudyError('native_results_required')
    transforms = {pid:rigid_transform(p.model_dump(mode='json')) for pid,p in context.resolved.placements.items()}
    geometry_hash=file_hash(prepared/'leaf_surfaces.csv'); accounting=[]; instances={}
    old={(r['target_id'],r['replicate']):r for r in legacy['tables']['interaction_cases'] if r['subset']=='ABC' and r['fixture_id']=='all'}
    replicates=sorted({r['replicate'] for r in legacy['tables']['interaction_cases']})
    for target in context.targets.values():
        pid=target['plant_instance_id']; compound=target['compound_id'] if target['hierarchy_ready'] else UNASSIGNED
        base=dict(run_id=run_id,scenario_id=manifest['plan']['scenario_id'],geometry_snapshot_id=snapshot['geometry_snapshot_id'],
            time_step_id='full_output',backend='native',geometry_variant_id=manifest['plan']['case']['geometry_variant_id'],
            data_kind=manifest['plan']['case']['data_kind'],plant_instance_id=pid,source_plant_id=target['source_plant_id'],
            session_id=target['session_id'],capture_date=target['capture_date'],observed_at=_observed_at(snapshot,pid),
            compound_id=compound,compound_leaf_id=UNASSIGNED,organ_id=target['organ_id'],leaflet_id=target['leaflet_id'],
            frame_id=snapshot['board_frame_ids'][pid],transform_id=transforms[pid]['transform_id'],
            area_basis_id=digest([geometry_hash,pid,target['session_id'],compound]))
        instances[(pid,target['session_id'],compound)]=dict(base,geometry_sha256=geometry_hash,
            association_status='growth_association_unavailable',evidence_sha256=UNASSIGNED)
        for replicate in replicates:
            previous=old.get((target['target_id'],replicate),{})
            area=target['area_m2']; q=previous.get('received_umol_s'); absorbed=previous.get('absorbed_umol_s')
            accounting.append(dict(base,replicate=replicate,fixture_id='all',sample_id='native_aggregate:'+target['target_id'],
                quadrature_area_m2=area,received_ppfd_umol_m2_s=q/area if q is not None else None,
                absorbed_ppfd_umol_m2_s=absorbed/area if absorbed is not None else None,
                normal_side_ppfd_umol_m2_s=None,opposite_side_ppfd_umol_m2_s=None,
                _reason='native_spatial_and_side_channels_unavailable',_native_aggregate=True))
    return dict(backend='native',samples=[],accounting_rows=accounting,instances=list(instances.values()),transforms=transforms,
        geometry_sha256=geometry_hash,spectral_band=context.resolved.scene.leaf_optics.photon_band,
        scalar_parity=[dict(status='imported_existing_native_scalar',results_sha256=file_hash(results/'results.json'))],
        native_source=dict(prepared_run=str(prepared),results=str(results),geometry_snapshot_id=snapshot['geometry_snapshot_id']))


def _join_observations(request: dict, base: Path, exports: list[dict], sources: dict) -> dict:
    """Explicit, reviewed source associations; no matching by leaf rank or position."""
    from tools.compound_growth import load_history
    if not request.get('compound_history'):
        if request.get('associations'): raise StudyError('association_requires_compound_history')
        return {}
    history_path = (base / request['compound_history']).resolve()
    states, context = load_history(history_path); sources.update(context['source_hashes'])
    lookup = {(s['plant_id'], s['session_id'], s['compound_leaf_id']): s for s in states}
    export_map = {r['geometry_snapshot_id']: e for e in exports for r in e['instances']}
    result = {}; joined_growth = set()
    for association in request.get('associations', []):
        key = tuple(association[k] for k in ('geometry_snapshot_id', 'plant_instance_id', 'session_id', 'compound_id'))
        if key in result: raise StudyError('duplicate_compound_association')
        export = export_map.get(key[0])
        if export is None: raise StudyError('unknown_association_snapshot')
        instances = [r for r in export['instances'] if (r['plant_instance_id'], r['session_id'], r['compound_id']) == key[1:]]
        if len(instances) != 1: raise StudyError('ambiguous_or_unknown_compound_association')
        instance = instances[0]
        state = lookup.get((instance['source_plant_id'], key[2], association['compound_leaf_id']))
        if state is None or state['identity_status'] != 'confirmed' or not state['review_source']:
            raise StudyError('confirmed_observed_compound_identity_required')
        if state['frame_stability'] != 'confirmed': raise StudyError('confirmed_observation_frame_required')
        growth_key = (key[0], key[1], key[2], association['compound_leaf_id'])
        if growth_key in joined_growth: raise StudyError('multiple_optical_compounds_mapped_to_one_growth_compound')
        joined_growth.add(growth_key)
        if state['coordinate_frame'] != 'board_mm' or state['frame_id'] != instance['frame_id']:
            raise StudyError('association_board_frame_mismatch')
        if instance['observed_at'] == UNASSIGNED or aware_time(state['observed_at']) != aware_time(instance['observed_at']):
            raise StudyError('association_observation_time_mismatch')
        if association.get('review_status') != 'reviewed': raise StudyError('reviewed_association_required')
        evidence = (base / association['evidence_path']).resolve()
        if file_hash(evidence) != association['evidence_sha256']: raise StudyError('stale_association_evidence')
        sources[str(evidence)] = file_hash(evidence)
        if association['geometry_sha256'] != instance['geometry_sha256']:
            raise StudyError('stale_association_geometry')
        tissue = [r for r in export['accounting_rows'] if (r['plant_instance_id'], r['session_id'], r['compound_id']) == key[1:]]
        allrows = [r for r in tissue if r['fixture_id'] == 'all']
        allrows = [r for r in allrows if r['replicate'] == allrows[0]['replicate']]
        area = aggregate_samples(allrows)['supported_area_m2']
        if association.get('area_basis_id') != state['area_basis_id'] or not state['area_basis_id']:
            raise StudyError('association_area_basis_mismatch')
        if not _close(area, association['supported_area_m2']): raise StudyError('association_supported_area_mismatch')
        if state['supported_area_cm2'] is not None and not _close(area * 1e4, state['supported_area_cm2']):
            raise StudyError('observation_optical_area_mismatch')
        copied = deepcopy(state)
        if copied['geometry_status'] != 'observed_axis':
            copied.update(direction_unit_xyz=None, transverse_unit_xyz=None, azimuth_deg=None, elevation_deg=None)
        copied['_rotation_board_to_grow'] = np.asarray(export['transforms'][key[1]]['T_board_to_grow'])[:3, :3].tolist()
        copied['_region_partition'] = association.get('region_partition')
        coverage = association.get('coverage')
        if coverage:
            proof = (base / coverage['evidence_path']).resolve()
            if file_hash(proof) != coverage['evidence_sha256']: raise StudyError('stale_coverage_evidence')
            sources[str(proof)] = file_hash(proof)
            total = nonnegative(coverage.get('estimated_total_area_m2'), 'estimated_area')
            fraction = nonnegative(coverage.get('coverage_fraction'), 'coverage_fraction')
            if total is not None and total < area - ATOL: raise StudyError('total_area_less_than_supported')
            if fraction is not None and fraction > 1: raise StudyError('invalid_coverage_fraction')
            if total is not None and fraction is not None and not _close(fraction, area / total):
                raise StudyError('inconsistent_independent_coverage')
            if coverage['coverage_status'] not in ('partial', 'complete', 'unknown'): raise StudyError('invalid_coverage_status')
            if coverage['coverage_status'] == 'complete' and fraction != 1.: raise StudyError('complete_coverage_requires_independent_fraction_one')
            copied['_coverage'] = dict(coverage_status=coverage['coverage_status'], estimated_total_area_m2=total, coverage_fraction=fraction)
        result[key] = copied
        instance.update(compound_leaf_id=state['compound_leaf_id'], association_status='reviewed', evidence_sha256=association['evidence_sha256'])
        for row in tissue:
            row.update(compound_leaf_id=state['compound_leaf_id'], observed_at=state['observed_at'], area_basis_id=state['area_basis_id'])
    return result


def _consumer_mapping(states: dict) -> dict:
    return dict(schema_version=SCHEMA['schema_version'], join_key=SCHEMA['join_key'],
        growth=dict(identity='reviewed source_plant_id + session_id + compound_leaf_id association; retain plant_instance_id for canopy copies',
            direction=dict(table='compound_light_features.csv', select=dict(level='compound', region_id='whole_supported', quantity_frame='board'),
                fields=['observed_rachis_x', 'observed_rachis_y', 'observed_rachis_z'], target='direction_unit_xyz', unit='1', meaning='observed rachis, not light direction'),
            area=dict(field='supported_area_cm2', target='supported_area_cm2', conversion='supported_area_m2 * 10000', required='matching reviewed area_basis_id'),
            observation_time='observed_at; capture_date is not a clock timestamp',
            light_covariates='supported tissue received/absorbed PPFD, flux and incident DLI with fixture/time/backend; direct actual arrival moments are available, not growth orientation',
            reference_dli=reference_mapping(None),
            orientation_binding='P3 must reject light arrival moments/directions as orientation parameters; P3 owns that binding guard',
            response='No automatic multiplier or rotation. Current growth light_features additionally require explicit metric/unit/backend/source_ref and response contract.'),
        physiology=dict(table='light_samples.csv', select='time_step_id != full_output; fixture_id = all; direct backend only',
            area_field='quadrature_area_m2', area_unit='m2', duration='join light_intervals.csv by run/scenario/snapshot/time/backend/replicate; duration_s counted once',
            incident_field='received_ppfd_umol_m2_s', absorbed_field='absorbed_ppfd_umol_m2_s', unit='umol/m2/s',
            convention='two-face photons divided by one-sided supported area; absorption already applied once',
            fixture_combination='sum simultaneous fixture PPFD at the same sample/time before nonlinear leaf exchange; use all once, never add all plus fixtures',
            face_policy='D15-D20: evidenced adaxial_only for dwarf-source before_mito exchange; P4 refuses both; transport remains unchanged',
            dwarf_source_light_basis='absorbed', dwarf_source_respiration='before_mito',
            coefficient_basis_conflict='P4 reports alpha_calibration_basis_conflict without P2 relabelling or extra absorptance',
            external_required=['temperature', 'RH_or_VPD', 'CO2', 'photosynthesis_contract', 'initial_carbon_and_mass', 'respiration_ownership'],
            unsupported=['blue_light', 'red_far_red', 'native_spatial_distribution', 'future_optical_envelopes']),
        reviewed_compound_count=len(states), biological_fields_populated=False,
        frame_and_region_contract=SCHEMA['region_convention'],
        observed_states=[dict(geometry_snapshot_id=k[0], plant_instance_id=k[1], session_id=k[2], compound_id=k[3],
            compound_leaf_id=v['compound_leaf_id'], observed_at=v['observed_at'], frame_id=v['frame_id'],
            area_basis_id=v['area_basis_id'], attachment_xyz_mm=v['attachment_xyz_mm'], rachis_points_mm=v['rachis_points_mm'],
            direction_unit_xyz=v['direction_unit_xyz'], transverse_unit_xyz=v['transverse_unit_xyz'], region_partition=v.get('_region_partition'))
            for k, v in states.items()])


def build_package(request_path: Path, out: Path) -> dict:
    request_path = request_path.resolve(); request = read_json(request_path)
    audit = audit_growth_light_inputs(request_path)
    if not audit['input_ready']: raise StudyError('input_audit_blocked:' + ';'.join(audit['input_blockers']))
    folder = output_dir(out); exports = []; source_hashes = dict(audit['source_hashes'])
    for index, snapshot in enumerate(request['snapshots']):
        prepared = (request_path.parent / snapshot['prepared_run']).resolve()
        results = (request_path.parent / snapshot['full_scene_results']).resolve()
        if read_json(prepared/'manifest.json')['backend']=='native':
            exports.append(export_native_scalar(prepared,results,snapshot,request['run_id']))
        else:
            exports.append(export_spatial_light(prepared, results, folder / f'snapshot_{index:04d}', snapshot=snapshot,
                run_id=request['run_id'], max_receiver_emitter_pairs=request['limits']['max_receiver_emitter_pairs']))
    states = _join_observations(request, request_path.parent, exports, source_hashes)
    spatial = [r for export in exports for r in export['accounting_rows']]
    faces = bind_face_mappings(request.get('face_mappings', []), request_path.parent, spatial,
        {s['geometry_snapshot_id']:e['geometry_sha256'] for s, e in zip(request['snapshots'], exports)}, source_hashes)
    envelope, reference = load_attachment(request.get('reference_dli'), request_path.parent,
                                          {r['area_basis_id'] for r in spatial})
    context_plants = sorted({r['plant_instance_id'] for r in spatial})
    if reference is not None and reference['status'] == 'available' and not set(
            reference['plant_association']['accepted_plant_instance_ids']).issubset(context_plants):
        raise StudyError('reference_dli_plant_association_outside_context')
    copy_attachment(envelope, reference, folder, source_hashes)
    temporal = integrate_light_schedule(spatial, request['schedule'], dict(request['interval'], snapshots=request['snapshots'],
        max_schedule_minutes=request['limits']['max_schedule_minutes']))
    features = export_compound_light_features(spatial, [], temporal, states)
    dose = integrate_dose(features, temporal)
    availability: dict = {}
    tables = {'instance_map.csv':[r for export in exports for r in export['instances']], 'light_samples.csv':[r for r in spatial + temporal['samples'] if r['backend']=='direct'],
        'compound_light_features.csv':features, 'light_intervals.csv':temporal['intervals'], 'light_dose.csv':dose}
    for name, records in tables.items(): _table(folder, name, records, availability)
    transforms = {r['transform_id']: e['transforms'][r['plant_instance_id']] for e in exports for r in e['instances']}
    capabilities = dict(direct=dict(spatial='implemented', scalar='implemented', sides='normal_and_opposite_with_reviewed_biological_face_mapping',
        directional='implemented', local_regions='requires_reviewed_full_axis_transverse_and_partition', time='fixed_response_schedule'),
        native=dict(spatial='unavailable', scalar='imported_existing_hierarchy_results', sides='unavailable', directional='unavailable',
            time='equal_fixture_schedules_only_combined_response'), probes='not_implemented_opt_in_extension',
        reference_dli=REFERENCE_CAPABILITY,
        physical_validation='unavailable_independent_calibration_required', biological_prediction='not_performed')
    write_json(folder / 'schema.json', SCHEMA)
    write_json(folder / 'availability.json', availability)
    write_json(folder / 'transforms.json', transforms)
    write_json(folder / 'capabilities.json', capabilities)
    mapping = _consumer_mapping(states)
    mapping['growth']['reference_dli'] = reference_mapping(reference, envelope['result_ref'])
    write_json(folder / 'consumer_mapping.json', mapping)
    write_json(folder / 'reference_channel.json', envelope)
    write_json(folder / 'face_mappings.json', faces)
    write_json(folder / 'angular_diagnostics.json', {s['geometry_snapshot_id']: e.get('angular_diagnostics',
        dict(status='unavailable_native_angular_channels')) for s, e in zip(request['snapshots'], exports)})
    audit.update(time_gaps=temporal['gaps'], scalar_parity=[r for e in exports for r in e['scalar_parity']],
        feature_status=dict(spatial='direct_only' if any(e['backend']=='direct' for e in exports) else 'unavailable_native_spatial_channels',
            temporal='partial_geometry' if temporal['gaps'] else 'covered_geometry_quantity_availability_separate',
            observed_growth_join='reviewed' if states else 'unavailable_missing_reviewed_associations',
            angular='direct_actual_path_diagnostics_native_unavailable'), software_scope_complete=True)
    write_json(folder / 'audit.json', audit)
    for path, expected in source_hashes.items():
        if not Path(path).is_file() or file_hash(Path(path)) != expected: raise StudyError('source_changed_during_export:' + path)
    package = dict(schema_version=SCHEMA['schema_version'], run_id=request['run_id'], canopy_run_id=request['run_id'],
        created_at=datetime.now(timezone.utc).isoformat(), source_hashes=source_hashes,
        request_source_ref=dict(path=str(request_path), sha256=file_hash(request_path)),
        code_hashes={str(p.resolve()):file_hash(p) for p in (Path(__file__), SCHEMA_PATH,
            Path(__file__).with_name('light_time.py'),
            Path(__file__).with_name('light_face_evidence.py'),
            Path(__file__).with_name('light_geometry_evidence.py'),
            Path(__file__).with_name('light_reference_channel.py'), Path(__file__).with_name('reference_dli_consumer.py'),
            Path(__file__).with_name('light_growth_consumer.py'), Path(__file__).with_name('light_direction_diagnostics.py'),
            Path(__file__).with_name('compound_growth.py'))},
        artifact_hashes={str(p.relative_to(folder)):file_hash(p) for p in folder.rglob('*') if p.is_file()},
        optical_geometry_contract=GEOMETRY_EVIDENCE_VERSION,
        geometry_validity=request['snapshots'], requested_interval=request['interval'], schedule=request['schedule'],
        reference_context_plant_instance_ids=context_plants,
        native_sources=[e['native_source'] for e in exports if e['backend']=='native'],
        context_geometry_hashes={s['geometry_snapshot_id']:e['geometry_sha256'] for s,e in zip(request['snapshots'],exports)},
        units_and_frames=SCHEMA['conventions'], spectral_bands=sorted({e['spectral_band'] for e in exports}),
        uncertainty=dict(geometry='uncalibrated',optics='uncalibrated',numerical=POLICY,
            monte_carlo='native_replicates_retained_no_new_uncertainty_estimator' if any(e['backend']=='native' for e in exports) else 'not_applicable_direct_deterministic'),
        software_scope_complete=True, directional_readiness=any(e['backend']=='direct' for e in exports), physical_validation=False, growth_prediction=False)
    write_json(folder / 'package.json', package)
    return package


def validate_growth_light_package(package: Path) -> dict:
    from tools.light_growth_consumer import validate_package
    return validate_package(package)


def split_canopy_results(package: Path, instance_id: str, out: Path) -> dict:
    """Reporting-only split: retain run/context provenance; never rerun transport."""
    from tools.light_growth_consumer import load_tables
    check = validate_growth_light_package(package)
    if not check['valid']: raise StudyError('invalid_package:' + ';'.join(check['errors']))
    tables = load_tables(package); source = read_json(package / 'package.json')
    if instance_id not in {r['plant_instance_id'] for r in tables['instance_map.csv']}:
        raise StudyError('unknown_split_instance')
    folder = output_dir(out); availability = read_json(package / 'availability.json')
    for name, records in tables.items():
        selected = records if name == 'light_intervals.csv' else [r for r in records if r['plant_instance_id'] == instance_id]
        write_rows(folder / name, selected, [c['name'] for c in SCHEMA['tables'][name]['columns']])
    for name in SCHEMA['required_json']:
        if name == 'package.json': continue
        write_json(folder / name, read_json(package / name))
    if (package/'reference_dli').is_dir():
        shutil.copytree(package/'reference_dli', folder/'reference_dli')
    result = dict(source, split_instance_id=instance_id, split_kind='report_only_full_canopy_shading',
        parent_package_sha256=file_hash(package / 'package.json'), parent_package=str(package.resolve()),
        source_hashes={**source['source_hashes'], str((package / 'package.json').resolve()):file_hash(package / 'package.json')},
        artifact_hashes={str(p.relative_to(folder)):file_hash(p) for p in folder.rglob('*') if p.is_file()})
    write_json(folder / 'package.json', result)
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('command', choices=('schema', 'audit', 'export', 'validate', 'split'))
    parser.add_argument('--input', type=Path)
    parser.add_argument('--out', type=Path)
    parser.add_argument('--instance')
    args = parser.parse_args()
    if args.command == 'schema':
        print(json.dumps(SCHEMA, indent=2))
        return
    if args.input is None: parser.error('--input required')
    if args.command == 'validate':
        result = validate_growth_light_package(args.input)
        print(json.dumps(result, indent=2)); raise SystemExit(0 if result['valid'] else 1)
    if args.out is None: parser.error('--out required')
    if args.command == 'audit':
        result = audit_growth_light_inputs(args.input); folder = output_dir(args.out); write_json(folder / 'audit.json', result)
    elif args.command == 'split':
        if not args.instance: parser.error('--instance required')
        result = split_canopy_results(args.input, args.instance, args.out)
    else:
        result = build_package(args.input, args.out)
    print(json.dumps(dict(output=str(args.out), status=result.get('feature_status', 'written')), indent=2))


if __name__ == '__main__':
    main()
