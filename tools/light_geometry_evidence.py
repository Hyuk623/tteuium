"""Read-only optical geometry boundary audit; python -m tools.light_geometry_evidence --help.

Computable geometry is not evidence of physical accuracy. No area reconstruction,
biological face inference, G correction or camera-occlusion attenuation occurs here.
"""
from __future__ import annotations

import argparse
import csv
import json
from pathlib import Path

import numpy as np

from tomato3d.io.schemas import LEAF_PATCHES_CSV_COLUMNS, LEAF_SURFACES_CSV_COLUMNS
from tomato3d.light.geometry import load_geometry, triangle_areas_mm2
from tomato3d.light.scene import LightInputError
from tools.leaf_light.common import StudyError, file_hash, output_dir, read_json, write_json

VERSION = 'optical-geometry-evidence-1'
MISSING = (None, '', 'unavailable', 'unknown')


def audit_surface(path: Path, data_kind: str) -> dict:
    """Audit a core triangle/patch CSV, or explain why a partial A2 table cannot place a surface.

    Missing science is unavailable; malformed/degenerate/duplicate geometry is invalid.
    Input values and claimed review flags never establish real optical eligibility.
    """
    if data_kind not in ('synthetic', 'observed_geometry', 'hypothetical_layout'):
        raise StudyError('explicit_data_kind_required')
    path = path.resolve()
    result = dict(schema_version=VERSION, source_ref=dict(path=str(path), sha256=file_hash(path)),
        data_kind=data_kind, geometric_computability='unavailable', reasons=[], variants=[],
        physical_ppfd_eligibility='unavailable', physical_validation=False,
        physical_reasons=['independent_geometry_scale_pose_area_and_optical_validation_required'],
        biological_face_evidence='separate_reviewed_mapping_required',
        coordinate_frame='board_mm', area_basis='one_sided_surface_geometry',
        area_conversion='mm2 * 1e-6 = m2; cm2 * 1e-4 = m2 only for explicitly cm2 inputs',
        receiving_ppfd_unit='umol/m2/s', integrated_flux_unit='umol/s',
        imaging_occlusion='not_lamp_visibility', extra_G_or_imaging_lambda_applied=False)
    if data_kind == 'synthetic': result['physical_reasons'].append('synthetic_geometry_not_physical_evidence')
    with path.open(encoding='utf-8-sig', newline='') as handle:
        reader = csv.DictReader(handle); header = reader.fieldnames or []; records = list(reader)
    triangle_columns = [f'v{i}_{a}_mm' for i in range(3) for a in 'xyz']
    centroid_columns = [f'centroid_{a}_mm' for a in 'xyz']
    if not records:
        result['reasons'] = ['no_leaf_surfaces']; return result
    is_triangles = header == list(LEAF_SURFACES_CSV_COLUMNS)
    is_patches = header == list(LEAF_PATCHES_CSV_COLUMNS)
    if not (is_triangles or is_patches):
        # An area/normal tuple is evidence about parameters, not a located lamina.
        if any(k in header for k in ('area_cm2', 'area_mm2', 'normal_zenith_rad', 'normal_tilt_deg',
                                     'leaf_area_proxy_cm2', 'hull_footprint_cm2', 'projected_area_cm2')):
            if any(k in header for k in ('leaf_area_proxy_cm2', 'hull_footprint_cm2', 'projected_area_cm2')):
                result['reasons'].append('projected_area_not_physical_receiving_surface')
            if not all(all(row.get(k) not in MISSING for k in centroid_columns) for row in records):
                result['reasons'].append('receiving_surface_position_unavailable')
            result['reasons'].append('receiving_surface_shape_unavailable')
        else:
            result['geometric_computability'] = 'invalid'
            result['reasons'].append('unsupported_geometry_table_schema')
        result.update(coordinate_frame='unavailable_undeclared', area_basis='unavailable_undeclared')
        return result
    required_geometry = triangle_columns if is_triangles else centroid_columns + [
        'area_mm2', 'length_to_width_ratio', 'normal_tilt_deg', 'normal_azimuth_deg']
    missing = sorted({k for row in records for k in required_geometry if row.get(k) in MISSING})
    if missing:
        result['missing_fields'] = missing
        if any(k in missing for k in (triangle_columns if is_triangles else centroid_columns)):
            result['reasons'].append('receiving_surface_position_unavailable')
        if is_triangles or 'length_to_width_ratio' in missing:
            result['reasons'].append('receiving_surface_shape_unavailable')
        if not result['reasons']: result['reasons'].append('receiving_surface_parameters_unavailable')
        return result
    try:
        geometry = load_geometry([path])
        for variant, surfaces in geometry.items():
            seen = set()
            for pid, vertices in zip(surfaces.plant_ids, surfaces.vertices_board_mm):
                key = (pid, tuple(sorted(map(tuple, vertices.tolist()))))
                if key in seen: raise LightInputError('duplicate_geometry_face')
                seen.add(key)
            areas = triangle_areas_mm2(surfaces.vertices_board_mm)[surfaces.is_receiver]
            result['variants'].append(dict(geometry_variant_id=variant,
                plant_ids=surfaces.plant_id_set, session_ids=sorted(set(surfaces.session_ids)),
                geometry_sources=sorted(set(surfaces.geometry_sources)),
                triangle_count=surfaces.n_triangles, receiver_triangle_count=int(np.sum(surfaces.is_receiver)),
                one_sided_area_mm2=float(np.sum(areas)), one_sided_area_m2=float(np.sum(areas)*1e-6),
                normal_convention='geometric_winding_not_botanical_evidence',
                surface_support='supplied_triangles_only_no_missing_tissue_extrapolation',
                shape_assumption='flat_rectangle' if is_patches else 'piecewise_planar_triangles'))
        result['geometric_computability'] = 'available'
    except (LightInputError, ValueError, KeyError) as exc:
        result.update(geometric_computability='invalid', reasons=[str(exc)], variants=[])
    return result


