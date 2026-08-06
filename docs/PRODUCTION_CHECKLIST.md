# Production Checklist

## Before changes

- Backup `config/loads.json` and `config/bridge_settings.json`
- Confirm API access: `curl http://localhost:8000/about`
- If HA is in Docker, confirm `http://172.17.0.1:8000` reachability

## Deploy changes

- Update code in `/home/pi/qlink-bridge`
- Restart service: `sudo systemctl restart qlink-bridge.service`
- Regenerate HA config if needed and restart HA

## Verify

- `curl http://localhost:8000/settings`
- `curl http://localhost:8000/api/loads/priority`
- HA dashboard shows live state changes

## Rollback

- Revert to previous commit
- Restart the bridge service

## Performance defaults

- HA subset polling: `scan_interval 180`
- Priority polling: `priority_scan_interval 30`
- Bridge cache: `LOADS_CACHE_TTL 240`
