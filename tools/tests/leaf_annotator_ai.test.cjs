// AI proposal -> correction -> acceptance workflow with MOCKED model responses (no model runs).
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function app() {
  const html = fs.readFileSync(path.join(__dirname,'../leaf_point_annotator.html'),'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const nodes = new Map(), saved = new Map(), fetched = [];
  const context = vm.createContext({crypto,console,setTimeout:()=>0,clearTimeout:()=>{},
    fetch:async (...args)=>{ fetched.push(args); throw Error('network must not be used in this test'); },
    IntersectionObserver:class {disconnect(){} observe(){}},
    localStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)},
    document:{getElementById:id=>{
      if(!nodes.has(id)) nodes.set(id,{value:'2',checked:true,hidden:false,textContent:''});
      return nodes.get(id);
    }},
    window:{devicePixelRatio:1}
  });
  vm.runInContext(script.slice(0,script.indexOf('// Wiring')) + `
    updateSide = () => {}; refreshSelects = () => {}; draw = () => {};
    getBitmap = async key => ({width:images.get(key).size[0],height:images.get(key).size[1]});
    ui.plant = 'TEST'; sessionId = 'TEST_session';
    this.api = {ui,store,images,frames,panes,vstate,Cam,applyCapture,compactCapture,setLeafBox,removeLeafBox,leafViewStatus,
      addProposal,selectProposalCandidate,editProposalVertex,acceptProposal,rejectProposal,proposalsState,moveLeafView,
      suggestIdentityCandidates,recordIdentityDecision,refreshAiStatus,requestProposal:()=>requestProposal(),aiPromptsFor,
      leafBoxPointerDown,leafBoxPointerMove,leafBoxPointerUp,buildExport,buildBackup,restoreBackup,undo,autoContour,
      identityEntries,selectLeaf,setTool,deleteAnnotationAt,toScreen,getAiInfo:()=>aiInfo,setSession:v=>{sessionId=v;}};
  })();`,context);
  const a = context.api;
  for (const name of ['one.jpg','two.jpg']) a.images.set(name,{name,size:[1000,800]});
  const pane = {key:'one.jpg',index:0,bitmap:{width:1000,height:800},view:{scale:1,ox:0,oy:0},gesture:null,hover:null,
    canvas:{getBoundingClientRect:()=>({width:800,height:600})}};
  a.panes.push(pane);
  return {a,pane,fetched};
}
const plain = value => JSON.parse(JSON.stringify(value));
const A = 'leaf_001|A1';
test('delete button edits only a draft vertex, preserves accepted boxes, and supports undo',()=>{
  const {a,pane}=app();
  const id=a.addProposal(mockResponse(),request());
  a.setLeafBox(A,'one.jpg',{x_min_px:90,y_min_px:90,x_max_px:210,y_max_px:190},{width:1000,height:800});
  a.ui.tool='leafbox'; a.ui.aiMode='edit'; a.ui.aiSelected=id;
  const before=plain(a.vstate().leaflets[A].bboxes);
  assert.equal(a.deleteAnnotationAt(pane,...a.toScreen(pane,100,100)),true);
  assert.equal(a.proposalsState()[id].rings[0].points_px.length,3);
  assert.deepEqual(plain(a.vstate().leaflets[A].bboxes),before);
  assert.throws(()=>a.deleteAnnotationAt(pane,...a.toScreen(pane,199,100)),/3개/);
  assert.equal(a.deleteAnnotationAt(pane,...a.toScreen(pane,150,110)),false);
  a.undo();
  assert.equal(a.proposalsState()[id].rings[0].points_px.length,4);
  assert.deepEqual(plain(a.vstate().leaflets[A].bboxes),before);
});
// Shape of tools.leaflet_segmenter.propose() output, written by hand: a mocked model response.
function mockResponse(extra = {}) {
  return {image_file:'one.jpg',image_sha256:'abc',image_size_px:[1000,800],crop_px:[0,0,400,400],
    model:{available:true,backend:'mock',model_name:'mock-ellipse-not-a-model',is_mock:true},
    prompts:{box_px:[100,100,200,180],positive_px:[[150,140]],negative_px:[]},
    candidates:[{candidate_index:0,score:0.9,mask_area_px:5000,discarded_components:0,
                 rings:[{is_hole:false,points_px:[[100,100],[199,100],[199,179],[100,179]]},{is_hole:true,points_px:[[140,130],[160,130],[160,150]]}]},
                {candidate_index:1,score:0.6,mask_area_px:3000,discarded_components:1,
                 rings:[{is_hole:false,points_px:[[120,110],[180,110],[180,170]]}]}],...extra};
}
const request = (extra = {}) => ({image_key:'one.jpg',session_id:'TEST_session',target_leaf_key:A,...extra});

