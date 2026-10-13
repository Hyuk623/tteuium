// Compound-leaf membership: detector import, parent anchors, evidence proposals and reviewed decisions.
// Deterministic mocked detections only; no model is run.
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
    localStorage:{getItem:key=>saved.get(key),setItem:(key,value)=>saved.set(key,value)},
    document:{getElementById:id=>{
      if(!nodes.has(id)) nodes.set(id,{value:'2',checked:true,hidden:false,textContent:''});
      return nodes.get(id);
    }},
    window:{devicePixelRatio:1}
  });
  vm.runInContext(script.slice(0,script.indexOf('// Wiring')) + `
    updateSide = () => {}; refreshSelects = () => {}; draw = () => {};
    ui.plant = 'dwt_01'; sessionId = 'dwt_01_20260920';
    this.api = {ui,store,images,vstate,leafKey,setLeafBox,setLeafViewStatus,setPointMeaning,moveLeafView,undo,
      buildExport,buildBackup,restoreBackup,nextOrganId,membershipState,parseCocoDetections,importDetections,
      linkDetectionObjects,unlinkDetectionObject,detectionObjects,addParent,linkCompoundAnchor,linkSubstem,unlinkAnchor,
      proposeMembership,keepCandidateUnresolved,rejectCandidate,confirmMembership,unassignMembership,reparentMembership,
      adoptLeafletDetection,loadGrowthReference,membershipCounts,detectionsFor,distanceToRings};
  })();`,context);
  const a = context.api;
  for (const name of ['one.jpg','two.jpg']) a.images.set(name,{name,size:[1000,800]});
  return a;
}
const plain = value => JSON.parse(JSON.stringify(value));
const SIZE = {width:1000,height:800};
const geom = (x0,y0,x1,y1) => ({x_min_px:x0,y_min_px:y0,x_max_px:x1,y_max_px:y1});
const rect = (x0,y0,x1,y1) => [x0,y0, x1,y0, x1,y1, x0,y1];
const resolver = name => ['one.jpg','two.jpg'].includes(name) ? {key:name,width:1000,height:800} : name === 'small.jpg' ? {key:'one.jpg',width:1000,height:800} : null;

// Compound boxes overlap; sub-stem S1 (L01) is a horizontal strip, S2 (L02) and S3 (L03) vertical strips crossing it.
function coco() {
  const cats = ['compoundleaves','leaflet','sub-stem','main-stem','growth-shoot','flower'].map((name,i) => ({id:i+1,name}));
  const cat = name => cats.find(c => c.name === name).id;
  const ann = (id,image_id,name,bbox,segmentation = []) => ({id,image_id,category_id:cat(name),bbox,segmentation});
  return {images:[{id:1,file_name:'one_jpg.rf.abc.jpg',extra:{name:'one.jpg'},width:1000,height:800},
                  {id:2,file_name:'two.jpg',width:1000,height:800},
                  {id:3,file_name:'small.jpg',width:500,height:400}],
    categories:cats,
    annotations:[
      ann(11,1,'compoundleaves',[100,100,300,300]),            // C1
      ann(12,1,'compoundleaves',[250,150,300,300]),            // C2 overlaps C1
      ann(13,1,'sub-stem',[150,380,250,10],[rect(150,380,400,390)]),   // S1 horizontal
      ann(14,1,'sub-stem',[300,150,10,300],[rect(300,150,310,450)]),   // S2 vertical, crosses S1
      ann(15,1,'sub-stem',[500,150,10,300],[rect(500,150,510,450)]),   // S3
      ann(16,1,'growth-shoot',[600,600,50,50]),                        // bbox-only annotation
      ann(17,1,'growth-shoot',[],[rect(605,605,640,640)]),             // mask-only annotation of the same shoot
      ann(18,1,'leaflet',[700.25,100.5,80,60]),
      ann(19,1,'main-stem',[480,0,20,800],[rect(480,0,500,800)]),
      ann(20,1,'flower',[10,10,5,5]),
      ann(21,1,'sub-stem',[1,1,2,2],{counts:[1,2],size:[800,1000]}),  // RLE
      ann(22,3,'leaflet',[10,10,20,20]),                               // photo of a different size
      ann(31,2,'sub-stem',[150,380,250,10],[rect(150,380,400,390)]),
    ]};
}
function fixture() {
  const a = app();
  const result = a.importDetections(coco(),'export.json',resolver);
  const det = (key,source) => a.detectionsFor(key).find(d => d.source.source_annotation_id === source).annotation_id;
  const ids = {C1:det('one.jpg',11), C2:det('one.jpg',12), S1:det('one.jpg',13), S2:det('one.jpg',14), S3:det('one.jpg',15),
               G1:det('one.jpg',16), G2:det('one.jpg',17), F:det('one.jpg',18), S1b:det('two.jpg',31)};
  a.linkCompoundAnchor('L01','one.jpg',ids.C1); a.linkCompoundAnchor('L02','one.jpg',ids.C2);
  a.linkSubstem('L01','one.jpg',ids.S1); a.linkSubstem('L02','one.jpg',ids.S2); a.linkSubstem('L03','one.jpg',ids.S3);
  a.linkSubstem('L01','two.jpg',ids.S1b);
  return {a,ids,result};
}
// A leaflet with a bbox and, optionally, a manually marked visible base (pixel centre convention).
function leaflet(a,id,key,box,base = null) {
  a.setLeafBox(id,key,box,SIZE);
  if (base) {
    const leaf = a.vstate().leaflets[id];
    (leaf.pts.b3 ||= {})[key] = base;
    (leaf.point_semantic_names ||= {}).b3 = 'visible_attachment';
  }
  return a.vstate().leaflets[id];
}
const A = 'leaf_001|unavailable', B = 'leaf_002|unavailable', C = 'leaf_003|unavailable';

