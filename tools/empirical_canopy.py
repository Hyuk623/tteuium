"""Conditional directional interception using the existing physical-leaf crossing engine."""
from __future__ import annotations

import argparse
from pathlib import Path

import numpy as np

from tomato3d.light.raytrace import Occluders, count_crossings
from tools.empirical_light_field import evaluate, finite, load_field, code_hashes
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json, write_rows


def directions(position_mm: np.ndarray, bars: list[dict], settings: dict) -> tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
    """Return direct/diffuse directions and intensity weights normalized to unit horizontal PPFD.

    Equal point samples along each bar; direct intensity proportional to 1/r^2.
    This is a declared directional kernel only, not a lamp emission/flux model.
    Diffuse dome uses midpoint quadrature uniform in azimuth and cos(zenith).
    """
    direct_u, intensity = [], []
    count = settings['bar_samples']
    for bar in bars:
        start = np.asarray(bar['start_mm'], dtype=float); stop = np.asarray(bar['stop_mm'], dtype=float)
        if start.shape != (3,) or stop.shape != (3,) or not np.isfinite([start, stop]).all() or np.linalg.norm(stop-start) <= 0:
            raise StudyError('invalid_bar_geometry')
        for t in (np.arange(count)+.5)/count:
            delta = start+t*(stop-start)-position_mm
            distance_mm = np.linalg.norm(delta)
            if distance_mm <= 0 or delta[2] <= 0:
                raise StudyError('bar_must_be_above_receiver')
            direct_u.append(delta/distance_mm); intensity.append(1/distance_mm**2/count)
    u = np.asarray(direct_u); w = np.asarray(intensity)
    if len(u) == 0:
        raise StudyError('declared_bar_geometry_required')
    w /= np.sum(w*u[:, 2])
    mu = (np.arange(settings['dome_mu_samples'])+.5)/settings['dome_mu_samples']
    phi = 2*np.pi*(np.arange(settings['dome_phi_samples'])+.5)/settings['dome_phi_samples']
    v = np.array([[np.sqrt(1-m*m)*np.cos(a), np.sqrt(1-m*m)*np.sin(a), m] for m in mu for a in phi])
    d = np.ones(len(v))/np.sum(v[:, 2])
    return u, w, v, d


