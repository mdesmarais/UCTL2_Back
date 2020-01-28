# UCTL 2 stats

- Initialisation d'une course avec son tracé dans une base de données
- Lancement de la simulation d'une course via le simulateur
- Réalisation de calculs sur les données de la course en direct
- Notification d'événnements via un serveur de websockets

## Pré-requis

Le programme utilise Python 3.  
Un fichier nommé `requirements.txt` contient les dépendances utilisées par les scripts.  
L'installation de celles-ci se fait à l'aide de l'utilitaire pip : `pip install -r requirements.txt`

## Utilisation

`python src/uctl2 config_path`

Le programme attend en paramètre un chemin vers un fichier de configuration. Si aucun  chemin n'est passé, un fichier `config.json `contenant une configuration initiale est créée dans le dossier courant.

## Configuration

La configuration doit être stockée dans un fichier au format json.

| Clé | Type | Description |
|-----|------|------------|
| raceName | String | Nom de la course |
| startTime | timestamp | Date et heure du début de la course |
| raceFile | String | Chemin vers un fichier de course |
| routeFile | String | Chemin vers un fichier contenant le tracé de la course (gpx ou json) |
| simPath | String | Chemin vers le fichier jar du simulateur |
| segments | List[int] | Liste de tailles de segments en mètre (au moins deux segments sont requis) |
| teams | List[Object] | Liste d'équipes (au minimum une)
| teams.bibNumber | int | Numéro de dossard de l'équipe (doit être unique et strictement positif) |
| teams.name | String | Nom de l'équipe |
| teams.pace | int | Allure initiale de l'équipe en secondes |
| api | Object | Paramètres de connexion à l'API de BDD |
| api.baseUrl | String | Adresse de l'API |
| api.actions | Object | Chemins des actions |
| api.actions.setupRace | String | Chemin de l'action permettant l'initialisation d'une course |
| api.actions.updateRaceStatus | String | Chemin de l'action permettant la mise à jour du statut de la course |
| api.actions.updateTeams | String | Chemin de l'action permettant la mise à jour des équipes (positions, classements, ...) |