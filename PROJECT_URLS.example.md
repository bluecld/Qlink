# Vantage Q-Link Home Automation - Quick Reference URLs

## Primary Access URLs

### Home Assistant Web UI
- **Local Network**: http://192.168.1.213:8123
- **Tailscale VPN**: http://100.81.88.76:8123
- **Login**: Use credentials created during onboarding

### Vantage Bridge API
- **Local Network**: http://192.168.1.213:8000
- **Tailscale VPN**: http://100.81.88.76:8000
- **Status**: Bridge should always be running via systemd/screen

### Vantage Controller (Q-Link)
- **Telnet Access**: telnet://192.168.1.200:3040
- **Protocol**: Q-Link (ASCII V-Commands)
- **Ports**: 3040 (control), 3041 (status)

---

## Bridge API Endpoints

### Configuration & Status

**Get All Device Configuration:**
```
GET http://192.168.1.213:8000/config
```
Returns: Complete room/floor/device hierarchy with all loads and stations

**Check Specific Light Status:**
```
GET http://192.168.1.213:8000/load/{LOAD_ID}/status
Example: http://192.168.1.213:8000/load/254/status
```
Returns: `{"resp": "75"}` (brightness 0-100)

**Bridge Information:**
```
GET http://192.168.1.213:8000/about
```
Returns: Version, manufacturer, model info

### Control Commands

**Turn Light On/Off with Brightness:**
```
POST http://192.168.1.213:8000/device/{LOAD_ID}/set
Content-Type: application/json
Body: {"switch": "on", "brightness": 75}
Body: {"switch": "off"}
```

**Example curl commands:**
```bash
# Get Master Bedroom Main status
curl http://192.168.1.213:8000/load/254/status

# Turn on at 50%
curl -X POST http://192.168.1.213:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on", "brightness": 50}'

# Turn off
curl -X POST http://192.168.1.213:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "off"}'
```

---

## Network Configuration

| Device | Local IP | Tailscale IP | Ports | Notes |
|--------|----------|--------------|-------|-------|
| Raspberry Pi | 192.168.1.213 | 100.81.88.76 | SSH: 22, Bridge: 8000, HA: 8123 | Running bridge.py + HA |
| Vantage Controller | 192.168.1.200 | N/A | 3040 (control), 3041 (status) | Q-Link protocol |
| Home NAS | 192.168.1.129 | N/A | SMB/NFS | Backup destination |
| Work NAS | 192.168.0.62 | N/A | SSH: 22, SMB: 445 | Via OpenVPN |
| SmartThings Hub | 192.168.1.155 | N/A | N/A | Not actively used |

---

## SSH Access

**Connect to Raspberry Pi:**
```bash
# Local network
ssh pi@192.168.1.213

# Via Tailscale (when remote)
ssh pi@100.81.88.76
```

**Default user**: pi
**Authentication**: SSH key

---

## Common Management Commands

### Home Assistant

**Restart Container:**
```bash
ssh pi@192.168.1.213 "sudo docker restart homeassistant"
```

**View Logs:**
```bash
ssh pi@192.168.1.213 "sudo docker logs homeassistant --tail 50"
ssh pi@192.168.1.213 "sudo docker logs homeassistant --tail 100 -f"  # follow mode
```

**Check Container Status:**
```bash
ssh pi@192.168.1.213 "sudo docker ps | grep homeassistant"
```

**Edit Configuration:**
```bash
ssh pi@192.168.1.213
sudo nano /home/pi/homeassistant/configuration.yaml
sudo docker restart homeassistant
```

**Check Disk Usage:**
```bash
ssh pi@192.168.1.213 "df -h / && du -sh /var/lib/docker /home/pi/homeassistant"
```

**Clean Docker Images:**
```bash
ssh pi@192.168.1.213 "sudo docker system prune -a"
```

### Bridge.py

