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


# Docker Compose Usage

## Build all images

```bash
docker compose build
```

---

## 1. Prepare training data

Run the DVC pipeline to collect raw data, create features and generate training datasets.

```bash
docker compose run --rm collect-training
```

Equivalent to:

```bash
dvc repro src/pipelines/dvc.yaml
```

---

## 2. Train the model

Train the XGBoost model and register it in MLflow / Dagshub.

```bash
docker compose run --rm training
```

Equivalent to:

```bash
python src/models/training.py
```

---

## 3. Prepare inference data

Generate the latest weather features for a specific city and save them in `data/inference`.

Default city:

```bash
docker compose run --rm collect-inference
```

Specify a city:

```bash
CITY=Canberra docker compose run --rm collect-inference
```

Equivalent to:

```bash
python src/data/collect_inference.py --city Canberra
```

---

## 4. Run prediction from CLI

Use the latest inference JSON file for a city and predict tomorrow's weather.

Default city:

```bash
docker compose run --rm predict
```

Specify a city:

```bash
CITY=Canberra docker compose run --rm collect-inference
CITY=Canberra docker compose run --rm predict
```

Equivalent to:

```bash
python src/models/predict.py --city Canberra
```

---

## 5. Run API service

Start the FastAPI application.

```bash
docker compose up -d api
```

Check logs:

```bash
docker compose logs -f api
```

Test endpoints:


```bash
curl -X POST http://127.0.0.1:8000/predict \
  -H "Content-Type: application/json" \
  -d '{"city":"Sydney"}'
```

Stop API:

```bash
docker compose stop api
```

---

## 6. Run Streamlit interface

Start the Streamlit application.

```bash
docker compose up -d interface
```

Check logs:

```bash
docker compose logs -f interface
```

Open in browser:

```text
http://localhost:8501
```

Stop interface:

```bash
docker compose stop interface
```

---

## Full workflow

### Initial model training

```bash
docker compose run --rm collect-training
docker compose run --rm training
```

### Generate inference data

```bash
CITY=Sydney docker compose run --rm collect-inference
```

### Start API

```bash
docker compose up -d api
```

### Predict

```bash
curl "http://localhost:8000/predict?city=Sydney"
```

---

## 7. Airflow orchestration

Runs the two DAGs in `dags/`: `data_pipeline` (dvc repro → dvc push → git commit/push → triggers training) and `model_training` (train → restart api). Both use `DockerOperator`, so tasks run in their own container rather than inside the Airflow containers.

### Setup

```bash
cp .env.example .env
# fill in DAGSHUB_USER_TOKEN, GITHUB_TOKEN, HOST_PROJECT_PATH (absolute path to this repo on YOUR machine)
```

### Which image do the DAG tasks run?

Both DAGs read `TRAINING_IMAGE` from `.env` and default to `ghcr.io/eveangelion/mlops-meteo-australie/training:latest` (built by [.github/workflows/build-push-images.yml](.github/workflows/build-push-images.yml) on push to `main`). **That GHCR package is private** — pulling it without `docker login ghcr.io` fails with `403 Forbidden`.

For local testing, build the training image yourself first and point `TRAINING_IMAGE` at it in `.env`:

```bash
docker build -t mlops_meteo_australie-training:latest -f src/training/Dockerfile .
# in .env:
# TRAINING_IMAGE=mlops_meteo_australie-training:latest
```

Only switch to the registry image once you've verified the DAGs work locally (and either the package is made public or you've run `docker login ghcr.io`).

### Start Airflow

```bash
docker compose up airflow-init                                      # one-off: db migrate + creates admin/admin
docker compose up -d postgres airflow-webserver airflow-scheduler
```

Open [http://localhost:8080](http://localhost:8080) (`admin` / `admin`). Check both DAGs loaded cleanly:

```bash
docker compose exec airflow-scheduler airflow dags list-import-errors
```

### Test a single task without side effects

```bash
docker compose exec airflow-scheduler airflow tasks test data_pipeline raw_processed 2026-07-23
```

### Trigger a full run

```bash
docker compose exec airflow-scheduler airflow dags trigger data_pipeline
```

Note: a full `data_pipeline` run really pushes to DagsHub (`dvc_push`) and commits/pushes `dvc.lock` to GitHub (`git_commit_push`) using the credentials in `.env` — it is not a dry run.

**Before triggering `model_training` (directly or via `data_pipeline`): make sure `api` is already running (`docker compose up -d api`).** Its last task, `restart_api`, runs `docker restart mlops_meteo_australie-api-1` — if that container doesn't exist yet, the task fails.

---

## Stop all services

```bash
docker compose down
```