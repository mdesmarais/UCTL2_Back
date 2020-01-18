
CONFIG_SCHEMA = {
    'type': 'object',
    'required': ['raceName', 'startTime', 'routeFile', 'raceFile', 'simPath', 'tickStep', 'fileUpdateRate', 'segments', 'teams', 'api'],
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
        'tickStep': {
            'type': 'integer',
            'minimum': 1
        },
        'fileUpdateRate': {
            'type': 'integer',
            'minimum': 1
        },
        'segments': {
            'type': 'array',
            'minItems': 2,
            'items': {
                'type': 'integer',
                'minimum': 1
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