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

import asyncio
import json
import logging
import os
import random
import secrets
import socket
import threading
import time
from datetime import datetime
from queue import Empty, Queue
from time import perf_counter
from typing import Any, Dict, Optional, Set, cast

from fastapi import (
    Depends,
    FastAPI,
    HTTPException,
    Request,
    WebSocket,
    WebSocketDisconnect,
)
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

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
    # Ensure we always return a str (never None) - use cast to convince mypy
    if v is None or v == "":
        return default
    return cast(str, v)


VANTAGE_IP = _env("VANTAGE_IP", "192.168.1.200")
VANTAGE_PORT = int(_env("VANTAGE_PORT", "3040"))
QLINK_EOL = _env("QLINK_EOL", _env("Q_LINK_EOL", "CR")).upper()
EOL = "\r\n" if QLINK_EOL == "CRLF" else "\r"
QLINK_TIMEOUT = float(_env("QLINK_TIMEOUT", "3.0"))
QLINK_FADE = _env("QLINK_FADE", "2.3")
QLINK_MONITOR_MODE = _env("QLINK_MONITOR_MODE", "poll").strip().lower()
if QLINK_MONITOR_MODE not in {"poll", "events", "off", "auto"}:
    QLINK_MONITOR_MODE = "poll"
QLINK_DISABLE_EVENTS = _env("QLINK_DISABLE_EVENTS", "0").lower() in (
    "1",
    "true",
    "yes",
    "on",
)
QLINK_LED_POLL_INTERVAL = float(_env("QLINK_LED_POLL_INTERVAL", "7.5"))
# TTL (seconds) for on-demand LED cache when in 'auto' mode (default 5s)
QLINK_LED_CACHE_TTL = float(_env("QLINK_LED_CACHE_TTL", "5.0"))
# Retry/backoff tuning (configurable via env or runtime /settings)
QLINK_MAX_RETRIES = int(_env("QLINK_MAX_RETRIES", "3"))
QLINK_RETRY_BASE_SEC = float(_env("QLINK_RETRY_BASE_SEC", "0.1"))
QLINK_COMMAND_GAP = float(_env("QLINK_COMMAND_GAP", "0.05"))
BRIDGE_API_SECRET = _env("BRIDGE_API_SECRET", "")

_DEFAULT_CONFIG_DIR = os.path.normpath(
    os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config")
)
# When deployed on the Pi the working tree is typically /home/pi/qlink-bridge
# prefer that path if present and writable so persisted settings survive
_DEPLOYED_CONFIG_DIR = "/home/pi/qlink-bridge/config"

if os.path.isdir(_DEPLOYED_CONFIG_DIR) and os.access(_DEPLOYED_CONFIG_DIR, os.W_OK):
    CONFIG_DIR = _DEPLOYED_CONFIG_DIR
else:
    CONFIG_DIR = _DEFAULT_CONFIG_DIR

PERSISTED_SETTINGS_FILE = os.path.join(CONFIG_DIR, "bridge_settings.json")


def _load_persisted_settings() -> None:
    """Load persisted bridge settings (vantage_ip, vantage_port, etc.) if present.

    This overrides the environment-derived defaults so runtime POST /settings
    changes can be made persistent by writing this file.
    """
    global VANTAGE_IP, VANTAGE_PORT, QLINK_TIMEOUT, QLINK_FADE, QLINK_EOL, EOL
    global QLINK_MAX_RETRIES, QLINK_RETRY_BASE_SEC, BRIDGE_API_SECRET

    try:
        if os.path.exists(PERSISTED_SETTINGS_FILE):
            with open(PERSISTED_SETTINGS_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "vantage_ip" in data:
                VANTAGE_IP = data["vantage_ip"]
            if "vantage_port" in data:
                try:
                    VANTAGE_PORT = int(data["vantage_port"])
                except Exception:
                    # logger may not be configured yet at import time
                    print("Invalid persisted vantage_port, ignoring")
            if "qlink_timeout" in data:
                try:
                    QLINK_TIMEOUT = float(data["qlink_timeout"])
                except Exception:
                    print("Invalid persisted qlink_timeout, ignoring")
            if "qlink_max_retries" in data:
                try:
                    QLINK_MAX_RETRIES = int(data["qlink_max_retries"])
                except Exception:
                    print("Invalid persisted qlink_max_retries, ignoring")
            if "qlink_retry_base_sec" in data:
                try:
                    QLINK_RETRY_BASE_SEC = float(data["qlink_retry_base_sec"])
                except Exception:
                    print("Invalid persisted qlink_retry_base_sec, ignoring")
            if "qlink_fade" in data:
                QLINK_FADE = str(data["qlink_fade"])
            if "qlink_eol" in data:
                new_eol = data["qlink_eol"].upper()
                if new_eol in ("CR", "CRLF"):
                    QLINK_EOL = new_eol
                    EOL = "\r\n" if QLINK_EOL == "CRLF" else "\r"
            if "bridge_api_secret" in data:
                BRIDGE_API_SECRET = str(data["bridge_api_secret"])
            try:
                logger.info(
                    f"Loaded persisted bridge settings from {PERSISTED_SETTINGS_FILE}"
                )
            except Exception:
                pass
    except Exception as e:
        try:
            logger.warning(f"Failed to load persisted bridge settings: {e}")
        except Exception:
            print(f"Failed to load persisted bridge settings: {e}")


def _persist_settings(settings: dict) -> None:
    """Write selected settings to the persisted settings file.

    Only a small set of keys are saved (vantage_ip, vantage_port, qlink_timeout,
    qlink_fade, qlink_eol, bridge_api_secret). Errors are non-fatal and logged.
    """
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        to_save = {}
        for k in (
            "vantage_ip",
            "vantage_port",
            "qlink_timeout",
            "qlink_fade",
            "qlink_eol",
            "qlink_max_retries",
            "qlink_retry_base_sec",
            "bridge_api_secret",
        ):
            if k in settings:
                to_save[k] = settings[k]

        # Read existing and merge so we don't clobber other settings unexpectedly
        if os.path.exists(PERSISTED_SETTINGS_FILE):
            try:
                with open(PERSISTED_SETTINGS_FILE, "r", encoding="utf-8") as f:
                    existing = json.load(f)
                    existing.update(to_save)
                    to_save = existing
            except Exception:
                pass

        with open(PERSISTED_SETTINGS_FILE, "w", encoding="utf-8") as f:
            json.dump(to_save, f, indent=2)
        try:
            logger.info(f"Persisted bridge settings to {PERSISTED_SETTINGS_FILE}")
        except Exception:
            pass
    except Exception as e:
        try:
            logger.warning(f"Failed to persist bridge settings: {e}")
        except Exception:
            print(f"Failed to persist bridge settings: {e}")


# Load persisted settings (if any) to override defaults
_load_persisted_settings()

logger = logging.getLogger("qlink")

# SSDP Advertiser for SmartThings LAN discovery
try:
    from app.ssdp_advertiser import SSDPAdvertiser, get_local_ip

    SSDP_ENABLED = True
except ImportError:
    try:
        # Try alternative import path (when running from app directory)
        import os
        import sys

        sys.path.insert(0, os.path.dirname(__file__))
        from ssdp_advertiser import SSDPAdvertiser, get_local_ip  # type: ignore

        SSDP_ENABLED = True
    except ImportError:
        logger.warning("ssdp_advertiser.py not found - SSDP discovery disabled")
        SSDP_ENABLED = False
        SSDPAdvertiser = None  # type: ignore
        get_local_ip = None  # type: ignore

ssdp_advertiser: Optional[Any] = None
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())

# ===== Event Monitoring Globals =====
event_socket: Optional[socket.socket] = None
event_socket_connected = False
event_monitoring_enabled = False
active_monitor_mode = "off"
websocket_clients: Set[WebSocket] = set()

