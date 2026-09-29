"""Phone orientation/profile and reduced-view annotation provenance regressions."""
from __future__ import annotations

import copy

import numpy as np
import pytest
from PIL import Image

from tools.leaf_light.common import StudyError, read_json, write_json, rows, write_rows
from tools.leaf_light.phone import normalize, validate_profile
from tools.leaf_light.evaluation import evaluate_data
from tools.leaf_light.reconstruction import reconstruct
from tools.leaf_light.annotations import POINT_COLUMNS, CONTOUR_COLUMNS
from tools.tests.test_leaf_light_study import protocol, synthetic, small_protocol, data_for


def phone_picture(path, orientation=6, focal_mm=4.2):
    pixels = np.zeros((24,32,3), dtype=np.uint8)
    pixels[2:8,3:10] = [240,20,50]
    exif=Image.Exif()
    exif[274]=orientation
    exif[272]="Synthetic phone"
    exif[37386]=focal_mm
    Image.fromarray(pixels).save(path,exif=exif)
    return pixels


def test_phone_rotation_is_applied_once_and_original_unchanged(tmp_path):
    from tools.leaf_light.common import file_hash
    source=tmp_path/"originals"
    source.mkdir()
    path=source/"휴대폰.png"
    pixels=phone_picture(path)
    before=file_hash(path)
    result=normalize(source,"phone_main",tmp_path/"normalized")
    image=Image.open(tmp_path/"normalized/images/휴대폰.png")
    np.testing.assert_array_equal(np.asarray(image),np.rot90(pixels,k=3))
    assert image.getexif().get(274,1)==1
    assert file_hash(path)==before
    assert result["capture_settings"]["image_width_px"]==24


def test_phone_lens_or_orientation_changes_rejected(tmp_path):
    source=tmp_path/"source"
    source.mkdir()
    phone_picture(source/"a.png")
    phone_picture(source/"b.png",focal_mm=8.4)
    with pytest.raises(StudyError,match="focal_length"):
        normalize(source,"phone",tmp_path/"bad")
    phone_picture(source/"b.png",orientation=1)
    with pytest.raises(StudyError,match="mix"):
        normalize(source,"phone",tmp_path/"bad2")


def test_phone_reference_profile_and_pixel_binding(tmp_path):
    from types import SimpleNamespace
    source=tmp_path/"source"
    source.mkdir()
    phone_picture(source/"a.png")
    normalize(source,"phone",tmp_path/"calib")
    reference=tmp_path/"calib/phone_profile.json"
    normalize(source,"phone",tmp_path/"capture",reference)
    profile=tmp_path/"capture/phone_profile.json"
    image=tmp_path/"capture/images/a.png"
    intr=SimpleNamespace(camera_id="phone",image_shape=(32,24))
    validate_profile(profile,intr,[image])
    image.write_bytes(b"changed")
    with pytest.raises(StudyError,match="changed"):
        validate_profile(profile,intr,[image])
    phone_picture(source/"a.png",focal_mm=8.4)
    with pytest.raises(StudyError,match="differs"):
        normalize(source,"phone",tmp_path/"changed",reference)


def test_no_plants_comparison_uses_same_sites():
    p=small_protocol()
    data=data_for(p,reference=105,candidate=110)
    for row in data:
        row["no_plants_ppfd_umol_m2_s"]="130"
    summary,_,_=evaluate_data(p,data)
    assert summary["variants"][0]["rmse_improvement_over_no_plants"]==pytest.approx(25)
    data[-1]["no_plants_ppfd_umol_m2_s"]="999"
    with pytest.raises(StudyError,match="empty light"):
        evaluate_data(p,data)


def independent_packages(synthetic, target):
    capture=read_json(synthetic/"capture.json")
    points,contours=rows(synthetic/"points.csv"),rows(synthetic/"contours.csv")
    packages=[]
    for selection in capture["variants"]:
        vid=selection["variant_id"]
        point_name=f"{vid}_points.csv"
        contour_name=f"{vid}_contours.csv"
        write_rows(target/point_name,[r for r in points if r["image_file"] in selection["image_files"]],POINT_COLUMNS)
        write_rows(target/contour_name,[r for r in contours if r["image_file"] in selection["image_files"]],CONTOUR_COLUMNS)
        packages.append(dict(variant_id=vid,source="independent_selected_images",operator="synthetic test fixture",
            reviewed_image_files=selection["image_files"],points=point_name,contours=contour_name))
    write_json(target/"annotation_sets.json",dict(variants=packages))
    return packages


