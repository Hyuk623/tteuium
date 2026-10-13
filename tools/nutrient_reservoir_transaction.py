"""Fixture-only atomic joint candidate publication for the future native owner.

No external stock is debited and no native growth state is advanced here.
The legacy element-resolved protocol is preserved; its mg units are not relabelled.
"""
from __future__ import annotations

from copy import deepcopy
import re
from pathlib import Path

from tools.vtc_growth_io import ROOT, require, aware, digest, read_json, write_json, fresh_build
from tools.nutrient_reservoir import identity, interval, replay, feedback_gate, trays

BINDINGS = ('run_id', 'scenario_id', 'tray_membership', 'interval_start', 'interval_end',
            'predecessor_sha256', 'model_sha256', 'parameter_sha256', 'geometry_sha256',
            'configuration_sha256', 'native_state_sha256', 'reservoir_state_sha256')


def _output_boundary(folder: Path) -> None:
    target, build = folder.resolve(), (ROOT/'build').resolve()
    require(target != build and target.is_relative_to(build), 'transaction output must be below project build/')


def _validate(proposal: dict) -> None:
    require(proposal.get('schema_version') == 'tray-resource-protocol-fixture-1', 'transaction schema')
    require(proposal.get('fixture') is True, 'native causal hook unavailable')
    identity(proposal.get('proposal_id'), 'proposal ID required')
    identity(proposal.get('run_id'), 'run ID required')
    identity(proposal.get('scenario_id'), 'scenario ID required')
    interval(proposal)
    require(aware(proposal['issued_at']) < aware(proposal['expires_at']), 'positive response lifetime required')
    for key in BINDINGS:
        require(key in proposal, 'missing binding: ' + key)
        if key.endswith('_sha256'):
            require(isinstance(proposal[key], str) and re.fullmatch('[0-9a-f]{64}', proposal[key]) is not None,
                    'hash required: ' + key)
    require(isinstance(proposal['tray_membership'], dict) and bool(proposal['tray_membership']), 'tray membership')
    members = []
    for tid, ids in proposal['tray_membership'].items():
        identity(tid, 'tray ID required')
        require(isinstance(ids, list), 'plant membership list')
        for pid in ids:
            members.append(identity(pid, 'plant ID required'))
    require(len(members) == len(set(members)), 'duplicate transaction plant')


def begin(folder: Path, proposal: dict) -> str:
    _output_boundary(folder)
    _validate(proposal)
    tx = digest(proposal)
    if folder.exists():
        require((folder/'proposal.json').is_file(), 'partial begin: proposal absent; use fresh transaction folder')
        require(read_json(folder/'proposal.json') == proposal, 'conflicting begin retry')
        return tx
    target = fresh_build(folder)
    write_json(target/'proposal.json', proposal)
    return tx


def finalize(folder: Path, response: dict, native_candidate: dict, reservoir_request: dict,
             now: str, *, stage_only: bool = False) -> dict:
    """Publish one canonical bundle; same interrupted/retried bundle cannot spend twice.

    stage_only simulates interruption before the sole publication point. A changed
    staged response fails. Timeout still applies to an uncommitted retry. An already
    committed identical retry is a read and can return after expiry.
    """
    _output_boundary(folder)
    proposal = read_json(folder/'proposal.json')
    _validate(proposal)
    tx = digest(proposal)
    binding = {key: proposal[key] for key in BINDINGS}
    require(response.get('proposal_id') == proposal['proposal_id'] and response.get('transaction_id') == tx,
            'wrong/stale proposal')
    require(response.get('binding') == binding, 'stale state/interval/configuration')
    require(response.get('expires_at') == proposal['expires_at'], 'response cannot extend expiry')
    feedback_gate(response.get('ENABLE_NUTRIENT_FEEDBACK', False))
    require(response.get('f_nut') is None, 'fixture transport cannot apply a response factor')
    require(native_candidate.get('fixture') is True and native_candidate.get('native_causality') is False,
            'native candidate must be labelled fixture only')
    require(native_candidate.get('predecessor_sha256') == proposal['native_state_sha256'], 'stale native candidate')
    require(native_candidate.get('state') is not None, 'explicit native candidate state required')
    require(response.get('native_candidate_sha256') == digest(native_candidate), 'native candidate hash mismatch')
    require(response.get('reservoir_request_sha256') == digest(reservoir_request), 'reservoir request hash mismatch')
    require(reservoir_request.get('scenario_id') == proposal['scenario_id'] and
            interval(reservoir_request) == interval(proposal), 'reservoir interval/scenario mismatch')
    membership = {tid: row['plant_ids'] for tid, row in trays(reservoir_request['trays']).items()}
    require(membership == proposal['tray_membership'], 'reservoir membership mismatch')
    candidate = replay(reservoir_request)
    require(candidate['status'] == 'available_prescribed_accounting', 'reservoir candidate unavailable')
    require(candidate['initial_sha256'] == proposal['reservoir_state_sha256'], 'stale reservoir state')
    request_hash = digest(dict(response=response, native_candidate=native_candidate, reservoir_request=reservoir_request))
    bundle = dict(status='fixture_joint_bundle_committed', native_causality=False,
                  biological_validation='not_established', growth_feedback_applied=False,
                  proposal_id=proposal['proposal_id'], transaction_id=tx, request_sha256=request_hash,
                  binding=binding, native_candidate=deepcopy(native_candidate), reservoir_candidate=candidate)
    target = folder/'committed'
    if target.exists():
        committed = read_json(target/'joint_commit.json')
        require(committed == bundle, 'conflicting finalized retry')
        return committed
    require(aware(proposal['issued_at']) <= aware(now) <= aware(proposal['expires_at']), 'response expired/not issued')
    # Exclusive writer. A leftover lock indicates concurrent work or an OS crash;
    # do not delete another writer's lock or publish without inspection.
    lock = folder/'.finalize_lock'
    require(not lock.exists(), 'transaction writer lock present; inspect before retry')
    lock.mkdir()
    try:
        partial = folder/'.joint_partial'
        if partial.exists():
            require((partial/'joint_commit.json').is_file(), 'incomplete partial bundle; inspect before retry')
            require(read_json(partial/'joint_commit.json') == bundle, 'conflicting interrupted retry')
        else:
            partial.mkdir()
            write_json(partial/'joint_commit.json', bundle)
        if stage_only:
            return dict(status='fixture_staged_not_committed', transaction_id=tx, native_causality=False)
        partial.rename(target)
    finally:
        lock.rmdir()
    return bundle
