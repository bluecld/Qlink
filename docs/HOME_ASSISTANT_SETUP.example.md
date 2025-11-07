# Home Assistant + Vantage Q-Link + Siri Voice Control Setup

## Overview
This guide documents the Home Assistant installation on Raspberry Pi for controlling Vantage Q-Link lights via Siri using Apple HomeKit integration.

## Architecture
```
Siri → Apple Home → HomeKit Bridge → Home Assistant → RESTful API → bridge.py → Q-Link → Vantage Controller
```

## System Information
- **Raspberry Pi IP**: 192.168.1.213
- **Home Assistant URL**: http://192.168.1.213:8123
- **Bridge API**: http://192.168.1.213:8000
- **Vantage Controller**: 192.168.1.200:3040 (Q-Link protocol)

## Installation Summary

### 1. System Preparation
- Updated Raspberry Pi OS packages
- Installed Docker CE
- Verified bridge.py is running on port 8000

### 2. Home Assistant Installation
- Installed via Docker container
- Container name: `homeassistant`
- Mount point: `/home/pi/homeassistant:/config`
- Network mode: host
- Restart policy: unless-stopped

### 3. Home Assistant Configuration

**Configuration File**: `/home/pi/homeassistant/configuration.yaml`

The configuration includes:
- **REST Commands**: Control lights via bridge.py API
  - `vantage_light_on`: Turn on light with brightness (0-100)
  - `vantage_light_off`: Turn off light

- **REST Sensors**: Poll light status every 30 seconds
  - Returns brightness value 0-100 from bridge.py

- **Template Lights**: 6 lights configured
  - Master Bedroom Main (load 254)
  - Master Bedroom Reading Left (load 241)
  - Master Bedroom Reading Right (load 240)
  - Kitchen Main Lights (load 141)
  - Kitchen Under Cabinet (load 144)
  - Living Room Main (load 122)

- **HomeKit Bridge**: Exposes lights to Apple HomeKit
  - Filters to include only light domain
  - Custom friendly names for each light

### 4. Configured Lights

| Room | Light Name | Vantage Load ID | HomeKit Name |
|------|-----------|----------------|--------------|
| Master Bedroom | 4x 6" Downlites Center | 254 | Master Bedroom Lights |
| Master Bedroom | Reading Left | 241 | Master Bedroom Reading Left |
| Master Bedroom | Reading Right | 240 | Master Bedroom Reading Right |
| Kitchen | Main Lights | 141 | Kitchen Lights |
| Kitchen | Under Cabinet | 144 | Kitchen Under Cabinet |
| Living Room | Main | 122 | Living Room Lights |

## Next Steps: Adding to Apple Home

### Step 1: Access Home Assistant UI
1. Open a web browser on your local network
2. Navigate to: http://192.168.1.213:8123
3. Log in with your Home Assistant credentials

### Step 2: Get HomeKit Pairing Code
1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Find the **HomeKit Bridge** integration card
3. The pairing code (8-digit PIN) and QR code will be displayed
4. Note: If you don't see the code, click **Configure** on the HomeKit card

### Step 3: Add to Apple Home
1. Open the **Home** app on your iPhone or iPad
2. Tap the **+** button (top right)
3. Select **Add Accessory**
4. Choose one of these methods:
   - **Scan QR Code**: Point camera at QR code in HA UI
   - **Enter Code Manually**: Type the 8-digit PIN from HA UI
5. If prompted about "Uncertified Accessory", tap **Add Anyway**
6. Assign lights to rooms in your Apple Home setup
7. Tap **Done**

### Step 4: Test Siri Voice Control
Try these commands:
- "Hey Siri, turn on Master Bedroom Lights"
- "Hey Siri, turn off Kitchen Lights"
- "Hey Siri, set Living Room Lights to 50%"
- "Hey Siri, dim Master Bedroom Reading Left"

## Technical Details

### REST API Endpoints (bridge.py)

