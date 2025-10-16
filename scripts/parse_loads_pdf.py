#!/usr/bin/env python3
"""Parse LoadL.pdf with proper structure recognition"""

import json
import re
from PyPDF2 import PdfReader
from collections import defaultdict


def parse_loads_pdf(pdf_path):
    """Parse the Vantage load schedule PDF."""

    reader = PdfReader(pdf_path)
    text = "".join(page.extract_text() for page in reader.pages)
    lines = text.split("\n")

    # Group loads by room
    room_loads = defaultdict(list)

    i = 0
    while i < len(lines):
        line = lines[i].strip()

        # Look for load entries: starts with number, has room name, floor, power, type
        # Format: "NUMBER NAME Room Floor POWER Type Address"
        match = re.match(
            r"^(\d+)\s+(.+?)\s+(.*?)\s+(1st Floor|2nd Floor|Exterior|Equipment)\s+(\d+)\s+(\w+)",
            line,
        )

        if match:
            load_id = int(match.group(1))
            load_name = match.group(2).strip()
            room_floor = match.group(3).strip()
            floor = match.group(4)
            power = match.group(5)
            load_type_raw = match.group(6)

            # Clean up room name - remove extra spaces and line breaks
            room = room_floor.replace("\n", " ").strip()

            # If room is empty, it might be on the previous line
            if not room and i > 0:
                prev_line = lines[i - 1].strip()
                # Check if previous line looks like a room name
                if prev_line and not prev_line[0].isdigit():
                    room = prev_line

            # Determine load type (dimmer vs switch)
            load_type = (
                "switch"
                if "switch" in load_name.lower() or "relay" in load_name.lower()
                else "dimmer"
            )

            # Skip motor/fan loads for now (can add back if needed)
            if load_type_raw.lower() in ["motor"]:
                load_type = "motor"

            room_loads[room].append(
                {
                    "id": load_id,
                    "name": load_name,
                    "type": load_type,
                    "floor": floor,
                    "power": int(power),
                }
            )

        i += 1

    # Convert to rooms structure, organized by floor
    rooms_by_floor = defaultdict(list)

    for room_name, loads in sorted(room_loads.items()):
        if not loads:
            continue

        # Get floor from first load
        floor = loads[0].get("floor", "1st Floor")

        rooms_by_floor[floor].append({"name": room_name, "loads": loads})

    # Create final structure with floors organized
    all_rooms = []
    for floor in ["1st Floor", "2nd Floor", "Exterior", "Equipment"]:
        all_rooms.extend(rooms_by_floor.get(floor, []))

    return all_rooms


if __name__ == "__main__":
    pdf_path = "Info/LoadL.pdf"

    print("Parsing LoadL.pdf...")
    rooms = parse_loads_pdf(pdf_path)

    print(f"\n✅ Found {len(rooms)} rooms")
    total_loads = sum(len(r["loads"]) for r in rooms)
    print(f"✅ Total loads: {total_loads}\n")

    # Show summary
    print("=" * 70)
    print("ROOM SUMMARY")
    print("=" * 70)

    for room in rooms[:10]:  # Show first 10
        print(f"\n{room['name']}: {len(room['loads'])} loads")
        for load in room["loads"][:3]:
            print(
                f"  {load['id']:3d}: {load['name']:<30} ({load['type']}, {load['power']}W)"
            )
        if len(room["loads"]) > 3:
            print(f"  ... and {len(room['loads']) - 3} more")

    if len(rooms) > 10:
        print(f"\n... and {len(rooms) - 10} more rooms")

    # Save to JSON
    config = {"rooms": rooms}
    output_path = "config/loads.json"

    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Saved to {output_path}")