**Check Bridge Status:**
```bash
ssh pi@192.168.1.213 "ps aux | grep '[u]vicorn.*bridge'"
```

**View Bridge Logs:**
```bash
ssh pi@192.168.1.213 "tail -f /home/pi/bridge.log"
```

**Restart Bridge:**
```bash
ssh pi@192.168.1.213
cd /home/pi/qlink-bridge
source .venv/bin/activate
uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

### NAS Backup

**Check Backup Status:**
```bash
ssh pi@192.168.1.213 "tail -50 /home/pi/nas-backup-cron.log"
```

**View Backup Logs:**
```bash
ssh pi@192.168.1.213 "tail -100 /home/pi/nas-backup.log"
```

**Manual Backup Run:**
```bash
ssh pi@192.168.1.213 "/home/pi/nas-backup.sh --execute"
```

**Check Cron Schedule:**
```bash
ssh pi@192.168.1.213 "crontab -l"
```

---

## File Locations

### On Raspberry Pi

**Home Assistant:**
- Configuration: `/home/pi/homeassistant/configuration.yaml`
- Backup: `/home/pi/homeassistant/configuration.yaml.backup-6lights`
- Database: `/home/pi/homeassistant/home-assistant_v2.db`
- Logs: `/home/pi/homeassistant/home-assistant.log`
- Docker volume: `/home/pi/homeassistant/`

**Bridge:**
- Code: `/home/pi/qlink-bridge/`
- Main script: `/home/pi/qlink-bridge/app/bridge.py`
- Virtual env: `/home/pi/qlink-bridge/.venv/`
- Logs: `/home/pi/bridge.log`

**Backup:**
- Script: `/home/pi/nas-backup.sh`
- Cron log: `/home/pi/nas-backup-cron.log`
- Main log: `/home/pi/nas-backup.log`
- Mount point: `/home/pi/mnt/home_nas/`

**Generator Script:**
- Location: `/tmp/gen_ha_fixed.py`
- Purpose: Generate HA config with all lights

### On Windows Development Machine

**Project Root:**
- `C:\Qlink\`

**Documentation:**
- Setup Guide: `C:\Qlink\HOME_ASSISTANT_SETUP.md`
- Progress Notes: `C:\Qlink\NOTES.md`
- This File: `C:\Qlink\PROJECT_URLS.md`

**SmartThings:**
- Driver Guide: `C:\Qlink\SmartThings_Edge\DEVICE_ADDITION_GUIDE.md`
- Driver Code: `C:\Qlink\SmartThings_Edge\vantage-bridge-driver\`

**Bridge Code:**
- Main: `C:\Qlink\app\bridge.py`
- SSDP: `C:\Qlink\app\ssdp_advertiser.py`

**Scripts:**
- Device Creation: `C:\Qlink\create_smartthings_device.py`
- HA Generator: `C:\Qlink\generate_ha_lights.py`

---

## Documentation Resources

### Official Documentation

**Home Assistant:**
- Official Docs: https://www.home-assistant.io/docs/
- HomeKit Integration: https://www.home-assistant.io/integrations/homekit/
- Template Lights: https://www.home-assistant.io/integrations/light.template/
- RESTful Integration: https://www.home-assistant.io/integrations/rest_command/
- REST Sensor: https://www.home-assistant.io/integrations/rest/
- Recorder: https://www.home-assistant.io/integrations/recorder/

**Claude Code:**
- Documentation: https://docs.claude.com/en/docs/claude-code/
- Feedback/Issues: https://github.com/anthropics/claude-code/issues

**Docker:**
- Docker Hub HA: https://hub.docker.com/r/homeassistant/home-assistant

### Project-Specific Docs

**In this repository:**
- `HOME_ASSISTANT_SETUP.md` - Complete HA setup guide with troubleshooting
- `NOTES.md` - Project progress and implementation notes
- `SmartThings_Edge/DEVICE_ADDITION_GUIDE.md` - SmartThings integration guide

---

## Key Light Load IDs

### Currently Configured (6 lights from initial setup)

| Room | Light Name | Load ID | Entity ID |
|------|-----------|---------|-----------|
| Master Bedroom | 4x 6" Downlites Center | 254 | light.master_bedroom_4x_6_downlites_center |
| Master Bedroom | Reading Left | 241 | light.master_bedroom_reading_left |
| Master Bedroom | Reading Right | 240 | light.master_bedroom_reading_right |
| Kitchen | 10x 6" Downlites | 141 | light.kitchen_10x_6_downlites |
| Kitchen | Under Cabinet | 144 | light.kitchen_under_cabinet |
| Living Room | 2x 6" Downlites | 122 | light.living_room_2x_6_downlites |

### All Available Lights (132 total)

To see complete list with all load IDs organized by floor and room:
```bash
curl -s http://192.168.1.213:8000/config | python3 -m json.tool
```

Or generate new config:
```bash
ssh pi@192.168.1.213 "python3 /tmp/gen_ha_fixed.py"
```

---

## Troubleshooting URLs

### Check System Health

**Pi System Resources:**
```bash
ssh pi@192.168.1.213 "top -bn1 | head -15"
ssh pi@192.168.1.213 "free -h"
ssh pi@192.168.1.213 "df -h"
```

**Network Connectivity:**
```bash
# Test bridge from local machine
curl http://192.168.1.213:8000/config