test('detector import keeps the five exact classes in original pixels and never rescales or overwrites', () => {
  const {a,result} = fixture();
  const reasons = plain(result.skipped).map(s => s.reason).sort();
  assert.deepEqual(reasons, ['class_not_one_of_five','image_not_matched','image_size_differs','rle_mask_not_supported']);
  const all = a.detectionsFor('one.jpg');
  assert.equal(all.length, 9);
  assert.ok(all.every(d => ['compoundleaves','leaflet','sub-stem','main-stem','growth-shoot'].includes(d.class_name)));
  const leafDet = all.find(d => d.class_name === 'leaflet');
  assert.deepEqual(plain(leafDet.bbox), geom(700.25,100.5,780.25,160.5));
  assert.equal(leafDet.coordinate_convention,'original_pixel_edges');
  assert.equal(leafDet.source.matched_by,'one.jpg', 'Roboflow extra.name matched the original photo');
  assert.deepEqual(plain(all.find(d => d.source.source_annotation_id === 13).rings[0][2]), [400,390]);
  const again = a.importDetections(coco(),'export_copy.json',resolver);
  assert.equal(again.imported, 0); assert.equal(again.duplicates, 10);
  assert.equal(a.detectionsFor('one.jpg').length, 9);
});

test('the real Roboflow spellings map through the fixed table, keep their original name, and nothing else maps', () => {
  const a = app();
  const names = ['compound_leaves','compond_leaf','sub_stem','main_stem','growth_shoot','shoot','leaflet','tom-seg-bbox-side','Compound_Leaves'];
  const doc = {images:[{id:1,file_name:'one.jpg',width:1000,height:800}], categories:names.map((name,i) => ({id:i+1,name})),
    annotations:names.map((name,i) => ({id:i+1,image_id:1,category_id:i+1,bbox:[10+i*20,10,10,10],segmentation:[]}))};
  const result = a.importDetections(doc,'roboflow.json',resolver);
  const got = Object.fromEntries(a.detectionsFor('one.jpg').map(d => [d.source.source_class_name,d.class_name]));
  assert.deepEqual(plain(got),{compound_leaves:'compoundleaves',compond_leaf:'compoundleaves',sub_stem:'sub-stem',main_stem:'main-stem',
    growth_shoot:'growth-shoot',shoot:'growth-shoot',leaflet:'leaflet'});
  assert.deepEqual(plain(result.skipped.map(s => s.class_name)).sort(),['Compound_Leaves','tom-seg-bbox-side']);
});

