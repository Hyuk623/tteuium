"""Audited retained-target light counterfactuals. Run python -m tools.hierarchical_light --help."""
from __future__ import annotations

import argparse
from copy import deepcopy
from collections import defaultdict
from dataclasses import dataclass, replace
from datetime import date
import itertools
import json
import math
from pathlib import Path
from typing import Any

import numpy as np

from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS
from tomato3d.light.geometry import load_geometry, place_in_grow_frame, triangle_areas_mm2
from tomato3d.light.pipeline import build_occluders, leaf_receivers
from tomato3d.light.raytrace import Occluders, Receivers, direct_light
from tomato3d.light.scene import load_scene, resolve_scenario
from tools.canopy_light import materialize_case
from tools.groimp_density import surface_gate
from tools.leaf_light.common import (ROOT, StudyError, digest, file_hash, output_dir,
                                     read_json, rows, write_json, write_rows)

SCHEMA = 'hierarchical-light-1'
MEMBERSHIP = ('source_plant_id', 'plant_instance_id', 'session_id', 'capture_date',
              'geometry_variant_id', 'organ_id', 'leaflet_id', 'compound_id',
              'identity_status', 'evidence_path', 'evidence_sha256')
SUBSETS = ('empty', 'A', 'B', 'AB', 'C', 'AC', 'BC', 'ABC')
BITS = {'A': 1, 'B': 2, 'C': 4}
QUANTITIES = ('received', 'absorbed')
MISSING = ('', 'unavailable', 'unknown')
METHOD = 'three-group-shapley-v1'


def path_at(base: Path, value: str) -> Path:
    return (base / value).resolve()


def finite(value: Any) -> float | None:
    return float(value) if value is not None and math.isfinite(float(value)) else None


def strict_sum(values: list[float | None]) -> float | None:
    return sum(values) if values and all(v is not None for v in values) else None


def ratio(a: float | None, b: float | None) -> float | None:
    return a / b if a is not None and b is not None and b > 0 else None


def token(value: Any) -> str:
    return digest(value)[:24]


def code_hashes() -> dict[str, str]:
    files = [Path(__file__), Path(__file__).with_suffix('.html'),
             ROOT / 'tools/hierarchical_light_native.py', ROOT / 'tools/canopy_light.py',
             ROOT / 'tools/groimp_density.py', ROOT / 'tools/ppfd_validation.py',
             ROOT / 'tools/groimp_light_sanity.py', ROOT / 'tools/leaf_light/common.py',
             ROOT / 'tomato3d/io/schemas.py']
    files += list((ROOT / 'tomato3d/light').glob('*.py'))
    return {str(p.resolve()): file_hash(p) for p in files if p.is_file()}