EVENT_ENABLE_COMMANDS = ("VOS 1", "VOD 1", "VOL 1")
monitor_thread: Optional[threading.Thread] = None
# Lock to serialize access to the Vantage IP-Enabler to avoid port exhaustion
qlink_io_lock = threading.Lock()


class CommandRequest:
    __slots__ = ("cmd", "timeout", "response_queue")

    def __init__(self, cmd: str, timeout: float, response_queue: "Queue[Any]") -> None:
        self.cmd = cmd
        self.timeout = timeout
        self.response_queue = response_queue


command_queue: "Queue[CommandRequest]" = Queue()
command_worker_thread: Optional[threading.Thread] = None
command_metrics_lock = threading.Lock()
command_metrics: Dict[str, Any] = {
    "queue_depth": 0,
    "queue_peak": 0,
    "last_rtt_ms": 0.0,
    "last_command": None,
    "last_error": None,
    "total_commands": 0,
}


def _update_metric(key: str, value: Any) -> None:
    with command_metrics_lock:
        command_metrics[key] = value


def _increment_metric(key: str, amount: int = 1) -> None:
    with command_metrics_lock:
        command_metrics[key] = command_metrics.get(key, 0) + amount


def _set_queue_depth(depth: int) -> None:
    with command_metrics_lock:
        command_metrics["queue_depth"] = depth
        if depth > command_metrics.get("queue_peak", 0):
            command_metrics["queue_peak"] = depth


def _perform_qlink_send(cmd: str, timeout: float) -> str:
    t0 = perf_counter()
    max_retries = QLINK_MAX_RETRIES

    for attempt in range(max_retries):
        try:
            with qlink_io_lock:
                with socket.create_connection(
                    (VANTAGE_IP, VANTAGE_PORT), timeout=timeout
                ) as s:
                    s.sendall((cmd + EOL).encode("ascii", errors="ignore"))
                    s.settimeout(timeout)
                    try:
                        data = s.recv(4096)
                    except socket.timeout:
                        data = b""

            dt = (perf_counter() - t0) * 1000
            logger.info("cmd=%s elapsedMs=%.1f attempt=%d", cmd, dt, attempt + 1)
            _update_metric("last_rtt_ms", dt)
            _update_metric("last_command", datetime.now().isoformat())
            return data.decode("ascii", errors="ignore").strip()

        except socket.timeout as ex:
            raise HTTPException(
                status_code=504, detail="Timeout contacting Vantage IP-Enabler"
            ) from ex
        except OSError as ex:
            if "refused" in str(ex).lower() and attempt < max_retries - 1:
                base = QLINK_RETRY_BASE_SEC
                delay = base * (2**attempt)
                jitter = random.uniform(0, delay * 0.5)
                sleep_for = delay + jitter
                logger.debug(
                    "Connection refused, retry %d/%d - sleeping %.3fs",
                    attempt + 1,
                    max_retries,
                    sleep_for,
                )
                time.sleep(sleep_for)
                continue
            raise HTTPException(status_code=502, detail=f"Connect error: {ex}") from ex

    raise HTTPException(status_code=502, detail="Max retries exceeded")


def _command_worker() -> None:
    while True:
        try:
            request: CommandRequest = command_queue.get()
            if request is None:  # pragma: no cover - allow graceful shutdown if needed
                break
            start_time = perf_counter()
            try:
                result = _perform_qlink_send(request.cmd, request.timeout)
                request.response_queue.put(("ok", result))
                _increment_metric("total_commands", 1)
                _update_metric("last_rtt_ms", (perf_counter() - start_time) * 1000)
                _update_metric("last_error", None)
            except HTTPException as exc:
                _update_metric("last_error", exc.detail)
                request.response_queue.put(("error", exc))
            except Exception as exc:  # pragma: no cover - defensive
                _update_metric("last_error", str(exc))
                request.response_queue.put(
                    ("error", HTTPException(status_code=500, detail=str(exc)))
                )
            finally:
                _set_queue_depth(command_queue.qsize())
                time.sleep(max(QLINK_COMMAND_GAP, 0.0))
        except Exception as worker_exc:  # pragma: no cover - defensive
            logger.exception("Command worker loop exception: %s", worker_exc)
            time.sleep(0.5)


def _ensure_command_worker() -> None:
    global command_worker_thread
    if command_worker_thread and command_worker_thread.is_alive():
        return
    command_worker_thread = threading.Thread(
        target=_command_worker, daemon=True, name="VantageCommandWorker"
    )
    command_worker_thread.start()


def _extract_secret_value(source: Any) -> str:
    if not source:
        return ""
    value = str(source).strip()
    return value


def _get_request_secret(request: Request) -> str:
    token = request.headers.get("x-bridge-secret") or request.query_params.get("token")
    if not token:
        auth_header = request.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    return _extract_secret_value(token)


def require_api_secret(request: Request) -> None:
    if not BRIDGE_API_SECRET:
        return
    provided = _get_request_secret(request)
    # Ensure both strings are non-empty before comparison
    if not provided:
        raise HTTPException(status_code=401, detail="Unauthorized: Missing API secret")
    # Use constant-time comparison to prevent timing attacks
    if not secrets.compare_digest(provided, BRIDGE_API_SECRET):
        raise HTTPException(status_code=401, detail="Unauthorized: Invalid API secret")


API_DEPENDENCIES = [Depends(require_api_secret)]


def _authorize_websocket(websocket: WebSocket) -> bool:
    if not BRIDGE_API_SECRET:
        return True
    token = websocket.headers.get("x-bridge-secret") or websocket.query_params.get(
        "token"
    )
    if not token:
        auth_header = websocket.headers.get("authorization")
        if auth_header and auth_header.lower().startswith("bearer "):
            token = auth_header[7:]
    token = _extract_secret_value(token)
    return bool(token) and secrets.compare_digest(token, BRIDGE_API_SECRET)


event_loop: Optional[asyncio.AbstractEventLoop] = None

# ===== LED State Storage =====
# Track button LED states for all stations
# Format: {"V23": {1: "on", 2: "off", 3: "blink", ...}, "V20": {...}}
button_led_states: Dict[str, Dict[int, str]] = {}
button_led_lock = threading.Lock()  # Thread-safe access

# ===== Loads Cache (for aggregated REST endpoint) =====
loads_cache: Dict[int, int] = {}
loads_cache_ts: Optional[float] = None
loads_cache_lock = threading.Lock()
LOADS_CACHE_TTL = float(_env("LOADS_CACHE_TTL", "30.0"))  # seconds (default 30s)

# ===== Loads Subset Caches (for distributed REST endpoints) =====
# Split 136 loads into 4 smaller sets to avoid timeouts
# Set 1: loads 0-33, Set 2: loads 34-67, Set 3: loads 68-101, Set 4: loads 102-135
loads_subset_caches: Dict[int, Dict[int, int]] = {1: {}, 2: {}, 3: {}, 4: {}}
loads_subset_ts: Dict[int, Optional[float]] = {1: None, 2: None, 3: None, 4: None}
loads_subset_locks: Dict[int, threading.Lock] = {
    1: threading.Lock(),
    2: threading.Lock(),
    3: threading.Lock(),
    4: threading.Lock(),
}
LOADS_SUBSET_TTL = float(_env("LOADS_SUBSET_TTL", "60.0"))  # seconds (default 60s)

# ===== LED cache (for on-demand /api/leds refresh in 'auto' mode) =====
leds_cache_ts: Optional[float] = None
leds_refresh_lock = threading.Lock()
# Event used to gracefully stop monitoring thread when requested (auto mode stop)
monitor_thread_stop_event = threading.Event()

# ===== Station to Master Mapping =====
# Load actual station-to-master assignments from Vantage config
# DO NOT GUESS based on station number - read from config file!
STATION_MASTER_MAP: Dict[int, int] = {}
STATION_PHYSICAL_MAP: Dict[int, int] = {}


