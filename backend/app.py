import os
import sys
import json
import uuid
import shutil
import sqlite3
import subprocess
import threading
import zipfile
import time
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.trustedhost import TrustedHostMiddleware
from pydantic import BaseModel, Field, SecretStr
from .models import Plan
from .media import inspect, audio_samples, mux, poster, srt
from .planner import ai_plan, guided_plan, infer_direction
from .render_status import with_render_status
from .cinematic import choose_world,render_three
from .transcript import transcribe_openai, correct, apply_texts, sentences
from .lesson import ai_lesson, PLANNING_MODEL

ROOT=Path(__file__).resolve().parents[1]

def load_env(path):
    """Read KEY=VALUE lines from .env without overriding the real environment."""
    if not path.is_file():return
    for line in path.read_text(encoding='utf-8').splitlines():
        key,sep,value=line.partition('=');key=key.strip()
        if sep and key and not key.startswith('#') and not os.environ.get(key):
            os.environ[key]=value.strip().strip('"\'')
load_env(ROOT/'.env')
DATA=Path(os.environ.get('FRAMECRAFT_DATA') or ROOT/'data').resolve()
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'studio.sqlite'
POOL=ThreadPoolExecutor(max_workers=1)
LOCK=threading.Lock()
MODEL_LOCK=threading.Lock()
MODEL=None
SETTINGS={'key':os.environ.get('OPENAI_API_KEY',''),'model':os.environ.get('OPENAI_MODEL') or PLANNING_MODEL}
MAX_BYTES=200*1024*1024

def connection():
    c=sqlite3.connect(DB,timeout=30);c.execute('PRAGMA journal_mode=WAL');return c
with connection() as c:
    c.execute('CREATE TABLE IF NOT EXISTS jobs (id TEXT PRIMARY KEY, payload TEXT NOT NULL)')

def save(job):
    with LOCK,connection() as c:c.execute('INSERT OR REPLACE INTO jobs VALUES (?,?)',(job['id'],json.dumps(job)))
def load(id):
    with connection() as c:r=c.execute('SELECT payload FROM jobs WHERE id=?',(id,)).fetchone()
    if not r:raise HTTPException(404,'Project not found.')
    return json.loads(r[0])
def update(id,**changes):
    job=load(id);job.update(changes);save(job);return job
def folder(id):
    load(id)
    return DATA/id

@asynccontextmanager
async def lifespan(app):
    with connection() as c:rows=c.execute('SELECT payload FROM jobs').fetchall()
    for row in rows:
        j=json.loads(row[0])
        if j['status'] in ['queued','transcribing','planning','artwork','rendering']:
            update(j['id'],status='error',error='The service restarted. Retry this project to continue.')
    yield

app=FastAPI(title='Framecraft Studio',lifespan=lifespan)
app.add_middleware(TrustedHostMiddleware,allowed_hosts=['127.0.0.1','localhost','testserver'])

@app.middleware('http')
async def local_boundary(request,call_next):
    # Browser mutations must come from this local studio; no wildcard CORS.
    if request.method not in ['GET','HEAD','OPTIONS']:
        origin=request.headers.get('origin')
        if origin and origin.rstrip('/')!=str(request.base_url).rstrip('/'):
            return __import__('starlette.responses',fromlist=['JSONResponse']).JSONResponse({'detail':'Open the local studio to use this service.'},status_code=403)
    response=await call_next(request)
    response.headers['X-Content-Type-Options']='nosniff'
    response.headers['Referrer-Policy']='same-origin'
    return response

@app.get('/api/health')
def health():
    return {'ok':True,'api_key_configured':bool(SETTINGS['key']),'model':SETTINGS['model'],'renderer':bool(renderer_python()),'code_only':True,'renderers':['manim','threejs']}

class Settings(BaseModel):
    api_key: SecretStr | None = None
    model: str = Field(default=PLANNING_MODEL,max_length=100,pattern=r'^[a-zA-Z0-9._:-]+$')
