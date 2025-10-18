# LED Polling Strategy - Port 3040 Solution

**Date:** October 16, 2025
**Discovery:** YES! We CAN poll button LED states!

---

## Key Discovery: VLS and VLT Commands ✅

### VLS Command - Query Single LED

**Format:** `VLS <master> <station> <led>[CR]`

**Returns:**
- `0` = LED off
- `1` = LED on
- `2` = LED blinking

**Example:**
```
Command:  VLS@ 1 23 5
Response: 1          (LED 5 on station V23 is ON)
```

### VLT Command - Query ALL LEDs on a Station ⭐

**Format:** `VLT <master> <station>[CR]`

**Returns:** `<onleds_hex> <blinkleds_hex>[CR]`

**Example:**
```
Command:  VLT@ 1 23
Response: 4C 20

Decoded:
- 4C hex = 01001100 binary = LEDs 3, 4, 7 are ON
- 20 hex = 00100000 binary = LED 6 is BLINKING
- All other LEDs are OFF
```

**This is PERFECT!** We can query all 8 button LEDs with a single command!

---

## Polling Architecture

### Strategy: Poll All Stations Periodically

Instead of event monitoring (which port 3040 doesn't support), we'll **poll LED states** every few seconds.

### Implementation Plan

#### 1. Poll All Stations on Timer

```python
import asyncio

async def poll_all_station_leds():
    """Poll LED states for all stations every 5 seconds"""
    while True:
        try:
            # Get all station IDs from loads.json
            stations = get_all_stations()  # e.g., [20, 23, 12, 2, ...]

            for station in stations:
                try:
                    # Query all LEDs for this station
                    response = qlink_send(f"VLT@ 1 {station}")
                    # Response: "4C 20\r"

                    parts = response.strip().split()
                    if len(parts) >= 2:
                        on_leds_hex = parts[0]
                        blink_leds_hex = parts[1]

                        # Decode hex to button states (use existing decode_led_hex function!)
                        button_states = decode_led_hex(on_leds_hex, blink_leds_hex)

                        # Update global state
                        update_station_leds(station, button_states)

                        # Broadcast to WebSocket clients
                        await broadcast_led_update(station, button_states)

                    await asyncio.sleep(0.1)  # Rate limit between stations

                except Exception as e:
                    logger.warning(f"Failed to poll station {station}: {e}")
                    continue

            # Wait before next poll cycle
            await asyncio.sleep(5)  # Poll every 5 seconds

        except Exception as e:
            logger.error(f"LED polling error: {e}")
            await asyncio.sleep(5)

# Start on startup
@app.on_event("startup")
async def startup_polling():
    asyncio.create_task(poll_all_station_leds())
```

#### 2. Performance Analysis

**For 71 stations:**
- 71 stations × VLT command
- Each command: ~50-100ms
- **Total per cycle: 3.5-7 seconds**
- **Poll interval: Every 5-10 seconds**

**Result:** LED states update every 5-10 seconds, which is acceptable for UI feedback!

---

## Comparison: Event Monitoring vs Polling

| Feature | Event Monitoring (Port 3041) | LED Polling (Port 3040) |
|---------|----------------------------|------------------------|
| **Availability** | ❌ Not available on your system | ✅ Available now |
| **Latency** | <100ms (instant) | 5-10 seconds |
| **Network Load** | Very low (events only) | Moderate (constant polling) |
| **Button Presses** | Detects presses | ❌ Only sees LED states |
| **LED States** | Real-time | Polled every 5-10s |
| **Automation** | ✅ Can trigger on press | ❌ Can't detect presses |

---

## What We Can Do with Polling

### ✅ Supported Features

1. **Show button LED states in UI**
   - Poll all stations every 5-10 seconds
   - Update UI to show which buttons are lit
   - Show blinking states

2. **Control loads**
   - VLO@ commands work on port 3040
   - Set dimmer levels
   - Turn lights on/off

3. **Press buttons via API**
   - VSW@ commands should work
   - Simulate button presses from UI
   - After press, LED state updates on next poll

4. **Query loads**
   - VGL@ commands work
   - Poll load levels
   - Show current dimmer states

### ❌ Not Supported

1. **Instant LED updates**
   - 5-10 second delay
   - Not real-time

2. **Button press detection**
   - Can't detect when physical button pressed
   - Can only see LED state changes
   - **No automation triggers from physical presses**

3. **Real-time event stream**
   - No WebSocket events from Vantage
   - Can broadcast polled states, but delayed

---

## Implementation Steps

### Phase 1: Test VLT Command

```bash
# SSH to Pi and test VLT command
ssh pi@192.168.1.213
cd qlink-bridge
source .venv/bin/activate

# Test VLT command on station V23
python3 <<EOF
import socket
s = socket.create_connection(("192.168.1.200", 3040), timeout=2.0)
s.send(b"VLT@ 1 23\r")
response = s.recv(1024).decode().strip()
print(f"Station V23 LEDs: {response}")
s.close()
EOF
```

**Expected:** Should return something like `"4C 20"` (hex values for on/blink LEDs)

### Phase 2: Add Polling to bridge.py

**Modify event_listener_loop():**

Since port 3040 doesn't support persistent monitoring connections, replace the event listener with a polling loop:

```python
def led_polling_loop():
    """Background thread that polls LED states"""
    global button_led_states

    logger.info("🔄 LED polling thread started (port 3040 mode)")

    while True:
        try:
            # Get all stations from loads.json
            stations = []
            try:
                with open("app/loads.json", "r") as f:
                    data = json.load(f)
                    for room in data.get("rooms", []):
                        if "station" in room:
                            stations.append(room["station"])
            except:
                pass

            if not stations:
                logger.warning("No stations configured in loads.json")
                time.sleep(10)
                continue

            logger.debug(f"Polling {len(stations)} stations...")

            for station in stations:
                try:
                    # Query all LEDs for this station
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.connect((VANTAGE_IP, VANTAGE_PORT))
                    sock.settimeout(2.0)

                    sock.send(f"VLT@ 1 {station}\r".encode("ascii"))
                    response = sock.recv(1024).decode("ascii").strip()
                    sock.close()

                    # Parse response: "4C 20"
                    parts = response.split()
                    if len(parts) >= 2:
                        on_hex = parts[0]
                        blink_hex = parts[1]

                        # Decode using existing function
                        button_states = decode_led_hex(on_hex, blink_hex)

                        # Update global state
                        update_station_leds(station, button_states)

                        # Create event for WebSocket broadcast
                        event = {
                            "type": "led_poll",
                            "station": station,
                            "station_id": f"V{station}",
                            "on_leds": on_hex,
                            "blink_leds": blink_hex,
                            "button_states": button_states,
                            "timestamp": datetime.now().isoformat()
                        }

                        # Broadcast to WebSocket clients
                        broadcast_event_sync(event)

                        logger.debug(f"📊 V{station}: {button_states}")

                    time.sleep(0.05)  # Rate limit between stations

                except Exception as e:
                    logger.warning(f"Failed to poll V{station}: {e}")
                    continue

            # Wait before next poll cycle
            time.sleep(5)  # Poll every 5 seconds

        except Exception as e:
            logger.error(f"Polling loop error: {e}")
            time.sleep(5)
```

### Phase 3: Update UI

The UI code from Phase 1 still works! Just update the WebSocket handler to expect polling events:

```javascript
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);

    // Handle polled LED states
    if (data.type === 'led_poll' && data.button_states) {
        updateButtonLEDs(data.station, data.button_states);
    }
};
```

---

## Performance Estimates

### Polling 71 Stations

**Best case:** 50ms per station
- 71 × 50ms = 3.55 seconds per cycle
- Poll every 5 seconds
- **Update latency: 5-10 seconds**

**Worst case:** 100ms per station
- 71 × 100ms = 7.1 seconds per cycle
- Poll every 10 seconds
- **Update latency: 10-20 seconds**

**Recommendation:** Start with 5-second interval, adjust based on performance.

### Network Load

- 71 stations × 1 VLT command = 71 queries per cycle
- Every 5 seconds = 14.2 queries/second average
- Moderate network load, should be fine

---

## Benefits of This Approach

1. ✅ **Works with port 3040** (your current setup)
2. ✅ **No config changes needed** (don't touch IP-Enabler)
3. ✅ **Shows button LED states** (main goal achieved!)
4. ✅ **Reuses Phase 1 code** (decode_led_hex, state storage, API endpoints)
5. ✅ **UI integration ready** (WebSocket broadcasts still work)

---

## Limitations

1. ⚠️ **5-10 second delay** for LED updates (not real-time)
2. ❌ **No button press detection** (can't trigger automation)
3. 📈 **Higher network load** than event monitoring

---

## Next Steps

1. ✅ Test VLT command on your Vantage system
2. ✅ Implement polling loop in bridge.py
3. ✅ Deploy to Pi
4. ✅ Test LED state polling
5. ✅ Move to Phase 2 (UI integration)

---

**Conclusion:** YES! We can absolutely implement LED status tracking using **VLT polling** on port 3040. It's not as fast as event monitoring, but it works with your current setup and achieves the main goal: showing button LED states in the UI!

Ready to implement this?
