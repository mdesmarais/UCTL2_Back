import asyncio
import json
import logging
import os
import signal
import sys
from multiprocessing import Process
from typing import Any, List

from flask import Flask
from flask_socketio import SocketIO, emit

from uctl2_back import race_file, uctl2
from uctl2_back.config import Config
from uctl2_back.simulator import Simulator

socketio = SocketIO()


def start_broadcast(config: Config) -> None:
    """
        Starts race broadcast

        This function should be runned in another process.
        A new event loop is created and set to asyncio, it will
        be used by the broadcast script.
    """
    print('Starting broadcast')
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    handler = logging.StreamHandler()
    formatter = logging.Formatter('[%(levelname)s] %(name)s - %(message)s')
    handler.setFormatter(formatter)

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


def create_app(config, pid) -> Flask:
    """
        Creates a new Flask app

        This app only contains socketio events, there is not http route.

        :return: instance of the new Flask app
    """
    app = Flask(__name__)
    app.broadcast_pid = pid
    socketio.init_app(app, cors_allowed_origins="*")

    sim = Simulator.create(config, socketio)
    sim.compute_times()

    def restart_broadcast(on_file_updated, on_race_finished) -> None:
        stop_broadcast()

        p = Process(target=start_broadcast, args=(config,))
        p.start()

        app.broadcast_pid = p.pid
        
        start_simulation(on_file_updated, on_race_finished)

    def start_simulation(on_file_updated, on_race_finished):
        simulation = sim.get_simulation(config.tickStep)
        socketio.start_background_task(simulation.run, on_file_updated=on_file_updated, on_race_finished=on_race_finished)
        sim.notify_simulation_status()

    def stop_broadcast(*args):
        try:
            os.kill(app.broadcast_pid, signal.SIGTERM)
            socketio.sleep(5)
            print('Killing process with pid', app.broadcast_pid)
            os.kill(app.broadcast_pid, signal.SIGKILL)
        except OSError:
            pass

    @socketio.on('connect')
    def new_client():
        emit('initialize', sim.to_json())

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
            sim.notify_simulation_status()
        else:
            if config.tickStep == tick_step:
                start_simulation(on_file_updated=lambda rows: socketio.emit('racefile', {'rows': rows}), 
                    on_race_finished=sim.notify_simulation_status)
            else:
                config.tickStep = tick_step
                socketio.start_background_task(restart_broadcast, on_file_updated=lambda rows: socketio.emit('racefile', {'rows': rows}),
                    on_race_finished=sim.notify_simulation_status)

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

    signal.signal(signal.SIGTERM, stop_broadcast)
    return app


if __name__ == '__main__':
    if len(sys.argv) == 1:
        print('Usage: uctl2.py path_to_config_file')
        configName = 'config.json'
        if not os.path.isfile(configName) and uctl2.create_default_config(configName):
            print('A default configuration %s has been created' % (configName,))
        sys.exit(-1)

    config = uctl2.load_config(os.path.abspath(sys.argv[1]))
    
    if config is False:
        print('Config error')
        sys.exit(-1)

    p = Process(target=start_broadcast, args=(config,))
    p.start()

    app = create_app(config, p.pid)
    socketio.run(app)
