# Starts Framecraft on Windows: .\start.ps1
$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot

# Load KEY=VALUE settings from .env (never committed) into this process.
if (Test-Path -LiteralPath '.env') {
    Get-Content -LiteralPath '.env' | ForEach-Object {
        if ($_ -match '^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$' -and -not [Environment]::GetEnvironmentVariable($Matches[1])) {
            [Environment]::SetEnvironmentVariable($Matches[1], $Matches[2].Trim('"').Trim("'"), 'Process')
        }
    }
}

# Python: FRAMECRAFT_PYTHON, or a local .venv created on first run.
$python = $env:FRAMECRAFT_PYTHON
if (-not $python) {
    $python = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
    if (-not (Test-Path -LiteralPath $python)) {
        Write-Host 'Creating .venv and installing Python dependencies...'
        python -m venv .venv
        & $python -m pip install -r requirements.txt
        if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
    }
}

# The procedural 3D renderer is optional; build it once when Node.js is available.
if (-not (Test-Path -LiteralPath 'dist\cinema\scene.js')) {
    $node = if ($env:FRAMECRAFT_NODE) { $env:FRAMECRAFT_NODE } else { (Get-Command node -ErrorAction SilentlyContinue).Source }
    if ($node) {
        if (-not (Test-Path -LiteralPath 'node_modules')) { npm ci; if ($LASTEXITCODE -ne 0) { throw 'npm ci failed.' } }
        & $node cinema/build.mjs
    } else {
        Write-Warning 'Node.js 22.12+ not found: Force 3D rendering is unavailable. Manim rendering still works.'
    }
}

$port = if ($env:FRAMECRAFT_PORT) { $env:FRAMECRAFT_PORT } else { '8765' }
Write-Host "Framecraft is starting at http://127.0.0.1:$port"
& $python -m uvicorn backend.app:app --host 127.0.0.1 --port $port
