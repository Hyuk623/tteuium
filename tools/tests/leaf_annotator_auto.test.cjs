// Automatic bbox drafts, landmark candidates and cross-view match proposals (MOCKED responses).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function app() {
  const html = fs.readFileSync(path.join(__dirname,'../leaf_point_annotator.html'),'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const nodes = new Map(), saved = new Map();
  const context = vm.createContext({crypto,console,setTimeout:()=>0,clearTimeout:()=>{},
    IntersectionObserver:class {disconnect(){} observe(){}},
    Option:class {constructor(text,value){this.text=text;this.value=value;}},
    localStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)},
    document:{querySelectorAll:()=>[],getElementById:id=>{
      // Guidance-box and gate settings as the editor's defaults, so epipolar sampling is real.
      const preset={maxErr:'2',minPar:'2',boxCx:'0',boxCy:'0',boxHalf:'400',boxZ0:'-100',boxZ1:'400'};
      if(!nodes.has(id)) nodes.set(id,{value:preset[id]??'2',checked:true,hidden:false,textContent:'',
        innerHTML:'',options:[],appendChild(){},replaceChildren(){},classList:{toggle(){}},setAttribute(){}});
      return nodes.get(id);
    }},
    window:{devicePixelRatio:1}
  });
  vm.runInContext(script.slice(0,script.indexOf('// Wiring')) + `
    updateSide = () => {}; refreshSelects = () => {}; draw = () => {};
    afterLoad = () => {}; rebuildImageMap = async () => {};
    getBitmap = async key => ({width:images.get(key).size[0],height:images.get(key).size[1]});
    ui.plant = 'TEST'; sessionId = 'TEST_session';
    this.api = {ui,store,images,frames,panes,vstate,Cam,applyCapture,compactCapture,currentLeaf,selectLeaf,undo,
      autoDraftsState,addAutoDrafts,assignAutoDraft,rejectAutoDraft,rejectAutoBatch,acceptProposal,addProposal,
      landmarkCandidates,deriveLandmarkCandidates,acceptLandmarkCandidate,rejectLandmarkCandidate,
      proposePointMatches,acceptPointMatch,nextFreePointId,setLeafBox,removeLeafBox,leafViewStatus,
      buildExport,buildBackup,restoreBackup,identityEntries,boundaryCount,moveLeafView};
  })();`,context);
  const a = context.api;
  for (const name of ['one.jpg','two.jpg']) a.images.set(name,{name,size:[1000,800]});
  a.panes.push({key:'one.jpg',index:0,bitmap:{width:1000,height:800},view:{scale:1,ox:0,oy:0},gesture:null,hover:null,
    canvas:{getBoundingClientRect:()=>({width:800,height:600})}});
  // Two cameras 120 mm apart looking the same way: ~11 deg parallax at the leaf depth,
  // so the existing residual/parallax gates behave like they do on real captures.
  const intrinsics={image_width_px:1000,image_height_px:800,camera_matrix:[[900,0,500],[0,900,400],[0,0,1]],dist_coeffs:[0,0,0,0,0]};
  const frame=(name,tx)=>({image_file:name,pose_status:'solved',passes_pose_gate:false,rvec_rad:[0,0,0],tvec_mm:[tx,0,500]});
  a.applyCapture(a.compactCapture({schema_version:'diagnostic-preview-capture-1',validated_metric:false,plant_id:'TEST',
    session_id:'TEST_session',intrinsics,variants:[],frames:[frame('one.jpg',-60),frame('two.jpg',60)]}));
  return {a,nodes};
}
const plain = value => JSON.parse(JSON.stringify(value));
const A = 'leaf_001|A1', B = 'leaf_002|B1';
const ring = (pts,hole=false) => ({is_hole:hole,points_px:pts});
// Shape of tools.leaflet_segmenter.propose_automatic() output, written by hand.
function autoResponse(extra={}) {
  return {mode:'automatic',image_file:'one.jpg',image_sha256:'abc',image_size_px:[1000,800],
    model:{available:true,backend:'mock',model_name:'mock-ellipse-not-a-model',is_mock:true,automatic:true,class_agnostic:true},
    candidate_class:'unclassified',dropped:{too_small:2,too_large:1,truncated:0},
    candidates:[
      {candidate_index:0,score:0.8,mask_area_px:40000,rings:[ring([[100,100],[300,100],[300,300],[100,300]])]},
      {candidate_index:1,score:0.7,mask_area_px:30000,rings:[ring([[250,250],[450,250],[450,400],[250,400]])]}, // overlaps the first
      {candidate_index:2,score:0.5,mask_area_px:900,rings:[ring([[700,600],[740,600],[740,640],[700,640]])]}],  // small real leaflet
    ...extra};
}
const request = (extra={}) => ({image_key:'one.jpg',session_id:'TEST_session',...extra});

