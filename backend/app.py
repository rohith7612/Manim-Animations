import os
import sys
import json
import uuid
import shutil
import sqlite3
import subprocess
import threading
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

ROOT=Path(__file__).resolve().parents[1]
DATA=Path(os.environ.get('FRAMECRAFT_DATA',ROOT/'data')).resolve()
DATA.mkdir(parents=True,exist_ok=True)
DB=DATA/'studio.sqlite'
POOL=ThreadPoolExecutor(max_workers=1)
LOCK=threading.Lock()
MODEL_LOCK=threading.Lock()
MODEL=None
SETTINGS={'key':os.environ.get('OPENAI_API_KEY',''),'model':os.environ.get('OPENAI_MODEL','gpt-4.1-mini')}
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
        if j['status'] in ['queued','transcribing','planning','rendering']:
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
    return {'ok':True,'api_key_configured':bool(SETTINGS['key']),'model':SETTINGS['model'],'renderer':bool(renderer_python())}

class Settings(BaseModel):
    api_key: SecretStr | None = None
    model: str = Field(default='gpt-4.1-mini',max_length=100,pattern=r'^[a-zA-Z0-9._:-]+$')
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
def project(id:str):return load(id)

def renderer_python():
    configured=os.environ.get('MANIM_PYTHON')
    if configured:return configured
    import importlib.util
    if importlib.util.find_spec('manim'):return sys.executable
    existing=Path.home()/'manimations'/'.venv'/'Scripts'/'python.exe'
    return str(existing) if existing.exists() else None

def transcribe(path):
    global MODEL
    from faster_whisper import WhisperModel
    samples=audio_samples(path)
    with MODEL_LOCK:
        if MODEL is None:
            cache=Path(os.environ.get('WHISPER_CACHE',ROOT.parent/'.whisper-models'))
            MODEL=WhisperModel(os.environ.get('WHISPER_MODEL','small'),device='cpu',compute_type='int8',download_root=str(cache))
        segments,info=MODEL.transcribe(samples,word_timestamps=True,beam_size=5)
        result=[{'start':s.start,'end':s.end,'text':s.text.strip(),'words':[{'start':w.start,'end':w.end,'word':w.word} for w in s.words or []]} for s in segments]
    if not result:raise ValueError('No speech was detected in the uploaded video.')
    return result

def analyze(id,key,model):
    try:
        job=update(id,status='transcribing',progress=12,error=None)
        segments=job.get('transcript') or transcribe(DATA/id/'input.mp4')
        (DATA/id/'transcript.srt').write_text(srt(segments),encoding='utf-8')
        update(id,status='planning',progress=42,transcript=segments)
        if job['planner']=='openai':
            if not key:raise ValueError('Add an OpenAI API key in Settings, or choose the built-in planner.')
            plan=ai_plan(segments,job['duration'],key,model,job['direction'],job.get('aspect','portrait'))
        else:plan=guided_plan(segments,job['duration'],job.get('aspect','portrait'))
        art=plan.art_direction or infer_direction(segments)
        update(id,status='review',progress=60,plan=plan.model_dump(),style=art.palette,art_direction=art.model_dump())
    except Exception as e:
        # No request headers or secrets in user-facing error details.
        from openai import AuthenticationError, RateLimitError, APIConnectionError
        if isinstance(e,AuthenticationError):message='OpenAI rejected the API key. Update it in Settings and retry.'
        elif isinstance(e,RateLimitError):message='OpenAI quota or rate limit reached. Check your API billing and retry.'
        elif isinstance(e,APIConnectionError):message='Could not reach OpenAI. Check the connection and retry.'
        else:message=str(e)[:700].replace(key,'[redacted]') if key else str(e)[:700]
        update(id,status='error',error=message)

@app.post('/api/projects')
async def create(file:UploadFile=File(...),aspect:str=Form('portrait'),quality:str=Form('preview'),planner:str=Form('openai'),direction:str=Form('')):
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
        job={'id':id,'name':Path(file.filename or 'Untitled video').stem[:100],**meta,'style':'auto','art_direction':None,'aspect':aspect,'quality':quality,'planner':planner,'direction':direction,'status':'queued','progress':2,'transcript':None,'plan':None,'error':None,'sample':False}
        save(job);POOL.submit(analyze,id,SETTINGS['key'],SETTINGS['model']);return job
    except Exception as e:
        shutil.rmtree(path,ignore_errors=True)
        raise HTTPException(400,str(e))
    finally:await file.close()

class PlanBody(BaseModel):
    plan: Plan
