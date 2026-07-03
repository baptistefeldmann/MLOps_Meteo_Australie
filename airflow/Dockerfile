FROM apache/airflow:2.9.2
USER root
RUN apt-get update && apt-get install -y docker.io && rm -rf /var/lib/apt/lists/*
COPY airflow/init.sh /init.sh
RUN chmod +x /init.sh
USER airflow
RUN pip install apache-airflow-providers-docker
