# Project Roadmap: Vantage Q-Link Bridge

This roadmap defines the work breakdown for the AI assistant and human contributors.
Each phase builds toward full integration with SmartThings (Edge) and Matter.

---

## Phase 1 — Core Functionality (Done)
✅ Base FastAPI bridge `app/bridge.py`  
✅ `/about`, `/send/{cmd}`, `/device/{id}/set` endpoints  
✅ Local deploy scripts for Pi + VS Code Windows task automation

---

## Phase 2 — System Hardening (Next)
1. Add `/healthz` endpoint returning `{ "ok": true }`.
2. Implement error handling with structured JSON (`ok`, `error`, `detail`).
3. Add configurable `Q_LINK_EOL` for CR vs CRLF.
4. Add logging to file `/var/log/qlink-bridge.log`.
5. Add `/config` endpoint showing runtime settings (safe subset).

---

## Phase 3 — SmartThings Integration
1. Create `SmartThings_Edge/` folder.  
2. Scaffold Edge driver (Lua) that sends local HTTP POSTs to the Pi bridge.  
3. Implement `switch` and `switchLevel` capabilities mapped to REST endpoints.  
4. Provide discovery of bridge via `/manifest`.  
5. Add Edge CLI packaging and VS Code task to deploy driver.

---

## Phase 4 — Configuration + Monitoring
1. Support `.env` file and `config.yaml`.  
2. Add systemd journal watcher script for remote log streaming.  
3. Create `/metrics` endpoint (simple counters).  
4. Add update notifier in VS Code (checks GitHub release).

---

## Phase 5 — Docker + Matter
1. Write optimized `Dockerfile` with multi-stage build.  
2. Add `docker-compose.yaml` with bridge + Edge emulator.  
3. Explore exposing bridge as a Matter bridge (optional).

---

## Maintenance Tasks (AI May Automate)
- Keep dependencies updated (`fastapi`, `uvicorn`).  
- Maintain CI tests once integrated.  
- Verify connectivity to Q-Link IP-Enabler and handle socket timeouts gracefully.  
- Add auto-restart watchdog for Pi service.

---

This file acts as the **AI assistant’s development brief**: it can plan, prioritize, and execute these tasks within VS Code using project context.
