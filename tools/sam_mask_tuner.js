/* Raw-logit thresholding and explicit 8-connected component filtering. */
'use strict';
function thresholdForSensitivity(value) {
  if (!Number.isFinite(value) || value < 0 || value > 100) throw Error('Sensitivity must be in [0,100]');
  return (50-value)*0.08;
}
function processMask(logits, width, height, options, positivePoints=[]) {
  if (!Number.isInteger(width)||!Number.isInteger(height)||width<1||height<1||logits.length!==width*height) throw Error('Invalid raster dimensions');
  if (!Number.isInteger(options.minAreaPx)||options.minAreaPx<0) throw Error('Invalid component area');
  if (typeof options.seedOnly!=='boolean') throw Error('Invalid seed filter');
  const threshold=thresholdForSensitivity(options.sensitivity), mask=new Uint8Array(logits.length);
  const seeds=new Uint8Array(logits.length);
  for (const p of positivePoints) {
    if (p.length!==2||!p.every(Number.isFinite)||p[0]<0||p[0]>=width||p[1]<0||p[1]>=height) throw Error('Seed outside crop');
    seeds[Math.floor(p[1])*width+Math.floor(p[0])]=1;
  }
  for (let i=0;i<logits.length;i++) {
    if (!Number.isFinite(logits[i])) throw Error('Non-finite score');
    mask[i]=logits[i]>threshold?1:0;
  }
  if (options.seedOnly && positivePoints.length===0) throw Error('Seed filtering requires include points');
  const rawAreaPx=mask.reduce((a,b)=>a+b,0);
  if (options.minAreaPx>0||options.seedOnly) {
    const visited=new Uint8Array(mask.length), queue=new Int32Array(mask.length);
    for (let start=0;start<mask.length;start++) {
      if (!mask[start]||visited[start]) continue;
      let head=0,tail=1,hit=false;queue[0]=start;visited[start]=1;
      while(head<tail) {
        const index=queue[head++],x=index%width,y=Math.floor(index/width);
        if (seeds[index]) hit=true;
        for(let dy=-1;dy<=1;dy++) for(let dx=-1;dx<=1;dx++) {
          const xx=x+dx,yy=y+dy;
          if((dx===0&&dy===0)||xx<0||xx>=width||yy<0||yy>=height)continue;
          const next=yy*width+xx;
          if(mask[next]&&!visited[next]) {visited[next]=1;queue[tail++]=next;}
        }
      }
      if(tail<options.minAreaPx||(options.seedOnly&&!hit)) for(let j=0;j<tail;j++) mask[queue[j]]=0;
    }
  }
  const areaPx=mask.reduce((a,b)=>a+b,0);
  const missedSeeds=positivePoints.filter(p=>!mask[Math.floor(p[1])*width+Math.floor(p[0])]).length;
  return {mask,threshold,rawAreaPx,areaPx,removedAreaPx:rawAreaPx-areaPx,missedSeeds};
}
function restoreFullMask(mask,crop,imageSize) {
  const [x0,y0,x1,y1]=crop,[width,height]=imageSize;
  if (![...crop,...imageSize].every(Number.isInteger)||x0<0||y0<0||x1>width||y1>height||x1<=x0||y1<=y0||mask.length!==(x1-x0)*(y1-y0)) throw Error('Invalid export coordinates');
  const full=new Uint8Array(width*height),cropWidth=x1-x0;
  for(let y=0;y<y1-y0;y++) for(let x=0;x<cropWidth;x++)full[(y+y0)*width+x+x0]=mask[y*cropWidth+x]?255:0;
  return full;
}
function selectionMetadata(data,candidateIndex,options,result) {
  const candidate=data.candidates[candidateIndex];
  if(!candidate)throw Error('Invalid candidate');
  return {schema_version:'sam-mask-selection-1',case_id:data.case_id,target_class:data.target_class,trial_id:data.trial_id,
    image_sha256:data.image_sha256,image_size_px:data.image_size_px,crop_xyxy_px:data.crop_xyxy_px,
    source_run_sha256:data.source_run_sha256,source_logits_sha256:candidate.logits_sha256,
    candidate_index:candidate.index,model_score_before_adjustment:candidate.score,
    sensitivity:options.sensitivity,threshold_logit:result.threshold,minimum_component_area_px:options.minAreaPx,
    keep_include_point_components_only:options.seedOnly,component_connectivity:8,
    selected_area_px:result.areaPx,removed_area_px:result.removedAreaPx,missed_include_points:result.missedSeeds,
    points:data.points,box_xyxy_px:data.box_xyxy_px,
    review_status:'unreviewed',measured_iou:'unavailable',postprocessed_model_score:'unavailable'};
}
const SamMaskCore={thresholdForSensitivity,processMask,restoreFullMask,selectionMetadata};
if(typeof module!=='undefined'&&module.exports)module.exports=SamMaskCore;
else window.SamMaskCore=SamMaskCore;