def audit_inputs(manifest_path: Path) -> dict:
    """Read-only audit; structural/optical/identity availability have separate states."""
    manifest_path = manifest_path.resolve()
    report: dict = dict(schema_version=SCHEMA, transport_blockers=[], hierarchy_issues=[],
                        warnings=[], source_hashes={}, surface_reviews=[], validated_metric=False,
                        suitable_for_ppfd=False)
    def track(p: Path) -> None:
        if not p.is_file():
            raise StudyError(f'missing_input:{p}')
        report['source_hashes'][str(p)] = file_hash(p)
    try:
        track(manifest_path)
        plan = read_json(manifest_path)
        report['plan'] = plan
        if plan.get('schema_version') != SCHEMA:
            raise StudyError('unsupported_manifest_schema')
        case = plan['case']
        base = manifest_path.parent
        if case.get('data_kind') not in ('observed_geometry', 'hypothetical_layout', 'synthetic'):
            raise StudyError('explicit_data_kind_required')
        for name in ('scene', 'geometry', 'membership'):
            track(path_at(base, case[name]))
        scene = load_scene(path_at(base, case['scene']))
        # Match canopy_light.materialize_case semantics before auditing overrides.
        from tomato3d.io.schemas import LightScene
        effective = scene.model_dump(mode='json')
        originals = {p['plant_id']: p for p in effective['plants']}
        effective['plants'] = [dict(deepcopy(item.get('placement', originals.get(item['source_plant_id'], {}))),
                                    plant_id=item['plant_id']) for item in case['instances']]
        if 'scenarios' in case:
            effective['scenarios'] = case['scenarios']
        resolved = resolve_scenario(LightScene.model_validate(effective), plan['scenario_id'])
        from tomato3d.light.scene import input_records
        report['light_inputs'] = [r.model_dump(mode='json') for r in input_records(resolved.scene)]
        if scene.ambient_light == 'present_not_modelled':
            report['warnings'].append('ambient_light_present_but_not_modelled')
        if not resolved.fixtures:
            raise StudyError('no_enabled_fixtures')
        if any(f.fixture_id == 'all' for f in resolved.fixtures):
            raise StudyError('fixture_id_all_is_reserved_for_aggregation')
        for state in resolved.fixtures:
            if state.missing_inputs:
                report['warnings'].append(f'fixture_unavailable:{state.fixture_id}:{state.missing_inputs}')
        for name in ('transmittance', 'absorptance'):
            if getattr(scene.leaf_optics, name).value is None:
                report['warnings'].append(f'leaf_{name}_unavailable')
        surfaces = load_geometry([path_at(base, case['geometry'])])[case['geometry_variant_id']]
        instances = case['instances']
        ids = [i['plant_id'] for i in instances]
        if not ids or len(ids) != len(set(ids)):
            raise StudyError('missing_or_duplicate_instance_ids')
        source_ids = {i['source_plant_id'] for i in instances}
        if source_ids != set(surfaces.plant_ids):
            raise StudyError('foreign_or_missing_source_plant_geometry')
        dates, origins = [], []
        for item in instances:
            pid = item['plant_id']
            source = item['source_plant_id']
            snapshot = item['capture_date']
            date.fromisoformat(snapshot)
            dates.append(snapshot)
            if case['data_kind'] == 'observed_geometry' and source != pid:
                raise StudyError('copied_instance_requires_hypothetical_layout')
            review = item.get('surface_review', case.get('surface_review'))
            if not review:
                raise StudyError(f'missing_surface_review:{pid}')
            track(path_at(base, review))
            gate = dict(geometry=case['geometry'], surface_review=review,
                        geometry_variant_id=case['geometry_variant_id'], snapshot_date=snapshot,
                        data_kind=case['data_kind'], instances=[item])
            blockers, evidence = surface_gate(gate, base)
            report['transport_blockers'].extend(f'{pid}:{b}' for b in blockers)
            report['surface_reviews'].append(dict(plant_instance_id=pid, **evidence))
            placement_obj = resolved.placements.get(pid)
            if placement_obj is None:
                raise StudyError(f'missing_placement:{pid}')
            placement = placement_obj.model_dump(mode='json')
            from tomato3d.io.schemas import PlantPlacement
            parsed = PlantPlacement.model_validate(dict(placement, plant_id=pid))
            if parsed.board_origin_grow_mm.value is None or parsed.board_yaw_deg.value is None:
                raise StudyError(f'unavailable_placement:{pid}')
            origin = tuple(parsed.board_origin_grow_mm.value)
            if origin in origins:
                raise StudyError('duplicate_board_origins')
            origins.append(origin)
            if parsed.posture_since_capture != 'unchanged_checked':
                report['warnings'].append(f'posture_not_confirmed:{pid}')
            if case['data_kind'] == 'observed_geometry' and parsed.posture_since_capture != 'unchanged_checked':
                report['transport_blockers'].append(f'observed_posture_not_confirmed:{pid}')
        if len(set(dates)) > 1 and case['data_kind'] == 'observed_geometry':
            raise StudyError('mixed_dates_require_hypothetical_layout')
        # Exact duplicate faces inflate area even when IDs differ. Vertex order is irrelevant.
        seen_faces: set = set()
        for i, verts in enumerate(surfaces.vertices_board_mm):
            face = (surfaces.plant_ids[i], tuple(sorted(map(tuple, verts.tolist()))))
            if face in seen_faces:
                raise StudyError('duplicate_geometry_face')
            seen_faces.add(face)
        membership = rows(path_at(base, case['membership']), MEMBERSHIP)
        lookup: dict = {}
        expected = set()
        for item in instances:
            for i, source in enumerate(surfaces.plant_ids):
                if source == item['source_plant_id'] and surfaces.is_receiver[i]:
                    expected.add((item['plant_id'], surfaces.session_ids[i],
                                  surfaces.organ_ids[i], surfaces.leaflet_ids[i]))
        for row in membership:
            key = tuple(row[n] for n in ('plant_instance_id', 'session_id', 'organ_id', 'leaflet_id'))
            if key in lookup:
                raise StudyError(f'duplicate_membership:{key}')
            if key not in expected:
                raise StudyError(f'foreign_membership:{key}')
            item = next(i for i in instances if i['plant_id'] == row['plant_instance_id'])
            for field, wanted in [('source_plant_id', item['source_plant_id']),
                                  ('session_id', item['source_session_id']),
                                  ('capture_date', item['capture_date']),
                                  ('geometry_variant_id', case['geometry_variant_id'])]:
                if row[field] != wanted:
                    raise StudyError(f'membership_{field}_mismatch:{key}')
            accepted = row['identity_status'] == 'reviewed' or (
                row['identity_status'] == 'synthetic' and case['data_kind'] == 'synthetic')
            if accepted and row['compound_id'] not in MISSING:
                evidence = path_at(base, row['evidence_path']) if row['evidence_path'] else None
                if evidence is None or not evidence.is_file():
                    accepted = False
                else:
                    track(evidence)
                    if file_hash(evidence) != row['evidence_sha256']:
                        raise StudyError(f'identity_evidence_hash_mismatch:{key}')
            else:
                accepted = False
            lookup[key] = dict(row, hierarchy_ready=accepted)
        for key in expected:
            if key[-1] in MISSING:
                raise StudyError(f'missing_physical_leaflet_id:{key}')
            if key not in lookup or not lookup[key]['hierarchy_ready']:
                report['hierarchy_issues'].append(dict(key=list(key), reason='unreviewed_compound_membership'))
        report['membership'] = list(lookup.values())
        report['fixed_background'] = []
        if plan.get('background_csv'):
            from tools.ppfd_validation import RIG_SURFACE_COLUMNS, rig_surface_triangles, surface_optics
            p = path_at(base, plan['background_csv']); track(p)
            background = rows(p, RIG_SURFACE_COLUMNS)
            if len({r['surface_id'] for r in background}) != len(background):
                raise StudyError('duplicate_background_id')
            for row in background:
                if row['role'] == 'display_only':
                    continue
                if row['role'] not in ('rig', 'physical_occluder'):
                    raise StudyError('unsupported_background_role')
                rig_surface_triangles(row); surface_optics(row)
                if row['geometry_status'] in MISSING or row['optics_status'] in MISSING:
                    raise StudyError('background_provenance_unavailable')
                if not row['geometry_source'] or not row['optics_source']:
                    raise StudyError('background_source_required')
                report['fixed_background'].append(row)
        report['resolved_placements'] = {k: p.model_dump(mode='json') for k, p in resolved.placements.items()}
        report['simulation'] = resolved.scene.simulation.model_dump(mode='json')
        report['warnings'].append('direct_backend_excludes_all_reflections_and_models_transmission_without_scattering')
        for name in ('max_transport_calls', 'max_receiver_emitter_pairs'):
            if type(plan['limits'].get(name)) is not int or plan['limits'][name] < 1:
                raise StudyError(f'explicit_positive_limit_required:{name}')
        if plan.get('heterogeneous_leaf_optics'):
            raise StudyError('heterogeneous_leaf_optics_unsupported')
    except (ValueError, KeyError, TypeError, OSError) as exc:
        report['transport_blockers'].append(str(exc))
    report['transport_ready'] = not report['transport_blockers']
    report['hierarchy_ready'] = report['transport_ready'] and not report['hierarchy_issues']
    return report


