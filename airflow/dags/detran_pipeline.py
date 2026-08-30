"""DAG diário: scrape → dbt run → dbt test."""

from __future__ import annotations

import os
from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

# Dentro do compose, postgres expõe 5432; no host é 5435.
DB_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://scraper:scraper@postgres:5432/detran_leiloes",
)
DBT_ENV = {
    "DBT_HOST": os.environ.get("DBT_HOST", "postgres"),
    "DBT_PORT": os.environ.get("DBT_PORT", "5432"),
    "DBT_USER": os.environ.get("DBT_USER", "scraper"),
    "DBT_PASSWORD": os.environ.get("DBT_PASSWORD", "scraper"),
    "DBT_DATABASE": os.environ.get("DBT_DATABASE", "detran_leiloes"),
}

default_args = {
    "owner": "detran",
    "depends_on_past": False,
    "email_on_failure": False,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="detran_scrape_dbt",
    description="Scrape DETRAN/MG, materializa mart_dbt e roda testes dbt",
    schedule="0 6 * * *",
    start_date=datetime(2026, 1, 1),
    catchup=False,
    default_args=default_args,
    tags=["detran", "dbt"],
) as dag:
    scrape_lotes = BashOperator(
        task_id="scrape_lotes",
        bash_command="cd /opt/project && python -m detran_scraper.run --lotes",
        env={"DATABASE_URL": DB_URL},
    )

    dbt_run = BashOperator(
        task_id="dbt_run",
        bash_command="cd /opt/project/transform && dbt run --profiles-dir .",
        env=DBT_ENV,
    )

    dbt_test = BashOperator(
        task_id="dbt_test",
        bash_command="cd /opt/project/transform && dbt test --profiles-dir .",
        env=DBT_ENV,
    )

    scrape_lotes >> dbt_run >> dbt_test
