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
from typing import Optional, Set
import os
import socket
import logging
import threading
import time
from datetime import datetime
from time import perf_counter

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


VANTAGE_IP = _env("VANTAGE_IP", "192.168.0.180")
VANTAGE_PORT = int(_env("VANTAGE_PORT", "3041"))
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
            event.update(
                {
                    "type": "led_keypad",
                    "master": int(parts[1]),
                    "station": int(parts[2]),
                    "on_leds": parts[3],
                    "blink_leds": parts[4],
                }
            )
            logger.info(f"🔆 LEDs V{parts[2]} on={parts[3]} blink={parts[4]}")

        # LED state change (LCD): LC <master> <station> <button> <state>
        elif parts[0] == "LC":
            event.update(
                {
                    "type": "led_lcd",
                    "master": int(parts[1]),
                    "station": int(parts[2]),
                    "button": int(parts[3]),
                    "state": "on" if parts[4] == "1" else "off",
                }
            )
            logger.info(f"🔆 LCD V{parts[2]} btn {parts[3]} LED {event['state']}")

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


def event_listener_loop():
    """Background thread that maintains persistent connection and listens for events"""
    global event_socket, event_socket_connected, event_monitoring_enabled

    logger.info("🎧 Event listener thread started")

    while True:
        try:
            logger.info(
                f"🔌 Connecting event listener to {VANTAGE_IP}:{VANTAGE_PORT}..."
            )

            # Create persistent socket
            event_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            event_socket.connect((VANTAGE_IP, VANTAGE_PORT))
            event_socket.settimeout(None)  # Blocking mode for persistent connection
            event_socket_connected = True

            logger.info("✅ Event listener connected")

            # Enable monitoring (settings persist, but good to send on each connect)
            logger.info("📡 Enabling Vantage event monitoring...")
            event_socket.send(b"VOS@ 1 1\r")  # Button monitoring with serial numbers
            time.sleep(0.1)
            event_socket.send(b"VOL@ 1\r")  # Load change monitoring
            time.sleep(0.1)
            event_socket.send(b"VOD@ 3\r")  # LED monitoring (all types)
            time.sleep(0.1)

            event_monitoring_enabled = True
            logger.info("✅ Event monitoring enabled (VOS@, VOL@, VOD@)")

            # Listen for events continuously
            buffer = ""
            while True:
                data = event_socket.recv(4096).decode("ascii", errors="ignore")

                if not data:
                    logger.warning("⚠️  Connection closed by Vantage")
                    raise ConnectionError("Socket closed by remote")

                buffer += data

                # Process complete messages (ending with \r)
                while "\r" in buffer:
                    message, buffer = buffer.split("\r", 1)
                    message = message.strip()

                    if message:
                        event = parse_vantage_event(message)
                        if event:
                            broadcast_event_sync(event)

        except Exception as e:
            logger.error(f"❌ Event listener error: {e}")
            event_socket_connected = False
            event_monitoring_enabled = False

            if event_socket:
                try:
                    event_socket.close()
                except:
                    pass
                event_socket = None

            logger.info("⏳ Reconnecting in 5 seconds...")
            time.sleep(5)


def start_event_listener():
    """Start the event listener background thread"""
    global event_listener_thread

    if event_listener_thread and event_listener_thread.is_alive():
        logger.info("Event listener already running")
        return

    event_listener_thread = threading.Thread(
        target=event_listener_loop, daemon=True, name="VantageEventListener"
    )
    event_listener_thread.start()
    logger.info("🚀 Event listener thread started")


def qlink_send(cmd: str, timeout: Optional[float] = None) -> str:
    """Send a single ASCII command to the Vantage IP-Enabler and return response.

    Raises HTTPException on connect/timeout errors so FastAPI returns proper status.
    """
    t0 = perf_counter()
    to = timeout or QLINK_TIMEOUT
    try:
        with socket.create_connection((VANTAGE_IP, VANTAGE_PORT), timeout=to) as s:
            s.sendall((cmd + EOL).encode("ascii", errors="ignore"))
            s.settimeout(to)
            try:
                data = s.recv(4096)
            except socket.timeout:
                data = b""
    except socket.timeout as ex:
        raise HTTPException(
            status_code=504, detail="Timeout contacting Vantage IP-Enabler"
        ) from ex
    except OSError as ex:
        raise HTTPException(status_code=502, detail=f"Connect error: {ex}") from ex
    finally:
        dt = (perf_counter() - t0) * 1000
        logger.info("cmd=%s elapsedMs=%.1f", cmd, dt)
    return data.decode("ascii", errors="ignore").strip()


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

    return RedirectResponse(url="/ui/home.html")


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


@app.post("/button/{station}/{button}")
def press_button(station: int, button: int):
    """Simulate a button press on a station using VSW@ command.

    Uses VSW@ (Vantage Switch) command with state=4 for button press simulation.
    Format: VSW@ <master> <station> <button> <state>
    State 4 = Simulate button press
    State 6 = Simulate press and release (alternative)
    """
    # Assuming master=1 for single-master system (or lookup based on station if multi-master)
    master = 1
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
    """Get event monitoring status"""
    return {
        "event_listener_connected": event_socket_connected,
        "monitoring_enabled": event_monitoring_enabled,
        "websocket_clients": len(websocket_clients),
        "vantage_ip": VANTAGE_IP,
        "vantage_port": VANTAGE_PORT,
    }


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
    start_event_listener()
    logger.info("✅ Bridge ready")


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
