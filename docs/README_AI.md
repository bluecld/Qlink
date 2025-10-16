# AI Maintainer Brief (VSC CoPilot / ChatGPT Code Companion)
This repository hosts a **Vantage Q‑Link → REST Bridge** that runs on a Raspberry Pi and talks to an old Vantage Q‑Link system via the IP‑Enabler (TCP). The goal is to expose **simple local HTTP endpoints** that other systems (SmartThings Edge driver, etc.) can call.

## Mission
- Maintain a stable FastAPI service that forwards ASCII Q‑Link commands over TCP.
- Keep everything **local LAN**: no cloud dependencies.
- Provide **idempotent** commands and **predictable** responses for home automation.
- Prepare for **SmartThings Edge** integration (LAN HTTP).

## System Diagram
```
SmartThings Hub (Edge Driver)  ←HTTP→  Pi Bridge (FastAPI)  ←TCP→  Vantage IP‑Enabler  ←bus→  Q‑Link
```

## Ground Rules
- Never expose the bridge publicly. LAN‑only.
- Keep commands ASCII, terminated with `\r` (or `\r\n` if required).
- Timeouts should fail **fast** (≤ 2 seconds) and return clear JSON.
- No blocking I/O on the main thread; prefer short-lived TCP connections per request (for now).
- Log inputs/outputs at INFO level; do **not** log secrets.

## Key Files (expected)
- `app/bridge.py` — FastAPI app (reference implementation provided).
- `app/requirements.txt` — dependencies (`fastapi`, `uvicorn`).
- `scripts/remote-setup.sh` — Pi bootstrap (venv, systemd unit).
- `qlink-bridge.service` — systemd unit (if managed manually).
- `.vscode/tasks.json` — tasks to deploy/update/logs (Windows PowerShell → Pi).

---

# API Contract (minimal)
- `GET /about` → `{ name, version, ip, port }`
- `GET /send/{cmd}` → forwards raw `{cmd}` (string, URL‑decoded) to Q‑Link; returns `{ command, response }`
- `POST /device/{id}/set` → `{ switch: "on"|"off" } | { level: 0..100 }`

## Constraints
- Default terminator: CR (`\r`). Some installs may require CRLF (`\r\n`).
- Encoding: ASCII. Fallback to Latin‑1 only if necessary.
- Port: typically 23 or 5000 on the IP‑Enabler.

## Done‑Definition for an endpoint
- Input validated.
- Times out in ≤ 2s on connect and read.
- Returns a JSON object with the original input echoed.
- Includes basic error JSON: `{ "ok": false, "error": "...", "detail": "..." }`.

---

# Backlog (AI can implement)
1. **Config file support**: Read `.env` or `config.yaml` / `config.json` instead of env vars only.
2. **CRLF toggle**: Add `Q_LINK_EOL` env (`CR`|`CRLF`) and unit tests.
3. **Status polling**: Optional `/device/{id}/state` with cached level and switch state.
4. **Regex feedback**: Accept backend feedback lines and update cache.
5. **Discovery**: `/manifest` returning a device list from config.
6. **Logging**: Add structured logs `uvicorn.access=false`, custom logger.
7. **Health**: `/healthz` and `/readyz` endpoints.
8. **Rate limiting**: Basic leaky bucket per source IP.
9. **SmartThings Edge**: Provide driver code and tests that call the REST endpoints.
10. **Dockerfile**: Produces a small image with multi‑stage build.

---

# Testing Playbook
- `curl http://<pi-ip>:8000/about`
- `curl "http://<pi-ip>:8000/send/VLA@12%20100"`
- `curl -X POST http://<pi-ip>:8000/device/12/set -H "Content-Type: application/json" -d "{\"level\": 33}"`

Simulate failure:
- Set `VANTAGE_IP` to an unused address and assert fast timeout & JSON error.

---

# Operational Notes
- Prefer **Ethernet** on the Pi for reliability.
- If Wi‑Fi is needed, ensure `/etc/wpa_supplicant/wpa_supplicant.conf` exists and `country=US` is set.
- Monitor logs: `journalctl -u qlink-bridge -f -n 200`.
