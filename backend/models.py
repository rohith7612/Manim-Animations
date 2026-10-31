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

    def check_timing(self, duration):
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
