import pytest
from datetime import datetime

from uctl2_back.team_state import TeamState, TransitionTime
from uctl2_back.stage import Stage


@pytest.fixture
def team_state():
    return TeamState(1, 'foo')


@pytest.fixture
def stages():
    return [
        Stage(0, '', 0, 100, True),
        Stage(1, '', 100, 100, False),
        Stage(2, '', 200, 100, True),
        Stage(3, '', 300, 100, False),
        Stage(4, '', 400, 100, True),
    ]


def test_constructor():
    with pytest.raises(ValueError):
        TeamState(-1, '')
    
    with pytest.raises(ValueError):
        TeamState(0, '')


def test_update_covered_distance_should_RaiseValueError_when_GivenNegativePace(team_state, stages):
    with pytest.raises(ValueError):
        team_state.update_covered_distance(stages, 34, 89, -7)
    
    with pytest.raises(ValueError):
        team_state.update_covered_distance(stages, 798, 16, 0)


def test_update_covered_distance_when_TeamNotStartYet(team_state, stages):
    team_state.update_covered_distance(stages, 0, 0.0)
    assert 0 == team_state.covered_distance


def test_update_covered_distance_when_TeamIsInFirstStage(team_state, stages):
    team_state.start_time = datetime(2020, 4, 21)

    team_state.update_covered_distance(stages, 4, 60, default_pace=240)
    assert 1000 == team_state.covered_distance


def test_update_covered_distance_when_TeamFinished(team_state, stages):
    team_state.start_time = datetime(2020, 4, 21)
    team_state.team_finished.set_value(True)
    race_length = stages[-1].dst_from_start + stages[-1].length

    team_state.update_covered_distance(stages, 4, 60)
    assert race_length == team_state.covered_distance


def test_update_covered_distance_when_TeamChangedStage(team_state, stages):
    team_state.current_stage.set_value(0)
    team_state.current_stage.set_value(4)
    team_state.start_time = datetime.now()
    team_state.split_times = [ 10, 10, 10 ]

    team_state.update_covered_distance(stages, 40, 1)
    assert 400 == team_state.covered_distance


def test_update_covered_distance(team_state, stages):
    team_state.current_stage.set_value(1)
    team_state.current_stage.set_value(1)
    team_state.current_time_index = 0
    team_state.covered_distance = 100

    team_state.start_time = datetime(2020, 4, 21, hour=10)
    team_state.split_times = [ 24 ]

    # with a pace of 240 secondes for 1km, we have 24 secondes for 100m
    # it the length of all stages
    team_state.intermediate_times = [
        datetime(2020, 4, 21, hour=10, second=24)
    ]

    team_state.update_covered_distance(stages, 4, 60)
    assert 1100 == team_state.covered_distance

def test_update_stage_times(team_state, stages):
    inter1 = datetime(2020, 4, 21, hour=12)
    inter2 = datetime(2020, 4, 21, hour=14)

    transition_times = [
        TransitionTime(relative_index=1, split_time=3600, inter_time=inter1),
        TransitionTime(relative_index=2, split_time=3600, inter_time=inter2)
    ]

    random_date = datetime(year=2020, month=4, day=21)

    team_state.intermediate_times = [random_date, random_date, random_date, random_date]
    team_state.split_times = [0, 0, 0, 0]
    team_state.stage_ranks = [4, 4, 4, 4]

    team_state.update_stage_times(transition_times)

    assert team_state.intermediate_times == [random_date, inter1, random_date, inter2, random_date, random_date]
    assert team_state.split_times == [0, 3600, 0, 3600, 0, 0]

