"""Private editor bundles preserve pixel coordinates, provenance and existing work."""
from __future__ import annotations

from copy import deepcopy
from pathlib import Path
import shutil
import subprocess

from PIL import Image
import pytest

from tools import prepare_leaf_edit_session as editor
from tools.leaf_light import common


@pytest.fixture
def inputs(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> tuple[Path, Path, Path]:
    board_path = editor.get_settings().board_spec_path.resolve()
    intrinsics = dict(image_width_px=1000, image_height_px=800, camera_matrix=[[1000, 0, 500], [0, 1000, 400], [0, 0, 1]], dist_coeffs=[0] * 5)
    calibration_path = tmp_path / "intrinsics.json"
    common.write_json(calibration_path, intrinsics)
    frames = []
    for name in ("One.png", "Two.png"):
        path = tmp_path / name
        Image.new("RGB", (1000, 800), "green").save(path)
        sha256 = common.file_hash(path)
        frames.append(dict(image_file=name, image_path=str(path), sha256=sha256, pose_status="failed",
                           passes_pose_gate=False, rvec_rad=None, tvec_mm=None,
                           board_evidence=dict(source_image_sha256=sha256, detected_marker_ids=[], detected_corner_ids=[])))
    capture = dict(schema_version="diagnostic-preview-capture-1", plant_id="testplant", session_id="testsession",
                   intrinsics=intrinsics, intrinsics_path=str(calibration_path), intrinsics_sha256=common.file_hash(calibration_path),
                   board_variant_id=common.read_json(board_path)["variant_id"], board_spec_sha256=common.file_hash(board_path),
                   frames=frames, quality=dict(max_point_error_px=2.), validated_metric=False)
    observed = [dict(image_file=frame["image_file"], label_image_size_px=[500, 400], boundary_xy_px=[[10, 20], [50, 20], [30, 60]]) for frame in frames]
    coarse_leaf = dict(organ_id="O1", leaflet_id="A1", observations=observed, review_status="candidate_unreviewed",
                       review_notes=["Physical correspondence needs human review"], description="Coarse candidate")
    partial_leaf = dict(organ_id="OD", leaflet_id="D2", observations=deepcopy(observed),
                        outline_completeness="partial_observed_patch", review_status="candidate_unreviewed")
    annotation = dict(schema_version="manual-leaf-preview-1", human_review="pending", annotation_source="assistant",
                      leaflets=[coarse_leaf, partial_leaf], two_d_only_candidates=[dict(leaflet_id="F2D", surface_extent="visible_fragment_only")])
    capture_path, annotation_path = tmp_path / "capture.json", tmp_path / "annotation.json"
    common.write_json(capture_path, capture)
    common.write_json(annotation_path, annotation)
    monkeypatch.setattr(common, "BUILD", tmp_path / "build")
    return capture_path, annotation_path, tmp_path / "build" / "session"


def test_prepared_bundle_hashes_original_pixels_and_excluded_partial_labels(inputs: tuple[Path, Path, Path]) -> None:
    capture_path, annotation_path, out = inputs
    source_hashes = [common.file_hash(p) for p in (capture_path, annotation_path)]
    report = editor.prepare(capture_path, annotation_path, out)
    seed = common.read_json(out / "seed.backup.json")
    state = seed["variants"]["__all__"]
    assert set(state["leaflets"]) == {"O1|A1"}
    leaf = state["leaflets"]["O1|A1"]
    assert leaf["pts"]["b0"] == {"one.png": [20., 40.], "two.png": [20., 40.]}
    assert leaf["boundary_count"] == 3 and leaf["contours"] == {}
    assert leaf["review_status"] == "candidate_unreviewed" and leaf["review_notes"] == ["Physical correspondence needs human review"]
    assert leaf["source_annotations_sha256"] == common.file_hash(annotation_path)
    assert not leaf["validated_metric"]
    assert report["excluded_partial_candidates"][0]["leaflet_id"] == "D2"
    assert state["seed_provenance"]["two_d_only_candidates"][0]["leaflet_id"] == "F2D"
    assert not report["launched"] and not report["uploaded"] and not report["deep_learning_run"]
    copied = common.read_json(out / "capture.json")
    original = common.read_json(capture_path)
    assert copied["quality"] == original["quality"] and copied["intrinsics"] == original["intrinsics"]
    for old, new in zip(original["frames"], copied["frames"]):
        assert new["board_evidence"] == old["board_evidence"] and new["passes_pose_gate"] is False
        assert common.file_hash(out / new["image_path"]) == old["sha256"]
    assert common.file_hash(out / "intrinsics.json") == original["intrinsics_sha256"]
    assert common.file_hash(out / "annotations.source.json") == common.file_hash(annotation_path)
    assert [common.file_hash(p) for p in (capture_path, annotation_path)] == source_hashes
    html = (out / "index.html").read_text(encoding="utf-8")
    assert editor.LOCAL_GUARD in html and editor.CSP in html and "fonts.googleapis.com" not in html
    assert "bootstrap.js" in html


@pytest.mark.parametrize("changed", ["photo", "board_evidence", "calibration"])
def test_bad_sources_fail_before_copy(inputs: tuple[Path, Path, Path], changed: str) -> None:
    capture_path, annotation_path, out = inputs
    capture = common.read_json(capture_path)
    if changed == "photo":
        Path(capture["frames"][0]["image_path"]).write_bytes(b"different")
    elif changed == "board_evidence":
        capture["frames"][0]["board_evidence"]["source_image_sha256"] = "wrong"
        common.write_json(capture_path, capture)
    else:
        Path(capture["intrinsics_path"]).write_text("{}", encoding="utf-8")
    with pytest.raises(common.StudyError):
        editor.prepare(capture_path, annotation_path, out)
    assert not out.exists()


def test_source_cloud_hook_change_fails_closed() -> None:
    with pytest.raises(common.StudyError, match="guard injection"):
        editor.local_html("<header></header></html>", {}, Path("unused"))


NODE_CHECK = r"""
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const {loadEditSession} = require(process.argv[1]);
const html = fs.readFileSync(process.argv[2], 'utf8');
const guard = html.indexOf('if (true) return; // LOCAL_ONLY_PREPARED_SESSION');
assert(guard > 0);
const start = html.lastIndexOf('(async () => {', guard);
const end = html.indexOf('\n})();', guard) + '\n})();'.length;
let cloudCalls = 0;
vm.runInNewContext(html.slice(start, end), {window:{claude:{use(){cloudCalls++;throw Error('Cloud must be unreachable');}}}});
assert.equal(cloudCalls, 0);
const config = {session_id:'S', plant_id:'P', image_urls:['images/a.png'],capture_url:'capture.json',seed_url:'seed.json'};
function harness(saved=null, priorVariants=null, onFetch=null) {
  let loaded = false, restores = 0, fetched = 0;
  let state={plant_id:'P',session_id:'S',variants:priorVariants || {__all__:{leaflets:{},boxes:{}}}};
  const api={ui:{variant:'another'},async loadFromUrls(images,poses){loaded=true;assert.deepEqual(images,config.image_urls);assert.deepEqual(poses,[config.capture_url]);},
    buildBackup(){return state;},vstate(){return state.variants.__all__;},async restoreBackup(seed){assert(loaded);restores++;state=seed;}};
  const storage={getItem(){return saved;}};
  const fetchJson=async()=>{assert(loaded);fetched++;if(onFetch) onFetch(state);return {plant_id:'P',session_id:'S',variants:{__all__:{leaflets:{seed:{}},boxes:{}}}};};
  return {args:{api,config,fetchJson,storage},stats:()=>({restores,fetched,state,loaded})};
}
(async()=>{
  let h=harness(); assert.equal((await loadEditSession(h.args)).status,'seeded');assert.equal(h.stats().restores,1);
  assert.equal((await loadEditSession(h.args)).status,'preserved');assert.equal(h.stats().restores,1);
  h=harness(null,{__all__:{leaflets:{user:{pts:{b0:{a:[1,2]}}}},boxes:{}}});
  await loadEditSession(h.args);assert.equal(h.stats().restores,0);assert.equal(h.stats().fetched,0);assert(h.stats().state.variants.__all__.leaflets.user);
  h=harness('{}');await loadEditSession(h.args);assert.equal(h.stats().restores,0); // Intentionally cleared session is preserved.
  h=harness(null,{__all__:{leaflets:{},boxes:{a:[{annotation_id:'bud'}]}}});await loadEditSession(h.args);assert.equal(h.stats().restores,0);
  h=harness(null,{__all__:{leaflets:{},boxes:{}},other:{leaflets:{otherUser:{}},boxes:{}}});await loadEditSession(h.args);assert.equal(h.stats().restores,0);
  h=harness(null,null,state=>{state.variants.__all__.leaflets.editedDuringFetch={};});await loadEditSession(h.args);assert.equal(h.stats().restores,0);
  console.log('All bootstrap preservation and local-only initialization checks passed');
})().catch(error=>{console.error(error);process.exit(1);});
"""


def test_bootstrap_keeps_saved_and_live_edits_and_blocks_cloud(inputs: tuple[Path, Path, Path]) -> None:
    node = shutil.which("node")
    if node is None:
        pytest.skip("Node runtime unavailable")
    capture_path, annotation_path, out = inputs
    editor.prepare(capture_path, annotation_path, out)
    result = subprocess.run([node, "-e", NODE_CHECK, str(out / "bootstrap.js"), str(out / "index.html")],
                            text=True, capture_output=True, timeout=30, check=False)
    assert result.returncode == 0, result.stdout + result.stderr
    assert "All bootstrap preservation" in result.stdout


def test_include_partial_preserves_physical_landmarks_and_never_seeds_2d_vertices(inputs: tuple[Path, Path, Path]) -> None:
    capture_path, annotation_path, out = inputs
    annotation = common.read_json(annotation_path)
    partial = annotation["leaflets"][1]
    partial.update(human_review="pending", correspondence_status="needs_revision",
                   surface_interpretation="Observed distal patch; full leaf outline unknown",
                   boundary_landmark_names=["distal tip", "visible right lobe", "visible left lobe"],
                   review_notes=["Occluded base remains unknown"], surface_extent="visible_fragment_only")
    fragment = dict(organ_id="fragment", leaflet_id="F2D", geometry_status="2d_only",
                    correspondence_status="not_point_correspondences", surface_extent="visible_fragment_only",
                    observations=deepcopy(partial["observations"]))
    fragment["observations"][1]["boundary_xy_px"].append([35, 35])
    annotation["two_d_only_candidates"] = [deepcopy(fragment)]
    # Even a 2D polygon accidentally placed in leaflets must remain excluded.
    misplaced = deepcopy(fragment)
    misplaced["leaflet_id"] = "MISPLACED_2D"
    misplaced["outline_completeness"] = "partial_observed_patch"
    annotation["leaflets"].append(misplaced)
    common.write_json(annotation_path, annotation)
    report = editor.prepare(capture_path, annotation_path, out, include_partial=True)
    seed = common.read_json(out / "seed.backup.json")
    state = seed["variants"]["__all__"]
    assert set(state["leaflets"]) == {"O1|A1", "OD|D2"}
    saved = state["leaflets"]["OD|D2"]
    for field in ("outline_completeness", "surface_interpretation", "boundary_landmark_names",
                  "correspondence_status", "surface_extent", "review_status", "human_review", "review_notes"):
        assert saved[field] == partial[field]
    assert saved["pts"]["b0"] == {"one.png": [20., 40.], "two.png": [20., 40.]}
    assert saved["boundary_count"] == 3 and saved["contours"] == {}
    assert saved["original_candidate_observations"] == partial["observations"]
    assert saved["validated_metric"] is False
    assert report["include_partial"] is True
    assert report["included_partial_leaflet_ids"] == ["D2"]
    assert report["included_partial_count"] == 1
    assert report["excluded_partial_candidates"] == []
    assert {item["leaflet_id"] for item in report["excluded_two_d_only_candidates"]} == {"F2D", "MISPLACED_2D"}
    assert state["seed_provenance"]["included_partial_leaflet_ids"] == ["D2"]
    html = (out / "index.html").read_text(encoding="utf-8")
    assert "1개 부분 잎의 대응점도 수정" in html
    assert "부분 표면은 완전한 잎 윤곽으로 취급하지 않습니다" in html
    assert '"include_partial": true' in html


def test_explicit_sparse_physical_points_keep_ids_gaps_semantics_and_independent_regions(inputs: tuple[Path, Path, Path]) -> None:
    capture_path, annotation_path, out = inputs
    annotation = common.read_json(annotation_path)
    points = [dict(point_id=f"b{index}", xy_px=[10 + index * 10, 20 + index * 3],
                   semantic_name=f"observed_lobe_{index}") for index in (0, 1, 2, 4, 5)]
    candidate = dict(organ_id="OB", leaflet_id="B1", review_status="candidate_unreviewed",
                     geometry_status="unmeshed_physical_point_candidates", boundary_count=6,
                     excluded_original_point_ids=["b3"], annotation_source="reviewed image features; unconfirmed identity",
                     observations=[dict(image_file=name, label_image_size_px=[500, 400], points=deepcopy(points))
                                   for name in ("One.png", "Two.png")])
    annotation["physical_point_candidates"] = [candidate]
    region = dict(organ_id="OB", leaflet_id="B1", geometry_status="2d_only",
                  correspondence_status="not_point_correspondences", surface_extent="visible_fragment_only",
                  observations=[dict(image_file="One.png", label_image_size_px=[500, 400],
                                     boundary_xy_px=[[100, 100], [150, 100], [125, 150]])])
    annotation["two_d_only_candidates"].append(region)
    common.write_json(annotation_path, annotation)
    capture = common.read_json(capture_path)
    default, default_report = editor.build_seed(capture, annotation, {"annotations_sha256": common.file_hash(annotation_path)})
    assert "OB|B1" not in default["variants"]["__all__"]["leaflets"]
    assert default_report["excluded_physical_point_candidates"] == [candidate]
    report = editor.prepare(capture_path, annotation_path, out, include_partial=True)
    state = common.read_json(out / "seed.backup.json")["variants"]["__all__"]
    leaf = state["leaflets"]["OB|B1"]
    assert set(leaf["pts"]) == {"b0", "b1", "b2", "b4", "b5"}
    assert "b3" not in leaf["pts"]
    assert leaf["pts"]["b4"] == {"one.png": [100., 64.], "two.png": [100., 64.]}
    assert leaf["boundary_count"] == 6 and leaf["contours"] == {}
    assert leaf["outline_completeness"] == "partial_observed_patch"
    assert leaf["geometry_status"] == "unmeshed_physical_point_candidates"
    assert leaf["point_semantic_names"] == {point["point_id"]: point["semantic_name"] for point in points}
    assert leaf["original_physical_point_candidate"] == candidate
    assert leaf["annotation_source"] == candidate["annotation_source"]
    assert leaf["review_status"] == "candidate_unreviewed" and not leaf["validated_metric"]
    assert report["included_physical_point_leaflet_ids"] == ["B1"]
    assert report["included_partial_leaflet_ids"] == ["D2", "B1"]
    assert region in state["seed_provenance"]["two_d_only_candidates"]
    assert region in report["excluded_two_d_only_candidates"]
