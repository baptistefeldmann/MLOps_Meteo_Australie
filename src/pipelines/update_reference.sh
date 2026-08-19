#!/bin/bash
# Met a jour + versionne (DVC) la reference de drift UNIQUEMENT si un nouveau
# best_model a ete promu lors du dernier entrainement.
#
# Lu par la tache Airflow "update_reference" (DAG model_training).
# Le marqueur reports/promotion_status.json est ecrit par src/training/training.py.
# Necessite : GITHUB_TOKEN + credentials DagsHub/AWS dans l'environnement.
set -e

STATUS_FILE="reports/promotion_status.json"

promoted=$(python -c "import json, os; p='${STATUS_FILE}'; print(json.load(open(p)).get('promoted', False) if os.path.exists(p) else False)")

if [ "$promoted" != "True" ]; then
    echo "Pas de promotion -> reference de drift inchangee."
    exit 0
fi

echo "Nouveau best_model promu -> mise a jour + versioning de la reference de drift."

# 1. Figer le dataset courant comme nouvelle reference
python -m src.monitoring.drift_report --update-reference

# 2. Versionner data/reference avec DVC + pousser sur le remote (DagsHub)
dvc add data/reference
dvc push

# 3. Committer le pointeur DVC sur Git
git config --global --add safe.directory /app
git config user.email airflow@mlops.com
git config user.name Airflow
git remote set-url origin "https://EveAngelion:${GITHUB_TOKEN}@github.com/EveAngelion/MLOps_Meteo_Australie.git"
git add data/reference.dvc data/.gitignore
if git diff --staged --quiet; then
    echo "Pointeur DVC inchange -> rien a committer."
else
    git commit -m "Auto: update drift reference $(date +%F)"
    git push
fi