test('scenario 1: overlapping compound boxes alone never confirm; a visible base on a linked sub-stem does', () => {
  const {a} = fixture();
  leaflet(a,A,'one.jpg',geom(260,200,340,280));
  const overlapOnly = a.proposeMembership(A,'one.jpg');
  assert.equal(overlapOnly.state,'ambiguous'); assert.equal(overlapOnly.state_reason,'supporting_overlap_only');
  assert.equal(overlapOnly.suggested_parent,null);
  assert.deepEqual(plain(overlapOnly.candidate_parents.map(p => p.parent_id)).sort(),['L01','L02']);
  assert.ok(overlapOnly.candidate_parents.every(p => p.evidence.every(e => e.kind === 'compound_bbox_overlap_supporting_only')));
  assert.equal(a.vstate().leaflets[A].organ_id,'leaf_001', 'containment alone changes nothing');
  a.vstate().leaflets[A].pts.b3 = {'one.jpg':[200,384]}; a.vstate().leaflets[A].point_semantic_names = {b3:'visible_attachment'};
  const withBase = a.proposeMembership(A,'one.jpg');
  assert.equal(withBase.state,'proposed'); assert.equal(withBase.suggested_parent,'L01');
  assert.equal(a.membershipState().candidates[overlapOnly.candidate_id].state,'superseded');
  assert.equal(a.vstate().leaflets[A].organ_id,'leaf_001', 'a proposal never confirms itself');
  const key = a.confirmMembership(A,'L01',{candidateId:withBase.candidate_id});
  assert.equal(key,'L01|leaf_001');
  const leaf = a.vstate().leaflets[key];
  assert.equal(leaf.organ_id,'L01'); assert.equal(leaf.membership_review.source_method,'accepted_candidate');
  assert.equal(leaf.membership_review.evidence[0].kind,'visible_base_on_linked_substem');
  assert.equal(a.membershipState().candidates[withBase.candidate_id].state,'accepted');
});

test('scenario 2: a base on crossing sub-stems stays ambiguous, and no hidden connection is invented', () => {
  const {a} = fixture();
  leaflet(a,A,'one.jpg',geom(280,340,330,379),[304,384]); // inside both S1 and S2
  const c = a.proposeMembership(A,'one.jpg');
  assert.equal(c.state,'ambiguous'); assert.equal(c.state_reason,'visible_attachment_touches_several_parents');
  assert.equal(c.suggested_parent,null);
  a.keepCandidateUnresolved(c.candidate_id);
  const counts = Object.fromEntries(a.membershipCounts().parents.map(p => [p.parent_id,p]));
  assert.deepEqual(plain(counts.L01.unresolved_candidate_leaflets),[A]);
  assert.deepEqual(plain(counts.L02.unresolved_candidate_leaflets),[A]);
  assert.equal(counts.L01.exact_total_claimed,false);
  // A human decision retires the open proposal, which followed the leaflet to its new name.
  const key = a.confirmMembership(A,'L01');
  const retired = a.membershipState().candidates[c.candidate_id];
  assert.equal(retired.leaf_key,key); assert.equal(retired.state,'superseded');
  const after = Object.fromEntries(a.membershipCounts().parents.map(p => [p.parent_id,p]));
  assert.deepEqual(plain(after.L02.unresolved_candidate_leaflets),[]);
  // Base hidden in this view: no evidence anywhere -> nothing is written.
  leaflet(a,B,'one.jpg',geom(800,600,900,700));
  const before = JSON.stringify(a.membershipState().candidates);
  assert.equal(a.proposeMembership(B,'one.jpg'),null);
  assert.equal(JSON.stringify(a.membershipState().candidates),before);
  assert.equal(a.vstate().leaflets[B].organ_id,'leaf_002');
});

