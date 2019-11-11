import csv
import json
import math
import os
import requests
import time

# =======================
# == Script parameters ==
# =======================

API_BASE_URL = 'http://127.0.0.1/'
API_ACTIONS = {
    'updateTeams': 'updateTeams'
}

REQUESTS_DELAY = 10 # In seconds
RACE_FILE_PATH = os.path.join('race.csv')
MAX_NETWORK_ERRORS = 5
DEBUG_DATA_SENT = True


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
        return splitTimes
    except ValueError:
        print('Invalid conversion to integer for a split time')
        return False


def readRaceFile(filePath, loopTime):
    """
        Extracts teams split times from a race file

        A race file is a csv file where values are separated by a tabulation (\t).
        If the given file can not be read then False is returned.
        If a line contains invalid data, then it is skipped.

        :param filePath: path to the file that contains race data
        :ptype filePath: str
        :param loopTime: elapsed time in seconds since the last call to this function
        :ptype loopTime: int
        :return: a list of teams or False if an io erro occured
        :rtype: list
    """
    teams = []

    try:
        with open(filePath, 'r') as f:
            reader = csv.DictReader(f, delimiter='\t')

            for teamRecord in reader:
                try:
                    bibNumber = int(teamRecord['BibNumber'])

                    splitTimes = readSplitTimes(teamRecord)

                    if len(splitTimes) == 0:
                        print('Invalid team record, no split times')
                        continue

                    currentSegmentId = len(splitTimes) - 1
                    segmentDistanceFromStart = readSegmentDistance(teamRecord, currentSegmentId)

                    if segmentDistanceFromStart is False:
                        print('Error while reading field D%d for team %s' % (currentSegmentId, teamName))
                        continue

                    # Computing some estimations : average pace, covered distance since the last loop
                    pace = splitTimes[currentSegmentId] * 1000 / segmentDistanceFromStart
                    averageSpeed = segmentDistanceFromStart / splitTimes[currentSegmentId]
                    stepDistance = averageSpeed * loopTime

                    teams.append({
                        'bibNumber': bibNumber,
                        'pace': pace,
                        'stepDistance': stepDistance
                    })

                except KeyError as e:
                    print('Invalid team record, key not found :', e)
                except ValueError as e:
                    print('Conversion from string to integer error :', e)
    except IOError as e:
        print('IOError :', e)
        return False
    
    return teams


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
        r = requests.post(API_BASE_URL + API_ACTIONS[action], data={key: json.dumps(data)})

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

    while True:
        loopTime = int(time.time() - startTime)
        startTime = time.time()
        teams = readRaceFile(RACE_FILE_PATH, loopTime)

        if teams is False:
            print('The given race file does not contain any teams')
            break

        # Prevents an infinite loop if the server is down or does not responding correctly
        if sendTeams(teams) is False:
            networkErrors += 1
        
        if networkErrors >= MAX_NETWORK_ERRORS:
            print('Script terminated because too many network errors occured')
            break
        else:
            time.sleep(REQUESTS_DELAY)
