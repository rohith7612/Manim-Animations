from typing import Literal
from pydantic import BaseModel, Field, model_validator

KINDS = Literal['plates', 'stack', 'queue', 'editor', 'browser', 'calls', 'expression', 'flow', 'illustration']

class ArtworkAsset(BaseModel):
    id: str = Field(min_length=1,max_length=40,pattern=r'^[a-zA-Z0-9_-]+$')
    role: Literal['background','cutout']
    prompt: str = Field(min_length=20,max_length=3500)
    aspect: Literal['landscape','portrait','square']

class VisualObject(BaseModel):
    id: str = Field(min_length=1,max_length=40,pattern=r'^[a-zA-Z0-9_-]+$')
    shape: Literal['circle','ellipse','rectangle','polygon','path','sun','cloud','droplet','mountain','water','tree','molecule','gear','star','image']
    x: float = Field(ge=-16,le=16)
    y: float = Field(ge=-12,le=12)
    width: float = Field(gt=0,le=32)
    # A valid 20-unit camera in portrait has a 35.56-unit height; artwork
    # overscan adds 16%. Keep backgrounds bounded while allowing that viewport.
    height: float = Field(gt=0,le=48)
    color: str = Field(pattern=r'^#[0-9A-Fa-f]{6}$')
    opacity: float = Field(ge=0,le=1)
    layer: int = Field(ge=-20,le=30)
    points: list[list[float]] = Field(max_length=30)
    asset_id: str = Field(default='',max_length=40,pattern=r'^[a-zA-Z0-9_-]*$')

class ObjectMotion(BaseModel):
    target: str = Field(max_length=40)
    action: Literal['move','flow','rotate','pulse','reveal','hide']
    start: float
    end: float
    path: list[list[float]] = Field(max_length=30)
    repeats: int = Field(ge=1,le=30)
    amount: float = Field(ge=-20,le=20)

class Illustration(BaseModel):
    background: str = Field(pattern=r'^#[0-9A-Fa-f]{6}$')
    objects: list[VisualObject] = Field(min_length=1,max_length=70)
    motions: list[ObjectMotion] = Field(max_length=120)
    camera_x: float = Field(ge=-12,le=12)
    camera_y: float = Field(ge=-8,le=8)
    camera_width: float = Field(ge=4,le=20)
    camera_end_x: float = Field(ge=-12,le=12)
    camera_end_y: float = Field(ge=-8,le=8)
    camera_end_width: float = Field(ge=4,le=20)

class ArtDirection(BaseModel):
    palette: Literal['midnight','paper','violet','sunrise','ocean','ember']
    mood: str = Field(max_length=80)
    rationale: str = Field(max_length=350)
    motion: Literal['precise','playful','calm','bold']
    backdrop: Literal['grid','orbits','minimal']

class CinemaObject(BaseModel):
    id: str = Field(min_length=1,max_length=40,pattern=r'^[a-zA-Z0-9_-]+$')
    shape: Literal['sphere','box','cone','cylinder','torus','plane']
    position: list[float] = Field(min_length=3,max_length=3)
    scale: list[float] = Field(min_length=3,max_length=3)
    color: str = Field(pattern=r'^#[0-9A-Fa-f]{6}$')
    roughness: float = Field(ge=0,le=1)
    metalness: float = Field(ge=0,le=1)
    opacity: float = Field(ge=0,le=1)

class CinemaMotion(BaseModel):
    target: str
    action: Literal['move','rotate','pulse','reveal','hide']
    start: float
    end: float
    path: list[list[float]] = Field(max_length=25)
    repeats: int = Field(ge=1,le=20)
    amount: float = Field(ge=-20,le=20)

class CinemaShot(BaseModel):
    start: float
    end: float
    position: list[float] = Field(min_length=3,max_length=3)
    end_position: list[float] = Field(min_length=3,max_length=3)
    target: list[float] = Field(min_length=3,max_length=3)
    end_target: list[float] = Field(min_length=3,max_length=3)
    fov: float = Field(ge=25,le=80)

