import csv
import datetime
import logging
from typing import TYPE_CHECKING, List, Iterable, Optional

import aiohttp

from uctl2_back import race_file
from uctl2_back.exceptions import RaceFileFieldError
from uctl2_back.team_state import TeamState

if TYPE_CHECKING:
    from uctl2_back.config import Config


class RaceStatus:

    """
        Represents all available options for the status of the race
    """

    UNKNOWN = -1
    WAITING = 0
    RUNNING = 1
    FINISHED = 2


class RaceState:

    """
        Represents a state of the race contained in a race file
    """

    def __init__(self, last_state: Optional['RaceState']=None):
        self.last_status = RaceStatus.UNKNOWN
        self.stages_number: int = 0 if last_state is None else last_state.stages_number
        self.distance: float = 0 if last_state is None else last_state.distance
        self.teams: List[TeamState] = []

        # Sets default race status from the previous state (is there is one)
        self.status: int = RaceStatus.UNKNOWN if last_state is None else last_state.status

    def status_changed(self) -> bool:
        """
            Checks if the status of the race state have changed after read the race file

            :return: True if the race status have changed, False if not
        """
        return not self.status == self.last_status

    def set_status(self, status):
        """
            Changes the current status to another one

            If the new status is different than the last one, then the method statusChanged will return True.
        """
        self.last_status = self.status
        self.status = status


def readRaceState(reader: Iterable[race_file.Record], config: 'Config', loop_time: float, last_state: Optional[RaceState]):
    """
        Extracts the state of the race from the given DictReader

        If a line contains invalid data, then it is skipped.

        :param reader: lines of the race file
        :param loop_time: elapsed time in seconds since the last call to this function
        :param last_state: last state of the race, could be None
        :return: the current state of the race
        :rtype: RaceState
    """
    logger = logging.getLogger(__name__)

    race_state = RaceState(last_state)

    race_started = False
    race_finished = True

    index = 0

    for index, record in enumerate(reader):
        if last_state is None:
            race_state.stages_number = race_file.computeCheckpointsNumber(record)

            try:
                race_state.distance = race_file.get_key(record, race_file.DISTANCE_FORMAT, convert=float)
            except RaceFileFieldError as e:
                logger.error(e)

        try:
            bib_number: int = race_file.get_key(record, race_file.BIB_NUMBER_FORMAT, convert=int)
        except RaceFileFieldError as e:
            logger.error('Bib error : ', e)
            continue
        
        split_times = race_file.read_split_times(record)
        stages_rank = race_file.read_stage_ranks(record)

        started_stage_times = race_file.read_stage_start_times(record)
        ended_stage_times = race_file.read_stage_end_times(record)

        team_started = len(started_stage_times) > 0
        team_finished = len(ended_stage_times) == race_state.stages_number

        # Computes race state based on team state
        if team_started:
            race_started = True
        
        if not team_finished:
            race_finished = False

        if team_finished:
            current_stage = len(config.stages) - 1
        elif len(ended_stage_times) == 0:
            current_stage = 0
        else:
            # TODO
            i, j = (0, 0)
            for stage in config.stages:
                if i >= len(ended_stage_times):
                    break

                if stage.is_timed:
                    i += 1
                
                j += 1
            
            current_stage = j if len(started_stage_times) == len(ended_stage_times) else j + 1

        start_time = started_stage_times[0] if team_started else None
        current_time_index = current_stage - 1

        # todo
        i, j, k = (0, 0, 0)
        for stage in config.stages:
            if stage.is_timed:
                i += 1
                j += 1
                continue

            if i >= len(started_stage_times):
                break

            real_i = i
            split_time = int((started_stage_times[i] - ended_stage_times[i - 1]).total_seconds())
            split_times.insert(i, split_time)

            inter_time = started_stage_times[i]
            ended_stage_times.insert(i + k, inter_time)
            stages_rank.insert(i + k, 0)
            k += 1

            j += 1

        try:
            if last_state is not None:
                last_team_state: Optional[TeamState] = last_state.teams[index]
            else:
                last_team_state = None
        except ValueError:
            last_team_state = None

        intermediate_times = list(ended_stage_times)
        current_time_index = 0 if len(ended_stage_times) == 0 else current_stage - 1

        # Creates a new team state for each team in the file
        team_state = TeamState(bib_number, record[race_file.TEAM_NAME_FORMAT], last_team_state)
        team_state.current_time_index = current_time_index
        team_state.current_stage.set_value(current_stage)
        team_state.intermediate_times = intermediate_times
        team_state.split_times = split_times
        team_state.start_time = start_time
        team_state.stage_ranks = stages_rank
        team_state.team_finished.set_value(team_finished)

        if len(split_times) > 0:
            # Computing the covered distance since the last loop (step distance)
            if team_finished:
                lastStage = config.stages[current_stage - 1]
                team_state.covered_distance = lastStage.dst_from_start + lastStage.lenght
            elif team_state.current_stage.has_changed:
                team_state.covered_distance = config.stages[current_stage]['start']
            else:
                stage_dst_from_start = config.stages[current_stage]['start']

                if stage_dst_from_start > 0 and start_time:
                    if split_times[current_time_index] > 0:
                        elapsed_time = intermediate_times[current_time_index] - start_time
                        average_speed = stage_dst_from_start / elapsed_time.total_seconds()
                    team_state.covered_distance += average_speed * loop_time * config.tick_step
        elif not race_state.status == RaceStatus.RUNNING:
            team_state.covered_distance = 0
        else:
            # Default pace when we don't known each team's pace yet
            team_state.covered_distance += 2.5 * loop_time * config.tick_step

        race_state.teams.append(team_state)

    if index == 0:
        return None
    
    # Updating the status of the race for the current state
    if not race_started:
        race_state.set_status(RaceStatus.WAITING)
    elif not race_finished:
        race_state.set_status(RaceStatus.RUNNING)
    else:
        race_state.set_status(RaceStatus.FINISHED)

    return race_state


