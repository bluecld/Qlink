# Bridge Update - VSW@ Command Implementation

**Date:** October 16, 2025
**Status:** ✅ Updated, Ready for Testing

---

## Changes Made

### 1. Updated Button Press Endpoint

**File:** `app/bridge.py`

**Endpoint:** `POST /button/{station}/{button}`

**Changed From:**
```python
def press_button(station: int, button: int):
    """Simulate a button press on a station"""
    return {"resp": qlink_send(f"VBTN@ {station} {button}")}
```

**Changed To:**
```python
def press_button(station: int, button: int):
    """Simulate a button press on a station using VSW@ command.

    Uses VSW@ (Vantage Switch) command with state=4 for button press simulation.
    Format: VSW@ <master> <station> <button> <state>
    State 4 = Simulate button press
    State 6 = Simulate press and release (alternative)
    """
    master = 1
    state = 4  # 4 = button press, 6 = press and release
    return {"resp": qlink_send(f"VSW@ {master} {station} {button} {state}")}
```

**Reason:**
- VBTN@ command does not exist in official Vantage documentation
- Correct command is **VSW@** (Vantage Switch) with state parameter
- State 4 = Simulate button press
- State 6 = Simulate press and release (alternative)

---

### 2. Updated Load Status Query

**File:** `app/bridge.py`

**Endpoint:** `GET /load/{id}/status`

**Changed From:**
```python
def get_load_status(id: int):
    """Get current level of a load (0-100)"""
    return {"resp": qlink_send(f"VGL {id}")}
```

**Changed To:**
```python
def get_load_status(id: int):
    """Get current level of a load (0-100) using VGL@ command"""
    return {"resp": qlink_send(f"VGL@ {id}")}
```

**Reason:**
- Consistency with command format
- `@` symbol requests regular response from controller
- Both VLO@ and VGL@ should include the @ modifier

---

### 3. Updated Button LED Status Endpoint

**File:** `app/bridge.py`

**Endpoint:** `GET /button/{station}/{button}/status`

**Changed From:**
```python
def get_button_status(station: int, button: int):
    """Get LED status of a button (to be tested - may be VLED command)"""
    return {"resp": qlink_send(f"VLED {station} {button}")}
```

**Changed To:**
```python
def get_button_status(station: int, button: int):
    """Get LED status of a button - NOT YET IMPLEMENTED.

    This endpoint may not be needed. The VLED command doesn't appear in
    official Vantage documentation. Consider using VOD (Output on button press)
    command for monitoring button state changes instead.

    TODO: Review VOD command and determine if LED status querying is possible.
    """
    raise HTTPException(
        status_code=501,
        detail="Button status query not yet implemented - VLED command not found in documentation",
    )
```

**Reason:**
- VLED command not found in official Vantage documentation
- Endpoint now returns HTTP 501 (Not Implemented) instead of sending invalid command
- Alternative: Use VOD command for monitoring button state changes (requires review)

---

## Command Reference

### VSW@ - Switch Control

**Full Format:**
```
VSW@ <master> <station> <switch> <state>[CR]
```

**Parameters:**
- `<master>` - Master board number (1-15), we use 1
- `<station>` - Station address (1-50 for wired, 65-124 for RadioLink)
- `<switch>` - Button/switch number (1-10 standard, 1-255 LCD)
- `<state>` - Operation to perform:
  - 0 = Execute OFF state
  - 1 = Execute ON state
  - 2 = Learn load values
  - 3 = Start dimming cycle
  - **4 = Button PRESS** ⭐
  - 5 = Button RELEASE
  - 6 = Button PRESS and RELEASE

**Example Usage:**
```bash
# Press button 5 on station V23 (Game Room On)
VSW@ 1 23 5 4[CR]

# Via HTTP API:
POST http://192.168.1.213:8000/button/23/5
```

**Response:**
- Regular: `4[CR]` (echoes the state)
- Detailed: `RSW 1 23 5 4[CR]`

---

## Testing Plan

### Test 1: Basic Button Press
```bash
POST http://192.168.1.213:8000/button/23/5
```
**Expected:** Game Room lights turn on to "Game Room On" scene

### Test 2: Different Stations
- V20 Entry (button 5 = "Entry On")
- V12 Master Bath (button 5 = "Bath On")
- V02 Library (button 3 = "Library On")

### Test 3: State Comparison
Compare state 4 (press only) vs state 6 (press and release):
```python
# State 4
VSW@ 1 23 5 4

# State 6
VSW@ 1 23 5 6
```

### Test 4: Multi-Load Scenes
Test buttons that control multiple loads:
- V20 Button 4: "All Outside Off" (controls loads 1127, 2115)
- V23 Button 1: "Path" (controls load 1328)

---

## Breaking Changes

⚠️ **API clients must update if they were calling the button endpoint:**

**Old behavior:**
- Sent invalid VBTN@ command (would have failed)

**New behavior:**
- Sends correct VSW@ command with state=4
- Should now work properly when tested

**LED Status endpoint:**
- Previously sent invalid VLED command
- Now returns HTTP 501 with explanation
- Clients should handle 501 status code

---

## Next Steps

1. ✅ Update bridge.py (DONE)
2. ✅ Add todo for V command review (DONE)
3. ⏳ Deploy updated bridge.py to Pi
4. ⏳ Test VSW@ command with real hardware
5. ⏳ Verify button presses trigger correct scenes
6. ⏳ Update UI if needed based on test results

---

## References

- `docs/VANTAGE_COMMANDS.md` - Complete V command reference
- `Info/QLINK2.rtf` - Official Vantage Q-Link documentation (lines 5689-5850 for VSW@)
- `Info/Home Prado Ver.txt` - System button configuration

---

**Notes:**
- Master number hardcoded to `1` (single-master assumption)
- If system has multiple masters, may need station-to-master lookup table
- State 4 vs State 6 behavior difference to be determined through testing
- VOD command investigation pending for button state monitoring