test('the nearest stem and the bbox centre are not attachment evidence', () => {
  const {a} = fixture();
  // bbox centre (305,350) lies on S2 (L02) but the visible base (160,385) lies on S1 (L01).
  leaflet(a,A,'one.jpg',geom(280,330,330,370),[160,385]);
  const c = a.proposeMembership(A,'one.jpg');
  assert.equal(c.state,'proposed'); assert.equal(c.suggested_parent,'L01');
  const l02 = c.candidate_parents.find(p => p.parent_id === 'L02');
  assert.ok(!l02 || l02.evidence.every(e => e.kind === 'compound_bbox_overlap_supporting_only'));
  // A base just outside the tolerance of every mask gives no attachment evidence.
  leaflet(a,B,'one.jpg',geom(700,500,720,520),[710,395]);
  assert.equal(a.proposeMembership(B,'one.jpg'),null);
  // Only a point whose meaning is a visible attachment is a base: a leaf tip lying on a stem is not.
  const tip = leaflet(a,C,'one.jpg',geom(700,600,720,620));
  tip.pts.b0 = {'one.jpg':[200,384]}; tip.point_semantic_names = {b0:'distal_tip'};
  assert.equal(a.proposeMembership(C,'one.jpg'),null);
});

test('scenario 3: a parent holds many leaflets; a confirmed leaflet cannot silently join a second parent', () => {
  const {a} = fixture();
  leaflet(a,A,'one.jpg',geom(10,10,50,50)); leaflet(a,B,'one.jpg',geom(60,10,90,50));
  const ka = a.confirmMembership(A,'L01'), kb = a.confirmMembership(B,'L01');
  assert.deepEqual([ka,kb],['L01|leaf_001','L01|leaf_002']);
  assert.throws(() => a.confirmMembership(ka,'L02'), /다른 복엽으로 변경/);
  assert.equal(a.vstate().leaflets[ka].organ_id,'L01');
  const counts = Object.fromEntries(a.membershipCounts().parents.map(p => [p.parent_id,p]));
  assert.deepEqual(plain(counts.L01.confirmed_member_ids),[ka,kb]);
  assert.deepEqual(plain(counts.L02.confirmed_member_ids),[]);
});

test('scenario 4: one leaflet seen in two photos counts once; uncertain identity is reported separately', () => {
  const {a} = fixture();
  leaflet(a,A,'one.jpg',geom(10,10,50,50)); leaflet(a,A,'two.jpg',geom(20,20,60,60));
  a.setLeafViewStatus(A,'one.jpg','identity_review','confirmed'); a.setLeafViewStatus(A,'two.jpg','identity_review','confirmed');
  leaflet(a,B,'one.jpg',geom(60,10,90,50));
  a.confirmMembership(A,'L01'); a.confirmMembership(B,'L01');
  const l01 = a.membershipCounts().parents.find(p => p.parent_id === 'L01');
  assert.equal(l01.confirmed_member_ids.length,2);
  assert.equal(l01.identity_confirmed_member_count,1, 'four sightings of one leaflet are one leaflet; unconfirmed identity is not counted');
});

test('scenario 5: a JSON count mismatch is a finding; the record, labels and assignments are untouched', () => {
  const {a} = fixture();
  const growth = {plant_id:'dwt_01',capture_date:'2026-09-20',compound_leaf_count:3,
    compound_leaves:[{compound_leaf_id:'L01',leaflet_count:8,is_unfolding:false},{compound_leaf_id:'L02',leaflet_count:9,is_unfolding:false},
                     {compound_leaf_id:'L03',leaflet_count:9,is_unfolding:false}],growth_shoot_count:3};
  const original = JSON.stringify(growth);
  leaflet(a,A,'one.jpg',geom(10,10,50,50)); a.setLeafViewStatus(A,'one.jpg','identity_review','confirmed');
  const nLeaves = Object.keys(a.vstate().leaflets).length;
  a.loadGrowthReference(growth,'dwt_01_260920.json');
  a.confirmMembership(A,'L01');
  assert.equal(JSON.stringify(growth),original);
  assert.equal(Object.keys(a.vstate().leaflets).length,nLeaves);
  const counts = Object.fromEntries(a.membershipCounts().parents.map(p => [p.parent_id,p]));
  assert.equal(counts.L01.recorded_leaflet_count,8); assert.equal(counts.L01.finding,'fewer_reviewed_leaflets_than_recorded');
  assert.equal(counts.L02.finding,'fewer_reviewed_leaflets_than_recorded');
  assert.throws(() => a.loadGrowthReference({...growth,plant_id:'dwt_02'},'dwt_02.json'), /다른 개체/);
});

