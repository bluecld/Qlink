"""Test script to run the bridge with event monitoring"""

import uvicorn
import logging

# Set logging level to see event messages
logging.basicConfig(level=logging.INFO)

if __name__ == "__main__":
    print("🚀 Starting Vantage QLink Bridge with Event Monitoring...")
    print(f"📡 Web UI: http://localhost:8000/ui/")
    print(f"📊 Monitor Status: http://localhost:8000/monitor/status")
    print(f"🔌 WebSocket Events: ws://localhost:8000/events")
    print("")
    print("Press CTRL+C to stop")
    print("")

    uvicorn.run(
        "app.bridge:app", host="0.0.0.0", port=8000, log_level="info", reload=False
    )