test('a proposal is stored apart from labels and exports; flowers and legacy leaves stay intact',()=>{
  const {a}=app();
  a.vstate().leaflets['leaf_009|unavailable']={organ_id:'leaf_009',leaflet_id:'unavailable',boundary_count:3,contours:{},pts:{b0:{'one.jpg':[5,6]}}};
  a.vstate().boxes['one.jpg']=[{annotation_id:'bbox_f',organ_id:'flower_001',class_name:'flower',x_min_px:1,y_min_px:1,x_max_px:20,y_max_px:20,image_width_px:1000,image_height_px:800}];
  const leavesBefore=JSON.stringify(a.vstate().leaflets), exportBefore=a.buildExport();
  const id=a.addProposal(mockResponse(),request());
  const p=a.proposalsState()[id];
  assert.equal(p.state,'proposed'); assert.equal(p.model.is_mock,true); assert.equal(p.human_review,'pending');
  assert.deepEqual(plain(p.prompts.positive_px),[[150,140]]);
  assert.equal(JSON.stringify(a.vstate().leaflets),leavesBefore, 'a draft never touches saved leaflets');
  const exportAfter=a.buildExport();
  for (const k of ['points','contours','bboxes','leafletBboxes']) assert.equal(exportAfter[k],exportBefore[k],k);
  assert.equal(a.vstate().boxes['one.jpg'].length,1);
});

test('stale or mismatched responses are discarded without storing anything',()=>{
  const {a}=app();
  assert.throws(()=>a.addProposal(mockResponse(),request({session_id:'other'})),/세션/);
  assert.throws(()=>a.addProposal(mockResponse({image_file:'two.jpg'}),request()),/다른 사진/);
  assert.throws(()=>a.addProposal(mockResponse({image_size_px:[1500,1200]}),request()),/해상도/);
  const outside=mockResponse(); outside.candidates[0].rings[0].points_px[0]=[1200,5];
  assert.throws(()=>a.addProposal(outside,request()),/사진 밖/);
  assert.throws(()=>a.addProposal(mockResponse({candidates:[]}),request()));
  assert.deepEqual(plain(a.proposalsState()),{});
});

test('candidate choice, vertex edits and undo move between proposed and edited states',()=>{
  const {a}=app();
  const id=a.addProposal(mockResponse(),request()), p=()=>a.proposalsState()[id];
  a.selectProposalCandidate(id,1);
  assert.equal(p().selected_candidate,1); assert.equal(p().rings.length,1);
  a.selectProposalCandidate(id,0);
  a.editProposalVertex(id,0,1,'move',[210.5,98.25]);
  assert.equal(p().state,'edited'); assert.deepEqual(plain(p().rings[0].points_px[1]),[210.5,98.25]);
  assert.throws(()=>a.selectProposalCandidate(id,1),/바꿀 수 없습니다/, 'switching candidates would discard edits');
  a.editProposalVertex(id,0,0,'insert',[150,95]);
  assert.equal(p().rings[0].points_px.length,5);
  assert.throws(()=>a.editProposalVertex(id,1,0,'delete'),/3개 이상/, 'a 3-vertex hole cannot lose a vertex');
  a.editProposalVertex(id,0,4,'delete');
  assert.equal(p().rings[0].points_px.length,4);
  assert.deepEqual(plain(p().candidates[0].rings[0].points_px[1]),[199,100], 'model output is kept unchanged for provenance');
  a.undo(); a.undo(); a.undo();
  assert.equal(p().state,'proposed'); assert.deepEqual(plain(p().rings[0].points_px[1]),[199,100]);
  assert.ok(p().history.some(h=>h.action==='candidate_selected'));
});

test('accepting writes a leaflet box and region with provenance but confirms nothing',()=>{
  const {a}=app();
  const id=a.addProposal(mockResponse(),request());
  a.editProposalVertex(id,0,2,'move',[249,179]);
  const box=a.acceptProposal(id);
  const leaf=a.vstate().leaflets[A];
  assert.deepEqual(plain([box.x_min_px,box.y_min_px,box.x_max_px,box.y_max_px]),[100,100,250,180]);
  assert.equal(leaf.regions['one.jpg'].region_source,'ai_proposal_edited_accepted');
  assert.equal(leaf.regions['one.jpg'].rings.length,2); assert.equal(leaf.regions['one.jpg'].rings[1].is_hole,true);
  assert.equal(leaf.regions['one.jpg'].model.model_name,'mock-ellipse-not-a-model');
  assert.deepEqual(plain(a.leafViewStatus(leaf,'one.jpg')),{visibility:'unknown',identity_review:'unconfirmed'});
  assert.deepEqual(plain(leaf.pts),{}, 'region vertices are not physical points');
  assert.equal(a.autoContour(leaf,'one.jpg'),null);
  assert.equal(a.buildExport().nPoints,0);
  const p=a.proposalsState()[id];
  assert.equal(p.state,'accepted'); assert.equal(p.accepted_into.annotation_id,box.annotation_id);
  assert.throws(()=>a.acceptProposal(id)); assert.throws(()=>a.rejectProposal(id));
  assert.ok(a.identityEntries('leaf').some(e=>e.id===A));
});

