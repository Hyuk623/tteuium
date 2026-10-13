"""Bounded consumer of the actual direct-light callback; not a transport backend.

Run ``python -m tools.light_direction_diagnostics --help`` for a read-only audit.
"""
from __future__ import annotations

import argparse
from dataclasses import dataclass
import inspect
from pathlib import Path
from typing import Any, Mapping

import numpy as np

from tomato3d.light.raytrace import DIRECT_ANGULAR_PROTOCOL, DirectLight, direct_light
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json

SCHEMA_PATH = Path(__file__).with_name('light_growth_schema.json')
POLICY = read_json(SCHEMA_PATH)['numerical_policy']
ATOL = POLICY['absolute_tolerance']
RTOL = POLICY['relative_tolerance']
PROTOCOL = DIRECT_ANGULAR_PROTOCOL
SECOND_INDEX = ((0, 0), (0, 1), (0, 2), (1, 1), (1, 2), (2, 2))


def _integer(value: Any, label: str, minimum: int = 0) -> int:
    if isinstance(value, (bool, np.bool_)) or not isinstance(value, (int, np.integer)) or value < minimum:
        raise StudyError('invalid_' + label)
    return int(value)


@dataclass(frozen=True)
class ReceiverMoments:
    """Owned snapshots; F/M/B have units umol/s and use the grow frame.

    Shapes are (fixture, receiver), (..., 3), (..., 6); B order is
    xx, xy, xz, yy, yz, zz. Unknown counts are -1 for an unknown inventory.
    Structural completeness does not imply finite transport values.
    """

    fixture_ids: tuple[str, ...]
    received_ppfd_umol_m2_s: np.ndarray
    normal_side_ppfd_umol_m2_s: np.ndarray
    flux_umol_s: np.ndarray
    first_umol_s: np.ndarray
    second_umol_s: np.ndarray
    unknown_path_count: np.ndarray
    first_missing_reason: tuple[tuple[str | None, ...], ...]


