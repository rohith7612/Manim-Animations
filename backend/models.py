from typing import Literal
from pydantic import BaseModel, Field, model_validator

KINDS = Literal['plates', 'stack', 'queue', 'editor', 'browser', 'calls', 'expression', 'flow']

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

class Plan(BaseModel):
    title: str = Field(max_length=100)
    scenes: list[Shot] = Field(min_length=1, max_length=40)
    art_direction: ArtDirection | None = None

    def check_timing(self, duration):
        last = 0
        for scene in self.scenes:
            if not (0 <= scene.start < scene.end <= duration + .1):
                raise ValueError('Scene timing must stay inside the source video.')
            if scene.start < last - .01:
                raise ValueError('Scenes must be ordered without overlaps.')
            if scene.end-scene.start < .65:
                raise ValueError('Each scene needs at least 0.65 seconds.')
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
