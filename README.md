# MLOps_Meteo_Australie
Projet MLOps de prediction de la meteo en Australie

Présentation fonctionnement :
- Collecte de données (dossier src/data) :
    . collect_raw.py : Collecte les données brutes pour toutes les stations sur une période de 2 mois (mois actuel + mois précédent).
    Puis nettoie les fichiers CSV pour les enregistrer dans le dossier data/processed.

    . create_features.py : Utilise les CSV du dossier data/processed pour calculer les features pour le modèle
    (direction du vent en degré, moyenne des températures sur 3 jours, etc..)
    puis enregistre les données dans data/features dans des fichiers .parquet par station

    . create_datasets.py : A partir des fichiers .parquet par station, créé les datasets d'entrainements (train/test/valid)
    selon les ratios suivant (défaut) : 75% Train, 20% Test et 5% validation (par station), enregistre les données dans le dossier data/datasets

    . collect_inference.py : Réalise les 3 étapes précédentes mais uniquement pour 1 seule station choisi (flag --city obligatoire)
    Enregistre les données dans le dossier data/inference.
    A la fin, le process garde uniquement les données météo du jour pour les enregistrer dans un fichier .json
    
    . Pipeline : Process DVC pour automatiser tout ça, dans le dossier src/pipelines/dvc.yaml.
    Pour le lancer faire : dvc repro src/pipeline/dvc.yaml

- Entrainement (training.py) :
    Récupération des fichiers dans data/datasets, puis extraction des données X et y (via le nom de la colonne target "RainTomorrow")
    Entrainement du modèle, suivi avec MLFlow, sauvegarde des métriques et comparison entre challenger et best_model (selon la métrique PR_AUC)
    Le modèle est enregstré sur MLFlow server hébergé sur la plateforme Dagshub du projet.
    Registered_name: 'XGBoost_WeatherAUS'
    Run_name: <today_date>_<version>

- Prédiction (predict.py):
    Flag --city pour récupérer le fichier JSON de la station correspondante. On prend le dernier fichier JSON de la station qui a été créé.
    Téléchargement du meilleur modèle (alias best_model)
    Prédiction du modèle

- Interface :
    Interface utilisateur pour sélectionner la ville et lancer la prédiction météo.
    Techno utilisée : Streamlit. Non terminé.

- Exemples :
    -> collecte de données training : dvc repro && dvc push
    -> collecte des données inférence : python collect_inference.py --city Canberra
    -> entrainement : python training.py
    -> prediction : python predict.py --city Canberra
    -> visualisation interface : streamlit run app.py

