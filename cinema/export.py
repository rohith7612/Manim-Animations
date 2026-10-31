"""Run from the extracted source-bundle root: python cinema/export.py."""
from pathlib import Path
import sys,os,json
root=Path(__file__).resolve().parents[1];sys.path.insert(0,str(root))
from backend.cinematic import render_three
plan=json.loads((root/'plan.json').read_text(encoding='utf-8'))
render_three(plan,root,root/'render-cache',os.environ.get('MANIM_PYTHON',sys.executable))
print(root/'silent.mp4')
