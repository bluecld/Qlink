# Handoff

This repository runs the Vantage Q-Link bridge and Home Assistant integration
for a **live home system**. Keep the system running while making changes.

## Summary

- Bridge API: `app/bridge.py` (FastAPI, uvicorn)
- Home Assistant generator: `generate_ha_config.py`
- Web UI: `app/static`, served at `/ui/`

## Current deployment

- **Bridge host:** a small Linux box (Debian) running `qlink-bridge.service`
  under systemd, uvicorn bound to `0.0.0.0:8000`.
- **Home Assistant:** runs as a **KVM/libvirt guest (Home Assistant OS)** on that
  same host. Manage it with `virsh --connect qemu:///system`, **not** Docker.
- The guest is **bridged onto the LAN**, so it reaches the bridge at the host's
  normal LAN address - `http://<BRIDGE_IP>:8000`. The Docker-gateway address
  `172.17.0.1` does **not** apply to this deployment.

> Real hostnames, IPs and SSH details are in the local, gitignored
> `PROJECT_URLS.md`. Ask the maintainer for a copy.

## Key configs

Tracked in git:

- `config/loads.json` - source of rooms and load IDs
- `config/station_master_map.json`, `config/station_physical_map.json`

**Not** in git (ask the maintainer, or copy the `.example` next to each):

- `config/targets.json` - SSH deploy target (host, user, key, remote dir, env)
- `config/bridge_settings.json` - runtime settings (Vantage IP/port, fade, EOL, API secret)
- `config/ha_areas.json` - Home Assistant area assignments
- `.env` - optional environment overrides
- `PROJECT_URLS.md` - real addresses for this deployment

## Home Assistant generation

Point the generated config at the bridge host's LAN address:

```bash
python generate_ha_config.py \
  --bridge-base-url http://<BRIDGE_IP>:8000 \
  --use-subsets \
  --use-priority \
  --priority-scan-interval 30 \
  --scan-interval 180 \
  --timeout 20 \
  > /tmp/ha_config.yaml
```

`--ha-in-docker` (which forces `http://172.17.0.1:8000`) is only for
Docker-based HA installs. Do not use it here.

## Repo hygiene

- Local artifacts and caches are ignored in `.gitignore`
- Never commit live config files, logs, `vantage.yaml`, or `PROJECT_URLS.md`
