# Vantage Q-Link V Commands Reference

Based on official Vantage QLINK help files (QLINK1.rtf, QLINK2.rtf)

## Command Format

All V commands follow this format:
```
VXX{S} <parameters>[CR]
```

Where:
- `V` = Command start character
- `XX` = 2-letter command code
- `{S}` = Optional special character (see below)
- `<parameters>` = Command-specific parameters
- `[CR]` = Carriage Return terminator

### Special Characters (Optional)

| Character | Description |
|-----------|-------------|
| `!` | Do not send any response |
| `@` | Send a regular response (default for most commands) |
| `#` | Send a detailed response |

**Note:** The `@` symbol appears to be the standard response modifier for control commands.

---

## Load Control Commands

### VLO - Load Control (Set Level)

**Format:** `VLO@ <con_num> <level> {<fade>}[CR]`

**Description:** Turns the specified load on to the given level with optional fade rate.

**Parameters:**
- `<con_num>` - Contractor number of the load (1-9999)
- `<level>` - Level as percentage (0-100)
  - 0 = Off
  - 1-100 = Percentage of full on
- `<fade>` - Fade time in seconds (optional, default 0)
  - Range: 0 to 6553.5 seconds with 0.1 second increments

**Response:**
- Regular: `<level>[CR]`
- Detailed: `RLO <con_num> <level> {<fade>}[CR]`

**Example:**
```
VLO@ 201 50 2.3[CR]
```
Sets load 201 to 50% with 2.3 second fade.

**Status:** ✅ Tested Oct 15, 2025 - Working on port 3041

---

### VGL - Get Load Status (Query Level)

**Format:** `VGL@ <con_num>[CR]`

**Description:** Queries the system for the current level of a load.

**Parameters:**
- `<con_num>` - Contractor number of the load to query

**Response:**
- Regular: `<level>[CR]`
- Detailed: `RGL <con_num> <level>[CR]`

Where `<level>` is 0-100 (percentage the load is on).

**Example:**
```
VGL@ 101[CR]
```
Returns: `50[CR]` (load is at 50%)

**Status:** ✅ Tested Oct 15, 2025 - Working

---

## Button/Switch Control Commands

### VSW - Switch Control (Simulate Button Press)

**Format:** `VSW@ <master> <station> <switch> <state>[CR]`

**Description:** Executes the switch function specified. Can simulate button presses, releases, and other switch operations.

**Parameters:**
- `<master>` - Master board address (1-15)
- `<station>` - Station address containing the switch
  - Wired Stations: 1-50
  - RadioLink Stations: 65-124
  - String Control: 131
  - TelleAccess: 132
  - Time Control: 133
  - IR Zone: 140-189
- `<switch>` - Switch/button number (1-10 for standard stations, 1-255 for LCD)
- `<state>` - Operation to perform:
  - `0` = Execute switch with OFF state
  - `1` = Execute switch with ON state
  - `2` = Learn current load values (Dim, Preset_on, Preset_toggle only)
  - `3` = Start dimming cycle on loads
  - **`4` = Execute switch emulating a BUTTON PRESS** ⭐
  - `5` = Execute switch emulating a button release
  - `6` = Execute switch emulating a press AND release

**Response:**
- Regular: `<state>[CR]`
- Detailed: `RSW <master> <station> <switch> <state>[CR]`

**Example:**
```
VSW@ 2 10 4 1[CR]
```
Executes the ON function for switch 4 on station 10 on master 2.

**For Button Press Simulation:**
```
VSW@ 1 23 5 4[CR]
```
Simulates pressing button 5 on station V23 (master 1).

**Status:** 🔸 Not yet tested - Ready for testing when Pi online

---

## Command Summary Table

### Control Commands
| Command | Purpose | Format | Tested |
|---------|---------|--------|--------|
| `VLO@` | Set load level | `VLO@ <load_id> <level> {<fade>}` | ✅ Working |
| `VGL@` | Get load level | `VGL@ <load_id>` | ✅ Working |
| `VSW@` | Simulate button press | `VSW@ <master> <station> <button> <state>` | 🔸 To test |

### Monitoring Commands (For External Automation)
| Command | Purpose | Format | Status |
|---------|---------|--------|--------|
| `VOS@` | Monitor button presses | `VOS@ <format> <enable>` | 📋 Ready to implement |
| `VOL@` | Monitor load changes | `VOL@ <enable>` | 📋 Ready to implement |
| `VOD@` | Monitor LED changes | `VOD@ <enable>` | 📋 Ready to implement |

---

## Important Notes

1. **Port Configuration:**
   - Port 3040 = Read-only (queries)
   - Port 3041 = Write/control (commands) ⭐

2. **@ Symbol:**
   - Originally thought to be part of the command name
   - Actually the "send regular response" modifier
   - Standard practice to include `@` for control commands

3. **Command Case:**
   - All commands should be in UPPERCASE
   - All data sent/received in ASCII format

4. **Termination:**
   - All commands must end with Carriage Return `[CR]`
   - System environment variable: `Q_LINK_EOL=CR`

