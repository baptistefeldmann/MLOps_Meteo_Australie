"""
Rapport de drift des donnees (Evidently)

Principe :
- reference = le dataset d'entrainement fige au moment ou le modele deploye
  (best_model) a ete entraine  ->  data/reference/data_reference.parquet
- current   = le dataset d'entrainement du cycle courant ->  data/datasets/data_train.parquet

On compare current vs reference pour detecter si les donnees ont derive
depuis l'entrainement du modele en production.

Sorties :
- un rapport HTML dans reports/drift/drift_<date>.html
- une synthese (part de colonnes driftees, drift cible...) affichee et,
  par defaut, logguee dans MLflow (experiment "Weather_AUS_Drift")

Gestion de la reference :
- au tout premier lancement (aucune reference), on initialise la reference
  depuis le dataset courant, puis on s'arrete (rien a comparer).
- apres la promotion d'un nouveau best_model, relancer avec --update-reference
  pour figer le nouveau dataset comme reference.

Exemples :
    python -m src.monitoring.drift_report
    python -m src.monitoring.drift_report --update-reference
    python -m src.monitoring.drift_report --no-mlflow --fail-on-drift
"""
import os
import os.path as osp
import json
import sys
import shutil
import logging
import argparse
from datetime import datetime

import pandas as pd

from evidently import ColumnMapping
from evidently.report import Report
from evidently.metric_preset import DataDriftPreset, TargetDriftPreset

try:
    PROJECT_ROOT = osp.join(osp.dirname(__file__))
except NameError:
    PROJECT_ROOT = os.getcwd()

DATA_FOLDER = osp.abspath(osp.join(PROJECT_ROOT, "..", "..", "data"))
REPORTS_FOLDER = osp.abspath(osp.join(PROJECT_ROOT, "..", "..", "reports", "drift"))

CURRENT_PATH = osp.join(DATA_FOLDER, "datasets", "data_train.parquet")
REFERENCE_PATH = osp.join(DATA_FOLDER, "reference", "data_reference.parquet")

# Marqueur lu par la tache Airflow "update_reference" (DAG model_training) :
# la reference n'est mise a jour que si AUCUN drift n'a ete detecte ici.
DRIFT_STATUS_FILE = osp.abspath(osp.join(PROJECT_ROOT, "..", "..", "reports", "drift_status.json"))

# Workspace servi par le service `evidently-ui` (docker compose).
WORKSPACE_PATH = osp.abspath(osp.join(PROJECT_ROOT, "..", "..", "reports", "evidently_workspace"))
PROJECT_NAME = "Weather AUS - Data Drift"

TARGET = "RainTomorrow"

# MLflow / DagsHub (memes coordonnees que training.py)
MLFLOW_PARAMS = {
    "repo_owner": os.environ["DAGSHUB_USERNAME"],
    "repo_name": "MLOps_Meteo_Australie",
    "experiment_name": "Weather_AUS_Drift",
}

def get_logger():
    logger = logging.getLogger("drift_report")
    logger.setLevel(logging.INFO)
    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(
            logging.Formatter("%(asctime)s [%(levelname)s] %(message)s", "%Y-%m-%d %H:%M:%S")
        )
        logger.addHandler(handler)
    logger.propagate = False
    return logger

logger = get_logger()

def update_reference(current_path=CURRENT_PATH, reference_path=REFERENCE_PATH):
    """Fige le dataset courant comme nouvelle reference (a appeler apres promotion d'un best_model)."""
    if not osp.exists(current_path):
        raise FileNotFoundError(f"Current dataset not found : {current_path}")
    os.makedirs(osp.dirname(reference_path), exist_ok=True)
    shutil.copyfile(current_path, reference_path)
    logger.info(f"Reference mise a jour : {current_path} -> {reference_path}")

def _align_columns(reference_df, current_df):
    """Ne garde que les colonnes communes (le schema des features peut evoluer dans le temps)."""
    common = [c for c in reference_df.columns if c in current_df.columns]
    missing = set(reference_df.columns).symmetric_difference(current_df.columns)
    if missing:
        logger.warning(f"Ignored unmatched columns : {sorted(missing)}")
    if TARGET not in common:
        raise ValueError(f"Target '{TARGET}' is missing from columns")
    return reference_df[common], current_df[common]

def extract_drift_summary(report):
    """Extrait les metriques cles du rapport Evidently (robuste)."""
    summary = {}
    for metric in report.as_dict().get("metrics", []):
        name = metric.get("metric")
        result = metric.get("result", {})
        if name == "DatasetDriftMetric":
            summary["dataset_drift"] = int(bool(result.get("dataset_drift")))
            summary["share_of_drifted_columns"] = float(result.get("share_of_drifted_columns", 0.0))
            summary["number_of_drifted_columns"] = int(result.get("number_of_drifted_columns", 0))
            summary["number_of_columns"] = int(result.get("number_of_columns", 0))
        elif name == "ColumnDriftMetric" and result.get("column_name") == TARGET:
            summary["target_drift_score"] = float(result.get("drift_score", 0.0))
            summary["target_drift_detected"] = int(bool(result.get("drift_detected")))
    return summary

