// Model/controller regression tests. Actual canvas interactions are also checked in the browser.
const test = require('node:test');
const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const vm = require('node:vm');
const crypto = require('node:crypto');

function app() {
  const html = fs.readFileSync(path.join(__dirname,'../leaf_point_annotator.html'),'utf8');
  const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
  const cutoff = script.indexOf('// Wiring');
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
  vm.runInContext(script.slice(0,cutoff) + `
    updateSide = () => {}; refreshSelects = () => {}; draw = () => {};
    getBitmap = async key => ({width:images.get(key).size[0],height:images.get(key).size[1]});
    ui.plant = 'TEST'; sessionId = 'TEST_session';
    this.api = {Cam,ui,store,images,frames,panes,history,vstate,currentLeaf,currentPid,
      boxFromDrag,validBox,moveBox,resizeBox,boxPointerDown,boxPointerMove,boxPointerUp,
      removeBox,undo,buildExport,buildBoxExport,importBoxRow,importCsv,parseCsv,
      boundaryCount,autoContour,leafStatus,fitPoint,saveLocal,restoreLocal,switchSession,
      advanceIndex,setMode,boxImageXY,boxScreenXY,
      boxOrgan,boxLinks,identityEntries,nextOrganId,validateBoxIdentity,assignBoxIdentity,
      moveLeafView,changeBoxClass,chooseIdentity,newIdentity,selectLeaf,
      setVariants:defs=>{variantDefs=defs;},
      getSession:()=>sessionId};
  })();`,context);
  const a=context.api;
  a.images.set('one.jpg',{name:'one.jpg',size:[1000,800]});
  a.images.set('two.jpg',{name:'two.jpg',size:[1000,800]});
  const pane={key:'one.jpg',index:0,bitmap:{width:1000,height:800},view:{scale:1,ox:0,oy:0},gesture:null,hover:null};
  a.panes.push(pane);
  return {a,pane,nodes,saved};
}
const plain = value => JSON.parse(JSON.stringify(value));
const geometry = {x_min_px:10,y_min_px:20,x_max_px:110,y_max_px:120};
const bbox = {...geometry,annotation_id:'bbox_1',class_name:'flower',image_width_px:1000,image_height_px:800};
function drag(a,pane,tool='flower',start=[10,20],end=[110,120],cancel=false,target=null) {
  a.ui.tool=tool; a.ui.forceNewBox=true; a.ui.boxTarget=target;
  a.boxPointerDown(pane,{altKey:false},...start);
  a.boxPointerMove(pane,...end);
  const gesture=pane.gesture; pane.gesture=null;
  a.boxPointerUp(pane,gesture,cancel);
}

