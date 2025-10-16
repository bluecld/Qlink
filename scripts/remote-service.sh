#!/usr/bin/env bash
set -euo pipefail
ACTION="${1:-status}"
sudo systemctl "$ACTION" qlink-bridge --no-pager -l
