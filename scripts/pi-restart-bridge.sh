#!/bin/bash
# Restart the Qlink Bridge service on the Pi

echo "Stopping any running bridge processes..."
pkill -f "uvicorn app.bridge:app" || true
sleep 2

echo "Starting Qlink Bridge..."
cd ~/qlink-bridge
source venv/bin/activate

# Start uvicorn in background
nohup uvicorn app.bridge:app --host 0.0.0.0 --port 8000 > ~/qlink-bridge.log 2>&1 &

echo "Bridge started! PID: $!"
echo "Log: ~/qlink-bridge.log"
echo "URL: http://$(hostname -I | awk '{print $1}'):8000"