@dataclass
class Context:
    surfaces: Any
    vertices: np.ndarray
    resolved: Any
    receivers: Receivers
    occluders: Occluders
    weights_m2: np.ndarray
    targets: dict[str, dict]
    triangle_targets: list[str]
    background: list[dict]


def load_context(folder: Path, manifest: dict) -> Context:
    plan = manifest['plan']
    s = load_geometry([folder / 'leaf_surfaces.csv'])[plan['case']['geometry_variant_id']]
    resolved = resolve_scenario(load_scene(folder / 'scene.json'), plan['scenario_id'])
    vertices = place_in_grow_frame(s, resolved.placements)
    memberships = {tuple(r[k] for k in ('plant_instance_id', 'session_id', 'organ_id', 'leaflet_id')): r
                   for r in manifest['audit'].get('membership', [])}
    targets, triangle_targets = {}, []
    areas = triangle_areas_mm2(vertices) * 1e-6
    for i in range(s.n_triangles):
        key = (s.plant_ids[i], s.session_ids[i], s.organ_ids[i], s.leaflet_ids[i])
        tid = token(key)
        triangle_targets.append(tid)
        member = memberships.get(key, {})
        item = next(x for x in plan['case']['instances'] if x['plant_id'] == key[0])
        if tid not in targets:
            targets[tid] = dict(target_id=tid, plant_instance_id=key[0], session_id=key[1],
                                organ_id=key[2], leaflet_id=key[3],
                                source_plant_id=item['source_plant_id'], capture_date=item['capture_date'],
                                compound_id=member.get('compound_id', 'unavailable'),
                                hierarchy_ready=member.get('hierarchy_ready', False),
                                area_m2=0., triangles=[])
        targets[tid]['area_m2'] += float(areas[i]); targets[tid]['triangles'].append(i)
    receivers, _ = leaf_receivers(s, vertices, resolved.scene.simulation.triangle_subdivisions)
    counts = np.bincount(receivers.own_triangle, minlength=s.n_triangles)
    weights = areas[receivers.own_triangle] / counts[receivers.own_triangle]
    # Namespace optical organ IDs with session without changing source/output IDs.
    optical_s = replace(s, organ_ids=tuple(token((s.session_ids[i], s.organ_ids[i]))
                                          for i in range(s.n_triangles)))
    occ = build_occluders(optical_s, vertices)
    background = manifest['audit'].get('fixed_background', [])
    if background:
        from tools.ppfd_validation import rig_surface_triangles
        v = np.concatenate([rig_surface_triangles(r) for r in background])
        start = int(occ.surface_code.max()) + 1
        occ = Occluders(np.concatenate([occ.vertices_grow_mm, v]),
                        np.concatenate([occ.is_leaf, np.zeros(len(v), dtype=bool)]),
                        np.concatenate([occ.surface_code, np.arange(start, start + len(v))]),
                        np.concatenate([occ.group, np.full(len(v), int(occ.group.max()) + 1)]))
    return Context(s, vertices, resolved, receivers, occ, weights, targets, triangle_targets, background)


