# Vantage Q-Link Event Monitoring for External Automation

**Question:** Can the Vantage Q-Link system trigger an outside automation system?

**Answer:** YES! ✅ Vantage has powerful real-time event monitoring commands that can stream all system activity to external automation systems.

---

## Overview

Vantage Q-Link provides three monitoring commands that output real-time events over the RS-232 connection. These enable external systems (like your Pi bridge, SmartThings, Home Assistant, etc.) to:

- **React to button presses** instantly
- **Monitor load changes** as they happen
- **Track LED state changes** for feedback
- **Trigger external automations** based on Vantage events

---

## The Three Monitoring Commands

### 1. VOS@ - Monitor Button/Switch Presses ⭐

**Command:** `VOS@ <format> <enable>[CR]`

**Purpose:** Outputs information whenever a station button or IR button is pressed or released.

**Parameters:**
- `<format>`:
  - `0` = Do not include station serial number
  - `1` = Include station serial number
- `<enable>`:
  - `0` = Disable monitoring
  - `1` = Enable monitoring

**Output Format (format=0):**
```
SW <master> <station> <button> <state>[CR]
```

**Example Output:**
```
SW 1 23 5 1[CR]    # Button 5 pressed on station V23
SW 1 23 5 0[CR]    # Button 5 released on station V23
```

**With Serial Number (format=1):**
```
SW 1 23 5 1 10345[CR]
```

**Use Cases:**
- Trigger external automation when "Game Room On" button pressed
- Send notifications when specific buttons are used
- Log button press history to external database
- Sync Vantage scenes with SmartThings/HomeKit

---

### 2. VOL@ - Monitor Load Changes 💡

**Command:** `VOL@ <enable>[CR]`

**Purpose:** Outputs information whenever a load level changes.

**Parameters:**
- `<enable>`:
  - `0` = Disable monitoring
  - `1` = Enable monitoring

**Output Formats:**

**Module Load:**
```
LO <master> <enclosure> <module> <load> <level>[CR]
```

**Station Load:**
```
LS <master> <station> <load> <level>[CR]
```

**Variable Load:**
```
LV <master> <variable> <level>[CR]
```

**Example Output:**
```
LO 1 3 2 5 55[CR]    # Load 5 on module 2, enclosure 3, master 1 changed to 55%
```

**Special Events:**
```
AON <num_not_affected>[CR]    # ALL_ON event executed
AOFF <num_not_affected>[CR]   # ALL_OFF event executed
```

**Use Cases:**
- Update external dashboards with real-time load levels
- Trigger scenes in other systems when Vantage loads change
- Log energy usage patterns
- Sync dimmer levels with external smart bulbs

---

### 3. VOD@ - Monitor LED State Changes 🔆

**Command:** `VOD@ <enable>[CR]`

**Purpose:** Outputs information when station LED states change (on/off/blinking).

**Parameters:**
- `<enable>`:
  - `0` = Disable all LED monitoring
  - `1` = Enable standard keypad LED changes
  - `2` = Enable LCD LED changes
  - `3` = Enable ALL LED changes

**Output Format (Standard Keypads):**
```
LE <master> <station> <onleds> <blinkleds>[CR]
```

- `<onleds>` = Hex value representing which LEDs are on
- `<blinkleds>` = Hex value representing which LEDs are blinking

**Output Format (LCD Stations):**
```
LC <master> <station> <button> <state>[CR]
```

- `<state>` = 0 (off) or 1 (on)
- Button number is NOT in hex (unlike standard keypads)

**Example Output:**
```
LE 1 3 4C 20[CR]
```
- Station 3, Master 1
- `4C` hex = LEDs 3, 4, and 7 are on
- `20` hex = LED 6 is blinking
- All other LEDs are off

**Use Cases:**
- Display current scene on external touch panel
- Mirror button LED states on virtual keypads
- Provide visual feedback in mobile apps
- Track which scenes are active

---

## Persistence Feature 🔥

