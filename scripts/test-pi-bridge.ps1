# Quick Test Script for Pi Bridge
# Run this from your Windows laptop to test the Pi bridge

$PI_IP = "192.168.0.180"
$PORT = "8000"
$BASE_URL = "http://${PI_IP}:${PORT}"

Write-Host "=== Testing Qlink Bridge on Pi ===" -ForegroundColor Cyan
Write-Host "Pi IP: $PI_IP" -ForegroundColor Yellow
Write-Host ""

# Test 1: Health check
Write-Host "1. Health Check..." -ForegroundColor Green
try {
    $health = Invoke-RestMethod -Uri "$BASE_URL/healthz" -Method GET
    Write-Host "   ✅ Bridge is healthy!" -ForegroundColor Green
    Write-Host "   Response: $($health | ConvertTo-Json -Compress)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ Health check failed: $_" -ForegroundColor Red
    exit 1
}
Write-Host ""

# Test 2: About endpoint
Write-Host "2. About Info..." -ForegroundColor Green
try {
    $about = Invoke-RestMethod -Uri "$BASE_URL/about" -Method GET
    Write-Host "   Version: $($about.version)" -ForegroundColor Gray
    Write-Host "   Vantage IP: $($about.vantage_ip):$($about.vantage_port)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ About check failed: $_" -ForegroundColor Red
}
Write-Host ""

# Test 3: Send VLO command (turn on device 1 to 50%)
Write-Host "3. Testing VLO Command (Device 1 → 50%)..." -ForegroundColor Green
try {
    $body = @{
        level = 50
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/device/1/set" -Method POST -Body $body -ContentType "application/json"
    Write-Host "   ✅ Command sent!" -ForegroundColor Green
    Write-Host "   Response: $($response.resp)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ VLO command failed: $_" -ForegroundColor Red
    Write-Host "   (This is normal if Vantage system isn't connected yet)" -ForegroundColor Yellow
}
Write-Host ""

# Test 4: Turn device ON
Write-Host "4. Testing ON Command (Device 1)..." -ForegroundColor Green
try {
    $body = @{
        switch = "on"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/device/1/set" -Method POST -Body $body -ContentType "application/json"
    Write-Host "   ✅ ON command sent!" -ForegroundColor Green
    Write-Host "   Response: $($response.resp)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ ON command failed: $_" -ForegroundColor Red
    Write-Host "   (This is normal if Vantage system isn't connected yet)" -ForegroundColor Yellow
}
Write-Host ""

# Test 5: Turn device OFF
Write-Host "5. Testing OFF Command (Device 1)..." -ForegroundColor Green
try {
    $body = @{
        switch = "off"
    } | ConvertTo-Json

    $response = Invoke-RestMethod -Uri "$BASE_URL/device/1/set" -Method POST -Body $body -ContentType "application/json"
    Write-Host "   ✅ OFF command sent!" -ForegroundColor Green
    Write-Host "   Response: $($response.resp)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ OFF command failed: $_" -ForegroundColor Red
    Write-Host "   (This is normal if Vantage system isn't connected yet)" -ForegroundColor Yellow
}
Write-Host ""

# Test 6: Raw VGL command (get load level)
Write-Host "6. Testing VGL Command (Read Device 1)..." -ForegroundColor Green
try {
    $response = Invoke-RestMethod -Uri "$BASE_URL/send/VGL%201" -Method GET
    Write-Host "   ✅ VGL command sent!" -ForegroundColor Green
    Write-Host "   Response: $($response.resp)" -ForegroundColor Gray
} catch {
    Write-Host "   ❌ VGL command failed: $_" -ForegroundColor Red
    Write-Host "   (This is normal if Vantage system isn't connected yet)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "=== Test Complete ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "Next steps:" -ForegroundColor Yellow
Write-Host "- Web UI is at: http://${PI_IP}:${PORT}/ui/" -ForegroundColor White
Write-Host "- To connect to real Vantage, SSH to Pi and set VANTAGE_IP environment variable" -ForegroundColor White
Write-Host "- To test with mock server first, start mock_vantage.py on Pi" -ForegroundColor White