test('reverse drags clip to pixel edges; malformed classes and zero-area boxes fail',()=>{
  const {a}=app();
  assert.deepEqual(plain(a.boxFromDrag([120,90],[-4,1],100,80)),{x_min_px:0,y_min_px:1,x_max_px:100,y_max_px:80});
  assert.equal(a.validBox(bbox,1000,800),true);
  for(const bad of [{class_name:'leaf'},{x_max_px:10},{x_min_px:NaN},{y_max_px:801}]) assert.equal(a.validBox({...bbox,...bad},1000,800),false);
});
test('movement preserves box size at image edges and corner resizing can cross the anchor',()=>{
  const {a}=app(); const moved=a.moveBox(bbox,-100,1000);
  assert.equal(moved.x_min_px,0); assert.equal(moved.y_max_px,800);
  assert.equal(moved.x_max_px-moved.x_min_px,100);
  assert.deepEqual(plain(a.resizeBox(bbox,'nw',[150,170])),{...bbox,x_min_px:110,y_min_px:120,x_max_px:150,y_max_px:170});
});
test('flower and bud gestures do not create leaf points; cancelled gestures leave no record',()=>{
  const {a,pane}=app(); drag(a,pane); drag(a,pane,'bud',[200,200],[230,240]); drag(a,pane,'bud',[300,300],[400,400],true);
  assert.deepEqual(Object.keys(a.vstate().leaflets),[]);
  assert.equal(a.vstate().boxes['one.jpg'].length,2);
  assert.deepEqual(plain(a.vstate().boxes['one.jpg'].map(b=>b.class_name)),['flower','bud']);
  assert.equal(a.buildExport().nPoints,0); assert.equal(a.buildExport().nContours,0);
  assert.equal(a.buildExport().nBoxes,2); assert.equal(a.buildExport().warnings.length,0);
});
test('box add/delete undo preserves leaf annotations and local storage restores both types',()=>{
  const {a,pane,saved}=app(); a.currentLeaf(true).pts.b0={'one.jpg':[20,30]};
  drag(a,pane); const id=a.vstate().boxes['one.jpg'][0].annotation_id;
  a.removeBox('one.jpg',id); assert.equal(a.buildBoxExport().nBoxes,0);
  a.undo(); assert.equal(a.buildBoxExport().nBoxes,1);
  a.saveLocal(); assert.equal(saved.size,1);
  a.store.variants={}; a.restoreLocal();
  assert.equal(a.buildBoxExport().nBoxes,1); assert.equal(a.currentLeaf().pts.b0['one.jpg'][0],20);
  a.undo(); assert.equal(a.buildBoxExport().nBoxes,0); assert.ok(a.currentLeaf().pts.b0);
});
test('bbox CSV round-trip preserves class, geometry, dimensions and ID without duplicate rows',async()=>{
  const {a,pane}=app(); drag(a,pane); const before=a.buildBoxExport().bboxes;
  const rows=a.parseCsv(before); a.vstate().boxes={};
  await a.importCsv([{name:'bboxes.csv',text:async()=>before}]);
  await a.importCsv([{name:'bboxes.csv',text:async()=>before}]);
  assert.equal(a.buildBoxExport().nBoxes,1);
  assert.equal(a.buildBoxExport().bboxes,before);
  assert.equal(rows[0].image_width_px,'1000');
});
test('bbox import rejects foreign sessions, missing coordinates, bad classes and changed resolution',async()=>{
  const {a,pane}=app(); drag(a,pane); const row=a.parseCsv(a.buildBoxExport().bboxes)[0]; a.vstate().boxes={};
  for(const change of [{session_id:'other'},{variant_id:'other'},{plant_id:'other'},{class_name:'unknown'},{x_min_px:''},{x_min_px:'NaN'},{image_width_px:'999'},{x_max_px:'1001'}]) {
    await assert.rejects(a.importBoxRow({...row,...change},new Map()));
    assert.equal(a.buildBoxExport().nBoxes,0);
  }
});
test('selected-view CSV excludes foreign images and importing them fails',async()=>{
  const {a,pane}=app(); drag(a,pane); pane.key='two.jpg'; drag(a,pane,'bud');
  const all=a.vstate(); a.store.variants.reduced=all;
  a.setVariants([{variant_id:'reduced',keys:new Set(['one.jpg'])}]); a.ui.variant='reduced';
  assert.equal(a.buildBoxExport().nBoxes,1);
  const row=a.parseCsv(a.buildBoxExport().bboxes)[0];
  await assert.rejects(a.importBoxRow({...row,image_file:'two.jpg'},new Map()));
});
test('switching sessions clears undo so another plant cannot be restored into this session',()=>{
  const {a,pane}=app(); drag(a,pane); a.switchSession('second_session'); a.undo();
  assert.equal(a.buildBoxExport().nBoxes,0); assert.equal(a.getSession(),'second_session');
});
test('box coordinate conversion survives pan/zoom without the point-center half pixel shift',()=>{
  const {a,pane}=app(); pane.view={scale:2,ox:50,oy:70};
  assert.deepEqual(plain(a.boxImageXY(pane,50,70)),[0,0]);
  assert.deepEqual(plain(a.boxScreenXY(pane,100,200)),[250,470]);
});
test('partial leaf outlines are not exported; the interior M point remains separate',()=>{
  const {a}=app(), leaf=a.currentLeaf(true);
  for(let i=0;i<6;i++) if(i!==3) leaf.pts['b'+i]={'one.jpg':[i*10,40]};
  leaf.pts.i0={'one.jpg':[20,20]};
  assert.equal(a.autoContour(leaf,'one.jpg'),null); assert.equal(a.buildExport().nContours,0);
  a.setMode('interior'); assert.equal(a.currentPid(),'i0');
  const center=a.parseCsv(a.buildExport().points).find(r=>r.point_id==='i0');
  assert.equal(center.boundary_index,'-1'); assert.equal(center.boundary_count,'6');
  leaf.pts.b3={'one.jpg':[30,40]}; assert.equal(a.autoContour(leaf,'one.jpg').length,6);
  a.ui.mode='boundary'; a.ui.bIndex=5; a.advanceIndex('one.jpg'); assert.equal(a.currentPid(),'i0');
});
test('two uncalibrated images cannot report geometric readiness and excluded views do not help fitting',()=>{
  const {a}=app(), leaf=a.currentLeaf(true);
  for(let i=0;i<6;i++) leaf.pts['b'+i]={'one.jpg':[i,1],'two.jpg':[i,2]};
  assert.equal(a.leafStatus(leaf).ready,false);
  a.frames.set('one.jpg',{cam:{width:1000,height:800}}); a.frames.set('two.jpg',{cam:{width:1000,height:800}});
  a.setVariants([{variant_id:'only_one',keys:new Set(['one.jpg'])}]); a.ui.variant='only_one';
  a.Cam.triangulate=()=>{throw Error('Excluded image must not be used');};
  assert.equal(a.fitPoint(leaf,'b0'),null);
});

