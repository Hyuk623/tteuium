const test=require('node:test');
const assert=require('node:assert/strict');
const core=require('../sam_mask_tuner.js');
const options={sensitivity:50,minAreaPx:0,seedOnly:false};

test('default preserves SAM strict >0 and broader sensitivity only adds pixels',()=>{
  const logits=new Float32Array([-2,0,2,3]);
  const low=core.processMask(logits,4,1,{...options,sensitivity:25});
  const mid=core.processMask(logits,4,1,options);
  const high=core.processMask(logits,4,1,{...options,sensitivity:75});
  assert.deepEqual([...low.mask],[0,0,0,1]);
  assert.deepEqual([...mid.mask],[0,0,1,1]);
  assert.deepEqual([...high.mask],[0,1,1,1]);
  for(let i=0;i<4;i++)assert.ok(low.mask[i]<=mid.mask[i]&&mid.mask[i]<=high.mask[i]);
});
test('8-connected filtering preserves thin diagonal, separate seeded regions and holes',()=>{
  const logits=new Float32Array(7*7).fill(-1);
  for(const [x,y] of [[0,0],[1,1],[2,2],[5,5],[5,6],[6,5],[6,6],[0,6]])logits[y*7+x]=1;
  const small=core.processMask(logits,7,7,{...options,minAreaPx:3});
  assert.equal(small.areaPx,7);assert.equal(small.mask[0],1);assert.equal(small.mask[6*7],0);
  const seeded=core.processMask(logits,7,7,{...options,seedOnly:true},[[0,0],[5,5]]);
  assert.equal(seeded.areaPx,7);assert.equal(seeded.missedSeeds,0);
  const strict=core.processMask(logits,7,7,{...options,sensitivity:0,seedOnly:true},[[0,0]]);
  assert.equal(strict.areaPx,0);assert.equal(strict.missedSeeds,1);
  const ring=new Float32Array([1,1,1,1,-1,1,1,1,1]);
  assert.equal(core.processMask(ring,3,3,{...options,seedOnly:true},[[0,0]]).mask[4],0);
});
test('export restores original image coordinates and records postprocessing without claiming accuracy',()=>{
  const mask=new Uint8Array([0,1,0,0]);
  const restored=core.restoreFullMask(mask,[2,3,4,5],[8,7]);
  assert.equal(restored.length,56);assert.equal(restored[3*8+3],255);
  assert.equal(restored.reduce((a,b)=>a+b,0),255);
  const data={case_id:'p',trial_id:'g',target_class:'petiole',image_sha256:'source',source_run_sha256:'run',image_size_px:[8,7],crop_xyxy_px:[2,3,4,5],points:[],box_xyxy_px:null,candidates:[{index:2,score:.8,logits_sha256:'prediction'}]};
  const record=core.selectionMetadata(data,0,{...options,minAreaPx:4},{threshold:0,areaPx:12,removedAreaPx:3,missedSeeds:0});
  assert.equal(record.source_logits_sha256,'prediction');assert.equal(record.minimum_component_area_px,4);
  assert.equal(record.measured_iou,'unavailable');assert.equal(record.review_status,'unreviewed');
});
test('invalid settings and source rasters fail visibly',()=>{
  assert.throws(()=>core.processMask([NaN],1,1,options),/Non-finite/);
  assert.throws(()=>core.processMask([1],1,1,{...options,seedOnly:true}),/include points/);
  assert.throws(()=>core.processMask([1],1,1,{...options,minAreaPx:-1}),/area/);
  assert.throws(()=>core.processMask([1],1,1,options,[[2,0]]),/outside/);
  assert.throws(()=>core.restoreFullMask([1],[0,0,2,2],[2,2]),/coordinates/);
});
