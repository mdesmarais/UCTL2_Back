import asyncio
import csv
import json
import io
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
from race_state import RaceState, RaceStatus
from team_state import TeamState

DEBUG_DATA_SENT = True
MAX_NETWORK_ERRORS = 10
REQUESTS_DELAY = 5

BIB_NUMBER_FORMAT = 'Numéro'
SEGMENT_NAME_FORMAT = 'Interm (S%d)'


async def broadcastRace(race, config, session):
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
    #updateTeams = config['api']['actions']['updateTeams']

    retreiveFileUrl = urllib.parse.urljoin(baseUrl, config['api']['actions']['retreiveFile'])

    while True:
        loopTime = int(time.time() - startTime)
        startTime = time.time()
        state = await readRaceStateFromFile(raceFile, config, loopTime, state, session, retreiveFileUrl)
        print('update')

        if state.status == RaceStatus.WAITING or state.status == RaceStatus.UNKNOWN:
            print('waiting for race')
            continue

        # Stores async tasks that have to be executed
        # before the end of the loop
        tasks = []

        if state is None:
            logger.warning('The given race file does not contain any teams')
            break         

        # Sorts teams by their covered distance, in reverse order
        # The first team in the list is the leader of the race
        sortedTeams = sorted(state.teams, key=lambda t: t.coveredDistance, reverse=True)

        for rank, team in enumerate(sortedTeams):
            # Updates rank
            team.rank = rank + 1

        for team in itertools.islice(sortedTeams, 5):
            if team.currentSegmentChanged:
                if team.currentSegment == state.segmentsNumber:
                    id = events.TEAM_END
                else:
                    id = events.TEAM_CHECKPOINT

                notifier.broadcastEventLater(id, {
                    'bibNumber': team.bibNumber,
                    'currentSegment': team.currentSegment + 1
                })
            
            if team.rankChanged and team.rank < team.oldRank:
                notifier.broadcastEventLater(events.TEAM_OVERTAKE, {
                    'bibNumber': team.bibNumber,
                    'oldRank': team.oldRank,
                    'rank': team.rank,
                    'teams': computeOvertakenTeams(team, state.teams)
                })

            if team.stepDistanceChanged or team.segmentDistanceFromStartChanged:
                i = 0
                while i < len(race['racePoints']) and race['racePoints'][i][3] < team.coveredDistance:
                    i += 1

                racePoint = race['racePoints'][i]
                notifier.broadcastEventLater(events.TEAM_MOVE, {
                    'bibNumber': team.bibNumber,
                    'pos': (racePoint[0], racePoint[1])
                })
        
        tasks.append(asyncio.ensure_future(notifier.broadcastEvents()))

        # @TODO send events to db
        
        if state.statusChanged():
            logger.debug('New race status : %s', state.status)
            event = {
                'race': config['raceName'],
                'status': state.status,
                'startTime': config['startTime']
            }

            #tasks.append(asyncio.ensure_future(sendPostRequest(session, baseUrl, updateRaceStatus, event)))
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
        field = SEGMENT_NAME_FORMAT % (i,)

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


def readRaceState(reader, config, loopTime, lastState):
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

    raceStarted = True
    raceFinished = True

    recordsNumber = 0
    for record in reader:
        if recordsNumber == 0:
            # Computation that only have to be done once
            totalSegmentsNumber = computeSegmentsNumber(record)

        raceState.segmentsNumber = totalSegmentsNumber - 1

        if raceStarted and record['Start'] == '0':
            raceStarted = False
        
        if raceFinished and record['Finish'] == '0':
            raceFinished = False

        bibNumber = getInt(record, BIB_NUMBER_FORMAT)
        if bibNumber is None:
            logger.error('Bib number error')
            continue
        
        splitTimes = readSplitTimes(record)
        segmentsRead += len(splitTimes)
        currentCheckpoint = -1

        pace = 0
        stepDistance = 0
        segmentDistanceFromStart = 0
        averageSpeed = 0
            
        if len(splitTimes) > 0:
            currentCheckpoint = len(splitTimes) - 1
            segmentDistanceFromStart = config['segments'][currentCheckpoint]

            if segmentDistanceFromStart is None:
                logger.error('Could not compute segment distance from start (id=%d) for team %d', currentCheckpoint, bibNumber)
                continue

            # Computing some estimations : average pace, covered distance since the last loop
            if segmentDistanceFromStart > 0:
                pace = splitTimes[currentCheckpoint] * 1000 / segmentDistanceFromStart
                if splitTimes[currentCheckpoint] > 0:
                    averageSpeed = segmentDistanceFromStart / splitTimes[currentCheckpoint]
                stepDistance = averageSpeed * loopTime

        try:
            if lastState is not None:
                lastTeamState = lastState.teams[list(map(lambda t: t.bibNumber, lastState.teams)).index(bibNumber)]
            else:
                lastTeamState = None
        except ValueError:
            lastTeamState = None

        teamState = TeamState(bibNumber, lastTeamState)
        teamState.currentSegment = currentCheckpoint if record['Finish'] == '0' else raceState.segmentsNumber
        teamState.pace = pace
        teamState.segmentDistanceFromStart = segmentDistanceFromStart
        teamState.stepDistance = stepDistance

        raceState.addTeam(teamState)

        recordsNumber += 1

    # Updating the status of the race for the current state
    if raceFinished:
        raceState.setStatus(RaceStatus.FINISHED)
    elif raceStarted:
        raceState.setStatus(RaceStatus.RUNNING)
    else:
        raceState.setStatus(RaceStatus.WAITING)
    
    return raceState


def pouet(stream):
    while not stream.at_eof():
        yield stream.readline()


async def readRaceStateFromFile(filePath, config, loopTime, lastState, session, url):
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
        print('wait for file')
        content = ''
        async with session.get(url) as r:
            content = await r.text()
            print('file downloaded')
        reader = csv.DictReader(content.split('\n'), delimiter='\t')

        raceState = readRaceState(reader, config, loopTime, lastState)
        print('state ok')
    except IOError as e:
        logger.error('IOError : %s', e)
    except aiohttp.client_exceptions.ServerDisconnectedError:
        return await readRaceStateFromFile(filePath, config, loopTime, lastState, session, url)
    
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

    i = 1
    # Retreiving all segments Si while Si is a valid key in record
    while True:
        segmentName = SEGMENT_NAME_FORMAT % (i, )
        
        value = getInt(record, segmentName)

        if value is None:
            break

        if value > 0:
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
