import asyncio
import csv
import json
import itertools
import logging
import math
import os
import sys
import time
import urllib

import aiohttp
import requests

import events
import notifier
from race_state import RaceState, RaceStatus, computeRaceStatus
from team_state import TeamState

DEBUG_DATA_SENT = True
MAX_NETWORK_ERRORS = 10
REQUESTS_DELAY = 3


async def broadcastRace(config, session):
    """
        Broadcasts the state of the race from a race file

        :param config: a valid configuration
        :ptype config: Config | dict
    """
    logger = logging.getLogger(__name__)

    loopTime = 0
    startTime = time.time()

    state = None
    raceFile = config['raceFile']

    baseUrl = config['api']['baseUrl']
    updateRaceStatus = config['api']['actions']['updateRaceStatus']
    updateTeams = config['api']['actions']['updateTeams']

    while state is None or not state.status == RaceStatus.FINISHED:
        await asyncio.sleep(REQUESTS_DELAY)
        loopTime = int(time.time() - startTime)
        startTime = time.time()
        state = readRaceStateFromFile(raceFile, loopTime, state)

        # Stores async tasks that have to be executed
        # before the end of the loop
        tasks = []

        if state is None:
            logger.warning('The given race file does not contain any teams')
            break         
        
        if state.statusChanged():
            logger.debug('New race status : %s', state.status)
            event = {
                'race': config['raceName'],
                'status': state.status,
                'startTime': config['startTime']
            }

            tasks.append(asyncio.ensure_future(sendPostRequest(session, baseUrl, updateRaceStatus, event)))
            tasks.append(asyncio.ensure_future(notifier.broadcastEvent(events.RACE_STATUS, event)))

        # @TODO only send teams that have been updated
        """tasks.append(asyncio.ensure_future(sendPostRequest(session, baseUrl, updateTeams, {
            'teams': state.teams
        })))"""

        # Sorts teams by their covered distance, in reverse order
        # The first team in the list is the leader of the race
        sortedTeams = sorted(state.teams, key=lambda t: t.coveredDistance, reverse=True)

        for rank, team in enumerate(sortedTeams):
            # Updates rank
            team.rank = rank + 1

        for team in itertools.islice(sortedTeams, 5):
            if team.currentSegmentChanged:
                if team.currentSegment == 0:
                    id = events.TEAM_START
                elif team.currentSegment == state.segmentsNumber:
                    id = events.TEAM_END
                else:
                    id = events.TEAM_CHECKPOINT

                notifier.broadcastEventLater(id, {
                    'bibNumber': team.bibNumber,
                    'currentSegment': team.currentSegment
                })
            
            if team.rankChanged and team.rank < team.oldRank:
                notifier.broadcastEventLater(events.TEAM_OVERTAKE, {
                    'bibNumber': team.bibNumber,
                    'oldRank': team.oldRank,
                    'rank': team.rank,
                    'teams': computeOvertakenTeams(team, state.teams)
                })
        
        tasks.append(asyncio.ensure_future(notifier.broadcastEvents()))

        # Waits for all async tasks    
        if len(tasks) > 0:
            await asyncio.wait(tasks)

    logger.info('End of the broadcast')


def computeOvertakenTeams(currentTeam, teams):
        overtakenTeams = []

        for team in teams:
            if not currentTeam.bibNumber == team.bibNumber and currentTeam.oldRank > team.oldRank and currentTeam.rank < team.rank:
                overtakenTeams.append(team.bibNumber)
        
        return overtakenTeams


def computeSegmentsNumber(record):
    """
        Computes the number of segments in the given record

        The record represents a line of a race file.
        A segment is a field with the following format : Si
        with i a positive number.

        :param record: line of a race file
        :ptype record: dict
        :return: the number of segments in the given record
        :rtype: int
    """
    i = 0
    while True:
        field = 'S%d' % (i,)

        if field in record:
            i += 1
        else:
            break
    
    return i


def getInt(container, key):
    """
        Extracts an int from a dict with the given key

        If the key does not exist or the associated value
        is not an int then None is returned.

        :param container: a dict that may contains the key
        :ptype container: dict
        :param key: the key
        :ptype key: any
        :return: an integer value associated to the given key or None
        :rtype: int
    """
    if key in container:
        try:
            return int(container[key])
        except ValueError:
            return None
    
    return None