def build_target_groups(context: Context, target_key: str) -> dict:
    target = context.targets[target_key]
    groups = {g: [] for g in BITS}
    issues = []
    if not target['hierarchy_ready']:
        issues.append('target_compound_membership_unavailable')
    for tid, other in context.targets.items():
        if tid == target_key:
            continue
        if other['plant_instance_id'] != target['plant_instance_id']:
            groups['C'].extend(other['triangles'])
        elif not target['hierarchy_ready'] or not other['hierarchy_ready']:
            issues.append(f'compound_membership_unavailable:{tid}')
        else:
            group = 'A' if other['compound_id'] == target['compound_id'] else 'B'
            groups[group].extend(other['triangles'])
    return dict(groups=groups, issues=sorted(set(issues)))


def entity_groups(context: Context, level: str) -> dict[str, dict]:
    entities: dict = {}
    for tid, target in context.targets.items():
        if level == 'compound' and not target['hierarchy_ready']:
            continue
        key = [target['plant_instance_id']]
        if level == 'compound':
            key += [target['session_id'], target['compound_id']]
        if level == 'leaflet':
            key = [tid]
        eid = token([level, key])
        if eid not in entities:
            entities[eid] = dict(entity_id=eid, level=level, plant_instance_id=target['plant_instance_id'],
                                 compound_id=target['compound_id'] if level != 'plant' else '',
                                 leaflet_id=target['leaflet_id'] if level == 'leaflet' else '',
                                 targets=[], triangles=[])
        entities[eid]['targets'].append(tid); entities[eid]['triangles'].extend(target['triangles'])
    for entity in entities.values():
        entity['membership_complete'] = level != 'compound' or all(
            t['hierarchy_ready'] for t in context.targets.values()
            if t['plant_instance_id'] == entity['plant_instance_id'])
    return entities


