# Onboarding a New Maintainer

Read this first if you have just been given access to this project. It controls
a **live house** - real lights respond to real API calls. Nothing here is a
sandbox unless you make it one (see "Working offline" below).

## 1. What is in the repo

- `app/bridge.py` - the whole bridge (FastAPI + uvicorn). It speaks the Vantage
  Q-Link ASCII protocol over TCP and exposes REST/WebSocket endpoints.
- `app/static/` - the web UI, served at `/ui/`.
- `generate_ha_config.py` - emits Home Assistant YAML from `config/loads.json`.
- `config/loads.json` - the room and load-ID map for the house (tracked).
- `scripts/` - deploy, parsing, and maintenance helpers.
- `tests/` - pytest suite.

## 2. What is NOT in the repo

These are gitignored. Ask the maintainer for a copy, or start from the
`.example` file sitting next to each one.

| File | What it holds |
|---|---|
| `config/targets.json` | SSH deploy target: host, user, key path, remote dir, env |
| `config/bridge_settings.json` | Vantage IP/port, fade time, EOL, API secret |
| `config/ha_areas.json` | Home Assistant area assignments |
| `.env` | Optional environment overrides |
| `PROJECT_URLS.md` | Real hostnames, IPs, SSH aliases for the live deployment |
| `vantage.yaml` | Full-house export (kept out of git deliberately) |

## 3. Access you need for live work

1. **Network** - the bridge is not exposed to the internet. You reach it either
   on the LAN or through the maintainer's Tailscale tailnet. Ask for an invite.
2. **SSH** - generate your **own** keypair (`ssh-keygen -t ed25519`) and send
   the maintainer the `.pub` file to add to the bridge host's
   `~/.ssh/authorized_keys`. Never share a private key.
3. **GitHub** - ask to be added as a collaborator, or fork and open PRs.

## 4. Local development setup

Python 3.11+.

```bash
git clone https://github.com/bluecld/Qlink.git
cd Qlink
python3 -m venv .venv && source .venv/bin/activate   # Windows: .\.venv\Scripts\Activate.ps1
pip install -r app/requirements.txt -r dev-requirements.txt
cp config/targets.example.json config/targets.json
cp config/bridge_settings.example.json config/bridge_settings.json
pytest
```

## 5. Working offline (do this before touching the live system)

There is a mock controller so you never have to point at the real house:

```bash
python scripts/mock_vantage.py            # fake Vantage controller
# in another shell, point the bridge at it:
VANTAGE_IP=127.0.0.1 VANTAGE_PORT=3040 \
  uvicorn app.bridge:app --host 127.0.0.1 --port 8000
```

`scripts/test-bridge-mock.sh` wires both together for a quick smoke test.

## 6. Deploying

Deploy reads `config/targets.json`:

```powershell
.\scripts\deploy.ps1     # full deploy, reinstalls dependencies
.\scripts\update.ps1     # quick code-only update
.\scripts\logs.ps1       # tail the service logs
```

Then verify: `curl http://<BRIDGE_IP>:8000/healthz` and
`curl http://<BRIDGE_IP>:8000/monitor/status`.

See `docs/RUNBOOK.md` for service and Home Assistant guest management, and
`docs/PRODUCTION_CHECKLIST.md` before and after any live change.

## 7. Rules of the road

- **The house is live.** Changing a load ID or a fade time has immediate,
  visible effects on someone's lights. Test against the mock first.
- **Never commit** `config/targets.json`, `config/bridge_settings.json`,
  `config/ha_areas.json`, `PROJECT_URLS.md`, `vantage.yaml`, or logs.
- **This repo is public.** Do not add real IPs, hostnames, usernames, key
  names, or the API secret to any tracked file. Use placeholders.
- Branch for changes; do not commit straight to `main`.
- Run `pytest` before pushing (18 tests, ~1s).
- `python scripts/validate_config.py --strict` is useful but **currently fails**
  on pre-existing data - see Known issues.

## 8. Known security note

`bridge_api_secret` is currently empty, which **disables authentication** on
every endpoint - anyone who can reach port 8000 can control every light. That
is tolerable only because the bridge is confined to the LAN/tailnet. Set a
secret in `config/bridge_settings.json` (and pass `--api-secret` when
generating the HA config) before exposing it anywhere wider.

## 9. Known issues

- **`config/loads.json` does not validate against its own schema.** Several
  rooms carry a `stations` array (schema expects a single `station` integer),
  some have `station: null`, and at least one has an empty `loads` array. The
  bridge tolerates this; `scripts/validate_config.py --strict` does not. Either
  the schema or the data needs to be reconciled - do not "fix" the data blindly,
  it is the live house map.
- **The bridge host has been intermittently unreachable over the LAN** while
  responding fine over Tailscale. If SSH to the LAN address times out, try the
  Tailscale address before assuming the host is down.
