"""Vantage QLink HTTP bridge (clean implementation).

Drop-in clean alternative to `app/bridge.py`. I couldn't safely overwrite the
existing `app/bridge.py` because it contains repeated/garbled content from
previous edits. I created this file as a single, audited implementation you can
swap in (or I can replace `app/bridge.py` for you if you want).

Endpoints:
- GET /about
- GET /config
- GET /healthz
- GET /send/{cmd}
- POST /device/{id}/set  (uses VLO for writes)

Serves a static UI from `app/static` at /ui when the directory exists.
"""

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional, Set, Dict
import os
import socket
import logging
import threading
import time
from datetime import datetime
from time import perf_counter

# Optional: jsonschema for config validation
try:
    from jsonschema import Draft202012Validator  # type: ignore
except Exception:
    Draft202012Validator = None  # type: ignore

try:
    from dotenv import load_dotenv

    load_dotenv()
except Exception:
    pass

app = FastAPI(title="Vantage QLink Bridge (fixed)")

# static UI mount
static_dir = os.path.join(os.path.dirname(__file__), "static")
if os.path.isdir(static_dir):
    app.mount("/ui", StaticFiles(directory=static_dir, html=True), name="ui")


def _env(name: str, default: str) -> str:
    v = os.getenv(name)
    return v if v not in (None, "") else default


VANTAGE_IP = _env("VANTAGE_IP", "192.168.1.200")
VANTAGE_PORT = int(_env("VANTAGE_PORT", "3040"))
QLINK_EOL = _env("Q_LINK_EOL", "CR").upper()
EOL = "\r\n" if QLINK_EOL == "CRLF" else "\r"
QLINK_TIMEOUT = float(_env("QLINK_TIMEOUT", "2.0"))
QLINK_FADE = _env("QLINK_FADE", "2.3")

logger = logging.getLogger("qlink")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

# ===== Event Monitoring Globals =====
event_socket: Optional[socket.socket] = None
event_socket_connected = False
event_monitoring_enabled = False
websocket_clients: Set[WebSocket] = set()
event_listener_thread: Optional[threading.Thread] = None

# ===== LED State Storage =====
# Track button LED states for all stations
# Format: {"V23": {1: "on", 2: "off", 3: "blink", ...}, "V20": {...}}
button_led_states: Dict[str, Dict[int, str]] = {}
button_led_lock = threading.Lock()  # Thread-safe access


def decode_led_hex(on_hex: str, blink_hex: str) -> Dict[int, str]:
    """Decode LED hex values to button states.

    Args:
        on_hex: Hex string for LEDs that are ON (e.g., "4C")
        blink_hex: Hex string for LEDs that are BLINKING (e.g., "20")

    Returns:
        Dict mapping button numbers (1-8) to states ("on", "off", "blink")

    Example:
        decode_led_hex("4C", "20") returns:
        {1: "off", 2: "off", 3: "on", 4: "on", 5: "off", 6: "blink", 7: "on", 8: "off"}

        4C hex = 01001100 binary = buttons 3, 4, 7
        20 hex = 00100000 binary = button 6
    """
    try:
        on_bits = int(on_hex, 16)
        blink_bits = int(blink_hex, 16)
    except ValueError:
        logger.warning(f"Invalid LED hex values: on={on_hex}, blink={blink_hex}")
        return {}

    states = {}
    for btn_num in range(1, 9):  # Buttons 1-8
        bit_mask = 1 << (btn_num - 1)  # Bit 0 = Button 1, Bit 7 = Button 8

        if blink_bits & bit_mask:
            states[btn_num] = "blink"
        elif on_bits & bit_mask:
            states[btn_num] = "on"
        else:
            states[btn_num] = "off"

    return states


def update_station_leds(station: int, button_states: Dict[int, str]):
    """Thread-safe update of station LED states."""
    station_id = f"V{station}"
    with button_led_lock:
        if station_id not in button_led_states:
            button_led_states[station_id] = {}
        button_led_states[station_id].update(button_states)


