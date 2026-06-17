# HealSense API - Quick Integration Test

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "  🧪 HealSense API Integration Test" -ForegroundColor Cyan
Write-Host "============================================================`n" -ForegroundColor Cyan

$baseUrl = "http://localhost:5000/api/v1"
$allTests = @()

# Test 1: Health Check
Write-Host "Test 1: Health Check Endpoint" -ForegroundColor Yellow
try {
    $health = Invoke-RestMethod -Uri "http://localhost:5000/health" -Method Get
    if ($health.status -eq "healthy") {
        Write-Host "✅ Health check passed" -ForegroundColor Green
        $allTests += $true
    } else {
        Write-Host "❌ Health check failed" -ForegroundColor Red
        $allTests += $false
    }
} catch {
    Write-Host "❌ Health check failed: $_" -ForegroundColor Red
    $allTests += $false
}

# Test 2: Get Patient
Write-Host "`nTest 2: Get Patient Profile" -ForegroundColor Yellow
try {
    $patient = Invoke-RestMethod -Uri "$baseUrl/patients/P001/profile" -Method Get
    if ($patient.id -eq "P001" -and $patient.first_name -eq "Muhammad") {
        Write-Host "✅ Patient profile retrieved" -ForegroundColor Green
        Write-Host "   Patient: $($patient.first_name) $($patient.last_name), Age: $($patient.age)" -ForegroundColor Gray
        $allTests += $true
    } else {
        Write-Host "❌ Invalid patient data" -ForegroundColor Red
        $allTests += $false
    }
} catch {
    Write-Host "❌ Failed to get patient: $_" -ForegroundColor Red
    $allTests += $false
}

# Test 3: Get Latest Vitals
Write-Host "`nTest 3: Get Latest Vitals" -ForegroundColor Yellow
try {
    $vitals = Invoke-RestMethod -Uri "$baseUrl/patients/P001/vitals/latest" -Method Get
    if ($vitals.heart_rate -and $vitals.spo2) {
        Write-Host "✅ Vitals retrieved successfully" -ForegroundColor Green
        Write-Host "   HR: $($vitals.heart_rate) bpm, SpO2: $($vitals.spo2)%, Temp: $($vitals.temperature)°C" -ForegroundColor Gray
        Write-Host "   Status: $($vitals.status)" -ForegroundColor Gray
        $allTests += $true
    } else {
        Write-Host "❌ Invalid vitals data" -ForegroundColor Red
        $allTests += $false
    }
} catch {
    Write-Host "❌ Failed to get vitals: $_" -ForegroundColor Red
    $allTests += $false
}

# Test 4: Get Alerts
Write-Host "`nTest 4: Get Patient Alerts" -ForegroundColor Yellow
try {
    $alerts = Invoke-RestMethod -Uri "$baseUrl/patients/P002/alerts" -Method Get
    Write-Host "✅ Alerts endpoint working" -ForegroundColor Green
    Write-Host "   Found $($alerts.Count) alert(s) for P002" -ForegroundColor Gray
    $allTests += $true
} catch {
    Write-Host "❌ Failed to get alerts: $_" -ForegroundColor Red
    $allTests += $false
}

# Test 5: Get Device Status
Write-Host "`nTest 5: Get Device Status" -ForegroundColor Yellow
try {
    $device = Invoke-RestMethod -Uri "$baseUrl/devices/DEV001/status" -Method Get
    if ($device.device_id -eq "DEV001") {
        Write-Host "✅ Device status retrieved" -ForegroundColor Green
        Write-Host "   Device: $($device.device_id), Connected: $($device.connected)" -ForegroundColor Gray
        Write-Host "   Battery: $($device.battery_level)%, Signal: $($device.signal_strength)%" -ForegroundColor Gray
        $allTests += $true
    } else {
        Write-Host "❌ Invalid device data" -ForegroundColor Red
        $allTests += $false
    }
} catch {
    Write-Host "❌ Failed to get device status: $_" -ForegroundColor Red
    $allTests += $false
}

# Test 6: API Documentation
Write-Host "`nTest 6: API Documentation" -ForegroundColor Yellow
try {
    $docs = Invoke-RestMethod -Uri "http://localhost:5000/api/docs" -Method Get
    Write-Host "✅ API documentation accessible" -ForegroundColor Green
    $allTests += $true
} catch {
    Write-Host "❌ API documentation not accessible: $_" -ForegroundColor Red
    $allTests += $false
}

# Summary
Write-Host "`n============================================================" -ForegroundColor Cyan
$passedTests = ($allTests | Where-Object { $_ -eq $true }).Count
$totalTests = $allTests.Count

Write-Host "Test Results: $passedTests / $totalTests tests passed" -ForegroundColor $(if ($passedTests -eq $totalTests) { "Green" } else { "Yellow" })

if ($passedTests -eq $totalTests) {
    Write-Host "`n🎉 All tests passed! Backend is ready for frontend integration!" -ForegroundColor Green
} else {
    Write-Host "`n⚠️  Some tests failed. Check the backend server." -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host ""
