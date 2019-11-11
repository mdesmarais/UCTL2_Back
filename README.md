# UCTL 2 Scripts

Ce dépôt contient des scripts permettant le bon fonctionnement de la simulation d'une course Breizh Chrono.

Liste des scripts avec un lien vers leur description

* [uctl2_setup.py](#UCTL2-Setup)
* [uctl2_race.py](#UCTL2-Race)

## Pré-requis

Les scripts utilisent Python 3.  
Un fichier nommé `requirements.txt` contient les dépendances utilisées par les scripts.
L'installation de celles-ci se fait à l'aide de l'utilitaire pip : `pip install -r requirements.txt`

## UCTL2 Setup

Usage : `uctl2_setup.py config_file`

Ce script permet d'initialiser une base de données avec les informations de la course : nom, heure de début, liste des équipes, tracé. Il devrait être exécuté avant l'utilisation du [second script](#uctl2-race)

Un fichier de configuration au format JSON est requis pour exécuter ce script.  
Voir la partie [Configuration](#configuration) pour plus de détails sur le format de ce fichier.

Une liste de points contenus dans un fichier GPX ou json permet de définir un tracé qui sera affiché sur l'interface web.

### Configuration

Liste des champs requis : 

* **raceName** : Chaine de caractères représentant le nom de la course
* **startTime** : Timestamp indiquant la date et l'heure du début de la course
* **teams** : Liste d'équipes (au minimum 1 équipe)
  * **bib** : Entier représentant le numéro de dossard de l'équipe (doit être unique et supérieur à 0)
  * **name** : Chaine de caractères indiquant le nom de l'équipe
  * **pace** : Entier représentant l'allure initiale de l'équipe (temps en secondes pour un kilomètre)

L'une de ces deux options est requise :

* **gpxFile** : Chemin vers un fichier [GPX](https://en.wikipedia.org/wiki/GPS_Exchange_Format) existant
* **pointsFile** : Chemin vers un fichier JSON contenant une liste de points
  * Format attendu : `[lat, long, ?ele]`
  * L'élévation n'est pas requise, une valeur de 0.0 sera assignée si celle-ci n'est pas renseignée

Si les deux options sont renseignées, alors le script utilisera en priorité le fichier GPX pour charger le tracé de la course.

## UCTL2 Race

Usage : `uctl2_race.py`

Ce script permet de faire le lien entre un fichier de course Breizh Chrono et la base de données qui est utilisée par l'interface web pour afficher les données de la course.

La description du contenu d'un fichier de course est faite dans le fichier README du programme de simulation disponible [ici](https://github.com/Noignon/UCTL2_Sim).

Chaque lecture du fichier de course permet d'estimer la position actuelle de chaque équipe. Nous calculons l'allure moyenne ainsi que la distance parcourue depuis le début de la course.

### Configuration

La configuration de ce script se faire directement dans son code source : des constantes permettent de changer ses paramètres.

* **API_BASE_URL** : Base de l'adresse de l'API de la base de données
* **API_ACTIONS** : Associations d'adresses relatives de l'API avec une étiquette
  * **updateTeams** : Adresse relative vers une action de l'API qui met à jour les équipes une fois les estimations calculées
* **REQUEST_DELAY** : Entier indiquant le temps en secondes entre chaque lecture du fichier de course
* **RACE_FILE_PATH** : Chemin vers le fichier de course (au format CSV)
* **MAX_NETWORK_ERRORS** : Nombre maximum d'erreurs liées aux requêtes vers l'API
* **DEBUG_DATA_SENT** : Booléen indiquant si les données envoyées à l'API doivent être affichées à l'écran