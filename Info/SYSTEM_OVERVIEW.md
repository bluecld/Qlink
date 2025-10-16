# Vantage System Overview - Home Prado Ver
**Generated**: October 16, 2025
**Source**: Home Prado Ver.txt

## System Information
- **QLink Version**: 4.82 (Build 346, 02/14/2007)
- **Firmware Version**: 7.89
- **TeleAccess Version**: 1.00
- **Project**: Tek Tjia
- **Controller IP**: 192.168.1.200:3040
- **Location**: Burbank, CA, United States

## Masters (Controllers)
1. **M1 West Utility 1** (Master 1)
   - Enclosure M1: West Utility 1 (4 modules)
   - Enclosure S1: West Utility 2 (4 modules)
   - Enclosure S2: West Utility 2A (2 modules)

2. **M2 Under Stairs** (Master 2)
   - Enclosure M2: Under Stairs (4 modules)
   - Enclosure S3: Linen Closet (4 modules)

## Key Findings

### Button Stations (Faceplates)
The system has **355 programmed buttons** across multiple stations (V01-V24, etc.)

### Example Button Configurations

**V23 - Game Room Station** (8 buttons):
1. Path - Controls loads 1317, 2148, 1328
2. Pendant - Controls load 1111
3. Soffit - Controls load 1114
4. Pool Table - Controls load 2141
5. Game Room On - Turns on: 1111, 1114, 1115, 2141
6. Medium - Sets 60%: 1111, 1114, 1115, 2141
7. Dim - Sets 20%: 1111, 1114, 1115, 2141
8. Game Room Off - Turns off all game room loads

**V02 - Library Station** (8 buttons):
1. Path - Switch pointer
4. Entry - Controls 1135, 1233, 1238
5. Library On - Turns on: 1113, 1147
6. Medium - Sets 60%: 1113, 1147
7. Dim - Sets 0%/20%: 1113, 1147
8. Library Off - Turns off: 1113, 1147

**V20 - Entry Station** (8 buttons):
1. Path
2. Outside
3. Foyer
4. All Outside Off
5. Entry On
6. Landscape
7. Dim
8. Entry Off

### Common Button Patterns
- **Button 1**: Often "Path" or "Outside" lighting
- **Button 5**: Typically "Room On" (full brightness)
- **Button 6**: Usually "Medium" (60% brightness)
- **Button 7**: Often "Dim" (20% brightness)
- **Button 8**: Commonly "Room Off" (all off)

### Scheduled Events
**Midnight** (11:59 PM):
- Load 1328 → 50%

**Exterior Off 10** (10:00 PM):
- Turns off exterior loads: 1112, 2212, 1117, 1144, 1127, 2115, 1231, 1232, 2221, 2231, 2233, 2238, 1145, 2121

## Load Types Configured
- Incandescent
- Fluorescent Magnetic (non-dimming & dimming)
- Fluorescent Electronic (non-dimming)
- Fluorescent Lutron High Lum
- Electronic Low Voltage
- Magnetic Low Voltage
- Motor / Variable Speed Motor
- DC Controlled
- HID
- Cold Cathode

## Module Types
- **MDS8RW101** - 8-channel dimmer
- **MDR8RW101** - 8-channel relay (non-dimming)
- **MDS8RW201** - 8-channel dimmer (alternate)
- **MDR8RW201** - 8-channel relay (alternate)
- **MDR8CW301** - 8-channel relay (alternate)
- **ED4008-120** - Electronic dimmer

## Notes for Integration
1. **Button commands can be sent** - The system supports button press simulation
2. **Load IDs are consistent** - Same load IDs used in LoadL.pdf
3. **Scenes are pre-programmed** - Multiple preset scenes on each station
4. **Time-based automation exists** - Exterior lights turn off at 10 PM, midnight preset
5. **Master/Station/Button hierarchy** - Commands can reference by Master, Station, Button
6. **Load groups** - Many buttons control multiple loads simultaneously

## Integration Opportunities
1. **Scene Control** - Trigger existing button scenes via API
2. **Time Override** - Manually control loads that have time schedules
3. **Multi-Load Commands** - Control room presets (On/Medium/Dim/Off)
4. **Status Monitoring** - Query button states and load levels
5. **Custom Scenes** - Create new combinations using existing load IDs

## Full Button Mapping
See `Button_Mappings_Summary.txt` for complete list of all 355 button configurations.
