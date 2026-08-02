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
    "AWS_ACCESS_KEY_ID": os.environ.get("AWS_ACCESS_KEY_ID"),
    "AWS_SECRET_ACCESS_KEY": os.environ.get("AWS_SECRET_ACCESS_KEY"),
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
            git remote set-url origin https://EveAngelion:${GITHUB_TOKEN}@github.com/EveAngelion/MLOps_Meteo_Australie.git &&
            git add src/pipelines/dvc.lock &&
            git diff --staged --quiet && echo 'Nothing to commit' || (git commit -m 'Auto: data update $(date +%F)' && git push)
        " """,
        extra_env={"GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN")},
    )

    trigger_training = TriggerDagRunOperator(
        task_id="trigger_model_training",
        trigger_dag_id="model_training",
    )

    raw_processed >> features >> datasets >> dvc_push >> git_commit_push >> trigger_training