test('scenario 6: equal recorded counts for L02 and L03 do not resolve an ambiguous leaflet', () => {
  const {a} = fixture();
  a.loadGrowthReference({plant_id:'dwt_01',compound_leaves:[{compound_leaf_id:'L02',leaflet_count:9},{compound_leaf_id:'L03',leaflet_count:9}]},'g.json');
  const leaf = leaflet(a,A,'one.jpg',geom(400,200,450,250),[305,300]); // on S2 (L02)
  (leaf.pts.b4 ||= {})['one.jpg'] = [505,300]; leaf.point_semantic_names.b4 = 'visible_attachment'; // and on S3 (L03)
  const c = a.proposeMembership(A,'one.jpg');
  assert.equal(c.state,'ambiguous'); assert.equal(c.suggested_parent,null);
  assert.deepEqual(plain(c.candidate_parents.map(p => p.parent_id)).sort(),['L02','L03']);
  assert.equal(a.vstate().leaflets[A].organ_id,'leaf_001', 'a count deficit never forces an assignment');
});

test('scenario 7: confirm, reparent, unassign, split and undo keep observations, references and coordinates', () => {
  const {a,ids} = fixture();
  const leaf = leaflet(a,A,'one.jpg',geom(10.5,20.25,110,220),[200,384]);
  leaflet(a,A,'two.jpg',geom(30,40,90,100));
  a.setPointMeaning(A,'b3','visible_attachment');
  leaf.pts.b0 = {'one.jpg':[12.5,22.75],'two.jpg':[31,41]};
  const coords = JSON.stringify({pts:leaf.pts,bboxes:leaf.bboxes});
  const st = a.vstate();
  st.proposals = {p1:{proposal_id:'p1',target_leaf_key:A,image_key:'one.jpg',state:'accepted',accepted_into:{leaf_key:A}}};
  st.auto_drafts = {d1:{draft_id:'d1',state:'assigned',assigned_to:A,image_key:'one.jpg'}};
  st.identity_decisions = [{source_leaf_key:A,candidate_leaf_key:'leaf_009|unavailable',image_key:'two.jpg',decision:'different'}];
  const adopted = a.adoptLeafletDetection('one.jpg',ids.F);
  const cand = a.proposeMembership(A,'two.jpg'); // other photo not identity-confirmed: its base is not evidence
  assert.equal(cand, null);
  const k1 = a.confirmMembership(A,'L01');
  assert.equal(k1,'L01|leaf_001'); assert.equal(a.ui.leafKey,k1, 'the selection follows the renamed leaflet');
  assert.equal(st.leaflets[A],undefined);
  assert.equal(st.proposals.p1.target_leaf_key,k1); assert.equal(st.proposals.p1.accepted_into.leaf_key,k1);
  assert.equal(st.auto_drafts.d1.assigned_to,k1); assert.equal(st.identity_decisions[0].source_leaf_key,k1);
  assert.deepEqual(plain(a.membershipState().key_map.map(r => [r.from,r.to])),[[A,k1]]);
  assert.equal(JSON.stringify({pts:st.leaflets[k1].pts,bboxes:st.leaflets[k1].bboxes}),coords);
  assert.equal(st.leaflets[k1].point_semantic_names.b3,'visible_attachment');
  const k2 = a.reparentMembership(k1,'L02');
  assert.equal(k2,'L02|leaf_001'); assert.equal(st.proposals.p1.target_leaf_key,k2);
  assert.equal(st.leaflets[k2].membership_review.previous_parent_id,'L01');
  const snapshot = JSON.stringify(a.vstate());
  const k3 = a.unassignMembership(k2);
  assert.equal(k3,A); assert.equal(a.vstate().leaflets[A].membership_review.state,'unassigned');
  a.undo();
  assert.equal(JSON.stringify(a.vstate()),snapshot, 'one undo reverts the rename and every reference together');
  assert.equal(a.ui.leafKey,k2, 'the selection follows the leaflet back to its restored name');
  // Split: the two.jpg observation becomes a new unassigned identity and takes its candidate along.
  const st2 = a.vstate();
  st2.leaflets[k2].view_status['two.jpg'].identity_review = 'confirmed';
  st2.membership.candidates.x = {candidate_id:'x',leaf_key:k2,image_key:'two.jpg',state:'kept_unresolved',candidate_parents:[{parent_id:'L01',evidence:[]}],history:[]};
  const newId = a.moveLeafView(k2,'two.jpg',null);
  assert.notEqual(newId.split('|')[0],'leaf_001', 'a renamed leaflet name is never handed out again');
  assert.equal(st2.membership.candidates.x.leaf_key,newId);
  assert.equal(st2.leaflets[newId].membership_review,undefined, 'the split observation does not inherit confirmed membership');
  assert.equal(st2.leaflets[k2].organ_id,'L02');
  assert.deepEqual(plain(st2.leaflets[newId].pts.b0['two.jpg']),[31,41]);
  assert.equal(adopted,'leaf_002|unavailable');
});

