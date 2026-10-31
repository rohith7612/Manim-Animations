"""Deterministic 3D direction, frame encoding, cache, and optional Manim overlays."""
from pathlib import Path
import hashlib
import json
import os
import shutil
import subprocess
import time
import av
import numpy as np
from PIL import Image
from .models import CinemaWorld

ROOT=Path(__file__).resolve().parents[1]

def node_runtime():
    return os.environ.get('FRAMECRAFT_NODE') or shutil.which('node')

def water_world(duration,segments=None,aspect='landscape'):
    def onset(terms,default):
        return next((w['start'] for s in segments or [] for w in s.get('words',[]) if w['word'].lower().strip(' .,!?;:') in terms),duration*default)
    evaporation=onset(['evaporation','evaporates','evaporate'],.12)
    condensation=onset(['condensation','condenses'],.35)
    rain=onset(['precipitation','rainfall','rain','rains'],.58)
    runoff=onset(['runoff','collection','collects'],.8)
    positions=[([-17,7.5,20],[-12,6,16],[4,2,-5],[4,2,-5]),([-10,2.3,9],[-7,3,8],[-2,1,-1],[-1,2,-2]),([-7,9,16],[-4,9.5,13],[4,8,-5],[5,8,-5]),([12,7,14],[10,5.5,11],[7,3,-5],[7,2,-4]),([13,5.5,11],[5,2.8,13],[6,1,0],[3,0,5])]
    boundaries=[0,duration*.2,duration*.4,duration*.6,duration*.8,duration]
    shots=[]
    for i,(a,b,c,d) in enumerate(positions):
        if aspect=='portrait':a=[a[0],a[1]+2,a[2]+9];b=[b[0],b[1]+2,b[2]+9]
        shots.append(dict(start=boundaries[i],end=boundaries[i+1],position=a,end_position=b,target=c,end_target=d,fov=48 if aspect=='portrait' else 44))
    stages=[]
    for name,start,end in [('evaporation',evaporation,max(condensation+duration*.15,evaporation+.5)),('condensation',condensation,duration),('rain',rain,max(runoff+duration*.04,rain+.5)),('runoff',runoff,duration)]:
        start=max(0,min(start,duration-.2));end=max(start+.1,min(end,duration));stages.append(dict(process=name,start=start,end=end,intensity=1))
    return CinemaWorld.model_validate(dict(world='landscape',seed=42,objects=[],motions=[],shots=shots,stages=stages,overlays=[]))

PALETTES={'midnight':['#4F8DFF','#7CE0C3','#F2C14E','#E86A92'],'paper':['#D9824B','#5C8A72','#3F6E9E','#C9A227'],'violet':['#9B6BFF','#5ED1F2','#F27BC1','#FFD166'],
    'sunrise':['#FF8A5B','#FFC857','#5BC0EB','#9BC53D'],'ocean':['#2A9DF4','#4FD1C5','#F6AE2D','#86BBD8'],'ember':['#E4572E','#F3A712','#A8C686','#669BBC']}
COLUMN_KINDS={'plates','stack','calls','editor'}
ROUND_SHAPES={'circle','ellipse','sun','cloud','droplet','molecule','star'}

