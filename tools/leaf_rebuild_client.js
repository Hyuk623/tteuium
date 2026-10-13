/* Explicit same-origin local rebuild. Never uploads to a cloud service. */
(() => {
  'use strict';
  const button=document.getElementById('rebuildLocal'),status=document.getElementById('rebuildState'),link=document.getElementById('rebuildResult');
  const token=JSON.parse(document.getElementById('localRebuildToken').textContent);
  const headers={'Content-Type':'application/json','X-Local-Token':token};
  async function responseJson(response){const body=await response.json();if(!response.ok)throw Error(body.error||'로컬 요청 실패');return body;}
  async function watch(id){
    const job=await responseJson(await fetch('/api/jobs/'+encodeURIComponent(id),{headers}));
    if(job.status==='running'){status.textContent='사진 라벨·깊이·소엽 가능 공간을 계산 중… ('+job.job_id+')';setTimeout(()=>watch(id).catch(fail),1500);return;}
    button.disabled=false;
    if(job.status==='failed')throw Error(job.error+' · 입력 백업은 '+job.job_id+' 폴더에 보존됨');
    status.textContent='계산 완료 ('+job.job_id+') · 점 관찰 '+job.editor_observations+'개 · 부분 면 '+job.modeled_leaflets+'개 · 소엽 박스 '+
      job.leaflet_bbox_observations+'개 · 직육면체 '+job.cuboids_available+'개 · 모두 미검증';
    if(job.attached_surface_status==='current_for_this_point_snapshot')status.textContent+=' · 연결된 보간 면 '+job.attached_surface_count+'개';
    else if(job.attached_surface_status==='stale_from_earlier_point_snapshot')status.textContent+=' · 이전 보간 면은 현재 점과 달라 숨김';
    link.href=job.result_url;link.hidden=false;
  }
  function fail(error){status.textContent='계산 실패: '+error.message;button.disabled=false;}
  button.addEventListener('click',async()=>{
    button.disabled=true;link.hidden=true;
    try{
      const backup=window.__leafAnnotator.buildBackup();
      if(!backup.capture||!backup.capture.frames?.length)throw Error('먼저 준비된 사진 불러오기를 눌러 주세요.');
      status.textContent='현재 라벨을 새 실행 폴더에 백업 중…';
      const job=await responseJson(await fetch('/api/rebuild',{method:'POST',headers,body:JSON.stringify(backup)}));
      await watch(job.job_id);
    }catch(error){fail(error);}
  });
})();
