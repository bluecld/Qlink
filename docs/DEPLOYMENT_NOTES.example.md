## Vantage Bridge Progress

### 2025-11-03 - SmartThings Driver & SSDP Integration

**Driver Status:**
- Built and uploaded driver version `2025-11-03T20:06:28.680894576`
- Channel: *My Vantage Bridge Channel*
- Driver ID: `0dd7f90d-9d6b-46e3-8d1f-6c46b7d2a11f`
- Hub ID: `92e0cdbe-81a5-49c6-91a5-45f31204b21b`
- Hub IP: `192.168.1.155`
- Bridge IP: `192.168.1.227:8000`

**Problem Identified:**
- Parent device not being created automatically
- Root cause: SmartThings LAN discovery requires SSDP/UPnP or manual device addition
- The driver's `fingerprints.yml` declares a LAN device but there was no network discovery mechanism

**Solution Implemented:**
1. **SSDP Advertiser** (`app/ssdp_advertiser.py`):
   - Broadcasts SSDP NOTIFY messages every 30 seconds to multicast `239.255.255.250:1900`
   - Listens for M-SEARCH requests and responds with device location
   - Properly handles startup/shutdown with "alive" and "byebye" notifications

2. **Bridge Integration** (`app/bridge.py`):
   - Auto-starts SSDP on FastAPI startup
   - Gracefully stops SSDP on shutdown
   - Enhanced `/about` endpoint with device metadata (manufacturer, model, etc.)

3. **Testing Tool** (`test_ssdp.py`):
   - Standalone SSDP test script
   - Useful for debugging network discovery issues

4. **Documentation** (`SmartThings_Edge/DEVICE_ADDITION_GUIDE.md`):
   - Complete troubleshooting guide
   - Covers both automatic (SSDP) and manual device addition
   - Step-by-step instructions for configuration

**Next Steps:**
1. **Restart bridge** with SSDP enabled:
   ```bash
   cd /path/to/Qlink
   python3 -m uvicorn app.bridge:app --host 0.0.0.0 --port 8000
   ```

2. **Test SSDP** (optional):
   ```bash
   python3 test_ssdp.py
   # In another terminal:
   sudo tcpdump -i any -n port 1900
   ```

3. **Add device in SmartThings app**:
   - Open SmartThings app
   - Devices → + → Scan for nearby devices
   - Look for "Vantage QLink Bridge"
   - Configure bridge IP: `192.168.1.227`, port: `8000`

4. **Verify child device creation**:
   - After configuring bridge preferences, child devices should auto-create
   - Check for loads (dimmers/switches) and stations (button controllers)

**Alternative (if SSDP doesn't work):**
- SmartThings Edge may require manual device addition flow
- See DEVICE_ADDITION_GUIDE.md section "Manual Device Addition"
- Consider removing LAN discovery requirement from driver

---

### 2025-11-06 - Home Assistant + HomeKit + Siri Integration

**Objective:**
Enable Siri voice control for Vantage Q-Link lights using Home Assistant and Apple HomeKit Bridge.

**System Configuration:**
- **Platform**: Raspberry Pi (192.168.1.213) - same Pi running bridge.py and NAS backup
- **Home Assistant**: Docker container (ghcr.io/home-assistant/home-assistant:stable)
- **Container Name**: homeassistant
- **Web UI**: http://192.168.1.213:8123
- **Architecture**: Siri → Apple Home → HomeKit Bridge → HA → RESTful → bridge.py → Q-Link → Vantage

**Key Discovery:**
- Native Home Assistant Vantage integrations (loopj/home-assistant-vantage, gjbadros/hass-vantage) ONLY support InFusion protocol
- Q-Link protocol (pre-2011) is incompatible with modern HA Vantage integrations
- Solution: Use HA's RESTful integration to consume existing bridge.py REST API

**Implementation:**

1. **Docker Installation**:
   - Installed Docker CE on Raspberry Pi
   - Created Home Assistant container with host networking
   - Mounted config directory: `/home/pi/homeassistant:/config`
   - Container restart policy: unless-stopped

2. **Configuration** (`/home/pi/homeassistant/configuration.yaml`):
   - **REST Commands**: Control lights via POST to bridge.py
     - `vantage_light_on`: Accepts load_id and brightness (0-255, converted to 0-100)
     - `vantage_light_off`: Turns off specified load_id

   - **REST Sensors**: Poll light status every 30 seconds
     - Queries `/load/{id}/status` endpoint
     - Returns brightness 0-100 as integer state

   - **Template Lights**: 6 lights configured as proof of concept
     - Master Bedroom Main (load 254)
     - Master Bedroom Reading Left (load 241)
     - Master Bedroom Reading Right (load 240)
     - Kitchen Main (load 141)
     - Kitchen Under Cabinet (load 144)
     - Living Room Main (load 122)

   - **HomeKit Bridge**: Exposes all light entities to Apple HomeKit
     - Filters to include only light domain
     - Custom friendly names for Siri recognition

3. **Technical Challenges Resolved**:
   - **Template Errors**: Fixed brightness attribute mapping (resp vs brightness)
   - **Type Conversion**: Added proper int() casting with defaults in Jinja2 templates
   - **JSON Attributes**: Simplified sensor configuration to avoid json_attributes issues
   - **Brightness Scaling**: Proper conversion between HA (0-255) and Vantage (0-100) scales

**Current Status:**
- Home Assistant running and accessible at http://192.168.1.213:8123
- All 6 lights configured and integrated with HomeKit Bridge
- HomeKit storage files created (`.storage/homekit.*`)
- Configuration validated with no errors in logs

**Next Steps (for user):**
1. Access HA UI at http://192.168.1.213:8123
2. Navigate to Settings → Devices & Services
3. Find HomeKit Bridge integration card
4. Copy pairing code (8-digit PIN) or QR code
5. Open Apple Home app on iPhone
6. Add accessory using code or QR scan
7. Accept "Uncertified Accessory" warning
8. Assign lights to rooms
9. Test Siri commands:
   - "Hey Siri, turn on Master Bedroom Lights"
   - "Hey Siri, set Kitchen Lights to 50%"
   - "Hey Siri, turn off Living Room Lights"

**Documentation:**
- Complete setup guide: `HOME_ASSISTANT_SETUP.md`
- Includes architecture overview, configuration details, troubleshooting, and maintenance procedures
- Instructions for adding additional lights (100+ available loads)

**Resource Management:**
- HA runs alongside existing bridge.py (port 8000) and NAS backup (2 AM daily)
- No resource conflicts expected - NAS backup is once daily with minimal files
- Docker container uses host networking for optimal performance

**Expandability:**
- Current implementation covers 6 lights as proof of concept
- Bridge.py exposes 100+ Vantage loads
- Easy to add more lights by editing configuration.yaml
- Template pattern established for replication
