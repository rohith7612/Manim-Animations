import json
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.models import Plan
from backend.planner import guided_plan, normalize_plan, infer_direction
from backend import app as studio

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'DB',tmp_path/'test.sqlite')
    monkeypatch.setattr(studio,'DATA',tmp_path)
    with studio.connection() as c:c.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    with TestClient(studio.app) as client:yield client

def valid():
    return {'title':'Stack','scenes':[{'start':0,'end':5,'kind':'plates','title':'Plate stack','items':['A','B','C'],'cues':[{'time':2,'action':'remove','index':2}]}]}

def job(client):
    j={'id':uuid.uuid4().hex,'name':'Test','status':'review','duration':5,'plan':valid(),'planner':'guided','progress':60}
    studio.save(j);return j

def test_plan_rejects_overlap_out_of_bounds_and_bad_indices():
    p=valid();p['scenes'].append({**p['scenes'][0],'start':4,'end':8})
    with pytest.raises(ValueError):Plan.model_validate(p).check_timing(8)
    p=valid();p['scenes'][0]['cues'][0]['time']=8
    with pytest.raises(ValueError):Plan.model_validate(p).check_timing(5)
    p=valid();p['scenes'][0]['cues'][0]['index']=5
    with pytest.raises(ValueError):Plan.model_validate(p).check_timing(5)

def test_plan_supports_safe_labels():
    p=valid();p['scenes'][0]['items'][0]="'); __import__('os').system('bad') #"
    assert Plan.model_validate(p).check_timing(5).scenes[0].items[0].startswith("');")

def test_settings_never_return_key(client):
    old=studio.SETTINGS.copy()
    try:
        r=client.post('/api/settings',json={'api_key':'sk-test-secret','model':'gpt-4.1-mini'})
        assert r.status_code==200
        assert 'sk-test-secret' not in r.text
        assert 'sk-test-secret' not in client.get('/api/health').text
    finally:studio.SETTINGS.update(old)

def test_cross_origin_and_unknown_hosts_are_rejected(client):
    assert client.post('/api/settings',json={},headers={'Origin':'https://evil.example'}).status_code==403
    assert client.get('/api/health',headers={'Host':'evil.example'}).status_code==400

def test_plan_can_be_reviewed_and_saved(client):
    j=job(client);p=valid();p['title']='Updated'
    r=client.put(f"/api/projects/{j['id']}/plan",json={'plan':p})
    assert r.status_code==200 and r.json()['plan']['title']=='Updated'
    assert client.get('/api/projects').json()[0]['id']==j['id']

def test_invalid_plan_does_not_replace_saved_plan(client):
    j=job(client);p=valid();p['scenes'][0]['end']=20
    assert client.put(f"/api/projects/{j['id']}/plan",json={'plan':p}).status_code==422
    assert studio.load(j['id'])['plan']['scenes'][0]['end']==5

def test_downloads_only_allow_known_artifacts(client,tmp_path):
    j=job(client);path=tmp_path/j['id'];path.mkdir();(path/'silent.mp4').write_bytes(b'test')
    assert client.get(f"/api/projects/{j['id']}/files/silent").status_code==200
    assert client.get(f"/api/projects/{j['id']}/files/secret").status_code==404
    assert client.get('/api/projects/missing').status_code==404

def test_invalid_upload_rejected_and_cleaned(client):
    r=client.post('/api/projects',files={'file':('bad.mp4',b'not video','video/mp4')},data={'planner':'guided'})
    assert r.status_code==400
    assert client.get('/api/projects').json()==[]

def test_guided_planner_covers_narration():
    s=[{'start':0,'end':5,'text':'Think of a stack of plates.'},{'start':5,'end':10,'text':'Remove the last plate first.'}]
    p=guided_plan(s,10)
    assert p.scenes[0].start==0 and p.scenes[-1].end==10
    assert p.scenes[0].kind=='plates'

