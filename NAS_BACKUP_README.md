# NAS Backup Solution - Work to Home

## Overview
This backup solution syncs data from your work NAS (ASUSTOR at 192.168.0.62) to your home NAS (Netgear at 192.168.1.129) using your **Raspberry Pi as a permanent bridge**. The backup runs automatically every night at 2 AM.

## Why This Approach?
- **Work NAS cannot reach home NAS directly**: Tailscale runs in a container on work NAS, which doesn't expose subnet routes to the host OS
- **Home NAS is too limited**: ReadyNAS runs old Debian 8 without Tailscale support
- **Pi as permanent bridge**: Raspberry Pi has both OpenVPN (to work network) and Tailscale (to home network), making it the perfect intermediary
- **Fully automated**: Runs independently of any PC being on

## What Gets Backed Up
- **Source**: `/volume1/Main/Main/` on work NAS (192.168.0.62)
- **Destination**: `/home/admin/WorkBackup/` on home NAS (192.168.1.129)
- **Size**: 85 GB (44,083 files successfully backed up)

## Exclusions
The backup automatically excludes:
- All hidden folders and files (starting with `.`)
- `@eaDir` (Synology metadata)
- `.DS_Store` (macOS metadata)
- `Thumbs.db` (Windows thumbnails)

## Network Setup
- **Raspberry Pi** (100.81.88.76 / 192.168.1.213): Bridge between networks
  - **OpenVPN client**: Connects to work network (99.7.105.188) to access 192.168.0.0/24
  - **Tailscale**: Advertises home subnet (192.168.1.0/24) to network
  - Runs Vantage QLink bridge + NAS backup automation
