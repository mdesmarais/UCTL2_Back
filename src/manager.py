import asyncio
import json
import logging
import os
import signal
import sys
from multiprocessing import Process
from typing import Any, List

import eventlet
import redis
from flask import Flask
from flask_socketio import SocketIO, emit

import race_file
import uctl2
from config import Config
from simulator import Simulator

eventlet.monkey_patch()
socketio = SocketIO()


class SocketIOHandler(logging.Handler):

    """
        Logger handler used to send records through socketio

        We use a redis message queue in order to emit events
        from another process.
    """

    def __init__(self):
        super().__init__()
        self.client = SocketIO(message_queue='redis://')

    def emit(self, record: logging.LogRecord) -> None:
        """
            Custom action for each record received

            This function is called by the logger.
            We it received a record, it emits an event.
        """
        self.client.emit('broadcast_logs', self.format(record))


def get_redis_client() -> redis.StrictRedis:
    """
        Creates a new connection to a redis server

        :return: new instance of a redis client
    """
    return redis.Redis(charset='utf-8', decode_responses=True)


def start_broadcast(config: Config) -> None:
    """
        Starts race broadcast

        This function should be runned in another process.
        A new event loop is created and set to asyncio, it will
        be used by the broadcast script.

        A socketio handler is created to send script's output into a
        redis queue through socketio. Records will be automaticaly sended
        to all clients by the main server.
    """
    handler = SocketIOHandler()
    formatter = logging.Formatter('[%(asctime)s][%(levelname)s] %(name)s - %(message)s', '%H:%M:%S')
    handler.setFormatter(formatter)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    uctl2.setup(config, handlers=[handler], loop=loop)


def update_racefile_thread(sim: Simulator, stages: List[Any]) -> None:
    """
        Updates the race file with the selected stages for each teams

        An event 'rows' is emitted to all connected clients with updated rows.

        :param sim: an instance to the Simulator
        :param stages: selected stages for each teams
    """
    rows = race_file.process_file(sim, stages)
    socketio.emit('racefile', {
        'rows': rows
    }, broadcast=True)


def create_app() -> Flask:
    """
        Creates a new Flask app

        This app only contains socketio events, there is not http route.
        We are using a redis message queue in order to emit events from
        another process.

        :return: instance of the new Flask app
    """
    app = Flask(__name__)
    socketio.init_app(app, cors_allowed_origins="*", message_queue='redis://')

    with open('config.json', 'r') as f:
        json_config = json.load(f)
        config = Config.readFromJson(json_config)

    if config is None:
        print('Could not load config')
        sys.exit(-1)

    sim = Simulator.create(config, socketio)
    sim.compute_times()

    @socketio.on('connect')
    def new_client():
        redis_client = get_redis_client()
        pid = redis_client.get('broadcast_process_pid')

        data = sim.to_json()
        data['broadcast_status'] = 0 if pid is None else 1
        emit('initialize', data)

    @socketio.on('toggle_broadcast')
    def toggle_broadcast():
        # We store the pid of the broadcast process into
        # the redis server
        print('asking redis')
        redis_client = get_redis_client()
        pid = redis_client.get('broadcast_process_pid')

        if pid is None:
            # Creates a new process for the broadcast
            # We use the option daemon=True to stop it when
            # this application is stopped
            p = Process(target=start_broadcast, args=(config,), daemon=True)
            p.start()
            app.logger.info('Starting broadcast')
            print('broadcast pid=', p.pid, 'current pid=', os.getpid())
            redis_client.set('broadcast_process_pid', p.pid)
        else:
            app.logger.info('stopping broadcast')
            redis_client.delete('broadcast_process_pid')
            print('killing pid', pid)

            try:
                os.kill(int(pid), signal.SIGTERM)
            except ProcessLookupError:
                pass

        emit('broadcast_status_updated', {
            'status': 1 if pid is None else 0
        }, broadcast=True)
        print('emit', 1 if pid is None else 0, '\n')

    @socketio.on('toggle_sim')
    def toggle_sim(data):
        """
            Starts / stops the simulation according to
            its current status

            The parameter 'data' should contain a key 'tick_step' that
            indicates the number of simulated seconds for one real second.

            An event 'sim_status_updated' will be emitted by the server to
            all connected clients with the new status of the simulation.

            When the simulation will finish, then another 'sim_status_updated' event
            will be emitted.

            When the race file is updated by the simulation, an event 'racefile' with
            all rows will be emitted to all connected clients.
        """
        try:
            tick_step = int(data['tickStep'])
        except (KeyError, ValueError):
            return

        if sim.simulation_status == 1:
            sim.stop_simulation()
        else:
            simulation = sim.get_simulation(tick_step)
            # We use 2 callbacks to track updates and status of the simulation
            socketio.start_background_task(simulation.run,
                on_file_updated=lambda rows: socketio.emit('racefile', {'rows': rows}), on_race_finished=sim.notify_simulation_status)

        sim.notify_simulation_status()

    @socketio.on('stop_sim')
    def stop_sim():
        """
            This event is emitted by the client when he wants
            to stop the simulation.

            An event 'sim_status_updated' will be sent to all connected clients.
            It will contain the status of the simulation -> 0.
        """
        sim.reset_simulation()
        sim.notify_simulation_status()

    @socketio.on('update_racefile')
    def update_racefile(data):
        """
            This event is emitted by the client when he wants
            to update the race file with some selected stages.

            The data parameter should contains a 'stages' key which is
            associated to an array where each item represents a race stage.
            An item is a pair of two bibs array : the first one is for teams
            that have started the stage and the last one is for teams that
            have finished the stage.

            :param data: event data
        """
        if 'stages' in data:
            app.logger.info('Update race file')
            socketio.start_background_task(update_racefile_thread, sim, data['stages'])

    return app


if __name__ == '__main__':
    app = create_app()
    socketio.run(app)
