#!/usr/bin/env python3
"""
Generate Home Assistant area assignments from loads.json
This script creates a YAML snippet to add area assignments to your lights
"""

import json
import re


def sanitize_name(name):
    """Convert room/light name to valid entity_id format"""
    # Remove special characters, convert to lowercase, replace spaces with underscores
    name = name.lower()
    name = re.sub(r"[^a-z0-9_\s-]", "", name)
    name = re.sub(r"\s+", "_", name)
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def main():
    # Read loads.json
    with open("config/loads.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    # Extract rooms and lights
    areas = {}
    light_to_area = {}

    for room in data["rooms"]:
        room_name = room["name"]
        floor = room.get("floor", "")

        # Skip placeholder rooms
        if "❄❄❄" in room_name or not room_name.strip():
            continue

        # Create area ID
        area_id = sanitize_name(room_name)

        # Store area info
        areas[area_id] = {"name": room_name, "floor": floor, "lights": []}

        # Map lights to this area
        for load in room.get("loads", []):
            load_id = load["id"]
            load_name = load["name"]

            # Generate entity_id as it appears in Home Assistant config
            # Format: light.{room}_{load_name}
            entity_id = f"light.{sanitize_name(room_name)}_{sanitize_name(load_name)}"

            light_to_area[entity_id] = area_id
            areas[area_id]["lights"].append(
                {
                    "entity_id": entity_id,
                    "name": f"{room_name} - {load_name}",
                    "load_id": load_id,
                }
            )

    # Generate output
    print("=" * 80)
    print("HOME ASSISTANT AREA ASSIGNMENTS")
    print("=" * 80)
    print()

    # Print summary
    print(f"Found {len(areas)} rooms with lights:")
    for area_id, area_info in sorted(areas.items()):
        print(f"  - {area_info['name']}: {len(area_info['lights'])} lights")
    print()

    # Generate customize.yaml content for area assignments
    print("=" * 80)
    print("ADD TO YOUR configuration.yaml:")
    print("=" * 80)
    print()
    print("# Add this at the top level of configuration.yaml")
    print("homeassistant:")
    print("  customize:")

    for entity_id, area_id in sorted(light_to_area.items()):
        area_name = areas[area_id]["name"]
        print(f"    {entity_id}:")
        print(
            f"      friendly_name: \"{area_name} - {entity_id.split('_', 1)[1].replace('_', ' ').title()}\""
        )
        # Note: area assignment must be done via UI or core.entity_registry

    print()
    print("=" * 80)
    print("AREA CREATION SCRIPT (Python for Home Assistant)")
    print("=" * 80)
    print()
    print("# Run this in Home Assistant's Python environment:")
    print("# Or use the REST API to create areas")
    print()

    # Generate area creation commands
    for area_id, area_info in sorted(areas.items()):
        print(f"# Area: {area_info['name']} ({area_info['floor']})")

    # Generate JSON for REST API area creation
    print()
    print("=" * 80)
    print("AREAS JSON (for REST API or manual creation)")
    print("=" * 80)
    print()

    areas_list = []
    for area_id, area_info in sorted(areas.items()):
        areas_list.append(
            {
                "area_id": area_id,
                "name": area_info["name"],
                "floor": area_info["floor"],
                "entities": [light["entity_id"] for light in area_info["lights"]],
            }
        )

    print(json.dumps(areas_list, indent=2))

    # Save to file
    output_file = "config/ha_areas.json"
    with open(output_file, "w", encoding="utf-8") as f:
        json.dump({"areas": areas_list, "entity_to_area": light_to_area}, f, indent=2)

    print()
    print(f"✅ Area mapping saved to: {output_file}")
    print()
    print("=" * 80)
    print("NEXT STEPS:")
    print("=" * 80)
    print("1. Areas must be created via Home Assistant UI or REST API")
    print("2. Then assign entities to areas using the entity registry")
    print("3. Alternatively, use the bulk area assignment script")


if __name__ == "__main__":
    main()
