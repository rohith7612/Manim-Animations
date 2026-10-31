import json
from backend.render_status import with_render_status

def test_live_progress_and_estimate(tmp_path):
    p=tmp_path/'project';p.mkdir()
    (p/'render-progress.json').write_text(json.dumps({'started_at':100,'updated_at':150,'rendered_seconds':40,'wall_elapsed':50}))
    j={'id':'project','status':'rendering','progress':71,'duration':80,'render_started_at':99}
    result=with_render_status(j,tmp_path,now=152)
    assert result['progress']==82
    assert result['rendered_seconds']==40
    assert result['render_eta_seconds']==50
    assert result['render_update_age']==2
    assert j['progress']==71

def test_stale_and_partial_progress_are_ignored(tmp_path):
    p=tmp_path/'project';p.mkdir()
    j={'id':'project','status':'rendering','progress':71,'duration':80,'render_started_at':200}
    (p/'render-progress.json').write_text(json.dumps({'started_at':100,'updated_at':150,'rendered_seconds':40,'wall_elapsed':50}))
    assert with_render_status(j,tmp_path)==j
    (p/'render-progress.json').write_text('{')
    assert with_render_status(j,tmp_path)==j

def test_completed_project_never_shows_rendering_progress(tmp_path):
    j={'id':'project','status':'complete','progress':100,'duration':80}
    assert with_render_status(j,tmp_path)==j
