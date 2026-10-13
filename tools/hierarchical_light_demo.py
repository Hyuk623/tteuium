"""Explicit synthetic inputs for reproducible hierarchy software verification, not crop data."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS
from tools.leaf_light.common import ROOT, file_hash, output_dir, read_json, write_json, write_rows


def synthetic_inputs(folder: Path, groups: tuple[str, ...] = ('A', 'B', 'C'),
                     transmittance: float = .1, subdivisions: int = 2) -> Path:
    from tools.hierarchical_light import SCHEMA, MEMBERSHIP
    folder.mkdir(parents=True, exist_ok=False)
    scene = read_json(ROOT / 'tests/fixtures/light/light_scene.example.json')
    scene['setup_id'] = 'synthetic_hierarchy'
    scene['fixtures'] = scene['fixtures'][:1]
    fx = scene['fixtures'][0]
    fx['fixture_id'] = 'synthetic_LED'
    for name, value in dict(emitting_center_grow_mm=[0., 0., 1000.], emitting_length_mm=1.,
                             emitting_width_mm=1., photon_flux_umol_s=100., aim_tilt_deg=0.,
                             aim_azimuth_deg=0., long_axis_azimuth_deg=0.).items():
        fx[name] = dict(value=value, status='assumed', source='synthetic software fixture')
    fx['distribution']['half_intensity_half_angle_deg']['value'] = 45.
    fx['emitter_grid'] = [1, 1]
    scene['scenarios'] = []
    scene['simulation']['triangle_subdivisions'] = subdivisions
    for name, value in dict(absorptance=1.-transmittance, reflectance=0., transmittance=transmittance).items():
        scene['leaf_optics'][name] = dict(value=value, status='assumed', source='synthetic software fixture')
    plants = ['P1'] + (['P2'] if 'C' in groups else [])
    scene['plants'] = []
    for p in plants:
        scene['plants'].append(dict(plant_id=p,
            board_origin_grow_mm=dict(value=[0., 0., 0.] if p == 'P1' else [500., 0., 0.],
                                      status='assumed', source='synthetic layout'),
            board_yaw_deg=dict(value=0., status='assumed', source='synthetic layout'),
            posture_since_capture='unchanged_checked'))
    write_json(folder / 'scene.json', scene)
    evidence = dict(kind='synthetic_fixture', note='Artificial identities and surfaces; no real observation.')
    write_json(folder / 'identity_evidence.json', evidence)
    geometry, membership = [], []
    # The target is deliberately last to exercise filtered receiver index remapping.
    specs = [(g, 'P2' if g == 'C' else 'P1', 200. + 150.*i, 200.) for i, g in enumerate(groups)]
    specs.append(('target', 'P1', 0., 10.))
    for name, plant, z_mm, half_mm in specs:
        offset_mm = 500. if plant == 'P2' else 0.
        vertices = [[-half_mm-offset_mm, -half_mm, z_mm], [half_mm-offset_mm, -half_mm, z_mm],
                    [half_mm-offset_mm, half_mm, z_mm], [-half_mm-offset_mm, half_mm, z_mm]]
        for index, indices in enumerate(((0, 1, 2), (0, 2, 3))):
            row = dict(plant_id=plant, session_id='synthetic_session', geometry_variant_id='synthetic_v1',
                       geometry_source='assumed', organ_class='leaflet', organ_id=name, leaflet_id=name,
                       triangle_id=f'{name}_{index}', normal_convention='adaxial_ccw')
            for j, vi in enumerate(indices):
                for axis, value in zip('xyz', vertices[vi]):
                    row[f'v{j}_{axis}_mm'] = value
            geometry.append(row)
        membership.append(dict(source_plant_id=plant, plant_instance_id=plant,
            session_id='synthetic_session', capture_date='2026-10-03', geometry_variant_id='synthetic_v1',
            organ_id=name, leaflet_id=name, compound_id='compound_1' if name in ('target', 'A') else f'compound_{name}',
            identity_status='synthetic', evidence_path='identity_evidence.json',
            evidence_sha256=file_hash(folder / 'identity_evidence.json')))
    write_rows(folder / 'leaf_surfaces.csv', geometry, LEAF_SURFACES_CSV_COLUMNS)
    write_rows(folder / 'membership.csv', membership, MEMBERSHIP)
    write_json(folder / 'review.json', dict(geometry_sha256=file_hash(folder / 'leaf_surfaces.csv'),
        geometry_variant_id='synthetic_v1', snapshot_date='2026-10-03', surface_kind='leaf_triangles',
        review_state='accepted', reviewer='synthetic_fixture_generator', reviewed_at='2026-10-03T00:00:00+09:00',
        geometry_completeness='partial', validated_metric=False, suitable_for_ppfd=False))
    plan = dict(schema_version=SCHEMA, scenario_id='as_built',
        case=dict(case_id='synthetic_layers', data_kind='synthetic', scene='scene.json', geometry='leaf_surfaces.csv',
            geometry_variant_id='synthetic_v1', membership='membership.csv', surface_review='review.json',
            instances=[dict(plant_id=p, source_plant_id=p, source_session_id='synthetic_session',
                            capture_date='2026-10-03') for p in plants]),
        background_csv=None, target_ids=[], source_entity_ids=[],
        limits=dict(max_transport_calls=256, max_receiver_emitter_pairs=1000000),
        native=dict(rays=100000, max_depth=8, seeds=[3103, 3104], max_jobs=128, max_total_rays=12800000))
    write_json(folder / 'input.json', plan)
    return folder / 'input.json'


def demo(out: Path) -> dict:
    from tools.hierarchical_light import prepare_subset_cases, calculate_direct, stale
    folder = output_dir(out)
    source = synthetic_inputs(folder / 'inputs')
    prepare_subset_cases(source, folder / 'prepared')
    result = calculate_direct(folder / 'prepared', folder / 'results')
    native = prepare_subset_cases(source, folder / 'native_prepared', 'native')
    summary = dict(status='completed_synthetic_demo', native_status=native['status'], native_executed=False,
        direct_stale=stale(folder / 'results'), native_stale=stale(folder / 'native_prepared'),
        validated_metric=False, viewer=str((folder / 'results/viewer.html').resolve()))
    write_json(folder / 'demo.json', summary)
    return summary
