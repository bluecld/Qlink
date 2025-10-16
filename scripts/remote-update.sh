#!/usr/bin/env bash
set -euo pipefail

REMOTE_DIR="${REMOTE_DIR:-/home/pi/qlink-bridge}"
cd "$REMOTE_DIR"

# restart service to pick up code changes
sudo systemctl restart qlink-bridge
sleep 1
sudo systemctl status qlink-bridge --no-pager -l | sed -n '1,15p'
