# Raspberry Pi Model B v1.2 Test Rig Setup Guide

## Hardware Overview
- **Model**: Raspberry Pi Model B v1.2 (2012)
- **CPU**: Single-core ARMv6 @ 700 MHz
- **RAM**: 512 MB
- **Network**: 10/100 Ethernet (no WiFi)
- **Use Case**: Safe offline testing before deploying to production Pi

## Why Use a Test Rig?
- Test VLO commands without risking real loads
- Validate SmartThings Edge integration in isolation
- Debug configuration issues safely
- Learn timing/behavior before production deployment

---

## OS Installation

### Recommended OS
**Raspberry Pi OS Lite (Legacy - Buster)** - Required for ARMv6 support

Download: https://downloads.raspberrypi.org/raspios_oldstable_lite_armhf/images/

### Initial Setup
1. Flash SD card with Raspberry Pi Imager
2. Enable SSH:
   ```bash
   # On SD card boot partition, create empty file:
   touch ssh
   ```
3. Boot Pi with Ethernet connected to your network
4. Find IP: Check router or use `nmap -sn 192.168.1.0/24`
5. SSH in: `ssh pi@<ip>` (default password: `raspberry`)

---

## Software Installation

### Update System
```bash
sudo apt update
sudo apt upgrade -y
```

### Install Dependencies
```bash
sudo apt install -y python3 python3-pip python3-venv git
```

### Clone Repository
```bash
cd ~
git clone https://github.com/<your-repo>/Qlink.git qlink-bridge
# OR copy from Windows:
# scp -r C:\Qlink pi@<pi-ip>:~/qlink-bridge
cd qlink-bridge
```

### Create Virtual Environment
```bash
python3 -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r app/requirements.txt
```

---

## Testing Modes

### Mode 1: Mock Server on Same Pi (Self-Contained)
Perfect for testing bridge logic without any Vantage hardware.

**Terminal 1 - Start Mock Vantage Server:**
```bash
cd ~/qlink-bridge
source venv/bin/activate
python scripts/mock_vantage.py --host 127.0.0.1 --port 2323
```

**Terminal 2 - Start Bridge (pointing at mock):**
```bash
cd ~/qlink-bridge
source venv/bin/activate
export VANTAGE_IP=127.0.0.1
export VANTAGE_PORT=2323
export QLINK_FADE=2.3
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

**From Windows - Test Commands:**
```powershell
# Health check
curl http://<test-pi-ip>:8000/healthz

# Set level
curl -X POST http://<test-pi-ip>:8000/device/251/set `
  -H "Content-Type: application/json" `
  -d '{"level":50}'

# Switch on/off
curl -X POST http://<test-pi-ip>:8000/device/251/set `
  -H "Content-Type: application/json" `
  -d '{"switch":"on"}'

# Raw command
curl "http://<test-pi-ip>:8000/send/VGL%20251"

# Web UI
# Open browser: http://<test-pi-ip>:8000/ui
```

---

### Mode 2: Bridge on Test Pi → Real Vantage (Cautious Testing)
Bridge runs on test Pi but talks to production Vantage system.

**⚠️ WARNING**: This sends real commands to real loads!

**Start Bridge (pointing at production Vantage):**
```bash
cd ~/qlink-bridge
source venv/bin/activate
export VANTAGE_IP=192.168.1.200  # Your real IP-Enabler
export VANTAGE_PORT=23
export QLINK_FADE=2.3
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

**Recommended First Test:**
```powershell
# Pick a non-critical load (hallway light, test outlet, etc.)
# Test device 251 (or whatever you know is safe):
curl -X POST http://<test-pi-ip>:8000/device/251/set `
  -H "Content-Type: application/json" `
  -d '{"switch":"on"}'

# Wait 2 seconds, observe physical load

curl -X POST http://<test-pi-ip>:8000/device/251/set `
  -H "Content-Type: application/json" `
  -d '{"switch":"off"}'
```

---

## Performance Expectations on Model B v1.2

### Startup Time
- **Cold boot to SSH**: ~45-60 seconds
- **Uvicorn startup**: ~5-10 seconds
- **First HTTP request**: ~500ms-1s (cold start)
- **Subsequent requests**: ~100-300ms

### Capacity
- **Concurrent requests**: 1-3 (single core)
- **Memory usage**: ~150MB (bridge + OS)
- **Good for**: Sequential testing, development, debugging
- **Not good for**: Load testing, high concurrency

