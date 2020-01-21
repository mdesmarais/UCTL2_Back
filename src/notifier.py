import asyncio
import json
import logging
import websockets

events = asyncio.Queue(10)

async def broadcastEvent(id, payload):
    """
        Broadcasts an event to the connected clients through
        a websocket server.

        :param id: id of the event
        :type id: int
        :param payload: optional data for this event, could be None
        :type payload: dict
    """
    await events.put({'id': id, 'payload': payload})

async def consumerHandler(websocket, path):
    logger = logging.getLogger(__name__)

    while True:
        # TODO works for only one client
        event = await events.get()
        logger.debug(event)
        await websocket.send(json.dumps(event))

def startNotifier(port):
    """
        Starts a new websocket server on the given port.

        :param port: port of the websocket server
        :type port: int
    """
    return websockets.serve(consumerHandler, '127.0.0.1', port)