def read_race_state_from_file(file_path: str, config: 'Config', loop_time: float, last_state: Optional[RaceState]) -> RaceState:
    """
        Extracts the current state of the race from the given race file

        A race file is a csv file where values are separated by a tabulation (\t).
        If the given file can not be read then None is returned.
        If a line contains invalid data, then it is skipped.

        :param file_path: path to the file that contains race data
        :param loop_time: elapsed time in seconds since the last call to this function
        :param last_state: last state of the race, could be None
        :return: a state contained in the race file
        :raises FileNotFoundError: if the given file does not exist
        :raises IOError: if an error occured while reading the file
    """
    with open(config.race_file, 'r', encoding=config.encoding) as raceFile:
        reader = csv.DictReader(raceFile, delimiter='\t')
        return readRaceState(reader, config, loop_time, last_state)


async def read_race_state_from_url(file_path: str, config: 'Config', loop_time: float, last_state: Optional[RaceState], session: aiohttp.ClientSession, url: str) -> RaceState:
    """
        Extracts the current state of the race from the given race file

        A race file is a csv file where values are separated by a tabulation (\t).
        If the given file can not be read then None is returned.
        If a line contains invalid data, then it is skipped.

        :param file_path: path to the file that contains race data
        :param loop_time: elapsed time in seconds since the last call to this function
        :param last_state: last state of the race, could be None
        :param session: async http session
        :param url: url of the race file
        :return: a state contained in the race file
        :raises IOError: if an error occurend while reading the file
    """
    logger = logging.getLogger(__name__)

    try:
        async with session.get(url) as r:
            content = await r.text(encoding=config.encoding)
            print('file downloaded')
        reader = csv.DictReader(content.split('\n'), delimiter='\t')

        return readRaceState(reader, config, loop_time, last_state)
    except aiohttp.client_exceptions.ServerDisconnectedError:
        return await read_race_state_from_url(file_path, config, loop_time, last_state, session, url)
