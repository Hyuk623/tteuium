"""25-view ChArUco capture and independent labeled-leaf reconstruction.

Nominal polar/azimuth angles select images only. They never substitute for PnP poses.
This adapter leaves the older 41-view study protocol unchanged.
"""
from __future__ import annotations

import argparse
from collections import Counter
from pathlib import Path
import sys
from time import perf_counter

import numpy as np

from tomato3d.calib.board import build_charuco_board, detect_board_corners
from tomato3d.calib.pose import solve_pose
from tomato3d.config import get_settings
from tomato3d.io.images import read_image
from tomato3d.io.schemas import BoardSpec, Intrinsics, LEAF_SURFACES_CSV_COLUMNS, load_json_model
from tomato3d.light.geometry import triangle_areas_mm2
from tools.canopy_light import identifier
from tools.leaf_light.annotations import POINT_COLUMNS, CONTOUR_COLUMNS
from tools.leaf_light.common import (StudyError, digest, file_hash, number, output_dir,
    read_json, rows, template, write_json, write_rows)
from tools.leaf_light.reconstruction import reconstruct_variant


def init(out: Path) -> None:
    folder = output_dir(out)
    settings = get_settings()
    spec = read_json(settings.board_spec_path)
    quality = read_json(settings.quality_thresholds_path)
    previous = template(read_json(settings.capture_config_path))
    frames = [dict(image_file='top_000.jpg',polar_deg=0,azimuth_deg=0)] + [
        dict(image_file=f'polar_{polar:03d}_az_{azimuth:03d}.jpg',polar_deg=polar,azimuth_deg=azimuth)
        for polar in (45,90,135) for azimuth in range(0,360,45)]
    plan = dict(schema_version='multiview-plant-1',plant_id='EDIT_PLANT_ID',session_id='EDIT_SESSION_ID',
        camera_id='EDIT_CAMERA_ID',images_root='images',board_variant_id=spec['variant_id'],frames=frames,
        scale_reference_block_mm=None,
        variants=[dict(variant_id='v25',image_files=[f['image_file'] for f in frames])],
        quality=dict(min_pose_corners=quality['min_charuco_corners_for_pose'],
            max_pose_error_px=quality['max_mean_reprojection_error_px'],
            **{key:previous[key] for key in ('max_point_error_px','min_ray_angle_deg','contour_tolerance_px')}),
        notice='EDIT identifiers, image paths and independently reviewed subsets. Angles describe capture labels only. Keep the same camera/lens/resolution; use phone-normalize when needed.')
    write_json(folder/'capture_plan.draft.json',plan)
    write_json(folder/'annotation_review.template.json',dict(variant_id='v25',operator='',
        source='independent_selected_images',reviewed_image_files=plan['variants'][0]['image_files']))


def validate_plan(plan: dict) -> None:
    if plan.get('schema_version') != 'multiview-plant-1':
        raise StudyError('Unsupported capture plan')
    for key in ('plant_id','session_id','camera_id'):
        identifier(plan.get(key),key)
        if plan[key].startswith('EDIT_'):
            raise StudyError('Fill in actual plant/session/camera IDs')
    frames = plan['frames']
    names = [f['image_file'] for f in frames]
    if not names or len(names) != len(set(names)) or len({Path(n).name.lower() for n in names}) != len(names):
        raise StudyError('Frame filenames must be present and unique, including case-insensitive basenames')
    ids = []
    for variant in plan['variants']:
        ids.append(identifier(variant['variant_id'],'variant_id'))
        selected = variant['image_files']
        if len(selected) < 2 or len(set(selected)) != len(selected) or not set(selected) <= set(names):
            raise StudyError('Each variant needs at least two distinct, known images')
    if not ids or len(set(ids)) != len(ids):
        raise StudyError('Variant IDs must be unique')
    q = plan['quality']
    if type(q['min_pose_corners']) is not int or q['min_pose_corners'] < 4:
        raise StudyError('min_pose_corners must be an integer >= 4')
    for key in ('max_point_error_px','min_ray_angle_deg','contour_tolerance_px'):
        if number(q[key],key) <= 0:
            raise StudyError('Reconstruction quality thresholds must be positive')
    if q['max_pose_error_px'] is not None and number(q['max_pose_error_px'],'max_pose_error_px') <= 0:
        raise StudyError('Pose error threshold must be positive or inactive (null)')


