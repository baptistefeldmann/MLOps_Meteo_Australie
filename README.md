# MLOps_Meteo_Australie
Projet MLOps de prediction de la meteo en Australie

Présentation fonctionnement :
- Collecte de données (collect_main.py) :
    . --mode inference : Collecte des données pour une station précise (flag --city obligatoire)
    écriture dans le dossier "data/inference" : fichier final <name_station>_<today_date>_weather.json
    . --mode training : Collecte des données pour toutes les stations sur 1 mois entier
    écriture dans les dossiers raw, processed, features puis datasets
        -> raw : rapport brut téléchargé
        -> processed : rapport nettoyé et transformé sous forme de tableau
        -> features : calcul des features (sauvegarde via fichier 1 fichier .parquet par station)
        -> datasets : création des données "training_ready" : data_train, data_test et data_valid.
        Par défaut voici les ratios utilisé pour chaque station : ratio_train: 0.75, ratio_test: 0.2, ratio_valid: 0.05

- Entrainement (training.py) :
    Récupération des fichiers dans data/datasets, puis extraction des données X et y (via le nom de la colonne target "RainTomorrow")
    Entrainement du modèle, suivi avec MLFlow et sauvegarde des métriques
    Registered_name: 'XGBoost_WeatherAUS'
    Run_name: <today_date>_<version>

- Prédiction (predict.py):
    Flag --city pour récupérer le fichier JSON. On prend le dernier fichier JSON de la station qui a été créé.
    Téléchargement du dernier modèle (latest), -> A modifier, à l'avenir il faudra utiliser le modèle défini comme "best"
    Prédiction du modèle