def parse_vantage_event(message: str) -> Optional[dict]:
    """Parse Vantage event messages (SW, LO, LS, LV, LE, LC)"""
    parts = message.strip().split()
    if not parts:
        return None

    event = {"raw": message, "timestamp": datetime.now().isoformat(), "type": "unknown"}

    try:
        # Button press/release: SW <master> <station> <button> <state> {<serial>}
        if parts[0] == "SW":
            event.update(
                {
                    "type": "button",
                    "master": int(parts[1]),
                    "station": int(parts[2]),
                    "button": int(parts[3]),
                    "state": "pressed" if parts[4] == "1" else "released",
                    "serial": parts[5] if len(parts) > 5 else None,
                }
            )
            logger.info(f"📍 Button V{parts[2]} btn {parts[3]} {event['state']}")

        # Module load change: LO <master> <enclosure> <module> <load> <level>
        elif parts[0] == "LO":
            event.update(
                {
                    "type": "load_module",
                    "master": int(parts[1]),
                    "enclosure": int(parts[2]),
                    "module": int(parts[3]),
                    "load": int(parts[4]),
                    "level": int(parts[5]),
                }
            )
            logger.info(
                f"💡 Load M{parts[1]}E{parts[2]}M{parts[3]}L{parts[4]} → {parts[5]}%"
            )

        # Station load change: LS <master> <station> <load> <level>
        elif parts[0] == "LS":
            event.update(
                {
                    "type": "load_station",
                    "master": int(parts[1]),
                    "station": int(parts[2]),
                    "load": int(parts[3]),
                    "level": int(parts[4]),
                }
            )
            logger.info(f"💡 Station V{parts[2]} load {parts[3]} → {parts[4]}%")

        # Variable load change: LV <master> <variable> <level>
        elif parts[0] == "LV":
            event.update(
                {
                    "type": "load_variable",
                    "master": int(parts[1]),
                    "variable": int(parts[2]),
                    "level": int(parts[3]),
                }
            )
            logger.info(f"💡 Variable {parts[2]} → {parts[3]}%")

        # LED state change (keypad): LE <master> <station> <onleds_hex> <blinkleds_hex>
        elif parts[0] == "LE":
            station_num = int(parts[2])
            on_leds_hex = parts[3]
            blink_leds_hex = parts[4]

            # Decode hex to button states
            button_states = decode_led_hex(on_leds_hex, blink_leds_hex)

            # Update global state store
            update_station_leds(station_num, button_states)

            event.update(
                {
                    "type": "led_keypad",
                    "master": int(parts[1]),
                    "station": station_num,
                    "station_id": f"V{station_num}",
                    "on_leds": on_leds_hex,
                    "blink_leds": blink_leds_hex,
                    "button_states": button_states,  # Include decoded states in event
                }
            )
            logger.info(
                f"🔆 LEDs V{station_num} on={on_leds_hex} blink={blink_leds_hex} {button_states}"
            )

        # LED state change (LCD): LC <master> <station> <button> <state>
        elif parts[0] == "LC":
            station_num = int(parts[2])
            button_num = int(parts[3])
            led_state = "on" if parts[4] == "1" else "off"

            # Update global state store (single button)
            update_station_leds(station_num, {button_num: led_state})

            event.update(
                {
                    "type": "led_lcd",
                    "master": int(parts[1]),
                    "station": station_num,
                    "station_id": f"V{station_num}",
                    "button": button_num,
                    "state": led_state,
                }
            )
            logger.info(f"🔆 LCD V{station_num} btn {button_num} LED {led_state}")

        # Response to our monitoring enable commands (ignore)
        elif parts[0] in ("ROD", "ROL", "ROS"):
            return None

        # Unknown event type
        else:
            logger.warning(f"⚠️  Unknown event: {message}")

        return event

    except (IndexError, ValueError) as e:
        logger.error(f"❌ Failed to parse event '{message}': {e}")
        return None


def broadcast_event_sync(event: dict):
    """Broadcast event to all connected WebSocket clients (synchronous)"""
    if not websocket_clients:
        return

    disconnected = set()
    for client in websocket_clients:
        try:
            # Use blocking send since we're in a thread
            import asyncio

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(client.send_json(event))
            loop.close()
        except Exception as e:
            logger.warning(f"WebSocket send failed: {e}")
            disconnected.add(client)

    # Remove disconnected clients
    for client in disconnected:
        websocket_clients.discard(client)


