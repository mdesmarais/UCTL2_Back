import json
import os.path

import jsonschema

from config_schema import CONFIG_SCHEMA


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
        self.tickStep = 0
        self.checkpoints = []
        self.raceFile = 'not set'
        self.routeFile = 'not set'
        self.simPath = 'not set'
        self.encoding = 'utf-8'
        """self.api = {
            'baseUrl': 'http://127.0.0.1',
            'actions': {
                'setupRace': '/setup-race',
                'updateRaceStatus': '/race-status',
                'updateTeams': '/teams'
            }
        }"""

        # Those fields are only used by the simulator
        # We put them here in order to create a default config
        # that works with the two apps
        self.fileUpdateRate = 1
        self.raceLength = 1
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
                print('Config validator error for field "%s" : %s (%s=%s)' % (path.pop(), e.message, e.validator, e.validator_value))
            else:
                print('Config validator error :', e.message)
            return None

        config = Config()
        config.raceName = jsonConfig['raceName']

        config.tickStep = int(jsonConfig['tickStep'])
        
        config.checkpoints = jsonConfig['checkpoints']

        routeFile = jsonConfig['routeFile']
        if routeFile.endswith('.gpx') or routeFile.endswith('.json'):
            if os.path.isfile(routeFile):
                config.routeFile = routeFile
            else:
                print('The given routeFile is not an existing file')
                return None
        else:
            print('Route file must have the extension .gpx or .json')
            return None
        
        raceFile = jsonConfig['raceFile']
        if os.path.isfile(raceFile):
            config.raceFile = raceFile
        else:
            print('The given raceFile does not exist')
            return None
        
        simPath = jsonConfig['simPath']
        if simPath.endswith('.jar') and os.path.isfile(simPath):
            config.simPath = simPath
        else:
            print('The given simPath does not exist or is not a jar file')
            return None

        #config.api = jsonConfig['api']

        config.encoding = jsonConfig['encoding']
        
        return config