def log_to_mlflow(summary, html_path):
    """Loggue la synthese de drift + le rapport HTML dans MLflow (DagsHub)."""
    import dagshub
    import mlflow

    dagshub.auth.add_app_token(token=os.environ["DAGSHUB_USER_TOKEN"])
    dagshub.init(
        repo_owner=MLFLOW_PARAMS["repo_owner"],
        repo_name=MLFLOW_PARAMS["repo_name"],
        mlflow=True,
    )
    mlflow.set_experiment(MLFLOW_PARAMS["experiment_name"])
    run_name = datetime.now().strftime("drift_%Y-%m-%d_%H-%M")
    with mlflow.start_run(run_name=run_name):
        if summary:
            mlflow.log_metrics(summary)
        mlflow.log_artifact(html_path, artifact_path="drift_report")
    logger.info("Synthese de drift logguee dans MLflow")

def write_drift_status(summary, computed=True):
    """Ecrit le marqueur de drift consomme par la tache Airflow update_reference."""
    os.makedirs(osp.dirname(DRIFT_STATUS_FILE), exist_ok=True)
    payload = {
        "computed": bool(computed),
        "dataset_drift": int(summary.get("dataset_drift", 0)),
        "share_of_drifted_columns": float(summary.get("share_of_drifted_columns", 0.0)),
        "timestamp": datetime.now().isoformat(timespec="seconds"),
    }
    with open(DRIFT_STATUS_FILE, "w") as dst:
        json.dump(payload, dst, indent=2)
    logger.info(f"Statut de drift ecrit : {DRIFT_STATUS_FILE} -> {json.dumps(payload)}")


def add_to_workspace(report):
    """Ajoute le rapport au workspace Evidently (servi par le service evidently-ui)."""
    from evidently.ui.workspace import Workspace

    os.makedirs(WORKSPACE_PATH, exist_ok=True)
    workspace = Workspace.create(WORKSPACE_PATH)
    projects = workspace.search_project(PROJECT_NAME)
    project = projects[0] if projects else workspace.create_project(
        PROJECT_NAME,
        description="Derive des donnees meteo : dataset courant vs reference du modele deploye.",
    )
    workspace.add_report(project.id, report)
    logger.info(f"Rapport ajoute au workspace Evidently : {WORKSPACE_PATH}")


def generate_report(reference_path=REFERENCE_PATH, current_path=CURRENT_PATH):
    reference_df = pd.read_parquet(reference_path)
    current_df = pd.read_parquet(current_path)
    reference_df, current_df = _align_columns(reference_df, current_df)
    logger.info(f"Reference : {len(reference_df)} lignes | Current : {len(current_df)} lignes")

    column_mapping = ColumnMapping()
    column_mapping.target = TARGET

    report = Report(metrics=[DataDriftPreset(), TargetDriftPreset()])
    report.run(
        reference_data=reference_df,
        current_data=current_df,
        column_mapping=column_mapping,
    )

    os.makedirs(REPORTS_FOLDER, exist_ok=True)
    stamp = datetime.now().strftime("%Y-%m-%d_%H-%M")
    html_path = osp.join(REPORTS_FOLDER, f"drift_{stamp}.html")
    report.save_html(html_path)
    logger.info(f"Rapport HTML : {html_path}")

    # Snapshot pour l'UI Evidently (ne doit jamais faire echouer le rapport)
    try:
        add_to_workspace(report)
    except Exception as exc:
        logger.warning(f"Ajout au workspace Evidently ignore ({exc})")

    summary = extract_drift_summary(report)
    logger.info(f"Synthese drift : {json.dumps(summary)}")
    return html_path, summary

def main():
    parser = argparse.ArgumentParser(
        description="Rapport de drift Evidently (reference = snapshot du modele deploye)."
    )
    parser.add_argument(
        "--update-reference", action="store_true",
        help="Fige le dataset courant comme nouvelle reference, puis quitte (apres promotion d'un best_model).",
    )
    parser.add_argument(
        "--no-mlflow", action="store_true",
        help="Ne pas logguer la synthese dans MLflow.",
    )
    parser.add_argument(
        "--fail-on-drift", action="store_true",
        help="Sortie en erreur (code 1) si un drift dataset est detecte.",
    )
    parser.add_argument(
        "--reference", default=REFERENCE_PATH, help="Chemin du dataset de reference.",
    )
    parser.add_argument(
        "--current", default=CURRENT_PATH, help="Chemin du dataset courant.",
    )
    args = parser.parse_args()

    # Ré-initialisation manuelle de la reference
    if args.update_reference:
        update_reference(current_path=args.current, reference_path=args.reference)
        return

    # Si 1ere fois, aucune reference -> on l'initialise et on s'arrete
    if not osp.exists(args.reference):
        logger.warning("No Reference found : Initialization from current dataset")
        update_reference(current_path=args.current, reference_path=args.reference)
        write_drift_status({}, computed=False)
        logger.info("Initialization succes, no drift computed for first run")
        return

    html_path, summary = generate_report(reference_path=args.reference, current_path=args.current)
    write_drift_status(summary)

    if not args.no_mlflow:
        try:
            log_to_mlflow(summary, html_path)
        except Exception as exc:  # ne jamais faire echouer le rapport a cause de MLflow
            logger.warning(f"Log MLflow ignore ({exc})")

    if summary.get("dataset_drift"):
        share = summary.get("share_of_drifted_columns", 0.0)
        logger.warning(f"/!\\ DRIFT detected : {share:.1%} drifted columns")
        if args.fail_on_drift:
            sys.exit(1)
    else:
        logger.info("No drift detected !")

if __name__ == "__main__":
    main()
