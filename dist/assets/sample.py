from manim import *
import numpy as np

config.pixel_width=1080
config.pixel_height=1920
config.frame_width=9
config.frame_height=16
config.frame_rate=30
config.background_color='#0A1020'
BG='#0A1020'; PANEL='#14243B'; INK='#EDF5FF'; DIM='#7992AF'
BLUE='#52B8FF'; GREEN='#46E0B0'; GOLD='#FFBD69'; RED='#FF748C'

class PolishedStack(MovingCameraScene):
    def text(self,s,size=30,color=INK):
        m=Text(s,font='Segoe UI',font_size=size,color=color)
        if m.width>7.5:m.scale_to_fit_width(7.5)
        return m
    def until(self,t):
        # Camera moves use existing narration pauses, preserving absolute cues.
        shots={1.64:(7.7,UP*.5),3.08:(8.4,ORIGIN),12.88:(7.4,DOWN*.5),
               14.68:(7.0,DOWN*.4),19.56:(8.1,DOWN*.6),22.16:(7.9,DOWN*.5),
               31.78:(7.3,DOWN*.1),33.58:(7.8,UP*.1),39.84:(7.5,ORIGIN),
               43.32:(7.5,DOWN*.4),47.88:(8.5,ORIGIN)}
        remaining=t-self.time
        if t in shots and remaining>.18:
            duration=min(.85,remaining)
            if remaining-duration>.015:self.wait(remaining-duration)
            width,center=shots[t]
            self.play(self.camera.frame.animate.set_width(width).move_to(center),run_time=duration,rate_func=smooth)
        elif remaining>.015:self.wait(remaining)
    def title(self,s,kicker=''):
        # Only the concept names remain; objects carry the explanation.
        labels={'STACK':'STACK','LAST IN · FIRST OUT':'LIFO','QUEUE':'QUEUE'}
        self.current_title=VGroup()
        if s in labels:
            self.current_title.add(self.text(labels[s],42,GREEN).move_to(UP*5.3))
        return self.current_title
    def transition(self,*new,dt=.35):
        self.play(*[FadeOut(m,shift=LEFT*.22) for m in list(self.mobjects)],
                  *[FadeIn(m,shift=RIGHT*.22) for m in new],
                  self.camera.frame.animate.set_width(8.4).move_to(ORIGIN),run_time=dt)
    def panel(self,w,h):
        shadows=VGroup(*[RoundedRectangle(width=w+.025*i,height=h+.025*i,corner_radius=.22+.012*i,
            stroke_width=0,fill_color=BLACK,fill_opacity=.018).shift(DOWN*(.09+.009*i)) for i in range(14,0,-1)])
        face=RoundedRectangle(width=w,height=h,corner_radius=.22,stroke_color='#385574',stroke_width=2,
            fill_color=PANEL,fill_opacity=1)
        highlight=Line(LEFT*(w/2-.25)+UP*(h/2-.03),RIGHT*(w/2-.25)+UP*(h/2-.03),color='#527391',stroke_width=1,stroke_opacity=.45)
        return VGroup(shadows,face,highlight)
    def key(self,s,w=2):
        return VGroup(self.panel(w,.75),self.text(s,26)).set_z_index(5)
    def block(self,s,color=BLUE,w=4.7):
        shadow=VGroup(*[RoundedRectangle(width=w+.02*i,height=.85+.02*i,corner_radius=.14+.01*i,
            stroke_width=0,fill_color=BLACK,fill_opacity=.025).shift(DOWN*(.1+.008*i)) for i in range(10,0,-1)])
        box=RoundedRectangle(width=w,height=.85,corner_radius=.14,stroke_color=color,
            stroke_width=2,fill_color='#19324A',fill_opacity=1)
        accent=Line(LEFT*(w/2-.1)+DOWN*.24,LEFT*(w/2-.1)+UP*.24,color=color,stroke_width=4)
        return VGroup(shadow,box,accent,self.text(s,29,color))
    def plate(self,color=BLUE):
        shadow=VGroup(*[Ellipse(width=5.3+i*.045,height=.92+i*.025,stroke_width=0,
            fill_color=BLACK,fill_opacity=.022).shift(DOWN*(.26+i*.008)) for i in range(12,0,-1)])
        lower=Ellipse(width=5.7,height=1.25,fill_color=color,fill_opacity=.65,stroke_color=color).shift(DOWN*.18)
        edge=Ellipse(width=5.7,height=1.25,fill_color='#172B42',fill_opacity=1,stroke_color=color,stroke_width=3)
        face=Ellipse(width=5.45,height=1.1,fill_color='#25445E',fill_opacity=1,stroke_color=color,stroke_width=1.5).shift(UP*.035)
        rim=Ellipse(width=4.25,height=.74,stroke_color=color,stroke_opacity=.65,stroke_width=2,fill_color=color,fill_opacity=.12).shift(UP*.04)
        shine=Arc(radius=1,start_angle=.15,angle=1.1,color=INK,stroke_opacity=.7,stroke_width=3).stretch_to_fit_width(1.5).stretch_to_fit_height(.12).move_to(LEFT*1.45+UP*.35)
        return VGroup(shadow,lower,edge,face,rim,shine)
    def person(self,color):
        head=Circle(radius=.19,fill_color=color,fill_opacity=1,stroke_width=0).shift(UP*.55)
        body=RoundedRectangle(width=.55,height=.62,corner_radius=.17,fill_color=color,fill_opacity=.85,stroke_width=0).shift(UP*.05)
        legs=VGroup(Line(LEFT*.13+DOWN*.2,LEFT*.15+DOWN*.68,color=color,stroke_width=8),Line(RIGHT*.13+DOWN*.2,RIGHT*.15+DOWN*.68,color=color,stroke_width=8))
        return VGroup(head,body,legs)
    def construct(self):
        # Original narration, absolute timestamps from transcript.json.
        title=self.title('A familiar shortcut')
        screen=self.panel(7,4.6).move_to(UP*.7)
        bar=Line(LEFT*3.2+UP*2.4,RIGHT*3.2+UP*2.4,color='#304867')
        dots=VGroup(*[Dot(radius=.06,color=c) for c in [RED,GOLD,GREEN]]).arrange(RIGHT,buff=.13).move_to(LEFT*2.65+UP*2.7)
        editor=VGroup(screen,bar,dots)
        chars=VGroup(*[self.text(c,78) for c in 'HELLO']).arrange(RIGHT,buff=.08).move_to(UP*.65)
        keys=VGroup(self.key('Ctrl'),self.key('+',.8),self.key('Z',1)).arrange(RIGHT,buff=.18).move_to(DOWN*3)
        self.camera.frame.set_width(8.4)
        self.add(title,editor)
        self.until(.58)
        self.play(LaggedStart(*[FadeIn(c,shift=UP*.12) for c in chars],lag_ratio=.14),run_time=.85)
        self.until(1.64)
        self.play(chars[-1].animate.set_color(RED),run_time=.18)
        self.play(FadeOut(chars[-1],shift=DOWN*.5),run_time=.46)
        self.until(3.08)
        self.play(FadeIn(keys),run_time=.32)
        self.until(4.16)
        self.play(Indicate(keys[2],color=GREEN),FadeIn(chars[-1],shift=UP*.5),run_time=.5)
        self.play(chars[-1].animate.set_color(INK),run_time=.16)
        self.until(4.88)
        check=VGroup(Circle(radius=.45,color=GREEN),VMobject(color=GREEN,stroke_width=5).set_points_as_corners([LEFT*.22,DOWN*.18,RIGHT*.25+UP*.22])).move_to(DOWN*4.5)
        self.play(Create(check),run_time=.4)
        self.until(5.68)
        # Objects become a data stack, using the same motion as the physical model.
        title=self.title('STACK')
        blocks=VGroup(*[self.block(str(i+1),GREEN if i==2 else BLUE).move_to(DOWN*(2-i*1.12)) for i in range(3)])
        rail=VGroup(Line(LEFT*2.7+DOWN*2.6,RIGHT*2.7+DOWN*2.6,color=DIM),Line(LEFT*2.7+DOWN*2.6,LEFT*2.7+UP*1.7,color=DIM),Line(RIGHT*2.7+DOWN*2.6,RIGHT*2.7+UP*1.7,color=DIM))
        self.transition(title,rail)
        for b in blocks:
            target=b.get_center();b.shift(UP*3)
            self.play(FadeIn(b),run_time=.14)
            self.play(b.animate.move_to(target),run_time=.48,rate_func=smooth)
        self.until(8.28)
        lifo=self.text('LIFO',45,GREEN).move_to(UP*3.8)
        self.play(FadeIn(lifo),run_time=.4)
        self.until(9.72)
        incoming=Arrow(UP*2.1+RIGHT*1.2,UP*.85+RIGHT*1.2,color=GREEN,buff=0)
        self.play(GrowArrow(incoming),Indicate(blocks[-1],color=GREEN),run_time=.5)
        self.until(10.34)
        self.play(blocks[-1].animate.move_to(UP*2.7),Transform(incoming,Arrow(UP*.8+LEFT*1.2,UP*2+LEFT*1.2,color=GOLD,buff=0)),run_time=.6)
        self.until(11.10)
        # Stack of plates: newest plate arrives, then is removed first.
        plates=VGroup(*[self.plate().move_to(DOWN*(2.5-i*.55)) for i in range(4)])
        table=Line(LEFT*3.4+DOWN*3.2,RIGHT*3.4+DOWN*3.2,color=DIM)
        self.transition(self.title('A stack of plates'),table)
        self.play(LaggedStart(*[FadeIn(p,shift=DOWN*.3) for p in plates],lag_ratio=.13),run_time=.8)
        self.until(12.88)
        newest=self.plate(GREEN).move_to(UP*2.3)
        self.play(FadeIn(newest),run_time=.3)
        self.until(13.78)
        self.play(newest.animate.move_to(DOWN*.3),run_time=.6)
        self.until(14.68)
        path=ArcBetweenPoints(newest.get_center(),RIGHT*4.8+UP*2.5,angle=-PI/3)
        self.play(MoveAlongPath(newest,path),run_time=1.16)
        self.remove(newest)
        self.until(16)
        # Undo history and the editor are animated together.
        frame=self.panel(7.2,2.6).move_to(UP*2.6)
        letters=VGroup(*[self.text(c,55) for c in 'ABC']).arrange(RIGHT,buff=.2).move_to(UP*2.6)
        history=VGroup(*[self.block('Type '+c,GREEN if i==2 else BLUE).move_to(DOWN*(3-i*1.12)) for i,c in enumerate('ABC')])
        arrow=Arrow(UP*1,DOWN*.15,color=DIM)
        self.transition(self.title('Every edit has a history'),frame,arrow)
        self.until(16.86)
        for i in range(3):
            self.play(FadeIn(letters[i]),FadeIn(history[i],shift=DOWN*.5),run_time=.52)
        undo=self.key('Ctrl + Z',3).move_to(DOWN*5)
        self.until(18.98)
        self.play(FadeIn(undo),run_time=.35)
        self.until(19.56)
        curve=CurvedArrow(history[2].get_right(),frame.get_right()+LEFT*.5,angle=PI/2,color=GOLD)
        self.play(Create(curve),history[2].animate.set_color(GOLD),run_time=.65)
        self.play(FadeOut(history[2],shift=UP*.8),FadeOut(letters[2],shift=DOWN*.3),FadeOut(curve),run_time=.65)
        self.until(22.16)
        self.play(Indicate(undo,color=GOLD),run_time=.42)
        self.until(22.78)
        self.play(FadeOut(history[1],shift=UP*.8),FadeOut(letters[1],shift=DOWN*.3),run_time=.75)
        self.until(23.76)
        # Four applications, each activated when it is spoken.
        tiles=VGroup(*[self.panel(3.65,3.6).move_to(np.array([x,y,0])) for x,y in [(-1.95,1.4),(1.95,1.4),(-1.95,-2.55),(1.95,-2.55)]])
        labs=VGroup(*[self.text(s,23,DIM).move_to(t.get_center()+DOWN*1.2) for s,t in zip(['Undo','Browser','Function calls','Expressions'],tiles)])
        self.transition(self.title('Stacks at work'),tiles,labs)
        # undo drawing strokes
        stroke1=Line(LEFT*.6,RIGHT*.5+UP*.5,color=BLUE,stroke_width=7)
        stroke2=Line(RIGHT*.5+UP*.5,RIGHT*.65+DOWN*.35,color=GREEN,stroke_width=7)
        pencil=VGroup(stroke1,stroke2).move_to(tiles[0].get_center()+UP*.25)
        self.play(Create(pencil),run_time=.8)
        self.until(25.76)
        self.play(Uncreate(stroke2),tiles[0].animate.set_stroke(GREEN),run_time=.65)
        self.until(26.68)
        mini=VGroup(*[RoundedRectangle(width=2.3,height=1.3,corner_radius=.14,stroke_color=c,fill_color=c,fill_opacity=.35).shift(RIGHT*i*.13+UP*i*.13) for i,c in enumerate([BLUE,GREEN,GOLD])]).move_to(tiles[1].get_center()+UP*.25)
        self.play(FadeIn(mini),run_time=.22)
        self.play(FadeOut(mini[-1],shift=RIGHT*.4),tiles[1].animate.set_stroke(GREEN),run_time=.5)
        self.until(27.74)
        calls=VGroup(*[self.block(s,BLUE,w=2.5).scale(.7).move_to(tiles[2].get_center()+UP*(-.4+i*.55)) for i,s in enumerate(['main()','a()','b()'])])
        self.play(LaggedStart(*[FadeIn(c,shift=DOWN*.2) for c in calls],lag_ratio=.2),tiles[2].animate.set_stroke(GREEN),run_time=.64)
        self.until(28.6)
        expr=self.text('2 + 3',35,BLUE).move_to(tiles[3].get_center()+UP*.3)
        self.play(FadeIn(expr),run_time=.22)
        self.play(Transform(expr,self.text('5',52,GREEN).move_to(expr)),tiles[3].animate.set_stroke(GREEN),run_time=.52)
        self.until(29.88)
        # Return to the mental model, with continuous plate movement.
        plates=VGroup(*[self.plate(GREEN if i==3 else BLUE).move_to(DOWN*(2-i*.6)) for i in range(4)])
        self.transition(self.title('LAST IN · FIRST OUT'),plates)
        ring=Ellipse(width=5.4,height=1.5,color=GREEN).move_to(plates[-1])
        self.play(Create(ring),run_time=.6)
        self.until(31.78)
        self.play(plates[-1].animate.shift(UP*2),ring.animate.shift(UP*2),run_time=.75)
        self.until(33.58)
        self.play(plates[-1].animate.shift(DOWN*2),ring.animate.shift(DOWN*2),run_time=.7)
        self.play(Indicate(plates[-1],color=GREEN),run_time=.6)
        self.until(35)
        self.play(plates[-1].animate.shift(UP*1.8+RIGHT*2),FadeOut(ring),run_time=.8)
        self.until(36.32)
        # Newest vs oldest, then transform the stack into a FIFO line.
        nodes=VGroup(*[self.block(str(i+1),GOLD if i==0 else GREEN if i==3 else BLUE,w=4).move_to(DOWN*(2.5-i*1.15)) for i in range(4)])
        self.transition(self.title('What if the oldest goes first?'),nodes)
        newest_label=self.text('NEWEST',23,GREEN).next_to(nodes[-1],UP,buff=.35)
        oldest_label=self.text('OLDEST',23,GOLD).next_to(nodes[0],DOWN,buff=.35)
        self.play(FadeIn(newest_label),FadeIn(oldest_label),run_time=.45)
        question=self.text('?',90,GOLD).move_to(UP*3.7)
        self.play(FadeIn(question),run_time=.5)
        self.until(39.84)
        self.play(Indicate(nodes[-1],color=GREEN),run_time=.65)
        self.until(41.24)
        self.play(nodes[-1].animate.shift(UP*.5),run_time=.4)
        self.play(nodes[-1].animate.shift(DOWN*.5),run_time=.4)
        self.until(43.32)
        self.play(Indicate(nodes[0],color=GOLD),run_time=.7)
        self.until(44.7)
        self.play(FadeOut(question),FadeOut(newest_label),FadeOut(oldest_label),run_time=.3)
        self.play(*[n.animate.scale(.38).move_to(LEFT*(2.7-i*1.8)+DOWN*.6) for i,n in enumerate(nodes)],run_time=.8)
        people=VGroup(*[self.person(c).move_to(n.get_center()+UP*.65) for n,c in zip(nodes,[GOLD,BLUE,BLUE,GREEN])])
        self.play(LaggedStart(*[FadeIn(p) for p in people],lag_ratio=.13),run_time=.65)
        self.until(46.46)
        flow=Arrow(RIGHT*3.2+DOWN*2.5,LEFT*3.2+DOWN*2.5,color=GOLD)
        self.play(GrowArrow(flow),run_time=.6)
        self.until(47.88)
        # The queue reveal lands exactly on the spoken word "queue".
        self.remove(self.current_title)
        self.add(self.title('QUEUE','NEXT / FIRST IN · FIRST OUT'))
        self.play(people[0].animate.shift(LEFT*3),nodes[0].animate.shift(LEFT*3),run_time=.65)
        self.play(*[p.animate.shift(LEFT*1.1) for p in people[1:]],*[n.animate.shift(LEFT*1.1) for n in nodes[1:]],run_time=.6)
        self.until(49.8)

