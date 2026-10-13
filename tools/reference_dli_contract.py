"""Evidence and geometry rules for measured reference light; no transport or fitting."""
from __future__ import annotations

import csv
from datetime import date, datetime, timedelta, timezone
import math
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

import numpy as np

from tools.compound_growth import aware_time
from tools.leaf_light.common import DLI_UNIT, StudyError, file_hash, read_json

READING_COLUMNS = ('reading_id','measured_at','ppfd_umol_m2_s','position_x_mm','position_y_mm','position_z_mm',
                   'sensor_model','sensor_serial','lights_state','notes','support_start_at','support_end_at')
DAILY_COLUMNS = ('basis_id','source_kind','local_date','dli_mol_m2_day','coverage_status','on_duration_s',
                 'n_readings','mean_ppfd_umol_m2_s','ambient_light','applicability_low','applicability_high',
                 'reason','applicability_status','ambient_light_declared','cosine_corrected','levelled','flags')


class Missing(StudyError):
    """Scientifically unsupported input: export an unavailable result, not a fake value."""


def number(value: Any, label: str, minimum: float | None = None) -> float:
    if isinstance(value,bool): raise StudyError('invalid_number:'+label)
    try: result=float(value)
    except (TypeError,ValueError) as exc: raise StudyError('invalid_number:'+label) from exc
    if not math.isfinite(result) or (minimum is not None and result<minimum):
        raise StudyError('invalid_number:'+label)
    return result


def require(value: Any, reason: str) -> Any:
    if value is None or value=='' or value==[] or value=={}: raise Missing(reason)
    return value


def evidence(ref: Any, base: Path, hashes: dict, label: str) -> dict:
    if not isinstance(ref,dict) or not ref.get('path') or not ref.get('sha256'):
        raise Missing(label+'_evidence_missing')
    path=(base/ref['path']).resolve()
    if not path.is_file(): raise Missing(label+'_evidence_missing')
    if file_hash(path)!=ref['sha256']: raise StudyError(label+'_evidence_hash_mismatch')
    hashes[str(path)]=ref['sha256']
    return dict(ref,path=str(path))


def canonical_unit(value: Any) -> None:
    if value=='mol/m2/d':
        raise StudyError('legacy_dli_unit_spelling:unit expected '+DLI_UNIT+', received mol/m2/d; regenerate frozen inputs')
    if value!=DLI_UNIT: raise StudyError('invalid_dli_unit:expected '+DLI_UNIT)


def read_readings(path: Path, position: dict, *, survey: bool = False) -> list[dict]:
    if position.get('reading_unit')!='umol/m2/s': raise StudyError('non_photon_unit')
    with path.open(encoding='utf-8-sig',newline='') as stream:
        reader=csv.DictReader(stream)
        if not reader.fieldnames or 'ppfd_umol_m2_s' not in reader.fieldnames:
            raise StudyError('non_photon_unit')
        required=set(READING_COLUMNS[:10])
        if not required.issubset(reader.fieldnames): raise StudyError('reading_columns_missing')
        raw=list(reader)
    result=[]; seen=set(); times=set()
    for row in raw:
        if None in row or any(v is None for v in row.values()): raise StudyError('malformed_reading_row')
        rid=row['reading_id']
        if not rid or rid in seen: raise StudyError('duplicate_or_empty_reading_id')
        seen.add(rid)
        t=aware_time(row['measured_at'])
        q=number(row['ppfd_umol_m2_s'],'ppfd',0) if row['ppfd_umol_m2_s'] not in ('','unavailable') else None
        xyz=[number(row['position_'+a+'_mm'],'position_'+a) for a in 'xyz']
        key=(t,tuple(xyz)) if survey else t
        if key in times: raise StudyError('ambiguous_duplicate_reading_time')
        times.add(key)
        if row['lights_state'] not in ('on','off','mixed','unknown'): raise StudyError('invalid_lights_state')
        result.append(dict(row,time=t,ppfd=q,position=xyz))
    return sorted(result,key=lambda r:r['time'])


def day_bounds(text: str, zone: ZoneInfo) -> tuple[datetime,datetime]:
    d=date.fromisoformat(text)
    a=datetime(d.year,d.month,d.day,tzinfo=zone)
    nxt=d+timedelta(days=1); b=datetime(nxt.year,nxt.month,nxt.day,tzinfo=zone)
    for t in (a,b):
        if t.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None)!=t.replace(tzinfo=None):
            raise Missing('nonexistent_local_midnight')
    return a.astimezone(timezone.utc),b.astimezone(timezone.utc)