@app.post('/api/settings')
def settings(body:Settings):
    if body.api_key is not None:SETTINGS['key']=body.api_key.get_secret_value().strip()
    SETTINGS['model']=body.model
    return {'configured':bool(SETTINGS['key']),'model':SETTINGS['model']}

@app.get('/api/projects')
def projects():
    with connection() as c:rows=c.execute('SELECT payload FROM jobs ORDER BY rowid DESC').fetchall()
    return [json.loads(r[0]) for r in rows]
@app.get('/api/projects/{id}')
def project(id:str):return with_render_status(load(id),DATA)

def renderer_python():
    configured=os.environ.get('MANIM_PYTHON')
    if configured:return configured
    import importlib.util
    return sys.executable if importlib.util.find_spec('manim') else None

def transcribe_task(id,key):
    try:
        job=update(id,status='transcribing',progress=10,error=None)
        if key:
            segments=transcribe_openai(DATA/id/'input.mp4',key)
            update(id,progress=30)
            context=f"Video title: {job.get('name','')}. {job.get('direction','')}"
            segments,terms=correct(segments,key,context=context)
            source='openai'
        else:
            segments=transcribe(DATA/id/'input.mp4');terms=[];source='local'
        (DATA/id/'transcript.srt').write_text(srt(segments),encoding='utf-8')
        update(id,status='transcript',progress=40,transcript=segments,key_terms=terms,transcript_source=source)
    except Exception as e:
        update(id,status='error',error=friendly(e,key))

def friendly(e,key):
    from openai import AuthenticationError, RateLimitError, APIConnectionError
    if isinstance(e,AuthenticationError):return 'OpenAI rejected the API key. Update it in Settings and retry.'
    if isinstance(e,RateLimitError):return 'OpenAI quota or rate limit reached. Check your API billing and retry.'
    if isinstance(e,APIConnectionError):return 'Could not reach OpenAI. Check the connection and retry.'
    message=str(e)[:700]
    return message.replace(key,'[redacted]') if key else message

def transcribe(path):
    global MODEL
    from faster_whisper import WhisperModel
    samples=audio_samples(path)
    with MODEL_LOCK:
        if MODEL is None:
            cache=Path(os.environ.get('WHISPER_CACHE') or ROOT/'.whisper-models')
            MODEL=WhisperModel(os.environ.get('WHISPER_MODEL') or 'small',device='cpu',compute_type='int8',download_root=str(cache))
        segments,info=MODEL.transcribe(samples,word_timestamps=True,beam_size=5)
        words=[{'start':w.start,'end':w.end,'word':w.word.strip()} for s in segments for w in s.words or [] if w.word.strip()]
    if not words:raise ValueError('No speech was detected in the uploaded video.')
    return sentences(words)

def analyze(id,key,model):
    try:
        job=load(id)
        segments=job.get('transcript')
        if not segments:raise ValueError('Transcribe this project first.')
        update(id,status='planning',progress=45,error=None)
        if job['planner']=='openai':
            if not key:raise ValueError('Add an OpenAI API key in Settings, or choose the built-in planner.')
            if job.get('force_3d'):
                plan=ai_plan(segments,job['duration'],key,model,job['direction'],job.get('aspect','portrait'),False,True)
            else:
                # Educational default: word-synced lesson beats rendered with Manim.
                plan=ai_lesson(segments,job['duration'],key,model,job['direction'],job.get('aspect','portrait'),job.get('key_terms') or [])
        else:plan=guided_plan(segments,job['duration'],job.get('aspect','portrait'))
        if plan.artwork or any(o.shape=='image' for s in plan.scenes if s.illustration for o in s.illustration.objects):raise ValueError('The planner requested raster artwork. Replan this project in code-only mode.')
        if not plan.lesson:plan=choose_world(plan,segments,job.get('aspect','portrait'),job.get('force_3d',False)).check_timing(job['duration'])
        art=plan.art_direction or infer_direction(segments)
        update(id,status='review',progress=60,plan=plan.model_dump(),style=art.palette,art_direction=art.model_dump(),engine='threejs' if plan.cinema else 'manim',artwork_enabled=False,artwork_assets=[])
    except Exception as e:
        # No request headers or secrets in user-facing error details.
        update(id,status='error',error=friendly(e,key))

