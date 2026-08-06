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
journalctl -u qlink-bridge.service -f          # follow
```

## Home Assistant (KVM guest)

Home Assistant OS runs as a libvirt guest named `homeassistant` on the bridge
host. It is **not** a Docker container.

List guests:
```bash
virsh --connect qemu:///system list --all
```

Restart / stop / start:
```bash
sudo virsh --connect qemu:///system reboot   homeassistant
sudo virsh --connect qemu:///system shutdown homeassistant
sudo virsh --connect qemu:///system start    homeassistant
```

Serial console (Ctrl-] to exit):
```bash
sudo virsh --connect qemu:///system console homeassistant
```

libvirt logs:
```bash
sudo journalctl -u libvirtd -n 200 --no-pager
```

HA's own logs and configuration live **inside the guest** - reach them through
the HA web UI (Settings -> Add-ons -> Terminal / File editor).

## Quick API checks

```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/about
curl http://localhost:8000/settings
curl http://localhost:8000/load/249/status
curl http://localhost:8000/api/loads/priority
curl http://localhost:8000/monitor/status     # Q-Link link health
```

`/monitor/status` is the one to read first when lights misbehave - check
`event_socket_connected`, `command_queue_depth`, and `last_command_error`.

## Common issues

- **HA shows all lights off:** verify the HA base URL is the bridge host's LAN
  address (`http://<BRIDGE_IP>:8000`), not `localhost` or `172.17.0.1`.
- **Bridge up but nothing responds:** check `/monitor/status`, then confirm the
  controller is reachable: `nc -vz <VANTAGE_IP> 3040`.
- **Slow updates:** reduce `scan_interval` or enable priority polling.
- **Timeouts:** increase `LOADS_CACHE_TTL` and keep subset polling enabled.
