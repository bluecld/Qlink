# Vantage Q-Link Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A modern REST API bridge for legacy Vantage lighting control systems. Run on a Raspberry Pi to control your Vantage devices via HTTP from any home automation platform, mobile app, or voice assistant.

Note: Config Schemas and validation guidance live in docs/SCHEMAS.md.
TODO (placeholder): After cleaning up README encoding artifacts, add a dedicated "Config Schemas" section here linking to docs/SCHEMAS.md and showing local/CI validation commands.

## 🌟 Features

- **REST API** - Control lights and scenes via simple HTTP endpoints
- **Real-time Event Monitoring** - WebSocket streaming of button presses, load changes, and LED updates
- **Web UI** - Browser-based control panel with configurable settings
- **Easy Deployment** - One-command deploy to Raspberry Pi with systemd service
- **SmartThings Ready** - Designed for integration with SmartThings Edge drivers
- **Low Latency** - Persistent TCP connection to Vantage for instant updates
- **Auto-reconnect** - Resilient connection handling with automatic retry

## 📋 Table of Contents

- [Quick Start](#quick-start)
- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [API Documentation](#api-documentation)
- [Web Interface](#web-interface)
- [Event Monitoring](#event-monitoring)
- [Deployment](#deployment)
- [Contributing](#contributing)
- [License](#license)

## 🚀 Quick Start

### For Development (Local Testing)

```powershell
# Clone the repository
git clone https://github.com/bluecld/Qlink.git
cd Qlink

# Install dependencies
pip install -r app/requirements.txt

# Set environment variables (optional)
$env:VANTAGE_IP="192.168.1.200"
$env:VANTAGE_PORT="3041"

# Run the bridge
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000

# Open web interface
start http://localhost:8000/ui/
```

### For Production (Raspberry Pi)

```powershell
# 1. Copy and edit deployment config
Copy-Item config\targets.example.json config\targets.json
# Edit config\targets.json with your Pi details

# 2. Deploy to Pi
powershell -ExecutionPolicy Bypass -File .\scripts\deploy.ps1

# 3. Access your bridge
start http://qlinkpi.local:8000/ui/
```

## 📦 Requirements

### Development Machine
- Windows, macOS, or Linux
- Python 3.11 or higher
- Git

### Raspberry Pi (Production)
- Raspberry Pi 3/4/5 or Zero 2 W
- Raspberry Pi OS (Bullseye or newer)
- SSH enabled
- Network access to Vantage IP-Enabler

### Security & Network Placement
- The bridge is designed for **LAN-only** use. Do not expose it directly to the internet.
- Set the optional `BRIDGE_API_SECRET` environment variable to require the `X-Bridge-Secret` header on every API/WebSocket request.
- Restrict access further with firewall rules or a reverse proxy when integrating with cloud services.

- The bundled UI will prompt for the secret and store it in `localStorage` when required.
### Vantage System
- Vantage InFusion controller with Q-Link protocol
- IP-Enabler or network-connected controller
- Port 3041 accessible (read/write: tested with `VLO@`, `VSW`, `VLT@`, `VGL@`); optional port 3040 for read-only polling (`VLT@` only)

## 🔧 Installation

### Option 1: Deploy to Raspberry Pi (Recommended)

1. **Prepare your deployment config:**

```powershell
Copy-Item config\targets.example.json config\targets.json
```

Edit `config\targets.json`:
```json
{
  "host": "qlinkpi.local",
  "user": "pi",
  "key": "C:\\Users\\yourname\\.ssh\\id_ed25519",
  "remote_dir": "/home/pi/qlink-bridge",
  "env": {
    "VANTAGE_IP": "192.168.1.200",
    "VANTAGE_PORT": "3041"
  }
}
```

2. **Deploy:**

```powershell
.\scripts\deploy.ps1
```

This will:
- Package the application
- Copy files to your Pi via SCP
- Create a Python virtual environment
- Install dependencies
- Create and start a systemd service
- Bridge will be available at `http://yourpi:8000`

### Option 2: Manual Installation on Pi

```bash
# SSH to your Pi
ssh pi@qlinkpi.local

# Clone repository
git clone https://github.com/bluecld/Qlink.git
cd Qlink

# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r app/requirements.txt

# Set environment variables
export VANTAGE_IP="192.168.1.200"
export VANTAGE_PORT="3041"

# Run bridge
python -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000
```

## ⚙️ Configuration

### Environment Variables

Configure the bridge using environment variables or the web settings interface:

| Variable | Default | Description |
|----------|---------|-------------|
| `VANTAGE_IP` | `192.168.1.200` | IP address of Vantage controller |
| `VANTAGE_PORT` | `3041` | Port for Q-Link commands (3041=RW, 3040=RO) |
| `QLINK_FADE` | `2.3` | Default fade time in seconds |
| `QLINK_TIMEOUT` | `2.0` | Command timeout in seconds |
| `QLINK_EOL` | `CR` | Line terminator (CR or CRLF) |
| `BRIDGE_API_SECRET` | *(empty)* | Optional shared secret required via the `X-Bridge-Secret` header and `?token=` WebSocket parameter. |

### Load Configuration

Create `app/loads.json` to define your lights and scenes:

```json
{
  "rooms": [
    {
      "name": "Living Room",
      "loads": [
        {"id": 101, "name": "Ceiling Lights"},
        {"id": 102, "name": "Table Lamps"}
      ],
      "buttons": [
        {"station": 23, "button": 1, "name": "All On"},
        {"station": 23, "button": 2, "name": "All Off"}
      ]
    }
  ]
}
```

## 📡 API Documentation

### Control Endpoints

#### Set Light Level
```http
POST /load/{id}/set
Content-Type: application/json

{
  "level": 75,
  "fade": 2.0
}
```

#### Get Light Status
```http
GET /load/{id}/status

Response: {
  "load_id": 101,
  "level": 75,
  "status": "R:STATUS 101 75"
}
```

#### Press Button (Trigger Scene)
```http
POST /button/{station}/{button}

Response: {
  "station": 23,
  "button": 5,
  "command": "VSW@ 1 23 5 4",
  "status": "ok"
}
```

### System Endpoints

#### Get Configuration
```http
GET /config

Response: {
  "ip": "192.168.1.200",
  "port": 3041,
  "fade": "2.3",
  "rooms": [...]
}
```

#### Health Check
```http
GET /healthz

Response: {"status": "ok"}
```

#### Monitor Status
```http
GET /monitor/status

Response: {
  "mode": "poll",
  "configured_mode": "poll",
  "command_queue_depth": 0,
  "command_queue_peak": 3,
  "last_command_rtt_ms": 12.4,
  "last_command_at": "2025-10-16T10:35:01",
  "last_command_error": null,
  "command_worker_alive": true,
  "total_commands_sent": 542,
  "event_socket_connected": true,
  "monitoring_enabled": true,
  "websocket_clients": 2,
  "vantage_ip": "192.168.1.200",
  "vantage_port": 3041,
  "stations_tracked": 42,
  "note": "Polling LED states every 7.5s via VLT@"
}
```


### Command Throttling & Metrics
- A single worker thread serializes all Q-Link traffic to avoid port exhaustion.
- `QLINK_COMMAND_GAP` (default 50ms) enforces a small delay between commands.
- `/monitor/status` exposes queue depth, peak usage, and last round-trip time to help tune automations.

## 🖥️ Web Interface

Access the web UI at `http://yourpi:8000/ui/`

**Features:**
- Control individual lights with sliders
- Trigger scenes with buttons
- Real-time status updates
- Settings page for configuration
- Event log viewer

### Settings Tab

The settings interface allows you to change configuration without SSH:
- Vantage IP address
- Vantage port
- Default fade time
- Timeout values

Changes are saved and applied immediately (no restart required for most settings).

## 📊 Event Monitoring

### WebSocket Event Stream

Connect to real-time events at `ws://yourpi:8000/events`

**Example (JavaScript):**
```javascript
const ws = new WebSocket('ws://qlinkpi.local:8000/events');
// Append ?token=YOUR_SECRET if BRIDGE_API_SECRET is set

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event received:', data);

  if (data.type === 'button') {
    console.log(`Button ${data.button} on station ${data.station}: ${data.state}`);
  }
};
```

If `BRIDGE_API_SECRET` is set, include the `X-Bridge-Secret` header on REST calls and append `?token=YOUR_SECRET` to WebSocket URLs.
**Event Types:**
- `button` - Button press/release (SW events)
- `load` - Load level change (LO/LS/LV events)
- `led` - LED state change (LE/LC events)

### Event Examples

**Button Press:**
```json
{
  "type": "button",
  "master": 1,
  "station": 23,
  "button": 5,
  "state": "pressed",
  "serial": null,
  "timestamp": "2025-10-16T10:30:45"
}
```

**Load Change:**
```json
{
  "type": "load",
  "subtype": "module",
  "load_id": 101,
  "level": 75,
  "timestamp": "2025-10-16T10:30:46"
}
```

**LED Update:**
```json
{
  "type": "led",
  "station": 32,
  "station_id": "V32",
  "button_states": {
    "5": "on",
    "6": "blink",
    "8": "off"
  },
  "timestamp": "2025-10-16T10:30:47"
}
```

## 🚀 Deployment

### Deploy from Windows

The included PowerShell script handles complete deployment:

```powershell
.\scripts\deploy.ps1
```

### Update Existing Installation

```powershell
# Use the update script for faster deployments
.\scripts\update.ps1
```

### View Service Logs

```powershell
# Tail logs from your Pi
.\scripts\logs.ps1
```

Or manually:
```bash
ssh pi@qlinkpi.local
journalctl -u qlink-bridge -f
```

### Systemd Service Management

```bash
# Start service
sudo systemctl start qlink-bridge

# Stop service
sudo systemctl stop qlink-bridge

# Restart service
sudo systemctl restart qlink-bridge

# View status
sudo systemctl status qlink-bridge

# Enable auto-start on boot
sudo systemctl enable qlink-bridge
```

## 🏗️ Project Structure

```
Qlink/
├── app/                    # Main application code
│   ├── bridge.py           # FastAPI application with REST API & WebSocket
│   ├── requirements.txt    # Python dependencies
│   ├── static/             # Web UI files (home-v2.html, etc.)
│   └── __init__.py         # Package marker
├── config/                 # Configuration files
│   ├── loads.json          # Active room/load/button configuration
│   ├── loads.example.json  # Example configuration template
│   ├── station_master_map.json      # Station-to-master assignments
│   ├── station_physical_map.json    # Virtual-to-physical station mapping
│   ├── targets.json        # Deployment settings (gitignored)
│   ├── targets.example.json
│   └── schemas/            # JSON schemas for validation
│       ├── loads.rooms.v1.schema.json
│       └── targets.v1.schema.json
├── scripts/                # Deployment and utility scripts
│   ├── deploy.ps1          # Deploy to Raspberry Pi
│   ├── update.ps1          # Quick update deployment
│   ├── logs.ps1            # View remote logs
│   ├── remote-setup.sh     # Pi setup script
│   ├── validate_config.py  # Config validation
│   └── extract_*.py        # Config parsing utilities
├── tests/                  # Unit tests
│   ├── test_app.py         # API endpoint tests
│   └── test_bridge_parsing.py  # Parsing/decoding tests
├── Info/                   # Vantage system reference materials
│   ├── QLINK1.rtf          # QLink protocol v1 spec
│   ├── QLINK2.rtf          # QLink protocol v2 spec
│   ├── Home Prado Ver.txt  # System export (all stations/loads)
│   ├── VANTAGE_COMMANDS.md
│   └── VANTAGE_EVENT_MONITORING.md
├── docs/                   # Current project documentation
│   ├── OPENAPI.yaml        # API specification
│   ├── SCHEMAS.md          # Config schema guide
│   └── WEB_UI_V2.md        # UI documentation
├── .github/
│   └── workflows/
│       └── ci.yml          # CI: lint, type-check, tests
├── .gitignore
├── LICENSE
├── README.md
├── TESTING.md              # Test running instructions
└── dev-requirements.txt    # Development tools (ruff, mypy, pytest)
```

## 🤝 Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

**Ways to contribute:**
- Report bugs and request features via Issues
- Submit Pull Requests for bug fixes or enhancements
- Improve documentation
- Share your integration examples

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- Vantage Q-Link protocol documentation
- Raspberry Pi Foundation

## 🔗 Links

- [Vantage Controls](https://www.vantagecontrols.com/)
- [Issue Tracker](https://github.com/bluecld/Qlink/issues)
- [Discussions](https://github.com/bluecld/Qlink/discussions)

## ⚠️ Disclaimer

This is an unofficial project and is not affiliated with or endorsed by Vantage Controls. Use at your own risk.

---

**Made with ❤️ for the smart home community**
