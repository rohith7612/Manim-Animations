"""Offline water-cycle reference composition; AI may author different worlds."""
import math

def water_cycle(segments,duration,aspect='portrait'):
    objects=[];motions=[]
    def obj(id,shape,x,y,w,h,color,layer=0,opacity=1,points=None):
        objects.append(dict(id=id,shape=shape,x=x,y=y,width=w,height=h,color=color,opacity=opacity,layer=layer,points=points or []))
    def motion(target,action,a,b,path=None,repeats=1,amount=0):
        motions.append(dict(target=target,action=action,start=a*duration,end=b*duration,path=path or [],repeats=repeats,amount=amount))
    # Scenic coordinates are authored in landscape, then fit to the requested canvas.
    obj('far_hill','polygon',2,-.45,14,4,'#A6D0CD',-5,points=[[-1,-1],[-1,0],[-.3,.7],[.2,.2],[.6,.8],[1,.1],[1,-1]])
    obj('mountain_back','mountain',3.6,.4,5.2,4.4,'#6B9C9D',-3)
    obj('mountain','mountain',5,.1,4.4,4.3,'#507C82',-2)
    obj('land','polygon',3.5,-2.1,10,3.4,'#719D6D',0,points=[[-1,-1],[-1,-.55],[-.55,-.25],[-.15,.05],[.3,.2],[.7,.75],[1,.2],[1,-1]])
    obj('ocean','water',-4,-2.4,8.6,2.35,'#298EA8',1)
    obj('sea_shine','ellipse',-4.6,-1.5,3.4,.16,'#B2EEF0',2,opacity=.45)
    obj('sun','sun',-5.2,2.6,2.4,2.4,'#FFD17A',-1)
    obj('cloud_one','cloud',-.8,2.4,4.1,1.8,'#F5FBFD',3)
    obj('cloud_two','cloud',2.25,2.6,3.6,1.5,'#D8EDF3',2)
    for i,x in enumerate([2,2.7,6.3,6.8]):obj('tree'+str(i),'tree',x,-.75+(x-2)*.09,.65,1.3,'#316B51',3)
    motion('sun','rotate',0,1,amount=.45)
    motion('sea_shine','pulse',0,1,repeats=5,amount=.12)
    motion('cloud_one','reveal',.18,.4)
    motion('cloud_two','reveal',.29,.48)
    motion('cloud_one','move',.35,1,path=[[-.8,2.4],[.1,2.6],[.75,2.45]])
    for i in range(10):
        x=-6.4+i*.4
        obj('vapor'+str(i),'circle',x,-1.3,.10,.10,'#D4F4F2',4,opacity=.75)
        motion('vapor'+str(i),'flow',.035+i*.008,.47,path=[[x,-1.3],[x+.4,-.2],[x+.35,1.05],[-1+i*.12,2.3]],repeats=2)
    for i in range(16):
        x=-.4+i*.28
        obj('rain'+str(i),'droplet',x,2,.075,.19,'#4D9DCE',5)
        motion('rain'+str(i),'flow',.48+(i%4)*.009,.79,path=[[x,2.05],[x-.22,.9],[x-.35,-.55]],repeats=3)
    river=[[5.8,1.3],[5.1,.6],[4.6,.15],[3.6,-.4],[2.3,-.8],[1,-1.4],[-.2,-1.5]]
    # Visible runoff follows the terrain slope to the sea.
    for i in range(9):
        obj('runoff'+str(i),'circle',5.8,1.3,.13,.13,'#A4E5EB',6)
        motion('runoff'+str(i),'flow',.75+i*.009,1,path=river,repeats=2)
    if aspect=='portrait':
        scale=.53
        for o in objects:
            o['x']*=scale;o['y']*=scale;o['width']*=scale;o['height']*=scale
        for m in motions:m['path']=[[x*scale,y*scale] for x,y in m['path']]
        camera=9;end_camera=8.5
    else:camera=16;end_camera=15.2
    art=dict(palette='ocean',mood='Natural, expansive, and explanatory',rationale='The scene illustrates the physical circulation of water through landscape, clouds, and ocean.',motion='calm',backdrop='minimal')
    scene=dict(start=0,end=duration,kind='illustration',title='The water cycle',items=['Ocean, atmosphere, and land'],cues=[],composition='hero',camera='tracking',transition='dissolve',illustration=dict(background='#C8E5ED',objects=objects,motions=motions,camera_x=0,camera_y=0,camera_width=camera,camera_end_x=.1,camera_end_y=.05,camera_end_width=end_camera))
    # Anchor stage boundaries to actual terms when they exist in a transcript.
    stage_words={'vapor':['evaporation','evaporates','evaporate'],'rain':['precipitation','rainfall','rains'],'runoff':['runoff','collection','collects']}
    for prefix,terms in stage_words.items():
        onset=next((w['start'] for s in segments for w in s.get('words',[]) if w['word'].lower().strip(' .,!?') in terms),None)
        if onset is not None and 0<=onset<duration-.5:
            relevant=[m for m in motions if m['target'].startswith(prefix)]
            old=min(m['start'] for m in relevant)
            for m in relevant:
                m['start']=min(duration-.25,onset+m['start']-old)
                m['end']=max(m['start']+.1,min(duration,m['end']+onset-old))
    return dict(title='Water cycle — illustrated',scenes=[scene],art_direction=art)
