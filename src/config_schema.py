
CONFIG_SCHEMA = {
    'type': 'object',
    'required': [
        'raceName', 'routeFile', 'raceFile', 'simPath', 'checkpoints', 
        'tickStep', 'fileUpdateRate', 'raceLength', 'teams', 'encoding'
    ],
    'properties': {
        'raceName': {
            'title': 'Nom de la course',
            'type': 'string',
            'minLength': 1
        },
        'routeFile': {
            'title': 'Chemin vers un fichier contenant le tracé de la course (gpx ou json)',
            'type': 'string'
        },
        'raceFile': {
            'title': 'Chemin vers un fichier de course (doit exister avant de lancer le backend python)',
            'type': 'string'
        },
        'simPath': {
            'title': 'Chemin vers le fichier jar du simulateur',
            'type': 'string'
        },
        'checkpoints': {
            'title': 'Liste de checkpoints (rangés dans l\'ordre croissant des distances',
            'type': 'array',
            'items': {
                'title': 'Distance en mètres depuis le départ de la course (doit être unique)',
                'type': 'integer'
            }
        },
        'tickStep': {
            'title': 'Indique le temps écoulé (en secondes) dans la simulation pour 1 secodne réelle',
            'type': 'integer'
        },
        'fileUpdateRate': {
            'title': 'Intervalle de mise à jour du fichier de course par le simulateur (en secondes)',
            'type': 'integer'
        },
        'raceLength': {
            'title': 'Longueur de la course en mètres',
            'type': 'integer',
            'minimum': 1
        },
        'teams': {
            'title': 'Liste des équipes engagées (1 minimum)',
            'type': 'array',
            'minItems': 1,
            'items': {
                'type': 'object',
                'required': ['bibNumber', 'name', 'pace'],
                'properties': {
                    'bibNumber': {
                        'title': 'Numéro de dossard (doit être unique)',
                        'type': 'integer',
                        'minimum': 1
                    },
                    'name': {
                        'title': 'Nom de l\'équipe',
                        'type': 'string',
                        'minLength': 1
                    },
                    'pace': {
                        'title': 'Allure initiale de l\'équipe (permet de faire les premières estimations) (nombre de secondes pour 1000m)',
                        'type': 'integer',
                        'minimum': 1
                    }
                }
            }
        },
        'encoding': {
            'title': 'Encodage du fichier de course (utf-8, iso8859_3, ...)',
            'type': 'string'
        }
    }
}