def dates_and_geometry(p: dict, base: Path, hashes: dict, tissue_bases: set[str]) -> tuple[list[str],ZoneInfo]:
    if p.get('schema_version')!='reference-dli-1': raise StudyError('reference_schema_mismatch')
    canonical_unit(p.get('unit'))
    basis=require(p.get('basis_id'),'reference_basis_missing')
    if basis in tissue_bases: raise StudyError('basis_collides_with_tissue_basis')
    require(p.get('frame_id'),'reference_frame_missing'); require(p.get('coordinate_frame'),'reference_frame_missing')
    require(p.get('height_basis'),'height_basis_missing')
    xyz=p.get('position_mm')
    if not isinstance(xyz,list) or len(xyz)!=3 or any(x is None for x in xyz): raise Missing('reference_position_missing')
    for v in xyz: number(v,'position_mm')
    normal=p.get('sensor_normal')
    if p.get('plane')!='horizontal' or normal!=[0,0,1]: raise StudyError('declared_horizontal_upward_sensor_required')
    evidence(p.get('source_ref'),base,hashes,'reference')
    if p.get('cosine_corrected') not in (True,False,'unknown') or type(p.get('cosine_corrected')) not in (bool,str):
        raise Missing('cosine_response_metadata_missing')
    if p.get('cosine_corrected') is True: evidence(p.get('cosine_source_ref'),base,hashes,'cosine')
    if p.get('levelled') is not True: raise Missing('sensor_level_not_established')
    evidence(p.get('level_source_ref'),base,hashes,'level')
    ds=require(p.get('dates'),'date_selection_missing')
    if not isinstance(ds,list) or len(set(ds))!=len(ds): raise StudyError('invalid_selected_dates')
    for d in ds: date.fromisoformat(d)
    zone=ZoneInfo(require(p.get('timezone'),'timezone_missing'))
    policy=p.get('dst_policy')
    if policy not in ('utc_elapsed','reject_transitions'): raise Missing('dst_policy_missing')
    if policy=='reject_transitions':
        for d in ds:
            a,b=day_bounds(d,zone)
            if (b-a).total_seconds()!=86400: raise Missing('dst_transition_refused')
    return sorted(ds),zone


def convex_hull(xy: list[list[float]]) -> list[tuple[float,float]]:
    pts=sorted(set(tuple(p) for p in xy))
    def cross(a,b,c): return (b[0]-a[0])*(c[1]-a[1])-(b[1]-a[1])*(c[0]-a[0])
    halves=[]
    for seq in (pts,list(reversed(pts))):
        stack=[]
        for pt in seq:
            while len(stack)>1 and cross(stack[-2],stack[-1],pt)<=0: stack.pop()
            stack.append(pt)
        halves.append(stack[:-1])
    return halves[0]+halves[1]


def inside_hull(xy: list[float], hull: list) -> bool:
    return len(hull)>=3 and all((b[0]-a[0])*(xy[1]-a[1])-(b[1]-a[1])*(xy[0]-a[0])>=0
                               for a,b in zip(hull,hull[1:]+hull[:1]))


