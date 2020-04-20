import datetime
import time
from typing import Any, Callable, List

from uctl2_back.race_file import process_file


class Simulation:

    def __init__(self, simulator: 'Simulator', tick_step: int):
        self.simulator = simulator
        self.tick_step = tick_step

        self.stages_with_times = [[set(), set()] for stage in simulator.race_stages if stage['timed']]
        self.race_time = simulator.start_time
        self.remaining_teams = list(simulator.race_teams)
        self.running = False

    def run(self, on_file_updated: Callable[[List[Any]], Any]=None, on_race_finished=Callable[[], Any]):
        last_call = time.time()
        self.running = True

        while self.running:
            current_time = time.time()
            loop_time = current_time - last_call
            last_call = current_time

            self.race_time += datetime.timedelta(seconds=self.tick_step * loop_time)

            stage_time_index = 0
            for i, stage in enumerate(self.simulator.race_stages):
                if not stage['timed']:
                    continue

                stage_times = self.stages_with_times[stage_time_index]
                stage_time_index += 1

                for j, team in enumerate(self.remaining_teams):
                    if i == 0 or self.simulator.stages_inter_times[i - 1][j] <= self.race_time:
                        stage_times[0].add(team['bibNumber'])

                    if self.simulator.stages_inter_times[i][j] <= self.race_time:
                        stage_times[1].add(team['bibNumber'])

                        if stage_time_index == len(self.stages_with_times):
                            self.remaining_teams.pop(j)

            rows = process_file(self.simulator, self.stages_with_times)
            if not on_file_updated is None:
                on_file_updated(rows)

            if len(self.remaining_teams) == 0:
                self.running = False
                self.simulator.reset_simulation()

                if not on_race_finished is None:
                    on_race_finished()
                break

            self.simulator.socketio.sleep(1)
