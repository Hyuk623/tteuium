// Leaflet bbox identity, per-photo visibility/review, point meaning and link/split regressions.
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
    getBitmap = async key => ({width:images.get(key).size[0],height:images.get(key).size[1]});
    ui.plant = 'TEST'; sessionId = 'TEST_session';
    this.api = {ui,store,images,frames,panes,vstate,currentLeaf,leafKey,identityEntries,leafHasView,chooseIdentity,
      setLeafBox,removeLeafBox,setLeafViewStatus,leafViewStatus,setPointMeaning,moveLeafView,undo,zoomToLeaf,
      leafBoxPointerDown,leafBoxPointerMove,leafBoxPointerUp,boxImageXY,buildExport,buildLeafBoxExport,importCsv,
      parseCsv,buildBackup,restoreBackup,selectLeaf,setTool,leafExtentReadiness,boxPointerDown,boxPointerMove,boxPointerUp,toScreen};
  })();`,context);
  const a = context.api;
  for (const name of ['one.jpg','two.jpg','three.jpg']) a.images.set(name,{name,size:[1000,800]});
  const pane = {key:'one.jpg',index:0,bitmap:{width:1000,height:800},view:{scale:1,ox:0,oy:0},gesture:null,hover:null,
    canvas:{getBoundingClientRect:()=>({width:800,height:600})}};
  a.panes.push(pane);
  return {a,pane,saved};
}
const plain = value => JSON.parse(JSON.stringify(value));
const SIZE = {width:1000,height:800};
const A = 'leaf_001|A1', B = 'leaf_002|B1';
const geom = (x0,y0,x1,y1) => ({x_min_px:x0,y_min_px:y0,x_max_px:x1,y_max_px:y1});

test('a bbox-only photo creates a leaflet identity that is listed and selectable across views',()=>{
  const {a}=app();
  a.setLeafBox(A,'one.jpg',geom(10.25,20.5,110.75,220),SIZE);
  let entry=a.identityEntries('leaf').find(e=>e.id===A);
  assert.ok(entry, 'bbox-only leaflet appears in identity list before any point');
  assert.deepEqual(plain(entry.keys),['one.jpg']);
  a.setLeafBox(A,'three.jpg',geom(400,300,500,420),SIZE);
  entry=a.identityEntries('leaf').find(e=>e.id===A);
  assert.deepEqual(plain(entry.keys),['one.jpg','three.jpg']);
  assert.equal(a.leafHasView(a.vstate().leaflets[A],'two.jpg'),false);
  assert.deepEqual(plain(a.leafViewStatus(a.vstate().leaflets[A],'one.jpg')),{visibility:'unknown',identity_review:'unconfirmed'});
  a.selectLeaf('leaf_999','unavailable'); a.chooseIdentity(A);
  assert.equal(a.ui.leafKey,A);
  const out=a.buildExport();
  assert.equal(out.nPoints,0); assert.equal(out.nLeafletBoxes,2);
  assert.ok(!out.warnings.some(w=>w.includes('빠진 점')), 'bbox-only leaflets do not raise missing-point warnings');
  assert.equal(a.leafExtentReadiness(a.vstate().leaflets[A]).eligible,0);
});

test('visibility and identity review are independent, validated and recorded in history',()=>{
  const {a}=app();
  a.setLeafBox(A,'one.jpg',geom(10,20,110,220),SIZE);
  a.setLeafViewStatus(A,'one.jpg','visibility','partial');
  assert.deepEqual(plain(a.leafViewStatus(a.vstate().leaflets[A],'one.jpg')),{visibility:'partial',identity_review:'unconfirmed'});
  a.setLeafViewStatus(A,'one.jpg','identity_review','confirmed');
  assert.deepEqual(plain(a.leafViewStatus(a.vstate().leaflets[A],'one.jpg')),{visibility:'partial',identity_review:'confirmed'});
  assert.throws(()=>a.setLeafViewStatus(A,'one.jpg','visibility','mostly'));
  assert.throws(()=>a.setLeafViewStatus(A,'two.jpg','visibility','full'), /박스나 점이 없습니다/);
  const actions=a.vstate().leaflets[A].observation_history.map(h=>h.action);
  assert.deepEqual(plain(actions),['bbox_create','visibility_change','identity_review_change']);
  a.undo();
  assert.equal(a.leafViewStatus(a.vstate().leaflets[A],'one.jpg').identity_review,'unconfirmed');
});

function linkedFixture(a) {
  const leaves=a.vstate().leaflets;
  leaves[A]={organ_id:'leaf_001',leaflet_id:'A1',boundary_count:3,contours:{},review_status:'candidate_unreviewed',
    pts:{b0:{'one.jpg':[50,60],'two.jpg':[52,61]},i0:{'two.jpg':[70,80]}},point_semantic_names:{b0:'distal_tip',i0:'vein_junction'}};
  a.setLeafBox(A,'two.jpg',geom(30,40,130,160),SIZE);
  a.setLeafViewStatus(A,'two.jpg','visibility','full');
  a.setLeafViewStatus(A,'two.jpg','identity_review','confirmed');
  a.setLeafBox(B,'one.jpg',geom(600,500,700,600),SIZE);
}

test('split moves points, bbox, visibility, meanings and records the moved observation',()=>{
  const {a}=app(); linkedFixture(a);
  const newId=a.moveLeafView(A,'two.jpg',null);
  const src=a.vstate().leaflets[A], dest=a.vstate().leaflets[newId];
  assert.notEqual(newId,A); assert.ok(a.vstate().leaflets[A], 'source identity is retained, never renamed');
  assert.deepEqual(plain(dest.pts.b0),{'two.jpg':[52,61]}); assert.deepEqual(plain(dest.pts.i0),{'two.jpg':[70,80]});
  assert.deepEqual(plain(src.pts.b0),{'one.jpg':[50,60]});
  assert.equal(src.bboxes['two.jpg'],undefined);
  assert.deepEqual(plain([dest.bboxes['two.jpg'].x_min_px,dest.bboxes['two.jpg'].y_max_px]),[30,160]);
  assert.deepEqual(plain(dest.point_semantic_names),{b0:'distal_tip',i0:'vein_junction'});
  assert.deepEqual(plain(a.leafViewStatus(dest,'two.jpg')),{visibility:'full',identity_review:'unconfirmed'});
  assert.equal(src.view_status['two.jpg'],undefined);
  const record=dest.identity_history.at(-1);
  assert.equal(record.action,'split_observation');
  assert.deepEqual(plain(record.moved_observation.point_ids),['b0','i0']);
  assert.equal(record.moved_observation.view_status_before.identity_review,'confirmed');
  assert.equal(record.moved_observation.bbox.x_min_px,30);
  assert.deepEqual(plain(src.identity_history.at(-1)),plain(record));
  assert.equal(dest.review_status,'candidate_unreviewed');
  a.undo();
  assert.deepEqual(plain(a.vstate().leaflets[A].pts.b0),{'one.jpg':[50,60],'two.jpg':[52,61]});
  assert.equal(a.vstate().leaflets[newId],undefined);
});

test('relink refuses destination overwrite and conflicting point meanings without partial changes',()=>{
  const {a}=app(); linkedFixture(a);
  a.setLeafBox(B,'two.jpg',geom(300,300,350,350),SIZE);
  const before=JSON.stringify(a.vstate());
  assert.throws(()=>a.moveLeafView(A,'two.jpg',B),/덮어쓰지 않습니다/);
  assert.equal(JSON.stringify(a.vstate()),before);
  a.removeLeafBox(B,'two.jpg');
  a.vstate().leaflets[B].point_semantic_names={b0:'lobe_apex'};
  a.vstate().leaflets[B].pts.b0={'one.jpg':[650,550]}; a.vstate().leaflets[B].boundary_count=3;
  const beforeMeaning=JSON.stringify(a.vstate());
  assert.throws(()=>a.moveLeafView(A,'two.jpg',B),/의미가 대상 잎과 다릅니다/);
  assert.equal(JSON.stringify(a.vstate()),beforeMeaning);
  a.vstate().leaflets[B].point_semantic_names={b0:'distal_tip'};
  a.moveLeafView(A,'two.jpg',B);
  const dest=a.vstate().leaflets[B];
  assert.deepEqual(plain(dest.pts.b0),{'one.jpg':[650,550],'two.jpg':[52,61]});
  assert.equal(dest.bboxes['two.jpg'].x_max_px,130);
  assert.equal(dest.bboxes['one.jpg'].x_min_px,600, 'existing destination bbox in another photo is untouched');
  assert.equal(dest.identity_history.at(-1).action,'relink_observation');
});

test('overlapping boxes in one photo stay separate leaflets and editing hits only the selected one',()=>{
  const {a,pane}=app(); a.setTool('leafbox');
  a.setLeafBox(A,'one.jpg',geom(100,100,300,300),SIZE);
  a.setLeafBox(B,'one.jpg',geom(200,200,400,400),SIZE);   // overlaps A
  assert.equal(Object.keys(a.vstate().leaflets).length,2);
  assert.deepEqual(plain(a.identityEntries('leaf').map(e=>e.id)).sort(),[A,B].sort());
  a.selectLeaf('leaf_001','A1');
  // A drag starting inside the overlap edits the SELECTED leaflet's box, never the other one.
  const before=plain(a.vstate().leaflets[B].bboxes['one.jpg']);
  a.leafBoxPointerDown(pane,{altKey:false},...a.toScreen(pane,250,250));
  a.leafBoxPointerMove(pane,...a.toScreen(pane,270,260));
  const g=pane.gesture; pane.gesture=null; a.leafBoxPointerUp(pane,g,false);
  assert.deepEqual(plain(a.vstate().leaflets[B].bboxes['one.jpg']),before);
  assert.equal(a.vstate().leaflets[A].bboxes['one.jpg'].x_min_px,120);
  // Deleting the selected leaflet's box leaves the overlapping one intact.
  a.removeLeafBox(A,'one.jpg');
  assert.equal(a.vstate().leaflets[A].bboxes['one.jpg'],undefined);
  assert.deepEqual(plain(a.vstate().leaflets[B].bboxes['one.jpg']),before);
});

test('a bbox-only view can be linked into a leaflet whose points use another boundary count',()=>{
  const {a}=app();
  a.setLeafBox(B,'three.jpg',geom(10,10,60,60),SIZE);
  a.vstate().leaflets[A]={organ_id:'leaf_001',leaflet_id:'A1',boundary_count:3,contours:{},pts:{b0:{'one.jpg':[1,2]}}};
  a.moveLeafView(B,'three.jpg',A);
  assert.ok(a.vstate().leaflets[A].bboxes['three.jpg']);
  assert.equal(a.vstate().leaflets[A].boundary_count,3);
});

test('drawn box coordinates stay in original pixels through zoom, pan, CSV and backup round trips',async()=>{
  const {a,pane}=app(); a.setTool('leafbox'); a.selectLeaf('leaf_001','A1');
  pane.view={scale:3.7,ox:-812.3,oy:-455.9};
  const start=[123.4,98.7], end=[611.2,407.3];
  a.leafBoxPointerDown(pane,{altKey:false},...start); a.leafBoxPointerMove(pane,...end);
  const gesture=pane.gesture; pane.gesture=null; a.leafBoxPointerUp(pane,gesture,false);
  const box=a.vstate().leaflets[A].bboxes['one.jpg'];
  const s=a.boxImageXY(pane,...start), e=a.boxImageXY(pane,...end);
  assert.deepEqual(plain([box.x_min_px,box.y_min_px,box.x_max_px,box.y_max_px]),plain([s[0],s[1],e[0],e[1]]));
  assert.ok(box.x_min_px>200 && box.x_max_px<600, 'stored values are image pixels, not screen pixels');
  const stored=plain(box);
  a.zoomToLeaf(pane); pane.view={scale:0.4,ox:3,oy:9};
  assert.deepEqual(plain(a.vstate().leaflets[A].bboxes['one.jpg']),stored);
  a.setLeafViewStatus(A,'one.jpg','visibility','full');
  const csv=a.buildLeafBoxExport().leafletBboxes;
  delete a.vstate().leaflets[A].bboxes['one.jpg'];
  await a.importCsv([{name:'TEST_leaflet_bboxes.csv',text:async()=>csv}]);
  const imported=a.vstate().leaflets[A].bboxes['one.jpg'];
  for (const k of ['x_min_px','y_min_px','x_max_px','y_max_px','image_width_px','image_height_px','annotation_id']) assert.equal(imported[k],stored[k],k);
  assert.equal(a.leafViewStatus(a.vstate().leaflets[A],'one.jpg').visibility,'full');
  assert.equal(a.buildLeafBoxExport().leafletBboxes,csv);
  const backup=JSON.parse(JSON.stringify(a.buildBackup()));
  a.store.variants={};
  await a.restoreBackup(backup);
  assert.deepEqual(plain(a.vstate().leaflets[A].bboxes['one.jpg']),plain(imported));
});

test('leaflet bbox import rejects foreign sessions, bad states, resolution changes and overwrites',async()=>{
  const {a}=app();
  a.setLeafBox(A,'one.jpg',geom(10,20,110,220),SIZE);
  const row=a.parseCsv(a.buildLeafBoxExport().leafletBboxes)[0];
  const head=Object.keys(row).join(',');
  const csv=r=>head+'\n'+Object.values(r).join(',')+'\n';
  const before=JSON.stringify(a.vstate());
  for (const change of [{session_id:'other'},{variant_id:'other'},{visibility:'mostly'},{identity_review:'yes'},
      {image_width_px:'1500'},{x_max_px:'1001'},{x_min_px:''},{annotation_id:'leafbox_other'}]) {
    await a.importCsv([{name:'x_leaflet_bboxes.csv',text:async()=>csv({...row,...change})}]);
  }
  const after=JSON.parse(JSON.stringify(a.vstate()));
  const strip=v=>{for (const l of Object.values(v.leaflets)) delete l.observation_history; return JSON.stringify(v);};
  assert.equal(strip(after),strip(JSON.parse(before)));
});

test('preview-resolution photos cannot receive leaflet boxes for a calibrated original',()=>{
  const {a}=app();
  a.frames.set('one.jpg',{image_file:'one.jpg',cam:{width:3024,height:3024}});
  assert.throws(()=>a.setLeafBox(A,'one.jpg',geom(10,20,110,220),SIZE),/해상도/);
  assert.equal(a.vstate().leaflets[A],undefined);
});

test('point meanings are per physical point ID and never reorder IDs',()=>{
  const {a}=app();
  a.vstate().leaflets[A]={organ_id:'leaf_001',leaflet_id:'A1',boundary_count:6,contours:{},pts:{b3:{'one.jpg':[5,5]},i2:{'two.jpg':[9,9]}}};
  a.setPointMeaning(A,'b3','visible_attachment');
  a.setPointMeaning(A,'i2','other:second vein fork');
  assert.deepEqual(plain(a.vstate().leaflets[A].point_semantic_names),{b3:'visible_attachment',i2:'other:second vein fork'});
  assert.deepEqual(Object.keys(a.vstate().leaflets[A].pts),['b3','i2']);
  a.setPointMeaning(A,'b3','');
  assert.deepEqual(plain(a.vstate().leaflets[A].point_semantic_names),{i2:'other:second vein fork'});
  assert.throws(()=>a.setPointMeaning(A,'x1','distal_tip'));
});

test('legacy leaves, sparse IDs, contours, flower boxes and history survive backup save/load unchanged',async()=>{
  const {a,pane}=app();
  const legacy={organ_id:'leaf_007',leaflet_id:'unavailable',boundary_count:6,review_status:'candidate_unreviewed',
    pts:{b0:{'one.jpg':[1.5,2.25]},b4:{'one.jpg':[3,4],'two.jpg':[5,6]},i3:{'two.jpg':[7,8]}},
    contours:{'one.jpg':[[1,1],[2,2],[3,1]]},identity_history:[{action:'split_observation',image_file:'x.png'}],
    point_semantic_names:{b0:'distal_upper_lobe'}};
  a.vstate().leaflets['leaf_007|unavailable']=JSON.parse(JSON.stringify(legacy));
  a.ui.tool='flower'; a.ui.forceNewBox=true;
  a.boxPointerDown(pane,{altKey:false},10,20); a.boxPointerMove(pane,110,120);
  const g=pane.gesture; pane.gesture=null; a.boxPointerUp(pane,g,false);
  const pointsBefore=a.buildExport().points, boxesBefore=a.buildExport().bboxes;
  const backup=JSON.parse(JSON.stringify(a.buildBackup()));
  a.store.variants={};
  await a.restoreBackup(backup);
  assert.deepEqual(plain(a.vstate().leaflets['leaf_007|unavailable']),legacy);
  assert.equal(a.buildExport().points,pointsBefore);
  assert.equal(a.buildExport().bboxes,boxesBefore);
  assert.equal(a.buildExport().nLeafletBoxes,0);
  assert.equal(a.vstate().boxes['one.jpg'][0].class_name,'flower');
});
