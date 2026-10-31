import pytest
from fastapi.testclient import TestClient
from backend import app as studio
from backend.transcript import align, sentences, apply_texts
from backend.lesson import resolve, AIPlan, missing
from backend.models import Plan, ArtDirection

def timed(text,step=.5):
    return [{'word':w,'start':i*step,'end':i*step+.4} for i,w in enumerate(text.split())]

def test_corrected_terms_inherit_heard_timing():
    heard=timed('stack follows leaf or last in first out')
    words=align('Stack follows LIFO, last in, first out.',heard)
    assert [w['word'] for w in words][:3]==['Stack','follows','LIFO,']
    lifo=words[2]
    assert lifo['start']==pytest.approx(1.0) and lifo['end']==pytest.approx(1.9)
    assert words[-1]['start']==pytest.approx(3.5)
    assert all(a['start']<=b['start'] for a,b in zip(words,words[1:]))

def test_inserted_words_get_neighbouring_time():
    words=align('Python and SQL are key',timed('Python SQL are key'))
    assert words[1]['word']=='and' and .4<=words[1]['start']<=.5

def test_sentences_split_on_punctuation_and_pauses():
    w=timed('One idea. Second idea here')
    w[3]['start']+=2;w[3]['end']+=2;w[4]['start']+=2;w[4]['end']+=2
    segs=sentences(w)
    assert [s['text'] for s in segs]==['One idea.','Second','idea here']

def test_edits_keep_word_timing():
    seg=sentences(timed('the queue is fifo'))
    out=apply_texts(seg,['The queue is FIFO'])
    assert out[0]['words'][3]['word']=='FIFO' and out[0]['words'][3]['start']==pytest.approx(1.5)

def plan_json(beats):
    return AIPlan.model_validate({'title':'T','art_direction':{'palette':'midnight','mood':'Clear','rationale':'r','motion':'precise','backdrop':'grid'},'beats':beats})

def beat(start,layout='list',items=(),continues=False,**kw):
    base={'start_word':start,'layout':layout,'heading':kw.get('heading','H'),'continues':continues,'items':[{'text':t,'detail':'','value':None,'at':a} for t,a in items],
          'edges':[],'code':kw.get('code',''),'analogy':kw.get('analogy','none'),'actions':kw.get('actions',[])}
    return base

def test_word_indexes_become_exact_times():
    words=timed('the third skill is Spark then cloud skills AWS beats Azure')
    draft=plan_json([beat(0,'roadmap',[('Spark',4)]),beat(6,'comparison',[('AWS',8),('Azure',10)])])
    plan=resolve(draft,words,6.0,['Spark','AWS','Azure'])
    b0,b1=plan.lesson.beats
    assert b0.start==0 and b0.end==b1.start==3.0 and b1.end==6.0
    assert b0.items[0].time==2.0 and [i.time for i in b1.items]==[4.0,5.0]
    assert plan.lesson.missing_terms==[]

def test_continued_roadmap_carries_previous_steps():
    words=timed('python and sql then a detour and spark comes next')
    draft=plan_json([beat(0,'roadmap',[('Python',0),('SQL',2)]),beat(3,'key_term',[('Detour',5)]),beat(6,'roadmap',[('Spark',6)],continues=True)])
    b=resolve(draft,words,5.0).lesson.beats[2]
    assert [i.text for i in b.items]==['Python','SQL','Spark'] and b.items[0].carried and not b.items[2].carried

def test_missing_key_terms_are_flagged():
    words=timed('learn kafka and rag basics')
    plan=resolve(plan_json([beat(0,'list',[('Kafka',1)])]),words,2.5,['Kafka','RAG'])
    assert plan.lesson.missing_terms==['RAG']

def test_out_of_range_and_crowded_beats_are_repaired():
    words=timed('a b c d e f')
    draft=plan_json([beat(3,'list',[('x',99)]),beat(0,'title',[]),beat(3,'list',[])])
    plan=resolve(draft,words,3.0)
    assert [b.start for b in plan.lesson.beats]==[0,1.5]
    assert plan.lesson.beats[1].items[0].time<=2.95

def test_lesson_validation_rejects_gaps():
    words=timed('one two three four')
    plan=resolve(plan_json([beat(0,'title',[]),beat(2,'list',[('three',2)])]),words,2.0)
    data=plan.model_dump();data['lesson']['beats'][1]['start']=1.5
    with pytest.raises(ValueError,match='consecutively'):Plan.model_validate(data).check_timing(2.0)

@pytest.fixture
def client(tmp_path,monkeypatch):
    monkeypatch.setattr(studio,'DB',tmp_path/'test.sqlite');monkeypatch.setattr(studio,'DATA',tmp_path)
    monkeypatch.setattr(studio.POOL,'submit',lambda *a,**k:None)
    with studio.connection() as c:c.execute('CREATE TABLE jobs (id TEXT PRIMARY KEY,payload TEXT NOT NULL)')
    (tmp_path/'p').mkdir()
    with TestClient(studio.app) as client:yield client

def test_transcript_review_saves_edits_and_starts_planning(client):
    studio.save({'id':'p','status':'transcript','planner':'guided','duration':2,'transcript':sentences(timed('stack follows leaf or')),'key_terms':[]})
    r=client.put('/api/projects/p/transcript',json={'texts':['Stack follows LIFO'],'key_terms':['LIFO',' ']})
    j=r.json()
    assert r.status_code==200 and j['status']=='queued' and j['key_terms']==['LIFO']
    assert j['transcript'][0]['words'][2]=={'word':'LIFO','start':1.0,'end':1.9}

def test_transcript_line_count_must_match(client):
    studio.save({'id':'p','status':'transcript','planner':'guided','duration':2,'transcript':sentences(timed('one two.')),'key_terms':[]})
    assert client.put('/api/projects/p/transcript',json={'texts':['a','b']}).status_code==422

def test_retry_without_transcript_retranscribes(client):
    studio.save({'id':'p','status':'error','planner':'openai','duration':2,'transcript':None,'plan':None})
    assert client.post('/api/projects/p/retry').json()['status']=='queued'
