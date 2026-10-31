import json
PLAN=json.loads('{"title": "Undo and Queue: Stacks and Queues Explained", "scenes": [{"start": 0.0, "end": 4.76, "kind": "editor", "title": "Typing and Undo", "items": ["A", "B", "C"], "cues": [{"time": 0.58, "action": "add", "index": 0}, {"time": 0.84, "action": "add", "index": 1}, {"time": 1.1, "action": "add", "index": 2}, {"time": 1.64, "action": "remove", "index": 2}, {"time": 4.16, "action": "restore", "index": 2}], "composition": "hero", "camera": "close", "transition": "match"}, {"start": 4.76, "end": 8.26, "kind": "stack", "title": "Basic Stack Concept", "items": ["typed", "deleted", "undo"], "cues": [{"time": 6.5, "action": "add", "index": 0}, {"time": 7.5, "action": "advance", "index": 2}], "composition": "cascade", "camera": "tracking", "transition": "slide"}, {"start": 8.26, "end": 11.08, "kind": "stack", "title": "LIFO Principle", "items": ["first in", "second", "last in"], "cues": [{"time": 9.5, "action": "focus", "index": 2}], "composition": "cascade", "camera": "wide", "transition": "dissolve"}, {"start": 11.08, "end": 16.0, "kind": "plates", "title": "Stack of Plates Analogy", "items": ["plate1", "plate2", "plate3"], "cues": [{"time": 13.5, "action": "add", "index": 0}, {"time": 14.5, "action": "focus", "index": 0}, {"time": 15.5, "action": "remove", "index": 0}], "composition": "hero", "camera": "close", "transition": "match"}, {"start": 16.0, "end": 18.98, "kind": "stack", "title": "Typing Actions Added to Stack", "items": ["action1", "action2"], "cues": [{"time": 16.8, "action": "add", "index": 0}, {"time": 18.0, "action": "add", "index": 1}], "composition": "cascade", "camera": "tracking", "transition": "slide"}, {"start": 18.98, "end": 23.76, "kind": "stack", "title": "Undo Removes Most Recent", "items": ["action1", "action2"], "cues": [{"time": 19.5, "action": "remove", "index": 1}, {"time": 22.2, "action": "remove", "index": 0}], "composition": "cascade", "camera": "tracking", "transition": "match"}, {"start": 23.76, "end": 29.36, "kind": "flow", "title": "Stack Useful for Undo & More", "items": ["undo", "browser nav", "func calls", "expression eval"], "cues": [{"time": 25.5, "action": "advance", "index": 0}, {"time": 27.0, "action": "advance", "index": 1}, {"time": 28.6, "action": "advance", "index": 2}], "composition": "orbit", "camera": "wide", "transition": "dissolve"}, {"start": 29.36, "end": 36.32, "kind": "stack", "title": "Visualize Stack of Plates", "items": ["plate1", "plate2", "plate3"], "cues": [{"time": 33.0, "action": "focus", "index": 2}], "composition": "hero", "camera": "close", "transition": "match"}, {"start": 36.32, "end": 42.28, "kind": "flow", "title": "Question: Removing Oldest Instead?", "items": ["remove newest", "remove oldest?"], "cues": [{"time": 38.5, "action": "focus", "index": 1}], "composition": "split", "camera": "wide", "transition": "slide"}, {"start": 42.28, "end": 49.783583, "kind": "queue", "title": "Queue: Oldest First Out", "items": ["item1", "item2", "item3"], "cues": [{"time": 45.8, "action": "focus", "index": 0}, {"time": 48.0, "action": "advance", "index": 1}], "composition": "cascade", "camera": "tracking", "transition": "dissolve"}], "art_direction": {"palette": "paper", "mood": "educational, clear, calm", "rationale": "The narration explains fundamental computer science concepts with analogies (typing, plates) in a gentle, clear teaching style. Paper palette is soft and editorial, aiding comprehension. Calm motion and minimal grid backdrop support focus and clarity without distraction.", "motion": "calm", "backdrop": "grid"}, "duration": 49.783583, "style": "paper", "aspect": "portrait", "quality": "preview"}')
"""Trusted renderer. PLAN is inserted as data by the server; AI code is never executed."""
from manim import *
import os
import json
import ast
import operator
from pathlib import Path

if 'PLAN' not in globals():
    PLAN=json.loads(Path(os.environ['FRAMECRAFT_PLAN']).read_text(encoding='utf-8'))
