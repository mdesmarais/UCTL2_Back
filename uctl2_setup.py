import json
import urllib

import gpxpy
import requests
from haversine import haversine


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
        :ptype config: Config | dict
        :return: a dict containing some informations (teams, race points, ...)
            about the race or False if an error occured
        :rtype: dict | bool
    """
    routeFile = config['routeFile']
    if routeFile.endswith('.gpx'):
        points = extractTrackPointsFromGpxFile(routeFile)
    else:
        points = extractRacePointsFromJsonFile(routeFile)

    if points is False:
        return False

    return {
        'teams': config['teams'],
        'racePoints': computeDistances(points),
        'infos': {
            'name': config['raceName'],
            'type': 'trail',
            'startTime': config['startTime']
        }
    }


def sendRace(race, baseUrl, action):
    """
        Sends the race (infos, teams, points) to a server throught post method

        :param race: informations about the race
        :ptype race: dict
        :return: true if the race was correctly sent to the server, false if not
        :rtype: bool
    """
    try:
        url = urllib.parse.urljoin(baseUrl, action)
        r = requests.post(url, data={"race": json.dumps(race)})

        #print(json.dumps(race))

        if not r.status_code == requests.codes.ok:
            print('Requests response error:', r.status_code)
            print(r.content)
            return False
    except requests.exceptions.RequestException as e:
        print('Something bad happened when trying to send a request\n->', e)
        return False

    return True
