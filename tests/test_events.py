from datetime import datetime
from unittest.mock import MagicMock

import jsonschema
import pytest

from uctl2_back.events import TEAM_END, create_team_end_race_event, create_team_end_stage_event, create_team_rank_event
from uctl2_back.events_schema import TEAM_OVERTAKE_SCHEMA, TEAM_RACE_END_SCHEMA, TEAM_STAGE_END_SCHEMA
from uctl2_back.race import Race
from uctl2_back.team import Team
from uctl2_back.team_state import TeamState
from uctl2_back.stage import Stage


@pytest.fixture
def default_race():
    race = Race('', [], [], 1)
    race.distance = 10
    race.length = 10

    race.stages = MagicMock()
    race.stages.__getitem__.return_value = Stage(1, '', 0, 100, True)

    race.racepoints = MagicMock()
    race.racepoints.__getitem__.return_value = (46.744681, 0.273571, 0, 210)

    return race


@pytest.fixture
def default_team(default_race):
    return Team(default_race, 1, 'foo')


@pytest.fixture
def default_team_state():
    team_state = TeamState(1, 'foo')
    team_state.start_time = datetime(year=2020, month=4, day=21)

    return team_state


def test_create_team_end_race_event(default_race, default_team_state):
    event = create_team_end_race_event(default_race, default_team_state)
    jsonschema.validate(instance=event, schema=TEAM_RACE_END_SCHEMA)


def test_create_team_end_stage_event(default_team, default_team_state):
    split_times = MagicMock()
    split_times.__getitem__.return_value = 12
    default_team_state.split_times = split_times

    stage_ranks = MagicMock()
    stage_ranks.__getitem__.return_value = 1
    default_team.stage_ranks = stage_ranks

    event = create_team_end_stage_event(default_team, default_team_state)
    jsonschema.validate(instance=event, schema=TEAM_STAGE_END_SCHEMA)


def test_create_team_rank_event(default_team, default_race):
    default_race.teams = { default_team.bib_number: default_team }

    event = create_team_rank_event(default_team, [])
    jsonschema.validate(instance=event, schema=TEAM_OVERTAKE_SCHEMA)
