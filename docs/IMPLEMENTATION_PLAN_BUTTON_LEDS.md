# Implementation Plan: Button LED Status & Real-Time UI Feedback

## Overview

Upgrade the Vantage Q-Link Bridge to display real-time button LED states in the web UI, mirroring the physical faceplate buttons. This creates a "virtual keypad" experience where users can see which scenes are active.

---

## Current State ✅

### What's Already Working

1. **Event Monitoring Infrastructure** - COMPLETE
   - `event_listener_loop()` - Background thread listening for Vantage events
   - `VOS@ 1 1` - Button press/release monitoring ENABLED
   - `VOL@ 1` - Load change monitoring ENABLED
   - `VOD@ 3` - LED state monitoring ENABLED (All types)
   - WebSocket endpoint `/events` - Broadcasting events to clients

2. **Event Parsing** - COMPLETE
   - `parse_vantage_event()` handles:
     - `SW` - Button press/release events
     - `LO/LS/LV` - Load change events
     - `LE` - Keypad LED state changes (hex format)
     - `LC` - LCD button LED state changes

3. **Preview UI** - COMPLETE
   - [docs/ui-preview-local.html](docs/ui-preview-local.html) shows desired layout
   - Room cards with faceplate button grids
   - Button styling and tooltips
   - Scene button activation visual feedback

4. **Production UI** - PARTIALLY COMPLETE
   - [app/static/home-v2.html](app/static/home-v2.html) - Modern dark theme UI
   - Room/floor organization
   - Load control sliders
   - **MISSING:** Faceplate buttons and LED status display

---

## What Needs to Be Built

### Phase 1: LED State Management (Backend)

**Goal:** Parse and maintain LED state for all buttons across all stations

#### 1.1 Add LED State Store
```python
# In bridge.py, add global state
button_led_states: Dict[str, Dict[int, str]] = {}
# Format: {"V23": {1: "on", 2: "off", 3: "blink", 4: "on", ...}, ...}
```

#### 1.2 Update parse_vantage_event()
Currently parses LE/LC events but doesn't store state. Add:

```python
def parse_vantage_event(message: str) -> Optional[dict]:
    # ... existing code ...

    # LED state change (keypad): LE <master> <station> <onleds_hex> <blinkleds_hex>
    elif parts[0] == "LE":
        station_id = f"V{parts[2]}"
        on_leds_hex = parts[3]
        blink_leds_hex = parts[4]

        # Decode hex to button states
        on_bits = int(on_leds_hex, 16)
        blink_bits = int(blink_leds_hex, 16)

        # Update global state
        if station_id not in button_led_states:
            button_led_states[station_id] = {}

        # Buttons 1-8 (bit positions)
        for btn_num in range(1, 9):
            bit_mask = 1 << (btn_num - 1)
            if blink_bits & bit_mask:
                button_led_states[station_id][btn_num] = "blink"
            elif on_bits & bit_mask:
                button_led_states[station_id][btn_num] = "on"
            else:
                button_led_states[station_id][btn_num] = "off"

        event.update({
            "type": "led_keypad",
            "master": int(parts[1]),
            "station": int(parts[2]),
            "station_id": station_id,
            "on_leds": on_leds_hex,
            "blink_leds": blink_leds_hex,
            "button_states": button_led_states[station_id].copy()
        })
```

#### 1.3 Add LED State Query Endpoint
```python
@app.get("/api/leds")
def get_all_led_states():
    """Get current LED states for all stations"""
    return {"stations": button_led_states}

@app.get("/api/leds/{station}")
def get_station_led_states(station: int):
    """Get current LED states for a specific station"""
    station_id = f"V{station}"
    return {
        "station": station,
        "station_id": station_id,
        "buttons": button_led_states.get(station_id, {})
    }
```

---

### Phase 2: Update loads.json Structure

**Goal:** Ensure loads.json includes button configurations

