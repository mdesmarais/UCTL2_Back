from datetime import datetime
from unittest.mock import MagicMock

import pytest

from uctl2_back.race_state import (RaceState, RaceStatus,
                                   compute_transition_times,
                                   get_current_stage_index)
from uctl2_back.stage import Stage
from uctl2_back.team_state import TeamState, TransitionTime


class TestRaceState:
    
    def test_update_race_status(self):
        state = RaceState()

        state.update_race_status(False, False)
        assert RaceStatus.WAITING == state.status.get_value()

        state.update_race_status(True, False)
        assert RaceStatus.RUNNING == state.status.get_value()

        state.update_race_status(True, True)
        assert RaceStatus.FINISHED == state.status.get_value()

        state.update_race_status(False, True)
        assert RaceStatus.UNKNOWN == state.status.get_value()


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
