#!/usr/bin/env python3
"""
Generate Home Assistant configuration for Vantage lights
"""

import json
import sys
import requests

def sanitize_name(name):
    """Convert room/light name to valid HA entity_id"""
    # Remove special characters and convert to lowercase with underscores
    sanitized = name.lower()
    sanitized = sanitized.replace(' - ', '_')
    sanitized = sanitized.replace('-', '_')
    sanitized = sanitized.replace(' ', '_')
    sanitized = sanitized.replace('/', '_')
    sanitized = sanitized.replace('&', 'and')
    # Remove any remaining special chars
    sanitized = ''.join(c for c in sanitized if c.isalnum() or c == '_')
    # Remove consecutive underscores
    while '__' in sanitized:
        sanitized = sanitized.replace('__', '_')
    return sanitized.strip('_')

def generate_sensor(load_id):
    """Generate REST sensor YAML for a load"""
    return f"""  - platform: rest
    name: "Vantage Load {load_id} Status"
    unique_id: vantage_load_{load_id}_status
    resource: "http://localhost:8000/load/{load_id}/status"
    value_template: "{{{{ value_json.resp | int }}}}"
    scan_interval: 30
"""

def generate_light(load_id, room_name, light_name):
    """Generate template light YAML for a load"""
    entity_id = sanitize_name(f"{room_name}_{light_name}")
    friendly_name = f"{room_name} - {light_name}"

    # Truncate if too long (HA has limits)
    if len(entity_id) > 50:
        entity_id = entity_id[:50]

    return f"""      {entity_id}:
        friendly_name: "{friendly_name}"
        unique_id: vantage_load_{load_id}
        value_template: "{{{{ (states('sensor.vantage_load_{load_id}_status') | int(0)) > 0 }}}}"
        level_template: "{{{{ ((states('sensor.vantage_load_{load_id}_status') | int(0)) * 2.55) | round(0) }}}}"
        turn_on:
          service: rest_command.vantage_light_on
          data:
            load_id: {load_id}
            brightness: "{{{{ brightness | default(255) }}}}"
        turn_off:
          service: rest_command.vantage_light_off
          data:
            load_id: {load_id}
"""

def generate_homekit_entity(load_id, room_name, light_name):
    """Generate HomeKit entity config"""
    entity_id = sanitize_name(f"{room_name}_{light_name}")
    if len(entity_id) > 50:
        entity_id = entity_id[:50]

    friendly_name = f"{room_name} - {light_name}"

    return f"""    light.{entity_id}:
      name: "{friendly_name}"
"""

def main():
    # Fetch config from bridge
    try:
        response = requests.get('http://192.168.1.213:8000/config')
        config = response.json()
    except Exception as e:
        print(f"Error fetching config from bridge: {e}")
        sys.exit(1)

    # Filter options
    print("Generate Home Assistant Configuration for Vantage Lights")
    print("=" * 60)
    print("\nOptions:")
    print("1. All lights (~150 lights)")
    print("2. All 1st Floor lights")
    print("3. All 2nd Floor lights")
    print("4. Exterior lights only")
    print("5. Select specific rooms")
    print("6. Master Bedroom + Kitchen + Living Room only (current 6 lights)")

    choice = input("\nEnter choice (1-6): ").strip()

    # Collect loads to include
    selected_loads = []

    for room in config.get('rooms', []):
        floor = room.get('floor', '')
        room_name = room.get('name', '')
        loads = room.get('loads', [])

        # Filter to dimmers/switches only
        lights = [l for l in loads if l.get('type') in ['dimmer', 'switch', 'relay']]

        include_room = False

        if choice == '1':
            # All lights
            include_room = True
        elif choice == '2' and floor == '1st Floor':
            include_room = True
        elif choice == '3' and floor == '2nd Floor':
            include_room = True
        elif choice == '4' and floor == 'Exterior':
            include_room = True
        elif choice == '6':
            # Only current 6 lights
            current_ids = [254, 241, 240, 141, 144, 122]
            lights = [l for l in lights if l.get('id') in current_ids]
            include_room = len(lights) > 0
        elif choice == '5':
            # Interactive room selection
            print(f"\nInclude {floor} - {room_name}? ({len(lights)} lights)")
            answer = input("  (y/n): ").strip().lower()
            include_room = answer == 'y'

        if include_room:
            for light in lights:
                selected_loads.append({
                    'id': light.get('id'),
                    'room': room_name,
                    'name': light.get('name'),
                    'type': light.get('type')
                })

    print(f"\n{len(selected_loads)} lights selected")

    # Generate YAML
    print("\n" + "=" * 60)
    print("YAML Configuration:")
    print("=" * 60)

    # REST commands (only once)
    print("""
# Vantage Q-Link Bridge Integration via RESTful Platform

# REST Commands to control Vantage lights via bridge
rest_command:
  vantage_light_on:
    url: "http://localhost:8000/device/{{ load_id }}/set"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: '{"switch": "on", "brightness": {{ (brightness / 255 * 100) | round(0) }}}'

  vantage_light_off:
    url: "http://localhost:8000/device/{{ load_id }}/set"
    method: POST
    headers:
      Content-Type: "application/json"
    payload: '{"switch": "off"}'

# Sensors to poll light status
sensor:""")

    # Generate sensors
    for load in selected_loads:
        print(generate_sensor(load['id']))

    # Generate template lights
    print("""
# Template lights using the bridge API
light:
  - platform: template
    lights:""")

    for load in selected_loads:
        print(generate_light(load['id'], load['room'], load['name']))

    # Generate HomeKit config
    print("""
# HomeKit Bridge Configuration
homekit:
  filter:
    include_domains:
      - light
  entity_config:""")

    for load in selected_loads:
        print(generate_homekit_entity(load['id'], load['room'], load['name']))

    # Database configuration
    print("""
# Database configuration - keep history lean for SD card
recorder:
  purge_keep_days: 3
  commit_interval: 30
  db_max_retries: 5
""")

    print("\n" + "=" * 60)
    print(f"Configuration generated for {len(selected_loads)} lights")
    print("=" * 60)

if __name__ == '__main__':
    main()
