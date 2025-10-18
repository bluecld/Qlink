# Monitoring vs Polling Strategy Analysis

**Date:** October 16, 2025
**Question:** Should we use event monitoring (VOD/VOL/VOS) or polling (VGL queries) for state tracking?

---

## TL;DR Recommendation

**Use HYBRID approach:**
1. ✅ **Monitor button presses** (VOS@) - MUST HAVE for automation triggers
2. ✅ **Monitor LED changes** (VOD@) - Event-driven, zero overhead
3. ✅ **Monitor load changes** (VOL@) - Real-time feedback
4. ⚠️ **Optional: Poll loads on startup** - Get initial states quickly
5. ❌ **Don't poll buttons** - No query command exists

---

## Key Findings

### 1. Button LED States: NO POLLING AVAILABLE ❌

**Finding:** There is **NO command to query button LED status** in Vantage Q-Link protocol.

**Evidence:**
- Searched entire documentation: No `VLED`, `VGB` (Get Button), or similar command
- [docs/BRIDGE_UPDATE_VSW.md:104](BRIDGE_UPDATE_VSW.md) confirms: "VLED command not found in official Vantage documentation"
- Only way to know LED state is via **VOD@ monitoring events**

**Conclusion:** Button LEDs **MUST** use event monitoring. Polling is not an option.

---

### 2. Load States: POLLING IS POSSIBLE ✅

**Command:** `VGL@ <load_id>` - Query individual load level

**Performance Test Needed:**
```python
# How fast can we poll all loads?
loads = [101, 102, 103, ...]  # ~50-100 loads typical
start = time.time()
for load_id in loads:
    level = qlink_send(f"VGL@ {load_id}")
duration = time.time() - start
print(f"Polled {len(loads)} loads in {duration}s")
```

**Estimated Performance:**
- Each VGL@ command: ~50-100ms (network + processing)
- 50 loads × 100ms = **5 seconds per poll cycle**
- 100 loads × 100ms = **10 seconds per poll cycle**

**Conclusion:** Polling loads is **feasible but slow** for initial state. Monitoring is better for real-time.

---

## Comparison Matrix

| Aspect | Event Monitoring (VOD/VOL/VOS) | Polling (VGL queries) |
|--------|-------------------------------|----------------------|
| **Button LEDs** | ✅ Only option (LE/LC events) | ❌ No query command exists |
| **Load Levels** | ✅ Real-time (LO/LS/LV events) | ✅ Possible (VGL@ command) |
| **Latency** | ⚡ Instant (<100ms) | 🐢 Slow (5-10s for all loads) |
| **Network Load** | 📉 Zero (events pushed by Vantage) | 📈 High (constant polling) |
| **CPU Load** | 📉 Minimal (event-driven) | 📈 Higher (continuous queries) |
| **Initial State** | ⚠️ Unknown until first event | ✅ Can query on startup |
| **Accuracy** | ✅ Always in sync | ⚠️ Stale between polls |
| **Button Presses** | ✅ Captures all presses | ❌ Can't detect |
| **Automation Triggers** | ✅ Perfect for triggers | ❌ Too slow, misses events |
| **Complexity** | 🟡 Moderate (async events) | 🟢 Simple (request/response) |
| **Reliability** | ✅ Persistent, auto-resumes | ⚠️ Stops if polling breaks |

---

## Your Use Cases Analysis

### Use Case 1: "React through other automation"
**Requirement:** Detect button presses to trigger external systems

**Answer:** **MUST use monitoring (VOS@)**

**Why:**
- Polling can't detect button presses (no query command)
- Need instant response (<500ms) for good UX
- Can't miss button presses between poll cycles
- VOS@ events are **exactly designed for this**

**Example:**
```
User presses "Movie Mode" button
    ↓ <100ms
Vantage sends: SW 1 23 5 1
    ↓ <100ms
Bridge receives event
    ↓ <100ms
External automation triggered:
    - Lower projector screen
    - Dim lights
    - Start Apple TV
```

**With polling:** Would take 5-10 seconds to detect, likely miss quick presses.

---

### Use Case 2: "Show button LED states in UI"
**Requirement:** Display which scene buttons are active

**Answer:** **MUST use monitoring (VOD@)**

**Why:**
- No polling command exists for button LEDs
- VOD@ events are pushed whenever LEDs change
- Zero overhead - only get events when state actually changes
- Events include all 8 buttons per station (efficient)

**Example:**
```
User presses "All On" button
    ↓
Vantage changes LED states
    ↓
Vantage sends: LE 1 23 4C 20
    ↓
Bridge decodes: {3: "on", 4: "on", 6: "blink", 7: "on"}
    ↓
WebSocket broadcast to all browsers
    ↓
UI updates button highlights
```

---

### Use Case 3: "Show load levels in UI"
**Requirement:** Display current dimmer levels