test('automatic drafts are unclassified, overlapping ones stay separate and small ones are kept',()=>{
  const {a}=app();
  const before=JSON.stringify(a.vstate().leaflets);
  const result=a.addAutoDrafts(autoResponse(),request());
  assert.equal(result.ids.length,3);
  const drafts=Object.values(a.autoDraftsState());
  assert.deepEqual(plain(drafts.map(d=>d.candidate_class)),['unclassified','unclassified','unclassified']);
  assert.deepEqual(plain(drafts.map(d=>d.state)),['draft','draft','draft']);
  assert.equal(drafts.every(d=>d.assigned_to===null),true);
  assert.equal(JSON.stringify(a.vstate().leaflets),before,'a draft is not a label');
  assert.equal(a.buildExport().nLeafletBoxes,0);
  assert.equal(drafts[2].bbox_px[2]-drafts[2].bbox_px[0],41,'small candidate survives');
  assert.equal(new Set(drafts.map(d=>d.batch_id)).size,1);
  assert.equal(result.dropped.too_small,2);
});

test('assigning a draft creates one leaflet label without confirming visibility or identity',()=>{
  const {a}=app();
  const {ids}=a.addAutoDrafts(autoResponse(),request());
  const first=a.assignAutoDraft(ids[0],A);
  const leaf=a.vstate().leaflets[A];
  assert.deepEqual(plain([leaf.bboxes['one.jpg'].x_min_px,leaf.bboxes['one.jpg'].x_max_px]),[100,301]);
  assert.equal(leaf.regions['one.jpg'].region_source,'auto_draft_assigned');
  assert.deepEqual(plain(a.leafViewStatus(leaf,'one.jpg')),{visibility:'unknown',identity_review:'unconfirmed'});
  assert.deepEqual(plain(leaf.pts||{}),{},'assignment creates no correspondence');
  assert.equal(a.autoDraftsState()[ids[0]].state,'assigned');
  // The overlapping draft becomes a DIFFERENT leaflet, never merged into the first.
  const second=a.assignAutoDraft(ids[1],null);
  assert.notEqual(second.leaf_key,first.leaf_key);
  assert.equal(Object.keys(a.vstate().leaflets).length,2);
  assert.throws(()=>a.assignAutoDraft(ids[2],A),/덮어쓰지 않습니다/);
  assert.equal(a.autoDraftsState()[ids[2]].state,'draft');
  a.undo();
  assert.equal(a.vstate().leaflets[second.leaf_key],undefined);
});

test('rejection, bulk rejection and stale responses never touch labels',()=>{
  const {a}=app();
  const {ids,batch_id}=a.addAutoDrafts(autoResponse(),request());
  a.assignAutoDraft(ids[0],A);
  const labels=JSON.stringify(a.vstate().leaflets);
  a.rejectAutoDraft(ids[1]);
  assert.equal(a.autoDraftsState()[ids[1]].state,'rejected');
  assert.equal(a.rejectAutoBatch(batch_id),1,'only the remaining open draft is rejected');
  assert.equal(JSON.stringify(a.vstate().leaflets),labels,'bulk rejection never removes assigned labels');
  assert.throws(()=>a.rejectAutoDraft(ids[0]),/이미 처리한/);
  assert.throws(()=>a.addAutoDrafts(autoResponse(),request({session_id:'other'})),/세션/);
  assert.throws(()=>a.addAutoDrafts(autoResponse({image_file:'two.jpg'}),request()),/다른 사진/);
  assert.throws(()=>a.addAutoDrafts(autoResponse({image_size_px:[1500,1200]}),request()),/해상도/);
});