test('same flower in two views shares organ_id but has separate observation IDs',async()=>{
  const {a,pane}=app(); drag(a,pane);
  const first=a.vstate().boxes['one.jpg'][0]; pane.key='two.jpg';
  drag(a,pane,'flower',[20,30],[80,90],false,first.organ_id);
  const second=a.vstate().boxes['two.jpg'][0];
  assert.equal(first.organ_id,'flower_001'); assert.equal(second.organ_id,first.organ_id);
  assert.notEqual(first.annotation_id,second.annotation_id);
  assert.deepEqual(plain(a.identityEntries('flower')[0].keys),['one.jpg','two.jpg']);
  const csv=a.buildBoxExport().bboxes;
  a.saveLocal(); a.store.variants={}; a.restoreLocal();
  assert.equal(a.boxLinks(first.organ_id).length,2);
  a.vstate().boxes={}; await a.importCsv([{name:'bboxes.csv',text:async()=>csv}]);
  assert.equal(a.buildBoxExport().bboxes,csv);
});

test('duplicate same-view identity and cross-class linking cannot overwrite boxes',()=>{
  const {a,pane}=app(); drag(a,pane); const flower=a.vstate().boxes['one.jpg'][0];
  drag(a,pane,'flower',[200,200],[250,250],false,flower.organ_id);
  assert.equal(a.vstate().boxes['one.jpg'].length,1);
  drag(a,pane,'bud',[200,200],[250,250]); const bud=a.vstate().boxes['one.jpg'][1];
  assert.throws(()=>a.assignBoxIdentity(pane.key,bud.annotation_id,flower.organ_id));
  assert.equal(bud.organ_id,'bud_001');
  drag(a,pane,'flower',[300,300],[350,350]); const other=a.vstate().boxes['one.jpg'][2];
  assert.equal(other.organ_id,'flower_002');
  assert.throws(()=>a.assignBoxIdentity(pane.key,other.annotation_id,flower.organ_id));
  assert.equal(other.organ_id,'flower_002');
});

test('split/relink only selected box; class correction and undo preserve group consistency',()=>{
  const {a,pane}=app(); drag(a,pane); const first=a.vstate().boxes['one.jpg'][0]; pane.key='two.jpg';
  drag(a,pane,'flower',[20,20],[80,90],false,first.organ_id);
  const second=a.vstate().boxes['two.jpg'][0], originalGeometry=plain(second);
  const id=a.assignBoxIdentity(pane.key,second.annotation_id);
  assert.notEqual(id,first.organ_id); assert.equal(first.organ_id,'flower_001');
  assert.equal(second.x_min_px,originalGeometry.x_min_px);
  a.assignBoxIdentity(pane.key,second.annotation_id,first.organ_id);
  assert.equal(a.boxLinks(first.organ_id).length,2);
  a.changeBoxClass(pane.key,second.annotation_id,'bud');
  assert.equal(a.identityEntries('flower').length,0); assert.equal(a.identityEntries('bud').length,1);
  a.undo(); assert.equal(a.identityEntries('flower')[0].keys.length,2);
});

