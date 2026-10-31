import json
import time

def with_render_status(job,data_root,now=None):
    if job.get('status')!='rendering':return job
    path=data_root/job['id']/'render-progress.json'
    try:
        raw=json.loads(path.read_text(encoding='utf-8'))
        if raw.get('started_at',0)<job.get('render_started_at',0)-2:return job
        duration=float(job['duration']);rendered=max(0,min(duration,float(raw['rendered_seconds'])))
        elapsed=max(0,float(raw['wall_elapsed']))
        age=max(0,(now or time.time())-float(raw['updated_at']))
        result=dict(job)
        result.update(progress=max(job.get('progress',71),min(94,71+int(rendered/max(duration,.01)*23))),rendered_seconds=round(rendered,1),render_total_seconds=round(duration,1),render_update_age=round(age),render_wall_seconds=round(elapsed))
        if rendered>2 and elapsed>2:result['render_eta_seconds']=round(max(0,elapsed*(duration-rendered)/rendered))
        return result
    except (OSError,ValueError,TypeError,KeyError):return job
