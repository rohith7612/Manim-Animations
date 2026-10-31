# Code-only video export

Everything visible is generated from code. No artwork or video-generation API is used.

Requirements: Node.js 22.12+, Chrome or Edge, Python with av, numpy, Pillow and pydantic. Install Manim if the plan requests educational overlays.

From the extracted source-bundle root:

    npm ci
    python cinema/export.py

This renders the scene in an isolated headless browser, captures deterministic frames, renders optional transparent Manim overlays, and encodes silent.mp4 using PyAV. You can set FRAMECRAFT_BROWSER, FRAMECRAFT_NODE, and MANIM_PYTHON to choose executables. The bundled dist/cinema/scene.js contains the render code and its Three.js dependencies; npm run build:cinema rebuilds it after source edits.

The original narration is provided separately in the studio's MP4 + narration export. No API key is required to rerender this bundle.
