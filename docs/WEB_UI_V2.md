# Web UI v2 - Dark Theme with Scene Control

## New Features

### 🎨 Modern Dark Theme
- Sleek dark gradient background (#1a1a2e to #16213e)
- Glassmorphism effects with backdrop blur
- Smooth animations and transitions
- Purple/indigo accent colors
- Better contrast for extended viewing

### 🎬 Scene/Button Control
Each room can now trigger pre-programmed scenes from the physical button stations:
- **On** - Full brightness (100%)
- **Medium** - 60% brightness
- **Dim** - 20% brightness
- **Off** - All loads off

Scene buttons:
- Highlight when active
- Show visual feedback on press
- Match the physical wall stations (V23, V02, V20, etc.)

### 📊 Real-time Polling
The UI now polls the system every 10 seconds to show:
- **Current load levels** - Displays actual % next to each load
- **Slider synchronization** - Sliders update to match real state
- **Last update timestamp** - Shows when data was refreshed
- **Connection status** - Color-coded status dot (green=online, yellow=warning, red=offline)

### 🔌 New Bridge Endpoints

#### Button Control
```http
POST /button/{station}/{button}
```
Simulates pressing a button on a station.
- Example: `POST /button/23/5` = Press button 5 on station V23 (Game Room On)
- Uses `VBTN@ {station} {button}` command format

#### Load Status Query
```http
GET /load/{id}/status
```
Returns current level of a load (0-100).
- Example: `GET /load/127/status`
- Uses `VGL {id}` command format

#### Button LED Status (To Be Tested)
```http
GET /button/{station}/{button}/status
```
Returns LED state of button (on/off/blink).
- Example: `GET /button/23/5/status`
- Uses `VLED {station} {button}` command format (needs testing)

## Updated Configuration Format

The `loads.json` file now supports station and button mappings:

```json
{
  "rooms": [
    {
      "name": "Game Room",
      "floor": "1st Floor",
      "station": 23,
      "loads": [
        {"id": 1111, "name": "Pendant", "type": "dimmer"}
      ],
      "buttons": [
        {"number": 5, "name": "Game Room On", "preset": 100},
        {"number": 6, "name": "Medium", "preset": 60},
        {"number": 7, "name": "Dim", "preset": 20},
        {"number": 8, "name": "Game Room Off", "preset": 0}
      ]
    }
  ]
}
```

**New Fields:**
- `station` (optional) - Station number (e.g., 23 for V23)
- `buttons` (optional) - Array of button definitions
  - `number` - Button number (1-8)
  - `name` - Display name
  - `preset` (optional) - Target level %
  - `loads` (optional) - Specific loads controlled

## Files

- **`app/static/home-v2.html`** - New dark-themed UI with polling and scene control
- **`app/bridge.py`** - Updated with 3 new endpoints
- **`config/loads-with-buttons-example.json`** - Example configuration with button mappings

## Testing Plan (When Pi is Online)

1. **Test Button Press Command:**
   ```bash
   curl http://192.168.1.213:8000/button/23/5
   ```
   - Expected: Game Room lights turn on
   - Confirms `VBTN@` command format

2. **Test Load Polling:**
   ```bash
   curl http://192.168.1.213:8000/load/127/status
   ```
   - Expected: Returns current level (e.g., `R:V50`)
   - Already know VGL works

3. **Test Button LED Status:**
   ```bash
   curl http://192.168.1.213:8000/button/23/5/status
   ```
   - Expected: Returns LED state
   - May need different command (VBTN?, GETLED, etc.)

4. **Test Web UI:**
   - Open `http://192.168.1.213:8000/ui/home-v2.html`
   - Verify polling updates load levels
   - Test scene buttons
   - Check visual feedback and animations

## Next Steps

1. Extract all button mappings from `Home Prado Ver.txt`
2. Update `loads.json` with complete station/button data
3. Test and confirm command formats
4. Fine-tune polling interval (currently 10 seconds)
5. Add button LED status indicators once command format confirmed

## UI Improvements

- **Performance:** Polling only updates visible loads
- **Responsiveness:** Mobile-friendly grid layout
- **Accessibility:** High contrast, clear labels, keyboard support
- **Visual Feedback:** Toast notifications, loading states, active button highlighting
- **Error Handling:** Connection status, failed commands show user-friendly messages
