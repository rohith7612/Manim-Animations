# Framecraft

A working local video-to-animated-B-roll studio with a private hosted interface preview.

## Start on this computer

Run `start.ps1` in PowerShell, then open http://127.0.0.1:8765.

1. Open Settings and enter your OpenAI API key. It stays in server memory. Alternatively select the built-in planner to work without an API key.
2. Upload a narrated video (200 MB maximum, 3 minutes maximum).
3. Choose portrait or landscape, and preview or full-HD output. AI automatically selects the palette, mood, motion character, background, composition, and camera treatment from the narration's tone and subject. There is no visual-style picker.
4. Create the scene plan. Review the transcript and storyboard. Use Edit plan to adjust exact labels, scene types, and action timestamps.
5. Render. Download the MP4 with original audio, silent MP4, Manim source, transcript, and scene plan.

An actual rendered example of the stack lesson is included. New projects use the reusable renderer and are not copies of that example's hand-authored animation.

## Technologies

Python/FastAPI API; SQLite project records; local disk uploads and exports; single-worker processing queue; Faster-Whisper Small (CPU/int8) word timestamps; NumPy audio processing; OpenAI Responses API structured scene planning; Manim Community rendering; PyAV decoding/audio muxing; Pillow posters; responsive HTML/CSS/JavaScript frontend.

OpenAI receives the timestamped transcript and creative direction, not the uploaded video. Transcription runs locally. Mood is inferred from the narration's language, rather than acoustic emotion analysis. The model returns validated data, never executable Python. Its art-direction decision is shown with the storyboard. The built-in planner uses a clearly labelled keyword-based fallback when AI planning is disabled.

The renderer now also accepts open visual compositions: positioned shapes, custom polygons and paths, layered scenery, particles, repeatable object motion, and camera tracks. AI can design an actual landscape, mechanism, molecular model, or other scene rather than selecting a text-card template. Illustration shots contain no on-screen text. These scenes use bounded, validated geometry and motion data; arbitrary model-written Python is never executed.

The built-in planner includes a water-cycle reference scene with sunlight, evaporation particles, cloud formation, rain, and runoff. AI planning can compose its own worlds using the illustration schema for science, nature, mechanisms, and other subjects. The included 24-second water-cycle video is a silent capability demo, not a render of a user-provided water-cycle narration.

This is stylized 2D/2.5D animation with layered scenery and camera movement. It is not a photorealistic 3D engine, a fluid simulation, or an unrestricted text-to-video generator. Blender rendering and imported/generated art assets would be separate extensions. Existing computer-science scene types remain available for appropriate topics.

## Configuration

- `OPENAI_API_KEY`: optional server environment key instead of Settings.
- `OPENAI_MODEL`: planning model, defaults to `gpt-4.1-mini`; adjustable in Settings.
- `MANIM_PYTHON`: Python executable with Manim installed. On this machine it automatically discovers `~/manimations/.venv/Scripts/python.exe`.
- `WHISPER_MODEL`: defaults to `small`. First use downloads the model if it is not cached.
- `WHISPER_CACHE`: defaults to the existing `.whisper-models` directory beside this project.
- `FRAMECRAFT_DATA`: upload/project/output directory, defaults to `data/` (ignored by source control).

For another machine: use Python 3.12+, install requirements.txt and Manim with its native dependencies, then run `python -m uvicorn backend.app:app --host 127.0.0.1 --port 8765`. Set MANIM_PYTHON when the renderer uses another environment. Use one server process; the included queue is for a personal studio, not a distributed production worker.

## Hosted interface

The private Sites deployment hosts the interface and a playable real example. It does not run Python or Manim. Its Open local studio button opens the installed local service. To support remote customers, deploy the Python service on compute with Cairo/Pango and Manim, add authentication, tenant-separated storage, upload limits at the reverse proxy, and an external durable worker queue. No remote Python service has been deployed as part of this local build.

## Development checks

Install requirements-dev.txt, then run `python -m pytest tests -q`.

`setup_sample.py` installs the existing local stack output as the example. It is specific to the source video and files from this workspace. The app works for new uploads without it.

Keys entered in Settings are cleared when the process restarts. Projects remain on disk. Interrupted jobs are marked with a retryable error on restart. Rendering has a 30-minute timeout. Inputs are treated as media/data; uploaded filenames never become executable commands. No endpoint accepts generated Python to execute.
