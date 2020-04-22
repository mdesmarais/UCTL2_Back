import collections
import csv
import datetime
import logging
from typing import TYPE_CHECKING, List, Iterable, Optional, Tuple

import aiohttp

from uctl2_back import race_file
from uctl2_back.exceptions import RaceEmptyError, RaceFileFieldError
from uctl2_back.team_state import TeamState
from uctl2_back.watched_property import WatchedProperty

if TYPE_CHECKING:
    from uctl2_back.config import Config
    from uctl2_back.stage import Stage

# Type alias
RaceTimes = List[datetime.datetime]

TransitionTime = collections.namedtuple('TransitionTime', ['split_time', 'inter_time', 'relative_index'])


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


def compute_covered_distance(team_state: TeamState, team_finished: bool, stages: List['Stage'], tick_step: int, loop_time: float, default_pace: int=300) -> float:
    """
        Computes an estimated covered distance for the given team state

        If the team does not have started the race yet then 0 will be returned.
        If the team is in the first state, then the default_pace parameter will
        be used. It the number of seconds for 1km.
        The the team already have finished the race, then the function will return
        the distance from start of the last stage.
        If the team have moved into another stage, then the function will
        return the distance from the start of the current checkpoint.

        :param team_state: instance of TeamState
        :param team_finished: indicates whether or not team has finished the race
        :param stages: list of stages
        :param tick_step: speed of the simulation (=1 if it is a real race)
        :param loop_time: number of seconds since the last call to the parent function
        :param default_pace: default pace in seconds (for 1km)
        :return: an estimated covered distance
    """
    if default_pace <= 0:
        raise ValueError('default pace must be strictely positive')

    intermediate_times = team_state.intermediate_times
    split_times = team_state.split_times
    start_time = team_state.start_time

    if start_time is None:
        return 0

    if team_finished:
        last_stage = stages[-1]
        return last_stage.dst_from_start + last_stage.length

    if len(split_times) == 0:
        # Default pace when we don't known each team's pace yet
        return team_state.covered_distance + loop_time * tick_step * 1000 / default_pace

    current_stage_index: int = team_state.current_stage.get_value()

    # Computing the covered distance since the last loop (step distance)
    if team_state.current_stage.has_changed:
        return stages[current_stage_index].dst_from_start
    else:
        stage_dst_from_start = stages[current_stage_index].dst_from_start

        elapsed_time = intermediate_times[team_state.current_time_index] - start_time
        average_speed = stage_dst_from_start / elapsed_time.total_seconds()
        return team_state.covered_distance + average_speed * loop_time * tick_step


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


def get_race_status(race_started: bool, race_finished: bool) -> int:
    """
        Gets the status of the race

        The 2 boolean parameters do not represent the real status of the race.
        They are computed by reading the race file for each team :
        If a team are in stage then the race is running.
        If all teams have finished all stages then race_finished will be true.

        If given booleans are not coherent : the race is not started
        but it is finished, then :attr:`RaceStatus.UNKNOWN` will be returned.
        
        :param race_started: indicates whether if the race is started or not
        :param race_finished: indicates whether is the race is finished or not
        :return: the status of the race
    """
    if not race_started:
        return RaceStatus.UNKNOWN if race_finished else RaceStatus.WAITING
    elif not race_finished:
        return RaceStatus.RUNNING
    else:
        return RaceStatus.FINISHED


def read_race_state(reader: Iterable[race_file.Record], config: 'Config', loop_time: float, last_state: Optional[RaceState]):
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
        update_stage_times(team_state, transition_times)

        if race_state.status.get_value() == RaceStatus.RUNNING:
            team_state.covered_distance = compute_covered_distance(team_state, team_finished, config.stages, config.tick_step, loop_time)
        else:
            team_state.covered_distance = 0

        race_state.teams.append(team_state)

    if len(race_state.teams) == 0:
        raise RaceEmptyError('coup dur')
    
    # Updating the status of the race for the current state
    race_state.status.set_value(get_race_status(race_started, race_finished))

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


def update_stage_times(team_state: TeamState, transition_times: List[TransitionTime]) -> None:
    """
        Updates times list of a team state with transition times

        Only lists :attr:`TeamState.intermediate_times`, :attr:`TeamState.split_times`, :attr:`TeamState.stage_ranks`
        are modified. The last one will be updated with 0s : we do not compute a rank for non timed stages.

        :param team_state: the state that will be updated with transition times
        :param transition_times: transitions times to add for the given state
    """
    for i, transition_time in enumerate(transition_times):
        team_state.intermediate_times.insert(transition_time.relative_index + i, transition_time.inter_time)
        team_state.split_times.insert(transition_time.relative_index + i, transition_time.split_time)
        team_state.stage_ranks.insert(transition_time.relative_index + i, 0)
