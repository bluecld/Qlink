import json

# Load area registry
with open("/config/.storage/core.area_registry", "r") as f:
    data = json.load(f)

# Add all missing required fields to areas
required_fields = {
    "floor_id": None,
    "icon": None,
    "labels": [],
    "humidity_entity_id": None,
    "temperature_entity_id": None,
}

for area in data["data"]["areas"]:
    for field, default_value in required_fields.items():
        if field not in area:
            area[field] = default_value

# Save fixed registry
with open("/config/.storage/core.area_registry", "w") as f:
    json.dump(data, f, indent=2)

print(f"Fixed {len(data['data']['areas'])} areas with all required fields")