test('scenario 8: an old backup without membership metadata loads and everything stays unresolved', async () => {
  const a = app();
  const legacy = {variants:{__all__:{leaflets:{'leaf_001|A1':{organ_id:'leaf_001',leaflet_id:'A1',pts:{b0:{'one.jpg':[5,6]}},contours:{},
    bboxes:{'one.jpg':{...geom(1,2,30,40),image_width_px:1000,image_height_px:800,annotation_id:'lb1'}}}},boxes:{}}}};
  await a.restoreBackup(plain(legacy));
  const counts = a.membershipCounts();
  assert.deepEqual(plain(counts.parents),[]);
  assert.deepEqual(plain(counts.unassigned_leaflets),['leaf_001|A1']);
  assert.equal(a.proposeMembership('leaf_001|A1','one.jpg'),null);
  assert.equal(a.buildExport().nPoints,1);
  a.addParent('L01');
  const key = a.confirmMembership('leaf_001|A1','L01');
  assert.equal(key,'L01|A1', 'an existing leaflet_id is kept');
});

test('scenario 9: bbox-only leaflets are usable; a growth-shoot bbox and mask count once and never as leaflets', () => {
  const {a,ids} = fixture();
  leaflet(a,A,'one.jpg',geom(10,10,50,50));
  assert.equal(a.confirmMembership(A,'L03'),'L03|leaf_001');
  assert.equal(a.detectionObjects('one.jpg','growth-shoot').length,2);
  a.linkDetectionObjects('one.jpg',ids.G1,ids.G2);
  assert.equal(a.detectionObjects('one.jpg','growth-shoot').length,1);
  const counts = a.membershipCounts();
  assert.deepEqual(plain(counts.growth_shoot_objects_by_photo),{'one.jpg':1});
  assert.ok(counts.parents.every(p => p.confirmed_member_ids.every(id => !id.includes('growth'))));
  assert.throws(() => a.linkDetectionObjects('one.jpg',ids.G1,ids.S1), /생장 순/);
  a.unlinkDetectionObject('one.jpg',ids.G2);
  assert.equal(a.detectionObjects('one.jpg','growth-shoot').length,2);
});

