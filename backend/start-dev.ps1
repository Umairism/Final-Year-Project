# HealSense Backend - Quick Start Scripts

# Start Development Server
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  🩺 HealSense Backend API - Development Server" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$env:PYTHONPATH = "$PSScriptRoot"

Write-Host "Starting server..." -ForegroundColor Yellow
Write-Host "Server will be available at: http://localhost:5000" -ForegroundColor Green
Write-Host "API Documentation: http://localhost:5000/api/docs" -ForegroundColor Green
Write-Host "Health Check: http://localhost:5000/health`n" -ForegroundColor Green

# Get the virtual environment Python path
$venvPython = "E:/Github/FYP-Project/.venv/Scripts/python.exe"

# Start the server
& $venvPython run.py