The preview UI already shows correct structure:
```json
{
  "rooms": [
    {
      "name": "Game Room",
      "floor": "1st Floor",
      "station": 23,
      "loads": [...],
      "buttons": [
        {"number": 1, "name": "Path"},
        {"number": 2, "name": "Pendant"},
        {"number": 5, "name": "Game Room On"},
        {"number": 8, "name": "Game Room Off"}
      ]
    }
  ]
}
```

**Action:** Verify your [config/loads.json](config/loads.json) includes `buttons` arrays for each room.

---

### Phase 3: Update home-v2.html UI

**Goal:** Port button layout from preview UI to production UI

#### 3.1 Add Button Section to Room Cards

Currently home-v2.html renders loads but not buttons. Add scene buttons section:

```html
<!-- Add to room card, before loads section -->
${room.buttons && room.buttons.length > 0 ? `
  <div class="scene-section">
    <div class="scene-label">Station V${room.station} - Faceplate Buttons</div>
    <div class="scene-buttons">
      ${room.buttons.map(btn => `
        <div class="scene-btn"
             id="btn-${room.station}-${btn.number}"
             data-station="${room.station}"
             data-button="${btn.number}"
             onclick="pressButton(${room.station}, ${btn.number}, '${btn.name}')">
          ${btn.name}
        </div>
      `).join('')}
    </div>
  </div>
` : ''}
```

#### 3.2 Add LED State Styling

```css
.scene-btn {
  position: relative;
  padding: 10px 12px;
  background: rgba(102, 126, 234, 0.2);
  border: 1px solid rgba(102, 126, 234, 0.3);
  border-radius: 10px;
  cursor: pointer;
  transition: all 0.3s;
}

/* LED off (default) */
.scene-btn[data-led="off"] {
  background: rgba(102, 126, 234, 0.2);
  border-color: rgba(102, 126, 234, 0.3);
  color: #c7d2fe;
}

/* LED on (scene active) */
.scene-btn[data-led="on"] {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-color: #667eea;
  color: white;
  box-shadow: 0 4px 16px rgba(102, 126, 234, 0.5);
}

/* LED blinking (transitioning/ramping) */
.scene-btn[data-led="blink"] {
  background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
  border-color: #f59e0b;
  color: white;
  animation: led-blink 1s ease-in-out infinite;
}

@keyframes led-blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0.5; }
}

/* LED indicator dot */
.scene-btn::before {
  content: '';
  position: absolute;
  top: 6px;
  right: 6px;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: transparent;
}

.scene-btn[data-led="on"]::before {
  background: #4ade80;
  box-shadow: 0 0 8px #4ade80;
}

.scene-btn[data-led="blink"]::before {
  background: #fbbf24;
  box-shadow: 0 0 8px #fbbf24;
  animation: pulse 1s ease-in-out infinite;
}
```

#### 3.3 Add WebSocket Event Handling

```javascript
// Connect to WebSocket for real-time events
const ws = new WebSocket(`ws://${window.location.host}/events`);

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);

  // Handle LED state updates
  if (data.type === 'led_keypad' && data.button_states) {
    updateButtonLEDs(data.station, data.button_states);
  }

  // Handle load changes
  if (data.type.startsWith('load_')) {
    updateLoadLevel(data.load, data.level);
  }

  // Handle button presses (optional: visual feedback)
  if (data.type === 'button' && data.state === 'pressed') {
    flashButton(data.station, data.button);
  }
};

function updateButtonLEDs(station, buttonStates) {
  // Update all button LEDs for this station
  Object.entries(buttonStates).forEach(([btnNum, state]) => {
    const btnEl = document.getElementById(`btn-${station}-${btnNum}`);
    if (btnEl) {
      btnEl.setAttribute('data-led', state);
    }
  });
}

function flashButton(station, button) {
  const btnEl = document.getElementById(`btn-${station}-${button}`);
  if (btnEl) {
    btnEl.classList.add('pressed');
    setTimeout(() => btnEl.classList.remove('pressed'), 200);
  }
}

