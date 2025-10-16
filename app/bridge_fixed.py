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

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from typing import Optional
import os
import socket
import logging
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


VANTAGE_IP = _env("VANTAGE_IP", "192.168.1.200")
VANTAGE_PORT = int(_env("VANTAGE_PORT", "23"))
QLINK_EOL = _env("Q_LINK_EOL", "CR").upper()
EOL = "\r\n" if QLINK_EOL == "CRLF" else "\r"
QLINK_TIMEOUT = float(_env("QLINK_TIMEOUT", "2.0"))
QLINK_FADE = _env("QLINK_FADE", "2.3")

logger = logging.getLogger("qlink")
if not logger.handlers:
    logger.addHandler(logging.StreamHandler())


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
    return {"ip": VANTAGE_IP, "port": VANTAGE_PORT, "fade": QLINK_FADE}


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.get("/send/{cmd}")
def send_raw(cmd: str):
    return {"command": cmd, "response": qlink_send(cmd)}


@app.post("/device/{id}/set")
def set_device(id: int, body: LevelCmd):
    fade = QLINK_FADE
    if body.switch:
        if body.switch.lower() == "on":
            return {"resp": qlink_send(f"VLO {id} 100 {fade}")}
        if body.switch.lower() == "off":
            return {"resp": qlink_send(f"VLO {id} 0 {fade}")}
        raise HTTPException(400, "switch must be on/off")
    if body.level is not None:
        lvl = max(0, min(100, int(body.level)))
        return {"resp": qlink_send(f"VLO {id} {lvl} {fade}")}
    raise HTTPException(400, "provide switch or level")


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
