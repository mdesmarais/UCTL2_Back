import csv
import datetime
import logging
from typing import TYPE_CHECKING, List, Iterable, Optional, Tuple

import aiohttp

from uctl2_back import race_file
from uctl2_back.exceptions import RaceEmptyError, RaceFileFieldError
from uctl2_back.team_state import TeamState, TransitionTime
from uctl2_back.watched_property import WatchedProperty

if TYPE_CHECKING:
    from uctl2_back.config import Config
    from uctl2_back.stage import Stage

# Type alias
RaceTimes = List[datetime.datetime]


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
        self.stages_number: int = 0 if last_state is None else last_state.stages_number
        self.distance: float = 0 if last_state is None else last_state.distance
        self.teams: List[TeamState] = []

        # Sets default race status from the previous state (is there is one)
        self.status: WatchedProperty = WatchedProperty(RaceStatus.UNKNOWN if last_state is None else last_state.status.get_value())

    def update_race_status(self, race_started: bool, race_finished: bool) -> None:
        """
            Updates the status of the race

            The 2 boolean parameters do not represent the real status of the race.
            They are computed by reading the race file for each team :
            If a team are in stage then the race is running.
            If all teams have finished all stages then race_finished will be true.

            If given booleans are not coherent : the race is not started
            but it is finished, then :attr:`RaceStatus.UNKNOWN` will be set.
            
            :param race_started: indicates whether if the race is started or not
            :param race_finished: indicates whether is the race is finished or not
        """
        if not race_started:
            self.status.set_value(RaceStatus.UNKNOWN if race_finished else RaceStatus.WAITING)
        elif not race_finished:
            self.status.set_value(RaceStatus.RUNNING)
        else:
            self.status.set_value(RaceStatus.FINISHED)


def compute_transition_times(current_stage_index: int, started_stage_times: RaceTimes, ended_stage_times: RaceTimes, stages: List['Stage']) -> List[TransitionTime]:
    """
        Computes a list of times for non timed stages

        This function returns a namedtuple that contains
        a split time (in seconds), an intermediate time (datetime)
        and a relative index -> it represents the target position in times list
        such as :attr:`TeamState:split_times` or :attr:`TeamState:intermediate_times`.

        The result of this function should be used by :func:`update_stage_times`

        :param current_stage_index: index of the current stage (in the global list)
        :param started_stage_times: date times for timed stages that the team have already started
        :param ended_stage_times: date times for timed stages that the team have finished
        :param stages: list of stages
        :return: list of transition times
    """
    timed_stage_index = 0

    transitions: List[TransitionTime] = []

    for stage_index, stage in enumerate(stages):
        if stage_index >= current_stage_index:
            break

        if stage.is_timed:
            timed_stage_index += 1
            continue

        transition_split_time = int((started_stage_times[timed_stage_index] - ended_stage_times[timed_stage_index - 1]).total_seconds())
        transition_inter_time = started_stage_times[timed_stage_index]

        transition_time = TransitionTime(split_time=transition_split_time, inter_time=transition_inter_time, relative_index=timed_stage_index)
        transitions.append(transition_time)

    return transitions


def get_current_stage_index(started_stages:int, completed_stages: int, stages: List['Stage']) -> int:
    """
        Finds the index of the current stage

        In the race file, we only have times for timed checkpoints.
        However, in the broadcaster, we have a time for every checkpoints,
        even if one is not timed.
        This function find the index of current stage stage by using the
        number of completed and started stages (timed only).

        Only works when the first stage is timed and all following stages
        are alternate : timed, not timed, timed, not timed, ...

        :param started_stages: number of started stages
        :param completed_stages: number of completed stages
        :param stages: list of stages
        :return: index of the last completed stages
        :raises ValueError: if completed_stages or started_stages is negative
        :raises quelquechose: if the index could not been found
    """
    if started_stages < 0:
        raise ValueError('number of started stages must be positive')

    if completed_stages < 0:
        raise ValueError('number of completed timed stages must be positive')

    if started_stages == 0 or completed_stages == 0:
        return 0

    timed_stage_index = 0
    for stage_index, stage in enumerate(stages):
        if timed_stage_index >= completed_stages:
            break

        if stage.is_timed:
            timed_stage_index += 1
    
    return stage_index if started_stages == completed_stages else stage_index + 1


def read_race_state(reader: Iterable[race_file.Record], config: 'Config', loop_time: float, last_state: Optional[RaceState]) -> RaceState:
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

    for index, record in enumerate(reader):
        if last_state is None and index == 0:
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
        else:
            current_stage = get_current_stage_index(len(started_stage_times), len(ended_stage_times), config.stages)

        start_time = started_stage_times[0] if team_started else None
        current_time_index = current_stage - 1

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

        transition_times = compute_transition_times(current_stage, started_stage_times, ended_stage_times, config.stages)
        team_state.update_stage_times(transition_times)

        if race_started:
            team_state.update_covered_distance(config.stages, config.tick_step, loop_time)
        else:
            team_state.covered_distance = 0

        race_state.teams.append(team_state)

    if len(race_state.teams) == 0:
        raise RaceEmptyError('coup dur')

    race_state.update_race_status(race_started, race_finished)

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
        return read_race_state(reader, config, loop_time, last_state)


"""async def read_race_state_from_url(file_path: str, config: 'Config', loop_time: float, last_state: Optional[RaceState], session: aiohttp.ClientSession, url: str) -> RaceState:
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
    logger = logging.getLogger(__name__)

    try:
        async with session.get(url) as r:
            content = await r.text(encoding=config.encoding)
            print('file downloaded')
        reader = csv.DictReader(content.split('\n'), delimiter='\t')

        return read_race_state(reader, config, loop_time, last_state)
    except aiohttp.client_exceptions.ServerDisconnectedError:
        return await read_race_state_from_url(file_path, config, loop_time, last_state, session, url)"""