**Get Load Status**:
```bash
curl http://localhost:8000/load/254/status
# Response: {"resp": "75"}  # Brightness 0-100
```

**Set Load**:
```bash
curl -X POST http://localhost:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on", "brightness": 75}'
```

**Get Full Config**:
```bash
curl http://localhost:8000/config
```

### Home Assistant Container Management

**View Logs**:
```bash
ssh pi@192.168.1.213
sudo docker logs homeassistant --tail 100
```

**Restart Container**:
```bash
sudo docker restart homeassistant
```

**Stop/Start Container**:
```bash
sudo docker stop homeassistant
sudo docker start homeassistant
```

### Configuration File Location
- **Container**: `/config/configuration.yaml`
- **Host**: `/home/pi/homeassistant/configuration.yaml`

To edit configuration:
1. SSH to Pi: `ssh pi@192.168.1.213`
2. Edit file: `sudo nano /home/pi/homeassistant/configuration.yaml`
3. Restart HA: `sudo docker restart homeassistant`

## Adding More Lights

To add additional lights to the HomeKit integration:

1. Get available loads from bridge:
```bash
curl http://192.168.1.213:8000/config | python3 -m json.tool
```

2. Edit `/home/pi/homeassistant/configuration.yaml`

3. Add new sensor (example for load 453):
```yaml
sensor:
  - platform: rest
    name: "Vantage Load 453 Status"
    unique_id: vantage_load_453_status
    resource: "http://localhost:8000/load/453/status"
    value_template: "{{ value_json.resp | int }}"
    scan_interval: 30
```

4. Add new template light:
```yaml
light:
  - platform: template
    lights:
      new_light_name:
        friendly_name: "Your Light Name"
        unique_id: vantage_load_453
        value_template: "{{ (states('sensor.vantage_load_453_status') | int(0)) > 0 }}"
        level_template: "{{ ((states('sensor.vantage_load_453_status') | int(0)) * 2.55) | round(0) }}"
        turn_on:
          service: rest_command.vantage_light_on
          data:
            load_id: 453
            brightness: "{{ brightness | default(255) }}"
        turn_off:
          service: rest_command.vantage_light_off
          data:
            load_id: 453
```

5. Add HomeKit entity config:
```yaml
homekit:
  entity_config:
    light.new_light_name:
      name: "HomeKit Display Name"
```

6. Restart Home Assistant: `sudo docker restart homeassistant`

## Troubleshooting

### Lights Not Responding
1. Check bridge.py is running: `curl http://localhost:8000/config`
2. Check HA logs: `sudo docker logs homeassistant --tail 50`
3. Verify Vantage controller connectivity from Pi

### HomeKit Not Showing in Apple Home
1. Ensure devices are on same network
2. Check HomeKit Bridge is running in HA UI
3. Remove and re-add accessory in Apple Home
4. Restart Home Assistant container

### Bridge API Errors
1. Check bridge.py process: `ps aux | grep bridge.py`
2. Verify Vantage controller is reachable: `telnet 192.168.1.200 3040`
3. Check bridge logs

## Maintenance

### NAS Backup Schedule
- **Frequency**: Once daily at 2:00 AM
- **Impact**: Minimal resource usage, should not affect HA performance

### Home Assistant Updates
To update Home Assistant:
```bash
sudo docker pull ghcr.io/home-assistant/home-assistant:stable
sudo docker stop homeassistant
sudo docker rm homeassistant
sudo docker run -d \
  --name homeassistant \
  --restart=unless-stopped \
  -e TZ=America/New_York \
  -v /home/pi/homeassistant:/config \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable
```

## Resources
- **Home Assistant Docs**: https://www.home-assistant.io/docs/
- **HomeKit Integration**: https://www.home-assistant.io/integrations/homekit/
- **Template Lights**: https://www.home-assistant.io/integrations/light.template/
- **RESTful Integration**: https://www.home-assistant.io/integrations/rest_command/
