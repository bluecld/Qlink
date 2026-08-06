# Home Assistant Integration

This guide explains how to integrate the Vantage Q-Link Bridge with Home Assistant for advanced home automation and voice control via Apple HomeKit/Siri.

## Overview

The integration uses Home Assistant's RESTful platform to consume the bridge's REST API, creating virtual light entities that can be controlled via:
- Home Assistant web interface
- Apple HomeKit / Siri voice commands
- Home Assistant automations
- Any HomeKit-compatible app

## Architecture

```
Siri / HomeKit → Home Assistant → REST API → Q-Link Bridge → Vantage Controller
```

## Prerequisites

- **Raspberry Pi** running the Q-Link Bridge
- **Home Assistant** installed (Docker recommended)
- **Network access** between HA and the bridge
- **Bridge running** and accessible via HTTP

## Installation

> **How the reference deployment runs:** Home Assistant OS as a **KVM/libvirt
> guest** on the same Linux host as the bridge, bridged onto the LAN. In that
> setup the bridge base URL is simply the host's LAN address,
> `http://<BRIDGE_IP>:8000` - do **not** pass `--ha-in-docker`.
> Manage the guest with `virsh --connect qemu:///system`. See `docs/RUNBOOK.md`.
>
> The Docker instructions below remain valid if you prefer a container install.

### Option 1: Docker Installation (Recommended)

```bash
# Create config directory
mkdir -p /home/pi/homeassistant

# Run Home Assistant container
docker run -d \
  --name homeassistant \
  --restart=unless-stopped \
  -e TZ=America/New_York \
  -v /home/pi/homeassistant:/config \
  --network=host \
  ghcr.io/home-assistant/home-assistant:stable
```

Access Home Assistant at: `http://YOUR_PI_IP:8123`

### Option 2: Home Assistant OS

Install Home Assistant OS on a separate device or SD card. See: https://www.home-assistant.io/installation/

## Configuration

### Step 1: Generate Configuration

Use the included generator script to create your Home Assistant configuration:

```bash
# On your Pi (aggregated mode reduces load on Vantage)
python3 generate_ha_config.py --use-aggregated > /tmp/ha_config.yaml
# If HA runs in Docker without --network=host, add:
#   --ha-in-docker
```

The script will:
1. Fetch your configuration from the bridge API
2. Generate REST sensors for all lights (or one aggregated sensor)
3. Create template light entities
4. Configure HomeKit Bridge integration

Pick the bridge base URL to match how HA is installed:

| HA install | Bridge base URL | Flag |
|---|---|---|
| HAOS / VM bridged to the LAN | `http://<BRIDGE_IP>:8000` | `--bridge-base-url http://<BRIDGE_IP>:8000` |
| Docker, no `--network=host` | `http://172.17.0.1:8000` | `--ha-in-docker` |
| Docker with `--network=host`, same box | `http://localhost:8000` | *(default)* |

> If you run the generator on a different machine, provide `--url http://YOUR_BRIDGE:8000/config` to fetch the config, and set `--bridge-base-url` to the address Home Assistant can reach.

### Step 2: Deploy Configuration

Copy the generated config to Home Assistant:

```bash
sudo cp /tmp/ha_config.yaml /home/pi/homeassistant/configuration.yaml
sudo docker restart homeassistant
```

### Step 3: Verify Setup

1. Open Home Assistant: `http://YOUR_PI_IP:8123`
2. Navigate to **Settings** → **Devices & Services**
3. Verify lights are appearing
4. Check for errors in **Settings** → **System** → **Logs**

### Endpoint Alignment & Verification

1. Run the generator with the same base URL Home Assistant will reach (see Step 1).
2. Confirm the emitted YAML references `http://YOUR_BRIDGE:8000/device/{{ load_id }}/set` and `http://YOUR_BRIDGE:8000/load/{id}/status`.
3. Validate the bridge API directly:

  ```bash
  curl http://<BRIDGE_TAILSCALE_IP>:8000/about
  curl http://<BRIDGE_TAILSCALE_IP>:8000/api/leds
  curl http://<BRIDGE_TAILSCALE_IP>:8000/load/254/status
  ```

