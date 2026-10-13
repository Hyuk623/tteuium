"""Compare fixed-camera observed mesh and local-plane candidates without filling tissue.

python -m tools.leaf_surface_compare --study build/study.json --out build/fresh_surface
"""
from __future__ import annotations

import argparse
from collections import defaultdict
import json
import os
from pathlib import Path

import cv2
import numpy as np

from tools.compound_surface import KEY, audit_surface, local_patch_faces
from tools.leaf_area_compare import Inputs, resolve
from tools.leaf_light.annotations import POINT_COLUMNS, CONTOUR_COLUMNS
from tools.leaf_light.common import StudyError, output_dir, read_json, rows, write_json, write_rows
from tools.leaf_light.reconstruction import project, reconstruct_variant, triangulate
from tools.plant_structure import Cameras
from tools.plant_traits import record_date
from tools.relative_leaf_area import normalize as normalize_leaf_areas, OUTPUT as RELATIVE_COLUMNS
from tomato3d.io.schemas import LEAF_SURFACES_CSV_COLUMNS


def fit_plane(points_mm: np.ndarray) -> tuple[np.ndarray, np.ndarray, float]:
    xyz = np.asarray(points_mm, float)
    if xyz.ndim != 2 or xyz.shape[1] != 3 or len(xyz) < 3 or not np.isfinite(xyz).all():
        raise StudyError('At least three finite observed points required')
    centre = xyz.mean(axis=0)
    if np.linalg.matrix_rank(xyz-centre) < 2:
        raise StudyError('Collinear observations do not constrain a plane')
    _, _, vt = np.linalg.svd(xyz-centre)
    normal = vt[-1]
    return centre, normal, float(np.sqrt(np.mean(((xyz-centre) @ normal)**2)))


def intersect_plane(centre_mm: np.ndarray, direction: np.ndarray, plane_point_mm: np.ndarray,
                    normal: np.ndarray, minimum_abs_cosine: float) -> np.ndarray:
    if not np.isfinite(minimum_abs_cosine) or not 0 < minimum_abs_cosine < 1:
        raise StudyError('Explicit ray-plane numerical conditioning limit required')
    den = float(direction @ normal)
    if abs(den) < minimum_abs_cosine:
        raise StudyError('Ray nearly parallel to supported plane')
    distance_mm = float((plane_point_mm-centre_mm) @ normal / den)
    if not np.isfinite(distance_mm) or distance_mm <= 0:
        raise StudyError('Supported plane is behind the camera')
    return centre_mm + distance_mm*direction


def plane_points(capture: dict, observations: list[dict], fit_images: list[str], quality: dict,
                 minimum_abs_cosine: float) -> tuple[dict[str, np.ndarray], dict]:
    frames = {f['image_file']: f for f in capture['frames']}
    by_id: dict[str, list] = defaultdict(list)
    for r in observations:
        if r['image_file'] in fit_images:
            by_id[r['point_id']].append(r)
    points = {}
    for point_id, rr in by_id.items():
        if len({r['image_file'] for r in rr}) != len(rr):
            raise StudyError('Duplicate image/point observation')
        for r in rr:
            if frames[r['image_file']].get('pose_status') != 'solved':
                raise StudyError('Plane comparison requires solved baseline board poses')
        obs = [(frames[r['image_file']], np.array([float(r['x_px']), float(r['y_px'])])) for r in rr]
        points[point_id] = triangulate(obs, capture['intrinsics'], quality)[0]
    centre, normal, rms_mm = fit_plane(np.array(list(points.values())))
    cameras = Cameras(capture)
    restored = {}
    for point_id, rr in by_id.items():
        hits = []
        for r in rr:
            origin, direction = cameras.ray(r['image_file'].lower(), [float(r['x_px']), float(r['y_px'])])
            hits.append(intersect_plane(origin, direction, centre, normal, minimum_abs_cosine))
        restored[point_id] = np.mean(hits, axis=0)
    return restored, dict(plane_point_board_mm=centre.tolist(), unsigned_normal=normal.tolist(),
                          triangulated_point_plane_rms_mm=rms_mm, normal_side='unknown')


