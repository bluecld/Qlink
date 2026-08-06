#!/usr/bin/env bash
# Qlink Pi health snapshot
set -euo pipefail

echo "=== Qlink Pi Health ==="
echo "[Time] $(date)"
echo "[Uptime] $(uptime -p) | Load $(cut -d' ' -f1-3 /proc/loadavg)"
echo "[Hostname] $(hostname)"
echo "[IPs] $(hostname -I 2>/dev/null || echo 'N/A')"

# CPU Model
CPU_MODEL=$(grep -m1 'Model' /proc/cpuinfo || true)
[ -n "$CPU_MODEL" ] && echo "[CPU] $CPU_MODEL"

# Temperature
if command -v vcgencmd >/dev/null 2>&1; then
  echo "[Temp] $(vcgencmd measure_temp | cut -d'=' -f2)"
elif [ -f /sys/class/thermal/thermal_zone0/temp ]; then
  RAW=$(cat /sys/class/thermal/thermal_zone0/temp)
  echo "[Temp] $(awk "BEGIN{printf \"%.1f°C\", $RAW/1000}")"
else
  echo "[Temp] Unknown"
fi

# Memory
echo "[Memory]"
free -h

# Disks
echo "[Disk /]"; df -h / | tail -1
if mount | grep -q '/mnt/data'; then
  echo "[Disk /mnt/data]"; df -h /mnt/data | tail -1
fi

# Services
for svc in tailscaled qlink-bridge; do
  if systemctl list-units --type=service --all | grep -q "${svc}.service"; then
    echo "[Service $svc] $(systemctl is-active $svc)";
  else
    echo "[Service $svc] not-installed";
  fi
done

# Tailscale status (truncated)
if command -v tailscale >/dev/null 2>&1; then
  echo "[Tailscale status]"; sudo tailscale status | head -n 25 || true
  echo "[Tailscale netcheck]"; sudo tailscale netcheck 2>&1 | sed -n '1,15p' || true
else
  echo "[Tailscale] tailscale command not found"
fi

# Recent logs
for svc in qlink-bridge tailscaled; do
  if systemctl list-units --type=service --all | grep -q "${svc}.service"; then
    echo "[Logs $svc]"; journalctl -u $svc -n 20 --no-pager || true
  fi
done

# Throttle state (Pi specific)
if command -v vcgencmd >/dev/null 2>&1; then
  echo "[Throttle] $(vcgencmd get_throttled | cut -d'=' -f2)"
fi

echo "=== End ==="