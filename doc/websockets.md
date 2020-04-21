# Documentation sur les websockets

La communication entre le manager et le front est réalisée grâce à des websockets.

## Liste des évènements

Voici les évènements qui sont émis avec leur description associée :

| Nom | Emetteur | Destinataire | Description | Réponse(s) |
|-----|----------|--------------|-------------|------------|
| initialize | serveur | client | Contient l'état courant du simulateur à la connexion du client | |
| racefile | serveur | tous les clients | Indique aux clients une mise à jour du fichier de course | |
| sim_status_updated | serveur | tous les clients | Indique le nouveau statut de la simulation (0=arrêt, 1=marche) | |
| stop_sim | client | serveur | Demande l'arrêt du simulateur | sim_status_updated |
| toggle_sim | client | serveur | Demande d'arrêt ou le lancement du simulateur en fonction de son état | racefile, sim_status_updated |
| update_racefile | client | serveur | Demande de mise à jour du fichier de course avec uniquement certaines sections | racefile |

La colonne *Réponse(s)* indique les évènements qui envoyés en réponse à la requête du client.

## Structure de chaque évènement

* initialize : *object*
    * headers : en-tête du fichier de course (nom des colonnes)
    * rows : lignes du fichier de course (contient une map qui associe un nom de colonne avec sa valeur)
    * stage_inter_times : temps intermédiaires pour chaque équipe dans les différentes spéciales. Chaque élément de la liste représente une spéciale : c'est une liste qui contient des temps intermédiaires
    * simulation_status : statut de la simulation (0=arrêt, 1=marche)
    * race_distance : distance de la course en mètres
    * race_duration : durée de la course (en secondes) pour les temps simulés
    * race_name : nom de la course
    * race_stages : liste des spéciales de la course
    * race_teams : liste des équipes
    * start_time : timestamp indiquant l'heure de début de la course
