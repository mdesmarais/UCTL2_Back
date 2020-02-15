import json
import os.path
from datetime import datetime

from jsonschema import validate

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
        self.raceLength = 0
        self.startTime = int(datetime.now().timestamp())
        self.tickStep = 0
        self.teams = []
        self.checkpoints = []
        self.raceFile = 'not set'
        self.routeFile = 'not set'
        self.simPath = 'not set'
        self.api = {
            'baseUrl': 'http://127.0.0.1',
            'actions': {
                'setupRace': '/setup-race',
                'updateRaceStatus': '/race-status',
                'updateTeams': '/teams'
            }
        }

    
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
            validate(instance=jsonConfig, schema=CONFIG_SCHEMA)
        except Exception as e:
            print(e)
            return None

        config = Config()
        config.raceName = jsonConfig['raceName']

        config.raceLength = jsonConfig['raceLength']
        config.tickStep = int(jsonConfig['tickStep'])

        timestamp = jsonConfig['startTime']
        try:
            datetime.fromtimestamp(timestamp)
            config.startTime = timestamp
        except Exception:
            print('Race start time must be a valid timestamp')
            return None
        
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
        
        teams = jsonConfig['teams']
        bibs = []

        for team in teams:
            bib = team['bibNumber']
            if bib in bibs:
                print('Bib number must be unique')
                return None
            
            bibs.append(bib)
        
        config.teams = teams
        config.api = jsonConfig['api']
        
        return config
