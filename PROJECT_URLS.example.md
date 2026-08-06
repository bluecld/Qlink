# Vantage Q-Link Home Automation - Quick Reference URLs

> **All services run on the Mac mini** (`<BRIDGE_HOST>`, <BRIDGE_IP>).
> Home Assistant is a KVM guest on that same machine. The Acer is idle.
> The old Pi (`qlinkpi`, <BRIDGE_TAILSCALE_IP>) is retired.

## Primary Access URLs

### Home Assistant Web UI
- **URL**: http://<HA_IP>:8123  (`<HA_HOST>`)
- **Runs as**: KVM guest `homeassistant` on the Mac mini
- **Tailscale**: not exposed
- **Login**: Use credentials created during onboarding

### Vantage Bridge API
- **Web UI**: http://<BRIDGE_IP>:8000/ui/  (root `/` redirects here)
- **Local Network**: http://<BRIDGE_IP>:8000  (`<BRIDGE_HOST>`)
- **Tailscale VPN**: http://<BRIDGE_TAILSCALE_IP>:8000  (MagicDNS name `qlink`)
- **API docs**: http://<BRIDGE_IP>:8000/docs
- **Status**: Bridge should always be running via systemd/screen

### Vantage Controller (Q-Link)
- **Telnet Access**: telnet://192.168.1.200:3040
- **Protocol**: Q-Link (ASCII V-Commands)
- **Ports**: 3040 (control + status; only writable port exposed)

---

## Bridge API Endpoints

### Configuration & Status

**Get All Device Configuration:**
```
GET http://<BRIDGE_IP>:8000/config
```
Returns: Complete room/floor/device hierarchy with all loads and stations

**Check Specific Light Status:**
```
GET http://<BRIDGE_IP>:8000/load/{LOAD_ID}/status
Example: http://<BRIDGE_IP>:8000/load/254/status
```
Returns: `{"resp": "75"}` (brightness 0-100)

**Bridge Information:**
```
GET http://<BRIDGE_IP>:8000/about
```
Returns: Version, manufacturer, model info

### Control Commands

**Turn Light On/Off with Brightness:**
```
POST http://<BRIDGE_IP>:8000/device/{LOAD_ID}/set
Content-Type: application/json
Body: {"switch": "on", "brightness": 75}
Body: {"switch": "off"}
```

**Example curl commands:**
```bash
# Get Master Bedroom Main status
curl http://<BRIDGE_IP>:8000/load/254/status

# Turn on at 50%
curl -X POST http://<BRIDGE_IP>:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on", "brightness": 50}'

# Turn off
curl -X POST http://<BRIDGE_IP>:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "off"}'
```

---

## Hosts

| Role | Hostname | LAN | Tailscale | Hardware | OS |
|---|---|---|---|---|---|
| Bridge + HA host | `<BRIDGE_HOST>` | <BRIDGE_IP> | <BRIDGE_TAILSCALE_IP> (`qlink`) | Apple **Mac mini** (Macmini7,1, Late 2014) - Intel i5-4260U | Debian 13 (trixie) |
| Home Assistant | `<HA_HOST>` | <HA_IP> | n/a | KVM guest on the Mac mini (2 vCPU / 2 GB) | Home Assistant OS 18.1 |
| Spare / idle | `<SPARE_HOST>` | <SPARE_IP> | <SPARE_TAILSCALE_IP> (`acer`) | Acer **Revo 70** - AMD E-450 APU | Ubuntu 24.04.4 LTS |
| NAS backup | `<BACKUP_HOST>` | <BACKUP_IP> | <BACKUP_TAILSCALE_IP> | Raspberry Pi | - |

**Both the bridge and Home Assistant run on the Mac mini.** Home Assistant is a
libvirt/KVM virtual machine on that same box, not a separate physical host.
The Acer Revo 70 is idle - no bridge service, no containers, no VMs.

Retired: Tailscale node `qlinkpi` (<BRIDGE_TAILSCALE_IP>) is offline and `qlinkpi.local`
no longer resolves. Do not use it anywhere.

---

## SSH Access

SSH config alias is `<SSH_ALIAS>` (see `~/.ssh/config`).

```bash
# Local network
ssh <SSH_ALIAS>                    # <USER>@<BRIDGE_IP>, key id_ed25519_<SSH_ALIAS>

# Via Tailscale (when remote)
ssh <SSH_ALIAS>-ts                 # <USER>@<BRIDGE_TAILSCALE_IP>

# Spare box
ssh acer                         # <USER>@<SPARE_IP> (Tailscale: <SPARE_TAILSCALE_IP>)
```

**User:** `<USER>` | **Key:** `~/.ssh/id_ed25519_<SSH_ALIAS>` | **Auth:** SSH key

> Note: on Windows, use Git's OpenSSH (`C:\Program Files\Git\usr\bin\ssh.exe`).
> The build at `C:\Program Files\OpenSSH\ssh.exe` fails silently (exit 255, no output).

---

## Common Management Commands

### Bridge (`qlink-bridge.service`)

The bridge runs as a **systemd service** owned by `<USER>`:

- `WorkingDirectory=/home/<USER>/qlink-bridge`
- `ExecStart=/home/<USER>/qlink-bridge/.venv/bin/uvicorn app.bridge:app --host 0.0.0.0 --port 8000`

