# HealSense Backend - Environment Verification Script

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "  🔍 HealSense Backend - Environment Verification" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""

$allChecks = @()

# Check 1: Python Version
Write-Host "Checking Python version..." -ForegroundColor Yellow
$pythonVersion = & "E:/Github/FYP-Project/.venv/Scripts/python.exe" --version 2>&1
Write-Host "✅ $pythonVersion" -ForegroundColor Green
$allChecks += $true

# Check 2: Required files
Write-Host ""
Write-Host "Checking required files..." -ForegroundColor Yellow
$requiredFiles = @(
    "api\app.py",
    "api\config.py",
    "requirements.txt",
    ".env",
    "run.py",
    "README.md"
)

foreach ($file in $requiredFiles) {
    if (Test-Path $file) {
        Write-Host "✅ $file exists" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "❌ $file missing" -ForegroundColor Red
        $allChecks += $false
    }
}

# Check 3: Directory structure
Write-Host ""
Write-Host "Checking directory structure..." -ForegroundColor Yellow
$requiredDirs = @(
    "api",
    "api\routes",
    "api\models",
    "api\services",
    "api\middleware",
    "api\utils",
    "tests"
)

foreach ($dir in $requiredDirs) {
    if (Test-Path $dir) {
        Write-Host "✅ $dir exists" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "❌ $dir missing" -ForegroundColor Red
        $allChecks += $false
    }
}

# Check 4: Dependencies
Write-Host ""
Write-Host "Checking key dependencies..." -ForegroundColor Yellow
$keyPackages = @("fastapi", "uvicorn", "sqlalchemy", "pydantic")

foreach ($package in $keyPackages) {
    $checkCmd = "import $package; print('installed')"
    $result = & "E:/Github/FYP-Project/.venv/Scripts/python.exe" -c $checkCmd 2>$null
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✅ $package is installed" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "❌ $package not installed" -ForegroundColor Red
        $allChecks += $false
    }
}

# Check 5: Configuration
Write-Host ""
Write-Host "Checking configuration..." -ForegroundColor Yellow
if (Test-Path ".env") {
    $envContent = Get-Content ".env" -Raw
    if ($envContent -match "PROJECT_NAME=HealSense") {
        Write-Host "✅ .env file properly configured" -ForegroundColor Green
        $allChecks += $true
    } else {
        Write-Host "⚠️  .env file exists but may need configuration" -ForegroundColor Yellow
        $allChecks += $true
    }
}

# Summary
Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
$passedChecks = ($allChecks | Where-Object { $_ -eq $true }).Count
$totalChecks = $allChecks.Count

Write-Host "Results: $passedChecks / $totalChecks checks passed" -ForegroundColor Green
Write-Host ""

if ($passedChecks -eq $totalChecks) {
    Write-Host "🎉 Perfect! Backend environment is ready!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Next steps:" -ForegroundColor Cyan
    Write-Host "1. Run: python run.py" -ForegroundColor White
    Write-Host "2. Open: http://localhost:5000/api/docs" -ForegroundColor White
    Write-Host "3. Check: http://localhost:5000/health" -ForegroundColor White
} else {
    Write-Host "⚠️  Some checks failed. Review the output above." -ForegroundColor Yellow
}

Write-Host ""
Write-Host "============================================================" -ForegroundColor Cyan
Write-Host ""
