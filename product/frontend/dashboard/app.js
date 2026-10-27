const $ = id => document.getElementById(id);
const names = {home:'오늘의 식물',growth:'성장의 기록',environment:'우리 집 환경',actions:'함께한 기록'};
const labels = {plant_height:['식물 높이','cm',10],leaf_area:['잎 면적','cm²',100],canopy_area:['잎이 덮는 면적','cm²',100]};
const fields = [['temperature_c','온도','°C'],['humidity_pct','습도','%']];
const kinds = {water:'물 보충',nutrients:'영양',lighting:'조명 변경',pruning:'가지치기',pollination:'수분 (꽃가루받이)',relocation:'화분 이동',inspection:'직접 확인',note:'메모',manual_care:'관리'};
const origins = {mock:'모의 데이터',human:'사람이 기록',model:'모델 추정',device:'센서 측정',unknown:'출처 미확인'};
let state = null, deviceId = '', generation = 0;
const fmt = n => n == null ? '관측값 없음' : Number(n).toLocaleString('ko-KR',{maximumFractionDigits:1});
const date = t => new Date(t).toLocaleString('ko-KR',{month:'numeric',day:'numeric',hour:'2-digit',minute:'2-digit'});
function el(tag,text,cls){const n=document.createElement(tag);if(text!=null)n.textContent=text;if(cls)n.className=cls;return n;}
async function api(path,options){const r=await fetch(path,options);if(!r.ok)throw new Error(`${r.status} · ${await r.text()}`);return r.json();}
function send(path,data){return api(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(data)});}
function route(){const page=location.hash.slice(1) in names?location.hash.slice(1):'home';$('heading').textContent=names[page];$('period').parentElement.hidden=page==='actions';document.querySelectorAll('[data-screen]').forEach(n=>n.hidden=n.dataset.screen!==page);document.querySelectorAll('[data-page]').forEach(n=>{n.classList.toggle('active',n.dataset.page===page);if(n.dataset.page===page)n.setAttribute('aria-current','page');else n.removeAttribute('aria-current');});}
function option(select,value,text){const n=el('option',text);n.value=value;select.append(n);}
function imageFigure(item){const f=el('figure');if(!item){f.append(el('div','아직 이미지가 없습니다.','empty-image'));return f;}let url;try{url=new URL(item.reference,document.baseURI);}catch{}if(url&&['http:','https:'].includes(url.protocol)){const img=el('img');img.src=url.href;img.alt=item.source==='mock'?'모의 식물 예시 그림':'식물 관찰 이미지';img.onerror=()=>img.replaceWith(el('div','이미지를 불러올 수 없습니다.','empty-image'));f.append(img);}else f.append(el('div','이미지 참조만 등록됨 · 연결 가능한 URL이 필요합니다.','empty-image'));f.append(el('figcaption',`${date(item.captured_at)} · ${origins[item.source]}${item.source==='mock'?' · 실제 촬영 아님':''}`));return f;}
function plot(title,items,unit,subtitle){const panel=el('article',null,'panel');panel.append(el('h2',title),el('p',subtitle,'muted'));const valid=items.filter(x=>x.value!=null);if(!valid.length){panel.append(el('p','이 기간에 표시할 관측값이 없습니다.'));return panel;}panel.append(el('p',`${date(valid[0].time)} ${fmt(valid[0].value)} → ${date(valid.at(-1).time)} ${fmt(valid.at(-1).value)} ${unit}`,'chart-summary'));
const ns='http://www.w3.org/2000/svg',svg=document.createElementNS(ns,'svg');svg.setAttribute('viewBox','0 0 640 220');svg.setAttribute('role','img');svg.setAttribute('aria-label',`${title} 추이, ${subtitle}. 아래 표에서 정확한 값을 확인할 수 있습니다.`);svg.classList.add('plot');const min=Math.min(...valid.map(x=>x.value)),max=Math.max(...valid.map(x=>x.value)),pad=Math.max((max-min)*.12,1),lo=min-pad,hi=max+pad;const start=Date.parse(items[0].time),end=Date.parse(items.at(-1).time),span=Math.max(end-start,1);function node(tag,attrs,text){const n=document.createElementNS(ns,tag);Object.entries(attrs).forEach(([k,v])=>n.setAttribute(k,v));if(text)n.textContent=text;svg.append(n);return n;}
for(let i=0;i<3;i++){const y=24+i*72;node('line',{x1:65,y1:y,x2:620,y2:y,stroke:'#e4eadf'});node('text',{x:4,y:y+5,fill:'#637565','font-size':12},fmt(hi-(hi-lo)*i/2));}
let points=[];function flush(){if(points.length>1)node('polyline',{points:points.join(' '),fill:'none',stroke:'#417455','stroke-width':2.5});points=[];}items.forEach((item,index)=>{if(item.value==null){flush();return;}if(index&&Date.parse(item.time)-Date.parse(items[index-1].time)>86400000*2)flush();const x=65+(Date.parse(item.time)-start)/span*555,y=168-(item.value-lo)/(hi-lo)*144;points.push(`${x},${y}`);const dot=node('circle',{cx:x,cy:y,r:3,fill:'#417455'});const t=document.createElementNS(ns,'title');t.textContent=`${date(item.time)}: ${fmt(item.value)} ${unit}`;dot.append(t);});flush();node('text',{x:65,y:204,fill:'#637565','font-size':12},date(items[0].time));node('text',{x:620,y:204,'text-anchor':'end',fill:'#637565','font-size':12},date(items.at(-1).time));panel.append(svg);
const details=el('details'),summary=el('summary','관측값 표 보기'),wrap=el('div',null,'data-table'),table=el('table');const head=el('tr');['관측 시각',`값 (${unit})`].forEach(t=>head.append(el('th',t)));table.append(head);items.forEach(x=>{const tr=el('tr');tr.append(el('td',new Date(x.time).toLocaleString()),el('td',fmt(x.value)));table.append(tr);});wrap.append(table);details.append(summary,wrap);panel.append(details);return panel;}
function render(){const s=state.state,images=state.images;const sensors=s.Environment.readings;const sources=new Set([...sensors.map(r=>r.source),...s.Growth.measurements.map(m=>m.source_kind)]);$('notice').textContent=sources.has('mock')?'모의 데이터가 포함되어 있습니다. 모의값·예시 그림은 실제 식물의 관측이나 정상 판정이 아닙니다.':'관측과 모델 결과를 출처별로 표시합니다. 데이터가 없으면 판단하지 않습니다.';$('plant-name').textContent=state.plant.name;$('summary').textContent=state.summary;$('hero-image').replaceChildren(imageFigure(images.at(-1)));$('comparison').replaceChildren();if(images.length){$('comparison').append(imageFigure(images[0]));if(images.length>1)$('comparison').append(imageFigure(images.at(-1)));}else $('comparison').append(imageFigure(null));
const devices=s.Environment.devices;if(!devices.some(d=>d.id===deviceId))deviceId=devices[0]?.id||'';['device','environment-device'].forEach(id=>{$(id).replaceChildren();devices.forEach(d=>option($(id),d.id,d.name));$(id).value=deviceId;});const d=devices.find(d=>d.id===deviceId),latest=d?.latest;$('freshness').textContent=latest?`${origins[latest.source]} · ${date(latest.observed_at)}${d.status==='stale'?' · 업데이트가 오래되었습니다. 현재값으로 판단하지 마세요.':''}`:'환경 데이터가 없습니다.';$('cards').replaceChildren();fields.forEach(([key,label,unit])=>{const card=el('article',null,'card');card.append(el('span',label),el('strong',fmt(latest?.sensors[key])),el('small',unit+' · '+(latest?origins[latest.source]:'관측값 없음')));$('cards').append(card);});
$('growth-charts').replaceChildren();$('growth-summary').replaceChildren();for(const [metric,[label,unit,divisor]] of Object.entries(labels)){const rows=s.Growth.measurements.filter(m=>m.metric===metric);const groups=Map.groupBy?Map.groupBy(rows,m=>m.series):rows.reduce((map,m)=>map.set(m.series,[...(map.get(m.series)||[]),m]),new Map());if(!groups.size){$('growth-charts').append(plot(label,[],unit,'관측값 없음 · 실제 결과가 연결되면 표시됩니다.'));const r=el('div',null,'growth-row');r.append(el('span',label),el('span','관측값 없음'));$('growth-summary').append(r);}for(const items of groups.values()){const m=items[0],tag=`${origins[m.source_kind]} · ${m.provenance.scenario_id} / ${m.provenance.geometry_variant_id}`;const points=items.map(i=>({time:i.observed_at,value:i.value==null?null:i.value/divisor}));$('growth-charts').append(plot(label,points,unit,tag));const valid=points.filter(i=>i.value!=null),r=el('div',null,'growth-row');const left=el('div',label);left.append(el('div',origins[m.source_kind],'muted'));r.append(left,el('strong',valid.length>1?`${fmt(valid.at(-1).value-valid[0].value)} ${unit}`:'비교 관측 부족'));$('growth-summary').append(r);}}
$('environment-charts').replaceChildren();const own=sensors.filter(r=>r.device_id===deviceId);for(const [key,label,unit] of fields){const present=[...new Set(own.map(r=>r.source))];if(!present.length)$('environment-charts').append(plot(label,[],unit,'관측값 없음'));present.forEach(source=>{$('environment-charts').append(plot(label,own.map(r=>({time:r.observed_at,value:r.source===source?r.sensors[key]:null})),unit,origins[source]+' · '+(state.demo_stream?'브라우저 생성 예시':'수신 데이터')));});}
$('checks').replaceChildren();if(!state.checks.length)$('checks').append(el('p','표시할 점검 항목이 없습니다. 데이터의 충분함이나 식물의 정상 상태를 뜻하지 않습니다.','muted'));state.checks.forEach(c=>{const n=el('div',null,'check');n.append(el('strong',c.observation),el('p',c.check),el('p',c.action));const details=el('details');details.append(el('summary','근거 보기 · 관측 기반 안내'),el('p',JSON.stringify(c.evidence)));n.append(details);$('checks').append(n);});
renderJournal();renderStream();}
async function refresh(){const request=++generation;try{$('error').hidden=true;const plants=await api('/api/plants');if(request!==generation)return;const selected=$('plant').value;$('plant').replaceChildren();plants.forEach(p=>option($('plant'),p.id,p.name));if(plants.some(p=>p.id===selected))$('plant').value=selected;else if(plants.some(p=>p.id==='mvp-demo'))$('plant').value='mvp-demo';$('empty').hidden=plants.length>0;if(!plants.length){$('content').hidden=true;$('notice').textContent='아직 연결된 데이터가 없습니다.';return;}const result=await api(`/api/plants/${encodeURIComponent($('plant').value)}/state?days=${$('period').value}`);if(request!==generation)return;state=result;$('content').hidden=false;render();}catch(e){if(request!==generation)return;$('error').textContent='불러오기 실패: '+e.message;$('error').hidden=false;$('stream-status').textContent='서버 조회 실패';$('stream-status').classList.add('stream-stale');$('notice').textContent='연결을 확인해 주세요. 이전 화면 값이 남아 있다면 최신 데이터가 아닙니다.';}}
async function save(form,result,work){const button=form.querySelector('button[type="submit"]')||form.querySelector('button');button.disabled=true;$(result).textContent='저장 중…';try{await work();$(result).textContent=result==='action-result'?'✓ 식물과 함께한 한 페이지가 쌓였어요.':'저장했습니다.';await refresh();}catch(e){$(result).textContent='저장 실패: '+e.message;}finally{button.disabled=false;}}
$('action-form').onsubmit=e=>{e.preventDefault();const plant=state?.plant.id;if(!plant)return;save(e.target,'action-result',async()=>{await send('/api/actions',{plant_id:plant,kind:$('kind').value,note:$('note').value,action_date:$('action-date').value});$('note').value='';updateNoteCount();selectedDay=$('action-date').value;const chosen=new Date(selectedDay+'T12:00:00');journalMonth=new Date(chosen.getFullYear(),chosen.getMonth(),1);$('journal-dialog').close();});};
$('measurement-form').onsubmit=e=>{e.preventDefault();if(!state)return;const plant=state.plant.id;save(e.target,'measurement-result',()=>send('/api/observations',{import_id:crypto.randomUUID(),plant_id:plant,observed_at:new Date($('measured-at').value).toISOString(),source_ref:'manual-dashboard',source_sha256:'0'.repeat(64),scenario_id:'observation',geometry_variant_id:'manual',evidence:'human',measurements:[{metric:'plant_height',value:Number($('height').value)*10,unit:'mm',status:'human'}]}));};
const local=new Date(Date.now()-new Date().getTimezoneOffset()*60000);$('measured-at').value=local.toISOString().slice(0,16);
$('plant').onchange=()=>{deviceId='';state=null;$('content').hidden=true;refresh();};$('period').onchange=refresh;$('refresh').onclick=refresh;['device','environment-device'].forEach(id=>$(id).onchange=()=>{deviceId=$(id).value;render();});window.addEventListener('hashchange',route);route();refresh();setInterval(()=>{if(!document.hidden)refresh();},30000);

