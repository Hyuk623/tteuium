"""Explicitly invented P4 fixture generator; not crop defaults or observations."""
from __future__ import annotations

import argparse
from copy import deepcopy
from pathlib import Path
from tools.fsp_carbon_diagnostic import SCHEMA
from tools.leaf_light.common import digest, output_dir, write_json


def seal(payload: dict) -> dict:
    return dict(payload=deepcopy(payload), sha256=digest(payload))


def synthetic_request() -> dict:
    """Return one labelled, complete hypothetical whole-plant diagnostic fixture."""
    t0, t1 = '2026-10-04T00:00:00+09:00', '2026-10-05T00:00:00+09:00'
    states = [dict(organ_id='leaf', organ_kind='leaf', supported_area_cm2=200.0,
                   area_basis_id='one_sided_blade', rachis_arc_length_mm=100.0)]
    config = dict(schema_version='probabilistic-compound-1', environment_profile='d9',
                  clock=dict(kind='calendar'), parameter_particles=[])
    manifest = dict(schema_version='probabilistic-compound-1', config_hash=digest(config),
                    p3_light_coupling='none', p3_environment_paths=[], environment_audit_status='complete')
    p3 = dict(schema_version=SCHEMA, run_id='hypothetical', scenario_id='constant_fixture',
              plant_instance_id='plant1', source_plant_id='source1', trajectory_id='trajectory1',
              trajectory_weight=1.0, t_start=t0, t_end=t1, frame_id='board',
              area_basis_id='one_sided_blade', organ_states_start=deepcopy(states), organ_states_end=deepcopy(states),
              geometry_hash_start=digest(states), geometry_hash_end=digest(states), events=[],
              post_termination_scope='available', p3_manifest_ref=seal(manifest), frozen_config_ref=seal(config),
              calibration_provenance=None)
    masses = [dict(organ_id=organ, organ_kind=kind, mass_compartment='blade' if kind == 'leaf' else 'root',
                   structural_dm_g=1.0, supported_area_m2=.02 if kind == 'leaf' else None,
                   mass_basis='structural_dm_excluding_reserve', evidence_kind='assumed', source_ref='synthetic_fixture')
              for organ, kind in [('leaf', 'leaf'), ('root', 'root')]]
    state = dict(context={key: p3[key] for key in ('plant_instance_id', 't_start', 't_end')}, scope='whole_plant',
                 included_organ_ids=['leaf', 'root'], excluded_organ_ids=[], organ_masses=masses,
                 reserve_evidence=dict(source_ref='invented_reserve_observation', lineage_id='synthetic_plant1_reserve'),
                 stock_at=t0, reserve_gC=.2, minimum_reserve_gC=.05, external_import_gC=0.0, external_export_gC=0.0,
                 boundary_policy='Hypothetical closed plant', coverage_statement='Invented two-compartment plant',
                 reproductive_scope=dict(status='not_present', organ_ids=[], source_ref='Explicit hypothetical vegetative plant without reproductive organs'),
                 nonfoliar_assimilation_assumption='Nonfoliar assimilation set to zero only for this invented fixture',
                 maintenance_start_mass_assumption='Hold starting structural mass constant over each interval',
                 mass_increments=[dict(organ_id=o, structural_dm_start_g=1.0, structural_dm_end_g=1.1,
                                       unit='g_structural_DM', evidence_kind='assumed', source_ref='invented_increment') for o in ('leaf', 'root')])
    context = dict(plant_instance_id='plant1', t_start=t0, t_end=t1, geometry_hash=digest(states),
                   area_basis_id='one_sided_blade', backend='hypothetical', replicate='replicate1')
    patches = [dict(patch_id='patch1', organ_id='leaf', area_weight_m2=.005, optical_eligible=True, geometry_kind='hypothetical_tissue',
                   illuminated_faces='adaxial_only', face_source_ref='synthetic_supported_biological_face_mapping'),
               dict(patch_id='patch2', organ_id='leaf', area_weight_m2=.015, optical_eligible=True, geometry_kind='hypothetical_tissue',
                   illuminated_faces='adaxial_only', face_source_ref='synthetic_supported_biological_face_mapping')]
    light = dict(context=context, geometry_policy='fixed_snapshot', geometry_assumption='Invented fixed metric tissue and irradiance for 24 hours',
                 fixture_ids=['fixture1'], patches=patches, samples=[dict(**context, **{k: p[k] for k in ('patch_id', 'organ_id', 'area_weight_m2')},
                 fixture_id='fixture1', illuminated_faces='adaxial_only', face_source_ref='synthetic_fixture_to_adaxial_mapping', ppfd_umol_m2_s=100.0 if p['patch_id'] == 'patch1' else 400.0,
                 one_sided_area_basis=True, light_basis='incident', status='available', source_ref='invented_light') for p in patches])
    env = dict(records=[dict(plant_instance_id='plant1', t_start=t0, t_end=t1, leaf_temperature_c=20.0,
                            air_temperature_c=20.0, co2_ppm=800.0, pressure_pa=101325.0, relative_humidity_pct=None,
                            vpd_kpa=None, ec_ms_cm=None, ph=None, phase='day', environment_kind='assumed', source_ref='synthetic_fixture')])
    parameters = {}
    for key, value, unit in [('alpha', .05, 'umolCO2/umol_photon'), ('Pmax', 20.0, 'umolCO2/m2/s'),
                             ('theta', .7, 'dimensionless'), ('maintenance', .01, 'gCH2O/g_structural_DM/day'),
                             ('Q10', 2.0, 'dimensionless'), ('Tref', 20.0, 'degC'), ('activity', 1.0, 'dimensionless'),
                             ('ASR', 1.5, 'gCH2O/g_structural_DM'), ('carbon', .4, 'gC/g_structural_DM'),
                             ('sla0', .02, 'm2/g_structural_blade_DM'), ('sla1', .02, 'm2/g_structural_blade_DM'),
                             ('lambda', .1, 'mm/mg^gamma'), ('gamma', 1.0, 'dimensionless'),
                             ('Rd_day', 1.0, 'umolCO2/m2/s'), ('Rd_night', 1.0, 'umolCO2/m2/s'), ('f_days', 33.0, 'day')]:
        parameters[key] = dict(value=value, unit=unit, evidence_kind='assumed', source_id='synthetic_fixture',
                               locator='Explicit invented example', applicability='Synthetic arithmetic only', review_state='hypothetical', source_family='non_dwarf' if key in {'Rd_day', 'Rd_night'} else 'hypothetical',
                               measured_light_basis='incident' if key in {'alpha','Pmax','theta'} else None,
                               cultivar=None, conditions='Invented constant forcing', uncertainty=None)
    pack = dict(schema_version=SCHEMA, pack_id='synthetic_pack', draw_id='synthetic_draw1', review_status='hypothetical',
                source_family='hypothetical', model_id='nrh', scope='whole_plant', light_basis='incident', respiration_accounting='before_mito',
                applicable_domain={'co2_ppm': [800, 800], 'leaf_temperature_c': [0, 40]},
                assumptions=['All biological values are invented numerical fixtures, not literature estimates or target defaults'],
                numerics=dict(carbon_abs_tol_gC=1e-12, carbon_rel_tol=1e-12, mass_abs_tol_gDM=1e-12, area_abs_tol_m2=1e-12),
                photosynthesis=dict(alpha='alpha', Pmax='Pmax', theta='theta', Rd_day='Rd_day', Rd_night='Rd_night'),
                parameters=parameters, mass_form_mapping={},
                organ_parameter_map={o: dict(maintenance_rate='maintenance', Q10='Q10', Tref='Tref', activity='activity', activity_kind='constant', ASR='ASR', carbon_fraction='carbon', temperature_metric='leaf_temperature_c', temperature_assumption='All synthetic compartments share the declared temperature') for o in ('leaf', 'root')},
                respiration_ownership=[dict(organ_id=o, maintenance='downstream', growth='demand') for o in ('leaf', 'root')])
    return dict(schema_version=SCHEMA, p3_interval=p3, carbon_state=state, light_series=light, environment=env, parameter_pack=seal(pack))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    folder = output_dir(args.out)
    write_json(folder / 'request.json', synthetic_request())
    print(str(folder / 'request.json'))


if __name__ == '__main__':
    main()
