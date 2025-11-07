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

for l in loads:
    print(f'  - platform: rest')
    print(f'    name: "Vantage Load {l["id"]} Status"')
    print(f'    unique_id: vantage_load_{l["id"]}_status')
    print(f'    resource: "http://localhost:8000/load/{l["id"]}/status"')
    print(f'    value_template: "{{{{ value_json.resp | int }}}}"')
    print(f'    scan_interval: 30\n')

print('light:')
print('  - platform: template')
print('    lights:')

cf, cr = None, None
for l in loads:
    if l['floor'] != cf:
        print(f'      # {l["floor"]}')
        cf, cr = l['floor'], None
    if l['room'] != cr:
        print(f'      # {l["room"]}')
        cr = l['room']
    eid = sanitize(f'{l["room"]}_{l["name"]}')
    fn = escape_yaml_string(f'{l["room"]} - {l["name"]}')
    lid = l['id']
    print(f'      {eid}:')
    print(f'        friendly_name: "{fn}"')
    print(f'        unique_id: vantage_load_{lid}')
    print(f'        value_template: "{{{{ (states(\'sensor.vantage_load_{lid}_status\') | int(0)) > 0 }}}}"')
    print(f'        level_template: "{{{{ ((states(\'sensor.vantage_load_{lid}_status\') | int(0)) * 2.55) | round(0) }}}}"')
    print(f'        turn_on:')
    print(f'          service: rest_command.vantage_light_on')
    print(f'          data:')
    print(f'            load_id: {lid}')
    print(f'            brightness: "{{{{ brightness | default(255) }}}}"')
    print(f'        turn_off:')
    print(f'          service: rest_command.vantage_light_off')
    print(f'          data:')
    print(f'            load_id: {lid}\n')

print('homekit:')
print('  filter:')
print('    include_domains:')
print('      - light')
print('  entity_config:')

cf, cr = None, None
for l in loads:
    if l['floor'] != cf:
        print(f'    # {l["floor"]}')
        cf, cr = l['floor'], None
    if l['room'] != cr:
        print(f'    # {l["room"]}')
        cr = l['room']
    eid = sanitize(f'{l["room"]}_{l["name"]}')
    fn = escape_yaml_string(f'{l["room"]} - {l["name"]}')
    print(f'    light.{eid}:')
    print(f'      name: "{fn}"')

print('\nrecorder:')
print('  purge_keep_days: 3')
print('  commit_interval: 30')
print('  db_max_retries: 5')
