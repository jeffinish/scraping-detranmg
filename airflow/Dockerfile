FROM apache/airflow:2.10.4-python3.11

USER root
COPY . /opt/project
RUN chown -R airflow:root /opt/project

USER airflow
# ponytail: --no-deps evita sobrescrever SQLAlchemy do Airflow (quebra o scheduler).
RUN pip install --no-cache-dir -r /opt/project/airflow/requirements-airflow.txt \
    && pip install --no-cache-dir httpx beautifulsoup4 lxml python-dotenv psycopg2-binary \
    && pip install --no-cache-dir --no-deps -e /opt/project

WORKDIR /opt/airflow
