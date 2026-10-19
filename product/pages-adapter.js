/* Static demo boundary: no localhost calls, no shared writes, no actual DB export. */
(() => {
  const nativeFetch = window.fetch.bind(window);
  const storeKey = 'tteuium-pages-demo-actions-v1';
  const states = new Map();
  const reply = (body, status=200) => new Response(JSON.stringify(body), {status, headers:{'Content-Type':'application/json'}});
  function records(){const value=JSON.parse(localStorage.getItem(storeKey)||'[]');return Array.isArray(value)?value:[];}
  window.fetch = async (input, options={}) => {
    if(typeof input!=='string'||!input.startsWith('/api/'))return nativeFetch(input,options);
    const url=new URL(input,location.origin),method=options.method||'GET';
    if(url.pathname==='/api/plants')return reply([{id:'mvp-demo',name:'나의 작은 토마토'}]);
    if(url.pathname==='/api/simulations')return reply([]);
    if(url.pathname==='/api/actions'&&method==='POST'){
      try{const data=JSON.parse(options.body);if(data.plant_id!=='mvp-demo'||!data.note?.trim())return reply({detail:'내용을 입력해 주세요.'},422);const existing=records();existing.unshift({id:crypto.randomUUID(),created_at:new Date().toISOString(),plant_id:data.plant_id,kind:data.kind,note:data.note,provenance:'human'});localStorage.setItem(storeKey,JSON.stringify(existing.slice(0,100)));return reply({saved:true},201);}catch{return reply({detail:'이 브라우저에서 저장을 허용하지 않습니다.'},400);}
    }
    if(url.pathname==='/api/observations')return reply({detail:'공개 데모에서는 실제 관측값을 저장하지 않습니다.'},403);
    if(url.pathname==='/api/plants/mvp-demo/state'){
      const days=['7','14','30'].includes(url.searchParams.get('days'))?url.searchParams.get('days'):'14';
      if(!states.has(days)){const response=await nativeFetch(new URL(`state-${days}.json`,document.baseURI));if(!response.ok)return reply({detail:'데모 데이터를 불러올 수 없습니다.'},500);states.set(days,await response.json());}
      const state=structuredClone(states.get(days));
      try{state.state.Action.entries=records();}catch{state.state.Action.entries=[];}
      state.state.Action.status=state.state.Action.entries.length?'available':'unavailable';
      document.getElementById('pages-mode').textContent=`공개 체험 데모 · ${new Date(state.generated_at).toLocaleString('ko-KR')} 생성된 모의 데이터 · 실시간 센서 연결 없음 · 기록은 이 브라우저에만 저장됩니다.`;
      return reply(state);
    }
    return reply({detail:'이 기능은 로컬 서버 버전에서 사용할 수 있습니다.'},404);
  };
  const form=document.getElementById('measurement-form');
  form.querySelectorAll('input,button').forEach(element=>element.disabled=true);
  document.getElementById('measurement-result').textContent='공개 데모에서는 관측 입력을 제공하지 않습니다. 로컬 서버 버전에서 사용할 수 있습니다.';
  const note=document.createElement('p');note.className='muted';note.textContent='체험용 기록 · 현재 브라우저에만 저장되며 팀원과 공유되지 않습니다. 브라우저 데이터를 삭제하면 사라집니다.';
  document.getElementById('action-form').prepend(note);
})();
