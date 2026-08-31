# Próximos passos

Roadmap após a entrega da camada **dbt + Airflow local + UI em `mart_dbt`** (branch `feat/dbt-airflow-local`).

## Estado atual (entregue)

| Componente | Status |
|------------|--------|
| Scraper EL (`run.py`) | Grava `raw.*` + `mart.*` (dual-run) |
| dbt (`transform/`) | Materializa `mart_dbt.*` com 23 testes |
| Reconciliação | `scripts/reconcile_mart.py` — 0 divergências no banco de referência |
| UI (Vite/React + FastAPI) | Lê `mart_dbt` via `MART_SCHEMA`; interesse em `mart.lotes_interesse` |
| Airflow local | DAG `detran_scrape_dbt`: scrape → dbt run → dbt test |

## 1. Cutover completo do mart (prioridade alta)

- [ ] Apontar notebooks `03_analise_mart.ipynb` e `04_watchlist_alertas.ipynb` para `mart_dbt.*`
- [ ] Remover upsert de `mart.*` em `storage.py` (scraper = só EL)
- [ ] Atualizar `docs/REFERENCE.md` com schema canônico `mart_dbt`
- [ ] Rodar `reconcile_mart.py` uma última vez; depois simplificar ou arquivar o script

## 2. CI (prioridade alta)

- [ ] GitHub Actions: `pytest` (fixtures offline)
- [ ] Job Postgres service: `dbt run` + `dbt test` em PR
- [ ] Opcional: smoke `test_ui_queries.py` sem rede

## 3. Airflow — endurecer operação

**Validado em 2026-08-31:** DAG `detran_scrape_dbt` com `scrape_lotes` → `dbt_run` → `dbt_test` (23/23 testes). Correções aplicadas: `airflow/Dockerfile` (`pip install --no-deps` para não quebrar SQLAlchemy do Airflow); `DBT_BIN` no DAG (`/home/airflow/.local/bin/dbt`).

- [ ] Variável/param `max_editais` no DAG para runs de dev mais rápidos
- [ ] Montar `/opt/project` como volume (evitar rebuild da imagem a cada mudança de código)
- [ ] Alertas: falha de task → log + notificação (local: e-mail desligado; cloud depois)
- [ ] Documentar credenciais standalone (`docker logs detran_airflow` na 1ª subida)

## 4. Curadoria analítica (após cutover)

- [ ] Split `marca_modelo` → marca / modelo em model dbt
- [ ] Tombstone de lotes/editais ausentes no último run
- [ ] Expor campos de enriquecimento na UI (`cor`, `ano_modelo`, `valor_inicial`)
- [ ] `tipo_veiculo` via enriquecimento (POST por tipo ou PDF — fora do card HTML)

## 5. AWS (quando o DAG local rodar todo dia sem o PC)

- [ ] EventBridge + ECS Fargate (scrape + dbt) **ou** MWAA se hub multi-projeto
- [ ] RDS Postgres ou manter volume gerenciado
- [ ] CloudWatch alarms em falha de task
- [ ] Secrets Manager para `DETRAN_COOKIE` (se `--lances` for para nuvem)

## 6. UI

- [ ] Detalhe do lote / galeria de imagens
- [ ] Deploy estático (build Vite + API atrás de reverse proxy) ou manter local

## Comandos de referência

```bash
# Pipeline manual
docker compose up -d
python -m detran_scraper.run --lotes
cd transform && dbt run --profiles-dir . && dbt test --profiles-dir .
python scripts/reconcile_mart.py

# UI (após dbt)
pip install -e ".[ui]"
cd ui && npm run build && cd ..
python -m detran_ui

# Airflow
docker compose -f docker-compose.yml -f docker-compose.airflow.yml up -d airflow
docker exec detran_airflow airflow dags trigger detran_scrape_dbt
# UI Airflow: http://localhost:8090
```
