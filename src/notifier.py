import asyncio
import json
import logging

import websockets

import events as customEvent


class Notifier:

    def __init__(self):
        self.race = None
        self.clients = set()
        self.events = asyncio.Queue(50)
        self.delayedEvents = []
        self.stop = asyncio.get_event_loop().create_future()

    async def broadcastEvent(self, id, payload):
        """
            Appends an event to a queue for events broadcasting.

            :param id: id of the event
            :type id: int
            :param payload: optional data for this event, could be None
            :type payload: dict
        """
        await self.events.put([{
            'id': id,
            'payload': payload
        }])


    def broadcastEventLater(self, id, payload):
        self.delayedEvents.append({
            'id': id,
            'payload': payload
        })

    async def broadcastEvents(self):
        if len(self.delayedEvents) > 0:
            await self.events.put(self.delayedEvents.copy())
            self.delayedEvents = []


    async def broadcaster(self):
        """
            Broadcasts events from a queue through a
            websockets server.
        """
        logger = logging.getLogger(__name__)

        while True:
            event = await self.events.get()
            
            if event is None:
                break

            logger.debug(event)

            raw_event = json.dumps(event)

            for client in list(self.clients):
                try:
                    await client.send(raw_event)
                except websockets.ConnectionClosed:
                    self.clients.remove(client)


    async def consumerHandler(self, websocket, path):
        self.clients.add(websocket)

        if self.race is not None:
            await websocket.send(json.dumps([{
                'id': customEvent.RACE_SETUP,
                'payload': self.race.toJSON()
            }]))

        # The handler needs to wait the end of the server in order
        # to keep the connection opened
        await self.stop


    async def startNotifier(self, port):
        """
            Starts a new websockets server on the given port.

            :param port: port of the websockets server
            :type port: int
        """
        async with websockets.serve(self.consumerHandler, '127.0.0.1', port):
            await self.stop

    async def stopNotifier(self):
        """
            Stops the websockets server
        """

        self.stop.set_result(1)
        await self.events.put(None)
