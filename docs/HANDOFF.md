# Handoff

This repository runs the Vantage Q-Link bridge and Home Assistant integration
for a live home system. Keep the system running while making changes.

## Summary

- Bridge API: `app/bridge.py` (FastAPI, uvicorn)
- Home Assistant generator: `generate_ha_config.py`
- Web UI: `app/static`

## Current deployment (home system)

- Bridge service: `qlink-bridge.service` (systemd)
- Home Assistant: Docker container
- HA container does not use `--network=host`, so the bridge base URL for HA
  must be `http://172.17.0.1:8000`.

## Key configs

- `config/loads.json`: source of rooms and load IDs
- `config/bridge_settings.json`: local runtime settings (ignored in git)
- `config/targets.json`: SSH targets (ignored in git)
- `.env`: optional environment overrides (ignored in git)
- Example files live next to the real configs

## Home Assistant generation

Recommended command for large installs:

```bash
python generate_ha_config.py \
  --ha-in-docker \
  --use-subsets \
  --use-priority \
  --priority-scan-interval 30 \
  --scan-interval 180 \
  --timeout 20 \
  > /tmp/ha_config.yaml
```

## Repo hygiene

- Local artifacts and caches are ignored in `.gitignore`
- Do not commit live config files or logs
