#!/usr/bin/env python3
"""
Merge complete faceplate/button data with loads config.
NEW CONFIG STRUCTURE: stations array per room (not single station property).
"""

import json
import sys

# Import the parser
sys.path.insert(0, 'C:/QLINK/scripts')
from parse_complete_faceplates import parse_vantage_config

def main():
    # Load existing loads config
    with open('C:/QLINK/config/loads-complete-all.json', 'r') as f:
        config = json.load(f)

    # Parse all button data from Home Prado Ver.txt
    print("Parsing Home Prado Ver.txt for ALL stations and event types...", file=sys.stderr)
    rooms_button_data = parse_vantage_config('C:/QLINK/Info/Home Prado Ver.txt')

    print(f"Found button data for {len(rooms_button_data)} rooms", file=sys.stderr)

    # Create mapping of room names (normalized) to button data
    button_map = {}
    for room_name, stations_list in rooms_button_data.items():
        # Normalize room name (remove extra spaces, lowercase for matching)
        norm_name = room_name.strip().lower()
        button_map[norm_name] = stations_list

    # Update config with button data (NEW STRUCTURE)
    rooms_updated = 0
    total_stations_added = 0
    total_buttons_added = 0
    multi_station_rooms = 0

    for room in config['rooms']:
        room_name = room['name']
        norm_name = room_name.strip().lower()

        if norm_name in button_map:
            stations_list = button_map[norm_name]

            # NEW: Add ALL stations as an array
            room['stations'] = []

            for station_data in stations_list:
                station_obj = {
                    'station': station_data['station'],
                    'buttons': [
                        {
                            'number': btn['number'],
                            'name': btn['name'],
                            'event_type': btn['event_type'],
                            'behavior': btn['behavior'],
                            'loads': [],
                            'event': 'PRESET_TOGGLE'  # Keep for backwards compatibility
                        }
                        for btn in station_data['buttons']
                    ]
                }
                room['stations'].append(station_obj)
                total_stations_added += 1
                total_buttons_added += len(station_data['buttons'])

            # Also keep the OLD 'station' and 'buttons' fields for backwards compatibility
            # Use the FIRST station as the primary
            if stations_list:
                first_station = stations_list[0]
                room['station'] = first_station['station']
                room['buttons'] = [
                    {
                        'number': btn['number'],
                        'name': btn['name'],
                        'event_type': btn['event_type'],
                        'behavior': btn['behavior'],
                        'loads': [],
                        'event': 'PRESET_TOGGLE'
                    }
                    for btn in first_station['buttons']
                ]

            rooms_updated += 1

            if len(stations_list) > 1:
                multi_station_rooms += 1
                station_nums = [s['station'] for s in stations_list]
                print(f"  {room_name}: {len(stations_list)} stations V{station_nums}", file=sys.stderr)

        else:
            # No button data for this room
            room['stations'] = []
            if 'station' not in room:
                room['station'] = None
            if 'buttons' not in room:
                room['buttons'] = []

    print(f"\n=== Merge Summary ===", file=sys.stderr)
    print(f"Rooms updated: {rooms_updated}", file=sys.stderr)
    print(f"Rooms with multiple stations: {multi_station_rooms}", file=sys.stderr)
    print(f"Total stations added: {total_stations_added}", file=sys.stderr)
    print(f"Total buttons added: {total_buttons_added}", file=sys.stderr)

    # Save updated config
    output_file = 'C:/QLINK/config/loads-v2-multi-station.json'
    with open(output_file, 'w') as f:
        json.dump(config, f, indent=2)

    print(f"\nSaved to: {output_file}", file=sys.stderr)

    # Output summary for user
    print(json.dumps({
        'rooms': len(config['rooms']),
        'rooms_with_buttons': rooms_updated,
        'rooms_with_multiple_stations': multi_station_rooms,
        'total_stations': total_stations_added,
        'total_buttons': total_buttons_added
    }, indent=2))

if __name__ == '__main__':
    main()
