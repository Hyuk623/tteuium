/* Exact cached-float32 thresholding; no morphology, interpolation or model calls. */
'use strict';
(function(root) {
  function threshold(value) {
    if (!Number.isFinite(value) || value < 0 || value > 100) throw Error('민감도는 0~100입니다.');
    // Match NumPy float32 array comparison, including pixels exactly at the boundary.
    return Math.fround((50 - value) * .08);
  }
  function raster(scores, count, height, width, candidate, sensitivity) {
    if (!Number.isInteger(candidate) || candidate < 0 || candidate >= count || scores.length !== count*height*width)
      throw Error('윤곽 후보의 크기가 맞지 않습니다.');
    const cut = threshold(sensitivity), size=height*width, offset=candidate*size;
    const mask=new Uint8Array(size);let area=0;
    for(let i=0;i<size;i++){if(scores[offset+i]>cut){mask[i]=1;area++;}}
    return {mask,area};
  }
  const api={threshold,raster};
  if(typeof module!=='undefined'&&module.exports)module.exports=api;
  else root.MaskPreviewMath=api;
})(typeof window!=='undefined'?window:globalThis);