function withRegion(a,key,pts) {
  const id=a.addAutoDrafts({...autoResponse(),image_file:key,candidates:[{candidate_index:0,score:0.9,mask_area_px:1,rings:[ring(pts)]}]},
    request({image_key:key})).ids[0];
  a.assignAutoDraft(id,A);
  return a.vstate().leaflets[A];
}
const LEAF_A=[[300,380],[420,340],[520,300],[600,290],[520,330],[430,370],[320,420],[260,470],[330,420]];
// The same leaflet seen by the second camera: a pure horizontal disparity of 180 px,
// which is exactly what a 120 mm baseline gives at 100 mm above the board.
const LEAF_B=LEAF_A.map(([x,y])=>[x+180,y]);

test('split and relink move view metadata and draft identity, with undo and backup preservation',async()=>{
  const {a}=app();
  withRegion(a,'one.jpg',LEAF_A); withRegion(a,'two.jpg',LEAF_B);
  for (const key of ['one.jpg','two.jpg']) {
    const made=a.deriveLandmarkCandidates(A,key);
    a.acceptLandmarkCandidate(A,key,made.find(m=>!m.inferred).candidate_id,'b0');
  }
  const before=plain(a.vstate());
  const split=a.moveLeafView(A,'one.jpg');
  let leaves=a.vstate().leaflets;
  assert.deepEqual(plain(leaves[split].landmark_candidates['one.jpg']),before.leaflets[A].landmark_candidates['one.jpg']);
  assert.deepEqual(plain(leaves[split].point_provenance.b0['one.jpg']),before.leaflets[A].point_provenance.b0['one.jpg']);
  assert.equal(leaves[A].landmark_candidates['one.jpg'],undefined);
  assert.equal(leaves[A].point_provenance.b0['one.jpg'],undefined);
  assert.deepEqual(plain(leaves[A].point_provenance.b0['two.jpg']),before.leaflets[A].point_provenance.b0['two.jpg']);
  assert.deepEqual(plain(leaves[split].pts.b0['one.jpg']),before.leaflets[A].pts.b0['one.jpg']);
  const draft=Object.values(a.autoDraftsState()).find(d=>d.image_key==='one.jpg');
  assert.equal(draft.assigned_to,split);
  assert.equal(draft.history.at(-1).source_leaf_key,A);
  assert.equal(Object.values(a.autoDraftsState()).find(d=>d.image_key==='two.jpg').assigned_to,A);
  const backup=plain(a.buildBackup());
  await a.restoreBackup(backup);
  assert.deepEqual(plain(a.vstate().leaflets[split].point_provenance),plain(leaves[split].point_provenance));
  const beforeRelink=plain(a.vstate());
  a.moveLeafView(split,'one.jpg',A);
  leaves=a.vstate().leaflets;
  assert.deepEqual(plain(leaves[A].point_provenance),before.leaflets[A].point_provenance);
  assert.equal(leaves[split].landmark_candidates['one.jpg'],undefined);
  assert.equal(Object.values(a.autoDraftsState()).find(d=>d.image_key==='one.jpg').assigned_to,A);
  a.undo();
  assert.deepEqual(plain(a.vstate()),beforeRelink);
});

test('many-to-one and many-to-many matches remain ambiguous in both directions',()=>{
  const {a}=app();
  withRegion(a,'one.jpg',LEAF_A); withRegion(a,'two.jpg',LEAF_B);
  const leaf=a.vstate().leaflets[A];
  const cand=(x,id)=>({candidate_id:id,xy_px:[x,380],semantic_proposal:'lobe_apex',inferred:false,state:'candidate'});
  leaf.landmark_candidates={'one.jpg':[cand(300,'a1'),cand(300.1,'a2')],'two.jpg':[cand(480,'b1')]};
  for (const count of [1,2]) {
    if (count===2) leaf.landmark_candidates['two.jpg'].push(cand(480.1,'b2'));
    for (const [from,to] of [['one.jpg','two.jpg'],['two.jpg','one.jpg']]) {
      const result=a.proposePointMatches(A,from,to);
      assert.equal(result.matches.length,2*count);
      assert.ok(result.matches.every(m=>m.status==='ambiguous'));
      assert.equal(result.eligible_count,0);
      assert.equal(result.ambiguous_count,2*count);
    }
  }
  assert.deepEqual(plain(leaf.pts),{});
});

