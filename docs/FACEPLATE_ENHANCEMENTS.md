# Faceplate & LED Status Enhancement Plan

## Current Status

**Configuration:**
- 66 total rooms
- 43 rooms have faceplate button data
- 283 buttons configured
- Only PRIMARY station displayed per room (16 rooms have multiple stations)

**Current Issues:**
1. Multiple faceplates per room not accessible (only first one shown)
2. No LED status polling (disabled due to port exhaustion)
3. Button highlighting doesn't reflect actual LED state
4. Toggle vs On/Off buttons not distinguished
5. Button pressed state doesn't update correctly

---

## Proposed Enhancements

### 1. Multiple Faceplates Per Room

**Problem:** 16 rooms have 2-4 faceplates, but only the first is displayed.

**Solution Options:**

**Option A: Tabs (RECOMMENDED)**
- Add tabs above the button section when room has multiple stations
- Tab labels: "Station V19", "Station V22", etc.
- Clicking tab switches visible buttons
- Cleaner UI, familiar pattern

**Option B: Dropdown Selector**
- Dropdown menu to select station
- More compact, but requires extra click

**Option C: Show All (NOT RECOMMENDED)**
- Display all stations' buttons at once
- Pro: See everything at once
- Con: Cluttered UI, too many buttons

**Implementation:**
```javascript
// Config structure change:
{
  "name": "Foyer",
  "stations": [
    { "station": 19, "buttons": [...] },
    { "station": 22, "buttons": [...] }
  ]
}

// UI: Tabs for multi-station rooms
<div class="station-tabs">
  <button class="tab active">V19</button>
  <button class="tab">V22</button>
</div>
```

---

### 2. LED Status Polling

**Problem:** Need to show real-time LED states without exhausting port connections.

**Vantage Command:**
- `VLT@ <master> <station>` - Returns LED state for all 8 buttons on a station
- Response format: `R:V 01 02 03 04 05 06 07 08` (00=off, FF=on)

**Solution Options:**

**Option A: Poll Visible Stations Only (RECOMMENDED)**
- Only poll stations currently visible on screen
- Poll every 2-3 seconds (not every 10 seconds like before)
- Dramatically reduces queries (only 1-5 stations visible vs 70 total)
- Stops polling when dashboard tab not active

**Option B: Single Persistent Connection**
- Keep one socket open, send VLT@ queries in sequence
- Avoids creating/destroying connections
- More complex to implement

**Option C: WebSocket Event Stream**
- Bridge monitors Vantage event stream on persistent connection
- Broadcasts LED changes to dashboard via WebSocket
- Most efficient, but requires bridge code changes

**Implementation (Option A):**
```javascript
// Poll only visible stations
function pollVisibleLEDs() {
  const visibleStations = getVisibleStations(); // [19, 23, 25, ...]

  for (const station of visibleStations) {
    fetch(`/api/leds/${station}`)
      .then(r => r.json())
      .then(data => updateStationLEDs(station, data.leds));
  }
}

// Stop polling when tab inactive
document.addEventListener('visibilitychange', () => {
  if (document.hidden) {
    clearInterval(ledPollInterval);
  } else {
    startLEDPolling();
  }
});
```

---

### 3. Button Event Types

**Problem:** All buttons currently treated as toggles, but some are on/off only.