def load_station_master_map():
    """Load station-to-master mapping from config file."""
    global STATION_MASTER_MAP
    candidate_paths = [
        os.path.join(
            os.path.dirname(__file__), "..", "config", "station_master_map.json"
        ),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "config",
            "station_master_map.json",
        ),
        "/home/pi/qlink-bridge/config/station_master_map.json",
        "config/station_master_map.json",
    ]

    loaded = False
    for map_file in candidate_paths:
        try:
            if os.path.exists(map_file):
                with open(map_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    STATION_MASTER_MAP = {int(k): int(v) for k, v in data.items()}
                logger.info(
                    f"✅ Loaded {len(STATION_MASTER_MAP)} station-to-master mappings from {map_file}"
                )
                loaded = True
                break
        except Exception as e:
            logger.warning(f"Failed to load station master map from {map_file}: {e}")
            continue
    if not loaded:
        logger.warning("❌ Station master map not found in any known path")
        logger.warning("⚠️  Will fall back to guessing (station >= 51 → master 2)")


def load_station_physical_map():
    """Load virtual-to-physical station number mapping from config file.

    IMPORTANT: Vantage has both virtual (V-numbers) and physical station numbers:
    - VLT@ commands use virtual station numbers (e.g., V55)
    - VSW commands use physical station numbers (e.g., 6 for V55)

    This mapping is extracted from the Vantage config file field:
    Station: V{virtual},{?},{master},{physical},...
    """
    global STATION_PHYSICAL_MAP
    candidate_paths = [
        os.path.join(
            os.path.dirname(__file__), "..", "config", "station_physical_map.json"
        ),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "..",
            "config",
            "station_physical_map.json",
        ),
        "/home/pi/qlink-bridge/config/station_physical_map.json",
        "config/station_physical_map.json",
    ]

    loaded = False
    for map_file in candidate_paths:
        try:
            if os.path.exists(map_file):
                with open(map_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    STATION_PHYSICAL_MAP = {int(k): int(v) for k, v in data.items()}
                logger.info(
                    f"✅ Loaded {len(STATION_PHYSICAL_MAP)} virtual-to-physical station mappings from {map_file}"
                )
                loaded = True
                break
        except Exception as e:
            logger.warning(f"Failed to load station physical map from {map_file}: {e}")
            continue
    if not loaded:
        logger.warning("❌ Station physical map not found in any known path")
        logger.warning(
            "⚠️  VSW commands may not work - will use virtual station numbers as fallback"
        )


def get_station_physical(station_virtual: int) -> int:
    """Get the physical station number for a virtual station number.

    Args:
        station_virtual: Virtual station number (e.g., 55)

    Returns:
        Physical station number (e.g., 6 for V55)
    """
    if station_virtual in STATION_PHYSICAL_MAP:
        return STATION_PHYSICAL_MAP[station_virtual]
    else:
        # FALLBACK - assume virtual = physical (often wrong!)
        logger.warning(
            f"⚠️  Virtual station {station_virtual} not in physical map, using as-is"
        )
        return station_virtual


def get_station_master(station: int) -> int:
    """Get the master controller for a station number.

    Args:
        station: Station number (e.g., 19, 55)

    Returns:
        Master number (1 or 2)

    Note:
        If mapping not found, falls back to guess (station >= 51 → master 2)
        This is WRONG for many stations (23, 46-50, 53-58 are mixed!)
    """
    if station in STATION_MASTER_MAP:
        return STATION_MASTER_MAP[station]
    else:
        # FALLBACK - this is often wrong!
        logger.warning(f"⚠️  Station {station} not in map, guessing master")
        return 2 if station >= 51 else 1


# Load mappings on startup
load_station_master_map()
load_station_physical_map()


def reconcile_station_maps() -> None:
    """Ensure station maps cover all stations referenced in loads.json.

    Fills in missing entries to prevent noisy fallback warnings during runtime.
    - Master map: chooses 1/2 using existing heuristic (>=51 → 2) when absent.
    - Physical map: defaults to virtual==physical when absent.
    """
    try:
        stations: Set[int] = set()
        config_paths = [
            os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
            "/home/pi/qlink-bridge/config/loads.json",
            "config/loads.json",
        ]

        for path in config_paths:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "rooms" in data and isinstance(data["rooms"], list):
                    for room in data["rooms"]:
                        candidate = normalize_station_id(room.get("station"))
                        if candidate is not None:
                            stations.add(candidate)
                else:
                    for key, value in data.items():
                        if key.startswith("station_") and isinstance(value, dict):
                            candidate = normalize_station_id(value.get("station"))
                            if candidate is not None:
                                stations.add(candidate)
                break

        if not stations:
            return

        added_master = 0
        added_physical = 0
        for st in stations:
            if st not in STATION_MASTER_MAP:
                STATION_MASTER_MAP[st] = 2 if st >= 51 else 1
                added_master += 1
            if st not in STATION_PHYSICAL_MAP:
                STATION_PHYSICAL_MAP[st] = st
                added_physical += 1

        if added_master or added_physical:
            logger.info(
                f"🔧 Reconciled station maps: +{added_master} master, +{added_physical} physical"
            )
    except Exception as e:
        logger.debug(f"reconcile_station_maps skipped: {e}")


# Reconcile maps so runtime avoids guessy warnings for known stations
reconcile_station_maps()


def normalize_station_id(value: Any) -> Optional[int]:
    """Normalize station identifiers pulled from config into integers."""
    if value is None:
        return None
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        # Narrow type for mypy
        assert isinstance(value, str)
        stripped: str = value.strip()
        if stripped.isdigit():
            return int(stripped)
        return None
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


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
    if len(parts) == 1 and parts[0] in {"0", "1"}:
        return None

    # Use a flexible typing for the event dictionary since values may be int/str/None
    event: Dict[str, Any] = {
        "raw": message,
        "timestamp": datetime.now().isoformat(),
        "type": "unknown",
    }

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


async def _broadcast_event(event: dict):
    """Broadcast an event to all connected WebSocket clients on the main loop."""
    if not websocket_clients:
        return

    disconnected: Set[WebSocket] = set()
    for client in tuple(websocket_clients):
        try:
            await client.send_json(event)
        except Exception as exc:
            logger.warning(f"WebSocket send failed: {exc}")
            disconnected.add(client)

    for client in disconnected:
        websocket_clients.discard(client)


def schedule_broadcast(event: dict):
    """Schedule an event broadcast on the main asyncio loop."""
    loop = event_loop
    if not loop or not loop.is_running():
        logger.debug("Skipping broadcast; event loop not ready")
        return

    try:
        running_loop = asyncio.get_running_loop()
    except RuntimeError:
        asyncio.run_coroutine_threadsafe(_broadcast_event(event), loop)
        return

    if running_loop is loop:
        running_loop.create_task(_broadcast_event(event))
    else:
        asyncio.run_coroutine_threadsafe(_broadcast_event(event), loop)


def _line_delimiter() -> bytes:
    """Return the expected line delimiter for Vantage responses."""
    return b"\r\n" if EOL == "\r\n" else b"\r"


def _consume_buffer_lines(buffer: bytearray, delimiter: bytes):
    """Yield complete lines decoded from the shared buffer."""
    while True:
        idx = buffer.find(delimiter)
        if idx == -1:
            break

        line_bytes = bytes(buffer[:idx])
        del buffer[: idx + len(delimiter)]

        # Responses may include CRLF even when delimiter is CR; trim stray LF.
        if delimiter == b"\r" and buffer.startswith(b"\n"):
            del buffer[0]

        line = line_bytes.decode("ascii", errors="ignore").strip()
        if line:
            yield line


def _readline_from_socket(
    sock: socket.socket, buffer: bytearray, delimiter: bytes
) -> Optional[str]:
    """Read a single line from the socket using an existing buffer."""
    while True:
        for line in _consume_buffer_lines(buffer, delimiter):
            return line

        try:
            chunk = sock.recv(4096)
        except socket.timeout:
            return None

        if not chunk:
            return None

        buffer.extend(chunk)


def _handle_event_line(line: str) -> None:
    """Parse a single raw line and broadcast any resulting event."""
    event = parse_vantage_event(line)
    if event:
        schedule_broadcast(event)


def event_listener_loop():
    """Long-lived event monitoring loop using VOS/VOD/VOL stream."""
    global \
        event_socket, \
        event_socket_connected, \
        event_monitoring_enabled, \
        active_monitor_mode

    delimiter = _line_delimiter()
    backoff = 1.0

    while True:
        if QLINK_DISABLE_EVENTS:
            logger.info("Event listener disabled via QLINK_DISABLE_EVENTS")
            active_monitor_mode = "off"
            return

        try:
            logger.info(
                "Connecting to Vantage event stream at %s:%s", VANTAGE_IP, VANTAGE_PORT
            )
            sock = socket.create_connection(
                (VANTAGE_IP, VANTAGE_PORT), timeout=QLINK_TIMEOUT
            )
            event_socket = sock
            event_socket_connected = True

            buffer = bytearray()
            sock.settimeout(QLINK_TIMEOUT)

            for cmd in EVENT_ENABLE_COMMANDS:
                payload = (cmd + EOL).encode("ascii", errors="ignore")
                sock.sendall(payload)
                ack = _readline_from_socket(sock, buffer, delimiter)
                if ack is None:
                    raise RuntimeError(f"No acknowledgement enabling {cmd}")

            event_monitoring_enabled = True
            active_monitor_mode = "events"
            logger.info("Event monitoring enabled via VOS/VOD/VOL")

            sock.settimeout(None)
            backoff = 1.0

            # Drain any buffered lines from the handshake before blocking reads.
            for line in _consume_buffer_lines(buffer, delimiter):
                _handle_event_line(line)

            while True:
                chunk = sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Event socket closed by remote host")

                buffer.extend(chunk)
                for line in _consume_buffer_lines(buffer, delimiter):
                    _handle_event_line(line)

        except Exception as exc:
            logger.warning(f"Event listener error: {exc}")
        finally:
            if event_socket:
                try:
                    event_socket.close()
                except Exception:
                    pass
            event_socket = None
            event_socket_connected = False
            event_monitoring_enabled = False
            active_monitor_mode = "off"

        sleep_for = min(backoff, 30.0)
        jitter = random.uniform(0.0, sleep_for * 0.25)
        time.sleep(sleep_for + jitter)
        backoff = min(backoff * 2, 30.0)


def led_polling_loop():
    """Background thread that polls LED states using VLT command in a throttled manner."""
    global event_monitoring_enabled, event_socket_connected, active_monitor_mode, leds_cache_ts
    import json

    logger.info("🔄 LED polling thread started (safe mode)")
    poll_interval = max(1.0, QLINK_LED_POLL_INTERVAL)

    # Clear stop event at start
    monitor_thread_stop_event.clear()

    while not monitor_thread_stop_event.is_set():
        try:
            # Load station list from config (rooms-based or legacy format)
            stations: Set[int] = set()
            config_paths = [
                os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
                "/home/pi/qlink-bridge/config/loads.json",
                "config/loads.json",
            ]

            for path in config_paths:
                if os.path.exists(path):
                    try:
                        with open(path, "r", encoding="utf-8") as f:
                            data = json.load(f)
                        if "rooms" in data and isinstance(data["rooms"], list):
                            for room in data["rooms"]:
                                candidate = normalize_station_id(room.get("station"))
                                if candidate is not None:
                                    stations.add(candidate)
                        else:
                            for key, value in data.items():
                                if key.startswith("station_") and isinstance(
                                    value, dict
                                ):
                                    candidate = normalize_station_id(
                                        value.get("station")
                                    )
                                    if candidate is not None:
                                        stations.add(candidate)
                        break
                    except Exception as e:  # pragma: no cover - best effort
                        logger.warning(f"Failed to load stations from {path}: {e}")
                        continue

            if not stations:
                logger.warning(
                    "⚠️  No stations configured in loads.json, will retry in 10s"
                )
                active_monitor_mode = "off"
                event_monitoring_enabled = False
                event_socket_connected = False
                time.sleep(10.0)
                continue

            active_monitor_mode = "poll"
            event_monitoring_enabled = True
            event_socket_connected = False

            logger.debug(
                f"Polling stations (interval {poll_interval}s): {sorted(stations)}"
            )

            polled_count = 0
            error_count = 0

            for station in sorted(stations):
                if monitor_thread_stop_event.is_set():
                    break
                master = get_station_master(station)
                try:
                    response = qlink_send(f"VLT@ {master} {station}")
                except HTTPException as exc:  # pragma: no cover - depends on hardware
                    logger.debug(f"V{station}: VLT@ failed ({exc.detail})")
                    error_count += 1
                    continue
                except Exception as exc:  # pragma: no cover - depends on hardware
                    logger.debug(f"V{station}: VLT@ error {exc}")
                    error_count += 1
                    continue

                parts = response.split()
                on_hex: Optional[str] = None
                blink_hex: Optional[str] = None
                if parts:
                    head = parts[0].upper()
                    if head == "RLT" and len(parts) >= 5:
                        on_hex = parts[-2]
                        blink_hex = parts[-1]
                    elif len(parts) >= 2:
                        on_hex = parts[0]
                        blink_hex = parts[1]

                if on_hex is None or blink_hex is None:
                    logger.debug(f"V{station}: unexpected response '{response}'")
                    error_count += 1
                    time.sleep(0.05)
                    continue

                button_states = decode_led_hex(on_hex, blink_hex)
                update_station_leds(station, button_states)

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
                schedule_broadcast(event)

                polled_count += 1
                time.sleep(0.05)

            logger.debug(
                "Poll cycle complete: %s stations, %s errors", polled_count, error_count
            )

            # Update LED cache timestamp to indicate fresh data
            leds_cache_ts = perf_counter()

            # Wait for next cycle or until stopped
            for _ in range(int(max(1, poll_interval))):
                if monitor_thread_stop_event.is_set():
                    break
                time.sleep(1.0)

        except Exception as exc:  # pragma: no cover - defensive
            logger.error(f"❌ LED polling error: {exc}")
            active_monitor_mode = "off"
            event_monitoring_enabled = False
            event_socket_connected = False
            time.sleep(5.0)

    logger.info("🛑 LED polling thread stopped")


def start_polling_thread():
    """Start the LED polling thread if not already running."""
    global monitor_thread, active_monitor_mode, event_monitoring_enabled
    if monitor_thread and monitor_thread.is_alive():
        return
    # Clear any previous stop signal
    monitor_thread_stop_event.clear()
    target = led_polling_loop
    name = "VantageLEDPoller"
    logger.info(
        "🚀 Starting LED polling thread (mode=poll, interval %.1fs)",
        QLINK_LED_POLL_INTERVAL,
    )
    monitor_thread = threading.Thread(target=target, daemon=True, name=name)
    monitor_thread.start()
    active_monitor_mode = "poll"
    event_monitoring_enabled = True


def stop_polling_thread():
    """Stop the LED polling thread if running (used by auto mode)."""
    global monitor_thread, active_monitor_mode, event_monitoring_enabled, event_socket_connected
    try:
        monitor_thread_stop_event.set()
        if monitor_thread and monitor_thread.is_alive():
            monitor_thread.join(timeout=3.0)
    except Exception:
        pass
    monitor_thread = None
    active_monitor_mode = "off"
    event_monitoring_enabled = False
    event_socket_connected = False


def start_monitoring():
    """Start the monitoring thread based on configured mode."""
    global monitor_thread, active_monitor_mode

    if QLINK_MONITOR_MODE == "off":
        logger.info("Monitoring disabled via QLINK_MONITOR_MODE=off")
        active_monitor_mode = "off"
        return

    if monitor_thread and monitor_thread.is_alive():
        logger.info("Monitoring thread already running")
        return

    if QLINK_MONITOR_MODE == "events":
        if QLINK_DISABLE_EVENTS:
            logger.info(
                "Event monitoring disabled via QLINK_DISABLE_EVENTS; not starting thread"
            )
            active_monitor_mode = "off"
            return
        target = event_listener_loop
        name = "VantageEventListener"
        logger.info("🚀 Starting event listener thread (mode=events)")
        active_monitor_mode = "events"
        monitor_thread = threading.Thread(target=target, daemon=True, name=name)
        monitor_thread.start()
    elif QLINK_MONITOR_MODE == "auto":
        # Auto mode: do not start polling at startup; polling will begin when
        # a WebSocket client connects or when an on-demand request forces it.
        logger.info("Auto monitoring enabled; polling will start on client connect or on-demand")
        active_monitor_mode = "off"
        return
    else:
        # Legacy 'poll' mode - start polling immediately
        start_polling_thread()
        active_monitor_mode = "poll"


def qlink_send(cmd: str, timeout: Optional[float] = None) -> str:
    """Enqueue a command to the Vantage IP-Enabler and return its response."""
    _ensure_command_worker()
    to = timeout or QLINK_TIMEOUT
    response_queue: Queue[Any] = Queue(maxsize=1)
    command_queue.put(
        CommandRequest(cmd=cmd, timeout=to, response_queue=response_queue)
    )
    _set_queue_depth(command_queue.qsize())
    try:
        status, payload = response_queue.get(timeout=to + QLINK_TIMEOUT + 2)
    except Empty:
        _update_metric("last_error", "Command queue timeout")
        raise HTTPException(status_code=504, detail="Command queue timeout") from None

    if status == "error":
        if isinstance(payload, HTTPException):
            raise payload
        raise HTTPException(status_code=500, detail=str(payload))

    return cast(str, payload)


class LevelCmd(BaseModel):
    level: Optional[int] = None
    switch: Optional[str] = None


@app.get("/about", dependencies=API_DEPENDENCIES)
def about():
    """Return bridge information for SSDP/SmartThings discovery."""
    return {
        "name": "qlink-bridge",
        "version": "1.0",
        "manufacturer": "Vantage",
        "model": "QLinkBridge",
        "device_type": "urn:schemas-upnp-org:device:Basic:1",
        "friendly_name": "Vantage QLink Bridge",
    }


@app.get("/config", dependencies=API_DEPENDENCIES)
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

    # Provide a small manifest-like config for tests and tooling
    return {
        "name": "qlink-bridge",
        "version": "0.1",
        "timeout": QLINK_TIMEOUT,
        "ip": VANTAGE_IP,
        "port": VANTAGE_PORT,
        "fade": QLINK_FADE,
        "rooms": rooms,
    }


@app.get("/healthz", dependencies=API_DEPENDENCIES)
def health():
    return {"ok": True}


def _get_load_list() -> list:
    """Return a list of load dicts from loads.json similar to /config's rooms parse.

    This mirrors the parsing in `get_config` but returns the flat list of loads with ids.
    """
    config_paths = [
        os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "config", "loads.json"
        ),
        "/home/pi/qlink-bridge/config/loads.json",
        "config/loads.json",
    ]

    for path in config_paths:
        try:
            if os.path.exists(path):
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                if "rooms" in data and isinstance(data["rooms"], list):
                    loads = []
                    for room in data["rooms"]:
                        for ld in room.get("loads", []):
                            loads.append(ld)
                    return loads
                else:
                    # legacy loads/ station based structure
                    loads = []
                    for key, val in data.items():
                        if key.startswith("load_") and isinstance(val, dict):
                            loads.append(val)
                    return loads
        except Exception:
            continue
    return []