def intercept(field: dict, scene: dict) -> dict:
    """Area support is one-sided m2; both faces receive. Unknown crossed-leaf tau poisons the row."""
    if scene.get('schema_version') != 'empirical-canopy-1' or scene.get('coordinate_frame') != 'grow':
        raise StudyError('invalid_canopy_contract')
    if scene.get('source_kind') not in ('fixture_truth', 'reviewed_optical_surface') or not scene.get('source_ref'):
        raise StudyError('optical_surface_evidence_required')
    if scene['source_kind'] == 'reviewed_optical_surface':
        ref = scene['source_ref']
        if not isinstance(ref, dict) or file_hash(Path(ref['path'])) != ref.get('sha256'):
            raise StudyError('reviewed_optical_surface_evidence_hash_mismatch')
    if scene.get('configuration_sha256') != field['configuration_sha256']:
        raise StudyError('canopy_configuration_mismatch')
    contract = field['configuration']['empirical_contract']
    bars = contract.get('direction_bars')
    if not bars or contract.get('direction_source_kind') != 'user_assumed':
        raise StudyError('explicit_assumed_direction_geometry_required')
    settings = scene['quadrature']
    limits = dict(bar_samples=4096, dome_mu_samples=128, dome_phi_samples=512,
                  max_pairs_per_chunk=1000000, max_total_pairs=500000000)
    for key, maximum in limits.items():
        if type(settings.get(key)) is not int or not 1 <= settings[key] <= maximum:
            raise StudyError('invalid_resource_limit:'+key)
    fractions = scene['diffuse_fractions']
    if (scene.get('direction_source_kind') != 'user_assumed' or not fractions or len(fractions) > 32 or
            len(set(fractions)) != len(fractions) or any(not 0 <= finite(f) <= 1 for f in fractions)):
        raise StudyError('explicit_distinct_direction_scenarios_required')
    tau = scene.get('leaf_transmittance')
    if tau is not None and (not 0 <= finite(tau) <= 1 or not scene.get('leaf_transmittance_source_ref')):
        raise StudyError('invalid_leaf_transmittance')
    triangles = scene['triangles']
    if any(t.get('role') != 'leaf' for t in triangles):
        raise StudyError('only_canopy_leaf_occluders_allowed_no_walls')
    codes = {name: i for i, name in enumerate(sorted({t['surface_id'] for t in triangles}))}
    vertices = np.array([t['vertices_mm'] for t in triangles], dtype=float).reshape(-1, 3, 3)
    if not np.isfinite(vertices).all() or (len(vertices) and (vertices[:, :, 2].max() > 150 or vertices[:, :, 2].min() < 0)):
        raise StudyError('canopy_geometry_outside_confirmed_height')
    if len(vertices) and np.any(np.linalg.norm(np.cross(vertices[:, 1]-vertices[:, 0], vertices[:, 2]-vertices[:, 0]), axis=1) == 0):
        raise StudyError('degenerate_leaf_triangle')
    occ = Occluders(vertices, np.ones(len(triangles), dtype=bool),
                    np.array([codes[t['surface_id']] for t in triangles], dtype=np.int64),
                    np.zeros(len(triangles), dtype=np.int64))
    receivers = scene['receivers']
    if not receivers or len({r['receiver_id'] for r in receivers}) != len(receivers):
        raise StudyError('empty_or_duplicate_receiver_ids')
    direction_count = len(bars)*settings['bar_samples']+settings['dome_mu_samples']*settings['dome_phi_samples']
    if direction_count > 65536:
        raise StudyError('per_receiver_direction_memory_limit_exceeded')
    if len(receivers)*direction_count*max(1, len(triangles)) > settings['max_total_pairs']:
        raise StudyError('resource_budget_exceeded')
    output = []
    for r in receivers:
        position_mm = np.asarray(r['position_mm'], dtype=float)
        q = evaluate(field, r['position_mm'])['ppfd_umol_m2_s']
        normal = np.asarray(r['normal'], dtype=float)
        if normal.shape != (3,) or not np.isfinite(normal).all() or not np.isclose(np.linalg.norm(normal), 1, atol=1e-10, rtol=1e-10):
            raise StudyError('unit_receiver_normal_required')
        area_m2 = finite(r['supported_one_sided_area_m2'])
        own = r['own_triangle']
        if area_m2 <= 0 or type(own) is not int or own < -1 or own >= len(triangles):
            raise StudyError('invalid_receiver_support')
        if own >= 0 and triangles[own]['surface_id'] != r['leaf_id']:
            raise StudyError('own_triangle_identity_mismatch')
        u, w, v, d = directions(position_mm, bars, settings)
        arrival = np.concatenate([u, v])
        # Stop just above the confirmed canopy top; there is no room/wall transport.
        distance_mm = (150.-position_mm[2]+1.)/arrival[:, 2]
        segments_mm = arrival*distance_mm[:, None]
        crossings, blocked = count_crossings(np.tile(position_mm, (len(arrival), 1)), segments_mm,
            np.full(len(arrival), own, dtype=int), occ, settings['max_pairs_per_chunk'])
        cosine = arrival@normal
        for fraction in fractions:
            intensity = q*np.concatenate([(1-fraction)*w, fraction*d])
            before = intensity*np.abs(cosine)
            missing = (crossings > 0) & (before > 0) & ~blocked if tau is None else np.zeros(len(arrival), bool)
            transmission = np.ones(len(arrival)) if tau is None else np.power(tau, crossings)
            after = before*transmission*~blocked
            valid = not np.any(missing)
            upper = float(np.sum(after*(cosine > 0))) if valid else None
            lower = float(np.sum(after*(cosine < 0))) if valid else None
            output.append(dict(receiver_id=r['receiver_id'], leaf_id=r['leaf_id'],
                diffuse_fraction=fraction, supported_one_sided_area_m2=area_m2,
                horizontal_incident_ppfd_umol_m2_s=q,
                unoccluded_ppfd_umol_m2_s=float(before.sum()),
                upper_ppfd_umol_m2_s=upper, lower_ppfd_umol_m2_s=lower,
                intercepted_flux_umol_s=float(after.sum()*area_m2) if valid else None,
                status='conditional' if valid else 'unavailable',
                reason=None if valid else 'leaf_transmittance_unavailable', source_kind='derived',
                direction_source_kind='user_assumed'))
    leaves = []
    for leaf_id in sorted({r['leaf_id'] for r in receivers}):
        for fraction in fractions:
            group = [r for r in output if r['leaf_id'] == leaf_id and r['diffuse_fraction'] == fraction]
            area = sum(r['supported_one_sided_area_m2'] for r in group)
            valid = all(r['intercepted_flux_umol_s'] is not None for r in group)
            flux = sum(r['intercepted_flux_umol_s'] for r in group) if valid else None
            leaves.append(dict(leaf_id=leaf_id, diffuse_fraction=fraction, supported_one_sided_area_m2=area,
                intercepted_flux_umol_s=flux, mean_ppfd_umol_m2_s=flux/area if valid else None,
                status='conditional' if valid else 'unavailable'))
    spreads = []
    for leaf_id in sorted({r['leaf_id'] for r in receivers}):
        values = [r['mean_ppfd_umol_m2_s'] for r in leaves if r['leaf_id'] == leaf_id]
        available = all(v is not None for v in values)
        spreads.append(dict(leaf_id=leaf_id, min_ppfd_umol_m2_s=min(values) if available else None,
            max_ppfd_umol_m2_s=max(values) if available else None,
            spread_ppfd_umol_m2_s=max(values)-min(values) if available else None))
    return dict(schema_version='empirical-canopy-result-1', method='empirical_light_field',
        source_kind='derived', direction_source_kind='user_assumed', geometry_source_kind=scene['source_kind'],
        physical_accuracy='unvalidated', receivers=output, leaves=leaves, spreads=spreads,
        scope='supported_surface_only_not_whole_plant',
        direction_kernel='equal_bar_line_samples_inverse_square_intensity_plus_uniform_radiance_upper_dome',
        disclosures=['scenario_spread_is_not_a_confidence_interval', 'no_growth_forecast',
                     'no_wall_surfaces_or_fitted_reflectance', 'interpolated_environment_is_conditional'])


def run(field_path: Path, configuration_path: Path, scene_path: Path, out: Path) -> dict:
    field = load_field(field_path, configuration_path)
    result = intercept(field, read_json(scene_path))
    folder = output_dir(out)
    for key in ('receivers', 'leaves', 'spreads'):
        write_rows(folder/(key+'.csv'), result[key], list(result[key][0]))
    result.update(source_hashes={str(p.resolve()): file_hash(p) for p in (field_path, configuration_path, scene_path)},
                  code_hashes=code_hashes(), artifact_hashes={key+'.csv': file_hash(folder/(key+'.csv')) for key in ('receivers', 'leaves', 'spreads')})
    write_json(folder/'canopy_result.json', result)
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ('field', 'configuration', 'scene', 'out'):
        parser.add_argument('--'+name, type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        result = run(args.field, args.configuration, args.scene, args.out)
        print(dict(status='conditional', leaves=len(result['leaves']), out=str(args.out)))
        return 0
    except (StudyError, OSError, ValueError, KeyError) as exc:
        parser.exit(2, str(exc)+'\n')


if __name__ == '__main__':
    raise SystemExit(main())
