# Port 3041 Issue - Critical for Control Commands

## Problem Summary

The Vantage Q-Link Bridge cannot control loads or buttons because **port 3041 is closed** on the Vantage IP-Enabler device.

## Port Configuration Status

### Port 3040 (Currently Open)
- ✅ **Status**: Open and accessible
- ✅ **Capabilities**: Read-only queries
- ✅ **Supported Commands**:
  - VGL@ - Query load status
  - VLT@ - Query all LED states on a station
  - VLS@ - Query single LED state
- ❌ **NOT Supported**: Control commands (VLO@, VSW@)

### Port 3041 (Currently CLOSED)
- ❌ **Status**: Connection refused - port is closed on IP-Enabler
- ✅ **Capabilities**: Full read/write control
- ✅ **Required For**:
  - VLO@ - Set load levels (on/off buttons, sliders)
  - VSW@ - Simulate button press (scene/faceplate buttons)
  - VOD@, VOS@, VOL@ - Event monitoring
- ⚠️ **Current State**: Disabled/closed on the Vantage IP-Enabler device

## What Works vs What Doesn't

### ✅ Working (Port 3040)
- Display all rooms and loads
- Query current load levels
- Query LED button states
- LED polling and display
- Real-time status monitoring

### ❌ NOT Working (Requires Port 3041)
- On/Off buttons for loads
- Load level sliders
- Scene/faceplate buttons
- Any control commands
- Direct load manipulation

## Testing Performed

```bash
# Port 3040 - SUCCESS
nc -zv 192.168.1.200 3040
# Result: Connection to 192.168.1.200 3040 port [tcp/*] succeeded!

# Port 3041 - FAILED
nc -zv 192.168.1.200 3041
# Result: nc: connect to 192.168.1.200 port 3041 (tcp) failed: Connection refused

# Control command test - FAILED
curl -X POST -H "Content-Type: application/json" -d '{"level": 100}' http://192.168.1.213:8000/device/127/set
# Result: {"ok":false,"detail":"Connect error: [Errno 111] Connection refused"}
```

## Root Cause

The Vantage IP-Enabler (Device Server Configuration Manager Version 1.3.0.0) has port 3041 disabled/closed.

## Solution Required

**You must enable port 3041 on the Vantage IP-Enabler device:**

1. Access the IP-Enabler web interface (usually http://192.168.1.200)
2. Navigate to port configuration settings
3. Enable/open port 3041 (read/write port)
4. Save configuration and reboot the IP-Enabler
5. Restart the qlink-bridge service on the Pi

## Additional Discovery - Port Exhaustion Issue

When LED polling was enabled on port 3040, it created **thousands of TIME_WAIT socket connections**:

```bash
# Found over 700+ connections in TIME_WAIT state
netstat -tnp | grep 3040 | wc -l
# Result: 700+
```

**Cause**: Polling loop creates new socket for each station query (66 stations × every 5 seconds)

**Impact**: Exhausted available ephemeral ports, preventing new connections

**Solution**: Either:
- Use port 3041 which allows persistent connections
- Drastically reduce polling frequency (60+ seconds)
- Reuse single connection for all queries

## Current Configuration

**Bridge Settings** (on Pi at 192.168.1.213):
- VANTAGE_IP: 192.168.1.200
- VANTAGE_PORT: 3041 (configured but port is closed)
- Service: qlink-bridge.service
- Config: /etc/systemd/system/qlink-bridge.service

**IP-Enabler**:
- IP Address: 192.168.1.200
- Port 3040: Open (read-only)
- Port 3041: Closed (needs to be opened)
- Device: Vantage IP-Enabler with Device Server Configuration Manager v1.3.0.0

## Files Modified for This Issue

- `app/bridge.py` - Added retry logic for connection refused errors
- `app/static/home-v2.html` - Added button debouncing (500ms)
- `config/targets.json` - Updated to use port 3040/3041
- `/etc/systemd/system/qlink-bridge.service` - Environment variables for port config

## Next Steps

1. **Critical**: Enable port 3041 on Vantage IP-Enabler
2. Update bridge to use port 3041 after it's enabled
3. Test all control commands
4. Re-enable LED polling if desired (but consider port exhaustion)

## Temporary Workaround

Currently running on port 3040 with:
- Read-only status display
- LED state monitoring (when polling enabled)
- No control functionality

This allows viewing system state but not controlling it.

---

**Date**: October 16, 2025
**Status**: Port 3041 must be enabled on IP-Enabler for full functionality