test('splitting is fully undoable and relinking never overwrites stranded target metadata',()=>{
  const {a}=app();
  withRegion(a,'one.jpg',LEAF_A); withRegion(a,'two.jpg',LEAF_B);
  a.deriveLandmarkCandidates(A,'one.jpg');
  const before=plain(a.vstate());
  a.moveLeafView(A,'one.jpg'); a.undo();
  assert.deepEqual(plain(a.vstate()),before);
  const split=a.moveLeafView(A,'one.jpg');
  a.vstate().leaflets[A].landmark_candidates['one.jpg']=[{candidate_id:'legacy_pending',state:'candidate'}];
  const collision=plain(a.vstate());
  assert.throws(()=>a.moveLeafView(split,'one.jpg',A),/덮어쓰지 않습니다/);
  assert.deepEqual(plain(a.vstate()),collision);
});

test('landmark candidates are separate from points and record their method',()=>{
  const {a}=app(); a.selectLeaf('leaf_001','A1');
  const leaf=withRegion(a,'one.jpg',LEAF_A);
  const made=a.deriveLandmarkCandidates(A,'one.jpg');
  assert.ok(made.length>=3);
  assert.deepEqual(plain(leaf.pts||{}),{},'candidates are never b*/i* points');
  const methods=new Set(made.map(m=>m.method));
  assert.ok(methods.has('principal_axis_extremum')&&methods.has('inferred_centerline'));
  const axis=made.filter(m=>m.method==='principal_axis_extremum');
  assert.deepEqual(plain(axis.map(m=>m.semantic_proposal)),['tip_or_attachment_unknown','tip_or_attachment_unknown'],
    'the outline alone cannot say which end is the tip');
  const inferred=made.find(m=>m.inferred);
  assert.equal(inferred.semantic_proposal,'midrib_guess');
  assert.throws(()=>a.acceptLandmarkCandidate(A,'one.jpg',inferred.candidate_id,'b0'),/추정 주맥/);
  a.acceptLandmarkCandidate(A,'one.jpg',axis[0].candidate_id,'b0');
  assert.deepEqual(plain(a.vstate().leaflets[A].pts.b0['one.jpg']),plain(axis[0].xy_px));
  assert.equal(a.vstate().leaflets[A].point_provenance.b0['one.jpg'].source,'landmark_candidate');
  assert.throws(()=>a.acceptLandmarkCandidate(A,'one.jpg',axis[1].candidate_id,'b0'),/이미 있습니다/);
  a.rejectLandmarkCandidate(A,'one.jpg',axis[1].candidate_id);
  assert.equal(a.landmarkCandidates(a.vstate().leaflets[A],'one.jpg').find(c=>c.candidate_id===axis[1].candidate_id).state,'rejected');
  a.undo();
  assert.equal(a.landmarkCandidates(a.vstate().leaflets[A],'one.jpg').find(c=>c.candidate_id===axis[1].candidate_id).state,'candidate');
});

test('existing human points are never moved or renumbered by candidate acceptance',()=>{
  const {a}=app(); a.selectLeaf('leaf_001','A1');
  withRegion(a,'one.jpg',LEAF_A);
  const leaf=a.vstate().leaflets[A];
  leaf.pts={b0:{'one.jpg':[11,22]}}; leaf.point_semantic_names={b0:'distal_tip'};
  const made=a.deriveLandmarkCandidates(A,'one.jpg');
  const usable=made.find(m=>!m.inferred);
  assert.throws(()=>a.acceptLandmarkCandidate(A,'one.jpg',usable.candidate_id,'b0'),/이미 있습니다/);
  assert.deepEqual(plain(a.vstate().leaflets[A].pts.b0['one.jpg']),[11,22]);
  a.acceptLandmarkCandidate(A,'one.jpg',usable.candidate_id,'b3');
  assert.deepEqual(plain(a.vstate().leaflets[A].pts.b0['one.jpg']),[11,22]);
  assert.deepEqual(plain(a.vstate().leaflets[A].point_semantic_names),{b0:'distal_tip'});
});