4. Update Home Assistant's `configuration.yaml` (or packages) with the regenerated REST commands and sensors, then reload the REST integration.
5. If any HA entities still call `/api/status`, search your config for that path and swap it for `/api/leds` (panel views) or `/load/{id}/status` (per-load sensors).

### Large-installation performance notes

If you have many loads (~100+) using individual `rest` sensors, Home Assistant may generate many concurrent HTTP requests every polling cycle which can overwhelm the bridge and lead to `Timeout while fetching data` and stale dashboards. To avoid this:

- Use `generate_ha_config.py --use-aggregated --scan-interval 120 --timeout 15` to produce a config that polls less frequently.
- If `/api/loads` is too slow on large installs, use `--use-subsets` to split load polling across 4 faster endpoints.
- Add `--use-priority` to keep recently used or active loads fresh without polling every load frequently.
- Prefer limiting the set of sensors to only the lights you actually want in the dashboard using `--include-loads` (comma-separated IDs).
- For dashboard-only LED indications, use the bridge's `/api/leds` endpoint rather than per-load REST sensors.
- If you need all loads visible, consider a bridge enhancement to return a consolidated `/api/loads` endpoint; this reduces HA-to-bridge request counts.

Tips to recover a stale dashboard:

1. Stop Home Assistant (or restart the container).
2. Replace `configuration.yaml` with a smaller generated file (or use packages) so only the critical sensors are active.
3. Restart HA and confirm `docker logs homeassistant` shows no `Timeout while fetching data` messages.
4. Remove old sensor entities from the HA UI or clear the `.storage/core.entity_registry` file if you understand the risk of direct edits.

## HomeKit Integration

### Enable HomeKit Bridge

The generated configuration includes HomeKit Bridge setup. To pair with your iPhone:

1. In Home Assistant, go to **Settings** → **Devices & Services**
2. Find the **HomeKit Bridge** integration card
3. Note the QR code or 8-digit pairing code
4. Open Apple **Home** app on your iPhone
5. Tap **+** → **Add Accessory**
6. Scan QR code or enter the code manually
7. Tap **Add Anyway** when warned about "Uncertified Accessory"
8. Assign lights to rooms

### Important Notes

- **Initial pairing requires local network** - HomeKit uses mDNS which doesn't work over VPN
- **After pairing**: Remote control works via Apple TV/HomePod hub
- **Room organization**: Lights must be manually assigned to rooms in Apple Home app

## Configuration Structure

### REST Commands

Controls lights by posting to the bridge API:

```yaml
rest_command:
  vantage_light_on:
    url: "http://<BRIDGE_TAILSCALE_IP>:8000/device/{{ load_id }}/set"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: '{"switch": "on", "brightness": {{ (brightness / 255 * 100) | round(0) }}}'
```

### REST Sensors

Polls light status every 30 seconds:

```yaml
sensor:
  - platform: rest
    name: "Vantage Load 254 Status"
    resource: "http://<BRIDGE_TAILSCALE_IP>:8000/load/254/status"
    value_template: "{{ value_json.resp | int }}"
    scan_interval: 30
```

### Template Lights

Creates virtual light entities with brightness control:

```yaml
light:
  - platform: template
    lights:
      master_bedroom_main:
        friendly_name: "Master Bedroom Main"
        value_template: "{{ (states('sensor.vantage_load_254_status') | int(0)) > 0 }}"
        level_template: "{{ ((states('sensor.vantage_load_254_status') | int(0)) * 2.55) | round(0) }}"
        turn_on:
          service: rest_command.vantage_light_on
          data:
            load_id: 254
            brightness: "{{ brightness | default(255) }}"
        turn_off:
          service: rest_command.vantage_light_off
          data:
            load_id: 254
```

## Customization

### Selecting Specific Rooms

Edit `generate_ha_config.py` to filter by room or floor:

```python
# Only 1st floor
if floor == '1st Floor':
    include_room = True

# Specific rooms only
if room_name in ['Master Bedroom', 'Kitchen', 'Living Room']:
    include_room = True
```

### Database Optimization

For Raspberry Pi installations, reduce database retention:

```yaml
recorder:
  purge_keep_days: 3
  commit_interval: 30
  db_max_retries: 5
```