class CinemaStage(BaseModel):
    process: Literal['evaporation','condensation','rain','runoff']
    start: float
    end: float
    intensity: float = Field(ge=0,le=1)

class CinemaOverlay(BaseModel):
    text: str = Field(max_length=70)
    start: float
    end: float
    position: Literal['top_left','bottom_left']

class CinemaWorld(BaseModel):
    world: Literal['landscape','space','studio']
    seed: int = Field(ge=0,le=2147483647)
    objects: list[CinemaObject] = Field(max_length=60)
    motions: list[CinemaMotion] = Field(max_length=100)
    shots: list[CinemaShot] = Field(min_length=1,max_length=40)
    stages: list[CinemaStage] = Field(max_length=30)
    overlays: list[CinemaOverlay] = Field(max_length=12)

LAYOUTS=Literal['title','key_term','list','comparison','roadmap','diagram','code','analogy','stat']

class LessonItem(BaseModel):
    text: str = Field(max_length=60)
    detail: str = Field(default='',max_length=80)
    value: float | None = None
    time: float
    carried: bool = False

class LessonEdge(BaseModel):
    source: int = Field(ge=0,le=11)
    target: int = Field(ge=0,le=11)
    label: str = Field(default='',max_length=30)

class LessonAction(BaseModel):
    action: Literal['push','pop','enqueue','dequeue','highlight']
    item: int = Field(ge=0,le=11)
    time: float

class LessonBeat(BaseModel):
    start: float
    end: float
    layout: LAYOUTS
    heading: str = Field(default='',max_length=70)
    items: list[LessonItem] = Field(default_factory=list,max_length=12)
    edges: list[LessonEdge] = Field(default_factory=list,max_length=12)
    code: str = Field(default='',max_length=900)
    analogy: Literal['stack','queue','plates','none'] = 'none'
    actions: list[LessonAction] = Field(default_factory=list,max_length=12)

class Lesson(BaseModel):
    beats: list[LessonBeat] = Field(min_length=1,max_length=60)
    key_terms: list[str] = Field(default_factory=list,max_length=60)
    missing_terms: list[str] = Field(default_factory=list,max_length=60)

    def check(self,duration):
        last=0
        for beat in self.beats:
            if abs(beat.start-last)>.05 or not beat.start<beat.end<=duration+.1:raise ValueError('Lesson beats must cover the narration consecutively.')
            if beat.end-beat.start<.4:raise ValueError('Each lesson beat needs at least 0.4 seconds.')
            for item in beat.items:
                if not beat.start-.01<=item.time<beat.end:raise ValueError(f'Item "{item.text}" must appear inside its beat.')
            for e in beat.edges:
                if max(e.source,e.target)>=len(beat.items):raise ValueError('Diagram arrows must connect existing items.')
            for a in beat.actions:
                if a.item>=len(beat.items) or not beat.start<=a.time<beat.end:raise ValueError('Analogy actions need an existing item and a time inside the beat.')
            if beat.layout=='code' and not beat.code.strip():raise ValueError('Code beats need code.')
            last=beat.end
        if abs(last-duration)>.1:raise ValueError('Lesson beats must cover the whole video.')
        return self

class Cue(BaseModel):
    time: float
    action: Literal['add', 'remove', 'focus', 'restore', 'advance']
    index: int = Field(ge=0, le=7)

class Shot(BaseModel):
    start: float
    end: float
    kind: KINDS
    title: str = Field(max_length=70)
    items: list[str] = Field(min_length=1, max_length=8)
    cues: list[Cue] = Field(max_length=20)
    composition: Literal['hero','cascade','orbit','split'] = 'hero'
    camera: Literal['wide','close','tracking'] = 'tracking'
    transition: Literal['match','slide','dissolve'] = 'match'
    illustration: Illustration | None = None

