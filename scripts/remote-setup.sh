#!/usr/bin/env bash
set -euo pipefail

# Inputs (from environment)
REMOTE_DIR="${REMOTE_DIR:-/home/pi/qlink-bridge}"
VANTAGE_IP="${VANTAGE_IP:-192.168.1.200}"
VANTAGE_PORT="${VANTAGE_PORT:-23}"

mkdir -p "$REMOTE_DIR"
cd "$REMOTE_DIR"

# Ensure Python venv available
sudo apt update -y
sudo apt install -y python3-venv

# Create venv if missing
if [ ! -d ".venv" ]; then
  python3 -m venv .venv
fi
source .venv/bin/activate

# Install requirements
pip install --upgrade pip
pip install -r app/requirements.txt

# Ensure log directory exists if using system path
sudo mkdir -p /var/log
sudo touch /var/log/qlink-bridge.log || true
sudo chown $(whoami):$(whoami) /var/log/qlink-bridge.log || true

# Create/overwrite systemd unit
SERVICE=/etc/systemd/system/qlink-bridge.service
sudo bash -c "cat > $SERVICE" <<UNIT
[Unit]
Description=Vantage QLink REST Bridge (uvicorn)
After=network-online.target
Wants=network-online.target

[Service]
User=$(whoami)
WorkingDirectory=$REMOTE_DIR
Environment=VANTAGE_IP=$VANTAGE_IP
Environment=VANTAGE_PORT=$VANTAGE_PORT
Environment=Q_LINK_EOL=${Q_LINK_EOL:-}
Environment=QLINK_TIMEOUT=${QLINK_TIMEOUT:-}
Environment=LOG_FILE=/var/log/qlink-bridge.log
ExecStart=$REMOTE_DIR/.venv/bin/uvicorn app.bridge:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=2

[Install]
WantedBy=multi-user.target
UNIT

sudo systemctl daemon-reload
sudo systemctl enable --now qlink-bridge
sudo systemctl restart qlink-bridge || true
sudo systemctl status qlink-bridge --no-pager -l | sed -n '1,20p'
