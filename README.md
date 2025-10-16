# Vantage Q-Link Bridge

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)

A modern REST API bridge for legacy Vantage lighting control systems. Run on a Raspberry Pi to control your Vantage devices via HTTP from any home automation platform, mobile app, or voice assistant.

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
git clone https://github.com/yourusername/vantage-qlink-bridge.git
cd vantage-qlink-bridge

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

### Vantage System
- Vantage InFusion controller with Q-Link protocol
- IP-Enabler or network-connected controller
- Port 3041 accessible (or 3040 for read-only)

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
git clone https://github.com/yourusername/vantage-qlink-bridge.git
cd vantage-qlink-bridge

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
  "event_listener_connected": true,
  "event_monitoring_enabled": true,
  "websocket_clients": 2,
  "vantage_ip": "192.168.1.200",
  "vantage_port": 3041
}
```

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

ws.onmessage = (event) => {
  const data = JSON.parse(event.data);
  console.log('Event received:', data);

  if (data.type === 'button') {
    console.log(`Button ${data.button} on station ${data.station}: ${data.state}`);
  }
};
```

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
vantage-qlink-bridge/
├── app/
│   ├── bridge.py           # Main FastAPI application
│   ├── requirements.txt    # Python dependencies
│   └── loads.json          # Light/scene configuration
├── config/
│   ├── targets.json        # Deployment config (ignored)
│   └── targets.example.json
├── docs/
│   ├── OPENAPI.yaml        # API specification
│   ├── VANTAGE_COMMANDS.md # Q-Link command reference
│   └── VANTAGE_EVENT_MONITORING.md
├── scripts/
│   ├── deploy.ps1          # Windows deployment
│   ├── update.ps1          # Quick update
│   ├── logs.ps1            # View logs
│   ├── remote-setup.sh     # Pi bootstrap
│   └── remote-update.sh    # Pi update script
├── tests/
│   └── test_app.py         # Unit tests
├── .gitignore
├── LICENSE
├── README.md
├── CONTRIBUTING.md
└── CHANGELOG.md
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
- [Issue Tracker](https://github.com/yourusername/vantage-qlink-bridge/issues)
- [Discussions](https://github.com/yourusername/vantage-qlink-bridge/discussions)

## ⚠️ Disclaimer

This is an unofficial project and is not affiliated with or endorsed by Vantage Controls. Use at your own risk.

---

**Made with ❤️ for the smart home community**

