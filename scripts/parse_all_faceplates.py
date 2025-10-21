#!/usr/bin/env python3
"""
Parse Home Prado Ver.txt to extract ALL button/faceplate data for all stations.
"""

import json
import re
import sys

def parse_vantage_config(file_path):
    """Parse Vantage configuration file and extract rooms, stations, and buttons."""

    with open(file_path, 'r', encoding='ascii', errors='ignore') as f:
        lines = f.readlines()

    rooms_data = {}  # room_name -> list of {station, buttons}
    current_room = None
    current_station = None
    current_station_buttons = []

    for line in lines:
        line = line.rstrip()

        # Room definition: "  Room: <name>"
        if line.startswith('  Room: '):
            # Save previous station if any
            if current_room and current_station and current_station_buttons:
                if current_room not in rooms_data:
                    rooms_data[current_room] = []
                rooms_data[current_room].append({
                    'station': current_station,
                    'buttons': current_station_buttons.copy()
                })

            current_room = line.split(':', 1)[1].strip()
            current_station = None
            current_station_buttons = []

        # Station definition: "    Station: V<num>,..."
        elif line.startswith('    Station: '):
            # Save previous station if any
            if current_room and current_station and current_station_buttons:
                if current_room not in rooms_data:
                    rooms_data[current_room] = []
                rooms_data[current_room].append({
                    'station': current_station,
                    'buttons': current_station_buttons.copy()
                })

            station_data = line.split(':', 1)[1].strip()
            station_num_match = re.match(r'V(\d+)', station_data)
            if station_num_match:
                current_station = int(station_num_match.group(1))
                current_station_buttons = []

        # Button definition: "      Btn: <name>,<num>,<line1>,<line2>,<visible>"
        elif line.startswith('      Btn: ') and current_station:
            btn_data = line.split(':', 1)[1].strip()
            parts = btn_data.split(',')
            if len(parts) >= 2:
                btn_name = parts[0].strip()
                try:
                    btn_num = int(parts[1].strip())
                    current_station_buttons.append({
                        'number': btn_num,
                        'name': btn_name
                    })
                except ValueError:
                    pass  # Skip if button number isn't an integer

    # Save last station
    if current_room and current_station and current_station_buttons:
        if current_room not in rooms_data:
            rooms_data[current_room] = []
        rooms_data[current_room].append({
            'station': current_station,
            'buttons': current_station_buttons.copy()
        })

    return rooms_data

def main():
    input_file = 'C:/QLINK/Info/Home Prado Ver.txt'

    print(f"Parsing {input_file}...", file=sys.stderr)
    rooms_data = parse_vantage_config(input_file)

    print(f"\nFound {len(rooms_data)} rooms with stations/buttons:", file=sys.stderr)

    total_stations = 0
    total_buttons = 0

    for room_name, stations_list in sorted(rooms_data.items()):
        print(f"\n{room_name}:", file=sys.stderr)
        for station_data in stations_list:
            station_num = station_data['station']
            buttons = station_data['buttons']
            total_stations += 1
            total_buttons += len(buttons)
            print(f"  Station V{station_num}: {len(buttons)} buttons", file=sys.stderr)
            for btn in buttons:
                print(f"    Button {btn['number']}: {btn['name']}", file=sys.stderr)

    print(f"\n=== Summary ===", file=sys.stderr)
    print(f"Total rooms: {len(rooms_data)}", file=sys.stderr)
    print(f"Total stations: {total_stations}", file=sys.stderr)
    print(f"Total buttons: {total_buttons}", file=sys.stderr)

    # Output JSON
    print(json.dumps(rooms_data, indent=2))

if __name__ == '__main__':
    main()
