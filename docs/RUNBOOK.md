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

## Vantage IP-Enabler quirks (read before debugging "lights won't respond")

The IP-Enabler at `<VANTAGE_IP>:3040` accepts **one TCP connection at a time**.
The bridge's command-queue worker normally owns that connection. Consequences:

- **Port probes lie.** `nc -vz <VANTAGE_IP> 3040` reporting closed/refused does
  NOT mean the enabler is down - it usually means the bridge currently holds the
  only socket. The device answering ping with 3040 "closed" is its normal busy state.
- **Status reads that bypass the command queue are flaky by design.**
  `/load/{id}/status` opens its own connection and will fail with
  "all candidate ports failed" whenever the worker has the socket. This is not
  a bug; do not chase it. Use `/monitor/status` and `/api/loads` (cached,
  queue-fed) instead.
- **Health is judged from `/monitor/status`, not from probes:**
  `last_command_at` fresh and `pending_commands` low/draining = healthy;
  `pending_commands` climbing with a stale `last_command_at` for hours = wedged.
- **If truly wedged** (stale for hours, dashboard toggles dead): the enabler's
  TCP side can hang while ping still answers. It often clears itself when the
  stale socket times out; the reliable fix is a **power-cycle of the IP-Enabler**
  (unplug 20 s). No bridge restart needed - the queue drains once it reconnects.
  Note the backlog then FIRES: queued on/off commands replay, so lights may blink.

## Host IP drift (the recurring root cause)

The bridge host's DHCP address has drifted over time and broken every consumer
that referenced a fixed IP. The host now pins its canonical address as a
permanent alias via the `qlink-lan-alias.service` systemd unit (enabled,
survives reboots) - `systemctl status qlink-lan-alias` to check. If the bridge
is suddenly unreachable at the canonical address, verify that unit first, then
`ip -4 -br addr show br0` (expect two addresses: the DHCP one plus the alias).

## Common issues

- **HA shows all lights off:** verify the HA base URL is the bridge host's LAN
  address (`http://<BRIDGE_IP>:8000`), not `localhost` or `172.17.0.1`.
- **Bridge up but nothing responds:** check `/monitor/status`, then confirm the
  controller is reachable: `nc -vz <VANTAGE_IP> 3040`.
- **Slow updates:** reduce `scan_interval` or enable priority polling.
- **Timeouts:** increase `LOADS_CACHE_TTL` and keep subset polling enabled.

## Dashboard state flicker (fixed - context if it returns)

Symptom: toggling a light from HA changed the light, but the dashboard state
changed, reverted, then changed back ~30-60 s later. Cause: HA's REST sensors
poll the bridge's caches, which only refreshed on background sweeps, so a poll
landing between the command and the next sweep served the stale level.

Fixed in `app/bridge.py`: successful commands write through to every served
cache immediately (`_write_through_load_level`), and sweeps overlay any load
commanded mid-sweep (`_overlay_recent_controls`) so they cannot resurrect a
stale value. If reverts ever reappear, confirm the deployed bridge contains
those two functions and that `_record_load_control` calls the write-through.

## Physical link flapping (cable)

Symptom: enabler drops off the network entirely (no ARP presence, 3040 closed
LAN-wide), with isolated single-sample "present" blips - the signature of an
Ethernet cable making momentary contact (bad RJ45 retention clip / not seated).
A power-cycle does NOT fix this; reseating or replacing the patch cable at the
panel does.

Tool: `/home/bluelcd/pronet_watch.sh` on the bridge host logs enabler ARP
presence + port 3040 state every 30 s. Run it in the background during cable
work and watch for continuous `PRONET+3040-OPEN`:

    setsid nohup /home/bluelcd/pronet_watch.sh > /dev/null 2>&1 &
    tail -f /home/bluelcd/pronet_watch.log

Stop it when done: `pkill -f 'pronet_watch.s[h]'` (bracket pattern avoids
pkill matching itself).
