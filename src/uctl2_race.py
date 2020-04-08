import asyncio
import logging
import time

import events
from race_state import RaceState, RaceStatus, readRaceStateFromFile, readRaceStateFromUrl

REQUESTS_DELAY = 2

broadcast_running = True

async def broadcastRace(race, config, notifier, session):
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
    raceFile = config.raceFile

    while broadcast_running:
        loopTime = int(time.time() - currentTime)
        currentTime = time.time()
        state = readRaceStateFromFile(raceFile, config, loopTime, state)

        # Stores async tasks that have to be executed
        # before the end of the loop
        tasks = []

        if state is None:
            logger.error('state is None')
            break

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

        if state.statusChanged():
            logger.debug('New race status : %s', state.status)
            race.status = state.status

            if state.status == RaceStatus.RUNNING:
                # Updates race starting time with the current timestamp
                race.startTime = int(time.time())

            event = {
                'race': config.raceName,
                'status': state.status,
                'startTime': race.startTime,
                'tickStep': config.tickStep
            }

            tasks.append(asyncio.ensure_future(notifier.broadcastEvent(events.RACE_STATUS, event)))

            if state.status == RaceStatus.WAITING:
                race.resetTeams()
                if len(tasks) > 0:
                    await asyncio.wait(tasks)

                await asyncio.sleep(REQUESTS_DELAY)
                
                continue

        # Sorts teams by their covered distance, in reverse order
        # The first team in the list is the leader of the race
        sortedTeams = sorted(state.teams, key=lambda team: team.coveredDistance, reverse=True)

        for rank, team in enumerate(sortedTeams):
            # Updates rank
            team.rank = rank + 1

        # @TODO compute those events only for a limited number of teams
        for teamState in sortedTeams:
            team = race.teams[teamState.bibNumber]
            race.updateTeam(team, teamState)

            if teamState.currentStageChanged and len(teamState.intermediateTimes) > 0:
                elapsedTime = teamState.intermediateTimes[team.currentTimeIndex] - teamState.startTime
                team.pace = elapsedTime.total_seconds() * 1000 / team.coveredDistance

                lastSplitTime = teamState.splitTimes[team.currentTimeIndex]
                # Pace computation : Xs * 1000m / segment distance (in meters)
                averagePace = lastSplitTime * 1000 / race.stages[team.currentStage - 1]['length']

                notifier.broadcastEventLater(events.TEAM_CHECKPOINT, {
                    'bibNumber': teamState.bibNumber,
                    'currentStage': team.currentStage,
                    'lastStage': team.currentStage - 1,
                    'splitTime': lastSplitTime,
                    'averagePace': averagePace,
                    'coveredDistance': team.coveredDistance,
                    'pos': team.pos,
                    'stageRank': team.lastStageRank
                })

            if teamState.teamFinishedChanged and teamState.teamFinished:
                # totalTime = sum of split times for timed stages only
                totalTime = sum((x for i, x in enumerate(teamState.splitTimes) if race.stages[i]['timed']))
                averagePace = totalTime * 1000 / race.length

                notifier.broadcastEventLater(events.TEAM_END, {
                    'bibNumber': teamState.bibNumber,
                    'totalTime': totalTime,
                    'averagePace': averagePace
                })
            
            if teamState.rankChanged and team.rank < team.oldRank:
                notifier.broadcastEventLater(events.TEAM_OVERTAKE, {
                    'bibNumber': team.bibNumber,
                    'oldRank': team.oldRank,
                    'rank': team.rank,
                    'teams': computeOvertakenTeams(team, race.teams)
                })
        
        tasks.append(asyncio.ensure_future(notifier.broadcastEvents()))

        # Waits for all async tasks    
        if len(tasks) > 0:
            await asyncio.wait(tasks)

        if state.status == RaceStatus.WAITING:
            logger.info('Waiting for race')

        await asyncio.sleep(REQUESTS_DELAY)

    logger.info('End of the broadcast')


def computeOvertakenTeams(currentTeam, teams):
        overtakenTeams = []

        for team in teams.values():
            if not currentTeam.bibNumber == team.bibNumber and currentTeam.oldRank > team.oldRank and currentTeam.rank < team.rank:
                overtakenTeams.append(team.bibNumber)
        
        return overtakenTeams

