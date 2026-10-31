const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const local=['127.0.0.1','localhost','[::1]'].includes(location.hostname);
let file=null,current=null,poll=null,health=null,busy=false,lastShown='';
const activeStates=['queued','transcribing','planning','artwork','rendering'];
const escapeHtml=s=>String(s??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const time=t=>`${Math.floor(t/60).toString().padStart(2,'0')}:${Math.floor(t%60).toString().padStart(2,'0')}`;
let toastTimeout;
function toast(message){$('#toast').textContent=message;$('#toast').hidden=false;clearTimeout(toastTimeout);toastTimeout=setTimeout(()=>$('#toast').hidden=true,5500);}
async function api(path,options={}){
 if(!local)throw new Error('Open the local studio to upload and render videos.');
 const response=await fetch('/api'+path,options);
 if(!response.ok){let body;try{body=await response.json();}catch{throw new Error('The service returned an unexpected response.');}throw new Error(typeof body.detail==='string'?body.detail:'Please check your scene plan and try again.');}
 return response.json();
}
function jsonOptions(data,method='POST'){return{method,headers:{'Content-Type':'application/json'},body:JSON.stringify(data)};}
async function refreshHealth(){
 if(!local){$('#engine-status').textContent='Explore the studio';$('#hosted-note').hidden=false;$('#settings-hosted').hidden=false;$('#settings-form').hidden=true;return;}
 try{health=await api('/health');$('#engine-status').textContent='Local studio connected';$('#key-note').innerHTML=health.api_key_configured?'<span>✓</span> OpenAI connected. Your key stays in server memory.':'<span>⌁</span> Connect your OpenAI key in <button class="settings-link">Settings</button>.';$('#model').value=health.model;$('#settings-status').textContent=health.api_key_configured?'An API key is currently connected.':'No OpenAI key connected. The built-in planner works without one.';}
 catch{$('#engine-status').textContent='Service unavailable';}
}
function settings(){ $('#settings-dialog').showModal();refreshHealth(); }
$('#open-settings').onclick=settings;$('#engine-button').onclick=settings;
document.addEventListener('click',e=>{if(e.target.closest('.settings-link'))settings();});
$('#close-settings').onclick=()=>$('#settings-dialog').close();
$('#settings-dialog').addEventListener('click',e=>{if(e.target===$('#settings-dialog')){const r=e.target.getBoundingClientRect();if(e.clientX<r.left||e.clientX>r.right||e.clientY<r.top||e.clientY>r.bottom)e.target.close();}});
$('#settings-form').onsubmit=async e=>{
 e.preventDefault();const button=e.target.querySelector('button[type="submit"]');button.disabled=true;
 try{const data={model:$('#model').value.trim()};if($('#api-key').value.trim())data.api_key=$('#api-key').value.trim();await api('/settings',jsonOptions(data));$('#api-key').value='';await refreshHealth();toast('Connection settings saved.');$('#settings-dialog').close();}
 catch(e){toast(e.message);}finally{button.disabled=false;}
};
function selectFile(selected){
 if(!selected)return;
 if(selected.size>200*1024*1024)return toast('Choose a video smaller than 200 MB.');
 if(!/\.(mp4|mov|webm|mkv|avi|m4v)$/i.test(selected.name)&&!selected.type.startsWith('video/'))return toast('Please choose a video file.');
 file=selected;$('#file-title').textContent=selected.name;$('#file-help').textContent=`${(selected.size/1024/1024).toFixed(1)} MB · Ready to plan`;$('#dropzone').classList.add('has-file');
}
$('#file').onchange=e=>selectFile(e.target.files[0]);
$('#dropzone').onkeydown=e=>{if(e.key==='Enter'||e.key===' '){e.preventDefault();$('#file').click();}};
['dragenter','dragover'].forEach(name=>$('#dropzone').addEventListener(name,e=>{e.preventDefault();$('#dropzone').classList.add('dragging');}));
['dragleave','drop'].forEach(name=>$('#dropzone').addEventListener(name,e=>{e.preventDefault();$('#dropzone').classList.remove('dragging');if(name==='drop')selectFile(e.dataTransfer.files[0]);}));
async function view(name){
 $('#studio-view').hidden=name!=='studio';$('#projects-view').hidden=name!=='projects';$('#view-name').textContent=name==='studio'?'Create B-roll':'Projects';$$('[data-view]').forEach(b=>b.classList.toggle('active',b.dataset.view===name));if(name==='projects')await library();
}
$$('[data-view]').forEach(button=>button.onclick=()=>view(button.dataset.view));
async function library(){
 try{
  const projects=local?await api('/projects'):[];$('#project-count').textContent=projects.length;
  $('#projects-list').innerHTML=projects.length?projects.map(j=>`<button class="library-card" data-project="${escapeHtml(j.id)}"><span class="state-pill">${escapeHtml(j.status)}</span><b>${escapeHtml(j.name)}</b><small>${time(j.duration)} · ${escapeHtml(j.style)} · ${j.aspect==='portrait'?'9:16':'16:9'}</small></button>`).join(''):'<div class="empty-state">Your next idea goes here.<br><br>Upload a video in Create B-roll to start your first project.</div>';
 }catch(e){toast(e.message);}
}
$('#projects-list').onclick=async e=>{const b=e.target.closest('[data-project]');if(!b)return;try{const j=await api('/projects/'+b.dataset.project);await view('studio');showProject(j,true);}catch(e){toast(e.message);}};
$('#generate').onclick=async()=>{
 if(!local){window.open('http://127.0.0.1:8765','_blank','noopener');toast('Start the Python service, then upload in the local studio.');return;}
 if(!file){$('#file').click();return;}
 if(busy)return;
 if(($('#planner').value==='openai')&&!health?.api_key_configured){settings();toast('Connect your planning API key, or use the built-in planner.');return;}
 const form=new FormData();form.append('file',file);form.append('aspect',$('#aspect').value);form.append('quality',$('#quality').value);form.append('planner',$('#planner').value);form.append('direction',$('#direction').value);form.append('force_3d',$('#force-3d').checked);
 busy=true;$('#generate').disabled=true;$('#generate').children[1].textContent='Uploading your video…';
 try{const j=await new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST','/api/projects');xhr.upload.onprogress=e=>{if(e.lengthComputable)$('#generate').children[1].textContent=`Uploading · ${Math.round(e.loaded/e.total*100)}%`;};xhr.onload=()=>{try{const data=JSON.parse(xhr.responseText);if(xhr.status>=200&&xhr.status<300)resolve(data);else reject(new Error(typeof data.detail==='string'?data.detail:'Upload could not be accepted.'));}catch{reject(new Error('The service returned an unexpected response.'));}};xhr.onerror=()=>reject(new Error('Upload interrupted. Check your local service.'));xhr.send(form);});showProject(j,true);library();}
 catch(e){toast(e.message);}finally{busy=false;$('#generate').disabled=false;$('#generate').children[1].textContent='Create my scene plan';}
};
const fileUrl=(j,kind,download=false)=>`/api/projects/${encodeURIComponent(j.id)}/files/${kind}${download?'?download=true':''}`;
function downloads(j){return [...(j.has_audio===false?[]:[['audio','MP4 + narration']]),['silent','Silent MP4'],[(j.engine==='threejs'||j.plan?.cinema||j.artwork_assets?.length)?'bundle':'source',(j.engine==='threejs'||j.plan?.cinema)?'Code-only source ZIP':j.artwork_assets?.length?'Legacy source ZIP':'Manim source'],['transcript','Transcript'],['plan','Scene plan']].map(([kind,label])=>`<a class="download-link" href="${fileUrl(j,kind,true)}">↓ ${label}</a>`).join('');}
function showProject(j,scroll=false){
 clearTimeout(poll);const changed=current?.id!==j.id;current=j;
 const art=j.art_direction||j.plan?.art_direction;
 $('#art-decision').textContent=art?`${art.mood} · ${art.palette} · ${art.motion} motion. ${art.rationale}`:'Your visual direction appears with the storyboard.';
 $('#project-panel').hidden=false;$('#project-title').textContent=j.name;$('#job-state').textContent=j.sample?'Example · complete':j.status==='review'?'Ready for review':j.status==='transcript'?'Review transcript':j.status;
 const running=activeStates.includes(j.status);$('#progress-area').hidden=!running;$('#progress-bar').style.width=(j.progress||0)+'%';
 $('#progress-text').textContent={queued:'Waiting for the local worker…',transcribing:'Transcribing with OpenAI, aligning word timings and fixing technical terms…',planning:'Planning word-synced lesson beats and checking key-term coverage…',artwork:'Generating and caching your illustrated backgrounds and objects…',rendering:'Animating your scenes. The worker is rendering the MP4…'}[j.status]||'';
 if(j.status==='rendering'&&Number.isFinite(j.rendered_seconds)){
  const eta=Number.isFinite(j.render_eta_seconds)?` · about ${j.render_eta_seconds<60?j.render_eta_seconds+' sec':Math.ceil(j.render_eta_seconds/60)+' min'} remaining`:'';
  const stale=j.render_update_age>30?` · last update ${j.render_update_age}s ago`:'';
  $('#progress-text').textContent=`Rendered ${time(j.rendered_seconds)} of ${time(j.render_total_seconds)}${eta}${stale}`;
 }
 $('#job-error').hidden=!j.error;$('#job-error').textContent=j.error||'';
 let actions='';
 if(j.status==='complete')actions=downloads(j);
 if(j.status==='transcript')actions+='<button class="primary" id="approve-transcript">✳ Approve transcript &amp; plan →</button>';
 if(j.status==='review'||(j.status==='error'&&j.plan))actions+='<button class="primary" id="render-project">✳ Render animation →</button>';
 if(j.status==='error')actions+='<button class="secondary" id="retry-project">Retry project</button>';
 if(j.status==='error'&&j.plan)actions+=`<a class="download-link" href="${fileUrl(j,'log',true)}">↓ Render log</a>`;
 if(!running&&j.transcript?.length&&j.status!=='transcript')actions+='<button class="secondary" id="approve-transcript">Save transcript &amp; replan</button>';
 if(!running&&!j.sample&&local)actions+='<button class="secondary" id="retranscribe">Retranscribe</button>';
 if(!running&&j.transcript?.length&&!j.plan?.cinema)actions+='<button class="secondary" id="replan-3d">Replan in 3D</button>';
 $('#project-actions').innerHTML=actions;
 const images=j.artwork_assets||[];$('#artwork-gallery').hidden=!images.length;
 const artworkUrl=a=>`/api/projects/${encodeURIComponent(j.id)}/artwork/${encodeURIComponent(a.id)}?v=${encodeURIComponent(a.hash)}`;
 $('#artwork-gallery').innerHTML=images.map(a=>`<figure><a href="${artworkUrl(a)}" target="_blank" rel="noopener"><img src="${artworkUrl(a)}" alt="${escapeHtml(a.id)} generated ${escapeHtml(a.role)}"></a><figcaption>${escapeHtml(a.role)} · ${a.cached?'cached':'generated'}<details><summary>Art brief</summary>${escapeHtml(a.prompt)}</details></figcaption></figure>`).join('');
 if(j.plan){
  $('#storyboard').innerHTML=j.plan.scenes.map((s,i)=>`<button class="story-card" data-scene="${i}"><span class="scene-number">${String(i+1).padStart(2,'0')}</span><span class="story-info"><b>${escapeHtml(s.title||s.kind)}</b><small>${escapeHtml(s.kind)} · ${s.illustration?.objects?.length||s.items.length} objects · ${s.illustration?.motions?.length||s.cues.length} timed actions</small></span><time>${time(s.start)}–${time(s.end)}</time></button>`).join('');
  if(j.plan.cinema){
   $('#storyboard').innerHTML=j.plan.cinema.shots.map((shot,i)=>`<button class="story-card" data-camera="${i}"><span class="scene-number">${String(i+1).padStart(2,'0')}</span><span class="story-info"><b>Camera shot ${i+1}</b><small>Procedural ${escapeHtml(j.plan.cinema.world)} · Three.js + GLSL · ${j.plan.cinema.overlays.length} Manim overlays</small></span><time>${time(shot.start)}–${time(shot.end)}</time></button>`).join('');
  }
  if(j.plan.lesson){
   const L=j.plan.lesson,miss=L.missing_terms||[];
   const cover=L.key_terms?.length?(miss.length?`<div class="coverage warn"><b>⚠ ${miss.length} spoken key term${miss.length>1?'s are':' is'} not on screen:</b> ${miss.map(escapeHtml).join(', ')}<small>Edit the plan or the key terms, then replan.</small></div>`:`<div class="coverage ok"><b>✓ All ${L.key_terms.length} key terms appear on screen when spoken.</b></div>`):'';
   $('#storyboard').innerHTML=cover+L.beats.map((b,i)=>`<button class="story-card" data-beat="${i}"><span class="scene-number">${String(i+1).padStart(2,'0')}</span><span class="story-info"><b>${escapeHtml(b.heading||b.items[0]?.text||b.layout)}</b><small>${escapeHtml(b.layout.replace('_',' '))}${b.analogy&&b.analogy!=='none'?' · '+escapeHtml(b.analogy):''} · ${b.items.map(it=>escapeHtml(it.text)).join(' → ')||'—'}</small></span><time>${time(b.start)}–${time(b.end)}</time></button>`).join('');
  }
  if(changed||document.activeElement!==$('#plan-json'))$('#plan-json').value=JSON.stringify(j.plan,null,2);
 }else{$('#storyboard').innerHTML='<p class="muted">Your scene plan will appear here after transcription and planning.</p>';$('#plan-json').value='';}
 const editable=local&&!running&&!j.sample&&j.transcript?.length;
 if(changed||lastShown!==j.id+j.status||!editable){
  const terms=editable?`<div class="key-terms"><label for="key-terms">Key terms that must appear on screen <span>comma-separated</span></label><input id="key-terms" value="${escapeHtml((j.key_terms||[]).join(', '))}" placeholder="e.g. LIFO, Spark, Databricks"><small>${j.transcript_source==='openai'?'Transcribed with OpenAI and proofread for technical terms.':'Transcribed locally. Retranscribe with an OpenAI key for higher accuracy.'} Fix any word below; timing stays locked to the speech.</small></div>`:'';
  $('#transcript').innerHTML=terms+((j.transcript||[]).map((s,i)=>`<div class="transcript-line"><button data-seek="${s.start}">${time(s.start)}</button>${editable?`<textarea data-line="${i}" rows="1">${escapeHtml(s.text)}</textarea>`:`<p>${escapeHtml(s.text)}</p>`}</div>`).join('')||'<p class="muted">Your timestamped transcript will appear here.</p>');
  $$('#transcript textarea').forEach(t=>{t.style.height=t.scrollHeight+'px';});
 }
 if(j.status==='transcript'&&lastShown!==j.id+'transcript')$('[data-tab="transcript"]').click();
 lastShown=j.id+j.status;
 $('#save-plan').disabled=running||!j.plan||(!local);
 if(j.status==='complete'){
  const src=j.hostedSample?(j.demo_video||'/assets/sample.mp4'):fileUrl(j,j.has_audio===false?'silent':'audio');
  if($('#player').getAttribute('src')!==src){$('#player').src=src;$('#player').poster=j.hostedSample?(j.demo_poster||'/assets/poster.jpg'):fileUrl(j,'poster');}
  $('#preview-name').textContent=j.name;$('#preview-badge').textContent=j.sample?'EXAMPLE':'YOUR RENDER';$('#preview-meta').textContent=`${time(j.duration)} · ${j.quality==='final'?'1080p':'540p'} · ${j.aspect==='portrait'?'9:16':'16:9'}`;
 }else if(changed){$('#preview-name').textContent='Your animation will appear here';$('#preview-badge').textContent='PLANNING';$('#player').pause();}
 if(scroll)$('#project-panel').scrollIntoView({behavior:'smooth',block:'start'});
 if(running)poll=setTimeout(async()=>{try{const next=await api('/projects/'+j.id);if(current?.id===j.id)showProject(next);}catch(e){toast(e.message);poll=setTimeout(()=>showProject(current),5000);}},1800);
}
$('#project-actions').onclick=async e=>{
 const approve=e.target.closest('#approve-transcript'),again=e.target.closest('#retranscribe');
 if(approve||again){
  (approve||again).disabled=true;
  try{let j;if(again)j=await api(`/projects/${current.id}/retranscribe`,{method:'POST'});
   else{const texts=$$('#transcript textarea').map(t=>t.value);const key_terms=($('#key-terms')?.value||'').split(',').map(t=>t.trim()).filter(Boolean);
    j=await api(`/projects/${current.id}/transcript`,jsonOptions({texts:texts.length?texts:null,key_terms,plan:true},'PUT'));}
   showProject(j);}catch(err){toast(err.message);(approve||again).disabled=false;}
  return;
 }
 const render=e.target.closest('#render-project'),retry=e.target.closest('#retry-project'),artwork=e.target.closest('#replan-project')||e.target.closest('#replan-3d');if(!render&&!retry&&!artwork)return;
 (render||retry||artwork).disabled=true;
 const query=artwork?.id==='replan-3d'?'?force_3d=true':'';
 try{const j=await api(`/projects/${current.id}/${artwork?'replan'+query:render?'render':'retry'}`,{method:'POST'});showProject(j);}catch(e){toast(e.message);(render||retry||artwork).disabled=false;}
};
$('#save-plan').onclick=async()=>{
 if(!current)return;let plan;try{plan=JSON.parse($('#plan-json').value);}catch{return toast('The scene plan contains invalid JSON. Check its formatting.');}
 try{const j=await api(`/projects/${current.id}/plan`,jsonOptions({plan},'PUT'));showProject(j);toast('Scene plan validated and saved.');}catch(e){toast(e.message);}
};
$$('[data-tab]').forEach(button=>button.onclick=()=>{$$('[data-tab]').forEach(b=>b.classList.toggle('selected',b===button));$$('.editor-pane').forEach(p=>p.hidden=p.id!==button.dataset.tab);});
$('#storyboard').onclick=e=>{const b=e.target.closest('[data-scene],[data-camera],[data-beat]');if(!b)return;const s=b.dataset.beat!==undefined?{...current.plan.lesson.beats[Number(b.dataset.beat)],kind:'lesson',items:current.plan.lesson.beats[Number(b.dataset.beat)].items.map(i=>i.text)}:b.dataset.camera!==undefined?current.plan.cinema.shots[Number(b.dataset.camera)]:current.plan.scenes[Number(b.dataset.scene)];if(current.status==='complete'){$('#player').currentTime=s.start;$('#player').play().catch(()=>{});$('#player').scrollIntoView({behavior:'smooth',block:'center'});}else{toast(s.kind?`${s.kind}: ${s.items.join(' → ')}. Edit timing and actions in Edit plan.`:'Edit the camera position, target, field of view, and timing in Edit plan.');}};
$('#transcript').addEventListener('input',e=>{if(e.target.matches('textarea')){e.target.style.height='auto';e.target.style.height=e.target.scrollHeight+'px';}});
$('#transcript').onclick=e=>{const b=e.target.closest('[data-seek]');if(b&&current?.status==='complete'){$('#player').currentTime=Number(b.dataset.seek);$('#player').play().catch(()=>{});}};
$('#load-example').onclick=async()=>{
 try{let j;if(local)j=await api('/sample',{method:'POST'});else{const r=await fetch('/assets/sample.json');if(!r.ok)throw new Error('Example unavailable.');j=await r.json();j.hostedSample=true;}showProject(j,true);
 if(!local)$('#project-actions').innerHTML='<a class="download-link" href="/assets/sample.mp4" download>↓ Example MP4</a><a class="download-link" href="/assets/sample.py" download>↓ Manim source</a>';
 }catch(e){toast(e.message);}
};
refreshHealth();if(local)library();
$('#load-nature').onclick=()=>{
 clearTimeout(poll);current=null;$('#project-panel').hidden=true;
 $('#player').src='/assets/water-cycle.mp4';$('#player').poster='/assets/water-cycle.jpg';
 $('#preview-name').textContent='Water cycle · illustrated world';$('#preview-badge').textContent='SILENT DEMO';
 $('#preview-meta').textContent='00:24 · 1920 × 1080 · Scenic animation';
 $('#player').play().catch(()=>{});$('#player').scrollIntoView({behavior:'smooth',block:'center'});
 toast('Illustrated capability demo. Upload your own narrated video for matching timing and audio.');
};

$('#load-cinema').onclick=async()=>{
 try{let j;if(local)j=await api('/cinema-sample',{method:'POST'});else{const r=await fetch('/assets/cinema-sample.json');if(!r.ok)throw new Error('Procedural demo is not ready.');j=await r.json();j.hostedSample=true;}showProject(j,true);
 if(!local)$('#project-actions').innerHTML='<a class="download-link" href="/assets/cinema-demo.mp4" download>↓ Code-only MP4</a><a class="download-link" href="/assets/cinema-source.zip" download>↓ Procedural source ZIP</a>';
 }catch(e){toast(e.message);}
};
