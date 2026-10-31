"""Maintainer tool: publish a rendered procedural 3D demo (data/cinema-demo) as static example assets.

Run from the repository root: python scripts/publish_cinema_demo.py
"""
from pathlib import Path
import json
import shutil
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from backend.app import DATA, load
path=DATA/'cinema-demo';assets=ROOT/'dist'/'assets'
if not (path/'silent.mp4').exists():raise SystemExit('Render the cinema-demo project first.')
job=load('cinema-demo')
for src,dest in [('silent.mp4','cinema-demo.mp4'),('poster.jpg','cinema-demo.jpg'),('source-bundle.zip','cinema-source.zip')]:shutil.copy2(path/src,assets/dest)
job.update(demo_video='/assets/cinema-demo.mp4',demo_poster='/assets/cinema-demo.jpg',sample=True)
(assets/'cinema-sample.json').write_text(json.dumps(job,ensure_ascii=False),encoding='utf-8')
print('Procedural demo published.')