def prepare(plan_path: Path, intrinsics_path: Path, out: Path) -> dict:
    plan = read_json(plan_path); validate_plan(plan)
    settings = get_settings()
    spec = load_json_model(settings.board_spec_path,BoardSpec)
    intr = load_json_model(intrinsics_path,Intrinsics)
    if plan['camera_id'] != intr.camera_id or plan['board_variant_id'] != spec.variant_id:
        raise StudyError('Camera or operational ChArUco board ID mismatch')
    image_root = (plan_path.parent/plan['images_root']).resolve()
    board = build_charuco_board(spec)
    frames = []
    for item in plan['frames']:
        path = (image_root/item['image_file']).resolve()
        if not path.is_relative_to(image_root):
            raise StudyError('Image path leaves images_root')
        frame = dict(item,image_path=str(path),sha256=file_hash(path) if path.is_file() else None,
            view_type='top' if item.get('polar_deg') == 0 else 'side',
            top_position='T0' if item.get('polar_deg') == 0 else None,
            pose_status='failed',failure_reason=None)
        image = read_image(path)
        if image is None:
            frame['failure_reason']='unreadable_image'
        elif image.shape[:2] != intr.image_shape:
            frame['failure_reason']='calibration_resolution_mismatch'
        else:
            pose = solve_pose(detect_board_corners(image,board),intr,board,plan['quality']['min_pose_corners'])
            limit = plan['quality']['max_pose_error_px']
            if pose.is_solved and (limit is None or pose.reprojection_error_px <= limit):
                frame.update(pose_status='solved',rvec_rad=pose.rvec_rad.reshape(3).tolist(),
                    tvec_mm=pose.tvec_mm.reshape(3).tolist(),reprojection_error_px=pose.reprojection_error_px)
            else:
                frame['failure_reason']=pose.failure_reason or 'pose_reprojection_error'
        frames.append(frame)
    blockers=[]
    if not spec.physical_print_verified: blockers.append('physical_print_not_verified')
    measured=number(plan.get('scale_reference_block_mm'),'scale_reference_block_mm',missing=True)
    if measured is None or spec.scale_block_nominal_height_mm is None:
        blockers.append('scale_reference_not_measured')
    elif not np.isclose(measured,spec.scale_block_nominal_height_mm):
        blockers.append('scale_reference_disagrees')
    hashes=Counter(f['sha256'] for f in frames if f['sha256'])
    if any(n>1 for n in hashes.values()): blockers.append('duplicate_image_content')
    result=dict(schema_version='multiview-capture-1',data_kind='observed',plant_id=plan['plant_id'],
        session_id=plan['session_id'],board_variant_id=spec.variant_id,coordinate_frame='board_mm',
        intrinsics=intr.model_dump(mode='json'),frames=frames,quality=plan['quality'],physical_blockers=blockers,
        variants=[dict(v,view_count=len(v['image_files'])) for v in plan['variants']],
        plan_sha256=file_hash(plan_path),intrinsics_sha256=file_hash(intrinsics_path),board_sha256=file_hash(settings.board_spec_path))
    folder=output_dir(out); write_json(folder/'capture.json',result)
    return result