def led_polling_loop():
    """Background thread that polls LED states using VLT command (port 3040 mode).

    Since port 3040 doesn't support persistent event monitoring (VOD@/VOS@/VOL@),
    we poll all stations every 5-10 seconds using the VLT@ command.
    """
    global event_socket_connected, event_monitoring_enabled
    import json

    logger.info("🔄 LED polling thread started (port 3040 mode)")

    poll_interval = 5.0  # seconds between full polling cycles
    master = 1  # Assume single master system

    while True:
        try:
            # Load station list from loads.json
            stations = []
            config_paths = [
                os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
                "/home/pi/qlink-bridge/config/loads.json",
                "config/loads.json",
            ]

            for path in config_paths:
                if os.path.exists(path):
                    try:
                        with open(path, "r") as f:
                            data = json.load(f)

                            # Try new "rooms" array format first
                            if "rooms" in data and isinstance(data["rooms"], list):
                                for room in data["rooms"]:
                                    if "station" in room:
                                        station_num = room["station"]
                                        if station_num not in stations:
                                            stations.append(station_num)

                            # Fallback: try old "station_X" key format
                            else:
                                for key, value in data.items():
                                    if key.startswith("station_") and isinstance(value, dict):
                                        if "station" in value:
                                            station_num = value["station"]
                                            if station_num not in stations:
                                                stations.append(station_num)
                        break
                    except Exception as e:
                        logger.warning(f"Failed to load stations from {path}: {e}")
                        continue

            if not stations:
                logger.warning("⚠️  No stations configured in loads.json, will retry in 10s")
                event_socket_connected = False
                event_monitoring_enabled = False
                time.sleep(10)
                continue

            logger.info(f"📡 Polling {len(stations)} stations: {sorted(stations)}")
            event_socket_connected = True
            event_monitoring_enabled = True

            # Poll all stations
            polled_count = 0
            error_count = 0

            for station in sorted(stations):
                try:
                    # Query all LEDs for this station using VLT@
                    # Format: VLT@ <master> <station>
                    # Response: <onleds_hex> <blinkleds_hex>
                    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    sock.settimeout(2.0)
                    sock.connect((VANTAGE_IP, VANTAGE_PORT))
                    sock.sendall(f"VLT@ {master} {station}\r".encode("ascii"))
                    response = sock.recv(1024).decode("ascii", errors="ignore").strip()
                    sock.close()

                    # Parse response: "81 0" or "4C 20"
                    parts = response.split()
                    if len(parts) >= 2:
                        on_hex = parts[0]
                        blink_hex = parts[1]

                        # Decode using existing function
                        button_states = decode_led_hex(on_hex, blink_hex)

                        # Update global state
                        update_station_leds(station, button_states)

                        # Create event for WebSocket broadcast
                        event = {
                            "type": "led_poll",
                            "master": master,
                            "station": station,
                            "station_id": f"V{station}",
                            "on_leds": on_hex,
                            "blink_leds": blink_hex,
                            "button_states": button_states,
                            "timestamp": datetime.now().isoformat(),
                        }

                        # Broadcast to WebSocket clients
                        broadcast_event_sync(event)

                        polled_count += 1
                        logger.debug(f"📊 V{station}: on={on_hex} blink={blink_hex}")
                    else:
                        logger.warning(f"⚠️  V{station}: unexpected response '{response}'")
                        error_count += 1

                    # Small delay between stations to avoid overwhelming the system
                    time.sleep(0.05)

                except Exception as e:
                    logger.debug(f"Failed to poll V{station}: {e}")
                    error_count += 1
                    continue

            logger.info(f"✅ Poll cycle complete: {polled_count} stations, {error_count} errors")

            # Wait before next poll cycle
            time.sleep(poll_interval)

        except Exception as e:
            logger.error(f"❌ LED polling error: {e}")
            event_socket_connected = False
            event_monitoring_enabled = False
            time.sleep(5)