class Plan(BaseModel):
    title: str = Field(max_length=100)
    scenes: list[Shot] = Field(min_length=1, max_length=40)
    art_direction: ArtDirection | None = None
    artwork: list[ArtworkAsset] = Field(default_factory=list,max_length=4)
    cinema: CinemaWorld | None = None
    lesson: Lesson | None = None

    def check_timing(self, duration):
        if self.lesson:
            # The lesson is the rendered timeline; scenes are storyboard metadata.
            self.lesson.check(duration)
            if self.artwork:raise ValueError('Lesson plans cannot request generated artwork.')
            return self
        if self.cinema:
            ids=[o.id for o in self.cinema.objects]
            if len(ids)!=len(set(ids)):raise ValueError('3D object IDs must be unique.')
            def vector(p):
                return len(p)==3 and all(-200<=x<=200 for x in p)
            for obj in self.cinema.objects:
                if not vector(obj.position) or not all(.01<=x<=40 for x in obj.scale):raise ValueError('3D object dimensions are out of bounds.')
            last=0
            for shot in self.cinema.shots:
                if abs(shot.start-last)>.1 or not 0<=shot.start<shot.end<=duration+.1:raise ValueError('Camera shots must cover the timeline consecutively.')
                if not all(vector(p) for p in [shot.position,shot.end_position,shot.target,shot.end_target]):raise ValueError('Camera coordinates are out of bounds.')
                last=shot.end
            if abs(last-duration)>.1:raise ValueError('Camera shots must cover the whole video.')
            for motion in self.cinema.motions:
                if motion.target not in ids or not 0<=motion.start<motion.end<=duration+.1:raise ValueError('Invalid 3D motion target or timing.')
                if any(not vector(p) for p in motion.path) or (motion.action=='move' and len(motion.path)<2):raise ValueError('3D travel needs bounded path points.')
            for item in [*self.cinema.stages,*self.cinema.overlays]:
                if not 0<=item.start<item.end<=duration+.1:raise ValueError('Physical stages and overlays must stay inside the video.')
            if self.artwork:raise ValueError('Procedural 3D plans cannot request generated artwork.')
            # Cinema has its own validated objects, motion, and complete camera
            # timeline. Legacy 2D illustration metadata is not rendered here.
            return self
        asset_ids=[asset.id for asset in self.artwork]
        if len(set(asset_ids))!=len(asset_ids):raise ValueError('Artwork IDs must be unique.')
        last = 0
        for scene in self.scenes:
            if not (0 <= scene.start < scene.end <= duration + .1):
                raise ValueError('Scene timing must stay inside the source video.')
            if scene.start < last - .01:
                raise ValueError('Scenes must be ordered without overlaps.')
            if scene.end-scene.start < .65:
                raise ValueError('Each scene needs at least 0.65 seconds.')
            if scene.kind=='illustration':
                if scene.illustration is None:raise ValueError('Illustrated scenes need a visual composition, not just text.')
                ids=[o.id for o in scene.illustration.objects]
                if len(set(ids))!=len(ids):raise ValueError('Visual object IDs must be unique within a scene.')
                for obj in scene.illustration.objects:
                    if obj.shape=='image' and obj.asset_id not in asset_ids:raise ValueError('Image object refers to missing artwork.')
                    if any(len(p)!=2 or any(not -32<=v<=32 for v in p) for p in obj.points):raise ValueError('Object points need bounded x/y coordinates.')
                for motion in scene.illustration.motions:
                    if motion.target not in ids:raise ValueError('Motion refers to a missing visual object.')
                    if not scene.start<=motion.start<motion.end<=scene.end+.001:raise ValueError('Object motion must stay inside its scene.')
                    if motion.action in ['move','flow'] and len(motion.path)<2:raise ValueError('Moving objects need a path.')
                    if any(len(p)!=2 or any(not -32<=v<=32 for v in p) for p in motion.path):raise ValueError('Motion paths need bounded x/y coordinates.')
            for cue in scene.cues:
                if not scene.start <= cue.time < scene.end:
                    raise ValueError('Action cues must fall inside their scene.')
                if cue.index >= len(scene.items):
                    raise ValueError('Action item does not exist.')
            scene.cues.sort(key=lambda c:c.time)
            if any(b.time-a.time < .25 for a,b in zip(scene.cues, scene.cues[1:])):
                raise ValueError('Leave at least 0.25 seconds between actions.')
            last = scene.end
        return self

class DirectedPlan(Plan):
    art_direction: ArtDirection
