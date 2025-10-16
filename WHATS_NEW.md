# What's New - October 16, 2025

## 🎨 New Dark Theme Web UI (v2)

Created a completely redesigned web interface with modern, sleek aesthetics and powerful new features.

### Visual Design
- **Dark Theme**: Beautiful dark blue gradient background (#1a1a2e → #16213e)
- **Glassmorphism**: Semi-transparent cards with backdrop blur effects
- **Purple Accents**: Consistent purple/indigo gradient theme (#667eea → #764ba2)
- **Smooth Animations**: 0.3s transitions on all interactive elements
- **Mobile Optimized**: Fully responsive, touch-friendly controls

### New Features

#### 1. Scene/Button Control 🎬
- Press physical button scenes from the web interface
- Common scenes: **On** (100%), **Medium** (60%), **Dim** (20%), **Off** (0%)
- Active scene button is highlighted
- Matches your physical wall stations (V23, V02, V20, etc.)

#### 2. Real-Time Polling 📊
- Automatically polls system every 10 seconds
- Shows **current load levels** (0-100%) next to each load
- Updates sliders to match actual state
- **Last update timestamp** visible
- **Connection status** with color-coded indicator:
  - 🟢 Green = Online
  - 🟡 Yellow = Warning
  - 🔴 Red = Offline

#### 3. Enhanced Feedback
- Toast notifications with color coding
- Loading states during operations
- Visual button press confirmation
- Smooth slider animations

### Bridge API Updates

Added 3 new endpoints to `bridge.py`:

```python
# Get current level of a load
GET /load/{id}/status
# Returns: {"resp": "R:V75"}  (75% level)

# Simulate button press
POST /button/{station}/{button}
# Example: POST /button/23/5  (Game Room On)

# Get button LED status (to be tested)
GET /button/{station}/{button}/status
# Returns LED state (on/off/blink)
```

### Command Discovery

Based on your `VLO@` success pattern, button commands likely use:
- **`VBTN@ {station} {button}`** - Press button (@ symbol needed)
- **`VLED {station} {button}`** - Query LED status (to be tested)

### Configuration Format

Updated `loads.json` to support button/station mappings:

```json
{
  "rooms": [
    {
      "name": "Game Room",
      "floor": "1st Floor",
      "station": 23,
      "loads": [...],
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

### Files Created

1. **`app/static/home-v2.html`** - New dark-themed UI with all features
2. **`app/bridge.py`** - Updated with 3 new endpoints
3. **`config/loads-with-buttons-example.json`** - Example config with buttons
4. **`docs/WEB_UI_V2.md`** - Complete feature documentation
5. **`docs/UI_DESIGN_PREVIEW.md`** - Visual design guide with mockups

### Documentation from Home Prado Ver.txt

Analyzed your complete Vantage system export:
- **355 programmed buttons** across 20+ stations
- Common button patterns identified (5=On, 6=Medium, 7=Dim, 8=Off)
- Scheduled automation documented (10 PM exterior off, midnight presets)
- Integration opportunities outlined

Created:
- **`Info/Button_Mappings_Summary.txt`** - All 355 button mappings
- **`Info/SYSTEM_OVERVIEW.md`** - Comprehensive system documentation

## Testing Plan (When Pi Online)

1. ✅ Deploy updated `bridge.py` to Pi
2. ✅ Test `VBTN@ 23 5` command (Game Room On)
3. ✅ Verify polling works with `VGL` commands
4. ✅ Test button LED status query command
5. ✅ Open `http://192.168.1.213:8000/ui/home-v2.html`
6. ✅ Verify scene buttons work
7. ✅ Check polling updates load levels automatically

## Next Steps

1. **Extract Button Data**: Parse all button mappings from Home Prado Ver.txt into loads.json
2. **Test Commands**: Confirm VBTN@, VLED formats when Pi is online
3. **Finalize Config**: Update loads.json with complete button/station data for all rooms
4. **Polish UI**: Fine-tune polling interval, add any requested features
5. **Optional**: Add SmartThings Edge driver integration

## Questions for You

1. **Do you like the dark theme design?** We can adjust colors, spacing, etc.
2. **Is 10 seconds a good polling interval?** Can make it faster/slower
3. **Want to add custom scenes?** Beyond the standard On/Medium/Dim/Off
4. **Any other UI features?** Color temperature controls, groups, favorites, etc.

---

**Ready to test when Pi is back online!** 🚀
