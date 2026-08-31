# AGENTS.md — ponto de entrada para agentes de IA

Leia este arquivo antes de alterar o repositório. Detalhes técnicos e convenções estão nos docs linkados abaixo.

## Mapa rápido

| Precisa de… | Vá em… |
|-------------|--------|
| Visão humana / setup | [README.md](README.md) |
| URLs, seletores, schema, pipeline | [docs/REFERENCE.md](docs/REFERENCE.md) |
| Convenções já adotadas no código | [docs/PRACTICES.md](docs/PRACTICES.md) |
| Orquestração local (Airflow + dbt) | [docs/ORCHESTRATION.md](docs/ORCHESTRATION.md) |
| Roadmap / próximos passos | [docs/NEXT_STEPS.md](docs/NEXT_STEPS.md) |
| Código do scraper | `src/detran_scraper/` |
| Transformação SQL (dbt) | `transform/` |
| UI local (API + Vite/React) | `src/detran_ui/` + `ui/` |
| Schema Postgres | `sql/001_init.sql` + `sql/002_create_airflow_db.sql` + `sql/003_lotes_lances.sql` + `sql/004_lotes_interesse.sql` |

## Escopo do projeto

Scraper local do portal [leilao.detran.mg.gov.br](https://leilao.detran.mg.gov.br/): editais + lotes → Postgres (`raw` / `mart`) → dbt (`mart_dbt`) → notebooks + UI Vite/React (API FastAPI).

**Não está no escopo atual:** AWS, download de fotos, `tipo_veiculo` (filtro do portal, não campo no lote), POST de lance (`/lotes/ajaxLance`).

## Onde mudar o quê

| Mudança | Arquivo(s) |
|---------|------------|
| HTML / seletores / regex | `parsers.py` (fonte única) |
| HTTP, headers, paginação | `client.py` |
| Campos de domínio | `models.py` + `sql/001_init.sql` + `sql/003_*.sql` + `storage.py` |
| Orquestração CLI | `run.py` |
| Transformação mart (dbt) | `transform/` (models + `seeds/marca_aliases.csv`) |
| Lances / detalhe (zona logada) | `parsers.py` (JSON + HTML) + `client.py` (`DETRAN_COOKIE`) |
| Orquestração agendada | `airflow/dags/` + `docker-compose.airflow.yml` |
| UI / flag de interesse | `src/detran_ui/` (API) + `ui/` (Vite/React); lê `mart_dbt` (`marca`/`modelo`/`ano_veiculo`), grava `mart.lotes_interesse` |
| Exploração / watchlist | `notebooks/` (não duplicar lógica de produção sem necessidade) |

## Regras operacionais

1. Preferir o menor diff que resolve o problema.
2. Não inventar campos no card que o HTML não expõe (ex.: `tipo_veiculo`). Split de `marca_modelo` é T no dbt, não no parser.
3. Validar parser contra HTML real ou fixture antes de “corrigir” no escuro.
4. Após mudança de schema: `sql/001_init.sql` (installs novos) + incrementos aditivos `sql/003_*.sql`, `sql/004_*.sql` (sem DROP). Models e storage juntos.
5. Não commitar `.env`, dumps HTML locais (`_diag/`), nem outputs grandes de notebook sem pedido.

## Comando de referência

```bash
docker compose up -d
python -m detran_scraper.run --lotes
python -m detran_scraper.run --lances
cd transform && dbt seed --profiles-dir . && dbt run --profiles-dir . && dbt test --profiles-dir .
pip install -e ".[ui]"
python -m detran_ui
cd ui && npm install && npm run dev
```

Após `npm run build`, `python -m detran_ui` serve API + UI em `http://127.0.0.1:8080`. A UI lê `mart_dbt` — rode o dbt após cada scrape.
