// Diagnostic camera evidence must survive editing without becoming accepted geometry.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const plain = value => JSON.parse(JSON.stringify(value));
function app() {
  const html = fs.readFileSync(path.join(__dirname, '../leaf_point_annotator.html'), 'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const nodes = new Map(), saved = new Map();
  const context = vm.createContext({console, setTimeout:()=>0, clearTimeout:()=>{},
    IntersectionObserver:class {disconnect(){} observe(){}},
    localStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)},
    document:{getElementById:id=>{
      if (!nodes.has(id)) nodes.set(id,{value:'2',checked:true,hidden:false,textContent:''});
      return nodes.get(id);
    }}, window:{devicePixelRatio:1}});
  vm.runInContext(script.slice(0,script.indexOf('// Wiring')) + `
    updateSide=()=>{}; refreshSelects=()=>{}; draw=()=>{};
    rebuildImageMap=async()=>{};
    ui.plant='TEST'; sessionId='TEST_session';
    this.api={Cam,store,ui,images,frames,compactCapture,applyCapture,readPoseFiles,
      buildBackup,restoreBackup,leafStatus,fitPoint,currentLeaf,buildExport,updateBadge,
      frameIsDiagnostic,captureIsDiagnostic,moveLeafView,autoContour,undo,vstate};
  })();`, context);
  return {a:context.api,nodes};
}
function capture(extra={}) {
  const intrinsics={schema_version:'1.0',camera_id:'test_camera',image_width_px:1000,image_height_px:800,
    camera_matrix:[[1000,0,500],[0,1000,400],[0,0,1]],dist_coeffs:[0,0,0,0,0],
    rms_reprojection_error_px:9.1,n_calibration_images:41,calibrated_at:'2026-09-19',distortion_model:'opencv_pinhole'};
  return {schema_version:'observed-capture-1',validated_metric:true,plant_id:'TEST',session_id:'TEST_session',
    intrinsics,intrinsics_sha256:'intrinsic-hash',intrinsics_path:'trial.json',board_variant_id:'test-board',
    quality:{max_pose_error_px:1},provenance:{producer:'test-fixture',human_review:'pending'},notice:'retain source evidence',
    frames:[-50,50].map((offset,i)=>({image_file:['one.png','two.png'][i],image_path:'local/path',sha256:'source-'+i,
      pose_status:'solved',passes_pose_gate:true,rvec_rad:[0,0,0],tvec_mm:[offset,0,500],
      reprojection_error_px:0.2,n_corners_detected:24,failure_reason:null,observed_view_group:'near_top'})),
    variants:[{variant_id:'pair',view_count:2,image_files:['one.png','two.png'],selection_provenance:'keep-me'}],...extra};
}
function loadLeaf(a,doc) {
  a.applyCapture(a.compactCapture(doc));
  for(const name of ['one.png','two.png']) a.images.set(name,{name,size:[1000,800]});
  const leaf=a.currentLeaf(true); leaf.boundary_count=3;
  for(const [i,X] of [[-10,-10,0],[10,-10,0],[0,10,0]].entries()) {
    leaf.pts['b'+i]={};
    for(const name of ['one.png','two.png']) leaf.pts['b'+i][name]=a.Cam.project(a.frames.get(name).cam,X);
  }
  return leaf;
}
test('pose file compaction, frame map and backup roundtrip retain all diagnostic source evidence',async()=>{
  const {a}=app();
  const raw=capture({schema_version:'diagnostic-preview-capture-1',validated_metric:false});
  raw.frames.forEach(f=>{f.passes_pose_gate=false;f.reprojection_error_px=8.7;f.failure_reason='pose gate exceeded';});
  const parsed=await a.readPoseFiles([{name:'capture.json',text:async()=>JSON.stringify(raw)}]);
  for(const key of ['schema_version','validated_metric','quality','board_variant_id','intrinsics_path','intrinsics_sha256','provenance','notice'])
    assert.deepEqual(plain(parsed[key]),raw[key],key);
  assert.deepEqual(plain(parsed.intrinsics),raw.intrinsics);
  assert.equal(parsed.variants[0].selection_provenance,'keep-me');
  a.applyCapture(parsed);
  assert.equal(a.frames.get('one.png').sha256,'source-0');
  assert.equal(a.frames.get('one.png').passes_pose_gate,false);
  assert.equal(a.frames.get('one.png').reprojection_error_px,8.7);
  assert.equal(a.frames.get('one.png').failure_reason,'pose gate exceeded');
  assert.ok(a.frames.get('one.png').cam,'raw camera is retained for diagnostic guides');
  const leaf=a.currentLeaf(true); Object.assign(leaf,{review_status:'candidate_unreviewed',human_review:'pending',annotation_source:'assistant visual candidates',review_notes:['ambiguous lobe']});
  const before=plain(a.buildBackup());
  a.store.variants={};
  await a.restoreBackup(before);
  const after=plain(a.buildBackup());
  assert.deepEqual(after.capture,before.capture);
  assert.deepEqual(after.variants,before.variants);
  assert.equal(a.frames.get('one.png').passes_pose_gate,false);
});
test('perfect point fits stay diagnostic when whole capture is unvalidated',()=>{
  const {a}=app(); const leaf=loadLeaf(a,capture({validated_metric:false}));
  for(let i=0;i<3;i++) {
    const fit=a.fitPoint(leaf,'b'+i);
    assert.ok(fit && fit.maxErr<1e-6 && fit.parallaxDeg>2,'synthetic fit really passes point thresholds');
  }
  const status=a.leafStatus(leaf);
  assert.equal(status.badFit,false); assert.equal(status.diagnostic,true); assert.equal(status.ready,false);
  const pane={key:'one.png',badge:{}}; a.updateBadge(pane);
  assert.equal(pane.badge.className,'badge warn'); assert.match(pane.badge.textContent,/미검증/);
  const out=a.buildExport();
  assert.ok(out.warnings.some(w=>w.includes('미검증 시험 포즈')));
  assert.equal(out.points.split('\n')[0],'image_file,organ_id,leaflet_id,point_id,x_px,y_px,boundary_index,boundary_count');
});
test('a failed source pose gate blocks readiness even when capture otherwise advertises validity',()=>{
  const {a}=app(); const raw=capture(); raw.frames[1].passes_pose_gate=false;
  const leaf=loadLeaf(a,raw);
  assert.ok(a.fitPoint(leaf,'b0').maxErr<1e-6);
  assert.equal(a.leafStatus(leaf).ready,false);
  assert.equal(a.leafStatus(leaf).diagnostic,true);
  const pane={key:'two.png',badge:{}}; a.updateBadge(pane);
  assert.equal(pane.badge.className,'badge warn');
});
test('accepted synthetic source still supports the existing geometric check and candidate review remains pending',()=>{
  const {a}=app(); const leaf=loadLeaf(a,capture());
  assert.equal(a.leafStatus(leaf).ready,true);
  Object.assign(leaf,{review_status:'candidate_unreviewed',human_review:'pending'});
  assert.ok(a.buildExport().warnings.some(w=>w.includes('검토 전')));
  assert.equal(a.buildBackup().variants.__all__.leaflets[a.ui.leafKey].human_review,'pending');
});

