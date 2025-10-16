"""
Extract all button configurations from Home Prado Ver.txt
Parses stations and buttons to create complete loads.json
"""

import json
import re
from pathlib import Path


def parse_station_line(line):
    """Parse station definition line"""
    # Station: V23,255,1,23,0182024,1,1948280182,0,1,0,1
    match = re.match(r"\s*Station:\s+([^,]+),\d+,(\d+),(\d+)", line)
    if match:
        name = match.group(1).strip()
        master = int(match.group(2))
        station_num = int(match.group(3))
        return {"name": name, "master": master, "station": station_num}
    return None


def parse_button_line(line):
    """Parse button definition line"""
    # Btn: Game Room On,5,Game,Room On,1
    match = re.match(r"\s*Btn:\s+([^,]+),(\d+)", line)
    if match:
        name = match.group(1).strip()
        button_num = int(match.group(2))
        return {"name": name, "button": button_num}
    return None


def parse_event_line(line):
    """Parse event line to extract event type"""
    # Event: 1, 0 DIM 34 2.0 3.0 1 0
    # Event: 1, 0 PRESET_ON 1 2.0 0 0
    # Event: 1, 0 TOGGLE 34 0.0
    match = re.match(
        r"\s*Event:.*?\s+(DIM|PRESET_ON|PRESET_OFF|TOGGLE|ON|OFF)\s+", line
    )
    if match:
        return match.group(1)
    return None


def parse_lda_line(line):
    """Parse load assignment line"""
    # LdA: 1111,1114,1115,2141
    # LdA: 1111:60%,1114,1115:60%,2141:60%
    match = re.match(r"\s*LdA:\s+(.+)", line)
    if match:
        loads_str = match.group(1).strip()
        loads = []
        for item in loads_str.split(","):
            item = item.strip()
            # Extract just the load number, ignore percentage
            load_match = re.match(r"(\d+)", item)
            if load_match:
                loads.append(int(load_match.group(1)))
        return loads
    return []


def extract_all_buttons(input_file):
    """Extract all buttons from configuration file"""
    print(f"Reading {input_file}...")

    with open(input_file, "r", encoding="utf-8") as f:
        lines = f.readlines()

    stations = []
    current_station = None
    current_button = None
    current_event = None

    for i, line in enumerate(lines):
        # Check for station line
        station_info = parse_station_line(line)
        if station_info:
            if current_station:
                stations.append(current_station)
            current_station = station_info
            current_station["buttons"] = []
            current_button = None
            current_event = None
            continue

        # Only process button/event/load lines if we're inside a station
        if not current_station:
            continue

        # Check for button line
        button_info = parse_button_line(line)
        if button_info:
            current_button = button_info
            current_button["station"] = current_station["station"]
            current_button["station_name"] = current_station["name"]
            current_button["event_type"] = None
            current_button["loads"] = []
            current_station["buttons"].append(current_button)
            continue

        # Check for event line
        if current_button:
            event_type = parse_event_line(line)
            if event_type:
                current_button["event_type"] = event_type
                continue

            # Check for load assignment
            loads = parse_lda_line(line)
            if loads:
                current_button["loads"] = loads

    # Don't forget the last station
    if current_station:
        stations.append(current_station)

    return stations


def create_loads_json(stations, output_file):
    """Create loads.json from extracted stations"""

    # Build loads.json structure
    loads_json = {}

    for station in stations:
        station_key = f"station_{station['station']}"

        if station["buttons"]:
            loads_json[station_key] = {
                "name": station["name"],
                "station": station["station"],
                "master": station["master"],
                "buttons": {},
            }

            for button in station["buttons"]:
                button_key = f"button_{button['button']}"
                loads_json[station_key]["buttons"][button_key] = {
                    "name": button["name"],
                    "button": button["button"],
                    "event_type": button["event_type"],
                    "loads": button["loads"],
                }

    # Write output
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump(loads_json, f, indent=2)

    print(f"\nCreated {output_file}")
    return loads_json


def print_summary(stations, loads_json):
    """Print extraction summary"""
    total_buttons = sum(len(s["buttons"]) for s in stations)
    stations_with_buttons = sum(1 for s in stations if s["buttons"])

    print("\n" + "=" * 60)
    print("EXTRACTION SUMMARY")
    print("=" * 60)
    print(f"Total stations found: {len(stations)}")
    print(f"Stations with buttons: {stations_with_buttons}")
    print(f"Total buttons extracted: {total_buttons}")
    print(f"\nStations in loads.json: {len(loads_json)}")

    # Show some examples
    print("\n" + "-" * 60)
    print("SAMPLE STATIONS:")
    print("-" * 60)

    for i, station in enumerate(stations[:5]):
        if station["buttons"]:
            print(
                f"\n{station['name']} (Station {station['station']}, Master {station['master']})"
            )
            print(f"  {len(station['buttons'])} buttons:")
            for button in station["buttons"][:3]:
                loads_str = ", ".join(str(l) for l in button["loads"])
                print(f"    Button {button['button']}: {button['name']}")
                print(f"      Event: {button['event_type']}, Loads: [{loads_str}]")
            if len(station["buttons"]) > 3:
                print(f"    ... and {len(station['buttons']) - 3} more buttons")


def main():
    # Paths
    project_root = Path(__file__).parent.parent
    input_file = project_root / "Info" / "Home Prado Ver.txt"
    output_file = project_root / "config" / "loads.json"

    print("Vantage Q-Link Button Extractor")
    print("=" * 60)

    # Extract buttons
    stations = extract_all_buttons(input_file)

    # Create loads.json
    loads_json = create_loads_json(stations, output_file)

    # Print summary
    print_summary(stations, loads_json)

    print("\n" + "=" * 60)
    print("DONE! Check config/loads.json for complete configuration")
    print("=" * 60)


if __name__ == "__main__":
    main()