### Tips for Best Performance
```bash
# Disable GUI (if installed)
sudo systemctl set-default multi-user.target

# Reduce GPU memory (edit /boot/config.txt)
gpu_mem=16

# Disable unnecessary services
sudo systemctl disable bluetooth
sudo systemctl disable avahi-daemon
```

---

## Deployment to Test Rig

### Option 1: Deploy from Windows (like production)
Use your existing VS Code tasks (modify IP):

```powershell
# Edit scripts/deploy.ps1 temporarily to point at test Pi
$PI_HOST = "192.168.1.XXX"  # Test Pi IP

# Run deploy task
# Or manually:
.\scripts\deploy.ps1
```

### Option 2: Manual Sync
```powershell
# Copy files to test Pi
scp -r app config scripts pi@<test-pi-ip>:~/qlink-bridge/

# SSH in and restart
ssh pi@<test-pi-ip>
cd ~/qlink-bridge
sudo systemctl restart qlink-bridge
```

---

## Testing Checklist

### Phase 1: Offline Mock Testing
- [ ] Mock server starts successfully
- [ ] Bridge connects to mock
- [ ] Health endpoint responds: `/healthz`
- [ ] Raw send works: `/send/VGL 251`
- [ ] POST set level works: `{"level":50}`
- [ ] POST switch works: `{"switch":"on"}`
- [ ] Web UI loads at `/ui`
- [ ] Web UI can send commands

### Phase 2: Real Vantage Testing (Cautious)
- [ ] Identify safe test load (non-critical)
- [ ] Verify load current state via Vantage keypad
- [ ] Send ON command via bridge
- [ ] Physically verify load turned on
- [ ] Send OFF command via bridge
- [ ] Physically verify load turned off
- [ ] Test dimming: 0%, 25%, 50%, 75%, 100%
- [ ] Verify fade time works correctly

### Phase 3: SmartThings Integration
- [ ] SmartThings hub can reach test Pi IP
- [ ] Edge driver can call `/healthz`
- [ ] Edge driver can POST to `/device/{id}/set`
- [ ] SmartThings app shows correct state
- [ ] Commands work from SmartThings app

---

## Troubleshooting

### Pi Model B v1.2 Specific Issues

**Problem**: "No space left on device"
```bash
# Check disk usage
df -h
# Clean apt cache
sudo apt clean
# Remove old logs
sudo journalctl --vacuum-time=1d
```

**Problem**: Out of memory errors
```bash
# Check memory
free -h
# Reduce worker processes in systemd unit:
# ExecStart=... --workers 1
```

**Problem**: Slow performance
```bash
# Check CPU usage
top
# Reduce logging verbosity
export LOG_LEVEL=WARNING
```

**Problem**: Network timeouts
```bash
# Increase timeout in bridge
export QLINK_TIMEOUT=5.0
# Check network cable
ethtool eth0
```

---

## Migration to Production Pi

Once testing is complete on Model B v1.2:

1. **Document any config changes** made during testing
2. **Take note of any OS-specific workarounds**
3. **Deploy same code to production Pi** (newer model)
4. **Verify faster performance** on production hardware
5. **Keep test rig** for future development/debugging

### Known Differences Production Pi Will Have:
- ✅ Faster startup (multi-core)
- ✅ More RAM (1-8GB depending on model)
- ✅ Built-in WiFi (if needed)
- ✅ Better concurrent request handling
- ✅ Modern OS support

---

## Summary

**Model B v1.2 as Test Rig: ✅ RECOMMENDED**

✅ **Pros:**
- Safe isolated testing environment
- No risk to production loads
- Learn system behavior offline
- Debug issues without pressure
- Validate SmartThings integration

⚠️ **Cons:**
- Slower performance (not representative of production)
- Requires Legacy OS (Buster)
- Limited concurrent capacity
- No WiFi

**Bottom Line**: Perfect for testing logic, command formats, and integration flows. Just don't use it for performance testing or production load!

---

## Quick Start Commands

```bash
# On Test Pi - Start Mock Server Test
cd ~/qlink-bridge && source venv/bin/activate
python scripts/mock_vantage.py &
export VANTAGE_IP=127.0.0.1 VANTAGE_PORT=2323
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000

# From Windows - Test It
curl http://<test-pi-ip>:8000/healthz
curl -X POST http://<test-pi-ip>:8000/device/251/set -H "Content-Type: application/json" -d '{"level":50}'
```

Good luck with your test rig! 🎯