// Add pressed animation
.scene-btn.pressed {
  transform: scale(0.95);
  filter: brightness(1.2);
}
```

#### 3.4 Load Initial LED States on Page Load

```javascript
async function loadInitialStates() {
  try {
    // Get all LED states
    const ledResponse = await fetch('/api/leds');
    const ledData = await ledResponse.json();

    // Update UI with current states
    Object.entries(ledData.stations).forEach(([stationId, buttonStates]) => {
      const station = parseInt(stationId.replace('V', ''));
      updateButtonLEDs(station, buttonStates);
    });

    // Get all load levels
    const configResponse = await fetch('/config');
    const config = await configResponse.json();

    // Query each load's current level
    for (const room of config.rooms) {
      for (const load of room.loads) {
        const statusResponse = await fetch(`/load/${load.id}/status`);
        const status = await statusResponse.json();
        const level = parseInt(status.resp);
        updateLoadLevel(load.id, level);
      }
    }
  } catch (error) {
    console.error('Failed to load initial states:', error);
  }
}

// Call on page load
window.addEventListener('DOMContentLoaded', loadInitialStates);
```

---

### Phase 4: Enhanced Features (Optional)

#### 4.1 Button Press Feedback

When user clicks a scene button in the UI, show immediate feedback while waiting for Vantage response:

```javascript
async function pressButton(station, button, name) {
  const btnEl = document.getElementById(`btn-${station}-${button}`);
  btnEl.classList.add('pressing');

  try {
    const response = await fetch(`/button/${station}/${button}`, {
      method: 'POST'
    });

    if (response.ok) {
      showToast(`${name} activated`);
    }
  } catch (error) {
    console.error('Button press failed:', error);
  } finally {
    btnEl.classList.remove('pressing');
  }
}

.scene-btn.pressing {
  transform: scale(0.95);
  opacity: 0.7;
}
```

#### 4.2 Load Level Display on Button Hover

Show which loads a button controls:

```javascript
// Add to button element
<div class="scene-btn"
     data-loads="1111,1114,2141"
     onmouseenter="showButtonLoads(this)">
  Game Room On
</div>

