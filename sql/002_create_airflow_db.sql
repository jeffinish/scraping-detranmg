-- Banco de metadados do Airflow (mesmo container Postgres, volume já existente).
-- Em volume novo: roda no init via docker-entrypoint-initdb.d.
-- Em volume antigo: CREATE DATABASE airflow; GRANT ALL ON DATABASE airflow TO scraper;

SELECT 'CREATE DATABASE airflow'
WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'airflow')\gexec

GRANT ALL PRIVILEGES ON DATABASE airflow TO scraper;
