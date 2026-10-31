"""Install the real, previously rendered stack example into the local studio."""
from pathlib import Path
import json
import shutil
from backend.app import DATA, save
from backend.media import poster, srt

ROOT=Path(__file__).resolve().parent
source=ROOT.parent
path=DATA/'sample';path.mkdir(exist_ok=True)
segments=json.loads((source/'transcript.json').read_text(encoding='utf-8'))
spec=[(0,5.68,'editor','Typing, deletion, and undo',['H','E','L','L','O'],[(1.64,'remove',4),(4.16,'restore',4)]),
 (5.68,11.1,'stack','Last in, first out',['1','2','3'],[(9.72,'focus',2),(10.34,'remove',2)]),
 (11.1,16,'plates','The newest plate leaves first',['First','Second','Third','Last'],[(13.78,'add',3),(14.68,'remove',3)]),
 (16,23.76,'editor','Undo history',['A','B','C'],[(19.56,'remove',2),(22.78,'remove',1)]),
 (23.76,26.68,'editor','Undo operations',['A','B','C'],[(25.76,'remove',2)]),
 (26.68,27.74,'browser','Browser history',['Home','Search','Article'],[(27.1,'remove',2)]),
 (27.74,28.6,'calls','Function calls',['main()','a()','b()'],[(28.08,'focus',2)]),
 (28.6,29.88,'expression','Expression evaluation',['2','+','3'],[(29.03,'focus',2)]),
 (29.88,36.32,'plates','Visualize the stack',['First','Second','Last'],[(31.78,'focus',2),(35,'remove',2)]),
 (36.32,44.7,'stack','Newest or oldest?',['Oldest','2','3','Newest'],[(39.84,'focus',3),(43.32,'focus',0)]),
 (44.7,49.8,'queue','A queue processes the oldest first',['1','2','3','4'],[(47.88,'remove',0)])]
plan={'title':'The stack, explained.','scenes':[{'start':a,'end':b,'kind':k,'title':t,'items':items,'cues':[{'time':time,'action':act,'index':i} for time,act,i in cues]} for a,b,k,t,items,cues in spec]}
job={'id':'sample','name':'The stack, explained.','duration':49.8,'width':1080,'height':1920,'has_audio':True,'style':'midnight','aspect':'portrait','quality':'final','planner':'guided','direction':'Larger objects, minimal text, close-ups, shadows.','status':'complete','progress':100,'transcript':segments,'plan':plan,'error':None,'sample':True}
for src,dest in [('Stack_Polished_With_Audio.mp4','with-audio.mp4'),('Stack_Polished_Silent.mp4','silent.mp4'),('stack_polished.py','animation.py')]:shutil.copy2(source/src,path/dest)
input_path=Path.home()/'Downloads'/'Stack Explained in 30 Seconds DAY 25 100.mp4'
if input_path.exists():shutil.copy2(input_path,path/'input.mp4')
(path/'plan.json').write_text(json.dumps(plan,indent=2),encoding='utf-8')
(path/'transcript.srt').write_text(srt(segments),encoding='utf-8')
poster(path/'silent.mp4',path/'poster.jpg')
shutil.copy2(path/'poster.jpg',ROOT/'dist'/'assets'/'poster.jpg')
(ROOT/'dist'/'assets'/'sample.json').write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
save(job)
print('Example installed.')