def start_event_listener():
    """Start the LED polling background thread (renamed for backwards compatibility)"""
    global event_listener_thread

    if event_listener_thread and event_listener_thread.is_alive():
        logger.info("LED polling thread already running")
        return

    event_listener_thread = threading.Thread(
        target=led_polling_loop, daemon=True, name="VantageLEDPoller"
    )
    event_listener_thread.start()
    logger.info("🚀 LED polling thread started")


def qlink_send(cmd: str, timeout: Optional[float] = None) -> str:
    """Send a single ASCII command to the Vantage IP-Enabler and return response.

    Raises HTTPException on connect/timeout errors so FastAPI returns proper status.
    Retries up to 3 times on connection refused (port may be busy with polling).
    """
    t0 = perf_counter()
    to = timeout or QLINK_TIMEOUT
    max_retries = 3
    retry_delay = 0.1  # 100ms between retries

    for attempt in range(max_retries):
        try:
            with socket.create_connection((VANTAGE_IP, VANTAGE_PORT), timeout=to) as s:
                s.sendall((cmd + EOL).encode("ascii", errors="ignore"))
                s.settimeout(to)
                try:
                    data = s.recv(4096)
                except socket.timeout:
                    data = b""

            dt = (perf_counter() - t0) * 1000
            logger.info("cmd=%s elapsedMs=%.1f attempt=%d", cmd, dt, attempt + 1)
            return data.decode("ascii", errors="ignore").strip()

        except socket.timeout as ex:
            raise HTTPException(
                status_code=504, detail="Timeout contacting Vantage IP-Enabler"
            ) from ex
        except OSError as ex:
            # Retry on connection refused (errno 111), fail immediately on other errors
            if "refused" in str(ex).lower() and attempt < max_retries - 1:
                logger.debug(f"Connection refused, retry {attempt + 1}/{max_retries}")
                time.sleep(retry_delay)
                continue
            raise HTTPException(status_code=502, detail=f"Connect error: {ex}") from ex

    # Should never reach here
    raise HTTPException(status_code=502, detail="Max retries exceeded")


class LevelCmd(BaseModel):
    level: Optional[int] = None
    switch: Optional[str] = None


@app.get("/about")
def about():
    return {"name": "qlink-bridge"}


@app.get("/config")
def get_config():
    """Return configuration including room/load definitions."""
    import json

    # Try to load rooms/loads configuration
    # First try relative path, then absolute paths
    config_paths = [
        os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "config", "loads.json"
        ),
        "/home/pi/qlink-bridge/config/loads.json",  # Pi absolute path
        "config/loads.json",  # CWD relative
    ]

    rooms = []
    config_file = None

    for path in config_paths:
        if os.path.exists(path):
            config_file = path
            break

    if config_file:
        try:
            with open(config_file, "r") as f:
                data = json.load(f)
                rooms = data.get("rooms", [])
                # Validate against JSON Schema if available and structure matches
                if rooms and Draft202012Validator is not None:
                    try:
                        schema_path = os.path.normpath(
                            os.path.join(
                                os.path.dirname(__file__),
                                "..",
                                "config",
                                "schemas",
                                "loads.rooms.v1.schema.json",
                            )
                        )
                        with open(schema_path, "r", encoding="utf-8") as sf:
                            schema = json.load(sf)
                        Draft202012Validator(schema).validate({"rooms": rooms})
                    except Exception as ve:
                        logger.warning(f"loads.json failed schema validation: {ve}")
        except Exception as e:
            logger.warning(f"Could not load loads.json: {e}")

    return {"ip": VANTAGE_IP, "port": VANTAGE_PORT, "fade": QLINK_FADE, "rooms": rooms}


@app.get("/healthz")
def health():
    return {"ok": True}


