
CONFIG_SCHEMA = {
    'type': 'object',
    'required': ['raceName', 'startTime', 'routeFile', 'raceFile', 'simPath', 'tickStep', 'fileUpdateRate', 'raceLength', 'checkpoints', 'teams', 'api'],
    'properties': {
        'raceName': {
            'type': 'string',
            'minLength': 1
        },
        'startTime': {
            'type': 'integer'
        },
        'routeFile': {
            'type': 'string'
        },
        'raceFile': {
            'type': 'string'
        },
        'simPath': {
            'type': 'string'
        },
        'checkpoints': {
            'type': 'array',
            'items': {
                'type': 'integer'
            }
        },
        'teams': {
            'type': 'array',
            'minItems': 1,
            'items': {
                'type': 'object',
                'required': ['bibNumber', 'name', 'pace'],
                'properties': {
                    'bibNumber': {
                        'type': 'integer',
                        'minimum': 1
                    },
                    'name': {
                        'type': 'string',
                        'minLength': 1
                    },
                    'pace': {
                        'type': 'integer',
                        'minimum': 1
                    }
                }
            }
        },
        'api': {
            'type': 'object',
            'required': ['baseUrl', 'actions'],
            'properties': {
                'baseUrl': {
                    'type': 'string'
                },
                'actions': {
                    'type': 'object',
                    'required': ['setupRace', 'updateRaceStatus', 'updateTeams'],
                    'properties': {
                        'setupRace': {
                            'type': 'string'
                        },
                        'updateRaceStatus': {
                            'type': 'string'
                        },
                        'updateTeams': {
                            'type': 'string'
                        }
                    }
                }
            }
        }
    }
}