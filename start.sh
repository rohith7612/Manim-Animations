#!/usr/bin/env bash
# Starts Framecraft on macOS/Linux: ./start.sh
set -euo pipefail
cd "$(dirname "$0")"

# Load KEY=VALUE settings from .env (never committed) without overriding the environment.
if [ -f .env ]; then
  while IFS='=' read -r key value; do
    [[ "$key" =~ ^[[:space:]]*[A-Za-z_][A-Za-z0-9_]*[[:space:]]*$ ]] || continue
    key="$(echo "$key" | xargs)"; value="$(echo "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//' -e "s/^[\"']//" -e "s/[\"']$//")"
    [ -z "${!key:-}" ] && export "$key=$value"
  done < .env
fi

# Python: FRAMECRAFT_PYTHON, or a local .venv created on first run.
PYTHON="${FRAMECRAFT_PYTHON:-}"
if [ -z "$PYTHON" ]; then
  PYTHON=".venv/bin/python"
  if [ ! -x "$PYTHON" ]; then
    echo "Creating .venv and installing Python dependencies..."
    python3 -m venv .venv
    "$PYTHON" -m pip install -r requirements.txt
  fi
fi

# The procedural 3D renderer is optional; build it once when Node.js is available.
if [ ! -f dist/cinema/scene.js ]; then
  NODE="${FRAMECRAFT_NODE:-$(command -v node || true)}"
  if [ -n "$NODE" ]; then
    [ -d node_modules ] || npm ci
    "$NODE" cinema/build.mjs
  else
    echo "Warning: Node.js 22.12+ not found: Force 3D rendering is unavailable. Manim rendering still works." >&2
  fi
fi

PORT="${FRAMECRAFT_PORT:-8765}"
echo "Framecraft is starting at http://127.0.0.1:$PORT"
exec "$PYTHON" -m uvicorn backend.app:app --host 127.0.0.1 --port "$PORT"