**Answer:** **Hybrid approach**

**Option A: Pure Monitoring (Recommended)**
- Enable VOL@ on startup
- Get LO/LS/LV events whenever loads change
- Fast, efficient, real-time
- ⚠️ Initial state unknown until first change

**Option B: Hybrid (Best User Experience)**
1. **On startup:** Poll all loads once with VGL@ to get initial state
2. **Runtime:** Use VOL@ monitoring for real-time updates
3. **Result:** Fast initial load + real-time sync

**Example Hybrid Implementation:**
```python
async def startup():
    # Step 1: Enable monitoring for real-time updates
    qlink_send("VOL@ 1")
    qlink_send("VOD@ 3")
    qlink_send("VOS@ 1 1")

    # Step 2: Poll all loads for initial state (background task)
    asyncio.create_task(poll_initial_states())

async def poll_initial_states():
    """One-time poll on startup to get current state"""
    loads = get_all_load_ids()  # From loads.json

    for load_id in loads:
        try:
            level = int(qlink_send(f"VGL@ {load_id}"))
            update_load_state(load_id, level)
        except:
            continue  # Skip failed queries

    logger.info(f"Initial poll complete: {len(loads)} loads")
```

---

## Performance Analysis

### Scenario: 71 stations × 8 buttons + 100 loads

#### Pure Polling Approach ❌
```
Every 5 seconds:
  - Poll 100 loads × 100ms = 10 seconds
  - Poll 568 buttons × ??? = IMPOSSIBLE (no query command)

Result:
  - Can't get button states
  - 10 second lag
  - 100 queries/cycle = network spam
  - Misses button presses between cycles
```

#### Pure Monitoring Approach ✅
```
On startup:
  - Send VOL@ 1 (once)
  - Send VOD@ 3 (once)
  - Send VOS@ 1 1 (once)

Runtime:
  - Zero queries
  - Events only when state changes
  - <100ms latency
  - Never misses button presses

Result:
  - ⚠️ Initial state unknown
  - ✅ Real-time updates
  - ✅ Minimal network load
```

#### Hybrid Approach ⭐ RECOMMENDED
```
On startup:
  - Send VOL@ 1, VOD@ 3, VOS@ 1 1 (monitoring)
  - Poll all loads once (background): ~10 seconds

Runtime:
  - Monitor button presses (VOS@) - instant
  - Monitor LED changes (VOD@) - instant
  - Monitor load changes (VOL@) - instant

Result:
  - ✅ Initial state available after ~10s
  - ✅ Real-time updates always
  - ✅ Never miss button presses
  - ✅ Minimal network load after startup
```

---

## Detailed Recommendations

### ✅ MUST DO: Button Press Monitoring

```python
# Enable on startup
qlink_send("VOS@ 1 1")  # Monitor button presses with serial numbers

# Handle events
def handle_button_press(event):
    if event['state'] == 'pressed':
        trigger_automation(event['station'], event['button'])
```

**Why:** This is your **core requirement** for automation triggers. Can't be done any other way.

---

### ✅ MUST DO: LED Monitoring

```python
# Enable on startup
qlink_send("VOD@ 3")  # Monitor all LED types

# Already implemented in Phase 1!
# Events automatically update button_led_states{}
# UI reads from /api/leds
```

**Why:** No polling alternative. Already working in Phase 1.

---

### ✅ RECOMMENDED: Load Monitoring + Initial Poll

```python
# Enable on startup
qlink_send("VOL@ 1")  # Monitor load changes

# Initial poll (background task)
async def poll_initial_loads():
    for load in loads:
        level = qlink_send(f"VGL@ {load['id']}")
        load_states[load['id']] = int(level)
```

**Why:** Best of both worlds - fast initial state + real-time updates.

---

### ❌ DON'T DO: Continuous Polling

```python
# BAD: Don't do this
while True:
    for load in loads:
        query_load(load)  # Spams network
    time.sleep(5)  # Still too slow for UX
```

**Why:**
- Slow (5-10 second cycles)
- Network spam
- Higher CPU
- Misses quick changes
- Can't detect button presses anyway

---

## Implementation Plan

### Current Status (Phase 1)
✅ VOD@ monitoring enabled
✅ VOL@ monitoring enabled
✅ VOS@ monitoring enabled
✅ LED state tracking working
✅ Event parsing complete

### Recommended Additions

#### 1. Add Initial Load Poll (Optional)
**File:** `app/bridge.py`

