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

with DAG(
    dag_id="model_training",
    schedule=None,  # triggered by data_pipeline DAG
    start_date=datetime(2026, 7, 1),
    catchup=False,
    tags=["training"],
) as dag:

    train_model = DockerOperator(
        task_id="train_model",
        image=TRAINING_IMAGE,
        command="python -m src.training.training",
        mounts=[PROJECT_MOUNT],
        environment=BASE_ENV,
        docker_url="unix://var/run/docker.sock",
        working_dir="/app",
        auto_remove="success",
        retries=1,
    )

    restart_api = BashOperator(
        task_id="restart_api",
        bash_command="docker restart mlops_meteo_australie-api-1",
    )

    train_model >> restart_api
