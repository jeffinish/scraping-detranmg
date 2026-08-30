FROM apache/airflow:2.10.4-python3.11

USER root
COPY . /opt/project
RUN chown -R airflow:root /opt/project

USER airflow
RUN pip install --no-cache-dir -r /opt/project/airflow/requirements-airflow.txt \
    && pip install --no-cache-dir -e /opt/project

WORKDIR /opt/airflow
