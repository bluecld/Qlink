# Configuration Examples

This document provides example configurations and usage patterns for the Vantage Q-Link Bridge.

## Table of Contents

- [Basic Setup](#basic-setup)
- [Home Assistant Integration](#home-assistant-integration)
- [API Usage Examples](#api-usage-examples)
- [Deployment Configurations](#deployment-configurations)
- [Automation Examples](#automation-examples)

## Basic Setup

### Deployment Configuration

**File**: `config/targets.json`

```json
{
  "host": "raspberrypi.local",
  "user": "pi",
  "key": "/home/youruser/.ssh/id_ed25519",
  "remote_dir": "/home/pi/qlink-bridge",
  "env": {
    "VANTAGE_IP": "192.168.1.200",
    "VANTAGE_PORT": "3041",
    "QLINK_FADE": "2.3",
    "QLINK_TIMEOUT": "2.0"
  }
}
```

### Load Configuration

**File**: `app/loads.json`

```json
{
  "rooms": [
    {
      "name": "Living Room",
      "floor": "1st Floor",
      "loads": [
        {"id": 101, "name": "Ceiling Lights", "type": "dimmer"},
        {"id": 102, "name": "Table Lamps", "type": "dimmer"},
        {"id": 103, "name": "Wall Sconces", "type": "dimmer"}
      ],
      "buttons": [
        {"station": 23, "button": 1, "name": "All On"},
        {"station": 23, "button": 2, "name": "Movie Mode"},
        {"station": 23, "button": 3, "name": "All Off"}
      ]
    },
    {
      "name": "Kitchen",
      "floor": "1st Floor",
      "loads": [
        {"id": 110, "name": "Main Lights", "type": "dimmer"},
        {"id": 111, "name": "Under Cabinet", "type": "dimmer"}
      ]
    }
  ]
}
```

## Home Assistant Integration

### Full Configuration Example

**File**: `homeassistant/configuration.yaml`

```yaml
# REST Commands for Vantage Control
rest_command:
  vantage_light_on:
    url: "http://BRIDGE_IP:8000/device/{{ load_id }}/set"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: '{"switch": "on", "brightness": {{ (brightness / 255 * 100) | round(0) }}}'

  vantage_light_off:
    url: "http://BRIDGE_IP:8000/device/{{ load_id }}/set"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: '{"switch": "off"}'

# Sensors for Light Status
sensor:
  - platform: rest
    name: "Living Room Ceiling Status"
    unique_id: vantage_load_101_status
    resource: "http://BRIDGE_IP:8000/load/101/status"
    value_template: "{{ value_json.resp | int }}"
    scan_interval: 30

# Template Lights
light:
  - platform: template
    lights:
      living_room_ceiling:
        friendly_name: "Living Room Ceiling"
        unique_id: vantage_load_101
        value_template: "{{ (states('sensor.vantage_load_101_status') | int(0)) > 0 }}"
        level_template: "{{ ((states('sensor.vantage_load_101_status') | int(0)) * 2.55) | round(0) }}"
        turn_on:
          service: rest_command.vantage_light_on
          data:
            load_id: 101
            brightness: "{{ brightness | default(255) }}"
        turn_off:
          service: rest_command.vantage_light_off
          data:
            load_id: 101

# HomeKit Bridge
homekit:
  filter:
    include_domains:
      - light
  entity_config:
    light.living_room_ceiling:
      name: "Living Room Lights"

# Database Configuration (for SD card)
recorder:
  purge_keep_days: 3
  commit_interval: 30
  db_max_retries: 5
```

### Minimal Configuration (Single Room)

```yaml
rest_command:
  vantage_on:
    url: "http://192.168.1.100:8000/device/{{ load_id }}/set"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: '{"switch": "on", "brightness": {{ brightness }}}'

sensor:
  - platform: rest
    name: "Bedroom Light Status"
    resource: "http://192.168.1.100:8000/load/201/status"
    value_template: "{{ value_json.resp }}"
    scan_interval: 30

light:
  - platform: template
    lights:
      bedroom_main:
        value_template: "{{ states('sensor.bedroom_light_status') | int > 0 }}"
        turn_on:
          service: rest_command.vantage_on
          data:
            load_id: 201
            brightness: 100
        turn_off:
          service: rest_command.vantage_on
          data:
            load_id: 201
            brightness: 0
```

## API Usage Examples

### Control Lights with curl

```bash
# Turn on light to 75%
curl -X POST http://BRIDGE_IP:8000/device/101/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on", "brightness": 75}'

# Turn off light
curl -X POST http://BRIDGE_IP:8000/device/101/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "off"}'

# Get light status
curl http://BRIDGE_IP:8000/load/101/status

# Get full configuration
curl http://BRIDGE_IP:8000/config | jq

# Press button (trigger scene)
curl -X POST http://BRIDGE_IP:8000/button/23/1
```

### Python Integration

```python
import requests

class VantageBridge:
    def __init__(self, host, port=8000):
        self.base_url = f"http://{host}:{port}"

    def set_light(self, load_id, brightness, fade=2.0):
        """Set light to specific brightness"""
        url = f"{self.base_url}/device/{load_id}/set"
        payload = {
            "switch": "on" if brightness > 0 else "off",
            "brightness": brightness,
            "fade": fade
        }
        return requests.post(url, json=payload)

    def get_status(self, load_id):
        """Get current light status"""
        url = f"{self.base_url}/load/{load_id}/status"
        response = requests.get(url)
        return response.json()

    def press_button(self, station, button):
        """Trigger a scene button"""
        url = f"{self.base_url}/button/{station}/{button}"
        return requests.post(url)

# Usage
bridge = VantageBridge("192.168.1.100")

# Turn on light
bridge.set_light(101, 75)

# Get status
status = bridge.get_status(101)
print(f"Light brightness: {status['resp']}%")

# Trigger scene
bridge.press_button(23, 1)
```

### Node.js Integration

```javascript
const axios = require('axios');

class VantageBridge {
  constructor(host, port = 8000) {
    this.baseUrl = `http://${host}:${port}`;
  }

  async setLight(loadId, brightness) {
    const url = `${this.baseUrl}/device/${loadId}/set`;
    const data = {
      switch: brightness > 0 ? 'on' : 'off',
      brightness: brightness
    };
    return axios.post(url, data);
  }

  async getStatus(loadId) {
    const url = `${this.baseUrl}/load/${loadId}/status`;
    const response = await axios.get(url);
    return response.data;
  }

  async pressButton(station, button) {
    const url = `${this.baseUrl}/button/${station}/${button}`;
    return axios.post(url);
  }
}

// Usage
const bridge = new VantageBridge('192.168.1.100');

// Turn on light
await bridge.setLight(101, 75);

// Get status
const status = await bridge.getStatus(101);
console.log(`Brightness: ${status.resp}%`);

// Trigger scene
await bridge.pressButton(23, 1);
```

## Deployment Configurations

### Development (Local Testing)

```bash
# Set environment variables
export VANTAGE_IP="192.168.1.200"
export VANTAGE_PORT="3041"

# Run bridge
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000 --reload
```

### Production (Systemd Service)

**File**: `/etc/systemd/system/qlink-bridge.service`

```ini
[Unit]
Description=Vantage Q-Link Bridge
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/qlink-bridge
Environment="VANTAGE_IP=192.168.1.200"
Environment="VANTAGE_PORT=3041"
ExecStart=/home/pi/qlink-bridge/.venv/bin/uvicorn app.bridge:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

### Docker Deployment

```yaml
version: '3.8'
services:
  qlink-bridge:
    build: .
    container_name: qlink-bridge
    ports:
      - "8000:8000"
    environment:
      - VANTAGE_IP=192.168.1.200
      - VANTAGE_PORT=3041
      - QLINK_FADE=2.3
    volumes:
      - ./config:/app/config
    restart: unless-stopped
```

## Automation Examples

### Time-Based Lighting

```yaml
# Home Assistant automation
automation:
  - alias: "Morning Lights"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      - service: light.turn_on
        entity_id: light.kitchen_main
        data:
          brightness: 128
      - service: light.turn_on
        entity_id: light.living_room_ceiling
        data:
          brightness: 64

  - alias: "Evening Lights"
    trigger:
      platform: sun
      event: sunset
    action:
      service: light.turn_on
      entity_id:
        - light.entry_lights
        - light.exterior_lights
      data:
        brightness: 255
```

### Motion-Activated Lighting

```yaml
automation:
  - alias: "Hallway Motion Lights"
    trigger:
      platform: state
      entity_id: binary_sensor.hallway_motion
      to: 'on'
    action:
      service: light.turn_on
      entity_id: light.hallway_lights
      data:
        brightness: 128

  - alias: "Hallway Lights Off"
    trigger:
      platform: state
      entity_id: binary_sensor.hallway_motion
      to: 'off'
      for:
        minutes: 2
    action:
      service: light.turn_off
      entity_id: light.hallway_lights
```

### Scene Management

```yaml
scene:
  - name: "Movie Time"
    entities:
      light.living_room_ceiling:
        state: on
        brightness: 30
      light.living_room_table_lamps:
        state: off
      light.hall_lights:
        state: on
        brightness: 10

  - name: "Dinner Party"
    entities:
      light.dining_room_chandelier:
        state: on
        brightness: 180
      light.kitchen_main:
        state: on
        brightness: 128
      light.entry_lights:
        state: on
        brightness: 200
```

## Network Configuration

### Raspberry Pi Static IP

**File**: `/etc/dhcpcd.conf`

```
interface eth0
static ip_address=192.168.1.100/24
static routers=192.168.1.1
static domain_name_servers=192.168.1.1
```

### Firewall Rules (Optional)

```bash
# Allow bridge access from local network only
sudo ufw allow from 192.168.1.0/24 to any port 8000

# Allow SSH from specific IP
sudo ufw allow from 192.168.1.50 to any port 22

# Enable firewall
sudo ufw enable
```

## Backup Scripts

### Automated Configuration Backup

```bash
#!/bin/bash
# backup.sh - Backup bridge configuration

BACKUP_DIR="/home/pi/backups"
DATE=$(date +%Y%m%d_%H%M%S)

mkdir -p $BACKUP_DIR

# Backup bridge files
tar -czf $BACKUP_DIR/qlink-bridge-$DATE.tar.gz \
  /home/pi/qlink-bridge/app/loads.json \
  /home/pi/qlink-bridge/config/ \
  /etc/systemd/system/qlink-bridge.service

# Keep only last 7 backups
ls -t $BACKUP_DIR/qlink-bridge-*.tar.gz | tail -n +8 | xargs rm -f

echo "Backup completed: qlink-bridge-$DATE.tar.gz"
```

### Restore from Backup

```bash
#!/bin/bash
# restore.sh - Restore from backup

BACKUP_FILE=$1

if [ -z "$BACKUP_FILE" ]; then
  echo "Usage: ./restore.sh <backup-file.tar.gz>"
  exit 1
fi

# Stop service
sudo systemctl stop qlink-bridge

# Restore files
tar -xzf $BACKUP_FILE -C /

# Restart service
sudo systemctl start qlink-bridge

echo "Restore completed from $BACKUP_FILE"
```

## Monitoring and Logging

### Log Rotation

**File**: `/etc/logrotate.d/qlink-bridge`

```
/var/log/qlink-bridge.log {
    daily
    rotate 7
    compress
    delaycompress
    missingok
    notifempty
    create 644 pi pi
}
```

### Monitoring Script

```bash
#!/bin/bash
# monitor.sh - Check bridge health

BRIDGE_URL="http://localhost:8000/healthz"

# Check if bridge is responding
if curl -f -s $BRIDGE_URL > /dev/null; then
  echo "Bridge is healthy"
  exit 0
else
  echo "Bridge is down - attempting restart"
  sudo systemctl restart qlink-bridge
  sleep 5

  if curl -f -s $BRIDGE_URL > /dev/null; then
    echo "Bridge restarted successfully"
    exit 0
  else
    echo "Bridge restart failed - manual intervention required"
    exit 1
  fi
fi
```

## Troubleshooting

### Connection Test Script

```bash
#!/bin/bash
# test-connection.sh - Verify bridge connectivity

echo "Testing Vantage Controller..."
nc -zv 192.168.1.200 3041

echo ""
echo "Testing Bridge API..."
curl -s http://localhost:8000/healthz | jq

echo ""
echo "Testing Light Status..."
curl -s http://localhost:8000/load/101/status | jq

echo ""
echo "Testing Configuration Endpoint..."
curl -s http://localhost:8000/config | jq -r '.ip, .port'
```

---

## Notes

- Replace `BRIDGE_IP` with your actual Raspberry Pi IP address
- Replace load IDs (101, 102, etc.) with your actual Vantage load IDs
- Replace station/button numbers with your actual button assignments
- Adjust brightness values (0-100) as needed
- All examples use port 8000 (default bridge port)

For more examples and community configurations, visit the [GitHub Discussions](https://github.com/bluecld/Qlink/discussions).