# Test from Pi to Vantage controller
ssh pi@192.168.1.213 "telnet 192.168.1.200 3040"

# Test HA web UI
curl -I http://192.168.1.213:8123
```

**Service Status:**
```bash
# Check if bridge is running
ssh pi@192.168.1.213 "ps aux | grep bridge"

# Check if HA container is running
ssh pi@192.168.1.213 "sudo docker ps"

# Check if NAS is mounted
ssh pi@192.168.1.213 "df -h | grep nas"
```

### Common Issues

**Bridge not responding:**
```bash
ssh pi@192.168.1.213
cd /home/pi/qlink-bridge
source .venv/bin/activate
uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

**HA won't start:**
```bash
# Check logs for errors
ssh pi@192.168.1.213 "sudo docker logs homeassistant | tail -100"

# Verify config syntax
ssh pi@192.168.1.213 "sudo docker exec homeassistant python -m homeassistant --script check_config"
```

**HomeKit not pairing:**
- Ensure iPhone and Pi are on same local network
- HomeKit requires mDNS (doesn't work over VPN)
- Check HomeKit Bridge is running in HA UI: Settings → Devices & Services
- Get pairing code from HA UI HomeKit integration card

---

## Git Repository

**Local Repository:**
```
C:\Qlink\
```

**Recent Commits:**
- b277865 - Add Home Assistant + HomeKit Bridge for Siri voice control
- 905d023 - Add NAS backup automation via Raspberry Pi bridge
- 1c72e03 - Add progress notes for Vantage bridge
- 2a7019e - Improve Vantage bridge discovery and HTTPS support

**Commit Changes:**
```bash
cd C:\Qlink
git status
git add <files>
git commit -m "Description"
```

---

## Quick Reference Card

### Most Common Tasks

**Access HA Dashboard:**
```
http://192.168.1.213:8123
```

**Restart HA after config change:**
```bash
ssh pi@192.168.1.213 "sudo docker restart homeassistant"
```

**Test a light:**
```bash
curl -X POST http://192.168.1.213:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on", "brightness": 75}'
```

**View recent logs:**
```bash
ssh pi@192.168.1.213 "sudo docker logs homeassistant --tail 50"
```

**Check backup status:**
```bash
ssh pi@192.168.1.213 "tail -20 /home/pi/nas-backup-cron.log"
```

---

**Last Updated:** 2025-11-06
**Project:** Vantage Q-Link Home Automation
**System:** Raspberry Pi + Home Assistant + HomeKit + Siri
