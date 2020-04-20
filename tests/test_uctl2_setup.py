from unittest.mock import MagicMock

import gpxpy
import pytest

from uctl2_back.stage import Stage
from uctl2_back.uctl2_setup import *


@pytest.fixture
def gpx_factory():
    def _gpx_factory(points=[]):
        segment = MagicMock()
        segment.points = points

        track = MagicMock()
        track.segments = [segment]

        gpx = MagicMock()
        gpx.tracks = [track]

        return gpx
    
    return _gpx_factory


def make_mock_point(point):
    m = MagicMock()
    m.latitude = point[0]
    m.longitude = point[1]
    m.elevation = point[2] if len(point) > 2 else None

    return m


def test_coords_from_point():
    point = (48.862725, 2.287592, 250)
    expected = (48.862725, 2.287592)

    assert expected == coords_from_point(point)

def test_compute_distances():
    points = [
        (48.531333, -1.409535, 4),
        (48.457520, -1.557404, 0),
        (48.430432, -1.674234, 1)
    ]

    result = compute_distances(points)

    assert len(result) == 3

    assert points[0] == result[0][:-1]
    assert result[0][3] == 0

    assert points[1] == result[1][:-1]
    assert result[1][3] > 0

    assert points[2] == result[2][:-1]
    assert result[2][3] > result[1][3]

def test_extract_trackpoints(gpx_factory):
    points = [
        make_mock_point((48.531333, -1.409535, 4)),
        make_mock_point((48.457520, -1.557404)),
        make_mock_point((48.430432, -1.674234, 1))
    ]

    expected = [
        (48.531333, -1.409535, 4),
        (48.457520, -1.557404, 0),
        (48.430432, -1.674234, 1)
    ]

    gpx = gpx_factory(points)

    result = extract_trackpoints(gpx)

    assert result == expected

def test_group_racepoints():
    stages = [
        Stage(0, '', 0, 2000, True),
        Stage(1, '', 2000, 500, True)
    ]

    points = [
        (48.531333, -1.409535, 4, 0),
        (48.457520, -1.557404, 0, 800),
        (48.430432, -1.674234, 1, 2000),
        (48.542577, -2.078059, 0, 2500),
        (48.542414, -2.084754, 0, 2501)
    ]

    result = group_racepoints(points, stages)

    # We must have 2 stages
    assert len(result) == 2
    assert result[0] == [points[0], points[1], points[2]]
    assert result[1] == [points[3]]
