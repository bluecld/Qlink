import asyncio
import websockets

async def run():
    uri = 'ws://<BRIDGE_IP>:8000/events'
    print('Connecting to', uri)
    try:
        async with websockets.connect(uri) as ws:
            print('Connected, sleeping for 6s to simulate UI')
            await asyncio.sleep(6)
            print('Closing websocket')
    except Exception as e:
        print('WebSocket connect failed:', e)

asyncio.run(run())