@app.get("/")
def root():
    """Redirect to home page."""
    from fastapi.responses import RedirectResponse

    return RedirectResponse(url="/ui/")


@app.get("/send/{cmd}", dependencies=API_DEPENDENCIES)
def send_raw(cmd: str):
    return {"command": cmd, "response": qlink_send(cmd)}


@app.post("/device/{id}/set", dependencies=API_DEPENDENCIES)
def set_device(id: int, body: LevelCmd):
    # Use VLO@ command format (not VLO with fade)
    # Format: VLO@ {load_id} {level}
    logger.info(f"set_device called: id={id} body={body}")

    try:
        if body.switch:
            if body.switch.lower() == "on":
                cmd = f"VLO@ {id} 100"
                resp = qlink_send(cmd)
                logger.info(f"set_device: cmd={cmd} resp={resp}")
                return {"resp": resp}
            if body.switch.lower() == "off":
                cmd = f"VLO@ {id} 0"
                resp = qlink_send(cmd)
                logger.info(f"set_device: cmd={cmd} resp={resp}")
                return {"resp": resp}
            raise HTTPException(400, "switch must be on/off")

        if body.level is not None:
            lvl = max(0, min(100, int(body.level)))
            cmd = f"VLO@ {id} {lvl}"
            resp = qlink_send(cmd)
            logger.info(f"set_device: cmd={cmd} resp={resp}")
            return {"resp": resp}

        raise HTTPException(400, "provide switch or level")
    except HTTPException:
        # Re-raise HTTPExceptions from qlink_send to preserve proper status codes
        raise
    except Exception as e:
        logger.exception(f"set_device failed for id={id}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/load/{id}/status", dependencies=API_DEPENDENCIES)