def errors(points: dict[str, np.ndarray], observations: list[dict], capture: dict, selected: list[str]) -> dict:
    frames = {f['image_file']: f for f in capture['frames']}
    values, absent, failed_pose = [], 0, 0
    for r in observations:
        if r['image_file'] not in selected:
            continue
        if frames[r['image_file']].get('pose_status') != 'solved':
            failed_pose += 1
            continue
        if r['point_id'] not in points:
            absent += 1
            continue
        xy = project(points[r['point_id']][None], frames[r['image_file']], capture['intrinsics'])[0]
        values.append(float(np.linalg.norm(xy-[float(r['x_px']), float(r['y_px'])])))
    return dict(observations=len(values), unavailable_observations=absent + failed_pose,
                failed_pose_observations=failed_pose,
                rms_px=float(np.sqrt(np.mean(np.square(values)))) if values else None,
                max_px=max(values) if values else None,
                status='conditional_on_fixed_camera_calibration' if values else 'unavailable')


def support_views(capture: dict, contours: list[dict], selected: list[str]) -> list:
    frames={f['image_file']:f for f in capture['frames']}
    intr=capture['intrinsics']; width,height=intr['image_width_px'],intr['image_height_px']
    support=[]
    for name in selected:
        rr=sorted([r for r in contours if r['image_file']==name],key=lambda r:int(r['vertex_index']))
        if len(rr)<3:
            continue
        if [int(r['vertex_index']) for r in rr]!=list(range(len(rr))):
            raise StudyError('Invalid contour vertex indices')
        polygon=np.array([[float(r['x_px']),float(r['y_px'])] for r in rr])
        if not np.isfinite(polygon).all() or np.any(polygon<0) or np.any(polygon>=np.array([width,height])):
            raise StudyError('Invalid contour pixels')
        mask=np.zeros((height,width),np.uint8)
        cv2.fillPoly(mask,[np.round(polygon).astype(np.int32)],1)
        support.append((frames[name],intr,mask.astype(bool)))
    return support


def face_evidence(faces: list[dict], patch: dict) -> list[dict]:
    return [{**{k:r[k] for k in KEY},'tissue_patch_id':patch['tissue_patch_id'],
             'identity_status':patch['identity_status'],'support_kind':'landmark_interpolated',
             'topology_review':patch.get('topology_review'),'review_source':patch['review_source']} for r in faces]


def chart_ids(patch: dict) -> tuple[list[str], list[str], list[list[str]]] | None:
    """Explicit observation IDs partition a leaflet into independently supported charts."""
    chart = patch.get('local_chart')
    if chart is None:
        return None
    ids, boundary, holes = (chart.get(k) for k in ('point_ids', 'boundary_point_ids', 'hole_point_ids'))
    if not isinstance(ids, list) or len(ids) < 3 or any(not isinstance(x,str) or not x for x in ids) or len(set(ids)) != len(ids):
        raise StudyError('Unique local chart point IDs required')
    if not isinstance(holes, list):
        raise StudyError('Explicit local chart hole rings required (empty list when none)')
    for ring in [boundary, *holes]:
        if not isinstance(ring,list) or len(ring)<3 or any(not isinstance(x,str) for x in ring) or len(set(ring))!=len(ring) or not set(ring)<=set(ids):
            raise StudyError('Invalid local chart boundary/hole point IDs')
    return ids, boundary, holes


