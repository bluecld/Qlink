# Apply area assignments to Home Assistant via SSH and Python
# Usage: .\apply_ha_areas.ps1

param(
    [Parameter(Mandatory = $false)]
    [string]$SshHost = "qlinkpi.tail875b5a.ts.net",

    [Parameter(Mandatory = $false)]
    [string]$SshUser = "pi"
)

# Load area mappings
$areasData = Get-Content "config\ha_areas.json" -Raw | ConvertFrom-Json

Write-Host "=" * 80
Write-Host "HOME ASSISTANT AREA ASSIGNMENT"
Write-Host "=" * 80
Write-Host "Target: Home Assistant via Docker on $SshHost"
Write-Host "Areas to create: $($areasData.areas.Count)"
Write-Host "Entities to assign: $(($areasData.areas | ForEach-Object { $_.entities.Count } | Measure-Object -Sum).Sum)"
Write-Host ""

Write-Host "=" * 80
Write-Host "UPLOADING AREA DATA TO RASPBERRY PI"
Write-Host "=" * 80

# Copy ha_areas.json to Pi
scp config\ha_areas.json "${SshUser}@${SshHost}:/home/pi/ha_areas.json"

Write-Host ""
Write-Host "=" * 80
Write-Host "CREATING AREAS AND ASSIGNING ENTITIES"
Write-Host "=" * 80

# Create Python script to run inside Home Assistant container
$pythonScript = @'
import json
import sys

# Load area mappings
with open('/config/ha_areas.json', 'r') as f:
    data = json.load(f)

# Read .storage files
import os
area_registry_path = '/config/.storage/core.area_registry'
entity_registry_path = '/config/.storage/core.entity_registry'

# Load registries
with open(area_registry_path, 'r') as f:
    area_registry = json.load(f)

with open(entity_registry_path, 'r') as f:
    entity_registry = json.load(f)

# Create areas
created_areas = 0
assigned_entities = 0

for area_data in data['areas']:
    area_name = area_data['name']
    entities = area_data['entities']

    if not entities:
        print(f"⏩ Skipping empty area: {area_name}")
        continue

    print(f"\n📁 {area_name} ({area_data['floor']}) - {len(entities)} lights")

    # Check if area exists
    area_id = None
    for area in area_registry['data']['areas']:
        if area['name'] == area_name:
            area_id = area['id']
            print(f"  ℹ️  Area already exists")
            break

    # Create area if not exists
    if not area_id:
        import uuid
        area_id = str(uuid.uuid4()).replace('-', '')
        area_registry['data']['areas'].append({
            'id': area_id,
            'name': area_name,
            'picture': None,
            'aliases': []
        })
        created_areas += 1
        print(f"  ✅ Created area")

    # Assign entities
    for entity_id in entities:
        entity_found = False
        for entity in entity_registry['data']['entities']:
            if entity['entity_id'] == entity_id:
                entity['area_id'] = area_id
                assigned_entities += 1
                entity_found = True
                print(f"  ✅ {entity_id}")
                break

        if not entity_found:
            print(f"  ⚠️  Entity not found: {entity_id}")

# Save registries
with open(area_registry_path, 'w') as f:
    json.dump(area_registry, f, indent=2)

with open(entity_registry_path, 'w') as f:
    json.dump(entity_registry, f, indent=2)

print(f"\n✅ Areas created/updated: {created_areas}")
print(f"✅ Entities assigned: {assigned_entities}")
print("\n🎉 Area assignment complete!")
'@

# Write Python script to temp file and execute via SSH
$pythonScript | Out-File -FilePath "temp_assign_areas.py" -Encoding UTF8 -NoNewline

# Copy Python script to Pi
scp temp_assign_areas.py "${SshUser}@${SshHost}:/home/pi/temp_assign_areas.py"

# Copy both files into Home Assistant config directory
ssh "${SshUser}@${SshHost}" "sudo cp /home/pi/ha_areas.json /home/pi/homeassistant/ha_areas.json && sudo cp /home/pi/temp_assign_areas.py /home/pi/homeassistant/temp_assign_areas.py"

# Execute Python script inside Home Assistant container
ssh "${SshUser}@${SshHost}" "docker exec homeassistant python3 /config/temp_assign_areas.py"

# Clean up temp files
Remove-Item temp_assign_areas.py -Force
ssh "${SshUser}@${SshHost}" "rm /home/pi/temp_assign_areas.py /home/pi/ha_areas.json && sudo rm /home/pi/homeassistant/temp_assign_areas.py"

Write-Host ""
Write-Host "=" * 80
Write-Host "NEXT STEPS"
Write-Host "=" * 80
Write-Host "1. Restart Home Assistant: Settings → System → Restart"
Write-Host "2. Check Settings → Areas & Labels in Home Assistant UI"
Write-Host "3. Verify lights are assigned to rooms"
Write-Host "4. Pair HomeKit SmartThings Bridge - rooms will auto-assign!"
Write-Host ""
