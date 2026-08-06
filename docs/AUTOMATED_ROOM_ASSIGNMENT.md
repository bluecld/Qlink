# Automated Room Assignment Solution

## Problem
You have 132 Vantage lights that need room assignments for HomeKit/SmartThings import, but doing this manually is tedious.

## Solution
Two scripts have been created to automatically assign all lights to their correct rooms:

### Step 1: Generate Area Mappings (Already Done ✅)
```bash
python scripts\generate_ha_areas.py
```

This created `config\ha_areas.json` with:
- **66 rooms** (Bar, Kitchen, Master Bedroom, etc.)
- **132 lights** mapped to their correct rooms
- Floor assignments (1st Floor, 2nd Floor, Exterior)

### Step 2: Apply Areas to Home Assistant

#### Option A: PowerShell Script (Recommended)
```powershell
# Run from C:\Qlink directory
.\scripts\apply_ha_areas.ps1
```

**First time setup:**
1. Go to http://<BRIDGE_IP>:8123/profile/security
2. Scroll to "Long-Lived Access Tokens"
3. Click "CREATE TOKEN"
4. Name it "Area Assignment Script"
5. Copy the token
6. Paste when prompted by the script

**What it does:**
- Creates all 66 areas in Home Assistant
- Assigns each of your 132 lights to the correct room
- Handles existing areas gracefully
- Shows progress for each room

#### Option B: Manual via Home Assistant UI
If you prefer not to use scripts:
1. Open `config\ha_areas.json` in the JSON output section
2. For each room, manually:
   - Go to Settings → Areas & Zones
   - Create area (e.g., "Bar", "Kitchen")
   - Go to Settings → Devices & Services → Entities
   - Filter by room name
   - Select all lights in that room
   - Assign to area

## Benefits After Running Script

### 1. Home Assistant
- All lights organized by room in the UI
- Easy to control entire rooms
- Better dashboards and automations

### 2. HomeKit (via HASS Bridge)
- When you pair your HomeKit bridges, rooms auto-assign!
- No manual room assignment during import
- Siri commands work by room: "Hey Siri, turn on Kitchen lights"

### 3. SmartThings
- Devices imported with room metadata
- Easier organization in SmartThings app
- Room-based scenes and automations

## Verification

After running the script:

1. **Check Home Assistant:**
   - Go to http://<BRIDGE_IP>:8123
   - Settings → Areas & Zones
   - You should see 66 areas

2. **Check Light Assignments:**
   - Settings → Devices & Services → Entities
   - Filter by "light."
   - Each light should show an area in the "Area" column

3. **Re-pair HomeKit SmartThings Bridge:**
   - Settings → Devices & Services → HomeKit
   - Find "SmartThings Bridge"
   - Click "CONFIGURE"
   - Copy QR code or pairing code
   - Open Apple Home app
   - Add Accessory → Scan QR code
   - **Rooms will automatically assign based on Home Assistant areas!**

## Example Output

```
📁 Bar (1st Floor) - 4 lights
  ✅ light.bar_main_lights
  ✅ light.bar_under_cabinet
  ✅ light.bar_3x_6_downlites
  ✅ light.bar_3_pendants

📁 Kitchen (1st Floor) - 3 lights
  ✅ light.kitchen_10x_6_downlites
  ✅ light.kitchen_4_surface_lights
  ✅ light.kitchen_under_cabinet
```

## Troubleshooting

### Script fails with "401 Unauthorized"
- Token expired or invalid
- Create a new Long-Lived Access Token
- Run script again with new token

### Some entities show as "not found"
- Light entities might not be created yet
- Check if lights appear in Home Assistant
- Verify entity_id matches (e.g., `light.bar_main_lights`)

### Areas created but entities not assigned
- Restart Home Assistant: Settings → System → Restart
- Re-run the script after restart

## What's Next?

1. ✅ Run `.\scripts\apply_ha_areas.ps1` (5 minutes)
2. ✅ Verify areas in Home Assistant UI
3. ✅ Re-pair HomeKit SmartThings Bridge
4. 🎉 Enjoy organized smart home with room-based control!

## Files Created
- `scripts/generate_ha_areas.py` - Parses loads.json and generates area mappings
- `scripts/apply_ha_areas.ps1` - Applies areas to Home Assistant via REST API
- `config/ha_areas.json` - Area mapping database (66 rooms, 132 lights)