def chart_faces(capture: dict, patch: dict, points: dict, method: str,
                boundary: list[str], holes: list[list[str]]) -> list[dict]:
    names = sorted(points)
    if not set(boundary + [p for ring in holes for p in ring]) <= set(names):
        raise StudyError('Observed chart boundary points unavailable')
    triangles = local_patch_faces(np.array([points[n] for n in names]),
                                 [names.index(n) for n in boundary],
                                 [[names.index(n) for n in ring] for ring in holes])
    result=[]
    for i,tri in enumerate(triangles):
        row=dict(plant_id=capture['plant_id'],session_id=capture['session_id'],geometry_variant_id=method,
                 geometry_source='reconstructed',organ_class='leaf',organ_id=patch['organ_id'],leaflet_id=patch['leaflet_id'],
                 triangle_id=f"{patch['tissue_patch_id']}:{i}",normal_convention='unknown')
        row.update({f'v{v}_{a}_mm':float(tri[v,j]) for v in range(3) for j,a in enumerate('xyz')})
        result.append(row)
    return result


def load_support(capture: dict, patch: dict, contours: list[dict], study: dict,
                 base: Path, inputs: Inputs) -> list:
    """Reuse the existing visible-support contract; hidden pixels are not negatives."""
    if 'visible_support' not in patch:
        if chart_ids(patch) is not None:
            raise StudyError('Local charts require explicit original-coordinate visible_support masks')
        return support_views(capture,contours,study['fit_images'])
    support=[]; seen=set(); frames={f['image_file']:f for f in capture['frames']}
    for v in patch['visible_support']:
        name=v['image_file']
        if name not in frames or name in seen:
            raise StudyError('Unknown or duplicate visibility image')
        seen.add(name)
        if v.get('visibility') not in ('visible','occluded','unknown'):
            raise StudyError('Explicit visible/occluded/unknown visibility required')
        if not v.get('review_source'):
            raise StudyError('Visibility review provenance required')
        if v['visibility'] != 'visible':
            continue
        if name not in study['fit_images']:
            raise StudyError('Held-out masks cannot constrain fitted surface support')
        if frames[name].get('pose_status')!='solved':
            raise StudyError('Visible support requires solved fixed camera poses')
        if not v.get('mask_sha256'):
            raise StudyError('Visible mask hash required')
        path=inputs.add(resolve(base,v['mask']),v['mask_sha256'])
        mask=cv2.imdecode(np.fromfile(path,dtype=np.uint8),cv2.IMREAD_GRAYSCALE)
        intr=capture['intrinsics']
        if mask is None or mask.shape!=(intr['image_height_px'],intr['image_width_px']):
            raise StudyError('Visible mask must use original calibrated image coordinates')
        support.append((frames[name],intr,mask!=0))
    return support