@app.post('/api/projects')
async def create(file:UploadFile=File(...),aspect:str=Form('portrait'),quality:str=Form('preview'),planner:str=Form('openai'),direction:str=Form(''),artwork_enabled:bool=Form(False),force_3d:bool=Form(False)):
    if aspect not in ['portrait','landscape'] or quality not in ['preview','final'] or planner not in ['openai','guided']:
        raise HTTPException(422,'Choose valid project settings.')
    if len(direction)>2000:raise HTTPException(422,'Keep the creative direction under 2,000 characters.')
    if planner=='openai' and not SETTINGS['key']:raise HTTPException(400,'Add your API key in Settings first, or select the built-in planner.')
    id=uuid.uuid4().hex;path=DATA/id;path.mkdir()
    try:
        size=0
        with (path/'input.mp4').open('wb') as f:
            while chunk:=await file.read(1024*1024):
                size+=len(chunk)
                if size>MAX_BYTES:raise ValueError('The upload limit is 200 MB.')
                f.write(chunk)
        meta=inspect(path/'input.mp4')
        if not meta['has_audio']:raise ValueError('Upload a video with narration.')
        job={'id':id,'name':Path(file.filename or 'Untitled video').stem[:100],**meta,'style':'auto','art_direction':None,'aspect':aspect,'quality':quality,'planner':planner,'direction':direction,'force_3d':force_3d,'artwork_enabled':False,'artwork_assets':[],'status':'queued','progress':2,'transcript':None,'plan':None,'error':None,'sample':False}
        save(job);POOL.submit(transcribe_task,id,SETTINGS['key']);return job
    except Exception as e:
        shutil.rmtree(path,ignore_errors=True)
        raise HTTPException(400,str(e))
    finally:await file.close()

class TranscriptBody(BaseModel):
    texts: list[str] | None = Field(default=None,max_length=400)
    key_terms: list[str] | None = Field(default=None,max_length=60)
    plan: bool = True

@app.put('/api/projects/{id}/transcript')
def edit_transcript(id:str,body:TranscriptBody):
    """Save the reviewed transcript (timing is re-aligned to the spoken words), then plan."""
    job=load(id)
    if job['status'] in ['queued','planning','transcribing','rendering','artwork']:raise HTTPException(409,'Wait for the current task to finish.')
    if not job.get('transcript'):raise HTTPException(409,'Transcribe this project first.')
    changes={}
    if body.texts is not None:
        if len(body.texts)!=len(job['transcript']):raise HTTPException(422,'Keep one line per transcript sentence.')
        try:segments=apply_texts(job['transcript'],body.texts)
        except ValueError as e:raise HTTPException(422,str(e))
        changes['transcript']=segments
        (DATA/id/'transcript.srt').write_text(srt(segments),encoding='utf-8')
    if body.key_terms is not None:changes['key_terms']=[t.strip()[:60] for t in body.key_terms if t.strip()]
    if body.plan:
        if job.get('planner')=='openai' and not SETTINGS['key']:raise HTTPException(400,'Connect your OpenAI planning key first.')
        changes.update(status='queued',plan=None,error=None,progress=42)
        update(id,**changes);POOL.submit(analyze,id,SETTINGS['key'],SETTINGS['model'])
        return load(id)
    return update(id,**changes)

@app.post('/api/projects/{id}/retranscribe')
def retranscribe(id:str):
    job=load(id)
    if job['status'] in ['queued','planning','transcribing','rendering','artwork']:raise HTTPException(409,'Wait for the current task to finish.')
    if not (DATA/id/'input.mp4').exists():raise HTTPException(404,'The original video is not available for this project.')
    update(id,status='queued',error=None,progress=5)
    POOL.submit(transcribe_task,id,SETTINGS['key']);return load(id)

class PlanBody(BaseModel):
    plan: Plan
