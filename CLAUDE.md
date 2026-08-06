# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Deployment Environment

The bridge runs as a **systemd service** (`qlink-bridge.service`) on a small Linux
host, with uvicorn bound to `0.0.0.0:8000`. Web UI at `/ui/`.

Home Assistant runs as a **KVM/libvirt guest** on that same host - manage it with
`virsh --connect qemu:///system`, **not** Docker.

Deploy target (host, user, SSH key, remote dir) is read from `config/targets.json`,
which is gitignored. See `PROJECT_URLS.example.md` for the shape.

> Actual hostnames, IPs, and SSH details for this deployment live in the local,
> gitignored `PROJECT_URLS.md`. Read that file first when you need real addresses.
> There is no Raspberry Pi in the current deployment.

## Project Overview

Vantage Q-Link Bridge is a REST API bridge that modernizes legacy Vantage lighting control systems. It runs on a Linux host and provides HTTP/WebSocket endpoints for home automation platforms (primarily Home Assistant), mobile apps, and voice assistants to control Vantage lights, scenes, and buttons.

**Key Integration:** The bridge primarily integrates with Home Assistant, which provides HomeKit/Siri voice control through its HomeKit Bridge component.

## Development Commands

### Local Development

```bash
# Install dependencies
pip install -r app/requirements.txt
pip install -r dev-requirements.txt

# Run the bridge locally (dev mode with auto-reload)
python -m uvicorn app.bridge:app --reload --host 0.0.0.0 --port 8000

# Run the bridge (production mode)
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Run all tests
pytest -q

# Run specific test file
pytest tests/test_app.py
pytest tests/test_bridge_parsing.py

# Run with verbose output
pytest -v

# Run with coverage (requires pytest-cov)
pytest --cov=app tests/
```

### Code Quality

```bash
# Format code with Black
black .

# Check formatting without changes
black --check .

# Lint with ruff
ruff .

# Validate config files against JSON schemas
python scripts/validate_config.py --strict
```

### Deployment to the bridge host

```powershell
# Deploy from Windows (full deployment with dependencies)
.\scripts\deploy.ps1

# Quick update (faster, skips dependency reinstall)
.\scripts\update.ps1

# View service logs from the bridge host
.\scripts\logs.ps1
```

```bash
# On the bridge host: systemd service management
sudo systemctl start qlink-bridge
sudo systemctl stop qlink-bridge
sudo systemctl restart qlink-bridge
sudo systemctl status qlink-bridge
journalctl -u qlink-bridge -f  # tail logs

# Manual run on the bridge host (for debugging)
cd /home/<USER>/qlink-bridge
source venv/bin/activate
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

### ESP32 Room Panel (PlatformIO)

```bash
cd esp32-room-panel

# Build and upload firmware
pio run --target upload

# Monitor serial output
pio device monitor

# Build for specific environment
pio run -e esp32s3
```

### Home Assistant Configuration Generation

```bash
# Generate Home Assistant YAML configuration
python generate_ha_config.py --url http://qlinkpi.local:8000/config

# With API secret
python generate_ha_config.py --url http://qlinkpi.local:8000/config --secret YOUR_SECRET