def compare_patch(capture: dict, point_rows: list[dict], contour_rows: list[dict], patch: dict,
                  study: dict, visible_support: list | None = None) -> dict:
    fit = study['fit_images']; heldout = study['heldout_images']
    if len(fit) < 2 or len(set(fit)) != len(fit) or len(set(heldout)) != len(heldout) or set(fit) & set(heldout):
        raise StudyError('Distinct fit views and disjoint held-out views required')
    frames = {f['image_file']: f for f in capture['frames']}
    if not set(fit + heldout).issubset(frames):
        raise StudyError('Unknown evaluation image')
    organ, leaflet = patch['organ_id'], patch['leaflet_id']
    output = dict(organ_id=organ, leaflet_id=leaflet, tissue_patch_id=patch['tissue_patch_id'],
                  physical_validation=False, suitable_for_ppfd=False,
                  total_tissue_area_cm2=None, curved_candidate=dict(status='unavailable', reason='reviewed_curved_fit_contract_missing'))
    if patch.get('identity_status') != 'confirmed' or patch.get('point_review_status') != 'confirmed' or not patch.get('review_source'):
        return {**output, 'status': 'reviewed_physical_correspondences_missing', 'methods': []}
    if any(frames[name].get('pose_status') != 'solved' for name in fit):
        return {**output, 'status': 'fit_pose_unavailable', 'methods': []}
    observations = [r for r in point_rows if r['organ_id']==organ and r['leaflet_id']==leaflet]
    chart = chart_ids(patch)
    if chart is not None:
        observations = [r for r in observations if r['point_id'] in chart[0]]
        if set(chart[0]) != {r['point_id'] for r in observations if r['image_file'] in fit}:
            return {**output,'status':'chart_observations_missing','methods':[]}
    output['observed_point_ids'] = sorted({r['point_id'] for r in observations})
    output['local_chart'] = patch.get('local_chart')
    output['visibility_evidence'] = patch.get('visible_support')
    contours = [r for r in contour_rows if r['organ_id']==organ and r['leaflet_id']==leaflet]
    if not observations:
        return {**output, 'status': 'observations_missing', 'methods': []}
    for row in observations:
        if row['image_file'] not in frames:
            raise StudyError('Unknown observation image')
        x, y = float(row['x_px']), float(row['y_px'])
        intr = capture['intrinsics']
        if not np.isfinite([x, y]).all() or not (0 <= x < intr['image_width_px'] and 0 <= y < intr['image_height_px']):
            raise StudyError('Invalid observation pixels')
    quality = study['quality']
    baseline, baseline_diag = ([],dict(status='explicit_local_chart',geometry='fixed_pose_DLT_piecewise_linear')) if chart else reconstruct_variant(capture, dict(image_files=fit, variant_id='existing_mesh'), observations, contours, quality)
    allpoints: dict[str, list] = defaultdict(list)
    for r in observations:
        if r['image_file'] in fit:
            allpoints[r['point_id']].append(r)
    points = {}
    try:
        for name, rr in allpoints.items():
            if len({r['image_file'] for r in rr}) != len(rr):
                raise StudyError('Duplicate image/point observation')
            points[name] = triangulate([(frames[r['image_file']], np.array([float(r['x_px']),float(r['y_px'])])) for r in rr], capture['intrinsics'], quality)[0]
        if chart:
            baseline = chart_faces(capture,patch,points,'existing_mesh',chart[1],chart[2])
    except (StudyError, ValueError, np.linalg.LinAlgError) as exc:
        return {**output, 'status': 'triangulation_failed', 'reason': str(exc), 'methods': [], 'baseline_diagnostics': baseline_diag}
    support = visible_support if visible_support is not None else ([] if chart else support_views(capture,contours,fit))

    def method(name: str, faces: list[dict], pp: dict, detail: dict) -> dict:
        evidence = face_evidence(faces,patch)
        audit = audit_surface(faces,evidence,study['surface_policy'],{patch['tissue_patch_id']:support})
        return dict(method=name, faces=faces, audit=audit, points_mm={k:v.tolist() for k,v in pp.items()},
                    training=errors(pp,observations,capture,fit), heldout=errors(pp,observations,capture,heldout),
                    detail=detail, physical_validation=False)

    methods = [method('existing_mesh',baseline,points,baseline_diag)]
    try:
        fitted, plane = plane_points(capture,observations,fit,quality,study['minimum_abs_ray_plane_cosine'])
        boundary_map = {}
        for r in observations:
            if not chart and r['image_file'] in fit and int(r['boundary_index']) >= 0:
                idx = int(r['boundary_index'])
                if idx in boundary_map and boundary_map[idx] != r['point_id']:
                    raise StudyError('Conflicting boundary identities')
                boundary_map[idx] = r['point_id']
        counts = {int(r['boundary_count']) for r in observations if r['image_file'] in fit}
        if not chart and (len(counts) != 1 or set(boundary_map) != set(range(next(iter(counts))))):
            raise StudyError('Incomplete plane boundary')
        surface_rows = chart_faces(capture,patch,fitted,'observed_plane',
                                    chart[1] if chart else [boundary_map[i] for i in sorted(boundary_map)],
                                    chart[2] if chart else [])
        methods.append(method('observed_plane',surface_rows,fitted,plane))
    except (StudyError, ValueError, np.linalg.LinAlgError) as exc:
        methods.append(dict(method='observed_plane',status='unavailable',reason=str(exc)))
    return {**output,'status':'diagnostic_comparison','methods':methods}


