"""Trusted lesson renderer. PLAN is inserted as data by the server; AI code is never executed.
Every visual change is scheduled at the timestamp of the spoken word it illustrates."""
from manim import *
import os
import json
import time
import textwrap
from pathlib import Path
import manimpango

if 'PLAN' not in globals():
    PLAN=json.loads(Path(os.environ['FRAMECRAFT_PLAN']).read_text(encoding='utf-8'))
ART=PLAN.get('art_direction') or {}
STYLE=ART.get('palette',PLAN.get('style','midnight'))
PAL={'midnight':('#0B1120','#16243A','#5CC7FF','#63E4B7'),
     'paper':('#F2EFE8','#FFFFFF','#2F6FC6','#1A9B7A'),
     'violet':('#151126','#251E40','#AD93FF','#FFBF88'),
     'sunrise':('#FFF2DA','#FFFAF0','#D2672E','#2F8F7B'),
     'ocean':('#071F2B','#0F3346','#65D8E8','#B7EECC'),
     'ember':('#251019','#3D1C27','#FF8E72','#FFD17C')}
BG,PANEL,ACCENT,ACCENT2=PAL.get(STYLE,PAL['midnight'])
LIGHT=STYLE in ['paper','sunrise']
INK='#1F2D42' if LIGHT else '#EEF5FF'
MUTED=interpolate_color(ManimColor(INK),ManimColor(BG),.45)
LINE=interpolate_color(ManimColor(INK),ManimColor(BG),.78)
FONTS=manimpango.list_fonts()
FONT='Segoe UI' if 'Segoe UI' in FONTS else 'DejaVu Sans'
MONO='Cascadia Code' if 'Cascadia Code' in FONTS else 'Consolas' if 'Consolas' in FONTS else 'DejaVu Sans Mono'
config.background_color=BG
portrait=PLAN.get('aspect','portrait')=='portrait'
config.frame_width=9 if portrait else 16
config.frame_height=16 if portrait else 9
quality=PLAN.get('quality','preview')
config.pixel_width=(1080 if portrait else 1920) if quality=='final' else (540 if portrait else 960)
config.pixel_height=(1920 if portrait else 1080) if quality=='final' else (960 if portrait else 540)
config.frame_rate=30
# Safe area: away from platform UI at the top and bottom of portrait video.
W=7.6 if portrait else 13.4
TOP=5.3 if portrait else 3.55
BOTTOM=-5.0 if portrait else -3.7

def fmt(value):
    if value is None:return ''
    return f'{value:,.0f}' if float(value).is_integer() else f'{value:,.1f}'

def T(text,size=36,color=INK,weight=NORMAL,maxw=None,font=None,wrap=None):
    text=str(text)
    if wrap:text='\n'.join(textwrap.wrap(text,wrap)) or ' '
    m=Text(text or ' ',font=font or FONT,font_size=size,color=color,weight=weight,line_spacing=.85)
    if maxw and m.width>maxw:m.scale_to_fit_width(maxw)
    return m

def onscreen(m,margin=.15):
    """Shift a mobject horizontally so it stays inside the frame."""
    half=config.frame_width/2-margin
    if m.get_right()[0]>half:m.shift(LEFT*(m.get_right()[0]-half))
    if m.get_left()[0]<-half:m.shift(RIGHT*(-half-m.get_left()[0]))
    return m

def card(w,h,fill=PANEL,stroke=None,r=.16):
    return RoundedRectangle(corner_radius=r,width=w,height=h,fill_color=fill,fill_opacity=1,stroke_color=stroke or fill,stroke_width=3 if stroke else 0)

