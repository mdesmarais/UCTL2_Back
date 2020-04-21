import csv
import datetime
from typing import Any, Callable, Dict, List, Optional, TypeVar

from uctl2_back.exceptions import RaceFileFieldError

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


def computeCheckpointsNumber(record):
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
        checkpointName = CHECKPOINT_NAME_FORMAT % (i, )
        
        if checkpointName in record:
            i += 1
        else:
            break
    
    return i - 1


def get_key(container: Record, key: str, convert: Optional[Converter]=None) -> T:
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

def process_file(simulator, stages):
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


def read_split_time(input: str) -> int:
    """
        Formats a string into a duration in seconds

        The input must have the format : HH:MM:ss
        A ValueError exception will be raised if it is not the case

        :param input: input with the correct format
        :return: duration in seconds
        :raises ValueError: if the given input has incorrect format
    """
    args = input.split(':')

    if len(args) < 3:
        raise ValueError('Incorrect format')

    return int(args[0]) * 3600 + int(args[1]) * 60 + int(args[2])


def read_time(input: str) -> datetime.datetime:
    date = datetime.date.today()
    return datetime.datetime.strptime(input, '%H:%M:%S').replace(year=date.year, month=date.month, day=date.day)


def read_values(record: Dict[str, Any], format: str, convert: Converter=str) -> List[T]:
    """
        Extracts values from the record that have a key in the given format

        The format parameter is a string that has only one string parameter 
        it should be an int.

        If the value can not be converted then it wont be added to the list

        :param record: dictionnary like
        :param format: format of the key
        :param convert: function used to convert value
        :return: list of values
    """
    values: List[T] = []

    i = 1
    while True:
        column = format % (i,)

        if not column in record or record[column] == EMPTY_VALUE_FORMAT:
            break

        try:
            values.append(convert(record[column]))
        except ValueError:
            continue
        
        i += 1
    
    return values


def stage_columns(index):
    return map(lambda x: x % (index,), ('Interm (S%d)', 'Clt Interm-1 (S%d)', '2%d|1', '3%d|1'))
