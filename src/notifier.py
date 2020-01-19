import asyncio

events = asyncio.Queue(10)

async def broadcastEvent(id, data):
    await events.put({'id': id, 'data': data})

async def producerHandler():
    while True:
        event = await events.get()
        print(event)
        #await websocket.send(event)