#!/usr/bin/env python3
"""
Parse Home Prado Ver.txt to extract ALL stations per room with button event types.
"""

import json
import re
import sys

# Map Vantage event types to button behaviors
EVENT_TYPE_MAP = {
    "PRESET_TOGGLE": "toggle",
    "DIM": "toggle",
    "TOGGLE": "toggle",
    "PRESET_ON": "on",
    "PRESET_OFF": "off",
    "SWITCH_POINTER": "momentary",
    "SWITCH_LINK": "momentary",
}


def parse_vantage_config(file_path):
    """Parse Vantage configuration file and extract rooms, ALL stations, and buttons with event types."""

    with open(file_path, "r", encoding="ascii", errors="ignore") as f:
        lines = f.readlines()

    rooms_data = {}  # room_name -> list of {station, buttons}
    current_room = None
    current_station = None
    current_station_buttons = []
    current_button = None  # Track current button to capture event type

    for i, line in enumerate(lines):
        line = line.rstrip()

        # Room definition: "  Room: <name>"
        if line.startswith("  Room: "):
            # Save previous station if any
            if current_room and current_station and current_station_buttons:
                if current_room not in rooms_data:
                    rooms_data[current_room] = []
                rooms_data[current_room].append(
                    {
                        "station": current_station,
                        "buttons": current_station_buttons.copy(),
                    }
                )

            current_room = line.split(":", 1)[1].strip()
            current_station = None
            current_station_buttons = []
            current_button = None

        # Station definition: "    Station: V<num>,..."
        elif line.startswith("    Station: "):
            # Save previous station if any
            if current_room and current_station and current_station_buttons:
                if current_room not in rooms_data:
                    rooms_data[current_room] = []
                rooms_data[current_room].append(
                    {
                        "station": current_station,
                        "buttons": current_station_buttons.copy(),
                    }
                )

            station_data = line.split(":", 1)[1].strip()
            station_num_match = re.match(r"V(\d+)", station_data)
            if station_num_match:
                current_station = int(station_num_match.group(1))
                current_station_buttons = []
                current_button = None

        # Button definition: "      Btn: <name>,<num>,<line1>,<line2>,<visible>"
        elif line.startswith("      Btn: ") and current_station:
            btn_data = line.split(":", 1)[1].strip()
            parts = btn_data.split(",")
            if len(parts) >= 2:
                btn_name = parts[0].strip()
                try:
                    btn_num = int(parts[1].strip())
                    # Create button with default event type
                    current_button = {
                        "number": btn_num,
                        "name": btn_name,
                        "event_type": "UNKNOWN",
                        "behavior": "toggle",  # default
                    }
                    current_station_buttons.append(current_button)
                except ValueError:
                    current_button = None

        # Event definition: "        Event: 1, 0 <EVENT_TYPE> ..."
        elif line.startswith("        Event: ") and current_button:
            # Extract event type from line like "Event: 1, 0 PRESET_TOGGLE 1 3.0 0 0"
            event_parts = line.split()
            if len(event_parts) >= 4:
                event_type = event_parts[3]  # Third field after "Event: 1, 0"
                current_button["event_type"] = event_type
                current_button["behavior"] = EVENT_TYPE_MAP.get(event_type, "toggle")

    # Save last station
    if current_room and current_station and current_station_buttons:
        if current_room not in rooms_data:
            rooms_data[current_room] = []
        rooms_data[current_room].append(
            {"station": current_station, "buttons": current_station_buttons.copy()}
        )

    return rooms_data


def main():
    input_file = "C:/QLINK/Info/Home Prado Ver.txt"

    print(f"Parsing {input_file}...", file=sys.stderr)
    rooms_data = parse_vantage_config(input_file)

    print(f"\nFound {len(rooms_data)} rooms with stations/buttons:", file=sys.stderr)

    total_stations = 0
    total_buttons = 0
    multi_station_rooms = 0

    for room_name, stations_list in sorted(rooms_data.items()):
        if len(stations_list) > 1:
            multi_station_rooms += 1
            station_nums = [s["station"] for s in stations_list]
            print(
                f"\n{room_name}: {len(stations_list)} stations V{station_nums}",
                file=sys.stderr,
            )
        else:
            print(f"\n{room_name}:", file=sys.stderr)

        for station_data in stations_list:
            station_num = station_data["station"]
            buttons = station_data["buttons"]
            total_stations += 1
            total_buttons += len(buttons)
            print(f"  Station V{station_num}: {len(buttons)} buttons", file=sys.stderr)
            for btn in buttons:
                print(
                    f"    Button {btn['number']}: {btn['name']} ({btn['behavior']}, {btn['event_type']})",
                    file=sys.stderr,
                )

    print("\n=== Summary ===", file=sys.stderr)
    print(f"Total rooms: {len(rooms_data)}", file=sys.stderr)
    print(f"Rooms with multiple stations: {multi_station_rooms}", file=sys.stderr)
    print(f"Total stations: {total_stations}", file=sys.stderr)
    print(f"Total buttons: {total_buttons}", file=sys.stderr)

    # Output JSON
    print(json.dumps(rooms_data, indent=2))


if __name__ == "__main__":
    main()
