import asyncio
import logging
import time
from typing import TYPE_CHECKING, Iterable, List, Optional

from uctl2_back import events
from uctl2_back.race_state import RaceState, RaceStatus, read_race_state_from_file
from uctl2_back.team import Team
from uctl2_back.exceptions import RaceEmptyError

if TYPE_CHECKING:
    from uctl2_back.config import Config
    from uctl2_back.notifier import Notifier
    from uctl2_back.race import Race

REQUESTS_DELAY = 2

broadcast_running = True

async def broadcastRace(race: 'Race', config: 'Config', notifier: 'Notifier', session):
    """
        Broadcasts the state of the race from a race file

        :param config: a valid configuration
    """
    logger = logging.getLogger(__name__)

    loop_time = 0
    current_time = time.time()

    state: Optional[RaceState] = None
    first_loop = True
    race_file = config.race_file

    while broadcast_running:
        loop_time = int(time.time() - current_time)
        current_time = time.time()

        try:
            state = read_race_state_from_file(race_file, config, loop_time, state)
        except IOError as e:
            logger.error(e)
            break
        except RaceEmptyError:
            logger.info('Waiting for race')
            await asyncio.sleep(REQUESTS_DELAY)
            continue

        # Stores async tasks that have to be executed
        # before the end of the loop
        tasks = []

        if first_loop:
            # Doing some computations that have only be done once
            first_loop = False

            # The distance of the race does not change during the broadcast
            race.distance = int(state.distance * 1000)

            # Initializes teams with default values (progression, position on the map, ...)
            for team_state in state.teams:
                race.add_team(team_state.bib_number, team_state.name)
            
            # Sends the first race state (initial informations) to all connected clients
            tasks.append(asyncio.ensure_future(notifier.broadcast_event(events.RACE_SETUP, race.serialize())))

        if state.status.has_changed:
            logger.debug('New race status : %s', state.status)
            race.status = state.status.get_value()

            if state.status == RaceStatus.RUNNING:
                # Updates race starting time with the current timestamp
                race.startTime = int(time.time())

            event = {
                'race': config.race_name,
                'status': state.status.get_value(),
                'startTime': race.startTime,
                'tickStep': config.tick_step
            }

            tasks.append(asyncio.ensure_future(notifier.broadcast_event(events.RACE_STATUS, event)))

            if state.status == RaceStatus.WAITING:
                race.reset_teams()
                if len(tasks) > 0:
                    await asyncio.wait(tasks)

                await asyncio.sleep(REQUESTS_DELAY)
                
                continue

        # Sorts teams by their covered distance, in reverse order
        # The first team in the list is the leader of the race
        sorted_team_states = sorted(state.teams, key=lambda team: team.covered_distance, reverse=True)

        for rank, team_state in enumerate(sorted_team_states):
            # Updates rank
            team_state.rank.set_value(rank + 1)

        # @TODO compute those events only for a limited number of teams
        for team_state in sorted_team_states:
            team = race.teams[team_state.bib_number]
            team.update_from_state(team_state)

            if team_state.current_stage.has_changed and len(team_state.intermediate_times) > 0 and not team_state.start_time is None:
                elapsed_time = team_state.intermediate_times[team.current_time_index] - team_state.start_time
                team.pace = int(elapsed_time.total_seconds() * 1000 / team.covered_distance)

                last_split_time = team_state.split_times[team.current_time_index]
                # Pace computation : Xs * 1000m / segment distance (in meters)
                average_pace = last_split_time * 1000 / race.stages[team.current_stage_index - 1].length

                notifier.broadcast_event_later(events.TEAM_CHECKPOINT, {
                    'bibNumber': team_state.bib_number,
                    'currentStage': team.current_stage_index,
                    'lastStage': team.current_stage_index - 1,
                    'splitTime': last_split_time,
                    'averagePace': average_pace,
                    'coveredDistance': team.covered_distance,
                    'pos': team.current_location,
                    'stageRank': team.last_stage_rank
                })

            if team_state.team_finished.has_changed and team_state.team_finished:
                # totalTime = sum of split times for timed stages only
                total_time = sum((x for i, x in enumerate(team_state.split_times) if race.stages[i].is_timed))
                average_pace = total_time * 1000 / race.length

                notifier.broadcast_event_later(events.TEAM_END, {
                    'bibNumber': team_state.bib_number,
                    'totalTime': total_time,
                    'averagePace': average_pace
                })
            
            if team_state.rank.has_changed and team.rank < team.old_rank:
                notifier.broadcast_event_later(events.TEAM_OVERTAKE, {
                    'bibNumber': team.bib_number,
                    'oldRank': team.old_rank,
                    'rank': team.rank,
                    'teams': compute_overtaken_teams(team, race.teams.values())
                })
        
        tasks.append(asyncio.ensure_future(notifier.broadcast_events()))

        # Waits for all async tasks    
        if len(tasks) > 0:
            await asyncio.wait(tasks)

        if state.status == RaceStatus.WAITING:
            logger.info('Waiting for race')

        await asyncio.sleep(REQUESTS_DELAY)

    logger.info('End of the broadcast')


def compute_overtaken_teams(current_team: Team, teams: Iterable[Team]) -> List[int]:
    overtaken_teams = []

    for team in teams:
        if not current_team.bib_number == team.bib_number and current_team.old_rank > team.old_rank and current_team.rank < team.rank:
            overtaken_teams.append(team.bib_number)
    
    return overtaken_teams
