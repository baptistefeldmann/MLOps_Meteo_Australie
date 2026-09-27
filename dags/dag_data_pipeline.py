import os
from datetime import datetime
from docker.types import Mount

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.trigger_dagrun import TriggerDagRunOperator

HOST_PROJECT_PATH = os.environ.get("HOST_PROJECT_PATH")
TRAINING_IMAGE = "mlops_meteo_australie-training"

BASE_ENV = {
    "DAGSHUB_USER_TOKEN": os.environ.get("DAGSHUB_USER_TOKEN"),
    "DAGSHUB_USERNAME": os.environ.get("DAGSHUB_USERNAME"),
    "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
}

# Identifiants du depot GitHub cible par les taches qui committent/poussent.
GIT_ENV = {
    "GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN"),
    "GITHUB_USER": os.environ.get("GITHUB_USER"),
    "GITHUB_REPO": os.environ.get("GITHUB_REPO"),
}

PROJECT_MOUNT = Mount(source=HOST_PROJECT_PATH, target="/app", type="bind")


def docker_op(task_id, command, extra_env=None):
    env = {**BASE_ENV, **(extra_env or {})}
    return DockerOperator(
        task_id=task_id,
        image=TRAINING_IMAGE,
        command=command,
        mounts=[PROJECT_MOUNT],
        environment=env,
        docker_url="unix://var/run/docker.sock",
        working_dir="/app",
        auto_remove="success",
        retries=1,
    )


with DAG(
    dag_id="data_pipeline",
    schedule="@monthly",
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["data"],
) as dag:

    # CORRECTIF STRUCTUREL : restaurer l'etat versionne AVANT toute chose.
    # Sans ca, sur une machine ou data/ est vide, le pipeline reconstruit tout
    # a partir des seuls mois collectes puis pousse cette perte (incident du
    # 2026-06-03 : historique passe de 120 000 a 2 000 lignes).
    dvc_pull = docker_op(
        task_id="dvc_pull",
        command='bash -c "git config --global --add safe.directory /app && dvc pull"',
    )

    raw_processed = docker_op(
        task_id="raw_processed",
        command='bash -c "cd src/pipelines && dvc repro raw_processed"',
    )

    features = docker_op(
        task_id="features",
        command='bash -c "cd src/pipelines && dvc repro features"',
    )

    datasets = docker_op(
        task_id="datasets",
        command='bash -c "cd src/pipelines && dvc repro datasets"',
    )

    # Drift calcule a chaque nouvelle collecte : nouveau dataset vs reference
    # (= donnees d'entrainement du modele actuellement deploye).
    # Ecrit reports/drift_status.json, lu ensuite par le DAG model_training.
    drift_report = docker_op(
        task_id="drift_report",
        command="python -m src.monitoring.drift_report",
    )

    dvc_push = docker_op(
        task_id="dvc_push",
        command="dvc push",
    )

    git_commit_push = docker_op(
        task_id="git_commit_push",
        command="""bash -c "
            git config --global --add safe.directory /app &&
            git config user.email airflow@mlops.com &&
            git config user.name Airflow &&
            git remote set-url origin https://${GITHUB_USER}:${GITHUB_TOKEN}@github.com/${GITHUB_USER}/${GITHUB_REPO}.git &&
            git add src/pipelines/dvc.lock &&
            git diff --staged --quiet && echo 'Nothing to commit' || (git commit -m 'Auto: data update $(date +%F)' && git push)
        " """,
        extra_env=GIT_ENV,
    )

    trigger_training = TriggerDagRunOperator(
        task_id="trigger_model_training",
        trigger_dag_id="model_training",
    )

    dvc_pull >> raw_processed >> features >> datasets >> drift_report >> dvc_push >> git_commit_push >> trigger_training
