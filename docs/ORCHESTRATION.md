# Orquestração local (Airflow + dbt)

Contrato para replicar este padrão em outros projetos de scraping/EL.

## Stack desta rodada

| Peça | Papel |
|------|-------|
| `python -m detran_scraper.run` | **EL** — grava `raw.*` e `mart.*` (Python, até cutover) |
| `transform/` (dbt) | **T** — reconstrói `mart_dbt.*` a partir de `raw.*` |
| `src/detran_ui/` + `ui/` | **Consumo** — lê `mart_dbt`; grava `mart.lotes_interesse` |
| Airflow (`docker-compose.airflow.yml`) | Scheduler: scrape → `dbt run` → `dbt test` |
| `scripts/reconcile_mart.py` | Gate de cutover: compara `mart` vs `mart_dbt` |

AWS (EventBridge, ECS, MWAA) fica para o capítulo seguinte, quando o DAG local já rodar todo dia sem depender do PC.

## Subir localmente

```bash
# 1. Postgres (se ainda não estiver)
docker compose up -d

# Banco airflow (só em volume Postgres já existente antes de sql/002):
#   docker exec -it detran_leiloes_db psql -U scraper -d detran_leiloes -c "CREATE DATABASE airflow;"

# 2. Scrape (popula raw)
python -m detran_scraper.run --lotes

# 3. dbt (host — porta 5435)
pip install -r transform/requirements.txt
cd transform && dbt run --profiles-dir . && dbt test --profiles-dir .

# 4. Reconciliação
python scripts/reconcile_mart.py

# 5. UI (lê mart_dbt — obrigatório após dbt)
pip install -e ".[ui]"
python -m detran_ui
# dev: cd ui && npm run dev

# 6. Airflow (opcional)
# Pré-requisito: banco `airflow` no Postgres (sql/002 ou CREATE DATABASE manual)
docker compose -f docker-compose.yml -f docker-compose.airflow.yml build airflow
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d airflow
docker exec detran_airflow airflow dags trigger detran_scrape_dbt
# UI Airflow: http://localhost:8090 (credenciais no 1º boot — ver logs do container)
```

## Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| `DATABASE_URL` | Scraper + reconcile + UI (host: `localhost:5435`) |
| `MART_SCHEMA` | Schema analítico da UI (default: `mart_dbt`) |
| `DBT_HOST`, `DBT_PORT`, … | dbt (`profiles.yml`); no Airflow: `postgres:5432` |
| `DETRAN_COOKIE` | Opcional; necessário para `--lances` (não no DAG padrão) |

## DAG padrão

`airflow/dags/detran_pipeline.py` — `detran_scrape_dbt`:

1. `scrape_lotes` — `python -m detran_scraper.run --lotes`
2. `dbt_run`
3. `dbt_test`

Schedule: `0 6 * * *` (06:00 UTC). Ajuste no DAG se quiser horário BR.

## Contrato para o próximo projeto

Copie este esqueleto:

1. **CLI de carga** com exit code ≠ 0 em falha (`python -m <pkg>.run …`)
2. **Camada raw** append-only no Postgres (schema `raw`)
3. **Pasta `transform/`** com dbt: staging 1:1 + mart em schema paralelo até reconciliar
4. **Um DAG** com três tasks: scrape → dbt run → dbt test
5. **Script de reconciliação** antes de apontar notebooks/BI para o mart dbt
6. **`.env.example`** documentando `DATABASE_URL` e secrets de sessão

Não duplicar lógica de transformação no Python depois do cutover — o mart dbt vira fonte de verdade analítica.

## Cutover (quando `reconcile_mart.py` passar)

1. ~~Apontar UI para `mart_dbt`~~ (feito — `MART_SCHEMA=mart_dbt`)
2. Apontar notebooks `03` e `04` para `mart_dbt.*`
3. Remover upsert de mart em `storage.py` (rodada seguinte)
4. Curadoria extra (split `marca_modelo`, tombstone, etc.) com testes regressando o mart