5. **Master Number:**
   - For single-master systems, use master number `1`
   - Our system has 2 masters (check which master controls each station)

---

## Bridge Implementation Status

### Current Bridge Endpoints (bridge.py)

```python
# ✅ Working
POST /device/{id}/set          # Uses VLO@ to set load level
GET  /load/{id}/status          # Uses VGL@ to query load level

# 🔸 Ready to test
POST /button/{station}/{button} # Should use VSW@ with state=4 (button press)
GET  /button/{station}/{button}/status  # Purpose unclear - may not be needed
```

### Recommended Updates

1. **Update POST /button/{station}/{button}** to use VSW@ command:
   ```python
   @app.post("/button/{station}/{button}")
   def press_button(station: int, button: int):
       """Simulate a button press on a station"""
       master = 1  # Assuming single master, or lookup based on station
       state = 4   # Button press simulation
       return {"resp": qlink_send(f"VSW@ {master} {station} {button} {state}")}
   ```

2. **Consider removing or repurposing GET /button/{station}/{button}/status**
   - VLED command may not exist
   - No clear use case for querying button LED status via HTTP
   - Alternative: Use VOD command to monitor button state changes

---

## Event Monitoring Commands ⭐

These commands enable real-time event streaming for external automation integration.

### VOS@ - Monitor Button/Switch Presses

**Format:** `VOS@ <format> <enable>[CR]`

**Description:** Outputs information when station buttons or IR buttons are pressed/released.

**Parameters:**
- `<format>` - Output format:
  - `0` = Without station serial number
  - `1` = With station serial number
- `<enable>`:
  - `0` = Disable monitoring
  - `1` = Enable monitoring

**Output Format:**
```
SW <master> <station> <button> <state> {<serial>}[CR]
```
- `<state>` = 1 (pressed) or 0 (released)

**Example:**
```
VOS@ 1 1[CR]             # Enable with serial numbers
SW 1 23 5 1 10345[CR]    # Button 5 pressed on V23
SW 1 23 5 0 10345[CR]    # Button 5 released
```

**Status:** 📋 Ready to implement - enables external automation triggers

---

### VOL@ - Monitor Load Changes

**Format:** `VOL@ <enable>[CR]`

**Description:** Outputs information when any load level changes.

**Parameters:**
- `<enable>`:
  - `0` = Disable monitoring
  - `1` = Enable monitoring

**Output Formats:**
```
LO <master> <encl> <module> <load> <level>[CR]    # Module load
LS <master> <station> <load> <level>[CR]          # Station load
LV <master> <variable> <level>[CR]                # Variable load
```

**Example:**
```
VOL@ 1[CR]              # Enable monitoring
LO 1 3 2 5 75[CR]       # Load changed to 75%
```

**Status:** 📋 Ready to implement - enables real-time status sync

---

### VOD@ - Monitor LED State Changes

**Format:** `VOD@ <enable>[CR]`

**Description:** Outputs information when station LED states change.

**Parameters:**
- `<enable>`:
  - `0` = Disable all LED monitoring
  - `1` = Enable standard keypad LEDs
  - `2` = Enable LCD LEDs
  - `3` = Enable ALL LEDs

**Output Formats:**
```
LE <master> <station> <onleds_hex> <blinkleds_hex>[CR]    # Keypad
LC <master> <station> <button> <state>[CR]                # LCD
```

**Example:**
```
VOD@ 3[CR]              # Enable all LED monitoring
LE 1 3 4C 20[CR]        # LEDs 3,4,7 on, LED 6 blinking
```

**Status:** 📋 Ready to implement - enables UI feedback

---

**Important:** All monitoring commands (VOS@, VOL@, VOD@) are **persistent after system reset**. Configure once and they remain active across reboots.

**See:** `docs/VANTAGE_EVENT_MONITORING.md` for full implementation guide and integration examples.

---

## Other Available V Commands

From QLINK2.rtf, other commands include:
- `VCL` - Configure communication line
- `VEC` - Execute event
- `VGA`-`VGV` - Various "Get" queries
- `VIC`, `VIR` - Infrared commands
- `VLA`-`VLT` - Load-related commands
- `VPG` - Program related
- `VQA`-`VQT` - Query commands
- `VSC`, `VSH`, `VSP`, `VST` - Station/system commands

(Full command list available in QLINK2.rtf)

---

## Testing Plan

When Pi comes online:

1. **Test VSW@ command for button press:**
   ```
   VSW@ 1 23 5 4[CR]
   ```
   - Should trigger "Game Room On" scene
   - Verify lights respond as expected

2. **Test via bridge API:**
   ```
   POST http://192.168.1.213:8000/button/23/5
   ```
   - Should call VSW@ internally
   - Verify same result as direct command

3. **Test with different stations:**
   - V20 (Entry/Foyer)
   - V12 (Master Bath)
   - V02 (Library)

4. **Verify state parameter options:**
   - State 4 (press only)
   - State 6 (press and release)
   - Compare behavior differences

---

**Last Updated:** October 16, 2025
**Source:** QLINK1.rtf, QLINK2.rtf (Vantage Q-Link Protocol Documentation)