def get_load_status(id: int):
    """Get current level of a load (0-100) using VGL@ command"""
    try:
        response = qlink_send(f"VGL@ {id}")
        return {"resp": response}
    except HTTPException:
        # Re-raise HTTPExceptions from qlink_send to preserve proper status codes
        raise
    except Exception as e:
        logger.exception(f"get_load_status failed for load {id}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get load status: {str(e)}"
        )


def _update_loads_cache() -> None:
    """Query configured loads and cache the current levels (0-100) with TTL.

    This function attempts to update the in-memory map loads_cache in a thread-safe way.
    It catches exceptions to avoid crashing the service if the Vantage controller is slow.
    """
    global loads_cache, loads_cache_ts
    try:
        loads = _get_load_list()
        newmap: Dict[int, int] = {}
        for ld in loads:
            lid = ld.get("id")
            if lid is None:
                continue
            try:
                resp = qlink_send(f"VGL@ {int(lid)}")
                # Try parse final integer or fallback to 0
                val = 0
                try:
                    val = int(str(resp).strip().split()[-1])
                except Exception:
                    try:
                        val = int(str(resp).strip())
                    except Exception:
                        val = 0
                newmap[int(lid)] = max(0, min(100, val))
            except Exception:
                # Don't fail the entire update for a single load read error
                newmap[int(lid)] = loads_cache.get(int(lid), 0)

        with loads_cache_lock:
            loads_cache = newmap
            loads_cache_ts = perf_counter()
    except Exception as e:
        logger.exception(f"Failed to update loads cache: {e}")