test('splitting an observation retains review metadata and records lineage without promoting it',()=>{
  const {a}=app(); const leaf=loadLeaf(a,capture()), sourceId=a.ui.leafKey;
  const provenance={review_status:'candidate_unreviewed',human_review:'pending',annotation_source:'assistant visual candidate',
    review_notes:['occluded lobe','needs human review'],outline_completeness:'partial_observed_patch',
    surface_interpretation:'Observed patch only',correspondence_status:'needs_revision'};
  Object.assign(leaf,provenance);
  const id=a.moveLeafView(sourceId,'one.png');
  const dest=a.vstate().leaflets[id];
  for(const [key,value] of Object.entries(provenance)) assert.deepEqual(plain(dest[key]),value,key);
  assert.ok(dest.pts.b0['one.png']); assert.equal(leaf.pts.b0['one.png'],undefined);
  assert.equal(dest.identity_history[0].source_leaf_key,sourceId);
  assert.equal(dest.identity_history[0].action,'split_observation');
  assert.equal(dest.identity_history[0].identity_review_status,'pending');
  assert.equal(leaf.identity_history[0].target_leaf_key,id);
  assert.equal(a.autoContour(dest,'one.png'),null);
  const backup=plain(a.buildBackup());
  assert.equal(backup.variants.__all__.leaflets[id].review_status,'candidate_unreviewed');
  a.undo();
  assert.ok(a.vstate().leaflets[sourceId].pts.b0['one.png']);
  assert.equal(a.vstate().leaflets[id],undefined);
});
test('relinking combines notes and source lineage, retains prior destination details and is conservative about review/partial outlines',()=>{
  const {a}=app(); const leaf=loadLeaf(a,capture()), sourceId=a.ui.leafKey;
  Object.assign(leaf,{review_status:'candidate_unreviewed',human_review:'pending',annotation_source:'assistant candidates',
    review_notes:['source caution'],outline_completeness:'partial_observed_patch',surface_interpretation:'partial fragment',correspondence_status:'needs_revision'});
  const targetId='other|tip';
  a.vstate().leaflets[targetId]={organ_id:'other',leaflet_id:'tip',boundary_count:3,pts:{b0:{'two.png':[1,2]}},contours:{},
    review_status:'reviewed',human_review:'reviewed',annotation_source:'human annotation',review_notes:['prior human note'],
    outline_completeness:'complete',surface_interpretation:'prior complete interpretation',correspondence_status:'confirmed',custom_dest_field:'keep'};
  a.moveLeafView(sourceId,'one.png',targetId);
  const dest=a.vstate().leaflets[targetId];
  assert.equal(dest.review_status,'candidate_unreviewed'); assert.equal(dest.human_review,'pending');
  assert.equal(dest.correspondence_status,'needs_revision'); assert.equal(dest.outline_completeness,'partial_observed_patch');
  assert.deepEqual(plain(dest.review_notes),['prior human note','source caution']);
  assert.equal(dest.annotation_source,'human annotation');
  assert.deepEqual(plain(dest.annotation_sources),['human annotation','assistant candidates']);
  assert.match(dest.surface_interpretation,/prior complete interpretation/); assert.match(dest.surface_interpretation,/partial fragment/);
  assert.equal(dest.custom_dest_field,'keep');
  assert.equal(dest.identity_history[0].destination_metadata_before.review_status,'reviewed');
  assert.equal(dest.identity_history[0].source_metadata.review_status,'candidate_unreviewed');
  assert.equal(dest.identity_history[0].action,'relink_observation');
  assert.equal(a.leafStatus(dest).ready,false);
});
test('partial observed patch with perfect accepted-camera fits never exports a complete contour or becomes ready',()=>{
  const {a}=app(); const leaf=loadLeaf(a,capture());
  assert.equal(a.leafStatus(leaf).ready,true);
  leaf.outline_completeness='partial_observed_patch';
  leaf.surface_interpretation='Only the visible patch is known';
  assert.ok(a.fitPoint(leaf,'b0').maxErr<1e-6);
  assert.equal(a.autoContour(leaf,'one.png'),null); assert.equal(a.autoContour(leaf,'two.png'),null);
  const status=a.leafStatus(leaf);
  assert.equal(status.partialOutline,true); assert.equal(status.ready,false); assert.equal(status.contourViews,0);
  const out=a.buildExport();
  assert.equal(out.nPoints,6); assert.equal(out.nContours,0);
  assert.ok(out.warnings.some(w=>w.includes('부분적으로 관찰된')));
  assert.equal(a.buildBackup().variants.__all__.leaflets[a.ui.leafKey].outline_completeness,'partial_observed_patch');
});