# Generate area assignments for Home Assistant
python scripts/generate_ha_areas.py
python scripts/apply_ha_areas.py
```

## Architecture

### Core Components

**app/bridge.py** - The main FastAPI application containing:
- REST API endpoints for light/button control
- WebSocket server for real-time event streaming
- Vantage Q-Link protocol client (TCP socket communication)
- Command queue with worker thread to serialize Q-Link traffic
- Event monitoring system (polls LED states or listens for real-time events)
- SSDP advertiser for SmartThings LAN discovery
- Settings persistence system

**Key architectural patterns:**
- **Single command worker thread** - All Q-Link commands are queued and executed serially to avoid port exhaustion on the Vantage controller
- **Dual monitoring modes** - Poll mode (VLT@ every 7.5s) or event mode (continuous TCP connection for SW/LE/LO events)
- **Persistent settings** - Runtime settings (IP, port, timeouts) can be changed via POST /settings and are persisted to `config/bridge_settings.json`
- **Optional API secret** - Set BRIDGE_API_SECRET env var to require X-Bridge-Secret header on all requests

### Configuration Files

**config/loads.json** - Active room/load/button configuration
- Schema: `config/schemas/loads.rooms.v1.schema.json`
- Defines rooms, loads (lights), and buttons (scenes)
- Each load has an ID (contractor number from Vantage system)
- Buttons are identified by station + button number

**config/station_master_map.json** - Maps station IDs to their master controller number (typically 1)

**config/station_physical_map.json** - Maps virtual station IDs to physical station addresses (for systems with address translation)

**config/targets.json** - Deployment configuration for scripts/deploy.ps1
- Schema: `config/schemas/targets.v1.schema.json`
- Contains Pi hostname, SSH key path, remote directory, environment variables
- Gitignored (use targets.example.json as template)

**config/bridge_settings.json** - Persisted runtime settings (auto-generated)
- Stores VANTAGE_IP, VANTAGE_PORT, QLINK_TIMEOUT, etc.
- Overrides environment variables on startup
- Written by POST /settings endpoint

**config/ha_areas.json** - Home Assistant area assignments for automated organization

### Vantage Q-Link Protocol

The bridge communicates with Vantage InFusion controllers via TCP socket on port 3040 (default) using the Q-Link protocol.

**Key protocol details:**
- Commands are ASCII strings terminated by CR (`\r`) or CRLF (`\r\n`)
- Special command modifiers: `@` (response), `!` (no response), `#` (detailed response)
- Port 3040: read/write commands (VLO, VSW, VLT, VGL)
- Port 3041: typically closed on production controllers

**Common commands:**
- `VLO@ <load_id> <level> <fade>` - Set load level (0-100%) with fade time
- `VSW@ 1 <station> <button> 4` - Press button (trigger scene)
- `VGL@ <load_id>` - Get load status
- `VLT@ 1 <station>` - Get LED states for keypad (returns hex bitmasks)

**Event monitoring:**
- `SW` events - Button press/release (master, station, button, state, serial)
- `LE` events - LED state changes (station, on_mask, blink_mask)
- `LO`/`LS`/`LV` events - Load level changes (various formats)
- `LC` events - LCD LED changes

See `Info/QLINK1.rtf`, `Info/QLINK2.rtf`, and `Info/VANTAGE_COMMANDS.md` for complete protocol documentation.

### Home Assistant Integration

The bridge generates Home Assistant `template` lights that call the bridge's REST API. The configuration is generated by `generate_ha_config.py` which:
1. Fetches `/config` endpoint from the bridge
2. Creates a `light:` entry for each load in loads.json
3. Uses `curl` commands to call bridge endpoints for on/off/brightness
4. Configures HomeKit bridge component for Siri voice control

**Key files:**
- `generate_ha_config.py` - Main config generator
- `generate_ha_lights.py` - Alternative light-only generator
- `scripts/generate_ha_areas.py` - Creates area assignments
- `scripts/apply_ha_areas.py` - Applies areas to Home Assistant

### ESP32 Room Panel

Separate embedded project in `esp32-room-panel/` for building physical touch panel controllers:
- Hardware: ESP32-S3 with 1.8" AMOLED touch display
- Framework: PlatformIO with Arduino core
- Integration: MQTT to Home Assistant
- Purpose: Wall-mounted room control panels with real-time light status

## Environment Variables

**Required for operation:**
- `VANTAGE_IP` - IP address of Vantage controller (default: 192.168.1.200)
- `VANTAGE_PORT` - Q-Link command port (default: 3040)

