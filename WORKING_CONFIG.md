# Vantage Lighting Control System - Working Configuration
## Date: October 15, 2025

### System Status:  WORKING

### Configuration
- **Bridge IP**: 192.168.1.213:8000
- **Vantage Controller**: 192.168.1.200:3041
- **Web Interface**: http://192.168.1.213:8000

### Key Settings
- **Command Format**: VLO@ {load_id} {level}
- **Port**: 3041 (write port, NOT 3040)
- **Line Ending**: CR (Carriage Return)
- **Timeout**: 2.0 seconds

### Working Features
 Accordion UI with collapsible floors
 Dropdown navigation between floors
 ON/OFF buttons working
 Dimmer sliders working (0-100%)
 "All Off" button per room
 66 rooms organized by floor
 Real-time control of Vantage loads

### Files Deployed to Pi
- /home/pi/qlink-bridge/app/bridge.py (VLO@ command format)
- /home/pi/qlink-bridge/app/static/home.html (accordion UI)
- /home/pi/qlink-bridge/app/static/index.html (diagnostic console)
- /home/pi/qlink-bridge/config/loads.json (66 rooms, inch marks replaced with 'in')
- /home/pi/qlink-bridge/.env (port 3041 configuration)

### Tested & Confirmed Working
- Load 250 (2x 6in Downlites) - ON/OFF working via web UI
- Load 249 (2 Under Cabinets) - working
- Load 337 - working
- Load 127 (Bar Main Lights) - working

### Notes
- Some load IDs in LoadL.pdf may not match actual Vantage system
- All inch marks (") replaced with "in" to avoid JavaScript quote issues
- Bridge auto-starts on Pi boot
- To restart: ssh pi@192.168.1.213 "pkill -9 uvicorn; cd ~/qlink-bridge && nohup .venv/bin/uvicorn app.bridge:app --host 0.0.0.0 --port 8000 > ~/bridge.log 2>&1 &"

### Next Steps (Optional)
- SmartThings Edge driver integration
- Deploy to production Pi (if separate from test rig)
- Update any remaining incorrect load IDs from LoadL.pdf