function showButtonLoads(btnEl) {
  const loadIds = btnEl.dataset.loads?.split(',');
  if (!loadIds) return;

  // Highlight associated loads
  loadIds.forEach(id => {
    document.getElementById(`load-${id}`)?.classList.add('highlighted');
  });
}
```

#### 4.3 Scene Detection

Analyze load levels to determine active scene:

```javascript
function detectActiveScene(roomConfig, currentLoadLevels) {
  // Compare current load levels against scene definitions
  // If match found, mark button as active
  // This is complex - may require scene definitions in loads.json
}
```

---

## Implementation Priority

### Must-Have (Phase 1 + 3)
1. ✅ LED state parsing (already done in parse_vantage_event)
2. 📋 LED state storage in memory
3. 📋 `/api/leds` endpoint to query states
4. 📋 Update home-v2.html to show buttons
5. 📋 WebSocket LED update handling
6. 📋 CSS for LED states (on/off/blink)

### Should-Have (Phase 2 + 4.1)
1. 📋 Verify loads.json has buttons arrays
2. 📋 Button press visual feedback
3. 📋 Initial state loading on page load

### Nice-to-Have (Phase 4.2, 4.3)
1. 📋 Button hover load highlighting
2. 📋 Scene detection from load levels
3. 📋 Long press for advanced functions

---

## Technical Considerations

### LED Hex Decoding

Vantage sends LED states as hex values:
- `LE 1 23 4C 20`
- `4C` hex = 0100 1100 binary = buttons 3, 4, 7 ON
- `20` hex = 0010 0000 binary = button 6 BLINKING

**Bit mapping:**
```
Bit 0 (LSB) = Button 1
Bit 1 = Button 2
Bit 2 = Button 3
...
Bit 7 = Button 8
```

### LCD Stations (LC Events)

LCD stations send individual button updates:
- `LC 1 12 5 1` = Station 12, button 5 LED ON
- Unlike keypads, button number is decimal (not hex bit position)

Handle both formats in state store.

### State Persistence

Button LED states are **in-memory only**. They reset on bridge restart. This is acceptable because:
1. Vantage controller maintains true state
2. Next LED change event will update our state
3. Can query initial state on connect (if query command exists)

### Performance

- LED events are infrequent (only on scene changes)
- State store is small (<50 stations × 8 buttons = 400 entries)
- WebSocket broadcasts are efficient
- No database needed

---

## Testing Plan

### Unit Tests
1. Test LED hex decoding: `4C` → buttons [3, 4, 7]
2. Test blink decoding: `20` → button 6
3. Test state store update logic
4. Test WebSocket broadcast

### Integration Tests
1. Press physical button → UI updates
2. Press UI button → Physical button activates → UI LED updates
3. Multi-client WebSocket sync
4. Page refresh → LED states reload

### Real-World Tests
1. Walk through house pressing buttons
2. Verify UI mirrors physical keypads
3. Test with multiple rooms/stations
4. Test LCD vs keypad stations
5. Verify blinking states during ramps

---

## Deployment Strategy

### Step 1: Backend Changes
1. Update bridge.py with LED state store
2. Add `/api/leds` endpoint
3. Deploy to Pi
4. Test with WebSocket client (browser console)

### Step 2: UI Update
1. Copy preview UI button HTML to home-v2.html
2. Add CSS for LED states
3. Add WebSocket event handling
4. Deploy static files to Pi

### Step 3: Validation
1. Press physical buttons
2. Verify UI updates
3. Press UI buttons
4. Verify physical buttons activate
5. Check LED feedback loop

### Step 4: Polish
1. Add button press animations
2. Tune WebSocket reconnection
3. Add error handling
4. User testing

---

## Code Locations

### Files to Modify
1. **[app/bridge.py](../app/bridge.py)** - Add LED state store and endpoint
2. **[app/static/home-v2.html](../app/static/home-v2.html)** - Add button UI
3. **[config/loads.json](../config/loads.json)** - Verify button configs (optional)

### Files to Reference
1. **[docs/ui-preview-local.html](ui-preview-local.html)** - Button layout example
2. **[docs/VANTAGE_EVENT_MONITORING.md](VANTAGE_EVENT_MONITORING.md)** - Event format reference
3. **[docs/VANTAGE_COMMANDS.md](VANTAGE_COMMANDS.md)** - VOD command details

---

## Success Criteria

✅ **Definition of Done:**
1. User can see faceplate buttons in web UI
2. Buttons show correct LED states (on/off/blink)
3. Clicking UI button activates Vantage scene
4. Physical button press updates UI in real-time (<500ms)
5. Multiple browser tabs stay in sync
6. Works across all configured rooms/stations
7. No errors in browser console
8. No errors in bridge logs

---

## Timeline Estimate

- **Phase 1 (Backend):** 2-3 hours
- **Phase 2 (Config):** 30 minutes (if needed)
- **Phase 3 (UI):** 3-4 hours
- **Phase 4 (Polish):** 2-3 hours
- **Testing:** 2-3 hours

**Total:** 10-13 hours of focused development

---

## Next Steps

1. **Review this plan** - Confirm approach
2. **Prioritize features** - Must/should/nice-to-have
3. **Start with Phase 1** - LED state storage in bridge.py
4. **Test incrementally** - Validate each phase before moving on
5. **Deploy to Pi** - Test with real Vantage system
6. **Iterate** - Refine based on real-world usage

---

## Questions to Resolve

1. ❓ Do all rooms in loads.json have buttons arrays defined?
2. ❓ Are there any LCD stations (different LED event format)?
3. ❓ Should we query initial LED state on startup or wait for first event?
4. ❓ Should button LEDs auto-dim after timeout (like physical keypads)?
5. ❓ Do we need to support master > 1 (multi-master systems)?

---

**Status:** Ready to implement
**Last Updated:** October 16, 2025
**Approved By:** [Pending User Approval]