@app.get("/")
def root():
    """Redirect to home page."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/ui/")


@app.get("/send/{cmd}")
def send_raw(cmd: str):
    return {"command": cmd, "response": qlink_send(cmd)}


@app.post("/device/{id}/set")
def set_device(id: int, body: LevelCmd):
    # Use VLO@ command format (not VLO with fade)
    # Format: VLO@ {load_id} {level}
    if body.switch:
        if body.switch.lower() == "on":
            return {"resp": qlink_send(f"VLO@ {id} 100")}
        if body.switch.lower() == "off":
            return {"resp": qlink_send(f"VLO@ {id} 0")}
        raise HTTPException(400, "switch must be on/off")
    if body.level is not None:
        lvl = max(0, min(100, int(body.level)))
        return {"resp": qlink_send(f"VLO@ {id} {lvl}")}
    raise HTTPException(400, "provide switch or level")


@app.get("/load/{id}/status")
def get_load_status(id: int):
    """Get current level of a load (0-100) using VGL@ command"""
    return {"resp": qlink_send(f"VGL@ {id}")}


@app.get("/api/leds/{station}")
def get_station_leds(station: int):
    """Get LED states for all 8 buttons on a station using VLT@ command.

    Returns LED state for buttons 1-8 as array of integers (0=off, 255=on).
    Command format: VLT@ <master> <station>
    Response format: R:V 01 02 03 04 05 06 07 08 (hex values, 00=off, FF=on)
    """
    # Determine master based on station number
    # Stations 1-50 typically on master 1, 51+ on master 2
    master = 2 if station >= 51 else 1

    response = qlink_send(f"VLT@ {master} {station}")

    # Parse response: "R:V 01 02 03 04 05 06 07 08"
    if response.startswith("R:V"):
        parts = response.split()
        if len(parts) >= 9:  # R:V + 8 LED values
            led_values = parts[1:9]  # Skip "R:V", take next 8
            # Convert hex strings to integers (00 -> 0, FF -> 255)
            leds = []
            for val in led_values:
                try:
                    leds.append(int(val, 16))
                except ValueError:
                    leds.append(0)
            return {"station": station, "leds": leds, "raw": response}

    # Fallback if parsing fails
    return {"station": station, "leds": [0] * 8, "raw": response, "error": "Parse failed"}


@app.post("/button/{station}/{button}")
def press_button(station: int, button: int):
    """Simulate a button press on a station using VSW@ command.

    Uses VSW@ (Vantage Switch) command with state=4 for button press simulation.
    Format: VSW@ <master> <station> <button> <state>
    State 4 = Simulate button press
    State 6 = Simulate press and release (alternative)
    """
    # Determine master based on station number (consistent with LED query logic)
    # Stations 1-50 typically on master 1, 51+ on master 2
    master = 2 if station >= 51 else 1
    state = 4  # 4 = button press, 6 = press and release
    return {"resp": qlink_send(f"VSW@ {master} {station} {button} {state}")}


@app.get("/button/{station}/{button}/status")
def get_button_status(station: int, button: int):
    """Get LED status of a button - NOT YET IMPLEMENTED.

    This endpoint may not be needed. The VLED command doesn't appear in
    official Vantage documentation. Consider using VOD (Output on button press)
    command for monitoring button state changes instead.

    TODO: Review VOD command and determine if LED status querying is possible.
    """
    # Placeholder - command format unknown/may not exist
    raise HTTPException(
        status_code=501,
        detail="Button status query not yet implemented - VLED command not found in documentation",
    )


@app.get("/monitor/status")
def monitor_status():
    """Get LED polling status"""
    return {
        "mode": "polling",  # Port 3040 uses polling instead of event monitoring
        "polling_active": event_socket_connected,
        "monitoring_enabled": event_monitoring_enabled,
        "websocket_clients": len(websocket_clients),
        "vantage_ip": VANTAGE_IP,
        "vantage_port": VANTAGE_PORT,
        "stations_tracked": len(button_led_states),
        "note": "Using VLT polling (port 3040 mode) - LED states update every 5 seconds",
    }


@app.get("/api/leds")
def get_all_led_states():
    """Get current LED states for all stations.

    Returns:
        {
            "stations": {
                "V23": {1: "on", 2: "off", 3: "blink", ...},
                "V20": {...},
                ...
            },
            "count": 2
        }
    """
    with button_led_lock:
        return {"stations": button_led_states.copy(), "count": len(button_led_states)}


## NOTE: DUPLICATE ROUTE - This endpoint is shadowed by the one at line 569
## FastAPI will use the FIRST matching route, so this function is never called
## TODO: Remove this duplicate or consolidate the two endpoints
# @app.get("/api/leds/{station}")
# def get_station_led_states(station: int):
#     """Get current LED states for a specific station.
#
#     Args:
#         station: Station number (e.g., 23 for V23)
#
#     Returns:
#         {
#             "station": 23,
#             "station_id": "V23",
#             "buttons": {1: "on", 2: "off", 3: "blink", ...}
#         }
#     """
#     station_id = f"V{station}"
#     with button_led_lock:
#         buttons = button_led_states.get(station_id, {})
#
#     return {"station": station, "station_id": station_id, "buttons": buttons.copy()}


