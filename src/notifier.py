import asyncio
import json
import logging
import websockets

events = asyncio.Queue(10)
delayedEvents = []

clients = []
stop = asyncio.get_event_loop().create_future()

async def broadcastEvent(id, payload):
    """
        Appends an event to a queue for events broadcasting.

        :param id: id of the event
        :type id: int
        :param payload: optional data for this event, could be None
        :type payload: dict
    """
    await events.put([{
        'id': id,
        'payload': payload
    }])

def broadcastEventLater(id, payload):
    delayedEvents.append({
        'id': id,
        'payload': payload
    })

async def broadcastEvents():
    global delayedEvents

    if len(delayedEvents) > 0:
        await events.put(delayedEvents.copy())
        delayedEvents = []


async def broadcaster():
    """
        Broadcasts events from a queue through a
        websockets server.
    """
    logger = logging.getLogger(__name__)

    while True:
        event = await events.get()
        
        if event is None:
            break

        logger.debug(event)

        for client in clients:
            try:
                await client.send(json.dumps(event))
            except websockets.ConnectionClosed:
                clients.remove(client)


async def consumerHandler(websocket, path):
    clients.append(websocket)

    # The handler needs to wait the end of the server in order
    # to keep the connection opened
    await stop


async def startNotifier(port):
    """
        Starts a new websockets server on the given port.

        :param port: port of the websockets server
        :type port: int
    """
    async with websockets.serve(consumerHandler, '127.0.0.1', port):
        await stop

async def stopNotifier():
    """
        Stops the websockets server
    """

    stop.set_result(1)
    await events.put(None)
