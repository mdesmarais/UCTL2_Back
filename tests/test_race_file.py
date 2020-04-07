import pytest
from src.race_file import EMPTY_VALUE_FORMAT, STAGE_START_FORMAT, read_time, read_stage_start_times


def test_read_time():
    input_time = '01:20:35'
    result = read_time(input_time)

    assert result.hour == 1
    assert result.minute == 20
    assert result.second == 35

    invalid_time = 'nothing'
    with pytest.raises(ValueError):
        read_time(invalid_time)


def test_read_stage_start_times():
    record = {}

    for i in range(3):
        column = STAGE_START_FORMAT % (i + 1, )
        record[column] = '00:05:45'

    result = read_stage_start_times(record)
    assert len(result) == 3

    empty_column = STAGE_START_FORMAT % (2, )
    record[empty_column] = EMPTY_VALUE_FORMAT

    result = read_stage_start_times(record)
    assert len(result) == 1