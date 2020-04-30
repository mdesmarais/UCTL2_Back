"""
    This modules defines a function to broadcast
    a race file.
"""
import asyncio
import logging
import time
from typing import TYPE_CHECKING, Optional

from uctl2_back import events
from uctl2_back.race_state import RaceState, RaceStatus, read_race_state_from_file
from uctl2_back.exceptions import RaceEmptyError

if TYPE_CHECKING:
    from uctl2_back.config import Config
    from uctl2_back.notifier import Notifier
    from uctl2_back.race import Race

REQUESTS_DELAY = 2

broadcast_running = True

async def broadcast_race(race: 'Race', config: 'Config', notifier: 'Notifier', session):
    """
        Broadcasts the state of the race from a race file

        :param config: a valid configuration
    """
    logger = logging.getLogger(__name__)

    loop_time = 0
    current_time = time.time()

    state: Optional[RaceState] = None
    first_loop = True

    while broadcast_running:
        loop_time = int(time.time() - current_time)
        current_time = time.time()

        try:
            state = read_race_state_from_file(config, loop_time, state)
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
                race.start_time = int(time.time())

            event = {
                'race': config.race_name,
                'status': state.status.get_value(),
                'startTime': race.start_time,
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
            team = race.teams[team_state.bib_number]
            team.rank = rank + 1

        # @TODO compute those events only for a limited number of teams
        for team_state in sorted_team_states:
            team = race.teams[team_state.bib_number]
            team.update_from_state(team_state)

            if team_state.current_stage.has_changed and len(team_state.intermediate_times) > 0 and not team_state.start_time is None:
                elapsed_time = team_state.intermediate_times[team.current_time_index] - team_state.start_time
                team.pace = int(elapsed_time.total_seconds() * 1000 / team.covered_distance)

                event = events.create_team_end_stage_event(team, team_state)
                notifier.broadcast_event_later(event)

            if team_state.team_finished.has_changed and team_state.team_finished.get_value():
                event = events.create_team_end_race_event(race, team_state)
                notifier.broadcast_event_later(event)

            if team_state.rank.has_changed and team.rank < team.old_rank:
                event = events.create_team_rank_event(team, race.teams.values())
                notifier.broadcast_event_later(event)

        tasks.append(asyncio.ensure_future(notifier.broadcast_events()))

        # Waits for all async tasks
        if len(tasks) > 0:
            await asyncio.wait(tasks)

        if state.status == RaceStatus.WAITING:
            logger.info('Waiting for race')

        await asyncio.sleep(REQUESTS_DELAY)

    logger.info('End of the broadcast')