- **Work NAS**: 192.168.0.62 (ASUSTOR - accessed via Pi's OpenVPN)
- **Home NAS**: 192.168.1.129 (Netgear ReadyNAS - accessed via Pi's local network)

## Backup Script

### Location
`/home/pi/nas-backup.sh` on Raspberry Pi

### How It Works
1. **SSHFS Mount**: Pi mounts home NAS filesystem via SSHFS
2. **Streaming Transfer**: rsync streams data directly from work NAS through Pi to home NAS
3. **No Local Storage**: Data flows through Pi memory without using disk space

### Commands
All commands are run via SSH to the Raspberry Pi:

#### Check Backup Status
```bash
ssh pi@100.81.88.76 "tail -50 /home/pi/nas-backup.log"
```
View the last backup log entries

#### Manual Dry Run (Test Mode)
```bash
ssh pi@100.81.88.76 "/home/pi/nas-backup.sh"
```
Shows what would be copied WITHOUT actually copying anything. Use this to verify the backup will work.

#### Manual Backup Execution
```bash
ssh pi@100.81.88.76 "/home/pi/nas-backup.sh --execute"
```
Manually trigger a backup. This will:
- Mount home NAS via SSHFS (if not already mounted)
- Stream ~85 GB from work NAS through Pi to home NAS
- Show progress and transfer speeds
- Log everything to `/home/pi/nas-backup.log`

#### Web Dashboard
```
http://192.168.1.213:8000/ui/backup.html
http://100.81.88.76:8000/ui/backup.html (via Tailscale)
```
Monitor backup status, logs, and progress in real-time (auto-refreshes every 30 seconds)

#### Check Scheduled Backup
```bash
ssh pi@100.81.88.76 "crontab -l"
```
View the automated backup schedule (runs daily at 2 AM)

## Important Notes

### Automated Schedule
- **Runs daily at 2:00 AM** (Pi local time)
- Logs to `/home/pi/nas-backup-cron.log` (cron log) and `/home/pi/nas-backup.log` (backup details)
- Pi must be powered on (it always is)
- OpenVPN connection must be active (auto-reconnects on boot)

### Disk Space Requirements
- **Pi**: No significant disk space needed (SSHFS streams data through memory)
- **Home NAS**: Needs ~100GB free space (currently using 85GB, 5% of 1.9TB capacity)

### --delete Flag
The rsync transfer uses `--delete` which means:
- Files deleted from work NAS will be deleted from home NAS backup
- This keeps the backup synchronized
- Home backup will exactly match work NAS (excluding hidden files/folders)

### Resource Usage
- **CPU**: Low (compression uses some CPU during backup)
- **RAM**: ~20-50MB during backup
- **Network**: Active transfer for 30-60 minutes depending on changes
- **Impact**: Minimal - scheduled at 2 AM to avoid interfering with Vantage bridge

## Troubleshooting

### Backup Not Running
```bash
# Check OpenVPN status
ssh pi@100.81.88.76 "sudo systemctl status openvpn-client@asustor"

# Check cron job
ssh pi@100.81.88.76 "crontab -l"

# View recent logs
ssh pi@100.81.88.76 "tail -100 /home/pi/nas-backup-cron.log"
```

### "ERROR: OpenVPN not connected"
- OpenVPN service may have stopped
- Restart: `ssh pi@100.81.88.76 "sudo systemctl restart openvpn-client@asustor"`
- Check status: `ssh pi@100.81.88.76 "ip addr show tun0"`

### "ERROR: Cannot reach work NAS"
- Work NAS may be offline or OpenVPN connection issue
- Test manually: `ssh pi@100.81.88.76 "ssh admin@192.168.0.62 'echo OK'"`
- Check work NAS is powered on and network is accessible

### Permission Denied
- SSH keys may have been removed
- Re-add Pi's SSH key to NAS devices (see setup section)

### SSHFS Mount Issues
- Check mount status: `ssh pi@100.81.88.76 "mountpoint /home/pi/mnt/home_nas"`
- Remount if needed: `ssh pi@100.81.88.76 "sshfs admin@192.168.1.129:/ /home/pi/mnt/home_nas"`
- Unmount: `ssh pi@100.81.88.76 "fusermount -u /home/pi/mnt/home_nas"`

## Files and Locations

### On Raspberry Pi
- `/home/pi/nas-backup.sh` - Main backup script
- `/home/pi/nas-backup.log` - Detailed backup log
- `/home/pi/nas-backup-cron.log` - Cron execution log
- `/home/pi/mnt/home_nas/` - SSHFS mount point for home NAS
- `/etc/openvpn/client/asustor.conf` - OpenVPN configuration
- `/etc/openvpn/client/auth.txt` - OpenVPN credentials (secure)
- `/home/pi/qlink-bridge/app/bridge.py` - Web dashboard backend
- `/home/pi/qlink-bridge/app/static/backup.html` - Web dashboard UI

### On PC (Legacy - for manual use)
- `C:\qlink\backup_simple.sh` - PC-based backup script (deprecated)
- `C:\qlink\backup-nas.ps1` - PowerShell version (not used)

## Technical Details
- **rsync**: Standard Linux rsync on Pi
- **SSH**: Standard OpenSSH on all devices
- **Transfer**: Compressed (-z flag) for faster transfers over VPN
- **Preservation**: Maintains permissions, timestamps, etc (-a flag)
- **Progress**: Shows progress during manual execution (--progress flag)
- **Automation**: Runs via cron daily at 2 AM
- **OpenVPN**: Auto-starts on Pi boot, connects to work network
- **Tailscale**: Always running on Pi, provides home network access

## System Architecture
```
Work NAS (192.168.0.62)
         |
    OpenVPN (99.7.105.188)
         |
    [Raspberry Pi]
    - OpenVPN client (tun0: 10.0.1.6)
    - Tailscale (100.81.88.76)
    - Local network (192.168.1.213)
         |
Home NAS (192.168.1.129)
```

## Backup Results

### Initial Backup (Completed 2025-11-05)
- **Files transferred**: 44,083 files
- **Data transferred**: 85 GB (compressed from 90.9 GB source)
- **Duration**: ~10 hours for initial full backup
- **Speed**: Average 2.0 MB/s over OpenVPN
- **Status**: ✅ Successfully completed

### Future Backups
- **Schedule**: Automated daily at 2:00 AM
- **Type**: Incremental (only changed files)
- **Expected duration**: 5-30 minutes depending on changes
- **Web dashboard**: http://192.168.1.213:8000/ui/backup.html

## Support
Created: 2025-01-05
Updated: 2025-11-05
Status: **ACTIVE - First backup completed successfully, daily automation running**
