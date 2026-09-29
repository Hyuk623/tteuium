"""Research invariants: no teacher leakage, physical references, missingness and geometry."""
from __future__ import annotations

import copy
from pathlib import Path

import numpy as np
import pytest

from tools.leaf_light.common import (ROOT, StudyError, digest, freeze, load_protocol, read_json,
                                    rows, template, variants, write_json, write_rows)
from tools.leaf_light.reconstruction import reconstruct, reconstruct_variant, triangulate, project
from tools.leaf_light.synthetic import make_inputs, camera_frame
from tools.leaf_light.optics import run, read_measurements, disk_receivers, sensor_predictions
from tools.leaf_light.evaluation import evaluate_data, paired_bootstrap, evaluate
from tools.light_study import main


@pytest.fixture
def protocol(tmp_path):
    p = template(read_json(ROOT / "config/capture_config.json"))
    draft = tmp_path / "draft.json"
    write_json(draft, p)
    freeze(draft, tmp_path / "frozen")
    return tmp_path / "frozen/protocol.json"


@pytest.fixture
def synthetic(protocol, tmp_path):
    folder = tmp_path / "inputs"
    make_inputs(protocol, folder)
    return folder


def test_approved_subsets_are_exact_and_unique(protocol):
    p, _ = load_protocol(protocol)
    choices = variants(p)
    assert len(choices) == 22
    assert {v["view_count"] for v in choices} == {41,37,19,13,10,7,5,3,2}
    assert len({v["variant_id"] for v in choices}) == 22
    for v in choices:
        assert len(v["side_indices"]) + len(v["top_positions"]) == v["view_count"]
        side = v["side_indices"]
        assert len(side) == len(set(side))
        if len(side)>1:
            assert len(set(np.diff(side))) == 1
        if v["view_count"]<41:
            assert v["top_positions"] == ["T0"]


def test_changed_frozen_protocol_rejected(protocol):
    data = read_json(protocol)
    data["protocol"]["nrmse_limit_pct"] = 99
    write_json(protocol, data)
    with pytest.raises(StudyError, match="changed"):
        load_protocol(protocol)


def test_output_stays_under_build(tmp_path):
    from tools.leaf_light.common import output_dir
    with pytest.raises(StudyError, match="build"):
        output_dir(ROOT / "config/should_not_exist")


def test_reconstructs_known_points_and_metric_scale(protocol, synthetic):
    p, _ = load_protocol(protocol)
    capture = read_json(synthetic / "capture.json")
    true = np.array([27.,-12.,133.])
    obs = [(f, project(true[None], f, capture["intrinsics"])[0]) for f in capture["frames"][::7]]
    point, error = triangulate(obs, capture["intrinsics"], p)
    np.testing.assert_allclose(point, true, atol=1e-7)
    assert error < 1e-7


def test_collinear_rays_rejected(protocol, synthetic):
    p, _ = load_protocol(protocol)
    capture = read_json(synthetic / "capture.json")
    frame = capture["frames"][0]
    xy = project(np.array([[0.,0.,150.]]), frame, capture["intrinsics"])[0]
    with pytest.raises(StudyError):
        triangulate([(frame,xy),(frame,xy)], capture["intrinsics"], p)


def test_excluded_view_cannot_change_reduced_geometry(protocol, synthetic):
    p, _ = load_protocol(protocol)
    capture = read_json(synthetic / "capture.json")
    selection = next(v for v in capture["variants"] if v["variant_id"] == "v02_s00")
    points, contours = rows(synthetic/"points.csv"), rows(synthetic/"contours.csv")
    first, _ = reconstruct_variant(capture,selection,points,contours,p)
    assert first
    altered = copy.deepcopy(points)
    for row in altered:
        if row["image_file"] not in selection["image_files"]:
            row["x_px"] = "99999999"
            row["boundary_count"] = "9000"
    second, _ = reconstruct_variant(capture,selection,altered,contours,p)
    assert first == second


def test_missing_leaf_boundary_not_hallucinated(protocol, synthetic):
    p, _ = load_protocol(protocol)
    capture = read_json(synthetic / "capture.json")
    points = [r for r in rows(synthetic/"points.csv") if r["point_id"] != "P2"]
    surface, diagnostics = reconstruct_variant(capture,capture["variants"][0],points,rows(synthetic/"contours.csv"),p)
    assert surface == []
    assert diagnostics["leaves"][0]["reason"] == "boundary_not_fully_observed"