class DirectionCollector:
    """Synchronous callback sink with explicit budgets and fail-closed finalization.

    Fixture inventory maps each real ID to emitter count, or None when unavailable.
    Chunks must be increasing/contiguous per fixture; fixtures may interleave.
    Input arrays are borrowed only during __call__; the sink retains no views.
    Reductions require O(F*S) storage and O(chunk length) temporary memory.
    An exception permanently invalidates the collector. Make a fresh one per run.
    """

    def __init__(self, fixture_inventory: Mapping[str, int | None],
                 unit_normals_grow: Any, quadrature_area_m2: Any, *,
                 max_paths: int, max_chunk_paths: int, max_receiver_fixture_pairs: int) -> None:
        self.max_chunk_paths = _integer(max_chunk_paths, 'max_chunk_paths', 1)
        max_paths = _integer(max_paths, 'max_paths', 1)
        max_pairs = _integer(max_receiver_fixture_pairs, 'max_receiver_fixture_pairs', 1)
        self.fixture_ids = tuple(fixture_inventory)
        if not self.fixture_ids or any(not isinstance(k, str) or not k.strip() or k in ('all', '__all__')
                                       for k in self.fixture_ids):
            raise StudyError('real_fixture_inventory_required')
        self._normals = np.array(unit_normals_grow, dtype=float, copy=True)
        self._area = np.array(quadrature_area_m2, dtype=float, copy=True)
        self.n = len(self._area) if self._area.ndim == 1 else 0
        if not self.n or self._normals.shape != (self.n, 3) or not np.isfinite(self._area).all() or np.any(self._area <= 0):
            raise StudyError('positive_metric_quadrature_required')
        if not np.isfinite(self._normals).all() or not np.allclose(np.linalg.norm(self._normals, axis=1), 1, atol=ATOL, rtol=RTOL):
            raise StudyError('receiver_unit_normals_required')
        self._emitters = tuple(None if v is None else _integer(v, 'emitter_count', 1)
                               for v in fixture_inventory.values())
        if len(self.fixture_ids) * self.n > max_pairs or sum(self.n * e for e in self._emitters if e is not None) > max_paths:
            raise StudyError('direction_resource_budget_exceeded')
        self._index = {fid: i for i, fid in enumerate(self.fixture_ids)}
        self._next = [0] * len(self.fixture_ids)
        self._unavailable = set()
        # PPFD, normal-side PPFD, M[3], B[6], before quadrature area weighting.
        self._totals = np.zeros((len(self.fixture_ids), self.n, 11))
        self._unknown = np.zeros((len(self.fixture_ids), self.n), dtype=np.int64)
        self._reasons: list[list[str | None]] = [[None] * self.n for _ in self.fixture_ids]
        self._failed = False
        self._finished = False
        self._verified = False
        self._chunks = [0] * len(self.fixture_ids)
        self._largest_chunk = 0

    def __call__(self, event: Mapping[str, Any]) -> None:
        if self._failed or self._finished:
            raise StudyError('direction_collector_closed')
        try:
            self._consume(event)
        except Exception:
            self._failed = True
            raise

    def _consume(self, event: Mapping[str, Any]) -> None:
        if event.get('protocol') != PROTOCOL or event.get('fixture_id') not in self._index:
            raise StudyError('foreign_direction_event')
        f = self._index[event['fixture_id']]
        e = self._emitters[f]
        if _integer(event['receiver_count'], 'receiver_count') != self.n or event['emitter_count'] != e:
            raise StudyError('direction_inventory_changed')
        if e is None:
            reason = event.get('missing_reason')
            if (event.get('kind') != 'fixture_unavailable' or f in self._unavailable
                    or 'expected_path_count' not in event or event['expected_path_count'] is not None):
                raise StudyError('invalid_or_duplicate_unavailable_fixture')
            if not isinstance(reason, str) or not reason.strip():
                raise StudyError('missing_fixture_reason_required')
            self._unavailable.add(f)
            self._totals[f] = np.nan
            self._unknown[f] = -1
            self._reasons[f] = [reason] * self.n
            return
        if event.get('kind') != 'paths' or _integer(event['emitter_count'], 'emitter_count', 1) != e:
            raise StudyError('invalid_path_event')
        expected = self.n * e
        start = _integer(event['path_start'], 'path_start')
        stop = _integer(event['path_stop'], 'path_stop')
        if _integer(event['expected_path_count'], 'expected_path_count') != expected:
            raise StudyError('direction_inventory_changed')
        if start != self._next[f] or not start < stop <= expected:
            raise StudyError('duplicate_missing_or_unordered_direction_chunk')
        count = stop - start
        if count > self.max_chunk_paths:
            raise StudyError('direction_chunk_budget_exceeded')
        flat = np.arange(start, stop, dtype=np.int64)
        indices = []
        for name, wanted in (('receiver_index', flat // e), ('emitter_index', flat % e)):
            values = np.asarray(event[name])
            if values.dtype.kind not in 'iu' or values.shape != (count,) or not np.array_equal(values, wanted):
                raise StudyError('unstable_global_path_indices')
            indices.append(values)
        receiver = indices[0]
        q = np.asarray(event['incident_ppfd_umol_m2_s'], dtype=float)
        u = np.asarray(event['arrival_unit_grow_xyz'], dtype=float)
        valid = np.asarray(event['ppfd_valid'])
        direction_valid = np.asarray(event['direction_valid'])
        if q.shape != (count,) or u.shape != (count, 3) or any(a.shape != (count,) or a.dtype.kind != 'b' for a in (valid, direction_valid)):
            raise StudyError('invalid_direction_chunk_shape_or_flags')
        if np.isinf(q).any() or np.any(q[valid] < 0) or not np.isfinite(q[valid]).all() or not np.isnan(q[~valid]).all():
            raise StudyError('invalid_path_ppfd_or_validity')
        for name, flags in (('missing_reason', valid), ('direction_missing_reason', direction_valid)):
            reasons = event[name]
            if len(reasons) != count or any((r is not None) if ok else (not isinstance(r, str) or not r.strip())
                                           for ok, r in zip(flags, reasons)):
                raise StudyError('path_missing_reason_mismatch')
        # The only path without a geometrically known direction is a known zero
        # (e.g. coincident receiver/emitter); unknown attenuation retains its direction.
        if not np.isfinite(u).all() or np.any(u[~direction_valid] != 0) or np.any(q[~direction_valid] != 0):
            raise StudyError('unknown_direction_requires_known_zero_contribution')
        if not np.allclose(np.linalg.norm(u[direction_valid], axis=1), 1, atol=ATOL, rtol=RTOL):
            raise StudyError('arrival_unit_vector_required')
        normal = np.einsum('ij,ij->i', u, self._normals[receiver]) > 0
        upper = np.where(normal, q, 0.)
        # Deliberately retain NaN in all M/B components when a contribution is
        # unknown, including axes on which the known direction happens to be zero.
        with np.errstate(invalid='ignore', over='raise'):
            first = q[:, None] * u
            second = np.column_stack([q * u[:, i] * u[:, j] for i, j in SECOND_INDEX])
            additions = np.column_stack((q, upper, first, second))
            np.add.at(self._totals[f], receiver, additions)
        np.add.at(self._unknown[f], receiver, (~valid).astype(np.int64))
        for i in np.flatnonzero(~valid):
            s = int(receiver[i])
            if self._reasons[f][s] is None:
                self._reasons[f][s] = str(event['missing_reason'][i])
        self._next[f] = stop
        self._chunks[f] += 1
        self._largest_chunk = max(self._largest_chunk, count)

    def finish(self, reference: DirectLight) -> ReceiverMoments:
        """Require complete inventory and parity; never turns absent chunks into zero.

        Reference must be the same call's untouched DirectLight result. This
        comparison alone cannot prove that the producer sent true transport paths;
        the core owner must additionally prove callback off/on parity.
        """
        if self._failed or self._finished:
            raise StudyError('direction_collector_closed')
        self._finished = True
        for f, e in enumerate(self._emitters):
            if (e is None and f not in self._unavailable) or (e is not None and self._next[f] != self.n * e):
                raise StudyError('missing_direction_paths_or_fixture')
        if tuple(reference.fixture_ids) != self.fixture_ids:
            raise StudyError('direction_reference_fixture_mismatch')
        for name, channel in (('ppfd_umol_m2_s', 0), ('upper_side_ppfd_umol_m2_s', 1)):
            value = np.asarray(getattr(reference, name), dtype=float)
            actual = self._totals[:, :, channel]
            if value.shape != actual.shape or np.isinf(value).any() or np.any(value[np.isfinite(value)] < 0):
                raise StudyError('invalid_direction_reference')
            if not np.allclose(actual, value, atol=ATOL, rtol=RTOL, equal_nan=True):
                raise StudyError('direction_transport_parity_failed_' + name)
        with np.errstate(over='raise', invalid='ignore'):
            weighted = self._totals[:, :, 2:] * self._area[None, :, None]
            flux = self._totals[:, :, 0] * self._area[None, :]
        self._verified = True
        return ReceiverMoments(self.fixture_ids, self._totals[:, :, 0].copy(), self._totals[:, :, 1].copy(),
                               flux.copy(), weighted[:, :, :3].copy(), weighted[:, :, 3:].copy(),
                               self._unknown.copy(), tuple(tuple(r) for r in self._reasons))

    def summary(self) -> dict:
        """Serializable same-call completeness/parity evidence after successful finish."""
        if not self._verified: raise StudyError('unverified_direction_summary')
        return dict(status='complete_inventory_scalar_and_normal_side_parity_passed',
            receiver_count=self.n, largest_chunk_paths=self._largest_chunk, max_chunk_paths=self.max_chunk_paths,
            accumulator_array_bytes=self._totals.nbytes + self._unknown.nbytes,
            absolute_tolerance=ATOL, relative_tolerance=RTOL,
            fixtures=[dict(fixture_id=fid, emitter_count=e, expected_path_count=self.n * e if e is not None else None,
                received_path_count=self._next[f] if e is not None else None, chunks=self._chunks[f],
                unavailable_fixture_event=f in self._unavailable)
                for f, (fid, e) in enumerate(zip(self.fixture_ids, self._emitters))])


def audit_core() -> dict:
    """Read-only signature audit; a parameter name alone never proves compatibility."""
    path = Path(inspect.getfile(direct_light))
    signature = inspect.signature(direct_light)
    return dict(protocol=PROTOCOL, producer_contract_adopted=True,
                actual_function='tomato3d.light.raytrace.direct_light', signature=str(signature),
                core_path=str(path.resolve()), core_sha256=file_hash(path),
                keyword_only_parameters=[p.name for p in signature.parameters.values() if p.kind == p.KEYWORD_ONLY],
                software_scope_complete=False, actual_direction_export_verified=False,
                physical_validation=False, numerical_policy=POLICY,
                collector_sha256=file_hash(Path(__file__)), schema_sha256=file_hash(SCHEMA_PATH))


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', type=Path, required=True, help='Fresh build directory for a read-only core audit')
    args = parser.parse_args()
    folder = output_dir(args.out)
    report = audit_core()
    write_json(folder / 'core_audit.json', report)
    print('Wrote core_audit.json; adopted callback signature audited, execution evidence is separate.')


if __name__ == '__main__':
    main()
