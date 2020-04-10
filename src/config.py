import json
import logging
import os.path

import jsonschema

from config_schema import CONFIG_SCHEMA


class Config:

    """
        Reprents a JSON configuration

        Each attribute of the class is a field in the configuration.
        The class inherits from dict, that means all attributs can be
        accessed by using the key notation : config['key'].
    """

    logger = logging.getLogger(__name__)

    def __init__(self):
        super().__init__()
        self.raceName = 'Unknown'
        self.tickStep = 1
        self.timeCheckpoints = []
        self.stages = []
        self.raceFile = 'not set'
        self.routeFile = 'not set'
        self.encoding = 'utf-8'
        self.teams = []

    
    @classmethod
    def readFromJson(cls, jsonConfig):
        """
            Loads and validates the given configuration

            The validation is done by using JSON schema and the file config_schema.py
            It contains the format that the given configuration should have.

            :param jsonConfig: a dictionnary containing a JSON configuration
            :ptype jsonConfig: dict
            :return: an instance of Config or None if an error occured
            :rtype: Config
        """
        try:
            jsonschema.validate(instance=jsonConfig, schema=CONFIG_SCHEMA)
        except jsonschema.exceptions.ValidationError as e:
            path = e.absolute_path
            if path:
                cls.logger.error('Config validator error for field "%s" : %s (%s=%s)' % (path.pop(), e.message, e.validator, e.validator_value))
            else:
                cls.logger.error('Config validator error : %s', e.message)
            return None

        config = Config()
        config.raceName = jsonConfig['raceName']

        config.timeCheckpoints = jsonConfig['timeCheckpoints']
        config.stages = jsonConfig['stages']

        for i, stage in enumerate(config.stages):
            if i == 0:
                stage['start'] = 0
            else:
                lastStage = config.stages[i - 1]

                stage['start'] = lastStage['start'] + lastStage['length']

        routeFile = jsonConfig['routeFile']
        if routeFile.endswith('.gpx') or routeFile.endswith('.json'):
            if os.path.isfile(routeFile):
                config.routeFile = routeFile
            else:
                cls.logger.error('The given routeFile is not an existing file')
                return None
        else:
            cls.logger.error('Route file must have the extension .gpx or .json')
            return None
        
        raceFile = jsonConfig['raceFile']
        if not os.path.isfile(raceFile):
            try:
                # Trying to create a default file if it does not exist
                with open(raceFile, 'w'):
                    pass
            except OSError:
                cls.logger.error('Unable to create the raceFile')
                return None
        
        config.raceFile = raceFile

        config.teams = jsonConfig['teams']
        bibs = [team['bibNumber'] for team in config.teams]

        if not len(set(bibs)) == len(bibs):
            cls.logger.error('Bibs must be unique')
            return None

        bibs_under_one = [x for x in bibs if x < 1]

        if len(bibs_under_one) > 0:
            cls.logger.error('Bibs must be greater or equal to 1')
            return None

        config.encoding = jsonConfig['encoding']
        
        return config
