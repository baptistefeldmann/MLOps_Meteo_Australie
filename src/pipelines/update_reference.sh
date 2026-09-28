#!/bin/bash
# Met a jour + versionne (DVC) la reference de drift UNIQUEMENT si :
#   1. un nouveau best_model a ete promu lors du dernier entrainement
#      -> reports/promotion_status.json  (ecrit par src/training/training.py)
#   2. ET aucun drift n'a ete detecte lors de la derniere collecte
#      -> reports/drift_status.json      (ecrit par src/monitoring/drift_report.py)
#
# Rationale : on n'accepte pas silencieusement une distribution qui a derive comme
# nouvelle "normalite". En cas de drift, la reference reste en place (et le drift
# continue donc d'etre signale) jusqu'a une decision humaine :
#   docker compose run --rm drift python -m src.monitoring.drift_report --update-reference
#
# Lu par la tache Airflow "update_reference" (DAG model_training).
# Necessite : GITHUB_TOKEN + credentials DagsHub/AWS dans l'environnement.
set -e

PROMOTION_FILE="reports/promotion_status.json"
DRIFT_FILE="reports/drift_status.json"

read_flag() {
    # $1 = chemin du json, $2 = cle, $3 = valeur par defaut
    python -c "import json, os, sys; p=sys.argv[1]; print(json.load(open(p)).get(sys.argv[2], sys.argv[3]) if os.path.exists(p) else sys.argv[3])" "$1" "$2" "$3"
}

promoted=$(read_flag "$PROMOTION_FILE" promoted False)
drift=$(read_flag "$DRIFT_FILE" dataset_drift 0)

echo "Promotion d'un nouveau best_model : ${promoted}"
echo "Drift detecte a la derniere collecte : ${drift}"

if [ "$promoted" != "True" ]; then
    echo "-> Pas de nouveau best_model : reference inchangee."
    exit 0
fi

if [ "$drift" != "0" ]; then
    echo "-> Drift detecte : reference volontairement inchangee (investigation requise)."
    exit 0
fi

echo "-> Nouveau best_model ET pas de drift : mise a jour + versioning de la reference."

# 1. Figer le dataset courant comme nouvelle reference
python -m src.monitoring.drift_report --update-reference

# 2. Versionner data/reference avec DVC + pousser sur le remote (DagsHub)
dvc add data/reference
dvc push

# 3. Committer le pointeur DVC sur Git
git config --global --add safe.directory /app
git config user.email airflow@mlops.com
git config user.name Airflow
git add data/reference.dvc data/.gitignore
if git diff --staged --quiet; then
    echo "Pointeur DVC inchange -> rien a committer."
else
    git commit -m "Auto: update drift reference $(date +%F)"
    git push "https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git" HEAD
fi