test('a proposal can never overwrite a saved box or region',()=>{
  const {a}=app();
  a.setLeafBox(A,'one.jpg',{x_min_px:10,y_min_px:10,x_max_px:60,y_max_px:60},{width:1000,height:800});
  const id=a.addProposal(mockResponse(),request());
  const before=JSON.stringify(a.vstate().leaflets);
  assert.throws(()=>a.acceptProposal(id),/덮어쓰지 않습니다/);
  assert.equal(JSON.stringify(a.vstate().leaflets),before);
  assert.equal(a.proposalsState()[id].state,'proposed');
  a.removeLeafBox(A,'one.jpg');
  a.acceptProposal(id);
  const second=a.addProposal(mockResponse(),request());
  assert.throws(()=>a.acceptProposal(second),/덮어쓰지 않습니다/);
  a.rejectProposal(second);
  assert.equal(a.proposalsState()[second].state,'rejected');
  a.removeLeafBox(A,'one.jpg');
  assert.equal(a.vstate().leaflets[A].regions['one.jpg'],undefined, 'deleting the box removes its accepted region');
});

test('a new request supersedes the open draft for the same leaflet and photo',()=>{
  const {a}=app();
  const first=a.addProposal(mockResponse(),request());
  const second=a.addProposal(mockResponse(),request({previous_proposal_id:first}));
  assert.equal(a.proposalsState()[first].state,'rejected');
  assert.equal(a.proposalsState()[first].history.at(-1).action,'superseded');
  assert.equal(a.proposalsState()[second].previous_proposal_id,first);
});

test('prompt clicks and edited vertices keep original pixel coordinates under zoom',()=>{
  const {a,pane}=app(); a.setTool('leafbox'); a.selectLeaf('leaf_001','A1');
  pane.view={scale:2.5,ox:-100,oy:-40};
  a.ui.aiMode='pos'; a.leafBoxPointerDown(pane,{altKey:false},400,300);
  assert.deepEqual(plain(a.aiPromptsFor('one.jpg').positive[0]),[(400+100)/2.5-0.5,(300+40)/2.5-0.5]);
  a.ui.aiMode='box'; a.leafBoxPointerDown(pane,{altKey:false},250,200); a.leafBoxPointerMove(pane,500,450);
  let g=pane.gesture; pane.gesture=null; a.leafBoxPointerUp(pane,g,false);
  assert.deepEqual(plain(a.aiPromptsFor('one.jpg').box),[(250+100)/2.5,(200+40)/2.5,(500+100)/2.5,(450+40)/2.5]);
  assert.equal(a.vstate().leaflets[A],undefined, 'a prompt box is not a label');
  const id=a.addProposal(mockResponse(),request()); a.ui.aiSelected=id; a.ui.aiMode='edit';
  const [sx,sy]=[(199+0.5)*2.5-100,(100+0.5)*2.5-40];
  a.leafBoxPointerDown(pane,{altKey:false,shiftKey:false},sx,sy); a.leafBoxPointerMove(pane,sx+25,sy+10);
  g=pane.gesture; pane.gesture=null; a.leafBoxPointerUp(pane,g,false);
  assert.deepEqual(plain(a.proposalsState()[id].rings[0].points_px[1]),[209,104]);
  const backup=JSON.parse(JSON.stringify(a.buildBackup()));
  a.store.variants={};
  return a.restoreBackup(backup).then(()=>{
    assert.deepEqual(plain(a.proposalsState()[id].rings[0].points_px[1]),[209,104]);
    assert.equal(a.proposalsState()[id].state,'edited');
  });
});

test('without a local server the AI stays unavailable and no request is sent',async()=>{
  const {a,fetched}=app();
  await a.refreshAiStatus();
  assert.equal(a.getAiInfo().available,false);
  await a.requestProposal();
  assert.equal(fetched.length,0);
});