def prepare_subset_cases(manifest_path: Path, out: Path, backend: str = 'direct') -> dict:
    audit = audit_inputs(manifest_path)
    folder = output_dir(out)
    write_json(folder / 'audit.json', audit)
    manifest = dict(schema_version=SCHEMA, backend=backend, status='blocked', audit=audit,
                    plan=audit.get('plan', {}), source_hashes=audit['source_hashes'], code_hashes=code_hashes(),
                    validated_metric=False, suitable_for_ppfd=False, allocation_method=METHOD,
                    quantity_convention='two_face_received_per_supported_one_sided_area',
                    reference='sum_of_target_specific_counterfactuals', cases=[], matrix_requests=[])
    if audit['transport_ready']:
        plan = manifest['plan']
        case = plan['case']
        # Materializer owns placement/copy semantics; use scenario placements consistently.
        materialize_case(case, manifest_path.resolve().parent, folder)
        context = load_context(folder, manifest)
        manifest['targets'] = context.targets
        selected = plan.get('target_ids') or list(context.targets)
        if not set(selected).issubset(context.targets):
            raise StudyError('unknown_target_filter')
        manifest['selected_targets'] = selected
        all_indices = set(range(context.surfaces.n_triangles))
        cases: dict[str, dict] = {}
        def add(retained: set[int], request: dict) -> str:
            ids = sorted(retained)
            cid = token(ids)
            if cid not in cases:
                cases[cid] = dict(case_id=cid, retained=ids, requests=[])
            cases[cid]['requests'].append(request)
            return cid
        manifest['full_case'] = add(all_indices, dict(kind='full'))
        for tid in selected:
            partition = build_target_groups(context, tid)
            context.targets[tid]['hierarchy_issues'] = partition['issues']
            for mask, subset in enumerate(SUBSETS):
                if partition['issues'] and mask not in (0, 7):
                    continue
                retain = set(context.targets[tid]['triangles'])
                if mask == 7:
                    retain = all_indices
                else:
                    for g, bit in BITS.items():
                        if mask & bit:
                            retain.update(partition['groups'][g])
                add(retain, dict(kind='subset', target_id=tid, subset=subset))
        known_sources = set()
        for level in ('leaflet', 'compound', 'plant'):
            entities = entity_groups(context, level)
            known_sources.update(entities)
            for sid, source in entities.items():
                source_filter = plan.get('source_entity_ids')
                if source_filter and sid not in source_filter:
                    continue
                cid = add(all_indices - set(source['triangles']), dict(kind='source_removal', level=level, source_id=sid)) if source['membership_complete'] else None
                for eid, target in entities.items():
                    target_ids = [t for t in target['targets'] if t in selected]
                    if not target_ids:
                        continue
                    manifest['matrix_requests'].append(dict(level=level, source_id=sid, target_id=eid,
                        source=source, target=target, receiver_targets=target_ids,
                        case_id=cid if sid != eid and target['membership_complete'] else None,
                        definition=('unavailable_self_removal' if sid == eid else
                                    'full_background_removal' if source['membership_complete'] and target['membership_complete']
                                    else 'unavailable_compound_membership')))
        if plan.get('source_entity_ids') and not set(plan['source_entity_ids']).issubset(known_sources):
            raise StudyError('unknown_source_filter')
        manifest['cases'] = list(cases.values())
        emitters = sum(len(f.emitters.positions_grow_mm) for f in context.resolved.fixtures if f.emitters is not None)
        pairs = len(context.receivers.points_grow_mm) * emitters * len(cases)
        manifest['cost'] = dict(transport_calls=len(cases), receiver_emitter_pairs=pairs,
                                receiver_samples=len(context.receivers.points_grow_mm))
        if len(cases) > plan['limits']['max_transport_calls'] or pairs > plan['limits']['max_receiver_emitter_pairs']:
            raise StudyError(f'calculation_budget_exceeded:{manifest["cost"]}')
        manifest['status'] = 'prepared'
        if backend == 'native':
            from tools.hierarchical_light_native import prepare_native
            prepare_native(folder, manifest, context)
        elif any(float(r['transmittance']) != 0 for r in context.background):
            manifest['status'] = 'blocked'
            audit['transport_blockers'].append('direct_background_transmission_unsupported')
            audit['transport_ready'] = audit['hierarchy_ready'] = False
        manifest['geometry_view'] = [dict(target_id=tid, vertices_grow_mm=context.vertices[i].tolist())
                                     for i, tid in enumerate(context.triangle_targets)]
    audit['backend'] = backend
    audit['backend_blockers'] = manifest.get('native_blockers', [])
    write_json(folder / 'audit.json', audit)
    manifest['artifact_hashes'] = {**manifest.get('artifact_hashes', {}),
                                  **{p.name: file_hash(p) for p in folder.iterdir() if p.is_file()}}
    write_json(folder / 'manifest.json', manifest)
    return manifest


def stale(folder: Path) -> dict:
    manifest = read_json(folder / 'manifest.json')
    changed = []
    for field in ('source_hashes', 'code_hashes', 'artifact_hashes'):
        for name, expected in manifest.get(field, {}).items():
            p = folder / name if field == 'artifact_hashes' else Path(name)
            if not p.is_file() or file_hash(p) != expected:
                changed.append(dict(kind=field, path=str(p)))
    return dict(stale=bool(changed), changed=changed)


def require_fresh(folder: Path) -> dict:
    state = stale(folder)
    if state['stale']:
        raise StudyError(f'stale_inputs_or_artifacts:{state["changed"]}')
    return read_json(folder / 'manifest.json')


def filtered_transport(context: Context, retained: list[int]) -> tuple[Receivers, Occluders, np.ndarray]:
    """Retain background and correctly map own indices into the filtered occluders."""
    indices = np.array(retained + list(range(context.surfaces.n_triangles,
                                             len(context.occluders.vertices_grow_mm))), dtype=int)
    remap = np.full(len(context.occluders.vertices_grow_mm), -1, dtype=int)
    remap[indices] = np.arange(len(indices))
    active = np.isin(context.receivers.own_triangle, retained)
    r = context.receivers
    receivers = Receivers(r.points_grow_mm[active], r.unit_normals[active], r.two_sided,
                          remap[r.own_triangle[active]])
    o = context.occluders
    occluders = Occluders(o.vertices_grow_mm[indices], o.is_leaf[indices],
                          o.surface_code[indices], o.group[indices])
    return receivers, occluders, active


