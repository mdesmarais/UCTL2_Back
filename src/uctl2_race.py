import asyncio
import csv
import json
import logging
import math
import os
import sys
import time
import urllib

import requests

from race_state import RaceState, RaceStatus, computeRaceStatus
import notifier

DEBUG_DATA_SENT = True
MAX_NETWORK_ERRORS = 10
REQUESTS_DELAY = 3

logger = logging.getLogger('Race')


async def broadcastRace(config):
    """
        Broadcasts the state of the race from a race file

        :param config: a valid configuration
        :ptype config: Config | dict
    """
    networkErrors = 0
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

        if state is None:
            print('The given race file does not contain any teams')
            break         
        
        if state.statusChanged():
            print('New race status :', state.status)
            event = {
                'race': config['raceName'],
                'status': state.status,
                'startTime': config['startTime']
            }
            r = sendPostRequest(baseUrl, updateRaceStatus, event)

            if not r:
                networkErrors += 1

            await notifier.broadcastEvent(1, event)
            
        
        r = sendPostRequest(baseUrl, updateTeams, {
            'teams': state.teams
        })

        if r is False:
            networkErrors += 1
        
        # Prevents an infinite loop if the server is down or does not responding correctly
        if networkErrors >= MAX_NETWORK_ERRORS:
            print('Script terminated because too many network errors occured')
            break
    
    logger.info('End of the broadcast')


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
    raceState = RaceState(lastState)

    totalSegmentsNumber = 0
    segmentsRead = 0

    recordsNumber = 0
    for record in reader:
        if recordsNumber == 0:
            totalSegmentsNumber = computeSegmentsNumber(record)

        bibNumber = getInt(record, 'BibNumber')
        if bibNumber is None:
            print('BibNumber error')
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
                print('Error while reading field D%d for team %s' % (currentSegmentId, bibNumber))
                continue

            # Computing some estimations : average pace, covered distance since the last loop
            if segmentDistanceFromStart > 0:
                pace = splitTimes[currentSegmentId] * 1000 / segmentDistanceFromStart
                if splitTimes[currentSegmentId] > 0:
                    averageSpeed = segmentDistanceFromStart / splitTimes[currentSegmentId]
                stepDistance = averageSpeed * loopTime

        raceState.addTeam({
            'bibNumber': bibNumber,
            'pace': pace,
            'stepDistance': stepDistance,
            'segmentDistanceFromStart': segmentDistanceFromStart
        })

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
    raceState = None

    try:
        with open(filePath, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')

            raceState = readRaceState(reader, loopTime, lastState)
    except IOError as e:
        print('IOError :', e)
    
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


def sendPostRequest(baseUrl, action, data):
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
    dataJson = {}
    for key, value in data.items():
        dataJson[key] = json.dumps(value)

    try:
        url = urllib.parse.urljoin(baseUrl, action)
        r = requests.post(url, data=dataJson)

        if DEBUG_DATA_SENT:
            logger.debug('Request sent to %s with data %s' % (r.url, data))
        
        if not r.status_code == requests.codes.ok:
            print('Requests response error', r.status_code)
            return False
    except requests.exceptions.RequestException as e:
        print('Something bad happened when trying to send a request :\n', e)
        return False
    
    return True
