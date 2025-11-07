#!/usr/bin/env python3
import json
import urllib.request

with urllib.request.urlopen('http://localhost:8000/config') as response:
    config = json.load(response)

def sanitize(name):
    s = name.lower().replace(' - ', '_').replace('-', '_').replace(' ', '_').replace('/', '_').replace('&', 'and').replace('"', '')
    s = ''.join(c for c in s if c.isalnum() or c == '_')
    while '__' in s:
        s = s.replace('__', '_')
    return s.strip('_')[:48]

def escape_yaml_string(s):
    """Escape string for YAML - replace quotes with inches symbol"""
    return s.replace('"', "'")

loads = []
for room in config.get('rooms', []):
    for light in room.get('loads', []):
        if light.get('type') in ['dimmer', 'switch', 'relay']:
            loads.append({'id': light['id'], 'floor': room.get('floor', ''), 'room': room.get('name', ''), 'name': light.get('name', '')})

loads.sort(key=lambda x: (x['floor'], x['room'], x['name']))

print('# Vantage Q-Link - All Lights')
print(f'# {len(loads)} lights\n')
print('rest_command:')
print('  vantage_light_on:')
print('    url: "http://localhost:8000/device/{{ load_id }}/set"')
print('    method: POST')
print('    headers:')
print('      Content-Type: "application/json"')
print('    payload: \'{"switch": "on", "brightness": {{ (brightness / 255 * 100) | round(0) }}}\'')
print('')
print('  vantage_light_off:')
print('    url: "http://localhost:8000/device/{{ load_id }}/set"')
print('    method: POST')
print('    headers:')
print('      Content-Type: "application/json"')
print('    payload: \'{"switch": "off"}\'')
print('\nsensor:')

for load in loads:
    print('  - platform: rest')
    print(f'    name: "Vantage Load {load["id"]} Status"')
    print(f'    unique_id: vantage_load_{load["id"]}_status')
    print(f'    resource: "http://localhost:8000/load/{load["id"]}/status"')
    print('    value_template: "{{ value_json.resp | int }}"')
    print('    scan_interval: 30\n')

print('light:')
print('  - platform: template')
print('    lights:')

cf, cr = None, None
for load in loads:
    if load['floor'] != cf:
        print(f'      # {load["floor"]}')
        cf, cr = load['floor'], None
    if load['room'] != cr:
        print(f'      # {load["room"]}')
        cr = load['room']
    eid = sanitize(f'{load["room"]}_{load["name"]}')
    fn = escape_yaml_string(f'{load["room"]} - {load["name"]}')
    lid = load['id']
    print(f'      {eid}:')
    print(f'        friendly_name: "{fn}"')
    print(f'        unique_id: vantage_load_{lid}')
    print(f'        value_template: "{{{{ (states(\'sensor.vantage_load_{lid}_status\') | int(0)) > 0 }}}}"')
    print(f'        level_template: "{{{{ ((states(\'sensor.vantage_load_{lid}_status\') | int(0)) * 2.55) | round(0) }}}}"')
    print('        turn_on:')
    print('          service: rest_command.vantage_light_on')
    print('          data:')
    print(f'            load_id: {lid}')
    print('            brightness: "{{ brightness | default(255) }}"')
    print('        turn_off:')
    print('          service: rest_command.vantage_light_off')
    print('          data:')
    print(f'            load_id: {lid}\n')

print('homekit:')
print('  filter:')
print('    include_domains:')
print('      - light')
print('  entity_config:')

cf, cr = None, None
for load in loads:
    if load['floor'] != cf:
        print(f'    # {load["floor"]}')
        cf, cr = load['floor'], None
    if load['room'] != cr:
        print(f'    # {load["room"]}')
        cr = load['room']
    eid = sanitize(f'{load["room"]}_{load["name"]}')
    fn = escape_yaml_string(f'{load["room"]} - {load["name"]}')
    print(f'    light.{eid}:')
    print(f'      name: "{fn}"')

print('\nrecorder:')
print('  purge_keep_days: 3')
print('  commit_interval: 30')
print('  db_max_retries: 5')
