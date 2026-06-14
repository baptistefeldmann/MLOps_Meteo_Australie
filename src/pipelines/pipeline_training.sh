#!/bin/bash

# Script path
SCRIPT_PATH="$( cd "$( dirname "${BASH_SOURCE[0]}" )" >/dev/null 2>&1 && pwd )"

# Volumes path
PROJ_PATH="$SCRIPT_PATH/.."

dvc repro dvc.yaml                            # collecte + (ré)entraîne, met à jour dvc.lock
dvc push                                      # envoie les nouvelles données vers DagsHub Storage
git add dvc.lock dvc.yaml                      # versionne les pointeurs
git commit -m "Auto: retrain $(date +%F_%T)"
git push