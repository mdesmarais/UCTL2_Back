import csv
import datetime
from typing import TYPE_CHECKING, Any, Callable, Dict, List, Optional, TypeVar

from uctl2_back.exceptions import RaceFileFieldError

if TYPE_CHECKING:
    from uctl2_back.simulation import StagesWithInts
    from uctl2_back.simulator import Simulator
    from uctl2_back.stage import Stage

BIB_NUMBER_FORMAT = 'Numéro'
TEAM_NAME_FORMAT = 'Nom'
CHECKPOINT_NAME_FORMAT = 'Interm (S%d)'
STAGE_RANK_FORMAT = 'Clt Interm-1 (S%d)'
DISTANCE_FORMAT = 'Distance'
STAGE_START_FORMAT = '2%d|1'
STAGE_END_FORMAT = '3%d|1'
EMPTY_VALUE_FORMAT = '0'

# Type aliases
T = TypeVar('T')
Converter = Callable[[Any], T]
Record = Dict[str, Any]


def compute_checkpoints_number(record):
    """
        Computes the number of checkpoints in the given record

        The record represents a line of a race file.

        :param record: line of a race file
        :ptype record: dict
        :return: the number of checkpoints in the given record
        :rtype: int
    """
    i = 1
    # Retreiving all segments Si while Si is a valid key in record
    while True:
        checkpoint_name = CHECKPOINT_NAME_FORMAT % (i, )

        if checkpoint_name in record:
            i += 1
        else:
            break

    return i - 1


def get_key(container: Record, key: str, convert: Optional[Converter] = None) -> T:
    """
        Gets a key from a dict

        If convert parameter is not None, then the value associated to the key
        will be converted by using the given function.
        It should take one argument as a string.
        This function should raise ValueError is the conversion is not possible.

        :param container: dictionnary
        :param key: the key
        :param convert: function for converting value
        :return: the value associated to the key
        :raises RaceFileFieldError: if the key does not exist
        :raises RaceFileFieldError: if the value could not be converted
    """
    try:
        value = container[key]
        if convert is None:
            return value

        return convert(value)
    except KeyError:
        raise RaceFileFieldError('The key ' + key + ' does not exist')
    except ValueError:
        raise RaceFileFieldError('Unable to convert ' + value)


def format_datetime(dt: datetime.datetime) -> str:
    """
        Formats a datetime into a string

        The output will have the following format :
        HH:MM:ss

        :param dt: an instance of datetime class
        :return: formatted datetime
    """
    return '{:02}:{:02}:{:02}'.format(dt.hour, dt.minute, dt.second)

def format_time(time: int) -> str:
    """
        Formats a duration

        The given duration should be in seconds.
        The output format is HH:MM:ss

        :param time: duration in seconds
        :return: formatted duration
    """
    hours, remainder = divmod(time, 3600)
    minutes, seconds = divmod(remainder, 60)

    return '{:02}:{:02}:{:02}'.format(int(hours), int(minutes), int(seconds))

def process_file(simulator: 'Simulator', stages: 'StagesWithInts') -> List[Dict[str, Any]]:
    """
        Updates a racefile with some stages for each team

        This function is used with a simulator.
        The simulator must have its lists headers and rows
        update to date.

        :param simulator: an instance to the Simulator class
        :return: new rows for the racefile
    """
    rows = []

    with open(simulator.race_file, 'w') as f:
        writer = csv.DictWriter(f, simulator.headers, delimiter='\t')
        writer.writeheader()

        for team in simulator.race_teams:
            row = dict(simulator.rows[team['bibNumber']])

            for i, stage in enumerate(stages):
                stage_cols = stage_columns(i + 1)

                if not team['bibNumber'] in stage[0]:
                    for stage_col in stage_cols:
                        row[stage_col] = '0'
                elif not team['bibNumber'] in stage[1]:
                    for stage_col in filter(lambda x: not x.startswith('2'), stage_cols):
                        row[stage_col] = '0'

            rows.append(row)
            writer.writerow(row)

    return rows


def read_split_times(record: Record) -> List[int]:
    """
        Extracts split times for the given record

        Split times columns follow the format :const:`CHECKPOINT_NAME_FORMAT`.
        A split time is a duration in seconds.

        :param record: line of a race file
        :return: list of split times
    """
    return read_values(record, CHECKPOINT_NAME_FORMAT, convert=read_split_time)


def read_stage_ranks(record: Record) -> List[int]:
    """
        Extracts rank for each stage

        Stage rank columns follow the format :const:`STAGE_RANK_FORMAT`.

        :param record: line of a race file
        :return: list of ranks
    """
    return read_values(record, STAGE_RANK_FORMAT, convert=int)


def read_stage_end_times(record: Record) -> List[datetime.datetime]:
    """
        Extracts end time for each stage

        Stage end time follow the format :const:`STAGE_END_FORMAT`

        :param record: line of a race file
        :return: list of datetimes
    """
    return read_values(record, STAGE_END_FORMAT, convert=read_time)


def read_stage_start_times(record: Record) -> List[datetime.datetime]:
    """
        Extracts start time for each stage

        Stage start time follow the format :const:`STAGE_START_FORMAT`

        :param record: line of a race file
        :return: list of datetimes
    """
    return read_values(record, STAGE_START_FORMAT, convert=read_time)


def read_split_time(raw_input: str) -> int:
    """
        Formats a string into a duration in seconds

        raw_input must have the format : HH:MM:ss
        A ValueError exception will be raised if it is not the case

        :param raw_input: input with the correct format
        :return: duration in seconds
        :raises ValueError: if the given input has incorrect format
    """
    if raw_input is None:
        print('NOIGNON')
    args = raw_input.split(':')

    if len(args) < 3:
        raise ValueError('Incorrect format')

    return int(args[0]) * 3600 + int(args[1]) * 60 + int(args[2])


def read_time(raw_input: str, base_date=datetime.date.today()) -> datetime.datetime:
    """
        Extracts a datetime from a string

        The base_date is used to set the wanted
        year, month and day.

        Hours, minutes and seconds will be replaced with
        the extracted values from the given string.

        :param raw_input: a string
        :param base_date: used to set the date
        :return: a datetime
        :raises ValueError: if the given string is not a time
    """
    return datetime.datetime.strptime(raw_input, '%H:%M:%S').replace(year=base_date.year, month=base_date.month, day=base_date.day)


def read_values(record: Dict[str, Any], output_format: str, convert: Converter = str) -> List[T]:
    """
        Extracts values from the record that have a key in the given format

        The output_format parameter is a string that has only one string parameter
        it should be an int.

        If the value can not be converted then it wont be added to the list

        :param record: dictionnary like
        :param output_format: format of the key
        :param convert: function used to convert value
        :return: list of values
    """
    values: List[T] = []

    i = 1
    while True:
        column = output_format % (i,)

        if not column in record or record[column] == EMPTY_VALUE_FORMAT:
            break

        try:
            values.append(convert(record[column]))
        except ValueError:
            continue

        i += 1

    return values


def stage_columns(index: int) -> List[str]:
    """
        Creates a list of stages columns for the given index

        This index must be positive

        A stage has many columns in a racefile:
        * a split time
        * a rank
        * an entrance time
        * a release time

        :param index: index of the stage
        :raises ValueError: if index is negative
    """
    if index < 0:
        raise ValueError('index must be positive')

    columns = ('Interm (S%d)', 'Clt Interm-1 (S%d)', '2%d|1', '3%d|1')
    return [x % (index,) for x in columns]