// Sentence starters describe observations, never prescribe care.
const activityPrompts = {
  water: ['물을 보충한 순간을 남겨볼까요?', '물을 준 양과 시간, 눈으로 확인한 모습을 적어보세요.', ['물을 준 시간은 ', '물을 준 양은 ']],
  nutrients: ['어떤 영양을 얼마나 더했나요?', '사용한 제품과 양 등 실제로 한 일을 남겨주세요.', ['사용한 제품은 ', '추가한 양은 ']],
  lighting: ['오늘의 빛은 어떻게 달라졌나요?', '조명의 위치, 켠 시간, 바꾼 설정을 적어보세요.', ['조명 위치를 ', '조명 시간을 ']],
  pruning: ['어느 부분을 정리했나요?', '정리한 위치와 개수, 눈에 보인 모습을 기록해 보세요.', ['정리한 부분은 ', '정리 후 모습은 ']],
  pollination: ['꽃과 함께한 순간이 있었나요?', '어떤 꽃에 어떤 방법으로 꽃가루받이를 했는지 남겨주세요.', ['꽃가루받이를 한 꽃은 ', '사용한 방법은 ']],
  relocation: ['식물의 새 자리는 어디인가요?', '옮긴 장소와 시간, 주변 환경을 적어보세요.', ['오늘 옮긴 자리는 ', '옮긴 시각은 ']],
  inspection: ['가만히 보니, 어떤 모습이 눈에 들어왔나요?', '잎의 모양이나 색, 어제와 달라 보이는 점을 적어보세요.', ['오늘 눈에 들어온 건 ', '어제와 비교해 보니 ']],
  note: ['오늘의 작은 이야기를 들려주세요.', '궁금한 점, 다음에 확인할 일, 기억하고 싶은 순간도 좋아요.', ['기억하고 싶은 순간은 ', '다음에 확인해 볼 것은 ']]
};
function updateNoteCount(){ $('note-count').textContent=`${$('note').value.length.toLocaleString()} / 2,000`; }
function chooseActivity(kind){
  $('kind').value=kind;
  const [prompt,placeholder,starters]=activityPrompts[kind];
  $('note-prompt').textContent=prompt;
  $('note').placeholder=placeholder;
  $('sentence-starters').replaceChildren();
  starters.forEach(text=>{const button=el('button',text.trim()+'…');button.type='button';button.onclick=()=>{const current=$('note').value;const addition=(current?'\n':'')+text;if(current.length+addition.length<=2000){$('note').value=current+addition;updateNoteCount();}$('note').focus();};$('sentence-starters').append(button);});
}
document.querySelectorAll('input[name="activity"]').forEach(input=>input.addEventListener('change',()=>chooseActivity(input.value)));
$('note').addEventListener('input',updateNoteCount);
chooseActivity('inspection');


