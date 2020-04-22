import datetime
import random
from typing import TYPE_CHECKING, Any, Dict, List, Optional, Tuple

from flask_socketio import SocketIO

from uctl2_back import race_file
from uctl2_back.config import Config
from uctl2_back.simulation import Simulation

if TYPE_CHECKING:
    from uctl2_back.stage import Stage


class Simulator:

    def __init__(self, socketio: SocketIO):
        """
            Creates a new instance of Simulator

            The constructor should not be called directly, prefer using 
            class methods create or from_json to construct a new instance.
            Some calculations are not made in this constructor but are required
            for running simulations.

            :param config: an instance to a configuration
            :param socketio: an instance to a socketio server
        """
        self.socketio = socketio
        self.headers = ['Numéro', 'Nom', 'Distance']
        self.rows: Dict[str, Any] = {}
        self.stages_inter_times: List[List[datetime.datetime]] = []
        self.race_file = ''

        self.race_distance = 0
        self.race_name = ''
        self.race_stages: List['Stage'] = []
        self.race_teams: List[Any] = []
        self.start_time: datetime.datetime = datetime.datetime.now()

        self._simulation: Optional[Simulation] = None

    @classmethod
    def create(cls, config: Config, socketio: SocketIO) -> 'Simulator':
        """
            Creates a new instance of class Simulator based on the given configuration

            This method should be used to create a new instance onstead of 
            the class constructor.

            :param config: an instance to a configuration
            :param socketio: an instance to a socketio server
            :return: a new instance of class Simulator
        """
        sim = Simulator(socketio)

        distance = 0
        j = 1

        for i, stage in enumerate(config.stages):
            if not stage.is_timed:
                continue

            distance += stage.length
            sim.headers.extend(race_file.stage_columns(j))
            j += 1

        sim.race_file = config.race_file

        sim.race_distance = distance
        sim.race_name = config.race_name
        sim.race_stages = list(config.stages)
        sim.race_teams = list(config.teams)
        sim.start_time = datetime.datetime.now()

        return sim

    def compute_times(self) -> None:
        """
            Computes simulated times for the given configuration

            Each call to this method will result of new simulated times.
        """
        stages_times: List[List[Tuple[int, int]]] = [[] for x in range(len(self.race_stages))]
        self.stages_inter_times = [[] for x in range(len(self.race_stages))]

        for team in self.race_teams:
            values = {
                'Numéro': team['bibNumber'],
                'Nom': team['name'],
                'Distance': self.race_distance / 1000
            }

            pace = team['pace']

            j = 1
            for i, stage in enumerate(self.race_stages):
                pace += pace * random.uniform(-0.2, 0.2)
                split_time = stage.length * pace / 1000

                stages_times[i].append((team['bibNumber'], split_time))
                entrance_time = self.start_time if i == 0 else self.stages_inter_times[i - 1][-1]

                inter_time = entrance_time + datetime.timedelta(seconds=split_time)
                self.stages_inter_times[i].append(inter_time)

                if stage.is_timed:
                    values['Interm (S%d)' % (j,)] = race_file.format_time(split_time)
                    values['2%d|1' % (j,)] = race_file.format_datetime(entrance_time)
                    values['3%d|1' % (j,)] = race_file.format_datetime(inter_time)
                    j+= 1

            self.rows[team['bibNumber']] = values

        stages_times_sorted = map(sort_teams_times, stages_times)

        # Computes teams rank for each stages
        j = 1
        for i, stage_times in enumerate(stages_times_sorted):
            if not self.race_stages[i].is_timed:
                continue

            for rank, stage_time in enumerate(stage_times):
                bib, _ = stage_time

                self.rows[bib]['Clt Interm-1 (S%d)' % (j,)] = rank + 1
            j += 1

    def get_simulation(self, tick_step: int) -> Simulation:
        """
            Retreives the instance of the current simulation

            If no simulation has been created already, then a new one
            will be constructed. The tick_step parameter wont be
            used in this case

            :param tick_step: number of simulated seconds for one real second
            :return: the instance of the current simulation
            :raises ValueError: if tick_step is lesser than 1
        """
        if tick_step <= 0:
            raise ValueError('tick_step must be strictely positive')

        if self._simulation is None:
            self._simulation = Simulation(self, tick_step)

        return self._simulation

    def notify_simulation_status(self):
        self.socketio.emit('sim_status_updated', {
            'status': self.simulation_status
        })

    @property
    def race_duration(self) -> int:
        """
            Gets the real duration in seconds of the simulation
        """
        max_duration = 0

        for i in range(len(self.race_teams)):
            start_time = self.stages_inter_times[0][i]
            end_time = self.stages_inter_times[-1][i]

            duration = int((end_time - start_time).total_seconds())

            if i == 0 or duration > max_duration:
                max_duration = duration

        return max_duration

    def reset_simulation(self) -> None:
        """
            Destroys the instance of the current simulation

            If there is a running simulation then it will be stopped
        """
        self.stop_simulation()
        self._simulation = None

    @property
    def simulation_status(self):
        if self._simulation is None:
            return 0
        
        return 1 if self._simulation.running else 0

    def stop_simulation(self):
        if self._simulation:
            self._simulation.running = False

    def to_json(self) -> Dict[str, Any]:
        """
            Converts class attributes into JSON compatibles types

            This method is used to serialize an instance of this class.

            :return: a dict containing class attributes
        """
        return {
            'headers': self.headers,
            'rows': self.rows,
            'stage_inter_times': [[inter_time.timestamp() for inter_time in inter_times] for inter_times in self.stages_inter_times],
            'simulation_status': self.simulation_status,
            'race_distance': self.race_distance,
            'race_duration': self.race_duration,
            'race_name': self.race_name,
            'race_stages': [stage.serialize() for stage in self.race_stages],
            'race_teams': list(self.race_teams),
            'start_time': self.start_time.timestamp() if self.start_time else 0
        }


def sort_teams_times(times):
    return sorted(times, key=lambda x: x[1])
