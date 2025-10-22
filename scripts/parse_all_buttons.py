#!/usr/bin/env python3
"""Parse button mappings and create complete loads.json with all faceplate buttons"""

import json
import re
import codecs

# Station to room name mapping (based on your system)
STATION_TO_ROOM = {
    1: "Unknown V01",
    2: "Library",
    3: "Unknown V03",
    5: "Unknown V05",
    6: "Unknown V06",
    7: "Unknown V07",
    9: "Master Sitting Room",  # From loads-with-real-buttons
    10: "Unknown V10",
    11: "Unknown V11",
    12: "Master Bath",
    13: "Master Bedroom",
    14: "Unknown V14",
    16: "Unknown V16",
    17: "Unknown V17",
    19: "Foyer",
    20: "Entry",
    22: "Unknown V22",
    23: "Game Room",
    24: "Unknown V24",
    40: "Unknown V40",
    73: "Unknown V73",
}


def parse_button_mappings():
    """Parse button mappings from Info/Button_Mappings_Summary.txt"""
    stations = {}

    with codecs.open(
        "Info/Button_Mappings_Summary.txt", "r", encoding="utf-16-le"
    ) as f:
        lines = f.readlines()

    for line in lines:
        line = line.strip()
        if not line or line.startswith("Global"):
            continue

        # Match: "V## - Button #: Name"
        match = re.match(r"V(\d+)\s*.*?Button\s*(\d+):\s*(.+)", line)
        if match:
            station = int(match.group(1))
            button_num = int(match.group(2))
            button_name = match.group(3).strip()

            if station not in stations:
                stations[station] = {}
            stations[station][button_num] = button_name

    return stations


def create_button_array(button_dict):
    """Convert button dict to array format for JSON"""
    buttons = []
    for num in sorted(button_dict.keys()):
        buttons.append(
            {
                "number": num,
                "name": button_dict[num],
                "loads": [],  # Will be populated manually if needed
                "event": "PRESET_TOGGLE",
            }
        )
    return buttons


def main():
    # Load full room config
    with open("config/loads.json", "r", encoding="utf-8") as f:
        full_config = json.load(f)

    # Parse button mappings
    station_buttons = parse_button_mappings()

    print(f"Parsed {len(station_buttons)} stations with button data\n")

    # Add station and button data to rooms
    added_count = 0
    for room in full_config["rooms"]:
        # Try to find matching station by room name
        room_name = room["name"]

        # Direct match by station number mapping
        for station, mapped_room in STATION_TO_ROOM.items():
            if (
                room_name.lower() in mapped_room.lower()
                or mapped_room.lower() in room_name.lower()
            ):
                if station in station_buttons:
                    room["station"] = station
                    room["buttons"] = create_button_array(station_buttons[station])
                    added_count += 1
                    print(
                        f"✓ Added {len(station_buttons[station])} buttons to {room_name} (V{station})"
                    )
                    break

    # Save complete config
    output_file = "config/loads-all-buttons.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(full_config, f, indent=4, ensure_ascii=False)

    print(f"\n✅ Complete config saved to {output_file}")
    print(f"   Total rooms: {len(full_config['rooms'])}")
    print(f"   Rooms with buttons: {added_count}")

    # List all stations that weren't matched
    matched_stations = set()
    for room in full_config["rooms"]:
        if "station" in room:
            matched_stations.add(room["station"])

    unmatched = set(station_buttons.keys()) - matched_stations
    if unmatched:
        print("\n⚠️  Unmatched stations (need room name mapping):")
        for station in sorted(unmatched):
            button_count = len(station_buttons[station])
            first_button = (
                list(station_buttons[station].values())[0]
                if station_buttons[station]
                else ""
            )
            print(
                f"   V{station:02d}: {button_count} buttons (first: '{first_button}')"
            )


if __name__ == "__main__":
    main()
