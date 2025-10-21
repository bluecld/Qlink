# Load Control Fix - October 17, 2025

## Problem Summary

After implementing LED polling on October 16, **load control (on/off buttons) stopped working**.

## Root Cause

The LED polling implementation in [app/bridge.py:280-409](../app/bridge.py#L280-L409) was creating a **new socket connection for every station** on every poll cycle:

```python
# Lines 351-356 - THE PROBLEM
for station in sorted(stations):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # NEW socket
    sock.settimeout(2.0)
    sock.connect((VANTAGE_IP, VANTAGE_PORT))
    sock.sendall(f"VLT@ {master} {station}\r".encode("ascii"))
    response = sock.recv(1024).decode("ascii", errors="ignore").strip()
    sock.close()  # Socket goes into TIME_WAIT state
```

### Impact

With 66+ stations configured in [config/loads.json](../config/loads.json):
- **66 new connections every 5 seconds** = 792 connections/minute
- Each closed socket remains in TIME_WAIT for 60-120 seconds
- This exhausted all available ephemeral ports (typically ~28,000-60,000)
- **Result**: Control commands (`VLO@` for load on/off) could not establish connections

### Symptoms

- Load status display worked (uses existing polling connections)
- On/off buttons failed with "Connection refused" or timeout errors
- `netstat -tnp | grep 3040 | wc -l` showed 700+ connections in TIME_WAIT
- System logs showed "Cannot assign requested address" errors

## Solution

**Immediate fix**: Disabled LED polling to restore load control functionality.

Modified [app/bridge.py:754-761](../app/bridge.py#L754-L761):

```python
@app.on_event("startup")
async def startup_event():
    """Start event listener on application startup"""
    logger.info("🚀 Starting Vantage QLink Bridge...")
    # TEMPORARILY DISABLED: LED polling causes port exhaustion
    # This was breaking load control (on/off buttons)
    # start_event_listener()
    logger.info("✅ Bridge ready (LED polling disabled to prevent port exhaustion)")
```

## Verification Steps

To verify the fix works:

1. **Deploy updated code** to Pi at 192.168.0.104
2. **Check port usage** before deployment:
   ```bash
   ssh pi@192.168.0.104
   netstat -tnp 2>/dev/null | grep 3041 | wc -l  # Should show 700+ if polling active
   ```

3. **Restart bridge service**:
   ```bash
   sudo systemctl restart qlink-bridge
   ```

4. **Wait 2-3 minutes** for TIME_WAIT connections to clear

5. **Test load control**:
   ```bash
   # Turn on load 127 (Bar Main Lights)
   curl -X POST http://192.168.0.104:8000/device/127/set \
     -H "Content-Type: application/json" \
     -d '{"switch": "on"}'

   # Should return: {"resp": ""} (success)
   # Should NOT return: {"ok":false,"detail":"Connect error..."}
   ```

6. **Check port usage** after deployment:
   ```bash
   netstat -tnp 2>/dev/null | grep 3041 | wc -l  # Should be 0-5
   ```

7. **Test via Web UI**:
   - Open http://192.168.0.104:8000/ui/
   - Click any On/Off button
   - Should see load turn on/off immediately

## Future Solutions

To re-enable LED polling without breaking load control, implement ONE of these:

### Option A: Single Persistent Socket (Best)
```python
# Create ONE socket and reuse it for all queries
poll_socket = socket.create_connection((VANTAGE_IP, VANTAGE_PORT), timeout=5.0)
poll_socket.settimeout(2.0)

for station in stations:
    try:
        poll_socket.sendall(f"VLT@ {master} {station}\r".encode("ascii"))
        response = poll_socket.recv(1024).decode("ascii").strip()
        # Process response...
    except:
        # Reconnect if socket dies
        poll_socket.close()
        poll_socket = socket.create_connection((VANTAGE_IP, VANTAGE_PORT), timeout=5.0)
```

**Pros**:
- No port exhaustion (1 connection total)
- Fast polling (no connection overhead)
- Works with port 3040

**Cons**:
- Need to handle socket disconnect/reconnect
- May need to buffer responses carefully

### Option B: Dramatically Increase Polling Interval
```python
poll_interval = 60.0  # Poll every 60 seconds instead of 5
```

**Pros**:
- Simple change
- Reduces connections by 12x

**Cons**:
- LED states update slowly (60 second delay)
- Still creates 66 connections per cycle

### Option C: Enable Port 3041 (Requires Vantage Hardware Access)

If you can access the Vantage IP-Enabler web interface:
1. Navigate to http://192.168.1.200 (your Vantage IP)
2. Enable port 3041 (read/write port)
3. Port 3041 supports persistent event monitoring (VOD@/VOS@/VOL@)
4. This gives real-time LED updates without polling

**Pros**:
- Real-time LED updates (<100ms)
- No polling overhead
- No port exhaustion

**Cons**:
- Requires Vantage hardware configuration access
- May not be available on your current test network

## Recommended Approach

1. **Now**: Keep polling disabled, load control works ✅
2. **Short term**: Implement Option A (single persistent socket) if LED polling is needed
3. **Long term**: Enable port 3041 if possible for real-time event monitoring

## Files Modified

- [app/bridge.py](../app/bridge.py#L754-L761) - Disabled LED polling in startup event

## Testing Checklist

- [ ] Deploy code to Pi at 192.168.0.104
- [ ] Restart qlink-bridge service
- [ ] Verify netstat shows low connection count
- [ ] Test load on/off via API (curl)
- [ ] Test load on/off via Web UI
- [ ] Confirm no "Connection refused" errors
- [ ] Check system logs for any errors

## Related Documents

- [PORT_3041_ISSUE.md](PORT_3041_ISSUE.md) - Original port 3041 discovery
- [LED_POLLING_STRATEGY.md](LED_POLLING_STRATEGY.md) - LED polling implementation details
- [PHASE1_COMPLETE.md](PHASE1_COMPLETE.md) - LED state management backend

---

**Status**: Fix implemented, ready for deployment and testing
**Date**: October 17, 2025
**Priority**: CRITICAL - Load control is core functionality
