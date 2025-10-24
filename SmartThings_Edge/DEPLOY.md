# SmartThings Edge Driver Deployment Guide

## Quick Start (When API is working)

The driver is already packaged and ready to deploy: `vantage-bridge.zip`

### Prerequisites
- SmartThings CLI installed: `npm install -g @smartthings/cli`
- Personal Access Token (24-hour validity): https://account.smartthings.com/tokens
- Hub ID: `92e0cdbe-81a5-49c6-91a5-45f31204b21b`

### Required Token Scopes
When creating your Personal Access Token, select:
- ✅ `l:drivers` - List drivers
- ✅ `w:drivers` - Write drivers
- ✅ `x:drivers` - Execute driver operations
- ✅ `l:devices` - List devices
- ✅ `r:channels` - Read channels
- ✅ `w:channels` - Write channels

### Deploy Commands

#### Option 1: Upload Pre-built Package (Fastest)

```bash
# Set your token (get fresh one from https://account.smartthings.com/tokens)
export SMARTTHINGS_TOKEN="YOUR_TOKEN_HERE"

# Upload the pre-built driver and install
cd c:\Qlink
smartthings edge:drivers:package --upload vantage-bridge.zip --install
```

The CLI will:
1. Upload the driver
2. Prompt for channel (or create new one)
3. Assign driver to channel
4. Prompt for hub to install
5. Install the driver

#### Option 2: Rebuild and Upload

If you made code changes:

```bash
export SMARTTHINGS_TOKEN="YOUR_TOKEN_HERE"
cd c:\Qlink

# Build locally first (validates package)
smartthings edge:drivers:package --build-only vantage-bridge.zip SmartThings_Edge/vantage-bridge-driver

# Upload and install
smartthings edge:drivers:package --upload vantage-bridge.zip --install
```

#### Option 3: Manual Channel Management

```bash
export SMARTTHINGS_TOKEN="YOUR_TOKEN_HERE"

# 1. Upload driver (get driverId from output)
smartthings edge:drivers:package --upload vantage-bridge.zip

# 2. List or create channel
smartthings edge:channels
# OR create new:
smartthings edge:channels:create

# 3. Assign driver to channel
smartthings edge:channels:assign <channelId> <driverId>

# 4. Enroll hub to channel
smartthings edge:channels:enroll <channelId>

# 5. Install driver via SmartThings mobile app
```

### Add Bridge Device in SmartThings App

After driver is installed:

1. Open SmartThings app
2. Go to: **Devices** → **+** → **Add device** → **Scan nearby**
3. Select **"Vantage QLink Bridge"**
4. Configure settings:
   - **Bridge IP**: `qlinkpi.tail875b5a.ts.net` (or local IP `192.168.1.xxx`)
   - **Bridge Port**: `8000`
   - **Use HTTPS**: No

5. Wait for discovery to complete
6. Child devices will auto-create for all loads and stations

### Troubleshooting

#### Token Expired (24-hour limit)
Personal Access Tokens expire after 24 hours. When you get authentication errors:
1. Delete old token at https://account.smartthings.com/tokens
2. Create new token with same scopes
3. Update `SMARTTHINGS_TOKEN` environment variable
4. Retry upload

#### SmartThings API 500 Errors
If you get HTTP 500 errors, SmartThings API may be temporarily down. Wait and retry later.

#### Driver Not Appearing in App
1. Check hub enrolled in channel: `smartthings edge:channels:enrolled`
2. Check driver assigned: `smartthings edge:channels:drivers <channelId>`
3. Restart SmartThings hub (unplug 30 seconds)

#### Child Devices Not Creating
1. Check bridge IP/port configured correctly in device settings
2. Check bridge is accessible from SmartThings hub
3. Trigger manual refresh in app
4. Check SmartThings hub logs: `smartthings edge:drivers:logcat`

### Update Existing Installation

When making driver changes:

```bash
export SMARTTHINGS_TOKEN="YOUR_NEW_TOKEN"

# Rebuild package
smartthings edge:drivers:package --build-only vantage-bridge.zip SmartThings_Edge/vantage-bridge-driver

# Upload new version (overwrites existing)
smartthings edge:drivers:package --upload vantage-bridge.zip --channel <channelId>
```

SmartThings will automatically update installed drivers within ~24 hours, or you can force update:
1. SmartThings app → Hub → Driver → Update

### Bridge Configuration

Once installed, configure the parent device with:
- **Bridge Host**: IP or hostname of your Raspberry Pi
- **Bridge Port**: `8000` (default)
- **HTTPS**: Disabled (unless you configured SSL)

The driver will:
1. Auto-discover all loads from `/config` endpoint
2. Create child devices (dimmers, switches, button stations)
3. Poll status every 120 seconds
4. Support manual refresh anytime

### What Gets Created

The driver creates these device types:

**Parent Device**
- Vantage QLink Bridge (with refresh capability)

**Load Children** (auto-discovered from `/config`)
- Format: `{Room Name} - {Load Name}`
- Profile: Dimmer or Switch (based on load type)
- Capabilities: switch, switchLevel, refresh

**Station Children** (auto-discovered from `/config`)
- Format: `{Room Name} - Station V{number}`
- Profile: 8-button controller with LED feedback
- Capabilities: button (push/hold), switch (LED state)

### Developer Resources

- SmartThings CLI Docs: https://github.com/SmartThingsCommunity/smartthings-cli
- Edge Driver Docs: https://developer.smartthings.com/docs/devices/hub-connected/get-started
- API Reference: https://developer.smartthings.com/docs/api/public
- Driver Source: `SmartThings_Edge/vantage-bridge-driver/`

## Current Status

✅ Driver fully implemented and tested
✅ Package built successfully (`vantage-bridge.zip`)
⏳ Awaiting SmartThings API availability or fresh token for upload

**Next Step**: Generate fresh token and run deployment command above.