**Important:** All three monitoring commands (VOS, VOL, VOD) are **persistent after system reset**!

- Settings persist across reboots
- Each serial port can be configured independently
- No need to re-send commands after power cycle
- Configure once and forget

---

## Implementation in Your Bridge

### Current Setup

Your Pi bridge at `192.168.1.213:8000` is connected to port 3041. To enable monitoring:

### Step 1: Enable Monitoring Commands

```python
# Add to bridge.py startup or configuration endpoint

@app.post("/monitor/enable")
def enable_monitoring():
    """Enable all Vantage monitoring outputs"""
    responses = {}

    # Enable button press monitoring (with serial numbers)
    responses['buttons'] = qlink_send("VOS@ 1 1")

    # Enable load change monitoring
    responses['loads'] = qlink_send("VOL@ 1")

    # Enable LED state monitoring (all types)
    responses['leds'] = qlink_send("VOD@ 3")

    return {"enabled": True, "responses": responses}

@app.post("/monitor/disable")
def disable_monitoring():
    """Disable all Vantage monitoring outputs"""
    responses = {}
    responses['buttons'] = qlink_send("VOS@ 0 0")
    responses['loads'] = qlink_send("VOL@ 0")
    responses['leds'] = qlink_send("VOD@ 0")
    return {"disabled": True, "responses": responses}
```

### Step 2: Create Event Stream Listener

The challenge: Vantage sends events asynchronously over the same TCP connection. You need to:

1. **Maintain persistent connection** to port 3041
2. **Parse incoming events** (SW, LO, LS, LV, LE, LC messages)
3. **Emit events** to external systems (WebSocket, MQTT, HTTP webhooks, etc.)

**Example Architecture:**

```python
import asyncio
import socket
from fastapi import WebSocket
from typing import Set

# Store connected WebSocket clients
websocket_clients: Set[WebSocket] = set()

async def vantage_event_listener():
    """Background task to listen for Vantage events"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.connect((VANTAGE_IP, VANTAGE_PORT))
    sock.settimeout(None)  # Blocking mode for listener

    buffer = ""
    while True:
        try:
            data = sock.recv(1024).decode('ascii')
            buffer += data

            # Process complete messages (ending with CR)
            while '\r' in buffer:
                message, buffer = buffer.split('\r', 1)
                await process_vantage_event(message)

        except Exception as e:
            logger.error(f"Event listener error: {e}")
            await asyncio.sleep(5)  # Reconnect delay

async def process_vantage_event(message: str):
    """Parse and broadcast Vantage events"""
    parts = message.split()

    if not parts:
        return

    event = {"raw": message, "type": parts[0]}

    # Parse button press/release
    if parts[0] == "SW":
        event.update({
            "type": "button",
            "master": int(parts[1]),
            "station": int(parts[2]),
            "button": int(parts[3]),
            "state": "pressed" if parts[4] == "1" else "released",
            "serial": parts[5] if len(parts) > 5 else None
        })

    # Parse load change
    elif parts[0] == "LO":
        event.update({
            "type": "load",
            "master": int(parts[1]),
            "enclosure": int(parts[2]),
            "module": int(parts[3]),
            "load": int(parts[4]),
            "level": int(parts[5])
        })

    # Parse LED change
    elif parts[0] == "LE":
        event.update({
            "type": "led",
            "master": int(parts[1]),
            "station": int(parts[2]),
            "on_leds": parts[3],
            "blink_leds": parts[4]
        })

    # Broadcast to all connected WebSocket clients
    for client in websocket_clients.copy():
        try:
            await client.send_json(event)
        except:
            websocket_clients.remove(client)

@app.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time events"""
    await websocket.accept()
    websocket_clients.add(websocket)
    try:
        while True:
            await websocket.receive_text()
    except:
        websocket_clients.remove(websocket)

@app.on_event("startup")
async def startup_event():
    """Start event listener on startup"""
    asyncio.create_task(vantage_event_listener())
```

