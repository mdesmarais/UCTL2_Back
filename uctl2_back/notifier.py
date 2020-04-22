import asyncio
import json
import logging
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Set

import websockets

import uctl2_back.events as customEvent

if TYPE_CHECKING:
    from uctl2_back.race import Race

# Type aliases
EventList = List[Dict[str, Any]]

class Notifier:

    def __init__(self, race: 'Race'):
        self.race = race
        self.clients: Set[websockets.WebSocketServerProtocol] = set()
        self.events: asyncio.Queue[Optional[EventList]] = asyncio.Queue(50)
        self.delayedEvents: EventList = []
        self.stop = asyncio.get_event_loop().create_future()

    async def broadcast_event(self, id: int, payload: Dict[str, Any]) -> None:
        """
            Appends an event to a queue for events broadcasting.

            :param id: id of the event
            :param payload: optional data for this event, could be None
        """
        await self.events.put([{
            'id': id,
            'payload': payload
        }])


    def broadcast_event_later(self, id: int, payload: Dict[str, Any]) -> None:
        self.delayedEvents.append({
            'id': id,
            'payload': payload
        })

    async def broadcast_events(self) -> None:
        if len(self.delayedEvents) > 0:
            await self.events.put(self.delayedEvents.copy())
            self.delayedEvents = []


    async def broadcaster(self) -> None:
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


    async def _consumer_handler(self, ws: websockets.WebSocketServerProtocol, path: str) -> None:
        self.clients.add(ws)
        print('new handler')

        if self.race is not None:
            await ws.send(json.dumps([{
                'id': customEvent.RACE_SETUP,
                'payload': self.race.serialize()
            }]))

        # The handler needs to wait the end of the server in order
        # to keep the connection opened
        await self.stop

    async def start_notifier(self, port) -> None:
        """
            Starts a new websockets server on the given port.

            :param port: port of the websockets server
            :type port: int
        """
        async with websockets.serve(self._consumer_handler, '127.0.0.1', port):
            await self.stop

    async def stop_notifier(self) -> None:
        """
            Stops the websockets server
        """
        self.stop.set_result(1)
        await self.events.put(None)
