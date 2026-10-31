import base64
import io
from types import SimpleNamespace
import pytest
from PIL import Image
from backend.artwork import generate, prepare_plan, validate_png, fingerprint
from backend.models import Plan,ArtworkAsset
from backend.nature import water_cycle

def png(alpha=255):
    image=Image.new('RGBA',(32,32),(30,120,180,alpha));b=io.BytesIO();image.save(b,format='PNG');return b.getvalue()

def plan():
    p=Plan.model_validate(water_cycle([],8,'landscape'))
    return prepare_plan(p,[{'text':'The water cycle, evaporation and condensation.'}],'landscape').check_timing(8)

class FakeImages:
    def __init__(self):self.calls=[]
    def generate(self,**kwargs):
        self.calls.append(kwargs)
        raw=png(0 if kwargs['background']=='transparent' else 255)
        return SimpleNamespace(data=[SimpleNamespace(b64_json=base64.b64encode(raw).decode())])

def test_artwork_is_generated_once_and_reused_from_cache(tmp_path):
    images=FakeImages();client=SimpleNamespace(images=images);p=plan()
    first=generate(p,tmp_path/'one',tmp_path/'cache','test-key',client=client)
    second=generate(p,tmp_path/'two',tmp_path/'cache','test-key',client=client)
    assert len(images.calls)==2
    assert not any(a['cached'] for a in first)
    assert all(a['cached'] for a in second)
    assert all((tmp_path/'two'/'artwork'/(a['id']+'.png')).exists() for a in second)
    assert 'test-key' not in (tmp_path/'one'/'artwork-manifest.json').read_text()

def test_cutouts_require_actual_transparency():
    assert validate_png(png(0),True)['transparent']
    with pytest.raises(ValueError,match='transparency'):validate_png(png(),True)
    with pytest.raises(Exception):validate_png(b'not an image')

def test_changed_brief_or_model_invalidates_cache():
    a=ArtworkAsset(id='sky',role='background',aspect='landscape',prompt='A painted landscape with distant mountains.')
    first=fingerprint(a,{},'model-a','low')[0]
    assert first!=fingerprint(a,{},'model-b','low')[0]
    assert first!=fingerprint(a,{},'model-a','high')[0]
    a.prompt+=' Warm sunset lighting.'
    assert first!=fingerprint(a,{},'model-a','low')[0]

def test_artwork_placement_retains_particle_motion():
    p=plan();scene=p.scenes[0]
    assert len(p.artwork)==2
    assert any(o.shape=='image' and o.asset_id=='scene_background' for o in scene.illustration.objects)
    assert any(o.shape=='image' and o.asset_id=='cloud_cutout' for o in scene.illustration.objects)
    assert any(m.target.startswith('rain') for m in scene.illustration.motions)
    assert not any(o.shape=='mountain' for o in scene.illustration.objects)

def test_missing_asset_references_are_rejected():
    p=plan();p.artwork=[]
    with pytest.raises(ValueError,match='missing artwork'):p.check_timing(8)

def test_corrupt_cached_image_is_regenerated(tmp_path):
    images=FakeImages();p=plan();cache=tmp_path/'cache';cache.mkdir()
    art=p.art_direction.model_dump();digest,_=fingerprint(p.artwork[0],art,'test-model','low')
    (cache/(digest+'.png')).write_bytes(b'broken')
    result=generate(p,tmp_path/'project',cache,'test-key','test-model',client=SimpleNamespace(images=images))
    assert len(result)==2 and len(images.calls)==2

def test_artwork_planner_places_declared_background_and_drops_unused_cutouts():
    from backend.planner import normalize_plan
    p=Plan.model_validate(water_cycle([],8,'landscape'))
    p.artwork=[ArtworkAsset(id='backdrop',role='background',aspect='landscape',prompt='A painted ocean and mountain landscape.'),ArtworkAsset(id='unused',role='cutout',aspect='square',prompt='An isolated subject that has no placement.')]
    result=normalize_plan(p,8,aspect='landscape')
    assert [a.id for a in result.artwork]==['backdrop']
    assert any(o.shape=='image' and o.asset_id=='backdrop' for o in result.scenes[0].illustration.objects)

@pytest.mark.parametrize('camera_width',[14,20])
@pytest.mark.parametrize('route',['prepare','normalize'])
def test_portrait_background_covers_valid_wide_camera(camera_width,route):
    from backend.planner import normalize_plan
    p=Plan.model_validate(water_cycle([],8,'portrait'))
    data=p.scenes[0].illustration
    data.camera_width=camera_width;data.camera_end_width=camera_width
    if route=='prepare':
        result=prepare_plan(p,[{'text':'The water cycle with evaporation and condensation.'}],'portrait')
    else:
        p.artwork=[ArtworkAsset(id='background',role='background',aspect='portrait',prompt='A detailed coastal mountain landscape for a portrait animation.')]
        result=normalize_plan(p,8,aspect='portrait')
    result=Plan.model_validate(result.model_dump()).check_timing(8)
    bg=next(o for o in result.scenes[0].illustration.objects if o.shape=='image')
    assert bg.height==pytest.approx(camera_width*1.16*16/9)
    assert bg.height>=camera_width*16/9
    assert bg.height<=48
