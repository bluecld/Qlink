# Vantage QLink Bridge SmartThings Edge Driver

This directory contains the first cut of a LAN Edge driver that connects a SmartThings hub to the `Vantage QLink Bridge` REST API exposed by this project.

## Structure

```
vantage-bridge-driver/
  config.yml                     # Driver metadata (name, package key, permissions)
  fingerprints.yml               # Initial LAN fingerprint to install the parent device
  profiles/                      # Device profiles for parent/child devices
  src/                           # Lua driver code (parent + child helpers)
  reference/SmartThingsEdgeDrivers/  # Official SmartThings sample drivers (git clone)
```

Key modules:

* `src/init.lua` – driver entry point; wires capability handlers and lifecycle callbacks.
* `src/devices/parent.lua` – manages the parent LAN device, including bridge preferences and child refresh scaffolding.
* `src/devices/load_child.lua` – stubs for switch/dimmer loads.
* `src/devices/scene_child.lua` – stubs for station button execution.
* `src/http_client.lua` – cosock-enabled HTTP helper used by the driver.

## Current behaviour

* Parent LAN device stores bridge IP/port preferences and keeps a scheduled refresh loop (120s).
* Discovery (`discovery.lua`) calls `/config`, creates/removes child devices for:
  * Loads (`load:<id>`) using the dimmer/switch profiles.
  * Stations (`station:<id>`) with components `button1`…`button8`.
* Load children issue `POST /device/{id}/set` for on/off/level and refresh from `/load/{id}/status`.
* Station children map SmartThings button/switch commands to `POST /button/{station}/{button}` and mirror LED status via component `switch` values using `/api/leds`.
* HTTP helper is cosock-friendly and shared by all modules.

## Next steps

1. Harden LED decoding (e.g., handle `on_leds`/`blink_leds` hex fallback).
2. Surface blink state visually (custom capability or extra attribute).
3. Add error/backoff handling for offline bridges and expose health to the parent device.

## Packaging & Installation (when ready to test)

1. **Install the SmartThings CLI**  
   Follow the official instructions: <https://developer.smartthings.com/docs/tools/cli>.

2. **Authenticate**  
   ```bash
   smartthings login
   ```

3. **Package the driver**  
   From the repository root:
   ```bash
   smartthings edge:drivers:package SmartThings_Edge/vantage-bridge-driver
   ```
   The CLI prints the `driverId` of the packaged build.

4. **Create or choose a channel** (once per project):
   ```bash
   smartthings edge:channels:create \
     --name "Vantage Bridge" \
     --description "LAN driver for the Vantage QLink bridge" \
     --type L
   ```
   Note the returned `channelId`.

5. **Assign the driver build to the channel**  
   ```bash
   smartthings edge:channels:drivers:add <channelId> <driverId>
   ```

6. **Enroll the hub**  
   ```bash
   smartthings edge:channels:enroll <channelId> <hubId>
   ```
   (`smartthings devices` lists hub IDs.)

7. **Install the driver**  
   In the SmartThings mobile app, open *Community Drivers*, pick the channel, and install the “Vantage QLink Bridge” driver.

8. **Add a device**  
   Use the app’s *Add device* → *Scan* flow. The parent LAN device should appear; enter the bridge IP/port preferences afterward.

These steps only need to be repeated when packaging a new build or adding hubs/channels.

See `driver-capability-mapping.md` for the working capability matrix.
