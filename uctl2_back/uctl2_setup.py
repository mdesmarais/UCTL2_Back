"""
    This module is used to extract informations of the race
    from a configuration. It should be used before the broadcast
    starts and not during its execution.
"""
from typing import List, Tuple

import gpxpy
from haversine import haversine

from uctl2_back.config import Config
from uctl2_back.exceptions import RaceError
from uctl2_back.race import Race
from uctl2_back.stage import Stage

# Type aliases
Point = Tuple[float, float, float]
Points = List[Point]
PointsWithDistance = List[Tuple[float, float, float, int]]


def compute_distances(points: Points) -> PointsWithDistance:
    """
        Computes the distrance (in meters) from the start for each point

        :param points: a list of points (latitude, longitude, elevation)
        :return: a list of points with a distance from the start (latitude, longitude, elevation, distance)
    """
    points_with_distances = []
    total_distance = 0

    for i, point in enumerate(points):
        lat, lng, alt = point

        if i == 0:
            points_with_distances.append((lat, lng, alt, 0))
        else:
            # Haversine function returns a distance in kilometers
            # But we want a distance in meters
            total_distance += haversine(coords_from_point(point), coords_from_point(points[i - 1])) * 1000

            points_with_distances.append((lat, lng, alt, int(total_distance)))
    
    return points_with_distances


def coords_from_point(point: Point) -> Tuple[float, float]:
    """
        Returns a coord tuple base on a given point

        A point has a latitude, longitude and an altitude.
        A coordinate only has a latitude and a longitude

        :param point: point to convert
        :return: coord
    """
    return (point[0], point[1])


def extract_trackpoints(gpx: gpxpy.gpx.GPX) -> Points:
    """
        Extracts trackpoints from the given gpx

        It should contain only one track and one segment.

        :param gpx: a GPX object
        :return: a list of points (latitude, longitude, elevation)
    """
    points = []

    for track in gpx.tracks:
        for segment in track.segments:
            for point in segment.points:
                # elevation is not required for a point, we need to check if it has one before use it
                points.append((point.latitude, point.longitude, point.elevation if point.elevation else 0))
    
    return points


def group_racepoints(points: PointsWithDistance, stages: List[Stage]) -> List[PointsWithDistance]:
    """
        Groups racepoints by stages

        A racepoints belongs to a stage when its distance from start
        is between the distance from start of the stage and
        its length.

        :param points: a list of points with their distances (lat, long, ele, dist)
        :param stages: list of stages
    """
    racepoints_with_stages = []
    last_racepoint = 0

    # Race points are grouped by their stage
    for stage in stages:
        # d = distance from the start at the end of the stage
        d = stage.dst_from_start + stage.length
        stagepoints = []

        # rp = (lat, lon, alt, distance from start)
        for i, rp in enumerate(points[last_racepoint:]):
            if rp[3] <= d:
                stagepoints.append(rp)
            else:
                last_racepoint += i
                break

        racepoints_with_stages.append(stagepoints)
    
    return racepoints_with_stages


def read_race(config: Config) -> Race:
    """
        Reads informations about the race in the given config

        :param config: instance of Config class
        :return: an instance of class Race which contains race informations
        :raises RaceError: if race informations can not be read from the given config
    """
    try:
        with open(config.route_file, 'r') as fIn:
            gpx = gpxpy.parse(fIn)
            points = extract_trackpoints(gpx)
    except FileNotFoundError:
        raise RaceError('File does not exist')
    except (gpxpy.gpx.GPXException, gpxpy.gpx.GPXXMLSyntaxException) as e:
        raise RaceError(e)

    racepoints = compute_distances(points)
    racepoints_with_stages = group_racepoints(racepoints, config.stages)

    return Race(config.race_name, racepoints_with_stages, config.stages, config.tick_step)
