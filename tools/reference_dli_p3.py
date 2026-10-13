"""Bounded representation mapping for a predeclared P3 light contract; no forecast."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from tools.leaf_light.common import DLI_UNIT, StudyError, file_hash, read_json
from tools.reference_dli_consumer import validate_result
from tools.reference_dli_contract import Missing, canonical_unit


def map_single_day(result_path: Path, model_light: dict, *, evidence_kind: str) -> dict:
    """Fill reference-light fields only, preserving model kind/center/scale/coefficients.

    The caller explicitly classifies evidence in P3's vocabulary; the detailed
    measured_logged/spot_schedule route is retained alongside it. This avoids
    silently labelling a schedule estimate as continuous sensor logging.
    """
    validate_result(result_path)
    source = read_json(result_path)
    if source['status'] != 'available': raise Missing('p3_reference_result_'+source['status'])
    if source['value_rule'] != 'single_representative_day' or len(source['days_used']) != 1:
        raise Missing('p3_single_local_day_contract_cannot_represent_'+source['value_rule'])
    if evidence_kind not in ('measured', 'user_assumed', 'literature_informed', 'fitted'):
        raise StudyError('explicit_p3_evidence_classification_required')
    canonical_unit(model_light.get('unit'))
    if any(model_light.get(k) is None for k in ('kind', 'center', 'scale', 'coefficients')):
        raise Missing('predeclared_p3_model_light_contract_required')
    domain = source['applicability_domain']
    proof = domain['applicability_source_ref']  # Producer resolved the hashed path to an absolute path.
    aliases = [model_light[k] for k in ('applicability_interval', 'dli_applicability_interval') if model_light.get(k) is not None]
    if not aliases or any(x != aliases[0] for x in aliases[1:]):
        raise StudyError('missing_or_conflicting_predeclared_p3_domain')
    frozen_domain = aliases[0]
    if any(frozen_domain.get(k) != domain[k] for k in ('min', 'max', 'unit', 'applicability_source_ref')):
        raise StudyError('predeclared_p3_domain_does_not_match_reference')
    for binding in model_light['coefficients'].values():
        if binding.get('applicability_source_ref') != proof:
            raise StudyError('predeclared_p3_coefficient_domain_does_not_match_reference')
    day = source['days'][source['days_used'][0]['local_date']]
    if day['coverage_status'] != 'complete': raise Missing('p3_reference_day_incomplete')
    result = deepcopy(model_light)
    result.update(value=source['value'], unit=DLI_UNIT, light_basis=source['quantity'], scope=source['model_scope'],
        basis_id=source['basis_id'], time_basis=source['time_basis'], fixed_over_horizon=source['fixed_over_horizon'],
        source_kind=evidence_kind, source_ref=dict(path=str(result_path.resolve()), sha256=file_hash(result_path)),
        producer_source_kind=source['source_kind'], producer_value_rule=source['value_rule'],
        predeclared_model_evidence={k:model_light.get(k) for k in ('source_kind', 'source_ref')})
    reference = source['reference']
    result['reference'] = dict(position_mm=reference['position_mm'], normal_unit_xyz=reference['sensor_normal'],
        frame_id=reference['frame_id'], coordinate_frame=reference['coordinate_frame'],
        source_kind=evidence_kind, source_ref=deepcopy(result['source_ref']),
        producer_geometry_evidence=deepcopy(reference))
    result['local_day'] = dict(start_at=day['start_at'], end_at=day['end_at'], timezone=source['timezone'],
        coverage=day['coverage_status'], source_kind=evidence_kind, source_ref=deepcopy(result['source_ref']),
        producer_source_kind=source['source_kind'])
    # Identical frozen domain aliases are retained; no coefficient/model policy is derived.
    result['applicability_interval'] = deepcopy(frozen_domain)
    return result
