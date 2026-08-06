#!/usr/bin/env python3
"""
Apply area assignments to Home Assistant entities via REST API
This script creates areas and assigns entities automatically
"""

import json
import sys

import requests


def get_ha_token():
    """Prompt for Home Assistant Long-Lived Access Token"""
    print("=" * 80)
    print("HOME ASSISTANT ACCESS TOKEN REQUIRED")
    print("=" * 80)
    print("To create a token:")
    print("1. Go to http://<BRIDGE_IP>:8123/profile/security")
    print("2. Scroll to 'Long-Lived Access Tokens'")
    print("3. Click 'CREATE TOKEN'")
    print("4. Give it a name like 'Area Assignment Script'")
    print("5. Copy the token")
    print()
    token = input("Paste your Home Assistant token here: ").strip()
    return token


def create_area(ha_url, token, area_name, floor=None):
    """Create an area in Home Assistant"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    payload = {"name": area_name}
    if floor:
        payload["floor_id"] = floor.lower().replace(" ", "_")

    response = requests.post(
        f"{ha_url}/api/config/area_registry", headers=headers, json=payload
    )

    if response.status_code in [200, 201]:
        return response.json()
    elif response.status_code == 400 and "already exists" in response.text.lower():
        # Area already exists, get it
        areas = requests.get(
            f"{ha_url}/api/config/area_registry", headers=headers
        ).json()
        for area in areas:
            if area["name"] == area_name:
                return area
    else:
        print(
            f"  ⚠️  Failed to create area '{area_name}': {response.status_code} - {response.text}"
        )
        return None


def assign_entity_to_area(ha_url, token, entity_id, area_id):
    """Assign an entity to an area"""
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

    # Update entity registry
    response = requests.post(
        f"{ha_url}/api/config/entity_registry/{entity_id}",
        headers=headers,
        json={"area_id": area_id},
    )

    return response.status_code in [200, 201]


def main():
    # Configuration
    ha_url = "http://<BRIDGE_IP>:8123"

    # Load area mappings
    with open("config/ha_areas.json", "r", encoding="utf-8") as f:
        data = json.load(f)

    areas_data = data["areas"]

    print("=" * 80)
    print("HOME ASSISTANT AREA ASSIGNMENT")
    print("=" * 80)
    print(f"Target: {ha_url}")
    print(f"Areas to create: {len(areas_data)}")
    print(f"Entities to assign: {sum(len(a['entities']) for a in areas_data)}")
    print()

    # Get token
    token = get_ha_token()

    print()
    print("=" * 80)
    print("CREATING AREAS AND ASSIGNING ENTITIES")
    print("=" * 80)

    created_areas = 0
    assigned_entities = 0
    failed_assignments = 0

    for area_data in areas_data:
        area_name = area_data["name"]
        floor = area_data.get("floor")
        entities = area_data["entities"]

        # Skip empty areas (separators)
        if not entities:
            print(f"⏩ Skipping empty area: {area_name}")
            continue

        print(f"\n📁 {area_name} ({floor}) - {len(entities)} lights")

        # Create area
        area_obj = create_area(ha_url, token, area_name, floor)
        if not area_obj:
            print(f"  ❌ Failed to create area, skipping entities")
            continue

        area_id = area_obj.get("area_id")
        created_areas += 1

        # Assign entities
        for entity_id in entities:
            if assign_entity_to_area(ha_url, token, entity_id, area_id):
                assigned_entities += 1
                print(f"  ✅ {entity_id}")
            else:
                failed_assignments += 1
                print(f"  ❌ {entity_id}")

    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"✅ Areas created: {created_areas}")
    print(f"✅ Entities assigned: {assigned_entities}")
    if failed_assignments > 0:
        print(f"❌ Failed assignments: {failed_assignments}")
    print()
    print("🎉 Area assignment complete!")
    print()
    print("Next steps:")
    print("1. Restart Home Assistant to apply changes")
    print("2. Check Settings → Areas & Labels in Home Assistant UI")
    print("3. HomeKit will now show proper room assignments")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n❌ Cancelled by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n\n❌ Error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)