@app.put('/api/projects/{id}/plan')
def edit_plan(id:str,body:PlanBody):
    job=load(id)
    if job['status'] not in ['review','complete','error']:raise HTTPException(409,'Wait for the current task to finish.')
    try:body.plan.check_timing(job['duration'])
    except ValueError as e:raise HTTPException(422,str(e))
    art=body.plan.art_direction or infer_direction(job.get('transcript') or [])
    return update(id,plan=body.plan.model_dump(),style=art.palette,art_direction=art.model_dump(),artwork_assets=[],status='review',progress=60,error=None)

@app.post('/api/projects/{id}/artwork')
def start_artwork(id:str):
    raise HTTPException(410,'Image generation is disabled. This studio now creates all visuals with code.')

def render(id,key=None):
    try:
        job=update(id,status='rendering',progress=70,error=None,render_started_at=time.time())
        (DATA/id/'render-progress.json').unlink(missing_ok=True)
        interpreter=renderer_python()
        if not interpreter:raise ValueError('Manim was not found. Set MANIM_PYTHON to your Manim Python executable and restart.')
        plan=Plan.model_validate(job['plan']).check_timing(job['duration']).model_dump()
        art=plan.get('art_direction') or infer_direction(job.get('transcript') or []).model_dump()
        plan['art_direction']=art
        job['style']=art['palette']
        plan.update({k:job[k] for k in ['duration','style','aspect','quality']})
        path=DATA/id
        if plan.get('artwork'):raise ValueError('This legacy plan uses generated artwork. Use Replan with code only before rendering.')
        (path/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        lesson=bool(plan.get('lesson'))
        source=(ROOT/'backend'/('lesson_renderer.py' if lesson else 'renderer.py')).read_text(encoding='utf-8')
        # repr encodes the plan as a Python string; it never becomes executable source.
        source='import json\nPLAN=json.loads('+repr(json.dumps(plan,ensure_ascii=False))+')\n'+source
        (path/'animation.py').write_text(source,encoding='utf-8')
        with zipfile.ZipFile(path/'source-bundle.zip','w',zipfile.ZIP_DEFLATED) as bundle:
            for name in ['animation.py','plan.json','artwork-manifest.json']:
                if (path/name).exists():bundle.write(path/name,name)
            for asset in plan.get('artwork',[]):bundle.write(path/'artwork'/(asset['id']+'.png'),'artwork/'+asset['id']+'.png')
            if plan.get('cinema'):
                for name in ['package.json','package-lock.json','cinema/render.mjs','cinema/scene.js','cinema/math.js','cinema/shaders.js','cinema/build.mjs','dist/cinema/scene.js','backend/__init__.py','backend/cinematic.py','backend/models.py','backend/cinema_overlays.py','backend/media.py','cinema/export.py','cinema/EXPORT.md']:
                    bundle.write(ROOT/name,name)
        env={k:v for k,v in os.environ.items() if k not in ['OPENAI_API_KEY']}
        env['PYTHONIOENCODING']='utf-8'
        if plan.get('cinema'):
            info=render_three(plan,path,DATA/'cinema-cache',interpreter)
            update(id,engine='threejs',render_info=info)
        else:
            with (path/'render.log').open('w',encoding='utf-8') as log:
                r=subprocess.run([interpreter,'-m','manim','--disable_caching','--media_dir',str(path/'media'),str(path/'animation.py'),'LessonScene' if lesson else 'BrollScene'],cwd=path,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
            if r.returncode:raise ValueError('Rendering failed. Download the render log for details, edit the scene plan, and retry.')
            candidates=[p for p in (path/'media'/'videos').rglob(('LessonScene' if lesson else 'BrollScene')+'.mp4') if 'partial_movie_files' not in str(p)]
            if not candidates:raise ValueError('The renderer did not produce an MP4.')
            shutil.copy2(candidates[0],path/'silent.mp4')
        update(id,progress=95)
        if job.get('has_audio',True):mux(path/'silent.mp4',path/'input.mp4',path/'with-audio.mp4')
        poster(path/'silent.mp4',path/'poster.jpg')
        update(id,status='complete',progress=100,style=art['palette'],art_direction=art)
    except subprocess.TimeoutExpired:update(id,status='error',error='Rendering exceeded 30 minutes. Try preview quality or a shorter video.')
    except Exception as e:
        message=str(e)[:700]
        for secret in [key,SETTINGS['key']]:
            if secret:message=message.replace(secret,'[redacted]')
        update(id,status='error',error=message)

@app.post('/api/projects/{id}/render')
def start_render(id:str):
    with LOCK:
        job=load(id)
        if job['status'] not in ['review','complete','error'] or not job.get('plan'):raise HTTPException(409,'A valid scene plan is needed before rendering.')
        job.update(status='queued',progress=65,error=None)
        with connection() as c:c.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(job),id))
    POOL.submit(render,id,SETTINGS['key']);return job

