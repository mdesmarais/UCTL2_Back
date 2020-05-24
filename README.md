# UCTL 2 Back

Cette application est composée de deux programmes :

* Broadcaster
    * Initialisation d'une course avec son tracé dans une base de données
    * Lancement de la simulation d'une course via le simulateur
    * Réalisation de calculs sur les données de la course en direct
    * Notification d'évènements via un serveur de websockets
* Manager
  * Interface web permettant de controler un simulateur
  * Génération manuelle du fichier de course
  * Possibilité de modifier la vitesse de la simulation en live

## Pré-requis

Le programme utilise Python 3.  
Un fichier nommé `requirements.txt` contient les dépendances utilisées par les scripts.  
L'installation de celles-ci se fait à l'aide de l'utilitaire pip : `pip install -r requirements.txt`.

Nous conseillons l'utilisation d'un environnement virtuel pour faciliter l'installation des modules. Veuillez vous reporter sur [ce lien](https://docs.python.org/3.7/library/venv.html) pour plus d'information.

Il faut également installer le projet localement pour résoudre les problèmes d'import : `pip install -e .`

## Utilisation

Lancement du broadcaster :  `python uctl2_back/uctl2.py config_path`  
Lancement du manager : `python uctl2_back/manager.py config_path`

Le programme attend en paramètre un chemin vers un fichier de configuration. Si aucun chemin n'est passé, un fichier `config.json `contenant une configuration initiale sera créée dans le dossier courant.  

Un exemple de configuration est disponible dans le fichier [samples/config.json](samples/config.json). Il est fourni avec un fichier gpx contenant le tracé de la course Univercity Trail 2020.

## Configuration

La configuration doit être stockée dans un fichier au format json.

Une description des champs requis dans le fichier est disponible ici : [uctl2_back/config_schema.py](src/config_schema.py). Ce lien pointe vers un fichier json qui respecte le format [JSON Schema](https://json-schema.org/). Ce dernier permet de vérifier automatiquement que la configuration fournie par l'utilisateur respecte le format attendu

## Tests

Les tests unitaires sont accessibles dans le dossier [tests/](tests/). Nous avons utilisé la librairie pytest. Leur exécution se fait à l'aide de la commande `pytest`.

Nous avons ajouté spécifié le type de chaque définition de méthodes et d'attributs dans le code afin d'utiliser l'outil [mypy](http://mypy-lang.org/). Il permet de vérifier statiquement qu'un programme respecte bien toutes les contraintes de type. Son exécution se fait à l'aide de la commande `mypy uctl2_back`.