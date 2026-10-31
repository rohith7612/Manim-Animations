import json
import uuid
import pytest
from fastapi.testclient import TestClient
from backend.models import Plan
from backend.planner import guided_plan
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
