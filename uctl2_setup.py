from datetime import datetime
from haversine import haversine
import gpxpy
import json
import requests
import sys


API_URL = 'http://google.fr'


def computeDistances(points):
    """
        Computes the distrance (in meters) from the start for each point

        :param points: a list of points (latitude, longitude, elevation)
        :ptype points: list
        :return: a list of points with a distance from the start (latitude, longitude, elevation, distance)
        :rtype: list
    """
    if len(points) == 0:
        return []

    pointsWithDistances = []
    totalDistance = 0

    coordsFromPoint = lambda p: (p[0], p[1])

    for i, point in enumerate(points):
        lat, lng, alt = point

        if i == 0:
            pointsWithDistances.append((lat, lng, alt, 0))
        else:
            # Haversine function returns a distance in kilometers
            # But we want a distance in meters
            totalDistance += haversine(coordsFromPoint(point), coordsFromPoint(points[i - 1])) * 1000

            pointsWithDistances.append((lat, lng, alt, int(totalDistance)))
    
    return pointsWithDistances


def extractTeams(config):
    """
        Extracts teams for the given configuration

        This function allows the selection of some elements for each team.
        Each team is represented by a name and a bib number.

        :param config: a configuration
        :ptype config: dict
        :return: a list of teams
        :rtype: list
    """
    teams = []

    for team in config['teams']:
        teams.append({
            'name': team['name'],
            'bibNumber': team['bib']
        })
    
    return teams


def extractTrackPoints(gpxFile):
    """
        Extracts trackpoints from the given gpx

        It should contain only one track and one segment.

        :param gpxFile: a GPX object
        :ptype gpxFile: gpxpy.GPX
        :return: a list of points (latitude, longitude, elevation)
        :rtype: list
    """
    points = []

    for track in gpxFile.tracks:
        for segment in track.segments:
            for point in segment.points:
                points.append((point.latitude, point.longitude, point.elevation))
    
    return points


def extractTrackPointsFromGpxFile(path):
    with open(path, 'r') as f:
        return extractTrackPoints(gpxpy.parse(f))


def extractRacePoints(points):
    """
        Extracts race points from the given list

        Checks the validity of the input.
        If a point does not have an elevation, then a default one will be set (0.0).

        :param points: a list of points
        :ptype points: list
        :return: a list of points (latitude, longitude, elevation)
        :rtype: list
    """
    racePoints = []

    for point in points:
        if len(point) < 2:
            print('A point must have at least 2 elements : latitude, longitude, ?elevation')
            continue

        lat = point[0]
        lon = point[1]

        if len(point) >= 3:
            ele = point[2]
        else:
            ele = 0.0
        
        racePoints.append((lat, lon, ele))
    
    return racePoints


def extractRacePointsFromJsonFile(path):
    with open(path, 'r') as f:
        pointsFile = json.load(f)
        if 'points' in pointsFile:
            return extractRacePoints(pointsFile['points'])
        else:
            print('Missing points key')
            return False


def readRace(config):
    """
        Reads informations about the race in the given config

        :param config: a valid configuration
        :ptype config: dict
        :return: a dict containing some informations (teams, race points, ...)
            about the race or False if an error occured
        :rtype: dict | bool
    """
    if 'gpxFile' in config:
        points = extractTrackPointsFromGpxFile(config['gpxFile'])
    elif 'pointsFile' in config:
        points = extractRacePointsFromJsonFile(config['pointsFile'])
    else:
        print('You must provide a gpx file (key gpxFile) or a json file (key pointsFile)')
        return False

    if points is False:
        return False

    return {
        'teams': extractTeams(config),
        'racePoints': computeDistances(points),
        'infos': {
            'name': config['raceName'],
            'type': 'trail',
            'startTime': config['startTime']
        }
    }


def sendRace(race):
    """
        Sends the race (infos, teams, points) to a server throught post method

        :param race: informations about the race
        :ptype race: dict
        :return: true if the race was correctly sent to the server, false if not
        :rtype: bool
    """
    try:
        r = requests.post(API_URL, data={"race": json.dumps(race)})

        #print(json.dumps(race))

        if not r.status_code == requests.codes.ok:
            print('Requests response error:', r.status_code)
            return False
    except requests.exceptions.RequestException as e:
        print('Something bad happened when trying to send a request :', e)
        return False

    return True


def validateConfig(config):
    """
        Checks if the given configuration is valid

        A configuration is valid when all required fields have a value and the value
        satisfies conditions.

        :param config: the configuration to check
        :ptype config: dict
        :return: True is the configuration is valid, false if not
        :rtype: bool
    """
    if not 'raceName' in config:
        print('WARNING : You should provide a name for the race (key raceName)')
        config['raceName'] = 'Unknown'

    if not 'teams' in config:
        print('Missing "teams" key')
        return False

    if not 'startTime' in config:
        print('Missing start time for the race')
        return False

    try:
        datetime.fromtimestamp(config['startTime'])
    except Exception as e:
        print('Race start time is not a valid timestamp:')
        return False
    
    bibs = []
    for i, team in enumerate(config['teams']):
        teamNumber = i + 1

        if not 'name' in team:
            print('Missing name for team', teamNumber)
            return False
        
        if 'bib' in team:
            try:
                team['bib'] = int(team['bib'])
            except ValueError:
                print('Bib number is not a valid integer for team', teamNumber)
                return False
        
        if len(team['name']) == 0:
            print('Team name can not be empty for team', teamNumber)
            return False

        bibNumber = team['bib']
        if bibNumber <= 0:
            print('Bib number must be positive for team', teamNumber)
            return False

        # Checks if each team has a unique bib number
        if bibNumber in bibs:
            print('Bib number must be unique for team', teamNumber)
            return False
        else:
            bibs.append(bibNumber)

    if len(bibs) == 0:
        print('At least one team is required')
        return False
    
    return True


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage : uctl2_setup.py config_file')
        sys.exit(-1)
    
    configPath = sys.argv[1]

    race = False
    print('Reading configuration')
    try:
        with open(configPath, 'r') as f:
            config = json.load(f)

            if validateConfig(config) is False:
                print('Invalid configuration')
            else:
                print('Extracting race informations')
                race = readRace(config)
    except FileNotFoundError as e:
        print('Unable to read file', e)
        sys.exit(-1)
    
    if race is not False:
        print('Sending request')
        sendRace(race)