def test_finite_sensor_is_area_not_center_sample(protocol):
    p, _ = load_protocol(protocol)
    row = dict(point_mm=np.array([0.,0.,0.]), normal=np.array([0.,0.,1.]), radius_mm=10.)
    sensors, n = disk_receivers([row],p)
    assert n == 48
    np.testing.assert_allclose(sensors.points_grow_mm.mean(axis=0),[0,0,0],atol=1e-12)
    # Equal-area disk integration: mean r^2 = R^2/2. A center sample would be 0.
    assert np.mean(np.sum(sensors.points_grow_mm**2,axis=1)) == pytest.approx(50)
    assert np.mean(sensors.points_grow_mm[:,0]>0) == pytest.approx(.5)
    tilted = dict(row, normal=np.array([1.,0.,0.]))
    points, _ = disk_receivers([tilted],p)
    np.testing.assert_allclose(points.points_grow_mm[:,0],0,atol=1e-12)


def small_protocol():
    p = template(read_json(ROOT/"config/capture_config.json"))
    p.update(evaluation_plants=["A","B","C"], development_plants=["D"],session_slots=["s1","s2"],
             sites_per_session=2,replicates_per_site=2,minimum_evaluation_plants=3,bootstrap_iterations=300)
    return p


def data_for(p, reference=100., candidate=100.):
    result=[]
    for v in variants(p):
        for plant in p["evaluation_plants"]:
            for slot in p["session_slots"]:
                for site in range(p["sites_per_session"]):
                    for repeat in range(p["replicates_per_site"]):
                        result.append(dict(plant_id=plant,session_id=slot,session_slot=slot,
                            variant_id=v["variant_id"],view_count=v["view_count"],reading_id=f"{site}-{repeat}",
                            site_id=str(site),replicate_id=str(repeat),region_label="upper",measurement_status="valid",
                            measured_ppfd_umol_m2_s="100",predicted_ppfd_umol_m2_s=str(reference if v["view_count"]==41 else candidate),run_status="ok"))
    return result


def test_noninferiority_and_absolute_reference_gate():
    p=small_protocol()
    result,_,_=evaluate_data(p,data_for(p,100,103))
    assert result["minimum_tested_view_count"] == 2
    reduced=result["variants"][-1]
    assert reduced["upper_one_sided_pp"]==pytest.approx(3)
    bad,_,_=evaluate_data(p,data_for(p,130,131))
    assert bad["minimum_tested_view_count"] is None
    assert "41_view_reference_not_qualified" in bad["variants"][-1]["failure_reasons"]


def test_failed_sessions_remain_in_denominator():
    p=small_protocol()
    data=[r for r in data_for(p) if not (r["plant_id"]=="C" and r["session_slot"]=="s2")]
    result,coverage,_=evaluate_data(p,data)
    assert result["variants"][0]["success_fraction"]==pytest.approx(5/6)
    assert result["minimum_tested_view_count"] is None
    assert any(r["plant_id"]=="C" and r["session_slot"]=="s2" and not r["success"] for r in coverage)


def test_missing_prediction_is_not_a_zero_or_dropped_success():
    p=small_protocol()
    data=data_for(p)
    for row in data:
        if row["variant_id"]=="v02_s00":
            row["predicted_ppfd_umol_m2_s"]="unavailable"
    result,_,_=evaluate_data(p,data)
    variant=next(v for v in result["variants"] if v["variant_id"]=="v02_s00")
    assert variant["nrmse_pct"] is None and variant["success_fraction"]==0
    assert result["minimum_tested_view_count"]==3


def test_reference_measurement_identity_enforced():
    p=small_protocol()
    data=data_for(p)
    data[-1]["measured_ppfd_umol_m2_s"]="101"
    with pytest.raises(StudyError,match="identical"):
        evaluate_data(p,data)


def test_genuine_zero_ppfd_is_valid_but_normalization_unavailable():
    p=small_protocol()
    data=data_for(p,0,0)
    for row in data:
        row["measured_ppfd_umol_m2_s"]="0"
    result,_,_=evaluate_data(p,data)
    assert result["valid_measurement_count"]==24
    assert result["variants"][0]["rmse"]==0
    assert result["variants"][0]["nrmse_pct"] is None
    assert result["minimum_tested_view_count"] is None


def test_bootstrap_counts_plants_not_repeated_readings():
    p=small_protocol()
    assert paired_bootstrap({"A":[(100,100,101)]*1000},p)==(None,None)
    small={k:[(100,100,101+i)] for i,k in enumerate("ABC")}
    large={k:v*20 for k,v in small.items()}
    assert paired_bootstrap(small,p)==pytest.approx(paired_bootstrap(large,p))


def test_fewer_sites_than_planned_cannot_pass():
    p=small_protocol()
    data=[r for r in data_for(p) if r["site_id"]=="0"]
    result,_,_=evaluate_data(p,data)
    assert result["minimum_tested_view_count"] is None
    assert result["measurement_coverage_fraction"]==.5