**Vantage Button Event Types:**
- `PRESET_TOGGLE` - Toggle preset on/off (LED toggles)
- `DIM` - Dim/brighten toggle (LED toggles)
- `TOGGLE` - Generic toggle (LED toggles)
- `PRESET_ON` - Turn on preset (LED turns on, doesn't toggle)
- `PRESET_OFF` - Turn off preset (LED turns off, doesn't toggle)
- `SWITCH_POINTER` - Trigger another button (momentary, no LED change)

**Solution:**
Parse event types from Home Prado Ver.txt and include in config:

```json
{
  "number": 5,
  "name": "Room On",
  "event_type": "PRESET_ON",  // NEW
  "behavior": "momentary"      // NEW: "toggle" or "momentary"
}
```

**Button Behavior:**
- **Toggle buttons**: Click highlights, click again unhighlights
- **Momentary buttons**: Click highlights briefly (500ms), then auto-unhighlight
- **On-only buttons**: Click highlights, stays highlighted
- **Off-only buttons**: Click unhighlights all buttons in group

---

### 4. LED State - Source of Truth

**CRITICAL INSIGHT:**
State tracking WON'T work because LED state can change from:
- Physical faceplate button presses in the house
- Other users on different browsers/devices
- Scheduled timers/events
- Voice control or other systems

**Solution: Always Poll, Never Cache**

The Vantage system is the ONLY source of truth. Dashboard must constantly poll:

1. **No Local State Tracking** - Don't store LED state locally
2. **Continuous Polling** - Poll visible stations every 2-3 seconds
3. **Visible Stations Only** - Dramatically reduces load vs polling all 70 stations
4. **Poll on Button Press** - Immediate poll after dashboard button click (optimistic UI update optional)
5. **Pause When Hidden** - Stop polling when browser tab not visible

**Implementation:**
```javascript
// NO state tracking - just poll and display
function pollVisibleStationLEDs() {
  const visibleStations = getVisibleStations(); // [19, 23, 25]

  for (const station of visibleStations) {
    fetch(`/api/leds/${station}`)
      .then(r => r.json())
      .then(data => {
        // Directly update UI from Vantage response
        updateStationLEDs(station, data.leds);
      });
  }
}

// Poll every 2 seconds (only 3-5 stations)
setInterval(pollVisibleStationLEDs, 2000);

// Update button UI from polled state
function updateStationLEDs(station, ledStates) {
  ledStates.forEach((state, index) => {
    const btnNum = index + 1;
    const btnElement = document.getElementById(`btn-${station}-${btnNum}`);
    if (state === 255 || state === 'FF') {
      btnElement.classList.add('active');
    } else {
      btnElement.classList.remove('active');
    }
  });
}
```

**Performance:**
- 3 visible stations × 30 polls/min = **90 queries/min**
- vs previous: 70 stations × 6 polls/min = **420 queries/min**
- **78% reduction** while maintaining real-time accuracy

---

## Implementation Plan

### Phase 1: Multiple Faceplates Support
1. Update parser to include ALL stations per room (not just first)
2. Modify config structure to support `stations: []` array
3. Add tab UI component for multi-station rooms
4. Test with Foyer (V19, V22) and Breakfast Room (V28, V29)

### Phase 2: Parse Button Event Types
1. Update `parse_all_faceplates.py` to extract event types from Vantage config
2. Map event types to button behaviors (toggle/momentary/on/off)
3. Include in JSON config
4. Test with different button types

### Phase 3: LED Status Polling
1. Add `/api/leds/<station>` endpoint to bridge (VLT@ command)
2. Implement visible-stations-only polling in dashboard
3. Add tab visibility detection to pause polling
4. Test connection count (should stay under 10)

### Phase 4: Button State Management
1. Update button click handler to respect event types
2. Implement optimistic updates + confirmation polls
3. Add periodic LED polling (2-3 second interval)
4. Visual feedback improvements

---

## Better Ideas & Optimizations

### Idea 1: Smart Polling Strategy
Instead of polling all visible stations every 2 seconds:
- **Adaptive polling:** Poll more frequently (1s) right after button press, slower (5s) when idle
- **Change detection:** Only update UI when LED state actually changes
- **Batch queries:** Send multiple VLT@ queries in one connection

### Idea 2: Scene Memory
- Remember last active scene button per room
- Highlight that button on page load
- Useful for "where did I leave the lights?" scenarios

### Idea 3: Button Groups
Some rooms have logical button groups:
- Buttons 1-4: Scene selection
- Buttons 5-8: On/Medium/Dim/Off

Could visually separate these groups or add labels.

### Idea 4: Virtual Buttons
For rooms without physical faceplates, create "virtual" buttons:
- "All On", "All Off", "50%"
- Useful for rooms with loads but no station

### Idea 5: Connection Pooling
Instead of creating new socket for each VLT@ query:
- Bridge maintains 1-2 persistent connections to port 3040
- Queues queries and sends sequentially
- Eliminates TIME_WAIT buildup

### Idea 6: Button Press Feedback
Add visual/audio feedback:
- Brief animation on button press
- Sound effect (optional, user configurable)
- Haptic feedback on mobile devices

---

## Testing Strategy

### Test Cases:
1. **Single faceplate room** (Bar) - Should work as before
2. **Two faceplate room** (Foyer V19/V22) - Tab switching
3. **Three faceplate room** (Hobby Room 2 V45/V58/V74) - Multiple tabs
4. **Toggle button** (Game Room "Path") - LED toggles on/off
5. **On button** (Entry "Entry On") - LED turns on, stays on
6. **Off button** (Entry "Entry Off") - All LEDs turn off
7. **Connection count** - Should stay under 10 during normal use

---

## Performance Estimates

**Before (disabled polling):**
- Active connections: 2-5
- No LED updates
- No port exhaustion

**After (visible-only polling, 3-second interval):**
- Typical visible stations: 3-5
- Queries per minute: 60-100 (vs 1,320 before)
- Active connections: 5-10
- Risk: LOW (90% reduction in queries)

**Alternative (persistent connection):**
- Active connections: 1-2 persistent
- Queries per minute: 60-100
- Risk: VERY LOW (no TIME_WAIT buildup)

---

## Recommendations

**Phase 1 Priority:**
1. ✅ Multiple faceplates with tab UI
2. ✅ Parse button event types
3. ⚠️ Start with visible-only LED polling
4. ⚠️ Monitor connection count

**Future Enhancements:**
- Persistent connection pooling
- Scene memory
- Virtual buttons
- Advanced button grouping

**Risk Mitigation:**
- Add connection count monitor in dashboard
- Add kill switch to disable polling if connections > 50
- Log all VLT@ queries for debugging