const journalToday = new Date();
let journalMonth = new Date(journalToday.getFullYear(),journalToday.getMonth(),1);
let journalView = 'calendar', selectedDay = null;
function dayKey(value){const d=new Date(value);return `${d.getFullYear()}-${String(d.getMonth()+1).padStart(2,'0')}-${String(d.getDate()).padStart(2,'0')}`;}
function filteredRecords(){
  const search=$('filter-search').value.trim().toLocaleLowerCase();
  const kind=$('filter-kind').value;
  return (state?.state.Action.entries||[]).filter(a=>(!kind||a.kind===kind)&&(!search||a.note.toLocaleLowerCase().includes(search)));
}
function renderJournal(){
  const all=filteredRecords(),monthKey=dayKey(journalMonth).slice(0,7);
  const monthly=all.filter(a=>recordDay(a).startsWith(monthKey));
  $('calendar-view').hidden=journalView!=='calendar';$('journal-list').hidden=journalView!=='list';
  $('view-calendar').setAttribute('aria-pressed',String(journalView==='calendar'));
  $('view-list').setAttribute('aria-pressed',String(journalView==='list'));
  $('calendar-month').textContent=journalMonth.toLocaleDateString('ko-KR',{year:'numeric',month:'long'});
  const grid=$('calendar-grid');grid.replaceChildren();
  for(let i=0;i<journalMonth.getDay();i++){const blank=el('div',null,'calendar-blank');blank.setAttribute('aria-hidden','true');grid.append(blank);}
  const end=new Date(journalMonth.getFullYear(),journalMonth.getMonth()+1,0).getDate();
  for(let day=1;day<=end;day++){
    const key=dayKey(new Date(journalMonth.getFullYear(),journalMonth.getMonth(),day));
    const records=monthly.filter(a=>recordDay(a)===key);
    const button=el('button',null,'calendar-day');button.type='button';
    button.setAttribute('aria-label',`${key}, 기록 ${records.length}건`);button.setAttribute('aria-pressed',String(selectedDay===key));
    if(key===dayKey(new Date()))button.setAttribute('aria-current','date');
    button.append(el('span',String(day),'day-number'));
    if(records.length){button.append(el('span',`${records.length}건`,'day-count'));const types=[...new Set(records.map(a=>kinds[a.kind]||a.kind))];button.append(el('span',types.slice(0,2).join(' · '),'day-types'));}
    button.onclick=()=>openJournal(key);grid.append(button);
  }
  let entries=journalView==='list'?all:monthly.filter(a=>!selectedDay||recordDay(a)===selectedDay);
  const sorting=$('action-sort').value;
  entries=[...entries].sort((a,b)=>sorting==='oldest'?recordDay(a).localeCompare(recordDay(b))||Date.parse(a.created_at)-Date.parse(b.created_at):sorting==='kind'?(kinds[a.kind]||a.kind).localeCompare(kinds[b.kind]||b.kind,'ko')||recordDay(b).localeCompare(recordDay(a))||Date.parse(b.created_at)-Date.parse(a.created_at):recordDay(b).localeCompare(recordDay(a))||Date.parse(b.created_at)-Date.parse(a.created_at));
  $('record-heading').textContent=journalView==='list'?'전체 기록 목록':selectedDay?`${selectedDay}의 기록`:'이 달의 기록';
  $('clear-day').hidden=journalView!=='calendar'||!selectedDay;
  $('record-count').textContent=`${entries.length}건${$('filter-kind').value||$('filter-search').value?' · 필터 적용 중':''}`;
  $('actions').replaceChildren();
  if(!entries.length)$('actions').append(el('p','조건에 맞는 기록이 없습니다. 날짜나 필터를 바꾸거나 날짜를 눌러 기록을 남겨보세요.','muted'));
  entries.forEach(a=>{const n=el('div',null,'entry');n.append(el('strong',kinds[a.kind]||a.kind),el('p',a.note),el('small',recordDay(a)+' · 사람이 기록','muted'));$('actions').append(n);});
}
Object.entries(kinds).forEach(([key,label])=>option($('filter-kind'),key,label));
['filter-kind','action-sort'].forEach(id=>$(id).onchange=renderJournal);$('filter-search').oninput=renderJournal;
$('view-calendar').onclick=()=>{journalView='calendar';renderJournal();};$('view-list').onclick=()=>{journalView='list';renderJournal();};
function changeMonth(offset){journalMonth=new Date(journalMonth.getFullYear(),journalMonth.getMonth()+offset,1);selectedDay=null;renderJournal();}
$('prev-month').onclick=()=>changeMonth(-1);$('next-month').onclick=()=>changeMonth(1);
$('calendar-today').onclick=()=>{const now=new Date();journalMonth=new Date(now.getFullYear(),now.getMonth(),1);selectedDay=null;renderJournal();};
$('clear-day').onclick=()=>{selectedDay=null;renderJournal();};