```python
# Add global
load_states: Dict[int, int] = {}  # {load_id: level}
load_states_lock = threading.Lock()

# Add on startup
@app.on_event("startup")
async def startup_event():
    start_event_listener()

    # NEW: Poll loads for initial state
    asyncio.create_task(poll_initial_load_states())

async def poll_initial_load_states():
    """One-time poll to get initial load levels"""
    await asyncio.sleep(2)  # Wait for monitoring to connect

    try:
        # Get all load IDs from loads.json
        config = get_config()
        load_ids = []
        for room in config.get('rooms', []):
            for load in room.get('loads', []):
                load_ids.append(load['id'])

        logger.info(f"📊 Polling {len(load_ids)} loads for initial state...")

        # Poll each load
        for load_id in load_ids:
            try:
                response = qlink_send(f"VGL@ {load_id}")
                level = int(response.strip())

                with load_states_lock:
                    load_states[load_id] = level

                await asyncio.sleep(0.1)  # Rate limit

            except Exception as e:
                logger.warning(f"Failed to poll load {load_id}: {e}")
                continue

        logger.info(f"✅ Initial poll complete: {len(load_states)} loads")

    except Exception as e:
        logger.error(f"Initial poll failed: {e}")

# Add endpoint
@app.get("/api/loads")
def get_all_load_states():
    """Get current levels for all loads"""
    with load_states_lock:
        return {"loads": load_states.copy(), "count": len(load_states)}
```

#### 2. Update Load Change Events
```python
# In parse_vantage_event(), add to LO/LS/LV handlers:
def parse_vantage_event(message: str):
    # ... existing code ...

    elif parts[0] == "LO":
        load_id = int(parts[4])
        level = int(parts[5])

        # Update state store
        with load_states_lock:
            load_states[load_id] = level

        event.update({...})  # existing code
```

---

## Testing Plan

### Test 1: Button Press Latency ⚡
1. Press physical button
2. Measure time to automation trigger
3. **Goal:** <500ms end-to-end

### Test 2: Load Polling Performance 🐢
1. Time how long to poll all loads
2. Measure network load
3. **Expected:** ~5-10 seconds for 50-100 loads

### Test 3: LED Event Frequency 📊
1. Monitor LED events for 1 hour
2. Count events per minute
3. **Expected:** <10 events/minute (only on scene changes)

### Test 4: Hybrid Initial State ⏱️
1. Restart bridge
2. Load UI immediately
3. **Expected:**
   - Page loads instantly
   - Loads show "polling..." for ~10s
   - Then all states populate
   - Real-time updates start immediately

---

## Answers to Your Questions

### Q1: "Is it best to monitor all states or just poll every few seconds?"

**A:** **Monitor** is better for everything except initial load state.

**Why:**
- Button LEDs: **Must** monitor (no polling option)
- Button presses: **Must** monitor (for automation)
- Load levels: **Hybrid** (monitor + initial poll)

### Q2: "How long would a complete poll take?"

**A:** **~5-10 seconds** for 50-100 loads.

**Calculation:**
- Each VGL@ query: ~50-100ms
- 50 loads = 2.5-5 seconds
- 100 loads = 5-10 seconds
- 200 loads = 10-20 seconds

**But:** This only gives you load levels. **Can't poll button LEDs.**

### Q3: "Can buttons be polled?"

**A:** **No.** There is no command to query button LED status.

**Evidence:**
- Searched all documentation
- No VLED, VGB, or similar command exists
- VOD@ monitoring is the **only** way to get button LED states

### Q4: "We want to monitor presses for automation"

**A:** **Absolutely! Use VOS@ monitoring.** (Already implemented in Phase 1)

**Perfect for:**
- Triggering external automation
- Logging button usage
- Syncing with SmartThings/Home Assistant
- Instant response (<100ms latency)

---

## Final Recommendation

**Use the HYBRID approach already implemented in Phase 1:**

✅ **Monitoring (Event-Driven):**
- VOD@ 3 - LED states (buttons)
- VOL@ 1 - Load changes
- VOS@ 1 1 - Button presses

✅ **Optional Enhancement:**
- Add one-time VGL@ poll on startup for initial load levels
- ~10 second operation, runs in background
- After that, VOL@ keeps everything in sync

✅ **Result:**
- Button presses detected instantly ⚡
- LED states always accurate 💡
- Load levels real-time 🔄
- Initial state available quickly 🚀
- Minimal network overhead 📉
- Never miss automation triggers ✅

---

## Summary Table

| Feature | Command | When | Why |
|---------|---------|------|-----|
| **Button Presses** | VOS@ 1 1 | Always monitor | For automation triggers |
| **Button LEDs** | VOD@ 3 | Always monitor | No polling option |
| **Load Changes** | VOL@ 1 | Always monitor | Real-time sync |
| **Initial Loads** | VGL@ loop | Once on startup | Fast initial state |
| **Runtime Loads** | VOL@ events | Use events | Real-time, efficient |

---

**Conclusion:** Phase 1 implementation is **optimal**. Consider adding optional initial load poll if you want UI to show levels immediately on page load. Otherwise, current monitoring-only approach is perfect.

**Next Step:** Test with real Vantage system to validate latency and event frequency.
