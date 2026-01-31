# Run AURAMART backend (PowerShell)
# From repo root: .\AURAMART\backend\run.ps1
# From backend:   .\run.ps1

Set-Location $PSScriptRoot

# Prefer venv if present
if (Test-Path ".venv\Scripts\Activate.ps1") {
    .\.venv\Scripts\Activate.ps1
} elseif (Test-Path "venv\Scripts\Activate.ps1") {
    .\venv\Scripts\Activate.ps1
}

# Use python -m so uvicorn doesn't need to be on PATH
python -m uvicorn app.main:app --reload --port 8000
