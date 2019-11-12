import csv
import json
import math
import os
import requests
import time
import sys

try:
    import api_config as cfg
except ImportError:
    print('You must create an api_config module')
    sys.exit(-1)

# =======================
# == Script parameters ==
# =======================

REQUESTS_DELAY = 2 # In seconds
RACE_FILE_PATH = 'C:\\Users\\Maxime\\IdeaProjects\\UCTL2\\race.csv'
MAX_NETWORK_ERRORS = 5
DEBUG_DATA_SENT = True


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

    def __init__(self, lastState=None):
        self.lastStatus = RaceStatus.UNKNOWN
        self.teams = []

        self.status = RaceStatus.UNKNOWN if lastState is None else lastState.status

    def addTeam(self, team):
        """
            Adds a team to the current race state

            :param team: team to add
            :ptype team: dict
        """
        self.teams.append(team)

    def statusChanged(self):
        """
            Checks if the status of the race state have changed after read the race file

            :return: True if the race status have changed, False if not
            :rtype: bool
        """
        return not self.status == self.lastStatus

    def setStatus(self, status):
        """
            Changes the current status to another one

            If the new status is different than the last one, then the method statusChanged will return True.
        """
        self.lastStatus = self.status
        self.status = status


def computeRaceStatus(segmentsRead, totalSegments):
    """
        Computes the race status according to the number of segments read

        The number of segments in the race file is equal to the number of segments per line
        times the number of teams

        :param segmentsRead: number of segments read
        :ptype segmentsRead: int
        :param totalSegments: number of segments in the race file
        :ptype totalSegments: int
        :return: the status of the race
        :rtype: RaceStatus
    """
    if segmentsRead == 0:
        return RaceStatus.WAITING
    elif segmentsRead == totalSegments:
        return RaceStatus.FINISHED
    else:
        return RaceStatus.RUNNING


def computeSegmentsNumber(record):
    """
        Computes the number of segments in the given record

        The record represents a line of a race file.
        A segment is a field with the following format : Si
        with i a positive number.

        :param record: line of a race file
        :ptype record: dict
    """
    i = 0
    while True:
        field = 'S%d' % (i,)

        if field in record:
            i += 1
        else:
            break
    
    return i


def readSegmentDistance(record, segmentId):
    """
        Extracts the distance from start of the given segment

        If the given segment id does not exist or the value is not
        a valid integer, then False is returned.

        :param record: line that contains the distance of the segment
        :ptype record: dict
        :param segmentId: id of the wanted segment
        :ptype segmentId: int
        :return: the distance from start of the given segment or False if an error occurred
        :rtype: int | bool
    """
    fieldName = 'D%d' % (segmentId,)

    if fieldName in record:
        try:
            return int(record[fieldName])
        except ValueError:
            return False

    return False


def readSplitTimes(record):
    """
        Extracts all split times from a line of a csv file

        A segment that did not have been exceeded by the team is represented by a split time of -1.
        The split times list only contains times of exceeded segments.
        If a conversion error occured, then False is returned.

        :param record: line to extract split times
        :ptype record: dict
        :return: a list of integers that correspond to an elapsed time in seconds
        :rtype: int
    """
    splitTimes = []

    try:
        i = 0
        # Retreiving all segments Si while Si is a valid key in record
        while True:
            segmentName = 'S%d' % (i, )
            
            value = int(record[segmentName])
            if value >= 0:
                splitTimes.append(value)
                i += 1
            else:
                break
    except KeyError:
        pass
    except ValueError:
        print('Invalid conversion to integer for a split time')
        return False
    
    return splitTimes


def readRaceState(reader, loopTime, lastState):
    """
        Extracts the state of the race from the given DictReader

        If a line contains invalid data, then it is skipped.

        :param reader: lines of the race file
        :ptype reader: DictReader
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype loopTime: int
        :param lastState: last state of the race, may be None
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
        
        if not 'BibNumber' in record:
            print('Invalid team record, missing key "BibNumber"')
            continue

        try:
            bibNumber = int(record['BibNumber'])
        except ValueError as e:
            print('Bib number is not a valid integer :', e)
            continue
        
        splitTimes = readSplitTimes(record)
        segmentsRead += len(splitTimes)

        pace = 0
        stepDistance = 0
        segmentDistanceFromStart = 0
            
        if len(splitTimes) > 0:
            currentSegmentId = len(splitTimes) - 1
            segmentDistanceFromStart = readSegmentDistance(record, currentSegmentId)

            if segmentDistanceFromStart is False:
                print('Error while reading field D%d for team %s' % (currentSegmentId, bibNumber))
                continue

            # Computing some estimations : average pace, covered distance since the last loop
            if segmentDistanceFromStart > 0:
                pace = splitTimes[currentSegmentId] * 1000 / segmentDistanceFromStart
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


def sendRaceStatus(status):
    return sendPostRequest('updateRaceStatus', 'status', status)


def sendTeams(teams):
    return sendPostRequest('updateTeams', 'teams', teams)


def sendPostRequest(action, key, data):
    """
        Sends a post request to the api server

        :param action: relative url to the action
        :ptype action: str
        :param key: name of the parameter that contains data
        :ptype key: str
        :param data: data to send
        :ptype data: dict
        :return: True if the request was sent correctly, False if not
        :rtype: bool
    """
    try:
        r = requests.post(cfg.API_BASE_URL + cfg.API_ACTIONS[action], data={key: json.dumps(data)})

        if DEBUG_DATA_SENT:
            print('Request sent to %s with data %s' % (r.url, data))
        
        if not r.status_code == requests.codes.ok:
            print('Requests response error', r.status_code)
            return False
    except requests.exceptions.RequestException as e:
        print('Something bad happened when trying to send a request :\n', e)
        return False
    
    return True


if __name__ == '__main__':
    if REQUESTS_DELAY <= 0:
        raise ValueError('REQUESTS_DELAY must be positive !')

    if MAX_NETWORK_ERRORS < 0:
        raise ValueError('MAX_NETWORK_ERRORS must be greather than or equals to 0')

    networkErrors = 0
    loopTime = 0
    startTime = time.time()

    race = None

    while race is None or not race.status == RaceStatus.FINISHED:
        loopTime = int(time.time() - startTime)
        startTime = time.time()
        race = readRaceStateFromFile(RACE_FILE_PATH, loopTime, race)

        if race is None:
            print('The given race file does not contain any teams')
            break

        if race.statusChanged():
            print('New race status :', race.status)
        
        if race.statusChanged() and not sendRaceStatus(race.status):
            networkErrors += 1
        
        if sendTeams(race.teams) is False:
            networkErrors += 1
        
        # Prevents an infinite loop if the server is down or does not responding correctly
        if networkErrors >= MAX_NETWORK_ERRORS:
            print('Script terminated because too many network errors occured')
            break
        else:
            time.sleep(REQUESTS_DELAY)
