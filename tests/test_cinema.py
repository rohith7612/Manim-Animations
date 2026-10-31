import pytest
from backend.cinematic import water_world,choose_world,cache_key,node_runtime
from backend.models import Plan,CinemaWorld
from backend.planner import guided_plan
from backend import app as studio
from fastapi.testclient import TestClient

def test_water_world_has_contiguous_cameras_and_physical_stages():
    world=water_world(15,aspect='landscape')
    assert world.shots[0].start==0 and world.shots[-1].end==15
    assert [s.process for s in world.stages]==['evaporation','condensation','rain','runoff']
    p=guided_plan([{'start':0,'end':15,'text':'Water cycle, evaporation and condensation.'}],15,'landscape')
    p=choose_world(p,[{'text':'Water cycle, evaporation and condensation.'}],'landscape')
    assert p.check_timing(15).cinema.world=='landscape'
    assert p.artwork==[]

def test_word_timing_drives_evaporation():
    world=water_world(20,[{'words':[{'word':'evaporation','start':5}]}])
    assert next(s for s in world.stages if s.process=='evaporation').start==5

def test_invalid_camera_and_motion_data_are_rejected():
    p=guided_plan([{'start':0,'end':15,'text':'Water cycle, evaporation and condensation.'}],15)
    p.cinema=water_world(15)
    p.cinema.shots[1].start=8
    with pytest.raises(ValueError,match='consecutively'):p.check_timing(15)

def test_existing_ai_camera_direction_is_preserved():
    p=guided_plan([{'start':0,'end':15,'text':'Water cycle, evaporation and condensation.'}],15)
    p.cinema=water_world(15);p.cinema.seed=99
    assert choose_world(p,[{'text':'water cycle'}]).cinema.seed==99

def test_image_generation_endpoint_is_disabled():
    with TestClient(studio.app) as client:
        assert client.post('/api/projects/any/artwork').status_code==410

def test_examples_fall_back_to_bundled_demos_then_prefer_local_projects(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'DB',tmp_path/'test.sqlite');monkeypatch.setattr(studio,'DATA',tmp_path)
    with studio.connection() as c:c.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    with TestClient(studio.app) as client:
        for endpoint in ['/api/cinema-sample','/api/sample']:
            assert client.post(endpoint).json()['hostedSample'] is True
        studio.save({'id':'cinema-demo','status':'complete','engine':'threejs'})
        (tmp_path/'cinema-demo').mkdir()
        local=client.post('/api/cinema-sample').json()
        assert local['engine']=='threejs' and 'hostedSample' not in local

def test_cached_render_changes_when_direction_changes():
    p={'duration':15,'cinema':water_world(15).model_dump()}
    key=cache_key(p,960,540,24)
    p['cinema']['shots'][0]['fov']=60
    assert key!=cache_key(p,960,540,24)
    assert node_runtime()

def test_cinema_validation_uses_3d_geometry_not_legacy_2d_metadata():
    p=guided_plan([{'start':0,'end':15,'text':'Water cycle, evaporation and condensation.'}],15)
    p.cinema=water_world(15)
    p.scenes[0].illustration.objects[0].points=[[0,0,0]]
    assert p.check_timing(15).cinema.world=='landscape'
    p.cinema=None
    with pytest.raises(ValueError,match='coordinates'):p.check_timing(15)

def test_force_3d_builds_studio_world_for_abstract_topics():
    segments=[{'start':0,'end':6,'text':'Push items onto a stack, then undo removes the last one.'},{'start':6,'end':12,'text':'A queue serves the oldest first.'}]
    p=guided_plan(segments,12,'portrait')
    assert choose_world(p.model_copy(deep=True),segments).cinema is None
    world=choose_world(p,segments,'portrait',force_3d=True).check_timing(12).cinema
    assert world.world=='studio' and world.objects
    assert world.shots[0].start==0 and world.shots[-1].end==12
    assert {m.target for m in world.motions}<={o.id for o in world.objects}

def test_force_3d_respects_object_and_motion_limits():
    scenes=[{'start':i,'end':i+1,'kind':'stack','title':'S','items':['A','B','C','D','E','F','G','H'],'cues':[{'time':i+.4,'action':'remove','index':7}]} for i in range(40)]
    p=Plan.model_validate({'title':'Many','scenes':scenes})
    world=choose_world(p,[],'landscape',force_3d=True).check_timing(40).cinema
    assert len(world.objects)<=60 and len(world.shots)==40

def test_force_3d_flag_is_stored_and_replan_can_enable_it(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'DB',tmp_path/'test.sqlite');monkeypatch.setattr(studio,'DATA',tmp_path)
    monkeypatch.setattr(studio.POOL,'submit',lambda *a,**k:None)
    with studio.connection() as c:c.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    with TestClient(studio.app) as client:
        studio.save({'id':'p','status':'complete','planner':'guided','transcript':[{'start':0,'end':2,'text':'x'}],'plan':None})
        assert client.post('/api/projects/p/replan?force_3d=true').json()['force_3d'] is True