def studio_world(plan,aspect='portrait'):
    """Turn a 2D storyboard into a procedural 3D studio: one lit station per scene, cues become 3D motion."""
    palette=PALETTES[(plan.art_direction.palette if plan.art_direction else 'midnight')]
    portrait=aspect=='portrait';vfov=50 if portrait else 42
    hfov=2*np.degrees(np.arctan(np.tan(np.radians(vfov/2))*(9/16 if portrait else 16/9)))
    budget=max(1,56//len(plan.scenes))
    objects,motions,shots,overlays=[],[],[],[]
    for i,scene in enumerate(plan.scenes):
        cx,cz=(i%8)*30-105,-(i//8)*30
        specs=[]
        if scene.kind=='illustration' and scene.illustration:
            # Extrude the 2D composition: x/y keep their layout, layers become depth.
            for o in sorted(scene.illustration.objects,key=lambda o:-o.width*o.height)[:budget]:
                if o.shape=='image':continue
                w,h=min(o.width,12),min(o.height,9);d=min(w,h)
                specs.append(dict(shape='sphere' if o.shape in ROUND_SHAPES else 'cone' if o.shape in ('mountain','tree') else 'box',
                    position=[cx+o.x*.8,max(-2.4+h*.4,o.y*.8),cz-o.layer*.4],scale=[w*.8,h*.8,d*.8],color=o.color,opacity=max(o.opacity,.35)))
        else:
            n=min(len(scene.items),budget)
            for j in range(n):
                if scene.kind in COLUMN_KINDS:
                    flat=scene.kind=='plates';size=[2.6,.28,2.6] if flat else [2.2,.7,1.5]
                    specs.append(dict(shape='cylinder' if flat else 'box',position=[cx,-2.5+size[1]/2+j*(size[1]+.12),cz],scale=size))
                else:
                    shape={'queue':'cylinder','browser':'box','expression':'box'}.get(scene.kind,'sphere')
                    size={'queue':[.9,1.8,.9],'browser':[1.7,1.2,.15]}.get(scene.kind,[1.4,1.4,1.4])
                    specs.append(dict(shape=shape,position=[cx+(j-(n-1)/2)*2,-2.5+size[1]/2+(.6 if scene.kind=='browser' else 0),cz],scale=size))
            for j,spec in enumerate(specs):spec.update(color=palette[j%len(palette)],opacity=1)
        ids=[]
        for j,spec in enumerate(specs):
            ids.append(f's{i}_o{j}')
            objects.append(dict(id=ids[-1],roughness=.35,metalness=.15,**{k:[round(x,3) for x in v] if isinstance(v,list) else v for k,v in spec.items()}))
        # One opacity/move and one pulse per object: later motions overwrite earlier ones in the renderer.
        faded,pulsed=set(),set()
        for cue in scene.cues:
            if cue.index>=len(ids):continue
            target=ids[cue.index];pos=specs[cue.index]['position'];above=[pos[0],pos[1]+3,pos[2]]
            end=min(scene.end,cue.time+.5)
            if cue.action in ('add','remove','restore') and target not in faded:
                faded.add(target);arriving=cue.action!='remove'
                motions.append(dict(target=target,action='reveal' if arriving else 'hide',start=cue.time,end=end,path=[],repeats=1,amount=0))
                motions.append(dict(target=target,action='move',start=cue.time,end=end,path=[above,pos] if arriving else [pos,above],repeats=1,amount=0))
            elif cue.action in ('focus','advance') and target not in pulsed:
                pulsed.add(target);motions.append(dict(target=target,action='pulse',start=cue.time,end=min(scene.end,cue.time+.7),path=[],repeats=1,amount=.14))
        lo=np.array([s['position'] for s in specs])-np.array([s['scale'] for s in specs])/2 if specs else np.array([[cx-1,-2.5,cz-1]])
        hi=np.array([s['position'] for s in specs])+np.array([s['scale'] for s in specs])/2 if specs else np.array([[cx+1,0,cz+1]])
        lo,hi=lo.min(0),hi.max(0);center=(lo+hi)/2;half=(hi-lo)/2
        dist=max(half[1]/np.tan(np.radians(vfov/2)),half[0]/np.tan(np.radians(hfov/2)))*1.35+half[2]+3
        start=[center[0]-dist*.28,center[1]+dist*.32,center[2]+dist];end_pos=[center[0]+dist*.18,center[1]+dist*.24,center[2]+dist*.88]
        shots.append(dict(start=scene.start,end=scene.end,position=start,end_position=end_pos,target=list(center),end_target=list(center),fov=vfov))
        if scene.title and scene.end-scene.start>=1.5 and len(overlays)<12:
            overlays.append(dict(text=scene.title[:70],start=scene.start+.2,end=min(scene.end-.05,scene.start+2.6),position='top_left'))
    for shot in shots:
        for k in ('position','end_position','target','end_target'):shot[k]=[round(float(x),3) for x in shot[k]]
    return CinemaWorld.model_validate(dict(world='studio',seed=7,objects=objects,motions=sorted(motions,key=lambda m:m['start'])[:100],shots=shots,stages=[],overlays=overlays))

def choose_world(plan,segments,aspect='portrait',force_3d=False):
    text=' '.join(s.get('text','') for s in segments).lower()
    if not plan.cinema and ('water cycle' in text or ('evaporation' in text and 'condensation' in text)):plan.cinema=water_world(max(s.end for s in plan.scenes),segments,aspect)
    if not plan.cinema and force_3d:
        plan.check_timing(max(s.end for s in plan.scenes))
        plan.cinema=studio_world(plan,aspect)
    plan.artwork=[]
    return plan

def cache_key(plan,width,height,fps):
    if not (ROOT/'dist/cinema/scene.js').is_file():raise ValueError('The 3D renderer is not built. Run: npm ci && npm run build:cinema')
    digest=hashlib.sha256(json.dumps({'cinema':plan['cinema'],'duration':plan['duration'],'width':width,'height':height,'fps':fps},sort_keys=True).encode())
    digest.update((ROOT/'dist/cinema/scene.js').read_bytes());digest.update((ROOT/'cinema/render.mjs').read_bytes())
    digest.update((ROOT/'backend/cinema_overlays.py').read_bytes())
    return digest.hexdigest()

def render_three(plan,project_path,cache_root,interpreter):
    project_path=Path(project_path)
    portrait=plan.get('aspect')=='portrait';final=plan.get('quality')=='final'
    width,height=((1080,1920) if portrait else (1920,1080)) if final else ((540,960) if portrait else (960,540))
    fps=24;key=cache_key(plan,width,height,fps);cache=Path(cache_root)/key;cache.mkdir(parents=True,exist_ok=True)
    output=cache/'silent.mp4'
    if output.exists():shutil.copy2(output,project_path/'silent.mp4');return {'engine':'threejs','cached':True,'fps':fps}
    node=node_runtime()
    if not node:raise ValueError('Node.js is required for procedural 3D rendering.')
    plan_path=project_path/'plan.json';frames=cache/'frames'
    progress=project_path/'render-progress.json'
    env={k:v for k,v in os.environ.items() if k!='OPENAI_API_KEY'}
    expected=int(np.ceil(plan['duration']*fps))
    ready=False
    try:
        meta=json.loads((frames/'render-info.json').read_text());ready=meta['width']==width and meta['height']==height and meta['frames']==expected and len(list(frames.glob('*.jpg')))==expected
    except (OSError,ValueError,KeyError):pass
    if not ready:
        with (project_path/'render.log').open('w',encoding='utf-8') as log:
            result=subprocess.run([node,str(ROOT/'cinema/render.mjs'),str(plan_path),str(frames),str(width),str(height),str(fps),str(progress)],cwd=ROOT,env=env,stdout=log,stderr=subprocess.STDOUT,timeout=1800)
        if result.returncode:raise ValueError('Procedural 3D rendering failed. Download the render log for details.')
    frame_files=sorted(frames.glob('*.jpg'))
    if len(frame_files)!=expected:raise ValueError('The 3D renderer did not produce all expected frames.')
    overlays=render_overlays(plan,project_path,interpreter,width,height)
    with av.open(str(output),'w',options={'movflags':'+faststart'}) as container:
        stream=container.add_stream('libx264',rate=fps);stream.width=width;stream.height=height;stream.pix_fmt='yuv420p';stream.options={'crf':'18','preset':'fast'}
        for i,path in enumerate(frame_files):
            with Image.open(path) as image:canvas=image.convert('RGBA')
            t=i/fps
            for spec,overlay in overlays:
                if spec['start']<=t<spec['end']:canvas.alpha_composite(overlay)
            frame=av.VideoFrame.from_ndarray(np.asarray(canvas.convert('RGB')),format='rgb24')
            for packet in stream.encode(frame):container.mux(packet)
        for packet in stream.encode():container.mux(packet)
    shutil.copy2(output,project_path/'silent.mp4')
    info=json.loads((frames/'render-info.json').read_text());info.update(engine='threejs',cached=False)
    (project_path/'cinema-render-info.json').write_text(json.dumps(info,indent=2))
    return info

def render_overlays(plan,project_path,interpreter,width,height):
    specs=plan['cinema'].get('overlays',[])
    if not specs:return []
    out=project_path/'overlays';out.mkdir(exist_ok=True)
    result=subprocess.run([interpreter,str(ROOT/'backend/cinema_overlays.py'),str(project_path/'plan.json'),str(out),str(width),str(height)],cwd=ROOT,capture_output=True,timeout=120)
    if result.returncode:
        (project_path/'overlay-error.log').write_bytes(result.stdout+result.stderr)
        raise ValueError('Manim overlay rendering failed. See overlay-error.log.')
    overlays=[]
    for i,spec in enumerate(specs):
        with Image.open(out/f'{i}.png') as image:overlays.append((spec,image.convert('RGBA')))
    return overlays