@app.post('/api/projects/{id}/retry')
def retry(id:str):
    job=load(id)
    if job['status']!='error':raise HTTPException(409,'This project is not waiting for a retry.')
    if job.get('plan'):return start_render(id)
    if not job.get('transcript'):
        update(id,status='queued',error=None);POOL.submit(transcribe_task,id,SETTINGS['key']);return load(id)
    if job['planner']=='openai' and not SETTINGS['key']:raise HTTPException(400,'Add an API key first.')
    update(id,status='queued',error=None);POOL.submit(analyze,id,SETTINGS['key'],SETTINGS['model']);return load(id)

@app.post('/api/projects/{id}/replan')
def replan(id:str,force_3d:bool|None=None):
    job=load(id)
    if job['status'] in ['queued','planning','transcribing','rendering','artwork']:raise HTTPException(409,'Wait for the current task to finish.')
    if job.get('planner')=='openai' and not SETTINGS['key']:raise HTTPException(400,'Connect your OpenAI planning key first.')
    update(id,status='queued',plan=None,error=None,progress=5,artwork_enabled=False,artwork_assets=[],**({} if force_3d is None else {'force_3d':force_3d}))
    POOL.submit(analyze,id,SETTINGS['key'],SETTINGS['model']);return load(id)

ARTIFACTS={'silent':'silent.mp4','audio':'with-audio.mp4','source':'animation.py','bundle':'source-bundle.zip','artwork':'artwork-manifest.json','transcript':'transcript.srt','plan':'plan.json','poster':'poster.jpg','log':'render.log','input':'input.mp4','render-info':'cinema-render-info.json'}
@app.get('/api/projects/{id}/files/{kind}')
def artifact(id:str,kind:str,download:bool=False):
    path=folder(id)/ARTIFACTS.get(kind,'__missing')
    if not path.is_file():raise HTTPException(404,'This file is not ready yet.')
    media='video/mp4' if path.suffix=='.mp4' else 'image/jpeg' if path.suffix=='.jpg' else 'application/zip' if path.suffix=='.zip' else 'text/plain'
    return FileResponse(path,media_type=media,filename=path.name if download else None)

@app.get('/api/projects/{id}/artwork/{asset_id}')
def artwork_file(id:str,asset_id:str):
    job=load(id)
    ids={a['id'] for a in (job.get('plan') or {}).get('artwork',[])}
    if asset_id not in ids:raise HTTPException(404,'Artwork not found.')
    path=DATA/id/'artwork'/(asset_id+'.png')
    if not path.exists():raise HTTPException(404,'Artwork is not ready yet.')
    return FileResponse(path,media_type='image/png')

def example(project_ids,asset):
    for id in project_ids:
        if (DATA/id).is_dir():
            try:return load(id)
            except HTTPException:pass
    path=ROOT/'dist'/'assets'/asset
    if not path.is_file():raise HTTPException(404,'This example is not installed.')
    return {**json.loads(path.read_text(encoding='utf-8')),'hostedSample':True}

@app.post('/api/sample')
def sample():
    return example(['sample-auto','sample'],'sample.json')

@app.post('/api/cinema-sample')
def cinema_sample():
    return example(['cinema-demo'],'cinema-sample.json')

app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='studio')
