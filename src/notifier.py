import asyncio
import json
import websockets

events = asyncio.Queue(10)

async def broadcastEvent(id, data):
    await events.put({'id': id, 'data': data})

async def producerHandler(websocket, path):
    while True:
        event = await events.get()
        print(event)
        await websocket.send(json.dumps(event))

def startNotifier(port):
    return websockets.serve(producerHandler, "127.0.0.1", port)