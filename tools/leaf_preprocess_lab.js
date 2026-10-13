'use strict';
// Independent UI: saves derived selections only. No editor or reconstruction calls.
const payload = window.LAB;
const el = id => document.getElementById(id);
const keys = ['ev', 'gamma', 'clahe', 'denoise', 'width'];
let revision = 0, timer = null, rendered = null, saved = null;
let midribAnchors=[], midribResult=null, midribRevision=0, midribImages={}, midribSaved=null;
const sample = () => payload.samples.find(s => s.id === el('sample').value);
const config = () => el('protocol').value === 'study'
 ? {...payload.defaults, protocol:'study', smoothing:el('smoothing').value, tone:el('tone').value, channel:el('channel').value}
 : Object.fromEntries([...keys.map(k => [k, Number(el(k).value)]), ['feature', el('feature').value], ['protocol','legacy']]);
const signature = () => JSON.stringify([el('sample').value, config()]);

async function api(route, body) {
  const response = await fetch(route, {method: 'POST', headers: {'Content-Type': 'application/json', 'X-Lab-Token': payload.token}, body: JSON.stringify(body)});
  const data = await response.json();
  if (!response.ok) throw new Error(data.error || '처리하지 못했습니다.');
  return data;
}

function labels() {
  for (const k of keys) el(k + 'Value').textContent = Number(el(k).value).toFixed(['gamma','ev'].includes(k) ? 2 : 1);
}
function invalidate() {
  invalidateMidrib(false);
  revision++; rendered = null; el('save').disabled = true;
  el('status').textContent = '현재 설정으로 비교하고 있습니다…'; el('status').classList.remove('error');
  clearTimeout(timer); labels();
  timer = setTimeout(render, 230);
}
function views() {
  if (!rendered) return;
  el('original').src = rendered.images[el('showMask').checked ? 'mask' : 'original'];
  el('processed').src = rendered.images.processed;
  el('analysis').src = rendered.images[el('thirdMode').value] || rendered.images.original;
  el('analysisCaption').textContent = el('thirdMode').value === 'ratio'
    ? '원본 RGB의 채널 비율을 표시합니다. 회색은 마스크 밖 또는 밝기 근거가 부족한 영역입니다.'
    : '주황색은 선 후보입니다. 주름·그림자가 섞일 수 있으며 주맥 확정 결과가 아닙니다.';
  if (el('protocol').value === 'study') el('analysisCaption').textContent = '수치 지도는 모든 평활화 조건의 공통 잎 내부만 비교합니다. 회색은 경계·구멍·무효 영역, 차이 영상은 4배 표시이며 정확도 점수가 아닙니다.';
  if (el('thirdMode').value.startsWith('model')) el('analysisCaption').textContent = rendered.images[el('thirdMode').value] ? '고정 모델의 실제 실행 결과입니다. 마스크는 자동 예측이며 검토 정답과 구분합니다.' : '아직 이 조건의 모델 결과가 없습니다. 원본을 표시하며, 이 화면에서 자동 추론하지 않습니다.';
}
async function render() {
  const version = ++revision, sig = signature(), item = sample();
  el('save').disabled = true; document.body.classList.add('busy');
  try {
    const data = await api('/api/render', {sample_id: item.id, settings: config()});
    if (version !== revision || sig !== signature()) return;
    rendered = {...data, signature: sig}; views();
    previewMidrib();
    const s = data.stats, pct = x => x.toFixed(1) + '%';
    el('clipped').textContent = pct(s.source_clipped_percent) + ' → ' + pct(s.processed_clipped_percent);
    el('dark').textContent = pct(s.source_dark_percent) + ' → ' + pct(s.processed_dark_percent);
    el('valid').textContent = pct(s.usable_line_region_percent);
    el('contrast').textContent = s.local_contrast_std.toFixed(4);
    el('studyStats').textContent = s.scalar_common_percent === undefined ? '' : `수치 지도 공통 영역 ${pct(s.scalar_common_percent)} · 0–1 밖 값 ${s.scalar_overshoot_percent === null ? '미산출' : pct(s.scalar_overshoot_percent)} · 선 후보의 내부 Gaussian σ=1,2,3px 고정`; 
    el('status').textContent = s.usable_line_region_percent < 10 ? '선 분석에 쓸 수 있는 영역이 적습니다. 원본과 마스크를 먼저 확인하세요.' : '비교 준비 완료 · 주맥과 잎맥 분기점이 더 잘 보이는지 살펴보세요.';
    el('save').disabled = false;
  } catch (error) {
    if (version === revision) { el('status').textContent = error.message; el('status').classList.add('error'); }
  } finally {
    if (version === revision) document.body.classList.remove('busy');
  }
}