@app.get("/api/leds/{station}", dependencies=API_DEPENDENCIES)
def get_station_leds(station: int):
    """Get LED states for all 8 buttons on a station using VLT@ command.

    Returns LED state for buttons 1-8 as array of integers (0=off, 255=on).
    Command format: VLT@ <master> <station>
    Response format: R:V 01 02 03 04 05 06 07 08 (hex values, 00=off, FF=on)
    """
    try:
        # Get actual master from Vantage config mapping
        master = get_station_master(station)

        response = qlink_send(f"VLT@ {master} {station}")
    except HTTPException:
        # Re-raise HTTPExceptions from qlink_send
        raise
    except Exception as e:
        logger.exception(f"get_station_leds failed for station {station}: {e}")
        raise HTTPException(
            status_code=500, detail=f"Failed to get LED status: {str(e)}"
        )

    parts = response.split()
    on_hex: Optional[str] = None
    blink_hex: Optional[str] = None

    if parts:
        head = parts[0].upper()
        if head == "RLT" and len(parts) >= 5:
            # Detailed response: RLT <master> <station> <onleds> <blinkleds>
            on_hex = parts[-2]
            blink_hex = parts[-1]
        elif len(parts) >= 2:
            # Regular response: <onleds> <blinkleds>
            on_hex = parts[0]
            blink_hex = parts[1]

    if on_hex is not None and blink_hex is not None:
        button_states = decode_led_hex(on_hex, blink_hex)
        update_station_leds(station, button_states)

        leds = []
        for btn in range(1, 9):
            state = button_states.get(btn, "off")
            if state == "on":
                leds.append(255)
            elif state == "blink":
                leds.append(128)
            else:
                leds.append(0)

        return {
            "station": station,
            "station_id": f"V{station}",
            "leds": leds,
            "button_states": button_states,
            "on_leds": on_hex,
            "blink_leds": blink_hex,
            "raw": response,
        }

    # Fallback if parsing fails
    return {
        "station": station,
        "station_id": f"V{station}",
        "leds": [0] * 8,
        "raw": response,
        "error": "Parse failed",
    }


@app.post("/button/{station}/{button}", dependencies=API_DEPENDENCIES)
def press_button(station: int, button: int, behavior: Optional[str] = None):
    """Simulate a button press on a station using VSW command.

    IMPORTANT: VSW requires PHYSICAL station numbers, not virtual (V-numbers)!
    - Input station parameter is VIRTUAL number (e.g., 55)
    - We convert to PHYSICAL number (e.g., 6) for the VSW command
    - VLT@ uses virtual numbers, but VSW uses physical numbers

    Format: VSW <master> <physical_station> <button> <state>

    State values (from QLINK2.rtf):
    - 6 = Execute switch emulating a press and release (works for all button types)

    Args:
        station: VIRTUAL station number (e.g., 55 for V55)
        button: Button number (1-10)
        behavior: Optional button behavior (not currently used, always uses state 6)
    """
    # Get actual master and physical station from Vantage config mappings
    master = get_station_master(station)
    station_physical = get_station_physical(station)

    # Use state 6 for ALL button types - emulates physical press and release
    # State 6 triggers whatever function the button is programmed for:
    # - PRESET_ON buttons will execute their ON function
    # - PRESET_OFF buttons will execute their OFF function
    # - DIM/TOGGLE buttons will toggle
    state = 6

    logger.info(
        f"Button press: virtual={station}, physical={station_physical}, button={button}, master={master}, state={state}"
    )
    return {"resp": qlink_send(f"VSW {master} {station_physical} {button} {state}")}


@app.get("/button/{station}/{button}/status", dependencies=API_DEPENDENCIES)
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


@app.get("/monitor/status", dependencies=API_DEPENDENCIES)
def monitor_status():
    """Get LED polling status"""
    mode = active_monitor_mode
    if mode == "events":
        note = "Using VOS/VOD/VOL event stream for live updates"
    elif mode == "poll":
        note = f"Polling LED states every {QLINK_LED_POLL_INTERVAL:.1f}s via VLT@"
    else:
        note = "Monitoring disabled"
    return {
        "mode": mode,
        "configured_mode": QLINK_MONITOR_MODE,
        "polling_active": mode == "poll" and event_monitoring_enabled,
        "event_socket_connected": event_socket_connected,
        "monitoring_enabled": event_monitoring_enabled,
        "websocket_clients": len(websocket_clients),
        "vantage_ip": VANTAGE_IP,
        "vantage_port": VANTAGE_PORT,
        "stations_tracked": len(button_led_states),
        "note": note,
        "command_queue_depth": command_metrics.get("queue_depth", 0),
        "command_queue_peak": command_metrics.get("queue_peak", 0),
        "last_command_rtt_ms": command_metrics.get("last_rtt_ms"),
        "last_command_at": command_metrics.get("last_command"),
        "last_command_error": command_metrics.get("last_error"),
        "total_commands_sent": command_metrics.get("total_commands", 0),
        "command_worker_alive": (
            command_worker_thread.is_alive() if command_worker_thread else False
        ),
        "command_gap_seconds": QLINK_COMMAND_GAP,
    }