```bash
ssh <SSH_ALIAS> "systemctl is-active qlink-bridge"
ssh <SSH_ALIAS> "sudo systemctl restart qlink-bridge"
ssh <SSH_ALIAS> "journalctl -u qlink-bridge -n 100 --no-pager"
ssh <SSH_ALIAS> "journalctl -u qlink-bridge -f"          # follow
```

### Home Assistant (KVM guest)

Managed with `virsh`, **not** Docker. Guest name: `homeassistant`.
Disk image: `/var/lib/libvirt/images/haos_ova-18.1.qcow2`

```bash
ssh <SSH_ALIAS> "virsh --connect qemu:///system list --all"
ssh <SSH_ALIAS> "sudo virsh --connect qemu:///system reboot homeassistant"
ssh <SSH_ALIAS> "sudo virsh --connect qemu:///system shutdown homeassistant"
ssh <SSH_ALIAS> "sudo virsh --connect qemu:///system start homeassistant"
ssh <SSH_ALIAS> "sudo virsh --connect qemu:///system console homeassistant"   # Ctrl-] to exit
```

HA configuration lives **inside the guest** - edit it through the HA web UI
(Settings -> Add-ons -> File editor / Terminal), not from the host filesystem.

### Host health

```bash
ssh <SSH_ALIAS> "uptime; free -h; df -h /"
ssh <SSH_ALIAS> "systemctl --failed --no-pager"
```

### NAS Backup

> **Unverified.** The backup cron previously lived on the retired `qlinkpi`.
> Confirm where it runs now (likely `pi-nas-backup`, <BACKUP_IP>) before
> relying on these paths.

---

## File Locations

### On the Mac mini (`<BRIDGE_HOST>`)

**Bridge:**
- Code: `/home/<USER>/qlink-bridge/`
- Main script: `/home/<USER>/qlink-bridge/app/bridge.py`
- Virtual env: `/home/<USER>/qlink-bridge/.venv/`
- Logs: `journalctl -u qlink-bridge`

**Home Assistant VM:**
- Disk image: `/var/lib/libvirt/images/haos_ova-18.1.qcow2`
- NVRAM: `/var/lib/libvirt/qemu/nvram/homeassistant_VARS.fd`
- HA config: inside the guest, not on the host

### On Windows Development Machine

**Project Root:**
- `C:\Qlink\`

**Bridge Code:**
- Main: `C:\Qlink\app\bridge.py`
- Static UI: `C:\Qlink\app\static\`

**Deploy target:** `C:\Qlink\config\targets.json`

---

## Troubleshooting

**Bridge not responding:**
```bash
curl http://<BRIDGE_IP>:8000/healthz          # expect {"ok":true}
ssh <SSH_ALIAS> "sudo systemctl restart qlink-bridge"
ssh <SSH_ALIAS> "journalctl -u qlink-bridge -n 50 --no-pager"
```

**Bridge up but lights not responding** - check the Q-Link link:
```bash
curl -s http://<BRIDGE_IP>:8000/monitor/status
# watch: event_socket_connected, command_queue_depth, last_command_error
ssh <SSH_ALIAS> "nc -vz 192.168.1.200 3040"
```

**HA won't start:**
```bash
ssh <SSH_ALIAS> "virsh --connect qemu:///system list --all"
ssh <SSH_ALIAS> "sudo virsh --connect qemu:///system start homeassistant"
ssh <SSH_ALIAS> "sudo journalctl -u libvirtd -n 100 --no-pager"
```

**HomeKit not pairing:**
- iPhone and the HA guest must be on the same L2 network (the guest is bridged)
- HomeKit needs mDNS - it does not work over Tailscale/VPN
- Check the HomeKit Bridge integration in HA: Settings -> Devices & Services

---

## Git Repository

**Local Repository:**
```
C:\Qlink\
```

**Recent Commits:**
- b277865 - Add Home Assistant + HomeKit Bridge for Siri voice control
- 905d023 - Add NAS backup automation
- 1c72e03 - Add progress notes for Vantage bridge
- 2a7019e - Improve Vantage bridge discovery and HTTPS support

**Commit Changes:**
```bash
cd C:\Qlink
git status
git add <files>
git commit -m "Description"
```

---

## Quick Reference Card

### Most Common Tasks

**Access HA Dashboard:**
```
http://<HA_IP>:8123
```

**Restart HA:**
```bash
ssh <SSH_ALIAS> "sudo virsh --connect qemu:///system reboot homeassistant"
```

**Restart the bridge:**
```bash
ssh <SSH_ALIAS> "sudo systemctl restart qlink-bridge"
```

**Test a light:**
```bash
curl -X POST http://<BRIDGE_IP>:8000/device/254/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on", "brightness": 75}'
```

**View recent bridge logs:**
```bash
ssh <SSH_ALIAS> "journalctl -u qlink-bridge -n 50 --no-pager"
```

**Check bridge / Q-Link link health:**
```bash
curl -s http://<BRIDGE_IP>:8000/monitor/status
```

---

**Last Updated:** 2026-08-06
**Project:** Vantage Q-Link Home Automation
**System:** Mac mini (Debian 13) + Q-Link bridge + Home Assistant OS (KVM) + HomeKit
