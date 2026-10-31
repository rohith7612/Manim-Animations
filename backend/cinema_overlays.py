"""Generate transparent educational overlays using Manim, not raster artwork."""
import sys,json
from pathlib import Path
from manim import *
import manimpango
plan=json.loads(Path(sys.argv[1]).read_text(encoding='utf-8'));out=Path(sys.argv[2]);width,height=map(int,sys.argv[3:5])
config.pixel_width=width;config.pixel_height=height;config.frame_width=16 if width>height else 9;config.frame_height=9 if width>height else 16
config.background_opacity=0.0;config.save_last_frame=False;config.write_to_movie=False;config.disable_caching=True
for i,spec in enumerate(plan['cinema']['overlays']):
    scene=Scene()
    label=Text(spec['text'],font='Segoe UI' if 'Segoe UI' in manimpango.list_fonts() else 'DejaVu Sans',font_size=25,color='#F3F8FA')
    if label.width>config.frame_width*.55:label.scale_to_fit_width(config.frame_width*.55)
    label.to_corner(UL if spec['position']=='top_left' else DL,buff=.5)
    backing=RoundedRectangle(width=label.width+.32,height=label.height+.28,corner_radius=.07,fill_color=BLACK,fill_opacity=.38,stroke_width=0).move_to(label)
    underline=Line(label.get_left()+DOWN*.25,label.get_right()+DOWN*.25,color='#8BD9D5',stroke_width=2)
    scene.add(backing,label,underline);scene.renderer.update_frame(scene)
    scene.renderer.camera.get_image().save(out/f'{i}.png')