test('legacy boxes remain unlinked until explicitly assigned and conflicting CSV rows fail',async()=>{
  const {a,pane}=app(); drag(a,pane); const row=a.parseCsv(a.buildBoxExport().bboxes)[0];
  a.vstate().boxes={}; delete row.organ_id;
  await a.importBoxRow(row,new Map());
  assert.equal(a.identityEntries('flower').length,0);
  assert.equal(a.parseCsv(a.buildBoxExport().bboxes)[0].organ_id,'unavailable');
  const id=a.assignBoxIdentity('one.jpg',row.annotation_id);
  assert.equal(id,'flower_001');
  await assert.rejects(a.importBoxRow({...row,annotation_id:'another',organ_id:id},new Map()));
  await assert.rejects(a.importBoxRow({...row,image_file:'two.jpg',annotation_id:'another',organ_id:id,class_name:'bud'},new Map()));
  assert.equal(a.buildBoxExport().nBoxes,1);
});

test('truss is labeled as a separate subject and is not counted as individual flowers',()=>{
  const {a,pane}=app(); drag(a,pane,'truss');
  const truss=a.vstate().boxes['one.jpg'][0];
  assert.equal(truss.organ_id,'truss_001'); assert.equal(a.identityEntries('flower').length,0);
  pane.key='two.jpg'; drag(a,pane,'truss',[20,20],[130,130],false,truss.organ_id);
  assert.equal(a.identityEntries('truss')[0].keys.length,2);
});

test('excluded views never appear in links and pending links cannot survive session changes',()=>{
  const {a,pane}=app(); drag(a,pane); pane.key='two.jpg'; drag(a,pane);
  const hidden=a.vstate().boxes['two.jpg'][0];
  a.store.variants.reduced=a.vstate(); a.setVariants([{variant_id:'reduced',keys:new Set(['one.jpg'])}]); a.ui.variant='reduced';
  assert.equal(a.boxLinks(hidden.organ_id).length,0);
  assert.deepEqual(plain(a.identityEntries('flower').map(x=>x.id)),['flower_001']);
  a.ui.boxTarget=hidden.organ_id; a.switchSession('another');
  assert.equal(a.ui.boxTarget,null); assert.equal(a.identityEntries('flower').length,0);
});

test('leaf photo split and relink move all landmarks and manual contour, preserving other views',()=>{
  const {a,pane}=app(), original=a.currentLeaf(true), source=a.ui.leafKey;
  original.pts={b0:{'one.jpg':[10,20],'two.jpg':[15,25]},i0:{'one.jpg':[30,40],'two.jpg':[35,45]}};
  original.contours={'one.jpg':[[10,20],[30,40],[50,60]],'two.jpg':[[1,2],[3,4],[5,6]]};
  const id=a.moveLeafView(source,pane.key), dest=a.currentLeaf();
  assert.notEqual(id,source); assert.equal(dest.organ_id,'leaf_002');
  assert.equal(original.pts.b0['one.jpg'],undefined); assert.deepEqual(plain(original.pts.b0['two.jpg']),[15,25]);
  assert.deepEqual(plain(dest.pts.i0['one.jpg']),[30,40]); assert.equal(dest.contours['one.jpg'].length,3);
  a.moveLeafView(id,pane.key,source);
  assert.equal(a.currentLeaf().pts.i0['one.jpg'][0],30);
  assert.deepEqual(plain(a.identityEntries('leaf')[0].keys),['one.jpg','two.jpg']);
  assert.equal(a.nextOrganId('leaf'),'leaf_003'); // Empty source IDs are reserved.
  a.undo(); assert.equal(a.vstate().leaflets[id].pts.b0['one.jpg'][0],10);
});

test('leaf relinking refuses same-photo replacement, incompatible landmark counts and excluded views',()=>{
  const {a}=app(), source=a.ui.leafKey, leaf=a.currentLeaf(true);
  leaf.pts.b0={'one.jpg':[10,20]};
  a.vstate().leaflets['leaf_002|unavailable']={organ_id:'leaf_002',leaflet_id:'unavailable',boundary_count:6,pts:{b0:{'one.jpg':[30,40]}},contours:{}};
  const target='leaf_002|unavailable', before=JSON.stringify(a.vstate());
  assert.throws(()=>a.moveLeafView(source,'one.jpg',target)); assert.equal(JSON.stringify(a.vstate()),before);
  const other=a.vstate().leaflets[target]; other.pts.b0={'two.jpg':[30,40]}; other.boundary_count=8;
  assert.throws(()=>a.moveLeafView(source,'one.jpg',target));
  other.boundary_count=6;
  a.store.variants.reduced=a.vstate(); a.setVariants([{variant_id:'reduced',keys:new Set(['one.jpg'])}]); a.ui.variant='reduced';
  assert.throws(()=>a.moveLeafView(source,'one.jpg',target));
});