### Polling Interval

Adjust sensor `scan_interval` to balance responsiveness vs. load:

```yaml
sensor:
  - platform: rest
    scan_interval: 30  # Reduce to 10 for faster updates
```

## Siri Voice Commands

After HomeKit pairing, use Siri to control lights:

```
"Hey Siri, turn on Master Bedroom Lights"
"Hey Siri, set Kitchen Lights to 50%"
"Hey Siri, dim Living Room Lights"
"Hey Siri, turn off all lights"
```

## Troubleshooting

### Lights Not Appearing

```bash
# Check bridge is running
curl http://<BRIDGE_TAILSCALE_IP>:8000/config

# Preferred LED endpoint (replaces legacy /api/status)
curl http://<BRIDGE_TAILSCALE_IP>:8000/api/leds

# Check HA logs
docker logs homeassistant --tail 100

# Restart HA
docker restart homeassistant
```

### REST Sensor Timeouts

If you see timeout errors during startup with many lights:
- This is normal - sensors will retry automatically
- Reduce number of lights in config
- Increase scan_interval to reduce load

### HomeKit Won't Pair

- Ensure iPhone is on same local network as Pi
- HomeKit requires mDNS (doesn't work over VPN)
- Check HomeKit Bridge is running in HA UI
- Try removing and re-adding accessory

### Lights in Wrong HomeKit Room

Home Assistant doesn't automatically create HomeKit rooms. You must:
1. Open Apple Home app
2. Tap and hold each light
3. Select **Settings** → **Room**
4. Assign to correct room

## Performance Considerations

### Raspberry Pi Resources

- **132 lights** = 132 REST sensors polling every 30s
- **Memory**: ~500MB for HA + sensors
- **CPU**: Minimal when idle, spikes during sensor updates
- **Disk**: 2-5GB for HA Docker image

### Recommendations

- Use 16GB+ SD card
- Enable log rotation (see docs/MAINTENANCE.md)
- Reduce database retention to 3 days
- Consider 32GB SD card for 100+ lights

## Advanced Features

### Automations

Create time-based or sensor-triggered automations:

```yaml
automation:
  - alias: "Morning Lights"
    trigger:
      platform: time
      at: "07:00:00"
    action:
      service: light.turn_on
      entity_id: light.kitchen_main
      data:
        brightness: 128
```

### Scenes

Group multiple lights into scenes:

```yaml
scene:
  - name: "Movie Time"
    entities:
      light.living_room_main:
        state: on
        brightness: 30
      light.family_room_main:
        state: off
```

## Security

### Local Network Only

- Never expose Home Assistant directly to the internet
- Use VPN (Tailscale/WireGuard) for remote access
- Keep HA and Pi updated

### API Protection

If exposing the bridge:
- Set `BRIDGE_API_SECRET` environment variable
- Use reverse proxy with authentication
- Enable HTTPS with valid certificate

## Maintenance

### Update Home Assistant

```bash
docker pull ghcr.io/home-assistant/home-assistant:stable
docker stop homeassistant
docker rm homeassistant
# Re-run docker run command from installation
```

### Backup Configuration

```bash
# Backup HA config
tar -czf ha-backup-$(date +%Y%m%d).tar.gz /home/pi/homeassistant/

# Backup bridge config
tar -czf bridge-backup-$(date +%Y%m%d).tar.gz /home/pi/qlink-bridge/
```

### View Logs

```bash
# HA logs
docker logs homeassistant -f

# Bridge logs
tail -f /home/pi/bridge.log
```

## Resources

- [Home Assistant Documentation](https://www.home-assistant.io/docs/)
- [HomeKit Integration](https://www.home-assistant.io/integrations/homekit/)
- [RESTful Integration](https://www.home-assistant.io/integrations/rest/)
- [Template Lights](https://www.home-assistant.io/integrations/light.template/)

## Support

For issues:
1. Check logs for errors
2. Verify bridge API is responding
3. Test with curl commands
4. File issue on GitHub with logs

---

**Note**: This integration was tested with Home Assistant 2025.x and Raspberry Pi 4. Your mileage may vary with other configurations.
