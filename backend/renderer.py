"""Trusted renderer. PLAN is inserted as data by the server; AI code is never executed."""
from manim import *
import os
import json
from pathlib import Path

if 'PLAN' not in globals():
    PLAN=json.loads(Path(os.environ['FRAMECRAFT_PLAN']).read_text(encoding='utf-8'))
STYLE=PLAN.get('style','midnight')
PAL={'midnight':('#0B1120','#162840','#5CC7FF','#63E4B7'),
     'paper':('#F2EFE8','#FFFFFF','#3272CB','#1A9B7A'),
     'violet':('#151126','#282044','#AD93FF','#FFBF88')}
BG,PANEL,BLUE,GREEN=PAL[STYLE]
INK='#20324A' if STYLE=='paper' else '#EEF5FF'
config.background_color=BG
portrait=PLAN.get('aspect','portrait')=='portrait'
config.frame_width=9 if portrait else 16
config.frame_height=16 if portrait else 9
quality=PLAN.get('quality','preview')
config.pixel_width=(1080 if portrait else 1920) if quality=='final' else (540 if portrait else 960)
config.pixel_height=(1920 if portrait else 1080) if quality=='final' else (960 if portrait else 540)
config.frame_rate=30

class BrollScene(MovingCameraScene):
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
        return VGroup(shadow,base,face,rim)
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
        elif kind in ['stack','calls']:
            for i,item in enumerate(items):
                obj=VGroup(self.panel(5.4,.88),self.label(item,30,GREEN if i==n-1 else BLUE))
                obj.move_to(UP*((i-(n-1)/2)*1.05));objects.append(obj)
            decor.add(Line(LEFT*3+DOWN*(n*.53+.3),RIGHT*3+DOWN*(n*.53+.3),color=BLUE))
        elif kind=='editor':
            decor.add(self.panel(7,4),Line(LEFT*3.2+UP*1.1,RIGHT*3.2+UP*1.1,color=BLUE,stroke_opacity=.35))
            for i,item in enumerate(items):
                objects.append(self.label(item,62).move_to(RIGHT*((i-(n-1)/2)*min(1.05,5/n))))
            decor.add(self.label('Ctrl + Z',24,BLUE).move_to(DOWN*2.9))
        elif kind=='browser':
            for i,item in enumerate(items):
                card=VGroup(self.panel(6.3,3.6),self.label(item,42),
                    VGroup(*[Dot(radius=.055,color=c) for c in ['#FF748C','#FFBF69',GREEN]]).arrange(RIGHT,buff=.12).move_to(LEFT*2.6+UP*1.4))
                card.move_to(RIGHT*(i-(n-1)/2)*.2+UP*(i-(n-1)/2)*.2);objects.append(card)
            decor.add(self.label('←',48,BLUE).move_to(DOWN*3))
        elif kind=='queue':
            for i,item in enumerate(items):objects.append(self.person(item,GREEN if i==0 else BLUE).move_to(RIGHT*((i-(n-1)/2)*min(1.7,7/n))))
            decor.add(Arrow(RIGHT*3.2+DOWN*2.2,LEFT*3.2+DOWN*2.2,color=GREEN))
        else:
            # Larger process nodes; a simple generic visual for other subjects.
            for i,item in enumerate(items):
                y=((n-1)/2-i)*1.65
                obj=VGroup(self.panel(5.9,1.05),self.label(item,30)).move_to(UP*y);objects.append(obj)
                if i<n-1:decor.add(Arrow(UP*(y-.57),UP*(y-1.08),buff=0,color=BLUE))
        group=VGroup(decor,*objects)
        max_h=10 if portrait else 6.4
        if group.height>max_h:group.scale_to_fit_height(max_h)
        return group,objects
    def wait_to(self,t):
        if t-self.time>.015:self.wait(t-self.time)
    def construct(self):
        active=[]
        for shot in PLAN['scenes']:
            self.wait_to(shot['start'])
            group,objects=self.build(shot)
            hidden={c['index'] for c in shot['cues'] if c['action']=='add'}
            for i in hidden:objects[i].set_opacity(0)
            dt=min(.3,(shot['end']-shot['start'])/4)
            self.play(*[FadeOut(m,shift=LEFT*.15) for m in active],FadeIn(group,shift=RIGHT*.15),
                self.camera.frame.animate.set_width(config.frame_width*.94).move_to(ORIGIN),run_time=dt)
            active=[group]
            for k,cue in enumerate(shot['cues']):
                self.wait_to(cue['time'])
                following=shot['cues'][k+1]['time'] if k+1<len(shot['cues']) else shot['end']
                dt=min(.55,following-self.time-.015)
                if dt<.04:continue
                obj=objects[cue['index']];action=cue['action']
                if action in ['add','restore']:
                    self.play(obj.animate.set_opacity(1),run_time=dt)
                elif action=='remove':
                    motion=LEFT*1.6 if shot['kind']=='queue' else UP*1.2+RIGHT*.6
                    self.play(obj.animate.shift(motion).set_opacity(0),run_time=dt)
                else:
                    center=obj.get_center()*.22
                    self.play(Indicate(obj,color=GREEN,scale_factor=1.06),
                        self.camera.frame.animate.set_width(config.frame_width*.86).move_to(center),run_time=dt)
            self.wait_to(shot['end'])
        self.wait_to(PLAN['duration'])
