"""Optional nutrient ledger alongside the existing P4 diagnostic, without feedback."""
from __future__ import annotations

from tools.leaf_light.common import StudyError, digest
from tools.nutrient_balance import simulate
from tools.nutrient_contract import SCHEMA, Unavailable, obj, require_json, science_readiness, time


def compute_with_nutrients(request: dict, nutrient_scenario: dict | None = None,
                           *, enabled: bool = False) -> dict:
    """Disabled returns the exact P4 result. Enabled does not change P3/P4 biology."""
    from tools.fsp_carbon_diagnostic import compute_carbon_sufficiency
    if not isinstance(enabled, bool):
        raise StudyError('enabled must be boolean')
    obj(request, 'P4 request')
    required = ('p3_interval', 'carbon_state', 'light_series', 'environment', 'parameter_pack')
    if any(k not in request for k in required):
        raise StudyError('Incomplete P4 request')
    baseline = compute_carbon_sufficiency(**{k: request[k] for k in required})
    if not enabled:
        return baseline
    binding = dict(status='unavailable', reason='nutrient_scenario_missing')
    nutrient = None
    if nutrient_scenario is not None:
        obj(nutrient_scenario, 'nutrient scenario')
        ctx = obj(request['p3_interval'], 'P3 interval')
        mismatches = [k for k in ('plant_instance_id', 'source_plant_id', 'scenario_id')
                      if nutrient_scenario.get(k) != ctx.get(k)]
        require_json(nutrient_scenario)
        for k in ('t_start', 't_end'):
            try:
                matches = time(nutrient_scenario.get(k), k) == time(ctx.get(k), k)
            except Unavailable:
                matches = False
            if not matches:
                mismatches.append(k)
        if mismatches:
            binding = dict(status='unavailable', reason='nutrient_fsp_context_mismatch', fields=mismatches)
        else:
            nutrient = simulate(nutrient_scenario)
            binding = dict(status=nutrient['status'], reason=None if nutrient['status'] == 'available'
                           else nutrient['reason'], scope='same_plant_and_interval_only',
                           interval_alignment='P4_internal_light_environment_alignment_retained')
    return dict(schema_version=SCHEMA, nutrient_enabled=True,
        p4_diagnostic=baseline, nutrient_accounting=nutrient, binding=binding,
        growth_constraints=science_readiness(),
        potential_growth_source_hash=digest(request['p3_interval']),
        nutrient_constrained_growth=None, carbon_and_nutrient_growth_commit=None,
        growth_feedback_applied=False, source_request_hash=digest(request),
        nutrient_request_hash=digest(nutrient_scenario),
        interpretation='side_by_side_diagnostics_not_coupled_growth_forecast')
