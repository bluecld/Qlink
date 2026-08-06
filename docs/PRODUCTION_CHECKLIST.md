# Production Checklist

## Before changes

- Backup `config/loads.json` and `config/bridge_settings.json`
- Confirm API access: `curl http://localhost:8000/healthz` (expect `{"ok":true}`)
- Confirm the Q-Link link is healthy: `curl http://localhost:8000/monitor/status`
- Confirm HA can reach the bridge at `http://<BRIDGE_IP>:8000/about`
  (from a Docker-based HA install it would be `http://172.17.0.1:8000` instead)

## Deploy changes

- Update code in the remote dir from `config/targets.json`
  (`.\scripts\deploy.ps1` for a full deploy, `.\scripts\update.ps1` for a quick one)
- Restart service: `sudo systemctl restart qlink-bridge.service`
- Regenerate HA config if needed and restart the HA guest:
  `sudo virsh --connect qemu:///system reboot homeassistant`

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