test('cross-view matches report ambiguity, missing poses and only create a point on acceptance',()=>{
  const {a}=app(); a.selectLeaf('leaf_001','A1');
  withRegion(a,'one.jpg',LEAF_A); withRegion(a,'two.jpg',LEAF_B);
  a.deriveLandmarkCandidates(A,'one.jpg'); a.deriveLandmarkCandidates(A,'two.jpg');
  const result=a.proposePointMatches(A,'one.jpg','two.jpg');
  assert.equal(result.status,'candidates');
  assert.equal(result.appearance_used,false);
  assert.equal(result.method,'epipolar_and_triangulation_residual');
  assert.ok(result.matches.some(m=>m.status!=='rejected'),'a real geometric check produces usable pairs');
  assert.ok(result.matches.some(m=>m.status==='rejected'),'wrong pairs are rejected with reasons');
  assert.ok(result.matches.every(m=>m.status!=='rejected'||m.reasons.length));
  assert.deepEqual(plain(a.vstate().leaflets[A].pts||{}),{},'proposing creates nothing');
  const usable=result.matches.find(m=>m.status!=='rejected');
  const id=a.acceptPointMatch(A,{...usable,source_key:'one.jpg',target_key:'two.jpg'},'b2');
  const pts=a.vstate().leaflets[A].pts[id];
  assert.deepEqual(Object.keys(pts).sort(),['one.jpg','two.jpg'],'the same physical ID in both photos');
  assert.equal(a.vstate().leaflets[A].point_provenance.b2['one.jpg'].source,'cross_view_match');
  assert.ok(Number.isFinite(a.vstate().leaflets[A].point_provenance.b2['two.jpg'].epipolar_px));
  assert.equal(a.vstate().leaflets[A].point_provenance.b2['two.jpg'].match_status_when_accepted,usable.status);
  assert.throws(()=>a.acceptPointMatch(A,{...usable,source_key:'one.jpg',target_key:'two.jpg'},'b2'),/이미/);
  const rejected=result.matches.find(m=>m.status==='rejected');
  assert.throws(()=>a.acceptPointMatch(A,{...rejected,source_key:'one.jpg',target_key:'two.jpg'},'b7'),/통과하지 못한/);
  a.frames.get('two.jpg').cam=null;
  const noPose=a.proposePointMatches(A,'one.jpg','two.jpg');
  assert.equal(noPose.status,'unavailable'); assert.match(noPose.reason,/포즈/);
  assert.equal(a.proposePointMatches(A,'one.jpg','one.jpg').status,'unavailable');
  assert.equal(a.proposePointMatches(B,'one.jpg','two.jpg').status,'unavailable');
});

test('two partners on the same viewing ray are reported ambiguous, never silently matched',()=>{
  const {a}=app(); a.selectLeaf('leaf_001','A1');
  withRegion(a,'one.jpg',LEAF_A); withRegion(a,'two.jpg',LEAF_B);
  const camA=a.frames.get('one.jpg').cam, camB=a.frames.get('two.jpg').cam;
  const X=[10,-5,120];
  const inA=a.Cam.project(camA,X), inB=a.Cam.project(camB,X);
  // A second point on the SAME ray from camera one: its image in one.jpg is identical,
  // so epipolar geometry alone cannot tell the two partners in two.jpg apart.
  const ray=a.Cam.ray(camA,inA[0],inA[1]);
  const far=[0,1,2].map(i=>ray.origin[i]+ray.dir[i]*(Math.hypot(...[0,1,2].map(j=>X[j]-ray.origin[j]))+60));
  const inB2=a.Cam.project(camB,far);
  const leaf=a.vstate().leaflets[A];
  const cand=(xy,key)=>({candidate_id:'lm_'+key+'_'+xy.map(Math.round).join('_'),xy_px:xy,method:'convex_hull_extremum',
    semantic_proposal:'lobe_apex',inferred:false,state:'candidate',accepted_point_id:null,image_file:key,human_review:'pending'});
  leaf.landmark_candidates={'one.jpg':[cand(inA,'one.jpg')],'two.jpg':[cand(inB,'two.jpg'),cand(inB2,'two.jpg')]};
  const result=a.proposePointMatches(A,'one.jpg','two.jpg');
  const usable=result.matches.filter(m=>m.status!=='rejected');
  assert.equal(usable.length,2,'both partners pass the geometric checks');
  assert.deepEqual(plain(usable.map(m=>m.status)),['ambiguous','ambiguous']);
  assert.deepEqual(plain(usable[0].reasons),['multiple_eligible_partners']);
  assert.equal(result.eligible_count,0); assert.equal(result.ambiguous_count,2);
  assert.deepEqual(plain(a.vstate().leaflets[A].pts||{}),{},'ambiguity never writes a point by itself');
  const id=a.acceptPointMatch(A,{...usable[0],source_key:'one.jpg',target_key:'two.jpg'},'b4');
  assert.equal(a.vstate().leaflets[A].point_provenance[id]['one.jpg'].match_status_when_accepted,'ambiguous');
});

