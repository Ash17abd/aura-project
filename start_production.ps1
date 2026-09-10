# AURA 3D Learning Lab — Production Launch Script
Write-Host "=========================================" -ForegroundColor Cyan
Write-Host " Starting AURA 3D Learning Lab Web Server " -ForegroundColor Cyan
Write-Host "=========================================" -ForegroundColor Cyan

$VenvPython = Join-Path $PSScriptRoot "..\.venv\Scripts\python.exe"
if (-not (Test-Path $VenvPython)) {
    $VenvPython = "python"
}

$Port = if ($env:PORT) { $env:PORT } else { "8501" }

Write-Host "Binding to: http://0.0.0.0:$Port" -ForegroundColor Green
Write-Host "Local URL:  http://localhost:$Port" -ForegroundColor Green
Write-Host "Starting Uvicorn web server..." -ForegroundColor DarkCyan

& $VenvPython -m uvicorn web_server:app --host 0.0.0.0 --port $Port