@app.put('/api/projects/{id}/plan')
def edit_plan(id:str,body:PlanBody):
    job=load(id)
    if job['status'] not in ['review','complete','error']:raise HTTPException(409,'Wait for the current task to finish.')
    try:body.plan.check_timing(job['duration'])
    except ValueError as e:raise HTTPException(422,str(e))
    art=body.plan.art_direction or infer_direction(job.get('transcript') or [])
    return update(id,plan=body.plan.model_dump(),style=art.palette,art_direction=art.model_dump(),status='review',progress=60,error=None)

def render(id):
    try:
        job=update(id,status='rendering',progress=70,error=None)
        interpreter=renderer_python()
        if not interpreter:raise ValueError('Manim was not found. Set MANIM_PYTHON to your Manim Python executable and restart.')
        plan=Plan.model_validate(job['plan']).check_timing(job['duration']).model_dump()
        art=plan.get('art_direction') or infer_direction(job.get('transcript') or []).model_dump()
        plan['art_direction']=art
        job['style']=art['palette']
        plan.update({k:job[k] for k in ['duration','style','aspect','quality']})
        path=DATA/id
        (path/'plan.json').write_text(json.dumps(plan,ensure_ascii=False,indent=2),encoding='utf-8')
        source=(ROOT/'backend'/'renderer.py').read_text(encoding='utf-8')
        # repr encodes the plan as a Python string; it never becomes executable source.
        source='import json\nPLAN=json.loads('+repr(json.dumps(plan,ensure_ascii=False))+')\n'+source
        (path/'animation.py').write_text(source,encoding='utf-8')
        env={k:v for k,v in os.environ.items() if k not in ['OPENAI_API_KEY']}
        env['PYTHONIOENCODING']='utf-8'
        with (path/'render.log').open('w',encoding='utf-8') as log:
            r=subprocess.run([interpreter,'-m','manim','--disable_caching','--media_dir',str(path/'media'),str(path/'animation.py'),'BrollScene'],cwd=path,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if r.returncode:raise ValueError('Rendering failed. Download the render log for details, edit the scene plan, and retry.')
        candidates=[p for p in (path/'media'/'videos').rglob('BrollScene.mp4') if 'partial_movie_files' not in str(p)]
        if not candidates:raise ValueError('The renderer did not produce an MP4.')
        shutil.copy2(candidates[0],path/'silent.mp4');update(id,progress=92)
        mux(path/'silent.mp4',path/'input.mp4',path/'with-audio.mp4')
        poster(path/'silent.mp4',path/'poster.jpg')
        update(id,status='complete',progress=100,style=art['palette'],art_direction=art)
    except subprocess.TimeoutExpired:update(id,status='error',error='Rendering exceeded 30 minutes. Try preview quality or a shorter video.')
    except Exception as e:update(id,status='error',error=str(e)[:700])

@app.post('/api/projects/{id}/render')
def start_render(id:str):
    with LOCK:
        job=load(id)
        if job['status'] not in ['review','complete','error'] or not job.get('plan'):raise HTTPException(409,'A valid scene plan is needed before rendering.')
        job.update(status='queued',progress=65,error=None)
        with connection() as c:c.execute('UPDATE jobs SET payload=? WHERE id=?',(json.dumps(job),id))
    POOL.submit(render,id);return job

@app.post('/api/projects/{id}/retry')
def retry(id:str):
    job=load(id)
    if job['status']!='error':raise HTTPException(409,'This project is not waiting for a retry.')
    if job.get('plan'):return start_render(id)
    if job['planner']=='openai' and not SETTINGS['key']:raise HTTPException(400,'Add an API key first.')
    update(id,status='queued',error=None);POOL.submit(analyze,id,SETTINGS['key'],SETTINGS['model']);return load(id)

ARTIFACTS={'silent':'silent.mp4','audio':'with-audio.mp4','source':'animation.py','transcript':'transcript.srt','plan':'plan.json','poster':'poster.jpg','log':'render.log','input':'input.mp4'}
@app.get('/api/projects/{id}/files/{kind}')
def artifact(id:str,kind:str,download:bool=False):
    path=folder(id)/ARTIFACTS.get(kind,'__missing')
    if not path.is_file():raise HTTPException(404,'This file is not ready yet.')
    media='video/mp4' if path.suffix=='.mp4' else 'image/jpeg' if path.suffix=='.jpg' else 'text/plain'
    return FileResponse(path,media_type=media,filename=path.name if download else None)

@app.post('/api/sample')
def sample():
    if (DATA/'sample-auto').exists():return load('sample-auto')
    path=DATA/'sample'
    if not path.exists():raise HTTPException(404,'The sample is not installed. Run the sample setup script.')
    return load('sample')

app.mount('/',StaticFiles(directory=ROOT/'dist',html=True),name='studio')
