import pytest
from datetime import datetime
from unittest.mock import MagicMock

from uctl2_back.race_state import RaceStatus, TransitionTime, compute_covered_distance, compute_transition_times, get_current_stage_index, get_race_status, update_stage_times
from uctl2_back.stage import Stage
from uctl2_back.team_state import TeamState


@pytest.fixture
def stages():
    return [
        Stage(0, '', 0, 100, True),
        Stage(1, '', 100, 100, False),
        Stage(2, '', 200, 100, True),
        Stage(3, '', 300, 100, False),
        Stage(4, '', 400, 100, True),
    ]

def test_get_current_stage_index_should_RaiseValueError_when_GivenNegativeParameter():
    with pytest.raises(ValueError):
        get_current_stage_index(-1, 4, [])
    
    with pytest.raises(ValueError):
        get_current_stage_index(8, -2, [])

def test_get_current_stage(stages):
    assert 0 == get_current_stage_index(0, 0, stages)
    assert 0 == get_current_stage_index(1, 0, stages)
    assert 1 == get_current_stage_index(1, 1, stages)
    assert 2 == get_current_stage_index(2, 1, stages)
    assert 3 == get_current_stage_index(2, 2, stages)


def test_compute_covered_distance_should_RaiseValueError_when_GivenNegativePace(stages):
    with pytest.raises(ValueError):
        compute_covered_distance(MagicMock(), True, stages, 34, 89, -7)
    
    with pytest.raises(ValueError):
        compute_covered_distance(MagicMock(), True, stages, 798, 16, 0)


def test_compute_covered_distance_when_TeamNotStartYet(stages):
    team_state = TeamState(1, '')

    assert 0 == compute_covered_distance(team_state, False, stages, 0, 0.0)


def test_compute_covered_distance_when_TeamIsInFirstStage(stages):
    team_state = TeamState(1, '')
    team_state.start_time = datetime(2020, 4, 21)

    assert 1000 == compute_covered_distance(team_state, False, stages, 4, 60, default_pace=240)


def test_compute_covered_distance_when_TeamFinished(stages):
    race_length = stages[-1].dst_from_start + stages[-1].length

    assert race_length == compute_covered_distance(MagicMock(), True, stages, 4, 60)


def test_compute_covered_distance_when_TeamChangedStage(stages):
    team_state = TeamState(1, '')
    team_state.current_stage.set_value(0)
    team_state.current_stage.set_value(4)
    print(team_state.current_stage.has_changed)
    team_state.start_time = datetime.now()
    team_state.split_times = [ 10, 10, 10 ]

    assert 400 == compute_covered_distance(team_state, False, stages, 40, 1)


def test_compute_covered_distance(stages):
    team_state = TeamState(1, '')
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

    assert 1100 == compute_covered_distance(team_state, False, stages, 4, 60)


def test_compute_transition_times(stages):
    start_times = [
        datetime(2020, 4, 21, hour=10),
        datetime(2020, 4, 21, hour=12),
        datetime(2020, 4, 21, hour=14)
    ]

    end_times = [
        datetime(2020, 4, 21, hour=11),
        datetime(2020, 4, 21, hour=13)
    ]

    t1 = TransitionTime(relative_index=1, split_time=3600, inter_time=datetime(2020, 4, 21, hour=12))
    t2 = TransitionTime(relative_index=2, split_time=3600, inter_time=datetime(2020, 4, 21, hour=14))

    result = compute_transition_times(0, start_times, end_times, stages)
    assert len(result) == 0

    result = compute_transition_times(1, start_times, end_times, stages)
    assert len(result) == 0

    result = compute_transition_times(2, start_times, end_times, stages)
    assert result == [t1]

    result = compute_transition_times(3, start_times, end_times, stages)
    assert result == [t1]

    result = compute_transition_times(4, start_times, end_times, stages)
    assert result == [t1, t2]


def test_get_race_status():
    assert RaceStatus.WAITING == get_race_status(False, False)
    assert RaceStatus.RUNNING == get_race_status(True, False)
    assert RaceStatus.FINISHED == get_race_status(True, True)

    assert RaceStatus.UNKNOWN == get_race_status(False, True)


def test_update_stage_times(stages):
    inter1 = datetime(2020, 4, 21, hour=12)
    inter2 = datetime(2020, 4, 21, hour=14)

    transition_times = [
        TransitionTime(relative_index=1, split_time=3600, inter_time=inter1),
        TransitionTime(relative_index=2, split_time=3600, inter_time=inter2)
    ]

    random_date = datetime(year=2020, month=4, day=21)

    team_state = TeamState(1, '')
    team_state.intermediate_times = [random_date, random_date, random_date, random_date]
    team_state.split_times = [0, 0, 0, 0]
    team_state.stage_ranks = [4, 4, 4, 4]

    update_stage_times(team_state, transition_times)

    assert team_state.intermediate_times == [random_date, inter1, random_date, inter2, random_date, random_date]
    assert team_state.split_times == [0, 3600, 0, 3600, 0, 0]
