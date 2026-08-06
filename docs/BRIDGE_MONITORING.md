# Bridge Monitoring & Recovery

Use these operator shortcuts to keep the Raspberry Pi hosted qlink-bridge healthy and to detect rogue uvicorn instances that can steal port 8000.

## Watch qlink-bridge Logs

```powershell
pwsh scripts\logs.ps1 -Lines 400 -SinceMinutes 60
```

- Reads SSH connection info from `config/targets.json`.
- Streams `journalctl -u qlink-bridge` with an optional look-back window.
- Pass `-NoFollow` to capture a static snapshot instead of following the log.
- Look for `Address already in use` or repeated restarts to catch port conflicts early.

## Detect or Terminate Legacy uvicorn Processes

```powershell
pwsh scripts\kill_legacy_uvicorn.ps1          # list only
pwsh scripts\kill_legacy_uvicorn.ps1 -Force   # terminate stale PIDs
```

- Lists every `uvicorn` process that is *not* running out of `/home/pi/qlink-bridge`.
- When `-Force` is supplied, the script issues `sudo kill <pid>` for each rogue process.
- Safe to run repeatedly—if only the managed service is active, the script exits without changes.

## Verify Port Ownership Manually

If the service keeps restarting, double-check what owns port 8000.

```bash
ssh -i ~/.ssh/id_ed25519 pi@<BRIDGE_TAILSCALE_IP> "sudo ss -tulpn | grep 8000"
ssh -i ~/.ssh/id_ed25519 pi@<BRIDGE_TAILSCALE_IP> "ps -fp <pid>"
```

Replace the key path and host if your `config/targets.json` uses different values. After killing any stray process, run `sudo systemctl restart qlink-bridge` and re-run the log watcher to confirm the service stays active.