---

## Integration Examples

### Example 1: Button Press → HTTP Webhook

```python
async def process_vantage_event(message: str):
    # ... parse event ...

    if event["type"] == "button" and event["state"] == "pressed":
        # Trigger external automation
        station_name = get_station_name(event["station"])
        button_name = get_button_name(event["station"], event["button"])

        # POST to external system
        async with aiohttp.ClientSession() as session:
            await session.post(
                "https://your-automation-system.com/webhook",
                json={
                    "source": "vantage",
                    "station": station_name,
                    "button": button_name,
                    "timestamp": datetime.now().isoformat()
                }
            )
```

### Example 2: Load Change → MQTT

```python
import paho.mqtt.client as mqtt

mqtt_client = mqtt.Client()
mqtt_client.connect("mqtt.local", 1883)

async def process_vantage_event(message: str):
    # ... parse event ...

    if event["type"] == "load":
        topic = f"vantage/load/{event['master']}/{event['enclosure']}/{event['module']}/{event['load']}"
        mqtt_client.publish(topic, event["level"])
```

### Example 3: SmartThings Integration

```python
# When Vantage button pressed, trigger SmartThings scene
async def process_vantage_event(message: str):
    if event["type"] == "button" and event["state"] == "pressed":
        if event["station"] == 23 and event["button"] == 5:
            # "Game Room On" pressed, trigger SmartThings
            await trigger_smartthings_scene("game-room-movie-mode")
```

---

## Testing Plan

### Test 1: Enable Monitoring
```bash
# Enable all monitoring
curl -X POST http://192.168.1.213:8000/monitor/enable
```

### Test 2: Press Physical Button
Press button 5 on station V23, should see:
```
SW 1 23 5 1[CR]    # Pressed
SW 1 23 5 0[CR]    # Released
```

### Test 3: Change Load Level
Use slider in UI or press dimmer button, should see:
```
LO 1 3 2 5 75[CR]  # Load changed to 75%
```

### Test 4: WebSocket Stream
```javascript
const ws = new WebSocket('ws://192.168.1.213:8000/events');
ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    console.log('Vantage event:', data);
};
```

---

## Benefits for Your System

1. **Two-Way Sync** 🔄
   - External systems know when Vantage buttons are pressed
   - Can keep SmartThings, HomeKit, etc. in sync with physical buttons

2. **Real-Time Automation** ⚡
   - Instant reaction to Vantage events
   - No polling needed (events pushed from Vantage)

3. **Better UI** 📱
   - Show real-time status in web UI
   - Display which scenes are active
   - Mirror physical button LEDs

4. **External Triggers** 🎬
   - Press Vantage "Movie" button → Close shades, dim lights, start projector
   - All systems stay in sync

5. **Logging & Analytics** 📊
   - Track button usage patterns
   - Monitor load levels over time
   - Generate usage reports

---

## Next Steps

1. ✅ Review monitoring commands (DONE - this document)
2. 📋 Add monitoring enable/disable endpoints to bridge
3. 📋 Implement background event listener
4. 📋 Create WebSocket stream for real-time events
5. 📋 Add event parsing and routing
6. 📋 Test with physical button presses
7. 📋 Integrate with external automation systems

---

## Important Notes

- **Persistent Connection Required:** Monitoring events come over the same TCP socket
- **Asynchronous:** Events arrive at any time, not in response to commands
- **Buffering:** May need to handle partial messages and buffer incoming data
- **Reconnection:** Handle connection drops gracefully
- **Port Choice:** Use port 3041 (read/write) not 3040 (read-only)

---

**Summary:** Yes, Vantage can absolutely trigger external automation systems! The VOS@, VOL@, and VOD@ commands provide real-time event streams that external systems can monitor and react to. This enables true two-way integration where Vantage events can trigger actions in SmartThings, Home Assistant, or any other automation platform.

**Source:** QLINK2.rtf lines 4634-4913 (VOD, VOL, VOS commands)