function geometryFixture(a) {
  const intrinsics={image_width_px:1000,image_height_px:800,camera_matrix:[[1000,0,500],[0,1000,400],[0,0,1]],dist_coeffs:[0,0,0,0,0]};
  const frame=(name,tx)=>({image_file:name,pose_status:'solved',passes_pose_gate:false,rvec_rad:[0,0,0],tvec_mm:[tx,0,500]});
  a.images.set('three.jpg',{name:'three.jpg',size:[1000,800]});
  a.applyCapture(a.compactCapture({schema_version:'diagnostic-preview-capture-1',validated_metric:false,plant_id:'TEST',session_id:'TEST_session',
    intrinsics,variants:[],frames:[frame('one.jpg',-60),frame('two.jpg',60),frame('three.jpg',0)]}));
  const cam=k=>a.frames.get(k).cam, X=[0,0,0];
  a.vstate().leaflets[A]={organ_id:'leaf_001',leaflet_id:'A1',boundary_count:3,contours:{},
    pts:{b0:{'one.jpg':a.Cam.project(cam('one.jpg'),X),'two.jpg':a.Cam.project(cam('two.jpg'),X)}}};
  const at=a.Cam.project(cam('three.jpg'),X);
  a.setLeafBox('leaf_002|B1','three.jpg',{x_min_px:at[0]-20,y_min_px:at[1]-20,x_max_px:at[0]+20,y_max_px:at[1]+20},{width:1000,height:800});
  a.setLeafBox('leaf_003|C1','three.jpg',{x_min_px:800,y_min_px:600,x_max_px:900,y_max_px:700},{width:1000,height:800});
}

test('cross-view candidates are ranked by measured-pose projection and need separate confirmation',()=>{
  const {a}=app(); geometryFixture(a);
  let s=a.suggestIdentityCandidates(A,'three.jpg');
  assert.equal(s.status,'candidates'); assert.equal(s.appearance_used,false); assert.equal(s.diagnostic_geometry,true);
  assert.deepEqual(plain(s.candidates.map(c=>c.leaf_key)),['leaf_002|B1','leaf_003|C1']);
  assert.equal(s.candidates[0].mean_distance_px,0); assert.equal(s.candidates[0].evidence,'triangulated_points');
  assert.equal(a.vstate().leaflets[A].bboxes,undefined, 'suggesting links nothing');
  a.recordIdentityDecision(A,'three.jpg','leaf_002|B1','different',s.candidates[0]);
  s=a.suggestIdentityCandidates(A,'three.jpg');
  assert.deepEqual(plain(s.candidates.map(c=>c.leaf_key)),['leaf_003|C1']);
  a.recordIdentityDecision(A,'three.jpg','leaf_003|C1','uncertain',s.candidates[0]);
  assert.equal(a.vstate().leaflets['leaf_003|C1'].bboxes['three.jpg'].x_min_px,800);
  a.recordIdentityDecision(A,'three.jpg','leaf_003|C1','same',s.candidates[0]);
  const leaf=a.vstate().leaflets[A];
  assert.ok(leaf.bboxes['three.jpg']); assert.equal(leaf.pts.b0['three.jpg'],undefined, 'no point is invented in the linked view');
  assert.equal(a.leafViewStatus(leaf,'three.jpg').identity_review,'unconfirmed');
  assert.deepEqual(plain(a.vstate().identity_decisions.map(d=>d.decision)),['different','uncertain','same']);
  assert.equal(a.suggestIdentityCandidates(A,'three.jpg').status,'already_linked');
  a.undo();
  assert.equal(a.vstate().leaflets[A].bboxes?.['three.jpg'],undefined);
  assert.equal(a.vstate().identity_decisions.length,2);
});

test('without usable geometry the suggestion reports unavailable and manual linking remains',()=>{
  const {a}=app();
  a.setLeafBox(A,'one.jpg',{x_min_px:10,y_min_px:10,x_max_px:60,y_max_px:60},{width:1000,height:800});
  const s=a.suggestIdentityCandidates(A,'two.jpg');
  assert.equal(s.status,'unavailable'); assert.deepEqual(plain(s.candidates),[]);
});

test('an accepted region moves with its photo observation on split',()=>{
  const {a}=app();
  const id=a.addProposal(mockResponse(),request()); a.acceptProposal(id);
  a.setLeafBox(A,'two.jpg',{x_min_px:10,y_min_px:10,x_max_px:60,y_max_px:60},{width:1000,height:800});
  const dest=a.moveLeafView(A,'one.jpg',null);
  assert.ok(a.vstate().leaflets[dest].regions['one.jpg']);
  assert.equal(a.vstate().leaflets[A].regions['one.jpg'],undefined);
  assert.equal(a.vstate().leaflets[dest].identity_history.at(-1).moved_observation.region_proposal_id,id);
});
