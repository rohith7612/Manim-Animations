"""Projects created before image generation was retired must still validate and render."""
import pytest
from backend.models import Plan, ArtworkAsset
from backend.nature import water_cycle
from backend.planner import normalize_plan

def legacy(aspect='landscape'):
    p=Plan.model_validate(water_cycle([],8,aspect))
    p.artwork=[ArtworkAsset(id='backdrop',role='background',aspect=aspect,prompt='A painted ocean and mountain landscape.'),
               ArtworkAsset(id='unused',role='cutout',aspect='square',prompt='An isolated subject that has no placement.')]
    return p

def test_legacy_background_is_placed_and_unused_cutouts_dropped():
    result=normalize_plan(legacy(),8,aspect='landscape')
    assert [a.id for a in result.artwork]==['backdrop']
    assert any(o.shape=='image' and o.asset_id=='backdrop' for o in result.scenes[0].illustration.objects)

def test_missing_asset_references_are_rejected():
    p=normalize_plan(legacy(),8,aspect='landscape');p.artwork=[]
    with pytest.raises(ValueError,match='missing artwork'):p.check_timing(8)

@pytest.mark.parametrize('camera_width',[14,20])
def test_portrait_background_covers_valid_wide_camera(camera_width):
    p=legacy('portrait');p.artwork=p.artwork[:1]
    data=p.scenes[0].illustration
    data.camera_width=camera_width;data.camera_end_width=camera_width
    result=Plan.model_validate(normalize_plan(p,8,aspect='portrait').model_dump()).check_timing(8)
    bg=next(o for o in result.scenes[0].illustration.objects if o.shape=='image')
    assert bg.height==pytest.approx(camera_width*1.16*16/9)
    assert camera_width*16/9<=bg.height<=48
