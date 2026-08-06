#!/bin/bash
# Apply area assignments to Home Assistant via Python script
# This runs inside the Home Assistant container

# Read the areas JSON from stdin
AREAS_JSON="$1"

python3 << 'EOF'
import json
import sys
import os

# Home Assistant imports
sys.path.insert(0, '/usr/src/homeassistant')
from homeassistant import config_entries
from homeassistant.core import HomeAssistant
from homeassistant.helpers import area_registry, entity_registry

async def apply_areas():
    """Apply area assignments"""
    # Load area mappings
    with open('/config/ha_areas.json', 'r') as f:
        data = json.load(f)

    # Get registries
    hass = HomeAssistant('/config')
    await hass.async_start()

    area_reg = area_registry.async_get(hass)
    entity_reg = entity_registry.async_get(hass)

    print("=" * 80)
    print("CREATING AREAS AND ASSIGNING ENTITIES")
    print("=" * 80)

    for area_data in data['areas']:
        area_name = area_data['name']
        entities = area_data['entities']

        if not entities:
            continue

        # Create or get area
        area = area_reg.async_get_area_by_name(area_name)
        if not area:
            area = area_reg.async_create(area_name)
            print(f"✅ Created area: {area_name}")
        else:
            print(f"ℹ️  Area exists: {area_name}")

        # Assign entities
        for entity_id in entities:
            entity = entity_reg.async_get(entity_id)
            if entity:
                entity_reg.async_update_entity(entity_id, area_id=area.id)
                print(f"  ✅ {entity_id} → {area_name}")
            else:
                print(f"  ⚠️  Entity not found: {entity_id}")

    await hass.async_stop()
    print("\n✅ Area assignment complete!")

# Run
import asyncio
asyncio.run(apply_areas())
EOF