class LessonScene(Scene):
    def setup(self):
        self._progress_started=time.time();self._progress_last=0
    def update_mobjects(self,dt):
        super().update_mobjects(dt)
        now=time.time()
        if now-getattr(self,'_progress_last',0)>.75:
            self._progress_last=now
            payload={'started_at':getattr(self,'_progress_started',now),'updated_at':now,'rendered_seconds':float(self.time),'wall_elapsed':now-getattr(self,'_progress_started',now)}
            try:
                path=Path(__file__).resolve().parent/'render-progress.json'
                temp=path.with_suffix('.partial');temp.write_text(json.dumps(payload),encoding='utf-8');temp.replace(path)
            except OSError:pass

    # ---- clock -------------------------------------------------------
    def until(self,t):
        if t-self.time>1/60:self.wait(t-self.time)
    def run(self,events,end):
        """events: [(time, fn -> list of animations)] played exactly at their times."""
        events=sorted(events,key=lambda e:e[0])
        for k,(t,fn) in enumerate(events):
            nxt=events[k+1][0] if k+1<len(events) else end
            self.until(t)
            rt=max(1/15,min(.5,(nxt-self.time)*.85,end-self.time-.03))
            anims=[a for a in fn() if a is not None]
            if anims:self.play(*anims,run_time=rt)

    def construct(self):
        lesson=PLAN['lesson'];beats=lesson['beats']
        for beat in beats:
            old=[m for m in self.mobjects]
            self.until(beat['start'])
            heading=self.heading(beat)
            intro,events=getattr(self,'layout_'+beat['layout'])(beat)
            enter=[m for m in [heading,*intro] if m is not None]
            length=beat['end']-beat['start']
            rt=max(.12,min(.35,length*.3,(min([e[0] for e in events],default=beat['end'])-beat['start'])*.9 or .12))
            anims=[FadeOut(Group(*old),shift=UP*.25)] if old else []
            anims+=[FadeIn(m,shift=UP*.15) for m in enter]
            if anims:self.play(*anims,run_time=rt)
            self.remove(*old)
            self.run(events,beat['end'])
        self.until(PLAN['duration'])

    def heading(self,beat):
        if beat['layout'] in ('title','key_term') or not beat.get('heading'):return None
        label=T(beat['heading'].upper(),34,ACCENT,BOLD,maxw=W-.5)
        bar=Rectangle(width=.12,height=label.height+.12,fill_color=ACCENT,fill_opacity=1,stroke_width=0)
        group=VGroup(bar,label).arrange(RIGHT,buff=.22)
        group.move_to([-W/2+group.width/2,TOP,0]);return group

    def area(self):
        top=TOP-(.9 if portrait else .8)
        return top,BOTTOM

    # ---- layouts -----------------------------------------------------
    def layout_title(self,beat):
        items=beat['items']
        main=beat['heading'] or (items[0]['text'] if items else '')
        title=T(main,76 if portrait else 72,INK,BOLD,maxw=W,wrap=16 if portrait else 28)
        title.move_to(UP*.8)
        line=Line(LEFT,RIGHT,color=ACCENT,stroke_width=8).set_width(min(title.width,3.5)).next_to(title,DOWN,buff=.45)
        events=[(beat['start']+.05,lambda:[Create(line)])]
        subs=items[1:] if not beat['heading'] else items
        for i,it in enumerate(subs[:3]):
            sub=T(it['text'],40,MUTED,maxw=W,wrap=26).next_to(line,DOWN,buff=.45+i*.75)
            events.append((it['time'],lambda s=sub:[FadeIn(s,shift=UP*.2)]))
        return [title],events

    def layout_key_term(self,beat):
        items=beat['items'] or [{'text':beat['heading'],'detail':'','time':beat['start'],'value':None}]
        term=items[0]
        small=T(beat['heading'].upper() if beat['heading'] and beat['heading'].lower()!=term['text'].lower() else 'KEY TERM',32,MUTED,BOLD,maxw=W).move_to(UP*2.2)
        word=T(term['text'],120 if portrait else 110,ACCENT,BOLD,maxw=W-.6)
        pill=card(word.width+1.0,word.height+.8,PANEL,ACCENT,r=.3)
        group=VGroup(pill,word).move_to(UP*.6)
        events=[(term['time'],lambda:[GrowFromCenter(pill),FadeIn(word,scale=.7)])]
        if term.get('detail'):
            d=T(term['detail'],46,INK,maxw=W,wrap=24 if portrait else 40).next_to(group,DOWN,buff=.6)
            events.append((min(term['time']+.45,beat['end']-.2),lambda:[FadeIn(d,shift=UP*.2)]))
        chips=[]
        for it in items[1:4]:
            chips.append((it,VGroup(card(1,1),T(it['text'],36,INK,maxw=W/2))))
        if chips:
            for _,c in chips:c[0].stretch_to_fit_width(c[1].width+.6).stretch_to_fit_height(c[1].height+.4);c[0].move_to(c[1])
            row=VGroup(*[c for _,c in chips]).arrange(RIGHT,buff=.3)
            if row.width>W:row.scale_to_fit_width(W)
            row.move_to(DOWN*(3.4 if portrait else 2.7))
            for it,c in chips:events.append((it['time'],lambda c=c:[FadeIn(c,shift=UP*.2)]))
        return [small],events

    def rows(self,n):
        top,bottom=self.area();n=max(n,1)
        h=min(1.75 if portrait else 1.25,(top-bottom)/n)
        mid=(top+bottom)/2+(.4 if portrait else 0)
        return [mid+(n-1)*h/2-i*h for i in range(n)],h

    def layout_list(self,beat):
        items=beat['items'];ys,h=self.rows(len(items))
        rows=[];events=[];intro=[]
        for i,(it,y) in enumerate(zip(items,ys)):
            badge=VGroup(Circle(radius=min(.4,h*.3),fill_color=ACCENT,fill_opacity=1,stroke_width=0),T(str(i+1),30,BG,BOLD))
            text=T(it['text'],54 if portrait else 46,INK,BOLD,maxw=W-1.3)
            body=VGroup(text)
            if it.get('detail'):body.add(T(it['detail'],34,MUTED,maxw=W-1.3,wrap=30 if portrait else 60))
            body.arrange(DOWN,aligned_edge=LEFT,buff=.12)
            row=VGroup(badge,body).arrange(RIGHT,buff=.38,aligned_edge=UP if it.get('detail') else ORIGIN)
            if body.height>h*.92:row.scale(h*.92/body.height)
            row.move_to([-W/2+row.width/2,y,0]);rows.append(row)
            if it.get('carried'):
                row.set_opacity(.45);intro.append(row)
            else:
                def show(r=row,k=i):
                    dims=[rows[j].animate.set_opacity(.45) for j in range(k) if rows[j] in self.mobjects]
                    return [FadeIn(r[0],scale=.5),FadeIn(r[1],shift=LEFT*.3),*dims]
                events.append((it['time'],show))
        return intro,events

    def layout_roadmap(self,beat):
        items=beat['items'];ys,h=self.rows(len(items))
        x=-W/2+.45;intro=[];events=[];nodes=[]
        for i,(it,y) in enumerate(zip(items,ys)):
            node=VGroup(Circle(radius=.38,fill_color=PANEL,fill_opacity=1,stroke_color=ACCENT,stroke_width=6),T(str(i+1),30,ACCENT,BOLD)).move_to([x,y,0])
            text=T(it['text'],52 if portrait else 44,INK,BOLD,maxw=W-1.5)
            body=VGroup(text)
            if it.get('detail'):body.add(T(it['detail'],32,MUTED,maxw=W-1.5,wrap=30 if portrait else 64))
            body.arrange(DOWN,aligned_edge=LEFT,buff=.1)
            if body.height>h*.9:body.scale(h*.9/body.height)
            body.next_to(node,RIGHT,buff=.35)
            rail=Line([x,ys[i-1]-.38,0],[x,y+.38,0],color=LINE,stroke_width=6) if i else None
            nodes.append((node,body,rail))
            def done(k):
                n=nodes[k][0];return [n[0].animate.set_fill(ACCENT2,1).set_stroke(ACCENT2),n[1].animate.set_color(BG),nodes[k][1].animate.set_opacity(.55)]
            if it.get('carried'):
                node[0].set_fill(ACCENT2,1).set_stroke(ACCENT2);node[1].set_color(BG);body.set_opacity(.55)
                intro+=[m for m in (rail,node,body) if m]
            else:
                def show(k=i):
                    n,b,r=nodes[k]
                    anims=[GrowFromCenter(n),FadeIn(b,shift=LEFT*.3)]+([Create(r)] if r else [])
                    if k and nodes[k-1][0] in self.mobjects and not items[k-1].get('done'):anims+=done(k-1);items[k-1]['done']=True
                    return anims
                events.append((it['time'],show))
        return intro,events

    def layout_comparison(self,beat):
        items=beat['items'];n=len(items) or 1
        values=[it['value'] if it.get('value') is not None else (n-i) for i,it in enumerate(items)]
        top=max([abs(v) for v in values]+[1e-9])
        ys,h=self.rows(n);h=min(h,1.6)
        best=max(range(n),key=lambda i:values[i]) if items else 0
        events=[];bars=[]
        for i,(it,y) in enumerate(zip(items,ys)):
            label=T(it['text'],48,INK,BOLD,maxw=W*.62).move_to([-W/2,y+.42,0],aligned_edge=LEFT)
            track=Rectangle(width=W,height=.55,fill_color=PANEL,fill_opacity=1,stroke_width=0).move_to([0,y-.22,0])
            width=max(.08,W*abs(values[i])/top)
            fill=Rectangle(width=width,height=.55,fill_color=ACCENT,fill_opacity=1,stroke_width=0).move_to([-W/2+width/2,y-.22,0])
            tag=it.get('detail') or (fmt(it['value']) if it.get('value') is not None else '')
            note=T(tag,38,ACCENT,BOLD,maxw=W*.36).move_to([W/2,y+.42,0],aligned_edge=RIGHT) if tag else None
            bars.append(fill)
            events.append((it['time'],lambda l=label,t=track,f=fill,nt=note:[FadeIn(l,shift=RIGHT*.2),FadeIn(t),GrowFromEdge(f,LEFT)]+([FadeIn(nt)] if nt else [])))
        if n>1 and items:
            win=min(max(it['time'] for it in items)+.7,beat['end']-.3)
            if win>max(it['time'] for it in items):events.append((win,lambda:[bars[best].animate.set_fill(ACCENT2)]))
        return [],events

    def layout_diagram(self,beat):
        items=beat['items'];n=len(items)
        edges=beat['edges'] or [{'source':i,'target':i+1,'label':''} for i in range(n-1)]
        top,bottom=self.area()
        zig=portrait and n>4
        cols=1 if portrait else min(n,4)
        nw=(W*.5 if zig else min(W*.7,5.2)) if portrait else min(W/cols*.78,3.6)
        nodes=[]
        for it in items:
            text=T(it['text'],46,INK,BOLD,maxw=nw-.4,wrap=16)
            body=VGroup(text)
            if it.get('detail'):body.add(T(it['detail'],30,MUTED,maxw=nw-.4,wrap=24))
            body.arrange(DOWN,buff=.1)
            nodes.append(VGroup(card(nw,body.height+.45,PANEL,ACCENT),body))
        # Measure, space for arrows and labels, then shrink to the safe area if needed.
        if portrait:
            grid=VGroup(*nodes).arrange(DOWN,buff=.85 if not zig else .55)
            if zig:
                for i,node in enumerate(nodes):node.shift(RIGHT*(-1 if i%2 else 1)*(W/2-nw/2-.05))
        else:
            rows=[VGroup(*nodes[r:r+cols]).arrange(RIGHT,buff=.9) for r in range(0,n,cols)]
            for k,row in enumerate(rows):
                if k%2:row.submobjects.reverse();row.arrange(RIGHT,buff=.9)
            grid=VGroup(*rows).arrange(DOWN,buff=.9)
        if grid.height>top-bottom:grid.scale_to_fit_height(top-bottom)
        if grid.width>W:grid.scale_to_fit_width(W)
        grid.move_to([0,(top+bottom)/2+(.3 if portrait else 0),0])
        shown=set();drawn=set();events=[]
        for i,it in enumerate(items):
            def show(k=i):
                shown.add(k);anims=[FadeIn(nodes[k],scale=.85)]
                for j,e in enumerate(edges):
                    if j not in drawn and e['source'] in shown and e['target'] in shown:
                        drawn.add(j);a,b=nodes[e['source']],nodes[e['target']]
                        d=b.get_center()-a.get_center()
                        if portrait and not zig and abs(e['target']-e['source'])>1:
                            # Skip-level link: arc around the right side instead of through other boxes.
                            arrow=CurvedArrow(a[0].get_right()+RIGHT*.08,b[0].get_right()+RIGHT*.08,angle=-PI/2 if d[1]<0 else PI/2,color=ACCENT2,stroke_width=6,tip_length=.22)
                            anims.append(Create(arrow))
                        else:
                            if abs(d[1])>abs(d[0])*.6:
                                start,end=(a[0].get_bottom(),b[0].get_top()) if d[1]<0 else (a[0].get_top(),b[0].get_bottom())
                            else:
                                start,end=(a[0].get_right(),b[0].get_left()) if d[0]>0 else (a[0].get_left(),b[0].get_right())
                            arrow=Arrow(start,end,buff=.1,color=ACCENT2,stroke_width=7,max_tip_length_to_length_ratio=.35)
                            anims.append(GrowArrow(arrow))
                        if e.get('label'):anims.append(FadeIn(onscreen(T(e['label'],26,ACCENT2,maxw=2.4).next_to(arrow,RIGHT if isinstance(arrow,CurvedArrow) or abs(arrow.get_unit_vector()[1])>.5 else UP,buff=.15))))
                return anims
            events.append((it['time'],show))
        return [],events

    def layout_code(self,beat):
        lines=beat['code'].rstrip().split('\n')[:10]
        texts=[T(l.replace('\t','    ') or ' ',32,INK,font=MONO) for l in lines]
        h=max(t.height for t in texts) if texts else .3
        maxw=max(t.width for t in texts)
        scale=min(1,(W-.8)/maxw) if maxw else 1
        for t in texts:t.scale(scale)
        block=VGroup(*texts).arrange(DOWN,aligned_edge=LEFT,buff=.18*scale)
        panel=card(W,block.height+1.2,'#0D1117' if not LIGHT else '#20252E',r=.2)
        dots=VGroup(*[Dot(radius=.07,color=c) for c in ['#FF5F57','#FEBC2E','#28C840']]).arrange(RIGHT,buff=.14)
        panel.move_to(UP*.4);dots.move_to(panel.get_corner(UL)+RIGHT*.45+DOWN*.3)
        block.move_to(panel).shift(DOWN*.15).align_to(panel,LEFT).shift(RIGHT*.4)
        for t in texts:t.set_color('#E6EDF3')
        events=[(beat['start']+.1,lambda:[LaggedStart(*[FadeIn(t,shift=RIGHT*.15) for t in texts],lag_ratio=.25)])]
        for it in beat['items']:
            k=next((i for i,l in enumerate(lines) if it['text'] and it['text'] in l),None)
            if k is None:continue
            mark=SurroundingRectangle(texts[k],color=ACCENT,buff=.08,corner_radius=.06,stroke_width=4)
            note=T(it['detail'],38,ACCENT,maxw=W,wrap=28).next_to(panel,DOWN,buff=.4) if it.get('detail') else None
            events.append((max(it['time'],beat['start']+.2),lambda m=mark,nt=note:[Create(m)]+([FadeIn(nt)] if nt else [])))
        return [panel,dots],events

    def layout_analogy(self,beat):
        kind=beat['analogy'] if beat['analogy']!='none' else 'stack'
        items=beat['items'];n=max(len(items),1)
        top,bottom=self.area()
        if kind=='queue':
            size=min(1.9,(W-.2)/n/1.12);x0=-(n-1)*size*1.12/2
            slots=[[x0+i*size*1.12,0,0] for i in range(n)]
            def shape(it):
                return VGroup(card(size,size,PANEL,ACCENT,r=.2),T(it['text'],36,INK,BOLD,maxw=size-.25,wrap=8))
            front=T('FRONT',28,MUTED,BOLD).move_to([slots[0][0],-size/2-.5,0]);back=T('BACK',28,MUTED,BOLD).move_to([slots[-1][0],-size/2-.5,0])
            intro=[front,back]
        else:
            plates=kind=='plates';w=min(W*.6,4.8);hh=.62 if plates else min(1.05,(top-bottom-1)/n)
            base=(top+bottom)/2-n*(hh+.1)/2-.3
            slots=[[0,base+hh/2+i*(hh+.1),0] for i in range(n)]
            def shape(it):
                body=card(w,hh,PANEL,ACCENT,r=hh/2 if plates else .14)
                return VGroup(body,T(it['text'],34 if plates else 40,INK,BOLD,maxw=w-.5))
            floor=Line([-w/2-.4,base-.05,0],[w/2+.4,base-.05,0],color=LINE,stroke_width=6)
            intro=[floor]
        mobs=[shape(it) for it in items];present=[]
        marker=T('← TOP',30,ACCENT2,BOLD) if kind!='queue' else None
        def place(anims):
            for k,idx in enumerate(present):anims.append(mobs[idx].animate.move_to(slots[k]))
            if marker is not None and present:
                target=mobs[present[-1]];pos=[slots[len(present)-1][0]+target.width/2+.25+marker.width/2,slots[len(present)-1][1],0]
                anims.append(marker.animate.move_to(pos) if marker in self.mobjects else FadeIn(marker.move_to(pos)))
            return anims
        events=[]
        for i,it in enumerate(items):
            def push(k=i):
                present.append(k);m=mobs[k];m.move_to(slots[len(present)-1]).shift(UP*1.2 if kind!='queue' else RIGHT*1.2)
                return place([FadeIn(m)])
            events.append((it['time'],push))
        for a in beat['actions']:
            if a['action'] in ('pop','dequeue'):
                def remove(k=a['item'],act=a['action']):
                    if k not in present:return []
                    present.remove(k);m=mobs[k]
                    out=[m.animate.shift(UP*1.4 if act=='pop' else LEFT*1.4).set_opacity(0)]
                    return place(out)
                events.append((a['time']+.001,remove))
            elif a['action']=='highlight':
                events.append((a['time']+.001,lambda k=a['item']:[Indicate(mobs[k],color=ACCENT2,scale_factor=1.12)] if k in present else []))
        return intro,events

    def layout_stat(self,beat):
        items=beat['items'] or [{'text':beat['heading'],'detail':'','value':None,'time':beat['start']}]
        it=items[0];events=[]
        label=T(it['text'] if it.get('value') is not None else it.get('detail',''),50,INK,BOLD,maxw=W,wrap=20)
        if it.get('value') is not None:
            v=float(it['value']);places=0 if v.is_integer() else 1
            unit=it.get('detail','') if len(it.get('detail',''))<=6 else ''
            size=200 if portrait else 190
            final=T(f'{v:,.{places}f}{unit}',size,ACCENT,BOLD,maxw=W).move_to(UP*.9)
            tracker=ValueTracker(0)
            # Text-based counter (no LaTeX dependency), anchored where the final number sits.
            number=always_redraw(lambda:T(f'{tracker.get_value():,.{places}f}{unit}',size,ACCENT,BOLD,maxw=W).move_to(final))
            def show():
                self.add(number);return [tracker.animate.set_value(v)]
            events.append((it['time'],show))
            label.next_to(number,DOWN,buff=.7)
        else:
            big=T(it['text'],120,ACCENT,BOLD,maxw=W).move_to(UP*.9)
            events.append((it['time'],lambda:[FadeIn(big,scale=.7)]))
            label.next_to(big,DOWN,buff=.7)
        events.append((min(it['time']+.35,beat['end']-.15),lambda:[FadeIn(label,shift=UP*.2)]))
        return [],events