def run(path: Path, out: Path) -> dict:
    inputs=Inputs(); study=read_json(inputs.add(path)); base=path.resolve().parent
    for name in ('leaf_surface_compare.py','leaf_surface_compare.html','compound_surface.py','plant_structure.py','visible_leaf_patch.py','plant_site.py','plant_traits.py','relative_leaf_area.py'):
        inputs.add(Path(__file__).with_name(name))
    inputs.add(Path(__file__).parent/'leaf_light/reconstruction.py')
    if study.get('schema') != 'leaf-surface-comparison-1':
        raise StudyError('Unsupported surface comparison study')
    capture_path=inputs.add(resolve(base,study['capture'])); capture=read_json(capture_path)
    capture_date=record_date(capture) or None
    if capture.get('coordinate_frame') not in ('board','board_mm',
            'board; origin inner corner 0; +Z away from the board surface; millimetres'):
        raise StudyError('Explicit supported board frame required')
    for path_key,hash_key in [('intrinsics_path','intrinsics_sha256'),('board_spec_path','board_spec_sha256')]:
        if capture.get(path_key):
            inputs.add(resolve(capture_path.parent,capture[path_key]),capture.get(hash_key))
    points=rows(inputs.add(resolve(base,study['points'])),POINT_COLUMNS)
    contours=rows(inputs.add(resolve(base,study['contours'])),CONTOUR_COLUMNS) if study.get('contours') else []
    for p in study['patches']:
        if p.get('holes'):
            raise StudyError('Use local_chart.hole_point_ids and reviewed visible_support for holes')
    names=defaultdict(list)
    for p in study['patches']:
        names[(p['organ_id'],p['leaflet_id'])].append(p)
    if any(len(pp)>1 and any(chart_ids(p) is None for p in pp) for pp in names.values()):
        raise StudyError('Multiple patches of one leaflet require explicit local charts')
    global_audits={}
    patch_ids=[p['tissue_patch_id'] for p in study['patches']]
    if len(set(patch_ids))!=len(patch_ids):
        raise StudyError('Repeated physical patch selection would double count tissue')
    support_by_patch={p['tissue_patch_id']:load_support(capture,p,
        [r for r in contours if r['organ_id']==p['organ_id'] and r['leaflet_id']==p['leaflet_id']],study,base,inputs) for p in study['patches']}
    results=[compare_patch(capture,points,contours,p,study,support_by_patch[p['tissue_patch_id']]) for p in study['patches']]
    for method_name in ('existing_mesh','observed_plane'):
        faces=[]; evidence=[]; supports={}
        for patch,result in zip(study['patches'],results):
            for method in result['methods']:
                if method['method']!=method_name:
                    continue
                rr=method.get('faces',[]);faces.extend(rr);evidence.extend(face_evidence(rr,patch))
                supports[patch['tissue_patch_id']]=support_by_patch[patch['tissue_patch_id']]
        global_audits[method_name]=audit_surface(faces,evidence,study['surface_policy'],supports)
    views=[]
    from tools.plant_site import thumb
    for frame in capture['frames']:
        name=frame['image_file']
        if name not in study['fit_images']+study['heldout_images']:
            continue
        source=inputs.add(resolve(capture_path.parent,frame['image_path']),frame.get('sha256'))
        projections=[]
        for patch in results:
            for method in patch['methods']:
                pp=method.get('points_mm',{})
                projections.append(dict(organ_id=patch['organ_id'],leaflet_id=patch['leaflet_id'],
                    tissue_patch_id=patch['tissue_patch_id'],method=method['method'],
                    point_ids=list(pp) if frame.get('pose_status')=='solved' else [],
                    xy_px=project(np.array(list(pp.values())),frame,capture['intrinsics']).tolist() if pp and frame.get('pose_status')=='solved' else []))
        masks=[]
        for patch in study['patches']:
            for evidence in patch.get('visible_support',[]):
                if evidence['image_file']==name and evidence['visibility']=='visible':
                    mask_path=resolve(base,evidence['mask'])
                    masks.append(dict(tissue_patch_id=patch['tissue_patch_id'],image_data=thumb(mask_path),
                        source_mask=os.path.relpath(mask_path,out.resolve()).replace('\\','/')))
        views.append(dict(image_file=name,role='heldout' if name in study['heldout_images'] else 'fit',
                          support_masks=masks,
                          image_data=thumb(source),width_px=capture['intrinsics']['image_width_px'],
                          height_px=capture['intrinsics']['image_height_px'],
                          source_image=os.path.relpath(source,out.resolve()).replace('\\','/'),
                          projections=projections,observations=[r for r in points if r['image_file']==name]))
    inputs.verify()
    folder=output_dir(out)
    labelled_areas=[]
    label_order=list(dict.fromkeys((p['organ_id'],p['leaflet_id']) for p in study['patches']))
    for method_name,audit in global_audits.items():
        for organ_id,leaflet_id in label_order:
            accepted=[f for f in audit['faces'] if f['organ_id']==organ_id and f['leaflet_id']==leaflet_id and f['eligible_supported_area']]
            labelled_areas.append(dict(plant_id=capture['plant_id'],session_id=capture['session_id'],capture_date=capture_date,
                area_method=method_name,area_scope='supported_partial_surface',view_id=None,
                label_id=f'{organ_id}/{leaflet_id}',area_cm2=sum(f['area_mm2'] for f in accepted)/100 if accepted else None))
    relative_areas=normalize_leaf_areas(labelled_areas)
    write_rows(folder/'relative_leaf_areas.csv',relative_areas,RELATIVE_COLUMNS)
    report=dict(schema='leaf-surface-comparison-1',patches=results,views=views,global_surface_audits=global_audits,source_hashes=inputs.hashes,
                relative_leaf_areas=relative_areas,relative_area_reference_rule='first labelled leaf in supplied patch order per method',
                plant_id=capture['plant_id'],session_id=capture['session_id'],capture_date=capture_date,
                source_hashes_verified=True,physical_validation=False,suitable_for_ppfd=False,
                curved_candidate_status='reviewed_contract_missing', evidence_kind=study.get('evidence_kind','unclassified'))
    write_json(folder/'comparison.json',report); write_json(folder/'study.snapshot.json',study)
    write_json(folder/'capture.snapshot.json',capture)
    faces=[r for p in results for m in p['methods'] for r in m.get('faces',[])]
    write_rows(folder/'candidate_surfaces.csv',faces,LEAF_SURFACES_CSV_COLUMNS)
    compounds=[dict(r,capture_date=capture_date) for audit in global_audits.values() for r in audit['compounds']]
    write_rows(folder/'compound_areas.csv',compounds,(*KEY[:4],'supported_area_cm2','supported_faces','input_faces',
                                                    'total_area_cm2','geometry_status','capture_date'))
    inventory=[dict(plant_id=capture['plant_id'],session_id=capture['session_id'],capture_date=capture_date,
                    organ_id=p['organ_id'],leaflet_id=p['leaflet_id'],tissue_patch_id=p['tissue_patch_id'],
                    status=p['status'],observed_point_count=len(p.get('observed_point_ids',[]))) for p in results]
    write_rows(folder/'patch_inventory.csv',inventory,('plant_id','session_id','capture_date','organ_id','leaflet_id',
                                                     'tissue_patch_id','status','observed_point_count'))
    template=Path(__file__).with_suffix('.html').read_text(encoding='utf-8')
    payload=json.dumps(report,ensure_ascii=False,allow_nan=False).replace('<','\\u003c')
    (folder/'viewer.html').write_text(template.replace('__SURFACE_DATA__',payload),encoding='utf-8')
    return report


def main() -> None:
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--study',type=Path,required=True); parser.add_argument('--out',type=Path,required=True)
    args=parser.parse_args(); result=run(args.study,args.out)
    print(json.dumps(dict(patches=len(result['patches']),physical_validation=False,curved_candidate_status=result['curved_candidate_status'])))


if __name__=='__main__':
    main()