def _refresh_led_cache_once() -> None:
    """Perform a single (synchronous) LED polling pass for all configured stations.

    This is used by the on-demand `/api/leds` endpoint when `force=true` or the
    cache has expired. It is throttled and uses the same VLT@ logic but only runs
    one cycle to avoid long-running background polling.
    """
    global leds_cache_ts

    # Prevent concurrent refreshes
    if not leds_refresh_lock.acquire(blocking=False):
        # Another refresh is in progress
        return
    try:
        # Load stations (reuse logic from led_polling_loop)
        stations: Set[int] = set()
        candidate_paths = [
            os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
            "/home/pi/qlink-bridge/config/loads.json",
            "config/loads.json",
        ]
        for path in candidate_paths:
            if os.path.exists(path):
                try:
                    with open(path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if "rooms" in data and isinstance(data["rooms"], list):
                        for room in data["rooms"]:
                            candidate = normalize_station_id(room.get("station"))
                            if candidate is not None:
                                stations.add(candidate)
                    else:
                        for key, value in data.items():
                            if key.startswith("station_") and isinstance(value, dict):
                                candidate = normalize_station_id(value.get("station"))
                                if candidate is not None:
                                    stations.add(candidate)
                    break
                except Exception:
                    continue
        if not stations:
            return

        for station in sorted(stations):
            try:
                master = get_station_master(station)
                response = qlink_send(f"VLT@ {master} {station}")
            except Exception:
                time.sleep(0.05)
                continue

            parts = response.split()
            on_hex: Optional[str] = None
            blink_hex: Optional[str] = None
            if parts:
                head = parts[0].upper()
                if head == "RLT" and len(parts) >= 5:
                    on_hex = parts[-2]
                    blink_hex = parts[-1]
                elif len(parts) >= 2:
                    on_hex = parts[0]
                    blink_hex = parts[1]

            if on_hex is None or blink_hex is None:
                time.sleep(0.05)
                continue

            button_states = decode_led_hex(on_hex, blink_hex)
            update_station_leds(station, button_states)
            # Throttle slightly to avoid overwhelming the controller
            time.sleep(max(QLINK_COMMAND_GAP, 0.03))

        leds_cache_ts = perf_counter()
    finally:
        try:
            leds_refresh_lock.release()
        except Exception:
            pass


@app.get("/api/leds", dependencies=API_DEPENDENCIES)
def get_all_led_states(force: bool = False):
    """Get current LED states for all stations.

    If `force=true` is provided, the bridge will perform a synchronous refresh
    pass to fetch fresh LED states (useful for Home Assistant on-demand scans).
    """
    global leds_cache_ts

    now = perf_counter()
    cache_expired = leds_cache_ts is None or (now - (leds_cache_ts or 0.0)) > QLINK_LED_CACHE_TTL
    if force or cache_expired:
        try:
            _refresh_led_cache_once()
        except Exception as e:
            logger.warning(f"On-demand LED refresh failed: {e}")

    with button_led_lock:
        return {"stations": button_led_states.copy(), "count": len(button_led_states)}


@app.get("/api/loads", dependencies=API_DEPENDENCIES)
def get_all_loads(force: bool = False):
    """Return aggregated load levels for all configured loads.

    The result looks like:
    {"loads": {"254": 0, "241": 100}, "count": 2}
    """
    global loads_cache, loads_cache_ts
    now = perf_counter()
    # If force requested or cache expired, update
    if (
        force
        or loads_cache_ts is None
        or (now - (loads_cache_ts or 0.0)) > LOADS_CACHE_TTL
    ):
        # Defensive: prefer calling the helper but fall back to inline computation
        # if the helper isn't present at runtime (e.g., old deployed code mismatch).
        try:
            _update_loads_cache()
        except NameError:
            logger.warning(
                "_update_loads_cache not available at runtime, computing loads inline as fallback"
            )
            # Inline fallback avoids repeating the whole function definition
            loads = _get_load_list()
            newmap: Dict[int, int] = {}
            for ld in loads:
                lid = ld.get("id")
                if lid is None:
                    continue
                try:
                    resp = qlink_send(f"VGL@ {int(lid)}")
                    val = 0
                    try:
                        val = int(str(resp).strip().split()[-1])
                    except Exception:
                        try:
                            val = int(str(resp).strip())
                        except Exception:
                            val = 0
                    newmap[int(lid)] = max(0, min(100, val))
                except Exception:
                    newmap[int(lid)] = loads_cache.get(int(lid), 0)
            with loads_cache_lock:
                loads_cache = newmap
                loads_cache_ts = perf_counter()
    with loads_cache_lock:
        return {"loads": loads_cache.copy(), "count": len(loads_cache)}


def _get_loads_subset(subset_num: int) -> Dict[int, int]:
    """Get a subset of loads by querying only loads in that subset's range.

    Subsets are divided to avoid timeout:
    - Subset 1: loads 0-33 (approx 34 loads)
    - Subset 2: loads 34-67 (approx 34 loads)
    - Subset 3: loads 68-101 (approx 34 loads)
    - Subset 4: loads 102-135 (approx 34 loads)

    Each subset takes ~3-5 seconds to query, well under the 30s HA timeout.
    """
    if subset_num not in (1, 2, 3, 4):
        return {}

    global loads_subset_caches, loads_subset_ts

    now = perf_counter()
    lock = loads_subset_locks[subset_num]

    # Check if cache is still valid
    if (
        loads_subset_ts[subset_num] is not None
        and (now - loads_subset_ts[subset_num]) < LOADS_SUBSET_TTL
    ):
        with lock:
            return loads_subset_caches[subset_num].copy()

    # Determine load range for this subset
    # Assuming 136 total loads (0-135), split into 4 groups
    range_size = 34  # 136 / 4 = 34 per subset
    start_idx = (subset_num - 1) * range_size
    end_idx = (
        start_idx + range_size if subset_num < 4 else 136
    )  # Last set gets remainder

    # Query only loads in this subset by index
    all_loads = _get_load_list()
    subset_loads = [
        ld
        for i, ld in enumerate(all_loads)
        if i >= start_idx and i < end_idx and ld.get("id") is not None
    ]

    newmap: Dict[int, int] = {}
    for ld in subset_loads:
        lid = int(ld.get("id", -1))
        if lid < 0:
            continue
        try:
            resp = qlink_send(f"VGL@ {lid}")
            val = 0
            try:
                val = int(str(resp).strip().split()[-1])
            except Exception:
                try:
                    val = int(str(resp).strip())
                except Exception:
                    val = 0
            newmap[lid] = max(0, min(100, val))
        except Exception:
            # Use cached value if query fails
            with lock:
                newmap[lid] = loads_subset_caches[subset_num].get(lid, 0)

    # Update cache
    with lock:
        loads_subset_caches[subset_num] = newmap
        loads_subset_ts[subset_num] = perf_counter()

    return newmap.copy()


@app.get("/api/loads/set1", dependencies=API_DEPENDENCIES)
def get_loads_set_1():
    """Get loads subset 1 (faster queries, avoids timeout)."""
    return {
        "loads": _get_loads_subset(1),
        "subset": 1,
        "count": len(_get_loads_subset(1)),
    }


@app.get("/api/loads/set2", dependencies=API_DEPENDENCIES)
def get_loads_set_2():
    """Get loads subset 2 (faster queries, avoids timeout)."""
    return {
        "loads": _get_loads_subset(2),
        "subset": 2,
        "count": len(_get_loads_subset(2)),
    }


@app.get("/api/loads/set3", dependencies=API_DEPENDENCIES)
def get_loads_set_3():
    """Get loads subset 3 (faster queries, avoids timeout)."""
    return {
        "loads": _get_loads_subset(3),
        "subset": 3,
        "count": len(_get_loads_subset(3)),
    }


@app.get("/api/loads/set4", dependencies=API_DEPENDENCIES)
def get_loads_set_4():
    """Get loads subset 4 (faster queries, avoids timeout)."""
    return {
        "loads": _get_loads_subset(4),
        "subset": 4,
        "count": len(_get_loads_subset(4)),
    }


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


@app.get("/settings", dependencies=API_DEPENDENCIES)
def get_settings():
    """Get current bridge settings"""
    return {
        "vantage_ip": VANTAGE_IP,
        "vantage_port": VANTAGE_PORT,
        "qlink_fade": QLINK_FADE,
        "qlink_timeout": QLINK_TIMEOUT,
        "qlink_eol": QLINK_EOL,
        "qlink_max_retries": QLINK_MAX_RETRIES,
        "qlink_retry_base_sec": QLINK_RETRY_BASE_SEC,
        "api_secret_set": bool(BRIDGE_API_SECRET),
    }


@app.get("/manifest", dependencies=API_DEPENDENCIES)
def manifest():
    """Return a small manifest describing the bridge endpoints for UI consumption/tests."""
    endpoints = [
        {"path": "/about", "method": "GET"},
        {"path": "/config", "method": "GET"},
        {"path": "/settings", "method": "GET"},
        {"path": "/probe", "method": "GET"},
    ]
    return {"name": "qlink-bridge", "endpoints": endpoints}


@app.get("/debug/ui-mapping", dependencies=API_DEPENDENCIES)
def debug_ui_mapping():
    """Return a mapping of rooms, stations and loads to the DOM id patterns

    This endpoint helps the UI developer verify which DOM ids the frontend
    will attempt to update for a given `config/loads.json` file. It returns
    a structure like:

    {
      "rooms": [
        {
          "name": "Living Room",
          "roomId": "living-room",
          "stations": [23],
          "loads": [101, 102],
          "buttonIds": ["scene-living-room-23-1", "scene-living-room-1"]
        }
      ]
    }
    """
    # Reuse the same config loading logic as /config
    config_paths = [
        os.path.join(os.path.dirname(__file__), "..", "config", "loads.json"),
        os.path.join(
            os.path.dirname(os.path.abspath(__file__)), "..", "config", "loads.json"
        ),
        "/home/pi/qlink-bridge/config/loads.json",
        "config/loads.json",
    ]

    rooms = []
    config_file = None
    for path in config_paths:
        if os.path.exists(path):
            config_file = path
            break

    if config_file:
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                rooms = data.get("rooms", [])
        except Exception as e:
            logger.warning(f"Could not load loads.json for ui-mapping: {e}")

    result = {"rooms": []}
    for room in rooms:
        name = room.get("name") or ""
        room_id = name.replace(" ", "-").lower()
        stations = []
        if "station" in room and room.get("station") is not None:
            try:
                stations.append(int(room.get("station")))
            except Exception:
                pass

        if "stations" in room and isinstance(room.get("stations"), list):
            for s in room.get("stations"):
                try:
                    # s may be a dict with 'station' key or a raw number
                    if isinstance(s, dict):
                        val = s.get("station")
                    else:
                        val = s
                    # Only append if we have a non-None value that can be converted
                    if val is None:
                        continue
                    stations.append(int(val))
                except Exception:
                    continue

        loads = [
            item.get("id")
            for item in room.get("loads", [])
            if isinstance(item, dict) and item.get("id") is not None
        ]

        # Build a sample of button DOM ids the UI would use
        button_ids = []
        # Legacy ids: scene-<roomId>-<btn>
        # Station-specific ids: scene-<roomId>-<station>-<btn>
        for st in stations:
            for btn in range(1, 9):
                button_ids.append(f"scene-{room_id}-{st}-{btn}")
        for btn in range(1, 9):
            button_ids.append(f"scene-{room_id}-{btn}")

        result["rooms"].append(
            {
                "name": name,
                "roomId": room_id,
                "stations": stations,
                "loads": loads,
                "buttonIdsSample": button_ids[:20],
            }
        )

    return result


@app.post("/settings", dependencies=API_DEPENDENCIES)
def update_settings(settings: dict):
    """Update bridge settings."""

    global BRIDGE_API_SECRET
    global VANTAGE_IP, VANTAGE_PORT, QLINK_FADE, QLINK_TIMEOUT, QLINK_EOL, EOL
    global QLINK_MAX_RETRIES, QLINK_RETRY_BASE_SEC

    updated: list[str] = []
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

    if "qlink_max_retries" in settings:
        try:
            QLINK_MAX_RETRIES = int(settings["qlink_max_retries"])
            updated.append("qlink_max_retries")
        except Exception:
            raise HTTPException(
                status_code=400, detail="qlink_max_retries must be integer"
            )

    if "qlink_retry_base_sec" in settings:
        try:
            QLINK_RETRY_BASE_SEC = float(settings["qlink_retry_base_sec"])
            updated.append("qlink_retry_base_sec")
        except Exception:
            raise HTTPException(
                status_code=400, detail="qlink_retry_base_sec must be numeric"
            )

    if "qlink_eol" in settings:
        new_eol = settings["qlink_eol"].upper()
        if new_eol in ("CR", "CRLF"):
            QLINK_EOL = new_eol
            EOL = "\r\n" if QLINK_EOL == "CRLF" else "\r"
            updated.append("qlink_eol")

    if "bridge_api_secret" in settings:
        BRIDGE_API_SECRET = str(settings["bridge_api_secret"] or "")
        updated.append("bridge_api_secret")

    try:
        to_persist: Dict[str, Any] = {}
        for key in (
            "vantage_ip",
            "vantage_port",
            "qlink_timeout",
            "qlink_fade",
            "qlink_eol",
            "qlink_max_retries",
            "qlink_retry_base_sec",
            "bridge_api_secret",
        ):
            if key in settings:
                to_persist[key] = settings[key]

        if to_persist:
            _persist_settings(to_persist)
    except Exception:
        logger.exception("Failed to persist settings")

    return {
        "status": "ok",
        "updated": updated,
        "restart_required": restart_required,
        "api_secret_set": bool(BRIDGE_API_SECRET),
        "message": (
            "Settings updated. Restart bridge for network changes to take effect."
            if restart_required
            else "Settings updated successfully."
        ),
    }


@app.get("/probe", dependencies=API_DEPENDENCIES)
def probe_connection(
    ip: Optional[str] = None,
    port: Optional[int] = None,
    timeout: Optional[float] = None,
):
    """Quick TCP connectivity probe to the Vantage IP-Enabler.

    Query parameters:
    - ip: optional IP address to probe (defaults to configured VANTAGE_IP)
    - port: optional port to probe (defaults to configured VANTAGE_PORT)
    - timeout: optional timeout in seconds (defaults to small value)

    Returns 200 with {ok: True} on success, or 502/504 on failure.
    """
    tgt_ip = ip or VANTAGE_IP
    tgt_port = int(port or VANTAGE_PORT)
    to = float(timeout or min(QLINK_TIMEOUT, 2.0))

    try:
        with socket.create_connection((tgt_ip, tgt_port), timeout=to):
            return {"ok": True, "ip": tgt_ip, "port": tgt_port}
    except socket.timeout as ex:
        raise HTTPException(
            status_code=504, detail="Timeout connecting to target"
        ) from ex
    except Exception as ex:
        raise HTTPException(status_code=502, detail=f"Connect error: {ex}") from ex


@app.websocket("/events")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time Vantage event streaming.

    Clients connect to ws://host:port/events and receive JSON events:
    - Button presses/releases (SW events)
    - Load changes (LO, LS, LV events)
    - LED state changes (LE, LC events)
    """
    if not _authorize_websocket(websocket):
        await websocket.close(code=4401, reason="Unauthorized")
        return
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
    except Exception:
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
        # If in auto mode and no clients remain, stop polling
        try:
            if QLINK_MONITOR_MODE == "auto" and len(websocket_clients) == 0:
                stop_polling_thread()
                logger.info("Auto mode: stopped polling (no WebSocket clients)")
        except Exception:
            pass
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_clients.discard(websocket)


@app.on_event("startup")
async def startup_event():
    """Start event listener and SSDP advertiser on application startup"""
    global event_loop, ssdp_advertiser
    event_loop = asyncio.get_running_loop()
    print("Starting Vantage QLink Bridge...")
    logger.info("Starting Vantage QLink Bridge...")
    start_monitoring()

    # Start SSDP advertiser for SmartThings LAN discovery
    print(f"SSDP_ENABLED = {SSDP_ENABLED}")
    if SSDP_ENABLED:
        try:
            print("Getting local IP for SSDP...")
            local_ip = get_local_ip()
            print(f"Local IP: {local_ip}")
            if local_ip:
                # Get bridge port from environment or default
                bridge_port = int(os.getenv("BRIDGE_PORT", "8000"))
                print(f"Creating SSDP advertiser on {local_ip}:{bridge_port}")
                ssdp_advertiser = SSDPAdvertiser(
                    local_ip=local_ip,
                    local_port=bridge_port,
                    uuid=f"vantage-qlink-bridge-{local_ip.replace('.', '-')}",
                    interval=30,
                )
                ssdp_advertiser.start()
                msg = f"📡 SSDP advertiser started on {local_ip}:{bridge_port}"
                print(msg)
                logger.info(msg)
            else:
                msg = "Could not determine local IP for SSDP advertising"
                print(f"WARNING: {msg}")
                logger.warning(msg)
        except Exception as e:
            msg = f"Failed to start SSDP advertiser: {e}"
            print(f"ERROR: {msg}")
            logger.error(msg)
            import traceback

            traceback.print_exc()
    else:
        print("SSDP is disabled")

    if QLINK_MONITOR_MODE == "events":
        if QLINK_DISABLE_EVENTS:
            logger.info("✅ Bridge ready (event monitoring disabled by configuration)")
        else:
            logger.info("✅ Bridge ready (event listener thread started)")
    elif QLINK_MONITOR_MODE == "poll":
        logger.info(
            "✅ Bridge ready (LED polling mode, interval %.1fs)",
            QLINK_LED_POLL_INTERVAL,
        )
    else:
        logger.info("✅ Bridge ready (monitoring disabled)")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop SSDP advertiser on application shutdown"""
    global ssdp_advertiser
    if ssdp_advertiser:
        try:
            logger.info("Stopping SSDP advertiser...")
            ssdp_advertiser.stop()
        except Exception as e:
            logger.error(f"Error stopping SSDP advertiser: {e}")


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Return both `error` and `detail` keys to satisfy clients/tests expecting either
    return JSONResponse(
        status_code=exc.status_code,
        content={"ok": False, "error": exc.detail, "detail": exc.detail},
    )


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.exception("Unhandled error: %s", exc)
    return JSONResponse(
        status_code=500,
        content={"ok": False, "error": "Internal Server Error", "detail": str(exc)},
    )
