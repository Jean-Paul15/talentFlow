# Dockerfile Airflow pour talentFlow
FROM apache/airflow:2.8.1-python3.11

USER root

# Installation dependances systeme
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
    gcc \
    g++ \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

USER airflow

# Copie requirements
COPY requirements.txt /requirements.txt

# Installation packages Python
RUN pip install --no-cache-dir -r /requirements.txt

# Copie code source
COPY --chown=airflow:root . /opt/airflow/talentflow

WORKDIR /opt/airflow
