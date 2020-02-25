# UCTL 2 stats

- Initialisation d'une course avec son tracé dans une base de données
- Lancement de la simulation d'une course via le simulateur
- Réalisation de calculs sur les données de la course en direct
- Notification d'évènements via un serveur de websockets

## Pré-requis

Le programme utilise Python 3.  
Un fichier nommé `requirements.txt` contient les dépendances utilisées par les scripts.  
L'installation de celles-ci se fait à l'aide de l'utilitaire pip : `pip install -r requirements.txt`.

Nous conseillons l'utilisation d'un environnement virtuel pour faciliter l'installation des modules. Veuillez vous reporter sur [ce lien](https://docs.python.org/3.7/library/venv.html) pour plus d'information.

## Utilisation

`python src/uctl2.py config_path`

Le programme attend en paramètre un chemin vers un fichier de configuration. Si aucun  chemin n'est passé, un fichier `config.json `contenant une configuration initiale sera créée dans le dossier courant.

## Configuration

La configuration doit être stockée dans un fichier au format json.

Une description des champs requis dans le fichier est disponible ici : [src/config_schema.py](src/config_schema.py). Ce lien pointe vers un fichier json qui respecte le format [JSON Schema](https://json-schema.org/). Ce dernier permet de vérifier automatiquement que la configuration fournie par l'utilisateur est valide.