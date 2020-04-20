import os.path
from typing import Any, Dict

import jsonschema

from uctl2_back.config_schema import CONFIG_SCHEMA


class InvalidConfigError(Exception):
    """
        Represents an error when a configuration is not valid (wrong format, invalid values, ...)
    """
    pass


class Config(dict):

    """
        Reprents a JSON configuration

        Each attribute of the class is a field in the configuration.
        The class inherits from dict, that means all attributs can be
        accessed by using the key notation : config['key'].
    """

    def __init__(self):
        super().__init__()
        self.__dict__ = self

        self.raceName = 'Unknown'
        self.tickStep = 1
        self.timeCheckpoints = []
        self.stages = []
        self.raceFile = 'not set'
        self.routeFile = 'not set'
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
        config.raceName = json_config['raceName']

        config.timeCheckpoints = json_config['timeCheckpoints']
        config.stages = json_config['stages']

        for i, stage in enumerate(config.stages):
            if i == 0:
                stage['start'] = 0
            else:
                lastStage = config.stages[i - 1]

                stage['start'] = lastStage['start'] + lastStage['length']

        routeFile = json_config['routeFile']
        if routeFile.endswith('.gpx') or routeFile.endswith('.json'):
            if os.path.isfile(routeFile):
                config.routeFile = routeFile
            else:
                raise InvalidConfigError('The given routeFile is not an existing file')
        else:
            raise InvalidConfigError('Route file must have the extension .gpx or .json')
        
        raceFile = json_config['raceFile']
        if not os.path.isfile(raceFile):
            try:
                # Trying to create a default file if it does not exist
                with open(raceFile, 'w'):
                    pass
            except OSError:
                raise InvalidConfigError('Unable to create the raceFile')
        
        config.raceFile = raceFile

        config.teams = json_config['teams']
        bibs = [team['bibNumber'] for team in config.teams]

        # We use a set to check if all bibs are unique
        if not len(set(bibs)) == len(bibs):
            raise InvalidConfigError('Bibs must be unique')

        bibs_under_one = [x for x in bibs if x < 1]

        if len(bibs_under_one) > 0:
            raise InvalidConfigError('Bibs must be greater or equal to 1')

        config.encoding = json_config['encoding']
        
        return config
