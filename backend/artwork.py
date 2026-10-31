"""Production image API integration: validated PNGs, local cache, no executable content."""
import base64
import hashlib
import io
import json
import shutil
from pathlib import Path
from PIL import Image
from openai import OpenAI
from .models import Plan, ArtworkAsset, VisualObject

DEFAULT_IMAGE_MODEL='gpt-image-2.5-flare'
SIZES={'landscape':'1536x1024','portrait':'1024x1536','square':'1024x1024'}

def asset_prompt(asset,art):
    context=f"Coherent animation art direction: {art.get('mood','educational')}; palette {art.get('palette','ocean')}; motion character {art.get('motion','calm')}."
    isolation=('A single isolated subject on a genuinely transparent background, with clean alpha edges. No scenery, checkerboard, drop shadow outside the subject, or text.' if asset.role=='cutout' else 'Full-bleed illustrated scene background, no borders, labels, lettering, captions, symbols, or arrows. Leave breathing room for animated overlays.')
    return f'Create a polished educational animation asset. {context}\n{asset.prompt}\n{isolation}\nMaintain clear forms, intentional lighting, and consistent materials. This is artwork for animation, not a diagram slide.'

def fingerprint(asset,art,model,quality):
    payload={'version':1,'model':model,'quality':quality,'size':SIZES[asset.aspect],'background':'transparent' if asset.role=='cutout' else 'opaque','prompt':asset_prompt(asset,art)}
    return hashlib.sha256(json.dumps(payload,sort_keys=True).encode()).hexdigest(),payload

def validate_png(raw,transparent=False):
    if len(raw)>25*1024*1024:raise ValueError('Generated artwork is too large.')
    with Image.open(io.BytesIO(raw)) as image:
        if image.format!='PNG':raise ValueError('The artwork service did not return PNG data.')
        if image.width*image.height>12_000_000:raise ValueError('Generated artwork exceeds the pixel limit.')
        image.load()
        if transparent:
            if 'A' not in image.getbands() or image.getchannel('A').getextrema()[0]==255:
                raise ValueError('The generated cutout has no transparency. Use an image model with transparent PNG support, then retry.')
        return {'width':image.width,'height':image.height,'transparent':transparent}

def prepare_plan(plan,segments,aspect='portrait'):
    """Fallback art brief for guided/legacy illustration plans; never changes a saved project implicitly."""
    if plan.artwork or not any(s.kind=='illustration' for s in plan.scenes):return plan
    text=' '.join(s.get('text','') for s in segments).lower()
    water='water cycle' in text or ('evaporation' in text and 'condensation' in text)
    bg=ArtworkAsset(id='scene_background',role='background',aspect=aspect,prompt=(
        'A cinematic painterly educational landscape: ocean on the left and lower third, snow-capped mountain peaks and forested sloping land on the right, a river draining downhill leftward into the sea. Pale clear sky in the upper half. Polished animated-film environmental concept art with layered atmospheric depth and warm natural light. No clouds, sun, rain, mist, particles, text, arrows, or diagrams; those are animated separately.' if water else
        f"A richly illustrated atmospheric environment appropriate for an educational film titled {plan.title}. Natural depth, textured materials, soft cinematic light, and space for moving foreground objects. No text, labels, diagrams, or foreground subjects."))
    plan.artwork=[bg]
    if water:plan.artwork.append(ArtworkAsset(id='cloud_cutout',role='cutout',aspect='landscape',prompt='One soft voluminous white cumulus cloud, softly shaded blue-gray underneath, warm rim lighting, polished painterly animated-film artwork, side-on view, centered and fully visible with ample padding. No rain, landscape, sun, or text.'))
    for shot in plan.scenes:
        if not shot.illustration:continue
        data=shot.illustration
        width=max(data.camera_width,data.camera_end_width)*1.16
        height=width*(16/9 if aspect=='portrait' else 9/16)
        data.objects.insert(0,VisualObject(id='generated_background',shape='image',asset_id=bg.id,x=data.camera_x,y=data.camera_y,width=width,height=height,color='#FFFFFF',opacity=1,layer=-8,points=[]))
        if water:
            remove={o.id for o in data.objects if o.shape in ['mountain','tree','water','polygon'] or o.id=='sea_shine'}
            data.objects=[o for o in data.objects if o.id not in remove]
            data.motions=[m for m in data.motions if m.target not in remove]
            for obj in data.objects:
                if obj.shape=='cloud':obj.shape='image';obj.asset_id='cloud_cutout'
    return Plan.model_validate(plan.model_dump())

def generate(plan,project_path,cache_path,key,model=DEFAULT_IMAGE_MODEL,quality='low',progress=None,client=None):
    if not plan.artwork:return []
    if not key:raise ValueError('Add an OpenAI API key in Settings to generate artwork.')
    if quality not in ['low','medium','high']:raise ValueError('Invalid artwork quality.')
    project_path=Path(project_path);cache_path=Path(cache_path)
    folder=project_path/'artwork';folder.mkdir(parents=True,exist_ok=True);cache_path.mkdir(parents=True,exist_ok=True)
    client=client or OpenAI(api_key=key,timeout=240,max_retries=0)
    art=plan.art_direction.model_dump() if plan.art_direction else {}
    results=[]
    for i,asset in enumerate(plan.artwork):
        digest,payload=fingerprint(asset,art,model,quality)
        cached=cache_path/(digest+'.png');target=folder/(asset.id+'.png')
        hit=False
        if cached.exists():
            try:meta=validate_png(cached.read_bytes(),asset.role=='cutout');hit=True
            except (ValueError,OSError):cached.unlink(missing_ok=True)
        if not hit:
            result=client.images.generate(model=model,prompt=payload['prompt'],background=payload['background'],size=payload['size'],quality=quality,output_format='png',n=1)
            if not result.data or not result.data[0].b64_json:raise ValueError('The artwork service returned no image data.')
            raw=base64.b64decode(result.data[0].b64_json,validate=True)
            meta=validate_png(raw,asset.role=='cutout')
            temporary=cache_path/(digest+'.partial');temporary.write_bytes(raw);temporary.replace(cached)
        shutil.copy2(cached,target)
        results.append({'id':asset.id,'role':asset.role,'prompt':asset.prompt,'generation_prompt':payload['prompt'],'model':model,'quality':quality,'hash':digest,'cached':hit,**meta})
        (project_path/'artwork-manifest.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        if progress:progress(i+1,len(plan.artwork),list(results))
    return results
