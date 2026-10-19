# Orquestração local (Airflow + dbt)

Contrato para replicar este padrão em outros projetos de scraping/EL.

## Stack desta rodada

| Peça | Papel |
|------|-------|
| `python -m detran_scraper.run` | **EL** — grava `raw.*`; imagens em `mart.lotes_imagens` |
| `transform/` (dbt) | **T** — reconstrói `mart_dbt.*` a partir de `raw.*` |
| `src/detran_ui/` + `ui/` | **Consumo** — lê `mart_dbt`; grava `mart.lotes_interesse` |
| Airflow (`docker-compose.airflow.yml`) | Scheduler: scrape lotes → (dbt seed+run → test) ∥ scrape imagens |
| `scripts/reconcile_mart.py` | Histórico do gate (2026-10-12, exit 0). Fora do fluxo |

AWS (EventBridge, ECS, MWAA) fica para o capítulo seguinte, quando o DAG local já rodar todo dia sem depender do PC.

## Subir localmente

```bash
# 1. Postgres (se ainda não estiver)
docker compose up -d

# Banco airflow (só em volume Postgres já existente antes de sql/002):
#   docker exec -it detran_leiloes_db psql -U scraper -d detran_leiloes -c "CREATE DATABASE airflow;"

# 2. Scrape (popula raw)
python -m detran_scraper.run --lotes
python -m detran_scraper.run --imagens   # galeria CONSERVADO; ver docs/IMAGENS.md

# 3. dbt (host — porta 5435)
pip install -r transform/requirements.txt
cd transform && dbt seed --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .

# 4. UI (lê mart_dbt — obrigatório após dbt)
pip install -e ".[ui]"
python -m detran_ui
# dev: cd ui && npm run dev

# 5. Airflow (opcional)
# Pré-requisito: banco `airflow` no Postgres (sql/002 ou CREATE DATABASE manual)
docker compose -f docker-compose.yml -f docker-compose.airflow.yml build airflow
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d airflow
docker exec detran_airflow airflow dags trigger detran_scrape_dbt
# UI Airflow: http://localhost:8090 (credenciais no 1º boot — ver logs do container)
```

## Variáveis de ambiente

| Variável | Uso |
|----------|-----|
| `DATABASE_URL` | Scraper + UI (host: `localhost:5435`) |
| `IMAGENS_DIR` | Galeria CAS (`--imagens`); default `data/imagens/` — [IMAGENS.md](IMAGENS.md) |
| `DBT_HOST`, `DBT_PORT`, … | dbt (`profiles.yml`); no Airflow: `postgres:5432` |
| `DETRAN_COOKIE` | Opcional; necessário para `--lances` (não no DAG padrão) |

## DAG padrão

`airflow/dags/detran_pipeline.py` — `detran_scrape_dbt`:

1. `scrape_lotes` — `python -m detran_scraper.run --lotes`
2. `scrape_imagens` — `python -m detran_scraper.run --imagens` (CONSERVADO incremental; em paralelo com dbt)
3. `dbt_run` — `dbt seed` + `dbt run` (seed `marca_aliases` precisa existir antes do mart)
4. `dbt_test`

Schedule: `0 6 * * *` (06:00 UTC). Ajuste no DAG se quiser horário BR.

## Contrato para o próximo projeto

Copie este esqueleto:

1. **CLI de carga** com exit code ≠ 0 em falha (`python -m <pkg>.run …`)
2. **Camada raw** append-only no Postgres (schema `raw`)
3. **Pasta `transform/`** com dbt: staging 1:1 + mart analítico. Um mart Python paralelo só até o primeiro reconcile limpo
4. **Um DAG** com scrape → (dbt run ∥ imagens) → dbt test
5. **Um reconcile** antes de apontar notebooks/BI para o mart dbt; depois o script sai do fluxo diário
6. **`.env.example`** documentando `DATABASE_URL` e secrets de sessão

Não duplicar lógica de transformação no Python depois do cutover — o mart dbt vira fonte de verdade analítica.

## Cutover (fechado em 2026-10-12)

1. UI lê `mart_dbt` (sem `MART_SCHEMA`)
2. Notebooks `03` e `04` leem `mart_dbt.*`
3. Scraper não faz upsert de `mart.editais` / `mart.lotes` / lances / histórico de status
4. Curadoria ainda aberta: histerese de `ativo`, expor `cor` / `valor_inicial` na UI
