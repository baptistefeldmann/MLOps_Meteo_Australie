import os
from datetime import datetime
from docker.types import Mount

from airflow import DAG
from airflow.providers.docker.operators.docker import DockerOperator
from airflow.operators.bash import BashOperator

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
    dag_id="model_training",
    schedule=None,  # triggered by data_pipeline DAG
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["training"],
) as dag:

    train_model = docker_op(
        task_id="train_model",
        command="python -m src.training.training",
    )

    # La reference n'est mise a jour + versionnee (DVC) que si les DEUX
    # conditions sont reunies :
    #   - un nouveau best_model a ete promu   (reports/promotion_status.json, ecrit par training.py)
    #   - aucun drift n'a ete detecte         (reports/drift_status.json, ecrit par le DAG data_pipeline)
    update_reference = docker_op(
        task_id="update_reference",
        command="bash src/pipelines/update_reference.sh",
        extra_env={"GITHUB_TOKEN": os.environ.get("GITHUB_TOKEN")},
    )

    restart_api = BashOperator(
        task_id="restart_api",
        bash_command="docker restart mlops_meteo_australie-api-1",
    )

    # Le service repart avec le nouveau modele des la fin de l'entrainement.
    train_model >> restart_api
    # Branche monitoring : mise a jour conditionnelle de la reference de drift.
    train_model >> update_reference