**Optional configuration:**
- `QLINK_FADE` - Default fade time in seconds (default: 2.3)
- `QLINK_TIMEOUT` - Command timeout in seconds (default: 3.0)
- `QLINK_EOL` - Line terminator: CR or CRLF (default: CR)
- `QLINK_MONITOR_MODE` - Event monitoring: poll, events, or off (default: poll)
- `QLINK_LED_POLL_INTERVAL` - Seconds between LED polls (default: 7.5)
- `QLINK_MAX_RETRIES` - Command retry attempts (default: 3)
- `QLINK_RETRY_BASE_SEC` - Base retry delay in seconds (default: 0.1)
- `QLINK_COMMAND_GAP` - Minimum gap between commands in seconds (default: 0.05)
- `BRIDGE_API_SECRET` - Optional shared secret for API authentication

## Testing Patterns

The test suite uses `pytest` with `FastAPI TestClient` for API testing:

**Monkeypatching for unit tests:**
```python
def test_send_raw(monkeypatch):
    # Stub network calls to avoid actual Vantage connection
    monkeypatch.setattr("app.bridge.qlink_send", lambda cmd: "OK")
    r = client.get("/send/TESTCMD")
    assert r.status_code == 200
```

**Testing event parsing:**
```python
def test_parse_vantage_event_sw():
    msg = "SW 1 23 5 1 0001"
    evt = bridge.parse_vantage_event(msg)
    assert evt["type"] == "button"
    assert evt["station"] == 23
```

**Key test files:**
- `tests/test_app.py` - API endpoint tests (healthz, config, device control, LED status)
- `tests/test_bridge_parsing.py` - Q-Link protocol parsing (events, LED decoding, retry logic)
- `tests/conftest.py` - Pytest fixtures and configuration

## CI/CD

GitHub Actions CI runs on push/PR to main/master:
1. Lint with `ruff` (non-blocking)
2. Format check with `black` (fails if not formatted)
3. Run `pytest` test suite (fails if tests fail)

**CI configuration:** `.github/workflows/ci.yml`

## Common Development Patterns

### Adding a new API endpoint

1. Add the route handler in `app/bridge.py`
2. Use Pydantic models for request/response validation
3. Call `qlink_send()` for synchronous commands or `command_queue.put()` for queued execution
4. Add tests in `tests/test_app.py`
5. Update API documentation in `docs/OPENAPI.yaml` if applicable

### Modifying Q-Link protocol handling

1. Check protocol docs: `Info/QLINK1.rtf`, `Info/QLINK2.rtf`, `Info/VANTAGE_COMMANDS.md`
2. Update command builder or response parser in `app/bridge.py`
3. Add parsing tests in `tests/test_bridge_parsing.py`
4. Test with actual Vantage hardware if changing command format

### Updating configuration schema

1. Edit schema in `config/schemas/*.schema.json`
2. Run `python scripts/validate_config.py --strict` to validate existing configs
3. Update example files: `config/*.example.json`
4. Update documentation referencing the schema

### Debugging connection issues

1. Check bridge logs: `journalctl -u qlink-bridge -f` (on Pi)
2. Verify Vantage IP/port: `curl http://qlinkpi:8000/config`
3. Test raw socket: `telnet <VANTAGE_IP> 3040`
4. Check command queue: `curl http://qlinkpi:8000/monitor/status`
5. Review retry/timeout settings in environment or persisted settings

## File Organization

**Critical:** Never modify files in `waveshare-official/` or `.venv/` - these are external dependencies.

**Script purposes:**
- `scripts/extract_*.py` - Parse Vantage system exports to extract configuration data
- `scripts/parse_*.py` - Additional parsing utilities for button/faceplate data
- `scripts/merge_*.py` - Combine multiple config sources
- `scripts/validate_config.py` - JSON schema validation
- `scripts/deploy.ps1` - Primary deployment script (PowerShell)
- `scripts/mock_vantage.py` - Mock Vantage controller for testing without hardware

**Info directory:** Contains Vantage protocol documentation and system exports - read-only reference material.

**Archive directory:** Old/experimental code kept for reference - not active in production.