def snapshot_evidence(prepared: Path, snapshot: dict, manifest: dict) -> dict:
    """Bind boundary evidence to the existing materialized full-canopy geometry and scene."""
    result = audit_surface(prepared/'leaf_surfaces.csv', manifest['plan']['case']['data_kind'])
    result.update(geometry_snapshot_id=snapshot['geometry_snapshot_id'],
        scene_ref=dict(path=str((prepared/'scene.json').resolve()), sha256=file_hash(prepared/'scene.json')),
        board_frame_ids=snapshot['board_frame_ids'], grow_frame='grow_mm',
        placements=manifest['audit']['resolved_placements'],
        surface_reviews=manifest['audit']['surface_reviews'],
        evidence_status='review_declarations_retained_not_independent_metric_validation',
        diagnostic_transport='available' if manifest['backend']=='direct' else 'native_scalar_only',
        reference_dli_dependency='none_measured_reference_validated_separately')
    return result


def check_package_evidence(folder: Path, package: dict) -> None:
    """Validate additive evidence and refuse fabricated physical claims, including legacy outputs."""
    if package.get('physical_validation') is not False or package.get('suitable_for_ppfd') is True:
        raise StudyError('unsupported_physical_ppfd_claim')
    audit = read_json(folder/'audit.json')
    if audit.get('physical_validation') is not False:
        raise StudyError('unsupported_physical_ppfd_claim')
    capabilities = read_json(folder/'capabilities.json')
    if capabilities.get('physical_validation') != 'unavailable_independent_calibration_required':
        raise StudyError('unsupported_physical_ppfd_claim')
    marker = package.get('optical_geometry_contract')
    if marker is None:
        if any(Path(p).name == 'light_geometry_evidence.py' for p in package['code_hashes']):
            raise StudyError('missing_optical_geometry_contract')
        return  # Pre-extension output; it never established physical eligibility.
    if marker != VERSION: raise StudyError('unknown_optical_geometry_contract')
    request = read_json(Path(package['request_source_ref']['path']))
    base = Path(package['request_source_ref']['path']).parent
    expected = []
    for snapshot in request['snapshots']:
        prepared = (base/snapshot['prepared_run']).resolve()
        manifest = read_json(prepared/'manifest.json')
        for name in ('leaf_surfaces.csv', 'scene.json', 'manifest.json'):
            p = prepared/name
            if package['source_hashes'].get(str(p)) != file_hash(p):
                raise StudyError('optical_geometry_source_binding_missing')
        expected.append(snapshot_evidence(prepared, snapshot, manifest))
    if audit.get('optical_geometry') != expected:
        raise StudyError('optical_geometry_evidence_mismatch')


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--geometry', type=Path, required=True)
    parser.add_argument('--data-kind', required=True, choices=('synthetic','observed_geometry','hypothetical_layout'))
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    result = audit_surface(args.geometry, args.data_kind)
    folder = output_dir(args.out); write_json(folder/'geometry_audit.json', result)
    print(json.dumps(result))
    if result['geometric_computability']=='invalid': raise SystemExit(1)


if __name__ == '__main__':
    main()
