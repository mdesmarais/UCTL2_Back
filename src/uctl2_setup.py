from typing import List, Tuple

import gpxpy
from haversine import haversine

from config import Config
from exceptions import RaceError
from race import Race


def compute_distances(points: List[Tuple[float, float, float]]) -> List[Tuple[float, float, float, float]]:
    """
        Computes the distrance (in meters) from the start for each point

        :param points: a list of points (latitude, longitude, elevation)
        :return: a list of points with a distance from the start (latitude, longitude, elevation, distance)
    """
    if len(points) == 0:
        return []

    pointsWithDistances = []
    totalDistance = 0

    for i, point in enumerate(points):
        lat, lng, alt = point

        if i == 0:
            pointsWithDistances.append((lat, lng, alt, 0))
        else:
            # Haversine function returns a distance in kilometers
            # But we want a distance in meters
            totalDistance += haversine(coords_from_point(point), coords_from_point(points[i - 1])) * 1000

            pointsWithDistances.append((lat, lng, alt, int(totalDistance)))
    
    return pointsWithDistances


def coords_from_point(point: Tuple[float, float, float]) -> Tuple[float, float]:
    """
        Returns a coord tuple base on a given point

        A point has a latitude, longitude and an altitude.
        A coordinate only has a latitude and a longitude

        :param point: point to convert
        :return: coord
    """
    return (point[0], point[1])


def extractTrackPoints(gpxFile: gpxpy.gpx.GPX) -> List[Tuple[float, float, float]]:
    """
        Extracts trackpoints from the given gpx

        It should contain only one track and one segment.

        :param gpxFile: a GPX object
        :return: a list of points (latitude, longitude, elevation)
    """
    points = []

    for track in gpxFile.tracks:
        for segment in track.segments:
            for point in segment.points:
                # elevation is not required for a point, we need to check if it has one before use it
                points.append((point.latitude, point.longitude, point.elevation if point.elevation else 0))
    
    return points


def extractTrackPointsFromGpxFile(path: str) -> List[Tuple[float, float, float]]:
    """
        Loads gpx from the given path and extracts trackpoints

        See :func:`extractTrackPoints` for more informations.

        :param path: path to a gpx file
        :return a list of points
        :raises FileNotFoundError: if the file does not exist
    """
    with open(path, 'r') as f:
        return extractTrackPoints(gpxpy.parse(f))


def readRace(config: Config) -> Race:
    """
        Reads informations about the race in the given config

        :param config: instance of Config class
        :return: an instance of class Race which contains race informations
        :raises RaceError: if race informations can not be read from the given config
    """
    try:
        points = extractTrackPointsFromGpxFile(config.routeFile)
    except FileNotFoundError:
        raise RaceError('File does not exist')

    racePoints = compute_distances(points)
    racePointsWithStages = []
    lastRacePoint = 0

    # Race points are grouped by their stage
    for stage in config.stages:
        # d = distance from the start at the end of the stage
        d = stage['start'] + stage['length']
        stagePoints = []

        # rp = (lat, lon, alt, distance from start)
        for i, rp in enumerate(racePoints[lastRacePoint:]):
            if rp[3] <= d:
                stagePoints.append(rp)
            else:
                lastRacePoint += i - 1
                break

        racePointsWithStages.append(stagePoints)

    return Race(config.raceName, racePointsWithStages, config.stages, config.tickStep)