def readRaceState(reader, loopTime, lastState):
    """
        Extracts the state of the race from the given DictReader

        If a line contains invalid data, then it is skipped.

        :param reader: lines of the race file
        :ptype reader: DictReader
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype looTime: int
        :param lastState: last state of the race, could be None
        :ptype lastState: RaceState
        :return: the current state of the race
        :rtype: RaceState
    """
    logger = logging.getLogger(__name__)

    raceState = RaceState(lastState)

    totalSegmentsNumber = 0
    segmentsRead = 0

    recordsNumber = 0
    for record in reader:
        if recordsNumber == 0:
            totalSegmentsNumber = computeSegmentsNumber(record)
        raceState.segmentsNumber = totalSegmentsNumber - 1

        bibNumber = getInt(record, 'BibNumber')
        if bibNumber is None:
            logger.error('BibNumber error')
            continue
        
        splitTimes = readSplitTimes(record)
        segmentsRead += len(splitTimes)

        pace = 0
        stepDistance = 0
        segmentDistanceFromStart = 0
        averageSpeed = 0
            
        if len(splitTimes) > 0:
            currentSegmentId = len(splitTimes) - 1
            segmentDistanceFromStart = getInt(record, 'D%d' % (currentSegmentId, ))

            if segmentDistanceFromStart is None:
                logger.error('Error while reading field D%d for team %s', currentSegmentId, bibNumber)
                continue

            # Computing some estimations : average pace, covered distance since the last loop
            if segmentDistanceFromStart > 0:
                pace = splitTimes[currentSegmentId] * 1000 / segmentDistanceFromStart
                if splitTimes[currentSegmentId] > 0:
                    averageSpeed = segmentDistanceFromStart / splitTimes[currentSegmentId]
                stepDistance = averageSpeed * loopTime

        try:
            if lastState is not None:
                lastTeamState = lastState.teams[list(map(lambda t: t.bibNumber, lastState.teams)).index(bibNumber)]
            else:
                lastTeamState = None
        except ValueError:
            lastTeamState = None

        teamState = TeamState(bibNumber, lastTeamState)
        teamState.currentSegment = currentSegmentId
        teamState.pace = pace
        teamState.segmentDistanceFromStart = segmentDistanceFromStart
        teamState.stepDistance = stepDistance

        raceState.addTeam(teamState)

        recordsNumber += 1

    # Updating the status of the race for the current state
    status = computeRaceStatus(segmentsRead, totalSegmentsNumber * recordsNumber)
    raceState.setStatus(status)
    
    return raceState


def readRaceStateFromFile(filePath, loopTime, lastState):
    """
        Extracts the current state of the race from the given race file

        A race file is a csv file where values are separated by a tabulation (\t).
        If the given file can not be read then None is returned.
        If a line contains invalid data, then it is skipped.

        :param filePath: path to the file that contains race data
        :ptype filePath: str
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype loopTime: int
        :param lastState: last state of the race, could be None
        :ptype lastState: RaceState
        :return: a list of teams or False if an io erro occured
        :rtype: RaceState
    """
    logger = logging.getLogger(__name__)

    raceState = None

    try:
        with open(filePath, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')

            raceState = readRaceState(reader, loopTime, lastState)
    except IOError as e:
        logger.error('IOError : %s', e)
    
    return raceState


def readSplitTimes(record):
    """
        Extracts all split times from a line of a csv file

        A segment that did not have been exceeded by the team is represented by a split time of -1.
        The split times list only contains times of exceeded segments.
        If a conversion error occured, then False is returned.

        :param record: line to extract split times
        :ptype record: dict
        :return: a list of integers that correspond to an elapsed time in seconds
        :rtype: list
    """
    splitTimes = []

    i = 0
    # Retreiving all segments Si while Si is a valid key in record
    while True:
        segmentName = 'S%d' % (i, )
        
        value = getInt(record, segmentName)

        if value is None:
            break

        if value >= 0:
            splitTimes.append(value)
            i += 1
        else:
            # No more split times for this team
            break
    
    return splitTimes


async def sendPostRequest(session, baseUrl, action, data):
    """
        Sends a post request to the api server

        :param baseUrl: base address of the server
        :ptype baseUrl: str
        :param action: relative url to the action
        :ptype action: str
        :param data: data to send
        :ptype data: dict
        :return: True if the request was sent correctly, False if not
        :rtype: bool
    """
    logger = logging.getLogger(__name__)

    dataJson = {}
    for key, value in data.items():
        dataJson[key] = json.dumps(value)

    try:
        url = urllib.parse.urljoin(baseUrl, action)

        async with session.post(url, data=dataJson) as r:
            if DEBUG_DATA_SENT:
                logger.debug('Request sent to %s with data %s', r.url, data)
            
            if not r.status == 200:
                logger.error('Requests response error %d', r.status)
                return False

            return True
    except requests.exceptions.RequestException as e:
        logger.error('Something bad happened when trying to send a request :\n%s', e)
        return False