def test_end_to_end_and_calibration_not_fitted_on_evaluation(protocol,synthetic,tmp_path):
    geometry=tmp_path/"geometry"
    reconstruction=reconstruct(synthetic/"capture.json",synthetic/"points.csv",synthetic/"contours.csv",protocol,geometry)
    assert len(reconstruction["variants"])==22
    assert all(v["status"]=="reconstructed" for v in reconstruction["variants"])
    light=tmp_path/"light"
    result=run(geometry/"reconstruction.json",synthetic/"scene.json",synthetic/"readings.csv",protocol,"visit_1",light)
    assert result["calibration_factor"]==pytest.approx(1.12)
    predicted=rows(light/"predictions.csv")
    assert all(float(r["calibration_factor"])==pytest.approx(1.12) for r in predicted)
    for row in predicted:
        assert float(row["predicted_ppfd_umol_m2_s"])==pytest.approx(float(row["measured_ppfd_umol_m2_s"]),abs=1e-6)
    modified=rows(synthetic/"readings.csv")
    for row in modified:
        if row["split_role"]=="evaluation":
            row["ppfd_umol_m2_s"]=float(row["ppfd_umol_m2_s"])*10
    write_rows(synthetic/"changed_readings.csv",modified,list(modified[0]))
    rerun=run(geometry/"reconstruction.json",synthetic/"scene.json",synthetic/"changed_readings.csv",protocol,"visit_1",tmp_path/"light2")
    assert rerun["calibration_factor"]==result["calibration_factor"]
    summary=evaluate(protocol,[light/"run.json"],tmp_path/"evaluation")
    assert summary["data_kind"]=="synthetic"
    assert summary["minimum_tested_view_count"] is None
    assert (tmp_path/"evaluation/report.html").exists()
    assert "SYNTHETIC SOFTWARE" in (tmp_path/"evaluation/report.html").read_text(encoding="utf-8")
    with pytest.raises(StudyError,match="Multiple runs"):
        evaluate(protocol,[light/"run.json",light/"run.json"],tmp_path/"duplicate")


def test_invalid_calibration_environment_rejected(protocol,synthetic):
    from tomato3d.light.scene import load_scene
    data=rows(synthetic/"readings.csv")
    data[0]["environment_state"]="plant_present"
    write_rows(synthetic/"bad_readings.csv",data,list(data[0]))
    with pytest.raises(StudyError,match="Calibration"):
        read_measurements(synthetic/"bad_readings.csv",load_scene(synthetic/"scene.json"))


def test_cli_does_not_create_physical_measurements(tmp_path):
    config_path = ROOT/"config/light_scene.json"
    before = config_path.read_bytes() if config_path.exists() else None
    assert main(["init","--out",str(tmp_path/"init")])==0
    assert rows(tmp_path/"init/ppfd_readings.template.csv")==[]
    assert (config_path.read_bytes() if config_path.exists() else None) == before


def test_actual_raytrace_averages_half_shadow_over_sensor(protocol, synthetic):
    from tomato3d.io.schemas import LightScene
    from tomato3d.light.scene import resolve_scenario
    from tomato3d.light.raytrace import Occluders, direct_light
    scene = read_json(synthetic/"scene.json")
    fixture = scene["fixtures"][0]
    fixture["emitting_center_grow_mm"]["value"]=[0.,0.,1000.]
    fixture["emitting_length_mm"]["value"]=0.
    fixture["emitting_width_mm"]["value"]=0.
    fixture["emitter_grid"]=[1,1]
    scene["fixtures"]=[fixture]
    model=LightScene.model_validate(scene)
    resolved=resolve_scenario(model,"as_built")
    p,_=load_protocol(protocol)
    disk,_=disk_receivers([dict(point_mm=np.zeros(3),normal=np.array([0.,0.,1.]),radius_mm=10.)],p)
    blocker=Occluders(np.array([[[0.,-100.,500.],[100.,-100.,500.],[100.,100.,500.]],
                               [[0.,-100.,500.],[100.,100.,500.],[0.,100.,500.]]]),
                      np.array([False,False]),np.array([0,0]),np.array([0,0]))
    open_light=direct_light(disk,resolved.fixtures,Occluders.none(),0.,model.simulation).ppfd_umol_m2_s.mean()
    shaded=direct_light(disk,resolved.fixtures,blocker,0.,model.simulation).ppfd_umol_m2_s.mean()
    assert shaded/open_light==pytest.approx(.5,abs=1e-8)