function recordDay(entry){return entry.action_date||dayKey(entry.created_at);}
function showDayRecords(){
  const key=$('action-date').value;
  $('journal-dialog-title').textContent=key+' · 식물 기록';
  const target=$('day-records');target.replaceChildren();
  const entries=(state?.state.Action.entries||[]).filter(a=>recordDay(a)===key);
  if(entries.length)target.append(el('h3',`이날 남긴 기록 ${entries.length}건`));
  entries.forEach(a=>{const row=el('div',null,'entry');row.append(el('strong',kinds[a.kind]||a.kind),el('p',a.note));target.append(row);});
}
const journalDrafts=new Map();
$('journal-dialog').addEventListener('close',()=>{journalDrafts.set(state.plant.id+'|'+$('action-date').value,{note:$('note').value,kind:$('kind').value});});
function openJournal(key){
  const draft=journalDrafts.get(state.plant.id+'|'+key);
  $('action-date').value=key;$('note').value=draft?.note||'';
  const kind=draft?.kind||'inspection';document.querySelector(`input[name="activity"][value="${kind}"]`).checked=true;chooseActivity(kind);updateNoteCount();
  selectedDay=$('action-date').value;
  $('action-result').textContent=$('note').value.trim()?'작성 중인 내용을 이어서 보여드려요. 날짜를 확인해 주세요.':'';
  showDayRecords();$('journal-dialog').showModal();
}
$('action-date').onchange=showDayRecords;
$('close-journal').onclick=()=>$('journal-dialog').close();
$('new-record').onclick=()=>openJournal(dayKey(new Date()));