def calculate_direct(prepared: Path, out: Path) -> dict:
    manifest = require_fresh(prepared)
    if manifest['status'] != 'prepared' or manifest['backend'] != 'direct':
        raise StudyError('prepared_direct_run_required')
    context = load_context(prepared, manifest)
    manifest['source_hashes'][str((prepared / 'manifest.json').resolve())] = file_hash(prepared / 'manifest.json')
    outputs = {}
    for case in manifest['cases']:
        receivers, occluders, active = filtered_transport(context, case['retained'])
        direct = direct_light(receivers, context.resolved.fixtures, occluders,
                              context.resolved.scene.leaf_optics.transmittance.value,
                              context.resolved.scene.simulation)
        own = context.receivers.own_triangle[active]
        weights = context.weights_m2[active]
        results: dict = {}
        for tid, target in context.targets.items():
            select = np.isin(own, target['triangles'])
            if not select.any():
                continue
            received = [finite(np.sum(v[select] * weights[select])) for v in direct.ppfd_umol_m2_s]
            alpha = context.resolved.scene.leaf_optics.absorptance.value
            scopes = list(zip(direct.fixture_ids, received)) + [('all', strict_sum(received))]
            for fixture, q in scopes:
                results.setdefault(tid, {})[fixture] = dict(received=q,
                    absorbed=q * alpha if q is not None and alpha is not None else None)
        outputs[case['case_id']] = results
    return write_report(manifest, [dict(replicate='deterministic', seed=None, values=outputs)], out)


def attribution(values: dict[str, float | None]) -> dict:
    """Exact arithmetic on the eight counterfactuals, preserving signed effects."""
    q = [values.get(s) for s in SUBSETS]
    baseline, full = q[0], q[7]
    total = baseline - full if baseline is not None and full is not None else None
    result = dict(baseline_umol_s=baseline, full_umol_s=full, total_loss_umol_s=total,
                  loss_fraction=ratio(total, baseline))
    complete = all(v is not None for v in q)
    for group, bit in BITS.items():
        result[f'standalone_{group}_umol_s'] = baseline - q[bit] if baseline is not None and q[bit] is not None else None
        result[f'marginal_{group}_umol_s'] = q[7 ^ bit] - full if full is not None and q[7 ^ bit] is not None else None
        phi = None
        if complete:
            phi = 0.
            for mask in range(8):
                if not mask & bit:
                    n = mask.bit_count()
                    phi += math.factorial(n) * math.factorial(2 - n) / 6 * (q[mask] - q[mask | bit])
        result[f'shapley_{group}_umol_s'] = phi
    for mask in range(1, 8):
        result[f'overlap_{SUBSETS[mask]}_umol_s'] = sum(
            (-1) ** (mask.bit_count() - sub.bit_count()) * (baseline - q[sub])
            for sub in range(8) if sub & mask == sub) if complete else None
    result['attribution_status'] = 'computed' if complete else 'unavailable'
    return result


def attribute_groups(case_rows: list[dict], targets: dict) -> list[dict]:
    grouped: dict = defaultdict(dict)
    for row in case_rows:
        grouped[(row['replicate'], row['seed'], row['target_id'], row['fixture_id'])][row['subset']] = row
    result = []
    for (replicate, seed, tid, fixture), subset in grouped.items():
        target = targets[tid]
        for quantity in QUANTITIES:
            values = {s: r[f'{quantity}_umol_s'] for s, r in subset.items()}
            metrics = attribution(values)
            for name, value in list(metrics.items()):
                if name.endswith('_umol_s'):
                    metrics[name.replace('_umol_s', '_umol_m2_s')] = ratio(value, target['area_m2'])
            result.append(dict(**{k: v for k, v in target.items() if k not in ('triangles', 'hierarchy_issues')},
                replicate=replicate, seed=seed, fixture_id=fixture, quantity=quantity, **metrics,
                reason=(';'.join(target.get('hierarchy_issues', [])) or 'transport_or_optics_unavailable') if metrics['attribution_status'] != 'computed'
                       else '', allocation_method=METHOD))
    return result


def aggregate_receivers(records: list[dict], level: str) -> list[dict]:
    grouped = defaultdict(list)
    for row in records:
        group = row['plant_instance_id']
        if level == 'compound':
            group = (group, row['session_id'], row['compound_id'] if row['hierarchy_ready'] else 'unassigned')
        grouped[(row['replicate'], row['fixture_id'], row['quantity'], group)].append(row)
    out = []
    for (_, _, _, group), sub in grouped.items():
        first = sub[0]
        record = {k: first[k] for k in ('replicate', 'seed', 'fixture_id', 'quantity', 'plant_instance_id')}
        record.update(level=level, compound_id=group[-1] if level == 'compound' else '',
                      area_m2=sum(r['area_m2'] for r in sub), n_leaflets=len(sub),
                      reference='sum_of_target_specific_counterfactuals', allocation_method=METHOD)
        for name in first:
            if name.endswith('_umol_s'):
                value = strict_sum([r[name] for r in sub])
                record[name] = value
                record[name.replace('_umol_s', '_umol_m2_s')] = ratio(value, record['area_m2'])
        record['loss_fraction'] = ratio(record['total_loss_umol_s'], record['baseline_umol_s'])
        record['attribution_status'] = 'computed' if all(r['attribution_status'] == 'computed' for r in sub) else 'unavailable'
        record['reason'] = ';'.join(sorted(set(r['reason'] for r in sub if r['reason'])))
        out.append(record)
    return out


