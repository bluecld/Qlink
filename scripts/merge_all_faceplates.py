#!/usr/bin/env python3
"""
Merge complete faceplate/button data from Home Prado Ver.txt with loads config.
"""

import json
import sys

# Import the parser
sys.path.insert(0, 'C:/QLINK/scripts')
from parse_all_faceplates import parse_vantage_config

def main():
    # Load existing loads config
    with open('C:/QLINK/config/loads-complete-all.json', 'r') as f:
        config = json.load(f)

    # Parse all button data from Home Prado Ver.txt
    print("Parsing Home Prado Ver.txt...", file=sys.stderr)
    rooms_button_data = parse_vantage_config('C:/QLINK/Info/Home Prado Ver.txt')

    print(f"Found button data for {len(rooms_button_data)} rooms", file=sys.stderr)

    # Create mapping of room names (normalized) to button data
    button_map = {}
    for room_name, stations_list in rooms_button_data.items():
        # Normalize room name (remove extra spaces, lowercase for matching)
        norm_name = room_name.strip().lower()
        button_map[norm_name] = stations_list

    # Update config with button data
    rooms_updated = 0
    stations_added = 0
    buttons_added = 0

    for room in config['rooms']:
        room_name = room['name']
        norm_name = room_name.strip().lower()

        if norm_name in button_map:
            stations_list = button_map[norm_name]

            # If room has multiple stations, use the first one as primary
            if stations_list:
                first_station_data = stations_list[0]
                room['station'] = first_station_data['station']
                room['buttons'] = [
                    {
                        'number': btn['number'],
                        'name': btn['name'],
                        'loads': [],
                        'event': 'PRESET_TOGGLE'
                    }
                    for btn in first_station_data['buttons']
                ]
                rooms_updated += 1
                stations_added += 1
                buttons_added += len(first_station_data['buttons'])

                # Log if room has multiple stations
                if len(stations_list) > 1:
                    station_nums = [s['station'] for s in stations_list]
                    print(f"  {room_name}: Multiple stations found V{station_nums}, using V{first_station_data['station']}", file=sys.stderr)

    print(f"\n=== Merge Summary ===", file=sys.stderr)
    print(f"Rooms updated: {rooms_updated}", file=sys.stderr)
    print(f"Stations added: {stations_added}", file=sys.stderr)
    print(f"Buttons added: {buttons_added}", file=sys.stderr)

    # Save updated config
    output_file = 'C:/QLINK/config/loads-all-faceplates.json'
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved to: {output_file}", file=sys.stderr)

    # Output summary for user
    print(json.dumps({
        'rooms': len(config['rooms']),
        'rooms_with_buttons': rooms_updated,
        'total_buttons': buttons_added
    }, indent=2))

if __name__ == '__main__':
    main()