for (const s of payload.samples) {
  const option = document.createElement('option'); option.value = s.id;
  option.textContent = `${s.plant_id} · ${s.view_group === 'side' ? '측면' : '사선'} · ${s.image_file.replace('.png', '').split('_').pop()}번 사진 · 라벨 ${s.source_annotation_id}`;
  el('sample').append(option);
}
for (const p of payload.presets) {
  const button = document.createElement('button'); button.textContent = p.label; button.dataset.preset = p.id;
  button.addEventListener('click', () => {
    for (const [k, v] of Object.entries(p.settings)) if (el(k)) el(k).value = v; syncProtocol();
    document.querySelectorAll('[data-preset]').forEach(b => b.classList.toggle('active', b === button)); invalidate();
  });
  el('presets').append(button);
}
function fullView() {
  const on = el('fullToggle').getAttribute('aria-pressed') === 'true', s = sample();
  el('fullPanel').hidden = !on;
  document.querySelector('.layout').style.display = on ? 'none' : '';
  el('fullToggle').textContent = on ? '소엽 비교로 돌아가기' : '전체 사진 보기';
  const [x0,y0,x1,y1] = s.crop_xyxy_px;
  el('sampleMeta').textContent = on ? `${payload.samples.indexOf(s)+1} / ${payload.samples.length} · 전체 원본` : `${payload.samples.indexOf(s)+1} / ${payload.samples.length} · ${x1-x0} × ${y1-y0}px · 검토된 소엽 마스크`;
  if (on) {
    el('fullImage').src = '/source/' + encodeURIComponent(s.id) + '?mode=' + el('fullMode').value + '&mask=' + (el('fullMask').checked ? 'reviewed' : 'none') + '&smoothing=' + el('smoothing').value + '&tone=' + el('tone').value;
    const channel = {red:'R', green:'G', blue:'B'}[el('fullMode').value];
    el('fullCaption').textContent = channel ? `전체 원본 RGB 값으로 ${channel}/(R+G+B)를 계산합니다. 검정=0, 흰색=1, 무채색 물체≈0.333. 자홍색은 R+G+B=0으로 계산 불가입니다. 마스크·자르기·감마 보정 없음. 밝을수록 ${channel} 비율이 높으며 탐지 정확도가 아닙니다.` : '전체 원본 사진입니다. 마스크·자르기·밝기 보정 없음.';
    if (el('fullMask').checked) el('fullCaption').textContent = el('fullCaption').textContent.replace('마스크·자르기·감마 보정 없음.', '선택한 소엽의 기존 마스크만 적용; 자르기·감마 보정 없음.').replace('마스크·자르기·밝기 보정 없음.', '선택한 소엽의 기존 마스크만 적용; 자르기·밝기 보정 없음.') + ' 마스크 밖은 투명합니다. 전체 식물 마스크나 새 자동 탐지 결과가 아닙니다.';
    if (el('smoothing').value !== 'none' || el('fullMode').value === 'processed') el('fullCaption').textContent = '현재 평활화 조건: '+el('smoothing').selectedOptions[0].text+' · RGB 처리 사진의 밝기 조건: '+el('tone').selectedOptions[0].text+'. 비율 지도에는 밝기 조건이 적용되지 않습니다. 마스크는 필터 처리 후 표시합니다.';
    el('fullMeta').textContent = `${s.image_file} · ${s.original_size_px.join(' × ')}px · 라벨 ${s.source_annotation_id}`;
  }
}
el('fullMode').onchange = fullView;
el('fullMask').onchange = fullView;
el('fullToggle').onclick = () => {
  el('fullToggle').setAttribute('aria-pressed', el('fullToggle').getAttribute('aria-pressed') === 'true' ? 'false' : 'true'); fullView();
};
function changedSample() {
  invalidateMidrib(true);
  const s = sample(), [x0,y0,x1,y1] = s.crop_xyxy_px;
  el('sampleMeta').textContent = `${payload.samples.indexOf(s)+1} / ${payload.samples.length} · ${x1-x0} × ${y1-y0}px · 검토된 소엽 마스크`;
  el('verdict').value = 'unreviewed'; el('note').value = '';
  el('saveStatus').textContent = '현재 소엽의 비교 결과를 별도로 저장합니다.';
  fullView(); invalidate();
}
el('sample').addEventListener('change', changedSample);
for (const [id, step] of [['prev', -1], ['next', 1]]) el(id).onclick = () => {
  el('sample').selectedIndex = (el('sample').selectedIndex + step + payload.samples.length) % payload.samples.length; el('sample').dispatchEvent(new Event('change'));
};
for (const k of [...keys, 'feature']) el(k).addEventListener('input', () => {
  document.querySelectorAll('[data-preset]').forEach(b => b.classList.remove('active')); invalidate();
});
el('showMask').onchange = views; el('thirdMode').onchange = views;
el('zoom').oninput = () => {
  const z = Number(el('zoom').value); el('zoomValue').textContent = z+'%';
  document.querySelectorAll('.viewport img').forEach(img => img.style.width = z+'%');
};
let scrolling = false;
document.querySelectorAll('.viewport').forEach(box => box.addEventListener('scroll', () => {
  if (scrolling) return; scrolling = true;
  document.querySelectorAll('.viewport').forEach(other => { if (other !== box) {other.scrollTop = box.scrollTop; other.scrollLeft = box.scrollLeft;} });
  requestAnimationFrame(() => scrolling = false);
}));
document.querySelectorAll('.viewport img').forEach(img => img.addEventListener('mousemove', event => {
  if (!rendered) return;
  const rect = img.getBoundingClientRect(), s = sample(), [x0,y0,x1,y1] = s.crop_xyxy_px;
  const x = Math.min(x1-1, x0 + Math.floor((event.clientX - rect.left) / rect.width * (x1-x0)));
  const y = Math.min(y1-1, y0 + Math.floor((event.clientY - rect.top) / rect.height * (y1-y0)));
  el('coord').textContent = `원본 좌표 x=${x}, y=${y}px · 깊이와 대응점은 아직 지정하지 않았습니다.`;
}));
el('save').onclick = async () => {
  if (!rendered || rendered.signature !== signature()) return;
  const sid = el('sample').value, cfg = {...rendered.settings};
  el('save').disabled = true; el('saveStatus').textContent = '새 결과 폴더에 저장 중…';
  try {
    const response = await api('/api/save', {sample_id:sid, settings:cfg, verdict:el('verdict').value, note:el('note').value});
    saved = response.record; el('download').disabled = false;
    el('saveStatus').textContent = `${payload.samples.find(s=>s.id===sid).observation_id} 저장 완료 · ${response.relative_path}`;
  } catch (error) { el('saveStatus').textContent = '저장 실패: ' + error.message; }
  finally { el('save').disabled = !rendered || rendered.signature !== signature(); }
};
el('download').onclick = () => {
  if (!saved) return;
  const url = URL.createObjectURL(new Blob([JSON.stringify(saved,null,2)], {type:'application/json'}));
  const a = document.createElement('a'); a.href=url; a.download=`${saved.observation.observation_id}_preprocess_selection.json`; a.click();
  setTimeout(()=>URL.revokeObjectURL(url),1000);
};
const requested = new URLSearchParams(location.search);
const chosen = payload.samples.find(s => String(s.source_annotation_id) === requested.get('annotation'));
if (chosen) el('sample').value = chosen.id;
if (['red','green','blue','original'].includes(requested.get('mode'))) el('fullMode').value = requested.get('mode');
el('fullMask').checked = requested.get('mask') === 'reviewed';
if (requested.get('full') === '1') el('fullToggle').setAttribute('aria-pressed', 'true');
function syncProtocol() {
 const study=el('protocol').value==='study'; el('studyControls').hidden=!study; el('legacyControls').hidden=study;
 el('width').disabled=study; el('feature').disabled=study;
 for (const op of el('thirdMode').options) op.disabled=!study && ['scalar_before','difference'].includes(op.value);
 if (!study && ['scalar_before','difference'].includes(el('thirdMode').value)) el('thirdMode').value='overlay';
}
for (const k of ['protocol','smoothing','tone','channel']) el(k).onchange=()=>{syncProtocol(); invalidate();fullView();};
syncProtocol(); labels(); changedSample();

