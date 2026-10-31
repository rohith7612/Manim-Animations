const $=s=>document.querySelector(s);
const $$=s=>[...document.querySelectorAll(s)];
const local=['127.0.0.1','localhost','[::1]'].includes(location.hostname);
let file=null,style='midnight',current=null,poll=null,health=null,busy=false;
const activeStates=['queued','transcribing','planning','rendering'];
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
$$('[data-style]').forEach(button=>button.onclick=()=>{style=button.dataset.style;$$('[data-style]').forEach(b=>{b.classList.toggle('selected',b===button);b.setAttribute('aria-pressed',String(b===button));});});
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
 if($('#planner').value==='openai'&&!health?.api_key_configured){settings();toast('Connect your API key, or select the built-in planner.');return;}
 const form=new FormData();form.append('file',file);form.append('style',style);form.append('aspect',$('#aspect').value);form.append('quality',$('#quality').value);form.append('planner',$('#planner').value);form.append('direction',$('#direction').value);
 busy=true;$('#generate').disabled=true;$('#generate').children[1].textContent='Uploading your video…';
 try{const j=await new Promise((resolve,reject)=>{const xhr=new XMLHttpRequest();xhr.open('POST','/api/projects');xhr.upload.onprogress=e=>{if(e.lengthComputable)$('#generate').children[1].textContent=`Uploading · ${Math.round(e.loaded/e.total*100)}%`;};xhr.onload=()=>{try{const data=JSON.parse(xhr.responseText);if(xhr.status>=200&&xhr.status<300)resolve(data);else reject(new Error(typeof data.detail==='string'?data.detail:'Upload could not be accepted.'));}catch{reject(new Error('The service returned an unexpected response.'));}};xhr.onerror=()=>reject(new Error('Upload interrupted. Check your local service.'));xhr.send(form);});showProject(j,true);library();}
 catch(e){toast(e.message);}finally{busy=false;$('#generate').disabled=false;$('#generate').children[1].textContent='Create my scene plan';}
};
const fileUrl=(j,kind,download=false)=>`/api/projects/${encodeURIComponent(j.id)}/files/${kind}${download?'?download=true':''}`;
function downloads(j){return [['audio','MP4 + narration'],['silent','Silent MP4'],['source','Manim source'],['transcript','Transcript'],['plan','Scene plan']].map(([kind,label])=>`<a class="download-link" href="${fileUrl(j,kind,true)}">↓ ${label}</a>`).join('');}
function showProject(j,scroll=false){
 clearTimeout(poll);const changed=current?.id!==j.id;current=j;
 $('#project-panel').hidden=false;$('#project-title').textContent=j.name;$('#job-state').textContent=j.sample?'Example · complete':j.status==='review'?'Ready for review':j.status;
 const running=activeStates.includes(j.status);$('#progress-area').hidden=!running;$('#progress-bar').style.width=(j.progress||0)+'%';
 $('#progress-text').textContent={queued:'Waiting for the local worker…',transcribing:'Listening to the narration and finding word timings…',planning:'Turning your transcript into a visual scene plan…',rendering:'Animating your scenes. The worker is rendering the MP4…'}[j.status]||'';
 $('#job-error').hidden=!j.error;$('#job-error').textContent=j.error||'';
 let actions='';
 if(j.status==='complete')actions=downloads(j);
 if(j.status==='review'||(j.status==='error'&&j.plan))actions+='<button class="primary" id="render-project">✳ Render animation →</button>';
 if(j.status==='error')actions+='<button class="secondary" id="retry-project">Retry project</button>';
 if(j.status==='error'&&j.plan)actions+=`<a class="download-link" href="${fileUrl(j,'log',true)}">↓ Render log</a>`;
 $('#project-actions').innerHTML=actions;
 if(j.plan){
  $('#storyboard').innerHTML=j.plan.scenes.map((s,i)=>`<button class="story-card" data-scene="${i}"><span class="scene-number">${String(i+1).padStart(2,'0')}</span><span class="story-info"><b>${escapeHtml(s.title||s.kind)}</b><small>${escapeHtml(s.kind)} · ${s.items.length} objects · ${s.cues.length} timed actions</small></span><time>${time(s.start)}–${time(s.end)}</time></button>`).join('');
  if(changed||document.activeElement!==$('#plan-json'))$('#plan-json').value=JSON.stringify(j.plan,null,2);
 }else{$('#storyboard').innerHTML='<p class="muted">Your scene plan will appear here after transcription and planning.</p>';$('#plan-json').value='';}
 $('#transcript').innerHTML=(j.transcript||[]).map(s=>`<div class="transcript-line"><button data-seek="${s.start}">${time(s.start)}</button><p>${escapeHtml(s.text)}</p></div>`).join('')||'<p class="muted">Your timestamped transcript will appear here.</p>';
 $('#save-plan').disabled=running||!j.plan||(!local);
 if(j.status==='complete'){
  const src=j.hostedSample?'/assets/sample.mp4':fileUrl(j,'audio');
  if($('#player').getAttribute('src')!==src){$('#player').src=src;$('#player').poster=j.hostedSample?'/assets/poster.jpg':fileUrl(j,'poster');}
  $('#preview-name').textContent=j.name;$('#preview-badge').textContent=j.sample?'EXAMPLE':'YOUR RENDER';$('#preview-meta').textContent=`${time(j.duration)} · ${j.quality==='final'?'1080p':'540p'} · ${j.aspect==='portrait'?'9:16':'16:9'}`;
 }else if(changed){$('#preview-name').textContent='Your animation will appear here';$('#preview-badge').textContent='PLANNING';$('#player').pause();}
 if(scroll)$('#project-panel').scrollIntoView({behavior:'smooth',block:'start'});
 if(running)poll=setTimeout(async()=>{try{const next=await api('/projects/'+j.id);if(current?.id===j.id)showProject(next);}catch(e){toast(e.message);poll=setTimeout(()=>showProject(current),5000);}},1800);
}
$('#project-actions').onclick=async e=>{
 const render=e.target.closest('#render-project'),retry=e.target.closest('#retry-project');if(!render&&!retry)return;
 (render||retry).disabled=true;
 try{const j=await api(`/projects/${current.id}/${render?'render':'retry'}`,{method:'POST'});showProject(j);}catch(e){toast(e.message);(render||retry).disabled=false;}
};
$('#save-plan').onclick=async()=>{
 if(!current)return;let plan;try{plan=JSON.parse($('#plan-json').value);}catch{return toast('The scene plan contains invalid JSON. Check its formatting.');}
 try{const j=await api(`/projects/${current.id}/plan`,jsonOptions({plan},'PUT'));showProject(j);toast('Scene plan validated and saved.');}catch(e){toast(e.message);}
};
$$('[data-tab]').forEach(button=>button.onclick=()=>{$$('[data-tab]').forEach(b=>b.classList.toggle('selected',b===button));$$('.editor-pane').forEach(p=>p.hidden=p.id!==button.dataset.tab);});
$('#storyboard').onclick=e=>{const b=e.target.closest('[data-scene]');if(!b)return;const s=current.plan.scenes[Number(b.dataset.scene)];if(current.status==='complete'){$('#player').currentTime=s.start;$('#player').play().catch(()=>{});$('#player').scrollIntoView({behavior:'smooth',block:'center'});}else{toast(`${s.kind}: ${s.items.join(' → ')}. Edit labels, timing, and actions in Edit plan.`);}};
$('#transcript').onclick=e=>{const b=e.target.closest('[data-seek]');if(b&&current?.status==='complete'){$('#player').currentTime=Number(b.dataset.seek);$('#player').play().catch(()=>{});}};
$('#load-example').onclick=async()=>{
 try{let j;if(local)j=await api('/sample',{method:'POST'});else{const r=await fetch('/assets/sample.json');if(!r.ok)throw new Error('Example unavailable.');j=await r.json();j.hostedSample=true;}showProject(j,true);
 if(!local)$('#project-actions').innerHTML='<a class="download-link" href="/assets/sample.mp4" download>↓ Example MP4</a><a class="download-link" href="/assets/sample.py" download>↓ Manim source</a>';
 }catch(e){toast(e.message);}
};
refreshHealth();if(local)library();
