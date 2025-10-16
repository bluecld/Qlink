# SmartThings Edge Playbook (LAN HTTP)
Objective: Pair SmartThings Hub (v2/v3) with the Pi bridge via LAN HTTP.

## Driver outline
- A single parent "Bridge" device that discovers `/manifest` and creates child devices.
- Child profiles: `dimmer`, `switch`, `scene(button)`.
- Capability handlers:
  - switch.on/off → POST /device/{id}/set {switch: 'on'|'off'}
  - switchLevel.setLevel → POST /device/{id}/set {level: n}
  - button.push → POST /scene/{id}/activate (optional endpoint)

## Tasks for AI
- Scaffold driver (Lua) with HTTP client (cosock).
- Implement discovery, refresh, and command handlers.
- Add driver preferences: bridge IP/port.
- Provide a `tasks.json` command to package/install via SmartThings CLI.