test('scenario 10: membership actions never change measured coordinates or exported point rows', () => {
  const {a} = fixture();
  const leaf = leaflet(a,A,'one.jpg',geom(10,10,50,50),[200,384]);
  leaf.pts.b0 = {'one.jpg':[1.25,2.5],'two.jpg':[3,4]};
  const rows = out => out.points.split('\n').slice(1).map(r => r.split(',')).map(c => [c[0],c[3],c[4],c[5]].join(',')).sort();
  const before = rows(a.buildExport());
  a.confirmMembership(A,'L01'); a.reparentMembership('L01|leaf_001','L02'); a.unassignMembership('L02|leaf_001');
  assert.deepEqual(rows(a.buildExport()),before);
  assert.deepEqual(plain(Object.values(a.vstate().leaflets)[0].pts.b0),{'one.jpg':[1.25,2.5],'two.jpg':[3,4]});
});

test('anchors are one-owner relationships and unlinking retires the proposals that cited them', () => {
  const {a,ids} = fixture();
  assert.throws(() => a.linkCompoundAnchor('L02','one.jpg',ids.C1), /이미 L01/);
  assert.throws(() => a.linkSubstem('L03','one.jpg',ids.S1), /이미 L01/);
  assert.throws(() => a.linkSubstem('L01','one.jpg',ids.C1), /잎자루/);
  leaflet(a,A,'one.jpg',geom(260,200,340,280),[200,384]);
  const c = a.proposeMembership(A,'one.jpg');
  a.unlinkAnchor('L01','one.jpg',ids.S1);
  assert.equal(a.membershipState().candidates[c.candidate_id].state,'superseded');
  assert.throws(() => a.confirmMembership(A,'L01',{candidateId:c.candidate_id}), /이미 처리된/);
  assert.throws(() => a.addParent('leaf_001'), /소엽 라벨 이름/);
  assert.throws(() => a.confirmMembership(A,'L77'), /등록되지 않은/);
});

test('an identity confirmed in another photo supplies evidence; an unconfirmed one does not', () => {
  const {a} = fixture();
  leaflet(a,A,'one.jpg',geom(800,600,900,700));        // no base visible here
  leaflet(a,A,'two.jpg',geom(180,340,260,379),[200,384]); // base on S1 of two.jpg
  assert.equal(a.proposeMembership(A,'one.jpg')?.state ?? null,null);
  a.setLeafViewStatus(A,'two.jpg','identity_review','confirmed');
  const c = a.proposeMembership(A,'one.jpg');
  assert.equal(c.state,'proposed'); assert.equal(c.suggested_parent,'L01');
  assert.equal(c.candidate_parents[0].evidence[0].kind,'visible_base_on_linked_substem_other_view');
});

test('every membership decision is logged with the scores the rules saw, and undo removes it', () => {
  const {a} = fixture();
  leaflet(a,A,'one.jpg',geom(260,200,340,280),[200,384]);
  const c = a.proposeMembership(A,'one.jpg');
  a.keepCandidateUnresolved(c.candidate_id);
  const key = a.confirmMembership(A,'L01',{candidateId:c.candidate_id});
  a.reparentMembership(key,'L02'); a.unassignMembership('L02|leaf_001');
  const log = a.membershipState().decision_log;
  assert.deepEqual(plain(log.map(e => [e.rule_id, e.decision])), [['membership_candidate','kept_unresolved'],['membership_candidate','accepted'],
    ['membership_manual','reparented'],['membership_manual','unassigned']]);
  const acc = log[1];
  assert.equal(acc.schema_version,'threshold-decision-log-1'); assert.equal(acc.rule_version,1);
  assert.equal(acc.score_name,'heuristic_score'); assert.ok(acc.score_value > 3, 'attachment weight plus overlap');
  assert.equal(acc.scores.attachment_distance_px,0); assert.equal(acc.scores.attachment_tolerance_px,6);
  assert.equal(acc.scores.compound_overlap_fraction,1); assert.equal(acc.image_file,'one.jpg');
  assert.equal(acc.decision_detail.parent_id,'L01'); assert.equal(acc.plant_id,'dwt_01');
  assert.ok(log.every(e => e.decision_id.startsWith('dec_') && e.decided_at));
  a.undo();
  assert.equal(a.membershipState().decision_log.length,3, 'an undone decision is not kept for calibration');
});