def reconstruct(capture_path: Path, points_path: Path, contours_path: Path, review_path: Path, out: Path) -> dict:
    capture=read_json(capture_path); review=read_json(review_path)
    matches=[v for v in capture['variants'] if v['variant_id'] == review['variant_id']]
    if len(matches)!=1: raise StudyError('Review references unknown variant')
    selection=matches[0]; selected=set(selection['image_files'])
    if review.get('source')!='independent_selected_images' or not review.get('operator','').strip():
        raise StudyError('Record the operator and independent selected-image annotation provenance')
    if set(review['reviewed_image_files'])!=selected or len(review['reviewed_image_files'])!=len(selected):
        raise StudyError('Reviewed images must match this subset exactly')
    for frame in capture['frames']:
        if frame['image_file'] in selected and frame.get('sha256') and file_hash(Path(frame['image_path']))!=frame['sha256']:
            raise StudyError('A source photograph changed after pose estimation')
    points=rows(points_path,POINT_COLUMNS); contours=rows(contours_path,CONTOUR_COLUMNS)
    if any(row['image_file'] not in selected for row in points+contours):
        raise StudyError('Independent annotation CSV includes excluded images')
    started=perf_counter()
    surfaces,diagnostics=reconstruct_variant(capture,selection,points,contours,capture['quality'])
    folder=output_dir(out)
    write_rows(folder/'leaf_surfaces.csv',surfaces,LEAF_SURFACES_CSV_COLUMNS)
    features=[]
    for organ in sorted({r['organ_id'] for r in surfaces}):
        tri=np.array([[[r[f'v{k}_{axis}_mm'] for axis in 'xyz'] for k in range(3)] for r in surfaces if r['organ_id']==organ])
        area=triangle_areas_mm2(tri)
        features.append(dict(plant_id=capture['plant_id'],session_id=capture['session_id'],variant_id=selection['variant_id'],
            organ_id=organ,area_mm2=float(area.sum()),min_z_board_mm=float(tri[:,:,2].min()),
            max_z_board_mm=float(tri[:,:,2].max()),centroid_z_board_mm=float(np.average(tri[:,:,2].mean(axis=1),weights=area))))
    write_rows(folder/'leaf_geometry_features.csv',features,('plant_id','session_id','variant_id','organ_id','area_mm2','min_z_board_mm','max_z_board_mm','centroid_z_board_mm'))
    result=dict(diagnostics,plant_id=capture['plant_id'],session_id=capture['session_id'],variant=selection,
        data_kind=capture['data_kind'],physical_blockers=capture.get('physical_blockers',[]),
        annotation_review=review,capture_sha256=file_hash(capture_path),points_sha256=file_hash(points_path),
        contours_sha256=file_hash(contours_path),reconstruction_seconds=perf_counter()-started,
        geometry_file='leaf_surfaces.csv',geometry_sha256=file_hash(folder/'leaf_surfaces.csv'),
        notice='Observed leaf surfaces only. Open surfaces are intentional; invisible leaves and gaps are not filled. Physical blockers prevent a validated metric claim.')
    write_json(folder/'reconstruction.json',result)
    return result


def main(argv: list[str] | None = None) -> int:
    cli=argparse.ArgumentParser(description=__doc__); sub=cli.add_subparsers(dest='command',required=True)
    initial=sub.add_parser('init'); initial.add_argument('--out',type=Path,required=True)
    prep=sub.add_parser('prepare')
    for name in ('plan','intrinsics','out'): prep.add_argument('--'+name,type=Path,required=True)
    recon=sub.add_parser('reconstruct')
    for name in ('capture','points','contours','review','out'): recon.add_argument('--'+name,type=Path,required=True)
    args=cli.parse_args(argv)
    try:
        if args.command=='init': init(args.out)
        elif args.command=='prepare': prepare(args.plan,args.intrinsics,args.out)
        else: reconstruct(args.capture,args.points,args.contours,args.review,args.out)
    except (ValueError,OSError,KeyError) as exc:
        print(f'Multiview input error: {exc}',file=sys.stderr); return 2
    print(args.out.resolve()); return 0


if __name__=='__main__':
    raise SystemExit(main())
