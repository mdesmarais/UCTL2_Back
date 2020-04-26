import json
import pytest

from uctl2_back.race import Race
from uctl2_back.stage import Stage
from uctl2_back.team import Team


@pytest.fixture
def racepoints():
    return [
        [
            (46.667297, 0.057259, 0, 0),
            (46.671451, 0.114163, 0, 50),
            (46.689983, 0.145508, 0, 80)
        ],
        [
            (46.688430, 0.148405, 0, 100),
            (46.702982, 0.174257, 0, 160)
        ],
        [
            (46.744681, 0.273571, 0, 210),
            (46.753552, 0.309115, 0, 264),
            (46.762367, 0.332877, 0, 289)
        ]
    ]


@pytest.fixture
def default_race(racepoints):
    stages = [
        Stage(0, '', 0, 100, True),
        Stage(1, '', 100, 100, False),
        Stage(2, '', 200, 100, True)
    ]

    race = Race('', racepoints, stages, 1)
    race.distance = 200

    return race


def test_constructor(default_race):
    team = Team(default_race, 1, 'foo')

    assert team.covered_distance == 0
    assert team.progression == 0.0
    assert team.current_location == (46.667297, 0.057259)


def test_covered_distance_should_RaiseValueError_when_GivenNegativeDistance(default_race):
    team = Team(default_race, 1, 'foo')

    with pytest.raises(ValueError):
        team.covered_distance = -0.1


def test_covered_distance(default_race):
    team = Team(default_race, 1, 'foo')

    team.covered_distance = 10.5

    assert team.current_location == (46.667297, 0.057259)

    team.covered_distance = 50
    assert team.current_location == (46.671451, 0.114163)

    team.covered_distance = 85
    assert team.current_location == (46.689983, 0.145508)

    team.current_stage_index = 1

    team.covered_distance = 100
    assert team.current_location == (46.688430, 0.148405)

    team.covered_distance = 200
    assert team.current_location == (46.702982, 0.174257)

def test_covered_distance_should_UpdateProgression(default_race):
    team = Team(default_race, 1, 'foo')

    team.covered_distance = 10.5
    assert team.progression > 0

    p1 = team.progression

    team.covered_distance = 50
    assert team.progression > p1

    p2 = team.progression

    team.covered_distance = 85
    assert team.progression > p2

    p3 = team.progression

    team.current_stage_index = 1

    team.covered_distance = 100
    assert team.progression > p3


def test_serialize(default_race):
    team = Team(default_race, 1, 'foo')

    to_json = json.dumps(team.serialize())
