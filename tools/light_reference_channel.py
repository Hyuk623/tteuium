"""Hashed measured-reference attachment contract for tissue light packages."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil

from tools.leaf_light.common import DLI_UNIT, StudyError, file_hash, read_json
from tools.reference_dli_consumer import validate_result

CAPABILITY = 'implemented_measured_logged_and_spot_schedule_simulation_readiness_only'


def reference_mapping(record: dict | None, attachment: dict | None = None) -> dict:
    available = record is not None and record['status'] == 'available'
    result = dict(status='available' if available else 'unavailable',
        reason=None if available else ';'.join(record['reasons']) if record else 'reference_inputs_not_supplied',
        value=record['value'] if available else None, basis_id=record['basis_id'] if available else None,
        unit=DLI_UNIT, quantity='incident', model_scope='whole_plant',
        spatial_basis='declared_reference_position_and_sensor_plane', time_basis='complete_local_day',
        applicability_interval=record['applicability_interval'] if available else None,
        evidence_attachment=attachment, plant_instance_ids=(record['plant_association']['accepted_plant_instance_ids']
            if available else []), application_scope='only_explicitly_associated_plant_instances')
    if available:
        result.update(source_kind=record['source_kind'], reference=deepcopy(record['reference']),
            reference_evidence_base=str(Path(record['inputs']['position']).parent),
            applicability_source_ref=deepcopy(record['applicability_domain']['applicability_source_ref']),
            value_rule=record['value_rule'], days_used=deepcopy(record['days_used']),
            fixed_over_horizon=record['fixed_over_horizon'], timezone=record['timezone'])
    return result


def load_attachment(spec: dict | None, base: Path, tissue_bases: set[str]) -> tuple[dict, dict | None]:
    if spec is None:
        return dict(status='not_supplied', source_ref=None, result_ref=None), None
    if not isinstance(spec, dict) or set(spec) != {'path', 'sha256'}:
        raise StudyError('reference_dli_requires_hashed_result')
    path = (base/spec['path']).resolve()
    if file_hash(path) != spec['sha256']: raise StudyError('reference_dli_result_hash_mismatch')
    check = validate_result(path, tissue_bases=tissue_bases)
    record = read_json(path)
    return dict(status=check['status'], source_ref=dict(path=str(path), sha256=spec['sha256']),
                result_ref=dict(path='reference_dli/reference_dli.json', sha256=spec['sha256'])), record


def copy_attachment(envelope: dict, record: dict | None, folder: Path, sources: dict) -> None:
    if record is None: return
    source = Path(envelope['source_ref']['path'])
    target = folder/'reference_dli'; target.mkdir()
    for name in ('reference_dli.json', 'reference_dli.csv', 'integration_evidence.json'):
        path = source.parent/name
        sources[str(path)] = file_hash(path)
        shutil.copyfile(path, target/name)
    sources.update(record['source_hashes'])


def check_attachment(folder: Path, envelope: dict, mapping: dict, tissue_bases: set[str],
                     package: dict) -> None:
    request_ref = package['request_source_ref']
    if package['source_hashes'].get(request_ref['path']) != request_ref['sha256']:
        raise StudyError('reference_dli_request_source_missing')
    request = read_json(Path(request_ref['path']))
    context = sorted({pid for s in request['snapshots'] for pid in s['board_frame_ids']})
    if package['reference_context_plant_instance_ids'] != context:
        raise StudyError('reference_dli_context_plant_inventory_mismatch')
    original = request.get('reference_dli')
    wanted_source = (dict(path=str((Path(request_ref['path']).parent/original['path']).resolve()),
                          sha256=original['sha256']) if original is not None else None)
    if envelope.get('source_ref') != wanted_source:
        raise StudyError('reference_dli_original_request_mismatch')
    if envelope.get('status') == 'not_supplied':
        if envelope != dict(status='not_supplied', source_ref=None, result_ref=None):
            raise StudyError('reference_dli_invalid_empty_attachment')
        expected = reference_mapping(None)
    else:
        source = envelope['source_ref']; result = envelope['result_ref']
        if result['path'] != 'reference_dli/reference_dli.json': raise StudyError('reference_dli_artifact_path_mismatch')
        path = folder/result['path']
        if file_hash(path) != result['sha256'] or source['sha256'] != result['sha256']:
            raise StudyError('reference_dli_copied_result_hash_mismatch')
        if package['source_hashes'].get(source['path']) != source['sha256']:
            raise StudyError('reference_dli_source_binding_missing')
        check = validate_result(path, tissue_bases=tissue_bases)
        if check['status'] != envelope['status']: raise StudyError('reference_dli_attachment_status_mismatch')
        record = read_json(path)
        expected = reference_mapping(record, result)
        if record['status'] == 'available' and not set(expected['plant_instance_ids']).issubset(
                package['reference_context_plant_instance_ids']):
            raise StudyError('reference_dli_plant_association_outside_context')
    if mapping != expected:
        raise StudyError('reference_dli_mapping_mismatch')
