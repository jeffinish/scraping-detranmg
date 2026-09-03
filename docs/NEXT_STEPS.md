# Próximos passos

Roadmap após a curadoria de identidade do lote (`feat/dbt-lote-identidade`): `marca` / `modelo` / `ano_veiculo` no `mart_dbt` e na UI.

## Estado atual (entregue)

| Componente | Status |
|------------|--------|
| Scraper EL (`run.py`) | Grava `raw.*` + `mart.*` (dual-run) |
| dbt (`transform/`) | `mart_dbt.*` + seed `marca_aliases`; 29 testes |
| Reconciliação | `scripts/reconcile_mart.py` — colunas do mart Python ainda batem |
| UI (Vite/React + FastAPI) | Lê `marca` / `modelo` / `ano_veiculo`; interesse em `mart.lotes_interesse` |
| Airflow local | DAG `detran_scrape_dbt`: scrape → dbt seed+run → dbt test |

**Carga de referência (2026-08-31):** `run_id=48e777df-…`, 61 editais, 6.346 lotes no scrape; `mart_dbt.mart_lotes` = 11.772 (acumulado sem purge).

## 1. Cutover completo do mart (prioridade alta)

- [ ] Apontar notebooks `03_analise_mart.ipynb` e `04_watchlist_alertas.ipynb` para `mart_dbt.*`
- [ ] Remover upsert de `mart.*` em `storage.py` (scraper = só EL)
- [ ] Atualizar `docs/REFERENCE.md` com schema canônico `mart_dbt`
- [ ] Rodar `reconcile_mart.py` uma última vez; depois simplificar ou arquivar o script

## 2. CI (prioridade alta)

- [ ] GitHub Actions: `pytest` (fixtures offline)
- [ ] Job Postgres service: `dbt seed` + `dbt run` + `dbt test` em PR
- [ ] Opcional: smoke `test_ui_queries.py` sem rede

## 3. Airflow — endurecer operação

**Validado em 2026-08-31:** DAG `detran_scrape_dbt` com `scrape_lotes` → `dbt_run` (inclui `dbt seed`) → `dbt_test`. Imagem: `airflow/Dockerfile` (`pip install --no-deps`); `DBT_BIN` no DAG.

- [ ] Variável/param `max_editais` no DAG para runs de dev mais rápidos
- [ ] Montar `/opt/project` como volume (evitar rebuild da imagem a cada mudança de código)
- [ ] Alertas: falha de task → log + notificação (local: e-mail desligado; cloud depois)
- [ ] Documentar credenciais standalone (`docker logs detran_airflow` na 1ª subida)

## 4. Curadoria analítica

- [x] Split `marca_modelo` → marca / modelo / `ano_veiculo` em model dbt (`marca_aliases` seed) + UI
- [x] Tombstone de lotes ausentes no último scrape completo (`mart_dbt.mart_lotes.ativo`; UI esconde com toggle)
- [ ] Histerese de 2 runs / tombstone de edital / probe de detalhe para status de lote
- [ ] Expor campos de enriquecimento `--lances` na UI (`cor`, `ano_modelo`, `valor_inicial`)
- [ ] `tipo_veiculo` via enriquecimento (POST por tipo ou PDF — fora do card HTML)

## 5. AWS (quando o DAG local rodar todo dia sem o PC)

- [ ] EventBridge + ECS Fargate (scrape + dbt) **ou** MWAA se hub multi-projeto
- [ ] RDS Postgres ou manter volume gerenciado
- [ ] CloudWatch alarms em falha de task
- [ ] Secrets Manager para `DETRAN_COOKIE` (se `--lances` for para nuvem)

## 6. UI

- [x] Card/detalhe com `marca`, `modelo`, `ano_veiculo` parseados
- [ ] Detalhe do lote / galeria de imagens
- [ ] Deploy estático (build Vite + API atrás de reverse proxy) ou manter local

## Comandos de referência

```bash
# Pipeline manual
docker compose up -d
python -m detran_scraper.run --lotes
cd transform && dbt seed --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .
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
