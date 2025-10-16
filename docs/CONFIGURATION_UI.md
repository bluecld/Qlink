# Configuration Updates

## Changes Made

### 1. Settings Page - Refresh Interval Control

**Added to `/ui/settings.html`:**
- New input field: "Status Refresh Interval (seconds)"
- Default value: 10 seconds
- Range: 0-300 seconds (0 = disable auto-refresh)
- JavaScript to dynamically update refresh rate without page reload

**How it works:**
```javascript
// Refresh interval is configurable
let currentRefreshSeconds = 10;

// Changes take effect immediately when field is updated
refreshInput.addEventListener('change', (e) => {
    currentRefreshSeconds = parseInt(e.target.value) || 0;
    startAutoRefresh(); // Restart timer with new interval
});
```

### 2. New Configuration Manager Page

**Created `/ui/config.html`:**

A comprehensive interface for managing your Vantage system configuration with three tabs:

#### Tab 1: 💡 Loads & Rooms
- **JSON Editor** for `loads.json`
- Live statistics showing:
  - Total rooms configured
  - Total loads
  - Master 1 loads count
  - Master 2 loads count
- **Actions:**
  - ↻ Reload - Refresh from file
  - ✓ Validate - Check JSON syntax
  - 💾 Save - Update configuration

#### Tab 2: 🎮 Stations & Buttons
- Statistics for your extracted buttons:
  - 71 Total Stations
  - 470 Total Buttons
  - 42 Configured Stations
- Quick access to re-run button extraction
- View current configuration endpoint

#### Tab 3: 📚 Help
Complete documentation including:
- Loads.json format examples
- Load ID numbering system (1xxx = Master 1, 2xxx = Master 2)
- Station numbering guide
- Automatic extraction instructions
- Step-by-step configuration guides

## How to Use

### Managing Refresh Interval

1. Open **Settings** page: `http://your-pi:8000/ui/settings.html`
2. Scroll to "Status Refresh Interval"
3. Change value (examples):
   - `5` = Refresh every 5 seconds (faster)
   - `30` = Refresh every 30 seconds (slower)
   - `0` = Disable auto-refresh (manual only)
4. Changes apply immediately - no save needed!

### Configuring Rooms and Loads

1. Open **Configuration** page: `http://your-pi:8000/ui/config.html`
2. Click the "💡 Loads & Rooms" tab
3. Edit the JSON to add/modify rooms:

```json
{
  "Living Room": {
    "loads": [1101, 1102, 1103],
    "master": 1,
    "icon": "🛋️"
  },
  "Kitchen": {
    "loads": [1201, 1202, 1203, 1204],
    "master": 1,
    "icon": "🍽️"
  }
}
```

4. Click **✓ Validate** to check syntax
5. Click **💾 Save** to apply changes

### Understanding Load Numbers

**Format:** `[Master][Load Number]`

Examples:
- `1101` = Master 1, Load 101
- `1234` = Master 1, Load 234
- `2101` = Master 2, Load 101
- `2225` = Master 2, Load 225

To find your load numbers:
1. Open Vantage Design Center
2. Go to **Loads** section
3. Note the load numbers (e.g., "Load 101")
4. Prefix with master: Master 1 → `1101`, Master 2 → `2101`

### Adding Stations and Buttons

**Option A: Automatic Extraction (Recommended)**

1. Export your Vantage configuration from Design Center
2. Save to `Info/Home Prado Ver.txt`
3. Run: `python scripts\extract_buttons.py`
4. Result: All 470 buttons configured automatically!

**Option B: Manual Configuration**

1. Open Configuration page → "🎮 Stations & Buttons" tab
2. View the format guide
3. Manually edit the extracted `config/loads.json`

Example station format:
```json
{
  "station_23": {
    "name": "Kitchen",
    "station": 23,
    "master": 1,
    "buttons": {
      "button_1": {
        "name": "Island Pendant",
        "button": 1,
        "event_type": "DIM",
        "loads": [1201]
      },
      "button_5": {
        "name": "All On",
        "button": 5,
        "event_type": "PRESET_ON",
        "loads": [1201, 1202, 1203, 1204]
      }
    }
  }
}
```

## Navigation

Updated navigation on all pages:
- 🏠 **Home** - Main control interface
- 🎛️ **Control** - Room/load controls
- ⚙️ **Settings** - Bridge configuration (IP, port, timeouts, **refresh interval**)
- 🔧 **Configuration** - Rooms, loads, stations (NEW!)
- 📊 **Status** - System status endpoint

## Files Updated

1. **`app/static/settings.html`**
   - Added status_refresh input field
   - Added dynamic refresh interval JavaScript
   - Updated to match dark theme

2. **`app/static/config.html`** (NEW)
   - Complete configuration manager
   - Three-tab interface
   - JSON editor with validation
   - Live statistics
   - Comprehensive help documentation

## Next Steps

To fully enable the configuration manager, you'll need to add backend endpoints:

```python
# In bridge.py

@app.post("/api/config/loads")
async def save_loads_config(config: dict):
    """Save loads.json configuration"""
    with open("config/loads.json", "w") as f:
        json.dump(config, f, indent=2)
    return {"status": "ok", "message": "Configuration saved"}

@app.get("/api/config/loads")
async def get_loads_config():
    """Get current loads.json"""
    with open("config/loads.json", "r") as f:
        return json.load(f)
```

## Benefits

✅ **Easy configuration** - Edit rooms/loads through web UI
✅ **No SSH required** - All changes via browser
✅ **Validation** - Check JSON syntax before saving
✅ **Statistics** - See your configuration at a glance
✅ **Guided setup** - Help tab with examples
✅ **Flexible refresh** - Control how often status updates
✅ **Dark theme** - Matches control interface

---

**Ready to use!** Just deploy to your Pi and access via browser.
