"""
    Thos modules defines the Config class
"""
import os.path
from typing import Any, Dict, List, Optional

import jsonschema

from uctl2_back.config_schema import CONFIG_SCHEMA
from uctl2_back.exceptions import InvalidConfigError
from uctl2_back.stage import Stage


class Config:

    """
        Reprents a JSON configuration

        Each attribute of the class is a field in the configuration.
        The class inherits from dict, that means all attributs can be
        accessed by using the key notation : config['key'].
    """

    def __init__(self):
        self.race_name = 'Unknown'
        self.tick_step = 1
        self.stages: List[Stage] = []
        self.race_file = 'not set'
        self.route_file = 'not set'
        self.encoding = 'utf-8'
        self.teams = []

    @classmethod
    def read_from_json(cls, json_config: Dict[str, Any]) -> 'Config':
        """
            Loads and validates the given configuration

            The validation is done by using JSON schema and the file config_schema.py
            It contains the format that the given configuration should have.

            :param jsonConfig: a dictionnary containing a JSON configuration
            :return: an instance of Config
            :raises InvalidConfigError: if the configuration is not valid
        """
        try:
            jsonschema.validate(instance=json_config, schema=CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            path = e.absolute_path
            if path:
                msg = 'Config validator error for field "%s" : %s (%s=%s)' % (path.pop(), e.message, e.validator, e.validator_value)
            else:
                msg = 'Config validator error : ' + e.message

            raise IndentationError(msg)

        config = Config()
        config.race_name = json_config['raceName']

        config.stages = validate_stages(json_config['stages'])

        config.route_file = json_config['routeFile']
        validate_route_file(config.route_file)

        config.race_file = json_config['raceFile']
        validate_race_file(config.race_file)

        config.teams = json_config['teams']

        validate_bibs([team['bibNumber'] for team in config.teams])

        config.encoding = json_config['encoding']

        return config


def validate_bibs(bibs: List[int]):
    """
        Validates bibs number

        Bibs must be unique and strictely positive

        :param bibs: list of bibs
        :raises InvalidConfigError: if a bib is not valid
    """
    # We use a set to check if all bibs are unique
    if not len(set(bibs)) == len(bibs):
        raise InvalidConfigError('Bibs must be unique')

    bibs_under_one = [x for x in bibs if x < 1]

    if len(bibs_under_one) > 0:
        raise InvalidConfigError('Bibs must be greater or equal to 1')


def validate_race_file(race_file: str):
    """
        Valides a path to a race file

        The path should point to an existing file
        If the file does not exist, then the function
        tries to create it. It it failed then
        a InvalidConfigError exception will be raised.

        :param race_file: path to a race file
        :raises InvalidConfigError: if the file could not be created
    """
    if os.path.isfile(race_file):
        return

    try:
        # Trying to create a default file if it does not exist
        with open(race_file, 'w'):
            pass
    except OSError:
        raise InvalidConfigError('Unable to create the raceFile')


def validate_route_file(route_file: str):
    """
        Validates the path of a route file

        The path must point to an existing file with the extension ".gpx".

        :param route_file: path to a route file
        :raises InvalidConfigError: if the file does not exist or is not a gpx file
    """
    if not route_file.endswith('.gpx'):
        raise InvalidConfigError('Route file must have the extension .gpx')

    if not os.path.isfile(route_file):
        raise InvalidConfigError('The given routeFile is not an existing file')


def validate_stages(raw_stages: List[Any]) -> List[Stage]:
    """
        Validates stages from a json config

        Each stage must have a positive length.
        The first stage must be timed.
        Two or more consecutive timed or non timed stages
        are not allowed.

        A raw stage is a dict with the following keys :
        * name: name of the stage
        * length: length in meters
        * timed: boolean indicates if the stage is timed or not

        :param raw_stages: list of stages from a json config
        :return: list of stages
        :raises InvalidConfigError: if a stage has a negative length
        or if the first stage is not timed
        or if there are two or more consecutive timed or non timed stages
    """
    stages: List[Stage] = []
    last_stage: Optional[Stage] = None

    for i, raw_stage in enumerate(raw_stages):
        if raw_stage['length'] <= 0:
            raise InvalidConfigError('Stage length must be strictely positive')

        if last_stage is None:
            dst_from_start = 0
        else:
            if i == 0 and not last_stage.is_timed:
                raise InvalidConfigError('The first stage must be timed')

            if last_stage.is_timed == raw_stage['timed']:
                raise InvalidConfigError('Two or more consecutive timed or non timed stages are not allowed')

            dst_from_start = last_stage.dst_from_start + last_stage.length

        stage = Stage(i, raw_stage['name'], dst_from_start, raw_stage['length'], raw_stage['timed'])

        last_stage = stage
        stages.append(stage)

    return stages