function renderStream(){
  const device=state.state.Environment.devices.find(d=>d.id===deviceId),latest=device?.latest;
  const rows=state.state.Environment.readings.filter(r=>r.device_id===deviceId).sort((a,b)=>Date.parse(b.observed_at)-Date.parse(a.observed_at));
  const stale=!latest||Date.now()-Date.parse(latest.observed_at)>300000;
  $('stream-status').textContent=!latest?'수신 대기':stale?'최근 데이터 없음':latest.source==='mock'?'모의 데이터 갱신 중':'센서 데이터 수신 중';
  $('stream-status').classList.toggle('stream-stale',stale);$('stream-heading').textContent=stale?'환경 데이터 연결을 확인해 주세요':state.demo_stream?'가상 환경이 계속 변화하고 있어요':'우리 집 환경이 기록되고 있어요';
  $('stream-detail').textContent=(state.demo_stream?'브라우저가 매분 생성하는 가상 환경입니다. 서버 수신 데이터가 아닙니다.':'선택 장치: '+(device?.name||'없음')+' · 수신 API를 통해 저장된 데이터입니다.')+' 화면은 30초마다 갱신합니다.';
  const daily=rows.filter(r=>Date.now()-Date.parse(r.observed_at)<=86400000&&r.source===latest?.source);
  $('daily-stats').replaceChildren();
  fields.forEach(([key,label,unit])=>{const values=daily.map(r=>r.sensors[key]).filter(v=>v!=null);const card=el('div',null,'day-stat');card.append(el('span','최근 24시간 '+label),el('strong',values.length?fmt(Math.min(...values))+' ~ '+fmt(Math.max(...values))+' '+unit:'관측값 없음'),el('small',values.length+'건 · '+(latest?origins[latest.source]:'수신 대기')));$('daily-stats').append(card);});
  const table=el('table'),head=el('tr');['측정 시각','온도','습도','출처'].forEach(t=>head.append(el('th',t)));table.append(head);
  rows.slice(0,5).forEach(r=>{const tr=el('tr');[new Date(r.observed_at).toLocaleTimeString('ko-KR'),fmt(r.sensors.temperature_c)+' °C',fmt(r.sensors.humidity_pct)+' %',origins[r.source]].forEach(t=>tr.append(el('td',t)));table.append(tr);});
  $('recent-readings').replaceChildren(rows.length?table:el('p','아직 수신한 데이터가 없습니다.'));
}