def test_cvat_import_preserves_visibility_and_identities(protocol,synthetic,tmp_path):
    from tools.leaf_light.annotations import import_cvat
    xml=tmp_path/"annotations.xml"
    xml.write_text('''<annotations><image name="side_000.png"><points points="20,30" occluded="0">
    <attribute name="organ_id">L1</attribute><attribute name="leaflet_id">A</attribute>
    <attribute name="point_id">tip</attribute><attribute name="boundary_index">0</attribute>
    <attribute name="boundary_count">3</attribute></points>
    <points points="30,40" occluded="1"/><polygon points="10,10;40,10;20,50">
    <attribute name="organ_id">L1</attribute><attribute name="leaflet_id">A</attribute>
    </polygon></image></annotations>''',encoding="utf-8")
    import_cvat(xml,synthetic/"capture.json",tmp_path/"converted")
    assert len(rows(tmp_path/"converted/points.csv"))==1
    assert len(rows(tmp_path/"converted/contours.csv"))==3


def test_mesh_export(protocol,synthetic,tmp_path):
    from tools.leaf_light.mesh import export
    reconstruct(synthetic/"capture.json",synthetic/"points.csv",synthetic/"contours.csv",protocol,tmp_path/"meshes")
    export(tmp_path/"meshes/v41_s00.csv","v41_s00",tmp_path/"ply")
    content=(tmp_path/"ply/leaves_mm.ply").read_text()
    assert "units millimetres" in content
    assert "element face 4" in content


def test_worklog_keeps_missing_and_real_zero_distinct(protocol,synthetic,tmp_path):
    path=tmp_path/"work.csv"
    write_rows(path,[dict(variant_id="v41_s00",capture_seconds=100,annotation_seconds=0,
                         correction_seconds=None,scope="independent_subset",operator="tester")],
               ("variant_id","capture_seconds","annotation_seconds","correction_seconds","scope","operator"))
    result=reconstruct(synthetic/"capture.json",synthetic/"points.csv",synthetic/"contours.csv",protocol,tmp_path/"work_geometry",path)
    assert result["variants"][0]["annotation_seconds"]==0
    assert result["variants"][0]["correction_seconds"] is None
    assert result["variants"][1]["capture_seconds"] is None


def test_prepare_uses_existing_board_renderer_and_checks_physical_status(protocol,synthetic,tmp_path):
    import importlib.util
    from tomato3d.io.schemas import BoardSpec, Intrinsics, load_json_model
    from tomato3d.calib.board import build_charuco_board
    from tomato3d.io.images import write_image
    from tools.leaf_light.capture import prepare
    spec=load_json_model(ROOT/"config/board_spec.json",BoardSpec)
    intr=Intrinsics.model_validate(read_json(synthetic/"capture.json")["intrinsics"])
    module_spec=importlib.util.spec_from_file_location("existing_test_renderer",ROOT/"tests/conftest.py")
    import sys
    existing=importlib.util.module_from_spec(module_spec)
    sys.modules[module_spec.name]=existing
    module_spec.loader.exec_module(existing)
    view=existing.render_charuco_view(spec,build_charuco_board(spec),intr,np.zeros(3),np.array([-95.,-95.,550.]))
    capture=read_json(synthetic/"capture.json")
    image_entries=[]
    for frame in capture["frames"]:
        write_image(tmp_path/frame["image_file"],view.image)
        image_entries.append(dict(file=frame["image_file"],view_type=frame["view_type"],top_position=frame["top_position"],
                                  nominal_angle_deg=0 if frame["view_type"]=="side" else None))
    config=read_json(ROOT/"config/capture_config.json")
    manifest=dict(schema_version="1.0",plant_id="DT-005",session_id="DT-005_20260917_1200",
        captured_at="2026-09-17T12:00:00+09:00",camera_id="synthetic",board_variant_id=spec.variant_id,
        board_spec_ref="board_spec.json",intrinsics_ref="intrinsics.json",rotation_mode="manual",
        side_view_count=36,side_view_step_deg=10.,top_view_count=5,top_view_method="jig",
        top_view_positions_mm=config["top_view_positions_mm"],operational_top_view="T0",side_camera_radius_mm=550.,
        side_camera_height_mm=300.,color_chart_in_frame=False,scale_reference_block_mm=None,
        environment_log_ref=None,images=image_entries,notes="SYNTHETIC repeated-image integrity test")
    write_json(tmp_path/"session_manifest.json",manifest)
    write_json(tmp_path/"intrinsics.json",intr.model_dump(mode="json"))
    bundle=prepare(tmp_path/"session_manifest.json",tmp_path/"intrinsics.json",protocol,tmp_path/"prepared")
    assert all(f["pose_status"]=="solved" for f in bundle["frames"])
    assert "duplicate_image_content" in bundle["physical_blockers"]
    assert "scale_reference_not_measured" in bundle["physical_blockers"]
