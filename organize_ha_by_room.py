import json
from datetime import datetime, timezone

# Load entity registry and area data
with open("/config/.storage/core.entity_registry", "r") as f:
    entity_registry = json.load(f)

with open("/config/ha_areas.json", "r") as f:
    area_data = json.load(f)

# Load or create area registry
import os

area_registry_path = "/config/.storage/core.area_registry"
if os.path.exists(area_registry_path):
    with open(area_registry_path, "r") as f:
        area_registry = json.load(f)
else:
    # Create new area registry
    area_registry = {
        "data": {"areas": []},
        "version": 1,
        "minor_version": 7,
        "key": "core.area_registry",
    }

# Create mapping of area name to area id
area_name_to_id = {}
for area in area_registry["data"]["areas"]:
    area_name_to_id[area["name"]] = area["id"]

# Create areas that don't exist
areas_created = 0
for area_info in area_data["areas"]:
    if not area_info["entities"]:  # Skip empty areas
        continue

    area_name = area_info["name"]
    if area_name not in area_name_to_id:
        import uuid

        area_id = str(uuid.uuid4()).replace("-", "")
        now = datetime.now(timezone.utc).isoformat()

        new_area = {
            "aliases": [],
            "floor_id": None,
            "icon": None,
            "id": area_id,
            "labels": [],
            "name": area_name,
            "picture": None,
            "created_at": now,
            "modified_at": now,
            "humidity_entity_id": None,
            "temperature_entity_id": None,
        }
        area_registry["data"]["areas"].append(new_area)
        area_name_to_id[area_name] = area_id
        areas_created += 1
        print(f"✅ Created area: {area_name}")

# Assign entities to areas
entities_assigned = 0
entity_id_to_area_name = {}
for area_info in area_data["areas"]:
    area_name = area_info["name"]
    for entity_id in area_info["entities"]:
        entity_id_to_area_name[entity_id] = area_name

for entity in entity_registry["data"]["entities"]:
    entity_id = entity["entity_id"]
    if entity_id in entity_id_to_area_name:
        area_name = entity_id_to_area_name[entity_id]
        area_id = area_name_to_id.get(area_name)
        if area_id:
            entity["area_id"] = area_id
            entities_assigned += 1
            print(f"  ✅ {entity_id} → {area_name}")

# Save registries
with open("/config/.storage/core.area_registry", "w") as f:
    json.dump(area_registry, f, indent=2)

with open("/config/.storage/core.entity_registry", "w") as f:
    json.dump(entity_registry, f, indent=2)

print(f"\n✅ Areas created: {areas_created}")
print(f"✅ Entities assigned: {entities_assigned}")
print("\n🎉 Home Assistant lights organized by room!")
