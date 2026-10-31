$ErrorActionPreference = 'Stop'
Set-Location -LiteralPath $PSScriptRoot
$existingPython = Join-Path (Split-Path $PSScriptRoot -Parent) '.transcribe-venv\Scripts\python.exe'
$localPython = Join-Path $PSScriptRoot '.venv\Scripts\python.exe'
if (Test-Path -LiteralPath $localPython) { $studioPython = $localPython }
elseif (Test-Path -LiteralPath $existingPython) { $studioPython = $existingPython }
else {
    python -m venv .venv
    $studioPython = $localPython
    & $studioPython -m pip install -r requirements.txt
    if ($LASTEXITCODE -ne 0) { throw 'Dependency installation failed.' }
}
Write-Host 'Framecraft is starting at http://127.0.0.1:8765'
& $studioPython -m uvicorn backend.app:app --host 127.0.0.1 --port 8765