def calculate_source_target(manifest: dict, runs: list[dict]) -> list[dict]:
    result = []
    for run in runs:
        values = run['values']
        for req in manifest['matrix_requests']:
            tids = req['receiver_targets']
            area = sum(manifest['targets'][t]['area_m2'] for t in tids)
            for quantity in QUANTITIES:
                full = strict_sum([values.get(manifest['full_case'], {}).get(t, {}).get('all', {}).get(quantity) for t in tids])
                without = strict_sum([values.get(req['case_id'], {}).get(t, {}).get('all', {}).get(quantity) for t in tids]) if req['case_id'] else None
                effect = without - full if without is not None and full is not None else None
                result.append(dict(level=req['level'], source_id=req['source_id'], target_id=req['target_id'],
                    source_label='/'.join(str(req['source'][k]) for k in ('plant_instance_id', 'compound_id', 'leaflet_id') if req['source'][k]),
                    target_label='/'.join(str(req['target'][k]) for k in ('plant_instance_id', 'compound_id', 'leaflet_id') if req['target'][k]),
                    target_selection='all_supported_entity_leaflets' if set(tids) == set(req['target']['targets']) else 'selected_leaflets_only',
                    n_receiver_leaflets=len(tids), n_entity_leaflets=len(req['target']['targets']),
                    receiver_target_ids=';'.join(tids), replicate=run['replicate'], seed=run['seed'], quantity=quantity,
                    fixture_id='all', area_m2=area, full_umol_s=full, without_source_umol_s=without,
                    effect_umol_s=effect, effect_umol_m2_s=ratio(effect, area), definition=req['definition'],
                    status='computed' if effect is not None else 'unavailable',
                    reason='' if effect is not None else (req['definition'] if not req['case_id'] else 'missing_transport_result'),
                    additive=False, fixed_background='all_declared_background'))
    return result


def write_csv(path: Path, records: list[dict]) -> None:
    columns = list(dict.fromkeys(k for row in records for k in row)) or ['status', 'reason']
    write_rows(path, records, columns)


def write_report(manifest: dict, runs: list[dict], out: Path) -> dict:
    folder = output_dir(out)
    case_rows = []
    scopes = sorted({f for run in runs for case in run['values'].values() for t in case.values() for f in t}) or ['all']
    # Include every required subset, even those blocked by hierarchy evidence.
    requests = {(r['target_id'], r['subset']): c['case_id'] for c in manifest['cases']
                for r in c['requests'] if r['kind'] == 'subset'}
    for run in runs:
        for tid in manifest['selected_targets']:
            target = manifest['targets'][tid]
            for subset, fixture in itertools.product(SUBSETS, scopes):
                cid = requests.get((tid, subset))
                value = run['values'].get(cid, {}).get(tid, {}).get(fixture, {})
                q, a = value.get('received'), value.get('absorbed')
                case_rows.append(dict(target_id=tid, **{k: target[k] for k in (
                    'plant_instance_id', 'source_plant_id', 'session_id', 'capture_date', 'compound_id', 'leaflet_id', 'area_m2')},
                    scenario_id=manifest['plan']['scenario_id'], backend=manifest['backend'], fixture_id=fixture,
                    replicate=run['replicate'], seed=run['seed'], case_id=cid, subset=subset,
                    received_umol_s=q, absorbed_umol_s=a, ppfd_umol_m2_s=ratio(q, target['area_m2']),
                    absorbed_umol_m2_s=ratio(a, target['area_m2']),
                    status='computed' if q is not None else 'unavailable',
                    absorbed_status='computed' if a is not None else 'unavailable',
                    reason='' if q is not None else ('membership_unavailable' if cid is None else 'transport_or_optics_unavailable')))
    leaf = attribute_groups(case_rows, manifest['targets'])
    compound, plant = aggregate_receivers(leaf, 'compound'), aggregate_receivers(leaf, 'plant')
    matrix = calculate_source_target(manifest, runs)
    tables = dict(interaction_cases=case_rows, leaflet_interactions=leaf,
                  compound_interactions=compound, plant_interactions=plant, source_target_interactions=matrix)
    # Native uncertainty is computed on paired replicate differences/allocations, never on independent means.
    uncertainty = []
    for name, table in tables.items():
        if name == 'interaction_cases':
            continue
        grouped = defaultdict(list)
        for row in table:
            key = tuple((k, str(row[k])) for k in ('target_id', 'source_id', 'level', 'plant_instance_id',
                                                   'compound_id', 'leaflet_id', 'fixture_id', 'quantity') if k in row)
            grouped[key].append(row)
        for key, records in grouped.items():
            for metric in records[0]:
                if metric.endswith('_umol_s'):
                    vals = [r[metric] for r in records]
                    valid = all(v is not None for v in vals)
                    uncertainty.append(dict(table=name, **dict(key), metric=metric,
                        n_replicates=len(vals), mean=float(np.mean(vals)) if valid else None,
                        paired_replicate_standard_error=float(np.std(vals, ddof=1) / math.sqrt(len(vals))) if valid and len(vals) > 1 else None,
                        status='estimated' if valid and len(vals) > 1 else 'unavailable',
                        reason='' if valid and len(vals) > 1 else 'requires_complete_multiple_replicates'))
    tables['replicate_summary'] = uncertainty
    for name, records in tables.items():
        for record in records:
            record.update(run_id=folder.name, scenario_id=manifest['plan']['scenario_id'], backend=manifest['backend'])
        write_csv(folder / f'{name}.csv', records)
    report = dict(schema_version=SCHEMA, status='calculated', backend=manifest['backend'],
                  validated_metric=False, suitable_for_ppfd=False, manifest=manifest, tables=tables,
                  limitations=['Supported surfaces only; no extrapolation to missing tissue.',
                               'Shapley is model accounting. Source-removal effects are nonadditive.',
                               'Received light is not photosynthesis or unique conserved photons.'])
    write_json(folder / 'results.json', report)
    write_json(folder / 'audit.json', manifest['audit'])
    html = Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    html = html.replace('/*RESULT_DATA*/null', json.dumps(report, ensure_ascii=False, allow_nan=False).replace('<', '\\u003c'))
    (folder / 'viewer.html').write_text(html, encoding='utf-8')
    result_manifest = dict(manifest, run_id=folder.name, status='calculated', artifact_hashes={p.name: file_hash(p) for p in folder.iterdir() if p.is_file()})
    write_json(folder / 'manifest.json', result_manifest)
    return report


