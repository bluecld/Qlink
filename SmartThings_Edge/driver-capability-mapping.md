# SmartThings Edge Driver Planning

## 1. Reference Material Pulled Locally

- Cloned `SmartThingsCommunity/SmartThingsEdgeDrivers` to `SmartThings_Edge/reference/SmartThingsEdgeDrivers/`.
  - Relevant examples to model:  
    - `drivers/SmartThings/lan-thing` â€“ minimal LAN driver layout (`config.yml`, `profiles/`, `src/init.lua`).  
    - `drivers/SmartThings/lan-hub-projector` and other LAN drivers for HTTP polling patterns.
  - Provides working `config.yml`, profile YAMLs, packaging scripts, and `smartthings` CLI workflow (see repo README).

## 2. Vantage Bridge Entities

| Entity Type | Source in Bridge | Behaviour | Current API |
|-------------|------------------|-----------|-------------|
| **Load (dimmer/on-off)** | `config/loads.json` entries (`loads` array) | Dimmer: accepts 0-100; Switch: 0/100 | `POST /device/{id}/set` with `{"level": 0-100}` or `{"switch": "on/off"}`<br>`GET /load/{id}/status` returns VGL response (0-100 or hex) |
| Scene / Station Button | `button` + `switch` per component | One device per station with components `button1`-`button8`; button commands trigger `/button/{station}/{button}` while switch states mirror LED feedback. |
| **LED state** | `/api/leds`, `/api/leds/{station}` | Reports per-button state (`on`, `blink`, `off`) | `GET /api/leds` (full map) or `GET /api/leds/{station}` |
| **Bridge telemetry** | `/monitor/status` | Indicates poll/event mode, connected clients | `GET /monitor/status` |

## 3. Capability Mapping Proposal

| Bridge Element | SmartThings Capability | Driver Notes |
|----------------|------------------------|--------------|
| Dimmer load (`type: dimmer`) | `switch`, `switchLevel` | Level drives both capabilities; 0 => `off`, >0 => `on`. Use `CapabilityHandlers` to map HTTP payloads. |
| Switch-only load (`type: switch` or implicit) | `switch` | Treat `on` as level 100, `off` as 0; hide level controls. |
| Scene / Station Button | `button` + `switch` per component | One device per station with components `button1`-`button8`; button commands trigger `/button/{station}/{button}` while switch states mirror LED feedback. |
| LED state indicator | `switch` (per button component) | LED polling from `/api/leds` updates each component's `switch` value (`on`, `off`, treating `blink` as `on`). |
| Bridge health | `healthCheck` / `presenceSensor` | Optional virtual parent device to surface connectivity. |

### Device Model Sketch

1. **Parent LAN Device**  
   - Represents the bridge itself.  
   - Handles configuration (IP, port) and dispatches child updates.  
   - Capabilities: `refresh`, optional `healthCheck`.

2. **Child Load Devices** (created per `loads.json` entry)  
   - `switch`, `switchLevel` (dimmers)  
   - Poll `GET /load/{id}/status` on refresh / schedule.  
   - Write `POST /device/{id}/set`.

3. **Child Scene Devices / Buttons**  
   - One device per station with components `button1`..`button8`.
   - Capabilities per component: `button`, `holdableButton`, `switch`.
   - Execute `POST /button/{station}/{button}` when receiving `switch.on` or `button.push`; LED polling drives the component `switch` state.

4. **LED Synchronisation**  
   - Parent polls `/api/leds` on a schedule.
   - Child load devices update their `switch`/`switchLevel` from `/load/{id}/status`.
   - Station children map LED data to component `switch` state (`on`, `off`, `blink`→`on`).

## 4. Driver Structure Outline

```
SmartThings_Edge/
  reference/SmartThingsEdgeDrivers/   # cloned samples
  custom-driver/
    config.yml
    profiles/
      parent-bridge.yml
      load-dimmer.yml
      scene-button.yml
    fingerprints/
      parent.yml                      # hub/lan placeholder
    src/
      init.lua                        # driver entry
      http_client.lua                 # helper for REST calls
      devices/
        parent.lua
        load_child.lua
        scene_child.lua
      util/
        polling.lua                   # periodic refresh / LED sync
```

Key SmartThings SDK modules to use:
- `cosock` + `socket.http` (LAN requests).
- `st.capabilities` for switch/level/button mapping.
- `st.driver` for child device creation (`driver:try_create_device`).

## 5. Next Steps

1. Draft profiles (`*.yml`) for parent/child devices.  
2. Implement driver scaffold (parent LAN driver + child handlers).  
3. Define polling strategy for loads/LEDs (pull or subscribe).  
4. Package via `smartthings edge:drivers:package` and test on hub.  
5. Document installation process (channel, driver install, bridge config).