test('each geometric gate is applied and reported independently',()=>{
  const {a,nodes}=app(); a.selectLeaf('leaf_001','A1');
  withRegion(a,'one.jpg',LEAF_A); withRegion(a,'two.jpg',LEAF_B);
  const leaf=a.vstate().leaflets[A];
  const cand=(xy,key,id)=>({candidate_id:id,xy_px:xy,method:'convex_hull_extremum',semantic_proposal:'lobe_apex',
    inferred:false,state:'candidate',accepted_point_id:null,image_file:key,human_review:'pending'});
  // Off the epipolar line (40 px of vertical disagreement): both epipolar and residual fail.
  leaf.landmark_candidates={'one.jpg':[cand([300,380],'one.jpg','a1')],'two.jpg':[cand([480,420],'two.jpg','b1')]};
  let match=a.proposePointMatches(A,'one.jpg','two.jpg').matches[0];
  assert.equal(match.status,'rejected');
  assert.deepEqual(plain(match.reasons),['epipolar_distance','reprojection_residual']);
  assert.ok(match.epipolar_px>10 && match.residual_px>2);
  // On the line but nearly 3 m away: only the parallax gate may reject it.
  nodes.get('boxZ1').value='5000'; nodes.get('boxHalf').value='5000';  // guidance box must contain the far ray
  leaf.landmark_candidates={'one.jpg':[cand([300,380],'one.jpg','a2')],'two.jpg':[cand([320,380],'two.jpg','b2')]};
  match=a.proposePointMatches(A,'one.jpg','two.jpg').matches[0];
  assert.deepEqual(plain(match.reasons),['insufficient_parallax']);
  assert.ok(match.parallax_deg<2 && match.residual_px<2);
  assert.equal(match.status,'rejected');
  assert.throws(()=>a.acceptPointMatch(A,{...match,source_key:'one.jpg',target_key:'two.jpg'},'b0'),/통과하지 못한/);
});

test('drafts, candidates and provenance survive a backup round trip',async()=>{
  const {a}=app(); a.selectLeaf('leaf_001','A1');
  const {ids}=a.addAutoDrafts(autoResponse(),request());
  a.rejectAutoDraft(ids[2]);
  withRegion(a,'one.jpg',LEAF_A);
  const made=a.deriveLandmarkCandidates(A,'one.jpg');
  a.acceptLandmarkCandidate(A,'one.jpg',made.find(m=>!m.inferred).candidate_id,'b1');
  const backup=JSON.parse(JSON.stringify(a.buildBackup()));
  a.store.variants={};
  await a.restoreBackup(backup);
  assert.equal(Object.keys(a.autoDraftsState()).length,4);
  assert.equal(a.autoDraftsState()[ids[2]].state,'rejected');
  assert.equal(a.landmarkCandidates(a.vstate().leaflets[A],'one.jpg').length,made.length);
  assert.equal(a.vstate().leaflets[A].point_provenance.b1['one.jpg'].method,'principal_axis_extremum');
});
