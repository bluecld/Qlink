# Runbook

## Bridge service

Check status:
```bash
systemctl status qlink-bridge.service
```

Restart:
```bash
sudo systemctl restart qlink-bridge.service
```

Logs:
```bash
journalctl -u qlink-bridge.service -n 200 --no-pager
```

## Home Assistant

Restart HA container:
```bash
sudo docker restart homeassistant
```

HA logs:
```bash
sudo docker logs homeassistant --tail 200
```

Test from inside the container (bridge reachability):
```bash
sudo docker exec homeassistant wget -qO- http://172.17.0.1:8000/about
```

## Quick API checks

```bash
curl http://localhost:8000/about
curl http://localhost:8000/settings
curl http://localhost:8000/load/249/status
curl http://localhost:8000/api/loads/priority
```

## Common issues

- HA shows all lights off: verify the HA base URL is `http://172.17.0.1:8000`.
- Slow updates: reduce `scan_interval` or enable priority polling.
- Timeouts: increase `LOADS_CACHE_TTL` and keep subset polling enabled.