def templates(out: Path) -> dict:
    folder = output_dir(out)
    plan = dict(schema_version=SCHEMA, scenario_id='as_built',
        case=dict(case_id='user_case', data_kind='observed_geometry', scene='scene.json',
                  geometry='leaf_surfaces.csv', geometry_variant_id='', membership='membership.csv',
                  instances=[dict(plant_id='', source_plant_id='', source_session_id='', capture_date='', surface_review='')]),
        background_csv=None, target_ids=[], source_entity_ids=[],
        limits=dict(max_transport_calls=256, max_receiver_emitter_pairs=10000000),
        native=dict(rays=None, max_depth=None, seeds=[], max_jobs=None, max_total_rays=None))
    write_json(folder / 'input.json', plan)
    write_rows(folder / 'membership.csv', [], MEMBERSHIP)
    write_rows(folder / 'leaf_surfaces.csv', [], LEAF_SURFACES_CSV_COLUMNS)
    return plan


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    subs = parser.add_subparsers(dest='command', required=True)
    for command in ('templates', 'audit', 'prepare', 'calculate', 'collect', 'stale', 'demo', 'execute'):
        p = subs.add_parser(command)
        if command not in ('templates', 'demo'):
            p.add_argument('--input', type=Path, required=True,
                           help='Input JSON for audit/prepare; prepared folder for calculate/execute/stale/collect')
        if command != 'stale':
            p.add_argument('--out', type=Path, required=True)
        if command == 'prepare':
            p.add_argument('--backend', choices=('direct', 'native'), default='direct')
        if command == 'execute':
            p.add_argument('--execute', action='store_true'); p.add_argument('--java', default='java')
            p.add_argument('--core', type=Path)
        if command == 'collect':
            p.add_argument('--execution', type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == 'templates':
            result = templates(args.out)
        elif args.command == 'audit':
            result = audit_inputs(args.input); folder = output_dir(args.out); write_json(folder / 'audit.json', result)
        elif args.command == 'prepare':
            result = prepare_subset_cases(args.input, args.out, args.backend)
        elif args.command == 'calculate':
            result = calculate_direct(args.input, args.out)
        elif args.command == 'stale':
            result = stale(args.input)
        elif args.command == 'demo':
            from tools.hierarchical_light_demo import demo
            result = demo(args.out)
        else:
            from tools.hierarchical_light_native import execute_native, collect_native
            if args.command == 'execute' and args.execute:
                print(json.dumps({'native_execution_cost': require_fresh(args.input).get('native_cost')}), flush=True)
            result = (execute_native(args.input, args.out, args.execute, args.java, args.core)
                      if args.command == 'execute' else collect_native(args.input, args.execution, args.out))
        print(json.dumps({k: result[k] for k in ('status', 'transport_ready', 'hierarchy_ready', 'stale', 'cost') if k in result}))
        return 0
    except (StudyError, ValueError, OSError, KeyError) as exc:
        parser.exit(2, f'{exc}\n')


if __name__ == '__main__':
    raise SystemExit(main())