def survey_tolerance(p: dict, survey: list[dict], exposure_s: float, base: Path, hashes: dict) -> dict:
    """Explicit affine local PPFD surface; no extrapolation, fitting lamp PPF or survey averaging."""
    policy=require(p.get('position_tolerance'),'position_tolerance_missing')
    if policy.get('method')!='affine_horizontal_survey': raise Missing('position_gradient_method_unsupported')
    evidence(policy.get('source_ref'),base,hashes,'position_error')
    evidence(policy.get('temporal_transfer_source_ref'),base,hashes,'gradient_temporal_transfer')
    err=number(require(policy.get('allowable_dli_error_mol_m2_day'),'position_error_missing'),'allowable_dli_error',0)
    plane_tol=number(require(policy.get('survey_plane_tolerance_mm'),'survey_plane_tolerance_missing'),'survey_plane_tolerance',0)
    fit_tol=number(require(policy.get('max_fit_residual_umol_m2_s'),'survey_fit_tolerance_missing'),'survey_fit_residual',0)
    accepted=[r for r in survey if r['ppfd'] is not None and r['lights_state']=='on' and r['sensor_model'] and r['sensor_serial']]
    if len(accepted)<3: raise Missing('position_gradient_underdetermined')
    if len({r['ppfd'] for r in accepted})==1: raise Missing('zero_or_unsupported_position_gradient')
    if any(abs(r['position'][2]-p['position_mm'][2])>plane_tol for r in accepted):
        raise Missing('survey_not_in_reference_plane')
    xy=[r['position'][:2] for r in accepted]; design=np.column_stack((np.ones(len(xy)),xy))
    if np.linalg.matrix_rank(design)<3: raise Missing('position_gradient_underdetermined')
    coeff=np.linalg.lstsq(design,np.array([r['ppfd'] for r in accepted]),rcond=None)[0]
    residual=float(np.max(np.abs(design@coeff-np.array([r['ppfd'] for r in accepted]))))
    if residual>fit_tol: raise Missing('survey_gradient_model_not_supported')
    gradient=float(np.linalg.norm(coeff[1:])); hull=convex_hull(xy)
    if not inside_hull(p['position_mm'][:2],hull): raise Missing('reference_outside_survey_support')
    # A flat finite survey alone does not establish an infinite radius.
    if gradient<=np.finfo(float).eps*max(1.,float(np.max(np.abs(coeff)))) or exposure_s<=0:
        raise Missing('zero_or_unsupported_position_gradient')
    dli_gradient=gradient*exposure_s*1e-6
    return dict(method='affine_horizontal_survey',gradient_ppfd_per_mm=gradient,
        gradient_dli_per_mm=dli_gradient,gradient_unit='mol/m2/day/mm',effective_duration_s=exposure_s,
        allowed_distance_mm=err/dli_gradient,allowable_dli_error_mol_m2_day=err,
        coefficients=coeff.tolist(),max_fit_residual_umol_m2_s=residual,support_hull_xy_mm=hull,
        plane_tolerance_mm=plane_tol,survey_reading_ids=[r['reading_id'] for r in accepted])


def select_readings(p: dict, data: list[dict], tolerance: dict) -> tuple[list[dict],list[dict]]:
    included=[]; excluded=[]
    for row in data:
        reason=None
        distance=float(np.linalg.norm(np.array(row['position'])-np.array(p['position_mm'])))
        if distance>tolerance['allowed_distance_mm']: reason='position_outside_derived_tolerance'
        elif not inside_hull(row['position'][:2],tolerance['support_hull_xy_mm']): reason='position_outside_survey_support'
        elif abs(row['position'][2]-p['position_mm'][2])>tolerance['plane_tolerance_mm']: reason='position_outside_survey_plane'
        elif not row['sensor_model'] or not row['sensor_serial']: reason='sensor_identity_missing'
        elif row['ppfd'] is None: reason='reading_unavailable'
        if reason: excluded.append(dict(reading_id=row['reading_id'],reason=reason,distance_mm=distance))
        else: included.append(row)
    return included,excluded


def association(p: dict, tolerance: dict, base: Path, hashes: dict) -> dict:
    item=require(p.get('plant_association'),'plant_association_missing')
    ids=require(item.get('plant_instance_ids'),'plant_association_missing')
    if len(set(ids))!=len(ids) or any(not isinstance(v,str) or not v for v in ids): raise StudyError('invalid_plant_association')
    evidence(item.get('association_evidence'),base,hashes,'plant_association')
    uniform=require(item.get('uniformity_basis'),'uniformity_basis_missing')
    evidence(uniform.get('source_ref'),base,hashes,'uniformity')
    if len(ids)==1: return dict(item,status='declared_single_plant_reference',accepted_plant_instance_ids=ids)
    limit=number(require(uniform.get('max_dli_difference_mol_m2_day'),'uniformity_tolerance_missing'),'uniformity_tolerance',0)
    positions=uniform.get('positions_mm') or {}
    if set(positions)!=set(ids): raise Missing('shared_reference_plant_positions_missing')
    coeff=np.array(tolerance['coefficients']); ref=float(coeff@np.array([1.,*p['position_mm'][:2]]))
    deviations={}
    for pid,xyz in positions.items():
        if len(xyz)!=3 or any(not math.isfinite(number(v,'plant_position')) for v in xyz): raise StudyError('invalid_plant_position')
        if not inside_hull(xyz[:2],tolerance['support_hull_xy_mm']) or abs(xyz[2]-p['position_mm'][2])>tolerance['plane_tolerance_mm']:
            raise Missing('shared_reference_outside_survey_support')
        delta=abs(float(coeff@np.array([1.,*xyz[:2]]))-ref)*tolerance['effective_duration_s']*1e-6
        deviations[pid]=delta
        if delta>limit: raise Missing('shared_reference_uniformity_failed')
    return dict(item,status='survey_supported',accepted_plant_instance_ids=ids,dli_deviations=deviations)
