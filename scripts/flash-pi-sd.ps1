# Flash Raspberry Pi OS to SD card for Pi Model B v1.2 (ARMv6)
# SD Card: E:

Write-Host "=== Raspberry Pi SD Card Setup for Model B v1.2 ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "IMPORTANT: Pi Model B v1.2 requires ARMv6 architecture!" -ForegroundColor Yellow
Write-Host "You must use: Raspberry Pi OS (Legacy, 32-bit) Lite" -ForegroundColor Yellow
Write-Host ""
Write-Host "Steps:" -ForegroundColor Green
Write-Host "1. Launch Raspberry Pi Imager (opening now...)" -ForegroundColor White
Write-Host "2. Click 'CHOOSE DEVICE' → Raspberry Pi 1 / Zero" -ForegroundColor White
Write-Host "3. Click 'CHOOSE OS' → Raspberry Pi OS (other) → Raspberry Pi OS (Legacy, 32-bit) Lite" -ForegroundColor White
Write-Host "4. Click 'CHOOSE STORAGE' → Select your E: drive (32GB SD card)" -ForegroundColor White
Write-Host "5. Click gear icon (⚙) for Advanced Options:" -ForegroundColor White
Write-Host "   - Set hostname: pi-test-rig" -ForegroundColor Gray
Write-Host "   - Enable SSH (password authentication)" -ForegroundColor Gray
Write-Host "   - Set username: pi" -ForegroundColor Gray
Write-Host "   - Set password: (your choice)" -ForegroundColor Gray
Write-Host "   - Configure WiFi: (skip - no WiFi on Model B v1.2)" -ForegroundColor Gray
Write-Host "   - Set locale: your timezone/keyboard" -ForegroundColor Gray
Write-Host "6. Click 'WRITE' and confirm" -ForegroundColor White
Write-Host ""
Write-Host "WARNING: This will erase all data on E: drive!" -ForegroundColor Red
Write-Host ""

# Launch Raspberry Pi Imager
Write-Host "Launching Raspberry Pi Imager..." -ForegroundColor Cyan
Start-Process "rpi-imager"

Write-Host ""
Write-Host "After flashing completes:" -ForegroundColor Green
Write-Host "1. Safely eject SD card" -ForegroundColor White
Write-Host "2. Insert into Pi Model B v1.2" -ForegroundColor White
Write-Host "3. Connect Ethernet cable" -ForegroundColor White
Write-Host "4. Power on the Pi" -ForegroundColor White
Write-Host "5. Wait 2-3 minutes for first boot" -ForegroundColor White
Write-Host "6. Find Pi IP: ssh pi@pi-test-rig.local (or check your router)" -ForegroundColor White
Write-Host ""
Write-Host "Next steps after SSH connection: See docs/PI_TEST_RIG_SETUP.md" -ForegroundColor Cyan
