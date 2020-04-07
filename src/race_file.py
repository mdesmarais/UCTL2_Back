import csv
import datetime

BIB_NUMBER_FORMAT = 'Numéro'
TEAM_NAME_FORMAT = 'Nom'
CHECKPOINT_NAME_FORMAT = 'Interm (S%d)'
STAGE_RANK_FORMAT = 'Clt Interm-1 (S%d)'
END_SECTION_FORMAT = '3%d|1'
DISTANCE_FORMAT = 'Distance'
START_FORMAT = '21|1'
FINISH_FORMAT = '33|1'
EMPTY_VALUE_FORMAT = '0'


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


def getFloat(container, key):
    """
        Extracts a float from a dict with the given key

        If the key does not exist or the associated value
        is not a float then None is returned.

        :param container: a dict that may contains the key
        :ptype container: dict
        :param key: the key
        :ptype key: any
        :return: a float value associated to the given key or None
        :rtype: float
    """
    if key in container:
        try:
            return float(container[key])
        except ValueError:
            return None
    
    return None  


def getInt(container, key):
    """
        Extracts an int from a dict with the given key

        If the key does not exist or the associated value
        is not an int then None is returned.

        :param container: a dict that may contains the key
        :ptype container: dict
        :param key: the key
        :ptype key: any
        :return: an integer value associated to the given key or None
        :rtype: int
    """
    if key in container:
        try:
            return int(container[key])
        except ValueError:
            return None
    
    return None


def format_datetime(dt):
    return '{:02}:{:02}:{:02}'.format(dt.hour, dt.minute, dt.second)

def format_time(time):
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

def readIntermediateTimes(record):
    intermediateTimes = []

    i = 1
    while True:
        columnName = END_SECTION_FORMAT % (i, )

        if not columnName in record or record[columnName] == EMPTY_VALUE_FORMAT:
            break

        date = datetime.date.today()
        time = datetime.datetime.strptime(record[columnName], '%H:%M:%S').replace(year=date.year, month=date.month, day=date.day)

        intermediateTimes.append(time)
        i += 1
    
    return intermediateTimes


def readSplitTimes(record):
    """
        Extracts all split times from a line of a csv file

        If a conversion error occured, then False is returned.

        :param record: line to extract split times
        :ptype record: dict
        :return: a list of integers that correspond to an elapsed time in seconds
        :rtype: list
    """
    splitTimes = []

    i = 1
    # Retreiving all segments Si while Si is a valid key in record
    while True:
        checkpointName = CHECKPOINT_NAME_FORMAT % (i, )
        
        # Split times should be in the following format : HH:mm:ss
        if not checkpointName in record or record[checkpointName] == EMPTY_VALUE_FORMAT:
            break

        args = record[checkpointName].split(':')
        if not len(args) == 3:
            break

        value = int(args[0]) * 3600 + int(args[1]) * 60 + int(args[2])
        splitTimes.append(value)
        i += 1

        """if value is None:
            break

        if value > 0:
            splitTimes.append(value)
            i += 1
        else:
            # No more split times for this team
            break"""
    
    return splitTimes


def readStageRanks(record):
    ranks = []

    i = 1
    while True:
        stageRankName = STAGE_RANK_FORMAT % (i, )

        if not stageRankName in record or record[stageRankName] == EMPTY_VALUE_FORMAT:
            break
        
        ranks.append(int(record[stageRankName]))
        i += 1
    
    return ranks


def readTime(record, column):
    date = datetime.date.today()
    return datetime.datetime.strptime(record[column], '%H:%M:%S').replace(year=date.year, month=date.month, day=date.day)


def stage_columns(index):
    return map(lambda x: x % (index,), ('Interm (S%d)', 'Clt Interm-1 (S%d)', '2%d|1', '3%d|1'))