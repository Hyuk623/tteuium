/* Live compound-leaf / leaflet review in the existing local editor. */
'use strict';
(() => {
  const token=JSON.parse(document.getElementById('localRebuildToken').textContent);
  const panel=document.createElement('section');panel.id='maskBatchPanel';
  panel.innerHTML=`<style>
    #maskBatchPanel{background:#f4f8f2;color:#193528;padding:18px;margin:10px;border:1px solid #b5c8b8;border-radius:12px;font:15px/1.5 system-ui,sans-serif}
    #maskBatchPanel h2{margin:0;font-size:23px} #maskBatchPanel p{margin:7px 0}
    #maskBatchPanel button,#maskBatchPanel select,#maskBatchPanel input[type=number]{font:inherit;padding:7px 10px;border:1px solid #9aae9c;border-radius:6px;background:white;color:#193528;max-width:100%}
    #maskBatchPanel button{cursor:pointer} #maskBatchPanel button:disabled{opacity:.45;cursor:default}
    #maskBatchPanel button.primary{background:#24613d;color:white;border-color:#24613d}
    #maskBatchPanel .row{display:flex;gap:8px;align-items:center;flex-wrap:wrap;margin:9px 0}
    #maskBatchPanel .controls{position:sticky;top:0;z-index:3;background:#f4f8f2;border-block:1px solid #c6d7c7;padding:6px 0}
    #maskBatchPanel .compare{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,330px),1fr));gap:12px;margin-top:12px}
    #maskBatchPanel figure{margin:0;min-width:0} #maskBatchPanel figcaption{font-weight:650;padding:7px 0}
    #maskBatchPanel canvas{display:block;background:#243028;width:100%;height:auto;border-radius:8px;touch-action:none}
    #maskBatchPanel .notice{color:#664d0b;background:#fff4cf;padding:8px;border-radius:6px}
    #maskBatchPanel input[type=range]{accent-color:#24613d;width:260px;max-width:55vw}
    #maskBatchPanel .muted{font-size:13px;color:#56715d} #maskBatchPanel [hidden]{display:none!important}
    #maskBatchPanel .savebar{background:#e3eee4;border:1px solid #b5c8b8;border-radius:8px;padding:6px 8px}
    #maskBatchPanel .savebar .accept{background:#1b4d30;border-color:#1b4d30}
    #maskBatchPanel .savebar .sep{width:1px;align-self:stretch;background:#b5c8b8;margin:0 4px}
  </style>
  <h2>복엽 · 소엽 윤곽 비교</h2>
  <p>사진과 잎을 선택하고, 민감도를 움직여 윤곽을 비교하세요. <b>미리보기 저장</b>을 눌러야 결과에 반영됩니다.</p>
  <div class="row"><label>대상 <select id="mbClass"><option value="leaflet">소엽 · leaflet</option><option value="compoundleaves">복엽 · compound leaf</option></select></label>
    <label>사진 <select id="mbPhoto"><option value="">전체 사진</option></select></label>
    <label>상태 <select id="mbFilter"><option value="pending">미완료·보류</option><option value="all">전체</option><option value="accepted">확정</option><option value="rejected">거절</option><option value="failed">생성 실패</option></select></label></div>
  <select id="mbQueue" aria-label="잎 선택" style="width:100%"></select>
  <p id="mbStatus" role="status"></p><p id="mbMessage" role="alert" style="color:#9b301c"></p>
  <div class="controls">
    <div class="row"><label>민감도 <input id="mbSensitivity" type="range" min="0" max="100" step="1" value="50"></label>
      <input id="mbSensitivityNumber" aria-label="민감도 숫자" type="number" min="0" max="100" step="1" value="50" style="width:76px">
      <button data-do="s20">20 비교</button><button data-do="s50">50 기본 경계</button>
      <button data-do="restorePreview">저장값 복원</button></div>
    <div class="row savebar"><button class="primary" data-do="savePreview">미리보기 저장</button><button class="primary" data-do="saveBrush">브러시 수정 저장</button><button class="primary accept" data-do="accept">확정 후 다음</button><button class="primary" data-do="acceptPartial" title="다른 잎에 가려져 일부만 보임: 보이는 부분만 수락">가려짐 · 보이는 부분 수락</button>
      <span class="sep" aria-hidden="true"></span><span class="muted">거절 이유</span><button data-do="rejectDuplicate" title="같은 잎에 박스가 여러 개">복수 박스</button><button data-do="rejectMisses" title="박스가 잎 전체를 담지 못함">잎을 다 못 담음</button><button data-do="rejectFalse" title="잎이 아닌 것을 잎으로 표시">오탐</button>
      <span class="sep" aria-hidden="true"></span><button data-do="defer">보류</button><button data-do="undo">되돌리기</button></div>
    <div class="muted">낮게 ← 더 엄격하게, 영역이 작아짐 · 높게 → 더 넓게 포함됨. 50은 모델의 기본 경계값이며 정확도 점수가 아닙니다.</div>
    <div class="row"><label>윤곽 후보 <select id="mbCandidate" aria-label="다른 후보"></select></label>
      <label>겹쳐보기 <input id="mbOpacity" type="range" min="0" max="80" value="35" style="width:100px"></label>
      <label><input id="mbMaskVisible" type="checkbox" checked>마스크 표시</label>
      <button data-do="zoomIn">+ 확대</button><button data-do="zoomOut">− 축소</button><button data-do="fit">확대 맞춤</button></div>
    <p id="mbPreviewStatus" aria-live="polite"></p>
    <div class="row"><button data-do="generate">선택한 잎 초안 생성</button><button data-do="edit">브러시·점·윤곽 수정</button>
      <button data-do="previous">이전 잎</button><button data-do="next">다음 잎</button></div>
  </div>
  <div class="compare">
    <figure><figcaption><label>비교 기준 <select id="mbReference"><option value="saved">저장된 윤곽</option><option value="original">원본 사진</option><option value="20">민감도 20</option><option value="50">민감도 50</option></select></label></figcaption><canvas id="mbReferenceCanvas" width="1000" height="680" aria-label="비교 기준 사진과 윤곽"></canvas><p id="mbReferenceInfo" class="muted"></p></figure>
    <figure><figcaption id="mbPreviewTitle">조절 중인 미리보기</figcaption><canvas id="mbCanvas" width="1000" height="680" tabindex="0" aria-label="미리보기 사진과 윤곽"></canvas><p id="mbCoordinate" class="muted">노란색: 원본 bbox · 초록색: 잎 윤곽</p></figure>
  </div>
  <p id="mbItem"></p><p id="mbCompoundNotice" class="notice" hidden>복엽 상자 안에는 다른 복엽의 잎도 겹칠 수 있습니다. 민감도만으로 소속을 구분할 수 없으므로 후보와 포함·제외점을 함께 확인하세요. 끊긴 부분과 구멍은 자동으로 지우거나 연결하지 않습니다.</p>
  <div id="mbEdit" hidden>
    <div class="row"><label>수정 도구 <select id="mbMode"><option value="pan">화면 이동</option><option value="paint">브러시 칠하기</option><option value="erase">브러시 지우기</option><option value="include">포함점 추가</option><option value="exclude">제외점 추가</option><option value="contour">윤곽 꼭짓점 수정</option></select></label>
      <label>브러시 반지름 <input id="mbBrushSize" type="range" min="1" max="100" value="12" style="width:120px"><span id="mbBrushSizeLabel">12</span> 원본 px</label>
      <button data-do="undoBrush">마지막 붓질 취소</button>
      <button data-do="refine">입력점으로 이 잎 다시 생성</button><button data-do="lastClick">마지막 입력점 취소</button><button data-do="clearClicks">입력점 지우기</button>
      <button data-do="saveContour">윤곽 수정 저장</button><button data-do="deleteVertex">선택 꼭짓점 삭제</button></div>
    <p>오른쪽에서 드래그해 칠하거나 지우고 위쪽 저장 줄의 <b>브러시 수정 저장</b>을 누르세요. 확대해도 반지름은 원본 픽셀 기준입니다. 브러시는 재추론 없이 수정하며 저장 후에도 되돌릴 수 있습니다. 포함·제외점은 재생성에 사용됩니다.</p>
  </div>
  <details><summary>처리·내보내기와 검토 정보</summary><div class="row"><button data-do="start">현재 클래스 전체 생성·재개</button><button data-do="stop">생성 중단</button><button data-do="retry">실패 항목 재시도</button><button data-do="export">현재 클래스 확정 마스크 내보내기</button><button data-do="refresh">목록 새로고침</button><button data-do="legacy">기존 라벨링 화면 펼치기</button></div><p id="mbRisk"></p><p class="muted">모델 점수·검토 순서는 정확도나 자동 정답 판정이 아닙니다. 원본 상자는 보존됩니다. 마스크 확정은 다른 사진의 같은 잎 연결이나 3D 깊이 확정과 별개입니다.</p></details>
  <p class="muted">휠: 페이지 이동 · Ctrl+휠/확대 버튼: 두 화면 함께 확대 · 화면 이동 도구: 끌기. 민감도·후보 미리보기는 재추론 없이 작동합니다.</p>`;
  document.querySelector('header').insertAdjacentElement('afterend',panel);
  const legacyNodes=[document.querySelector('header'),document.getElementById('loadPreparedSession')?.closest('section'),document.getElementById('rebuildLocal')?.closest('section'),...['workflow','setup','app'].map(id=>document.getElementById(id))].filter(Boolean).map(node=>({node,value:node.style.getPropertyValue('display'),priority:node.style.getPropertyPriority('display')}));
  let legacyVisible=false;
  function showLegacy(){for(const e of legacyNodes){if(legacyVisible){if(e.value)e.node.style.setProperty('display',e.value,e.priority);else e.node.style.removeProperty('display');}else e.node.style.setProperty('display','none','important');}}showLegacy();
  const el=id=>panel.querySelector('#'+id),canvas=el('mbCanvas'),ctx=canvas.getContext('2d');
  const referenceCanvas=el('mbReferenceCanvas'),referenceCtx=referenceCanvas.getContext('2d');
  const names={unreviewed:'검토 전',edited:'수정됨·미확정',accepted:'확정',deferred:'보류',rejected:'거절',pending:'생성 대기',running:'생성 중',ready:'계산 완료',failed:'생성 실패'};
  let kind='leaflet',queue=[],current=null,photo=null,maskImage=null,previewImage=null,referenceImage=null,logits=null,busy=false,running=false;
  let previewSensitivity=50,previewCandidate=0,previewTouched=false,previewArea=0,previewFrame=0;
  let displayedPhoto='',displayedFilter='pending';
  const lastActions=[];let view={x:0,y:0,scale:1},rings=[],positive=[],negative=[],clickHistory=[],selectedVertex=null,drag=null,dirty=false;
  let brushStrokes=[],brushCursor=null;
  let activeStart=performance.now(),activeSeconds=0,loadSerial=0;
  document.addEventListener('visibilitychange',()=>{if(document.hidden)activeSeconds+=(performance.now()-activeStart)/1000;else activeStart=performance.now();});
  function elapsed(){const value=activeSeconds+(document.hidden?0:(performance.now()-activeStart)/1000);activeSeconds=0;activeStart=performance.now();return Math.max(0,Math.min(value,1800));}
  function message(text=''){el('mbMessage').textContent=text;}
  function endpoint(path){return '/api/mask-batch/'+path+'?organ_class='+encodeURIComponent(kind);}
  async function api(path,body){const response=await fetch(body===undefined?endpoint(path):'/api/mask-batch/'+path,{method:body===undefined?'GET':'POST',headers:{'X-Local-Token':token,...(body===undefined?{}:{'Content-Type':'application/json'})},body:body===undefined?undefined:JSON.stringify({...body,organ_class:kind})});const data=await response.json();if(!response.ok)throw Error(data.error||'요청을 처리하지 못했습니다');return data;}
  function guard(fn){return async(...args)=>{if(busy)return;busy=true;message('');updateControls();try{await fn(...args);}catch(error){message('처리하지 못했습니다: '+error.message);}finally{busy=false;updateControls();}};}
  function previewDiff(){return !!current&&(previewSensitivity!==current.sensitivity||previewCandidate!==current.selected_candidate);}
  function requireSaved(){if(dirty)throw Error('입력점·윤곽 수정을 저장하거나 되돌리세요.');if(previewTouched&&previewDiff())throw Error('민감도 미리보기를 저장하거나 저장값 복원을 누르세요.');}
  function updateControls(){
    const ready=current?.generation==='ready';
    for(const button of panel.querySelectorAll('button')){const a=button.dataset.do;button.disabled=busy||(running&&!['stop','refresh','fit','zoomIn','zoomOut','next','previous','legacy','s20','s50','restorePreview'].includes(a));
      if((a==='accept'||a==='acceptPartial')&&(!ready||!current.area_px||previewDiff()||dirty))button.disabled=true;
      if(a==='savePreview'&&(!ready||!previewDiff()||dirty))button.disabled=true;
      if(['s20','s50','restorePreview','edit','refine','saveContour','deleteVertex'].includes(a)&&!ready)button.disabled=true;
      if(a==='saveBrush'||a==='undoBrush')button.disabled=busy||running||!brushStrokes.length;
      if(['s20','s50'].includes(a)&&dirty)button.disabled=true;
      if(a==='generate'&&(!current||ready))button.disabled=true;
    }
    for(const id of ['mbClass','mbPhoto','mbQueue','mbFilter','mbMode'])el(id).disabled=busy;
    for(const id of ['mbSensitivity','mbSensitivityNumber','mbCandidate'])el(id).disabled=busy||!logits||dirty;
  }
  function filtered(){const filter=el('mbFilter').value,image=el('mbPhoto').value;return queue.filter(i=>(!image||i.image_file===image)&&(filter==='all'||(filter==='pending'&&!['accepted','rejected'].includes(i.review))||(filter==='failed'?i.generation==='failed':i.review===filter)));}
  function renderQueue(){const selected=current?.id;el('mbQueue').replaceChildren(...filtered().map((i,n)=>{const o=document.createElement('option');o.value=i.id;o.textContent=`${n+1}. ${i.image_file} / 라벨 ${i.id} · ${names[i.review]} · ${names[i.generation]}`;o.selected=i.id===selected;return o;}));}
  async function refresh(){
    const status=await api('status');running=status.job.running;
    el('mbStatus').textContent=`${status.plant_id} · ${kind==='leaflet'?'소엽':'복엽'} ${status.total}개 · 계산 ${status.generation.ready||0}/${status.total} · 확정 ${status.review.accepted||0} · 보류 ${status.review.deferred||0} · 실패 ${status.generation.failed||0}${running?' · 생성 진행 중':''}`;
    const compound=el('mbClass').querySelector('option[value="compoundleaves"]');compound.disabled=!(status.available_classes||[]).includes('compoundleaves');
    if(status.job.error)message('생성 작업 오류: '+status.job.error);
    queue=(await api('queue')).items;const selected=el('mbPhoto').value;
    el('mbPhoto').replaceChildren(new Option('전체 사진',''),...[...new Set(queue.map(i=>i.image_file))].sort().map(name=>new Option(name,name)));
    el('mbPhoto').value=[...el('mbPhoto').options].some(o=>o.value===selected)?selected:'';
    displayedPhoto=el('mbPhoto').value;
    renderQueue();updateControls();
  }
  async function imageFromURL(url){const picture=new Image();picture.src=url;await picture.decode();return picture;}
  function overlay(mask,width,height){const off=document.createElement('canvas');off.width=width;off.height=height;const oc=off.getContext('2d'),rgba=oc.createImageData(width,height);for(let i=0;i<mask.length;i++){const j=i*4;rgba.data[j]=45;rgba.data[j+1]=240;rgba.data[j+2]=100;rgba.data[j+3]=mask[i]?255:0;}oc.putImageData(rgba,0,0);return off;}
  async function load(id,fit=true,preserveChoice=false){
    const keepSensitivity=previewSensitivity,keepCandidate=previewCandidate;
    if(!id){current=null;photo=null;logits=null;maskImage=null;previewImage=null;referenceImage=null;el('mbItem').textContent='선택한 조건에 해당하는 잎이 없습니다.';el('mbPreviewStatus').textContent='';el('mbReferenceInfo').textContent='';el('mbPreviewTitle').textContent='미리보기';draw();updateControls();return;}
    const serial=++loadSerial,item=await api('item/'+encodeURIComponent(id));let picture=null,saved=null,data=null;
    try{picture=await imageFromURL('/'+item.image_path.split('/').map(encodeURIComponent).join('/'));}catch(error){message('원본 사진을 불러오지 못했습니다.');}
    if(item.generation==='ready'){
      const [maskResponse,scoreResponse]=await Promise.all([fetch(endpoint('mask/'+encodeURIComponent(id)),{headers:{'X-Local-Token':token}}),fetch(endpoint('logits/'+encodeURIComponent(id)),{headers:{'X-Local-Token':token}})]);
      if(!maskResponse.ok||!scoreResponse.ok)throw Error('저장된 윤곽 점수를 불러오지 못했습니다. 새로고침하세요.');
      const bytes=await scoreResponse.arrayBuffer(),head=new DataView(bytes),n=head.getUint32(0,true),h=head.getUint32(4,true),w=head.getUint32(8,true),revision=head.getUint32(12,true);
      if(revision!==item.revision||bytes.byteLength!==16+n*h*w*4)throw Error('다른 작업에서 항목이 바뀌었습니다. 다시 선택하세요.');
      data={scores:new Float32Array(bytes,16),n,h,w};const url=URL.createObjectURL(await maskResponse.blob());
      try{const raw=await imageFromURL(url),off=document.createElement('canvas');off.width=raw.width;off.height=raw.height;const oc=off.getContext('2d');oc.drawImage(raw,0,0);const rgba=oc.getImageData(0,0,off.width,off.height);const bits=new Uint8Array(off.width*off.height);for(let i=0;i<bits.length;i++)bits[i]=rgba.data[i*4]?1:0;saved=overlay(bits,off.width,off.height);}finally{URL.revokeObjectURL(url);}
    }
    if(serial!==loadSerial)return;
    current=item;photo=picture;maskImage=saved;logits=data;rings=structuredClone(item.rings||[]);positive=structuredClone(item.prompts.positive_px);negative=structuredClone(item.prompts.negative_px);clickHistory=[];dirty=false;selectedVertex=null;previewTouched=false;brushStrokes=[];brushCursor=null;
    previewCandidate=preserveChoice?keepCandidate:item.selected_candidate;
    previewSensitivity=preserveChoice?keepSensitivity:(item.review==='unreviewed'&&!item.manual_rings?50:item.sensitivity);
    if(!data){previewCandidate=item.selected_candidate;previewSensitivity=item.sensitivity;}
    activeStart=performance.now();activeSeconds=0;
    el('mbCandidate').replaceChildren(...(item.result?.scores||[]).map((score,index)=>new Option(`후보 ${index+1} · 모델 점수 ${score===null?'없음':score.toFixed(3)}`,index)));
    el('mbItem').textContent=`${item.image_file} · 원본 라벨 ${item.source_annotation_id} · ${names[item.review]} · 저장 민감도 ${item.sensitivity}${item.error?' · '+item.error:''}`;
    el('mbCompoundNotice').hidden=kind!=='compoundleaves';
    const risk=item.result?.risk;el('mbRisk').textContent=risk?`초기 초안 참고: 분리 영역 ${risk.components}개 · 구멍 ${risk.holes}개 · bbox 밖 ${(risk.outside_bbox_fraction*100).toFixed(1)}% · 주변 윤곽과 겹침 ${((risk.neighbor_overlap_max||0)*100).toFixed(1)}%. 후보 간 차이는 서로 다른 분할 범위의 영향을 받아 우선순위의 확실한 근거가 아닙니다.`:'';
    updatePreview();if(fit)fitView();renderQueue();updateControls();
  }
  function updatePreview(touched=false){
    previewTouched=previewTouched||touched;el('mbSensitivity').value=previewSensitivity;el('mbSensitivityNumber').value=previewSensitivity;el('mbCandidate').value=previewCandidate;
    if(!current||!logits){previewImage=null;referenceImage=null;previewArea=0;el('mbPreviewStatus').textContent=current?'아직 윤곽 점수가 없습니다. 선택한 잎 초안 생성을 누르세요.':'';el('mbReferenceInfo').textContent='원본 사진 · bbox만 표시';el('mbPreviewTitle').textContent='초안 생성 대기';draw();updateControls();return;}
    const make=s=>MaskPreviewMath.raster(logits.scores,logits.n,logits.h,logits.w,previewCandidate,s);
    if(!previewDiff()){previewImage=maskImage;previewArea=current.area_px;}else{const result=make(previewSensitivity);previewImage=overlay(result.mask,logits.w,logits.h);previewArea=result.area;}
    if(brushStrokes.length)renderBrush();
    const ref=el('mbReference').value;
    if(ref==='saved'){referenceImage=maskImage;el('mbReferenceInfo').textContent=`저장 민감도 ${current.sensitivity} · 후보 ${current.selected_candidate+1} · ${current.area_px.toLocaleString()} 픽셀${current.manual_rings?' · 수동 윤곽 포함':''}`;}
    else if(ref==='original'){referenceImage=null;el('mbReferenceInfo').textContent='원본 사진 · bbox만 표시';}
    else{const result=make(Number(ref));referenceImage=overlay(result.mask,logits.w,logits.h);el('mbReferenceInfo').textContent=`민감도 ${ref} · 후보 ${previewCandidate+1} · ${result.area.toLocaleString()} 픽셀 · 비교용`;} 
    el('mbPreviewTitle').textContent=`미리보기 · 민감도 ${previewSensitivity} · 후보 ${previewCandidate+1}`;
    el('mbPreviewStatus').textContent=`${previewDiff()?'미저장 미리보기':'저장된 설정'} · 영역 ${previewArea.toLocaleString()} 픽셀${previewArea===0?' · 빈 윤곽: 민감도/후보를 바꾸거나 점으로 수정하세요.':''}${previewDiff()&&current.manual_rings?' · 저장하면 기존 수동 윤곽 수정이 교체됩니다. 되돌리기로 복원할 수 있습니다.':''}`;
    draw();updateControls();
  }
  function schedulePreview(){if(previewFrame)cancelAnimationFrame(previewFrame);previewFrame=requestAnimationFrame(()=>{previewFrame=0;updatePreview(true);});}
  function fitView(){if(!current)return;const c=current.result?.crop_px||(()=>{const[x,y,w,h]=current.source_bbox_xywh_px;return [Math.max(0,x-w*.3),Math.max(0,y-h*.3),Math.min(current.image_size_px[0],x+w*1.3),Math.min(current.image_size_px[1],y+h*1.3)];})();view.scale=Math.min(canvas.width/(c[2]-c[0]),canvas.height/(c[3]-c[1]))*.94;view.x=(c[0]+c[2])/2;view.y=(c[1]+c[3])/2;draw();}
  function toCanvas(p){return[(p[0]-view.x)*view.scale+canvas.width/2,(p[1]-view.y)*view.scale+canvas.height/2];}
  function eventPoint(event){const r=event.currentTarget.getBoundingClientRect();return[(event.clientX-r.left)*canvas.width/r.width,(event.clientY-r.top)*canvas.height/r.height];}
  function toOriginal(p){return[(p[0]-canvas.width/2)/view.scale+view.x,(p[1]-canvas.height/2)/view.scale+view.y];}
  function drawOne(c,mask,right){c.clearRect(0,0,canvas.width,canvas.height);if(!photo||!current)return;c.save();c.translate(canvas.width/2,canvas.height/2);c.scale(view.scale,view.scale);c.translate(-view.x,-view.y);c.drawImage(photo,0,0);if(mask&&el('mbMaskVisible').checked){c.globalAlpha=Number(el('mbOpacity').value)/100;c.drawImage(mask,...current.result.crop_px.slice(0,2));c.globalAlpha=1;}
    const[x,y,w,h]=current.source_bbox_xywh_px;c.strokeStyle='#ffe052';c.lineWidth=2/view.scale;c.strokeRect(x,y,w,h);
    if(right&&!previewDiff()&&el('mbMode').value==='contour'){c.strokeStyle='#51ff98';c.lineWidth=1/view.scale;for(const ring of rings){c.beginPath();ring.points_px.forEach((p,i)=>i?c.lineTo(...p):c.moveTo(...p));c.closePath();c.stroke();}}c.restore();}
  function draw(){drawOne(referenceCtx,referenceImage,false);drawOne(ctx,previewImage,true);if(!photo||!current)return;const point=(p,color,radius=5)=>{ctx.fillStyle=color;ctx.beginPath();ctx.arc(...toCanvas(p),radius,0,Math.PI*2);ctx.fill();ctx.strokeStyle='black';ctx.lineWidth=1;ctx.stroke();};positive.forEach(p=>point(p,'#38baff'));negative.forEach(p=>point(p,'#ff4e69'));if(el('mbMode').value==='contour'&&!previewDiff())rings.forEach((r,ri)=>r.points_px.forEach((p,vi)=>point(p,selectedVertex?.[0]===ri&&selectedVertex?.[1]===vi?'#ffdf3e':'#fff',3)));}
  function drawBrushCursor(){if(!brushCursor||!['paint','erase'].includes(el('mbMode').value))return;ctx.strokeStyle=el('mbMode').value==='erase'?'#ff4e69':'white';ctx.lineWidth=2;ctx.beginPath();ctx.arc(...toCanvas(brushCursor),Number(el('mbBrushSize').value)*view.scale,0,2*Math.PI);ctx.stroke();}
  function renderBrush(){if(!maskImage)return;const off=document.createElement('canvas');off.width=maskImage.width;off.height=maskImage.height;const c=off.getContext('2d');c.drawImage(maskImage,0,0);const crop=current.result.crop_px;for(const s of brushStrokes){c.globalCompositeOperation=s.mode==='erase'?'destination-out':'source-over';c.strokeStyle=c.fillStyle='#2df064';c.lineWidth=s.radius_px*2;c.lineCap=c.lineJoin='round';c.beginPath();s.points_px.forEach((p,i)=>i?c.lineTo(p[0]-crop[0],p[1]-crop[1]):c.moveTo(p[0]-crop[0],p[1]-crop[1]));c.stroke();for(const p of [s.points_px[0],s.points_px.at(-1)]){c.beginPath();c.arc(p[0]-crop[0],p[1]-crop[1],s.radius_px,0,2*Math.PI);c.fill();}}previewImage=off;el('mbPreviewStatus').textContent=`미저장 브러시 수정 · ${brushStrokes.length}회 · 브러시 수정 저장을 누르세요`; }
  async function review(action,extra={}){if(brushStrokes.length&&['refine','contour'].includes(action))throw Error('브러시 수정을 먼저 저장하세요.');if(!current)throw Error('먼저 잎을 선택하세요.');if(dirty&&['select','accept','defer','reject'].includes(action))throw Error('입력점·윤곽 수정을 먼저 저장하세요.');const saved=await api('review',{id:current.id,revision:current.revision,action,active_seconds:elapsed(),...extra});window.dispatchEvent(new Event('mask-review-saved'));if(action!=='undo')lastActions.push({id:saved.id,revision:saved.revision,kind});await load(saved.id,false,true);previewSensitivity=saved.sensitivity;previewCandidate=saved.selected_candidate;previewTouched=false;updatePreview();await refresh();}
  async function undoSaved(){if(brushStrokes.length){brushStrokes.pop();dirty=brushStrokes.length>0;updatePreview();return;}if(dirty||previewTouched&&previewDiff()){await load(current.id,false);previewSensitivity=current.sensitivity;previewCandidate=current.selected_candidate;updatePreview();return;}window.dispatchEvent(new Event('mask-review-saved'));const target=lastActions.at(-1);if(!target){await review('undo');return;}const saved=await api('review',{id:target.id,revision:target.revision,action:'undo',active_seconds:elapsed()});lastActions.pop();lastActions.forEach(e=>{if(e.id===saved.id)e.revision=saved.revision;});await load(saved.id);previewSensitivity=saved.sensitivity;previewCandidate=saved.selected_candidate;updatePreview();await refresh();}
  async function next(direction=1,id=current?.id){const available=filtered();if(!available.length){await load(null);return;}const index=available.findIndex(i=>i.id===id);await load(available[index<0?0:(index+direction+available.length)%available.length].id);}
  panel.addEventListener('click',event=>{const a=event.target.closest('button')?.dataset.do;if(!a)return;guard(async()=>{if(brushStrokes.length&&['refine','saveContour','clearClicks','lastClick','deleteVertex'].includes(a))throw Error('브러시 수정을 먼저 저장하세요.');
    if(a==='s20'||a==='s50'){previewSensitivity=a==='s20'?20:50;updatePreview(true);}
    else if(a==='savePreview'){await review('select',{sensitivity:previewSensitivity,candidate:previewCandidate});message('미리보기 설정을 저장했습니다. 아직 확정 전입니다.');}
    else if(a==='restorePreview'){previewSensitivity=current.sensitivity;previewCandidate=current.selected_candidate;previewTouched=false;updatePreview();}
    else if(a==='generate'||a==='start'||a==='retry'){requireSaved();await api('start',{retry_failed:a!=='start',...(a==='generate'?{id:current.id}:{})});await refresh();message('초안 생성 중입니다. 민감도 미리보기는 점수 생성이 끝난 뒤 사용할 수 있습니다.');}
    else if(a==='stop'){await api('stop',{});message('현재 잎 계산 후 중단합니다.');}
    else if(a==='refresh'){requireSaved();await refresh();if(current)await load(current.id,false);}
    else if(a==='legacy'){legacyVisible=!legacyVisible;showLegacy();event.target.textContent=legacyVisible?'기존 라벨링 화면 접기':'기존 라벨링 화면 펼치기';}
    else if(a==='export'){requireSaved();const r=await api('export',{});message(`${r.count}개 확정 마스크 저장: ${r.path}`);}
    else if(a==='fit')fitView();
    else if(a==='zoomIn'||a==='zoomOut'){view.scale=Math.max(.05,Math.min(12,view.scale*(a==='zoomIn'?1.25:.8)));draw();}
    else if(a==='edit'){if(previewDiff())throw Error('미리보기를 저장하거나 저장값 복원 후 점·윤곽을 수정하세요.');el('mbEdit').hidden=false;el('mbMode').value='paint';draw();}
    else if(a==='next'||a==='previous'){requireSaved();await next(a==='next'?1:-1);}
    else if(['accept','defer','reject'].includes(a)){requireSaved();if(a==='accept'&&previewDiff())throw Error('미리보기를 먼저 저장하세요.');const id=current?.id;await review(a);await next(1,id);}
    else if(a==='acceptPartial'){requireSaved();if(previewDiff())throw Error('미리보기를 먼저 저장하세요.');const id=current?.id;await review('accept',{visibility:'partial'});await next(1,id);}
    else if(['rejectDuplicate','rejectMisses','rejectFalse'].includes(a)){requireSaved();const id=current?.id;await review('reject',{reason:{rejectDuplicate:'duplicate_box',rejectMisses:'box_misses_leaf',rejectFalse:'false_positive'}[a]});await next(1,id);}
    else if(a==='undo')await undoSaved();
    else if(a==='refine'){if(brushStrokes.length)throw Error('브러시 수정을 먼저 저장하세요.');await review('refine',{positive_px:positive,negative_px:negative});}
    else if(a==='clearClicks'){positive=[];negative=[];clickHistory=[];dirty=true;draw();}
    else if(a==='lastClick'){const type=clickHistory.pop();if(type==='include')positive.pop();if(type==='exclude')negative.pop();dirty=true;draw();}
    else if(a==='saveBrush')await review('brush',{strokes:brushStrokes});
    else if(a==='undoBrush'){brushStrokes.pop();dirty=brushStrokes.length>0;updatePreview();}
    else if(a==='saveContour'){if(brushStrokes.length)throw Error('브러시 수정을 먼저 저장하세요.');await review('contour',{rings});}
    else if(a==='deleteVertex'){if(!selectedVertex)throw Error('윤곽 점을 먼저 선택하세요.');const[ri,vi]=selectedVertex;if(rings[ri].points_px.length<=3)throw Error('윤곽에는 최소 3점이 필요합니다.');rings[ri].points_px.splice(vi,1);selectedVertex=null;dirty=true;draw();}
  })();});
  el('mbClass').addEventListener('change',guard(async()=>{const selected=el('mbClass').value;try{requireSaved();}catch(e){el('mbClass').value=kind;throw e;}kind=selected;current=null;lastActions.length=0;el('mbPhoto').value='';el('mbEdit').hidden=true;el('mbMode').value='pan';await refresh();await load(el('mbQueue').value);}));
  el('mbQueue').addEventListener('change',guard(async()=>{try{requireSaved();}catch(e){el('mbQueue').value=current?.id;throw e;}await load(el('mbQueue').value);}));
  for(const id of ['mbFilter','mbPhoto'])el(id).addEventListener('change',guard(async()=>{try{requireSaved();}catch(error){el('mbPhoto').value=displayedPhoto;el('mbFilter').value=displayedFilter;throw error;}displayedPhoto=el('mbPhoto').value;displayedFilter=el('mbFilter').value;renderQueue();await load(el('mbQueue').value);}));
  el('mbCandidate').addEventListener('change',()=>{previewCandidate=Number(el('mbCandidate').value);updatePreview(true);});
  el('mbSensitivity').addEventListener('input',()=>{previewSensitivity=Number(el('mbSensitivity').value);el('mbSensitivityNumber').value=previewSensitivity;schedulePreview();});
  el('mbSensitivityNumber').addEventListener('input',()=>{const n=Number(el('mbSensitivityNumber').value);if(el('mbSensitivityNumber').value!==''&&Number.isInteger(n)&&n>=0&&n<=100){previewSensitivity=n;el('mbSensitivity').value=n;schedulePreview();}});
  function validateSensitivityInput(){const value=el('mbSensitivityNumber').value,n=Number(value);if(value===''||!Number.isInteger(n)||n<0||n>100){el('mbSensitivityNumber').value=previewSensitivity;message('민감도는 0부터 100까지의 정수로 입력하세요. 직전 미리보기 값을 유지했습니다.');}}
  el('mbSensitivityNumber').addEventListener('change',validateSensitivityInput);
  el('mbSensitivityNumber').addEventListener('blur',validateSensitivityInput);
  el('mbBrushSize').addEventListener('input',()=>{el('mbBrushSizeLabel').textContent=el('mbBrushSize').value;});
  el('mbReference').addEventListener('change',()=>updatePreview());el('mbOpacity').addEventListener('input',draw);el('mbMaskVisible').addEventListener('change',draw);el('mbMode').addEventListener('change',draw);
  document.addEventListener('keydown',event=>{if(!panel.contains(event.target))return;event.stopPropagation();if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='z'&&!['INPUT','TEXTAREA'].includes(event.target.tagName)){event.preventDefault();panel.querySelector('[data-do="undo"]').click();}},true);
  window.addEventListener('beforeunload',event=>{if(dirty||previewTouched&&previewDiff()){event.preventDefault();event.returnValue='';}});
  function inCrop(p){const c=current.result?.crop_px||[0,0,...current.image_size_px];return[Math.max(c[0],Math.min(c[2]-1,p[0])),Math.max(c[1],Math.min(c[3]-1,p[1]))];}
  function nearestVertex(p){let found=null,distance=12;for(let ri=0;ri<rings.length;ri++)for(let vi=0;vi<rings[ri].points_px.length;vi++){const q=toCanvas(rings[ri].points_px[vi]),d=Math.hypot(q[0]-p[0],q[1]-p[1]);if(d<distance){distance=d;found=[ri,vi];}}return found;}
  for(const surface of [canvas,referenceCanvas]){
    surface.addEventListener('pointerdown',event=>{if(!current||busy)return;surface.focus();const p=eventPoint(event),xy=toOriginal(p),mode=surface===canvas?el('mbMode').value:'pan';
      if(mode!=='pan'&&(running||previewDiff())){message('미리보기를 저장하거나 저장값 복원 후 수정하세요.');return;}
      if(brushStrokes.length&&!['paint','erase','pan'].includes(mode)){message('브러시 수정을 먼저 저장하세요.');return;}
      if(mode==='paint'||mode==='erase'){if(dirty&&!brushStrokes.length){message('입력점·윤곽 수정을 먼저 저장하세요.');return;}const q=inCrop(xy);if(q.some((v,i)=>v!==xy[i]))return;brushStrokes.push({mode,radius_px:Number(el('mbBrushSize').value),points_px:[q]});drag={brush:true};dirty=true;renderBrush();draw();updateControls();surface.setPointerCapture(event.pointerId);return;}
      if(mode==='include'||mode==='exclude'){const[w,h]=current.image_size_px;if(xy[0]<0||xy[1]<0||xy[0]>=w||xy[1]>=h)return;(mode==='include'?positive:negative).push(xy);clickHistory.push(mode);dirty=true;el('mbCoordinate').textContent=`원본 x=${xy[0].toFixed(2)}, y=${xy[1].toFixed(2)} 픽셀`;draw();updateControls();return;}
      if(mode==='contour'){selectedVertex=nearestVertex(p);if(selectedVertex)drag={vertex:selectedVertex};draw();}else drag={point:p,x:view.x,y:view.y};if(drag)surface.setPointerCapture(event.pointerId);
    });
    surface.addEventListener('pointermove',event=>{const p=eventPoint(event);if(surface===canvas&&current&&['paint','erase'].includes(el('mbMode').value)){brushCursor=toOriginal(p);}if(!drag){if(brushCursor){draw();drawBrushCursor();}return;}if(drag.brush){const stroke=brushStrokes.at(-1),q=inCrop(toOriginal(p));if(Math.hypot(q[0]-stroke.points_px.at(-1)[0],q[1]-stroke.points_px.at(-1)[1])>=.5)stroke.points_px.push(q);renderBrush();draw();drawBrushCursor();return;}if(drag.vertex){const[ri,vi]=drag.vertex;rings[ri].points_px[vi]=inCrop(toOriginal(p));dirty=true;updateControls();}else{view.x=drag.x-(p[0]-drag.point[0])/view.scale;view.y=drag.y-(p[1]-drag.point[1])/view.scale;}draw();});
    surface.addEventListener('pointerleave',()=>{brushCursor=null;if(!drag)draw();});
    surface.addEventListener('pointerup',()=>drag=null);surface.addEventListener('pointercancel',()=>drag=null);
    surface.addEventListener('wheel',event=>{if(!current||(!event.ctrlKey&&!event.metaKey))return;event.preventDefault();const p=eventPoint(event),before=toOriginal(p);view.scale=Math.max(.05,Math.min(12,view.scale*Math.exp(-event.deltaY*.0015)));const after=toOriginal(p);view.x+=before[0]-after[0];view.y+=before[1]-after[1];draw();},{passive:false});
  }
  canvas.addEventListener('dblclick',event=>{if(!current||busy||running||previewDiff()||el('mbMode').value!=='contour')return;const p=eventPoint(event);let nearest=null,distance=15;rings.forEach((r,ri)=>r.points_px.forEach((a,vi)=>{const b=r.points_px[(vi+1)%r.points_px.length],u=toCanvas(a),v=toCanvas(b),dx=v[0]-u[0],dy=v[1]-u[1],t=Math.max(0,Math.min(1,((p[0]-u[0])*dx+(p[1]-u[1])*dy)/(dx*dx+dy*dy||1))),d=Math.hypot(p[0]-u[0]-t*dx,p[1]-u[1]-t*dy);if(d<distance){distance=d;nearest=[ri,vi];}}));if(nearest){const[ri,vi]=nearest;rings[ri].points_px.splice(vi+1,0,inCrop(toOriginal(p)));selectedVertex=[ri,vi+1];dirty=true;draw();updateControls();}});
  window.__maskBatchReview={requireSaved};
  guard(async()=>{await refresh();await load(el('mbQueue').value);})();
  setInterval(()=>{if(!busy&&running)guard(async()=>{await refresh();const queued=queue.find(i=>i.id===current?.id);if(queued&&queued.revision!==current.revision&&!dirty&&!previewTouched)await load(current.id,false);})();},1500);
})();
