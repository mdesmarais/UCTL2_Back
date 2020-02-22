import asyncio
import logging
import time

import events
import notifier
from race_state import RaceState, RaceStatus, readRaceStateFromFile, readRaceStateFromUrl

DEBUG_DATA_SENT = True
MAX_NETWORK_ERRORS = 10
REQUESTS_DELAY = 2


async def broadcastRace(race, config, session):
    """
        Broadcasts the state of the race from a race file

        :param config: a valid configuration
        :ptype config: Config | dict
    """
    logger = logging.getLogger(__name__)

    loopTime = 0
    currentTime = time.time()

    state = None
    firstLoop = True
    raceFile = config['raceFile']

    #baseUrl = config['api']['baseUrl']
    #updateRaceStatus = config['api']['actions']['updateRaceStatus']
    #updateTeams = config['api']['actions']['updateTeams']

    #retreiveFileUrl = urllib.parse.urljoin(baseUrl, config['api']['actions']['retreiveFile'])

    while True:
        loopTime = int(time.time() - currentTime)
        currentTime = time.time()
        #state = await readRaceStateFromFile(raceFile, config, loopTime, state, session, retreiveFileUrl)
        state = readRaceStateFromFile(raceFile, config, loopTime, state)

        # Stores async tasks that have to be executed
        # before the end of the loop
        tasks = []

        if firstLoop:
            # Doing some computations that have only be done once
            firstLoop = False

            # The distance of the race does not change during the broadcast
            race.distance = state.distance * 1000

            # Initializes teams with default values (progression, position on the map, ...)
            for team in state.teams:
                race.addTeam(team.name, team.bibNumber)
            
            # Sends the first race state (initial informations) to all connected clients
            tasks.append(notifier.broadcastEvent(events.RACE_SETUP, race.toJSON()))

        if state.status == RaceStatus.WAITING or state.status == RaceStatus.UNKNOWN:
            # If the race is not started yet, then we don't need to continue the loop
            print('waiting for race')
            continue

        if state is None:
            logger.error('Unable to read a race state from the given file')
            break

        # Sorts teams by their covered distance, in reverse order
        # The first team in the list is the leader of the race
        sortedTeams = sorted(state.teams, key=lambda t: t.coveredDistance, reverse=True)

        for rank, team in enumerate(sortedTeams):
            # Updates rank
            team.rank = rank + 1

        # @TODO compute those events only for a limited number of teams
        for teamState in sortedTeams:
            team = race.teams[teamState.bibNumber]
            race.updateTeam(team, teamState)

            if teamState.currentCheckpointChanged:
                if team.currentCheckpoint == state.checkpointsNumber:
                    id = events.TEAM_END
                else:
                    id = events.TEAM_CHECKPOINT

                lastSplitTime = teamState.splitTimes[team.currentCheckpoint]
                # Pace computation : Xs * 1000m / segment distance (in meters)
                averagePace = lastSplitTime * 1000 / race.checkpoints[team.currentCheckpoint][1]

                notifier.broadcastEventLater(id, {
                    'bibNumber': teamState.bibNumber,
                    'currentCheckpoint': team.currentCheckpoint + 1,
                    'lastCheckpoint': team.currentCheckpoint,
                    'splitTime': lastSplitTime,
                    'averagePace': averagePace
                })
            
            if teamState.rankChanged and team.rank < team.oldRank:
                notifier.broadcastEventLater(events.TEAM_OVERTAKE, {
                    'bibNumber': team.bibNumber,
                    'oldRank': team.oldRank,
                    'rank': team.rank,
                    'teams': computeOvertakenTeams(team, race.teams)
                })

            if teamState.currentCheckpointChanged or teamState.coveredDistanceChanged:
                notifier.broadcastEventLater(events.TEAM_MOVE, {
                    'bibNumber': team.bibNumber,
                    'pos': team.pos,
                    'progression': team.progression
                })
        
        tasks.append(asyncio.ensure_future(notifier.broadcastEvents()))

        # @TODO send events to db
        
        if state.statusChanged():
            logger.debug('New race status : %s', state.status)
            race.status = state.status

            if state.status == RaceStatus.RUNNING:
                # Updates race starting time with the current timestamp
                race.startTime = int(time.time())

            event = {
                'race': config['raceName'],
                'status': state.status,
                'startTime': race.startTime
            }

            tasks.append(asyncio.ensure_future(notifier.broadcastEvent(events.RACE_STATUS, event)))

        # Waits for all async tasks    
        if len(tasks) > 0:
            await asyncio.wait(tasks)
        
        if state.status == RaceStatus.FINISHED:
            break
        
        await asyncio.sleep(REQUESTS_DELAY)

    logger.info('End of the broadcast')


def computeOvertakenTeams(currentTeam, teams):
        overtakenTeams = []

        for team in teams.values():
            if not currentTeam.bibNumber == team.bibNumber and currentTeam.oldRank > team.oldRank and currentTeam.rank < team.rank:
                overtakenTeams.append(team.bibNumber)
        
        return overtakenTeams

