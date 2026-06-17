# HealSense Backend - Production Start Script

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  🩺 HealSense Backend API - Production Server" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$env:PYTHONPATH = "$PSScriptRoot"
$env:ENV = "production"
$env:DEBUG = "false"

Write-Host "Starting production server with Gunicorn..." -ForegroundColor Yellow
Write-Host "Workers: 4" -ForegroundColor Green
Write-Host "Server: http://0.0.0.0:5000`n" -ForegroundColor Green

# Get the virtual environment Python path
$venvPython = "E:/Github/FYP-Project/.venv/Scripts/python.exe"

# Start with gunicorn
& $venvPython -m gunicorn api.app:app -w 4 -k uvicorn.workers.UvicornWorker -b 0.0.0.0:5000