def test_independent_annotations_reject_excluded_images(protocol,synthetic,tmp_path):
    packages=independent_packages(synthetic,tmp_path)
    result=reconstruct(synthetic/"capture.json",None,None,protocol,tmp_path/"independent",
                       annotation_sets_path=tmp_path/"annotation_sets.json")
    assert len(result["variants"])==22
    assert all(v["status"]=="reconstructed" for v in result["variants"])
    packages[-1]["reviewed_image_files"].append("excluded.png")
    write_json(tmp_path/"annotation_sets.json",dict(variants=packages))
    with pytest.raises(StudyError,match="excluded"):
        reconstruct(synthetic/"capture.json",None,None,protocol,tmp_path/"bad_annotation",
                    annotation_sets_path=tmp_path/"annotation_sets.json")


def test_observed_shared_labels_cannot_qualify(protocol,synthetic,tmp_path):
    capture=read_json(synthetic/"capture.json")
    capture["data_kind"]="observed"
    write_json(synthetic/"capture.json",capture)
    result=reconstruct(synthetic/"capture.json",synthetic/"points.csv",synthetic/"contours.csv",protocol,tmp_path/"shared")
    assert "independent_subset_annotation_provenance_missing" in result["physical_blockers"]


def test_six_week_defaults(protocol):
    from tools.leaf_light.common import load_protocol
    p,_=load_protocol(protocol)
    assert p["planned_duration_weeks"]==6
    assert p["evaluation_week_by_slot"]==dict(visit_1=3,visit_2=4,visit_3=5)
    assert p["capture_device"]=="ordinary_smartphone_rgb"


def test_partial_auto_contour_reports_conflict_instead_of_truncated_leaf(protocol,synthetic):
    from tools.leaf_light.common import load_protocol
    from tools.leaf_light.reconstruction import reconstruct_variant
    p,_=load_protocol(protocol)
    capture=read_json(synthetic/"capture.json")
    points,contours=rows(synthetic/"points.csv"),rows(synthetic/"contours.csv")
    # Simulate an annotator skip in the T0 photo: a missing corner is joined across.
    partial=[r for r in contours if not (r["image_file"]=="top_T0.png" and r["vertex_index"]=="3")]
    surfaces,diagnostics=reconstruct_variant(capture,capture["variants"][0],points,partial,p)
    assert not surfaces
    assert diagnostics["leaves"][0]["reason"].startswith("contour_conflicts_with_boundary:top_T0.png")


def test_cvat_variant_import_refuses_foreign_photo(protocol,synthetic,tmp_path):
    from tools.leaf_light.annotations import import_cvat
    xml=tmp_path/"wrong_subset.xml"
    xml.write_text('<annotations><image name="side_001.png"/></annotations>',encoding="utf-8")
    with pytest.raises(StudyError,match="mapped"):
        import_cvat(xml,synthetic/"capture.json",tmp_path/"wrong_import",variant_id="v02_s00")


def test_failed_pose_run_still_generates_inspector(protocol,synthetic,tmp_path):
    from tools.leaf_light.optics import run
    from tools.leaf_light.evaluation import evaluate
    capture=read_json(synthetic/"capture.json")
    capture["frames"][0]["pose_status"]="failed"
    write_json(synthetic/"capture.json",capture)
    reconstruct(synthetic/"capture.json",synthetic/"points.csv",synthetic/"contours.csv",protocol,tmp_path/"failed_geometry")
    run(tmp_path/"failed_geometry/reconstruction.json",synthetic/"scene.json",synthetic/"readings.csv",protocol,"visit_1",tmp_path/"failed_light")
    evaluate(protocol,[tmp_path/"failed_light/run.json"],tmp_path/"failed_evaluation")
    assert (tmp_path/"failed_evaluation/inspector.html").is_file()
