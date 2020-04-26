
TEAM_OVERTAKE_SCHEMA = {
    'type': 'object',
    'required': ['id', 'payload'],
    'properties': {
        'id': { 'type': 'integer' },
        'payload': {
            'type': 'object',
            'required': ['bibNumber', 'oldRank', 'rank', 'teams'],
            'properties': {
                'bibNumber': {
                    'title': 'Team bib number',
                    'type': 'integer',
                    'minimum': 1
                },
                'oldRank': {
                    'title': 'Old rank',
                    'type': 'integer',
                    'minimum': 0
                },
                'rank': {
                    'title': 'Current rank',
                    'type': 'integer',
                    'minimum': 0
                },
                'teams': {
                    'title': 'Bib list of overtaken teams',
                    'type': 'array',
                    'items': {
                        'type': 'integer'
                    }
                }
            }
        }
    }
}

TEAM_RACE_END_SCHEMA = {
    'type': 'object',
    'required': ['id', 'payload'],
    'properties': {
        'id': {
            'type': 'integer'
        },
        'payload': {
            'type': 'object',
            'required': ['averagePace', 'bibNumber', 'totalTime'],
            'properties': {
                'averagePace': {
                    'title': 'Average space during the race (number of seconds for 1km)',
                    'type': 'integer',
                    'minimum': 0
                },
                'bibNumber': {
                    'title': 'Team bib number',
                    'type': 'integer',
                    'minimum': 1
                },
                'totalTime': {
                    'title': 'Total seconds for finishing all timed stages',
                    'type': 'integer',
                    'minimum': 0
                }
            }
        }
    }
}


TEAM_STAGE_END_SCHEMA = {
    'type': 'object',
    'required': ['id', 'payload'],
    'properties': {
        'id': {
            'type': 'integer'
        },
        'payload': {
            'type': 'object',
            'required': [
                'averagePace', 'bibNumber', 'coveredDistance', 'currentStage',
                'lastStage', 'pos', 'splitTime', 'stageRank'
            ],
            'properties': {
                'averagePace': {
                    'title': 'Average pace for the last stage',
                    'type': 'integer',
                    'minimum': 0
                },
                'bibNumber': {
                    'title': 'Team bib number',
                    'type': 'integer',
                    'minimum': 1
                },
                'coveredDistance': {
                    'title': 'Covered distance by the team (in meters)',
                    'minimum': 0
                },
                'currentStage': {
                    'title': 'Index of the current stage',
                    'minimum': 0
                },
                'lastStage': {
                    'title': 'Index of the last stage'
                },
                'pos': {
                    'title': 'GPS coords of the team',
                    'type': 'array',
                    'items': [
                        { 'title': 'latitude', 'type': 'number' },
                        { 'title': 'longitude', 'type': 'number' }
                    ]
                },
                'splitTime': {
                    'title': 'Elapsed time (in seconds) to finish the stage',
                    'type': 'integer',
                    'minimum': 0
                },
                'stageRank': {
                    'title': 'Rank for the last stage',
                    'type': 'integer',
                    'minimum': 0
                }
            }
        }
    }
}
