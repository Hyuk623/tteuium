"""Known-projection recovery for the new capture layout, without another board renderer."""
from pathlib import Path

import numpy as np
import pytest

from tools.multiview_plant import init, validate_plan, reconstruct
from tools.leaf_light.annotations import POINT_COLUMNS, CONTOUR_COLUMNS
from tools.leaf_light.common import read_json, rows, write_json, write_rows
from tools.leaf_light.synthetic import camera_frame
from tools.leaf_light.reconstruction import project


def projected_inputs(folder: Path) -> tuple[Path,Path,Path,Path]:
    init(folder/'draft')
    plan=read_json(folder/'draft/capture_plan.draft.json')
    intr=dict(camera_matrix=[[1200,0,800],[0,1200,600],[0,0,1]],dist_coeffs=[0,0,0,0,0],
              image_width_px=1600,image_height_px=1200)
    target=np.array([0.,0.,150.]); frames=[]
    for entry in plan['frames']:
        polar,az=np.radians(entry['polar_deg']),np.radians(entry['azimuth_deg'])
        center=target+550*np.array([np.sin(polar)*np.cos(az),np.sin(polar)*np.sin(az),np.cos(polar)])
        frame=camera_frame(entry['image_file'],center,target,'top' if entry['polar_deg']==0 else 'side')
        frames.append(frame)
    capture=dict(data_kind='synthetic',plant_id='TEST',session_id='synthetic',frames=frames,intrinsics=intr,
        quality=plan['quality'],physical_blockers=[],variants=plan['variants'])
    # Two planes avoid edge-on views of the leaf in the synthetic full capture.
    corners=np.array([[-30.,-20.,130.],[30.,-20.,136.],[30.,20.,156.],[-30.,20.,150.]])
    points=[]; contours=[]
    for frame in frames:
        for i,xy in enumerate(project(corners,frame,intr)):
            common=dict(image_file=frame['image_file'],organ_id='leaf_001',leaflet_id='unavailable',x_px=xy[0],y_px=xy[1])
            points.append(dict(common,point_id=f'b{i}',boundary_index=i,boundary_count=4))
            contours.append(dict(common,vertex_index=i))
    write_json(folder/'capture.json',capture)
    write_rows(folder/'points.csv',points,POINT_COLUMNS)
    write_rows(folder/'contours.csv',contours,CONTOUR_COLUMNS)
    write_json(folder/'review.json',dict(variant_id='v25',operator='synthetic_test',source='independent_selected_images',
        reviewed_image_files=[f['image_file'] for f in frames]))
    return tuple(folder/name for name in ('capture.json','points.csv','contours.csv','review.json'))


def test_new_plan_has_top_and_three_eight_view_rings(tmp_path):
    init(tmp_path/'draft'); plan=read_json(tmp_path/'draft/capture_plan.draft.json')
    assert len(plan['frames'])==25
    assert [sum(f['polar_deg']==p for f in plan['frames']) for p in (0,45,90,135)]==[1,8,8,8]
    with pytest.raises(ValueError,match='actual'): validate_plan(plan)
    plan.update(plant_id='TEST',session_id='TEST_session',camera_id='phone')
    validate_plan(plan)


def test_known_25_view_points_recover_surface_area_and_height(tmp_path):
    args=projected_inputs(tmp_path); result=reconstruct(*args,tmp_path/'recon')
    assert result['status']=='reconstructed'; assert result['n_failed_leaves']==0
    feature=rows(tmp_path/'recon/leaf_geometry_features.csv')[0]
    assert float(feature['min_z_board_mm'])==pytest.approx(130,abs=1e-6)
    assert float(feature['max_z_board_mm'])==pytest.approx(156,abs=1e-6)
    assert float(feature['area_mm2'])==pytest.approx(np.sqrt(1+.1**2+.5**2)*60*40,rel=1e-6)


def test_reduced_variant_cannot_use_full_annotations_or_wrong_review(tmp_path):
    args=projected_inputs(tmp_path); capture=read_json(args[0]); review=read_json(args[3])
    selected=capture['variants'][0]['image_files'][:2]
    capture['variants'].append(dict(variant_id='v2',image_files=selected)); write_json(args[0],capture)
    review['variant_id']='v2'; write_json(args[3],review)
    with pytest.raises(ValueError,match='match this subset'): reconstruct(*args,tmp_path/'wrong_review')
    review['reviewed_image_files']=selected; write_json(args[3],review)
    with pytest.raises(ValueError,match='excluded'): reconstruct(*args,tmp_path/'wrong_points')
    write_rows(args[1],[r for r in rows(args[1]) if r['image_file'] in selected],POINT_COLUMNS)
    write_rows(args[2],[r for r in rows(args[2]) if r['image_file'] in selected],CONTOUR_COLUMNS)
    result=reconstruct(*args,tmp_path/'v2')
    assert result['status']=='reconstructed'


def test_failed_measured_pose_is_not_replaced_by_nominal_camera_angle(tmp_path):
    args=projected_inputs(tmp_path); capture=read_json(args[0])
    capture['frames'][0].update(pose_status='failed',polar_deg=0,azimuth_deg=0)
    write_json(args[0],capture)
    result=reconstruct(*args,tmp_path/'failed')
    assert result['status']=='failed' and result['reason']=='selected_pose_failed'
    assert rows(tmp_path/'failed/leaf_surfaces.csv')==[]