@app.get("/settings")
def get_settings():
    """Get current bridge settings"""
    return {
        "vantage_ip": VANTAGE_IP,
        "vantage_port": VANTAGE_PORT,
        "qlink_fade": QLINK_FADE,
        "qlink_timeout": QLINK_TIMEOUT,
        "qlink_eol": QLINK_EOL,
    }


@app.post("/settings")
def update_settings(settings: dict):
    """Update bridge settings (runtime only - not persisted)

    Note: Changes VANTAGE_IP or VANTAGE_PORT require bridge restart.
    QLINK_FADE and QLINK_TIMEOUT apply immediately.
    """
    global VANTAGE_IP, VANTAGE_PORT, QLINK_FADE, QLINK_TIMEOUT, QLINK_EOL, EOL

    updated = []
    restart_required = False

    if "vantage_ip" in settings:
        VANTAGE_IP = settings["vantage_ip"]
        updated.append("vantage_ip")
        restart_required = True

    if "vantage_port" in settings:
        VANTAGE_PORT = int(settings["vantage_port"])
        updated.append("vantage_port")
        restart_required = True

    if "qlink_fade" in settings:
        QLINK_FADE = str(settings["qlink_fade"])
        updated.append("qlink_fade")

    if "qlink_timeout" in settings:
        QLINK_TIMEOUT = float(settings["qlink_timeout"])
        updated.append("qlink_timeout")

    if "qlink_eol" in settings:
        new_eol = settings["qlink_eol"].upper()
        if new_eol in ("CR", "CRLF"):
            QLINK_EOL = new_eol
            EOL = "\r\n" if QLINK_EOL == "CRLF" else "\r"
            updated.append("qlink_eol")

    return {
        "status": "ok",
        "updated": updated,
        "restart_required": restart_required,
        "message": "Settings updated. Restart bridge for network changes to take effect."
        if restart_required
        else "Settings updated successfully.",
    }


@app.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time Vantage event streaming.

    Clients connect to ws://host:port/events and receive JSON events:
    - Button presses/releases (SW events)
    - Load changes (LO, LS, LV events)
    - LED state changes (LE, LC events)
    """
    await websocket.accept()
    websocket_clients.add(websocket)
    logger.info(f"✅ WebSocket client connected (total: {len(websocket_clients)})")

    # Send initial status
    try:
        await websocket.send_json(
            {
                "type": "status",
                "connected": event_socket_connected,
                "monitoring": event_monitoring_enabled,
                "timestamp": datetime.now().isoformat(),
            }
        )
    except:
        pass

    try:
        # Keep connection alive - just wait for client to disconnect
        while True:
            await websocket.receive_text()
    except WebSocketDisconnect:
        websocket_clients.discard(websocket)
        logger.info(
            f"❌ WebSocket client disconnected (total: {len(websocket_clients)})"
        )
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_clients.discard(websocket)


@app.on_event("startup")
async def startup_event():
    """Start event listener on application startup"""
    logger.info("🚀 Starting Vantage QLink Bridge...")
    # TEMPORARILY DISABLED: LED polling causes port exhaustion
    # This was breaking load control (on/off buttons)
    # start_event_listener()
    logger.info("✅ Bridge ready (LED polling disabled to prevent port exhaustion)")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code, content={"ok": False, "detail": exc.detail}
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "Internal Server Error", "detail": str(exc)},
    )
