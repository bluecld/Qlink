#!/bin/bash
# Quick test of the bridge on Pi test rig

echo "=========================================="
echo "Qlink Bridge Test - Phase 1 (Mock Mode)"
echo "=========================================="
echo ""

cd ~/qlink-bridge
source venv/bin/activate

# Start mock Vantage server
echo "🔧 Starting mock Vantage server on 127.0.0.1:2323..."
python3 scripts/mock_vantage.py &
MOCK_PID=$!
sleep 2
echo "  Mock server PID: $MOCK_PID"
echo ""

# Start bridge pointing at mock
echo "🌉 Starting bridge (pointing at mock)..."
export VANTAGE_IP="127.0.0.1"
export VANTAGE_PORT="2323"
uvicorn app.bridge:app --host 0.0.0.0 --port 8000 &
BRIDGE_PID=$!
sleep 3
echo "  Bridge PID: $BRIDGE_PID"
echo ""

# Test endpoints
echo "🧪 Testing endpoints..."
echo ""

echo "1. Health check:"
curl -s http://localhost:8000/healthz | python3 -m json.tool
echo ""

echo "2. About:"
curl -s http://localhost:8000/about | python3 -m json.tool
echo ""

echo "3. Set device 101 to 75%:"
curl -s -X POST http://localhost:8000/device/101/set \
  -H "Content-Type: application/json" \
  -d '{"level": 75}' | python3 -m json.tool
echo ""

echo "4. Read device 101:"
curl -s http://localhost:8000/send/VGL%20101 | python3 -m json.tool
echo ""

echo "5. Turn device 102 ON:"
curl -s -X POST http://localhost:8000/device/102/set \
  -H "Content-Type: application/json" \
  -d '{"switch": "on"}' | python3 -m json.tool
echo ""

echo "=========================================="
echo "✅ Test complete!"
echo "=========================================="
echo ""
echo "Bridge is running at: http://192.168.0.180:8000"
echo "Web UI at: http://192.168.0.180:8000/ui"
echo ""
echo "To stop services:"
echo "  kill $MOCK_PID $BRIDGE_PID"
echo ""
echo "Processes are running in background."
echo "Check logs: tail -f ~/qlink-bridge/mock.log"
echo ""