function midribOptions() {
 return {channel:el('midribChannel').value,polarity:el('midribPolarity').value,sigma_px:Number(el('midribSigma').value)};
}
function midribSignature() { return JSON.stringify([signature(),midribAnchors,midribOptions()]); }
function invalidateMidrib(reset) {
 midribRevision++; midribResult=null; el('midribSave').disabled=true;
 if(reset) { midribAnchors=[]; midribImages={}; el('midribReview').value='candidate'; }
 el('midribTrace').disabled=midribAnchors.length<2 || !midribImages.original;
 el('midribUndo').disabled=!midribAnchors.length; el('midribClear').disabled=!midribAnchors.length;
 el('midribPoints').textContent=midribAnchors.length+'개 점 · 최대 12개';
 el('midribStatus').textContent=midribAnchors.length<2?'기부와 끝을 잎 안쪽에 순서대로 찍어 주세요.':'점 또는 조건이 바뀌었습니다. 주맥 후보를 다시 계산하세요.';
 drawMidrib();
}
function drawMidrib() {
 const s=sample(); if(!s) return;
 const [x0,y0,x1,y1]=s.crop_xyxy_px;
 for(const [id,name] of [['midribCanvas','original'],['midribEvidence','evidence']]) {
  const c=el(id); c.width=x1-x0;c.height=y1-y0; const ctx=c.getContext('2d');
  if(midribImages[name]) ctx.drawImage(midribImages[name],0,0,c.width,c.height);
  const line=midribResult?.path_original_px || [];
  if(line.length) {ctx.strokeStyle='#ff5353';ctx.lineWidth=2;ctx.beginPath();line.forEach(([x,y],i)=>i?ctx.lineTo(x-x0,y-y0):ctx.moveTo(x-x0,y-y0));ctx.stroke();}
  midribAnchors.forEach(([x,y],i)=>{ctx.fillStyle='#ffe66b';ctx.beginPath();ctx.arc(x-x0,y-y0,4,0,2*Math.PI);ctx.fill();ctx.font='14px sans-serif';ctx.fillText(String(i+1),x-x0+6,y-y0-5);});
 }
}
async function previewMidrib() {
 const rev=++midribRevision,sig=midribSignature(); el('midribTrace').disabled=true; el('midribSave').disabled=true;
 el('midribStatus').textContent='원본과 고정 마스크에서 선 후보를 계산 중…';
 try {
  const r=await api('/api/midrib',{sample_id:sample().id,settings:config(),anchors:midribAnchors,options:midribOptions()});
  const pairs=await Promise.all(Object.entries(r.images).map(async([k,url])=>{const im=new Image();im.src=url;await im.decode();return [k,im];}));
  if(rev!==midribRevision||sig!==midribSignature())return;
  midribImages=Object.fromEntries(pairs);midribResult={...r,signature:sig};drawMidrib();
  const message = !midribAnchors.length && r.status==='needs_anchors'
   ? (r.ridge_normalization_scale>1e-8?'잎맥 후보 표시 완료 · 주맥 경로가 필요할 때만 점을 찍으세요.':'선 구조의 밝기 근거가 부족합니다.') : r.reason;
  el('midribStatus').textContent=message+` · 분석 가능 영역 ${r.usable_percent.toFixed(1)}%`+(r.path_length_px===null?'':` · 2D 경로 ${r.path_length_px.toFixed(1)}px`);
  el('midribSave').disabled=r.status!=='proposed';
 } catch(e) { if(rev===midribRevision) {midribResult=null;drawMidrib();el('midribStatus').textContent='계산 실패: '+e.message;} }
 finally {if(rev===midribRevision)el('midribTrace').disabled=midribAnchors.length<2||!midribImages.original;}
}
el('midribCanvas').onclick=event=>{
 if(!midribImages.original||midribAnchors.length>=12)return;
 const c=el('midribCanvas'),r=c.getBoundingClientRect(),s=sample(),[x0,y0]=s.crop_xyxy_px;
 const x=Math.floor((event.clientX-r.left)/r.width*c.width),y=Math.floor((event.clientY-r.top)/r.height*c.height);
 if(x<0||y<0||x>=c.width||y>=c.height)return;
 if(midribAnchors.some(p=>p[0]===x+x0&&p[1]===y+y0))return;
 midribAnchors.push([x+x0,y+y0]);invalidateMidrib(false);
};
el('midribUndo').onclick=()=>{midribAnchors.pop();invalidateMidrib(false);};
el('midribClear').onclick=()=>{midribAnchors=[];invalidateMidrib(false);};
el('midribTrace').onclick=previewMidrib;
for(const id of ['midribChannel','midribPolarity','midribSigma'])el(id).onchange=()=>{invalidateMidrib(false);previewMidrib();};
el('midribZoom').onchange=()=>{for(const id of ['midribCanvas','midribEvidence'])el(id).style.width=el('midribZoom').value+'%';};
el('midribSave').onclick=async()=>{
 if(!midribResult||midribResult.status!=='proposed'||midribResult.signature!==midribSignature())return;
 const sig=midribSignature(),sid=sample().id;el('midribSave').disabled=true;
 try {
  const r=await api('/api/midrib/save',{sample_id:sid,settings:config(),anchors:midribAnchors,options:midribOptions(),review:el('midribReview').value,note:el('note').value});
  midribSaved=r.record;el('midribDownload').disabled=false;
  if(sig===midribSignature())el('midribStatus').textContent='주맥 검토 저장 완료 · '+r.relative_path;
 }catch(e){if(sig===midribSignature())el('midribStatus').textContent='저장 실패: '+e.message;}
 finally{if(sig===midribSignature())el('midribSave').disabled=false;}
};
el('midribDownload').onclick=()=>{
 if(!midribSaved)return;
 const url=URL.createObjectURL(new Blob([JSON.stringify(midribSaved,null,2)],{type:'application/json'}));
 const a=document.createElement('a');a.href=url;a.download=midribSaved.observation.observation_id+'_midrib_review.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);
};