ART=PLAN.get('art_direction') or {}
STYLE=ART.get('palette',PLAN.get('style','midnight'))
PAL={'midnight':('#0B1120','#162840','#5CC7FF','#63E4B7'),
     'paper':('#F2EFE8','#FFFFFF','#3272CB','#1A9B7A'),
     'violet':('#151126','#282044','#AD93FF','#FFBF88'),
     'sunrise':('#FFF2DA','#FFF9EE','#D76F35','#369A86'),
     'ocean':('#071F2B','#103447','#65D8E8','#B7EECC'),
     'ember':('#251019','#441F2B','#FF8E72','#FFD17C')}
BG,PANEL,BLUE,GREEN=PAL.get(STYLE,PAL['midnight'])
INK='#20324A' if STYLE in ['paper','sunrise'] else '#EEF5FF'
config.background_color=BG
portrait=PLAN.get('aspect','portrait')=='portrait'
config.frame_width=9 if portrait else 16
config.frame_height=16 if portrait else 9
quality=PLAN.get('quality','preview')
config.pixel_width=(1080 if portrait else 1920) if quality=='final' else (540 if portrait else 960)
config.pixel_height=(1920 if portrait else 1080) if quality=='final' else (960 if portrait else 540)
config.frame_rate=30

class BrollScene(MovingCameraScene):
    def expression_value(self,items):
        operations={ast.Add:operator.add,ast.Sub:operator.sub,ast.Mult:operator.mul,ast.Div:operator.truediv}
        def value(node):
            if isinstance(node,ast.Constant) and type(node.value) in [int,float] and abs(node.value)<1e6:return node.value
            if isinstance(node,ast.BinOp) and type(node.op) in operations:
                result=operations[type(node.op)](value(node.left),value(node.right))
                if abs(result)<1e9:return result
            raise ValueError('Unsupported expression')
        try:
            result=value(ast.parse(''.join(items),mode='eval').body)
            return f'{result:g}'
        except (ValueError,SyntaxError,ZeroDivisionError,TypeError,OverflowError):return None
    def background(self):
        self.ambient=VGroup()
        for center,color in [(LEFT*3+UP*3,BLUE),(RIGHT*3+DOWN*4,GREEN)]:
            for i in range(8,0,-1):
                self.ambient.add(Circle(radius=.6+i*.48,stroke_width=0,fill_color=color,fill_opacity=.006).move_to(center))
        motif=ART.get('backdrop','grid')
        if motif=='grid':
            for x in range(-10,11):self.ambient.add(Line(RIGHT*x+DOWN*12,RIGHT*x+UP*12,color=BLUE,stroke_width=.5,stroke_opacity=.055))
            for y in range(-12,13):self.ambient.add(Line(LEFT*12+UP*y,RIGHT*12+UP*y,color=BLUE,stroke_width=.5,stroke_opacity=.055))
        elif motif=='orbits':
            rings=VGroup(*[Ellipse(width=8+i*2,height=3+i,stroke_color=BLUE,stroke_width=.7,stroke_opacity=.1).rotate(.4).shift(DOWN*2) for i in range(3)])
            rings.add_updater(lambda m,dt:m.rotate(dt*.018))
            self.ambient.add(rings)
        self.ambient.set_z_index(-10)
        self.add(self.ambient)

    def icon(self,label,color=BLUE):
        word=label.lower()
        if any(w in word for w in ['undo','back','return']):
            return VGroup(Arc(radius=.45,start_angle=-.5,angle=4.4,color=color,stroke_width=5),Triangle(color=color,fill_color=color,fill_opacity=1).scale(.11).rotate(PI/3).shift(LEFT*.45+DOWN*.3))
        if any(w in word for w in ['browser','search','web','page']):
            globe=VGroup(Circle(radius=.5,color=color),Ellipse(width=.45,height=1,color=color),Line(LEFT*.5,RIGHT*.5,color=color))
            return globe
        if any(w in word for w in ['call','function','code','type']):
            return VGroup(self.label('{',48,color).shift(LEFT*.42),self.label('}',48,color).shift(RIGHT*.42),Dot(color=GREEN,radius=.07))
        if any(w in word for w in ['result','out','finish']):
            return VGroup(Circle(radius=.5,color=color),VMobject(color=color,stroke_width=4).set_points_as_corners([LEFT*.28,DOWN*.2,RIGHT*.3+UP*.25]))
        if any(w in word for w in ['idea','think','concept']):
            return VGroup(Circle(radius=.38,color=color).shift(UP*.1),Line(LEFT*.2+DOWN*.35,RIGHT*.2+DOWN*.35,color=color,stroke_width=4),Line(LEFT*.13+DOWN*.47,RIGHT*.13+DOWN*.47,color=color,stroke_width=4))
        return VGroup(*[Circle(radius=.12,fill_color=color,fill_opacity=1,stroke_width=0).move_to(p) for p in [LEFT*.4,UP*.4,RIGHT*.4,DOWN*.4]],Line(LEFT*.4,UP*.4,color=color),Line(UP*.4,RIGHT*.4,color=color),Line(RIGHT*.4,DOWN*.4,color=color))
    def label(self,s,size=34,color=None):
        m=Text(str(s)[:80],font='DejaVu Sans',font_size=size,color=color or INK)
        if m.width>5.8:m.scale_to_fit_width(5.8)
        return m
    def panel(self,w,h):
        shadow=VGroup(*[RoundedRectangle(width=w+i*.025,height=h+i*.025,corner_radius=.18,
            stroke_width=0,fill_color=BLACK,fill_opacity=.025).shift(DOWN*(.12+i*.008)) for i in range(8,0,-1)])
        return VGroup(shadow,RoundedRectangle(width=w,height=h,corner_radius=.18,
            stroke_color=BLUE,stroke_opacity=.45,stroke_width=2,fill_color=PANEL,fill_opacity=1))
    def plate(self,i,n):
        color=GREEN if i==n-1 else BLUE
        shadow=Ellipse(width=6.2,height=1.3,stroke_width=0,fill_color=BLACK,fill_opacity=.2).shift(DOWN*.18)
        base=Ellipse(width=6,height=1.25,fill_color=color,fill_opacity=.55,stroke_color=color).shift(DOWN*.14)
        face=Ellipse(width=6,height=1.25,fill_color=PANEL,fill_opacity=1,stroke_color=color,stroke_width=3)
        rim=Ellipse(width=4.6,height=.8,fill_color=color,fill_opacity=.12,stroke_color=color,stroke_width=1.5)
        shine=Arc(radius=1,start_angle=.2,angle=1.2,color=WHITE,stroke_opacity=.65,stroke_width=3).stretch_to_fit_width(1.6).stretch_to_fit_height(.13).move_to(LEFT*1.5+UP*.36)
        return VGroup(shadow,base,face,rim,shine)
    def person(self,label,color):
        head=Circle(radius=.2,fill_color=color,fill_opacity=1,stroke_width=0).shift(UP*.55)
        body=RoundedRectangle(width=.6,height=.65,corner_radius=.18,fill_color=color,fill_opacity=1,stroke_width=0)
        legs=VGroup(*[Line(RIGHT*x+DOWN*.2,RIGHT*x+DOWN*.7,color=color,stroke_width=7) for x in [-.16,.16]])
        return VGroup(head,body,legs,self.label(label,20,color).move_to(DOWN*1.1))
    def build(self,shot):
        kind=shot['kind'];items=shot['items'];n=len(items)
        objects=[];decor=VGroup()
        if kind=='plates':
            for i in range(n):objects.append(self.plate(i,n).move_to(UP*(-1.8+i*.53)))
            decor.add(Line(LEFT*3.5+DOWN*2.65,RIGHT*3.5+DOWN*2.65,color=BLUE,stroke_opacity=.4))
            decor.add(Ellipse(width=7.1,height=.85,fill_color=BLACK,fill_opacity=.22,stroke_width=0).move_to(DOWN*2.7))
        elif kind in ['stack','calls']:
            for i,item in enumerate(items):
                color=GREEN if i==n-1 else BLUE
                top=Polygon(LEFT*2.7+UP*.44,RIGHT*2.7+UP*.44,RIGHT*2.9+UP*.64,LEFT*2.5+UP*.64,fill_color=color,fill_opacity=.3,stroke_color=color,stroke_width=1)
                side=Polygon(RIGHT*2.7+DOWN*.44,RIGHT*2.9+DOWN*.24,RIGHT*2.9+UP*.64,RIGHT*2.7+UP*.44,fill_color=color,fill_opacity=.2,stroke_color=color,stroke_width=1)
                obj=VGroup(top,side,self.panel(5.4,.88),self.label(item,30,color))
                obj.move_to(UP*((i-(n-1)/2)*1.05));objects.append(obj)
            if kind=='calls':
                for i in range(n-1):decor.add(CurvedArrow(objects[i].get_right()+RIGHT*.2,objects[i+1].get_right()+RIGHT*.2,angle=PI/2,color=GREEN,stroke_width=2))
            decor.add(Line(LEFT*3+DOWN*(n*.53+.3),RIGHT*3+DOWN*(n*.53+.3),color=BLUE))
        elif kind=='editor':
            decor.add(self.panel(7,4),Line(LEFT*3.2+UP*1.1,RIGHT*3.2+UP*1.1,color=BLUE,stroke_opacity=.35))
            decor.add(VGroup(*[Dot(radius=.055,color=c) for c in ['#FF748C','#FFBF69',GREEN]]).arrange(RIGHT,buff=.12).move_to(LEFT*2.85+UP*1.55))
            keyboard=VGroup(*[RoundedRectangle(width=.48,height=.33,corner_radius=.05,stroke_color=BLUE,stroke_opacity=.3,fill_color=PANEL,fill_opacity=1).move_to(RIGHT*((j-4)*.58)+DOWN*(3.35+i*.43)) for i in range(3) for j in range(9)])
            decor.add(keyboard)
            snapshots=n>1 and any(len(item)>1 for item in items)
            for i,item in enumerate(items):objects.append(self.label(item,62))
            if not snapshots:
                row=VGroup(*objects).arrange(RIGHT,buff=.2)
                if row.width>6:row.scale_to_fit_width(6)
                row.move_to(ORIGIN)
            decor.add(self.label('Ctrl + Z',24,BLUE).move_to(DOWN*2.9))
        elif kind=='browser':
            for i,item in enumerate(items):
                content=VGroup(RoundedRectangle(width=1.5,height=1.3,corner_radius=.1,fill_color=BLUE,fill_opacity=.18,stroke_width=0).move_to(LEFT*1.9+DOWN*.3),*[Line(LEFT*.5+DOWN*(.05+j*.32),RIGHT*(2.35-j*.25)+DOWN*(.05+j*.32),stroke_color=BLUE,stroke_opacity=.3,stroke_width=5) for j in range(3)])
                card=VGroup(self.panel(6.3,3.6),self.label(item,30).move_to(UP*.85),content,
                    VGroup(*[Dot(radius=.055,color=c) for c in ['#FF748C','#FFBF69',GREEN]]).arrange(RIGHT,buff=.12).move_to(LEFT*2.6+UP*1.4))
                card.move_to(RIGHT*(i-(n-1)/2)*.2+UP*(i-(n-1)/2)*.2);objects.append(card)
            decor.add(self.label('←',48,BLUE).move_to(DOWN*3))
        elif kind=='queue':
            for i,item in enumerate(items):objects.append(self.person(item,GREEN if i==0 else BLUE).move_to(RIGHT*((i-(n-1)/2)*min(1.7,7/n))))
            decor.add(Arrow(RIGHT*3.2+DOWN*2.2,LEFT*3.2+DOWN*2.2,color=GREEN))
            decor.add(DashedLine(LEFT*3.6+DOWN*.85,RIGHT*3.6+DOWN*.85,dash_length=.16,color=BLUE,stroke_opacity=.25))
        elif kind=='expression':
            for item in items:
                objects.append(VGroup(Circle(radius=.65,fill_color=PANEL,fill_opacity=1,stroke_color=BLUE),self.label(item,42)))
            row=VGroup(*objects).arrange(RIGHT,buff=.4)
            if row.width>7:row.scale_to_fit_width(7)
            row.move_to(ORIGIN)
            decor.add(Arc(radius=2,start_angle=PI,angle=PI,color=BLUE,stroke_opacity=.2).stretch_to_fit_height(.8).shift(DOWN*1.3))
        else:
            composition=shot.get('composition','orbit')
            for i,item in enumerate(items):
                if composition=='orbit' and n<=5:
                    angle=PI/2-i*TAU/n
                    position=np.array([2.5*np.cos(angle),2.5*np.sin(angle),0])
                elif composition=='split':position=RIGHT*((i%2)*3.7-1.85)+UP*((n//2-i//2)*2.4-1)
                else:position=UP*((n-1)/2-i)*2.15
                badge=VGroup(Circle(radius=.8,fill_color=PANEL,fill_opacity=1,stroke_color=BLUE,stroke_opacity=.5),self.icon(item,GREEN if i==n-1 else BLUE))
                label=self.label(item,22).next_to(badge,DOWN,buff=.2)
                if label.width>3:label.scale_to_fit_width(3)
                objects.append(VGroup(badge,label).move_to(position))
            for a,b in zip(objects,objects[1:]):decor.add(DashedLine(a.get_center(),b.get_center(),dash_length=.12,color=BLUE,stroke_opacity=.25).set_z_index(-1))
        group=VGroup(decor,*objects)
        max_h=10 if portrait else 6.4
        if group.height>max_h:group.scale_to_fit_height(max_h)
        if group.width>config.frame_width*.7:group.scale_to_fit_width(config.frame_width*.7)
        return group,objects
    def wait_to(self,t):
        remaining=t-self.time
        if remaining>.3:
            self.play(self.camera.frame.animate.set_width(max(config.frame_width*.75,self.camera.frame.width*.985)),run_time=remaining,rate_func=linear)
        elif remaining>.015:self.wait(remaining)
    def construct(self):
        self.background()
        active=[]
        for shot in PLAN['scenes']:
            self.wait_to(shot['start'])
            group,objects=self.build(shot)
            home_positions=[obj.get_center().copy() for obj in objects]
            home_shapes=[obj.copy() for obj in objects]
            hidden={c['index'] for c in shot['cues'] if c['action']=='add'}
            snapshots=shot['kind']=='editor' and len(shot['items'])>1 and any(len(item)>1 for item in shot['items'])
            if snapshots:
                visible=[i for i in range(len(objects)) if i not in hidden]
                initial=visible[0] if any(c['action'] in ['add','advance'] for c in shot['cues']) else visible[-1] if visible else None
                for i in visible:
                    if i!=initial:objects[i].set_opacity(0)
            for i in hidden:objects[i].set_opacity(0)
            dt=min(.65,(shot['end']-shot['start'])/4)
            width=config.frame_width*({'wide':.98,'close':.82,'tracking':.91}.get(shot.get('camera'),.91))
            transition=shot.get('transition','match')
            if active and transition=='match':
                self.play(FadeTransform(active[0],group,stretch=False),self.camera.frame.animate.set_width(width).move_to(ORIGIN),run_time=dt)
            else:
                shift=RIGHT*.55 if transition=='slide' else UP*.2
                self.play(*[FadeOut(m,shift=-shift) for m in active],
                    LaggedStart(FadeIn(group[0]),*[FadeIn(obj,shift=DOWN*.35,scale=.9) for obj in objects],lag_ratio=.09),
                    self.camera.frame.animate.set_width(width).move_to(ORIGIN),run_time=dt)
                self.add(group)
            active=[group]
            for k,cue in enumerate(shot['cues']):
                self.wait_to(cue['time'])
                following=shot['cues'][k+1]['time'] if k+1<len(shot['cues']) else shot['end']
                dt=min(.55,following-self.time-.015)
                if dt<.04:continue
                obj=objects[cue['index']];action=cue['action']
                if action in ['add','restore'] or (snapshots and action=='advance'):
                    extra=[other.animate.set_opacity(0) for other in objects if other is not obj] if snapshots else []
                    obj.become(home_shapes[cue['index']]).move_to(home_positions[cue['index']]+UP*(.15 if snapshots else 1.5))
                    curve=rate_functions.ease_out_back if ART.get('motion') in ['playful','bold'] else smooth
                    self.play(obj.animate.move_to(home_positions[cue['index']]),*extra,run_time=dt,rate_func=curve)
                elif action=='remove':
                    motion=LEFT*1.6 if shot['kind']=='queue' else UP*1.2+RIGHT*.6
                    extra=[objects[cue['index']-1].animate.set_opacity(1)] if snapshots and cue['index']>0 else []
                    path=ArcBetweenPoints(obj.get_center(),obj.get_center()+motion,angle=-PI/4)
                    self.play(MoveAlongPath(obj,path),*extra,run_time=dt*.65)
                    self.play(obj.animate.set_opacity(0).scale(.82),run_time=dt*.35)
                    if shot['kind']=='queue':
                        survivors=[o for i,o in enumerate(objects) if i>cue['index']]
                        if survivors:
                            available=min(.3,following-self.time-.02)
                            if available>.04:self.play(*[o.animate.shift(LEFT*.45) for o in survivors],run_time=available)
                else:
                    center=obj.get_center()*.08
                    result=self.expression_value(shot['items']) if shot['kind']=='expression' else None
                    if result is not None:
                        answer=VGroup(Circle(radius=1,fill_color=PANEL,fill_opacity=1,stroke_color=GREEN,stroke_width=3),self.label(result,64,GREEN))
                        self.play(*[o.animate.move_to(ORIGIN).set_opacity(0).scale(.6) for o in objects],GrowFromCenter(answer),
                            self.camera.frame.animate.set_width(config.frame_width*.86).move_to(ORIGIN),run_time=dt)
                        group.add(answer)
                    else:
                        self.play(Indicate(obj,color=GREEN,scale_factor=1.06),
                            self.camera.frame.animate.set_width(config.frame_width*.86).move_to(center),run_time=dt)
            self.wait_to(shot['end'])
        self.wait_to(PLAN['duration'])