def test_normalization_preserves_start_cues_and_clamps_final_duration():
    p=valid()
    p['scenes'][0]['end']=9
    p['scenes'].append({'start':4,'end':12,'kind':'queue','title':'Next','items':['1'],'cues':[{'time':5,'action':'remove','index':0}]})
    result=normalize_plan(Plan.model_validate(p),7.8)
    assert result.scenes[0].end==4
    assert result.scenes[1].start==4
    assert result.scenes[1].end==7.8
    assert result.scenes[1].cues[0].time==5

def test_art_direction_follows_narration_and_survives_validation():
    calm=infer_direction([{'text':'Breathe, relax, and find peace.'}])
    urgent=infer_direction([{'text':'An urgent warning about danger.'}])
    assert calm.palette=='ocean' and calm.motion=='calm'
    assert urgent.palette=='ember' and urgent.motion=='bold'
    p=valid();p['art_direction']=calm.model_dump()
    assert normalize_plan(Plan.model_validate(p),5).art_direction.palette=='ocean'

def test_legacy_plans_remain_renderable():
    p=Plan.model_validate(valid())
    assert p.art_direction is None
    assert p.scenes[0].camera=='tracking'

def test_editor_hook_uses_transcript_action_times():
    p=valid();p['scenes'][0]['kind']='editor'
    words=[{'start':.58,'word':'typed'},{'start':1.64,'word':'deleted'},{'start':4.16,'word':'Z.'}]
    result=normalize_plan(Plan.model_validate(p),5,[{'words':words}])
    cues=result.scenes[0].cues
    assert [c.action for c in cues]==['add','add','add','remove','restore']
    assert cues[-2].time==1.64 and cues[-1].time==4.16

def test_upload_has_no_user_style_field(client):
    schema=client.get('/openapi.json').json()
    ref=schema['paths']['/api/projects']['post']['requestBody']['content']['multipart/form-data']['schema']['$ref'].split('/')[-1]
    assert 'style' not in schema['components']['schemas'][ref]['properties']

def test_water_cycle_produces_a_world_with_physical_motion_not_text_cards():
    p=guided_plan([{'start':0,'end':24,'text':'The water cycle: evaporation, condensation, precipitation, and runoff.'}],24,'landscape')
    scene=p.scenes[0]
    assert scene.kind=='illustration'
    kinds={o.shape for o in scene.illustration.objects}
    assert {'sun','water','cloud','mountain','droplet'}.issubset(kinds)
    for stage in ['vapor','rain','runoff']:
        assert any(m.target.startswith(stage) and m.action=='flow' for m in scene.illustration.motions)

def test_illustration_rejects_missing_objects_and_unsafe_motion_coordinates():
    from backend.nature import water_cycle
    p=water_cycle([],12,'landscape')
    p['scenes'][0]['illustration']['motions'][0]['target']='missing'
    with pytest.raises(ValueError):Plan.model_validate(p).check_timing(12)
    p=water_cycle([],12,'landscape')
    p['scenes'][0]['illustration']['motions'][5]['path']=[[0,0],[1e10,0]]
    with pytest.raises(ValueError):Plan.model_validate(p).check_timing(12)

def test_freeform_objects_support_other_subjects():
    from backend.nature import water_cycle
    p=water_cycle([],12,'landscape')
    illustration=p['scenes'][0]['illustration']
    illustration['objects']=[dict(id='planet',shape='circle',x=0,y=0,width=3,height=3,color='#4088DD',opacity=1,layer=0,points=[]),dict(id='moon',shape='circle',x=3,y=0,width=.5,height=.5,color='#CCCCCC',opacity=1,layer=1,points=[])]
    illustration['motions']=[dict(target='moon',action='move',start=0,end=12,path=[[3,0],[0,2],[-3,0],[0,-2],[3,0]],repeats=1,amount=0)]
    assert Plan.model_validate(p).check_timing(12).scenes[0].illustration.objects[0].id=='planet'
