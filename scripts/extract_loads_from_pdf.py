#!/usr/bin/env python3
"""Extract load information from LoadL.pdf and create loads.json"""

import json
import re
from PyPDF2 import PdfReader


def extract_loads_from_pdf(pdf_path):
    """Extract room and load information from the PDF."""

    reader = PdfReader(pdf_path)
    text = ""

    # Extract all text from PDF
    for page in reader.pages:
        text += page.extract_text() + "\n"

    print("=" * 60)
    print("PDF CONTENT EXTRACTED")
    print("=" * 60)
    print(text)
    print("=" * 60)

    # Try to parse the structure
    # Common formats might be:
    # - Room Name
    #   Load ID: Load Name (Type)
    # or similar patterns

    rooms = []
    current_room = None

    lines = text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        print(f"Processing line: {line}")

        # Look for room names (heuristic: lines that don't start with numbers)
        # and load entries (lines with load IDs)

        # Try to match patterns like "123 - Load Name" or "Load 123: Name"
        load_match = re.search(r"(\d+)[\s\-:]+(.+)", line)

        if load_match:
            load_id = int(load_match.group(1))
            load_name = load_match.group(2).strip()

            # Determine type (assume dimmer unless it says switch/relay)
            load_type = (
                "switch"
                if any(x in load_name.lower() for x in ["switch", "relay", "outlet"])
                else "dimmer"
            )

            if current_room:
                current_room["loads"].append(
                    {"id": load_id, "name": load_name, "type": load_type}
                )
        else:
            # Might be a room name
            if len(line) > 3 and not line[0].isdigit():
                # Start a new room
                if current_room and current_room["loads"]:
                    rooms.append(current_room)

                current_room = {"name": line, "loads": []}

    # Add last room
    if current_room and current_room["loads"]:
        rooms.append(current_room)

    return rooms


if __name__ == "__main__":
    pdf_path = "Info/LoadL.pdf"

    print(f"Reading {pdf_path}...")
    rooms = extract_loads_from_pdf(pdf_path)

    print("\n" + "=" * 60)
    print(f"EXTRACTED {len(rooms)} ROOMS")
    print("=" * 60)

    for room in rooms:
        print(f"\n{room['name']}: {len(room['loads'])} loads")
        for load in room["loads"][:3]:  # Show first 3
            print(f"  - {load['id']}: {load['name']} ({load['type']})")
        if len(room["loads"]) > 3:
            print(f"  ... and {len(room['loads']) - 3} more")

    # Create the config structure
    config = {"rooms": rooms}

    # Save to loads.json
    output_path = "config/loads.json"
    with open(output_path, "w") as f:
        json.dump(config, f, indent=2)

    print(f"\n✅ Saved to {output_path}")
    print(f"Total loads: {sum(len(r['loads']) for r in rooms)}")
